#!/usr/bin/env python3
"""RETIRED 2026-10-27 (the owner: "make this name agnostic. and the name of the folders need to be the same for both repo
and drive"; "use the working folders, retire the old names"): no machine makes a folder named after a person. Work for a
role goes to Shared Assets/runs/handoffs/<role>/<brand>/<brief key>/ and comes back into its returned/ (tools/image-edit
handoff.py and delivery.py). seed_team() and the command refuse by name and make nothing; `retired_ok=True` runs the old
walk for its tests only. The old description follows.

Seed every team member's working folders on Shared Assets: team/<person>/
and one team/<person>/<station>/ per entry of the `stations` list in their
team/people/<person>/identity.json (LD-88 (team station folders), 2026-10-23).

    python3 -m gdrive_creator.seed_team [--dry-run]     # cwd components/gdrive-creator

A STATION IS A COMPONENT NAME. One that is not an existing components/<name>/
folder is refused by name and nothing is made for it; every other folder is
still processed. The top folder is `team`, never `people` (the team, 2026-10-23).

THE SURFACE
  seed_team(repo=None, svc=None, dry_run=False, find_engine=None, drive_root=None)
      -> [{"person", "station" (or None), "path": "team/<p>[/<s>]",
           "state": "made" | "already there" | "would make" | "refused",
           "why" (or None)}], one row per person folder and station folder,
      in walk order: people sorted by folder name, each person's folder
      first, then their stations in list order. "stations" absent = [].

THE WALK. From the Shared Assets root, one name at a time ("team", person[,
station]): the engine's find_file looks; a missing step is made with the
engine's `folder` (two looks before a create, scar 5) — unless dry_run, which
makes nothing and answers "would make". reach.folder_id(make=True) is the same
walk but cannot say which steps it made, so this walks itself. `team` is made
on the first walk that needs it and has no row of its own. "made" means the
look found no folder and `folder` ensured one — its own second look may find
one the search index had not caught up with, which is still one folder, never
two.

RE-RUNNABLE. A second run makes nothing: every row "already there".

**NOTHING HERE DELETES, TRASHES, MOVES OR RENAMES ANYTHING** — on the Drive or
on disk. The only Drive write is the engine's `folder` create; identity files
are read, never written. test_seed_team.py asserts it on the calls and the
source.

SEAMS. `find_engine` (a zero-arg callable answering the engine module; default
reach._engine) and `svc` (made from the engine only when a Drive call is
needed) — a test passes a fake engine. `drive_root` skips the Shared Assets
lookup. Stdlib only; Python 3.9. No brand, product or account is named here.
"""
import argparse
import json
import sys
from pathlib import Path

from . import reach

TEAM = "team"
RETIRED = ("seed_team is retired (the owner, 2026-10-27): no folder is named after a person. Work for a role lives at "
           "Shared Assets/runs/handoffs/<role>/<brand>/<brief key>/ and comes back into its returned/.")


class Retired(Exception):
    pass
STATES = ("made", "already there", "would make", "refused")
REPO = Path(__file__).resolve().parents[3]


def people(repo):
    """[(person, [station, ...])] from every team/people/*/identity.json, sorted
    by folder name; "stations" absent = []; a repeated station counts once."""
    out = []
    for f in sorted(Path(repo).joinpath("team", "people").glob("*/identity.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        stations = data.get("stations") or []
        if not isinstance(stations, list):
            raise ValueError(f"{f}: \"stations\" must be a list, got {type(stations).__name__}")
        seen = []
        for s in stations:
            if s not in seen:
                seen.append(s)
        out.append((f.parent.name, seen))
    return out


def _refusal(repo, station):
    """None when `station` names an existing components/<station>/ folder, else why not."""
    if not isinstance(station, str) or not station or "/" in station or "\\" in station \
            or station in (".", ".."):
        return f"not a component name: {station!r}"
    if not Path(repo).joinpath("components", station).is_dir():
        return f"not a component: components/{station}/ does not exist"
    return None


def seed_team(repo=None, svc=None, dry_run=False, find_engine=None, drive_root=None, retired_ok=False):
    """RETIRED: refuses (Retired) and makes nothing unless retired_ok. Was: ensure Shared Assets/team/<person>/ and
    each team/<person>/<station>/; one row per folder (see the module doc). Raises reach.NoDrive when no
    drive_root is given and this key sees no Shared Assets drive."""
    if not retired_ok:
        raise Retired(RETIRED)
    repo = Path(repo) if repo is not None else REPO
    E = (find_engine or reach._engine)()
    state = {"svc": svc, "root": drive_root}
    ids = {}                                    # (names...) -> id, or None when missing on a dry run

    def drive():
        if state["svc"] is None:
            state["svc"] = E.service()
        if state["root"] is None:
            state["root"] = reach.shared_assets_id(state["svc"])
            if state["root"] is None:
                raise reach.NoDrive(f"this key sees no shared drive named {reach.SHARED_DRIVE!r}")
        return state["svc"], state["root"]

    def ensure(names):
        """Walk to Shared Assets/<names>; the last step's state."""
        svc_, parent = drive()
        got = "already there"
        for i in range(len(names)):
            key = tuple(names[:i + 1])
            if key in ids:
                parent, got = ids[key], "already there"
            elif parent is None:                # a dry run below a missing step
                parent, got = None, "would make"
            else:
                hit = E.find_file(svc_, names[i], parent, mime=E.FOLDER_MIME)
                if hit:
                    parent, got = hit["id"], "already there"
                elif dry_run:
                    parent, got = None, "would make"
                else:
                    parent, got = E.folder(names[i], parent, svc=svc_), "made"
            ids[key] = parent
        return got

    rows = []
    for person, stations in people(repo):
        for station in [None] + stations:
            names = [TEAM, person] + ([] if station is None else [station])
            path = "/".join(names)
            why = None if station is None else _refusal(repo, station)
            if why:
                rows.append({"person": person, "station": station, "path": path,
                             "state": "refused", "why": why})
                continue
            rows.append({"person": person, "station": station, "path": path,
                         "state": ensure(names), "why": None})
    return rows


def render(rows):
    """The CLI's lines: one per row, then the totals."""
    lines = []
    for r in rows:
        line = f"{r['state']}  {r['path']}"
        if r["why"]:
            line += f"  — {r['why']}"
        lines.append(line)
    n = {s: sum(1 for r in rows if r["state"] == s) for s in STATES}
    lines.append(" · ".join(f"{s} {n[s]}" for s in STATES))
    return lines


def main(argv=None, **seams):
    """CLI: retired, exit 3 and nothing made. Was: exit 0, or 2 when any row is refused, or 1 when there is no Drive."""
    ap = argparse.ArgumentParser(prog="python3 -m gdrive_creator.seed_team",
                                 description="Make Shared Assets/team/<person>/<station>/ "
                                             "for every team/people/*/identity.json.")
    ap.add_argument("--dry-run", action="store_true", help="look only; make nothing")
    a = ap.parse_args(argv)
    try:
        rows = seed_team(dry_run=a.dry_run, **seams)
    except Retired as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    except reach.NoDrive as e:
        print(f"NoDrive: {e}", file=sys.stderr)
        return 1
    for line in render(rows):
        print(line)
    return 2 if any(r["state"] == "refused" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
