"""The judge — a generated sheet, checked before it is banked.

**This writes no second judge.** The eyes, the judge prompt and the vision
model are `tools/image-production/image_production/judge.py`'s, asked
through its `seen()` — one judge for the system, one place a judge prompt is
versioned. What is this component's own is the QUESTIONS, because a character
sheet fails differently from an ad frame: it fails by being the baseline's
person, by being two people, or by drifting between the nine portraits.

**A judge that did not run HOLDS the picture** (image-production's rule,
verbatim reasoning from `finish.py`). The judge failing is not the picture
passing — a banked face is referenced by everything made after it, so an
unchecked one is the most expensive thing in the chain.

No brand, person or product is named in this file.
"""
import sys

from . import paths as P

# On every generated sheet, whatever the step.
STANDING = [
    "No third-party or competitor brand name, logo or wordmark is legible "
    "anywhere in the frame.",
    "Nothing is grossly broken — a limb attached wrongly, a face melted, a "
    "body with the wrong number of arms. Judge this the way a viewer scrolling "
    "past would. A partly hidden hand, a foreshortened grip, an odd-looking "
    "finger or a stylised illustration all PASS.",
    "There are NO words, letters, numbers, captions, labels, watermarks or "
    "user-interface elements rendered anywhere in the frame. FAIL if any "
    "legible text appears. Words that are part of a real object in the world — "
    "a sign on a wall behind the subject, a book's spine — PASS.",
    "The skin is unretouched: pores, follicles, small marks and natural "
    "asymmetry are visible. FAIL if it has been smoothed, beautified or "
    "airbrushed into something no camera would record.",
]

# THE ONE THAT MATTERS, and the reason this component has its own tests at
# all. The output is a DIFFERENT person; the baseline is a baseline, not a
# likeness (brands/<brand>/ai-cast/README.md, ruled 2026-09-14).
DIFFERENT = (
    "The person in this picture is a DIFFERENT person from the one in the "
    "reference the picture was made from — different face, different features, "
    "not the same individual. The room, the light, the framing and the wardrobe "
    "category carrying over is CORRECT and passes. FAIL only if the person "
    "could be mistaken for the person in the reference.")

ONE_PERSON = (
    "Exactly one person appears, and every appearance of them in this frame is "
    "the same person — the same face, the same hair, the same skin, the same "
    "wardrobe and the same accessories on the same side of the body.")

PER_STEP = {
    "master": [DIFFERENT, ONE_PERSON,
               "The room, the light and the camera register are the reference "
               "picture's, not a studio's — this frame has to cut against "
               "filmed footage without a visible change of world."],
    "anchor": [ONE_PERSON,
               "This is a character sheet: nine portraits of ONE person, evenly "
               "spaced on a plain neutral background, at a consistent camera "
               "distance and in consistent light. FAIL if the portraits are of "
               "people who are not clearly the same individual, or if the count "
               "or the layout is not a clean grid of nine.",
               "The identity is unchanged from the reference this sheet was "
               "made from: the same facial structure, the same hairline, the "
               "same skin tone, the same age, the same asymmetries. FAIL if it "
               "has been beautified, restyled or reinterpreted."],
    "detail": ["No face is in frame — this is the continuity board, and it is "
               "the part of the body the format leans on.",
               "The wardrobe, the skin tone and every accessory are the "
               "reference's, on the SAME side of the body as the reference has "
               "them. Handedness is the thing a generator flips without "
               "noticing, and this board is what everything later matches."],
}


def tests_for(step, req):
    tests = list(STANDING) + list(PER_STEP.get(step) or [])
    tests += list(req.get("checks") or [])
    return tests


def eyes():
    """image-production's judge. APPENDED to sys.path, never inserted at 0."""
    d = str(P.sibling("..", "tools", "image-production"))
    if d not in sys.path:
        sys.path.append(d)
    from image_production import judge as J
    from image_production import route as R
    return J, R


def verdict(step, picture, req, caller=None, entry=None):
    """One sheet's verdict — `{step, file, verdict, fails, checks_run, raw}`.

    `caller(prompt, image_path, entry) -> str` is the seam; tests pass a stub
    and nothing here opens a socket by itself.
    """
    tests = tests_for(step, req)
    try:
        J, R = eyes()
    except Exception as e:                       # noqa: BLE001
        return {"step": step, "file": str(picture), "verdict": "reject",
                "fails": ["the judge could not be loaded: %s: %s — a judge that "
                          "does not run holds the picture" % (type(e).__name__, e)],
                "checks_run": tests, "judge_model": None, "raw": ""}
    e = entry if entry is not None else R.judge_entry()
    fails, raw = J.seen(picture, tests, e, caller)
    return {"step": step, "file": str(picture),
            "verdict": "reject" if fails else "pass", "fails": fails,
            "checks_run": tests, "judge_model": (e or {}).get("vendor_model"),
            "raw": raw}


def why_md(step, fails, raw=""):
    """The reject note. A kill is a work item, not a verdict: fix the prompt,
    never the picture."""
    out = ["# %s — held" % step, ""]
    out += ["- %s" % f for f in fails]
    out += ["", "Every one of these is a prompt to fix, not a picture to patch.",
            "", "A held sheet is NOT filed into the brand's cast folder, and no "
            "later step references it.", ""]
    if raw:
        out += ["<details><summary>judge, raw</summary>", "", "```",
                str(raw).strip(), "```", "</details>", ""]
    return "\n".join(out)
