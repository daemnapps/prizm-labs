#!/usr/bin/env python3
"""swipe_look — a frame made by editing the swipe is given the swipe's own look back (the owner, 2026-10-20: "let's make
sure the lighting is proper and the quality literally matches the swipe as well").

    python3 swipe_look.py <production run> [--only S1-F1,S2-FLAST] [--dry-run]

For every still the run made by SWIPE EDIT (element-refs.json names its swipe frame first), in order:
  1. light and colour — each channel's level and contrast moved toward that swipe frame along a straight line
     (never a histogram remap);
  2. the swipe's key light — the face lifted by the swipe's own face-to-room brightness, feathered;
  3. the phone video's texture — taken down to the swipe's own width, softened to its softness, a little grain,
     one JPEG pass at the swipe's compression, then back up to the frame's size.
The original is kept as media/versions/<stem>-before-swipe-look.png; a frame already matched is skipped
(swipe-look.json in the run). Brand-agnostic; reads only the run and its teardown.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    import importlib.util as ilu
    sp = ilu.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    m = ilu.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def swipe_width(frame: Path) -> int:
    from PIL import Image
    return Image.open(frame).size[0]


def texture(img, width: int, grain: float = 2.0, quality: int = 65, soften: float = 0.5):
    """The phone-video texture: the swipe's width, its softness, a little grain, its compression, back to size.
    Tuned on the expert swipe (2026-10-20): edge energy 1304 on the swipe frame, 1623 after the colour match alone,
    ~1300 with soften 0.5 · grain 2 · JPEG 65."""
    from PIL import Image, ImageFilter, ImageChops
    w, h = img.size
    small = img.resize((width, round(h * width / w)), Image.LANCZOS)
    small = small.filter(ImageFilter.GaussianBlur(soften))
    noise = Image.effect_noise(small.size, grain).convert("RGB")
    # grain around zero: (pixel + noise − 128), clipped — effect_noise is centred on 128
    small = ImageChops.add(small, noise, scale=1.0, offset=-128)
    buf = io.BytesIO(); small.save(buf, "JPEG", quality=quality); buf.seek(0)
    return Image.open(buf).convert("RGB").resize((w, h), Image.LANCZOS)


def light_and_colour(img, ref, strength: float = 0.85):
    """Each channel's level and contrast moved toward the swipe frame's, as one straight line per channel (a smooth
    curve — never a histogram remap, which posterised a portrait into green blotches on the first try, 2026-10-20)."""
    from PIL import ImageStat
    r = ref.convert("RGB").resize(img.size)
    s, t = ImageStat.Stat(img), ImageStat.Stat(r)
    luts = []
    for c in range(3):
        m0, d0, m1, d1 = s.mean[c], max(s.stddev[c], 1e-3), t.mean[c], t.stddev[c]
        k = 1 + strength * (d1 / d0 - 1)
        m = m0 + strength * (m1 - m0)
        luts += [max(0, min(255, round((v - m0) * k + m))) for v in range(256)]
    out = img.point(luts)
    # stretching each channel's contrast lifts the colour too: bring its saturation back to the swipe's
    from PIL import ImageEnhance
    s_now = ImageStat.Stat(out.convert("HSV")).mean[1]
    s_ref = ImageStat.Stat(r.convert("HSV")).mean[1]
    return ImageEnhance.Color(out).enhance(max(0.5, min(1.5, s_ref / max(s_now, 1e-3))))


def face_light(img, ref, box=None, strength: float = 0.8):
    """The swipe's key light: its face sits brighter than its room. The person's face (the frame's subject box, else
    the upper middle) is lifted by the swipe's own face-to-room difference, feathered so no edge shows."""
    from PIL import Image, ImageDraw, ImageFilter, ImageStat, ImageChops
    W, H = img.size

    def ratio(im, b):
        L = im.convert("L").resize((W, H))
        x0, y0, x1, y1 = [round(v) for v in (b[0] * W, b[1] * H, b[2] * W, b[3] * H)]
        inner = ImageStat.Stat(L.crop((x0, y0, x1, y1))).mean[0]
        return inner / max(ImageStat.Stat(L).mean[0], 1)
    if isinstance(box, dict) and "x_pct" in box:   # direct.json's subject_box: percents of the frame
        box = (box["x_pct"] / 100, box["y_pct"] / 100, (box["x_pct"] + box["w_pct"]) / 100,
               (box["y_pct"] + box["h_pct"]) / 100)
    face = box if isinstance(box, (list, tuple)) and len(box) == 4 else (0.3, 0.12, 0.7, 0.45)
    want = ratio(ref, (0.3, 0.12, 0.7, 0.45))
    have = ratio(img, face)
    gain = 1 + strength * max(0.0, want / max(have, 1e-3) - 1)
    if gain <= 1.01:
        return img
    mask = Image.new("L", (W, H), 0)
    x0, y0, x1, y1 = face[0] * W, face[1] * H, face[2] * W, face[3] * H
    ImageDraw.Draw(mask).ellipse((x0 - 0.1 * W, y0 - 0.05 * H, x1 + 0.1 * W, y1 + 0.08 * H), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(W * 0.08))
    bright = img.point(lambda v: min(255, round(v * gain)))
    return Image.composite(bright, img, mask)


