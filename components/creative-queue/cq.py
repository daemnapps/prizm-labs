"""cq.py — the one queue command every Claude can call, QB-1 (queue core).

  cq.py set <id> <field> <value>                  a person's decision on one field (who, priority, due, title_set,
                                                  note, requested_stage); due is YYYY-MM-DD or "" to clear,
                                                  anything else is refused with exit 2
  cq.py add <id> --title T [--brand B] [--type K] a new entry no machine has seen yet
  cq.py remove <id> | restore <id> | approve <id>
  cq.py rebuild [--now <UTC …Z>]                  observations + decisions -> index.json
  cq.py show <id>                                 the reduced entry, as JSON
  cq.py import-legacy --from <queue dir>          today's per-entry files -> observations/localhost.json
                                                  + decisions/owner/legacy.jsonl

Every subcommand takes --root (default <repo>/runs/queue-shadow) and --no-commit; the decision ones take
--by (default: the name before "@" in `git config user.email`). Without --no-commit a writing subcommand
commits and pushes exactly the files it wrote. Exit 0 ok, 2 refused (the live queue is off), 1 any other error.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import qcore  # noqa: E402
from qcore import paths  # noqa: E402

RUN = subprocess.run          # the git seam: tests replace it, nothing else does
LEGACY_SOURCE = "localhost"   # the one machine that writes today's store
LEGACY_PERSON = "owner"
LEGACY_HUMAN = ("who", "priority", "title_set", "note", "removed", "removed_at", "decided")   # today's person fields
APPROVE_ACTIONS = ("go", "approve")


def _person():
    """The person whose team/people/<id>/identity.json lists git config user.email
    (run_kit.people, never the name before "@" — LD-77 (one person resolver)), or None."""
    from run_kit import people    # on sys.path through qcore
    try:
        r = RUN(["git", "config", "user.email"], capture_output=True, text=True)
    except OSError:
        return None
    email = (r.stdout or "").strip() if r.returncode == 0 else ""
    return people.try_person_of(paths.repo(), email)


def _commit(a, files, message):
    if a.no_commit or not files:
        return
    sha = qcore.commit_paths(files, message, paths.repo(), run=RUN)
    print("commit: %s" % sha)


def _decide(a, root, rec):
    person = (a.by or _person() or "").strip().lower()
    if not person:
        raise ValueError("cannot read your name from git config user.email — pass --by <person>")
    path = qcore.append_decision(root, person, rec)
    print("decision: %s" % path)
    what = " ".join(str(x) for x in (rec["op"], rec["id"], rec.get("field") or "") if x)
    _commit(a, [path], "creative-queue: %s %s" % (person, what))
    return 0


def cmd_set(a, root):
    if a.field == "due" and not qcore.due_ok(a.value):
        print("REFUSED: due must be a date like 2026-10-27, or \"\" to clear, got %r" % a.value, file=sys.stderr)
        return 2
    return _decide(a, root, {"id": a.id, "op": "set", "field": a.field, "value": a.value})


def cmd_add(a, root):
    value = {"title": a.title}
    if a.brand:
        value["brand"] = a.brand
    if a.type:
        value["type"] = a.type
    return _decide(a, root, {"id": a.id, "op": "add", "value": value})


def cmd_op(a, root):
    return _decide(a, root, {"id": a.id, "op": a.cmd})


def cmd_rebuild(a, root):
    now = qcore._need_utc(a.now, "--now") if a.now else qcore.utc_now()
    obs, dec = qcore.load(root)
    idx = qcore.reduce(obs, dec, now)
    path = qcore.write_index(root, idx)
    srcs = ", ".join("%s %ss" % (s, "?" if v["age_s"] is None else v["age_s"]) for s, v in idx["sources"].items())
    print("index: %d entries · sources: %s" % (len(idx["entries"]), srcs or "none"))
    _commit(a, [path], "creative-queue: rebuild index (%d entries)" % len(idx["entries"]))
    return 0


def cmd_show(a, root):
    obs, dec = qcore.load(root)
    hit = next((e for e in qcore.reduce(obs, dec, qcore.utc_now())["entries"] if e["id"] == a.id), None)
    if hit is None:
        raise ValueError("no entry called %s under %s" % (a.id, root))
    print(json.dumps(hit, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


def _when(e, field):
    """The entry's own timestamp for a person field, as written: the last history line that set it, else
    the entry's updated / created. Naive local text is kept as text."""
    for h in reversed(e.get("history") or []):
        if isinstance(h, dict) and isinstance(h.get("set"), dict) and field in h["set"] and h.get("at"):
            return h["at"]
    return e.get("updated") or e.get("created") or ""


