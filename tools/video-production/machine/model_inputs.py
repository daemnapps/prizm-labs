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
    # One image door (the owner, 2026-09-18: "gpt for all image work"): when the
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


def model_of(station_name: str, model: str | None = None) -> str | None:
    """The station's model slug, read from providers.json — never written
    here. A RUN MAY PICK (the owner, 2026-09-22: "when we do video production we
    should have the ability to pick which models we want to run with"): a
    slug passed in wins over the registry's settled one, for this clip only.
    The registry still says what the house default is."""
    if model:
        return str(model)
    ptr = station(station_name).get("model_from")
    return dotted(ptr) if ptr else None


def clip_models(station_name: str = "motion") -> list[dict]:
    """THE MENU — every clip model this station can be pointed at, as rows a
    person reads: id, what it is good at, what it is weak at, credits a
    second, the ceiling. Straight off providers.json `models`; nothing is
    named in code."""
    reg = platform.registry()
    settled = str(dotted(f"doors.{station_name}.model") or "")
    # THE ROSTER (the owner, 2026-09-22: "I don't want to use wan at all, seedance
    # and minimax are good for sure") — when the registry declares one, the
    # menu IS the roster. A model in the book that is not on it is a record,
    # not an offer, and a menu of eight doors nobody ruled on is not a choice.
    roster = list(((reg.get("picking") or {}).get("roster") or {}).get("clip") or [])
    out = []
    for slug, m in (reg.get("models") or {}).items():
        stations = m.get("stations") or [m.get("station")]
        if station_name not in stations:
            continue
        if roster and slug not in roster:
            continue
        if str(m.get("status", "")).startswith(("retired", "audition")):
            continue
        rate = next((r for r in reversed(m.get("rates") or [])
                     if r.get("credits_per_second")), {})
        out.append({
            "model": slug,
            "settled": slug == settled,
            "good_at": list(m.get("good_at") or []),
            "weak_at": list(m.get("weak_at") or []),
            "credits_per_second": rate.get("credits_per_second"),
            "max_seconds": m.get("max_seconds"),
            "status": m.get("status", ""),
        })
    out.sort(key=lambda r: (not r["settled"], r.get("credits_per_second") or 99))
    return out


def model_fault(model: str | None, station_name: str = "motion") -> str:
    """A pick nothing on this station answers to is refused BY NAME, with
    the menu — never a silent fall back to the settled door, which is how a
    run quietly costs 3x what it was asked to."""
    if not model:
        return ""
    menu = clip_models(station_name)
    if any(r["model"] == str(model) for r in menu):
        return ""
    return (f"the run picked the clip model {model!r}, and no {station_name} model "
            f"answers to that name. The ones that do: "
            f"{', '.join(r['model'] for r in menu)}")


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


def door_of(station_name: str, model: str | None = None) -> dict:
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
    # One house, two slugs, two shapes (2026-09-22): the settled slug's row
    # is the plain door id; an alternate slug on the same connector has its
    # own row, `<door id>:<slug>`, so flipping providers.json's
    # doors.<station>.model to the alternate changes the shape with it.
    slug = model_of(station_name, model)
    return (rows.get(f"{mapped}:{slug}") if mapped and slug else None) \
        or rows.get(mapped) or rows.get(st.get("preferred_door")) or next(iter(rows.values()))


def end_image_door(station_name: str, model: str | None = None) -> tuple[str, bool, str]:
    """(door id, does it take the last frame as a real input, how it lands).
    A scene always has a last frame; this decides whether it is attached or
    described. A door that COULD take one but refuses it beside audio (the
    settled door's 422, 2026-09-22) says so in its own words."""
    row = door_of(station_name, model)
    if row.get("takes_end_image"):
        return row["id"], True, f"attached as {row.get('field')} on {row['id']}"
    if row.get("when_no_end_image"):
        return row.get("id", "?"), False, str(row["when_no_end_image"])
    return (row.get("id", "?"), False,
            f"described as the timeline's final beat — {row.get('id', 'this door')} "
            f"has no end-frame field")


def first_frame_role(station_name: str, model: str | None = None) -> str:
    """The media role the FIRST FRAME travels under on this station's door.
    `start_image` where the frames go as frames; `image_references` on a
    talking scene on the settled door, because start_image cannot be mixed
    with audio_references there (the 422 of 2026-09-22)."""
    return str(door_of(station_name, model).get("first_frame_role") or "start_image")


def clip_media_roles(station_name: str, model: str | None = None) -> list[str]:
    """EXACTLY the roles the clip carries on this station's door."""
    row = door_of(station_name, model)
    roles = row.get("clip_media_roles") or (station(station_name).get("limits") or {}).get("clip_media_roles")
    return list(roles or [])


def duration_span(station_name: str, model: str | None = None) -> list:
    """[floor, ceiling] in seconds on this station's door — the door row's
    own when it has one, else the station's limit."""
    row = door_of(station_name, model)
    span = row.get("duration_seconds") or (station(station_name).get("limits") or {}).get("duration_seconds")
    return list(span or [])


def door_params(station_name: str, model: str | None = None) -> dict:
    """Params a door needs that the settled one does not (the alternate's
    `mode` and `generate_audio`) — read off the door row, never written in
    code."""
    return dict(door_of(station_name, model).get("params") or {})


def fixed_resolution(station_name: str, model: str | None = None) -> str | None:
    """The one resolution this door makes, when it makes only one (the
    settled clip door: 2K)."""
    v = door_of(station_name, model).get("fixed_resolution")
    return str(v) if v else None


def door_rule(station_name: str, model: str | None = None) -> dict:
    """What rule 12 says when a scene does not fit this station's slug —
    `door_rules[<slug>]` in the contract, keyed by the slug the registry
    holds."""
    slug = model_of(station_name, model)
    return dict((contract().get("door_rules") or {}).get(slug or "") or {})


def end_attached(scene: dict, talking: bool) -> bool:
    """Is the LAST FRAME on the call? run.py stamps the scene once it has
    asked the door; a scene that has not been stamped asks the door here, so
    the prompt and the item can never disagree about it."""
    if "end_frame_attached" in scene:
        return bool(scene["end_frame_attached"])
    return end_image_door("talking" if talking else "motion")[1]


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
    first = _clean(((contract().get("frame_rules") or {}).get("first_instant") or {}).get("says"))
    if first:
        parts.append(first)
    words = (contract().get("aspect_words") or {}).get(_clean(piece.get("aspect")))
    if words:
        parts.append(words)
    return sep.join(parts)


