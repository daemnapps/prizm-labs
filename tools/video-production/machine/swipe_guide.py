"""THE SWIPE GUIDE — the swipe shot a picture copies, kept SHARP, with every face
and every on-screen word covered (the owner, 2026-10-02: "literally look like the
swipe … this is what makes it indistinguishable from AI").

A blurred swipe shot carried the light but lost the shape: hands came from the
wrong edge, the camera drifted closer. Sharp, the picture door rebuilds the exact
frame — camera, distance, crop, posture, hands, room, light — and only the people
change. Faces are covered so no real person's face can be lifted; words are
covered so no caption is copied. Brand-agnostic: it reads only the frame map.

    python3 swipe_guide.py <shot.jpg> <out.jpg>

Faces and words are found by macOS Vision (`vision/faces.swift`, compiled once into
vision/.build/, git-ignored). With no Vision on the machine the whole frame is
blurred instead — never sent sharp with a face showing.
"""
from __future__ import annotations

import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE / "vision" / ".build" / "faces"   # built here, never outside the workspace (2026-09-23 rule)


def finder() -> Path | None:
    src = HERE / "vision" / "faces.swift"
    if BIN.is_file() and BIN.stat().st_mtime >= src.stat().st_mtime:
        return BIN
    try:
        BIN.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(BIN)], check=True, capture_output=True)
        return BIN
    except (OSError, subprocess.CalledProcessError):
        return None


def found(src: str | Path) -> list[tuple[str, float, float, float, float]] | None:
    b = finder()
    if b is None:
        return None
    r = subprocess.run([str(b), str(src)], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    rows = []
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) == 5:
            rows.append((p[0], *map(float, p[1:])))
    return rows


def make(src: str | Path, dst: str | Path) -> Path:
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.open(src).convert("RGB")
    W, H = im.size
    heavy = im.filter(ImageFilter.GaussianBlur(max(W, H) / 40))
    rows = found(src)
    if rows is None:                       # no Vision: never sharp with a face showing
        heavy.save(dst, quality=92)
        return Path(dst)
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    for k, x, y, w, h in rows:
        x, y, w, h = x * W, y * H, w * W, h * H
        if k == "face":
            # the whole HEAD, hair included: with only the face covered the door
            # kept the creator's hair and head shape and invented a new woman
            # around them (2026-10-02, round 3)
            d.ellipse([x - w * 0.75, y - h * 1.0, x + w * 1.75, y + h * 1.35], fill=255)
        else:
            # a caption is covered across the whole width: stylised words the
            # finder reads only in part still showed (2026-10-02, K01 sticker)
            d.rectangle([0, y - h * 0.9, W, y + h * 1.9], fill=255)
    Image.composite(heavy, im, mask.filter(ImageFilter.GaussianBlur(4))).save(dst, quality=92)
    return Path(dst)


if __name__ == "__main__":
    print(make(sys.argv[1], sys.argv[2]))
