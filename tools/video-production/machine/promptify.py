#!/usr/bin/env python3
"""
promptify.py — a scene becomes a generation prompt, mechanically.

Hand-writing a prompt per scene is where the rules get forgotten. Twice in one
afternoon: a camera named in the text put a tripod in the shot, and a
"plain unlabelled bottle" left a hand holding nothing while the line said the
product's name. Both were me typing, not the brief.

So the brief's scene is the input and the rules are applied here, every time,
the same way:

  · identities come in as Element ids, never re-described
  · the room and the props are carried through as written
  · the camera is never named — only the framing and the light
  · filming equipment is negated out loud on any shot with a person
  · nothing is added that the scene did not say

    python3 machine/promptify.py <run folder> [--scene N] [--brand B]

The cast is the BRAND's: brands/<brand>/core-avatars/casting. The brand is the
run's own — `--brand`, else the "brand" the run wrote in run.json or
out/plan.json. A run that names none is refused; no brand is ever assumed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenes as SC                                     # noqa: E402

# who and what resolve to reference ids the generator can hold faithfully —
# out of the casting folder of the brand the RUN names, never one written here
WORKSPACE = Path(os.environ.get("AI_WORKSPACE") or HERE.parents[3])
CAST_FILE: Path | None = None                 # set per run by use_brand()


def cast_dir(brand: str) -> Path:
    return WORKSPACE / "brands" / brand / "core-avatars" / "casting"


def brand_of(run: Path, flag: str | None = None) -> str:
    """The run's brand: the flag, else what the run itself wrote down."""
    if flag:
        return flag
    for f in (run / "run.json", run / "out" / "plan.json", run / "plan.json"):
        try:
            b = json.loads(f.read_text()).get("brand")
        except (OSError, ValueError, AttributeError):
            continue
        if b:
            return str(b)
    raise SystemExit(
        "This run does not name a brand.\n"
        "  Pass --brand <name>, or add \"brand\": \"<name>\" to the run's run.json.\n"
        "  The cast is read from brands/<name>/core-avatars/casting.")


def use_brand(brand: str) -> Path:
    """Point the cast lookup at a brand. Called once, from the run."""
    global CAST_FILE
    CAST_FILE = cast_dir(brand)
    return CAST_FILE

# A generator has no camera it looks *through*. Anything named is an object it
# can place IN the picture, so these words never survive into a prompt.
# Words that name a physical object a generator can stand in the room. Note
# what is NOT here: "handheld", "locked-off", "push", "macro", "close" are
# descriptions of a shot, not objects, and they have to survive — stripping
# them leaves a prompt with no framing at all.
GEAR = re.compile(
    r"\b(cameras?|phones?|iphones?|tripods?|gimbals?|webcams?|lenses|lens|"
    r"softboxe?s?|ring lights?|booms?|microphones?|mics?|rigs?|dollys?|dollies|"
    r"cranes?|monitors?|\d+mm)\b", re.I)

# A gear word sometimes sits inside a phrase that is really about framing.
# Rewrite those rather than losing the framing with them.
REWRITE = [
    (re.compile(r"\block(ed)?[- ]off camera\b", re.I), "locked off"),
    (re.compile(r"\bcamera (is )?(at|held at)\b", re.I), "framed at"),
    (re.compile(r"\bthe camera (pushes|moves|drifts|holds|pulls)\b", re.I),
     r"the frame \1"),
    (re.compile(r"\bcamera[- ]?(left|right)\b", re.I), r"frame \1"),
    (re.compile(r"\b(shot|filmed) on [^,.;]*", re.I), ""),
    (re.compile(r"\btoward the lens\b", re.I), "toward the viewer"),
    (re.compile(r"\bto camera\b", re.I), "to the viewer"),
]

NO_GEAR = ("IMPORTANT: no camera, no phone, no tripod, no lights, no microphone "
           "and no filming equipment anywhere in the frame.")

# The look tail is assembled per scene, never pasted whole. A blanket tail
# contradicts the brief: it asked a product shot for "real skin texture with
# visible pores", and told a diagram "no added text" in the same breath as the
# brief asking for two labels to fade in. A prompt that argues with itself
# gets a picture that splits the difference.
PHOTOREAL = "Photoreal, shot on a real camera."
SKIN = "Real skin texture with visible pores, no beauty retouching."
NO_TEXT = "No added text, captions, watermarks or graphics."
LABEL_STAYS = ("The product's own printed label stays crisp and legible. "
               "Add no other text, captions or graphics.")
WORDS_ASKED = ("Render only the words the scene names, in plain white sans-serif. "
               "No other text, captions or graphics.")

# does a person appear in this scene at all?
PERSON = re.compile(r"\b(she|her|he|his|him|man|woman|hand|hands|fingers?|"
                    r"face|neck|jaw|cheek|wrist|barber|client)\b", re.I)
# does the brief ask for words to appear inside the frame?
ASKS_TEXT = re.compile(r"\b(fade[s]? in|label(l)?ed|the words?|reads?|caption|"
                       r"on-?screen text|title)\b", re.I)


