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
            out.append(_movement().line(r, i))
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


def no_overlays(text: str) -> str:
    """Overlays are the edit's layer: a clip's words never name one, or the model draws it (2026-10-31)."""
    word = r"(?:cartoon|graphic|cross-section|overlay)"
    text = re.sub(r"\s*(?:toward|to|at|beside|behind)\s+(?:the|a)\s+(?:[\w-]+\s+){0,3}" + word + r"(?:\s+and back to the lens)?", "", text, flags=re.I)
    text = re.sub(r"[^.;\n]*\b" + word + r"\b[^.;\n]*[.;]\s?", " ", text, flags=re.I)
    return re.sub(r" {2,}", " ", text)


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


# A SUNG PERFORMANCE has its own movement bar (owner, 2026-10-29: the song-ad singer "stiffly delivering the lyrics"): the
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
    if hb_modes(call):                                  # the switch (off unless the call names an hb mode): its own builder
        return build_hb(call, scenes, people, words, style, lead)
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
    assets += [f"Image {2 + i} is a reference for {r['job']}." for i, r in enumerate(call.get("image_refs") or [])]
    assets += call.get("ref_notes") or []
    assets += video_lines(call.get("refs") or [])
    if talking:
        verb = "sings" if call.get("sung") else "speaks"      # a song ad's on-camera singer (2026-10-29)
        assets.append(f"Audio 1 is {who}'s voice: {who} {verb} Audio 1 word for word, lips matching every word, and says nothing else: when Audio 1 goes silent the lips stay closed.")

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
    prompt = no_overlays(prompt)
    return {"prompt": prompt, "windows": [(a, z) for a, z, _ in wins], "dropped": dropped,
            "words": len(prompt.split()), "acting": acting_notes}


# ====================================================================================================================
# THE TWO HB CLIP MODES (2026-11-07) — behind a switch that is OFF unless `call["clip_mode"]` names one.
#
#   hb-multishot : ONE call of 8 to 15 s carries 2 to 4 shots joined by hard cuts, all in one place.
#   hb-voice     : the video model speaks the lines; one voice sample per person who speaks on screen.
#   "hb-multishot+hb-voice" (or a list of both) is allowed: the interview shape, cuts and two voices in one call.
#   Neither mode regenerates a filmed shot (hb_filmed), and a multi-cut call never joins shots set in two places (hb_place).
#
# The narrator read stays the default. With no mode named, `build` never reaches this code and its output is
# byte-for-byte what it was (test_seedance_prompt.HbSwitchOff). The rules below are ours, written for Seedance 2.5's
# own prompt guide (whole-second windows, one visible change each, assets bound by number and job); the idea of
# cutting inside one call and of tagging a voice per speaker came from a study of a short-drama maker, and none of its
# wording is used here.
# ====================================================================================================================
HB_MULTISHOT = "hb-multishot"
HB_VOICE = "hb-voice"
HB_MODES = (HB_MULTISHOT, HB_VOICE)
HB_CLIP_SECONDS = (8, 15)          # a multi-shot call: no shorter than 8 s, no longer than 15 s
HB_SHOTS = (2, 4)                  # cuts + 1: two to four shots in one call
HB_MIN_SHOT = 2                    # whole seconds a shot needs between its two cuts
HB_VOICE_SAMPLE_SECONDS = (2, 15)  # a voice sample's length (components/model-inputs/inputs/seedance-2.5.json audio_clip_seconds)
HB_MAX_VOICES = 5                  # the stable range for voice-bound people in one call (same file, stable_audio_video_subjects)
HB_LINE_WPS = 2.5                  # spoken words a second, for a line with no recorded time
HB_READ_WPS = 3.0                  # read-aloud words a second, to share a scene's read among its shots
HB_PAUSE = 0.3                     # air after a line
HB_NO_HOLD = ("hold", "holds", "holds still", "holds the frame")
HB_SMALL_WORDS = {"the", "a", "an", "to", "her", "his", "their", "its", "of", "at", "on", "in"}   # left out when a gesture is matched to the action


