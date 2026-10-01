#!/usr/bin/env python3
"""
prompt.py — the Cinema Studio stage. One A-roll talking clip, two calls.

    python3 prompt.py payloads <plan.json>     print the generate payloads
    python3 prompt.py prompt   <plan.json> A1  print one prompt, verbatim

THE CONTRACT (THE-CINEMA-LINE.md):

  1  generate   cinematic_studio_3_0 · generate_audio true · the line IN the
                prompt as words · NO audio file, NO start image
  2  revoice    voice_change · video_id = step 1's job id · the cast member's
                voice element · voice_type "element"

Nothing is synced, because nothing is married: Cinema Studio performs the
speech and the picture together. Attaching an audio file is the failure this
stage exists to prevent, and the reason to read the durations below: a clip
whose length equals its voiceover file sample-for-sample was built the old
way, whatever it looks like.

Higgsfield has NO API key on this machine — it is reached through the MCP
connector only. So this module BUILDS and RECORDS; a session SUBMITS. Every
submission writes back the model and both job ids, because a wrong model that
leaves no trace is a wrong model that gets used twice.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# --------------------------------------------------------- element facts
#
# Every slop round so far has been a fact the repo already held and the
# prompt did not send: the FLEX standing on a base it does not have, bristles
# on a back that has none, invented bottles beside a real product element.
#
# So the facts live with the element, in element-facts.json, and ANY prompt
# that references <<<uuid>>> gets that element's facts appended automatically.
# Nobody has to remember. A prompt cannot silently omit what is true.

# Brand data lives with the BRAND. The lane is brand-agnostic: a run names its
# brand in plan.json and the facts are read from there, so the same chain runs
# the brand, or a brand that does not exist yet, without a line of it changing.
WORKSPACE = Path(__file__).resolve().parents[4]
BRAND: str | None = None      # set per run by use_brand(), from the plan


def facts_file() -> Path:
    if not BRAND:
        raise SystemExit(
            "This run does not name a brand.\n"
            '  Add  "brand": "<name>"  to the run\'s out/plan.json.\n'
            "  The lane reads brands/<name>/element-facts.json from it, and "
            "ships to that brand's Drive folder.")
    return WORKSPACE / "brands" / BRAND / "element-facts.json"


def use_brand(name: str) -> None:
    """Point the lane at a brand. Called once, from the run's plan."""
    global BRAND
    BRAND = name
_EL = re.compile(r"<<<([0-9a-fA-F-]{36})>>>")


def _facts() -> dict:
    try:
        return json.loads(facts_file().read_text()).get("elements", {})
    except Exception:
        return {}


def with_facts(prompt: str) -> str:
    """Append what is true of every element this prompt references."""
    book = _facts()
    seen, lines, warn = [], [], []
    for uid in _EL.findall(prompt):
        if uid in seen:
            continue
        seen.append(uid)
        row = book.get(uid)
        if not row:
            continue
        if row.get("same_as"):
            row = book.get(row["same_as"], row)
        if row.get("blocked"):
            # A hard stop, not a note. An element that is known to be wrong
            # gets used again the moment refusing it is left to memory.
            raise SystemExit(
                f"BLOCKED ELEMENT {row.get('name', uid)} <<<{uid}>>>\n"
                f"  {row['warning']}\n"
                f"  Nothing was submitted. Swap the element and run again.")
        if row.get("warning"):
            warn.append(f"{row.get('name', uid)}: {row['warning']}")
        for f in row.get("facts", []):
            lines.append(f)
        for f in row.get("forbids", []):
            lines.append(f)
    if warn:
        # printed for the operator, never sent to the model
        for w in warn:
            print(f"  !! {w}", file=sys.stderr)
    if not lines:
        return prompt
    return (prompt + "\n\nWhat is true of what is in this shot, and must hold:\n"
            + "\n".join(f"- {l}" for l in lines))


# ------------------------------------------------------- the prompt files
#
# The shapes live in ../prompts/, one versioned file per stage, the same way
# the teardown machine keeps its prompts. They are NOT strings in here.
#
# The reason is uniformity: the shape is what makes the output consistent, so
# when it needs a change the change has to reach every brief at once. A string
# buried in a module gets edited for one run and forgotten; a file in the
# prompt library is the thing everybody reads and tweaks.

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
STAGE_PROMPT = {
    "openings": "stage-1-openings/stage1-openings-v1-damon.md",
    "aroll":    "stage-2-aroll/stage2-aroll-v2-damon.md",
    "broll":    "stage-3-broll/stage3-broll-v1-damon.md",
    "offer":    "stage-4-offer/stage4-offer-v2-damon.md",
}
_SHAPE = re.compile(r"```shape\n(.*?)```", re.S)


def shape(stage: str) -> str:
    """The fenced `shape` block out of that stage's prompt file."""
    f = PROMPTS / STAGE_PROMPT[stage]
    if not f.exists():
        raise SystemExit(f"missing prompt file: {f}")
    m = _SHAPE.search(f.read_text())
    if not m:
        raise SystemExit(f"no ```shape block in {f}")
    # the files wrap long lines with a trailing backslash for readability
    return re.sub(r"\\\n", "", m.group(1)).strip()


MODEL = "cinematic_studio_3_0"
CEILING = 15          # Cinema Studio's hard duration ceiling, seconds

