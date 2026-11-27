#!/usr/bin/env python3
"""voice_cast.py — every speaking role takes the one voice set for its demographic (rule 2026-11-12: every voice in an
ad matches the demographic on screen; one voice per demographic, set once, never picked per ad). One home for every
path that casts a voice: production, the edit line and the Video Studio read the rule from here.

The list is brands/<brand>/ai-elements/voices.json: {"voices": {"<sex>/<age band>/<ethnicity>": {"voice_id", "name",
"model", "settings"}}}. The narrator takes the row of the people on screen; each on-camera speaker takes the row of
their own face. A face with no row is refused by name (NoVoice): choose one real voiceprint of that demographic and
add its row; it is then used for every video.

    python3 voice_cast.py <brand> <face, e.g. male/25-34/black or a library path>

Brand-agnostic: the brand comes in as a name, its list from its own folder.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ETHNIC = ("black", "white", "latino", "hispanic", "asian", "east-asian", "south-asian", "southeast-asian",
          "middle-eastern", "mixed")


class NoVoice(SystemExit):
    """A speaking role whose demographic has no voice set."""


def workspace(start=HERE) -> Path:
    """The workspace this component sits in: the first folder upward holding both components/ and brands/."""
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return here.parents[2]


def registry(brand: str, root=None) -> dict:
    """{face: voice row} for the brand, from brands/<brand>/ai-elements/voices.json. {} when it has none."""
    f = Path(root or workspace()) / "brands" / brand / "ai-elements" / "voices.json"
    try:
        return json.loads(f.read_text()).get("voices") or {}
    except (OSError, ValueError):
        return {}


def norm_face(face) -> str | None:
    """'male/25-34/black' from a face or a library path ('/content-creators/male/black/25-34/devonte/')."""
    if not face:
        return None
    parts = [p for p in re.split(r"[/\s]+", str(face).lower()) if p]
    sex = next((p for p in parts if p in ("male", "female")), None)
    age = next((p for p in parts if re.fullmatch(r"\d{2}-\d{2}", p)), None)
    eth = next((p for p in parts if p in ETHNIC), None)
    return f"{sex}/{age}/{eth}" if sex and age and eth else None


def voice_for(brand: str, face, role: str = "the narrator", rows: dict | None = None, root=None) -> dict:
    """The voice row for this face (with `face` set), or NoVoice naming the role and the missing row."""
    face = norm_face(face)
    rows = registry(brand, root) if rows is None else rows
    row = rows.get(face) if face else None
    if not row:
        raise NoVoice(f"{role}: no voice is set for {brand} {face or '(no face named)'}. Choose one real voiceprint of that "
                      f"demographic and add it to brands/{brand}/ai-elements/voices.json; it is then used for every video.")
    return dict(row, face=face)


def matches(brand: str, face, has_voice_id, role: str = "the narrator", rows: dict | None = None, root=None) -> dict:
    """One role's row: {face, wants, has, ok[, why]}: does the voice it reads in match the one set for its face?"""
    try:
        want = voice_for(brand, face, role, rows, root)["voice_id"]
    except NoVoice as e:
        return {"face": norm_face(face), "wants": None, "has": has_voice_id, "ok": False, "why": str(e)}
    return {"face": norm_face(face), "wants": want, "has": has_voice_id, "ok": has_voice_id == want}


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    v = voice_for(a[0], a[1])
    print(json.dumps(v, indent=1))
