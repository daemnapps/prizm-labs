#!/usr/bin/env python3
"""The human layer over a planned month.

`slots.json` is the MACHINE's record of what it decided and why. This is the
separate file a reviewer writes into — status, edits, notes — so the two never
overwrite each other. Re-planning a month replaces slots.json and leaves every
judgement already made on it intact; a reviewer's rewrite is never lost to a
re-run, and a re-run is never quietly re-approved.

    review.json
    {
      "slots": {
        "sep-01": {
          "status": "approved" | "needs-work" | "cut" | "pending",
          "note":   "free text from the reviewer",
          "edits":  {"<field>": "<new value>", ...},          # overrides
          "by": "<who>", "at": "<iso timestamp>",
          "identity": {"date", "segment", "type", "occasion"}  # the send it was for
        }
      },
      "copy": {"sep-01": {"state": "queued|running|done|failed", "at": ...}}
    }

A field the reviewer never touched is absent from `edits`, so the board can
always show what the machine said beside what the human changed it to.
"""
import datetime
import json
from pathlib import Path

STATUSES = ("pending", "approved", "needs-work", "cut")

# The fields a reviewer may rewrite. Everything else on a slot is the
# machine's reasoning — readable, never editable, because editing a `why`
# would forge the record of why the send exists.
EDITABLE = ("date", "hour", "segment", "category", "type", "role",
            "offer", "product", "occasion", "angle")


def path(run_dir):
    return Path(run_dir) / "review.json"


def load(run_dir):
    try:
        d = json.loads(path(run_dir).read_text())
    except (FileNotFoundError, ValueError):
        d = {}
    d.setdefault("slots", {})
    d.setdefault("copy", {})
    return d


def save(run_dir, data):
    path(run_dir).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def for_slot(data, slot_id):
    return data["slots"].setdefault(
        slot_id, {"status": "pending", "note": "", "edits": {}})


# WHICH SEND a review was given to. Ids are renumbered in date order on every
# plan, so an id alone can carry an approval onto a different send after a
# replan (CAL-1 (calendar gates hold), SI-148, 2026-10-08). Each entry stores
# the send's identity when it is written, and is laid on a slot only when the
# slot still IS that send. Taken from the PLANNER's slot, never the edited
# view, so a reviewer's own date edit does not orphan their review.
IDENTITY = ("date", "segment", "type", "occasion")


def identity(slot):
    return {f: slot.get(f) for f in IDENTITY}


def describe(ident):
    return " · ".join(str(ident[f]) for f in IDENTITY if ident.get(f)) or "an unnamed send"


def month_slots(run_dir):
    try:
        slots = json.loads((Path(run_dir) / "slots.json").read_text())
    except (FileNotFoundError, ValueError):
        return []
    if isinstance(slots, dict):
        slots = slots.get("slots", [])
    return slots


def _entry(run_dir, d, slot_id, slot):
    """The entry a write lands on, stamped with the send it is for. An entry
    made for another send is set aside, never carried onto this one."""
    if slot is None:
        slot = next((s for s in month_slots(run_dir) if s.get("id") == slot_id), None)
    r = for_slot(d, slot_id)
    if slot is None:                      # not in the month: written as before
        return r
    ident = identity(slot)
    if r.get("identity") not in (None, ident):
        old = {k: v for k, v in r.items() if k != "superseded"}
        r = d["slots"][slot_id] = {"status": "pending", "note": "", "edits": {},
                                   "superseded": old}
    r["identity"] = ident
    return r


def set_status(run_dir, slot_id, status, who="reviewer", slot=None):
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    d = load(run_dir)
    r = _entry(run_dir, d, slot_id, slot)
    r.update(status=status, by=who, at=now())
    return save(run_dir, d)


def set_note(run_dir, slot_id, note, who="reviewer", slot=None):
    d = load(run_dir)
    r = _entry(run_dir, d, slot_id, slot)
    r.update(note=note, by=who, at=now())
    return save(run_dir, d)


def set_edit(run_dir, slot_id, field, value, who="reviewer", slot=None):
    """An edit back to the machine's own value clears the override, so a
    reverted change stops reading as a change."""
    if field not in EDITABLE:
        raise ValueError(f"{field!r} is not a reviewer-editable field")
    d = load(run_dir)
    r = _entry(run_dir, d, slot_id, slot)
    value = (value or "").strip()
    if value:
        r["edits"][field] = value
    else:
        r["edits"].pop(field, None)
    r.update(by=who, at=now())
    return save(run_dir, d)


def clear_edit(run_dir, slot_id, field):
    d = load(run_dir)
    for_slot(d, slot_id)["edits"].pop(field, None)
    return save(run_dir, d)


