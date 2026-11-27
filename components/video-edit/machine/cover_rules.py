#!/usr/bin/env python3
"""cover_rules.py — the three cover rules every cover passes, whoever makes it (owner ruling 2026-11-16, V57 (swipe is the backbone): the
rules live in the chain so every path gets them; the Video Studio's cover stage reads them from here).

  1. FACES       every face on a cover is checked against the ad's cast sheets (video-production face_gate). An ad
                 that names no cast sheet is refused by name; a face the judge did not answer for is not read, never
                 a miss. And the headline never sits on a face (`words_off_faces`).
  2. SIBLINGS    no two versions' covers are the same picture (`dhash`, `same_as`: SAME_AT_BITS bits apart or fewer),
                 and each version's headline is the first line of its opener its siblings do not open with, whole or
                 cut at its first clause, never mid-clause (`headline_for`).
  3. PROVEN      every cover follows a proven cover: one of the avatar's own covers in the cover index with a rated
                 move (`proven`); a cover with none is held.

Brand-agnostic: pictures and records come in as files and dicts.
"""
from __future__ import annotations

import re
from pathlib import Path

NO_MOVE = ("", "none", "as-shot", "unrated")
NAME_THE_CAST = ("name the cast: the ad names no cast sheet (brief.json `cast`), and every face on a cover is "
                 "checked against one")
SAME_AT_BITS = 8
READ_VERDICTS = ("SAME", "GROUP", "DIFFERENT")       # the face judge's answers; any other verdict is no answer


# ---------------------------------------------------------------- 3 proven
def proven(row: dict | None) -> bool:
    """Is this swipe cover a proven cover to follow: an index row whose move is rated?"""
    return bool(row) and (row.get("move") or "") not in NO_MOVE


# ---------------------------------------------------------------- 2 siblings: the picture
def dhash(picture):
    """A 64-bit difference hash of the picture, as 16 hex digits; None when it cannot be opened."""
    try:
        from PIL import Image
        with Image.open(picture) as im:
            px = list(im.convert("L").resize((9, 8)).tobytes())
    except Exception:  # noqa: BLE001
        return None
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = bits << 1 | (px[y * 9 + x] > px[y * 9 + x + 1])
    return "%016x" % bits


def apart(a, b) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def same_as(h, others, bits: int = SAME_AT_BITS):
    """The first sibling hash this picture's hash is the same picture as (bits apart or fewer), or None."""
    return next((o for o in others or [] if h and o and apart(h, o) <= bits), None)


