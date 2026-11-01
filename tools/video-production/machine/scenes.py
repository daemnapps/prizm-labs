#!/usr/bin/env python3
"""
scenes.py — read the AI brief's scenes into something a tool can act on.

The brief is written for a person. This turns it into rows: one per scene,
each knowing its setting, its section, the PARAGRAPH it speaks, and the
FRAMES it plays out across. Nothing is invented here — a field the brief did
not write comes back empty, because a storyboard that fills its own gaps
hides the ones worth fixing.

TWO SHAPES, ONE OUTPUT (2026-09-18).

  * **The scene shape** (v8 briefs). A scene is one setting, one section of
    the argument, one paragraph of voice, and ONE clip — with exactly TWO
    stills: a FIRST FRAME written in full in the stills order, and a LAST
    FRAME written as a delta from it. What happens between them is BEATS —
    timed spans written into the clip prompt's own timeline, one verb each,
    never generated as pictures (the owner, 2026-09-18).

        **Scene 3 · BATHROOM COUNTER**

  * **The old shape** (v7 and earlier), still parsed so every run already on
    disk still renders. A scene there is one still and one line, so it comes
    back as exactly that: one frame, one line.

        **Scene 3 · 0:09–0:14 · 5s · TYPE A**

Both come back in the same shape, so nothing downstream has to know which
brief it was handed.

THE BRIEF IS THE PROMPT (the owner, 2026-09-19: "this brief is for the AI system
to interpret, not for me as the human to read — format these briefs in a way
that AI is able to directly build what it needs to build").

So a current brief carries its truth as the LAST fenced json block in it, in
the shape `machine/model-inputs.json` names as `brief_schema`. That block is
read FIRST and the prose is never parsed: the Markdown above it is the
readable view for a person, rendered from these same fields. A brief with no
block at all is an older one and falls back to the Markdown parse above, so
every run already on disk still renders.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# ---------------------------------------------------------------- heads

# the old shape — start, end, seconds, type
HEAD_TIMED = re.compile(
    r"^\*\*Scene\s+(\d+)\s*·\s*([0-9:.]+)\s*[–-]\s*([0-9:.]+)\s*·\s*([\d.]+)s"
    r"\s*·\s*TYPE\s+([ABC])\*\*", re.M)
# the scene shape — a number and a setting, and nothing that is a length
HEAD_SCENE = re.compile(r"^\*\*Scene\s+(\d+)\s*·\s*([^*\n]+?)\s*\*\*\s*$", re.M)

FIELDS = {
    "source": r"^\*\*Source:\*\*\s*(.+)$",
    "who": r"^\*\*Who:\*\*\s*(.+?)(?:\s*·|\s*$)",
    "still": r"\*\*Still:\*\*\s*(.+)$",
    "happens": r"^\*\*Happens:\*\*\s*(.+)$",
    "camera": r"^\*\*Camera:\*\*\s*(.+)$",
    "refs": r"^\*\*Refs:\*\*\s*(.+)$",
    "hear": r"^\*\*Hear:\*\*\s*(.+)$",
    "product": r"^\*\*Product:\*\*\s*(.+)$",
    "delivery": r"^\*\*Delivery:\*\*\s*(.+)$",
    "on_screen": r"^\*\*On screen:\*\*\s*(.+)$",
    "hold": r"^\*\*Hold:\*\*\s*(.+)$",
    "section": r"\*\*Section:\*\*\s*(.+?)(?:\s*·\s*\*\*|\s*$)",
    "technique": r"\*\*Technique:\*\*\s*(.+?)(?:\s*·\s*\*\*|\s*$)",
    "emotion": r"\*\*Emotion:\*\*\s*(.+?)(?:\s*·\s*\*\*|\s*$)",
    "outcome": r"\*\*Outcome:\*\*\s*(.+?)(?:\s*·\s*\*\*|\s*$)",
    "setting": r"^\*\*Setting:\*\*\s*(.+)$",
    "to_camera": r"\*\*To camera:\*\*\s*(.+?)(?:\s*·|\s*$)",
    # B-ROLL IS A SCENE, NOT AN INSERT (2026-09-19). A brief that still lists
    # cutaways under a scene is read, not ignored — the gate refuses it by
    # name, which is how the writer finds out rather than the editor.
    "cutaways": r"^\*\*Cutaways:\*\*\s*(.+)$",
}

SAY = re.compile(r"^>\s*\*\*Say:\*\*\s*(.+(?:\n>.*)*)", re.M)
VOICE = re.compile(r"^>\s*\*\*Voice:\*\*\s*(.+(?:\n>.*)*)", re.M)

# the two frame blocks — **FIRST FRAME** and **LAST FRAME**, each on its own
# line, optionally numbered (**F1 · FIRST FRAME**) so an old file still reads
FRAME_HEAD = re.compile(
    r"^\*\*(?:F(\d+)\s*·\s*)?(FIRST FRAME|LAST FRAME)\*\*\s*$", re.M)
FRAME_FIELDS = {
    "subject": r"^\*\*Subject:\*\*\s*(.+)$",
    "composition": r"^\*\*Composition:\*\*\s*(.+)$",
    "action": r"^\*\*Action:\*\*\s*(.+)$",
    "location": r"^\*\*Location:\*\*\s*(.+)$",
    "style": r"^\*\*Style:\*\*\s*(.+)$",
    "camera": r"^\*\*Camera:\*\*\s*(.+)$",
    "viewpoint": r"^\*\*Viewpoint:\*\*\s*(.+)$",
    "lighting": r"^\*\*Lighting:\*\*\s*(.+)$",
    "delta": r"^\*\*Change:\*\*\s*(.+)$",
    "beat": r"^\*\*Beat:\*\*\s*(.+)$",
}
FRAME_REFS = re.compile(r"^\*\*Refs:\*\*\s*(.+)$", re.M)

# a beat — one line, one verb, its span from the timing sheet:
#   - **B2** · **At:** 3.18–4.55 · **Do:** … · **Camera:** … · **Over:** "…" · **Beat:** …
BEAT_LINE = re.compile(r"^[-*]\s*\*\*B(\d+)\*\*\s*(.+)$", re.M)
BEAT_FIELD = re.compile(r"\*\*([A-Za-z ]+):\*\*\s*([^·\n]+)")
SPAN = re.compile(r"([0-9]*\.?[0-9]+)\s*[–-]\s*([0-9]*\.?[0-9]+)")

PIECE = {
    "aspect": r"^\*\*Aspect:\*\*\s*(.+)$",
    "resolution": r"^\*\*Resolution:\*\*\s*(.+)$",
    "style": r"^\*\*Style:\*\*\s*(.+)$",
}


def secs(t: str) -> float:
    parts = [float(p) for p in str(t).split(":")]
    out = 0.0
    for p in parts:
        out = out * 60 + p
    return out


def _quote(block: str) -> str:
    """A blockquote's text, with the markers off and the wrapping undone."""
    text = re.sub(r"^>\s?", "", block or "", flags=re.M)
    return " ".join(text.split()).strip().strip('"').strip("—").strip()