def plate_prompt(plate: str, piece: dict | None = None) -> str:
    """A CARD's plate (2026-09-23): the picture the brief described, the
    piece's grade, the contract's clean line — no words laid over it — and
    the aspect words. The card's own words never enter this prompt."""
    piece = piece or {}
    parts = [_sentence(plate)] if _clean(plate) else []
    if _clean(piece.get("style")):
        parts.append(_sentence(piece["style"]))
    clean = _clean(card_plate().get("clean_line"))
    if clean:
        parts.append(clean)
    words = (contract().get("aspect_words") or {}).get(_clean(piece.get("aspect")))
    if words:
        parts.append(words)
    sep = station("still-generate")["assembly"].get("separator", " ")
    return sep.join(parts)


def edit_prompt(frame: dict, station_id: str = "still-edit-fidelity") -> str:
    """A LAST FRAME — the delta, then the one line that says what may not
    change. The delta alone lets an edit door re-decide the exposure, the
    wardrobe and the room; the pair then reads as two different shots the
    moment a clip runs from one to the other (live 2026-09-18)."""
    delta = _sentence(frame.get("delta") or frame.get("do") or "")
    if not delta:
        return ""
    asm = station(station_id).get("assembly") or {}
    keep = _clean(asm.get("keep_line"))
    out = f"{delta} {keep}".strip() if keep else delta
    # A faceless frame's body geometry travels with the edit: a camera move
    # re-frames the hands, it never re-seats the body (frame_rules.viewpoint,
    # live 2026-09-22 — two arms from opposite corners).
    vp = _clean(frame.get("viewpoint"))
    line = asm.get("keep_viewpoint_line")
    if vp and line:
        out = f"{out} {_sentence(line.replace('{viewpoint}', vp))}".strip()
    return out


def beats_of(scene: dict) -> list[dict]:
    """The scene's beats — the timed spans written into the clip's timeline.
    They are NOT pictures: a scene generates exactly two stills, its first
    frame and its last (the owner, 2026-09-18)."""
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
    out = [shape["first"].format(first=join.join(parts))]
    # @Image2 is named only where it travels. On the settled door a talking
    # scene attaches no end_image (start_image/end_image cannot be mixed
    # with reference media — the 422 of 2026-09-22), so the sentence is
    # dropped and the last beat says where the clip ends instead.
    if end_attached(scene, talking):
        out.append(shape["last"].format(last=join.join(tail)))
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
    # Where the last frame is attached the last beat settles on @Image2.
    # Where it is not (a talking scene on the settled door), the LAST
    # FRAME's Change is said in words — it is the one place the clip is told
    # where to end, and without it the model holds the last gesture.
    attached = end_attached(scene, talking)
    last_change = _mid(frame_of(scene, "last").get("delta"))
    if not attached and not last_change:
        return "", ["the LAST FRAME's Change (where the clip ends, in words — "
                    "this door attaches no end_image beside audio)"]
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
            line += (shape["last_beat"] if attached
                     else shape["last_beat_talking"].format(last_change=last_change))
        if _clean(b.get("beat")):
            line += shape["performance"].format(beat=_mid(b["beat"]))
        rows.append(line + ".")
    return "\n".join(rows), []


_CLAUSE_SPLIT = re.compile(r"\s*,\s*")
_STOPWORDS = {"no", "not", "a", "an", "the", "of", "on", "in", "and", "or",
              "with", "under", "over", "at", "from", "to", "its", "it"}


def _hold_clauses(lighting: str, scene: dict) -> tuple[str, list[str]]:
    """(the hold's lighting, the clauses dropped from it). A HOLD SENTENCE
    SAYS WHAT DOES NOT CHANGE, so a lighting clause the timeline contradicts
    cannot travel in it — live 2026-09-22 the first frame's honest 'no
    running water' became 'same … no running water … throughout' while beat
    4 moved the hand under the running tap, and the clip split the
    difference by running the tap with nobody turning it on ("the water just
    magically turned on"). The clause is true of the FIRST FRAME and false
    of the take."""
    beats = set(" ".join(_clean(b.get("do")) for b in
                         (scene.get("beats") or [])).lower().replace(".", "").split())
    if not beats:
        return lighting, []
    kept, dropped = [], []
    for clause in _CLAUSE_SPLIT.split(lighting):
        words = [w.strip(".").lower() for w in clause.split()]
        # ONLY A NEGATION can be contradicted by a beat. "plain daylight
        # across the counter" is a description of the light and holds all
        # take; "no running water" is a claim about what is not happening,
        # and a beat that turns the tap on makes it false.
        if words and words[0] in ("no", "not") and any(
                w in beats for w in words[1:] if w not in _STOPWORDS and len(w) > 3):
            dropped.append(clause)
        else:
            kept.append(clause)
    return (", ".join(kept) if kept else lighting), dropped


def hold_dropped(scene: dict) -> list[str]:
    """The lighting clauses the hold sentence could not carry, for the
    record and the board — a finding about the BRIEF, not a fault in the
    clip: the clause is true of the first frame and belongs only there."""
    first = frame_of(scene, "first")
    return _hold_clauses(_mid(first.get("lighting")), scene)[1]


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
    lighting, _dropped = _hold_clauses(lighting, scene)
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
# A BEAT IS ONE VISIBLE ACTION (the owner, 2026-09-19). One verb, present tense,
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


def needs_viewpoint(scene: dict, first: dict | None = None) -> bool:
    """A frame with no face in it needs its body geometry said in words
    (frame_rules.viewpoint): a B-roll scene whose `who` is hands or the
    product, or whose first frame says there is no face."""
    if scene.get("to_camera"):
        return False
    first = first if first is not None else frame_of(scene, "first")
    if not first:
        first = scene.get("first_frame") or {}
    who = _clean(scene.get("who")).lower()
    subj = _clean(first.get("subject")).lower()
    return ("hand" in who or "product" in who or "no face" in subj
            or "nobody's face" in subj or "faceless" in subj)


