"""acting — every to-camera shot says what the face and hands VISIBLY do (VIDEO-RULINGS V46).

The clip model is never sent an emotion word (a strong label is what lights the eyes or overacts), so the only way a
feeling reaches the clip is the shot's `face` and `gestures`. This module is the check and the fill-in for those two
fields, run when the clip prompt is built:

    fill(shots, person, talking, layers) -> (shots, notes)

  * a field that holds a visible action is kept as written (note: ok)
  * a blank field, or one that is only emotion words, is filled from the emotion bank's video line for the shot's
    emotion (components/creative-controls controls.json -> emotions[].video), or marked `not applicable` with the reason
  * the person's own gestures (character file) cover an empty `gestures` when the file has them
  * a person with no "Life marks and gestures" section is said so once, as `not applicable: no character file section`

Nothing here stops a call: an output is never held (V34). The notes go into the call record (`call["acting"]`), the
clip plan's `acting_notes` and the run record, so nothing is silently blank. Reads controls.json by path; writes nothing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTROLS = HERE.parents[1] / "creative-controls" / "controls.json"

# words that name a feeling or a state, not something a camera can see
FEELING = {
    "angry", "anger", "sad", "sadness", "happy", "happiness", "joy", "joyful", "upset", "excited", "excitement", "nervous",
    "curious", "annoyed", "proud", "pride", "determined", "worried", "worry", "embarrassed", "embarrassment", "frustrated",
    "frustration", "disgusted", "disgust", "afraid", "fearful", "fear", "calm", "tense", "anxious", "anxiety", "hopeful",
    "hope", "skeptical", "sceptical", "confident", "confidence", "relieved", "relief", "shocked", "shock", "surprised",
    "surprise", "amused", "amusement", "satisfied", "satisfaction", "awe", "craving", "empathic", "pain", "emotional",
    "emotion", "mood", "feeling", "feels", "feel", "looks", "seems", "very", "slightly", "a", "an", "the", "and", "then",
    "with", "of", "is", "are", "bit", "little", "quite", "deeply", "genuinely", "mix", "sense"}
# a few spoken-style synonyms -> a bank id
SYNONYM = {"skeptic": "frustration", "sceptic": "frustration", "disbelief": "surprise", "shock": "surprise",
           "shocked": "surprise", "amazed": "awe", "wonder": "awe", "pain": "empathic-pain", "wince": "disgust",
           "gross": "disgust", "annoy": "frustration", "angry": "frustration", "worried": "anxiety", "nervous": "anxiety",
           "happy": "satisfaction", "pleased": "satisfaction", "delighted": "amusement", "funny": "amusement",
           "ashamed": "embarrassment", "awkward": "embarrassment", "hope": "relief", "tempted": "craving",
           "want": "craving", "confident": "pride", "proud": "pride"}


def bank() -> dict:
    """{emotion id: {"name", "video"}} from the creative controls; {} when the file is not there."""
    try:
        return {e["id"]: {"name": e.get("name", e["id"]), "video": str(e.get("video") or "").strip()}
                for e in json.loads(CONTROLS.read_text()).get("emotions") or []}
    except (OSError, ValueError, KeyError):
        return {}


def _text(v) -> str:
    if isinstance(v, (list, tuple)):
        return "; ".join(_text(x) for x in v if x)
    return str(v or "").strip()


def visible(value) -> bool:
    """True when the text holds at least one word that is not a feeling or filler — something the camera could see."""
    toks = re.findall(r"[a-z']+", _text(value).lower())
    return any(t not in FEELING for t in toks)


def emotion_id(label, b: dict | None = None) -> str | None:
    """The bank id a shot's `emotion` label points at, or None."""
    b = b if b is not None else bank()
    t = _text(label).lower()
    if not t:
        return None
    for eid, e in b.items():
        if eid in t or e["name"].lower() in t:
            return eid
    for w, eid in SYNONYM.items():
        if re.search(rf"\b{re.escape(w)}", t) and eid in b:
            return eid
    return None


def fill(shots: list, person: dict | None, talking: bool, layers=None) -> tuple:
    """-> (shots with face/gestures filled where they could be, notes). Only a to-camera call is held to this."""
    out, notes = [], []
    b = bank()
    has_own = bool(str((person or {}).get("gestures") or "").strip())
    for n, sh in enumerate(shots, 1):
        sh = dict(sh)
        sid = str(sh.get("id") or sh.get("shot") or f"shot{n}")
        if not talking:
            out.append(sh)
            continue
        eid = emotion_id(sh.get("emotion"), b)
        for field in ("face", "gestures"):
            if visible(sh.get(field)):
                notes.append({"shot": sid, "field": field, "status": "ok"})
                continue
            line = b.get(eid, {}).get("video") if eid else ""
            if field == "face" and line:
                sh["face"] = line.rstrip(".")
                notes.append({"shot": sid, "field": field, "status": "filled",
                              "from": f"emotion bank: {eid} -> {line}"})
            elif field == "gestures" and has_own and (layers is None or 2 in layers):
                notes.append({"shot": sid, "field": field, "status": "ok",
                              "from": "the person's own gestures (character file) fill it"})
            else:
                why = ("no emotion named on the shot and no visible action written" if not eid else
                       "the emotion's bank line describes the face only, and the person has no gestures of their own"
                       if field == "gestures" else "no bank line")
                if field == "gestures" and not has_own:
                    why += "; no character file section 'Life marks and gestures' to fall back on"
                sh[field] = ""
                notes.append({"shot": sid, "field": field, "status": "not applicable", "reason": why})
        out.append(sh)
    if talking and not has_own and (layers is None or 2 in layers or 3 in layers):
        notes.append({"shot": "*", "field": "character", "status": "not applicable",
                      "reason": "no character file section 'Life marks and gestures': spice layers 2 and 3 send nothing for this person"})
    return out, notes


def summary(notes: list) -> str:
    """One plain line for the run record / variable sheet."""
    if not notes:
        return "acting: not a to-camera call"
    c = {}
    for n in notes:
        c[n["status"]] = c.get(n["status"], 0) + 1
    na = [f"{n['shot']}.{n['field']}: {n['reason']}" for n in notes if n["status"] == "not applicable"]
    return ("acting: " + ", ".join(f"{v} {k}" for k, v in sorted(c.items()))
            + ("; not applicable — " + " | ".join(na) if na else ""))