def _one(body: str, pat: str) -> str:
    m = re.search(pat, body, re.M)
    return m.group(1).strip() if m else ""


def _yes(v: str) -> bool:
    return str(v).strip().lower() in ("yes", "true", "y", "to camera", "on")


# ---------------------------------------------------------------- frames

def frames_of(body: str) -> list[dict]:
    """The scene's two frames — the first and the last — in order. A scene
    has exactly these two; everything between them is a beat, not a picture
    (the owner, 2026-09-18)."""
    heads = list(FRAME_HEAD.finditer(body))
    out: list[dict] = []
    for i, m in enumerate(heads):
        chunk = body[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(body)]
        # a beat list under the first frame is not part of it
        chunk = BEAT_LINE.split(chunk)[0]
        label = (m.group(2) or "").strip().upper()
        role = "first" if "FIRST" in label else "last"
        fr = {"n": int(m.group(1)) if m.group(1) else (1 if role == "first" else 2),
              "role": role, "label": label}
        for key, pat in FRAME_FIELDS.items():
            fr[key] = _one(chunk, pat)
        refs = FRAME_REFS.search(chunk)
        fr["refs"] = [r.strip() for r in re.split(r"\s*·\s*|\s*;\s*", refs.group(1))
                      if r.strip()] if refs else []
        out.append(fr)
    return out


def beats_of(body: str) -> list[dict]:
    """Every beat in a scene body, in order: its span off the timing sheet,
    the one action it names, the camera only where it moves, the words
    playing over it and the feeling it carries."""
    out = []
    for m in BEAT_LINE.finditer(body):
        fields = {k.strip().lower(): v.strip()
                  for k, v in BEAT_FIELD.findall(m.group(2))}
        span = SPAN.search(fields.get("at", ""))
        out.append({
            "n": int(m.group(1)),
            "at": [float(span.group(1)), float(span.group(2))] if span else None,
            "do": fields.get("do", ""),
            "camera": fields.get("camera", ""),
            "over": fields.get("over", "").strip().strip('"“”'),
            "beat": fields.get("beat", ""),
        })
    return out


def _frames_from_old(sc: dict) -> list[dict]:
    """The old shape, in the new one: a scene with one Still and one Say is
    one frame and one line. Nothing is invented — the still's own sentence
    is the frame's action, and every slot the old brief never wrote stays
    empty."""
    still = sc.get("still") or sc.get("happens") or sc.get("product") or ""
    return [{
        "n": 1, "role": "first", "label": "FIRST FRAME",
        "subject": sc.get("who", ""), "composition": "", "action": still,
        "location": "", "style": "", "camera": sc.get("camera", ""),
        "lighting": "", "delta": "", "beat": sc.get("emotion", ""),
        "refs": [r.strip() for r in
                 re.split(r"\s*·\s*|\s*,\s*", sc.get("refs", "")) if r.strip()],
    }]


# ------------------------------------------------------------- the block
#
# THE BRIEF IS THE PROMPT. Everything below reads the brief's own json block
# — the shape `model-inputs.json` holds as `brief_schema` — into exactly the
# rows the Markdown parser produces, so nothing downstream can tell which
# door a brief came through.