def viewpoint_fault(scene: dict, first: dict | None = None,
                    where: str = "the FIRST FRAME") -> str:
    first = first if first is not None else (frame_of(scene, "first")
                                             or scene.get("first_frame") or {})
    if needs_viewpoint(scene, first) and not _clean(first.get("viewpoint")):
        rule = (contract().get("frame_rules") or {}).get("viewpoint") or {}
        return (f"{where} shows no face and carries no 'viewpoint' — say whose "
                f"eyes the camera is and which edge every limb enters from, "
                f"elbows off-frame (e.g. {rule.get('example', '')}). Without it "
                f"the image door invents the body: live 2026-09-22 two arms came "
                f"in from opposite corners")
    return ""


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
# THE BRIEF IS THE PROMPT (the owner, 2026-09-19). A brief's truth is the last
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
              and k not in set(brief_schema().get("may_be_empty") or [])
              # a sung scene says its words as `lyrics` and leaves `voice` empty —
              # the brief prompt and SONG-CHAIN.md both ask for exactly that (7 Oct)
              and not (k == "voice" and str(obj.get("lyrics") or "").strip())):
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
    letting a take carry them (the owner, 2026-09-19: "humans don't use em
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

    # a v14 `module` stands in for a missing `section` (warned at the gate)
    doc = json.loads(json.dumps(doc))
    retire_module(doc)
    out: list[str] = []
    out.extend(doctrine_findings(doc)[0])
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
    got = _clean(piece.get("resolution"))
    fixed = fixed_resolution("motion")
    if fixed:
        # The settled clip door makes ONE resolution (2K, 2026-09-22), so the
        # piece's value sizes the stills and is not asked to match the clip;
        # a pixel pair is still refused — a size is not a resolution word.
        if got and re.fullmatch(r"\d+\s*[x×]\s*\d+", got):
            out.append(f"the piece's resolution {got!r} is a pixel pair — the clip "
                       f"door makes {fixed} and the still size is resolved from "
                       f"the aspect; write a resolution word (720p · 1080p · 2K)")
    else:
        row = field_named("motion", "resolution") or {}
        allowed = [v.strip() for v in str(row.get("values") or "").split("·")]
        allowed = [v.split(" ")[0] for v in allowed if v]
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
            # brief v17+ names the voice by source (banked · NEW · none) and the
            # voice itself lives in the person's element folder; v16 and older
            # carry cast_voice_id. Either shape is a voice named.
            v = c.get("voice")
            if not (isinstance(v, dict) and v.get("source")):
                _keys(f"cast[{i}]'s 'voice'", v, sch.get("cast_voice") or [], out)

    scenes = doc.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        out.append("the block names no scenes — 'scenes' is the brief")
        return out

    for sc in scenes:
        sid = (sc or {}).get("id", "?") if isinstance(sc, dict) else "?"
        where = f"scene {sid}"
        if is_card(sc):
            # A CARD (2026-09-23) is a plate and its words, not a clip: it is
            # asked for its own keys, never for frames or beats it cannot have
            out.extend(card_faults(sc))
            continue
        if kind_of(sc) in STILL_KINDS:
            # SCREEN · SPLIT · ENDCARD (ELEMENTS.md §1) — each is asked for
            # its own kind's keys, never for a talking scene's. A GREENSCREEN
            # is a talking scene, so it goes on through the scene checks below
            # and its background is asked for after them.
            out.extend(kind_faults(sc, doc))
            continue
        if kind_of(sc) == "greenscreen":
            out.extend(kind_faults(sc, doc))
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
        # `viewpoint` is optional on a frame with a face and required on one
        # without — viewpoint_fault below decides which, by name
        opt_ff = set((sch.get("optional") or {}).get("first_frame") or [])
        _keys(f"{where}'s 'first_frame'", sc.get("first_frame"),
              [k for k in (sch.get("first_frame") or []) if k not in opt_ff], out)
        ff = sc.get("first_frame")
        if isinstance(ff, dict) and "refs" in ff and not isinstance(ff["refs"], list):
            out.append(f"{where}'s first_frame.refs is "
                       f"{type(ff['refs']).__name__}, not a list")
        if isinstance(ff, dict):
            bad = viewpoint_fault(sc, ff, f"{where}'s first_frame")
            if bad:
                out.append(bad)
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
    out.extend(element_faults(doc))
    out.extend(roll_sheet_check(doc)[0])
    return out


# ------------------------------------------------ cards and the roll sheet
#
# the owner, 2026-09-23: "We need to ensure b-roll makes it into the actual
# production brief too, clearly AFTER a-roll is detailed, and it's carried
# through our process properly." B-roll is ideated from the swipe and MADE at
# production; so are cards. Type is a layer, never a generation — a card is a
# text-free PLATE the machine makes as one still, plus its exact words as
# data for the edit to set on top. The roll sheet is how the brief proves it
# carried every shot on the swipe's make-list.

def card_plate() -> dict:
    return contract().get("card_plate") or {}


def is_card(sc) -> bool:
    return isinstance(sc, dict) and _clean(sc.get("kind")).lower() == "card"


_QUOTED = re.compile(r"\"[^\"]{2,}\"|“[^”]{2,}”")


def card_faults(sc: dict) -> list[str]:
    """Every way a card scene fails its shape, each naming the card."""
    sc = _kind_fields(sc, "card")      # flat (v13) or nested `card: {...}`
    sid = sc.get("id", "?")
    where = f"card {sid}"
    sch = brief_schema()
    keys = sch.get("card") or ["id", "kind", "plate", "lines", "lands_on", "sfx", "voice"]
    may_empty = set(sch.get("card_may_be_empty") or [])
    out: list[str] = []
    for k in keys:
        if k not in sc:
            out.append(f"{where} is missing {k!r}")
        elif k not in may_empty and isinstance(sc[k], str) and not sc[k].strip():
            out.append(f"{where}'s {k!r} is empty — a key with nothing to say "
                       f"still says it; never drop it and never leave it blank")
    if "to_camera" in sc and sc["to_camera"] is not False:
        out.append(f"{where}'s 'to_camera' is {sc['to_camera']!r} — a card is "
                   f"never the speaker; it is false")
    lines = sc.get("lines")
    if "lines" in sc and (not isinstance(lines, list) or not any(_clean(l) for l in lines)):
        out.append(f"{where}'s 'lines' is not a list of the card's words — the "
                   f"words travel as data, one string per line, exactly as set")
    if "refs" in sc and not isinstance(sc["refs"], list):
        out.append(f"{where}'s 'refs' is {type(sc['refs']).__name__}, not a list")
    plate = _clean(sc.get("plate"))
    if plate:
        baked = _QUOTED.search(plate)
        hit = next((l for l in (lines if isinstance(lines, list) else [])
                    if len(_clean(l)) >= 4 and "[UNFILLED]" not in str(l)
                    and _clean(l).lower() in plate.lower()), None)
        if baked or hit:
            out.append(f"{where}'s plate has words in it "
                       f"({(baked.group(0) if baked else hit)!r}) — type is a layer, "
                       f"never a generation: describe the picture with empty space "
                       f"where the words go, and keep the words in 'lines'")
    if isinstance(sc.get("voice"), str) and sc["voice"].strip():
        out.extend(voice_faults(sc["voice"], f"{where}'s 'voice'"))
    return out


def card_warnings(sc: dict) -> list[str]:
    sc = _kind_fields(sc, "card")
    lines = sc.get("lines") if isinstance(sc.get("lines"), list) else []
    return [f"card {sc.get('id', '?')}: line {l!r} carries [UNFILLED] — the "
            f"offer file has not settled it; the plate is made, the words cannot ship"
            for l in lines if "[UNFILLED]" in str(l)]


_ROLL_HEAD = re.compile(r"^#+\s*ROLL SHEET CHECK\s*$", re.M | re.I)


def roll_sheet_of(brief) -> list[dict] | None:
    """The brief's carried-or-dropped table: the block's `roll_sheet` first,
    else the view's `## ROLL SHEET CHECK` table. None when the brief has
    neither — a brief written before v13."""
    doc, text = brief, ""
    if isinstance(brief, str):
        text = brief
        doc, _ = json_block(brief)
    if isinstance(doc, dict) and isinstance(doc.get("roll_sheet"), list):
        return [r for r in doc["roll_sheet"] if isinstance(r, dict)]
    m = _ROLL_HEAD.search(text or "")
    if not m:
        return None
    rows = []
    for line in text[m.end():].splitlines():
        s = line.strip()
        if not s:
            if rows:
                break
            continue
        if not s.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: ") or cells[0].lower() in ("swipe row", "row"):
            continue
        cells += [""] * (4 - len(cells))
        rows.append({"row": cells[0], "roll": cells[1], "scene": cells[2], "dropped": cells[3]})
    return rows


def roll_sheet_check(brief, scenes: list[dict] | None = None) -> tuple[list[str], list[str]]:
    """(fails, warns). Every make-list row maps to a scene of the matching
    kind, or is dropped with a reason. `scenes` may be the parsed rows (they
    carry `to_camera` and `kind`); otherwise the block's own scenes are read."""
    rows = roll_sheet_of(brief)
    if rows is None:
        return [], ["the brief carries no roll sheet — the swipe's make-list could not "
                    "be checked against its scenes (a brief written before the "
                    "2026-09-23 ruling); every B-roll shot and card on the swipe is "
                    "on trust"]
    if scenes is None:
        doc = brief if isinstance(brief, dict) else json_block(brief)[0]
        scenes = (doc or {}).get("scenes") or [] if isinstance(doc, dict) else []
    by_id = {str(s.get("id")): s for s in scenes if isinstance(s, dict) and s.get("id")}
    kinds = brief_schema().get("roll_kinds") or {
        "B-over": "broll", "B-vo": "broll", "B-silent": "broll", "C": "card", "A": "talking"}
    fails, warns = [], []
    if not rows:
        warns.append("the roll sheet is empty — a swipe with no make-list, or a table "
                     "left unfilled")
    for r in rows:
        name = _clean(r.get("row")) or "?"
        roll = _clean(r.get("roll"))
        sid = _clean(r.get("scene"))
        dropped = _clean(r.get("dropped"))
        want = next((v for k, v in kinds.items() if k.lower() == roll.lower()), None)
        if want is None:
            fails.append(f"roll sheet row {name!r}: roll {roll!r} is not a make-list "
                         f"label — it is one of {' · '.join(kinds)}")
            continue
        if not sid or sid.lower() in ("—", "-", "none"):
            if not dropped:
                fails.append(f"roll sheet row {name!r} ({roll}) maps to no scene and "
                             f"gives no drop reason — the shot was lost between the "
                             f"swipe and the brief; make it a scene or say why not")
            continue
        sc = by_id.get(sid)
        if sc is None:
            fails.append(f"roll sheet row {name!r} ({roll}) names scene {sid!r}, which "
                         f"is not in the brief's scenes")
            continue
        if _clean(sc.get("held")):
            warns.append(f"roll sheet row {name!r} ({roll}) maps to {sid}, which is HELD "
                         f"— nothing is made for it until it is released")
            continue
        got = ("card" if is_card(sc) or sc.get("type") == "C" else
               kind_of(sc) if kind_of(sc) in ELEMENT_KINDS else
               "talking" if sc.get("to_camera") is True else
               "broll" if sc.get("to_camera") is False else "unknown")
        if got != want:
            says = {"broll": "a B-roll scene (to_camera false)", "card": "a card scene "
                    "(kind card)", "talking": "a to-camera scene", "unknown": "a scene "
                    "with no to_camera", "screen": "a screen scene (kind screen)",
                    "split": "a split scene (kind split)", "greenscreen": "a greenscreen "
                    "scene (kind greenscreen)", "endcard": "an endcard scene (kind endcard)"}
            fails.append(f"roll sheet row {name!r} ({roll}) maps to {sid}, which is "
                         f"{says[got]} — a {roll} row is made as {says[want]}")
    return fails, warns


def production_gate(brief_text: str, scenes: list[dict],
                    brand: str | None = None) -> tuple[list[str], list[str]]:
    """The checks that run BEFORE anything is spent (2026-09-23): every scene
    says whether it is the speaker, every card is a plate and its words, every
    screen · split · greenscreen · endcard is its kind's shape (ELEMENTS.md
    §1), the layers, music, sfx and hooks are shapes the edit can read, and
    the swipe's make-list is carried or dropped row by row. (fails, warns)."""
    fails: list[str] = []
    warns: list[str] = []
    for s in scenes:
        if s.get("to_camera_missing"):
            fails.append(f"scene {s.get('id', '?')} does not say to_camera — true (the "
                         f"speaker, on screen, saying it) or false (B-roll, the voice "
                         f"over it). Nothing guesses which")
    doc, _ = json_block(brief_text)
    if isinstance(doc, dict):
        warns.extend(retire_module(doc))
        d_fails, d_warns = doctrine_findings(doc)
        fails.extend(d_fails)
        warns.extend(d_warns)
        for sc in doc.get("scenes") or []:
            if is_card(sc):
                fails.extend(card_faults(sc))
                warns.extend(card_warnings(sc))
            elif kind_of(sc) in ELEMENT_KINDS:
                fails.extend(kind_faults(sc, doc, brand))
                warns.extend(kind_warnings(sc, brand))
        fails.extend(element_faults(doc))
    f, w = roll_sheet_check(brief_text, scenes)
    return fails + f, warns + w


# ------------------------------------------- the element kinds (ELEMENTS.md)
#
# the owner, 2026-09-23: "teardown names every element, the AI brief carries it,
# production makes it (or pulls it from a bank made once), the edit only
# assembles … all these elements need to be green." Each kind below is
# refused by name when its shape is wrong, before anything is spent.

ELEMENT_KINDS = ("screen", "split", "greenscreen", "endcard")
# the kinds that are not a talking scene: no first frame / beats / voice asked
STILL_KINDS = ("screen", "split", "endcard")


def elements() -> dict:
    return contract().get("elements") or {}


def kind_of(sc) -> str:
    return _clean((sc or {}).get("kind")).lower() if isinstance(sc, dict) else ""


def _kind_fields(sc: dict, kind: str) -> dict:
    nested = sc.get(kind)
    return {**sc, **nested} if isinstance(nested, dict) else dict(sc)


def plate_word_fault(where: str, text, lines=()) -> str:
    """Type is a layer, never a generation: a picture description that quotes
    words, or copies one of the scene's own lines, is refused by name."""
    text = _clean(text)
    if not text:
        return ""
    baked = _QUOTED.search(text)
    hit = next((l for l in (lines or []) if len(_clean(l)) >= 4
                and "[UNFILLED]" not in str(l) and _clean(l).lower() in text.lower()), None)
    if baked or hit:
        return (f"{where} has words in it ({(baked.group(0) if baked else hit)!r}) — type "
                f"is a layer, never a generation: describe the picture with empty space "
                f"where the words go, and keep the words as data for the edit")
    return ""


def _enum_fault(where: str, value, allowed: list[str]) -> str:
    v = _clean(value).lower()
    if v in [a.lower() for a in allowed]:
        return ""
    return f"{where} is {value!r} — it is one of: {' · '.join(allowed)}"


# ------------------------------------ the doctrine's words (2026-09-23)
#
# A scene's `section` and the piece's `framework` are the MARKETING DOCTRINE's
# ids, read from components/marketing-doctrine at run time and never restated
# here (its README, "The one rule"). v14's six-word `module` tag was a second,
# coarser copy of the sections list; it is read now only as a deprecated alias
# for `section`, with a warning, through `elements.module_deprecated`.

DOCTRINE = HERE.parents[1].parent / "components" / "marketing-doctrine"
SECTIONS_FILE = DOCTRINE / "frameworks.json"
AD_FRAMEWORKS_FILE = DOCTRINE / "ad-frameworks.json"
OBSERVED = re.compile(r"^observed\s*[—–-]\s*\S")


def _doctrine_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"the marketing doctrine cannot be read ({path}: {e}) — "
                         f"section and framework ids come only from there")


