"""The Kling prompt — the backup clip's words, built from the same scene fields as seedance_prompt.py (2026-10-26).

Kling 4.0 on Higgsfield is the wired BACKUP behind Seedance (components/model-inputs/inputs/kling-4.0.json). It takes the
approved start picture and NO audio, so its clip is always silent: a talking call that falls back to it is made with the
person's mouth closed and the line laid under it as an off-camera read (clips_run.make_backup). The rules it follows are
the rulebook's `structure`: subject, action, camera, style; the picture is the anchor, so only change is described; one
action and one camera move per window; locks and two negatives last.

    build(call, scenes, people, words, style, lead) -> {"prompt", "windows", "dropped", "words"}

Pure: no network, no spend, callable by the preflight. Brand-agnostic. Python 3.9.
"""
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SP = []


def _sp():
    if not _SP:
        sp = importlib.util.spec_from_file_location("kling_prompt_seedance_prompt", HERE / "seedance_prompt.py")
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _SP.append(m)
    return _SP[0]


def build(call, scenes, people, words, style, lead=None):
    S = _sp()
    oc = S._runner()
    talking = bool(call.get("talking"))
    lines_ = call.get("lines") or []
    who_id = next((l["speaker"] for l in lines_ if l.get("on_camera")), None) or lead
    who = oc.desc(who_id, people) if who_id in people else "the person in the picture"
    Who = who[:1].upper() + who[1:]
    sc_ids = call.get("scenes") or []
    sc0 = scenes.get(sc_ids[0] if sc_ids else None) or {}
    shots = S.shots_of(call, scenes) or [oc.shot_of(sc0)]
    seconds = float(call.get("duration") or call.get("seconds") or 5)
    layers = call.get("spice_layers")
    shots, acting_notes = S._acting().fill(shots, people.get(who_id), talking, layers)   # the same face/gestures as Seedance (V46)
    kind = oc.camera_move_of(sc0) or call.get("camera") or "still"
    still = kind in ("still", "hold")
    camera = S.CAMERA.get(kind, S.CAMERA["held"])

    st = re.sub(r"\s*Hold this look in every picture\.?", "", oc.style_clean(style) if style else "").strip()
    st = re.sub(r"^The look, exactly:\s*", "", st)
    if still:
        st = re.sub(r"handheld[^,.]*,?\s*", "", st).strip(" ,")
    event = oc.no_speech(oc.no_composition(oc.swap_names(sc0.get("happens"), people))) or "looks at the camera"
    subj = "" if S._has_subject(event) else Who + " "
    # the anchor: the picture already shows who, where and the light; the words carry only what changes
    head = [S._sentence(st) if st else "", S._sentence(f"{subj}{event}, {camera}")]
    if talking:
        head.append(f"{Who} keeps the mouth closed and does not speak; the line is laid under the clip.")

    acts = S.actions_of(call, scenes, people)
    wins, dropped = S.windows(acts, seconds)
    lines = []
    for i, (a, z, group) in enumerate(wins):
        lo, hi = i * len(shots) // len(wins), max(i * len(shots) // len(wins) + 1, (i + 1) * len(shots) // len(wins))
        look = "; ".join(x for x in (S.look(sh) for sh in shots[lo:hi]) if x)
        txt = "; then ".join((f"{who} " if j == 0 and not S._has_subject(g) else "") + (g if S._has_subject(g) and j == 0 else g[:1].lower() + g[1:])
                             for j, g in enumerate(group))
        if talking:                                           # nobody speaks on this clip: the face does the acting
            txt = re.sub(r"\b(says|speaks|tells|asks|replies|announces)\b[^;.]*", "looks to the lens", txt)
        if not look and i == 0 and (layers is None or 2 in layers) and not any(S.oc_text(sh.get("gestures")) for sh in shots):
            habits = S.own_habits(people.get(who_id), call.get("id") or "")
            look = f"moves the way {(people.get(who_id) or {}).get('pron', 'they')} always does: {habits}" if habits else ""
        bits = [x for x in (txt, f"{Who}'s face and hands: {look}" if look else "") if x]
        lines.append(f"{a}-{z}s: {S._sentence('. '.join(bits)) or 'Holds still, breathing naturally.'}")
    end = oc._as_text(oc.last_shot(scenes.get(sc_ids[-1] if sc_ids else None)).get("ends_on"))
    if end:
        lines[-1] = lines[-1].rstrip(".") + f". It ends on: {end.rstrip('.')}."
    marks = str((people.get(who_id) or {}).get("marks") or "").strip().rstrip(".")
    keep_marks = (layers is None or 3 in layers) and marks
    lock = (f"Camera: {camera}. One continuous take. Same person, clothing, props, room and light as the picture."
            + (f" Marks kept exactly as in the picture: {marks}." if keep_marks else "")
            + " No subtitles. No on-screen text.")
    prompt = "\n\n".join(x for x in (" ".join(h for h in head if h), "\n".join(lines), lock) if x)
    return {"prompt": prompt, "windows": [(a, z) for a, z, _ in wins], "dropped": dropped, "words": len(prompt.split()),
            "acting": acting_notes}