FENCE = re.compile(r"```[ \t]*([a-zA-Z0-9_+-]*)[ \t]*\r?\n(.*?)```", re.S)


def json_block(text: str):
    """The LAST fenced json block in a brief, parsed -> (value, reason).

    The same rule the teardown chain reads its stage blocks by: the last
    block wins, an untagged fence still counts if it parses, and nothing
    raises — an unparseable block is a finding the gate names, not a run
    lost."""
    blocks = FENCE.findall(text or "")
    if not blocks:
        return None, "no fenced block in the brief"
    tagged = [b for lang, b in blocks if lang.lower() == "json"]
    why = ""
    for body in reversed(tagged or [b for _, b in blocks]):
        try:
            return json.loads(body), None
        except Exception as e:
            why = why or f"{type(e).__name__}: {e}"
    return None, why or "no fenced block parsed as json"


def _n_of(sid, i: int) -> int:
    m = re.search(r"(\d+)", str(sid or ""))
    return int(m.group(1)) if m else i


def _delivery_line(d) -> str:
    """The four dials as one line, the way a scene has always carried them."""
    if isinstance(d, dict):
        return " · ".join(str(d.get(k, "")).strip()
                          for k in ("humor", "style", "register", "pacing"))
    return _one_line(d)


def _one_line(v) -> str:
    return " ".join(str(v or "").split())


def _frames_from_block(row: dict) -> list[dict]:
    """The scene's TWO stills, out of the block: the first frame written in
    full, the last written as its delta and nothing else."""
    ff = row.get("first_frame") or {}
    lf = row.get("last_frame") or {}
    refs = ff.get("refs")
    first = {"n": 1, "role": "first", "label": "FIRST FRAME",
             "delta": "", "beat": _one_line(ff.get("bracket")),
             "refs": [_one_line(r) for r in refs if _one_line(r)]
                     if isinstance(refs, list) else
                     [r.strip() for r in re.split(r"\s*·\s*|\s*;\s*",
                                                 str(refs or "")) if r.strip()]}
    for key in ("subject", "composition", "action", "location", "style",
                "camera", "viewpoint", "lighting"):
        first[key] = _one_line(ff.get(key))
    last = {"n": 2, "role": "last", "label": "LAST FRAME",
            "subject": "", "composition": "", "action": "", "location": "",
            "style": "", "lighting": "", "refs": [],
            "camera": _one_line(lf.get("camera")),
            "delta": _one_line(lf.get("change")),
            "beat": _one_line(lf.get("bracket"))}
    return [first, last]


def _beats_from_block(row: dict) -> list[dict]:
    out = []
    for i, b in enumerate(row.get("beats") or [], 1):
        if not isinstance(b, dict):
            continue
        at = b.get("at")
        out.append({
            "n": _n_of(b.get("id"), i),
            "at": [float(at[0]), float(at[1])]
                  if isinstance(at, (list, tuple)) and len(at) == 2 else None,
            "do": _one_line(b.get("do")),
            "camera": _one_line(b.get("camera")),
            "over": _one_line(b.get("over")).strip('"“”'),
            "beat": _one_line(b.get("bracket")),
        })
    return out


