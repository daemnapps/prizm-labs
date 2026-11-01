"""The clip prompt — the ONLY one the chain writes — in the way BytePlus says Seedance 2.5 reads it (2026-10-26).

Source: https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide — reference assets are bound by number and
job; a one-sentence summary; a timeline in whole-second windows with ONE visible change each; consistency notes at the
end; positive wording, with negatives only for subtitles and music. This replaces the Omni-era paragraph that
the retired Omni writer produced for another model and that `seedance.py` used to wrap a second time.

    build(call, scenes, people, words, style, lead) -> {"prompt", "windows", "dropped", "words", "acting"}

Brand-agnostic: everything comes from the call, the brief's scenes and the cast. Reads `clips_run` helpers by path.
Rules (each one a fault found in the 21 Oct Yai plan, see PROMPT-CHANGES-SEEDANCE.md):
  * the first picture is BOUND ("Image 1 is the first frame"), a voice read is BOUND ("Audio 1 is X's voice")
  * the words are in the audio, never typed again beside it (a repeated line is what triggers burnt-in subtitles)
  * no identity paragraph: the picture is the identity; the cast's marks are not re-described
  * emotion labels become what the face and hands do; the person's habit list is not dumped into every clip
  * one visible action per window of at least two and a half seconds; the rest is dropped by name, never crammed
  * no second picture is named unless a second picture is sent
"""
from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_WINDOW = 2.5          # seconds a window needs to hold one visible change without cuts or skipped actions
MAX_PER_WINDOW = 2        # the guide: too much in a window gives excess cuts or a dropped plot

CAMERA = {
    "selfie": "handheld phone selfie at arm's length, a slight natural drift with the arm and breathing",
    "mirror": "handheld mirror selfie, a slight natural drift with the arm and breathing",
    "held": "handheld phone footage, a slight natural drift",
    "still": "static phone frame, propped and not moving",
    "push-in": "slow handheld push-in toward the face",
    "pan": "slow handheld pan following the action",
    "tilt": "slow handheld tilt following the action",
    "arc": "slow handheld arc around the person, face kept in frame",
    "handheld": "handheld phone footage, a slight natural drift",
    "hold": "static phone frame, propped and not moving",
}

# V10 (camera and cutting like TV, adapted to a phone): how one moment hands to the next inside a take, and how a take ends
HAND = {"continuous": "Without a cut, the phone carries straight on into the next moment.",
        "action": "The next moment starts in the middle of that movement.",
        "match": "The next moment picks up the same shape and position.",
        "whip": "The phone whips quickly to one side and settles on the next moment."}
END = {"continuous": "The take ends mid-movement, still going, so the next clip carries straight on from it.",
       "action": "The take ends in the middle of a movement, so the next clip picks the movement up.",
       "match": "The take ends holding a clear shape and position for the next clip to match.",
       "whip": "The take ends on a quick whip of the phone to one side."}

VIDEO_LINE = ("Video {n} is a motion reference only: copy how the camera moves, how the person and hands move, where each touch "
              "lands and the timing of each movement. Take nothing else from it: no person, face, hair, clothing, place, words or subtitles.")


def video_lines(refs) -> list:
    """One bound line per reference video, in upload order (the guide: bind every file by number and job). `refs` is
    the call's refs (a real person's movement is bound by movement.LINE) or, as before, how many swipe pieces."""
    if isinstance(refs, int):
        refs = [{}] * refs
    out = []
    for i, r in enumerate(refs, 1):
        if r.get("kind") == "movement":
            out.append(_movement().LINE.format(n=i))
        else:
            out.append(VIDEO_LINE.format(n=i))
    return out