def section_ids() -> list[str]:
    """The doctrine's section ids, in its own order — read, never listed here."""
    return [str(s["id"]) for s in _doctrine_json(SECTIONS_FILE).get("sections") or []
            if isinstance(s, dict) and s.get("id")]


def ad_frameworks() -> list[dict]:
    """The doctrine's ad-framework rows ({id, name, ...}) — read, never listed here."""
    return [f for f in _doctrine_json(AD_FRAMEWORKS_FILE).get("frameworks") or []
            if isinstance(f, dict) and f.get("id")]


def module_as_section(module) -> str:
    """The section id a deprecated v14 `module` value stands for: the two
    renames in `elements.module_deprecated`, every other value as itself."""
    v = _clean(module).lower()
    renames = (elements().get("module_deprecated") or {}).get("renames") or {}
    return renames.get(v, v)


def framework_id(value) -> str:
    """The ad-framework id a piece's `framework` names: the id itself, or the
    id of the row whose full name it spells (an older brief wrote the name).
    Anything else comes back unchanged — `observed — …` included."""
    v = _clean(value)
    for f in ad_frameworks():
        if v.lower() in (str(f["id"]).lower(), _clean(f.get("name")).lower()):
            return str(f["id"])
    return v


def retire_module(doc) -> list[str]:
    """Read every scene's deprecated `module` as its `section` (filling a
    missing one, never overriding one the scene states), drop the key, and
    say so. Mutates `doc`; returns the warnings."""
    warns: list[str] = []
    if not isinstance(doc, dict):
        return warns
    for sc in doc.get("scenes") or []:
        if not isinstance(sc, dict) or "module" not in sc:
            continue
        mod = sc.pop("module")
        as_sec = module_as_section(mod)
        where = f"scene {sc.get('id', '?')}"
        if not _clean(sc.get("section")):
            sc["section"] = as_sec
            warns.append(f"{where} carries 'module' {mod!r}, retired 2026-09-23 — read as "
                         f"section {as_sec!r}; write 'section' with a doctrine id instead")
        else:
            clash = ("" if as_sec == _clean(sc["section"]).lower() else
                     f", and it disagrees with the section — the section wins")
            warns.append(f"{where} carries 'module' {mod!r}, retired 2026-09-23 — ignored; "
                         f"its section {sc['section']!r} is what the edit swaps{clash}")
    return warns