def scenes_from_block(doc: dict) -> list[dict]:
    """The block's scenes, as the rows every tool here already reads. A
    B-roll scene (`to_camera: false`) is a scene like any other — its own
    setting, its own frames, its own beats — and the paragraph in its
    `voice` is the slice of the one read that plays OVER it."""
    out = []
    for i, row in enumerate(doc.get("scenes") or [], 1):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or f"S{i}")
        kind = _one_line(row.get("kind")).lower()
        if kind == "card":
            out.append(_carry_element_fields(_card_from_block(row, sid, i), row))
            continue
        if kind in PLATE_KINDS:
            out.append(_carry_element_fields(_plate_kind_from_block(row, sid, i, kind), row))
            continue
        if kind == "split":
            worlds = [_one_line(w.get("id")) for w in doc.get("world") or []
                      if isinstance(w, dict) and _one_line(w.get("id"))]
            out.append(_carry_element_fields(_split_from_block(row, sid, i, worlds), row))
            continue
        # TO CAMERA IS SAID, NEVER GUESSED (the owner, 2026-09-23). A scene that
        # does not carry it is marked, and the gate refuses it by id before
        # anything is made; it is planned as B-roll only so nothing
        # downstream crashes on the way to that refusal.
        to_camera_missing = "to_camera" not in row
        to_camera = bool(row.get("to_camera"))
        sc = {
            "n": _n_of(sid, i), "id": sid, "shape": "scene",
            "start": None, "end": None, "seconds": 0.0,
            "type": "A" if to_camera else "B",
            "section": _one_line(row.get("section")),
            "technique": _one_line(row.get("technique")),
            "delivery": _delivery_line(row.get("delivery")),
            "emotion": _one_line(row.get("emotion")),
            "outcome": _one_line(row.get("outcome")),
            "setting": _one_line(row.get("setting_id")),
            "who": _one_line(row.get("who")),
            "to_camera": to_camera,
            "voice": _one_line(row.get("voice")),
            # THE SPOKEN PASS (2026-09-19): the brief may carry, per scene,
            # the voice-model settings the register recipe put on it
            # (stability / style / speed within the recipe's range). voice.py
            # lays them over the cast voice's own record for that chunk.
            "voice_settings": dict(row.get("voice_settings") or {})
            if isinstance(row.get("voice_settings"), dict) else {},
            # A SUNG PIECE (brief v16, 2026-09-23): the lines sung over this
            # scene, verbatim — the script song.py checks every lyric against.
            "lyrics": [_one_line(x) for x in row.get("lyrics") or [] if _one_line(x)]
            if isinstance(row.get("lyrics"), list) else [],
            "source": _one_line(row.get("source")),
            "happens": _one_line(row.get("happens")),
            "on_screen": _one_line(row.get("on_screen")),
            "hold": _one_line(row.get("hold")),
            "still": "", "camera": "", "refs": "", "hear": "", "product": "",
            # A HELD SCENE has no frames and no beats to have — there is
            # nothing to describe until the fact that releases it arrives.
            "frames": [] if _one_line(row.get("held")) else _frames_from_block(row),
            "beats": [] if _one_line(row.get("held")) else _beats_from_block(row),
        }
        sc["say"] = sc["voice"]
        if to_camera_missing and not _one_line(row.get("held")):
            sc["to_camera_missing"] = True
        # A HELD SCENE keeps its place and makes nothing (2026-09-19): the
        # brand's own files could not fill it, and the one fact that would
        # release it is written here rather than invented.
        sc["held"] = _one_line(row.get("held"))
        if "cutaways" in row:
            sc["cutaways"] = row["cutaways"]
        sc["needs"] = ("a still of the speaker, then lip-sync to the voice take"
                       if to_camera else
                       "two stills and one clip — the voice plays over it")
        sc["status"] = "empty"
        sc["takes"] = []
        if kind in ("talking", "broll", "greenscreen"):
            sc["kind"] = kind
        if kind == "greenscreen":
            # A GREENSCREEN IS A TALKING SCENE (brief v14): its own frames,
            # beats and voice make the presenter's clip; the background is one
            # more still, and the edit keys the one over the other.
            g = kind_fields(row, "greenscreen")
            sc["greenscreen"] = {"background": _one_line(g.get("background")),
                                 "talker_scene": _one_line(g.get("talker_scene")) or sid,
                                 "layout": _one_line(g.get("layout")),
                                 "refs": _refs((row.get("greenscreen") or {}).get("refs"))
                                 if isinstance(row.get("greenscreen"), dict) else []}
            sc["needs"] += "; plus one background still, keyed behind it at the edit"
        out.append(_carry_element_fields(sc, row))
    return out


# ------------------------------------------------ the element kinds
#
# ELEMENTS.md §1 (2026-09-23): "teardown names every element, the AI brief
# carries it, PRODUCTION MAKES IT, the edit only assembles." Beyond the
# speaker, B-roll and the card, a scene may be a SCREEN (a plate of a review,
# a comment, an order page — the legible text is set by the edit), a SPLIT
# (two B-roll pictures side by side), a GREENSCREEN (a background plate the
# presenter's talking scene is keyed over) or an ENDCARD (the brand's REAL
# packshot, edited into a plate; the offer words set on top). Each kind's
# fields may sit on the scene or nested under the kind's own name.

PLATE_KINDS = ("screen", "endcard")
ELEMENT_FIELDS = ("opens", "priority")


def _module_renames() -> dict:
    """v14's retired `module` → the doctrine section id it stood for. The map
    lives in model-inputs.json (`elements.module_deprecated`), never here."""
    try:
        c = json.loads((Path(__file__).resolve().parent / "model-inputs.json").read_text())
        return ((c.get("elements") or {}).get("module_deprecated") or {}).get("renames") or {}
    except (OSError, ValueError):
        return {}


def _carry_element_fields(sc: dict, row: dict) -> dict:
    """`opens` and `priority` travel on every scene, untouched, for the edit
    (the scroll-stopper, the order a cutdown cuts in); the scene's `section`
    — a doctrine id — is the unit a version swaps. Absent stays absent. A v14
    brief's retired `module` fills a MISSING section, never overrides one
    (the gate warns about it)."""
    for k in ELEMENT_FIELDS:
        if k in row:
            sc[k] = row[k]
    if "module" in row and not _one_line(sc.get("section")):
        v = _one_line(row.get("module")).lower()
        sc["section"] = _module_renames().get(v, v)
    return sc


def kind_fields(row: dict, kind: str) -> dict:
    """The kind's fields, whether written flat on the scene (the card's
    shape) or nested under the kind's name (ELEMENTS.md's shape)."""
    nested = row.get(kind)
    return {**row, **nested} if isinstance(nested, dict) else dict(row)


def _lines(v) -> list[str]:
    if isinstance(v, list):
        return [_one_line(x) for x in v if _one_line(x)]
    return [_one_line(v)] if _one_line(v) else []


