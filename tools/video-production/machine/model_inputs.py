#!/usr/bin/env python3
"""
model_inputs.py — the model input contract, read and applied.

`model-inputs.json` is the data: per station on the settled doors, the exact
request fields, the order the maker recommends the prompt be assembled in,
the maker's limits, and which of OUR scene/frame fields fills each model
field. This module is the one place that reads it, so that:

  * `run.py` assembles every item's fields FROM the contract — a still in
    the stills order, a clip in the maker's four blocks — instead of a
    session remembering what a door takes;
  * `preflight.py`'s contract gate refuses an item the contract says is
    incomplete, naming the field;
  * `render_model_inputs.py` prints the same data as `MODEL-INPUTS.md`, so
    a prompt reads the contract rather than restating it.

No model slug, provider name, brand or person is written here: a station's
model comes from `providers.json` through the contract's own `model_from`
pointer, and everything else is the contract's own text.

    python3 machine/model_inputs.py                 # the stations, one line each
    python3 machine/model_inputs.py <station>       # one station's fields
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT_FILE = HERE / "model-inputs.json"

_spec = importlib.util.spec_from_file_location("vm_platform_mi", HERE / "platform.py")
platform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(platform)

_CACHE: dict | None = None


def contract() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(CONTRACT_FILE.read_text())
    return _CACHE


def stations() -> dict:
    return contract()["stations"]


def station(name: str) -> dict:
    st = stations().get(name)
    if st is None:
        raise SystemExit(f"model-inputs.json has no station {name!r} — "
                         f"the ones it has: {', '.join(stations())}")
    return st


def contract_id_for_kind(kind: str | None) -> str | None:
    return contract()["contract_of_kind"].get(kind or "")


def for_kind(kind: str | None) -> dict | None:
    cid = contract_id_for_kind(kind)
    return stations().get(cid) if cid else None


def edit_route(camera: str | None) -> dict:
    """Which door a LAST FRAME's edit goes to, from the camera it declares.
    A push-in or a new angle rescales the face, and that edit goes to the
    fidelity door; everything else is the everyday delta edit."""
    routing = contract().get("edit_routing") or {}
    # One image door (Damon, 2026-09-18: "gpt for all image work"): when the
    # contract names `all_edits`, every edit goes there, whatever the camera
    # word says — the word is still recorded for the director. The older
    # face-rescale routing stays readable for a contract that still uses it.
    if routing.get("all_edits"):
        return routing["all_edits"]
    want = _clean(camera).lower()
    face = routing.get("face_rescale") or {}
    for word in face.get("when", []):
        if word and word in want:
            return face
    return routing.get("default") or {}


def dotted(path: str, book: dict | None = None):
    """`direct.openai.model` -> the value in providers.json. A pointer that
    leads nowhere comes back None — never a crash, because a contract row is
    a description first and a lookup second."""
    cur = book if book is not None else platform.registry()
    for part in (path or "").split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def model_of(station_name: str) -> str | None:
    """The station's model slug, read from providers.json — never written here."""
    ptr = station(station_name).get("model_from")
    return dotted(ptr) if ptr else None


def house_default(field: dict):
    """A field's house default: a dotted pointer resolves against
    providers.json, anything else is the value itself."""
    v = field.get("house_default")
    if isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_.\-]+", v) and "." in v:
        got = dotted(v)
        if got is not None:
            return got
    return v


def field_named(station_name: str, name: str) -> dict | None:
    for f in station(station_name).get("fields", []):
        if f.get("name") == name:
            return f
    return None


def door_of(station_name: str) -> dict:
    """Which door this station's clips actually go to, and what it takes.
    The registry decides the door (`providers.json` → `doors[...]`); this
    file says what that door's request looks like. A door the registry names
    and the contract does not know falls back to the station's preferred
    door, and the submit sheet says which was used."""
    st = station(station_name)
    rows = {r["id"]: r for r in (st.get("doors") or [])}
    if not rows:
        return {}
    reg_door = str(dotted(f"doors.{st.get('station', station_name)}.primary") or "")
    mapped = (contract().get("door_of_registry") or {}).get(reg_door)
    return rows.get(mapped) or rows.get(st.get("preferred_door")) or next(iter(rows.values()))


def end_image_door(station_name: str) -> tuple[str, bool, str]:
    """(door id, does it take the last frame as a real input, how it lands).
    A scene always has a last frame; this decides whether it is attached or
    described."""
    row = door_of(station_name)
    if row.get("takes_end_image"):
        return row["id"], True, f"attached as {row.get('field')} on {row['id']}"
    return (row.get("id", "?"), False,
            f"described as the timeline's final beat — {row.get('id', 'this door')} "
            f"has no end-frame field")


def takes(station_name: str, name: str) -> bool:
    """Does this door take this field at all? (`end_image` is the one that
    matters: present on some doors, absent on others, and the difference
    decides whether the last frame is attached or written.)"""
    return field_named(station_name, name) is not None


def size_for(aspect: str | None) -> str | None:
    return contract()["aspect_to_size"].get(aspect or "")


def piece_default(name: str):
    return (contract()["piece_fields"].get(name) or {}).get("house_default")


# ------------------------------------------------------------ assembling

def _clean(s) -> str:
    return " ".join(str(s or "").split())


def _sentence(s: str) -> str:
    s = _clean(s)
    if s and s[-1] not in ".!?":
        s += "."
    return s