# The no-cut line — every video prompt this lane builds carries it, without
# exception (the course write-up, Damon 09-14, §7): a model that invents a
# cut mid-sentence is a dead generation, and it is one line. preflight.py's
# rule 11 gates on it; this is where it gets INTO the prompt, so `run.py
# start` produces compliant batches without a session having to remember.
NO_CUT_LINE = "Single continuous take, no cuts or scene changes."


def with_no_cut(prompt: str) -> str:
    """Append the no-cut line, unless the shape already carries wording that
    satisfies rule 11 (both "single continuous take" and "no cuts")."""
    p = prompt.lower()
    if "single continuous take" in p and "no cuts" in p:
        return prompt
    return prompt.rstrip() + " " + NO_CUT_LINE


# The prompt shape. Every blank is filled from the scene row; no sentence here
# is ever rewritten per scene, which is what makes this printable at volume.

def payload(row: dict, cast: dict) -> dict:
    """The generate_video params for one talking beat."""
    if row["seconds"] > CEILING:
        raise SystemExit(
            f"{row['id']} is {row['seconds']}s — over the {CEILING}s ceiling. "
            "Split it at a sentence break, never at a cutaway.")
    room = f"The room is <<<{cast['room']}>>>."
    return {
        "model": MODEL,
        "prompt": with_no_cut(with_facts(shape("aroll").format(
            room=room, face=cast["face"],
            presenter=cast.get("presenter") or cast["name"].split()[0].upper(),
            who=cast.get("who", "speaking to camera"),
            says=cast.get("says", "They say"),
            gesture=row["gesture"].strip(),
            delivery=row["delivery"].strip(),
            line=row["line"].strip()))),
        "duration": int(row["seconds"]),
        "aspect_ratio": "9:16",
        "resolution": cast.get("resolution", "720p"),
        "generate_audio": True,
        "genre": "drama",
    }


def revoice(job_id: str, cast: dict) -> dict:
    """The voice_change params — step two, which keeps timing and visuals."""
    return {"video_id": job_id, "voice_id": cast["voice"], "voice_type": "element"}



# --------------------------------------------------------------- B-roll
#
# A cutaway is NOT a talking beat and does not share its shape.
#
#   · Nothing is said, so generate_audio is FALSE. It sits under her voice,
#     which never stops. A cutaway that carries its own dialogue fights the
#     take it is covering.
#   · A named product comes in as its PROP ELEMENT, never as a description.
#     The element was built from the brand's own photography, so the label is
#     real. Asking a generator to letter a bottle returns "bloodmark" and
#     "BUMP PATROL" — it has, twice.
#   · Never ask for text of any kind. The line below says so out loud because
#     the model will otherwise invent a price tag or a logo unprompted.
#   · State ONE action with a beginning and an end. An insert told only what
#     is in frame comes back as a still with a slow push on it.
#   · Never name the camera. Say the result: how close, how shallow, how lit.


# The no-text line has TWO forms, and using the wrong one breaks the shot.
#
# A cutaway with no product in it must be told plainly that there is no text,
# or the model invents a price tag or a wordmark unprompted.
#
# But a cutaway carrying a real product element must NOT be told that: the
# element exists precisely so the label renders, and forbidding all text
# fights the thing that finally put the real wordmark on the bottle. What is
# forbidden there is INVENTED lettering, not lettering.
NO_TEXT = ("Nothing in frame carries any text, label copy, price tag or "
           "writing.")
ONLY_REAL_TEXT = ("The only writing anywhere in frame is the real label "
                  "each product actually carries; no other text, no invented "
                  "lettering, no price tags, no signage.")


def broll(row: dict) -> dict:
    """The generate_video params for one cutaway. Silent by design."""
    return {
        "model": MODEL,
        "prompt": with_no_cut(with_facts(shape("broll").format(
            place=row["place"].strip(), subject=row["subject"].strip(),
            action=row["action"].strip(), look=row["look"].strip(),
            text_rule=ONLY_REAL_TEXT if row.get("products") else NO_TEXT))),
        "duration": int(row["seconds"]),
        "aspect_ratio": "9:16",
        "resolution": row.get("resolution", "720p"),
        "generate_audio": False,
        "genre": "drama",
    }


def load(p: Path) -> tuple[dict, list[dict]]:
    d = json.loads(p.read_text())
    use_brand(d.get("brand"))
    return d["cast"], d["scenes"]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    verb, plan = sys.argv[1], Path(sys.argv[2])
    cast, scenes = load(plan)
    if verb == "broll":
        cuts = json.loads(plan.read_text()).get("cutaways", [])
        print(json.dumps([{"index": i + 1, "id": c["id"],
                           "params": broll(c)}
                          for i, c in enumerate(cuts)], indent=1))
    elif verb == "brollprompt":
        cuts = json.loads(plan.read_text()).get("cutaways", [])
        print(broll(next(c for c in cuts if c["id"] == sys.argv[3]))["prompt"])
    elif verb == "payloads":
        print(json.dumps([{"index": i + 1, "id": s["id"],
                           "params": payload(s, cast)}
                          for i, s in enumerate(scenes)], indent=1))
    elif verb == "prompt":
        want = sys.argv[3]
        row = next(s for s in scenes if s["id"] == want)
        print(payload(row, cast)["prompt"])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