def _refs(v) -> list[str]:
    if isinstance(v, list):
        return [_one_line(r) for r in v if _one_line(r)]
    return [r.strip() for r in re.split(r"\s*·\s*|\s*;\s*", str(v or "")) if r.strip()]


def _still_only(row: dict, sid: str, i: int, kind: str, typ: str, needs: str) -> dict:
    voice = _one_line(row.get("voice"))
    return {
        "n": _n_of(sid, i), "id": sid, "shape": "scene", "kind": kind,
        "start": None, "end": None, "seconds": 0.0, "type": typ,
        "section": _one_line(row.get("section")),
        "technique": "", "delivery": "", "emotion": "", "outcome": "",
        "setting": "", "who": "", "to_camera": False,
        "voice": voice, "say": voice, "voice_settings": {},
        "source": _one_line(row.get("source")),
        "happens": "", "on_screen": "", "hold": "",
        "still": "", "camera": "", "refs": "", "hear": "", "product": "",
        "frames": [], "beats": [], "held": "",
        "needs": needs, "status": "empty", "takes": [],
    }


ROLL_LETTER = {"screen": "S", "greenscreen": "G", "endcard": "E", "split": "X"}


def _plate_kind_from_block(row: dict, sid: str, i: int, kind: str) -> dict:
    """SCREEN · GREENSCREEN · ENDCARD — one still each and no clip. What the
    still IS comes from the kind's own field (`plate`, or a greenscreen's
    `background`); every word that will be read on it travels as data."""
    f = kind_fields(row, kind)
    needs = {"screen": "one still — the screen, its words left blank; the edit sets them",
             "endcard": "one edit of the brand's REAL packshot; the edit sets the offer"}[kind]
    sc = _still_only(row, sid, i, kind, ROLL_LETTER[kind], needs)
    if kind == "screen":
        sc["screen"] = {"plate": _one_line(f.get("plate")),
                        "surface": _one_line(f.get("surface")).lower(),
                        "lines": _lines(f.get("lines")),
                        "lands_on": _one_line(f.get("lands_on")),
                        "refs": _refs(f.get("refs"))}
    else:
        sc["endcard"] = {"plate": _one_line(f.get("plate")),
                         "product": _one_line(f.get("product")),
                         "offer_lines": _lines(f.get("offer_lines")),
                         "cta": _one_line(f.get("cta")),
                         "guarantee": _one_line(f.get("guarantee")),
                         "refs": _refs(f.get("refs"))}
        sc["product"] = sc["endcard"]["product"]
    return sc


def _side_setting(side: dict, row: dict, worlds: list[str]) -> str:
    """A split side's place: its own setting_id, the split's, else the world
    block its first frame's location names (the brief v14 writes a side as
    first_frame · beats · last_frame only). Read, never invented."""
    own = _one_line(side.get("setting_id") or row.get("setting_id"))
    if own:
        return own
    loc = _one_line((side.get("first_frame") or {}).get("location"))
    for w in sorted(worlds, key=len, reverse=True):
        if w and w.lower() in loc.lower():
            return w
    return loc.split(",")[0].strip()


def _side_who(side: dict, row: dict) -> str:
    own = _one_line(side.get("who") or row.get("who"))
    if own:
        return own
    subj = _one_line((side.get("first_frame") or {}).get("subject"))
    return subj.split(",")[0].strip()


def _split_side(side, sid: str, letter: str, row: dict, worlds=()) -> dict:
    """One side of a split — a B-roll picture in its own right: a setting,
    its two frames and its beats. Its id is the split's plus L or R."""
    side = side if isinstance(side, dict) else {}
    return {
        "n": 0, "id": f"{sid}-{letter}", "shape": "scene", "kind": "split-side",
        "start": None, "end": None, "seconds": 0.0, "type": "B",
        "section": _one_line(row.get("section")),
        "technique": _one_line(side.get("technique") or row.get("technique")),
        "delivery": _delivery_line(side.get("delivery") or row.get("delivery")),
        "emotion": _one_line(side.get("emotion") or row.get("emotion")),
        "outcome": _one_line(side.get("outcome") or row.get("outcome")),
        "setting": _side_setting(side, row, list(worlds)),
        "who": _side_who(side, row),
        "to_camera": False, "voice": "", "say": "", "voice_settings": {},
        "source": "", "happens": _one_line(side.get("happens")), "on_screen": "", "hold": "",
        "still": "", "camera": "", "refs": "", "hear": "", "product": "",
        "frames": _frames_from_block(side), "beats": _beats_from_block(side),
        "held": "",
    }


def _split_from_block(row: dict, sid: str, i: int, worlds=()) -> dict:
    """SPLIT — two B-roll pictures on one screen. Each side is made like
    B-roll (a first frame, a last frame, one silent clip); the scene's own
    voice paragraph is laid under both at the edit, once."""
    f = kind_fields(row, "split")
    sc = _still_only(row, sid, i, "split", "X",
                     "two B-roll pictures — first and last frame and one silent clip a side")
    sc["split"] = {"left": _split_side(f.get("left"), sid, "L", row, worlds),
                   "right": _split_side(f.get("right"), sid, "R", row, worlds),
                   "layout": _one_line(f.get("layout")).lower(),
                   "labels": _lines(f.get("labels"))}
    return sc