def still_prompt(frame: dict, piece: dict | None = None) -> str:
    """A FIRST FRAME, in the stills order the maker recommends:
    subject · composition · action · location · style · camera · lighting —
    and then the piece's aspect, said in words. A size parameter tells the
    door how big the picture is; only the words tell it how to compose."""
    piece = piece or {}
    order = station("still-generate")["assembly"]["order"]
    sep = station("still-generate")["assembly"].get("separator", " ")
    parts = []
    for slot in order:
        val = frame.get(slot) or (piece.get(slot) if slot in ("style",) else "")
        if val:
            parts.append(_sentence(val))
    words = (contract().get("aspect_words") or {}).get(_clean(piece.get("aspect")))
    if words:
        parts.append(words)
    return sep.join(parts)


def edit_prompt(frame: dict, station_id: str = "still-edit-fidelity") -> str:
    """A LAST FRAME — the delta, then the one line that says what may not
    change. The delta alone lets an edit door re-decide the exposure, the
    wardrobe and the room; the pair then reads as two different shots the
    moment a clip runs from one to the other (live 2026-09-18)."""
    delta = _sentence(frame.get("delta") or frame.get("do") or "")
    if not delta:
        return ""
    keep = _clean((station(station_id).get("assembly") or {}).get("keep_line"))
    return f"{delta} {keep}".strip() if keep else delta


def beats_of(scene: dict) -> list[dict]:
    """The scene's beats — the timed spans written into the clip's timeline.
    They are NOT pictures: a scene generates exactly two stills, its first
    frame and its last (Damon, 2026-09-18)."""
    return list(scene.get("beats") or [])


def frame_of(scene: dict, role: str) -> dict:
    return next((f for f in (scene.get("frames") or []) if f.get("role") == role), {})


# TWO KINDS OF JOINER, because a beat is written in present tense and the
# difference is readable (2026-09-19).
#
#   * `then` and `followed by` sequence two things whatever follows them —
#     "taps one finger against the tube, then a second" is two beats even
#     though the second half names no verb at all.
#   * `and`, `until`, `while`, `before`, `after` join a second ACTION only
#     when a verb follows. "sets the tube down front-on and square to the
#     lens" is one action with two adjectives; "stands and walks out of
#     frame" is two. The tell is the verb, and in this grammar a verb is
#     present tense third person, so it ends in s.
#
# "once" is deliberately in neither. It is an adverb far more often than a
# joiner — "taps the tube once", "nods once", "turns it over once" are all ONE
# action, and counting them as two refused five good beats on the first brief
# written to this grammar.
ALWAYS_JOINER = re.compile(r"(?<![\w-])(then|followed by)(?![\w-])", re.I)
VERB_JOINER = re.compile(
    r"(?<![\w-])(?:and|while|whilst|before|after|until|plus|as well as)"
    r"(?![\w-])\s+(?:the\s+|a\s+|an\s+|it\s+|they\s+|she\s+|he\s+)?"
    r"([a-z’']+)", re.I)
# words that end in s and are not verbs — the ones that actually turn up in a
# beat after a joiner
NOT_A_VERB = {"his", "hers", "its", "as", "plus", "this", "these", "those",
              "always", "across", "towards", "downwards", "upwards", "backwards",
              "sideways", "less", "eyes", "hands", "fingers", "shoulders",
              "spots", "glass", "grains", "others", "words", "yes", "us"}


def _is_verb(word: str) -> bool:
    w = (word or "").lower().strip("’'")
    return len(w) > 2 and w.endswith("s") and w not in NOT_A_VERB


def action_count(text: str) -> int:
    """How many actions a beat names. One verb per beat is the maker's own
    limit ("two short actions are stable, three or more often produce
    drift"), and a joiner is how a second one gets in. Sentences count too:
    a beat written as two sentences is two beats."""
    t = _clean(text)
    if not t:
        return 0
    n = 1 + len(ALWAYS_JOINER.findall(t))
    n += sum(1 for w in VERB_JOINER.findall(t) if _is_verb(w))
    n += len([s for s in re.split(r"[.!?]+", t) if s.strip()]) - 1
    return n


# The shortest span a beat is ever given when the read did not name one.
MIN_BEAT = 0.5


