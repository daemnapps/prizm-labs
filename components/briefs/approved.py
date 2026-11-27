#!/usr/bin/env python3
"""Only a brief the owner approved is readable by a maker (2026-11-25). One record, runs/briefs/approved.json, read by
every list a maker opens: make.py waiting, video-edit/handoff/pull.py waiting, creative-queue/statics.py, maker_queue.py.

  approved.py list                                   every approved brief, and what each is held until
  approved.py add <brief key> ... --how "<where the owner said it>" [--hold-until YYYY-MM-DD]
  approved.py hold <brief key> ... --until YYYY-MM-DD      approved, and not shown before that day
  approved.py revoke <brief key> ... --how "<where>"

Nothing here approves: it records a yes the owner gave in their own words, named in --how. The queue's decision log is not
read: it names the owner by default whoever acted, so a row there proves nothing. A brief
approved under its run is approved under the number the register gives that run later. No record, or a record that
cannot be read, means not approved: the list is short, never open. Runs by: person.
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REL = ("runs", "briefs", "approved.json")
# The makers' roles whose lists are locked to the record. Any other role reads everything.
LOCKED = ("video-editor", "video-producer", "graphic-designer")
OWNER = "owner"


def _load(repo=None):
    try:
        got = json.loads(Path(repo or REPO).joinpath(*REL).read_text(encoding="utf-8"))
        return got if isinstance(got.get("approved"), dict) else {"approved": {}}
    except (OSError, ValueError, AttributeError):
        return {"approved": {}}


def _register(repo=None):
    try:
        f = Path(repo or REPO) / "components" / "image-teardown" / "briefs.json"
        return json.loads(f.read_text(encoding="utf-8")).get("briefs") or {}
    except (OSError, ValueError):
        return {}


def keys(repo=None, today=None):
    """Every brief key a maker may read today: approved, and not held to a later day. An approval given on a run before
    it was numbered covers the number the register gives that run."""
    today = str(today or date.today().isoformat())
    rows = _load(repo)["approved"]
    ok = {k for k, v in rows.items() if isinstance(v, dict) and not v.get("revoked")
          and str(v.get("hold_until") or "") <= today}
    held = {k for k, v in rows.items() if k not in ok}
    for k, v in _register(repo).items():
        run = v.get("run") if isinstance(v, dict) else None
        if run and k not in held and "%s_idea_%s" % (v.get("brand"), run) in ok:
            ok.add(k)
    return ok


class Everything(object):
    def __contains__(self, key):
        return True


def readable(role, repo=None, today=None):
    """What a role may read: the approved briefs for a locked role, else everything."""
    return keys(repo, today) if role in LOCKED else Everything()


def _save(doc, repo=None):
    f = Path(repo or REPO).joinpath(*REL)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(f)


def add(ks, how, by=OWNER, at=None, hold=None, repo=None):
    doc = _load(repo)
    for k in ks:
        row = {"by": by, "at": at or datetime.now().isoformat(timespec="seconds"), "how": how}
        if hold:
            row["hold_until"] = hold
        doc["approved"][k] = row
    _save(doc, repo)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("list", "add", "hold", "revoke"))
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--how")
    ap.add_argument("--hold-until")
    ap.add_argument("--until")
    a = ap.parse_args(argv)
    doc = _load()
    if a.cmd in ("add", "revoke") and not (a.keys and a.how):
        ap.error("name the briefs and --how: where the owner said it")
    if a.cmd == "add":
        add(a.keys, a.how, hold=a.hold_until)
    elif a.cmd in ("hold", "revoke"):
        gone = [k for k in a.keys if k not in doc["approved"]]
        if gone or not a.keys or (a.cmd == "hold" and not a.until):
            ap.error("not approved: %s" % ", ".join(gone) if gone else "name the briefs and --until")
        for k in a.keys:
            doc["approved"][k].update({"hold_until": a.until} if a.cmd == "hold" else
                                      {"revoked": datetime.now().isoformat(timespec="seconds"), "revoked_how": a.how})
        _save(doc)
    now = keys()
    for k, v in sorted(_load()["approved"].items()):
        print("%-58s %s" % (k, "readable" if k in now else "revoked" if v.get("revoked") else "held to %s" % v.get("hold_until")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
