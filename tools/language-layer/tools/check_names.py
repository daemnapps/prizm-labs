#!/usr/bin/env python3
"""Check a brand's language bank against the Naming Standard — row ids and
source ids — and say exactly what does not fit.

    python3 tools/check_names.py --brand B         # report
    python3 tools/check_names.py --brand B --json  # the same, as data

The rules (lab/damon/naming-standard, v5; brands/language-schema.md):
  a value is lowercase a–z 0–9, words joined by "-"; values joined by "_";
  the type first; the brand spelled in full.
  row id     language_<brand>_<avatar>_<lane>_<number>   number: 4 digits or more, never cut
  source id  <kind>_<values…>                           one shape per kind, below
No model, no network, nothing written.
"""
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402

VALUE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NUMBER = re.compile(r"^\d{4,}$")
# kind -> how many values follow the kind (None = any number ≥ 1)
KINDS = {"survey": 2, "post": 3, "ticket": 2, "review": 2, "community": 2,
         "copy": 2, "database": 2, "interview": 2, "panel": 2, "email": 2}
LANES = {"customer", "lead", "prospect", "churned"}


def check_row_id(rid, brand):
    p = (rid or "").split("_")
    if len(p) != 5 or p[0] != "language":
        return "not five values starting with language_"
    if p[1] != brand:
        return f"brand value is {p[1]!r}, not {brand!r}"
    if not all(VALUE.match(v) for v in p[1:4]):
        return "a value has capitals, spaces or a character other than a–z 0–9 -"
    if not NUMBER.match(p[4]):
        return "the number is not 4+ digits"
    return None


def check_source_id(sid):
    p = (sid or "").split("_")
    if p[0] not in KINDS:
        return f"unknown kind {p[0]!r}"
    if KINDS[p[0]] is not None and len(p) - 1 != KINDS[p[0]]:
        return f"{p[0]} takes {KINDS[p[0]]} values, has {len(p) - 1}"
    if not all(VALUE.match(v) for v in p[1:]):
        return "a value has capitals, spaces or a character other than a–z 0–9 -"
    return None


def run(brand):
    rows = E.load(brand)
    rep = collections.OrderedDict(brand=brand, rows=len(rows))
    bad_ids = [(r.get("id"), check_row_id(r.get("id"), brand)) for r in rows]
    bad_ids = [(i, w) for i, w in bad_ids if w]
    dup = [i for i, n in collections.Counter(r.get("id") for r in rows).items() if n > 1]
    rep["row_ids_off_standard"] = len(bad_ids)
    rep["row_id_examples"] = bad_ids[:5]
    rep["duplicate_row_ids"] = dup[:10]
    # the number width: how close each lane's sequence is to 9999
    seq = collections.Counter()
    for r in rows:
        p = (r.get("id") or "").split("_")
        if len(p) == 5 and p[4].isdigit():
            seq[(p[2], p[3])] = max(seq[(p[2], p[3])], int(p[4]))
    rep["highest_number_per_avatar_lane"] = {f"{a}_{l}": n for (a, l), n in seq.most_common(5)}
    rows_per = collections.Counter((r.get("avatar"), r.get("funnel")) for r in rows)
    rep["rows_per_avatar_lane"] = {f"{a}_{l}": n for (a, l), n in rows_per.most_common(5)}
    srcs = [((r.get("source") or {}).get("id"), (r.get("source") or {}).get("ref")) for r in rows]
    rep["rows_with_source_id"] = sum(1 for s, _ in srcs if s)
    bad_src = collections.Counter(check_source_id(s) for s, _ in srcs if s and check_source_id(s))
    rep["source_ids_off_standard"] = dict(bad_src)
    rep["refs_on_a_laptop_path"] = sum(1 for _, ref in srcs if str(ref or "").startswith("/Users/"))
    rep["distinct_source_names"] = len({(r.get("source") or {}).get("name") for r in rows})
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, action="append")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    reps = [run(b) for b in a.brand]
    if a.json:
        print(json.dumps(reps, indent=1, ensure_ascii=False)); return
    for rep in reps:
        print(f"\n{rep['brand']} — {rep['rows']:,} rows")
        for k, v in rep.items():
            if k not in ("brand", "rows"):
                print(f"  {k.replace('_', ' ')}: {v}")


if __name__ == "__main__":
    main()