def beat_windows(scene: dict, seconds: float | None,
                 timing: dict | None = None) -> list[tuple[float, float]]:
    """A span per beat, on the scene's own clock, read off the ONE voice
    track: the beat's own `At:` if the brief carried one, else the sentence
    its words play over, else its share of what is left. No number is ever
    chosen by a format — every one of these comes from the read."""
    beats = beats_of(scene)
    if not beats:
        return []
    rows = ((timing or {}).get("scenes") or {}).get(str(scene.get("id")), {})
    lines = rows.get("lines") or []
    base = float(rows.get("start") or 0.0)
    total = float(seconds or 0)
    if not total and rows.get("end") is not None:
        total = float(rows["end"]) - base
    if not total:
        total = float(len(beats))

    known: dict[int, tuple[float, float]] = {}
    for i, b in enumerate(beats):
        at = b.get("at")
        if isinstance(at, (list, tuple)) and len(at) == 2:
            known[i] = (float(at[0]), float(at[1]))
            continue
        over = _clean(b.get("over")).strip('"“”').lower()
        if not over or not lines:
            continue
        for ln in lines:
            if over[:40] in _clean(ln.get("text")).lower():
                known[i] = (float(ln["start"]) - base, float(ln["end"]) - base)
                break

    out: list[tuple[float, float]] = []
    for i in range(len(beats)):
        if i in known:
            out.append(known[i])
            continue
        # the unknown beat takes what is left between the beats around it
        prev_end = out[-1][1] if out else 0.0
        nxt = next((known[j][0] for j in range(i + 1, len(beats)) if j in known), total)
        unknowns = 1 + sum(1 for j in range(i + 1, len(beats))
                           if j not in known and all(k not in known for k in range(i + 1, j + 1)))
        gap = (nxt - prev_end) / max(unknowns, 1)
        if gap < MIN_BEAT and out:
            # A PAUSE IS A BEAT (2026-09-19) — `Do: holds`, with the silence
            # in Over. But a read with no gap between its sentences leaves
            # one nowhere to sit, and two beats claiming the same span is a
            # timeline the door cannot follow. So the pause borrows the tail
            # of the beat before it rather than overlapping the one after.
            a, z = out[-1]
            borrow = min(MIN_BEAT, max((z - a) / 3, 0.2))
            out[-1] = (a, round(z - borrow, 2))
            prev_end, gap = out[-1][1], borrow
        span = max(gap, MIN_BEAT if not out else 0.2)
        out.append((round(prev_end, 2), round(prev_end + span, 2)))
    return [(round(a, 2), round(b, 2)) for a, b in out]


def clip_shape() -> dict:
    """The four-block shape both clip stations are assembled in — the exact
    shape of the call that worked live 2026-09-18 evening."""
    return contract()["clip_prompt"]


def _mid(s) -> str:
    """A labelled field placed INSIDE a sentence: its trailing stop dropped,
    and a leading capital lowered where it is ordinary prose. A name the
    brief wrote in capitals is left exactly as the brief wrote it."""
    t = _clean(s).rstrip(".").strip()
    if not t:
        return ""
    head = t.split(" ", 1)[0]
    if head[:1].isupper() and not head.isupper():
        t = t[0].lower() + t[1:]
    return t


def camera_of(scene: dict) -> tuple[str, str, list[str]]:
    """(the camera in one phrase, the camera as a sentence, what is missing).

    Both come from LABELLED fields — the LAST FRAME's Camera word, and the
    framing the FIRST FRAME's Composition starts on. A move that names no
    framing to land on is a refusal, never a guess."""
    shape = clip_shape()
    first, last = frame_of(scene, "first"), frame_of(scene, "last")
    word = _clean(last.get("camera")).lower()
    if not word:
        return "", "", ["the LAST FRAME's Camera (same · push-in to <framing> · "
                        "new angle to <framing>)"]
    key = None
    for cand in ("push-in", "push in", "pull-out", "pull out", "new angle", "same"):
        if cand in word:
            key = {"push in": "push-in", "pull out": "pull-out"}.get(cand, cand)
            break
    if key is None:
        key = "same"
    phrase = (shape["camera_phrases"].get(key) or "")
    sentence = (shape["camera_sentences"].get(key) or "")
    if "{" not in phrase:
        return phrase, sentence, []
    missing: list[str] = []
    first_framing = _mid(_clean(first.get("composition")).split(",")[0])
    if not first_framing:
        missing.append("the FIRST FRAME's Composition (the framing the move starts from)")
    target = _mid(word.split(" to ", 1)[1]) if " to " in word else ""
    if not target:
        missing.append(f"the framing the move lands on — the LAST FRAME's "
                       f"Camera reads {word!r}, and this door needs "
                       f"'{key} to <framing>', in the same words the FIRST "
                       f"FRAME's Composition uses")
    if missing:
        return "", "", missing
    return (phrase.format(first_framing=first_framing, target=target),
            sentence, [])


def summary_of(scene: dict, piece: dict | None = None) -> tuple[str, list[str]]:
    """(the ONE summary sentence, what is missing). Built from the labelled
    slots the contract names, in a fixed template — never by gluing raw
    fields end to end. A slot that resolves to nothing is named, and the
    caller writes no prompt at all: a fragment is how a clip ends up being
    about something else."""
    piece = piece or {}
    shape = clip_shape()["summary"]
    first = frame_of(scene, "first")
    sources = {
        "scene.who": _clean(scene.get("who")).split("·")[0].strip(),
        "scene.setting": _clean(scene.get("setting")),
        "scene.happens": _clean(scene.get("happens")),
        "first_frame.action": _clean(first.get("action")),
        "first_frame.style": _clean(first.get("style")),
        "first_frame.composition": _clean(first.get("composition")),
        "piece.style": _clean(piece.get("style")),
    }
    camera, _, cam_missing = camera_of(scene)
    values, missing = {}, list(cam_missing)
    for name, row in shape["slots"].items():
        if name == "camera":
            values["camera"] = camera
            continue
        got = next((sources.get(f) for f in row.get("from", []) if sources.get(f)), "")
        if not got:
            missing.append(f"{row.get('what', name)} ({' or '.join(row.get('from', []))})")
        values[name] = got if name in ("who", "setting") else _mid(got)
    if missing:
        return "", missing
    return shape["template"].format(**values), []