def applied(slots, data):
    """Every slot with the reviewer's overrides laid on top, plus the review
    state itself. This is what anything downstream should read — the copy
    machine must write the send the human approved, not the one the planner
    first proposed."""
    out = []
    for s in slots:
        r = data["slots"].get(s["id"], {})
        # `identity` on _review: "verified" (stored and matching), "unverified"
        # (a legacy entry with none stored — applied as before), "mismatch"
        # (made for another send — not applied), or None (never reviewed).
        stored = r.get("identity")
        if not r:
            check = None
        elif stored is None:
            check = "unverified"
        elif stored == identity(s):
            check = "verified"
        else:
            check = "mismatch"
            r = {"status": "pending", "edits": {},
                 "note": f"review was for {describe(stored)}; re-review"}
        merged = dict(s)
        # What the PLANNER said, kept beside what the human made of it — the
        # board shows both, and a merge that forgot the original would show
        # the edit twice (caught on the first edit, 2026-09-13).
        orig = {f: s.get(f) for f in EDITABLE if f != "angle"}
        vs = s.get("variants") or []
        orig["angle"] = vs[0].get("angle") if vs else s.get("angle")
        merged["_orig"] = orig
        merged["variants"] = [dict(v) for v in vs]
        for f, v in (r.get("edits") or {}).items():
            if f == "angle":
                for var in merged.get("variants") or []:
                    var["angle"] = v
            elif f == "hour":
                try:
                    merged["hour"] = int(v)
                except ValueError:
                    merged["hour"] = v
            else:
                merged[f] = v
        if "segment" in (r.get("edits") or {}):
            merged["segments"] = [merged["segment"]]
        merged["_review"] = {"status": r.get("status", "pending"),
                             "note": r.get("note", ""),
                             "edits": r.get("edits", {}),
                             "at": r.get("at"), "by": r.get("by"),
                             "identity": check}
        merged["_copy"] = data["copy"].get(s["id"], {})
        out.append(merged)
    return out


# ------------------------------------------------------------------ mark: one verdict from outside the board
# The emails page's Calendar tab lets a reviewer judge an unwritten send where he sees it (email_lead, 2026-11-06: "you
# fix it, owner reviews"; owner reviews every send of the month). It writes through the same set_status / set_note
# the board uses, into the same review.json, and commits that one file by path; the page server's sync pushes it.
#     python3 review.py mark <brand> <YYYY-MM> <slot id> <approved|needs-work|cut|pending> --by <person>
#                           [--note "<one line>"] [--no-commit]
#     python3 review.py edit <brand> <YYYY-MM> <slot id> <field> --value "<new value>" --by <person> [--no-commit]
#                           (field: one of EDITABLE; an empty value clears the rewrite)
# Exit 0 marked (and committed) · 2 refused, nothing written (no such month or slot, bad status) · 1 the commit failed
# (the file is written; the server's next sync commits it).
def mark(brand, month, slot_id, status, by, note=None, root=None, commit=True, run=None):
    if status not in STATUSES:
        raise ValueError("unknown status %r: one of %s" % (status, ", ".join(STATUSES)))

    def act(run_dir, slot):
        set_status(run_dir, slot_id, status, who=by, slot=slot)
        if note is not None:
            set_note(run_dir, slot_id, note.strip(), who=by, slot=slot)
    return _write(brand, month, slot_id, by, root, commit, run, act, status)


def edit(brand, month, slot_id, field, value, by, root=None, commit=True, run=None):
    """One field of a planned send rewritten from the emails page (L61 (rewrite a planned send)), through the board's
    own set_edit: an empty value clears the rewrite. Committed by path like mark()."""
    return _write(brand, month, slot_id, by, root, commit, run,
                  lambda run_dir, slot: set_edit(run_dir, slot_id, field, value, who=by, slot=slot),
                  "%s %s" % (field, "rewritten" if (value or "").strip() else "put back to the plan"))


def _write(brand, month, slot_id, by, root, commit, run, act, what):
    import re
    import subprocess
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", brand or "") or not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise ValueError("want a brand and a month YYYY-MM")
    repo = Path(root) if root else Path(__file__).resolve().parents[3]
    run_dir = repo / "runs" / "marketing-calendar" / brand / month
    slot = next((s for s in month_slots(run_dir) if s.get("id") == slot_id), None)
    if slot is None:
        raise ValueError("%s %s has no slot %r" % (brand, month, slot_id))
    act(run_dir, slot)
    said = "%s %s %s: %s by %s" % (brand, month, slot_id, what, by)
    if not commit:
        return said
    rel = str(path(run_dir).relative_to(repo))
    run = run or subprocess.run
    for argv in (["git", "add", "--", rel],
                 ["git", "commit", "-q", "-m", "calendar review: %s" % said, "--", rel]):
        r = run(argv, cwd=str(repo), capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            raise RuntimeError("written, not committed: %s" % ((r.stderr or r.stdout or "").strip()[-200:]))
    return said + " · committed"


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="One reviewer's verdict on one planned send, into review.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mark")
    m.add_argument("brand"); m.add_argument("month"); m.add_argument("slot"); m.add_argument("status")
    m.add_argument("--by", required=True); m.add_argument("--note"); m.add_argument("--no-commit", action="store_true")
    e = sub.add_parser("edit")
    e.add_argument("brand"); e.add_argument("month"); e.add_argument("slot"); e.add_argument("field")
    e.add_argument("--value", default=""); e.add_argument("--by", required=True)
    e.add_argument("--no-commit", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "edit":
            print(edit(a.brand, a.month, a.slot, a.field, a.value, a.by, commit=not a.no_commit))
        else:
            print(mark(a.brand, a.month, a.slot, a.status, a.by, a.note, commit=not a.no_commit))
    except ValueError as e:
        print("refused: %s" % e, file=sys.stderr)
        sys.exit(2)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