CANDIDATE = re.compile(r"candidate", re.I)


def doctrine_findings(doc) -> tuple[list[str], list[str]]:
    """(fails, warns). Every scene's `section` is a doctrine section id and
    the piece's `framework` an ad-framework id (or `observed — …`); a value
    off either list is refused naming the real ids. A section the teardown
    flagged `(candidate for the bank)` is warned, never refused — it is a
    finding for the owner, not a new id."""
    fails: list[str] = []
    warns: list[str] = []
    if not isinstance(doc, dict):
        return fails, warns
    ids = section_ids()
    for sc in doc.get("scenes") or []:
        if not isinstance(sc, dict) or "section" not in sc:
            continue          # a missing key is _keys' finding, not this one
        v = _clean(sc.get("section"))
        where = f"scene {sc.get('id', '?')}'s 'section'"
        if v.lower() in ids:
            continue
        if CANDIDATE.search(v):
            warns.append(f"{where} is {v!r} — a candidate for the doctrine's sections, "
                         f"carried as written; only the doctrine's owner adds an id")
            continue
        fails.append(f"{where} is {v!r} — a section id from "
                     f"components/marketing-doctrine/frameworks.json: {' · '.join(ids)}")
    piece = doc.get("piece") if isinstance(doc.get("piece"), dict) else {}
    if "framework" in piece:
        raw = _clean(piece.get("framework"))
        rows = ad_frameworks()
        fids = [str(f["id"]) for f in rows]
        got = framework_id(raw)
        if raw in fids or OBSERVED.match(raw):
            pass
        elif got in fids:
            warns.append(f"the piece's 'framework' {raw!r} is the row's name — read as "
                         f"its id {got!r}; write the id")
        elif raw:
            # the owner, 2026-09-23: "this ad framework might be unique, which is fine —
            # that's why we develop this to create its own and we just use sections …
            # we can name it whatever we want if it doesn't fit a normal convention."
            # A framework of its own is carried as named; the SECTIONS are the contract.
            warns.append(f"the piece's framework {raw!r} is its own (not one of "
                         f"{' · '.join(fids)}) — carried as named; promote it to the "
                         f"doctrine's bank once it's proven")
    return fails, warns