def asset_line(scene: dict, talking: bool) -> tuple[str, list[str]]:
    """(@Image1 · @Image2 · @Audio1, what is missing). The first frame said
    in one line, the last frame said as its delta, and — on a to-camera
    scene — whose voice the attached audio is."""
    shape = clip_shape()["assets"]
    first, last = frame_of(scene, "first"), frame_of(scene, "last")
    got = {"first_frame.subject": _clean(first.get("subject")),
           "first_frame.composition": _clean(first.get("composition")),
           "first_frame.action": _clean(first.get("action")),
           "last_frame.delta": _clean(last.get("delta"))}
    missing: list[str] = []
    parts = [_mid(got[f]) for f in shape["first_from"] if got.get(f)]
    if not parts:
        missing.append("the FIRST FRAME (Subject · Composition · Action)")
    tail = [_mid(got[f]) for f in shape["last_from"] if got.get(f)]
    if not tail:
        missing.append("the LAST FRAME's Change (the delta)")
    who = _clean(scene.get("who")).split("·")[0].strip()
    if talking and not who:
        missing.append("who speaks (the scene's Who)")
    if missing:
        return "", missing
    join = shape.get("join", ", ")
    out = [shape["first"].format(first=join.join(parts)),
           shape["last"].format(last=join.join(tail))]
    if talking:
        out.append(shape["audio"].format(who=who))
    return shape.get("separator", " ").join(out), []


def timeline_of(scene: dict, seconds: float | None = None,
                timing: dict | None = None, talking: bool = False) -> tuple[str, list[str]]:
    """(the timeline, what is missing). One verb a beat, its span read off
    the one voice track, the first beat anchored on @Image1 and the last
    settling on the framing of @Image2."""
    shape = clip_shape()["timeline"]
    beats = beats_of(scene)
    if not beats:
        return "", ["the beats — what happens between the two frames"]
    windows = beat_windows(scene, seconds, timing)
    rows = []
    for i, b in enumerate(beats):
        a, z = windows[i] if i < len(windows) else (float(i), float(i + 1))
        do = _mid(b.get("do"))
        if not do:
            return "", [f"beat {b.get('n', i + 1)} names no action"]
        # A held beat on a to-camera scene keeps the mouth moving: a "holds"
        # with audio attached came back barely speaking (live 2026-09-19).
        if talking and _clean(b.get("do")).lower().split()[:1] == [
                _clean(beat_grammar().get("pause_verb")).lower()]:
            do = _mid(clip_shape().get("to_camera_hold", {}).get("text") or do)
        line = shape["line"].format(start=f"{a:g}", end=f"{z:g}", do=do)
        if not talking and _clean(b.get("over")):
            line += shape["words"].format(over=_clean(b["over"]).strip('"“”').rstrip("."))
        if i == 0:
            line += shape["first_beat"]
        if i == len(beats) - 1:
            line += shape["last_beat"]
        if _clean(b.get("beat")):
            line += shape["performance"].format(beat=_mid(b["beat"]))
        rows.append(line + ".")
    return "\n".join(rows), []


def consistency_of(scene: dict, talking: bool) -> tuple[str, list[str]]:
    """(what holds, what is missing) — the take, the setting, the light, the
    wardrobe, and the two negatives every clip carries."""
    shape = clip_shape()["consistency"]
    first = frame_of(scene, "first")
    _, camera_sentence, missing = camera_of(scene)
    setting = _clean(scene.get("setting"))
    lighting = _mid(first.get("lighting"))
    if not setting:
        missing.append("the scene's Setting")
    if not lighting:
        missing.append("the FIRST FRAME's Lighting")
    if missing:
        return "", missing
    out = [shape["take"].format(camera_sentence=camera_sentence),
           shape["hold"].format(setting=setting, lighting=lighting)]
    if talking:
        out.append(shape["lip"])
    elif shape.get("silent"):
        # A B-ROLL SCENE CARRIES NO SPEECH (2026-09-19). Its paragraph is the
        # voice playing OVER it at the edit, so the clip itself has nobody
        # talking in it — said out loud, because a door handed a person and a
        # voice track in the same run will otherwise make a mouth move.
        out.append(shape["silent"])
    out += list(shape["negatives"])
    return shape.get("separator", " ").join(out), []


def clip_blocks(scene: dict, piece: dict | None = None, seconds: float | None = None,
                timing: dict | None = None, talking: bool = False) -> tuple[list[str], list[str]]:
    """(the four blocks in order, everything missing). One place assembles
    them, so the prompt and the gate can never disagree about what a scene
    still owes."""
    blocks, missing = [], []
    for text, gaps in (asset_line(scene, talking),
                       summary_of(scene, piece),
                       timeline_of(scene, seconds, timing, talking),
                       consistency_of(scene, talking)):
        blocks.append(text)
        missing += gaps
    return blocks, missing


def clip_prompt(scene: dict, piece: dict | None = None, seconds: float | None = None,
                timing: dict | None = None, talking: bool = False) -> str:
    """The clip prompt, in the maker's four blocks: the asset line, the ONE
    summary sentence, the timeline of beats with their spans, what holds.

    A block that cannot be built from labelled fields is not written as a
    fragment — the whole prompt comes back empty and `clip_missing()` says
    which field is owed, so the gate refuses by name and nothing submits."""
    blocks, missing = clip_blocks(scene, piece, seconds, timing, talking)
    if missing:
        return ""
    return clip_shape().get("separator", "\n\n").join(blocks)


