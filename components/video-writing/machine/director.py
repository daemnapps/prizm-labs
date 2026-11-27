"""Stage 5d — the director at the storyboard step: one strong visual idea per scene, chosen by the machine.

Sits after the stage-5 brief (`stages/5-brief.md`) and before Video Studio production (which seeds from that
brief). Stage 5 stages each scene from the swipe's own shot, so scenes come out as literal re-enactments. This
station hands every scene to the Writers' Room director (its prompt and ladder, reused as they are, with a
storyboard reply format appended), which pitches several ideas per scene; a producer pass scores every pitch on
the room's own axes plus the run's creative-controls target, and this code keeps ONE per scene by score and by
hard checks. No person picks.

The kept idea is written into the scene as the data production already reads: `happens` (the staging line),
every beat's `who` / `action` / `prop` / `where` (and `do`), and the opening picture's `action`. The text it
replaces stays beside it (`happens_swipe`, `do_swipe`, `action_swipe`). Pitches, scores and the reason for each
pick land in `<run>/director/`.

    python3 components/video-writing/machine/director.py <teardown run folder | label> [--scenes S1,S3]
        [--per-scene 3] [--batch 6] [--dry] [--fresh]

`--dry` writes the prompts and stops: no call, no change to the brief. A rerun reuses every reply already on file
for the same prompt (so a failed batch is the only one asked again); `--fresh` asks every call again.
Spends writing-model calls only; never makes a picture or a clip."""
import argparse
import json
import re
import sys
import time
import concurrent.futures as cf
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent / "prompts" / "stage-5d-director"
STATION = "5d director v2"

# THE VISUALS ARE OURS (owner ruling, 2026-11-20): once the script is written the swipe's job is done. Every scene's
# setting, staging, action, camera (angle, distance, move) and motion are pitched fresh from our script, our idea and
# the dial target; the swipe's version stays beside each field only as a *_swipe record. A hold needs its reason.
# Switch: visuals_ours.json lane `director` (false = v1: the swipe's shot as backbone, no camera), or
# VISUALS_OURS_OFF=director on one machine.
# The moves production takes (video-production clips_run.camera_move_of, read there as CAMERA_MOVES).
CAMERA_MOVES = ("push-in", "pan", "tilt", "arc", "handheld", "hold")
MOVE_ALIASES = {"push": "push-in", "pushin": "push-in", "push-in-slow": "push-in", "dolly-in": "push-in",
                "hand-held": "handheld", "still": "hold", "static": "hold", "locked": "hold", "locked-off": "hold"}

# which sections must keep the problem on screen, and which must show the product clearly
BEFORE_PAYOFF = {"hook", "problem", "agitation", "failed-solutions", "proof", "story", "unique-mechanism",
                 "identification", "root-cause",
                 "mechanism", "solution", "product"}
PRODUCT_BEATS = {"solution", "product", "unique-mechanism", "mechanism", "offer", "transformation",
                 "call-to-action", "demo", "results", "objections"}
NOT_STAGED = {"card", "endcard", "screen"}
RUNGS = "L2 Remix, L3 Transplant, L5 Auteur — applied to one scene at a time (L1, the swipe's own shot, is never " \
        "pitched; L4's plot is the brief's own story, which stays)"
HARD_RULES = ("compliance, the right product, no captions or burned-in words, facts and research verbatim, "
              "the brand's own rules (VIDEO-RULINGS V57)")
SCORE_KEYS = ("stops", "made", "doctrine", "controls", "camera")   # camera: v2 producer; a v1 reply has none
DIRECTED = '"happens_swipe"'                 # a brief this station already wrote


# ---------- the workspace and its parts ----------

def workspace():
    """The workspace root through run-kit's paths.repo() (AI_WORKSPACE wins)."""
    rk = HERE.parents[1] / "run-kit"
    if str(rk) not in sys.path:
        sys.path.insert(0, str(rk))
    from run_kit import paths
    return paths.repo(HERE)


def camera_on():
    """The visuals are ours at 5d (owner ruling, 2026-11-20): fresh pictures and camera, the swipe kept as a record."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import visuals
    return visuals.ours("director")


def mode():
    """"swipe-base" (the swipe's shot and motion pattern are the base, ours on top — the owner's last word,
    2026-11-20), "ours" (staged fresh, the swipe as understanding only) or "v1" (the camera switch off)."""
    if not camera_on():
        return "v1"
    import visuals
    return "swipe-base" if visuals.director_base() == "swipe" else "ours"


# which version of each mode-dependent prompt a mode reads; every other prompt is v1
MODE_PROMPTS = {"v1": {}, "ours": {"storyboard-ask": 2, "pick": 2, "rulings": 2},
                "swipe-base": {"storyboard-ask": 3, "pick": 3, "rulings": 3}}


def prompt(name):
    """The prompt this mode reads (MODE_PROMPTS; v1 otherwise)."""
    v = MODE_PROMPTS[mode()].get(name, 1)
    if name == "storyboard-ask" and mode() == "swipe-base":      # AI-1: the Intent paragraph (v4); off keeps v3
        import importlib.util as _u                      # by path: this file may itself be loaded by path
        _s = _u.spec_from_file_location("vw_acting_intent", HERE / "acting_intent.py")
        AI = _u.module_from_spec(_s)
        _s.loader.exec_module(AI)
        v = AI.STORYBOARD_ASK if AI.on() else v
    return (PROMPTS / f"{name}-v{v}-owner.md").read_text()


def move_of(text):
    """A camera move as production takes it, or None."""
    m = str(text or "").strip().lower().replace(" ", "-").replace("_", "-")
    m = MOVE_ALIASES.get(m, m)
    return m if m in CAMERA_MOVES else None


def swipe_camera(sh):
    return (sh.get("angle_swipe") or sh.get("angle") or "", sh.get("camera_move_swipe") or sh.get("camera_move") or "")


def camera_fails(sc, pitch):
    """What is wrong with a pitch's camera: every shot that carries a camera today gets its own angle and a move
    production takes, a hold says why, and the shots are not all the swipe's camera copied."""
    if not camera_on():
        return []
    base = mode() == "swipe-base"     # the swipe's camera is the base: keeping it is right, a hold needs no reason
    have = [sh for sh in sc.get("shots") or [] if sh.get("angle") or sh.get("camera_move") or sh.get("angle_swipe")]
    if not have:
        return []
    got = {str(x.get("id")): x for x in pitch.get("shots") or [] if isinstance(x, dict)}
    fails, copied = [], 0
    for sh in have:
        ns = got.get(str(sh.get("id"))) or {}
        mv = move_of(ns.get("camera_move"))
        if not str(ns.get("angle") or "").strip() or not mv:
            fails.append(f"shot {sh.get('id')} has no camera of its own (angle and one of {', '.join(CAMERA_MOVES)})")
            continue
        if mv == "hold" and not base and not str(ns.get("camera_why") or "").strip():
            fails.append(f"shot {sh.get('id')} holds the camera with no reason")
        a0, m0 = swipe_camera(sh)
        if " ".join(str(ns["angle"]).lower().split()) == " ".join(str(a0).lower().split()) and mv == move_of(m0):
            copied += 1
    if copied == len(have) and not base:
        fails.append("the camera is the swipe's, copied shot for shot")
    return fails


def fill(text, vals):
    """One pass: `{slot}` -> its value; a slot with no value is left as written; inserted text is never re-filled."""
    return re.sub(r"\{(\w+)\}", lambda m: str(vals[m.group(1)]) if m.group(1) in vals else m.group(0), text)


def _read(p):
    try:
        return Path(p).read_text()
    except (OSError, TypeError):
        return ""


# ---------- the brief ----------

def brief_path(run):
    return Path(run) / "stages" / "5-brief.md"


def _blocks(text):
    return list(re.finditer(r"```json\s*\n(.*?)\n```", text, re.S))


def brief_doc(text):
    """The brief's production data: its last ```json block (the one Video Studio seeds from)."""
    b = _blocks(text)
    if not b:
        raise ValueError("the brief has no json block")
    return json.loads(b[-1].group(1))


def put_doc(text, doc):
    """The brief with its last json block replaced by `doc`; every other line untouched."""
    m = _blocks(text)[-1]
    ind = re.match(r"\{\n( +)\"", m.group(1))
    esc = "\\u" in m.group(1) or not re.search(r"[^\x00-\x7f]", m.group(1))
    body = json.dumps(doc, indent=len(ind.group(1)) if ind else 1, ensure_ascii=esc)
    return text[:m.start(1)] + body + text[m.end(1):]


def directable(sc):
    """A scene the director stages: it has a staging line (or sung lines) and beats, and it is not a card, end card
    or screen."""
    return bool(sc.get("kind") not in NOT_STAGED and (sc.get("happens") or sc.get("happens_swipe") or sc.get("lyrics"))
                and sc.get("beats"))


def sung_shots(sc):
    """The song-ad rule: every sung line is acted out as its own silent shot. A sung scene with no shots or beats of
    its own gets one shot and one beat per line (ids `<scene>.<n>` and `B<n>`), so the director stages each line."""
    lyr = [str(x) for x in sc.get("lyrics") or [] if str(x).strip()]
    if not lyr or sc.get("beats"):
        return sc
    sc["shots"] = [{"id": f"{sc['id']}.{k}", "lyrics": [ln], **({"line": sc["lines_from"][k - 1]}
                    if len(sc.get("lines_from") or []) == len(lyr) else {})} for k, ln in enumerate(lyr, 1)]
    sc["beats"] = [{"id": f"B{k}", "shot": f"{sc['id']}.{k}", "over": ln, "do": ""} for k, ln in enumerate(lyr, 1)]
    return sc