def _movement():
    sp = importlib.util.spec_from_file_location("sp_movement", HERE / "movement.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


_rc = None


def _runner():
    global _rc
    if _rc is None:
        sp = importlib.util.spec_from_file_location("sp_clips_run", HERE / "clips_run.py")
        _rc = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(_rc)
    return _rc


def _sentence(t: str) -> str:
    t = " ".join(str(t or "").split()).strip()
    return (t[:1].upper() + t[1:]).rstrip(".") + "." if t else ""


def shots_of(call: dict, scenes: dict) -> list:
    """Every shot the call shows, in order; a split part takes only the shots its own words fall in (P60)."""
    oc = _runner()
    out = []
    for sid in call.get("scenes") or []:
        part = next((l for l in call.get("lines") or [] if l.get("scene") == sid and l.get("part")), None)
        out += oc.shots_in(scenes.get(sid), part.get("text") if part else None)
    return out


def nod_scenes(call: dict) -> set:
    """Scenes whose line is only a sound ("mm-hmm"): the person nods, lips closed — the brief's "murmurs" would move the lips."""
    return {l["scene"] for l in call.get("lines") or [] if l.get("sound") and l.get("nod") and not l.get("on_camera")}


def actions_of(call: dict, scenes: dict, people: dict | None = None) -> list:
    """The visible actions of the take, in order, each once. A beat that names no shot belongs to the scene, not to every
    shot of it (the 21 Oct plan repeated one 11-step list four times in one 10-second clip). A scene with no beats
    contributes what it `happens` (or, with nothing written, that its picture comes alive)."""
    oc = _runner()
    people = people or {}
    seen, out = set(), []
    skip = nod_scenes(call)
    for sid in call.get("scenes") or []:
        if sid in skip:
            continue
        sc = scenes.get(sid) or {}
        got = 0
        for sh in shots_of({**call, "scenes": [sid]}, scenes):
            for b in (sc.get("beats") or []):
                if not isinstance(b, dict) or not str(b.get("do") or "").strip():
                    continue
                if b.get("shot") not in (None, "", sh.get("id")) and b.get("shot") != sh.get("id"):
                    continue
                key = str(b["do"]).strip().lower()
                if key not in seen:
                    seen.add(key)
                    out.append(str(b["do"]).strip().rstrip("."))
                    got += 1
        if not got:
            h = oc.no_speech(oc.no_composition(oc.swap_names(sc.get("happens"), people)))
            if not h and not (sc.get("voice") or "").strip():
                # nothing written to happen: the scene's first picture says what is there, and it comes alive
                ff = next((f for f in sc.get("frames") or [] if f.get("role") in (None, "first")), None) or sc.get("first_frame") or {}
                act = oc.no_composition(oc.swap_names(ff.get("action") or "", people))
                raw_subj = oc.swap_names(ff.get("subject") or "", people)
                subj = oc.no_composition(raw_subj) or raw_subj.strip()
                h = act or (f"everything in the picture moves gently and naturally: {subj}" if subj else "")
            if h and h.lower() not in seen:
                seen.add(h.lower())
                out.append(h)
    return out


def _norm_words(t) -> list:
    return re.findall(r"[a-z0-9']+", str(t or "").lower())


def cued(call: dict, scenes: dict) -> list:
    """THE BEATS ON THEIR WORDS (2026-10-28: a beat must not start before its words).
    Every beat of a talking take names the words it happens over (`over`); each one starts when those words start, never
    before. Times are placed inside each line's own window on the call's clock (`at`..`until`), by where the words sit in
    the line. A beat over no words ("the stop after 70") starts where the line before it ends. Returns
    [{"a", "z", "do", "over", "bracket", "said"}] in order, or [] when a talking beat has no `over` to place it by."""
    lines = [l for l in call.get("lines") or [] if l.get("on_camera")]
    if not lines:
        return []
    out, prev_end = [], 0.0
    for sid in call.get("scenes") or []:
        sc = scenes.get(sid) or {}
        line = next((l for l in lines if l.get("scene") == sid), None)
        for b in sc.get("beats") or []:
            if not isinstance(b, dict) or not str(b.get("do") or "").strip():
                continue
            fx = re.search(r"(?i)\beffect-?\d|composited in the edit", str(b.get("bracket") or ""))
            if fx and _has_subject(str(b["do"])) and not re.match(r"(?i)(her|his|their|she|he|they)\b", str(b["do"]).strip()):
                continue                                 # the effect's own beat is laid on in the edit, never acted in the clip
            over = str(b.get("over") or "").strip()
            if not line:
                return []
            lw = _norm_words(line.get("text"))
            ow = _norm_words(over)
            a0, z0 = float(line.get("at") or 0), float(line.get("until") or 0)
            hit = next((i for i in range(len(lw) - len(ow) + 1) if ow and lw[i:i + len(ow)] == ow), None)
            if hit is not None and lw:
                chars = [len(w) + 1 for w in lw]
                t = a0 + (z0 - a0) * sum(chars[:hit]) / sum(chars)
                prev_end = a0 + (z0 - a0) * sum(chars[:hit + len(ow)]) / sum(chars)
                said = True
            else:                                        # no words of its own ("the stop after 70"): right after the last words
                t, said = prev_end, False
            if out:
                t = max(t, out[-1]["a"])
            out.append({"a": round(t, 1), "do": str(b["do"]).strip().rstrip("."), "over": over,
                        "bracket": "" if fx else str(b.get("bracket") or "").strip(), "said": said})
    if not out:
        return []
    end = float(call.get("duration") or call.get("seconds") or out[-1]["a"] + 1)
    for i, x in enumerate(out):
        x["z"] = out[i + 1]["a"] if i + 1 < len(out) else round(end, 1)
    return out


def windows(actions: list, seconds: float) -> tuple:
    """Whole-second windows that tile 0..seconds with no gaps. Returns (windows, dropped_actions)."""
    total = max(1, int(round(seconds)))
    n_win = max(1, min(len(actions) or 1, int(total // MIN_WINDOW) or 1))
    take = actions[: n_win * MAX_PER_WINDOW]
    dropped = actions[n_win * MAX_PER_WINDOW:]
    per = math.ceil(len(take) / n_win) if take else 0
    groups = [take[i * per:(i + 1) * per] for i in range(n_win)] if per else [[] for _ in range(n_win)]
    groups = [g for g in groups if g] or [[]]
    edges = [round(total * i / len(groups)) for i in range(len(groups) + 1)]
    return [(edges[i], edges[i + 1], g) for i, g in enumerate(groups)], dropped


def _acting():
    spec = importlib.util.spec_from_file_location("vm_acting", HERE / "acting.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SUBJECT = re.compile(r"^(?:the|a|an|her|his|their|its|some|one|two|both|she|he|they)\b", re.I)


def _has_subject(action: str) -> bool:
    """An action that already names its subject ("the brown spot peels up") takes no "the woman" in front of it."""
    return bool(_SUBJECT.match(action.strip()))


def look(shot: dict) -> str:
    """What the face and hands do — from the shot's own `face` and `gestures`. The emotion label is not sent: a strong
    emotion word is what makes Seedance light the eyes or overact (guide FAQ, 'glowing eyes')."""
    oc = _runner()
    bits = [oc._as_text(shot.get("face")), oc._as_text(shot.get("gestures"))]
    return "; ".join(b for b in bits if b)


def oc_text(v) -> str:
    return _runner()._as_text(v)


def own_habits(person: dict, call_id: str) -> str:
    """Two of the person's own gestures (character.md), never the whole list: a stock bank dumped into every clip is what
    made them all move alike. Which two follows the call, so the clips of one ad vary."""
    raw = str((person or {}).get("gestures") or "")
    bits = [b.strip().rstrip(".") for b in re.split(r"(?<=[.;])\s+", raw) if b.strip()]
    if not bits:
        return ""
    k = sum(ord(ch) for ch in str(call_id)) % len(bits)
    return "; ".join([bits[k]] + ([bits[(k + 1) % len(bits)]] if len(bits) > 1 else []))


# A SUNG PERFORMANCE has its own movement bar (the owner, 2026-10-29: the song-ad singer "stiffly delivering the lyrics"): the
# singer performs with the whole body, to the beat and the phrasing.
SUNG = ("The singer performs with the whole body, unhurried and continuous: the head, shoulders and hands move with the "
        "beat and the phrasing, the eyes hold the lens and drift off it between lines, the face carries the feeling of "
        "each lyric, the mouth shapes every sung word, no frozen pose and no held stare.")
# PROPS MAKE PHYSICAL SENSE (2026-10-28): stated in every clip
PHYSICAL = ("Every lid comes off before anything is taken out; every ingredient goes somewhere you can see and stays "
            "the same thing and texture; each action lands on the object the timeline names, and that object stays the "
            "same object.")
# THE MOVEMENT BAR (2026-10-28): the hands keep working and the eyes move, said in every clip with a person
MOTION = ("The person's hands keep doing the real task the whole time, unhurried and continuous: each action flows into "
          "the next with no frozen hold; their eyes go down to their hands while they work and come back up to the lens "
          "between actions; their head tilts and nods with their words; the material visibly moves (it falls, pours, "
          "spreads).")


def build(call: dict, scenes: dict, people: dict, words: dict, style: str, lead: str | None = None) -> dict:
    """A last frame is named only for a silent clip whose end picture is a different picture from its start."""
    oc = _runner()
    W = words or {}
    lines_ = call.get("lines") or []
    talking = bool(call.get("talking"))
    who_id = next((l["speaker"] for l in lines_ if l.get("on_camera")), None) or lead
    who = oc.desc(who_id, people) if who_id in people else "the person in the picture"
    Who = who[:1].upper() + who[1:]
    sc_ids = call.get("scenes") or []
    sc0 = scenes.get(sc_ids[0] if sc_ids else None) or {}
    shots = shots_of(call, scenes) or [oc.shot_of(sc0)]
    seconds = float(call.get("duration") or call.get("seconds") or 5)
    layers = call.get("spice_layers")
    shots, acting_notes = _acting().fill(shots, people.get(who_id), talking, layers)   # V46: what the face and hands visibly do

    kind = oc.camera_move_of(sc0) or call.get("camera") or "still"
    if call.get("camera_held") and kind in ("still", "hold"):   # the swipe's phone measured as held by a hand (scene_breakdown)
        kind = "held"
    kind_still = kind in ("still", "hold")
    camera = CAMERA.get(kind, CAMERA["held"])

    # 1 · the assets, bound by number and job
    assets = [f"Image 1 is the first frame and shows {who}: keep this exact person, face, clothing, props, room and light."]
    has_end = (not talking) and bool(call.get("end_frame")) and call.get("end_frame") != call.get("start_frame")
    if has_end:
        assets.append("Image 2 is the last frame: the clip settles on it, the same person, props, room and light.")
    assets += video_lines(call.get("refs") or [])
    if talking:
        verb = "sings" if call.get("sung") else "speaks"      # a song ad's on-camera singer (2026-10-29)
        assets.append(f"Audio 1 is {who}'s voice: {who} {verb} Audio 1 word for word, lips matching every word.")

    # 2 · one sentence
    st = re.sub(r"\s*Hold this look in every picture\.?", "", oc.style_clean(style) if style else "").strip()
    st = re.sub(r"^The look, exactly:\s*", "", st)
    if kind_still:      # a propped phone is not "handheld": the style and the camera must not argue
        st = re.sub(r"handheld[^,.]*,?\s*", "", st).strip(" ,")
    event = oc.no_speech(oc.no_composition(oc.swap_names(sc0.get("happens"), people))) or "talks to the camera"
    if sc_ids and sc_ids[0] in nod_scenes(call):
        event = "listens"
    subj = "" if _has_subject(event) else f"{Who} "
    summary = (_sentence(st) + " " if st else "") + _sentence(f"{subj}{event}, {camera}")
    # the skin after the routine: the spots are not asked for, the even skin is said (the picture already shows it)
    if oc.scene_even(sc0) and W.get("identity_even"):
        summary += " " + _sentence(oc._fill(W["identity_even"], poss=(people.get(who_id) or {}).get("poss", "their")).strip())

    # 3 · the timeline
    acts = actions_of(call, scenes, people)
    wins, dropped = windows(acts, seconds)
    habits = ""
    if not any(oc._as_text(sh.get("gestures")) for sh in shots) and (layers is None or 2 in layers):
        habits = own_habits(people.get(who_id), call.get("id") or "")
    lines = []
    prev_move = kind
    hand_before = {}                                    # the previous window's last shot hands off to this one
    for i in range(1, len(wins)):
        last = shots[max(0, min(len(shots) - 1, i * len(shots) // len(wins) - 1))]
        h = str(last.get("hands_off") or "").strip().lower()
        if len(shots) > 1 and HAND.get(h):
            hand_before[i] = HAND[h]
    for i, (a, z, group) in enumerate(wins):
        txt = "; then ".join((f"{who} " if j == 0 and not _has_subject(g) else "") + (g if _has_subject(g) and j == 0 else g[:1].lower() + g[1:])
                             for j, g in enumerate(group))
        lo, hi = i * len(shots) // len(wins), max(i * len(shots) // len(wins) + 1, (i + 1) * len(shots) // len(wins))
        mine = shots[lo:hi] or shots[-1:]                                   # each window takes its own shots' acting and move
        sh = mine[0]
        mv = oc.camera_move_of(sh)
        bits = []
        parts, pm = [], prev_move
        for k, x in enumerate(mine):                 # shots that share a window: each one's acting, handed on in order
            xm = oc.camera_move_of(x)
            if k:
                h = HAND.get(str(mine[k - 1].get("hands_off") or "").strip().lower())
                if h:
                    parts.append(h.rstrip("."))
                if xm and xm != pm and CAMERA.get(xm):
                    parts.append(f"Camera: {CAMERA[xm]}")
            pm = xm or pm
            if look(x):
                parts.append(("Then " if k else "") + look(x))
        acting = ". ".join(parts)
        if acting:
            bits.append(f"{Who}'s face and hands: {acting}")
        elif i == 0 and habits:
            bits.append(f"{Who} moves the way {(people.get(who_id) or {}).get('pron', 'they')} always does: {habits}")
        if i and mv and mv != prev_move and CAMERA.get(mv):
            bits.append(f"Camera: {CAMERA[mv]}")
        if i and hand_before.get(i):
            bits.append(hand_before[i].rstrip("."))
        prev_move = mv or prev_move
        if i == 0:
            if talking:
                bits.append(f"{Who} starts {'singing' if call.get('sung') else 'speaking'} Audio 1")
            else:
                nods = [l for l in lines_ if l.get("sound") and l.get("nod")]
                if nods:
                    bits.append(f"{Who} nods slightly, lips closed, without a sound")
        txt = ". ".join(x for x in [txt] + bits if x)
        lines.append(f"{a}-{z}s: {_sentence(txt) or 'Holds the first frame, breathing naturally.'}")
    beats = cued(call, scenes) if talking else []
    if beats:
        # a talking take: the timeline is the brief's beats ON THEIR WORDS, replacing the even windows above
        lines = []
        for i, b in enumerate(beats):
            do = b["do"]
            act = (f"{who} " if not _has_subject(do) else "") + do
            ow = b["over"].rstrip(".").split()
            cue = " ".join(ow[:3]) + ("…" if len(ow) > 3 else "")   # the line is never typed whole: only its first words
            when = f'as {who} starts "{cue}"' if b["said"] else "after the words, in the pause"
            extra = f" ({b['bracket']})" if b["bracket"] and len(b["bracket"]) < 120 else ""
            start = f" {Who} starts {'singing' if call.get('sung') else 'speaking'} Audio 1." if i == 0 else ""
            lines.append(f"{b['a']:.1f}-{b['z']:.1f}s, {when}: {_sentence(act).rstrip('.')}{extra}.{start}")
        seen_look = []
        for x in shots:                                  # the shots' face and hands (the board's fields), once, each on its words
            if look(x) and look(x) not in seen_look:
                seen_look.append(look(x))
        if seen_look:
            lines.append(f"{Who}'s face and hands, each on its own words: " + ". ".join(l.rstrip(".") for l in seen_look) + ".")
        lines.append("Each movement starts on its own words and never before them: until those words are said, the hand "
                     "stays where it is. Between movements the head, face and shoulders keep moving naturally with the speech.")
    last_sh = oc.last_shot(scenes.get(sc_ids[-1] if sc_ids else None))
    end = oc._as_text(last_sh.get("ends_on"))
    part = str((lines_[-1] if lines_ else {}).get("part") or "")
    if not part or part.split("/")[0] == part.split("/")[-1]:             # only the call that ends the scene
        h = str(call.get("hands_off") or last_sh.get("hands_off") or "").strip().lower()
        tail = " ".join(x for x in (END.get(h, ""), f"At the end of the take: {end.rstrip('.')}." if end else "") if x)
        if tail:
            lines[-1] = lines[-1].rstrip(".") + ". " + tail

    # 4 · what stays constant, then the only negatives the model honours
    off = next((l for l in lines_ if not l.get("on_camera") and not l.get("sound")), None)
    listeners = [p for p in (call.get("people") or []) if p != (off["speaker"] if off else who_id)]
    quiet = []
    if any(not l.get("on_camera") for l in lines_) and listeners:
        quiet.append(f"{' and '.join(oc.desc(p, people) for p in listeners).capitalize()} "
                     f"{'listens' if len(listeners) == 1 else 'listen'} in silence, lips closed.")
    if not talking:
        quiet.append("Nobody speaks; mouths stay closed unless an action says otherwise.")
    own_acting = any(oc._as_text(sh.get("gestures")) for sh in shots)
    fams = tuple(f for f in oc.CLIP_FAMILIES if not (f == "camera-hand" and (kind_still or call.get("refs")))
                 and not (f in ("body", "face") and not call.get("people"))
                 and not (f == "body" and own_acting))      # the shot's own gestures replace the stock body rows
    if layers is not None and 4 in layers:
        fams += (oc.SENSE_FAMILY,)
    rows = oc.realism_rows(call.get("realism_format") or oc.REALISM_FORMAT.get(call.get("camera")), fams, call.get("realism"),
                           level=int(call.get("spice_level") or 2))
    real = " ".join(r["prompt"].strip().rstrip(".") + "." for r in rows[:4])
    marks = str((people.get(who_id) or {}).get("marks") or "").strip().rstrip(".")
    keep_marks = (layers is None or 3 in layers) and marks      # layer 3, lived-in marks (VIDEO-SPICE.md): kept as the picture shows them
    hold = (f"Constant throughout: one continuous take, {camera}; the same person, clothing, props, room and light as Image 1."
            + (f" Marks kept exactly as in Image 1: {marks}." if keep_marks else "")
            + (" " + " ".join(quiet) if quiet else "") + (" " + real if real else "")
            + " " + (SUNG if call.get("sung") else PHYSICAL + (" " + MOTION if call.get("people") or talking else ""))
            + " No subtitles. No background music.")
    # THE SWIPE'S ELEMENTS, read to the smallest one (scene_breakdown.py, 2026-10-28): the camera's hand drift, the eyes,
    # each prop's state and lift, where each ingredient goes, what each action lands on, the atmosphere
    elements = str(call.get("swipe_elements") or "").strip()
    prompt = "\n\n".join(x for x in ["\n".join(assets), summary, "\n".join(lines), elements, hold] if x)
    return {"prompt": prompt, "windows": [(a, z) for a, z, _ in wins], "dropped": dropped,
            "words": len(prompt.split()), "acting": acting_notes}