def clip_missing(scene: dict, piece: dict | None = None, seconds: float | None = None,
                 timing: dict | None = None, talking: bool = False) -> list[str]:
    return clip_blocks(scene, piece, seconds, timing, talking)[1]


# ------------------------------------------------------- the beat grammar
#
# A BEAT IS ONE VISIBLE ACTION (Damon, 2026-09-19). One verb, present tense,
# something a camera can see: "taps the tube once", "turns the forearm
# face-up", "looks up to the lens". How a line is DELIVERED — says, stops,
# slows, settles — is not an action; it belongs in the bracket at the end of
# the beat. A pause is a beat too, and its action is `holds`.
#
# Every word below comes from the contract's own `beat_grammar`, so a
# correction there corrects the gate and the prompt together.

def beat_grammar() -> dict:
    return clip_shape().get("beat_grammar") or {}


def delivery_note(text: str) -> str:
    """The delivery word a beat opens on, or "". The verb a beat starts with
    is what the camera sees happen; these name the performance instead, and
    the bracket is where they belong."""
    t = _clean(text).lower().lstrip("*_(“\"' ")
    if not t:
        return ""
    head = re.split(r"[^a-z’']+", t)[0]
    if head == _clean(beat_grammar().get("pause_verb")).lower():
        return ""
    return head if head in set(beat_grammar().get("delivery_verbs") or []) else ""


def insert_marker(text: str) -> str:
    """The insert marker in a beat, or "". B-ROLL IS A SCENE, NOT AN INSERT:
    a picture wedged into another scene's beat is a second shot inside one
    clip, and one clip cannot cut."""
    t = _clean(text).lower()
    for m in beat_grammar().get("insert_markers") or []:
        if m and m.lower() in t:
            return m
    return ""


def beat_faults(beat: dict, n=None) -> list[str]:
    """Every way one beat breaks the grammar, each naming the beat and the
    words that broke it."""
    n = n if n is not None else beat.get("n", beat.get("id", "?"))
    do = beat.get("do") or ""
    out: list[str] = []
    if not _clean(do):
        out.append(f"beat {n} names no action — one verb per beat, and every "
                   f"beat has one")
        return out
    if action_count(do) > 1:
        out.append(f"beat {n} names more than one action ({_clean(do)[:70]!r}) "
                   f"— one verb per beat")
    word = delivery_note(do)
    if word:
        out.append(f"beat {n} opens on {word!r} ({_clean(do)[:70]!r}) — that is "
                   f"a delivery note, not an action. Put it in the bracket at "
                   f"the end of the beat and write what the camera sees")
    mark = insert_marker(do) or insert_marker(beat.get("over") or "")
    if mark:
        out.append(f"beat {n} carries {mark!r} ({_clean(do)[:70]!r}) — B-roll is "
                   f"a scene, not an insert: give it its own scene with "
                   f"to_camera false, its own frames and the paragraph that "
                   f"plays over it")
    return out


def camera_fault(camera: str, where: str = "the LAST FRAME's Camera") -> str:
    """"" when the camera word is one of the four the door takes, otherwise
    the refusal. A move always names the framing it lands on."""
    shape = clip_shape()
    words = shape.get("camera_words") or []
    want = _clean(camera).lower()
    if not want:
        return (f"{where} is empty — it is one of: " + " · ".join(words))
    key = None
    for cand in ("push-in", "push in", "pull-out", "pull out", "new angle", "same"):
        if cand in want:
            key = {"push in": "push-in", "pull out": "pull-out"}.get(cand, cand)
            break
    if key is None:
        return (f"{where} reads {_clean(camera)!r} — it is one of: "
                + " · ".join(words))
    if key == "same":
        return ""
    target = want.split(" to ", 1)[1].strip() if " to " in want else ""
    if not target:
        return (f"{where} reads {_clean(camera)!r}, and this door needs "
                f"'{key} to <framing>' — the framing it lands on, in the same "
                f"words the FIRST FRAME's Composition uses")
    return ""


# ------------------------------------------------------------- the brief
#
# THE BRIEF IS THE PROMPT (Damon, 2026-09-19). A brief's truth is the last
# fenced json block in it, in the shape `brief_schema` names; the Markdown
# above it is the readable view, rendered from the same fields, and nothing
# downstream parses it. This is where the block is checked — every key
# present, a string still a string, a list still a list — so a brief that
# cannot be built is refused by the name of the key it is missing.

FENCE = re.compile(r"```[ \t]*([a-zA-Z0-9_+-]*)[ \t]*\r?\n(.*?)```", re.S)


def json_block(text: str):
    """The LAST fenced json block in a document, parsed -> (value, reason).

    The same rule the teardown chain already reads its stage blocks by: a
    model that explains itself after the block is normal, so the last block
    wins, and a block fenced with no language tag still counts as long as it
    parses. Never raises."""
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


def brief_schema() -> dict:
    return contract().get("brief_schema") or {}


def _keys(where: str, obj, wanted, out: list[str]) -> None:
    if not isinstance(obj, dict):
        out.append(f"{where} is {type(obj).__name__}, not an object")
        return
    for k in wanted:
        if k not in obj:
            out.append(f"{where} is missing {k!r}")
        elif (isinstance(obj[k], str) and not obj[k].strip()
              and k not in set(brief_schema().get("may_be_empty") or [])):
            out.append(f"{where}'s {k!r} is empty — a key with nothing to say "
                       f"still says it; never drop it and never leave it blank")


