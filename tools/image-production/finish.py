#!/usr/bin/env python3
"""finish — any picture in, in any ratio; one 9:16 asset out, the picture untouched.

    python3 tools/image-production/finish.py <picture or folder> [--out <file or folder>] [--dry-run]

The whole picture is taped down inside the centred 4:5 safe zone of the 9:16
frame (the team notes/SAFE-ZONE.md) and only the backdrop around it is painted —
the scene continuing, nothing placed there. Nothing is cropped, nothing is
stretched, no bars (the owner, 2026-09-22; any ratio in, 2026-09-29).

- A FOLDER does every picture in it (not its subfolders); a picture already
  at 9:16 is left alone and said so.
- Without --out the 9:16 versions go in a `9x16/` folder beside the pictures,
  same file names. The originals are never written over.
- --dry-run spends nothing: prints each picture's ratio and what would happen.
- A `resize.json` in the out folder records every picture: before, after, the
  box the original sits in, or why it was skipped.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import image_production as IP  # noqa: E402
from image_production import providers  # noqa: E402

PICTURES = {".png", ".jpg", ".jpeg", ".webp"}


def ratio_name(w, h):
    for name, (a, b) in {"9:16": (9, 16), "4:5": (4, 5), "1:1": (1, 1), "2:3": (2, 3),
                         "3:4": (3, 4), "16:9": (16, 9), "3:2": (3, 2), "4:3": (4, 3)}.items():
        if abs(h / w - b / a) < 0.02:
            return name
    return f"{w}x{h}"


def plan(src, out):
    from PIL import Image
    pics = sorted(p for p in src.iterdir() if p.suffix.lower() in PICTURES) if src.is_dir() else [src]
    if src.is_dir():
        out_dir = Path(out) if out else src / "9x16"
        return [(p, out_dir / (p.stem + ".png")) for p in pics], out_dir
    target = Path(out) if out else src.parent / "9x16" / (src.stem + ".png")
    if target.suffix.lower() not in PICTURES:
        target = target / (src.stem + ".png")
    return [(src, target)], target.parent


def main():
    from PIL import Image
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("picture", help="a picture, or a folder of them")
    ap.add_argument("--out", help="file (one picture) or folder; default a 9x16/ folder beside")
    ap.add_argument("--dry-run", action="store_true", help="spend nothing; say what would happen")
    a = ap.parse_args()
    src = Path(a.picture).expanduser()
    jobs, out_dir = plan(src, a.out)
    record = []
    for pic, target in jobs:
        if target.resolve() == pic.resolve():
            raise SystemExit(f"{target} is the picture itself — the original is never written over")
        with Image.open(pic) as im:
            w, h = im.size
        row = {"picture": str(pic), "before": f"{w}x{h}", "ratio": ratio_name(w, h)}
        if providers.is_9x16(w, h):
            row["result"] = "already 9:16 — left alone"
        elif a.dry_run:
            row["result"] = f"would finish to 9:16 → {target}"
        else:
            r = IP.finish(pic, target)
            row.update(result="finished", after=str(target), size="1080x1920",
                       content_box=r["content_box"], sides_painted=r["sides_painted"],
                       request_id=r["request_id"])
        record.append(row)
        print(f"{row['ratio']:>9}  {pic.name}  —  {row['result']}")
    if not a.dry_run and any(r.get("after") for r in record):
        out_dir.mkdir(parents=True, exist_ok=True)
        log = out_dir / "resize.json"
        old = json.loads(log.read_text()) if log.exists() else []
        done = {r["picture"] for r in record}
        log.write_text(json.dumps([r for r in old if r["picture"] not in done] + record, indent=1) + "\n")
        print(f"record: {log}")


if __name__ == "__main__":
    main()
