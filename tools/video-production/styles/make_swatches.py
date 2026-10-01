#!/usr/bin/env python3
"""make_swatches.py — one picture per style: the SAME approved frame restyled
through the image door, so the only thing that differs between two swatches is
the style. Reads bank.json; writes swatches/<id>.jpg; skips any that exist.

    python3 styles/make_swatches.py --base <frame.png> [--only id,id] [--workers 4]

The instruction never describes what the base frame already shows
(frames-by-edit.md) — it names the rendering swap and nothing else. Swatches
are bank furniture, not ad frames: they run at medium quality."""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import direct_openai as door

_cfg = door.cfg
def _swatch_cfg():
    c = dict(_cfg()); c["params"] = {**(c.get("params") or {}), "quality": "medium"}; return c
door.cfg = _swatch_cfg

LOCK = ("Restyle this exact frame. Keep the framing, the pose, the room layout and every object exactly where it is. "
        "Change only the rendering — redraw everything in the frame, the person included, as: {formula}. No text, no captions, no logos.")

def one(row, base):
    out = HERE / row["swatch"]
    if out.exists(): return row["id"], "kept"
    png = out.with_suffix(".png")
    r = door.generate(LOCK.format(formula=row["formula"]), [base], png)
    if not r.get("file"): return row["id"], "FAILED"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(png), "-vf", "scale=512:-1", "-q:v", "4", str(out)], check=True)
    png.unlink()
    return row["id"], "made"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", required=True); ap.add_argument("--only"); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    rows = json.loads((HERE / "bank.json").read_text())["styles"]
    if a.only: rows = [r for r in rows if r["id"] in a.only.split(",")]
    with ThreadPoolExecutor(a.workers) as ex:
        for rid, state in ex.map(lambda r: _safe(r, Path(a.base)), rows): print(rid, state, flush=True)

def _safe(row, base):
    try: return one(row, base)
    except BaseException as e: return row["id"], f"FAILED {str(e)[:160]}"

if __name__ == "__main__": main()