# ---------------------------------------------------------------- 2 siblings: the headline
ABBREV = {"mr", "mrs", "ms", "mx", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "a.m", "p.m", "u.s",
          "u.k", "inc", "ltd", "co", "approx", "dept", "gen", "gov", "sen", "sgt", "capt", "col", "lt", "cmdr", "pres",
          "ave", "blvd", "jan", "feb", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"}
NUMBERED = {"no", "nos", "vol", "vols", "fig", "figs", "pg", "pp", "ch", "pt", "ep", "art", "sec"}   # abbreviations
# only before a number ("No. 1 seller"); "No." before a word is a whole line
_END = re.compile(r"(\.{2,}|…|[.?!]+)([\"'”’)\]]*)(?=\s|$)")
MIN_CLAUSE = 3


def _ends_here(words, start, m) -> bool:
    """Does the line end at this stop? An ellipsis inside a line is a pause; a full stop after an abbreviation or an
    initial is not an end."""
    stop = m.group(1)
    if stop == "…" or stop.startswith(".."):
        return not words[m.end():].strip()
    if stop == ".":
        before = words[start:m.start()].split()
        w = before[-1].lstrip("\"'“‘(") if before else ""
        if w.lower() in ABBREV or (len(w) == 1 and w.isupper() and w != "I") or re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", w):
            return False
        if w.lower() in NUMBERED and re.match(r"\s*[#\d]", words[m.end():]):
            return False
    return True


def sentences(words, whole: bool = True) -> list:
    """The lines of the words, whole: a line ends at . ? ! (with its closing quote), never at an abbreviation
    (Mr., Dr., e.g.; No., Vol., Fig. before a number), an initial or an ellipsis inside the line. whole=False: every
    . ? ! ends one."""
    words = words or ""
    if not whole:
        return [s.strip() for s in re.findall(r"[^.?!]+[.?!]*", words) if s.strip(" .?!,")]
    out, start = [], 0
    for m in _END.finditer(words):
        if _ends_here(words, start, m):
            out.append(words[start:m.end()].strip())
            start = m.end()
    out.append(words[start:].strip())
    return [x for x in out if x.strip(" .?!,…\"'")]


def balanced(s) -> bool:
    """Every quote and bracket the line opens, it closes."""
    return (s.count('"') % 2 == 0 and s.count("“") == s.count("”") and s.count("(") == s.count(")")
            and s.count("[") == s.count("]"))


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def headline_for(vid, own_words, sibling_words, limit=8, whole: bool = True):
    """(headline, why): the first line of this version's opener that its siblings do not open with, whole or cut at its
    first clause, within `limit` words. (None, why) when no whole clause fits: a line is never cut mid-clause."""
    lines = sentences(own_words, whole)
    if not lines:
        return None, "its opener has no words"
    others = [{_norm(x) for x in sentences(w, whole)} for w in sibling_words]
    shared = {_norm(x) for x in lines if others and all(_norm(x) in o for o in others)}
    pick = next((x for x in lines if _norm(x) not in shared), lines[0])
    why = ("the first line of its opener" if pick == lines[0]
           else "the first line of its opener the other versions do not say (they all open on \"%s\")" % lines[0])
    if whole and not balanced(pick):
        return None, ('its line "%s" opens a quote or bracket it does not close, so it is not a whole line; name it'
                      % pick)
    if whole and len(pick.split()) < 2:
        return None, 'its line "%s" is one word, not a headline' % pick
    if len(pick.split()) > limit:
        clause = re.split(r"(?<=[,;:])\s", pick)[0].rstrip(",;:")
        if len(clause.split()) > limit or (whole and (len(clause.split()) < MIN_CLAUSE or not balanced(clause))):
            return None, ('its line "%s" has no whole clause of %d to %d words, so it is not cut'
                          % (pick, MIN_CLAUSE, limit) if whole else
                          'its line "%s" has no whole clause within %d words, so it is not cut' % (pick, limit))
        pick = clause
        why += ", cut at its first clause (%d words)" % len(pick.split())
    return pick, why


# ---------------------------------------------------------------- 1 faces
def words_off_faces(pic, box_px, read):
    """(ok, short): the headline's box touches no face on the cover. read([picture]) -> [{"faces": [{x, y, w, h}]}]
    (fractions of the picture). None when no reader or no box."""
    if not read or not box_px:
        return None, ("no face reader on this machine" if not read
                      else "the image tool's record gives no words box to check against the faces")
    try:
        from PIL import Image
        with Image.open(pic) as im:
            w, h = im.size
        faces = (read([Path(pic)]) or [{}])[0].get("faces") or []
    except (Exception, SystemExit) as e:  # noqa: BLE001
        return None, "not read (%s)" % type(e).__name__
    l, t, r, b = box_px
    for f in faces:
        fl, ft = float(f["x"]) * w, float(f["y"]) * h
        fr, fb = fl + float(f["w"]) * w, ft + float(f["h"]) * h
        if min(r, fr) > max(l, fl) and min(b, fb) > max(t, ft):
            return False, "the headline sits on a face"
    return True, "%d face(s), none under the words" % len(faces)


def who(p):
    return Path(str(p.get("master", "?"))).parent.parent.name


def not_read(verdict) -> bool:
    """A verdict that is not one of the judge's answers (UNCHECKED, empty, unknown): the face was not read."""
    return str(verdict or "").strip().upper() not in READ_VERDICTS


def unanswered(rec) -> bool:
    """The record's only misses are faces the judge did not answer for: not read, not a miss, so no remake is bought."""
    people = rec.get("people") or []
    misses = [p.get("verdict") for p in people if p.get("verdict") not in ("SAME", "GROUP")]
    return bool(misses) and all(not_read(v) for v in misses)


def faces_against_cast(pic, masters, check, unread: bool = True):
    """(ok, short): every face on the cover against the ad's cast sheets. check(picture, masters) -> the face gate's
    record {"pass", "people": [{"master", "verdict"}]}. None when the ad names no cast sheet, and (unread=True) when the
    check stopped or the judge did not answer."""
    if not masters:
        return None, NAME_THE_CAST
    try:
        rec = check(pic, masters)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        why = str(e)[:200] or type(e).__name__
        return (None, "the face check stopped (%s)" % why) if unread else (False, why)
    if not isinstance(rec, dict):
        return (None, "the face check gave no record") if unread else (False, "the face check gave no record")
    if rec.get("pass"):
        return True, "%d face(s) match the cast" % len(rec.get("people") or [])
    if unread and unanswered(rec):
        return None, "the face judge did not answer for %s" % ", ".join(
            who(p) for p in rec.get("people") or [] if not_read(p.get("verdict")))[:180]
    bad = [p for p in rec.get("people") or [] if p.get("verdict") not in ("SAME", "GROUP")]
    return False, "; ".join("%s %s" % (Path(str(p.get("master", "?"))).parent.parent.name, p.get("verdict"))
                            for p in bad)[:200] or "no face confirmed"


def face_gate_check(face_gate, unread: bool = True):
    """The default check for faces_against_cast from video-production's face_gate module: a record for these exact
    bytes is reused, unless the judge did not answer."""
    def check(p, m):
        rec = face_gate.read(p)
        if not rec or (unread and unanswered(rec)):
            rec = face_gate.stamp(p, m)
        return rec
    return check


def rules_md() -> list[str]:
    """The three rules as the video editor reads them in the hand-off's edit notes (editor_handoff.edit_notes_md)."""
    return ["## Covers", "",
            "- **Faces**: every face on a cover is one of the ad's cast. The headline never sits on a face.",
            "- **Siblings**: no two versions' covers are the same picture. Each version's headline is the first line of "
            "its opener the other versions do not open with, whole or cut at its first clause, never mid-clause.",
            "- **Proven**: every cover follows a proven cover, one of the avatar's own covers with a rated move.", ""]
