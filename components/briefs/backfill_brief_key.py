#!/usr/bin/env python3
"""Stamp `brief_key` into every run record the briefs index can place.

    python3 components/briefs/backfill_brief_key.py            what it would stamp, per station (writes nothing)
    python3 components/briefs/backfill_brief_key.py --apply    stamp it, then rebuild runs/BRIEFS-INDEX.json + BRIEFS.md

the owner, 2026-10-28 (WHERE-EVERYTHING-GOES-owner.md, item 2): run folders keep their labels (links and other sessions lean
on them); each station's run.json carries the brief key instead. The key is the catalog form
(`brand_<catalog product id>_brief-NNNN`, names.catalog_key). A run is placed by briefs_index.place_runs, which never
guesses: a label the register gives to two briefs, or a number the register gives to another run, stays unstamped.

The edit is ONE line of text added after the record's opening brace — the file is never re-dumped, so its order,
spacing and every other field stay byte for byte. A record that already carries a non-empty `brief_key` is left alone.
Nothing is deleted or renamed. Python 3.9.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import briefs_index as BI  # noqa: E402


def stamp_text(text, key):
    """The record's text with `"brief_key": key` as its first field, or None when it cannot be done safely (not a JSON
    object, or it already says a brief key)."""
    try:
        d = json.loads(text)
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("brief_key"):
        return None
    if "brief_key" in d:                                     # an empty one: fill it in place
        new = re.sub(r'("brief_key"\s*:\s*)(null|"")', lambda m: m.group(1) + json.dumps(key), text, count=1)
    else:
        m = re.match(r"(\s*\{)(\s*)", text)
        if not m:
            return None
        lead, gap = m.group(1), m.group(2)
        field = f'"brief_key": {json.dumps(key)}'
        if not d:                                            # {} -> {"brief_key": "..."}
            new = lead + field + text[m.end():]
        elif "\n" in gap:
            new = lead + gap + field + "," + gap + text[m.end():]
        else:
            new = lead + gap + field + ", " + text[m.end():]
    try:
        back = json.loads(new)
    except ValueError:
        return None
    rest = {k: v for k, v in back.items() if k != "brief_key"}
    return new if back.get("brief_key") == key and rest == {k: v for k, v in d.items() if k != "brief_key"} else None


def stamp_file(path, key):
    """True when the file was stamped."""
    p = Path(path)
    text = p.read_text()
    new = stamp_text(text, key)
    if new is None or new == text:
        return False
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(new)
    os.replace(tmp, p)
    return True


def correct_text(text, old, new_brief, key):
    """The record's text with `"brief": old` changed to new_brief, `brief_was: old` added and `brief_key` set — one
    value changed and two fields added by text, nothing else moved — or None when that cannot be done safely."""
    try:
        d = json.loads(text)
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("brief") != old or "brief_was" in d:
        return None
    t, n = re.subn(r'("brief"\s*:\s*)' + re.escape(json.dumps(old)), lambda m: m.group(1) + json.dumps(new_brief), text, count=1)
    if n != 1:
        return None
    m = re.match(r"(\s*\{)(\s*)", t)
    gap = m.group(2)
    sep = ("," + gap) if "\n" in gap else ", "
    t = m.group(1) + gap + f'"brief_was": {json.dumps(old)}' + sep + t[m.end():]
    if d.get("brief_key") and d["brief_key"] != key:
        t = re.sub(r'("brief_key"\s*:\s*)' + re.escape(json.dumps(d["brief_key"])), lambda q: q.group(1) + json.dumps(key), t,
                   count=1)
    elif not d.get("brief_key"):
        t = stamp_text(t, key) or t
    back = json.loads(t)
    want = dict(d, brief=new_brief, brief_was=old, brief_key=key)
    return t if back == want else None


def corrections(repo=None):
    """[(record, old brief, new brief, key)] for every CLEAR collision in the briefs index (see briefs_index.collisions)."""
    repo = Path(repo or BI.REPO)
    reg = BI.Register(repo)
    out = []
    for c in BI.collisions(BI.place_runs(repo, reg), reg, repo):
        if c["clear"]:
            rk = reg.lookup(c["placed"])
            out.append((c["record"], c["says"], reg.rows[rk].get("brief") or rk, c["placed"]))
    return out


def plan(repo=None):
    """[(station, record path, key)] for every record that would be stamped."""
    repo = Path(repo or BI.REPO)
    names = BI.names(repo)
    out = []
    for p in BI.place_runs(repo):
        if not p["key"] or not names.parse_brief_key(p["key"]):    # a key only; an old pNNN that would share one is not
            continue
        for r in p["records"]:
            d = BI._read(repo / r)
            if isinstance(d, dict) and not d.get("brief_key"):
                out.append((p["station"], r, p["key"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="stamp the records (default: say what would be stamped)")
    ap.add_argument("--fix-briefs", action="store_true",
                    help="correct the runs whose own `brief` the register and a hand-off clearly contradict")
    a = ap.parse_args(argv)
    if a.fix_briefs:
        n = 0
        for r, old, new, key in corrections():
            f = BI.REPO / r
            t = correct_text(f.read_text(), old, new, key)
            print(f"  {r}: {old} -> {new} ({key})" + ("" if t else "  [left alone: cannot be edited safely]"))
            if t and a.apply:
                tmp = f.with_name(f".{f.name}.{os.getpid()}.tmp")
                tmp.write_text(t)
                os.replace(tmp, f)
                n += 1
        print(f"{'corrected' if a.apply else 'would correct'} {n if a.apply else len(corrections())} run record(s)")
        if a.apply:
            BI.write()
        return 0
    todo = plan()
    done, per = 0, {}
    for st, r, key in todo:
        if a.apply and not stamp_file(BI.REPO / r, key):
            continue
        done += 1
        per[st] = per.get(st, 0) + 1
    for st in BI.STATIONS:
        print(f"  {st:17} {per.get(st, 0)}")
    print(f"{'stamped' if a.apply else 'would stamp'} {done} run record(s)")
    if a.apply:
        w = BI.write()
        print(f"rebuilt {w['json']} + {w['md']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