def _side_faults(where: str, side) -> list[str]:
    """One side of a split: a B-roll picture — its setting, both frames and
    its beats, held to the same rules as any B-roll scene."""
    sch = brief_schema()
    out: list[str] = []
    if not isinstance(side, dict):
        return [f"{where} is not an object — each side is a B-roll picture: "
                f"{', '.join(sch.get('split_side') or [])}"]
    _keys(where, side, sch.get("split_side") or [], out)
    opt_ff = set((sch.get("optional") or {}).get("first_frame") or [])
    ff = side.get("first_frame")
    _keys(f"{where}'s 'first_frame'", ff,
          [k for k in (sch.get("first_frame") or []) if k not in opt_ff], out)
    if isinstance(ff, dict):
        bad = viewpoint_fault({**side, "to_camera": False}, ff, f"{where}'s first_frame")
        if bad:
            out.append(bad)
        for k in ("subject", "action", "composition"):
            bad = plate_word_fault(f"{where}'s first_frame.{k}", ff.get(k))
            if bad:
                out.append(bad)
    lf = side.get("last_frame")
    _keys(f"{where}'s 'last_frame'", lf, sch.get("last_frame") or [], out)
    if isinstance(lf, dict):
        bad = camera_fault(lf.get("camera"), f"{where}'s last_frame.camera")
        if bad:
            out.append(bad)
    beats = side.get("beats")
    if not isinstance(beats, list) or not beats:
        out.append(f"{where} has no beats — a side is animated like B-roll, and a "
                   f"clip with nothing on its timeline is a still with a duration")
    else:
        for b in beats:
            if isinstance(b, dict):
                _keys(f"{where} beat {b.get('id', '?')}", b, sch.get("beat") or [], out)
                out.extend(beat_faults(b, f"{b.get('id', '?')} of {where}"))
    return out


def kind_faults(sc: dict, doc: dict | None = None, brand: str | None = None) -> list[str]:
    """Every way a screen · split · greenscreen · endcard scene fails its
    shape, each naming the scene and the field."""
    kind = kind_of(sc)
    sid = sc.get("id", "?")
    where = f"{kind} {sid}"
    sch = brief_schema()
    en = elements()
    f = _kind_fields(sc, kind)
    out: list[str] = []
    may_empty = set(sch.get(f"{kind}_may_be_empty") or [])
    for k in sch.get(kind) or []:
        if k not in f:
            out.append(f"{where} is missing {k!r}")
        elif k not in may_empty and isinstance(f[k], str) and not f[k].strip():
            out.append(f"{where}'s {k!r} is empty — a key with nothing to say still "
                       f"says it; never drop it and never leave it blank")
    if kind == "greenscreen":
        if f.get("to_camera") is not True:
            out.append(f"{where}'s 'to_camera' is {f.get('to_camera')!r} — a greenscreen "
                       f"is the speaker keyed over a background; it is true")
    elif "to_camera" in f and f["to_camera"] is not False:
        out.append(f"{where}'s 'to_camera' is {f['to_camera']!r} — a {kind} is never "
                   f"the speaker; it is false")
    lines = f.get("lines") if isinstance(f.get("lines"), list) else []
    if kind == "screen":
        if "lines" in f and (not isinstance(f.get("lines"), list) or not any(_clean(l) for l in lines)):
            out.append(f"{where}'s 'lines' is not a list of the screen's words — the "
                       f"legible text travels as data and the edit sets it")
        if "surface" in f:
            bad = _enum_fault(f"{where}'s 'surface'", f["surface"], en.get("surface") or [])
            if bad:
                out.append(bad)
        bad = plate_word_fault(f"{where}'s plate", f.get("plate"), lines)
        if bad:
            out.append(bad)
    elif kind == "greenscreen":
        if "layout" in f:
            bad = _enum_fault(f"{where}'s 'layout'", f["layout"], en.get("greenscreen_layout") or [])
            if bad:
                out.append(bad)
        bad = plate_word_fault(f"{where}'s background", f.get("background"))
        if bad:
            out.append(bad)
        talker = _clean(f.get("talker_scene"))
        if talker and isinstance(doc, dict):
            row = next((s for s in doc.get("scenes") or []
                        if isinstance(s, dict) and str(s.get("id")) == talker), None)
            if row is None:
                out.append(f"{where}'s talker_scene {talker!r} is not in the brief's scenes "
                           f"— the presenter is a talking scene made like any other")
            elif row.get("to_camera") is not True or kind_of(row) not in ("", "talking", "greenscreen"):
                out.append(f"{where}'s talker_scene {talker} is not a to_camera scene — the "
                           f"presenter keyed over the background has to be the speaker, "
                           f"to camera")
    elif kind == "split":
        if "layout" in f:
            bad = _enum_fault(f"{where}'s 'layout'", f["layout"], en.get("split_layout") or [])
            if bad:
                out.append(bad)
        if "labels" in f and not isinstance(f["labels"], list):
            out.append(f"{where}'s 'labels' is {type(f['labels']).__name__}, not a list")
        for side in ("left", "right"):
            if side in f:
                out.extend(_side_faults(f"{where}'s {side}", f[side]))
    elif kind == "endcard":
        bad = plate_word_fault(f"{where}'s plate", f.get("plate"),
                               f.get("offer_lines") if isinstance(f.get("offer_lines"), list) else [])
        if bad:
            out.append(bad)
        offers = f.get("offer_lines")
        if "offer_lines" in f and (not isinstance(offers, list) or not any(_clean(l) for l in offers)):
            out.append(f"{where}'s 'offer_lines' is not a list of the offer's words")
        brand = brand or _clean(((doc or {}).get("piece") or {}).get("brand"))
        bf = _brandfiles()
        for line in offers if isinstance(offers, list) else []:
            if "[UNFILLED]" in str(line):
                continue
            ok, why = bf.offer_line_found(brand, line)
            # the owner, 2026-09-23 ("improvise and infer, don't overcomplicate"): the FIGURES
            # must be the offer bank's; the wording around them may be natural. So a line
            # whose every figure is in the bank passes; only an unknown figure is refused.
            if not ok and "figures are in offer-bank.md" in str(why):
                ok = True
            # A line with no figure at all is wording, not an offer term (2026-09-30:
            # an organic swipe's end card asks a question — "Who would you choose?" —
            # and "if the swipe has it, that's what we do"). Only figures are checked.
            if not ok and not re.search(r"[0-9$£€%]", str(line)):
                ok = True
            if not ok:
                out.append(f"{where}'s offer line {line!r} is not from the offer bank ({why}) "
                           f"— an endcard's figures come from brands/{brand or '<brand>'}/"
                           f"products/offer-bank.md or carry [UNFILLED]")
        g = (f.get("guarantee") or "")
        if _clean(g) and "[UNFILLED]" not in str(g):
            ok, why = bf.offer_line_found(brand, g)
            if not ok:
                out.append(f"{where}'s guarantee {g!r} is not from the offer bank ({why}) — "
                           f"a guarantee the offer file does not hold is an empty string")
        product, why = endcard_product(sc, doc, brand)
        if not product:
            out.append(f"{where} names no product the brand has a packshot for ({why}) — add "
                       f"\"product\": \"<slug>\" to its endcard block; the plate is an edit of "
                       f"the brand's own photograph, never a product generated from words")
        else:
            got, why = bf.packshot_of(brand, product)
            if got is None:
                out.append(f"{where}'s product {product!r} has no real packshot ({why}) — the "
                           f"plate is an edit of the brand's own photograph, never a product "
                           f"generated from words")
    if kind != "greenscreen" and isinstance(f.get("voice"), str) and f["voice"].strip():
        out.extend(voice_faults(f["voice"], f"{where}'s 'voice'"))
    out.extend(_scene_element_faults(sc))
    return out


