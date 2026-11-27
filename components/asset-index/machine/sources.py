#!/usr/bin/env python3
"""sources.py — where a brand's footage lives, and how to read seconds of any clip by range without syncing it.

A brand lists its footage roots in brands/<brand>/footage-library.json under "footage_roots", each a label prefix and
a reader:

    {"prefix": "Shared Assets/", "reader": "gdrive"}                               # the default when none are listed
    {"prefix": "<Library>/<Drive>/", "reader": "shade", "api": "<api base>", "drive_id": "<id>",
     "key": "<KEY NAME>", "origin": "SOURCE", "id_field": "shade_asset_id"}

    admitted(brand, label)        -> the root a record's label sits under, or None (search admits only these)
    base_label(label)             -> the label without an indexed piece's " @ m:ss" suffix (the file itself)
    offset(clip)                  -> seconds the indexed piece starts into the file (clip.json segment_start_s)
    ranged(brand, label, clip_id) -> (url, ffmpeg -headers value) to read seconds of the file by range, or None

The gdrive reader goes through the team's one Drive door (gdrive-creator engine.media_request). Other readers ask the
service for a short-lived link to the file and read it by range; keys come through the shared key loader by name.
Nothing here names a brand: every root, id and key name is the brand's own setting.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNS = Path(os.environ.get("ASSET_INDEX_RUNS") or (REPO / "runs" / "asset-index"))
BRANDS = Path(os.environ.get("ASSET_INDEX_BRANDS") or (REPO / "brands"))
DEFAULT = [{"prefix": "Shared Assets/", "reader": "gdrive"}]
PIECE = re.compile(r"\s+@\s+\d+:\d{2}(?::\d{2})?$")
_IDX: dict = {}
_LINK: dict = {}
LINK_S = 20 * 60          # a service's short-lived link is reused this long, then asked for again


def roots(brand: str) -> list:
    try:
        cfg = json.loads((BRANDS / brand / "footage-library.json").read_text())
    except (OSError, ValueError):
        cfg = {}
    return cfg.get("footage_roots") or DEFAULT


def admitted(brand: str, label: str | None) -> dict | None:
    s = str(label or "")
    for r in roots(brand):
        if s.startswith(r["prefix"]):
            return r
    return None


def base_label(label: str | None) -> str:
    return PIECE.sub("", str(label or ""))


def offset(clip: dict) -> float:
    try:
        return float(clip.get("segment_start_s") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _index(brand: str) -> dict:
    """base label -> the record's service id, for every record under a non-Drive root (read once per process)."""
    if brand not in _IDX:
        idx = {}
        for f in (RUNS / brand).glob("*/*/clip.json"):
            try:
                c = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            r = admitted(brand, c.get("label"))
            if r and r.get("reader") != "gdrive" and c.get(r.get("id_field") or "asset_id"):
                idx[base_label(c["label"])] = c[r.get("id_field") or "asset_id"]
        _IDX[brand] = idx
    return _IDX[brand]


def _key(name: str) -> str:
    sys.path.insert(0, str(REPO / "components" / "keys"))
    import loader  # noqa: E402  (the shared key loader: environment, then the key file)
    return loader.key(name)


def _shade(root: dict, asset_id: str) -> str:
    got = _LINK.get(asset_id)
    if got and time.time() - got[1] < LINK_S:
        return got[0]
    url = "%s/assets/%s/download?drive_id=%s&origin_type=%s" % (root["api"].rstrip("/"), asset_id, root["drive_id"],
                                                                 root.get("origin") or "SOURCE")
    req = urllib.request.Request(url, headers={"Authorization": _key(root["key"])})
    link = json.loads(urllib.request.urlopen(req, timeout=60).read())
    _LINK[asset_id] = (link, time.time())
    return link


def ranged(brand: str, label: str | None, clip_id: str | None = None) -> tuple | None:
    """(url, ffmpeg -headers value) to read seconds of a clip by range, or None when its root has no ranged reader
    here. gdrive needs the Drive id (clip_id); other readers find the id from the brand's records by label."""
    r = admitted(brand, label)
    if not r:
        return None
    if r.get("reader") == "gdrive":
        if not clip_id:
            return None
        root = REPO / "components" / "gdrive-creator"
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from gdrive_creator import engine as E
        return tuple(E.media_request(clip_id))
    if r.get("reader") == "shade":
        aid = clip_id if clip_id and clip_id in _index(brand).values() else _index(brand).get(base_label(label))
        return (_shade(r, aid), "") if aid else None
    return None


if __name__ == "__main__":
    b, lab = sys.argv[1], sys.argv[2]
    print(json.dumps({"root": admitted(b, lab), "ranged": bool(ranged(b, lab))}))