def _card_from_block(row: dict, sid: str, i: int) -> dict:
    """A CARD (the owner, 2026-09-23: cards are handled at production, not left
    for the edit). Type is a layer, never a generation: the machine makes the
    PLATE — the picture with no words in it — as one still and no clip, and
    the card's exact words, the moment they land on and the sound they come
    in on travel in `card` for the edit to set on top. Its fields may sit on
    the scene (v13) or nested as `card: {...}` (ELEMENTS.md) — both read the
    same."""
    row = kind_fields(row, "card")
    refs = row.get("refs")
    lines = row.get("lines")
    card = {
        "plate": _one_line(row.get("plate")),
        "lines": [_one_line(l) for l in lines] if isinstance(lines, list)
                 else ([_one_line(lines)] if _one_line(lines) else []),
        "lands_on": _one_line(row.get("lands_on")),
        "sfx": _one_line(row.get("sfx")),
        "refs": [_one_line(r) for r in refs if _one_line(r)]
                if isinstance(refs, list) else
                [r.strip() for r in re.split(r"\s*·\s*|\s*;\s*", str(refs or "")) if r.strip()],
    }
    voice = _one_line(row.get("voice"))
    return {
        "n": _n_of(sid, i), "id": sid, "shape": "scene", "kind": "card",
        "start": None, "end": None, "seconds": 0.0, "type": "C",
        "section": _one_line(row.get("section")),
        "technique": "", "delivery": "", "emotion": "", "outcome": "",
        "setting": "", "who": "", "to_camera": False,
        "voice": voice, "say": voice, "voice_settings": {},
        "source": _one_line(row.get("source")),
        "happens": "", "on_screen": "", "hold": "",
        "still": "", "camera": "", "refs": "", "hear": "", "product": "",
        "frames": [], "beats": [], "held": "",
        "card": card,
        "needs": "one still — the plate, no words in it; the edit sets the card's words on it",
        "status": "empty", "takes": [],
    }


def piece_from_block(doc: dict) -> dict:
    """Aspect, resolution and the one grade sentence — declared once for the
    piece and never on a scene. The grade is the words every FIRST FRAME
    carries, so a block that does not state it takes them from the first
    scene rather than leaving the summary sentence a slot short."""
    p = doc.get("piece") or {}
    style = _one_line(p.get("style"))
    if not style:
        for row in doc.get("scenes") or []:
            style = _one_line(((row or {}).get("first_frame") or {}).get("style"))
            if style:
                break
    return {"aspect": _one_line(p.get("aspect_ratio") or p.get("aspect")),
            "resolution": _one_line(p.get("resolution")),
            "style": style,
            # an ad-framework id from the doctrine, or "observed — …" (v15)
            "framework": _one_line(p.get("framework"))}


