"""File one act on a triage item to the decision log: one `triage` record, append-only.

    python3 components/triage/tools/file_record.py <act> --item <id> --who <person> [fields...] [--dry-run]

Acts and what each needs (platform/data/kinds/triage.json is the authority; this reads it, never a copy):
  close    --evidence path:line@sha [...]          answer   --words "..."
  forward  --forwarded-to <person>                 change   --commit <sha> --test <test> (Option 3, ruled 2026-10-02)
  draft    (optional --why)                        sign     (the owner agrees; optional --why)
  undo     --undoes <record file name>             decide   --ruling <decision-log pointer>
Every act may carry --theme, --areas (repeat; typed: path:… brand:… product:…) and --why (one plain line).

Writes platform/data/records/triage/<UTC stamp>--<who>--<item slug>.json and prints the path; commit it with the
change it records. Refuses, naming the reason: an act or field the kind doesn't declare; a required field missing;
evidence not path:line@sha; a commit that is not a sha in this repo; an undo pointing at no change record.
Python 3.9-clean; no network, no credential. ≈ STREAM · atlas [6941d8], 2026-10-02."""
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KIND = ROOT / "platform/data/kinds/triage.json"
PLANE = ROOT / "platform/data/records/triage"
SLUG = re.compile(r"[^A-Za-z0-9._-]+")


def refuse(msg):
    sys.exit(f"refused: {msg}")


def slug(item):
    s = SLUG.sub("-", item.replace("#", "-").replace(" ", "")).strip("-")
    return s[:80] or refuse(f"item {item!r} makes no id")


def is_commit(sha):
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha or ""):
        return False
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True).returncode == 0


def main(argv=None):
    kind = json.loads(KIND.read_text(encoding="utf-8"))
    fields = {f["key"]: f for f in kind["verdict_fields"]}
    acts = fields["act"]["values"]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("act", choices=acts)
    ap.add_argument("--item", required=True, help="human form: intake#6, intake #6, or an action slug")
    ap.add_argument("--who", required=True, help="the person who acted, lowercase (team/people/<name>)")
    ap.add_argument("--filed-by", help="who files it, if not the person who acted (e.g. a seat relaying)")
    ap.add_argument("--theme"); ap.add_argument("--why"); ap.add_argument("--words")
    ap.add_argument("--forwarded-to"); ap.add_argument("--commit"); ap.add_argument("--test")
    ap.add_argument("--ruling"); ap.add_argument("--undoes")
    ap.add_argument("--areas", action="append", default=[]); ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true", help="print the record, write nothing")
    a = ap.parse_args(argv)

    item = re.sub(r"\s*#\s*", " #", a.item.strip()) if "#" in a.item else a.item.strip()
    v = {"act": a.act, "item": item, "who": a.who.lower()}
    for key, val in (("theme", a.theme), ("why", a.why), ("words", a.words), ("forwarded_to", a.forwarded_to),
                     ("commit", a.commit), ("test", a.test), ("ruling", a.ruling), ("undoes", a.undoes),
                     ("areas", a.areas), ("evidence", a.evidence)):
        if val not in (None, "", []):
            if key not in fields:
                refuse(f"`{key}` is not a field of the triage kind")
            v[key] = val
    for key, f in fields.items():
        cond = f.get("required_when")
        if cond and cond == f"act={a.act}" and v.get(key) in (None, "", []):
            refuse(f"a {a.act} needs --{key.replace('_', '-')} ({f.get('note', '')[:120]})")
    pat = (fields.get("evidence") or {}).get("pattern")
    for x in v.get("evidence", []):
        if pat and not re.match(pat, x):
            refuse(f"evidence {x!r} is not path:line@sha")
    if "commit" in v and not is_commit(v["commit"]):
        refuse(f"commit {v['commit']!r} is not a commit sha in this repo (never a branch)")
    if "undoes" in v:
        target = PLANE / v["undoes"]
        if not target.is_file():
            refuse(f"--undoes {v['undoes']!r} names no record in {PLANE.relative_to(ROOT)}")
        if json.loads(target.read_text(encoding="utf-8")).get("verdict", {}).get("act") != "change":
            refuse("--undoes must name a `change` record")
    if a.why and len(a.why) > 200:
        refuse("--why is one plain line (200 characters at most)")

    now = datetime.now(timezone.utc)
    filer = (a.filed_by or a.who).lower()
    rec = {"schema": 1, "kind": "triage", "reviewer": filer, "item": slug(item), "verdict": v,
           "created": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "via": "components/triage/tools/file_record.py"}
    out = PLANE / f'{now.strftime("%Y%m%dT%H%M%SZ")}--{filer}--{rec["item"]}.json'
    if a.dry_run:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return 0
    PLANE.mkdir(parents=True, exist_ok=True)
    if out.exists():
        refuse(f"{out.name} exists; records are never overwritten")
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