def gates(sc):
    """The hard checks this scene's section brings: problem kept visible, product clear."""
    sec = str(sc.get("section") or "").lower()
    return {"problem": sec in BEFORE_PAYOFF, "product": sec in PRODUCT_BEATS}


def swipe_happens(sc):
    """The staging stage 5 wrote from the swipe, even on a scene this station already directed."""
    return sc.get("happens_swipe") or sc.get("happens") or ""


def swipe_do(beat):
    return beat.get("do_swipe") or beat.get("do") or ""


def spoken(sc):
    if sc.get("lyrics") and not sc.get("script"):
        return "SUNG (each line its own silent shot): " + " / ".join(str(x) for x in sc["lyrics"])
    rows = sc.get("script") or []
    if rows:
        return " / ".join(f"{r.get('speaker') or sc.get('speaker') or ''}: {r.get('say', '')}".strip(": ") for r in rows)
    return sc.get("voice") or "(no words: a silent scene under the music)"


def swipe_rows(doc):
    """Scene id -> what the swipe shows in the rows the brief's roll sheet gives that scene."""
    rows = {}
    for r in (doc or {}).get("roll_sheet") or []:
        m = re.search(r"shows:\s*([^\]]+)", str(r.get("row") or ""))
        if r.get("scene") and m:
            rows.setdefault(r["scene"], []).append(m.group(1).strip())
    return rows


def shot_notes(sc, doc):
    """Shot id -> who is in it and what the swipe shows there. A scene folded from several keeps one shot per old
    scene, in order, so each shot is matched to the old scene it came from."""
    rows = swipe_rows(doc)
    shots = sc.get("shots") or []
    olds = sc.get("folded_from") or [sc.get("id")]
    notes = {}
    for i, sh in enumerate(shots):
        old = olds[i] if len(olds) == len(shots) else (sc.get("id") if i == 0 else None)
        bits = []
        if sh.get("gestures_swipe") or sh.get("gestures"):
            bits.append("today: " + "; ".join(str(g) for g in (sh.get("gestures_swipe") or sh["gestures"])))
        if old and rows.get(old):
            bits.append("the swipe shows: " + ", ".join(dict.fromkeys(rows[old])))
        notes[sh.get("id")] = " · ".join(bits)
    return notes


def swipe_understanding(run):
    """What the swipe does and why (owner, 2026-11-20: "we use the swipe as understanding of what's going on, but we
    generate our own work"): the teardown's scene mechanics and psychology, as context for the director."""
    t = _read(Path(run) / "stages" / "1-teardown.md")
    parts = re.findall(r"(?ms)^### (THE SCENE MECHANICS|THE PSYCHOLOGY)\s*$(.*?)(?=^### |\Z)", t)
    out = "\n\n".join(f"#### {h.title()}\n{b.strip()}" for h, b in parts).strip()
    return out[:14000] or "(no teardown read on file for this run)"


def swipe_moment(sc):
    """One scene's line of understanding: the job its moment does in the swipe and what happened there."""
    bits = [x for x in (sc.get("source"), sc.get("happens_swipe") or "") if x and "script-backed" not in str(x)]
    return " · what happened there: ".join(str(b) for b in bits)


def fresh_card(sc, doc=None):
    """One scene as the director reads it once the visuals are ours: our words, the job, the emotion, who and what
    the brief has, the beats with the words they sit under, and what the swipe's moment did and why (understanding,
    never a shot to restage). No swipe camera, face or beat staging."""
    g = gates(sc)
    places = ", ".join(str(w.get("id")) for w in (doc or {}).get("world") or [] if w.get("id")) or "(none listed)"
    out = [f"## {sc['id']} · section {sc.get('section', '?')} · {sc.get('kind', '?')}",
           f"- **Spoken:** {spoken(sc)}",
           f"- **What it has to land:** {sc.get('outcome') or (sc.get('doctrine') or {}).get('feel') or '(not stated)'}",
           f"- **Emotion:** {sc.get('emotion') or '(not stated)'}",
           f"- **Cast on screen:** {sc.get('who') or sc.get('speaker') or '(none)'}; props in the brief: "
           f"{', '.join(sc.get('props') or []) or '(none)'}",
           f"- **Places you may set it in** (the brief's world): {places}",
           ("- **Nothing staged yet** — a sung moment; you stage every line as its own silent shot"
            if sc.get("lyrics") and not sc.get("happens") else
            "- **Staging:** none handed to you. The setting, the action, the camera and the motion are yours, from "
            "the words, the idea and the dial target."),
           *([f"- **What the swipe does here and why** (understanding only — never a shot to restage): {swipe_moment(sc)}"]
             if swipe_moment(sc) else []),
           f"- **Checks this scene carries:** problem visible = {'YES' if g['problem'] else 'no (payoff or later)'}; "
           f"product clear = {'YES' if g['product'] else 'no'}",
           "- **Shots** (give each its face, gestures and camera): " + ", ".join(
               f"`{s.get('id')}`" + (f" ({len(s.get('lines') or [])} line(s))" if s.get("lines") else "")
               for s in sc.get("shots") or []),
           "- **Beats** (keep these ids, this count, this order; each plays under its words):"]
    people = named_people(sc, doc)
    for b in sc.get("beats") or []:
        must = f" — MUST SHOW {people[b.get('id')]} doing it (the words name them)" if b.get("id") in people else ""
        shot = f" (shot {b['shot']})" if b.get("shot") else ""
        out.append(f"  - `{b.get('id')}` under \"{b.get('over', '')}\"{shot}{must}")
    return "\n".join(out)


def scene_card(sc, doc=None):
    """One scene as the director and the producer read it: its words, its job, the swipe's shot as backbone only
    (v1); once the visuals are ours, the fresh card."""
    if mode() == "ours":
        return fresh_card(sc, doc)
    g = gates(sc)
    ff = sc.get("first_frame") or {}
    out = [f"## {sc['id']} · section {sc.get('section', '?')} · {sc.get('kind', '?')} · {sc.get('setting_id', '?')}",
           f"- **Spoken:** {spoken(sc)}",
           f"- **What it has to land:** {sc.get('outcome') or (sc.get('doctrine') or {}).get('feel') or '(not stated)'}",
           f"- **Emotion:** {sc.get('emotion') or '(not stated)'}",
           f"- **Cast on screen:** {sc.get('who') or sc.get('speaker') or '(none)'}; props in the brief: "
           f"{', '.join(sc.get('props') or []) or '(none)'}",
           (f"- **The swipe's shot — backbone only, never the picture to copy:** {swipe_happens(sc)}"
            + (f" (swipe: {sc['source']})" if sc.get("source") else "")) if swipe_happens(sc) else
           "- **Staged today:** nothing yet — a sung moment; you stage every line as its own silent shot",
           f"- **Opening picture today:** {ff.get('subject', '')}; {ff.get('action_swipe') or ff.get('action', '')}",
           f"- **Checks this scene carries:** problem visible = {'YES' if g['problem'] else 'no (payoff or later)'}; "
           f"product clear = {'YES' if g['product'] else 'no'}",
           "- **Shots** (give each its face and gestures for your idea" + (", and its camera" if camera_on() else "")
           + "): " + "; ".join(
               f"`{s.get('id')}` face today: {s.get('face_swipe') or s.get('face') or '(none)'}"
               + (f"; the swipe's camera (backbone only): {swipe_camera(s)[0] or '(none)'}, {swipe_camera(s)[1] or '(none)'}"
                  if camera_on() and any(swipe_camera(s)) else "")
               for s in sc.get("shots") or []),
           *([f"- **What the swipe does here and why:** {swipe_moment(sc)}"]
             if mode() == "swipe-base" and swipe_moment(sc) else []),
           *([f"- **Places you may set it in** (the brief's world): "
              + (", ".join(str(w.get("id")) for w in (doc or {}).get("world") or [] if w.get("id")) or "(none listed)")]
             if mode() == "swipe-base" else []),
           "- **Beats** (keep these ids, this count, this order):"]
    shots = {s.get("id"): s for s in sc.get("shots") or []}
    notes = shot_notes(sc, doc)
    people = named_people(sc, doc)
    for b in sc.get("beats") or []:
        sh = shots.get(b.get("shot")) or {}
        extra = "; ".join(x for x in (sh.get("face_swipe") or sh.get("face"), notes.get(b.get("shot"))) if x)
        where = f" (shot {b['shot']}: {extra})" if b.get("shot") else ""
        must = f" — MUST SHOW {people[b.get('id')]} doing it (the words name them)" if b.get("id") in people else ""
        out.append(f"  - `{b.get('id')}` under \"{b.get('over', '')}\" — today: {swipe_do(b)}{where}{must}")
    return "\n".join(out)


def ad_outline(doc):
    """The whole ad in one line per scene, so each batch keeps one idea running and never repeats a premise."""
    rows = []
    for sc in doc.get("scenes") or []:
        rows.append(f"- {sc.get('id')} · {sc.get('section', '')}" + (f" · {sc['title']}" if sc.get("title") else "")
                    + f" · {(spoken(sc) or '')[:140]}"
                    + ("" if mode() == "ours" else " · staged today: "
                       f"{swipe_happens(sc) or ('(not yet)' if sc.get('lyrics') else '(card)')}"))
    return "\n".join(rows)