def hb_modes(call) -> tuple:
    """The hb modes a call names, in a fixed order; () when it names none (the switch is off)."""
    raw = (call or {}).get("clip_mode")
    if not raw:
        return ()
    toks = [raw] if isinstance(raw, str) else list(raw)
    named = {p.strip().lower() for t in toks for p in str(t).split("+")}
    return tuple(m for m in HB_MODES if m in named)


def _line_seconds(l: dict) -> float:
    """How long a line takes: its recorded window when it has one, else its words at a speaking pace."""
    try:
        if l.get("at") is not None and l.get("until") is not None and float(l["until"]) > float(l["at"]):
            return round(float(l["until"]) - float(l["at"]), 2)
    except (TypeError, ValueError):
        pass
    n = len(_norm_words(l.get("text") or l.get("say")))
    return round(max(1.0, n / HB_LINE_WPS + HB_PAUSE), 2)


def _spoken(call: dict, shots: list) -> list:
    """Per shot, its lines: [{"speaker", "text", "on_camera", "seconds", "says"}]. A shot's own `lines[]` are matched by
    their words to the call's lines (which know the speaker and whether it is said on camera); a call line that names
    a `shot` is that shot's when the shot carries none of its own."""
    oc = _runner()
    rows = list(call.get("lines") or [])
    out = []
    for sh in shots:
        got = []
        for l in sh.get("lines") or []:
            text = oc.without_tags(l.get("say") or l.get("text") or "")
            if not text:
                continue
            w = oc._norm(text)
            m = next((c for c in rows if oc._norm(c.get("text")) == w), None) \
                or next((c for c in rows if w and w in oc._norm(c.get("text"))), None)
            got.append({"speaker": (m or {}).get("speaker") or sh.get("speaker"), "text": text,
                        "on_camera": bool(m["on_camera"]) if m else bool(sh.get("on_camera")),
                        "seconds": _line_seconds({**(m or {}), "text": text})})
        if not got:
            for c in rows:
                if c.get("shot") and c.get("shot") == sh.get("id") and oc.without_tags(c.get("text")):
                    got.append({"speaker": c.get("speaker"), "text": oc.without_tags(c.get("text")),
                                "on_camera": bool(c.get("on_camera")), "seconds": _line_seconds(c)})
        for r in got:
            r["says"] = bool(r["on_camera"] and r["speaker"])
        out.append(got)
    return out


def _shot_secs(call: dict, scenes: dict, shots: list, spoken: list) -> list:
    """Seconds each shot wants: its own `length`; else the time of the lines said on camera in it; else its share of the
    scene's read (a montage shot has no words of its own, the narrator's read runs across it)."""
    out = []
    for i, sh in enumerate(shots):
        try:
            ln = float(sh.get("length") or 0)
        except (TypeError, ValueError):
            ln = 0.0
        said = [r["seconds"] for r in spoken[i] if r["on_camera"]]
        out.append(ln if ln > 0 else (sum(said) + HB_PAUSE if said else None))
    rest = [i for i, v in enumerate(out) if v is None]
    if rest:
        try:
            read = float(call.get("read_seconds") or 0)
        except (TypeError, ValueError):
            read = 0.0
        if not read:
            n_words = sum(len(_norm_words((scenes.get(s) or {}).get("voice"))) for s in call.get("scenes") or [])
            read = n_words / HB_READ_WPS
        left = max(0.0, read - sum(v for v in out if v))
        share = max(float(HB_MIN_SHOT), left / len(rest)) if read else float(HB_MIN_SHOT)
        for i in rest:
            out[i] = share
    return out


def _place_of(scene: dict) -> str:
    return str((scene or {}).get("setting_id") or (scene or {}).get("setting") or "").strip()


# FILMED SHOTS AND ONE PLACE PER SHOT (fix round, 2026-11-07). A shot cut from footage we own (as filmed, CUT [SLOT…],
# a real interview answer) is never regenerated by either hb mode: it is cut from its take in the edit. A multi-cut
# call joins only shots set in the same place, read per shot, not per scene: a scene whose shots each sit somewhere
# else (an owned montage, four couples in four homes) is never one call.
HB_FILMED_TEXT = re.compile(r"\bas filmed\b|\bcut the actual\b|\bkeep (?:the )?original (?:recorded )?audio\b|"
                            r"\bno reanimation\b|\brecorded face only\b", re.I)
