"""THE FACE GATE — no clip is made from a picture whose people are not the people on their banked masters
(the owner, 2026-10-23, after the pastor barber body put a different man in Marcus's chair in four scenes: "you have
the nerve to tell me that's the same guy sitting in the chair?" … "establish a fix in the chain for this").

identity.py has asked the question since 2026-10-02, but only as a CHECK: run.py printed a DIFFERENT and moved on,
and the clip step's face lock compares a clip with its own picture — so a wrong picture passed both. A session that
made its pictures by hand (outside run.py) skipped even the check. The gate closes both holes at the clip door:

    stamp(picture, masters)            -> asks identity.check, writes <picture>.faces.json, returns the record
    require(picture, masters=None,     -> the record, or a REFUSAL (SystemExit) naming the person who is different
            no_people=False)
    masters_for(run, people)           -> each person's banked master, read from the run's elements.json

A record belongs to the picture's exact bytes (sha256): remade picture, new check. Every person must come back SAME
by majority; DIFFERENT or UNCHECKED (the judge did not answer) refuses — a face nobody confirmed is never animated.
A crowd element (its spec says many people) comes back GROUP and passes; a person seen from behind is judged by
head, hair, skin and build (model-inputs.json frame_rules.face_check, 2026-10-24).
A picture with nobody of ours in it is stamped `no_people`, said by the caller, never assumed.

    python3 machine/face_gate.py stamp <picture> --master <master.png> [--master …]
    python3 machine/face_gate.py stamp <picture> --no-people
    python3 machine/face_gate.py show  <picture>

The clip doors call require(): seedance.py talk/motion (every hand-made clip) and clips_run.make_call (the chain).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
# SAME, or GROUP: the master stands for a crowd (a congregation, a choir), which has no one face to match — the
# judge says so from the element's own words (identity.stands_for), never a list kept here (2026-10-24)
PASSES = ("SAME", "GROUP")


def _load(name):
    sp = importlib.util.spec_from_file_location(f"vm_fg_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def sidecar(picture) -> Path:
    p = Path(picture)
    return p.with_name(p.name + ".faces.json")


def sha(picture) -> str:
    return hashlib.sha256(Path(picture).read_bytes()).hexdigest()


def read(picture):
    """The picture's record, or None when there is none or it was made for other bytes."""
    s = sidecar(picture)
    try:
        rec = json.loads(s.read_text())
    except (OSError, ValueError):
        return None
    return rec if rec.get("sha") == sha(picture) else None


def stamp(picture, masters, no_people: bool = False, check=None) -> dict:
    """Ask the face question for every master and write the record beside the picture."""
    picture = Path(picture)
    masters = [str(m) for m in masters or []]
    if not masters and not no_people:
        raise SystemExit(f"FACE GATE: {picture.name} — say who is in it (their banked masters) or that nobody of ours is")
    missing = [m for m in masters if not Path(m).is_file()]
    if missing:
        raise SystemExit(f"FACE GATE: {picture.name} — no master at {', '.join(missing)}")
    people = (check or _load("identity").check)(str(picture), masters) if masters else []
    ok = bool(no_people and not masters) or (bool(people) and all(p.get("verdict") in PASSES for p in people))
    rec = {"picture": picture.name, "sha": sha(picture), "no_people": bool(no_people and not masters),
           "people": people, "pass": ok, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    sidecar(picture).write_text(json.dumps(rec, indent=1))
    return rec


def refusal(picture, rec) -> str:
    bad = [p for p in rec.get("people") or [] if p.get("verdict") not in PASSES]
    who = "; ".join(f"{Path(p['master']).parent.name if Path(p['master']).parent.name != 'full' else Path(p['master']).parents[1].name}"
                    f" = {p.get('verdict')} ({str(p.get('why') or '')[:140]})" for p in bad)
    return (f"FACE GATE: {Path(picture).name} is refused — {who or 'no face confirmed'}. Remake the picture with that "
            f"person's banked master as the FIRST reference, then stamp it again; no clip is made from it before.")


def require(picture, masters=None, no_people: bool = False, check=None) -> dict:
    """The record of a picture that passed, checking it now if it has none; otherwise a refusal (SystemExit)."""
    rec = read(picture)
    if rec is None:
        rec = stamp(picture, masters or [], no_people=no_people, check=check)
    if not rec.get("pass"):
        raise SystemExit(refusal(picture, rec))
    return rec


def masters_for(run, people) -> list[str]:
    """Each named person's banked master, from the run's elements.json (the folders elements_check resolved)."""
    try:
        items = json.loads((Path(run) / "elements.json").read_text()).get("items") or []
    except (OSError, ValueError):
        return []
    ER = _load("element_refs")
    out = []
    for it in items:
        if it.get("kind") == "person" and it.get("id") in set(people or []) and it.get("folder"):
            m = ER.person_master(WS / it["folder"])
            if m:
                out.append(str(m))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stamp"); s.add_argument("picture"); s.add_argument("--master", action="append", default=[])
    s.add_argument("--no-people", action="store_true")
    w = sub.add_parser("show"); w.add_argument("picture")
    a = ap.parse_args(argv)
    if a.cmd == "show":
        print(json.dumps(read(a.picture), indent=1))
        return 0
    rec = stamp(a.picture, a.master, no_people=a.no_people)
    print(json.dumps(rec, indent=1))
    return 0 if rec["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