def cast_lines(doc):
    return "\n".join(f"- {c.get('id')}: {str(c.get('identity_block') or '')[:160]}"
                     for c in (doc or {}).get("cast") or []) or "(no cast list)"


def place_lines(doc):
    return "\n".join(f"- {w.get('id')}: {str(w.get('description') or '')[:140]}"
                     for w in (doc or {}).get("world") or []) or "(no places listed)"


# ---------- the inputs every call carries ----------

def controlling_idea(run):
    """Stage 4i's winning idea, without its candidate table (the losers are not this run's idea)."""
    t = _read(Path(run) / "stages" / "4i-controlling-idea.md")
    return (t.split("### THE FIVE CANDIDATES")[0].strip() or "(no controlling idea on file for this run)")


def controls_target(ws, brand, preset="maxed"):
    """The VIDEO dial levels this run aims for (creative-controls `target_md`, the one place the dials live).
    `preset` is the one the writing kept on the run (`controls_preset.preset`, by its awareness level since
    2026-11-18), so the director aims where the passes before it aimed; the house preset when the run names none."""
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("director_creative_controls",
                                                    ws / "components/creative-controls/creative_controls.py")
        mod = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mod)
        return mod.target_md(preset or "maxed", brand, "video")
    except Exception as e:  # noqa: BLE001 — an unreadable input is said, not fatal
        return f"(the controls target could not be read: {str(e)[:120]})"


def brand_text(ws, brand, filename):
    """A brand-identity file, read only, found through brandpath."""
    bp = ws / "components" / "brandpath"
    if str(bp) not in sys.path:
        sys.path.insert(0, str(bp))
    try:
        import brandpath
        return _read(brandpath.brand_file(brand, "brand-identity", filename, root=ws / "brands")).strip()
    except Exception:  # noqa: BLE001
        return ""


def run_rulings(run):
    """This run's own rulings (RULINGS.md: the owner's rulings for this piece — its offer, its close, what may and may
    not be shown). 2026-11-20: the director never read them and drew a removed gift back into an end card."""
    t = _read(Path(run) / "RULINGS.md").strip()
    if not t:
        return ""
    # the owner's rulings first and whole, wherever they sit in a long file (2026-11-20: they sat past the cut)
    owner = re.findall(r"(?ms)^#+ Owner rulings\b.*?(?=^#{1,2} (?!#)|\Z)", t)
    rest = t
    for o in owner:
        rest = rest.replace(o, "")
    return ("**This run's rulings (RULINGS.md) — they bind every picture; where a later ruling supersedes an earlier "
            "one, the later one holds. The owner's rulings first:**\n\n" + "\n\n".join(o.strip() for o in owner)
            + ("\n\n**The rest of the run's rulings:**\n\n" + rest.strip()[:20000] if rest.strip() else ""))


def rulings_block(run, ws, brand):
    return "\n\n".join(x for x in [
        prompt("rulings").strip(),
        run_rulings(run),
        "**The controlling idea (stage 4i) — the one idea the whole ad runs on:**\n\n" + controlling_idea(run),
        "**The creative controls target — the levels every picture aims for:**\n\n"
        + controls_target(ws, brand, run_preset(run)),
    ])


def run_preset(run):
    """The dial preset the writing kept on this run (`controls_preset.preset` on run.json), else the house preset."""
    try:
        return (json.loads(_read(Path(run) / "run.json") or "{}").get("controls_preset") or {}).get("preset") or "maxed"
    except (ValueError, AttributeError, TypeError):
        return "maxed"


def shared_values(run, ws, doc, brand):
    """Every slot of the director prompt that does not change from batch to batch."""
    slices = ws / "components" / "marketing-doctrine" / "slices"
    song = doc.get("song")
    return {
        "ladder": prompt("ladder"),
        "rungs": RUNGS,
        "swipe_understanding": swipe_understanding(run),
        "curation": ("(No curator shelf at the storyboard step. The shelf is the swipe: each scene below gives the "
                     "swipe's shot — its picture and its motion pattern — as the base your version is built from; our "
                     "people, place, product and idea go on top, pushed by the dial target.)") if mode() == "swipe-base"
        else ("(No curator shelf at the storyboard step. The swipe is here as understanding — what each moment "
                     "does and why — never a shot to restage: the pictures are yours, from our words, the idea and the "
                     "dial target.)") if camera_on() else
                    ("(No curator shelf at the storyboard step. The shelf is the swipe: each scene below names the "
                     "swipe's shot as its backbone — what the moment has to land — never as the picture to copy.)"),
        "rulings": rulings_block(run, ws, brand),
        "avatar_card": _read(Path(run) / "stages" / "1b-audience.md").strip() or "(no reader card on file)",
        "customer_language": "(The brief's spoken lines are the reader's words, already placed. Quote nothing new.)",
        "position": brand_text(ws, brand, "position.md") or "(no position on file)",
        "story": brand_text(ws, brand, "story.md") or "(no brand story on file)",
        "music_profile": (json.dumps(song, ensure_ascii=False)[:4000] if song else
                          "(This brief carries no song. The pictures play under the spoken lines.)"),
        "angles": "(The angle is already set by the brief. Do not change it.)",
        "desire_dimensions": _read(slices / "desire.md"),
        "awareness_levels": _read(slices / "awareness.md"),
        "sophistication_stages": _read(slices / "sophistication.md"),
        "ad_frameworks": "(The framework is already set by the brief.)",
    }


# ---------- the two calls ----------

def director_prompt(shared, doc, batch, per_scene, notes=None):
    vals = dict(shared)
    vals["per_rung"] = f"{per_scene} per scene in all, spread across the rungs"
    if mode() == "swipe-base":
        lead = ("**What the swipe does and why** — read it with each scene's swipe shot: it says what the moment does "
                "and why it works, so our version keeps what made it work:\n\n")
    else:
        lead = ("**What the swipe does and why** — read it to understand what each moment does and why it works; "
                "never restage its shots. Everything you pitch is generated from our words, our idea and the dial "
                "target:\n\n")
    understanding = (lead + shared["swipe_understanding"] + "\n\n") if camera_on() and shared.get("swipe_understanding") else ""
    vals["seed"] = (understanding + f"**The ad as written — \"{(doc.get('piece') or {}).get('title', '')}\"**, one line per scene "
                    "(keep one idea running through the pictures; never use the same premise on two scenes):\n\n"
                    + ad_outline(doc) + "\n\n**The cast** (ids as the beats name them):\n\n" + cast_lines(doc)
                    + "\n\n**The places** (setting ids as the beats name them in `where`):\n\n" + place_lines(doc))
    ask = fill(prompt("storyboard-ask"), {"per_scene": per_scene, "hard_rules": HARD_RULES,
                                          "scenes": "\n\n".join(scene_card(s, doc) + (
                                              "\n- **Your first round for this scene failed — fix exactly this:** "
                                              + notes[s["id"]] if (notes or {}).get(s["id"]) else "")
                                                                  for s in batch)})
    return fill(prompt("room2-director"), vals).rstrip() + "\n\n" + ask


def pick_prompt(shared, batch, pitched, doc=None, notes=None):
    parts = []
    for sc in batch:
        pp = pitched.get(sc["id"]) or []
        note = ("\n- **Your first round for this scene failed — the director was told:** " + notes[sc["id"]]
                if (notes or {}).get(sc["id"]) else "")
        parts.append(scene_card(sc, doc) + note + "\n\n**The pitches:**\n\n" + "\n\n".join(
            f"### {p.get('title')} ({p.get('rung', '?')})\n```json\n{json.dumps(p, indent=1, ensure_ascii=False)}\n```"
            for p in pp))
    return fill(prompt("pick"), {"rulings": shared["rulings"], "scenes": "\n\n---\n\n".join(parts)})


def parse_block(text, tag):
    """The JSON inside the reply's fenced block tagged `tag` (a plain ```json block or a bare object as a fallback)."""
    m = (re.search(r"```" + tag + r"\s*\n(.*?)\n```", text, re.S) or re.search(r"```json\s*\n(.*?)\n```", text, re.S)
         or re.search(r"(\{.*\})", text, re.S))
    if not m:
        raise ValueError(f"no {tag} block in the reply")
    # the slips models make in long JSON: a raw line break or tab inside a string, a comma before a closing bracket
    try:
        return json.loads(m.group(1), strict=False)
    except ValueError:
        return json.loads(re.sub(r",(\s*[\]}])", r"\1", m.group(1)), strict=False)


def sid(x):
    """A scene id as the reply wrote it, read to its first word: "S40 · section ..." is S40."""
    m = re.match(r"\s*#*\s*([A-Za-z]*\d+[A-Za-z0-9.]*)", str(x or ""))
    return m.group(1) if m else str(x or "").strip()


