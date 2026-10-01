#!/usr/bin/env python3
"""
preflight.py — the mechanical gates around a generation batch. Nothing here
submits; a session submits. This validates BEFORE and records AFTER.

    python3 preflight.py check    <batch.json> --run <run-dir> [--provider P] [--bank <path>]
                                  [--library <dir>]
    python3 preflight.py coverage --run <run-dir>
    python3 preflight.py verify   --run <run-dir> <media-uuid> --shot S3 --by <who> [--note ...]
    python3 preflight.py ledger   --run <run-dir> --model <slug> --job <id> --seconds N
                                  --status done|nsfw|ip_detected|failed [--tier ..] [--resolution ..]
                                  [--brand B] [--shot S3] [--note ...]
    python3 preflight.py verdict  --run <run-dir> <item-id> --layer inspector|motion|director
                                  (--json '<verdict-json>' | --file <path>)

Exit 0 green · 2 failures, each named [rule N] <item>: <what> → <what to do> · 3 bad input.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_BANK = HERE.parent / "formats" / "bank.json"

# platform.py shares its name with a stdlib module; load it by path so the
# import never depends on what sits first on sys.path.
_spec = importlib.util.spec_from_file_location("vm_platform", HERE / "platform.py")
platform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(platform)

# the model input contract — what each door actually takes. Loaded the same
# way, by path, and read as data: no field name, limit or door is written
# here, so a contract change lands in the gate without touching this file.
_mi_spec = importlib.util.spec_from_file_location("vm_model_inputs", HERE / "model_inputs.py")
model_inputs = importlib.util.module_from_spec(_mi_spec)
_mi_spec.loader.exec_module(model_inputs)

# the element library (components/elements) — rule 13. Loaded by path for the
# same reason as the two above, and because this folder has its own
# elements.py: library_check.py does the walk-up and the by-path import.
_lc_spec = importlib.util.spec_from_file_location("vm_library_check", HERE / "library_check.py")
library_check = importlib.util.module_from_spec(_lc_spec)
_lc_spec.loader.exec_module(library_check)

UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ELEMENT = re.compile(r"<<<([0-9a-fA-F-]{36})>>>")

POST_EFFECTS = [
    r"picture[- ]in[- ]picture", r"pip", r"captions?", r"subtitles?", r"luma[- ]key",
    r"chroma[- ]key", r"keyed", r"transitions?", r"borders?", r"circle overlay",
    r"title cards?", r"lower thirds",
    r"lower[- ]third (?:graphic|bar|strap|title|overlay|card)",
    r"on[- ]screen text",
]
_POST = re.compile(r"(?<![\w-])(" + "|".join(POST_EFFECTS) + r")(?![\w-])", re.I)
_NEGATED_LEAD = re.compile(r"^\s*(no|never|negatives)\b", re.I)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1) + "\n")


# ------------------------------------------------------------- the rules

# A run's brief is ONE document, and a run is checked one batch at a time.
# Reported per batch it arrives six times over; reported once it reads like
# what it is. Keyed on the file and the moment it was written, so a brief
# rewritten mid-session is read again.
_BRIEFS_SEEN: set = set()


def _brief_unseen(path: Path) -> bool:
    key = (str(path), path.stat().st_mtime_ns)
    if key in _BRIEFS_SEEN:
        return False
    _BRIEFS_SEEN.add(key)
    return True


def post_effect_hits(prompt: str) -> list[str]:
    """Post-effect words in a prompt, ignoring the sentences that forbid them —
    "No subtitles. No captions." is the prompt doing its job, not breaking it."""
    hits = []
    for sentence in re.split(r"[.\n;]", prompt or ""):
        if _NEGATED_LEAD.match(sentence):
            continue
        for m in _POST.finditer(sentence):
            before = sentence[:m.start()].rstrip().lower()
            if before.endswith(" no") or before == "no" or before.endswith(" without"):
                continue
            hits.append(m.group(1))
    return hits


def medias_of(item: dict) -> list[dict]:
    return [m for m in (item.get("medias") or []) if isinstance(m, dict)]


def references(item: dict) -> dict:
    params = item.get("params") or {}
    meds = medias_of(item)
    return {
        "image_refs": [m.get("value") for m in meds if m.get("role") == "image_references"],
        "start": [m.get("value") for m in meds if m.get("role") == "start_image"],
        "values": [m.get("value") for m in meds],
        "elements": ELEMENT.findall(params.get("prompt") or ""),
        "soul": bool(params.get("soul_id")),
        # the scene shape names the frame this clip starts on by the id of the
        # frame item the run makes, because the media id does not exist yet
        "frame": item.get("start_frame"),
    }


def load_bank_names(bank_path: Path) -> list[str] | None:
    d = read_json(bank_path)
    if d is None:
        return None
    rows = d
    if isinstance(d, dict):
        rows = None
        for k in ("formats", "rows", "bank"):
            if isinstance(d.get(k), list):
                rows = d[k]
                break
        if rows is None:
            rows = next((v for v in d.values() if isinstance(v, list)), [])
    # a deprecated row stays in the bank for the record but a run may not name it
    return [r.get("id") or r.get("name") for r in rows
            if isinstance(r, dict) and (r.get("id") or r.get("name"))
            and r.get("status") != "deprecated"]


def claims_in(batch: list[dict], reg: dict) -> dict[str, list[str]]:
    """line id → item ids that claim it (motion/revoice items only)."""
    out: dict[str, list[str]] = {}
    for it in batch:
        if platform.item_kind(it, reg) not in ("motion", "revoice"):
            continue
        for line in it.get("lines") or []:
            out.setdefault(str(line), []).append(str(it.get("id", "?")))
    return out


def other_batches(run: Path, skip_name: str | None = None) -> list[dict]:
    items = []
    for f in sorted((run / "batches").glob("*.json")):
        if skip_name and f.name == skip_name:
            continue
        try:
            items += platform.load_batch(f)
        except SystemExit:
            continue
    return items


def check(batch_path: Path, run: Path, provider_name: str | None, bank_path: Path,
          library_dir: Path | None = None) -> tuple[list[str], list[str]]:
    reg = platform.registry()
    pname, prov, _ = platform.resolve_provider(provider_name)
    batch = platform.load_batch(batch_path)
    fails, warns = [], []

    def fail(rule: int, iid: str, what: str, todo: str) -> None:
        fails.append(f"[rule {rule}] {iid}: {what} → {todo}")

    # rule 9 — the run names a format the bank knows
    run_json = read_json(run / "run.json")
    bank = load_bank_names(bank_path)
    if bank is None:
        fail(9, "run", f"format bank missing at {bank_path}", "add formats/bank.json from formats/TEMPLATE.md")
    elif not run_json:
        fail(9, "run", f"no run.json in {run}", "open the run: run.json with machine, brand, label, format")
    elif not run_json.get("format"):
        fail(9, "run", "run.json names no format", "add \"format\" to run.json — a name from formats/bank.json")
    elif run_json["format"] not in bank:
        fail(9, "run", f"format {run_json['format']!r} is not in the bank",
             "add it to formats/bank.json from formats/TEMPLATE.md")

    # rule 13 — THE ELEMENT LIBRARY IS ASKED TOO (2026-09-20). The library's
    # format/video list is built from the same bank plus the formats the owner
    # has named and nobody has defined — so it can refuse what the bank cannot:
    # a format that is a name and nothing else. The brief's delivery dials and
    # a `style_id` are asked of their lists the same way. Asked whenever the
    # run is on the real bank; a run pointed at another bank (`--bank`, the
    # tests' fixture universe) is only asked when it names a library as well.
    if library_dir is not None or Path(bank_path).resolve() == DEFAULT_BANK.resolve():
        brief_doc = None
        if (run / "brief.md").is_file():
            brief_doc, _ = model_inputs.json_block((run / "brief.md").read_text())
        try:
            for item, what, todo in library_check.problems(run_json, brief_doc, library_dir,
                                                           local_formats=bank or []):
                fail(13, item, what, todo)
        except library_check.NoLibrary as e:
            warns.append(f"[rule 13] the element library was not asked ({e}) — "
                         "format checked against formats/bank.json only")

    # rule 5 — the batch fits the provider's cap
    cap = prov.get("batch_max")
    if cap and len(batch) > cap:
        fail(5, "batch", f"{len(batch)} items over {pname}'s batch_max of {cap}",
             f"split into batches of {cap} and poll to terminal between them")

    frames = read_json(run / "frames.json", {}) or {}
    verdicts = read_json(run / "verdicts.json", {}) or {}

    for it in batch:
        iid = str(it.get("id", "?"))
        params = it.get("params") or {}
        slug = platform.item_model(it)
        model = reg["models"].get(slug or "")
        kind = platform.item_kind(it, reg)

        # rule 8 — the model is one this provider offers
        _, refusal = platform.resolve_model(it, prov, reg)
        if refusal:
            fail(8, iid, refusal, "flip the provider or change the model")
        if kind is None:
            fail(8, iid, "no kind and no known model to infer one from",
                 "add \"kind\" to the item or name a model from providers.json")
            continue

        for key in ("characters", "products"):
            if key not in it:
                fail(1 if key == "characters" else 2, iid,
                     f"item says nothing about who/what is in it ({key!r} missing)",
                     f"add \"{key}\": [] for none, or list them")
        chars, prods = it.get("characters") or [], it.get("products") or []
        refs = references(it)

        # rule 1 — a person in the shot arrives as a reference, never a description
        if chars and kind in ("still", "restyle", "edit", "cast"):
            if not (refs["image_refs"] or refs["soul"] or refs["elements"]):
                fail(1, iid, f"characters {chars} with no reference",
                     "attach image_references, a soul_id, or a <<<uuid>>> element in the prompt")
        if chars and kind in ("motion", "talking"):
            if not (refs["start"] or refs["elements"] or refs["frame"]):
                fail(1, iid, f"characters {chars} with no start_image and no element",
                     "animate a verified frame (start_image) or reference the cast element in the prompt")

        # rule 2 — a product arrives as its packshot, never as words
        if prods and kind in ("still", "restyle", "edit"):
            uuid_prods = [p for p in prods if isinstance(p, str) and UUID.match(p)]
            present = set(refs["values"]) | set(refs["elements"])
            if uuid_prods:
                for p in uuid_prods:
                    if p not in present:
                        fail(2, iid, f"product {p} is named but not attached",
                             "put it in medias as image_references or as <<<uuid>>> in the prompt")
            elif not (refs["image_refs"] or refs["elements"]):
                fail(2, iid, f"products {prods} with no reference",
                     "attach the packshot media as image_references or the prop element in the prompt")

        # rule 3 — post effects are the editor's, never the generator's
        if kind in ("still", "restyle", "edit"):
            hits = post_effect_hits(params.get("prompt") or "")
            if hits:
                fail(3, iid, f"prompt asks for post effects: {sorted(set(h.lower() for h in hits))}",
                     "generate the raw plate; keying, captions and overlays happen in the edit")

        # rule 4 — start_image is a media UUID, not a URL. One exemption, and
        # only one: the scene shape names the FIRST FRAME by the id of the
        # frame item this same run makes, because the media id does not exist
        # until that still is uploaded. The item's own `start_frame` is what
        # it must equal, so a URL or a stray string is still refused.
        for v in refs["start"]:
            if isinstance(v, str) and UUID.match(v):
                continue
            if v and v == it.get("start_frame"):
                continue
            fail(4, iid, f"start_image {str(v)[:60]!r} is not a media uuid",
                 "upload the still first and pass its media id")

        # rule 6 — motion: within the model's ceiling, on a frame someone verified
        if kind == "motion":
            dur = params.get("duration")
            cap_s = (model or {}).get("max_seconds")
            if dur is not None and cap_s and float(dur) > cap_s:
                fail(6, iid, f"duration {dur}s over {slug}'s {cap_s}s cap",
                     "split at a sentence break, never at a cutaway")
            for v in refs["start"]:
                if not (isinstance(v, str) and UUID.match(v)):
                    continue
                row = frames.get(v)
                if not row or not row.get("verified"):
                    fail(6, iid, f"unverified frame {v}",
                         f"look at it, then: preflight.py verify --run {run.name} {v} --shot {iid} --by <you>")

        # rule 10 — a clip that will ship carries its motion + director verdicts
        if kind == "motion" and (refs["start"] or (it.get("lines") or [])):
            v = verdicts.get(iid) or {}
            if not v.get("motion") and not v.get("director"):
                warns.append(f"[rule 10] {iid}: no motion/director verdict yet — required before pack")

        # rule 11 — the no-cut line, on every motion/talking prompt, without
        # exception (the course write-up, Damon 09-14, §7: a model that
        # invents a cut mid-sentence is a dead generation, and it is one line)
        if kind in ("motion", "talking"):
            p_lower = (params.get("prompt") or "").lower()
            # either wording of the same line: "Single continuous take, no
            # cuts or scene changes" (the old shape) or "One continuous take,
            # no cuts, …" (the shape the live call used, 2026-09-18 evening)
            if not ("continuous take" in p_lower and "no cut" in p_lower):
                fail(11, iid, "prompt carries no continuous-take line",
                     "add the no-cut line: Single continuous take, no cuts or scene changes")

        # rule 12 — THE CONTRACT GATE (2026-09-18). Every item assembled from
        # the scene shape is checked against what its door actually takes:
        # the required fields, the maker's own limits on how many beats a
        # timeline may carry and how many actions a beat may name, a frame
        # that changes nothing, a to-camera scene with no slice of the voice
        # track. What each door takes lives in model-inputs.json, with the
        # doc it was read from; nothing about it is written here, so a
        # correction to the contract corrects the gate.
        for bad in model_inputs.violations(it, kind):
            fail(12, iid, bad,
                 "fill it from the scene's frames — machine/MODEL-INPUTS.md is the contract")

    # rule 12, the other half — THE BRIEF IS THE PROMPT (Damon, 2026-09-19).
    # A current brief's truth is the fenced json block at the end of it, and
    # the machine reads that and never the prose. So the block is checked
    # against `brief_schema` here, key by key: a missing key, a string where
    # a list belongs, a beat that names two actions or a delivery note, a
    # last frame whose camera move names no framing to land on. A brief with
    # no block at all is an older one, read from its Markdown, and the item
    # rules above are what check it.
    brief_file = run / "brief.md"
    if brief_file.is_file() and _brief_unseen(brief_file):
        for bad in model_inputs.brief_violations(brief_file.read_text()):
            fail(12, "brief", bad,
                 "the json block is the brief — machine/MODEL-INPUTS.md holds "
                 "brief_schema, and the prose above it is only the view")

    # rule 7 — every line claimed once, across the run
    lines = read_json(run / "lines.json")
    if lines is not None:
        keys = list(lines.keys()) if isinstance(lines, dict) else [str(x) for x in lines]
        mine = claims_in(batch, reg)
        others = claims_in(other_batches(run, batch_path.name), reg)
        for line, who in mine.items():
            prior = others.get(line, [])
            if len(who) > 1 or prior:
                fail(7, ",".join(who), f"line {line} claimed more than once ({', '.join(prior + who)})",
                     "one clip per line — drop the duplicate claim")
        claimed = set(mine) | set(others)
        unclaimed = [k for k in keys if k not in claimed]
        if unclaimed:
            warns.append(f"[rule 7] lines still unclaimed after this batch: {', '.join(unclaimed)}")
        stray = [k for k in claimed if k not in keys]
        if stray:
            warns.append(f"[rule 7] claimed lines not in lines.json: {', '.join(sorted(stray))}")

    if not fails:
        dest = run / "batches" / batch_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(batch_path, dest)
    return fails, warns


def coverage(run: Path) -> tuple[list[str], list[str], list[str], list[str]]:
    reg = platform.registry()
    lines = read_json(run / "lines.json")
    if lines is None:
        return [f"no lines.json in {run}"], [], [], []
    keys = list(lines.keys()) if isinstance(lines, dict) else [str(x) for x in lines]
    items = other_batches(run)
    claims = claims_in(items, reg)
    uncovered = [k for k in keys if k not in claims]
    dupes = [f"{k} ({', '.join(v)})" for k, v in claims.items() if len(v) > 1]

    # every clip that will ship (motion/revoice) needs both its motion and
    # director verdicts on file, or it is not a deliverable pack
    verdicts = read_json(run / "verdicts.json", {}) or {}
    not_shippable, concept_weak = [], []
    for it in items:
        if platform.item_kind(it, reg) not in ("motion", "revoice"):
            continue
        iid = str(it.get("id", "?"))
        v = verdicts.get(iid) or {}
        for layer in ("motion", "director"):
            if not v.get(layer):
                not_shippable.append(f"not shippable: no {layer} verdict ({iid})")
        director = v.get("director")
        if isinstance(director, dict) and director.get("verdict") == "FLAG":
            prior_flags = sum(1 for h in (director.get("history") or [])
                               if isinstance(h, dict) and h.get("verdict") == "FLAG")
            if prior_flags >= 1:
                concept_weak.append(f"concept weak — rework the scene in the script ({iid})")

    # every clip that carries a line — talking, revoice, or a motion item
    # that carries `lines` — must be transcribed and checked against what it
    # was supposed to say (Damon, 2026-09-18: a clip lip-synced perfectly to
    # the WRONG words). No parity verdict on file is as undeliverable as a
    # FLAGged one; neither ships quietly.
    for it in items:
        kind = platform.item_kind(it, reg)
        carries_lines = bool(it.get("lines"))
        if kind not in ("talking", "revoice") and not (kind == "motion" and carries_lines):
            continue
        iid = str(it.get("id", "?"))
        parity = (verdicts.get(iid) or {}).get("parity")
        if isinstance(parity, dict) and parity.get("verdict") == "FLAG":
            not_shippable.append(
                f"not shippable: says other words (heard: {parity.get('heard', '')!r}) ({iid})")
        elif not isinstance(parity, dict):
            not_shippable.append(f"not shippable: no parity verdict — run lineparity ({iid})")

    return uncovered, dupes, not_shippable, concept_weak


def verdict(run: Path, item_id: str, layer: str, payload: dict) -> dict:
    """Merge one QC layer's verdict for one item, keeping every prior write in
    that layer's `history` — a check not written down did not happen, and a
    layer overwritten without a trace hides the pattern (two director FLAGs)
    the whole point is to catch."""
    p = run / "verdicts.json"
    data = read_json(p, {}) or {}
    item = data.setdefault(str(item_id), {})
    prior = item.get(layer)
    row = dict(payload)
    row["at"] = now()
    history = list(prior.get("history") or []) if isinstance(prior, dict) else []
    if isinstance(prior, dict):
        history.append({k: v for k, v in prior.items() if k != "history"})
    row["history"] = history
    item[layer] = row
    write_json(p, data)
    return item


def verify(run: Path, uuid: str, shot: str, by: str, note: str | None) -> dict:
    if not UUID.match(uuid):
        raise SystemExit(f"{uuid!r} is not a media uuid")
    p = run / "frames.json"
    frames = read_json(p, {}) or {}
    row = {"shot": shot, "verified": True, "by": by, "at": now()}
    if note:
        row["note"] = note
    frames[uuid] = row
    write_json(p, frames)
    return row


AMBIGUOUS = ("nsfw", "ip_detected")


def ledger(run: Path, model: str, job: str, seconds: float, status: str, tier=None,
           resolution=None, brand=None, shot=None, note=None) -> dict:
    reg = platform.registry()
    m = reg["models"].get(model)
    if not m:
        raise SystemExit(f"model {model!r} is not in providers.json — record the true slug, then add it there")
    run_json = run / "run.json"
    seed = {"machine": "video-machine", "brand": brand or "", "label": run.name, "opened": now()}
    existing = read_json(run_json, {}) or {}
    if not existing:
        write_json(run_json, seed)
    else:
        merged = {**seed, **existing}
        if merged != existing:
            write_json(run_json, merged)
    est = platform.estimate(m, seconds, reg, tier, resolution)
    row = {"model": model, "job": job, "seconds": seconds, "tier": tier or (est["rate"] or {}).get("tier"),
           "resolution": resolution or (est["rate"] or {}).get("resolution"), "status": status,
           "credits": est["credits"], "usd": est["usd"], "at": now()}
    if shot:
        row["shot"] = shot
    if note:
        row["note"] = note
    if status in AMBIGUOUS:
        row["billing"] = "ambiguous"
    p = run / "ledger.json"
    rows = read_json(p, []) or []
    rows.append(row)
    write_json(p, rows)
    return totals(rows)


def totals(rows: list[dict]) -> dict:
    billed = [r for r in rows if r.get("billing") != "ambiguous"]
    amb = [r for r in rows if r.get("billing") == "ambiguous"]
    s = lambda xs, k: round(sum(r.get(k) or 0 for r in xs), 3)
    shots: dict[str, int] = {}
    for r in rows:
        if r.get("shot"):
            shots[r["shot"]] = shots.get(r["shot"], 0) + 1
    return {"billed_credits": s(billed, "credits"), "billed_usd": s(billed, "usd"),
            "ambiguous_credits": s(amb, "credits"), "ambiguous_usd": s(amb, "usd"),
            "unrated": sum(1 for r in rows if r.get("credits") is None and r.get("usd") is None),
            "rerolls": sum(n - 1 for n in shots.values() if n > 1),
            "rerolled_shots": sorted(k for k, n in shots.items() if n > 1),
            "grand_credits": s(rows, "credits"), "grand_usd": s(rows, "usd"), "rows": len(rows)}


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    c = sub.add_parser("check")
    c.add_argument("batch")
    c.add_argument("--run", required=True)
    c.add_argument("--provider")
    c.add_argument("--bank", default=str(DEFAULT_BANK))
    c.add_argument("--library", help="another folder of element lists (tests); "
                                     "default: components/elements/library")

    v = sub.add_parser("coverage")
    v.add_argument("--run", required=True)

    f = sub.add_parser("verify")
    f.add_argument("uuid")
    f.add_argument("--run", required=True)
    f.add_argument("--shot", required=True)
    f.add_argument("--by", required=True)
    f.add_argument("--note")

    l = sub.add_parser("ledger")
    l.add_argument("--run", required=True)
    l.add_argument("--model", required=True)
    l.add_argument("--job", required=True)
    l.add_argument("--seconds", type=float, required=True)
    l.add_argument("--status", required=True, choices=["done", "nsfw", "ip_detected", "failed"])
    l.add_argument("--tier", choices=["std", "fast"])
    l.add_argument("--resolution")
    l.add_argument("--brand")
    l.add_argument("--shot")
    l.add_argument("--note")

    vd = sub.add_parser("verdict")
    vd.add_argument("item")
    vd.add_argument("--run", required=True)
    vd.add_argument("--layer", required=True, choices=["inspector", "motion", "director"])
    src = vd.add_mutually_exclusive_group(required=True)
    src.add_argument("--json", dest="json_str")
    src.add_argument("--file")

    a = ap.parse_args(argv)
    run = Path(a.run).resolve()

    try:
        if a.verb == "check":
            bp = Path(a.batch)
            if not bp.exists():
                print(f"no such batch: {bp}", file=sys.stderr)
                return 3
            fails, warns = check(bp, run, a.provider, Path(a.bank),
                                 Path(a.library) if a.library else None)
            for w in warns:
                print(f"WARNING {w}")
            for x in fails:
                print(x)
            if fails:
                print(f"{len(fails)} failure(s) — nothing to submit")
                return 2
            print(f"green — copied to {run / 'batches' / bp.name}")
            return 0

        if a.verb == "coverage":
            uncovered, dupes, not_shippable, concept_weak = coverage(run)
            for k in uncovered:
                print(f"uncovered: {k}")
            for d in dupes:
                print(f"duplicated: {d}")
            for m in not_shippable:
                print(m)
            for c in concept_weak:
                print(c)
            if uncovered or dupes or not_shippable or concept_weak:
                print(f"{len(uncovered)} uncovered, {len(dupes)} duplicated, "
                      f"{len(not_shippable)} not shippable, {len(concept_weak)} concept-weak — not deliverable")
                return 2
            print("every line claimed exactly once")
            return 0

        if a.verb == "verify":
            row = verify(run, a.uuid, a.shot, a.by, a.note)
            print(f"verified {a.uuid} for {row['shot']} by {row['by']} at {row['at']}")
            return 0

        if a.verb == "ledger":
            t = ledger(run, a.model, a.job, a.seconds, a.status, a.tier, a.resolution,
                       a.brand, a.shot, a.note)
            print(f"billed     {t['billed_credits']} cr  ${t['billed_usd']:.3f}")
            print(f"ambiguous  {t['ambiguous_credits']} cr  ${t['ambiguous_usd']:.3f}  (nsfw / ip_detected)")
            if t["unrated"]:
                print(f"unrated    {t['unrated']} row(s) with no rate on file")
            print(f"re-rolls   {t['rerolls']}" + (f"  ({', '.join(t['rerolled_shots'])})" if t["rerolls"] else ""))
            print(f"grand      {t['grand_credits']} cr  ${t['grand_usd']:.3f}  over {t['rows']} row(s)")
            return 0

        if a.verb == "verdict":
            payload = (json.loads(a.json_str) if a.json_str is not None
                       else json.loads(Path(a.file).read_text()))
            if not isinstance(payload, dict):
                raise SystemExit("verdict payload must be a JSON object")
            item = verdict(run, a.item, a.layer, payload)
            for layer in ("inspector", "motion", "director"):
                row = item.get(layer)
                print(f"{layer}: {json.dumps(row) if row else 'none'}")
            return 0
    except (SystemExit, ValueError, OSError) as e:
        if isinstance(e, SystemExit) and isinstance(e.code, int):
            return e.code
        print(e, file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    sys.exit(main())
