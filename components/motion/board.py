#!/usr/bin/env python3
"""The motion chain on a board: every scene's stages and every clip's motion match, as check rows.

    python3 board.py <production dir>

rows(production) -> [{"group", "name", "ok", "short", "detail", "pics", "video"}]: the shape the Video Studio's Checks
panel draws (ok: true pass, false fail, null waiting). `pics` and `video` are files inside the production. It reads
only what the chain wrote (<scene>/motion/chain.json, match-*.json); it runs nothing and imports nothing else, so a
board can load this one file by path. No brand, product or person is named here.
"""
import json
import sys
from pathlib import Path


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def rows(production):
    B = Path(production)
    out = []
    for cj in sorted(B.glob("scenes/**/motion/chain.json")):
        d = cj.parent
        rel = str(d.parent.relative_to(B / "scenes"))
        for stage, s in ((_load(cj) or {}).get("stages") or {}).items():
            f = d / s["file"] if s.get("file") else None
            pics = [str(f)] if f and f.suffix in (".jpg", ".png") and f.exists() else []
            if stage == "preview" and (d / "preview.jpg").exists():
                pics = [str(d / "preview.jpg")]
            out.append({"group": "Motion chain", "name": "%s · %s" % (rel, s["name"]), "ok": s["ok"], "short": s["short"],
                        "detail": s.get("detail", ""), "pics": pics,
                        "video": str(f) if f and f.suffix == ".mp4" and f.exists() else None})
        for mf in sorted(d.glob("match-*.json")):
            m = _load(mf) or {}
            who = mf.stem.replace("match-", "")
            for r in m.get("rows") or []:
                out.append({"group": "Motion match · %s · %s" % (rel, who), "name": r["name"], "ok": r["ok"], "short": r["short"],
                            "detail": r.get("detail", ""), "pics": [], "video": None})
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(rows(sys.argv[1]), indent=1, ensure_ascii=False))