HB_FILMED_CUT = re.compile(r"^\s*CUT\b|\bCUT \[SLOT")      # the brief's own marker, in capitals
HB_EACH_PLACE = re.compile(r"\bseparate\b[^.;]*\b(?:location|place)s?\b|\beach (?:listed )?shot\b|"
                           r"\bdifferent (?:locations|places)\b|\bmontage\b", re.I)     # a montage is cut across places
HB_PLACE_WORDS = ("street", "sidewalk", "car", "kitchen", "bathroom", "shower", "bedroom", "living room", "office",
                  "gym", "beach", "park", "patio", "restaurant", "cafe", "lunch table", "dinner table", "store",
                  "barbershop", "salon", "garage", "garden", "yard", "balcony", "hallway", "elevator", "studio", "pool")


def hb_filmed(shot: dict) -> str:
    """Why a shot (as `shots_in` returns it: the scene's fields under the shot's own) is filmed, or "" when it is made.
    The shot's own `operation` wins: CUT is filmed, GENERATE is made."""
    sh = shot or {}
    op = str(sh.get("operation") or "").strip().upper()
    if op == "CUT":
        return "operation CUT: cut from an owned take"
    if op in ("GENERATE", "MAKE"):
        return ""
    if sh.get("owned_asset") or str(sh.get("source_plan") or "").lower() == "cut":
        return "cut from an owned take"
    ff = sh.get("first_frame") if isinstance(sh.get("first_frame"), dict) else {}
    for key, text in (("start_picture", sh.get("start_picture")), ("picture", sh.get("picture")),
                      ("first_frame subject", ff.get("subject"))):
        if HB_FILMED_CUT.search(str(text or "")):
            return f"{key} says CUT"
    for key, text in (("speaker", sh.get("speaker")), ("happens", sh.get("happens")), ("face", sh.get("face")),
                      ("first_frame style", ff.get("style"))):
        m = HB_FILMED_TEXT.search(str(text or ""))
        if m:
            return f'{key} says "{m.group(0)}"'
    return ""


def _places_named(text) -> set:
    t = str(text or "").lower()
    return {w for w in HB_PLACE_WORDS if re.search(rf"\b{re.escape(w)}s?\b", t)}


def hb_place(shot: dict) -> str:
    """Where a shot is set. The scene's place, unless the scene says each shot has its own place, or the shot's own
    start picture names a place the scene's place does not."""
    sh = shot or {}
    ff = sh.get("first_frame") if isinstance(sh.get("first_frame"), dict) else {}
    base = _place_of(sh)
    where = f"{base} {ff.get('location') or ''}"
    own = f"shot {sh.get('id')}'s own place ({base or 'no place named'})"     # a montage: each shot is somewhere else
    if HB_EACH_PLACE.search(where):
        return own
    sp = str(sh.get("start_picture") or "")
    if sp and sp != "first_frame" and not sp.startswith("from S"):
        new = _places_named(sp) - _places_named(where)
        if new:
            return f"{base or 'place'} · {', '.join(sorted(new))}"
    return base


def _hb_shots_of(call: dict, scenes: dict) -> list:
    """The shots a call shows; `shot_ids` narrows them to the group the planner gave this call."""
    shots = shots_of(call, scenes)
    ids = call.get("shot_ids")
    return [s for s in shots if s.get("id") in ids] if ids else shots


def hb_shots(call: dict, scenes: dict) -> list:
    """What the planner groups: [{"id", "seconds", "setting", "speakers", "filmed"}] for every shot the call shows, in
    order. `setting` is the shot's own place (hb_place); `filmed` is why the shot is cut from owned footage, or ""."""
    shots = []
    for sid in call.get("scenes") or []:
        shots += shots_of({**call, "scenes": [sid]}, scenes)
    spoken = _spoken(call, shots)
    secs = _shot_secs(call, scenes, shots, spoken)
    return [{"id": sh.get("id"), "seconds": round(secs[i], 2), "setting": hb_place(sh),
             "speakers": sorted({r["speaker"] for r in spoken[i] if r["says"]}), "filmed": hb_filmed(sh)}
            for i, sh in enumerate(shots)]