def claude_call(text, tier):
    """One writing-model call through run-kit's claude_door (no account wired in), on the registry's tier model."""
    rk = workspace() / "components" / "run-kit"
    if str(rk) not in sys.path:
        sys.path.insert(0, str(rk))
    from run_kit import claude_door
    from run_kit.model import TIERS
    last = None
    for attempt in (1, 2, 3):
        r = claude_door.run(["--model", TIERS[tier], "--output-format", "text"],
                            text + "\n\nReturn only the deliverable. No tools, no preamble.", timeout=3600)
        if not r.returncode and (r.stdout or "").strip():
            return r.stdout
        last = r
        time.sleep(10 * attempt)
    raise RuntimeError("the call failed 3 times: " + ((last.stderr or last.stdout or "") if last else "")[:300])


# ---------- the machine's decision ----------

def named_people(sc, doc):
    """Beat id -> the cast id its words name doing something, where the swipe's own shot shows that person too
    ("Two weeks later, the general manager wrote me a letter" over a shot the swipe shows as "manager writing").
    The speaker is never counted; a name the words carry but the swipe's shot does not is left to the producer."""
    notes = shot_notes(sc, doc)
    speaker = str(sc.get("speaker") or "").upper()
    want = {}
    for b in sc.get("beats") or []:
        words = set(re.findall(r"[a-z]+", str(b.get("over") or "").lower()))
        shown = set(re.findall(r"[a-z]+", str(notes.get(b.get("shot")) or "").split("the swipe shows:")[-1].lower())
                    ) if "the swipe shows:" in str(notes.get(b.get("shot")) or "") else set()
        for c in (doc or {}).get("cast") or []:
            cid = str(c.get("id") or "").upper()
            if not cid or cid == speaker:
                continue
            toks = {w for w in re.findall(r"[a-z]+", cid.lower()) if len(w) >= 4}
            if toks & words and toks & shown:
                want[b.get("id")] = cid
    return want


def beats_match(sc, pitch):
    """Every beat of the scene is restaged, in the scene's order; a beat the pitch adds past them is dropped."""
    want = [b.get("id") for b in sc.get("beats") or []]
    got = [b.get("id") for b in pitch.get("beats") or [] if b.get("id") in want]
    return want == got


def decide(sc, pitches, scores, doc=None):
    """Keep ONE pitch for the scene. A pitch is out when its beats do not line up with the scene's, when it does not
    say the line, when it leaves the real scene, or when it fails a check the scene's section carries (problem
    visible, product clear). Of the rest, the highest total of the four scores wins; a tie goes to the director's
    order. Returns {"keep": pitch or None, "why": str, "table": [...]}."""
    g = gates(sc)
    people = named_people(sc, doc)
    by_title = {str(s.get("title", "")).strip().lower(): s for s in scores or []}
    table, best = [], None
    for i, p in enumerate(pitches or []):
        s = by_title.get(str(p.get("title", "")).strip().lower()) or {}
        fails = []
        if not s:
            fails.append("not scored")
        if not beats_match(sc, p):
            fails.append("does not restage every beat of the scene")
        if not str(p.get("happens") or "").strip():
            fails.append("no staging line")
        if s and not s.get("says_the_line"):
            fails.append("does not say the line")
        whos = {x.get("id"): str(x.get("who") or "").upper() for x in p.get("beats") or []}
        for bid, cid in people.items():
            if cid not in whos.get(bid, ""):
                fails.append(f"{bid} does not show {cid}, whom its words name")
        if s and not s.get("inside_the_scene"):
            fails.append("leaves the real scene")
        if s and g["problem"] and not s.get("problem_visible"):
            fails.append("problem not visible")
        if s and g["product"] and not s.get("product_clear"):
            fails.append("product not clear")
        fails += camera_fails(sc, p)
        total = sum(int(s.get(k) or 0) for k in SCORE_KEYS)
        row = {"title": p.get("title"), "rung": p.get("rung"), "total": total,
               "of": 10 * max(4, sum(1 for k in SCORE_KEYS if k in s)),
               **{k: s.get(k) for k in SCORE_KEYS}, "out": fails, "why": s.get("why", "")}
        table.append(row)
        if not fails and (best is None or total > best[1]):
            best = (i, total)
    if best is None:
        return {"keep": None, "table": table,
                "why": "no pitch passed the checks; the scene keeps the swipe's staging"}
    keep = pitches[best[0]]
    others = [r for r in table if r["title"] != keep.get("title")]
    lost = "; ".join(f"{r['title']} {r['total']}" + (f" (out: {', '.join(r['out'])})" if r["out"] else "")
                     for r in others)
    row = table[best[0]]
    return {"keep": keep, "table": table,
            "why": f"highest score that passed every check: {row['total']}/{row['of']} "
                   f"(stops {row['stops']}, made {row['made']}, doctrine {row['doctrine']}, controls {row['controls']}"
                   + (f", camera {row['camera']}" if row.get("camera") is not None else "") + "). "
                   f"{row['why']}" + (f" Beat: {lost}." if lost else "")}


DELIVERY_SWAP = {"stops": "halts", "slows": "eases", "settles": "rests", "says": "mouths"}
JOINERS = re.compile(r"[,;:.!?]|\s(?:and|as|while|then|until|before|after|so|but|or|when|whilst|till|plus)\s", re.I)


def one_action(text):
    """A beat's `do` as production takes it: ONE visible action, one verb (MODEL-INPUTS, beat grammar). The director
    writes it so; where a reply still joins a second action on, the beat is cut at the first joiner. The whole
    picture stays in the beat's `action`."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    m = JOINERS.search(t)
    t = (t[:m.start()] if m and m.start() > 3 else t).strip(" ,;:-—")
    head, _, rest = t.partition(" ")
    swap = DELIVERY_SWAP.get(head.lower())   # a delivery word is a bracket, never the beat's verb (stage 5 v15)
    return f"{swap} {rest}".strip() if swap else t


def apply_pick(sc, keep, record, doc_world=None):
    """Write the kept idea into the scene as production reads it; the swipe's text stays beside it."""
    sc.setdefault("happens_swipe", sc.get("happens") or "")
    sc["happens"] = keep["happens"].strip()
    new = {b.get("id"): b for b in keep.get("beats") or []}
    for b in sc.get("beats") or []:
        nb = new.get(b.get("id")) or {}
        if not nb:
            continue
        b.setdefault("do_swipe", b.get("do") or "")
        for k in BEAT_LAYER:                 # what stage 5 had, so a rerun can take this pick off again (unlayer)
            b.setdefault(k + "_swipe", b.get(k))
        b["action"] = nb.get("action") or nb.get("do") or b["do_swipe"]
        b["do"] = one_action(nb.get("do") or b["action"])
        b["who"] = nb.get("who") or b.get("who") or sc.get("who") or ""
        b["prop"] = nb.get("prop") or ""
        b["where"] = nb.get("where") or sc.get("setting_id") or ""
    new_shots = {s.get("id"): s for s in keep.get("shots") or [] if isinstance(s, dict)}
    for sh in sc.get("shots") or []:
        ns = new_shots.get(sh.get("id")) or {}
        if str(ns.get("face") or "").strip():
            sh.setdefault("face_swipe", sh.get("face") or "")
            sh["face"] = ns["face"].strip()
        g = [str(x).strip() for x in (ns.get("gestures") or []) if str(x).strip()]
        if g:
            sh.setdefault("gestures_swipe", sh.get("gestures") or [])
            sh["gestures"] = g
        mv = move_of(ns.get("camera_move"))
        if camera_on() and str(ns.get("angle") or "").strip() and mv:
            sh.setdefault("angle_swipe", sh.get("angle") or "")
            sh.setdefault("camera_move_swipe", sh.get("camera_move") or "")
            sh["angle"] = ns["angle"].strip()
            sh["camera_move"] = mv
            if str(ns.get("camera_why") or "").strip():
                sh["camera_why"] = ns["camera_why"].strip()
    places = {str(w.get("id")) for w in (doc_world or [])}
    if camera_on() and str(keep.get("setting_id") or "").strip() and (not places or keep["setting_id"] in places):
        sc.setdefault("setting_id_swipe", sc.get("setting_id") or "")
        sc["setting_id"] = keep["setting_id"].strip()
    ff = sc.get("first_frame")
    if isinstance(ff, dict) and str(keep.get("first_frame_action") or "").strip():
        ff.setdefault("action_swipe", ff.get("action") or "")
        ff["action"] = keep["first_frame_action"].strip()
    sc["director"] = {"station": STATION, "title": keep.get("title"), "rung": keep.get("rung"),
                      "premise": keep.get("premise"), "picture": keep.get("picture"), "record": record}
    return sc


BEAT_LAYER = ("action", "who", "prop", "where")


def unlayer(doc, base=None, only=None):
    """Take the last director's picks off a directed brief, keeping everything else in it (the hand fixes made after
    it was directed: viewpoints, offer lines, sections, the fold, the style map). Each field goes back to the value
    kept beside it (`*_swipe`); a beat directed before those copies were kept takes its action / who / prop / where
    from `base`, the brief stage 5 wrote, by scene and beat id, and keeps the pick's where `base` has no such beat."""
    old = {s.get("id"): {b.get("id"): b for b in s.get("beats") or []} for s in (base or {}).get("scenes") or []}
    for sc in doc.get("scenes") or []:
        if only and sc.get("id") not in only:
            continue                         # a rerun of some scenes keeps every other scene's pick
        if "happens_swipe" in sc:
            sc["happens"] = sc.pop("happens_swipe")
        sc.pop("director", None)
        if "setting_id_swipe" in sc:
            sc["setting_id"] = sc.pop("setting_id_swipe")
        ff = sc.get("first_frame")
        if isinstance(ff, dict) and "action_swipe" in ff:
            ff["action"] = ff.pop("action_swipe")
        for b in sc.get("beats") or []:
            if "do_swipe" not in b:
                continue
            b["do"] = b.pop("do_swipe")
            was = (old.get(sc.get("id")) or {}).get(b.get("id"))
            for k in BEAT_LAYER:
                if k + "_swipe" in b:
                    v = b.pop(k + "_swipe")
                elif was is not None:
                    v = was.get(k)
                else:
                    continue
                if v is None:
                    b.pop(k, None)
                else:
                    b[k] = v
        for sh in sc.get("shots") or []:
            for k in ("face", "gestures", "angle", "camera_move"):
                if k + "_swipe" in sh:
                    sh[k] = sh.pop(k + "_swipe")
            if "angle_swipe" not in sh:
                sh.pop("camera_why", None)
    return doc


