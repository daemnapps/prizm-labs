#!/usr/bin/env python3
"""
playbook_builder.py — every swipe that comes in either JOINS a playbook family that
already works, or drafts a new one. Nobody has to sit and write workflows.

the owner, 2026-10-10: "I'm not going to have time to identify and create every
individual workflow … I need a system that can build out the specific workflows
based off of the videos that come into the system" — and the same day: "every time
there's a new format … we first need to identify whether or not it's similar
enough to another type of format that's already worked … so we're not doing double
work and creating a bunch of new formats all the time."

MATCH FIRST. From a teardown run (stages/0-triage.md, 1-teardown.md, 1c-doctrine.md,
framemap/framemap.json) it reads the swipe's STRUCTURAL SIGNATURE — audio driver,
speakers on screen and who they address, settings, the product's role, pacing,
capture, story shape — and scores it against every family playbook and every
variant already recorded under one (`score()`):

  * the format already resolves to a playbook      → nothing to build; logged
  * score ≥ MATCH (and audio + capture agree)      → recorded as a VARIANT of the
                                                     nearest family: a small entry
                                                     holding only the differences;
                                                     the run uses the parent + the
                                                     variant's overrides
  * nothing close                                  → a NEW FAMILY drafted (status
                                                     draft) from the swipe + the
                                                     nearest playbook — by the
                                                     builder prompt
                                                     (prompts/stage-0p-playbook/)
                                                     through run-kit's one claude
                                                     caller, or, when that caller
                                                     is unavailable, a skeleton
                                                     from the nearest

Every decision is logged under runs/playbook-learn/<format_id>/<run-label>/MATCH.md
(+ MATCH.json) and appended to runs/playbook-learn/decisions.jsonl.

    python3 machine/playbook_builder.py <teardown-run> [--format <id>] [--skeleton] [--dry-run]

`ensure(run_dir, ...)` is the public entry the teardown runner calls right after
triage records format_id. It never raises — a failure is logged and the teardown
goes on. No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent / "prompts" / "stage-0p-playbook"
MATCH = 0.75          # at or above: a variant of the nearest family, never a new playbook
WEIGHTS = {"audio": 0.22, "address": 0.15, "speakers": 0.13, "settings": 0.08,
           "product_role": 0.10, "pacing": 0.07, "capture": 0.10, "story": 0.15}
HARD = ("audio", "capture_group")   # a song is never a variant of a talking ad; animated never of live action
ANIMATED_FAMILIES = ("handmade", "drawn", "3d")
PACING = ("slow", "medium", "fast")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PB = _load("playbook")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo() -> Path:
    sys.path.insert(0, str(HERE.parents[1].parent / "components" / "run-kit"))
    from run_kit.paths import repo as _repo
    return _repo(HERE)


def _text(p: Path) -> str:
    try:
        return p.read_text()
    except OSError:
        return ""


# ── reading the swipe ─────────────────────────────────────────────────────────

FORMAT_LINE = re.compile(r"^\s*\**FORMAT\**\s*:\s*\**\s*`?([a-z0-9][a-z0-9:_-]*)`?", re.I | re.M)
STYLE_LINE = re.compile(r"^\s*\**STYLE\**\s*:\s*\**\s*`?([a-z0-9][a-z0-9:_-]*)`?", re.I | re.M)
SOUND_LINE = re.compile(r"^\s*\**SOUND FORM\**\s*:\s*\**\s*([A-Z /&-]+)", re.I | re.M)


def _style_families() -> Dict[str, str]:
    try:
        d = json.loads((HERE.parent / "styles" / "bank.json").read_text())
        return {r["id"]: r.get("family") or "" for r in d.get("styles") or []}
    except (OSError, ValueError, KeyError):
        return {}


def _bank_ids() -> List[str]:
    try:
        d = json.loads((HERE.parent / "formats" / "bank.json").read_text())
        return [r["id"] for r in d.get("formats") or []]
    except (OSError, ValueError, KeyError):
        return []


def read_swipe(run: Path) -> dict:
    """Everything the matcher and the builder need from a teardown run."""
    run = Path(run)
    st = run / "stages"
    triage, teardown, doctrine = _text(st / "0-triage.md"), _text(st / "1-teardown.md"), _text(st / "1c-doctrine.md")
    fm = {}
    try:
        fm = json.loads((run / "framemap" / "framemap.json").read_text())
    except (OSError, ValueError):
        pass
    rj = {}
    try:
        rj = json.loads((run / "run.json").read_text())
    except (OSError, ValueError):
        pass
    tr = []
    try:
        tr = json.loads((run / "transcript.json").read_text())
        tr = tr if isinstance(tr, list) else (tr.get("segments") or [])
    except (OSError, ValueError, AttributeError):
        tr = []
    fmt = rj.get("format_id")
    if not fmt:
        m = FORMAT_LINE.search(triage)
        fmt = m.group(1) if m else None
    if not fmt:   # older runs: the doctrine read names the format when a row fits
        m = FORMAT_LINE.search(doctrine)
        if m and (m.group(1).lower() in _bank_ids() or PB.has_playbook(m.group(1))):
            fmt = m.group(1)
    style = rj.get("style_id")
    if not style:
        m = STYLE_LINE.search(triage)
        style = m.group(1) if m else None
    fline = ""
    m = re.search(r"^\s*\**FORMAT\**\s*:\s*\**(.+)$", doctrine, re.M)
    if m:
        fline = m.group(1).strip()
    return {"run": str(run), "label": run.name, "format_id": (fmt or "").lower() or None,
            "style_id": (style or "").lower() or None, "triage": triage, "teardown": teardown,
            "doctrine": doctrine, "doctrine_format": fline, "framemap": fm, "transcript": tr}


def _section(text: str, head: str) -> str:
    m = re.search(r"^\s*\*\*" + head + r"\*\*\s*$(.*?)(?=^\s*\*\*(?:CAST|PLACES|PROPS|THE [A-Z ]+)\*\*\s*$|^#|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def _people_blocks(teardown: str) -> Dict[str, str]:
    cast = _section(teardown, "CAST")
    out, name = {}, None
    for line in cast.splitlines():
        m = re.match(r"^\s*\*\*([^*]{1,60})\*\*\s*$", line)
        if m:
            name = m.group(1).strip()
            out[name] = ""
        elif name:
            out[name] += line + "\n"
    return out


DEMO = re.compile(r"\b(appl(y|ies|ying)|rubs?|rubbing|scrub(s|bing)?|massag\w*|pumps?|spray\w*|spread\w*|dabs?|wipes?|smooth(s|ing)? (it|on))\b", re.I)
HOLD = re.compile(r"\b(hold(s|ing)?|shows? (the )?(bottle|jar|tube|product|box)|presents?)\b", re.I)
INSERT = re.compile(r"\b(packshot|product shot|end ?card|product card)\b", re.I)
SONG = re.compile(r"\b(sung|sings?|singing|lyric\w*|song)\b", re.I)
INTERVIEW = re.compile(r"\b(press conference|press-conference|reporters?|interview\w*|podium|q&a)\b", re.I)
STORY = re.compile(r"\b(story|drama|confront\w*|twist|revenge|cheat\w*|betray\w*|plot|short film|short movie)\b", re.I)
PITCH = re.compile(r"\b(demo\w*|host|explain\w*|expert\w*|doctor\w*|surgeon\w*|review\w*|tutorial|routine|consult\w*|shopping)\b", re.I)


def signature(sw: dict) -> dict:
    """The swipe's structural signature, read from its records (no model call)."""
    tri, td, fm = sw["triage"], sw["teardown"], sw["framemap"] or {}
    m = SOUND_LINE.search(tri)
    sound = (m.group(1).strip().upper() if m else "")
    people = _people_blocks(td)
    speakers = [n for n, b in people.items() if re.search(r"speaking\s*\[", b)]
    if "SUNG" in sound or "SING" in sound or (sw.get("format_id") == "song-ad"):
        audio = "song"
    elif "SPOKEN" in sound or "VOICE" in sound or speakers:
        audio = "voice"
    elif "MUSIC" in sound:
        audio = "none"
    else:
        audio = "song" if SONG.search(tri) else "voice"
    on_screen = len(fm.get("people") or people or [])
    # the transcript's own speaker turns: a voice counts once it says three real words
    said = {}
    for seg in sw.get("transcript") or []:
        if isinstance(seg, dict) and seg.get("speaker"):
            words = [w for w in re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", str(seg.get("text") or "")).split() if w.strip()]
            said[seg["speaker"]] = said.get(seg["speaker"], 0) + len(words)
    heard = len([k for k, n in said.items() if n >= 3])
    if audio == "voice" and sw.get("transcript") and sum(said.values()) < 6:
        audio, speakers = "none", []   # a sigh and a "hmm" are sound, not a voice track
    n_speak = max(len(speakers), heard)
    if not n_speak and audio == "voice":
        n_speak = 1

    # who addresses whom: the frame map's faces while a speaker is on screen
    cam = other = 0
    names = [str(x).lower() for x in (fm.get("people") or list(people))]
    spk = [s.lower() for s in speakers] or names
    for shot in fm.get("shots") or []:
        for mo in ((shot.get("map") or {}).get("moments") or []):
            who = str(mo.get("who") or "").lower()
            if spk and not any(s in who or who in s for s in spk):
                continue
            face = str(mo.get("face") or "").lower()
            if "camera" in face or "lens" in face:
                cam += 1
            elif any(n and n != who and n in face for n in names) or "each other" in face \
                    or re.search(r"\bat (the )?(host|doctor|reporter|interviewer|her|him|them)\b", face):
                other += 1
    if audio != "voice" and not speakers:
        address = "none" if not (cam or other) else ("to-camera" if cam >= other else "to-each-other")
    elif cam + other == 0:
        address = "to-each-other" if INTERVIEW.search(tri + sw["doctrine_format"]) else "to-camera"
    else:
        r = cam / float(cam + other)
        address = "to-camera" if r >= 0.66 else "to-each-other" if r <= 0.33 else "mixed"

    places = _section(td, "PLACES")
    settings = len(re.findall(r"^\s*\*\*[^*]{1,60}\*\*\s*$", places, re.M)) or 1

    does = " ".join(str(mo.get("does") or "") for s in fm.get("shots") or []
                    for mo in ((s.get("map") or {}).get("moments") or []))
    nd, nh = len(DEMO.findall(does)), len(HOLD.findall(does))
    product = "demo" if nd >= 2 else "held" if nh >= 2 else "insert" if INSERT.search(td + does) else "none"

    secs = float(fm.get("seconds") or 0) or None
    cuts = len(fm.get("cuts") or [])
    if secs:
        cpm = cuts / (secs / 60.0)
        pacing = "fast" if cpm >= 20 else "medium" if cpm >= 6 else "slow"
    else:
        pacing = "medium"

    fam = _style_families().get(sw.get("style_id") or "", "")
    if fam in ANIMATED_FAMILIES or re.search(r"\b(3d animated|animated|cartoon|claymation|doll)\b",
                                            sw["doctrine_format"] + tri, re.I):
        capture = "animated"
    elif re.search(r"broadcast|press conference|press-conference|tv shop|shopping channel|studio set|news", td[:4000] + tri, re.I):
        capture = "broadcast"
    else:
        held = [str(((s.get("map") or {}).get("camera") or {}).get("held") or "") for s in fm.get("shots") or []]
        capture = "phone-ugc" if sum("hand" in h for h in held) >= max(1, len(held) // 2) else "studio"

    blob = tri + "\n" + sw["doctrine_format"]
    if audio == "song" or (STORY.search(blob) and not PITCH.search(blob)):
        story = "narrative"
    elif INTERVIEW.search(blob):
        story = "interview"
    elif PITCH.search(blob):
        story = "pitch"
    else:
        story = "narrative" if STORY.search(td[:3000]) else "pitch"
    return {"audio": audio, "speakers": n_speak, "on_screen": on_screen, "address": address,
            "settings": settings, "product_role": product, "pacing": pacing, "capture": capture,
            "story": story}


# ── the matcher ───────────────────────────────────────────────────────────────

def capture_group(c: Optional[str]) -> str:
    return "animated" if c == "animated" else "live"


def _num(a, b, cap) -> float:
    try:
        return 1.0 - min(abs(int(a) - int(b)), cap) / float(cap)
    except (TypeError, ValueError):
        return 0.5


def score(a: dict, b: dict) -> Tuple[float, List[str]]:
    """How alike two signatures are, 0–1, and the hard reasons they can never be one
    family (empty when none). Missing dimensions score half."""
    parts = {}
    parts["audio"] = 1.0 if a.get("audio") == b.get("audio") else 0.0
    aa, ba = a.get("address"), b.get("address")
    parts["address"] = 1.0 if aa == ba else 0.5 if "mixed" in (aa, ba) and "none" not in (aa, ba) else 0.0
    parts["speakers"] = _num(a.get("speakers"), b.get("speakers"), 3)
    parts["settings"] = _num(a.get("settings"), b.get("settings"), 4)
    pa, pb = a.get("product_role"), b.get("product_role")
    parts["product_role"] = 1.0 if pa == pb else 0.4 if "none" not in (pa, pb) else 0.0
    try:
        parts["pacing"] = 1.0 - abs(PACING.index(a.get("pacing")) - PACING.index(b.get("pacing"))) / 2.0
    except ValueError:
        parts["pacing"] = 0.5
    ca, cb = a.get("capture"), b.get("capture")
    parts["capture"] = 1.0 if ca == cb else 0.5 if capture_group(ca) == capture_group(cb) else 0.0
    parts["story"] = 1.0 if a.get("story") == b.get("story") else 0.0
    s = round(sum(WEIGHTS[k] * v for k, v in parts.items()), 3)
    hard = []
    if a.get("audio") != b.get("audio"):
        hard.append(f"audio {a.get('audio')} ≠ {b.get('audio')}")
    if capture_group(ca) != capture_group(cb):
        hard.append(f"capture {capture_group(ca)} ≠ {capture_group(cb)}")
    return s, hard


def nearest(sig: dict, fams: Optional[List[dict]] = None) -> List[dict]:
    """Every family scored against the swipe (best of the family and its variants),
    best first: [{family, via, score, hard}]."""
    out = []
    for fam in (PB.families() if fams is None else fams):
        best = None
        cands = [("family", fam.get("signature") or {})] + \
                [(f"variant:{v.get('id')}", v.get("signature")) for v in fam.get("variants") or [] if v.get("signature")]
        for via, s2 in cands:
            sc, hard = score(sig, s2)
            if best is None or (not hard, sc) > (not best["hard"], best["score"]):
                best = {"family": fam.get("format_id"), "via": via, "score": sc, "hard": hard}
        out.append(best)
    out.sort(key=lambda r: (not r["hard"], r["score"]), reverse=True)
    return out


def decide(sig: dict, fams: Optional[List[dict]] = None, threshold: float = MATCH) -> dict:
    ranked = nearest(sig, fams)
    top = ranked[0] if ranked else None
    if top and not top["hard"] and top["score"] >= threshold:
        return {"decision": "variant", "family": top["family"], "score": top["score"], "via": top["via"],
                "ranked": ranked, "why": f"matched {top['family']} ({top['via']}) at {top['score']} ≥ {threshold}"}
    if not top:
        why = "no family playbooks exist yet"
    elif top["hard"]:
        why = f"nearest {top['family']} at {top['score']} but " + "; ".join(top["hard"])
    else:
        why = f"nearest {top['family']} at {top['score']} < {threshold}"
    return {"decision": "new-family", "family": None, "nearest": top["family"] if top else None,
            "score": top["score"] if top else None, "ranked": ranked, "why": "new family because " + why}


# ── writing ───────────────────────────────────────────────────────────────────

def differences(sig: dict, parent_sig: dict) -> dict:
    return {k: sig.get(k) for k in PB.SIGNATURE_KEYS if sig.get(k) != parent_sig.get(k)}


def add_variant(family_id: str, variant_id: str, sig: dict, sw: dict, sc: float, folder: Optional[Path] = None) -> dict:
    """Record the swipe as a variant of a family — differences only; status draft."""
    folder = Path(folder or PB.root())
    fam = json.loads((folder / f"{family_id}.json").read_text())
    vs = fam.setdefault("variants", [])
    for v in vs:
        if PB.normalise_id(v.get("id")) == variant_id:
            if sw["run"] not in (v.get("from_runs") or []):
                v.setdefault("from_runs", []).append(_rel(sw["run"]))
            PB.write(fam, folder)
            return v
    v = {"id": variant_id, "name": variant_id.replace("-", " "), "status": "draft",
         "state": "matched-by-builder", "signature": sig,
         "differences": differences(sig, fam.get("signature") or {}), "overrides": {},
         "from_runs": [_rel(sw["run"])], "match_score": sc, "added": now()[:10],
         "what": (sw.get("doctrine_format") or "")[:240] or None}
    vs.append(v)
    PB.write(fam, folder)
    return v


def _rel(p) -> str:
    try:
        return str(Path(p).resolve().relative_to(repo()))
    except (ValueError, FileNotFoundError):
        s = str(p)
        return s[s.index("/runs/") + 1:] if "/runs/" in s else s   # never a machine path in a record


def skeleton(fid: str, sw: dict, sig: dict, near: Optional[dict], why: str) -> dict:
    """A draft family from the nearest playbook (or the default) and the swipe — what
    the builder writes when no model writer is available."""
    base = copy.deepcopy(near) if near else PB.default_playbook()
    stages = copy.deepcopy(base.get("stages") or {})
    stages.setdefault("audio", {})["first"] = sig["audio"]
    spec = [{"what": f"audio first: {sig['audio']}", "why": "read from the swipe's sound form"}]
    if sig["capture"] == "animated" and sw.get("style_id"):
        stages.setdefault("pictures", {})["style_lock"] = sw["style_id"]
        spec.append({"what": f"every picture in {sw['style_id']}", "why": "the swipe is animated; its style row locks every element"})
    if sig["address"] == "to-each-other":
        spec.append({"what": "speakers address each other, not the lens", "why": "the frame map's faces look at one another"})
    if sig["pacing"] == "slow":
        spec.append({"what": "long held takes, few cuts", "why": "the swipe cuts under 6 times a minute"})
    return {
        "format_id": fid, "name": fid.replace("-", " ").capitalize(), "status": "draft",
        "state": "skeleton-from-nearest", "signed": None, "family": fid,
        "nearest": near.get("format_id") if near else "default",
        "what": sw.get("doctrine_format") or None, "signature": sig,
        "specialised": spec, "stage_order": base.get("stage_order") or [], "stages": stages,
        "failures": [], "cost": {"target_usd_per_ad": (base.get("cost") or {}).get("target_usd_per_ad")},
        "quality_bar": list(base.get("quality_bar") or []), "variants": [],
        "built_from": [_rel(sw["run"])], "rulings": [], "drafted": now()[:10], "why_new": why}


def _json_block(text: str) -> Optional[dict]:
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = m.group(1) if m else (text[text.find("{"): text.rfind("}") + 1] if "{" in text else "")
    try:
        return json.loads(raw)
    except ValueError:
        return None


def prompt_fields(fid: str, sw: dict, sig: dict, near: Optional[dict]) -> dict:
    fm = sw.get("framemap") or {}
    shots = [{"id": s.get("id"), "seconds": s.get("seconds"), "who": (s.get("map") or {}).get("who"),
              "camera": (s.get("map") or {}).get("camera")} for s in (fm.get("shots") or [])[:40]]
    return {"format_id": fid, "triage": sw["triage"][:4000], "teardown": sw["teardown"][:24000],
            "doctrine_format": sw.get("doctrine_format") or "(none)",
            "framemap": json.dumps({"seconds": fm.get("seconds"), "cuts": len(fm.get("cuts") or []),
                                    "people": fm.get("people"), "shots": shots}, ensure_ascii=False)[:12000],
            "signature": json.dumps(sig), "style_id": sw.get("style_id") or "(none)",
            "nearest_playbook": json.dumps({k: v for k, v in (near or PB.default_playbook()).items() if k != "variants"},
                                           indent=1, ensure_ascii=False)[:20000]}


def model_draft(fid: str, sw: dict, sig: dict, near: Optional[dict], call: Optional[Callable] = None) -> Optional[dict]:
    """The builder prompt through run-kit's one claude caller. None when unavailable."""
    sys.path.insert(0, str(HERE.parents[1].parent / "components" / "run-kit"))
    from run_kit import prompts as P
    tpl = Path(P.latest(PROMPTS, "playbook-builder")).read_text()
    sent = P.fill(tpl, prompt_fields(fid, sw, sig, near))
    if call is None:
        from run_kit import model as M
        mdl, _ = M.pick("designs", len(sent))
        call = lambda p: M.call(p, mdl, label=f"playbook-{fid}", tries=2)
    d = _json_block(call(sent) or "")
    if not d:
        return None
    d["format_id"], d["status"], d["family"] = fid, "draft", d.get("family") or fid
    d["signed"] = None
    d.setdefault("variants", [])
    d.setdefault("built_from", [_rel(sw["run"])])
    # the machine's reading of the hard lines (audio driver, capture) always stands
    d["signature"] = {**sig, **{k: v for k, v in (d.get("signature") or {}).items()
                                if v is not None and k in PB.SIGNATURE_KEYS and k not in ("audio", "capture")}}
    au = d.setdefault("stages", {}).setdefault("audio", {})
    if au.get("first") not in PB.AUDIO:   # e.g. "music bed": keep the words, file the driver
        if au.get("first"):
            au["bed"] = au["first"]
        au["first"] = sig["audio"]
    d["state"] = "drafted-by-builder"
    return d


def log(fid: str, label: str, rec: dict, out_root: Optional[Path] = None) -> Path:
    base = Path(out_root or (repo() / "runs" / "playbook-learn"))
    d = base / (fid or "_unnamed") / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "MATCH.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    L = [f"# Playbook match · {label}", "", f"**Decision:** {rec['decision']} — {rec['why']}", "",
         f"Format: `{fid}` · when: {rec['at']}", "", "## The swipe's signature", "", "| | |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in rec["signature"].items()]
    L += ["", "## Every family, scored", "", "| family | via | score | can never be one because |", "|---|---|---|---|"]
    L += [f"| {r['family']} | {r['via']} | {r['score']} | {'; '.join(r['hard']) or '—'} |" for r in rec.get("ranked") or []]
    (d / "MATCH.md").write_text("\n".join(L) + "\n")
    with (base / "decisions.jsonl").open("a") as f:
        f.write(json.dumps({k: v for k, v in rec.items() if k != "ranked"}, ensure_ascii=False) + "\n")
    return d


def build(run: Path, format_id: Optional[str] = None, use_model: bool = True, call: Optional[Callable] = None,
          folder: Optional[Path] = None, out_root: Optional[Path] = None, dry_run: bool = False,
          threshold: float = MATCH) -> dict:
    """Match first, then join or draft. Returns the logged decision record."""
    if not (Path(run) / "stages" / "0-triage.md").exists():
        raise FileNotFoundError(f"no teardown triage at {run}")
    sw = read_swipe(Path(run))
    fid = PB.normalise_id(format_id or sw["format_id"])
    sig = signature(sw)
    rec = {"at": now(), "run": _rel(sw["run"]), "format_id": fid, "style_id": sw.get("style_id"), "signature": sig}
    if fid and PB.has_playbook(fid):
        pb = PB.playbook_for(fid)
        rec.update(decision="exists", family=pb.get("format_id"), why=f"{fid} already resolves to {pb.get('format_id')} ({pb['_source']})",
                   ranked=nearest(sig))
    else:
        dec = decide(sig, threshold=threshold)
        rec.update(dec)
        if not dry_run:
            if dec["decision"] == "variant":
                vid = fid or PB.normalise_id(sw["label"])
                v = add_variant(dec["family"], vid, sig, sw, dec["score"], folder)
                rec["variant"] = v["id"]
            else:
                fid = fid or PB.normalise_id("new-" + sw["label"])
                rec["format_id"] = fid
                near = None
                if dec.get("nearest"):
                    near = json.loads((Path(folder or PB.root()) / f"{dec['nearest']}.json").read_text())
                draft = None
                if use_model:
                    try:
                        draft = model_draft(fid, sw, sig, near, call)
                    except Exception as e:  # the caller missing or capped never blocks a teardown
                        rec["model_error"] = str(e)[:300]
                if draft:
                    draft.setdefault("nearest", near.get("format_id") if near else "default")
                    draft["why_new"] = dec["why"]
                    probs = PB.validate(draft)
                    if probs:
                        rec["model_rejected"] = probs
                        draft = None
                if not draft:
                    draft = skeleton(fid, sw, sig, near, dec["why"])
                PB.write(draft, folder)
                rec["drafted"] = draft["state"]
    if not dry_run:
        rec["logged"] = str(log(rec.get("format_id") or fid, sw["label"], rec, out_root))
    return rec


def ensure(run_dir, format_id: Optional[str] = None, use_model: bool = True) -> Optional[dict]:
    """The teardown runner's hook: never raises."""
    try:
        return build(Path(run_dir), format_id=format_id, use_model=use_model)
    except Exception as e:
        print(f"      playbook builder skipped: {str(e)[:200]}", file=sys.stderr)
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--format", dest="format_id")
    ap.add_argument("--skeleton", action="store_true", help="no model call — draft from the nearest")
    ap.add_argument("--dry-run", action="store_true", help="score and print; write nothing")
    a = ap.parse_args(argv)
    rec = build(Path(a.run), a.format_id, use_model=not a.skeleton, dry_run=a.dry_run)
    print(f"{rec['decision']}: {rec['why']}")
    for r in rec.get("ranked") or []:
        print(f"  {r['family']:<24} {r['via']:<34} {r['score']}  {'; '.join(r['hard'])}")
    if rec.get("logged"):
        print("logged:", rec["logged"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