def kind_warnings(sc: dict, brand: str | None = None) -> list[str]:
    kind = kind_of(sc)
    f = _kind_fields(sc, kind)
    field = {"screen": "lines", "endcard": "offer_lines"}.get(kind)
    vals = f.get(field) if field and isinstance(f.get(field), list) else []
    out = [f"{kind} {sc.get('id', '?')}: line {l!r} carries [UNFILLED] — the offer "
           f"file has not settled it; the plate is made, the words cannot ship"
           for l in vals if "[UNFILLED]" in str(l)]
    if kind == "endcard" and _clean(f.get("cta")) and "[UNFILLED]" not in str(f.get("cta")):
        ok, why = _brandfiles().offer_line_found(brand, f["cta"])
        if not ok:
            out.append(f"endcard {sc.get('id', '?')}: the cta {f['cta']!r} is not in the offer "
                       f"bank ({why}) — check it against the offer file before it ships")
    return out


def _norm_words(s) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s or "").lower().replace("™", "")).split())


def endcard_product(sc: dict, doc: dict | None = None, brand: str | None = None):
    """(product slug, why). The endcard's own `product` when it names one;
    otherwise the ONE product of the brand's images.json whose title or slug
    the endcard's refs, plate or the brief's product_lock name. None when no
    product, or more than one, is named — the gate says which."""
    f = _kind_fields(sc, "endcard")
    if _clean(f.get("product")):
        return _clean(f["product"]), "named by the endcard"
    brand = brand or _clean(((doc or {}).get("piece") or {}).get("brand"))
    piece_product = _clean(((doc or {}).get("piece") or {}).get("product"))
    if piece_product:
        return piece_product, "named by the piece"
    bf = _brandfiles()
    root = bf.brand_root(brand)
    known = bf._images_json(root) if root else {}
    if not known:
        return None, f"brand {brand!r} declares no products in products/images.json"
    refs = f.get("refs") if isinstance(f.get("refs"), list) else [f.get("refs")]
    text = " ".join([_clean(r) for r in refs] + [_clean(f.get("plate"))]
                    + [_clean(x) for x in ((doc or {}).get("product_lock") or [])
                       if isinstance(x, str)])
    hay = f" {_norm_words(text)} "
    hits = sorted(k for k, row in known.items()
                  if f" {_norm_words(k)} " in hay
                  or (_norm_words((row or {}).get("title")) and
                      f" {_norm_words(row.get('title'))} " in hay))
    if len(hits) == 1:
        return hits[0], "the one brand product its refs, plate or product_lock name"
    if hits:
        return None, f"it names more than one product ({', '.join(hits)})"
    return None, f"its refs, plate and product_lock name none of: {', '.join(sorted(known))}"


_BF = None


def _brandfiles():
    global _BF
    if _BF is None:
        spec = importlib.util.spec_from_file_location("vm_brandfiles", HERE / "brandfiles.py")
        _BF = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BF)
    return _BF


def _scene_element_faults(sc: dict) -> list[str]:
    """`opens`, `priority` on any scene — absent is fine. (`section` is the
    doctrine's, checked by `doctrine_findings`; `module` is retired.)"""
    en = elements()
    where = f"scene {sc.get('id', '?')}"
    out = []
    if "opens" in sc and not isinstance(sc["opens"], bool):
        out.append(f"{where}'s 'opens' is {sc['opens']!r} — true on the scroll-stopper, "
                   f"false or absent everywhere else")
    if "priority" in sc:
        p = sc["priority"]
        lo, hi = (en.get("priority_range") or [1, 3])
        if isinstance(p, bool) or not isinstance(p, int) or not lo <= p <= hi:
            out.append(f"{where}'s 'priority' is {p!r} — a whole number {lo} (never cut) "
                       f"to {hi} (first to go); a cutdown cuts the highest first")
    kind = kind_of(sc)
    if kind:
        wants = brief_schema().get("scene_kinds") or {}
        if kind not in wants:
            out.append(f"{where}'s 'kind' is {sc.get('kind')!r} — it is one of: "
                       f"{' · '.join(wants)}")
        elif "to_camera" in sc and isinstance(sc["to_camera"], bool) \
                and sc["to_camera"] is not wants[kind]:
            out.append(f"{where} is kind {kind} with to_camera {sc['to_camera']} — a {kind} "
                       f"scene is to_camera {str(wants[kind]).lower()}; the two must agree")
    return out


