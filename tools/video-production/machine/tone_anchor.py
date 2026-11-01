"""ONE TONE FOR THE WHOLE AD (P69, 2026-10-21 — the owner on the first fixed sheet: the cast member's skin and shirt
changed tone from picture to picture). Every start picture of a run is colour-matched to ONE anchor frame: the frame whose
person reads closest to the cast master (skin), so the person's skin and clothes hold one tone from the first frame to the
last. Only the grade moves — one linear gain and offset per channel, measured on the person (face + shirt), applied to
the whole picture; nothing in the picture is redrawn.

    python3 machine/tone_anchor.py <run> [--master <cast master.jpg>] [--dry-run]

run_v2 runs it after the pictures (and the swipe's look) and before the review. Originals are kept as
media/versions/<id>-before-tone.png; <run>/tone-anchor.json says which frame anchored and how far each moved.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STRENGTH = 0.85            # how far each frame moves toward the anchor (1.0 = all the way)
FRAMES = ("-F1", "-FLAST", "-F2")


def _load(name: str):
    import importlib.util as u
    sp = u.spec_from_file_location(f"vm_ta_{name}", HERE / f"{name}.py")
    m = u.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _sha(p: Path) -> str:
    import hashlib
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def face_box(pic: Path, faces=None) -> tuple | None:
    """(x, y, w, h) 0-1, top-left origin, of the largest face, or None."""
    faces = faces or _load("clip_qc").faces
    with tempfile.TemporaryDirectory() as t:
        shutil.copy2(pic, Path(t) / Path(pic).name)
        rows = faces(t)
    if not rows:
        return None
    # the PERSON: a face with a shirt under it in the picture wins over a bigger face without one (S1's half-face
    # model is the largest face in its frame and has no body)
    f = max(rows, key=lambda r: (r["y"] + r["h"] * 2.0 <= 1.0, r["w"] * r["h"]))
    return f["x"], f["y"], f["w"], f["h"]


def regions(img, box) -> dict:
    """The person's skin (the middle of the face) and shirt (the chest under the face) as pixel boxes."""
    W, H = img.size
    x, y, w, h = box
    skin = (x + w * 0.25, y + h * 0.35, x + w * 0.75, y + h * 0.85)
    shirt = (x - w * 0.2, y + h * 1.35, x + w * 1.2, y + h * 2.2)
    clamp = lambda b: (int(max(0, b[0]) * W), int(max(0, b[1]) * H), int(min(1, b[2]) * W), int(min(1, b[3]) * H))
    return {"skin": clamp(skin), "shirt": clamp(shirt)}


def stats(img, box) -> list:
    """[(mean, std)] per RGB channel inside a pixel box."""
    from PIL import ImageStat
    crop = img.convert("RGB").crop(box)
    st = ImageStat.Stat(crop)
    return [(st.mean[c], max(1.0, st.stddev[c])) for c in range(3)]


def person(img, box) -> dict:
    r = regions(img, box)
    return {k: stats(img, b) for k, b in r.items() if b[2] > b[0] + 4 and b[3] > b[1] + 4}


def distance(a: list, b: list) -> float:
    return sum((x[0] - y[0]) ** 2 for x, y in zip(a, b)) ** 0.5


