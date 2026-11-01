#!/usr/bin/env python3
"""A tracked Drive move: one file goes to another Shared Assets folder by changing its parent — the
Drive id kept, nothing copied — and every move leaves ONE drive-move record, so anyone can ask
"where did my X go" (LD-89 (tracked Drive moves), 2026-10-23; the team, ~04:25Z: "since the move is by
machine anwayys, it should be fully tracked").

    from gdrive_creator.move import move, MoveRefused
    got = move(file_id, ["team", "<person>", "<station>"], by="<person>", why="<one line>")
                                   # -> {"drive_id", "name", "from", "to", "record"}

THE ONE CALL
  move(file_id, to_parts, by, why, svc=None, find_engine=None, record_root=None)
    1 files().get the file (id, name, parents, driveId); refused when the key cannot see it, when it
      has more than one parent (or none), or when it is not on Shared Assets
    2 to_parts checked: a list of folder names under Shared Assets, none empty, "." or ".." and none
      holding "/"; else refused
    3 the from-label: the old parent's names walked up to the drive root
    4 the target folder: reach.folder_id(to_parts, make=True) — missing steps made, never outside
      Shared Assets because the walk starts at its root; the file already there is refused
    5 ONE files().update(addParents=<target>, removeParents=<old parent>, supportsAllDrives=True)
    6 ONE record at <record_root>/platform/data/records/drive-move/<UTC stamp>--<by>--<drive_id>.json
      (kind manifest platform/data/kinds/drive-move.json), never over an earlier one (-2, -3, …)
  Every refusal is MoveRefused, raised before any folder is made or anything is changed. A Drive
  failure on the update itself (a key below Content manager cannot move) propagates as the client
  raised it, and no record is written.

NO DELETE, NO TRASH, NO RENAME — a wall, not a default. The update carries only the two parent
changes: no body, no name, no trashed flag. This module and the move test are the only places in
gdrive-creator that change a parent; test_reach.py asserts it on the source.

Stdlib only at import. Python 3.9. No brand, product, person or account is named in this file.
"""
import datetime as dt
import json
from pathlib import Path

from . import reach
from .refs import _repo

KIND = "drive-move"
VIA = "gdrive-creator/move"
MAX_DEPTH = 100                     # the from-label walk stops here; a deeper tree is not expected


class MoveRefused(Exception):
    """A move that was not made. The message says why; nothing was changed on the Drive."""


def _get(svc, fid, fields):
    return svc.files().get(fileId=fid, fields=fields, supportsAllDrives=True).execute()


def _from_label(svc, parent, root):
    """"Shared Assets/…" for a folder id: its names walked up through parents to the drive root."""
    names, cur = [], parent
    for _ in range(MAX_DEPTH):
        if cur == root:
            return reach._label(list(reversed(names)))
        node = _get(svc, cur, "id,name,parents")
        names.append(node.get("name") or cur)
        ups = node.get("parents") or []
        if not ups:
            break
        cur = ups[0]
    return reach._label(list(reversed(names)))


def _check_parts(to_parts):
    if isinstance(to_parts, (str, bytes)) or not isinstance(to_parts, (list, tuple)):
        raise MoveRefused("to_parts must be a list of folder names under %s, got %r"
                          % (reach.SHARED_DRIVE, to_parts))
    for p in to_parts:
        if not isinstance(p, str) or p in ("", ".", "..") or "/" in p:
            raise MoveRefused("target outside %s: %r is not one folder name (in %r)"
                              % (reach.SHARED_DRIVE, p, list(to_parts)))
    return list(to_parts)


def _record(root, verdict, who, drive_id, now):
    out = Path(root) / "platform" / "data" / "records" / KIND
    out.mkdir(parents=True, exist_ok=True)
    stem = "%s--%s--%s" % (now.strftime("%Y%m%dT%H%M%SZ"), who, drive_id)
    f, k = out / (stem + ".json"), 2
    while f.exists():                                       # one record per move, never over an earlier one
        f, k = out / ("%s-%d.json" % (stem, k)), k + 1
    f.write_text(json.dumps({"schema": 1, "kind": KIND, "reviewer": who, "item": drive_id,
                             "verdict": verdict, "created": verdict["at"], "via": VIA},
                            indent=1, ensure_ascii=False) + "\n")
    return f


def move(file_id, to_parts, by, why, svc=None, find_engine=None, record_root=None):
    """Move one Shared Assets file to Shared Assets/<to_parts…> by changing its parent; the Drive id
    is kept. Returns {"drive_id", "name", "from", "to", "record"} — both labels "Shared Assets/…",
    record the path of the drive-move record written. MoveRefused names why when it is not made."""
    E = (find_engine or reach._engine)()
    svc = svc or E.service()
    sa = reach.shared_assets_id(svc)
    if sa is None:
        raise MoveRefused("this key sees no shared drive named %r" % reach.SHARED_DRIVE)
    try:
        f = _get(svc, file_id, "id,name,parents,driveId")
    except Exception as e:
        raise MoveRefused("%s: this key cannot see that file (%s: %s)"
                          % (file_id, type(e).__name__, e))
    name, parents = f.get("name"), list(f.get("parents") or [])
    if len(parents) != 1:
        raise MoveRefused("%s (%s): has %d parents, a move needs exactly one"
                          % (file_id, name, len(parents)))
    if f.get("driveId") != sa:
        raise MoveRefused("%s (%s): not on %s (drive %s)"
                          % (file_id, name, reach.SHARED_DRIVE, f.get("driveId")))
    parts = _check_parts(to_parts)
    old = parents[0]
    frm = _from_label(svc, old, sa)
    to = reach._label(parts)
    target = reach.folder_id(parts, svc, make=True, find_engine=lambda: E)
    if target == old:
        raise MoveRefused("%s (%s): already in %s" % (file_id, name, to))
    svc.files().update(fileId=file_id, addParents=target, removeParents=old,
                       supportsAllDrives=True, fields="id,name,parents").execute()
    who = str(by or "unknown").strip().lower()
    now = dt.datetime.now(dt.timezone.utc)
    verdict = {"drive_id": file_id, "name": name, "from": frm, "to": to, "by": who, "why": why,
               "at": now.isoformat(timespec="seconds").replace("+00:00", "Z")}
    rec = _record(record_root or _repo(), verdict, who, file_id, now)
    return {"drive_id": file_id, "name": name, "from": frm, "to": to, "record": str(rec)}
