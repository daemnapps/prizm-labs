"""THE SKIN BANK: real skin texture for every print and every cast member that shows skin (owner ruling, 2026-11-26).

One bank for every brand: runs/ai-elements/_texture-refs/index.json (`skin` rows). Two kinds, always used together:
  customer  a crop of a real customer's before photo, skin only (no eyes, no face, no words): the real condition
  macro     a close macro shot of that skin type: pores, fine hair, sheen
The reference gives texture only. A face is never copied from it and the photo itself never appears in an ad.

    pick(condition, tone)   -> [customer row, macro row] that match best (either may be missing: then `gaps` names it)
    files(rows)             -> absolute paths for a reference board
    PRINT_WORDS             the line every people or skin print carries
"""
import json
from pathlib import Path

from image_production import paths as P

PRINT_WORDS = ("Every bit of skin takes its texture from the pictures labelled 'skin' on the reference: real pores, fine "
               "hairs, uneven tone, the marks exactly as they really sit on skin, phone-camera sharpness. Never smooth, "
               "waxy, glossy, airbrushed or plastic. The 'skin' pictures give texture only: never their face, never the "
               "photo itself.")

TONES = ["fair", "olive", "light-tan", "light-brown", "medium-brown", "dark-brown", "deep-brown"]


def home():
    return P.repo() / "runs" / "ai-elements" / "_texture-refs"


def load():
    f = home() / "index.json"
    return json.loads(f.read_text()).get("skin") or [] if f.is_file() else []


def _tone_gap(a, b):
    a, b = str(a or ""), str(b or "")
    if a in TONES and b in TONES:
        return abs(TONES.index(a) - TONES.index(b))
    return 0 if not a or not b or a == b else 3


def _words(x):
    return {w for w in str(x or "").lower().replace(",", " ").split() if len(w) > 2}


def _score(row, condition, tone):
    cond = _words(condition)
    hit = len(cond & (_words(row.get("condition")) | _words(" ".join(row.get("marks") or [])))) if cond else 0
    return (-hit, _tone_gap(row.get("tone"), tone))


def pick(condition=None, tone=None, rows=None):
    """The best customer row and the best macro row for a condition (acne, razor bumps, dark marks, clear) and a tone."""
    rows = load() if rows is None else rows
    out = []
    for kind in ("customer", "macro"):
        cands = [r for r in rows if (r.get("kind") or "macro") == kind]
        if cands:
            best = sorted(cands, key=lambda r: _score(r, condition, tone))[0]
            out.append(best)
            tone = tone or best.get("tone")           # the macro shot matches the customer crop's tone
    return out


def gaps(rows):
    have = {(r.get("kind") or "macro") for r in rows}
    return [f"no {k} skin row in the bank" for k in ("customer", "macro") if k not in have]


def files(rows):
    return [home() / r["file"] for r in rows]
