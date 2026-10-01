#!/usr/bin/env python3
"""Bring every concept up to three variations. Higgsfield only.

    make_variations.py prepare --jobs jobs.json --out <dir>
    make_variations.py ingest  --out <dir> --results results.json

A variation is the approved render with one thing changed: same man, same
layout, same words, same bar, different shot. So it is an edit, not a fresh
generation — the words survive because they were never re-typed.

**The pictures are made on Higgsfield. Nothing else.** Damon, 2026-09-11:
"remove fal from any workflow here... just higgsfield only."

Higgsfield's image models are reached through its MCP, which a script cannot
call. So this runs in two halves and a session drives the middle:

    prepare   crops each source to its bandless 4:5 and writes refs.json
    (session) media_upload the refs, then generate_image_batch with
              nano_banana_pro, role image_references, aspect 4:5
    ingest    downloads the results, pads to 9:16, checks the bands

Two rules from PIPELINE.md are load-bearing and both were learned the hard
way:

  §4a  The reference is the BANDLESS 4:5, never the padded 9:16. Feed the
       finished file back and the model reads the ink bands as picture,
       shrinks everything to fit, and adds fresh bands around it.

  §4   The change is one thing. The brief line says what moves.

And one learned on 2026-09-11: the change has to move what is HAPPENING in
the frame, not the camera. Sixteen of the first 110 came back as renders a
perceptual hash could not separate, every one of them from a brief that only
asked for different light or a tighter crop.
"""
import argparse, json, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pad

MODEL = "nano_banana_pro"
ROLE = "image_references"
ASPECT = "4:5"

# The model will happily re-draw the type it sees, and re-drawn type is
# almost-right type: a letter off, a bar a shade lighter, a guarantee that no
# longer matches the one legal signed off. Say it plainly and say it twice.
HOLD = (" Keep every word, letter, number and typographic mark exactly as it "
        "appears, in the same place, the same size, the same colour. Keep the "
        "solid bar and its text untouched. Do not re-draw, re-letter, re-flow "
        "or translate any text. Change only the photograph behind it. Add no "
        "new text: no extra caption, thought bubble, label, sticker, badge or "
        "line of copy that is not already in the reference. The words are "
        "signed off; an invented one is a claim nobody approved.")

# Asked to put the product somewhere new, the model adds one rather than moving
# the one it has — the first Higgsfield probe came back with the device in
# Beto's hand AND a second on the counter AND an unbranded serum bottle nobody
# sells. One device, the one already there, and nothing else on the shelf.
# The failure mode, every time, is DUPLICATION. Asked to move something, the
# model adds a copy instead: a second device on the counter, the crossed-out
# list printed twice, the man standing beside his own reflection. Three of the
# first four validation renders failed this way on 2026-09-11. Say "exactly
# one" about every element, and say what a mirror is.
ONE_OF_EVERYTHING = (
    " Exactly one man appears, the one in the reference — same face, same age, "
    "same build. A mirror shows HIS REFLECTION, not a second person. Exactly "
    "one face-brush device appears, the one in the reference, same shape, "
    "colour and finish: never two. Every piece of artwork, lettering, list or "
    "panel appears exactly once and is never reprinted, framed, or repeated "
    "elsewhere in the picture. Add no bottle, tube, jar, pump or package that "
    "is not already there, and no razor, shaver, trimmer or grooming product "
    "of any other brand.")

# The standing device rule (queue.py DEVICE): bristles against skin means the
# camera sees the smooth back. Bristles facing the lens while the pod is on
# the face is the single most common way these come back wrong.
DEVICE = (
    " If the device is pressed against the face or neck, the BRISTLE side is "
    "the side touching the skin, so the camera sees the smooth matte back of "
    "the pod with the hand over it and the bristles are hidden against the "
    "skin. Bristles facing the camera while the pod is on the skin is wrong.")


def tag(j):
    return f"{j['talent']}-{j['concept']}-{j['slot']}"


def prepare(jobs, out):
    """Bandless 4:5 references, and the prompt each one goes up with."""
    from PIL import Image
    out.mkdir(parents=True, exist_ok=True)
    refs = []
    for j in jobs:
        src = Path(j["src_path"])
        if not src.is_file():
            print(f"  {tag(j)}: source missing — {src}")
            continue
        dst = out / f"ref-{tag(j)}.png"
        pad.content_4x5(Image.open(src).convert("RGB")).save(dst, "PNG")
        refs.append({"tag": tag(j), "ref": str(dst), "prompt": j["change"] + HOLD + ONE_OF_EVERYTHING + DEVICE,
                     "model": MODEL, "role": ROLE, "aspect_ratio": ASPECT,
                     "from": j["ref_ad"], "headline": j["headline"]})
    (out / "refs.json").write_text(json.dumps(refs, indent=1))
    print(f"{len(refs)} references -> {out / 'refs.json'}")
    return refs


def ingest(out, results):
    """Download what Higgsfield made, pad each to 9:16, report."""
    out.mkdir(parents=True, exist_ok=True)
    made = {}
    for tg, url in results.items():
        raw = out / f"{tg}.png"
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                raw.write_bytes(r.read())
        except Exception as e:
            made[tg] = {"ok": False, "why": f"download failed: {type(e).__name__}"}
            continue
        padded = out / f"{tg}-9x16.png"
        try:
            pad.pad(raw, padded)
            ok = pad.solid(padded)
            made[tg] = {"ok": ok, "file": str(padded),
                        "why": "ok" if ok else "band is not solid — smeared pad"}
        except SystemExit as e:
            made[tg] = {"ok": False, "why": str(e)}
    (out / "made.json").write_text(json.dumps(made, indent=1))
    good = sum(1 for v in made.values() if v["ok"])
    print(f"{good} padded clean, {len(made) - good} to look at -> {out}")
    for k, v in made.items():
        if not v["ok"]:
            print(f"   {k}: {v['why']}")
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prepare", "ingest"])
    ap.add_argument("--jobs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--results", help="ingest: {tag: url} from the Higgsfield jobs")
    a = ap.parse_args()
    out = Path(a.out)
    if a.step == "prepare":
        prepare(json.loads(Path(a.jobs).read_text()), out)
    else:
        ingest(out, json.loads(Path(a.results).read_text()))


if __name__ == "__main__":
    main()
