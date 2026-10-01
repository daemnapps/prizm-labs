#!/usr/bin/env python3
"""Character board generator — the production bible, per character.

Damon's ruling (2026-08-31): every AI character gets a full board set —
who they are, what they wear, what they do, the unique elements that
make them THEM — so the character is truly represented end to end.

Every board is an image-EDIT chained off the character's CANONICAL
master (identity chaining — the character is never re-described fresh).

  python3 boards.py <character-dir> \
      --baseline-dir <the brand baseline boards dir> \
      --outfits "o1|o2|o3|o4" [--outfits2 "..."] \
      --context "scene one" [--context2 "scene two"] \
      [--only wardrobe,wardrobe2,expressions,hair,details,context,context2]

Every board is generated AGAINST THE BASELINE: the matching baseline
board rides along as IMAGE 2, layout only — grid, panel count, framing,
background treatment copied exactly; its subject ignored entirely.

Reads the identity block (first blockquote) from character.md and the
canonical master (master-sheet.png/webp). Writes boards/*.png into the
character dir. ~$0.04 per board.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sequence import (MODEL_STILL_EDIT, data_uri, fetch, key, media_urls,  # noqa: E402
                      shrunk, submit, wait)

REALISM = ("Visible fine skin texture with natural pores, no digital "
           "smoothing, no beauty filter, natural anatomy, unretouched "
           "commercial photography style, soft studio lighting.")
NEG = ("NO TEXT anywhere — no panel numbers, no labels, no captions — no readable signage, no grid lines or overlay lines on the image, no watermark, no logos, no "
      "frame borders, no duplicate inconsistent faces — the SAME person "
      "in every panel, not resembling any real celebrity or real "
      "content creator.")
LAYOUT = ("\nIMAGE 2 is a LAYOUT reference ONLY — copy its grid "
          "composition, panel count, aspect, framing and background "
          "treatment exactly; ignore its subject entirely, no trace of "
          "the person in IMAGE 2 may appear.")
BASELINE_MATCH = {"wardrobe": "wardrobe-01-everyday",
                  "wardrobe2": "wardrobe-02-elevated",
                  "expressions": "expressions", "hair": "hair",
                  "details": "details", "context": "context-ricefield-02",
                  "context2": "context-airplane"}

BOARDS = {
    "wardrobe": (
        "IMAGE 1 is the identity reference — keep the exact same person "
        "(face, hair, skin, age, build) in every panel.\n\n"
        "EXACTLY FOUR panels — no more, no fewer, NO printed numbers or labels. Wardrobe lineup, side by side, every panel FULL BODY head-to-toe STANDING (never seated, never cropped at the waist or thigh), full body head-to-toe, "
        "the SAME person standing in a neutral pose on a plain light studio "
        "background, one outfit per panel, in this order: {outfits}.\n\n"
        "{identity}\n\n" + REALISM + "\n" + NEG),
    "expressions": (
        "IMAGE 1 is the identity reference — keep the exact same person "
        "(face, hair, skin, age) in every panel.\n\n"
        "EXACTLY SIX panels — no more, no fewer, NO printed numbers or labels on any panel. Grid of chest-up portraits "
        "of the SAME person against a plain light wall in warm natural light: (1) facing camera with a "
        "warm easy smile, (2) three-quarter turn smiling softly, (3) full "
        "profile looking away, (4) selfie angle reaching toward the "
        "camera, (5) hand raised into her hair mid-laugh, (6) calm neutral "
        "looking straight into the lens.\n\n"
        "{identity}\n\n" + REALISM + "\n" + NEG),
    "hair": (
        "IMAGE 1 is the identity reference — keep the exact same person "
        "(face, skin, age) in every panel.\n\n"
        "EXACTLY FOUR panels in a two-by-two grid — no more, no fewer, NO "
        "printed numbers or labels. Chest-up portraits of the SAME person "
        "on a plain light background — the IDENTICAL face at the "
        "IDENTICAL age in every panel, the IDENTICAL natural hair color "
        "the identity describes (NEVER darker, browner, or younger). One "
        "hairstyle per panel, only these, in this order: {hair}.\n\n"
        "{identity}\n\n" + REALISM + "\n" + NEG),
    "details": (
        "IMAGE 1 is the identity reference — this is the SAME person's "
        "body in close-up; keep her exact skin tone, age and every "
        "distinguishing detail.\n\n"
        "EXACTLY FOUR panels — no more, no fewer. Grid of macro detail "
        "photographs of the SAME person, documentary style — every panel "
        "shows THIS person's own body at their exact age, never a younger "
        "stand-in, and no tattoos: (1) her hands in her lap holding a small "
        "object, every distinguishing mark visible, (2) her footwear and "
        "ankles, standing, (3) a tight close-up of the skin of her cheek "
        "and jaw in natural light, real texture, (4) her forearms resting "
        "together, their skin condition clearly visible.\n\n"
        "{identity}\n\n" + REALISM + "\n" + NEG),
    "context": (
        "IMAGE 1 is the identity reference — keep the exact same person "
        "(face, hair, skin, age, build).\n\n"
        "A single cinematic vertical photograph of the SAME person in "
        "their world: {context}\n\n"
        "{identity}\n\n" + REALISM + "\n" + NEG),
}
BOARDS["wardrobe2"] = BOARDS["wardrobe"]
BOARDS["context2"] = BOARDS["context"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chardir")
    ap.add_argument("--outfits", default="")
    ap.add_argument("--outfits2", default="")
    ap.add_argument("--hair", default="")
    ap.add_argument("--context", default="")
    ap.add_argument("--context2", default="")
    ap.add_argument("--baseline-dir", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cd = Path(a.chardir).resolve()
    text = (cd / "character.md").read_text()
    block = re.search(r"^> (.+?)(?=\n[^>]|\Z)", text, re.M | re.S)
    if not block:
        sys.exit("no identity blockquote in character.md")
    identity = re.sub(r"^> ?", "", block.group(0), flags=re.M).strip()
    master = next((cd / n for n in
                   ("master-sheet.png", "master-sheet.webp",
                    "master-portrait.webp") if (cd / n).exists()), None)
    if not master:
        sys.exit("no canonical master image found")
    only = [s.strip() for s in a.only.split(",") if s.strip()] or list(BOARDS)
    outfits = " · ".join(s.strip() for s in a.outfits.split("|") if s.strip())
    outfits2 = " · ".join(s.strip() for s in a.outfits2.split("|") if s.strip())
    k = key()
    ref = data_uri(shrunk(master))
    (cd / "boards").mkdir(exist_ok=True)
    hair = " · ".join(s.strip() for s in a.hair.split("|") if s.strip())
    vals = {"wardrobe": outfits, "wardrobe2": outfits2, "hair": hair,
            "context": a.context, "context2": a.context2}
    for name in only:
        if name in vals and not vals[name]:
            print(f"skip {name}: no input given")
            continue
        prompt = BOARDS[name].format(
            identity=identity, hair=hair,
            outfits=vals.get(name, outfits) if name.startswith("wardrobe") else outfits,
            context=vals.get(name, a.context))
        # LESSON (2026-08-31): passing the baseline board as an image
        # reference bleeds its SUBJECT into panels ("layout only" is not
        # obeyed reliably). The baseline's layout is enforced by the text
        # spec instead — panel counts and poses mirror it exactly.
        refs = [ref]
        size = ("portrait_16_9" if name.startswith("context")
                else "landscape_16_9")
        if a.dry_run:
            print(f"\n===== {cd.name} · {name} · {size} =====\n{prompt}")
            continue
        print(f"board {name}...", flush=True)
        try:
            res = wait(*submit(MODEL_STILL_EDIT, {
                "prompt": prompt, "image_urls": refs, "num_images": 1,
                "image_size": size}, k), k, name)
            dest = cd / "boards" / f"{name}.png"
            fetch(media_urls(res)[0], dest)
            print(f"  saved {dest}", flush=True)
        except Exception as e:
            print(f"  {name} FAILED: {str(e)[:160]} — redo later", flush=True)


if __name__ == "__main__":
    main()