def voice_forbidden() -> list[dict]:
    """The marks a scene's `voice` may not carry — writing, not speech
    (`brief_schema.voice_forbidden` in the contract). Each row is
    {mark, name}; the doctrine's spoken.json punctuation map says what each
    one does on the voice model, and voice.py's for_reading() reads that
    map for the safety net on older briefs."""
    return list((brief_schema().get("voice_forbidden") or {}).get("marks") or [])


def voice_faults(text: str, where: str = "the voice") -> list[str]:
    """Every written-only mark in a voice paragraph, each named. The voice
    model reads a dash as a long silence (measured 2026-09-19: 1.3–1.7 s
    at every one) and a parenthesis as an aside nobody hears; the spoken
    script writes without them and the gate refuses them by name rather than
    letting a take carry them (Damon, 2026-09-19: "humans don't use em
    dashes when speaking")."""
    s = text or ""
    out: list[str] = []
    for row in voice_forbidden():
        mark = row.get("mark") or ""
        if mark and mark in s:
            n = s.count(mark)
            out.append(f"{where} carries {row.get('name') or mark!r} "
                       f"({n}×) — the voice paragraph is spoken copy: "
                       f"a pause is a full stop or a comma, never a dash, a "
                       f"semicolon or a parenthesis (an ellipsis is the breath and is kept)")
    return out


def voice_settings_ranges() -> dict:
    return {k: v for k, v in (brief_schema().get("voice_settings_ranges") or {}).items()
            if isinstance(v, list) and len(v) == 2}


def voice_settings_faults(vs, where: str = "voice_settings") -> list[str]:
    """A scene's per-scene voice settings, checked against the voice model's
    own limits (`brief_schema.voice_settings_ranges`). Only the keys the
    model takes, only numbers, only inside the range."""
    if not isinstance(vs, dict):
        return [f"{where} is {type(vs).__name__}, not an object of stability / style / speed"]
    out: list[str] = []
    ranges = voice_settings_ranges()
    for k, v in vs.items():
        if k == "use_speaker_boost":
            if not isinstance(v, bool):
                out.append(f"{where}.{k} is {v!r} — true or false")
            continue
        if k not in ranges:
            out.append(f"{where} carries {k!r} — the voice model takes "
                       f"{' · '.join(ranges)} and use_speaker_boost, nothing else")
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            out.append(f"{where}.{k} is {v!r} — a number")
            continue
        lo, hi = ranges[k]
        if not lo <= float(v) <= hi:
            out.append(f"{where}.{k} is {v} — the voice model takes {lo} to {hi}")
    return out


