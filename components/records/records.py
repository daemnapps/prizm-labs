#!/usr/bin/env python3
"""The records: every record the system keeps, one name each, linked by id.

    python3 components/records/records.py list                      # every record, what it means, what it links to
    python3 components/records/records.py new <record> [--brand <id>]  # a blank record to fill, printed
    python3 components/records/records.py check <file.json> ...     # each file against its record's shape
    python3 components/records/records.py trace <id> --root <dir>   # one record back through its links

The definition is records.json beside this file. Records live at brands/<brand>/records/<record>/<id>.json.
Standard library only.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = re.compile(r"^https?://\S+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def load():
    return json.loads((HERE / "records.json").read_text())["records"]


def shape(defs, name):
    """A record's fields, with the fields of the record it extends."""
    d = defs[name]
    fields = dict(shape(defs, d["extends"])) if d.get("extends") else {}
    fields.update(d["fields"])
    return fields


def record_of(defs, rid):
    """The record an id belongs to, by its prefix (longest prefix wins)."""
    hits = [n for n, d in defs.items() if isinstance(rid, str) and rid.startswith(d["prefix"])]
    return max(hits, key=lambda n: len(defs[n]["prefix"])) if hits else None


def links_to(defs, target, linked):
    """True when an id of record `linked` may stand where `target` is asked (a presell page is a page)."""
    while linked:
        if linked == target:
            return True
        linked = defs[linked].get("extends")
    return False


def check_value(defs, kind, value):
    optional = kind.endswith("?")
    kind = kind.rstrip("?")
    if value in (None, "", []):
        return None if optional else "is empty"
    if kind == "text":
        return None if isinstance(value, str) else "should be text"
    if kind == "number":
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else "should be a number"
    if kind == "url":
        return None if isinstance(value, str) and URL.match(value) else "should be a web address"
    if kind == "date":
        return None if isinstance(value, str) and DATE.match(value) else "should be a date (YYYY-MM-DD)"
    if kind == "list":
        return None if isinstance(value, list) else "should be a list"
    if kind == "object":
        return None if isinstance(value, dict) else "should be an object"
    if kind.startswith("one-of:"):
        opts = kind[7:].split("|")
        return None if value in opts else "should be one of " + ", ".join(opts)
    if kind.startswith(("id:", "ids:")):
        target = kind.split(":", 1)[1]
        ids = value if kind.startswith("ids:") else [value]
        if kind.startswith("ids:") and not isinstance(value, list):
            return "should be a list of ids"
        for i in ids:
            if not links_to(defs, target, record_of(defs, i)):
                return f"{i!r} is not a {target} id"
        return None
    return f"unknown field type {kind}"


def check(defs, rec):
    """Problems with one record, as plain lines. Empty list = it passes."""
    rid = rec.get("id")
    name = record_of(defs, rid)
    if not name:
        return [f"id {rid!r} does not start with any record's prefix"]
    if rec.get("record") not in (None, name):
        return [f"says it is a {rec.get('record')} but its id is a {name} id"]
    problems = []
    for field, kind in shape(defs, name).items():
        why = check_value(defs, kind, rec.get(field))
        if why:
            problems.append(f"{field} {why}")
    return problems


def blank(defs, name, brand=None):
    if name not in defs:
        sys.exit(f"records: no record {name!r}. Records: {', '.join(defs)}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rec = {"id": defs[name]["prefix"] + stamp, "record": name}
    for field, kind in shape(defs, name).items():
        k = kind.rstrip("?")
        rec[field] = [] if k in ("list",) or k.startswith("ids:") else {} if k == "object" else ""
    if brand and "brand" in rec:
        rec["brand"] = brand
    if name == "session":
        rec["started"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return rec


def index(root):
    found = {}
    for p in Path(root).rglob("*.json"):
        try:
            rec = json.loads(p.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(rec, dict) and isinstance(rec.get("id"), str):
            found[rec["id"]] = rec
    return found


def trace(defs, rid, root):
    """The chain of records behind one id, nearest first."""
    recs, out, todo, seen = index(root), [], [rid], set()
    while todo:
        i = todo.pop(0)
        if i in seen:
            continue
        seen.add(i)
        rec = recs.get(i)
        if not rec:
            out.append((i, None))
            continue
        out.append((i, record_of(defs, i)))
        for field, kind in shape(defs, record_of(defs, i)).items():
            v = rec.get(field)
            if kind.rstrip("?").startswith(("id:", "ids:")) and v:
                todo += v if isinstance(v, list) else [v]
    return out


def main(argv):
    defs = load()
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        for n, d in defs.items():
            links = sorted({k.split(":", 1)[1].rstrip("?") for k in shape(defs, n).values() if k.startswith(("id:", "ids:"))})
            print(f"{n:<20} {d['means']}" + (f"  → {', '.join(links)}" if links else ""))
        return 0
    if cmd == "new" and len(argv) > 1:
        brand = argv[argv.index("--brand") + 1] if "--brand" in argv else None
        print(json.dumps(blank(defs, argv[1], brand), indent=1))
        return 0
    if cmd == "check" and len(argv) > 1:
        bad = 0
        for f in argv[1:]:
            problems = check(defs, json.loads(Path(f).read_text()))
            print(f"{'✓' if not problems else '✗'} {f}" + "".join(f"\n    {p}" for p in problems))
            bad += bool(problems)
        return 1 if bad else 0
    if cmd == "trace" and len(argv) > 1 and "--root" in argv:
        for i, name in trace(defs, argv[1], argv[argv.index("--root") + 1]):
            print(f"{name or 'missing':<20} {i}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
