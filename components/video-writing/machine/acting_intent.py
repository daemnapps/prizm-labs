"""AI-1 (acting intent, 2026-11-27): the one switch for the want-behind-the-face prompts.

On (the default): the presenter body reads its v7 prompt (each scene's performance cell opens with what the presenter
wants, what is in the way and the word it turns on) and the director's swipe-base storyboard ask reads its v4 prompt
(an `intent` object on every pitch, every shot's face and gestures derived from it). Off: v6 and v3, exactly as before.

    acting_intent.json  {"on": false}   turns it off for everyone
    ACTING_INTENT_OFF=1                 turns it off on one machine

Row AI-1 in team/rollbacks.md. Reads nothing else; writes nothing.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRESENTER_BODY_MIN = 7        # the first presenter-body version that carries rule 18
STORYBOARD_ASK = 4            # the swipe-base storyboard ask that carries the Intent paragraph


def on() -> bool:
    if os.environ.get("ACTING_INTENT_OFF"):
        return False
    try:
        return bool(json.loads((HERE / "acting_intent.json").read_text()).get("on", True))
    except (OSError, ValueError):
        return True