def _sha(f) -> str:
    import hashlib
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def run(run_dir: Path, only=None, dry_run=False) -> list[str]:
    from PIL import Image

    refs = json.loads((run_dir / "element-refs.json").read_text()) if (run_dir / "element-refs.json").is_file() else {}
    direct = json.loads((run_dir / "direct.json").read_text()) if (run_dir / "direct.json").is_file() else {}
    rec_p = run_dir / "swipe-look.json"          # its own record: run.py rewrites direct.json from its own manifest
    rec = json.loads(rec_p.read_text()) if rec_p.is_file() else {}
    done = []
    for iid, rows in sorted(refs.items()):
        if not rows or not str(rows[0].get("what", "")).startswith("swipe frame"):
            continue
        sw = Path(rows[0]["file"])
        stems = [iid] + ([iid.replace("-F1", "-FLAST")] if iid.endswith("-F1") else [])
        for stem in stems:
            if only and stem not in only:
                continue
            f = run_dir / "media" / f"{stem}.png"
            if not f.is_file():
                continue
            # A REMADE PICTURE GETS ITS LOOK TOO (2026-10-24, the pastor barber's S4/S22A/S22B): the record is tied to the
            # bytes it wrote, so a picture remade since is new and is looked again — from ITS OWN bytes; the old
            # "before" copy is set aside, never used (it would have put the old picture back). A record from before
            # this (no sha) is redone only when the picture is named with --only.
            old = rec.get(stem)
            if old and (old.get("sha") == _sha(f) or (not old.get("sha") and not (only and stem in only))):
                continue
            if dry_run:
                done.append(f"[dry run] {stem} ← {sw.name}"); continue
            keep = run_dir / "media" / "versions" / f"{stem}-before-swipe-look.png"
            keep.parent.mkdir(parents=True, exist_ok=True)
            if old and keep.exists():
                n = 2
                while (keep.parent / f"{stem}-before-swipe-look-{n}.png").exists():
                    n += 1
                shutil.move(str(keep), keep.parent / f"{stem}-before-swipe-look-{n}.png")
            if not keep.exists():
                shutil.copy2(f, keep)
            ref = Image.open(sw)
            img = light_and_colour(Image.open(keep).convert("RGB"), ref)
            img = face_light(img, ref, (direct.get(stem) or {}).get("subject_box"))
            img = texture(img, swipe_width(sw))
            img.save(f)
            rec[stem] = {"from": str(sw), "kept": str(keep.relative_to(run_dir)), "sha": _sha(f)}
            done.append(f"{stem} ← {sw.name}")
    if not dry_run and done:
        rec_p.write_text(json.dumps(rec, indent=1))
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run"); ap.add_argument("--only"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    for line in run(Path(a.run), set(a.only.split(",")) if a.only else None, a.dry_run):
        print("swipe look:", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
