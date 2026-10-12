"""The ONE prompting structure. Every picture, every caller, same skeleton.

The skeleton is a prompt FILE (`prompts/picture-vN-damon.md`), so a change to
how pictures are asked for is a change the owner can read — it is never a string
edited inside code. Highest `-vN-` wins, numerically, the same rule
`components/run-kit/run_kit/prompts.py` enforces (an alphabetical sort lets v2
beat v10).

Why slots rather than prose, in one line from the tool this was lifted out of:
a prompt written as prose has no parts, so re-rolling it rewrites the whole
paragraph and nothing in the system can tell you which of those you meant to
change (`tools/image-production/static/tools/prompt.py`).

The ORDER of the slots is the contract. A slot with nothing in it is dropped
entirely — never sent empty, never filled with a guess.
"""
import re
from pathlib import Path

from . import paths as P

VERSION = re.compile(r"-v(\d+)[-.]")
SLOT = re.compile(r"\{([a-z_]+)\}")

# The order the skeleton declares. Kept here as well so a skeleton that loses
# a slot is caught rather than silently dropping it.
ORDER = ("purpose_frame", "direction", "style", "format", "template", "product",
         "brand_ground", "references", "aspect_line", "standing_rules")

# the owner, 2026-09-14: "I want them to be 9:16, not 4x5 — the 4x5 is just for the
# contents to fit in there, but the full images should always be 9x16 so we can
# hit all placement." Emitted automatically for any purpose whose frame is
# cropped in feed, so a prompt cannot ask for the tall canvas without also
# saying which part of it survives the crop. Verbatim from prompt.py SAFE.
SAFE = (
    "COMPOSITION FOR CROPPING: this frame is {aspect} and will be cropped to a "
    "centred 4:5 window in feed, so the top 15% and the bottom 15% get cut "
    "off. Compose the whole picture for the tall frame — it must read "
    "complete at {aspect}, with real scene continuing top and bottom, never "
    "empty space and never a band. But every part that carries meaning — the "
    "subject's face, the eye line, the hands, the body part the proof is on, "
    "the product, and any words — sits inside the centred 4:5 window, "
    "comfortably clear of the top and bottom edges. Treat the outer 15% top "
    "and bottom as bleed: more of the same scene, nothing that must be seen.")

CONTENT_WINDOW = (
    "The frame is {gen}. This is the CONTENT of a {aspect} asset: the finished "
    "asset is made by continuing this picture's backdrop above and below it, "
    "with this picture untouched — so nothing here is ever cropped. Compose the "
    "whole picture for this {gen} frame, with every headline, badge, price, logo, "
    "face and the product comfortably clear of its top and bottom edges, never "
    "flush to them.")

EDIT_CLAUSE = (
    "Keep the attached picture exactly as it is — same people, same faces, "
    "same layout, same type, same colours, same composition. Change ONLY what "
    "the direction above asks for, and nothing else.")

NO_WORDS = "No words, letters, numbers or logos anywhere in the picture."


def latest(stage, folder=None):
    """The highest `-vN-` prompt file for a stage. Numeric, never alphabetical."""
    folder = Path(folder or P.prompts_dir())
    best, best_v = None, -1
    for f in sorted(folder.rglob(f"{stage}-*.md")):
        if "superseded" in f.parts:
            continue
        m = VERSION.search(f.name)
        v = int(m.group(1)) if m else 0
        if v > best_v:
            best, best_v = f, v
    if best is None:
        raise FileNotFoundError(f"no prompt file for `{stage}` in {folder}")
    return best


def body(path):
    """A prompt file is documentation above the `---` rule and the prompt
    below it, so the reasoning travels with the prompt without being sent."""
    text = Path(path).read_text()
    parts = re.split(r"^---\s*$", text, maxsplit=1, flags=re.M)
    return (parts[1] if len(parts) > 1 else parts[0]).strip()


def standing_rules(folder=None):
    """The rules on every picture, whatever it is for. Read from the file."""
    return body(latest("standing-rules", folder))


def slots(req, ctx, folder=None):
    """Every slot's value for one request. Nothing is invented: each value is
    either the caller's words, a row the element library returned, or a fact
    read from the brand."""
    purpose = ctx["purpose"]
    aspect = req["_aspect"]
    rows = ctx["elements"]["rows"]
    out = {k: "" for k in ORDER}

    out["purpose_frame"] = purpose.get("frame", "")
    out["direction"] = str(req.get("direction") or "").strip()

    if "style" in rows:
        r = rows["style"]
        out["style"] = f"HOW IT IS RENDERED ({r.get('name') or r['id']}): {r.get('what') or ''}".strip()
    if "format" in rows:
        r = rows["format"]
        out["format"] = f"THE SHAPE IT TAKES ({r.get('name') or r['id']}): {r.get('what') or ''}".strip()
    if "template" in rows:
        r = rows["template"]
        out["template"] = f"THE LAYOUT ({r.get('name') or r['id']}): {r.get('what') or ''}".strip()

    prod = ctx["product"]
    if prod.get("key"):
        line = f"THE PRODUCT: {prod.get('title') or prod['key']}."
        if prod.get("facts"):
            line += " What is true of it: " + prod["facts"]
        out["product"] = line

    ground = []
    if ctx.get("palette"):
        ground.append("The brand's colours, and no others introduced as brand colour: "
                      + ", ".join(ctx["palette"]))
    if ground:
        out["brand_ground"] = "BRAND GROUND: " + " ".join(ground)

    if ctx.get("references"):
        if req.get("from_image"):
            out["references"] = EDIT_CLAUSE
        else:
            out["references"] = (
                "The attached photograph is the real object. It appears in this "
                "picture exactly as it is — same pack, same proportions, same "
                "colours, same label. Do not redraw it.")

    if req.get("_finish"):
        # Generated at 4:5 as the CONTENT of a 9:16 asset; the strips above and
        # below are painted afterwards with the content taped down, so nothing
        # is ever cropped — the model is told the canvas it actually has.
        line = CONTENT_WINDOW.replace("{gen}", req["_gen_aspect"]).replace("{aspect}", aspect)
    else:
        line = f"The frame is {aspect}."
        # The composition clause tells the model how to COMPOSE a scene for the
        # crop. An edit has its composition already — the reference's — and the
        # clause's own words ("the hands, the body part the proof is on") invited
        # a headline swap to grow hands (2026-09-22). Skipped for edits.
        if purpose.get("safe_zone") and not req.get("from_image"):
            line += " " + SAFE.replace("{aspect}", aspect)
    if purpose.get("words") == "never":
        line += " " + NO_WORDS
    out["aspect_line"] = line

    out["standing_rules"] = standing_rules(folder)
    for extra in req.get("rules") or []:
        out["standing_rules"] += "\n\n" + str(extra)
    return out


def render(req, ctx, folder=None):
    """The prompt exactly as it will be sent. (text, skeleton_path)."""
    path = latest("picture", folder)
    skeleton = body(path)
    values = slots(req, ctx, folder)

    asked = set(SLOT.findall(skeleton))
    unknown = sorted(asked - set(ORDER))
    if unknown:
        raise ValueError(f"{path.name} asks for slots nothing fills: {', '.join(unknown)}")

    out = skeleton
    for name in ORDER:
        out = out.replace("{" + name + "}", values.get(name) or "")
    # A dropped slot leaves a blank line behind; collapse runs of them so the
    # prompt reads as one piece however many slots this picture used.
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out, path