def _fit(secs: list, total: int, floor: int) -> list:
    """Whole seconds per segment that sum to `total`, none under `floor`, shared in proportion to what each wants."""
    n = len(secs)
    left = total - floor * n
    extra = [max(0.0, s - floor) for s in secs]
    sx = sum(extra)
    shares = [left * e / sx for e in extra] if sx > 0 else [left / n] * n
    ints = [int(x) for x in shares]
    for i in sorted(range(n), key=lambda i: (-(shares[i] - ints[i]), i))[:left - sum(ints)]:
        ints[i] += 1
    return [floor + x for x in ints]


def _clamp(v, lo, hi) -> int:
    return int(max(lo, min(hi, v)))


def _who_phrase(ids: list, people: dict) -> str:
    oc = _runner()
    names = list(dict.fromkeys(oc.desc(i, people) for i in ids if i))
    if not names:
        return "the people in the picture"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _cast_ids(call: dict, scene_rows: list, people: dict) -> list:
    ids = [p for p in (call.get("people") or []) if p]
    if not ids:
        for s in scene_rows:
            for part in re.split(r"\s*(?:,|\band\b|·)\s*", str(s.get("who") or "")):
                if part.strip() in people and part.strip() not in ids:
                    ids.append(part.strip())
    return ids


def _hb_refusal(modes: tuple, missing: list, **extra) -> dict:
    return {"prompt": "", "windows": [], "dropped": [], "words": 0, "acting": [], "clip_mode": "+".join(modes),
            "duration": None, "cuts": [], "voices": [], "missing": missing, "skipped_lines": [], "filmed": [], **extra}