def elements() -> dict[str, str]:
    """name -> element id, from the brand's own casting records."""
    out = {}
    if CAST_FILE is None:
        raise SystemExit("promptify: no brand set — call use_brand(<brand>) "
                         "or run with --brand")
    # authority.json carries its people's handles inline; the roster's men keep
    # theirs in identities.json beside it, so both have to be read.
    for f in ("authority.json", "roster.json"):
        p = CAST_FILE / f
        if not p.exists():
            continue
        for person in json.loads(p.read_text()).get("people", []):
            eid = person.get("element_id")
            if eid:
                out[person["id"].lower()] = eid
                out[(person.get("name") or "").split()[0].lower()] = eid
    ids = CAST_FILE / "identities.json"
    if ids.exists():
        for who, rec in (json.loads(ids.read_text()).get("people") or {}).items():
            if rec.get("element_id"):
                out.setdefault(who.lower(), rec["element_id"])
    return {k: v for k, v in out.items() if k}


def strip_gear(text: str) -> str:
    """Remove equipment without removing the shot.

    Rewrite the phrases where a gear word is really carrying framing
    ("locked-off camera at chest height" is framing), then drop only the
    clauses that are left naming equipment and nothing else.
    """
    # Text with no equipment in it is returned exactly as the brief wrote it.
    # The clause surgery below rebuilds punctuation, which is fine when it is
    # removing a tripod and wrong when there was nothing to remove.
    if not GEAR.search(text) and not any(p.search(text) for p, _ in REWRITE):
        return text.strip()
    for pat, repl in REWRITE:
        text = pat.sub(repl, text)
    kept = []
    for clause in re.split(r"(?<=[.;])\s+|,\s+", text):
        c = clause.strip(" ,.;")
        if not c or GEAR.search(c):
            continue
        kept.append(c)
    return ", ".join(kept).strip()


def world(run: Path, want: str = "") -> str:
    """The place, from the brief's world block.

    A scene names its room and trusts the block to describe it — which is
    right for a person reading the brief and useless to a generator, which
    was not handed the block. A type-A still generated from the scene alone
    came back as a person against nothing.
    """
    brief = (run / "stages" / "5-brief.md")
    if not brief.exists():
        return ""
    t = brief.read_text()
    m = re.search(r"^## THE WORLD\s*(.+?)^## ", t, re.M | re.S)
    if not m:
        return ""
    blocks = re.findall(r"^\*\*(.+?)\*\*\s*[—-]\s*(.+?)(?=\n\n|\Z)",
                        m.group(1), re.M | re.S)
    if not blocks:
        return ""
    if want:
        for name, body in blocks:
            if want.lower() in name.lower():
                return " ".join(body.split())
    return " ".join(blocks[0][1].split())


def build(sc: dict, elems: dict[str, str], place: str = "") -> str:
    who = (sc.get("who") or "").strip().lower()
    body = strip_gear(sc.get("happens") or sc.get("product") or "")
    parts = []

    tag = next((f"<<<{v}>>>" for k, v in elems.items() if k and k in who), None)
    if sc["type"] == "A":
        # A talking beat needs the person and the room and nothing else — the
        # words are carried by the voice take, not by the picture.
        parts.append((tag or "The presenter") +
                     " mid-sentence to the viewer, waist-up, hands up and moving as she talks.")
        if place:
            parts.append("She is standing in: " + place)
    elif body:
        for name, eid in elems.items():
            if len(name) > 3 and re.search(rf"\b{re.escape(name)}\b", body, re.I):
                body = re.sub(rf"\b{re.escape(name)}\b", f"<<<{eid}>>>", body,
                              count=1, flags=re.I)
                break
        parts.append(body)

    if sc.get("camera"):
        framing = strip_gear(sc["camera"])
        if framing:
            parts.append(framing)
    blob = " ".join(str(sc.get(k) or "") for k in
                    ("happens", "product", "who", "camera", "hold"))
    # "FLEX Pro Vibrating Face Brush" matched the person test on the word
    # "face" and a product shot was told to render visible pores.
    blob_np = re.sub(r"\bface (brush|wash)\b", "", blob, flags=re.I)
    has_person = sc["type"] == "A" or (sc["type"] != "C" and bool(PERSON.search(blob_np)))

    if has_person:
        parts.append(NO_GEAR)
    parts.append(PHOTOREAL)
    if has_person:
        parts.append(SKIN)
    # Text: the product's label is the product's, words the scene asks for are
    # content, and everything else is noise we do not want invented.
    if sc["type"] == "C" or re.search(r"\blabel\b", blob, re.I):
        parts.append(LABEL_STAYS)
    elif ASKS_TEXT.search(blob):
        parts.append(WORDS_ASKED)
    else:
        parts.append(NO_TEXT)
    return " ".join(p.rstrip(".") + "." for p in parts if p)


def main() -> None:
    run = Path(sys.argv[1]).expanduser().resolve()
    only = None
    if "--scene" in sys.argv:
        only = int(sys.argv[sys.argv.index("--scene") + 1])
    flag = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    use_brand(brand_of(run, flag))
    elems = elements()
    place = world(run)
    for sc in SC.load(run)["scenes"]:
        if only and sc["n"] != only:
            continue
        print(f"\n--- scene {sc['n']} · TYPE {sc['type']} · {sc['seconds']}s ---")
        print(build(sc, elems, place if sc["type"] == "A" else ""))


if __name__ == "__main__":
    main()