def render_view(doc: dict) -> str:
    """The human view of a brief, rendered FROM the block — the same fields,
    read the way a person reads. Nothing parses this: it exists so the page
    a person opens and the prompt a door receives can never be two different
    documents."""
    p = doc.get("piece") or {}
    L = [f"# {_one_line(p.get('title')) or 'the piece'}", ""]
    L += [f"**Lane:** {_one_line(doc.get('lane'))} · "
          f"**Format:** {_one_line(p.get('format'))} · "
          f"**Aspect:** {_one_line(p.get('aspect_ratio'))} · "
          f"**Resolution:** {_one_line(p.get('resolution'))}",
          f"**Avatar:** {_one_line(p.get('avatar'))} / {_one_line(p.get('sub'))} · "
          f"**Awareness:** {_one_line(p.get('awareness'))} · "
          f"**Sophistication:** {_one_line(p.get('sophistication'))} · "
          f"**Framework:** {_one_line(p.get('framework'))}",
          "",
          "*Rendered from this brief's json block, which is the brief. "
          "Nothing downstream reads these words.*", ""]
    if doc.get("cast"):
        L += ["## The cast", ""]
        for c in doc["cast"]:
            L.append(f"**{_one_line(c.get('name'))}** — {_one_line(c.get('identity_block'))}")
            L.append("")
    if doc.get("world"):
        L += ["## The world", ""]
        for w in doc["world"]:
            L.append(f"**{_one_line(w.get('id'))}** — {_one_line(w.get('description'))}")
            L.append("")
    if doc.get("product_lock"):
        L += ["## Product lock", ""]
        for row in doc["product_lock"]:
            L.append(f"- {_one_line(row if isinstance(row, str) else json.dumps(row))}")
        L.append("")
    L += ["## The scenes", ""]
    for sc in scenes_from_block(doc):
        kind = "to camera" if sc["to_camera"] else "B-ROLL — the voice plays over it"
        if sc.get("kind") == "card":
            c = sc["card"]
            L.append(f"**{sc['id']} · CARD** — made at production as a plate; "
                     f"the edit sets the words on it")
            L.append("")
            L.append(f"**Plate:** {c['plate']}")
            L.append(f"**Words:** {' / '.join(c['lines'])}")
            L.append(f"**Lands on:** {c['lands_on']} · **Sound:** {c['sfx'] or 'none'}")
            if sc["voice"]:
                L.append(f"> {sc['voice']}")
            L.append("")
            continue
        if sc.get("kind") in ("screen", "endcard", "split"):
            L += _kind_view(sc)
            continue
        if sc.get("to_camera_missing"):
            kind = "NO TO_CAMERA — refused until the brief says which"
        if sc.get("held"):
            kind = "HELD — nothing is made for it yet"
        if sc.get("kind") == "greenscreen":
            g = sc["greenscreen"]
            kind = (f"GREENSCREEN ({g['layout'] or '?'}) — to camera, keyed over a "
                    f"background plate: {g['background']}")
        L.append(f"**{sc['id']} · {sc['setting']}** — {kind}")
        if sc.get("held"):
            L.append("")
            L.append(f"> Held. Released by: {sc['held']}")
            L.append("")
            continue
        L.append("")
        L.append(f"**Section:** {sc['section']} · **Technique:** {sc['technique']} · "
                 f"**Emotion:** {sc['emotion']} · **Outcome:** {sc['outcome']}")
        L.append(f"**Who:** {sc['who']} · **Delivery:** {sc['delivery']}")
        L.append("")
        L.append(f"> {sc['voice']}")
        L.append("")
        first = next((f for f in sc["frames"] if f["role"] == "first"), {})
        last = next((f for f in sc["frames"] if f["role"] == "last"), {})
        L.append(f"**First frame.** {first.get('subject', '')} "
                 f"{first.get('composition', '')} {first.get('action', '')}")
        for b in sc["beats"]:
            L.append(f"- **B{b['n']}** {b['do']}"
                     + (f" — “{b['over']}”" if b["over"] else "")
                     + (f" [{b['beat']}]" if b["beat"] else ""))
        L.append(f"**Last frame.** {last.get('camera', '')} — {last.get('delta', '')}")
        L.append("")
    L += _piece_elements_view(doc)
    rows = doc.get("roll_sheet")
    if isinstance(rows, list) and rows:
        L += ["## Roll sheet check", "",
              "| Swipe row | Roll | Our scene | Or dropped, because |",
              "|---|---|---|---|"]
        for r in rows:
            if isinstance(r, dict):
                L.append(f"| {_one_line(r.get('row'))} | {_one_line(r.get('roll'))} | "
                         f"{_one_line(r.get('scene'))} | {_one_line(r.get('dropped'))} |")
        L.append("")
    return "\n".join(L)


def _kind_view(sc: dict) -> list[str]:
    tag = " · ".join(f"{k} {sc[k]}" for k in ("section",) + ELEMENT_FIELDS
                     if _one_line(sc.get(k)) or k in ELEMENT_FIELDS and k in sc)
    head = f"**{sc['id']} · {sc['kind'].upper()}**" + (f" ({tag})" if tag else "")
    L = []
    if sc["kind"] == "screen":
        s = sc["screen"]
        L += [f"{head} — a {s['surface'] or '?'} screen, made as a plate; the edit sets its words",
              "", f"**Plate:** {s['plate']}", f"**Words:** {' / '.join(s['lines'])}",
              f"**Lands on:** {s['lands_on']}"]
    elif sc["kind"] == "endcard":
        e = sc["endcard"]
        L += [f"{head} — the REAL packshot of {e['product'] or '?'}, edited into a plate",
              "", f"**Plate:** {e['plate']}", f"**Offer:** {' / '.join(e['offer_lines'])}",
              f"**CTA:** {e['cta']} · **Guarantee:** {e['guarantee'] or 'none'}"]
    else:
        x = sc["split"]
        L += [f"{head} — {x['layout'] or '?'}, two B-roll pictures"
              + (f"; labels {' / '.join(x['labels'])}" if x["labels"] else ""), ""]
        for side in ("left", "right"):
            s = x[side]
            first = next((f for f in s["frames"] if f["role"] == "first"), {})
            last = next((f for f in s["frames"] if f["role"] == "last"), {})
            L.append(f"**{side.title()} ({s['id']}) · {s['setting']}** — "
                     f"{first.get('subject', '')} {first.get('action', '')}")
            for b in s["beats"]:
                L.append(f"- **B{b['n']}** {b['do']}")
            L.append(f"**Last frame.** {last.get('camera', '')} — {last.get('delta', '')}")
    if sc.get("voice"):
        L.append(f"> {sc['voice']}")
    L.append("")
    return L


