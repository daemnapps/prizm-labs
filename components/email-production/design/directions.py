"""Wireframe directions: three different layouts of one email, shown as placeholders, so a person picks a direction BEFORE any picture is made.

    python3 line.py <brand> --run <run folder> --directions     three layouts -> design/direction-a|b|c.json + directions.html (no picture made)
    python3 line.py <brand> --run <run folder> --pick b         keep direction b as the email (design/email.json + preview.html)

Why (editor, 2026-11-20): emails from the same base template came out with the same hero, the same picture sizes and the same person. Each
direction here has its own hero type and height band; every direction is checked against the brand's most recent emails so a hero height,
a palette or a setup is not repeated. Brand-agnostic: it reads other emails' design/email.json from runs/email-production/<brand>/.
"""
import json
import re
from pathlib import Path

# Three hero archetypes. `band` is the photo_h range for an fg_hero; the layout step may use any section order that fits the copy.
DIRECTIONS = [
    {"id": "a", "name": "Product still life", "band": (880, 1000),
     "brief": "The hero is a product still life: the real products as the subject, no person, on a surface and light that fit the email's idea. "
              "A calm, empty wall above for the headline.",
     "structure": "Build it on the brand's BASIC recipe: the full teaching order, the middle explaining the idea step by step before the offer."},
    {"id": "b", "name": "Abstract set", "band": (1000, 1100),
     "brief": "The hero is an abstract set: light, shape, texture and the email's setting (no person, no product close-up); the products appear "
              "further down. A calm area for the headline.",
     "structure": "Build it picture-led and short: fewer sections, bigger pictures, mosaics and zigzag rows carrying the story in short lines, the "
                  "offer or the ask earlier. Use whichever of the brand's OTHER recipes fits this copy best, or your own order of the building blocks."},
    {"id": "c", "name": "A new person", "band": (740, 880),
     "brief": "The hero is a person who has NOT appeared in the recent emails below (a different age, hair, skin tone and setting from the last "
              "three people), holding or using the product by her face or hands. A calm area for the headline.",
     "structure": "Build it people- and proof-led: creator stills, quotes or the voice of customers early, the product and the practice as the answer "
                  "after them, the promise and the ask last. Use a section order different from the other two directions."},
]


def _hero(spec):
    for s in spec.get("sections", []):
        if s.get("s") == "fg_hero":
            return s
    return None


def _grounds(spec):
    return sorted({s.get("bg") for s in spec.get("sections", []) if s.get("s") in ("fg_block", "fg_band") and s.get("bg")})


def recent(brand, repo, exclude=None, n=5, before=None):
    """The brand's n most recent designed emails with an fg_hero (by date, only those dated before `before` when given), newest first:
    label, date, hero height, hero picture words, section grounds. An email with no Figma-look hero has nothing to repeat and is skipped."""
    out = []
    for p in sorted((Path(repo) / "runs" / "email-production" / brand).glob("*/design/email.json")):
        if exclude and p.parent.parent.name == exclude:
            continue
        try:
            d = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not d.get("sections"):
            continue
        h = _hero(d)
        if not h or (before and str(d.get("date") or "") >= str(before)):
            continue
        pic = h.get("picture") if isinstance(h.get("picture"), dict) else {}
        out.append({"label": p.parent.parent.name, "date": str(d.get("date") or ""), "hero_h": h.get("photo_h"),
                    "hero_words": (pic.get("todo") or pic.get("alt") or "")[:140], "grounds": _grounds(d),
                    "diagram": (diagram_of(d) or [None])[0], "diagram_all": diagram_of(d)})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:n]


def recent_text(rec):
    if not rec:
        return "(no earlier designed emails on file)"
    return "\n".join("- %s (%s): hero %s px; hero picture: %s; section grounds: %s" % (
        r["label"], r["date"], r["hero_h"] or "?", r["hero_words"] or "?", ", ".join(r["grounds"]) or "?") for r in rec)


def direction_text(d, rec):
    lo, hi = d["band"]
    return ("\n\nDIRECTION %s: %s (this layout is ONE of three the designer will compare, so it must really differ from the others).\n"
            "HERO: %s Use an fg_hero with photo_h between %d and %d.\n"
            "STRUCTURE: %s The three directions must differ in section ORDER and in which blocks lead, not only in the hero; the copy decides which "
            "blocks fit, and every one of the copy's lines is kept.\n"
            "RECENT EMAILS (do not repeat their hero height within 60px, their people, their set or their palette):\n%s\n"
            "Pick a fresh palette and set from the brand's reference board, a section order that fits the copy and the recipe, and different "
            "picture sizes from the other directions. Every picture is a todo slot with a short brief; nothing is made yet."
            % (d["id"].upper(), d["name"], d["brief"], lo, hi, d.get("structure", ""), recent_text(rec)))