def _legacy(eid, op, field, value, made):
    return {"schema": 1, "id": eid, "op": op, "field": field, "value": value, "by": LEGACY_PERSON,
            "made": made, "legacy": True}


def cmd_import_legacy(a, root):
    src = Path(a.source).expanduser()
    if not src.is_dir():
        raise ValueError("--from %s is not a folder" % src)
    entries, lines = {}, []
    for f in sorted(src.glob("*/*.json")):
        try:
            e = json.loads(f.read_text())
        except ValueError:
            continue
        # an entry file is named for its own id; a moved idea's old name points at the new one and is skipped
        if not isinstance(e, dict) or e.get("id") != f.stem or e.get("moved_to"):
            continue
        eid = e["id"]
        o = {k: v for k, v in e.items() if k not in LEGACY_HUMAN and k not in ("id", "stage")}
        if e.get("stage") not in (None, ""):
            o["observed_stage"] = e["stage"]
        entries[eid] = o
        for k in ("who", "priority", "title_set", "note"):
            if e.get(k) not in (None, ""):
                lines.append(_legacy(eid, "set", k, e[k], _when(e, k)))
        if e.get("removed"):
            lines.append(_legacy(eid, "remove", None, None, e.get("removed_at") or _when(e, "removed")))
        d = e.get("decided")
        if isinstance(d, dict):
            if d.get("action") in APPROVE_ACTIONS:
                lines.append(_legacy(eid, "approve", None, d, d.get("at") or _when(e, "decided")))
            else:
                print("skipped: %s decided %r is not an approval" % (eid, d.get("action")), file=sys.stderr)
    written = []
    p = qcore.write_observation(root, LEGACY_SOURCE, entries)
    if p:
        written.append(p)
    legacy = Path(root) / "decisions" / LEGACY_PERSON / "legacy.jsonl"
    text = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in lines)
    try:
        old = legacy.read_text()
    except OSError:
        old = None
    if old != text:
        written.append(qcore._write(legacy, text))
    print("legacy: %d entries, %d decisions" % (len(entries), len(lines)))
    _commit(a, written, "creative-queue: import legacy queue (%d entries, %d decisions)" % (len(entries), len(lines)))
    return 0


def parser():
    ap = argparse.ArgumentParser(prog="cq.py", description="The shared creative queue: decisions, rebuild, show.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, func, decision=False, help=None):
        p = sub.add_parser(name, help=help)
        p.add_argument("--root", help="queue folder (default <repo>/runs/queue-shadow)")
        p.add_argument("--no-commit", action="store_true", help="write only; no git add / commit / push")
        if decision:
            p.add_argument("--by", help="the person deciding (default: from git config user.email)")
        p.set_defaults(func=func)
        return p

    p = add("set", cmd_set, True, "set one field: " + ", ".join(qcore.SETTABLE))
    p.add_argument("id")
    p.add_argument("field", choices=qcore.SETTABLE)
    p.add_argument("value")
    p = add("add", cmd_add, True, "add an entry no machine has seen yet")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--brand")
    p.add_argument("--type")
    for op in ("remove", "restore", "approve"):
        add(op, cmd_op, True, op + " an entry").add_argument("id")
    add("rebuild", cmd_rebuild, help="observations + decisions -> index.json").add_argument(
        "--now", help="the build time, UTC like 2026-10-22T02:24:18Z (default: now)")
    add("show", cmd_show, help="print one reduced entry").add_argument("id")
    add("import-legacy", cmd_import_legacy, help="today's per-entry files -> observation + legacy decisions"
        ).add_argument("--from", dest="source", required=True, help="the old queue folder (<brand>/<id>.json)")
    return ap


def main(argv=None):
    try:
        a = parser().parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1
    try:
        root = qcore.check_root(a.root or qcore.shadow_root())
        return a.func(a, root)
    except qcore.Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    except (ValueError, RuntimeError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