def element_faults(doc) -> list[str]:
    """The piece-level elements the edit reads — `layers`, `music`, `sfx`,
    `hooks` — and every scene's `opens` / `priority`, checked
    against ELEMENTS.md's enums. Each finding names its field."""
    if not isinstance(doc, dict):
        return []
    en = elements()
    scenes = [s for s in doc.get("scenes") or [] if isinstance(s, dict)]
    ids = {str(s.get("id")) for s in scenes if s.get("id")}
    out: list[str] = []
    for s in scenes:
        if kind_of(s) not in ELEMENT_KINDS:     # kind_faults already asks these
            out.extend(_scene_element_faults(s))
    openers = [str(s.get("id")) for s in scenes if s.get("opens") is True]
    if len(openers) > 1:
        out.append(f"'opens' is true on {', '.join(openers)} — one scene is the "
                   f"scroll-stopper; a second opener is a hook, and goes in 'hooks'")
    elif not openers and any("opens" in s for s in scenes):
        out.append("'opens' is true on no scene — exactly one scene is the scroll-stopper")

    def scene_ref(where, v):
        if _clean(v) and _clean(v) not in ids:
            out.append(f"{where} names scene {v!r}, which is not in the brief's scenes")

    def rows(name, v):
        if not isinstance(v, list):
            out.append(f"{name} is {type(v).__name__}, not a list")
            return []
        bad = [i for i, r in enumerate(v, 1) if not isinstance(r, dict)]
        for i in bad:
            out.append(f"{name}[{i}] is not an object")
        return [(i, r) for i, r in enumerate(v, 1) if isinstance(r, dict)]

    layers = doc.get("layers")
    if layers is not None:
        if not isinstance(layers, dict):
            out.append(f"'layers' is {type(layers).__name__}, not an object of "
                       f"{' · '.join(en.get('layers') or [])}")
        else:
            for k in layers:
                if k not in (en.get("layers") or []):
                    out.append(f"layers.{k} is not a layer — the layers are: "
                               f"{' · '.join(en.get('layers') or [])}")
            hook = layers.get("hook")
            if hook is not None and not (isinstance(hook, dict) and "text" in hook):
                out.append("layers.hook has no 'text' key — the hook is {text, look}, on "
                           "screen from frame one (an empty string when there is none)")
            cap = layers.get("captions")
            if cap is not None and not (isinstance(cap, dict) and "look" in cap):
                out.append("layers.captions has no 'look' key — a look id from "
                           "looks/bank.json, match-swipe, or an empty string")
            if "lower_thirds" in layers:
                for i, r in rows("layers.lower_thirds", layers["lower_thirds"]):
                    scene_ref(f"layers.lower_thirds[{i}].scene", r.get("scene"))
                    if not _clean(r.get("name")):
                        out.append(f"layers.lower_thirds[{i}] has no 'name'")
            for key, enum in (("annotations", "annotation_kind"),
                              ("platform_ui", "platform_ui_kind")):
                if key in layers:
                    for i, r in rows(f"layers.{key}", layers[key]):
                        scene_ref(f"layers.{key}[{i}].scene", r.get("scene"))
                        bad = _enum_fault(f"layers.{key}[{i}].kind", r.get("kind"),
                                          en.get(enum) or [])
                        if bad:
                            out.append(bad)
            if "transitions" in layers:
                for i, r in rows("layers.transitions", layers["transitions"]):
                    scene_ref(f"layers.transitions[{i}].after_scene", r.get("after_scene"))
                    bad = _enum_fault(f"layers.transitions[{i}].kind", r.get("kind"),
                                      en.get("transition_kind") or [])
                    if bad:
                        out.append(bad)
    music = doc.get("music")
    if music is not None:
        if not isinstance(music, dict):
            out.append(f"'music' is {type(music).__name__}, not {{energy, tempo_bpm, mood}}")
        else:
            bad = _enum_fault("music.energy", music.get("energy"), en.get("music_energy") or [])
            if bad:
                out.append(bad)
            bpm = music.get("tempo_bpm")
            if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not 30 <= bpm <= 240:
                out.append(f"music.tempo_bpm is {bpm!r} — a number of beats a minute "
                           f"(30 to 240)")
            if not _clean(music.get("mood")):
                out.append("music.mood is empty — the bank is picked by energy, tempo "
                           "and mood")
    if "sfx" in doc:
        for i, r in rows("'sfx'", doc["sfx"]):
            if not _clean(r.get("cue")):
                out.append(f"sfx[{i}] has no 'cue' — the cue is the bank row's name")
            if not (_clean(r.get("at_words")) or _clean(r.get("scene"))):
                out.append(f"sfx[{i}] ({r.get('cue', '?')}) says neither 'at_words' nor "
                           f"'scene' — the edit has nowhere to land it")
            scene_ref(f"sfx[{i}].scene", r.get("scene"))
    if "hooks" in doc:
        for i, r in rows("'hooks'", doc["hooks"]):
            if not _clean(r.get("id")) or not _clean(r.get("text")):
                out.append(f"hooks[{i}] needs 'id' and 'text' — one render per hook, "
                           f"same body")
            scene_ref(f"hooks[{i}].opener_scene", r.get("opener_scene"))
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

    # A SCENE THAT DOES NOT SAY WHETHER IT IS THE SPEAKER (2026-09-23) is
    # refused, never defaulted — a default is how B-roll became a face
    if item.get("to_camera_missing"):
        out.append(f"scene {item.get('for') or item.get('id')} does not say to_camera — "
                   f"true (the speaker, saying it) or false (B-roll, the voice over "
                   f"it); nothing guesses which")

    # a picked model changes the door's shape, so every lookup below reads
    # the item's own model (the owner's pick, 2026-09-22), not just the registry
    pick = item.get("model") if item.get("model_picked") else None
    door = door_of(cid, pick)
    door_roles = clip_media_roles(cid, pick) if cid in ("motion", "talking") else []
    for f in st.get("fields", []):
        req, where = f.get("required"), f.get("item")
        if req is not True or not where:
            continue
        # a field the CHOSEN door has no place for is not a missing field —
        # the contract says where it lands instead, and the sheet says so
        if f.get("when_absent") and door and not door.get("takes_end_image"):
            continue
        # a media role the CHOSEN door does not carry (the alternate door
        # sends the first frame as start_image where the settled one sends
        # image_references) is checked by that door's own roles below
        if where.startswith("medias.") and door_roles and where.split(".", 1)[1] not in door_roles:
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
        # the paragraph has to fit the clip the door will make — the span
        # is the DOOR's (the settled slug: 4–15 s; the alternate: 4–30 s),
        # and the slug's own rule says what to do past it
        span = duration_span(cid, pick)
        rule = door_rule(cid, pick)
        dur = (item.get("params") or {}).get("duration")
        if not dur:
            out.append("no duration — the scene's own slice of the one voice track "
                       "decides how long the clip runs, and nothing else may")
        elif span and float(dur) > float(span[1]):
            out.append(f"the voice paragraph runs {dur}s, past this door's {span[1]}s "
                       f"ceiling — "
                       + (str(rule["over_ceiling"]) if rule.get("over_ceiling")
                          else "split the scene at a beat boundary, never mid-sentence"))
        # EXACTLY the door's own roles on the clip, and nothing else: the
        # first frame carries the identity, so a cast sheet or a style frame
        # attached beside it is a second opinion about the same face. The
        # roles are the DOOR's: on the settled door a talking scene is
        # image_references + audio_references and a silent one start_image
        # + end_image — the two cannot mix (the 422 of 2026-09-22).
        allowed = clip_media_roles(cid, pick)
        if allowed:
            seen = [m.get("role") for m in (item.get("medias") or []) if isinstance(m, dict)]
            for role in seen:
                if role not in allowed:
                    why = limits.get("clip_media_roles_why", "")
                    if role in ("start_image", "end_image") and door.get("why_no_end_image"):
                        why = door["why_no_end_image"]
                    out.append(f"the clip carries a {role!r} media — this door takes only "
                               f"{', '.join(allowed)}; {why}")
            first_role = first_frame_role(cid, pick)
            if first_role in allowed and first_role not in seen:
                out.append(f"the clip attaches no {first_role!r} — the first frame is what "
                           f"it starts on, and on this door it travels as a media, not as words")
            if "end_image" in allowed and "end_image" not in seen:
                out.append("the clip attaches no 'end_image' — the last frame is what it "
                           "lands on, and on this door it travels as a media, not as words")
        for gap in (item.get("model_missing") or []):
            out.append(gap)
        # a prompt that could not be assembled from labelled fields
        for gap in (item.get("prompt_missing") or []):
            out.append(f"the prompt could not be assembled — missing {gap}. A block "
                       f"built from a gap is a fragment, and a fragment is how a clip "
                       f"ends up being about something else")

    if cid == "still-generate":
        # a faceless first frame with no body geometry — the door would
        # invent it (frame_rules.viewpoint, live 2026-09-22)
        for gap in (item.get("prompt_missing") or []):
            out.append(gap)

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
