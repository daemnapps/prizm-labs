#!/usr/bin/env python3
"""Rename a brand's language rows to the Naming Standard's row id.

    python3 tools/rename_ids.py --brand B --dry-run    # what would change, nothing written
    python3 tools/rename_ids.py --brand B              # propose the rename, the gatherer applies it
    python3 tools/rename_ids.py --brand B --propose-only   # the proposal under runs/, nothing applied

    language_<brand>_<avatar>_<lane>_<number>

The rule (brands/language-schema.md, "Row ids", as the first brand's rename ran it):
- <avatar> is the avatar FOLDER the row sits in; <lane> the lane word of its
  file (prospect · lead · customer · churned) — or the file's own kind for a
  bank file that is not a lane (candidates, creator-audience); a dated
  deep-research file takes the lane of each row's funnel.
- A row keeps its old number when that number is free in its lane; a clash,
  or an id with no number, takes the next free number. Numbers run across the
  whole avatar bank, sub-avatar folders included.
- Numbers are 4 digits or more and never cut (…_9999 → …_10000).
- A row already on the standard is left alone.
- The lookup old → new is written to runs/language-layer/<brand>/id-rename-<date>.json,
  and every used-lane record under the brand is repointed to the new ids.
  Dated run records are history and keep the ids they were written with.

`brands/` is read-only to machines (decision-log 2026-09-17): the rename and
the used-lane repoints are written as a PROPOSAL under
runs/language-layer/<brand>/rename-<date>/ and handed to the research
gatherer's apply step (`gather.py apply --proposal …`), the one machine ruled
to write the bank.
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402
from language_layer import proposal as P  # noqa: E402
sys.path.append(str(Path(__file__).resolve().parent))
from label import open_run, bank_root, finish  # noqa: E402

LANE_FILE = {"prospects": "prospect", "leads": "lead"}
LANE_DIR = {"customers": "customer", "churned": "churned"}
FUNNEL = {"prospect": "prospect", "lead": "lead", "customer": "customer", "churned": "churned"}


def lane_of(f, lang, row):
    rel = f.relative_to(lang).parts
    if rel[0] in LANE_DIR:
        return LANE_DIR[rel[0]]
    stem = f.stem
    if stem in LANE_FILE:
        return LANE_FILE[stem]
    if stem.startswith("deep-research") or re.match(r"\d{4}-\d{2}-\d{2}", stem):
        return FUNNEL.get(row.get("funnel"), "prospect")
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")


def number_of(old):
    m = re.search(r"-(\d+)$", old or "")
    return int(m.group(1)) if m else None


def fmt(raw):
    m = re.search(r"\n( +)\"", raw)
    return (len(m.group(1)) if m else 1), raw.endswith("\n"), "\\u" in raw


def plan(brand):
    base = E.bank_dir(E.brand_dir(brand))
    files, lookup = {}, {}
    for av_dir in sorted(x for x in base.iterdir() if x.is_dir()):
        avatar = av_dir.name
        rows = []   # (lane, file, index, entry)
        for lang in E._lang_dirs(brand, avatar):
            if not lang.is_dir():
                continue
            for f in sorted(lang.rglob("*.json")):
                if E.USED_DIR in f.relative_to(lang).parts:
                    continue
                raw = f.read_text()
                try:
                    d = json.loads(raw)
                except Exception:
                    continue
                files[f] = (raw, d)
                for i, e in enumerate(d.get("entries") or []):
                    rows.append((lane_of(f, lang, e), f, i, e))
        taken, lk = {}, {}
        for lane, f, i, e in rows:          # numbers already on the standard are taken first
            if (e.get("id") or "").startswith("language_"):
                taken.setdefault(lane, set()).add(number_of(e["id"].replace("_", "-")))
        for lane, f, i, e in rows:          # then old numbers, where free
            old = e.get("id") or ""
            if old.startswith("language_"):
                continue
            n = number_of(old)
            t = taken.setdefault(lane, set())
            if n is not None and n not in t:
                t.add(n); lk[(f, i)] = (old, lane, n)
        for lane, f, i, e in rows:          # then everything else takes the next free number
            old = e.get("id") or ""
            if old.startswith("language_") or (f, i) in lk:
                continue
            t = taken.setdefault(lane, set())
            n = (max(t) if t else 0) + 1
            t.add(n); lk[(f, i)] = (old, lane, n)
        for (f, i), (old, lane, n) in lk.items():
            lookup[(f, i)] = (old, f"language_{brand}_{avatar}_{lane}_{n:04d}")
    return files, lookup


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--dry-run", action="store_true", help="print what would change; write nothing, not even a proposal")
    ap.add_argument("--propose-only", action="store_true", help="write the proposal under runs/ and stop — nothing applied")
    ap.add_argument("--run", default=None)
    a = ap.parse_args(argv)
    files, lookup = plan(a.brand)
    news = [v[1] for v in lookup.values()]
    dup = len(news) - len(set(news))
    olds = {}
    for v in lookup.values():
        olds.setdefault(v[0], []).append(v[1])
    print(f"{len(lookup):,} rows to rename · {dup} clashing new ids · "
          f"{sum(1 for v in olds.values() if len(v) > 1)} old ids that were not unique")
    for (f, i), (old, new) in list(lookup.items())[:6]:
        print(f"  {old} → {new}")
    if dup:
        print("clashing new ids — nothing written")
        return 1
    if a.dry_run or not lookup:
        return 0
    prop = P.Proposal(a.brand, "language-layer tools/rename_ids.py", open_run(a.brand, "rename", a.run))
    for (f, i), (old, new) in lookup.items():
        prop.row(f, i, files[f][1]["entries"][i], id=new)
    flat = {old: new for (old, new) in lookup.values() if old}
    out = E.WORKSPACE / "runs" / "language-layer" / a.brand
    out.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    (out / f"id-rename-{stamp}.json").write_text(json.dumps(dict(
        rule="Naming Standard two-mark rule: language_<brand>_<avatar>_<lane>_<number>; an old number is kept where free in its lane, anything else takes the next; 4+ digits, never cut",
        date=stamp, map=flat), indent=1, ensure_ascii=False) + "\n")
    # the used lane follows the rename
    for lang in E._lang_dirs(a.brand):
        u = lang / E.USED_DIR
        for f in (sorted(u.glob("*.json")) if u.is_dir() else []):
            d = json.loads(f.read_text())
            for k, e in enumerate(d.get("used") or []):
                if e.get("row_id") in flat:
                    prop.used_mark(f, k, e["row_id"], flat[e["row_id"]])
    print(f"proposed: {len(prop.rows):,} rows renamed · {len(prop.used)} used-lane marks repointed · lookup {out}")
    return finish(prop, a, dict(renamed=len(prop.rows), used_marks_repointed=len(prop.used)),
                  [f"`{o}` → `{n}`" for o, n in list(flat.items())[:12]])


if __name__ == "__main__":
    sys.exit(main())
