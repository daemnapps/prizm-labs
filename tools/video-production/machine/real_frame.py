"""THE REAL FRAME — a shot of the product in use starts from a REAL frame of a real person using it (the
usage bank, product_usage.py), and only the person and the room are changed to the ad's own cast and set
(2026-10-09, the owner, after a pasted product read as a sticker: the grip, the light on the product and the way
it meets the skin have to be real). The product's own pixels are put back from the real frame after the edit,
so the product is never drawn and never pasted from another photo.

  source   the usage frame closest to the scene, read at full resolution from the original clip
  frame    cropped to the still's 2:3 around the product
  keep     the product's pixels (SAM, the box the vision model finds) — the edit may change everything else
  edit     the ruled stills door: image 1 the real frame (with the mask), then the cast master and the set plate
  restore  the real product's pixels laid back over the result, feathered

    python3 real_frame.py <run folder> <item id> --scene "<what the scene does>" --cast <cast master> \
        [--set <set plate>] [--usage <usage frame name>] [--prompt "<the scene's own words>"]

Brand-agnostic: the kit, the cast and the set come from the caller.
"""
from __future__ import annotations

import argparse, json, shutil, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _footage_local(ref):
    """A footage "Shared Assets/…" label (or an old mount path) as a file to open — asset-index
    shared_paths.local(), through the key (LD-56 (footage index in git))."""
    import importlib.util as _u
    f = Path(__file__).resolve().parents[2] / "asset-index" / "machine" / "shared_paths.py"
    sp = _u.spec_from_file_location("asset_index_shared_paths", str(f)); m = _u.module_from_spec(sp); sp.loader.exec_module(m)
    return m.local(ref)


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py"); m = u.module_from_spec(sp); sp.loader.exec_module(m); return m


def full_frame(row: dict, kit: Path, folder: Path) -> Path:
    """The usage frame at the clip's own resolution (the bank keeps a proxy-sized one)."""
    out = folder / f"full-{Path(row['file']).name}"
    src = row.get("shared_path")
    if src and not Path(src).exists():
        src = _footage_local(src)             # a "Shared Assets/…" label, read through the key (LD-56)
    if not out.exists() and src and Path(src).exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{float(row['at']):.2f}", "-i", src, "-frames:v", "1",
                        "-q:v", "2", str(out)], capture_output=True)
    return out if out.exists() else kit / row["file"]


def crop_23(img, box, W, H):
    """A 2:3 crop of the frame around the product box (0–1), as large as the frame allows."""
    cx = (box[0] + box[2]) / 2 * W
    cy = (box[1] + box[3]) / 2 * H
    if W / H > 2 / 3:
        ch, cw = H, H * 2 / 3
    else:
        cw, ch = W, W * 3 / 2
    left = min(max(cx - cw / 2, 0), W - cw)
    top = min(max(cy - ch / 2, 0), H - ch)
    return (int(left), int(top), int(left + cw), int(top + ch))


def make(run: Path, iid: str, scene: str, cast: Path, set_plate: Path | None, kit: Path, usage: str | None = None,
         words: str = "", what: str = "the product", log=print) -> dict:
    from PIL import Image, ImageFilter
    PU, PK, PC, DO = _load("product_usage"), _load("product_kit"), _load("product_check"), _load("direct_openai")
    idx = json.loads((kit / "usage" / "index.json").read_text())["frames"]
    if usage:
        row = idx[usage]
    else:
        pick = PU.pick(kit, scene)
        row = next(r for r in idx.values() if Path(r["file"]).name == Path(pick).name)
    work = run / "media" / "versions" / "real-frame"
    work.mkdir(parents=True, exist_ok=True)
    src = full_frame(row, kit, work)
    im = Image.open(src).convert("RGB")
    W, H = im.size
    f = PK.detect(str(src), what)
    box = crop_23(im, f["box"], W, H)
    frame = im.crop(box).resize((1024, 1536), Image.LANCZOS)
    fp = work / f"{iid}-source.png"
    frame.save(fp)
    f2 = PK.detect(str(fp), what)
    keep = PC.product_mask(fp, f2["box"]).resize(frame.size)
    keep = keep.filter(ImageFilter.MaxFilter(5))
    # the edit's mask: opaque = keep (the product), transparent = may change
    m = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    m.putalpha(keep)
    mp = work / f"{iid}-mask.png"
    m.save(mp)
    prompt = ("Image 1 is a real photo of a man using the product. Keep EXACTLY: the pose, the hand, how the hand grips "
              "the product, where it touches the skin, the camera angle, framing and light. Change ONLY who he is: he is "
              "the man in image 2 — his face, skin tone, hair, beard and body"
              + (", and the room becomes the place in image 3, seen from the same angle" if set_plate else "")
              + ". The product (the masked area) is not touched. " + (words or "") +
              " Real phone footage look, natural skin texture, no retouching, no words anywhere.")
    out = run / "media" / f"{iid}.png"
    if out.exists():
        shutil.copy2(out, work / f"{iid}-before-real-frame.png")
    refs = [fp, Path(cast)] + ([Path(set_plate)] if set_plate else [])
    res = DO.generate(prompt, refs, out, mask=mp)
    # restore the real product's pixels exactly
    got = Image.open(out).convert("RGB").resize(frame.size)
    soft = keep.filter(ImageFilter.GaussianBlur(1.5))
    got.paste(frame, (0, 0), soft)
    got.save(out)
    log(f"  {iid}: real frame {Path(row['file']).name} ({row.get('contact')}, {row.get('camera')}) → our cast, real product kept")
    return {"file": str(out), "usage": Path(row["file"]).name, "source": str(fp), "model": res.get("model")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("iid")
    ap.add_argument("--scene", default=""); ap.add_argument("--cast", required=True); ap.add_argument("--set")
    ap.add_argument("--kit", required=True); ap.add_argument("--usage"); ap.add_argument("--prompt", default="")
    ap.add_argument("--what", default="the product")
    x = ap.parse_args()
    print(json.dumps(make(Path(x.run), x.iid, x.scene, Path(x.cast), Path(x.set) if x.set else None, Path(x.kit),
                          x.usage, x.prompt, x.what), indent=1))