def problems(spec, d, rec):
    """What makes a direction a repeat: the wrong hero band, a hero height or a set of section grounds the last emails already used."""
    out = []
    h = _hero(spec)
    lo, hi = d["band"]
    if not h:
        return ["direction %s has no hero" % d["id"]]
    ph = h.get("photo_h")
    try:
        ph = int(ph)
    except (TypeError, ValueError):
        return ["direction %s: the hero has no photo_h" % d["id"]]
    if not lo <= ph <= hi:
        out.append("direction %s: hero photo_h %d is outside its band %d to %d" % (d["id"], ph, lo, hi))
    for r in rec[:3]:
        if r["hero_h"] and abs(int(r["hero_h"]) - ph) <= 60:
            out.append("direction %s: hero height %d repeats %s (%s)" % (d["id"], ph, r["label"], r["hero_h"]))
    if rec and rec[0]["grounds"] and _grounds(spec) == rec[0]["grounds"]:
        out.append("direction %s: the same section colours as %s" % (d["id"], rec[0]["label"]))
    return out


def compare_page(items):
    """One page, the directions side by side, from their rendered html: [(title, note, html)]."""
    cols = "".join('<div style="flex:none;width:400px"><div style="color:#fff;font:600 15px/1.3 sans-serif;margin:0 0 8px">%s</div>'
                   '<div style="color:#cbb;font:12px/1.4 sans-serif;margin:0 0 10px;min-height:34px">%s</div>%s</div>' % (t, n, h) for t, n, h in items)
    return '<!doctype html><meta charset="utf-8"><body style="margin:0;background:#222"><div style="display:flex;gap:28px;padding:24px;align-items:flex-start">%s</div>' % cols


def shape(spec):
    """A layout's skeleton: the sequence of its sections and, inside fg_block / fg_band, its item types."""
    out = []
    for s in spec.get("sections", []):
        out.append(s.get("s"))
        out += [it.get("t") for it in s.get("items", []) or [] if isinstance(it, dict)]
    return out


def similarity(a, b):
    """0 to 1: how alike two layouts' skeletons are (1 = the same order of the same blocks)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, shape(a), shape(b)).ratio()


TOO_ALIKE = 0.72


DIAGRAMS = ("infographic", "curvepanel", "steps", "statpanel", "routinepanel", "rhythm_rows", "rhythm", "prices", "zigzag", "mosaic", "trio", "stats")


def diagram_of(spec):
    """The explaining block(s) an email used (first two found), so the next email can explain a different way."""
    found = []
    for s in spec.get("sections", []):
        for it in s.get("items", []) or []:
            if isinstance(it, dict) and it.get("t") in DIAGRAMS and it["t"] not in found and it["t"] not in ("mosaic", "zigzag"):
                found.append(it["t"])
    return found[:2]


def single_text(rec):
    """The default instruction for one email: weigh the three structures privately, deliver the one the copy fits best (editor, 2026-11-20:
    'keep the three variations in your head and restructure the email from the copy; it is faster')."""
    last = [r.get("diagram") for r in rec[:3] if r.get("diagram")]
    return ("\n\nHOW TO STRUCTURE THIS EMAIL: weigh three structures privately, then deliver ONE layout, the one this copy fits best: "
            "(1) teaching-first (the idea explained step by step, then the offer); (2) offer-first (price and the ask early, the story shorter); "
            "(3) proof-first (creator stills and customers' words early, the product as the answer). Let the copy decide; do not default to the "
            "same structure as the last emails. Choose a hero type (a product still life, an abstract set, or a person who has not appeared in "
            "the recent emails) and a hero height that differ from them. "
            "Explain with a DIFFERENT kind of diagram than the recent emails used (%s): the explaining block follows the copy (a curve for a "
            "mechanism, steps for a routine, a comparison, big numbers, a timeline...), never one fixed style. Ingredients are a small "
            "supporting line or a compact list, never a big section of their own.\n"
            "RECENT EMAILS (do not repeat their hero height within 60px, their people, their set or their palette):\n%s\n"
            % (", ".join(sorted(set(sum([r.get("diagram_all", []) for r in rec[:3]], [])))) or "none yet", recent_text(rec)))


def repeat_problems(spec, rec):
    """What makes ONE layout a repeat of the brand's recent emails: the same hero height or the same section colours."""
    out, h = [], _hero(spec)
    if h:
        try:
            ph = int(h.get("photo_h"))
        except (TypeError, ValueError):
            ph = None
        for r in rec[:3]:
            if ph and r["hero_h"] and abs(int(r["hero_h"]) - ph) <= 60:
                out.append("hero height %d repeats %s (%s)" % (ph, r["label"], r["hero_h"]))
    if rec and rec[0]["grounds"] and _grounds(spec) == rec[0]["grounds"]:
        out.append("the same section colours as %s" % rec[0]["label"])
    return out