def brief_violations(brief) -> list[str]:
    """Every way a brief's json block fails `brief_schema`, each naming its
    own key. A brief with no fenced block at all is an older one, parsed from
    its Markdown, and is checked by the item rules instead."""
    sch = brief_schema()
    if not sch:
        return []
    doc = brief
    if isinstance(brief, str):
        doc, why = json_block(brief)
        if doc is None:
            # no block at all: an older brief, read from its Markdown. A block
            # that IS there and will not parse is a refusal, because that one
            # was meant to be the truth.
            return [] if "no fenced block in the brief" in (why or "") else [
                f"the brief's json block will not parse ({why}) — the block IS "
                f"the brief, and nothing downstream reads the prose"]
    if not isinstance(doc, dict):
        return [f"the brief's json block is a {type(doc).__name__}, not an object"]

    out: list[str] = []
    _keys("the brief's json block", doc, sch.get("required") or [], out)
    _keys("the block's 'piece'", doc.get("piece"), sch.get("piece") or [], out)

    # THE TWO VALUES DECLARED ONCE FOR THE PIECE have to be values the doors
    # actually take. A pixel pair where the clip door wants `720p` is a call
    # that comes back rejected after the stills are paid for (2026-09-19).
    piece = doc.get("piece") if isinstance(doc.get("piece"), dict) else {}
    aspects = list(contract().get("aspect_to_size") or {})
    got = _clean(piece.get("aspect_ratio") or piece.get("aspect"))
    if got and got not in aspects:
        out.append(f"the piece's aspect_ratio {got!r} is not one the doors take "
                   f"— it is one of: {' · '.join(aspects)}")
    row = field_named("motion", "resolution") or {}
    allowed = [v.strip() for v in str(row.get("values") or "").split("·")]
    allowed = [v.split(" ")[0] for v in allowed if v]
    got = _clean(piece.get("resolution"))
    if allowed and got and got not in allowed:
        out.append(f"the piece's resolution {got!r} is not one the clip door "
                   f"takes — it is one of: {' · '.join(allowed)}, never a "
                   f"pixel pair; the still size is resolved from the aspect")

    for name in sch.get("lists") or []:
        if name in doc and not isinstance(doc[name], list):
            out.append(f"the block's {name!r} is {type(doc[name]).__name__}, "
                       f"not a list")

    world_ids = set()
    for i, w in enumerate(doc.get("world") or [], 1):
        _keys(f"world[{i}]", w, sch.get("world_item") or [], out)
        if isinstance(w, dict) and w.get("id"):
            world_ids.add(str(w["id"]))
    for i, c in enumerate(doc.get("cast") or [], 1):
        _keys(f"cast[{i}]", c, sch.get("cast_item") or [], out)
        if isinstance(c, dict):
            _keys(f"cast[{i}]'s 'voice'", c.get("voice"),
                  sch.get("cast_voice") or [], out)

    scenes = doc.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        out.append("the block names no scenes — 'scenes' is the brief")
        return out

    for sc in scenes:
        sid = (sc or {}).get("id", "?") if isinstance(sc, dict) else "?"
        where = f"scene {sid}"
        if isinstance(sc, dict) and _clean(sc.get("held")):
            # A HELD SCENE is one the brand's own files cannot fill yet. It
            # keeps its place and its section and names the one fact that
            # would release it; nothing is generated for it, so it is not
            # asked for a frame nobody can describe. That is a finding for
            # the owner, and the run says so out loud.
            _keys(where, sc, ["id", "section", "setting_id", "held"], out)
            continue
        _keys(where, sc, sch.get("scene") or [], out)
        if not isinstance(sc, dict):
            continue
        if "to_camera" in sc and not isinstance(sc["to_camera"], bool):
            out.append(f"{where}'s 'to_camera' is {sc['to_camera']!r} — it is "
                       f"true or false, and it is what decides whether the clip "
                       f"carries the voice or the edit lays it over")
        if world_ids and sc.get("setting_id") and str(sc["setting_id"]) not in world_ids:
            out.append(f"{where}'s setting_id {sc['setting_id']!r} names no world "
                       f"block — the places there are: "
                       f"{', '.join(sorted(world_ids))}")
        _keys(f"{where}'s 'delivery'", sc.get("delivery"),
              sch.get("delivery") or [], out)
        _keys(f"{where}'s 'first_frame'", sc.get("first_frame"),
              sch.get("first_frame") or [], out)
        ff = sc.get("first_frame")
        if isinstance(ff, dict) and "refs" in ff and not isinstance(ff["refs"], list):
            out.append(f"{where}'s first_frame.refs is "
                       f"{type(ff['refs']).__name__}, not a list")
        _keys(f"{where}'s 'last_frame'", sc.get("last_frame"),
              sch.get("last_frame") or [], out)
        lf = sc.get("last_frame")
        if isinstance(lf, dict):
            bad = camera_fault(lf.get("camera"),
                               f"{where}'s last_frame.camera")
            if bad:
                out.append(bad)
        beats = sc.get("beats")
        if not isinstance(beats, list) or not beats:
            out.append(f"{where} has no beats — every scene has at least one, "
                       f"and a pause is a beat whose action is 'holds'")
        else:
            for b in beats:
                if not isinstance(b, dict):
                    out.append(f"{where} has a beat that is not an object")
                    continue
                _keys(f"{where} beat {b.get('id', '?')}", b,
                      sch.get("beat") or [], out)
                for bad in beat_faults(b, f"{b.get('id', '?')} of {where}"):
                    out.append(bad)
        if isinstance(sc.get("voice"), str):
            out.extend(voice_faults(sc["voice"], f"{where}'s 'voice'"))
        if "voice_settings" in sc:
            out.extend(voice_settings_faults(sc["voice_settings"],
                                             f"{where}'s 'voice_settings'"))
        if "cutaways" in sc:
            out.append(f"{where} carries a 'cutaways' key — B-roll is a scene, "
                       f"not an insert: write it as its own scene with "
                       f"to_camera false and the paragraph that plays over it")
    return out


# ------------------------------------------------------------- the gate

def _at(item: dict, path: str | None):
    """Read the place in an item a contract row says a field comes from —
    `params.prompt`, `medias.audio_references`, `start_frame`."""
    if not path:
        return None
    if path.startswith("params."):
        return (item.get("params") or {}).get(path.split(".", 1)[1])
    if path.startswith("medias."):
        role = path.split(".", 1)[1]
        vals = [m.get("value") for m in (item.get("medias") or [])
                if isinstance(m, dict) and m.get("role") == role and m.get("value")]
        return vals or None
    return item.get(path)


def shaped(item: dict) -> bool:
    """Is this item one the scene shape built? The contract gate speaks for
    the scene shape only — an item from the old timed shape is checked by the
    rules that were written for it, and is not asked for fields its own brief
    never had a place to write."""
    return any(k in item for k in ("frame_role", "beats", "frames", "start_frame"))