def choose_anchor(people: dict, master: dict | None) -> str:
    """The frame whose skin is closest to the cast master's; with no master, the one closest to the others' middle."""
    # a frame counts only when the face found is the PERSON (a shirt under it) — S1's half-face model is not her
    have = {k: v for k, v in people.items() if v.get("skin") and v.get("shirt")}
    if not have:
        return next(iter(people))
    if master and master.get("skin"):
        return min(have, key=lambda k: (distance(have[k]["skin"], master["skin"]), k))
    mid = [sorted(v["skin"][c][0] for v in have.values())[len(have) // 2] for c in range(3)]
    return min(have, key=lambda k: (sum((have[k]["skin"][c][0] - mid[c]) ** 2 for c in range(3)), k))


def gains(src: dict, ref: dict) -> list:
    """Per channel (gain, 0): the source person's SKIN brought onto the anchor's — one multiplicative gain per
    channel, so a yellow or orange cast and an exposure step both go and the shirt moves with them. Held to
    0.8–1.25: a grade, never a repaint."""
    return [(max(0.8, min(1.25, ref["skin"][c][0] / max(1.0, src["skin"][c][0]))), 0.0) for c in range(3)]


def apply(img, gn: list, strength: float = STRENGTH):
    lut = []
    for g, off in gn:
        g2, off2 = 1 + (g - 1) * strength, off * strength
        lut += [int(max(0, min(255, round(g2 * v + off2)))) for v in range(256)]
    return img.convert("RGB").point(lut)


def run(run_dir: Path, master: Path | None = None, dry: bool = False, faces=None) -> dict:
    from PIL import Image
    run_dir = Path(run_dir)
    media = run_dir / "media"
    pics = sorted(p for p in media.glob("*.png") if any(p.stem.endswith(s) for s in FRAMES))
    try:
        prev = json.loads((run_dir / "tone-anchor.json").read_text()).get("frames") or {}
    except (OSError, ValueError):
        prev = {}
    # each frame is measured UNGRADED: the kept original when the picture is still the one we graded, else itself
    source = {}
    for p in pics:
        keep = media / "versions" / f"{p.stem}-before-tone.png"
        graded = (prev.get(p.stem) or {}).get("graded_sha")
        source[p.stem] = keep if (keep.exists() and graded and _sha(p) == graded) else p
    people, boxes = {}, {}
    for p in pics:
        b = face_box(source[p.stem], faces)
        if b:
            with Image.open(source[p.stem]) as im:
                people[p.stem] = person(im, b)
                boxes[p.stem] = b
    if len(people) < 2:
        return {"skipped": "fewer than two frames with a face — nothing to hold to one tone"}
    m = None
    if master and Path(master).is_file():
        mb = face_box(Path(master), faces)
        if mb:
            with Image.open(master) as im:
                m = person(im, mb)
    anchor = choose_anchor(people, m)
    rec = {"anchor": anchor, "master": str(master) if master else None, "frames": {}}
    for stem, pp in people.items():
        if stem == anchor:
            if source[stem] != media / f"{stem}.png":
                shutil.copy2(source[stem], media / f"{stem}.png")      # the anchor is shown ungraded
            rec["frames"][stem] = {"moved": 0.0}
            continue
        if not pp.get("shirt"):
            rec["frames"][stem] = {"skipped": "the face found is not the person (no body under it) — not graded"}
            continue
        gn = gains(pp, people[anchor])
        rec["frames"][stem] = {"gains": [[round(g, 3), round(o, 1)] for g, o in gn],
                               "skin_before": round(distance(pp.get("skin") or [], people[anchor].get("skin") or []), 1)}
        if dry:
            continue
        f = media / f"{stem}.png"
        keep = media / "versions" / f"{stem}-before-tone.png"
        keep.parent.mkdir(parents=True, exist_ok=True)
        # the ungraded picture is kept once; a picture remade since the last pass (it no longer is the graded one we
        # wrote) is the new ungraded picture — never graded twice, never put back to an older picture
        if source[stem] == f:
            shutil.copy2(f, keep)
        with Image.open(keep) as im:
            out = apply(im, gn)
        out.save(f)
        rec["frames"][stem]["graded_sha"] = _sha(f)
    if not dry:
        (run_dir / "tone-anchor.json").write_text(json.dumps(rec, indent=1))
    return rec


def master_of(run_dir: Path) -> Path | None:
    """The lead's cast master, from the run's element sheet."""
    try:
        els = json.loads((Path(run_dir) / "elements.json").read_text())
    except (OSError, ValueError):
        return None
    ws = HERE.parents[2]
    for it in els.get("items") or []:
        if it.get("kind") == "person" and it.get("folder"):
            for n in ("master.jpg", "full/master.png", "master.png"):
                if (ws / it["folder"] / n).is_file():
                    return ws / it["folder"] / n
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run"); ap.add_argument("--master"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    master = Path(a.master) if a.master else master_of(Path(a.run))
    print(json.dumps(run(Path(a.run), master, a.dry_run), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