def picks_md(doc, picks):
    lines = ["## Director's picks (stage 5d, automatic)", "",
             "One idea per scene, kept by the machine from the director's pitches. The swipe's staging is kept "
             "beside each scene in the json (`happens_swipe`). Pitches and scores: `director/`.", ""]
    for sid, p in picks.items():
        if p.get("lyrics"):                 # a sung moment: its title, its lines, the kept idea and its score
            head = f"- **{sid} · {p.get('title', '')}** ({len(p['lyrics'])} lines: \"{p['lyrics'][0]}\" …)"
            lines.append(head + (f"  \n  idea: **{p['kept']['title']}** ({p['kept'].get('rung')}, "
                                 f"{p['kept'].get('score')}): {p['after']}" if p.get("kept") else
                                 f"  \n  no idea kept: {p['why']}"))
            continue
        if p.get("kept"):
            lines.append(f"- **{sid} · {p['kept']['title']}** ({p['kept'].get('rung')}): {p['after']}  \n"
                         f"  was: {p['before']}")
        else:
            lines.append(f"- **{sid}** unchanged: {p['why']}")
    return "\n".join(lines) + "\n"


def with_picks_section(text, section):
    """The brief with its director's-picks section replaced (or added at the end)."""
    head = "## Director's picks (stage 5d, automatic)"
    if head in text:
        start = text.index(head)
        nxt = re.search(r"\n## ", text[start + len(head):])
        end = start + len(head) + nxt.start() + 1 if nxt else len(text)
        return text[:start] + section + ("\n" + text[end:] if nxt else "")
    return text.rstrip() + "\n\n" + section


# ---------- the station ----------