def violations(item: dict, kind: str | None = None) -> list[str]:
    """Every way this item fails its door's contract, each naming the field.
    Empty list = the door will get everything it needs."""
    kind = kind or item.get("kind")
    # an item may name the contract it was built against (a face-rescale edit
    # runs at the stills door and would otherwise be read as a generation)
    cid = item.get("contract") or contract_id_for_kind(kind)
    if not cid or cid not in stations() or not shaped(item):
        return []
    st = station(cid)
    out: list[str] = []

    door = door_of(cid)
    for f in st.get("fields", []):
        req, where = f.get("required"), f.get("item")
        if req is not True or not where:
            continue
        # a field the CHOSEN door has no place for is not a missing field —
        # the contract says where it lands instead, and the sheet says so
        if f.get("when_absent") and door and not door.get("takes_end_image"):
            continue
        if _at(item, where) in (None, "", [], {}):
            out.append(f"missing required field {f['name']!r} for the {cid} door "
                       f"(the item's {where}) — it carries {f.get('fills', '?')}")

    limits = st.get("limits") or {}
    beats = item.get("beats") or []
    if cid in ("motion", "talking"):
        cap = limits.get("max_beats")
        if cap and len(beats) > cap:
            out.append(f"{len(beats)} beats over the maker's limit of {cap} — "
                       f"{limits.get('max_beats_why', 'the order drifts past it')}")
        if len(beats) < int(limits.get("min_beats") or 1):
            out.append("no beats — a clip with nothing on its timeline is a still "
                       "with a duration; write what happens between the two frames")
        if limits.get("one_verb_per_beat"):
            for b in beats:
                out += beat_faults(b)
        # B-ROLL IS A SCENE, NOT AN INSERT (2026-09-19). A scene that lists
        # cutaways under it is describing a second picture inside one clip.
        if item.get("cutaways"):
            out.append("this scene carries a 'Cutaways:' line — B-roll is a "
                       "scene, not an insert: give it its own scene, with "
                       "To camera: no, its own frames and the paragraph that "
                       "plays over it")
        # a B-roll scene's voice plays OVER it at the edit — the clip itself
        # carries no audio, so the mouth in it never moves
        if item.get("to_camera") is False:
            if _at(item, "medias.audio_references"):
                out.append("a B-roll scene with audio attached — its paragraph "
                           "is laid over it at the edit, never dubbed onto the "
                           "clip; the voice is still recorded, as vo/<scene>.mp3")
        # exactly two stills: the first frame and the last
        frames = item.get("frames") or []
        want = limits.get("frames_per_scene")
        if want and len(frames) != want:
            out.append(f"{len(frames)} frame(s) for this scene — a scene generates "
                       f"exactly {want}: the first frame and the last "
                       f"({limits.get('frames_per_scene_why', '')})")
        if not item.get("start_frame"):
            out.append("no FIRST FRAME — the clip has nothing to start on")
        if not item.get("last_frame"):
            out.append("no LAST FRAME — the clip has nothing to land on, attached "
                       "or described")
        # the paragraph has to fit the clip the door will make
        span = limits.get("duration_seconds") or []
        dur = (item.get("params") or {}).get("duration")
        if not dur:
            out.append("no duration — the scene's own slice of the one voice track "
                       "decides how long the clip runs, and nothing else may")
        elif span and float(dur) > float(span[1]):
            out.append(f"the voice paragraph runs {dur}s, past this door's {span[1]}s "
                       f"ceiling — split the scene at a beat boundary, never mid-sentence")
        # EXACTLY the door's own roles on the clip, and nothing else: the
        # first frame carries the identity, so a cast sheet or a style frame
        # attached beside it is a second opinion about the same face.
        allowed = limits.get("clip_media_roles")
        if allowed:
            seen = [m.get("role") for m in (item.get("medias") or []) if isinstance(m, dict)]
            for role in seen:
                if role not in allowed:
                    out.append(f"the clip carries a {role!r} media — this door takes only "
                               f"{', '.join(allowed)}; {limits.get('clip_media_roles_why', '')}")
            for role in ("start_image", "end_image"):
                if role in allowed and role not in seen:
                    out.append(f"the clip attaches no {role!r} — "
                               f"{'the first frame is what it starts on' if role == 'start_image' else 'the last frame is what it lands on'}, "
                               f"and on this door it travels as a media, not as words")
        # a prompt that could not be assembled from labelled fields
        for gap in (item.get("prompt_missing") or []):
            out.append(f"the prompt could not be assembled — missing {gap}. A block "
                       f"built from a gap is a fragment, and a fragment is how a clip "
                       f"ends up being about something else")

    if cid in ("still-edit", "still-edit-fidelity"):
        if not _clean(item.get("delta")):
            out.append(f"frame {item.get('frame', '?')} has no delta — an edit that names "
                       f"nothing re-generates the frame instead of changing it")
        refs = _at(item, "medias.image_references") or []
        # The second reference is the CAST SHEET, and it exists to hold a
        # face. A frame with nobody in it has no face to hold — a B-roll
        # scene of the hands, the product or the shelf is edited from the
        # frame it edits and nothing else (2026-09-19).
        if len(refs) < 2 and item.get("characters"):
            out.append("an edit with fewer than two references — the previous frame "
                       "FIRST and the character's cast sheet SECOND, always; with the "
                       "frame alone the face drifts (live 2026-09-18)")
        if not refs:
            out.append("an edit with no reference at all — the frame it edits is "
                       "the one thing it cannot be made without")
        elif item.get("edit_of") and refs[0] != item["edit_of"]:
            out.append(f"the first reference is {refs[0]!r}, not the frame this edits "
                       f"({item['edit_of']}) — the first reference is the one whose "
                       f"detail is preserved")

    if cid == "talking":
        slice_ = _at(item, "medias.audio_references")
        if not slice_:
            out.append("a to-camera scene with no audio slice — attach this scene's "
                       "slice of the one voice track as audio_references")

    return out


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        for name, st in stations().items():
            print(f"{name:22} {st['door']:18} {model_of(name) or '—'}")
            print(f"{'':22} {st['makes']}")
        return 0
    st = station(argv[0])
    print(f"{argv[0]} — {st['door']} — {model_of(argv[0]) or '—'}")
    for f in st.get("fields", []):
        req = f.get("required")
        mark = "required" if req is True else ("optional" if req is False else str(req))
        print(f"  {f['name']:42} {mark:22} {f.get('values', '')}")
    print("  assembly: " + " · ".join(st["assembly"]["order"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
