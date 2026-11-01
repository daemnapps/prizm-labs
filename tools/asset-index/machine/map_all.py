#!/usr/bin/python3
"""map_all.py — a free mapping record for every picture and video the key reaches (LD-59 (image records), widened
2026-10-21 by the team's rule: "asset index should index everything that can be seen by keys (and only those) … the goal
is just to have the full mapping of all assets that components can use. Describing it can still be based on actual
use need").

    python3 machine/map_all.py --brand <brand> [--dry-run]

Walks Shared Assets/brands/<brand>/ through the key (shared_paths.key_walk: names and the Drive's own media
metadata, NOTHING downloaded, no model) and writes one record per file not yet recorded anywhere:

    runs/asset-index/<brand>/<collection>/<drive-id>/clip.json   kind image|video, described false
    runs/asset-index/<brand>/<collection>/map.json               the id, its label, md5 and size

<collection> is the first folder under brands/<brand>/. A file already recorded (any collection's map.json — the
described clips keep their breakdowns) is left as it is; a mapping record whose file moved gets its new label.
Run it again to map new uploads: that IS the re-walk. Where another component already describes a file (the
products index's best_for, the proof index, a design or intake record naming its Drive id) the record carries
`pointer` (that file) and `text` (its words), read with no model. Describing on use is LD-63 (describe on use).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shared_paths as SP  # noqa: E402

REPO = HERE.parents[2]
VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
WORD = re.compile(r"[a-z][a-z0-9]+")
NOISE = {"img", "dsc", "dji", "mov", "mp4", "jpg", "jpeg", "png", "webp", "heic", "copy", "final", "edit", "version",
         "brands", "shared", "assets"}
TEXT_FIELDS = ("best_for", "description", "alt", "caption", "what", "said", "problem", "note", "kind")
ID = re.compile(r"\b[0-9A-Za-z_-]{25,44}\b")


def words(label: str) -> list[str]:
    """The folder words plus the file name's words, normalised: "…/products/brilliance-face-scrub/IMG_1.jpg" →
    products, brilliance, face, scrub. Camera counters and extensions are dropped."""
    rest = label.split("/brands/", 1)[-1]
    rest = rest.split("/", 1)[-1] if "/" in rest else rest        # the brand itself is not a search word
    stem = rest.rsplit(".", 1)[0]
    out = []
    for w in WORD.findall(stem.lower().replace("_", " ")):
        if w in NOISE or w.isdigit() or re.fullmatch(r"\d+[a-z]?", w):
            continue
        if w not in out:
            out.append(w)
    return out


def collection_of(label: str) -> str:
    parts = label.split("/brands/", 1)[-1].split("/")
    return parts[1] if len(parts) > 2 else "_top"


def recorded_ids(brand: str, runs: Path) -> dict:
    """{drive id: record folder} for every record already under runs/asset-index/<brand>/."""
    out = {}
    for m in (runs / brand).glob("*/map.json"):
        try:
            for k in json.loads(m.read_text()):
                out.setdefault(k, m.parent / k)
        except (OSError, ValueError):
            continue
    return out


def _texts(obj, want: set, found: dict, where: str):
    """Walk a JSON value; a dict naming a wanted Drive id gives that id its first text field."""
    if isinstance(obj, dict):
        ids = {str(v) for v in obj.values() if isinstance(v, str) and v in want}
        for k in ("drive_id", "id", "file_id", "fileId"):
            if isinstance(obj.get(k), str) and obj[k] in want:
                ids.add(obj[k])
        for v in obj.values():
            if isinstance(v, str):
                for m in re.findall(r"/d/([0-9A-Za-z_-]{25,44})", v):
                    if m in want:
                        ids.add(m)
        if ids:
            text = next((str(obj[f]) for f in TEXT_FIELDS if isinstance(obj.get(f), str) and obj[f].strip()), "")
            for i in ids:
                found.setdefault(i, (where, text[:400]))
        for v in obj.values():
            _texts(v, want, found, where)
    elif isinstance(obj, list):
        for v in obj:
            _texts(v, want, found, where)


def pointers(brand: str, want: set, repo: Path = REPO) -> dict:
    """{drive id: (pointer path, text)} from records other components already made — the class (a) files.
    Read only, no model. Sources: the products index, the proof index, and image/email/intake/casting runs."""
    srcs = [repo / "brands" / brand / "products" / "DRIVE-INDEX.json",
            repo / "runs" / "asset-index" / brand / "proof" / "proof.json"]
    for top in ("image-production", "email-production", "intake", "casting", "image-teardown"):
        d = repo / "runs" / top / brand
        if d.is_dir():
            srcs += sorted(d.rglob("*.json"))[:20000]
    found: dict = {}
    for f in srcs:
        try:
            if f.stat().st_size > 20_000_000:
                continue
            raw = f.read_text(errors="ignore")
        except OSError:
            continue
        if not any(i in want for i in ID.findall(raw)):
            continue
        try:
            _texts(json.loads(raw), want, found, str(f.relative_to(repo)))
        except ValueError:
            continue
    return found


def record(f: dict, brand: str) -> dict:
    label = f["path"] if f["path"].startswith("Shared Assets/") else "Shared Assets/" + f["path"]
    kind = "video" if Path(f["name"]).suffix.lower() in VIDEO else "image"
    return {"clip_id": f["drive_id"], "drive_id": f["drive_id"], "label": label, "path": None,
            "filename": f["name"], "name": f["name"], "kind": kind, "described": False,
            "collection": collection_of(label), "bytes": f.get("bytes"), "md5": f.get("md5"),
            "meta": {"width": f.get("width"), "height": f.get("height"), "duration_s": f.get("duration_s"),
                     "size_mb": round(f["bytes"] / 1e6, 1) if f.get("bytes") else None},
            "created": f.get("created"), "modified": f.get("modified"),
            "words": words(label),
            "frames": [{"file": "frame_01.jpg", "at_s": 0}] if kind == "image" else [],
            "indexed_by": "map_all (LD-59 (image records))"}


def run(brand: str, files: list, runs: Path | None = None, dry: bool = False, repo: Path = REPO) -> dict:
    runs = Path(runs or SP.runs_root())
    have = recorded_ids(brand, runs)
    new = [f for f in files if f["drive_id"] not in have]
    moved = 0
    for f in files:                        # a mapping record whose file moved on the Drive gets its new label
        d = have.get(f["drive_id"])
        if d is None or not (d / "clip.json").is_file() or (d / "breakdown.json").is_file():
            continue
        try:
            c = json.loads((d / "clip.json").read_text())
        except ValueError:
            continue
        lab = f["path"] if f["path"].startswith("Shared Assets/") else "Shared Assets/" + f["path"]
        if c.get("described") is False and c.get("label") != lab:
            moved += 1
            if not dry:
                c.update({"label": lab, "words": words(lab)})
                (d / "clip.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    ptr = pointers(brand, {f["drive_id"] for f in new}, repo) if new else {}
    per = {}
    for f in new:
        r = record(f, brand)
        if f["drive_id"] in ptr:
            r["pointer"], r["text"] = ptr[f["drive_id"]]
        per.setdefault(r["collection"], []).append(r)
    if not dry:
        for col, rows in per.items():
            cdir = runs / brand / col
            cdir.mkdir(parents=True, exist_ok=True)
            mf = cdir / "map.json"
            try:
                mp = json.loads(mf.read_text()) if mf.is_file() else {}
            except ValueError:
                mp = {}
            for r in rows:
                d = cdir / r["drive_id"]
                d.mkdir(exist_ok=True)
                (d / "clip.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
                mp[r["drive_id"]] = {"filename": r["name"], "indexed_by": r["indexed_by"], "label": r["label"],
                                     "md5": r["md5"], "old_id": None, "size": r["bytes"]}
            mf.write_text(json.dumps(mp, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    out = {"brand": brand, "walked": len(files), "already": len(files) - len(new), "new": len(new),
           "moved": moved, "with_pointer": sum(1 for f in new if f["drive_id"] in ptr),
           "by_collection": {c: len(v) for c, v in sorted(per.items())},
           "by_kind": {k: sum(1 for v in per.values() for r in v if r["kind"] == k) for k in ("image", "video")}}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--dry-run", dest="dry", action="store_true", help="say what would be written; write nothing")
    a = ap.parse_args(argv)
    res = run(a.brand, SP.key_walk(a.brand), dry=a.dry)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