def run_director(doc, todo, out, shared, caller, per_scene=3, batch=6, workers=3, fresh=False, dry=False,
                 record="director/picks.json", retry=True):
    """The director, the producer and the machine's pick over `todo` (scenes of `doc`, changed in place).
    Returns scene id -> pick record; {} on a dry run."""
    out.mkdir(parents=True, exist_ok=True)
    groups = [todo[i:i + batch] for i in range(0, len(todo), batch)]
    notes, tag = {}, [""]

    def one(k_group):
        k, group = k_group
        k = f"{tag[0]}{k}"
        dp = director_prompt(shared, doc, group, per_scene, notes)
        if dry:
            (out / f"{k}-director.prompt.md").write_text(dp)
            return {}
        try:
            said = ask(out, caller, dp, "designs", f"{k}-director", fresh)
            pitched = {sid(s.get("id")): s.get("pitches") or [] for s in parse_block(said, "STORYBOARD").get("scenes") or []}
            judged = ask(out, caller, pick_prompt(shared, group, pitched, doc, notes), "checks", f"{k}-pick", fresh)
            scored = {sid(s.get("id")): s.get("pitches") or [] for s in parse_block(judged, "SCORES").get("scenes") or []}
        except Exception as e:  # noqa: BLE001 — one failed batch leaves its scenes on the swipe staging, said
            err = f"batch {k} failed: {str(e)[:200]}"
            return {sc["id"]: ([], [], err) for sc in group}
        return {sc["id"]: (pitched.get(sc["id"]) or [], scored.get(sc["id"]) or [], None) for sc in group}

    results = {}
    with cf.ThreadPoolExecutor(max(1, min(workers, len(groups)))) as ex:
        for r in ex.map(one, enumerate(groups, 1)):
            results.update(r)
    if dry:
        return {}
    # A BATCH THAT BROKE IS ASKED AGAIN, never left on the swipe's staging (owner ruling 2026-11-20: every visual is
    # ours). An unreadable reply used to drop its whole batch back to the swipe and the stage still finished: ideas
    # 40 and 42 shipped with 6 undirected scenes each. Two more tries, smaller batches; still broken = the stage fails.
    for attempt in (1, 2):
        broke = [sc for sc in todo if results.get(sc["id"], ([], [], "not run"))[2]]
        if not broke:
            break
        tag[0] = f"x{attempt}"
        size = max(1, batch // (2 * attempt))
        with cf.ThreadPoolExecutor(max(1, min(workers, len(broke)))) as ex:
            for r in ex.map(one, enumerate([broke[i:i + size] for i in range(0, len(broke), size)], 1)):
                results.update(r)
    still = [sc["id"] for sc in todo if results.get(sc["id"], ([], [], "not run"))[2]]
    if still:
        last = next(results[s][2] for s in still)
        raise DirectorFailed("5d director: no readable reply for " + ", ".join(still) + " after three tries ("
                             + last + "); the stage fails rather than leave a scene on the swipe's staging — run it again")
    decided = {sc["id"]: decide(sc, *results.get(sc["id"], ([], [], "not run"))[:2], doc) for sc in todo}
    # ONE MORE ROUND for a scene where nothing passed: the director is told exactly why each pitch was out
    again = [sc for sc in todo if retry and not decided[sc["id"]]["keep"] and decided[sc["id"]]["table"]]
    first = {}
    if again:
        for sc in again:
            first[sc["id"]] = decided[sc["id"]]["table"]
            notes[sc["id"]] = "; ".join(f"\"{r['title']}\" was out because it "
                                        + ", ".join(r["out"] or ["scored low"]) + (f" ({r['why']})" if r.get("why") else "")
                                        for r in decided[sc["id"]]["table"])
        tag[0] = "r"
        with cf.ThreadPoolExecutor(max(1, min(workers, len(again)))) as ex:
            for r in ex.map(one, enumerate([again[i:i + batch] for i in range(0, len(again), batch)], 1)):
                results.update(r)
        for sc in again:
            decided[sc["id"]] = decide(sc, *results.get(sc["id"], ([], [], "not run"))[:2], doc)
    picks = {}
    for sc in todo:
        pitches, scores, err = results.get(sc["id"], ([], [], "not run"))
        d = decided[sc["id"]]
        if err:
            d["why"] = err + "; the scene keeps the swipe's staging"
        before = swipe_happens(sc)
        rec = {"scene": sc["id"], "section": sc.get("section"), "before": before, "pitches": pitches,
               "scores": d["table"], "why": d["why"], "kept": None, "after": before}
        if sc["id"] in first:
            rec["round"] = 2
            rec["first_round"] = first[sc["id"]]
        if sc.get("title"):
            rec["title"] = sc["title"]
        if sc.get("lyrics"):
            rec["lyrics"] = list(sc["lyrics"])
        if d["keep"]:
            apply_pick(sc, d["keep"], f"{record}#{sc['id']}", (doc or {}).get("world"))
            row = next((r for r in d["table"] if r["title"] == d["keep"].get("title")), {})
            rec.update(kept={"title": d["keep"].get("title"), "rung": d["keep"].get("rung"),
                             "premise": d["keep"].get("premise"), "picture": d["keep"].get("picture"),
                             "score": row.get("total")},
                       after=sc["happens"],
                       beats=[{k: b.get(k) for k in ("id", "who", "action", "prop", "where", "do_swipe", "over")}
                              for b in sc.get("beats") or []],
                       first_frame_action=(sc.get("first_frame") or {}).get("action"),
                       setting_id=sc.get("setting_id"), setting_id_swipe=sc.get("setting_id_swipe"),
                       shots=[{k: s.get(k) for k in ("id", "face", "gestures", "face_swipe", "gestures_swipe", "angle",
                                                     "camera_move", "camera_why", "angle_swipe", "camera_move_swipe")
                               if k in s}
                              for s in sc.get("shots") or []])
        picks[sc["id"]] = rec
    return picks


def ask(out, caller, text_in, tier, name, fresh=False):
    """One call, or the reply already on file for this exact prompt (a rerun resumes; `fresh` asks again)."""
    pf, af = out / f"{name}.prompt.md", out / f"{name}.md"
    if not fresh and pf.is_file() and af.is_file() and pf.read_text() == text_in and af.read_text().strip():
        return af.read_text()
    pf.write_text(text_in)
    said = caller(text_in, tier)
    af.write_text(said)
    return said


class DirectorFailed(RuntimeError):
    """The director could not direct every scene. The stage fails and is run again; a scene is never left on the
    swipe's staging (owner ruling 2026-11-20: every visual is ours)."""


def for_whom(caller, run):
    """The model door with the run's who-and-what block on top, so the staging is for the same person the words are."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.append(here)
    try:
        import writing_v2 as W
        b = W.who_block(Path(run), json.loads(_read(Path(run) / "run.json") or "{}"), "5-director.md") if run else ""
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — a block that cannot be read never stops the director
        print("  who block not read (%s)" % type(e).__name__)
        b = ""
    return (lambda text, tier: caller(b + text, tier)) if b else caller


def direct(run, scenes=None, per_scene=3, batch=6, caller=None, dry=False, ws=None, workers=3, fresh=False,
           brief=None):
    """Run stage 5d on one writing run's brief. Returns the picks, scene id -> record. `caller(text, tier)` is the
    model door (claude_call by default; a test passes its own)."""
    run = Path(run)
    ws = Path(ws) if ws else workspace()
    caller = for_whom(caller or claude_call, run)
    bp = Path(brief) if brief else brief_path(run)
    keep_copy = bp.with_name(bp.stem + ".before-director" + bp.suffix)
    text = bp.read_text()
    if DIRECTED in text:
        # A RERUN STARTS FROM THE BRIEF AS IT STANDS, the last picks taken off (2026-11-20: starting from the copy
        # stage 5 wrote threw away every hand fix made after the brief was first directed)
        base = brief_doc(keep_copy.read_text()) if keep_copy.is_file() else None
        text = put_doc(text, unlayer(brief_doc(text), base, scenes))
    doc = brief_doc(text)
    for s in doc.get("scenes") or []:
        sung_shots(s)                       # a sung brief: one silent shot per line
    st = json.loads(_read(run / "run.json") or "{}")
    todo = [s for s in doc.get("scenes") or [] if directable(s) and (not scenes or s.get("id") in scenes)]
    if not todo:
        raise SystemExit("no scene to direct in this brief")
    out = run / "director"
    shared = shared_values(run, ws, doc, st.get("brand") or "")
    picks = run_director(doc, todo, out, shared, caller, per_scene, batch, workers, fresh, dry)
    if dry:
        return {}
    if scenes:                              # some scenes again: every other scene keeps its pick and its record
        try:
            before = json.loads((out / "picks.json").read_text()).get("picks") or {}
        except (OSError, ValueError):
            before = {}
        picks = {sid: picks.get(sid, before.get(sid)) for sid in dict.fromkeys([*before, *picks])}
        picks = {k: v for k, v in picks.items() if v is not None}
    if any(p.get("kept") for p in picks.values()):
        if not scenes:
            keep_copy.write_text(text)      # the brief this pick was laid on: stage 5's, with every later fix in it
        bp.write_text(with_picks_section(put_doc(text, doc), picks_md(doc, picks)))
    (out / "picks.json").write_text(json.dumps({"schema": "director-picks/v1", "station": STATION,
                                                "brief": "stages/5-brief.md", "picks": picks},
                                               indent=1, ensure_ascii=False))
    (out / "picks.md").write_text(picks_md(doc, picks))
    return picks


# ---------- a sung plan (a song ad written as a song spec: one plan scene per line) ----------

def plan_lines(plan):
    """[(line id, lyric, song section)] in the song's order. A plan scene with one lyric is that line; a scene that
    already holds several (a directed plan) gives one per lyric, from the per-line ids it was grouped from."""
    names = []
    for sec in (plan.get("song") or {}).get("sections") or []:
        names += [sec.get("name")] * len(sec.get("lines") or [])
    out = []
    for sc in plan.get("scenes") or []:
        lyr = [str(x) for x in sc.get("lyrics") or [] if str(x).strip()]
        ids = sc.get("lines_from") if len(sc.get("lines_from") or []) == len(lyr) else \
            ([sc.get("id")] if len(lyr) == 1 else [f"{sc.get('id')}-{k}" for k in range(1, len(lyr) + 1)])
        for i, ln in zip(ids, lyr):
            out.append((i, ln, names[len(out)] if len(out) < len(names) else ""))
    return out


SECTIONS_FALLBACK = ("hook", "problem", "failed-solutions", "root-cause", "unique-mechanism", "solution", "product",
                     "offer", "call-to-action", "identification", "agitation", "proof", "transformation", "objections",
                     "urgency")


def section_ids(ws=None):
    """The doctrine's section ids (components/marketing-doctrine/frameworks.json), the only ones a brief may carry."""
    try:
        f = Path(ws or workspace()) / "components" / "marketing-doctrine" / "frameworks.json"
        got = [s.get("id") for s in json.loads(f.read_text()).get("sections") or [] if s.get("id")]
        return tuple(got) or SECTIONS_FALLBACK
    except Exception:  # noqa: BLE001
        return SECTIONS_FALLBACK


def valid_groups(groups, lines, sections=SECTIONS_FALLBACK):
    """Every line exactly once, in order, each scene a consecutive run; a section id from the list. Raises otherwise."""
    order = [i for i, _, _ in lines]
    flat = [str(x) for g in groups for x in g.get("lines") or []]
    if flat != order:
        raise ValueError("the scenes do not hold every line once, in the song's order")
    for g in groups:
        if not g.get("lines"):
            raise ValueError("an empty scene")
        if g.get("section") not in sections:
            g["section"] = "identification" if "identification" in sections else sections[0]
    return groups


def groups_by_section(lines):
    """The fallback cut: one scene per song section."""
    out = []
    for i, ln, sec in lines:
        if not out or out[-1]["_sec"] != sec:
            out.append({"title": sec or "the song", "section": "identification", "lines": [], "_sec": sec})
        out[-1]["lines"].append(i)
    return [{k: v for k, v in g.items() if k != "_sec"} for g in out]


def group_prompt(lines, context, sections=SECTIONS_FALLBACK):
    song, last = [], None
    for i, ln, sec in lines:
        if sec != last:
            song.append(f"\n[{sec}]")
            last = sec
        song.append(f"{i}: {ln}")
    return fill(prompt("group"), {"song": "\n".join(song).strip(), "context": context,
                                  "sections": " · ".join(f"`{s}`" for s in sections)})


def song_scenes(groups, lines):
    """The plan's moments as scenes in the brief's shape: the lines in order, one silent shot and one beat per line."""
    text = {i: ln for i, ln, _ in lines}
    scenes = []
    for k, g in enumerate(groups, 1):
        ids = [str(x) for x in g["lines"]]
        sc = {"id": f"M{k}", "title": g.get("title") or f"moment {k}", "section": g.get("section") or "identification",
              "kind": "broll", "to_camera": False, "voice": "", "lyrics": [text[i] for i in ids], "lines_from": ids,
              "outcome": g.get("title") or ""}
        scenes.append(sung_shots(sc))
    return scenes


def plan_scene(sc):
    """One directed moment as a plan scene: the sung lines it carries, its staging, one shot and one beat per line."""
    out = {k: sc.get(k) for k in ("id", "title", "section", "kind", "to_camera", "voice", "lyrics", "lines_from")}
    for k in ("happens", "first_frame", "director", "setting_id", "who"):
        if sc.get(k):
            out[k] = sc[k]
    beats = {b.get("shot"): b for b in sc.get("beats") or []}
    out["shots"] = []
    for sh in sc.get("shots") or []:
        b = beats.get(sh.get("id")) or {}
        row = {"id": sh.get("id"), "line": sh.get("line"), "lyrics": sh.get("lyrics"),
               "start_picture": "first_frame" if not out["shots"] else "own"}
        for k in ("who", "action", "prop", "where"):
            if b.get(k):
                row[k] = b[k]
        for k in ("face", "gestures"):
            if sh.get(k):
                row[k] = sh[k]
        out["shots"].append(row)
    out["beats"] = [{k: b.get(k) for k in ("id", "shot", "over", "who", "action", "prop", "where", "do") if b.get(k)}
                    for b in sc.get("beats") or []]
    if not sc.get("director"):
        out["director"] = {"station": STATION, "state": "no idea kept"}
    return out


def direct_plan(plan_path, writing_run=None, per_scene=3, batch=5, caller=None, dry=False, ws=None, workers=3,
                fresh=False):
    """Stage 5d on a sung plan (video-production's plan.json for a song ad): the lines are cut into moments (one
    model call, checked by code; one scene per song section when the cut does not hold), the director stages every
    moment line by line, the machine keeps one idea per moment, and the plan's scenes become those moments, each with
    one silent shot per line (who, action, prop, where, face, gestures). The plan before it is kept beside it.
    `writing_run` (the spoken writing run of the same ad) gives the cast, the places, the controlling idea, the
    reader card and its own director's picks as context only."""
    plan_path = Path(plan_path)
    ws = Path(ws) if ws else workspace()
    caller = for_whom(caller or claude_call, writing_run)
    keep_copy = plan_path.with_name(plan_path.stem + ".before-director" + plan_path.suffix)
    plan = json.loads(plan_path.read_text())
    if plan.get("director") and keep_copy.is_file():
        plan = json.loads(keep_copy.read_text())   # a rerun starts from the plan the song spec made
    base = json.loads(json.dumps(plan))
    lines = plan_lines(plan)
    if not lines:
        raise SystemExit("no sung lines in this plan")
    run = Path(writing_run) if writing_run else None
    wdoc = {}
    if run and (run / "stages").is_dir():
        for f in (run / "stages" / "5-brief.before-director.md", brief_path(run)):
            if f.is_file():
                wdoc = brief_doc(f.read_text())
                break
    out = plan_path.parent / "director"
    out.mkdir(parents=True, exist_ok=True)
    context = (controlling_idea(run) if run else "") or "(no controlling idea on file)"
    secs = section_ids(ws)
    if dry:
        (out / "0-group.prompt.md").write_text(group_prompt(lines, context, secs))
        groups = groups_by_section(lines)
    else:
        try:
            groups = valid_groups(parse_block(ask(out, caller, group_prompt(lines, context, secs), "designs", "0-group",
                                                  fresh), "SCENES").get("scenes") or [], lines, secs)
        except Exception as e:  # noqa: BLE001 — the cut falls back to the song's own sections, said
            (out / "0-group.fallback.txt").write_text(f"{type(e).__name__}: {e}\n")
            groups = groups_by_section(lines)
    doc = {"piece": {"title": plan.get("title") or (plan.get("song") or {}).get("title") or plan_path.parent.name},
           "song": plan.get("song"), "cast": wdoc.get("cast") or [], "world": wdoc.get("world") or [],
           "scenes": song_scenes(groups, lines)}
    brand = plan.get("brand") or json.loads(_read(run / "run.json") or "{}").get("brand") if run else plan.get("brand")
    shared = shared_values(run or plan_path.parent, ws, doc, brand or "")
    spoken_picks = _read(run / "director" / "picks.md") if run else ""
    if spoken_picks:
        shared["curation"] += ("\n\n**The spoken version of this ad was storyboarded like this — context only, "
                               "never a picture to copy:**\n\n" + spoken_picks.strip())
    picks = run_director(doc, doc["scenes"], out, shared, caller, per_scene, batch, workers, fresh, dry,
                         record="director/picks.json")
    if dry:
        return {}
    keep_copy.write_text(json.dumps(base, indent=1, ensure_ascii=False) + "\n")
    plan["scenes"] = [plan_scene(sc) for sc in doc["scenes"]]
    kept = sum(1 for p in picks.values() if p.get("kept"))
    plan["director"] = {"station": STATION, "moments": len(picks), "kept": kept, "record": "director/picks.json",
                        "before": keep_copy.name, "lines": len(lines)}
    plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    times_onto(plan_path)                   # the song's clock, when the song is in
    if run:                                 # the sung brief Produce and the hand-off pack read
        write_sung_brief(plan_path, run, sung_run_for(plan_path, ws), ws)
    (out / "picks.json").write_text(json.dumps({"schema": "director-picks/v1", "station": STATION,
                                                "plan": plan_path.name, "picks": picks}, indent=1, ensure_ascii=False))
    (out / "picks.md").write_text(picks_md(doc, picks))
    return picks


def _norm(s):
    return " ".join(re.findall(r"[a-z0-9']+", str(s or "").lower().replace("\u2019", "'")))


def lay_times(plan, timing):
    """The song's clock laid on a directed plan: each shot gets its line's `start` / `end`, each scene its `window`,
    matched line by line IN ORDER (a chorus sung twice is two lines, never the same one twice). A line the timing
    lists but did not hear takes the gap it sits in (the previous heard line's end to the next one's start) and is
    marked `timed: "window"`; a heard line is `timed: "heard"`. Returns the shots left without times."""
    rows = list((timing or {}).get("lines") or [])
    heard_at = [k for k, r in enumerate(rows) if r.get("start") is not None]

    def gap(k):
        a = max((rows[j]["end"] for j in heard_at if j < k), default=None)
        z = min((rows[j]["start"] for j in heard_at if j > k), default=None)
        return (a, z) if a is not None and z is not None and z > a else None

    i, missing = 0, []
    for sc in plan.get("scenes") or []:
        got = []
        for sh in sc.get("shots") or []:
            want = _norm((sh.get("lyrics") or [""])[0])
            j = next((k for k in range(i, len(rows)) if _norm(rows[k].get("line")) == want), None)
            span, how = None, None
            if j is not None:
                i = j + 1
                if rows[j].get("start") is not None:
                    span, how = (rows[j]["start"], rows[j]["end"]), "heard"
                elif gap(j):
                    span, how = gap(j), "window"
            if not span:
                for k in ("start", "end", "timed"):
                    sh.pop(k, None)
                missing.append(sh.get("line") or sh.get("id"))
                continue
            sh["start"], sh["end"], sh["timed"] = round(float(span[0]), 2), round(float(span[1]), 2), how
            got.append((sh["start"], sh["end"]))
        if got:
            sc["window"] = [min(a for a, _ in got), max(z for _, z in got)]
        else:
            sc.pop("window", None)
    return missing


def times_onto(plan_path):
    """Lay the newest song/timing.json beside the plan onto it (a song re-timed after it was directed). Returns the
    shots left without times, or None when there is no timing yet."""
    plan_path = Path(plan_path)
    tf = plan_path.parent / "song" / "timing.json"
    if not tf.is_file():
        return None
    plan = json.loads(plan_path.read_text())
    timing = json.loads(tf.read_text())
    missing = lay_times(plan, timing)
    plan.setdefault("director", {})["times"] = {
        "from": "song/timing.json", "at": timing.get("at"), "missing": missing,
        "windows": [sh.get("line") for sc in plan.get("scenes") or [] for sh in sc.get("shots") or []
                    if sh.get("timed") == "window"]}
    plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    return missing


# ---------- a directed sung plan as a sung stage-5 brief (what Produce and the hand-off pack read) ----------

SONG_KINDS = ("pre-chorus", "chorus", "bridge", "outro", "intro", "verse")


SECTION_ALIASES = {"mechanism": "unique-mechanism", "story": "identification", "results": "transformation"}


def doctrine_section(s, sections=SECTIONS_FALLBACK):
    """A scene's section as a doctrine id: an old or loose name mapped to its id, anything else to identification."""
    s = SECTION_ALIASES.get(str(s or ""), str(s or ""))
    return s if s in sections else ("identification" if "identification" in sections else sections[0])


def section_kind(name):
    """A song section's name as stage 5 spells it: intro · verse · pre-chorus · chorus · bridge · outro."""
    n = str(name or "").lower()
    return next((k for k in SONG_KINDS if k in n), "verse")


def _s(x):
    return str(x or "").strip()


def sung_brief(plan, wdoc, lines=None):
    """A directed sung plan in stage 5 v15's shape for a SUNG piece: every scene carries its `lyrics` (and an empty
    `voice`), its staging, its first frame, one shot and one beat per line (who · action · prop · where · face ·
    gestures from 5d), and the top-level `song` block holds one section per scene, in the order sung, its lines
    copied from that scene's lyrics. The cast, places, props, product lock and the piece come from the spoken brief
    of the same ad (`wdoc`); nothing is invented here."""
    lines = lines if lines is not None else plan_lines(plan)
    sec_of = {i: sec for i, _, sec in lines}
    world_ids = [w.get("id") for w in wdoc.get("world") or [] if w.get("id")]
    cast_ids = [c.get("id") for c in wdoc.get("cast") or [] if c.get("id")]
    style = next((_s((s.get("first_frame") or {}).get("style")) for s in wdoc.get("scenes") or []
                  if (s.get("first_frame") or {}).get("style")), "")
    refs_style = next((r for s in wdoc.get("scenes") or [] for r in (s.get("first_frame") or {}).get("refs") or []
                       if "style" in str(r).lower()), "")
    scenes, sections = [], []
    for n, ps in enumerate(plan.get("scenes") or [], 1):
        sid = f"S{n}"
        shots_in = ps.get("shots") or []
        whos = list(dict.fromkeys(_s(sh.get("who")) for sh in shots_in if _s(sh.get("who"))))
        wheres = [_s(sh.get("where")) for sh in shots_in if _s(sh.get("where")) in world_ids]
        setting = wheres[0] if wheres else (world_ids[0] if world_ids else "")
        props = list(dict.fromkeys(_s(sh.get("prop")) for sh in shots_in if _s(sh.get("prop"))))
        lead = whos[0] if whos else ""
        ff_action = _s((ps.get("first_frame") or {}).get("action")) or _s((shots_in[0] if shots_in else {}).get("action"))
        shots, beats = [], []
        for k, sh in enumerate(shots_in, 1):
            act = _s(sh.get("action"))
            shots.append({"id": f"{sid}.{k}", "start_picture": "first_frame", "copies": "", "angle": "",
                          "camera_move": "handheld", "face": _s(sh.get("face")) or "n/a: no face staged",
                          "emotion": "", "gestures": sh.get("gestures") or (["n/a: no gesture staged"]),
                          "action": act, "who": _s(sh.get("who")), "prop": _s(sh.get("prop")),
                          "where": _s(sh.get("where")), "line": sh.get("line"), "lyrics": sh.get("lyrics") or [],
                          "lines": [], "length": None, "ends_on": act, "hands_off": "cut" if k == len(shots_in) else "action",
                          **({"start": sh["start"], "end": sh["end"], "timed": sh.get("timed") or "heard",
                              "seconds": round(max(1.5, sh["end"] - sh["start"]), 2)}
                             if sh.get("start") is not None else {})})
            beats.append({"id": f"B{k}", "shot": f"{sid}.{k}", "do": one_action(_s(sh.get("do")) or act),
                          "who": _s(sh.get("who")),
                          "action": act, "prop": _s(sh.get("prop")), "where": _s(sh.get("where")),
                          "camera": "handheld", "over": (sh.get("lyrics") or [""])[0], "bracket": "sung"})
        win = ps.get("window")
        secs = round(max(3.0, min(120.0, win[1] - win[0])), 1) if win else None
        scenes.append({
            "id": sid, "kind": "broll", "opens": n == 1, "priority": 1, "section": doctrine_section(ps.get("section")),
            "technique": "sung line acted out as a silent shot", "delivery": {"humor": "unfilled", "style": "unfilled", "register": "unfilled",
                                          "pacing": "unfilled"},
            "emotion": "n/a: carried by the song", "outcome": _s(ps.get("title")), "setting_id": setting, "happens": _s(ps.get("happens")),
            "who": ", ".join(whos) or "nobody", "speaker": "", "looks": {}, "props": props, "to_camera": False,
            "voice": "", "lyrics": list(ps.get("lyrics") or []),
            "first_frame": {"subject": f"{lead}, {ff_action}".strip(", ") if lead else ff_action,
                            "composition": "n/a: framed at production from the scene's action",
                            "action": ff_action, "location": setting, "style": style,
                            "camera": "eye level, handheld", "lighting": "the place's own light",
                            "refs": [f"{w} cast sheet" for w in whos if w in cast_ids] + ([refs_style] if refs_style else [])},
            "shots": shots, "beats": beats,
            "last_frame": {"camera": "same", "change": _s(shots[-1]["action"]) if shots else ""},
            "on_screen": "nothing", "hold": "", "source": "none — script-backed", "take": "continuous",
            "title": _s(ps.get("title")), "lines_from": ps.get("lines_from") or [],
            **({"window": win, "seconds": secs} if win else {}),
            **({"director": ps["director"]} if ps.get("director") else {})})
        first_line = (ps.get("lines_from") or [None])[0]
        sections.append({"name": section_kind(sec_of.get(first_line)), "scene": sid,
                         "seconds": secs or round(max(3.0, 2.5 * len(ps.get("lyrics") or [])), 1),
                         "lines": list(ps.get("lyrics") or [])})
    song = dict(plan.get("song") or {})
    piece = dict(wdoc.get("piece") or {})
    piece["title"] = plan.get("title") or piece.get("title") or ""
    return {"lane": wdoc.get("lane") or "ai", "piece": piece, "edit": wdoc.get("edit") or {}, "roll_sheet": [],
            "layers": {}, "music": wdoc.get("music") or {}, "sfx": [], "hooks": [],
            "cast": wdoc.get("cast") or [], "world": wdoc.get("world") or [],
            "product_lock": wdoc.get("product_lock") or [], "props": wdoc.get("props") or [], "openings": [],
            "song": {"style_id": song.get("style_id") or "[UNFILLED]", "vocal": song.get("vocal"),
                     "bpm": song.get("bpm"), "sections": sections},
            "scenes": scenes}


def sung_brief_md(doc, plan_rel, timing_note):
    rows = [f"# {doc['piece'].get('title') or 'The song'} (sung)", "",
            "FORM: SUNG. Written by stage 5d from the directed song plan; every scene's `lyrics` is its script and "
            "every line is its own silent shot.", "",
            f"Plan: `{plan_rel}`. {timing_note}", "", "## THE SCENES", ""]
    for sc in doc["scenes"]:
        rows.append(f"**{sc['id']} · {sc.get('title')}** ({sc['section']}): {sc['happens'] or '(not staged)'}")
        for sh in sc["shots"]:
            rows.append(f"- {sh['id']} \"{(sh['lyrics'] or [''])[0]}\": {sh['who']} {sh['action'] or '(no shot)'}")
        rows.append("")
    return "\n".join(rows) + "\n```json\n" + json.dumps(doc, indent=1, ensure_ascii=False) + "\n```\n"


def write_sung_brief(plan_path, writing_run, out_run, ws=None):
    """The directed sung plan as `out_run/stages/5-brief.md` (a writing run of its own beside the spoken one), with a
    run.json naming the spoken run as its source — the brief Produce and the hand-off pack read unchanged.
    Returns (brief path, scene count, lines without a shot)."""
    plan_path, out_run = Path(plan_path), Path(out_run)
    plan = json.loads(plan_path.read_text())
    wrun = Path(writing_run) if writing_run else None
    wdoc = {}
    if wrun:
        for f in (wrun / "stages" / "5-brief.before-director.md", brief_path(wrun)):
            if f.is_file():
                wdoc = brief_doc(f.read_text())
                break
    doc = sung_brief(plan, wdoc)
    (out_run / "stages").mkdir(parents=True, exist_ok=True)
    ws = Path(ws) if ws else workspace()
    try:
        plan_rel = str(plan_path.resolve().relative_to(ws.resolve()))
    except ValueError:
        plan_rel = plan_path.name
    times = (plan.get("director") or {}).get("times") or {}
    note = (f"Times from song/timing.json ({times.get('at') or 'undated'}); "
            f"{len(times.get('windows') or [])} line(s) not heard and timed by the gap they sit in "
            f"({', '.join(times.get('windows') or []) or 'none'}); {len(times.get('missing') or [])} without times."
            if times else "No song timing laid on yet.")
    bp = out_run / "stages" / "5-brief.md"
    bp.write_text(sung_brief_md(doc, plan_rel, note))
    wst = json.loads(_read(wrun / "run.json") or "{}") if wrun else {}
    rj = out_run / "run.json"
    st = json.loads(_read(rj) or "{}")
    try:
        src = str(wrun.resolve().relative_to(ws.resolve())) if wrun else None
    except ValueError:
        src = wrun.name if wrun else None
    st.update({"slug": out_run.name, "label": out_run.name, "brand": plan.get("brand") or wst.get("brand"),
               "product": wst.get("product"), "style_id": wst.get("style_id"), "format_id": wst.get("format_id"),
               "production_route": "ai", "writing": "v2", "form": "sung", "source_run": src,
               "forked_from": wrun.name if wrun else None, "song_plan": plan_rel})
    st.setdefault("opened", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    stages = st.setdefault("stages", {})
    stages["stage5"] = {"status": "done", "name": "Brief", "out": "stages/5-brief.md",
                        "engine": "5d director (sung plan)", "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rj.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
    return bp, len(doc["scenes"]), unshot_lines(plan)


def sung_run_for(plan_path, ws):
    """The writing run a sung plan's brief goes in: runs/video-teardown/_work/<the plan's folder name>."""
    return Path(ws) / "runs" / "video-teardown" / "_work" / Path(plan_path).resolve().parent.name


def unshot_lines(plan):
    """The sung lines of a directed plan that carry no shot action."""
    return [(sh.get("line"), (sh.get("lyrics") or [""])[0]) for sc in plan.get("scenes") or []
            for sh in sc.get("shots") or [] if not sh.get("action")]


def resolve(arg, ws):
    p = Path(arg)
    if p.is_dir():
        return p
    q = ws / "runs" / "video-teardown" / "_work" / arg
    if q.is_dir():
        return q
    raise SystemExit(f"no teardown run at {arg}")


def main(argv=None):
    a = argparse.ArgumentParser(description="Stage 5d: the director picks one visual idea per scene.")
    a.add_argument("run", help="a teardown run folder or label; with --plan, the spoken writing run of the same ad "
                               "(context), or '-' for none")
    a.add_argument("--plan", default="", help="a sung plan.json (a song ad): direct it instead of the brief")
    a.add_argument("--times", action="store_true", help="with --plan: only lay the newest song/timing.json on it")
    a.add_argument("--brief-only", action="store_true", help="with --plan: only (re)write the sung brief from it")
    a.add_argument("--scenes", default="")
    a.add_argument("--per-scene", type=int, default=3)
    a.add_argument("--batch", type=int, default=6)
    a.add_argument("--dry", action="store_true")
    a.add_argument("--fresh", action="store_true", help="ask again even where a reply for the same prompt is on file")
    o = a.parse_args(argv)
    ws = workspace()
    if o.plan and (o.times or o.brief_only):
        if o.times:
            miss = times_onto(o.plan)
            print("no song/timing.json beside the plan yet" if miss is None else
                  f"times laid on {o.plan}; {len(miss)} shot(s) without a heard line: {', '.join(map(str, miss)) or 'none'}")
        if o.run != "-":
            bp, n, miss = write_sung_brief(o.plan, resolve(o.run, ws), sung_run_for(o.plan, ws), ws)
            print(f"sung brief: {bp} · {n} scenes · {len(miss)} line(s) with no shot")
        return
    if o.plan:
        run = None if o.run == "-" else resolve(o.run, ws)
        picks = direct_plan(o.plan, run, per_scene=o.per_scene, batch=o.batch, dry=o.dry, ws=ws, fresh=o.fresh)
        if not o.dry:
            kept = sum(1 for p in picks.values() if p.get("kept"))
            miss = unshot_lines(json.loads(Path(o.plan).read_text()))
            print(f"5d director: {kept}/{len(picks)} moments staged, {len(miss)} line(s) with no shot → {o.plan}")
        return
    run = resolve(o.run, ws)
    picks = direct(run, scenes=[s for s in o.scenes.split(",") if s] or None, per_scene=o.per_scene,
                   batch=o.batch, dry=o.dry, ws=ws, fresh=o.fresh)
    if o.dry:
        print(f"prompts written → {run / 'director'}")
        return
    kept = sum(1 for p in picks.values() if p.get("kept"))
    print(f"5d director: {kept}/{len(picks)} scenes restaged → {run / 'director' / 'picks.md'}")


if __name__ == "__main__":
    main()
