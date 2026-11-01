"""Apply a language-bank proposal — the gatherer's one write path for changes
the language layer's bank tools propose.

    python3 components/research-gatherer/gather.py apply --proposal runs/language-layer/<b>/<run>/proposal.json [--dry-run]

Why here: `brands/` is read-only to machines (decision-log 2026-09-17); the
research gatherer is the one machine ruled to write into the bank, and only
what passed its gates (the owner 2026-09-18, the O5 carve-out). The labeller,
the id renamer and the source mapper (tools/language-layer/tools/)
now write a PROPOSAL under `runs/language-layer/`; this step checks it and
writes it, with the same file writer the gatherer files new rows with
(`annotate._dump` — each file keeps its indent, escaping and newline).

The gates, every one checked before anything is written:
  REFUSED (nothing written at all):
    - not a language-bank proposal, or for another brand
    - a path outside `brands/<brand>/core-avatars/`, or not a bank file:
      rows only in a `language/` folder, used-lane marks only in
      `language/used/`, a whole file only `core-avatars/language-sources.json`
    - a field the bank tools do not own (words, dates, signal … are never
      touched): rows may set only awareness, sophistication, lane_words,
      origin, voice, use, id, source
    - a row id off the Naming Standard, or two rows ending on one id
    - a source change that drops the row's link (its receipt)
    - a registry that is not a registry for this brand
  SKIPPED, row by row, and listed:
    - the row is not there any more, or its words changed since the
      proposal read them (`text_sha`)
    - a label a PERSON wrote (`"by"` other than "model") — never overwritten
Nothing removes a row. Rows are added only through a proposal's `add` list
(2026-10-06, the gatherer's own feed and dig comments — `gather.py
feedcomments` / `digcomments`): each new row lands in a `language/` file of
its avatar, must carry its words and a link, gets its id here (numbered across
the whole avatar bank at the moment of writing), and is SKIPPED when a row with
the same (source.ref, source.id) is already in that avatar's bank. Tags are
added through `add_use` on a row (`gather.py retag --culture`): only the
culture tags (`annotate.CULTURE_TAGS`), unioned into `use` — never a tag
removed.
Writes `applied.json` + `applied.md` beside the proposal (under `runs/`).
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import engine
from .annotate import _dump, CULTURE_TAGS, LANE_FUNNEL, next_ids

KIND = "language-bank-proposal"
ROW_FIELDS = {"awareness", "sophistication", "lane_words", "origin", "voice", "use", "id", "source"}
LABELS = ("awareness", "sophistication")


class Refused(Exception):
    pass


def _sha(text):
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def _link(src):
    ref = str((src or {}).get("ref") or "")
    return ref if ref.startswith("http") else ""


def _check_path(p, brand, what):
    parts = p.split("/")
    if ".." in parts or p.startswith("/") or parts[:3] != ["brands", brand, "core-avatars"] or not p.endswith(".json"):
        raise Refused(f"{what}: {p} is outside brands/{brand}/core-avatars/")
    if what == "row" and ("language" not in parts or "used" in parts[parts.index("language"):]):
        raise Refused(f"row: {p} is not a language bank file")
    if what == "used" and not re.search(r"/language/used/[^/]+\.json$", p):
        raise Refused(f"used: {p} is not a used-lane file")
    if what == "write" and p != f"brands/{brand}/core-avatars/language-sources.json":
        raise Refused(f"write: {p} — the only whole file a proposal may write is the source registry")


def plan(prop, root):
    """Check a proposal against the tree at `root`. Returns (files, applied,
    skipped) — files maps path -> (raw, data) with every change made in
    memory; raises Refused when any structural gate fails."""
    if prop.get("kind") != KIND or prop.get("version") != 1:
        raise Refused("not a version-1 language-bank proposal")
    brand = prop.get("brand") or ""
    if not re.match(r"^[a-z0-9-]+$", brand):
        raise Refused(f"brand {brand!r} is not a brand slug")
    id_re = re.compile(rf"^language_{re.escape(brand)}_[a-z0-9]+(?:-[a-z0-9]+)*_[a-z0-9]+(?:-[a-z0-9]+)*_\d{{4,}}$")
    for r in prop.get("rows", []):
        _check_path(r.get("file", ""), brand, "row")
        extra = set(r.get("set") or {}) - ROW_FIELDS
        if extra:
            raise Refused(f"row {r.get('id')}: sets {sorted(extra)} — not a field the bank tools own")
        bad = [t for t in r.get("add_use") or [] if t not in CULTURE_TAGS]
        if bad or ("add_use" in r and not isinstance(r["add_use"], list)):
            raise Refused(f"row {r.get('id')}: add_use {bad or r.get('add_use')!r} — only {', '.join(CULTURE_TAGS)}")
        new_id = (r.get("set") or {}).get("id")
        if new_id is not None and not id_re.match(new_id):
            raise Refused(f"row {r.get('id')}: new id {new_id!r} is off the Naming Standard")
    for u in prop.get("used", []):
        _check_path(u.get("file", ""), brand, "used")
    for a in prop.get("add", []):
        _check_path(a.get("file", ""), brand, "row")
        e = a.get("entry") or {}
        if not (e.get("text") or "").strip():
            raise Refused(f"add: a new row in {a['file']} has no words")
        if not _link(e.get("source")):
            raise Refused(f"add: a new row in {a['file']} has no link (source.ref)")
        if e.get("funnel") not in set(LANE_FUNNEL.values()):
            raise Refused(f"add: funnel {e.get('funnel')!r} is not a lane")
    for w in prop.get("write", []):
        _check_path(w.get("file", ""), brand, "write")
        c = w.get("content") or {}
        if c.get("brand") != brand or not isinstance(c.get("sources"), list):
            raise Refused(f"write: {w['file']} is not this brand's source registry")

    files, applied, skipped = {}, [], []

    def doc(p):
        if p not in files:
            f = root / p
            try:
                raw = f.read_text()
                files[p] = (raw, json.loads(raw))
            except Exception:
                files[p] = None
        return files[p]

    taken = {}
    for r in prop.get("rows", []):
        d = doc(r["file"])
        if d is None:
            skipped.append(dict(id=r.get("id"), file=r["file"], why="file missing or unreadable")); continue
        entries = d[1].get("entries") or []
        taken.setdefault(r["file"], set())
        i = r.get("index")
        if not (isinstance(i, int) and 0 <= i < len(entries) and entries[i].get("id") == r.get("id")
                and i not in taken[r["file"]]):
            i = next((k for k, e in enumerate(entries) if e.get("id") == r.get("id") and k not in taken[r["file"]]), None)
        if i is None:
            skipped.append(dict(id=r.get("id"), file=r["file"], why="row not found")); continue
        e = entries[i]
        if r.get("text_sha") and _sha(e.get("text")) != r["text_sha"]:
            skipped.append(dict(id=r.get("id"), file=r["file"], why="words changed since the proposal read them")); continue
        sets = dict(r.get("set") or {})
        if r.get("add_use"):
            cur = e.get("use")
            cur = [cur] if isinstance(cur, str) else list(cur or [])
            new = [t for t in r["add_use"] if t not in cur]
            if not new and not sets:
                skipped.append(dict(id=r.get("id"), file=r["file"], why="tags already there")); continue
            if new:
                sets["use"] = cur + new
        person = [k for k in LABELS if k in sets and isinstance(e.get(k), dict) and e[k].get("by") not in (None, "model")]
        if person:
            skipped.append(dict(id=r.get("id"), file=r["file"], why=f"{', '.join(person)} labelled by a person")); continue
        if "source" in sets:
            if not isinstance(sets["source"], dict):
                raise Refused(f"row {r.get('id')}: source is not an object")
            if _link(e.get("source")) and not _link(sets["source"]):
                raise Refused(f"row {r.get('id')}: the new source drops the row's link")
        taken[r["file"]].add(i)
        e.update(sets)
        applied.append(dict(id=r.get("id"), file=r["file"], fields=sorted(sets)))

    # no two rows may end on one id, anywhere in the avatar bank the proposal touched
    new_ids = {(r.get("set") or {}).get("id") for r in prop.get("rows", [])} - {None}
    clash = []
    if new_ids:
        avatars = {"/".join(r["file"].split("/")[:4]) for r in prop.get("rows", []) if (r.get("set") or {}).get("id")}
        ids = {}
        for av in sorted(avatars):
            for f in sorted((root / av).rglob("*.json")):
                p = f.relative_to(root).as_posix()
                if "/language/" not in p or "/language/used/" in p:
                    continue
                d = doc(p)
                for e in (d[1].get("entries") or []) if d else []:
                    if e.get("id"):
                        ids[e["id"]] = ids.get(e["id"], 0) + 1
        clash = [k for k in new_ids if ids.get(k, 0) > 1]
    if clash:
        raise Refused(f"{len(clash)} ids would be carried by two rows, e.g. {clash[0]}")

    for u in prop.get("used", []):
        d = doc(u["file"])
        if d is None:
            skipped.append(dict(id=u.get("row_id"), file=u["file"], why="used-lane file missing")); continue
        marks = d[1].get("used") or []
        i = u.get("index")
        if not (isinstance(i, int) and 0 <= i < len(marks) and marks[i].get("row_id") == u.get("row_id")):
            skipped.append(dict(id=u.get("row_id"), file=u["file"], why="used-lane mark not found")); continue
        marks[i]["row_id"] = u["new_row_id"]
        applied.append(dict(id=u["row_id"], file=u["file"], fields=["row_id"]))

    # new rows: deduped on (source.ref, source.id) against the avatar's whole
    # bank, numbered across it now — so two proposals never race for a number
    banks = {}

    def avatar_bank(av):
        if av not in banks:
            keys, ids = set(), []
            for f in sorted((root / av).rglob("*.json")):
                p = f.relative_to(root).as_posix()
                if "/language/" not in p or "/language/used/" in p:
                    continue
                d = doc(p)
                for e in (d[1].get("entries") or []) if d else []:
                    s_ = e.get("source") or {}
                    if s_.get("ref"):
                        keys.add((s_.get("ref"), s_.get("id")))
                    if e.get("id"):
                        ids.append({"id": e["id"]})
            banks[av] = (keys, ids)
        return banks[av]

    for a in prop.get("add", []):
        d = doc(a["file"])
        if d is None:
            skipped.append(dict(id=None, file=a["file"], why="bank file missing")); continue
        e = dict(a["entry"])
        e.pop("id", None)
        parts = a["file"].split("/")
        keys, ids = avatar_bank("/".join(parts[:4]))
        k = ((e.get("source") or {}).get("ref"), (e.get("source") or {}).get("id"))
        if k in keys:
            skipped.append(dict(id=None, file=a["file"], why="already in the bank (same ref + comment id)")); continue
        prefix = f"language_{brand}_{parts[3]}_{e['funnel']}_"
        new_id = (next_ids([x for x in ids if x["id"].startswith(prefix)], 1) or [f"{prefix}0001"])[0]
        if not id_re.match(new_id):
            raise Refused(f"add: id {new_id!r} would be off the Naming Standard")
        keys.add(k)
        ids.append({"id": new_id})
        d[1].setdefault("entries", []).append({"id": new_id, **e})
        applied.append(dict(id=new_id, file=a["file"], fields=["new row"]))

    for w in prop.get("write", []):
        f = root / w["file"]
        raw = f.read_text() if f.is_file() else "{\n \"x\": 1\n}\n"
        files[w["file"]] = (raw, w["content"])
        applied.append(dict(id=None, file=w["file"], fields=["whole file"]))
    return files, applied, skipped


def apply(proposal_path, root=None, dry_run=False):
    """Check, then write. Returns a report dict; raises Refused (nothing written)."""
    proposal_path = Path(proposal_path)
    prop = json.loads(proposal_path.read_text())
    root = Path(root) if root else engine.WORKSPACE
    files, applied, skipped = plan(prop, root)
    touched = sorted({a["file"] for a in applied})
    if not dry_run:
        for p in touched:
            raw, d = files[p]
            (root / p).write_text(_dump(d, raw))
    rep = dict(proposal=str(proposal_path.name), brand=prop["brand"], tool=prop.get("tool"),
               applied_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), dry_run=dry_run,
               applied=len(applied), skipped=len(skipped), files=len(touched),
               skipped_rows=skipped[:500])
    if not dry_run:
        out = proposal_path.parent
        (out / "applied.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n")
        why = {}
        for s in skipped:
            why[s["why"]] = why.get(s["why"], 0) + 1
        (out / "applied.md").write_text("\n".join(
            [f"# Applied — {prop.get('tool')} — {prop['brand']} — {rep['applied_at']}", "",
             f"Written by the research gatherer's apply step (`gather.py apply`).", "",
             f"- changes applied: {len(applied):,}", f"- files written: {len(touched)}",
             f"- skipped: {len(skipped):,}"] + [f"  - {k}: {v}" for k, v in why.items()]
            + ["", "## Files", ""] + [f"- `{p}`" for p in touched] + [""]))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gather.py apply")
    ap.add_argument("--proposal", required=True)
    ap.add_argument("--root", default=None, help="the tree that holds brands/ (default: the workspace)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        rep = apply(a.proposal, a.root, a.dry_run)
    except Refused as e:
        print(f"REFUSED — nothing written: {e}")
        return 2
    print(f"{'would apply' if a.dry_run else 'applied'} {rep['applied']:,} changes in {rep['files']} files · "
          f"skipped {rep['skipped']:,}")
    for s in rep["skipped_rows"][:10]:
        print(f"  skipped {s['id']}: {s['why']}")
    return 0