def build_hb(call: dict, scenes: dict, people: dict, words: dict, style: str, lead=None) -> dict:
    """The clip prompt for an hb mode. Same return shape as `build`, plus `clip_mode`, `duration`, `cuts`, `voices`,
    `missing` (a refusal by name: the prompt is empty then), `skipped_lines`, and `filmed` (the shots left out because
    they are cut from owned footage, each with why).

    THE RULES (ours):
      * a filmed shot (hb_filmed: as filmed, CUT [SLOT…], a real interview answer) is never regenerated: it is left out
        of the call and named in `filmed`; a call of filmed shots only is refused.
      * one place per call is read per shot (hb_place), not only per scene.
      * hb-multishot: 2 to 4 shots, 8 to 15 s, one place; each shot window is whole seconds and at least 2 s;
        the first window sets the place and who stands where; each later window opens "Cut to" (or "Cut back to"
        for a framing already used) and restates the framing and who is in it; one camera state and one visible
        action per window; every emotion is the face and hands doing something; the last window lands on the
        scene's result. Hard cuts only: no dissolve, fade, wipe or zoom between shots.
      * a window acts its shot's first beat and, when the shot has more, the beat the shot lands on (its payoff, e.g. a
        recoil); beats between them are named in `dropped`. The shot's gestures ride with it as its body's moves,
        as the narrator path carries them in "face and hands"; a gesture the action already says is not repeated
        (round 3, 2026-11-07: the payoff and the body's moves are what the narrator path already sends).
      * hb-voice: a line is typed in the window where it is said, with the person's name and "in Audio N's voice";
        the sample sets timbre only. A person who speaks needs a sample of 2 to 15 s; at most 5 voices. A line said
        off camera (the narrator's) is never typed: the narrator's read stays on the edit's track.
      * a motion-reference video is not sent in these modes (one reference carries one camera; the cuts carry several).
    """
    oc = _runner()
    modes = hb_modes(call)
    multi, voice = HB_MULTISHOT in modes, HB_VOICE in modes
    sc_ids = call.get("scenes") or []
    scene_rows = [scenes.get(s) or {} for s in sc_ids]
    sc0 = scene_rows[0] if scene_rows else {}
    shots = _hb_shots_of(call, scenes) or [oc.shot_of(sc0)]
    filmed = [{"shot": sh.get("id"), "why": hb_filmed(sh)} for sh in shots if hb_filmed(sh)]
    if filmed:                                           # filmed takes are cut in the edit, never regenerated
        shots = [sh for sh in shots if not hb_filmed(sh)]
        if not shots:
            return _hb_refusal(modes, ["every shot in this call is filmed (" + "; ".join(
                f"{f['shot']}: {f['why']}" for f in filmed) + "): it is cut from its take, never regenerated"],
                filmed=filmed)
    spoken = _spoken(call, shots)
    cast = _cast_ids(call, scene_rows, people)
    missing, skipped = [], []

    if multi:
        shot_places = list(dict.fromkeys(hb_place(sh) for sh in shots))
        if len({_place_of(s) for s in scene_rows}) > 1:
            missing.append("hb-multishot keeps one place per call: this call's scenes are in different places")
        elif len(shot_places) > 1:
            missing.append("hb-multishot keeps one place per call: this call's shots are in different places ("
                           + " / ".join(shot_places) + ")")
        if not HB_SHOTS[0] <= len(shots) <= HB_SHOTS[1]:
            missing.append(f"hb-multishot carries {HB_SHOTS[0]} to {HB_SHOTS[1]} shots in a call: this call has {len(shots)}")

    voices = []                                          # [{"person", "audio", "file", "seconds"}] in order of first speech
    if voice:
        samples = call.get("voice_samples") or {}
        for rows in spoken:
            for r in rows:
                if not r["says"]:
                    skipped.append({"speaker": r["speaker"], "text": r["text"],
                                    "why": "said off camera: stays on the edit's track" if not r["on_camera"] else "no speaker named"})
                    continue
                if r["speaker"] in [v["person"] for v in voices]:
                    continue
                smp = samples.get(r["speaker"])
                f = smp if isinstance(smp, str) else (smp or {}).get("file")
                sec = None if isinstance(smp, str) else (smp or {}).get("seconds")
                if not f:
                    missing.append(f"hb-voice needs a voice sample for {r['speaker']}, who speaks on screen")
                elif sec is not None and not HB_VOICE_SAMPLE_SECONDS[0] <= float(sec) <= HB_VOICE_SAMPLE_SECONDS[1]:
                    missing.append(f"the voice sample for {r['speaker']} runs {sec} s: it must run "
                                   f"{HB_VOICE_SAMPLE_SECONDS[0]} to {HB_VOICE_SAMPLE_SECONDS[1]} s")
                voices.append({"person": r["speaker"], "audio": len(voices) + 1, "file": f, "seconds": sec})
        if len(voices) > HB_MAX_VOICES:
            missing.append(f"hb-voice holds {HB_MAX_VOICES} voices at most in one call: this call has {len(voices)}")
        if not voices:
            missing.append("hb-voice needs at least one line said on camera by a named person")
    audio_of = {v["person"]: v["audio"] for v in voices}

    # the segments: a shot each (multishot), or a line each (one continuous take)
    if multi:
        secs = _shot_secs(call, scenes, shots, spoken)
        try:
            want = round(float(call.get("duration") or 0))
        except (TypeError, ValueError):
            want = 0
        total = _clamp(want or round(sum(secs)), *HB_CLIP_SECONDS)
        total = max(total, HB_MIN_SHOT * len(shots))
        lens = _fit(secs, total, HB_MIN_SHOT) if len(shots) <= HB_SHOTS[1] else []
        segs = [{"shot": sh, "i": i, "lines": [r for r in spoken[i] if r["says"]] if voice else [],
                 "who": [r for r in spoken[i] if r["says"]]} for i, sh in enumerate(shots)]
    else:
        flat = [(i, r) for i, rows in enumerate(spoken) for r in rows if r["says"]]
        try:
            want = round(float(call.get("duration") or 0))
        except (TypeError, ValueError):
            want = 0
        need = sum(r["seconds"] for _, r in flat)
        total = _clamp(want or math.ceil(need * 1.15 + 0.6), 4, HB_CLIP_SECONDS[1])
        if HB_MIN_SHOT * len(flat) > HB_CLIP_SECONDS[1]:
            missing.append(f"{len(flat)} spoken lines do not fit one call of {HB_CLIP_SECONDS[1]} s: split the scene")
        total = max(total, HB_MIN_SHOT * len(flat))
        lens = _fit([r["seconds"] for _, r in flat], total, HB_MIN_SHOT) if flat and not missing else []
        segs = [{"shot": shots[i], "i": i, "lines": [r], "who": [r]} for i, r in flat]
    if missing:
        return _hb_refusal(modes, missing, voices=voices, skipped_lines=skipped, filmed=filmed)

    edges = [0]
    for n in lens:
        edges.append(edges[-1] + n)
    ff = sc0.get("first_frame") or (sc0.get("frames") or [{}])[0] or {}
    place = oc.swap_names(oc._as_text(ff.get("location")), people) or _place_of(sc0)
    sp0 = str(shots[0].get("start_picture") or "")
    if sp0 and sp0 != "first_frame" and not sp0.startswith("from S"):
        # the call opens on a later shot of the scene (the planner's second group): its own picture, not the scene's
        ff = {**ff, "subject": sp0}
        place = _place_of(sc0) or place
    cast_phrase = _who_phrase(cast or [v["person"] for v in voices], people)

    # 1 · the assets, bound by number and job
    assets = [f"Image 1 is the first frame and shows {cast_phrase}: keep these exact people, clothing, props, place and light."]
    n_img = 1
    for sp in call.get("shot_pictures") or []:
        n_img += 1
        assets.append(f"Image {n_img} is the opening picture of shot {sp['shot']}: {sp['job']}.")
    for r in call.get("image_refs") or []:
        n_img += 1
        assets.append(f"Image {n_img} is a reference for {r['job']}.")
    assets += call.get("ref_notes") or []
    for v in voices:
        who = oc.desc(v["person"], people)
        assets.append(f"Audio {v['audio']} is {who}'s voice sample: it sets how {who} sounds and nothing else; "
                      f"{who} says the lines written below, in that voice.")

    # 2 · one sentence
    st = re.sub(r"\s*Hold this look in every picture\.?", "", oc.style_clean(style) if style else "").strip()
    st = re.sub(r"^The look, exactly:\s*", "", st)
    core = (f"One clip of {len(segs)} shots joined by hard cuts, in {place}" if multi
            else f"One continuous take in {place}") if place else \
        (f"One clip of {len(segs)} shots joined by hard cuts" if multi else "One continuous take")
    summary = (_sentence(st) + " " if st else "") + _sentence(core)

    # 3 · the timeline
    lines, seen_frames, cuts, dropped = [], [], [], []
    prev_mv = None
    for k, seg in enumerate(segs):
        a, z = edges[k], edges[k + 1]
        sh = seg["shot"]
        said = seg["lines"]
        speakers = seg["who"]
        nobody = oc._as_text(sh.get("face")).lower().startswith("n/a")      # a product or place shot: no person in it
        actor_id = (speakers[0]["speaker"] if speakers else None) or (cast[0] if cast else None)
        actor = oc.desc(actor_id, people) if actor_id in people else "the person"
        beats = [b for b in sh.get("beats") or [] if isinstance(b, dict) and b.get("shot") == sh.get("id")
                 and str(b.get("do") or "").strip().lower().rstrip(".") not in HB_NO_HOLD]
        gest = sh.get("gestures")
        gest = [str(g).strip() for g in (gest if isinstance(gest, (list, tuple)) else [gest]) if g and not str(g).lower().startswith("n/a")]
        body = []
        if beats:                                       # the first beat, then the beat the shot lands on; the ones between are named
            do = str(beats[0]["do"]).strip().rstrip(".")
            if len(beats) > 1:
                do += ", then " + str(beats[-1]["do"]).strip().rstrip(".")
            dropped += [str(b["do"]).strip() for b in beats[1:-1]]
            body = gest
        else:
            do = gest[0].rstrip(".") if gest else ""
            body = gest[1:]
        do = oc.swap_names(do, people)
        action = (do if _has_subject(do) else f"{'the product' if nobody else actor} {do}") if do else ""
        said_words = set(_norm_words(action))
        body = [oc.swap_names(g.rstrip("."), people) for g in body]
        body = [g for g in body if not (set(_norm_words(g)) - HB_SMALL_WORDS) <= said_words]
        parts = []
        if multi:
            frame = oc._as_text(sh.get("angle")) or "same framing"
            mv = oc.camera_move_of(sh)
            cam = CAMERA.get(mv) if (mv and mv != prev_mv) or (mv and k == 0) else ""
            prev_mv = mv or prev_mv
            if k == 0:
                head = f"Opening shot, {frame}" + (f", {cam}" if cam else "")
                subj = oc.swap_names(oc._as_text(ff.get("subject")), people) or cast_phrase
                parts.append(subj)
            else:
                back = frame in seen_frames and frame != seen_frames[-1]      # the same framing straight away is a jump cut, not a return
                head = f"{'Cut back to' if back else 'Cut to'} {frame}" + (f", {cam}" if cam else "")
                cuts.append(a)
                ids = [r["speaker"] for r in speakers] or ([] if nobody else cast)
                if ids:
                    parts.append(f"{_who_phrase(ids, people)} in frame")
            seen_frames.append(frame)
        else:
            head = ""
            if k == 0:
                parts.append(oc.swap_names(oc._as_text(ff.get("subject")), people) or cast_phrase)
        if action:
            parts.append(action)
        for r in said:
            parts.append(f'{oc.desc(r["speaker"], people)} says "{r["text"]}" in Audio {audio_of[r["speaker"]]}\'s voice, '
                         "lips matching every word")
        if body:
            parts.append("body: " + ", ".join(body))
        face = oc._as_text(sh.get("face"))
        if face and not nobody:
            parts.append(f"face: {oc.swap_names(face, people)}")
        body = "; ".join(p for p in parts if p)
        txt = f"{head}: {body}" if head and body else (head or body)
        lines.append(f"{a}-{z}s: {_sentence(txt) or 'Holds the frame, breathing naturally.'}")
    end = oc._as_text(oc.last_shot(sc0 if len(sc_ids) < 2 else scenes.get(sc_ids[-1])).get("ends_on"))
    end = oc.swap_names(end, people) if end else end    # the cast by their nouns, as in every other line of the call
    if end:
        lines[-1] = lines[-1].rstrip(".") + f". At the end of the clip: {end.rstrip('.')}."

    # 4 · what stays constant, then the only negatives the model honours
    hold = ["Constant throughout:"]
    if multi:
        at = ", ".join(f"{c}s" for c in cuts)
        hold.append(f"{len(segs)} shots, hard cuts at {at}, no dissolves, fades, wipes or zooms between them; "
                    "the same people, clothing, props, place and light in every shot; one camera state inside each shot.")
    else:
        hold.append("one continuous take; the same people, clothing, props, place and light throughout.")
    if voice:
        hold.append("Each person speaks only their own lines, in the voice of their own sample, lips matching every word; "
                    "when nobody is speaking every mouth stays closed.")
    else:
        hold.append("Nobody speaks; mouths stay closed unless an action says otherwise.")
    hold.append("No subtitles, no captions, no on-screen text. No background music.")
    prompt = no_overlays("\n\n".join(x for x in ["\n".join(assets), summary, "\n".join(lines), " ".join(hold)] if x))
    return {"prompt": prompt, "windows": [(edges[i], edges[i + 1]) for i in range(len(segs))], "dropped": dropped,
            "words": len(prompt.split()), "acting": [], "clip_mode": "+".join(modes), "duration": total, "cuts": cuts,
            "voices": voices, "missing": [], "skipped_lines": skipped, "filmed": filmed}
