"""The edit discipline — lifted from the video machine's frame edits and made
brand-free.

    generate from a description        4,262 chars   wrong wardrobe, blended faces
    edit, but still describing it      766-1,133     composition better, caption wrong
    EDIT, DELTA ONLY                     204-386     scene held, wardrobe right, legible

One rule (2026-09-02): **an edit instruction must never describe anything the
reference already shows.** Re-describing the room tells the model to rebuild
it, and rebuilding is the generation we are escaping.

Second rule (2026-09-11): **change one thing, and only one**, so the next
result answers a question. A 349-character instruction that changes the room,
the wardrobe, the shelves and the light is five edits wearing one sentence,
and when it comes back wrong nothing says which of the five did it.

No brand, product, person or model is named here. A caller passes the element
ids the change is ABOUT, read from the brand, never from this file.
"""
import json
import re
from pathlib import Path

DELTA_MIN, DELTA_MAX = 120, 400        # measured band, with a little headroom
MAX_CHANGES = 2                        # an edit moves one thing, two at a push
TEXT_MAX = 700                         # the whole instruction, keeps included

# The band is measured on the DELTA — the part that can start describing the
# scene. The keep clause is a list of what must not move, and a longer list is
# a tighter edit, not a looser one; it is capped separately so a five-item keep
# list on a static ad does not refuse a one-line change (found on the first
# variation run, 2026-09-22).

# `faces`, not `face`: "face visible" (a keep note on almost every carousel
# delta) read as a second change and refused one-panel slides (2026-10-02).
# "she faces the window" still counts; "turns to face" counts on "turns".
_SPLIT = re.compile(r",\s+|\band\b|\bthen\b|;\s*", re.I)
_VERB = re.compile(
    r"\b(is|are|make[s]?|move[s]?|change[s]?|put[s]?|add[s]?|remove[s]?|swap[s]?|"
    r"turn[s]?|faces|hold[s]?|look[s]?|stand[s]?|sit[s]?|open[s]?|close[s]?|"
    r"lift[s]?|drop[s]?|bring[s]?|show[s]?|lose[s]?|keep[s]?|replace[s]?|fix|fixes)\b", re.I)


# Words in quotes are the literal words a picture carries — "the words change
# to "<name> / a support line with commas, and an and""
# is ONE change however many commas and "and"s the copy holds. They are
# counted as one token and left out of the length band (a carousel slide's
# words, 2026-10-02: every slide with a support line was refused for its copy).
_QUOTED = re.compile(r'"[^"]*"|“[^”]*”')


def _unquoted(change: str) -> str:
    return _QUOTED.sub('"…"', change)


def count_changes(change: str) -> int:
    """How many separate alterations this asks for."""
    parts = [p.strip() for p in _SPLIT.split(_unquoted(change)) if p.strip()]
    return max(1, sum(1 for p in parts if _VERB.search(p) or len(p.split()) > 4))


def splits(path=None) -> dict:
    """The default keep/change split per KIND of reference (`splits.json`).
    A caller's own split for a picture outranks the kind's default."""
    p = Path(path) if path else Path(__file__).resolve().parent.parent / "splits.json"
    return {k: v for k, v in json.loads(p.read_text()).items() if not k.startswith("_")}


def split_for(kind: str, own: dict | None = None, table: dict | None = None) -> dict:
    if own and own.get("keep"):
        return {"keep": list(own["keep"]), "change": list(own.get("change") or [])}
    t = table or splits()
    if kind not in t:
        raise SystemExit(f"`{kind}` is not a reference kind — have: {', '.join(sorted(t))}")
    return {"keep": list(t[kind]["keep"]), "change": list(t[kind]["change"])}


def instruction(keep: list[str], change: str, element_ids: list[str] | None = None,
                extra_keep: list[str] | None = None) -> str:
    """The delta, and only the delta.

    An edit off the reference alone re-derives whatever the reference got
    wrong: a product face that came back as coarse ridges stays ridges,
    because the only picture in the room still shows ridges. When the change
    is ABOUT a banked element, its id rides along so the bank's own reference
    is reproduced exactly (edit.py, 2026-09-11)."""
    keeps = list(keep) + list(extra_keep or [])
    text = (f"Keep the reference image exactly as it is — {'; '.join(keeps)} — and change "
            f"only this: {change.strip().rstrip('.')}.")
    for eid in element_ids or []:
        text += f" The <<<{eid}>>> is reproduced exactly from its own reference."
    return text


def guard(change: str, text: str) -> str | None:
    """Why this instruction is refused, or None. Refusal is a note, not an
    exception: the record keeps what was asked so the next ask is narrower."""
    moves = count_changes(change)
    if moves > MAX_CHANGES:
        return (f"this asks for {moves} changes at once. An edit moves one thing "
                f"so the next result answers a question — run them one at a time, "
                f"starting with whichever is most wrong.")
    if len(_unquoted(change)) > DELTA_MAX:
        return (f"the change is {len(_unquoted(change))} chars (quoted words not counted), past the {DELTA_MAX} band — "
                "it has started describing the scene again. Narrow the change.")
    if len(_unquoted(text)) > TEXT_MAX:
        return (f"instruction is {len(_unquoted(text))} chars (quoted words not counted), past {TEXT_MAX} — too many keeps "
                "for one edit. Keep what the kind's split keeps and name the change.")
    return None