def _piece_elements_view(doc: dict) -> list[str]:
    """Layers, sound and versions — carried for the edit, shown here so the
    person reading the brief sees every element it names."""
    L = []
    for key, title in (("layers", "Layers — set by the edit"), ("music", "Music"),
                       ("sfx", "Sound effects"), ("hooks", "Hooks — one render each")):
        v = doc.get(key)
        if v in (None, "", [], {}):
            continue
        L += [f"## {title}", ""]
        if key == "music" and isinstance(v, dict):
            L.append(f"energy {v.get('energy', '?')} · {v.get('tempo_bpm', '?')} bpm · "
                     f"{v.get('mood', '?')}")
        elif key == "layers" and isinstance(v, dict):
            for k, x in v.items():
                L.append(f"- **{k}**: {json.dumps(x, ensure_ascii=False)}")
        elif isinstance(v, list):
            for x in v:
                L.append(f"- {json.dumps(x, ensure_ascii=False)}")
        else:
            L.append(json.dumps(v, ensure_ascii=False))
        L.append("")
    return L


# ---------------------------------------------------------------- scenes

def piece_of(brief: str) -> dict:
    """The values declared ONCE for the whole piece — never per scene. The
    block first; the prose only for a brief that has no block."""
    doc, _ = json_block(brief)
    if isinstance(doc, dict) and doc.get("scenes"):
        return piece_from_block(doc)
    head = brief.split("**Scene ")[0]
    return {k: _one(head, pat) for k, pat in PIECE.items()}


def parse(brief: str) -> list[dict]:
    doc, _ = json_block(brief)
    if isinstance(doc, dict) and doc.get("scenes"):
        return scenes_from_block(doc)
    timed = list(HEAD_TIMED.finditer(brief))
    heads = timed or [m for m in HEAD_SCENE.finditer(brief)
                      if "TYPE" not in m.group(2)]
    shape = "timed" if timed else "scene"
    out = []
    for i, m in enumerate(heads):
        body = brief[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(brief)]
        if shape == "timed":
            sc = {"n": int(m.group(1)), "start": secs(m.group(2)), "end": secs(m.group(3)),
                  "seconds": float(m.group(4)), "type": m.group(5), "shape": "timed"}
        else:
            sc = {"n": int(m.group(1)), "start": None, "end": None, "seconds": 0.0,
                  "type": "", "shape": "scene"}
        for key, pat in FIELDS.items():
            f = re.search(pat, body, re.M)
            sc[key] = f.group(1).strip() if f else ""
        s = SAY.search(body)
        v = VOICE.search(body)
        sc["say"] = _quote(s.group(1)) if s else ""
        # THE PARAGRAPH — byte-identical to the script, one per scene. The old
        # shape's single line is that scene's paragraph; nothing is merged.
        sc["voice"] = _quote(v.group(1)) if v else sc["say"]
        sc["id"] = f"S{sc['n']}"

        if shape == "scene":
            sc["setting"] = sc.get("setting") or m.group(2).strip()
            sc["frames"] = frames_of(body)
            sc["beats"] = beats_of(body)
            # TO CAMERA IS SAID, NEVER GUESSED (the owner, 2026-09-23). It used
            # to default to true whenever the scene had a voice — which every
            # B-roll scene has too, so a B-roll shot silently became a face.
            # A scene that does not say is marked, and the gate refuses it.
            if sc.get("to_camera"):
                sc["to_camera"] = _yes(sc.get("to_camera"))
            else:
                sc["to_camera"] = False
                sc["to_camera_missing"] = True
            sc["type"] = "A" if sc["to_camera"] else "B"
        else:
            sc["setting"] = sc.get("setting") or ""
            sc["frames"] = _frames_from_old(sc)
            sc["beats"] = []
            sc["to_camera"] = sc["type"] == "A"

        sc["needs"] = {"A": "a still of the speaker, then lip-sync to the voice take",
                       "B": "a generated clip, or footage we already own",
                       "C": "the product packshot, moved"}.get(sc["type"], "frames, then one clip")
        sc["status"] = "empty"
        sc["takes"] = []
        out.append(sc)
    return out


def load(run_dir: Path) -> dict:
    brief = (run_dir / "stages" / "5-brief.md")
    if not brief.exists():
        raise SystemExit(f"no brief in {run_dir}")
    text = brief.read_text()
    title = next((l.lstrip("# ").strip() for l in text.splitlines()
                  if l.startswith("# ")), run_dir.name)
    scenes = parse(text)
    doc, _ = json_block(text)
    block = doc if isinstance(doc, dict) and doc.get("scenes") else None
    if block:
        title = _one_line((block.get("piece") or {}).get("title")) or title
    return {"run": run_dir.name, "title": title, "folder": str(run_dir),
            "block": block,
            "piece": piece_of(text),
            "shape": scenes[0]["shape"] if scenes else "scene",
            "scenes": scenes,
            "runtime": round(sum(s["seconds"] for s in scenes), 1)}


if __name__ == "__main__":
    import sys
    d = load(Path(sys.argv[1]).expanduser().resolve())
    print(f"{d['title']} — {len(d['scenes'])} scenes ({d['shape']} shape)")
    for s in d["scenes"]:
        head = s["setting"] or s["happens"] or s["product"]
        print(f"  {s['n']:2}  {len(s['frames'])} frame(s) · {len(s['beats'])} beat(s)  "
              f"{'to camera' if s['to_camera'] else 'silent':9}  {head[:44]}")
        if s["voice"]:
            print(f"      “{s['voice'][:70]}…”")
