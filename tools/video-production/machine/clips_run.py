"""THE CLIPS ROUTE — every clip is Seedance 2.5 (the owner, 2026-10-23; the Omni route was removed 2026-10-26).

Which model does what: components/generative-model-house/MODEL-HOUSE.md (read by machine/house.py). Every clip
animates an approved GPT Image 2.5 picture already in media/ (step 4.4) at `direct.clip_route.resolution` (480p, upscaled on this Mac), 9:16,
whole seconds a call, through machine/seedance.py: a talking clip sends the approved start picture AND the line's own
locked ElevenLabs read in ONE call, so nothing is re-voiced or fitted afterwards; a silent clip goes from the picture
(or picture + the swipe's blurred motion clip). The prompt is machine/seedance_prompt.py's, written the way BytePlus
documents the model (SEEDANCE-INPUTS.md).

  * talking / staged sections: the approved picture is Image 1, the line's locked read is Audio 1;
  * sections that copy the swipe's movement: the picture + up to 3 pieces of <=3 s of the swipe's own footage for that
    span, ALWAYS heavily blurred (scale 720, gblur sigma 30) and bound in the prompt as motion-only references;
  * a line is ON camera only when its speaker's face is in the clip's picture: the brief's `to_camera`, corrected per
    section (or per clip) by <run>/clips/on-camera.json. Off-camera lines are NOT in the clip: the person on camera
    listens, silent, and the line is read by that person's cloned voice and laid at its storyboard time;
  * each storyboard clip is its own window, split at line boundaries into calls, never padded (spare seconds make the
    model improvise); NO HAND-OFFS FOR PEOPLE (providers.json ruling_2026_10_03_no_handoffs): a person on screen starts
    EVERY call from the section's approved picture, never from a call's last frame; cards, plates and the endcard get
    no clip; a reused section is not made twice;
  * after each call (live, `run`): line check -> face lock -> clip_qc.py -> the clip judge; ONE take, another only when
    it fails, three at most (VIDEO-RULINGS V34); only the kept take is upscaled, on this Mac. Non-word sounds (mm-hmm,
    uh-huh) are never said in a clip: the person nods, lips closed. Who says a line is the brief's `speaker`.

Every price and fixed sentence comes from providers.json `direct.clip_route`; voice ids from each person's casting
voice.json. This file names no brand or person. A run keeps its clip results at `clips/ledger.json` and its per-call
files at `clips/calls/<call>/` (a run made before 2026-10-26 keeps the old names on disk; clip_kit finds both).

    python3 machine/clips_run.py plan <run> [--only G05,G12]   (= run.py start ... --clips)
    python3 machine/clips_run.py refs <run>                    local ffmpeg only: the blurred refs
    python3 machine/clips_run.py run  <run> [--only ...] [--parallel 6] --yes   LIVE, spends money
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import difflib
import importlib.util
import json
import math
import mimetypes
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_oc_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cp = _load("clips_plan")
platform = cp.platform
sbp = cp.sbp


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def route_cfg(reg: dict | None = None, fmt: str | None = None) -> dict:
    """The route's settings; a format with its own row under `by_format` (a song ad: every section a clip) is laid
    over them. The clip model is the house's Seedance (VIDEO-RULINGS V2); nothing here names another."""
    reg = reg if reg is not None else platform.registry()
    c = ((reg.get("direct") or {}).get("clip_route"))
    if not c:
        raise SystemExit("providers.json has no direct.clip_route — the clips route reads every price and fixed "
                         "sentence from there")
    over = ((c.get("by_format") or {}).get(fmt) or {}) if fmt else {}
    if over:
        c = {**c, **{k: v for k, v in over.items() if k != "ruled"}, "format": fmt}
    H = _load("house")
    sd = _load("seedance")
    c = {**c, "models": {"image-to-video": sd.MOTION, "reference-to-video": sd.TALK},
         "tts": {**(c.get("tts") or {}), "model_id": H.voice_model()},
         "engines": {"seedance": H.clip("seedance")}}
    return c


def format_of(run: Path, plan_doc: dict | None = None) -> str | None:
    """The run's format: its plan's `format`, else run.json's."""
    return (plan_doc or {}).get("format") or (_read(Path(run) / "run.json", {}) or {}).get("format")


def style_line(run: Path, plan_doc: dict | None = None) -> str:
    """The run's style lock (THE-CHAIN.md "The swipe's style is read at 1"): the style row's
    STYLE LOCK line (make_character.style_lock) and its motion language, read from the run's
    style_id (run.json, else the plan's piece). No style id: the piece's own style sentence."""
    plan_doc = plan_doc or {}
    piece = plan_doc.get("piece") or {}
    sid = (_read(Path(run) / "run.json", {}) or {}).get("style_id") or piece.get("style_id") or plan_doc.get("style_id")
    if sid:
        mc = _load("make_character")
        lock = mc.style_lock(sid)
        if lock:
            row = next((r for r in (_read(mc.STYLES, {}) or {}).get("styles") or [] if r.get("id") == sid), {})
            motion = str(row.get("motion") or "").strip().rstrip(".")
            return lock + (f" Motion: {motion}." if motion else "")
    return str(piece.get("style") or "")


# ------------------------------------------------------------ people and voices

# Framing words only: the approved picture carries the framing. A real camera MOVE (push-in, zoom, pan) is not
# framing and goes through — the shot's `camera_move` slot says it plainly (VIDEO-RULINGS V8/V10, P2 2026-10-21).
COMPOSITION = re.compile(
    r"close-?up|medium (close|shot)|wide shot|two-shot|\bframing\b|\bframed\b|centred|centered|\bcrop|"
    r"\d+\s*[–-]\s*\d+\s*%|in frame|out of frame|frame edge|edge of the frame|head and shoulders", re.I)
# the style lock never carries a camera move either: the move is the shot's own (its camera_move slot)
STYLE_CAMERA = re.compile(COMPOSITION.pattern + r"|zoom|push-?ins?", re.I)


def _gender(describe: str) -> str:
    d = f" {describe.lower()} "
    if re.search(r"\b(woman|female|she|her)\b", d):
        return "f"
    if re.search(r"\b(man|male|he|his|clean-shaven|beard|moustache)\b", d):
        return "m"
    return "x"


def people_of(run: Path) -> tuple[dict, list[str]]:
    """{ID: {noun, pron, poss, voice_id, model_id, settings, voice_file}} from the
    run's elements.json; each voice from that person's casting voice.json (the
    cloned voice — never the stale id elements.json may still carry)."""
    els = _read(Path(run) / "elements.json", {}) or {}
    out, problems = {}, []
    persons = [i for i in els.get("items") or [] if i.get("kind") == "person"]
    for it in persons:
        pid, desc = it["id"], str(it.get("describe") or "")
        g = _gender(desc)
        role = "doctor" if re.search(r"doctor|expert|surgeon|dermatolog|clinician", pid + " " + desc, re.I) else None
        noun = role or {"f": "woman", "m": "man"}.get(g, "person")
        folder = it.get("folder") or ""
        vf = (WORKSPACE / folder / "voice.json") if folder else None
        v = _read(vf, None) if vf else None
        if not v or not v.get("voice_id"):
            # only a person who SPEAKS needs a voice (2026-10-07: LeBron's staff member
            # and press pack never say a word and held the clips); the per-line
            # checks below still stop any line whose speaker has none
            if it.get("speaks"):
                problems.append(f"{pid}: no cloned voice — {vf or 'no casting folder in elements.json'} has no voice_id")
            v = {}
        ident = identity_words(WORKSPACE / folder) if folder else ""
        lm = life_marks(WORKSPACE / folder) if folder else {}
        out[pid] = {"noun": noun, "identity": ident, "marks": lm.get("marks", ""), "gestures": lm.get("gestures", ""),
                    "pron": {"f": "she", "m": "he"}.get(g, "they"),
                    "poss": {"f": "her", "m": "his"}.get(g, "their"),
                    "voice_id": v.get("voice_id"), "model_id": v.get("model_id"),
                    "settings": v.get("settings") or {}, "voice_file": str(vf) if vf else None,
                    "speaks": list(it.get("speaks") or [])}
    # two people with the same noun in one ad: the first keeps it, the rest are told apart by role
    seen = {}
    for pid, p in out.items():
        if p["noun"] in seen and p["noun"] != "doctor":
            p["noun"] = f"other {p['noun']}"
        seen.setdefault(p["noun"], pid)
    return out, problems


def identity_words(folder: Path) -> str:
    """The parts of a person's casting description that make them THEM on camera — eye colour,
    marks, spots, freckles, scars, tattoos, hair — so every clip prompt states them (2026-10-03:
    at 360p with only a picture, the model turned Creator-A's blue-grey eyes brown and moved her spots)."""
    spec = _read(Path(folder) / "spec.json", {}) or {}
    text = " ".join(str(v) for v in _walk_strings(spec))
    keep = []
    for part in re.split(r"(?<=[.;])\s+", text):
        if re.search(r"\beyes?\b|spot|freckl|mole|scar|tattoo|birthmark|\bbob\b|hair", part, re.I) and len(part) < 700:
            t = part.strip().rstrip(";.")
            if t and t not in keep:
                keep.append(t)
    return "; ".join(keep[:6])


def life_marks(folder: Path) -> dict:
    """{"marks", "gestures"} from the person's character.md "Life marks and gestures" section (VIDEO-SPICE layers
    2–3; P36, 2026-10-21) — the small real things that make them read as a person. {} when the file has none."""
    try:
        text = (Path(folder) / "character.md").read_text()
    except OSError:
        return {}
    m = re.search(r"^##\s+Life marks[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return {}
    out = {}
    for key, pat in (("marks", r"life marks"), ("gestures", r"gestures")):
        hit = re.search(rf"^\s*-\s*\*\*{pat}:?\*\*:?\s*(.+)$", m.group(1), re.I | re.M)
        if hit:
            out[key] = hit.group(1).strip().rstrip(".")
    return out


REALISM = HERE.parent / "spice" / "realism-index.json"
SPICE = HERE.parent / "VIDEO-SPICE.md"
# the swipe's kind of camera → the realism index's format, when the brief names none (P37)
REALISM_FORMAT = {"selfie": "selfie-talk", "mirror": "grwm-mirror", "held": "street-interview", "still": "propped-phone-talk"}
CLIP_FAMILIES = ("camera-hand", "body", "face")
PICTURE_FAMILIES = ("skin", "place", "face", "finish")
SENSE_FAMILY = "sense"


def realism_format_of(scene: dict | None, camera: str | None = None) -> str | None:
    """THE REALISM FORMAT A SHOT IS (verify 2026-10-21 row 19, VIDEO-RULINGS V9): the brief's own `realism_format`,
    else read off the scene — the phone looking down at hands (pov-hands), walking (walk-and-talk), making or showing
    something at a counter (counter-demo), seated on a stand (sit-down-interview) — else the swipe's kind of camera
    (selfie-talk · grwm-mirror · street-interview · propped-phone-talk). Every format of the realism index can be
    reached, never only four; None only when nothing says."""
    s = shot_of(scene)
    if s.get("realism_format"):
        return str(s["realism_format"])
    ff = s.get("first_frame") or next((f for f in s.get("frames") or [] if f.get("role") in (None, "first")), {}) or {}
    text = " ".join(str(x or "") for x in (s.get("who"), s.get("happens"), s.get("angle"), ff.get("subject"),
                                            ff.get("composition"), ff.get("camera"), ff.get("location"), ff.get("action"),
                                            ff.get("viewpoint"))).lower()
    if ff.get("viewpoint") or re.search(r"\bpov\b|point of view|looking down at (?:her|his|their) (?:own )?hands", text) \
            or str(s.get("who") or "").strip().lower().startswith("hands"):
        return "pov-hands"
    if re.search(r"\bwalk(?:s|ing)?\b", text):
        return "walk-and-talk"
    if re.search(r"\b(?:counter|countertop|worktop|table|stove|cutting board|chopping board)\b", text) and \
            re.search(r"\b(?:mak|mix|grind|pour|stir|whisk|squeez|scoop|spread|show|demo|cut|chop|press|blend)\w*", text):
        return "counter-demo"
    if re.search(r"\b(?:seated|sitting|sits|sat)\b", text) and re.search(r"\b(?:stand|tripod|propped|interview)\b", text):
        return "sit-down-interview"
    return REALISM_FORMAT.get(camera or "") if camera else None


def spice_layers(level) -> set | None:
    """The VIDEO SPICE layers a level turns on, read from VIDEO-SPICE.md's own Levels table (verify 2026-10-21 row 19,
    VIDEO-RULINGS V9) — level 1: 1, 5, 6; level 2: + 3; level 3: + 2, 4, 7. None when the piece names no level
    (every layer stays on, as before)."""
    try:
        n = int(str(level).strip()[:1])
    except (TypeError, ValueError):
        return None
    try:
        text = SPICE.read_text()
    except OSError:
        raise SystemExit(f"the piece asks for VIDEO SPICE level {n} and {SPICE} cannot be read")
    m = re.search(r"^##\s+Levels.*?\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    on = set()
    for row in (m.group(1) if m else "").splitlines():
        hit = re.match(r"^\|\s*(\d)\b[^|]*\|([^|]*)\|", row)
        if not hit or int(hit.group(1)) > n:
            continue
        said = re.split(r":", hit.group(2), 1)[0]
        on |= {int(x) for x in re.findall(r"\d", said)}
    if not on:
        raise SystemExit(f"VIDEO-SPICE.md has no Levels row for level {n}")
    return on


def spice_level_of(run: Path) -> int | None:
    """The piece's `spice_level` (brief v3, the spice sheet's level: 1 · 2 · 3), from plan.json's piece, else None."""
    piece = (_read(Path(run) / "plan.json", {}) or {}).get("piece") or {}
    try:
        return int(str(piece.get("spice_level")).strip()[:1]) if piece.get("spice_level") not in (None, "") else None
    except ValueError:
        return None


def realism_rows(fmt: str | None, families=CLIP_FAMILIES, ids=None, level: int = 2, index: dict | None = None) -> list[dict]:
    """The production rows of the realism index (spice/realism-index.json, VIDEO-RULINGS V9; P37) that this shot
    carries: the brief's own picks (`realism` ids) when it has them, else every row of these families for the
    format, up to `level`. Rows marked deprecated never come back."""
    idx = index if index is not None else (_read(REALISM, {}) or {})
    out = []
    for r in idx.get("rows") or []:
        if r.get("status") == "deprecated" or not r.get("prompt"):
            continue
        if "production" not in [r.get("stage")] + list(r.get("also") or []):
            continue
        if ids:
            if r.get("id") in ids:
                out.append(r)
            continue
        # a shot with no format gets NO format rows — never the rows of every format (verify 2026-10-21 row 19)
        if r.get("family") in families and fmt and fmt in (r.get("formats") or []) and int(r.get("level") or 1) <= level:
            out.append(r)
    return out


def _walk_strings(o):
    if isinstance(o, dict):
        for k in ("who", "description", "describe", "face", "look", "prompt", "person"):
            if isinstance(o.get(k), str):
                yield o[k]
        for v in o.values():
            if isinstance(v, (dict, list)):
                yield from _walk_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_strings(v)


# Sounds that are not words — "mm-hmm", "uh-huh", "hmm", "um". The model mouths them badly (the owner, 3 Oct:
# "the umms … the hmm … don't come out clean"), so the person on screen only nods, lips closed, and the
# sound is made on its own track (the cloned voice) and laid in at the edit.
NONWORD = re.compile(r"^(?:m+-?h+m+|m+h+m+|uh-?huh|u+h+-?h+u+h+|h+m+|m{2,}|u+m+|u+h+|e+r+m+|a+h+)$", re.I)


def split_sound(text: str) -> tuple[str, str]:
    """(words to say on camera, the sound at the start/end that goes on its own track)."""
    toks = text.split()
    bare = lambda t: re.sub(r"[^\w-]", "", t)
    a, z = 0, len(toks)
    while a < z and NONWORD.match(bare(toks[a]) or "x"):
        a += 1
    while z > a and NONWORD.match(bare(toks[z - 1]) or "x"):
        z -= 1
    sound = " ".join(toks[:a] + toks[z:]).strip()
    return " ".join(toks[a:z]).strip(), sound


def with_speakers(run: Path, sb: dict, scenes: list[dict]) -> list[dict]:
    """The run's scenes, each carrying the brief's `speaker` (who says the line in the swipe's
    transcript). The run's plan.json drops that field; the brief keeps it."""
    brief = {}
    for f in [run / "brief.md", run / str(sb.get("brief") or "_none_")]:
        try:
            found = re.findall(r"```json\s*\n(.*?)\n```", f.read_text(), re.S)
            for blk in reversed(found):
                sc = json.loads(blk).get("scenes")
                if sc:
                    brief = {x.get("id"): x for x in sc}
                    break
        except (OSError, ValueError):
            continue
        if brief:
            break
    out = []
    for sc in scenes:
        b = brief.get(sc.get("id")) or {}
        # the speaker, and the shooting script's fields plan.json may not carry (shots, beats, the shot contract —
        # verify 2026-10-21 rows 4 and 19): the brief's, wherever the scene has none of its own
        carry = {k: b[k] for k in ("speaker", "shots", "beats", "first_frame") + SHOT_FIELDS
                 if b.get(k) not in (None, "", [], {}) and sc.get(k) in (None, "", [], {})}
        out.append({**sc, **carry} if carry else sc)
    return out


def speaker_of(scene: dict, people: dict) -> str | None:
    """Who SAYS the line: the brief's own `speaker` (it matches the swipe's transcript) — and only
    that. Never whose hands or face are in the shot (`who`), never the voice map (`speaks`): 3 Oct,
    going by `who` put "A little glycolic peel." in Creator-A's mouth because the shot is CREATOR-A's hands
    (in the swipe it is the doctor talking over the cut), and the voice map gave Creator-A's "Why?" to
    Expert 2. No `speaker`, or one not in the cast → None, and the plan refuses the line."""
    said_by = str(scene.get("speaker") or "").strip()
    return said_by if said_by in people else None


def desc(pid: str | None, people: dict, cap: bool = False) -> str:
    d = f"the {people[pid]['noun']}" if pid in people else "someone"
    return d[:1].upper() + d[1:] if cap else d


def swap_names(text: str, people: dict) -> str:
    t = " ".join(str(text or "").split())
    for pid in sorted(people, key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(pid)}'s\b", f"the {people[pid]['noun']}'s", t)
        t = re.sub(rf"\b{re.escape(pid)}\b", f"the {people[pid]['noun']}", t)
    return t


FRAMING_WORDS = re.compile(
    r"\b(?:an?\s+)?(?:extreme\s+|tight\s+|slow\s+)?(?:close-?up|medium (?:close-?up|shot)|wide shot|two-shot)(?:\s+shot)?"
    r"(?:\s+(?:of|on))?\s*|\b(?:centred|centered|in frame|out of frame)\b\s*|\d+\s*[–-]\s*\d+\s*%\s*(?:width|height)?",
    re.I)


def no_composition(text: str) -> str:
    """The framing words out — the approved picture carries the composition (2026-10-02: 'close-up' made the
    model zoom) — and the DEPICTION kept: a clause that names framing keeps every other word it says, so "an extreme
    close-up of a grapefruit-sized whitehead oozing yellow" still says the whitehead, its size, colour and what it
    does (P59, VIDEO-RULINGS V24: hyper-specific depictions pass through untrimmed). A clause that is framing and
    nothing else goes."""
    parts = re.split(r"(?<=[.;])\s+|,\s+", text or "")
    out = []
    for p in parts:
        p = p.strip().rstrip(".;")
        if not p:
            continue
        if COMPOSITION.search(p):
            p = " ".join(FRAMING_WORDS.sub(" ", p).split()).strip(" ,;")
            if len(p.split()) < 3 or COMPOSITION.search(p):
                continue
        out.append(p)
    return ", ".join(out).strip()


def style_clean(text: str) -> str:
    """The style lock with any framing clause dropped (the picture carries the framing), its
    sentences kept as sentences."""
    out = []
    for sent in re.split(r"(?<=[.;])\s+", (text or "").strip()):
        end = sent[-1] if sent[-1:] in ".;" else "."
        parts = [p for p in re.split(r",\s+", sent.rstrip(".;")) if p.strip() and not STYLE_CAMERA.search(p)]
        if parts:
            out.append(", ".join(parts) + end)
    return " ".join(out).rstrip(";") .rstrip() if out else ""


# ------------------------------------------------------------ on camera or off

def overrides_of(run: Path) -> dict:
    """<run>/clips/on-camera.json — {section or clip id: {"on_camera": [person],
    "off_camera": [person], "why": ...}}: who is (or is not) visibly in the
    picture, where the brief's to_camera is wrong for that picture."""
    return _read(Path(run) / "clips" / "on-camera.json", {}) or {}


def on_camera(scene: dict, speaker: str | None, gid: str, clip_ids: list[str], ov: dict) -> bool:
    for key in list(clip_ids) + [gid]:                       # the most specific entry wins
        o = ov.get(key) or {}
        if speaker and speaker in (o.get("on_camera") or []):
            return True
        if speaker and speaker in (o.get("off_camera") or []):
            return False
    return bool(scene.get("to_camera"))


# ------------------------------------------------------------ the clock and the calls

def sentences(text: str) -> list[str]:
    out = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]
    return out or [text.strip()]


def pieces_of(line: dict, level: str = "sentence") -> list[dict]:
    """A line as its sentences (or, at level "comma", its clauses), the line's
    time shared by word count — the places a call may be cut inside a line."""
    bits = sentences(line["text"])
    if level == "comma":
        bits = [p.strip() for b in bits for p in re.split(r"(?<=,)\s+", b) if p.strip()]
    words = sum(len(b.split()) for b in bits) or 1
    per = (line["z"] - line["a"]) / words
    out, t = [], line["a"]
    for n, b in enumerate(bits):
        z = line["z"] if n == len(bits) - 1 else t + len(b.split()) * per
        out.append({**line, "text": b, "a": round(t, 3), "z": round(z, 3), "line_start": n == 0,
                    "line_a": line["a"], "line_z": line["z"], "line_text": line["text"]})
        t = z
    return out


def _cut_plan(cands: list[tuple[float, bool]], t0: float, t1: float, max_s: float, lo: float):
    """The cut points that make the fewest calls ≤ max_s; then the least time under
    the shortest call (a short call is padded and the model improvises); then the
    fewest cuts inside a line; then the fewest billed seconds. None if impossible."""
    pts = [(t0, True)] + cands + [(t1, True)]
    best = {0: ((0, 0.0, 0, 0), None)}
    for i in range(1, len(pts)):
        for j in range(i):
            if j not in best:
                continue
            ln = pts[i][0] - pts[j][0]
            if ln > max_s + 1e-6 or ln <= 0:
                continue
            c = best[j][0]
            cost = (c[0] + 1, round(c[1] + max(0.0, lo - ln), 3), c[2] + (0 if pts[i][1] or i == len(pts) - 1 else 1),
                    c[3] + max(int(lo), math.ceil(round(ln, 2) - 1e-6)))
            if i not in best or cost < best[i][0]:
                best[i] = (cost, j)
    last = len(pts) - 1
    if last not in best:
        return None
    edges, i = [], last
    while i is not None:
        edges.append(pts[i][0]); i = best[i][1]
    return sorted(edges)


def split_calls(lines: list[dict], t0: float, t1: float, max_s: float, lo: float = 3.0) -> list[tuple[float, float, list[dict]]]:
    """[(from, to, lines)] — every call ≤ max_s, cut where a line starts, or where
    a sentence starts inside a long line (then a clause); never mid-word, never
    padded. A line spread over calls carries `part` "k/n" and only its own words."""
    if t1 - t0 < 0.05:                               # a section with no length on the clock makes no call (2026-10-09)
        return []
    edges, ps = None, []
    for level in ("sentence", "comma"):
        ps = [p for l in lines for p in pieces_of(l, level)]
        cand = {}
        for p in ps:
            if t0 + 0.01 < p["a"] < t1 - 0.01:
                cand[round(p["a"], 3)] = cand.get(round(p["a"], 3), False) or p["line_start"]
        edges = _cut_plan(sorted(cand.items()), t0, t1, max_s, lo)
        if edges:
            break
    if not edges:                                    # a silent stretch with nowhere to cut: even parts
        n = math.ceil((t1 - t0) / max_s - 1e-9)
        edges = [t0 + (t1 - t0) * k / n for k in range(n + 1)]
    spans = list(zip(edges, edges[1:]))
    owner = {}                                       # each piece belongs to the call its start is in
    for p in ps:
        k = next((i for i, (a, z) in enumerate(spans) if a - 0.01 <= max(p["a"], t0) < z - 0.01), None)
        owner.setdefault((p["scene"], p["line_a"]), set())
        if k is not None:
            owner[(p["scene"], p["line_a"])].add(k)
    calls = []
    for k, (a, z) in enumerate(spans):
        got = {}
        for p in ps:
            if not (p["z"] > a + 0.01 and p["a"] < z - 0.01):
                continue
            mine = next((i for i, (x, y) in enumerate(spans) if x - 0.01 <= max(p["a"], t0) < y - 0.01), k)
            if mine != k:
                continue
            g = got.setdefault((p["scene"], p["line_a"]), {**{x: p[x] for x in p if x not in
                                                            ("text", "a", "z", "line_start", "line_a", "line_z", "line_text")},
                                                         "text": [], "a": p["a"], "z": p["z"]})
            g["text"].append(p["text"]); g["z"] = p["z"]
        ls = []
        for key, g in got.items():
            g["text"] = " ".join(g["text"])
            parts = sorted(owner.get(key) or [])
            if len(parts) > 1:
                g["part"] = f"{parts.index(k) + 1}/{len(parts)}"
            ls.append(g)
        ls.sort(key=lambda x: x["a"])
        calls.append((round(a, 2), round(z, 2), ls))
    return calls


TALK_ROOM = 1.15   # a talking take is this much longer than its read (+0.6 s): the model's own pauses between lines


def billed(seconds: float, span: list) -> int:
    """Whole seconds, the least that holds the window — never padded to the top."""
    lo, hi = int(span[0]), int(span[1])
    return int(min(hi, max(lo, math.ceil(round(seconds, 2) - 1e-6))))


# ------------------------------------------------------------ the blurred swipe pieces

def ref_pieces(wins: list[tuple[str, float, float]], shots: dict, a: float, b: float, keep: set | None,
               refs: dict) -> list[dict]:
    """Up to refs.max_clips pieces of ≤ refs.max_seconds of the swipe's own shot
    files for the call's window [a, b] on the section clock. Our clock maps onto
    each shot file proportionally (the storyboard stretched the swipe)."""
    mx, cap, mn = float(refs["max_seconds"]), int(refs["max_clips"]), float(refs.get("min_seconds", 0.5))
    segs = []
    for k, x, y in wins:
        if keep is not None and k not in keep:
            continue
        lo, hi = max(a, x), min(b, y)
        if hi - lo < 0.05:
            continue
        sh = shots.get(k) or {}
        file_s = float(sh.get("end", 0) - sh.get("start", 0)) or (y - x)
        scale = file_s / (y - x) if y > x else 1.0
        f0, f1 = (lo - x) * scale, (hi - x) * scale
        t = f0
        while f1 - t > 0.05:
            s = min(mx, f1 - t)
            segs.append({"shot": k, "from": round(t, 2), "seconds": round(s, 2), "clip": sh.get("clip") or f"{k}.mp4"})
            t += s
    good = [s for s in segs if s["seconds"] >= mn] or segs[:1]
    if len(good) > cap:                                      # spread across the window: first, middle, last
        idx = sorted({round(i * (len(good) - 1) / (cap - 1)) for i in range(cap)}) if cap > 1 else [0]
        good = [good[i] for i in idx]
    return good


# ------------------------------------------------------------ the prompt

def camera_kind(shots: list[dict], scene: dict | None) -> str:
    """selfie · mirror · held · still — from the swipe's capture (or the brief's
    camera words where the section is not in the swipe). Only the KIND of
    camera is kept: its distance and framing stay in the picture."""
    if shots:
        held = " ".join(str((s.get("camera") or {}).get("held", "")) for s in shots).lower()
        types = " ".join(str(s.get("type", "")) for s in shots).lower()
        moves = " ".join(str((s.get("camera") or {}).get("move", "")) for s in shots).lower()
        if "arm's length" in held or "selfie" in types:
            return "selfie"
        if "someone" in held or "handheld" in held or "drift" in moves:
            return "held"
        return "still"
    cam = ""
    for f in (scene or {}).get("frames") or []:
        if f.get("role") == "first":
            cam = str(f.get("camera") or "").lower()
    if "mirror" in cam and ("selfie" in cam or "handheld" in cam):
        return "mirror"
    if "selfie" in cam or "arm's length" in cam:
        return "selfie"
    if "handheld" in cam or "drift" in cam:
        return "held"
    return "still"


def _fill(t: str, **kw) -> str:
    for k, v in kw.items():
        t = t.replace("{" + k + "}", v)
    return t


def tone_of(scene: dict) -> str:
    parts = [p.strip() for p in str(scene.get("delivery") or "").split("·")]
    skip = {"", "none", "unfilled", "list-stack", "interview-consult"}
    for p in parts[0:1]:
        if p.lower() not in skip:
            return p.lower()
    return ""



def clip_people(section_people, scene_ids, by_id, lead=None):
    """The people the brief puts in this clip's own scenes (their `looks`, or named in who/happens), plus the lead,
    in the section's order. With no lead known, the section's people unchanged (a listener the scene does not
    name may be in frame)."""
    if not lead:
        return list(section_people)
    names, said = set(), ""
    for sid in scene_ids:
        sc = by_id.get(sid) or {}
        names |= set((sc.get("looks") or {}).keys())
        said += " " + str(sc.get("who") or "") + " " + str(sc.get("happens") or "")
    said = said.lower()
    # the section's first person — the lead — is always in frame; others only when the scene names them
    own = [p for p in section_people if p == lead or str(lead).lower() in p.lower() or p in names
           or p.lower() in said or p.lower().replace("the ", "", 1) in said]
    return own or list(section_people)


def _words_in(cue, text):
    """Do the cue's words appear, in order, in this part's text?"""
    w = lambda t: re.findall(r"[a-z0-9']+", str(t).lower())
    c, t = " ".join(w(cue)), " ".join(w(text))
    return bool(c) and c in t

# A scene whose picture shows the skin AFTER the routine (2026-10-09, Grandma TV-shopping S8: the clip
# prompt still described her face spots, so the model pushed in and painted a dark patch back onto the cheek
# the scene exists to show clear). The picture's own words in the brief decide — never a guess.
EVEN_SKIN = re.compile(r"\bno (?:dark |age[- ])?spots\b|even where the (?:dark )?spots were|spots (?:are )?gone|"
                       r"weeks into the|clear where the (?:dark )?spots were", re.I)
MARK_PART = re.compile(r"\b(?:spot|spots|patch|patches|blemish|marks?)\b", re.I)


def scene_even(scene: dict) -> bool:
    """Does this scene's first picture show the skin after the routine (the spots gone)?"""
    fr = (scene.get("frames") or [{}])[0] if isinstance(scene.get("frames"), list) else {}
    text = " ".join(str(x) for x in [fr.get("subject"), *(fr.get("refs") or [])] if x)
    return bool(EVEN_SKIN.search(text))


def identity_for(identity: str, even: bool, words: dict, poss: str = "their") -> str:
    """The identity words for this clip: in an after-the-routine scene the spots are left out and the
    even skin is said instead, so the prompt never asks for marks the picture no longer has."""
    if not even or not identity:
        return identity
    keep = [p for p in identity.split("; ") if not MARK_PART.search(p)]
    said = _fill(words.get("identity_even", ""), poss=poss).strip()
    return "; ".join(keep).rstrip(" ;.") + ((". " + said.rstrip(".")) if said else "")


# ------------------------------------------------------------ the shot contract (CHANGES.md 2026-10-21)
# The fields the writing station's shooting script carries per shot and per line. A brief that predates them
# carries none, and every reader below falls back to what it did before.

SHOT_FIELDS = ("face", "emotion", "gestures", "angle", "camera_move", "hands_off", "ends_on", "start_picture",
               "delivery_tag", "emphasis", "length", "props", "lines")
CAMERA_MOVES = ("push-in", "pan", "tilt", "arc", "handheld", "hold")
AUDIO_TAG = re.compile(r"\[([^\]]{1,80})\]\s*")


def shot_of(scene: dict | None) -> dict:
    """The scene with its shot-contract fields: its own, else its first `shots[]` row's."""
    s = dict(scene or {})
    shots = s.get("shots")
    if isinstance(shots, list) and shots and isinstance(shots[0], dict):
        for k in SHOT_FIELDS:
            if not s.get(k) and shots[0].get(k):
                s[k] = shots[0][k]
    return s


def shots_in(scene: dict | None, text: str | None = None) -> list[dict]:
    """EVERY SHOT OF A SCENE, in order (verify 2026-10-21 row 4, VIDEO-RULINGS V8): each `shots[]` row with the
    scene's fields under its own and only its own `lines`. With `text` (a split part's words), the shots whose lines
    are in it, and the wordless shots that follow one of them. A scene with no `shots[]` is one shot: itself."""
    s = dict(scene or {})
    rows = [x for x in s.get("shots") or [] if isinstance(x, dict)] if isinstance(s.get("shots"), list) else []
    if not rows:
        return [s]
    base = {k: v for k, v in s.items() if k not in ("shots", "lines")}
    out = [{**base, **{k: v for k, v in r.items() if v not in (None, "", [])}, "lines": list(r.get("lines") or [])}
           for r in rows]
    if text:
        out = _shots_of_part(out, s, text)
    return out


def _shots_of_part(shots: list[dict], scene: dict, text: str) -> list[dict]:
    """The shots a split part's words fall in (P60): the part's words are found in the scene's words in order, and
    every shot whose lines share a word position with them is in, with the wordless shots that follow one of them.
    A part that is only a piece of one long shot line maps to that one shot. Not found: every shot."""
    want = _norm(text).split()
    spans, pos = [], 0
    for sh in shots:
        n = sum(len(_norm(_say(l)).split()) for l in sh.get("lines") or [] if isinstance(l, dict))
        spans.append((pos, pos + n))
        pos += n
    words = [w for sh in shots for l in sh.get("lines") or [] if isinstance(l, dict) for w in _norm(_say(l)).split()]
    if not want or not words:
        return shots
    at = next((i for i in range(len(words) - len(want) + 1) if words[i:i + len(want)] == want), None)
    if at is None:                                      # the voice was rewritten past the shot lines: by overlap
        keep = [sh for sh in shots if any(_norm(_say(l)) and (_norm(_say(l)) in _norm(text) or _norm(text) in _norm(_say(l)))
                                          for l in sh.get("lines") or [] if isinstance(l, dict))]
        return keep or shots
    a, z = at, at + len(want)
    keep, on = [], False
    for sh, (s0, s1) in zip(shots, spans):
        if s1 > s0:
            on = s0 < z and s1 > a
        if on:
            keep.append(sh)
    return keep or shots


def beat_steps(scene: dict | None, shot_id: str | None = None, text: str | None = None) -> list[str]:
    """THE STEPS ON SCREEN (verify 2026-10-21 row 19, VIDEO-RULINGS V11 "every step said is shown, one step per
    line"): the brief's `beats[]` — each ONE visible action (`do`) — for this shot (`shot`), or, with `text` (a split
    part's words), the beats whose words (`over`) are in it. [] for a brief with no beats."""
    out = []
    want = _norm(text) if text else ""
    for b in (scene or {}).get("beats") or []:
        if not isinstance(b, dict) or not str(b.get("do") or "").strip():
            continue
        if shot_id is not None and b.get("shot") not in (None, "", shot_id):
            continue
        if want and b.get("over") and _norm(b["over"]) not in want:
            continue
        out.append(str(b["do"]).strip().rstrip("."))
    return out


def has_shots(scene: dict | None) -> bool:
    """Does the brief give this scene its own `shots[]` rows (the shooting script)?"""
    return any(isinstance(x, dict) for x in ((scene or {}).get("shots") or [])) if isinstance((scene or {}).get("shots"), list) else False


def last_shot(scene: dict | None) -> dict:
    """The scene's last shot — the one its hand-off and `ends_on` belong to."""
    return shots_in(scene)[-1]


def _say(l: dict) -> str:
    return str((l or {}).get("say") or (l or {}).get("text") or "").strip()


def _norm(t) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", without_tags(t).lower()))


def camera_move_of(scene: dict | None) -> str | None:
    """push-in · pan · tilt · arc · handheld · hold — the shot's `camera_move`, or None."""
    m = str(shot_of(scene).get("camera_move") or "").strip().lower().replace(" ", "-").replace("_", "-")
    m = {"push": "push-in", "pushin": "push-in", "push-in-slow": "push-in", "hand-held": "handheld", "still": "hold",
         "static": "hold", "locked": "hold"}.get(m, m)
    return m if m in CAMERA_MOVES else None


def without_tags(text: str) -> str:
    """The words as said — the v3 audio tags ([whispers], [pause]) are for the voice, never for the model's mouth."""
    return " ".join(AUDIO_TAG.sub("", str(text or "")).split())


def _as_text(v) -> str:
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x).strip().rstrip(".") for x in v if str(x).strip())
    return str(v or "").strip().rstrip(".")


def line_row(scene: dict, text: str) -> dict:
    """The scene's `lines[]` row whose words are this text (a split part matches its own words), else {}."""
    want = _norm(text)
    s = dict(scene or {})
    rows = [l for sh in shots_in(s) for l in sh.get("lines") or []] + list(s.get("lines") or [] if isinstance(s.get("lines"), list) else [])
    for row in rows:
        if isinstance(row, dict) and want and (_norm(_say(row)) == want or want in _norm(_say(row))):
            return row
    return {}


def delivery_of(scene: dict, text: str = "") -> str:
    """How the line is said, for the actor: the line's own v3 `delivery_tag`, else the scene's, else a tag
    written into the voice text — '' when the brief says nothing (the old `tone_of` then speaks)."""
    s = shot_of(scene)
    tag = line_row(s, text).get("delivery_tag") or s.get("delivery_tag")
    if not tag:
        found = AUDIO_TAG.findall(str(s.get("voice") or ""))
        tag = ", ".join(found)
    return _as_text(tag).strip("[] ")


def acting_of(scene: dict, who: str, words: dict) -> str:
    """The actor's face, emotion and gestures in this shot (VIDEO-RULINGS V8), in words — '' when the shot
    carries none."""
    s = shot_of(scene)
    out = []
    face, emo, gest = _as_text(s.get("face")), _as_text(s.get("emotion")), _as_text(s.get("gestures"))
    if emo:
        out.append(_fill(words.get("acting_emotion", "{who} feels {emotion}, and it shows in the eyes and the face."),
                         who=who, emotion=emo))
    if face:
        out.append(_fill(words.get("acting_face", "{who}'s face: {face}."), who=who, face=face))
    if gest:
        out.append(_fill(words.get("acting_gestures", "{who}'s hands and body: {gestures}."), who=who, gestures=gest))
    return " ".join(x.rstrip(".") + "." for x in out)


# Off-camera speech in a scene's `happens` (P38, VIDEO-RULINGS V8): the model turns "the off-screen voice names the soap"
# into a line of its own. Only the listener's own action is kept; quoted words go with it.
SPEECH = re.compile(r"\b(?:says?|said|saying|names?|named|naming|asks?|asked|asking|tells?|told|telling|"
                    r"calls? out|announc\w*|reads? out|explain\w*|mention\w*|narrat\w*|voice[- ]?over|voice|"
                    r"whisper\w*|shout\w*|repl(?:y|ies|ied)|answer\w*|speak\w*|spoke|talk\w*|lists?|listing)\b", re.I)
QUOTED = re.compile(r"(?:\bon\s+)?[\"“][^\"”]*[\"”]")


def no_speech(text: str) -> str:
    """`happens` with every clause that describes someone speaking dropped, and every quoted word gone."""
    t = QUOTED.sub("", str(text or ""))
    parts = re.split(r"\s*(?:[,;]|\bas\b|\bwhile\b|\bwhen\b|\bwhere\b)\s+", t)
    if not any(SPEECH.search(p) for p in parts):
        return " ".join(t.split()).strip(" ,;")
    return ", ".join(p.strip(" ,;") for p in parts if p.strip(" ,;") and not SPEECH.search(p)).strip()


def _section_people(g: dict) -> list[str]:
    return [e.split(" · ")[1] for e in g.get("elements") or [] if e.startswith("person · ")]


def cut_from_footage(scene_ids, by_id: dict) -> bool:
    """Every scene of a section is CUT from our own footage (footage.py's gate,
    2026-10-05): the section is made from that footage, no clip is generated."""
    ids = [s for s in scene_ids or [] if s]
    return bool(ids) and all((by_id.get(s) or {}).get("source_plan") == "cut"
                             and (by_id.get(s) or {}).get("owned_file") for s in ids)


# ONE SWIPE CUT, ONE CONTINUOUS TAKE (2026-10-28: a scene is one real cut in the swipe). A section that copies
# exactly one filmed swipe shot never cuts: the camera holds as the swipe's does, a line written as a cutaway (a close
# insert, a push-in, "the cheekbone alone in frame") is said on camera inside the same take, and only the section's
# last moment may say how it ends. The brief's split into scenes is a writing convenience, not the film.
def one_cut(sb: dict, scenes: list[dict]) -> list[dict]:
    import copy
    by_id = {s["id"]: s for s in scenes}
    out = {s["id"]: s for s in scenes}
    for g in sb.get("sections") or []:
        filmed = [k for k in (g.get("swipe") or {}).get("shots") or [] if "graphic" not in str(k.get("type", "")).lower()]
        if len(filmed) != 1:
            continue
        ids = [i for i in g.get("scenes") or [] if i in by_id]
        talker = next((by_id[i].get("speaker") for i in ids if by_id[i].get("to_camera") and by_id[i].get("speaker")), None)
        for n, i in enumerate(ids):
            sc = copy.deepcopy(by_id[i])
            if (sc.get("voice") or "").strip() and not str(sc.get("voice")).lower().startswith("none"):
                sc["to_camera"] = True
                sc["speaker"] = sc.get("speaker") or talker
            prev_face = next((s.get("face") for j in reversed(ids[:n]) for s in (by_id[j].get("shots") or [])
                              if s.get("face") and not str(s.get("face")).lower().startswith("n/a")), None)
            for sh in sc.get("shots") or []:
                sh["camera_move"] = "hold"
                if str(sh.get("face") or "").lower().startswith("n/a") and prev_face:
                    sh["face"] = prev_face                  # her face stays in the take: no "out of frame" inside one cut
                if n < len(ids) - 1 or re.search(r"alone in frame|close on|fills the frame", str(sh.get("ends_on") or ""), re.I):
                    sh.pop("ends_on", None)
            for b in sc.get("beats") or []:
                if isinstance(b, dict):
                    b["camera"] = "held"
            out[i] = sc
    return [out[s["id"]] for s in scenes]


def plan(run: Path, sb: dict, scenes: list[dict], reg: dict | None = None, only: list[str] | None = None,
         cfg: dict | None = None, people: dict | None = None, style: str = "") -> dict:
    """-> {"calls", "sections", "tts", "totals", "problems"}. Pure: reads the
    run's files, writes nothing, calls nothing."""
    run = Path(run)
    cfg = cfg or route_cfg(reg)
    problems = []
    scenes = one_cut(sb, scenes)
    if people is None:
        people, pp = people_of(run)
        problems += pp
    by_id = {s["id"]: s for s in scenes}
    ov = overrides_of(run)
    span, max_s = cfg["seconds_range"], float(cfg["seconds_range"][1])
    res_ = cfg["resolution"]
    rate = _load("seedance").usd_per_s(res_)      # every clip is Seedance (ruled 2026-10-23), priced at its own rate
    up_on = bool(cfg.get("upscale_below_1080p", True))  # the pick is upscaled on this Mac (upscale_where local)
    lead = ((sb.get("people_map") or {}).get("lead") or [None])[0]
    want = None
    if only:
        want = set()
        for x in only:
            m = re.match(r"^(?:G|Section\s*)?0*(\d+)$", x.strip(), re.I)
            want.add(f"G{int(m.group(1)):02d}" if m else x.strip())
    voice_at = {v["scene"]: v["at"] for v in ((sb.get("layers") or {}).get("voice") or [])}
    # VIDEO SPICE (VIDEO-SPICE.md, V9; verify 2026-10-21 row 19): the piece's level and the layers it turns on
    spice_level = spice_level_of(run)
    spice_on = spice_layers(spice_level)
    rows, calls, spoken_on = [], [], set()
    all_lines: dict[str, dict] = {}
    for n, g in enumerate(sb.get("sections") or [], 1):
        gid = g["id"]
        clock = cp.section_clock(g)
        g_start = float(g.get("starts") or 0)
        for sid, (a, z) in clock.items():
            sc = by_id.get(sid) or {}
            if (sc.get("voice") or "").strip():
                spk = speaker_of(sc, people)
                if spk is None and (not want or gid in want):
                    problems.append(f"{sid}: the brief names no speaker in the cast for this line "
                                    f"({sc.get('speaker') or 'none'}) — the brief's `speaker` decides who says it")
                all_lines[sid] = {"scene": sid, "section": gid, "speaker": spk, "text": sc["voice"].strip(),
                                  "at": round(voice_at.get(sid, g_start + a), 2), "seconds": round(z - a, 2)}
        if want and gid not in want:
            continue
        row = {"n": n, "id": gid, "maker": g.get("maker"), "what": sbp.PLAIN.get(g.get("maker"), g.get("maker")),
               "seconds": g.get("seconds"), "calls": [], "note": ""}
        rows.append(row)
        if g.get("reuses"):
            src = next((x for x in sb.get("sections") or [] if x["id"] == g["reuses"]), {})
            row["note"] = (f"the same {'clip' if src.get('clips') else 'picture'} as "
                           f"{sbp.section_no(g['reuses'])} — not made twice")
            for sid in clock:
                sc = by_id.get(sid) or {}
                if (sc.get("voice") or "").strip() and on_camera(sc, speaker_of(sc, people), gid, [], ov):
                    problems.append(f"{sbp.section_no(gid)} reuses {sbp.section_no(g['reuses'])} but {sid} is said "
                                    f"ON camera — the reused clip says other words")
            continue
        if cut_from_footage(list(clock), by_id):
            row["note"] = "cut from our own footage — no clip generated"
            continue
        if clock and all((by_id.get(s) or {}).get("source_plan") == "swap" for s in clock):
            # SHOT-ROUTES.md SWAP: the swipe's own shot with our cast swapped in (swap-orders.json, swap_run.py) —
            # no picture and no clip; it asked for an S<n>-F1 and stopped the baddie barber's clips (2026-10-21)
            row["note"] = "the swipe's own shot, our cast swapped in — made by the swap order, not here"
            continue
        if not g.get("clips"):
            row["note"] = "no clip — the approved picture is shown for its time"
            if cfg.get("every_section_a_clip") and g.get("maker") not in ("plate", "packshot edit", "endcard plate"):
                problems.append(f"{sbp.section_no(gid)} has no clip — every section of a {cfg.get('format') or 'this format'} "
                                f"is a clip, never a still or a hold (providers.json direct.clip_route.by_format)")
            continue
        pics = cp.picture_ids(g)
        need = [p for p in [pics["start"], pics["end"]] + [o["id"] for o in pics["own"]]
                + [x["id"] for x in pics.get("setups") or []] if p]
        missing = [p for p in need if cp.picture_file(run, p) is None]
        if missing:
            problems.append(f"{sbp.section_no(gid)} needs the approved picture {', '.join(missing)} — not in media/")
            continue
        movement = g.get("maker") == "motion transfer"
        wins = cp.shot_windows(g)
        shots = {k["id"]: k for k in (g.get("swipe") or {}).get("shots") or []}
        own_shots = {k for o in pics["own"] for k in o["drives"]}
        g_people = _section_people(g)
        total = len(g["clips"])
        prev = None
        units = []
        for ci, c in enumerate(g["clips"], 1):
            scs = [by_id[s] for s in c.get("scenes") or [] if s in by_id]
            if not scs:
                problems.append(f"{sbp.section_no(gid)} clip {ci}: none of its scenes is in the brief")
                continue
            ts = [clock[s["id"]] for s in scs if s["id"] in clock]
            _span = (g.get("swipe") or {}).get("span") or [0, 0]
            _gs = float(g.get("seconds") or 0) or max(0.0, float(_span[1] or 0) - float(_span[0] or 0))
            # A SECTION WITH NO WORDS IN A PIECE THAT HAS A FEW (2026-10-10: a wordless ad with one "Hmm." and one
            # "Oof." left every other section at 0 s) — its length is the swipe shots it copies, as above.
            if not ts and _gs > 0:
                # A WORDLESS SECTION (2026-10-09, an ad carried by its song): no line is recorded, so the voice
                # clock is empty and every clip's own seconds are ~0. The section's seconds (the swipe shots it
                # copies) are the length: the clips' own seconds when they add up to it, else an even share.
                g_s = _gs
                own_s = [float(x.get("seconds") or 0) for x in g["clips"]]
                lens = own_s if all(own_s) and abs(sum(own_s) - g_s) < 0.1 else [g_s / total] * total
                ts = [(round(sum(lens[:ci - 1]), 2), round(sum(lens[:ci]), 2))]
            t0 = min(a for a, _ in ts) if ts else 0.0
            t1 = max(z for _, z in ts) if ts else float(c.get("seconds") or 0)
            if t1 - t0 < 0.05 and float(c.get("seconds") or 0) > 0:
                # A WORDLESS PIECE (2026-10-09, a BRAND-A ad carried by its song): nothing is spoken, so the voice
                # clock gives every scene no length — the storyboard clip's own seconds are its length
                t1 = t0 + float(c["seconds"])
            units.append({"cid": f"{gid}-C{ci}", "t0": t0, "t1": t1, "picture": pics["start"] if ci == 1 else None,
                          "scenes": [s["id"] for s in scs],
                          "end": pics["end"] if ci == total else None, "keep": None if not movement else
                          {k for k, _, _ in wins} - own_shots, "kind": "clip", "chain": True})
        for o in pics["own"]:
            ks = [w for w in wins if w[0] in o["drives"]]
            # one call per unbroken run of the shots this picture drives — the set-up
            # shots in between are the main clip's, never made twice from this picture
            runs_, cur = [], []
            for w in ks:
                if cur and abs(cur[-1][2] - w[1]) > 0.05:
                    runs_.append(cur); cur = []
                cur.append(w)
            if cur:
                runs_.append(cur)
            for ri, r in enumerate(runs_):
                units.append({"cid": f"{gid}-{o['copies']}" + (chr(ord("a") + ri) if len(runs_) > 1 else ""),
                              "t0": r[0][1], "t1": r[-1][2], "picture": o["id"], "end": None,
                              "keep": set(o["drives"]), "kind": "cutaway", "chain": False})
        for u in units:
            sec_lines = []
            for sid, (a, z) in clock.items():
                sc = by_id.get(sid) or {}
                if not (sc.get("voice") or "").strip() or z <= u["t0"] + 0.01 or a >= u["t1"] - 0.01:
                    continue
                spk = speaker_of(sc, people)
                cam = on_camera(sc, spk, gid, [u["cid"]], ov)
                said, sound = split_sound(without_tags(sc["voice"]).strip())
                ln = {"scene": sid, "speaker": spk, "text": said or without_tags(sc["voice"]).strip(), "a": a, "z": z,
                      "on_camera": cam and bool(said)}
                if sound:
                    ln["sound"] = sound                 # on its own track at the edit, never in the clip
                    ln["nod"] = cam                     # the speaker is on screen: a nod, lips closed
                sec_lines.append(ln)
            parts = split_calls(sec_lines, u["t0"], u["t1"], max_s, float(span[0]))

            def setup_of(ls_):
                # the set-up this clip is in: the picture of the latest set-up at or before its first scene
                sp_ = None
                order = list(g.get("scenes") or [])
                first_sc = (ls_[0]["scene"] if ls_ else None) or (u.get("scenes") or [None])[0]
                for spic in pics.get("setups") or []:
                    if first_sc in order and spic["scene"] in order and order.index(spic["scene"]) <= order.index(first_sc):
                        sp_ = spic["id"]
                return sp_
            for pi, (a, z, ls) in enumerate(parts):
                call_id = u["cid"] + (f"-{pi + 1}" if len(parts) > 1 else "")
                setup_pic = setup_of(ls)
                if u["chain"] and g_people:
                    # ROOT CAUSE, 3 Oct (Creator-A): a clip started from the clip before's last frame copies a
                    # copy — every hand-off paled her skin, faded her spots, aged the face, and by the 2nd-3rd
                    # her eyes went brown; all 17 clips started from the approved picture held her. So a
                    # person on screen: every clip starts from the approved picture. No hand-offs — and no
                    # approved picture is a stop (handoff_breaks), never a fall back to a made frame.
                    start, after = setup_pic or pics["start"], None
                elif u["chain"]:
                    start = u["picture"] if (pi == 0 and u["picture"]) else f"{prev}-LAST"
                    after = None if (pi == 0 and u["picture"]) else prev
                else:
                    start, after = u["picture"], None
                end = u["end"] if pi == len(parts) - 1 else None
                if end is None and pi < len(parts) - 1 and u["chain"] and g_people:
                    # THE JOIN (P6, VIDEO-RULINGS V10): a person's split call starts the next part from the approved
                    # picture, so this part ENDS on that same picture — the join is invisible, never a jump back
                    end = setup_of(parts[pi + 1][2]) or pics["start"]
                refs = ref_pieces(wins, shots, a, z, u["keep"], cfg["refs"]) if movement else []
                if refs and _section_people(g):
                    refs = []        # a person on screen: lock the approved picture as the first frame (always)
                endpoint = "reference-to-video" if refs else "image-to-video"
                in_shots = [shots[k] for k, x, y in wins if y > a + 0.01 and x < z - 0.01 and
                            (u["keep"] is None or k in u["keep"])]
                seconds = round(z - a, 2)
                # EVERY CLIP AT ITS FULL WINDOW (VIDEO-RULINGS V17, verify 2026-10-21 row 8): a silent clip is never
                # made shorter to be slowed at the edit — the 2026-10-09 silent_share cut is retired
                dur = billed(seconds, span)
                ls_in = [{**l, "at": round(max(l["a"], a) - a, 2), "until": round(min(l["z"], z) - a, 2)} for l in ls]
                for l in ls_in:
                    if l["on_camera"]:
                        spoken_on.add(l["scene"])
                # the brief's scenes this call shows: those whose time on the section's clock falls in its window
                # (a scene with no clock time — no voice — is in every call of its clip)
                in_call = [sid for sid in u.get("scenes") or []
                           if sid not in clock or (clock[sid][1] > a + 0.01 and clock[sid][0] < z - 0.01)]
                call = {
                    "id": call_id, "section": sbp.section_no(gid), "section_id": gid, "n": n, "scenes": in_call,
                    "maker": g.get("maker"), "clip": u["cid"], "clip_is": u["kind"],
                    "endpoint": endpoint, "model": cfg["models"][endpoint],
                    "window": [round(a, 2), round(z, 2)], "at": round(g_start + a, 2),
                    "seconds": seconds, "duration": dur,
                    "start_frame": start, "end_frame": end, "after": after,
                    # the face check always compares with an approved picture, never a handed-on last
                    # frame (3 Oct: G22-C2 started from a blink, so brown eyes had nothing to fail against)
                    "face_ref": (u["picture"] or pics["start"]) if not u["chain"] else (setup_pic or pics["start"] or start),
                    "camera": camera_kind(in_shots, by_id.get((ls_in or [{}])[0].get("scene", ""), {}) or
                                          by_id.get((g.get("scenes") or [""])[0], {})),
                    # THE CLIP'S OWN PEOPLE (2026-10-08, LeBron): the brief names who is in each scene's frame
                    # (`looks`); describing everyone in the section had the model bring the staff member — in S2 only —
                    # into every later clip, and pull back to show the press. Fallback: the section's people.
                    "people": clip_people(g_people, [l["scene"] for l in ls_in] or (u.get("scenes") or []), by_id, lead),
                    "lines": [{k: l[k] for k in ("scene", "speaker", "text", "on_camera", "at", "until")}
                              | ({"part": l["part"]} if l.get("part") else {})
                              | ({"sound": l["sound"], "nod": l["nod"]} if l.get("sound") else {}) for l in ls_in],
                    "refs": [{**r, "file": f"clips/refs/{call_id}-ref{i + 1}.mp4"} for i, r in enumerate(refs)],
                    # the shot contract the clip reads (CHANGES.md 2026-10-21) — absent on an older brief
                    "realism": sorted({x for sid in in_call for x in (shot_of(by_id.get(sid)).get("realism") or [])}) or None,
                    "realism_format": next((f_ for f_ in (realism_format_of(by_id.get(sid)) for sid in in_call) if f_), None),
                    "spice_level": spice_level,
                    "spice_layers": sorted(spice_on) if spice_on is not None else None,
                    # the hand-off is the LAST shot's — how the scene leaves this take (row 4)
                    "hands_off": next((last_shot(by_id.get(sid)).get("hands_off") for sid in reversed(in_call)
                                       if last_shot(by_id.get(sid)).get("hands_off")), None),
                }
                call["talking"] = any(l["on_camera"] for l in call["lines"])
                if call["talking"]:
                    # ROOM TO FINISH (2026-10-28): the model leaves natural pauses between lines, so a take sized to the
                    # read ran out on the last words every time (two takes cut off at "every month", 9.9 s of 10)
                    call["duration"] = dur = billed(seconds * TALK_ROOM + 0.6, span)
                if not call["refs"] and call["people"]:
                    # REAL HUMAN MOVEMENT (2026-10-28): a person on screen gets a real person's performance as a
                    # movement-only reference, so the head, neck, face and hands move like a person, not a still come alive
                    does = " ".join(_as_text(x) for sid in in_call for x in
                                    [(by_id.get(sid) or {}).get("happens")] + [b.get("do") for b in (by_id.get(sid) or {}).get("beats") or []
                                                                             if isinstance(b, dict)]
                                    + [sh.get("gestures") for sh in (by_id.get(sid) or {}).get("shots") or []])
                    call["refs"] = _load("movement").for_call({**call, "duration": dur}, does + (" talks to camera" if call["talking"] else ""))
                call["engine"] = "seedance"
                call["endpoint"] = "reference-to-video" if call.get("refs") else "image-to-video"   # a talking clip adds its voice (TALK path)
                call["model"] = cfg["models"][call["endpoint"]]
                call["takes"] = int(cfg.get("takes") or 1)
                call["resolution"] = res_
                call["voice_parts"] = [{"scene": l["scene"], "person": l["speaker"], "line": l["text"],
                                        "voice_id": (people.get(l["speaker"]) or {}).get("voice_id")}
                                       for l in call["lines"] if l["on_camera"]]
                # THE PROMPT is Seedance's own (2026-10-26, BytePlus Seedance 2.5 prompt guide): bound assets, one
                # sentence, whole-second windows, constants (machine/seedance_prompt.py, SEEDANCE-INPUTS.md)
                _br = _load("scene_breakdown").of_call(run, call)
                call["swipe_elements"] = _load("scene_breakdown").prompt_lines(_br)
                call["camera_held"] = bool((_br.get("drift") or {}).get("held"))
                call["seedance"] = _load("seedance_prompt").build(call, by_id, people, cfg["words"], style, lead)
                call["prompt"] = call["seedance"]["prompt"]
                call["acting"] = call["seedance"].get("acting") or []            # V46: what is filled / not applicable
                if (cfg.get("backup") or {}).get("enabled"):
                    # the backup's own words, built now so the preflight can show them (nothing is sent)
                    call["kling"] = _load("kling_prompt").build(call, by_id, people, cfg["words"], style, lead)
                call["params"] = {"prompt": call["prompt"], "duration": dur, "aspect_ratio": cfg["aspect_ratio"],
                                  "resolution": res_}
                call["usd"] = round(dur * rate, 4)
                call["upscale_usd"] = 0.0                      # the upscale runs on this Mac, free
                call["upscale"] = None if res_ in ("1080p", "4k") or not up_on else "local"
                call["steps"] = steps_of(call)
                for vp in call["voice_parts"]:
                    if not vp["voice_id"]:
                        problems.append(f"{call_id}: {vp['person']} says {vp['scene']} on camera but has no cloned voice")
                calls.append(call)
                row["calls"].append(call_id)
                if u["chain"]:
                    prev = call_id
    # the off-camera lines: every voiced line no clip says on camera, in its person's cloned voice
    tts = []
    for sid, l in all_lines.items():
        if want and l["section"] not in want:
            continue
        said, sound = split_sound(l["text"])
        if sid in spoken_on and not sound:
            continue
        p = people.get(l["speaker"]) or {}
        if sound:
            l = {**l, "text": sound if sid in spoken_on else l["text"], "sound": True,
                 "why": "not a word: no lip sync, laid in at the edit"}
            sid_out = f"{sid}-sound" if sid in spoken_on else sid
        else:
            sid_out = sid
        if not p.get("voice_id"):
            problems.append(f"{sid}: off camera, but {l['speaker'] or 'nobody'} has no cloned voice")
        tts.append({**l, "section": sbp.section_no(l["section"]), "voice_id": p.get("voice_id"),
                    # the house voice (eleven_v3) and the line's own delivery tag (P14, VIDEO-RULINGS V4)
                    # (the house's, over any older model a voice.json still names — VIDEO-RULINGS V2/V4)
                    "model_id": cfg["tts"]["model_id"],
                    "delivery_tag": delivery_of(by_id.get(sid) or {}, l["text"]) or None,
                    "out": f"clips/offcam/{sid_out}.mp3", "finish": "crisp", "chars": len(l["text"])})
    totals = {"calls": len(calls), "clip_seconds": sum(c["duration"] for c in calls),
              "clip_usd": round(sum(c["usd"] for c in calls), 2),
              "upscale_seconds": round(sum(c["seconds"] for c in calls if c["upscale_usd"]), 2),
              "upscale_usd": round(sum(c["upscale_usd"] for c in calls), 2),
              "talking_calls": sum(1 for c in calls if c["talking"]),
              "voice_swaps": sum(len(c["voice_parts"]) for c in calls),
              "tts_lines": len(tts), "tts_chars": sum(t["chars"] for t in tts)}
    totals["spend_usd"] = round(totals["clip_usd"] + totals["upscale_usd"], 2)
    # THREE TAKES OF EVERY CLIP (V5): what the takes cost, all of them, beside the one-take figure
    totals["takes"] = int(cfg.get("takes") or 1)
    totals["usd_all_takes"] = round(totals["clip_usd"] * totals["takes"] + totals["upscale_usd"], 2)
    # V34: one take, another only on failure — the most it can cost if every clip fails twice
    totals["max_tries"] = max(totals["takes"], int(cfg.get("max_tries") or totals["takes"]))
    totals["usd_worst"] = round(totals["clip_usd"] * totals["max_tries"] + totals["upscale_usd"], 2)
    problems += handoff_breaks(calls)
    # V46: a to-camera shot with no visible face/gestures, or a person with no character-file section, is SAID here —
    # in the plan (the run record and the variable sheet read it), never silently blank, and never a stop
    acting_notes = [f"{c['id']}: {n['shot']}.{n['field']} {n['status']}"
                    + (f" — {n.get('reason') or n.get('from')}" if n.get("reason") or n.get("from") else "")
                    for c in calls for n in c.get("acting") or [] if n["status"] != "ok"]
    return {"route": "seedance", "format": cfg.get("format"), "calls": calls, "sections": rows, "tts": tts,
            "totals": totals, "problems": problems, "overrides": ov, "acting_notes": acting_notes}


def handoff_breaks(calls: list[dict]) -> list[str]:
    """THE NO-HAND-OFF GUARD (the owner, 2026-10-03, providers.json ruling_2026_10_03_no_handoffs):
    a call with a person on screen must start from an approved picture — never from a made frame
    (a call's `-LAST`), never from nothing. Each break is a stop, named."""
    out = []
    for c in calls:
        if not c.get("people"):
            continue
        sf = str(c.get("start_frame") or "")
        if not sf:
            out.append(f"{c['id']}: a person is on screen but the section has no approved start picture — "
                       "a person's clip starts only from the approved picture")
        elif sf.endswith("-LAST") or c.get("after"):
            out.append(f"{c['id']}: a person is on screen but the clip would start from {sf} — a person's clip "
                       "starts from the approved picture, never a clip's last frame (3 Oct)")
    return out


def steps_of(call: dict) -> list[str]:
    s = [f"animate: Seedance 2.5 {call['endpoint']}, {call['duration']} s, from the approved picture "
         f"{call['start_frame']}" + (f" to {call['end_frame']}" if call.get("end_frame") and not call["talking"] else "")]
    if call["talking"]:
        who = ", ".join(sorted({p["person"] or "?" for p in call["voice_parts"]}))
        s += [f"voice: each on-camera line's own locked read ({who}, ElevenLabs v3) goes in the SAME call as the picture; "
              "nothing is re-voiced or fitted after",
              "line check: every on-camera word heard"]
    else:
        s.append("sound: none kept (silent clip; the cut carries the sound)")
    s.append("clip_qc.py: framing · scene · camera · lips")
    if int(call.get("takes") or 1) > 1 or int(call.get("max_tries") or 1) > 1:
        s.append(f"takes: one take, judged by the clip judge (dead pauses · lips closed listening · kept its object · room "
                 "unchanged); another only if it fails, three at most; none passing = the best-scoring one is kept and flagged below criteria")
    if call.get("upscale") == "local":
        s.append("upscale: on this Mac (local-studio upscale, Real-ESRGAN) → 1080x1920, no cost")
    return s


# ------------------------------------------------------------ the page

def _lines_cell(c: dict, on: bool) -> str:
    ls = [l for l in c["lines"] if l["on_camera"] == on]
    if not ls:
        return "—"
    return "; ".join(f"{l['scene']} {l['speaker'] or '?'}" + (f" ({l['part']})" if l.get("part") else "") for l in ls)


def table(res: dict) -> list[str]:
    calls = {c["id"]: c for c in res["calls"]}
    L = ["| Section | What | On camera (said in the clip) | Off camera (cloned voice, later) | Call | Seconds (billed) "
         "| Endpoint | Start → end picture | Blurred refs | Clip $ | Upscale $ |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["sections"]:
        if not r["calls"]:
            L.append(f"| {r['n']} | {r['what']} | — | — | — | {r['seconds']} | — | — | — | 0 | 0 — {r['note']} |")
            continue
        for cid in r["calls"]:
            c = calls[cid]
            refs = ", ".join(f"{x.get('shot') or 'real movement ' + str(x.get('id'))}@{x['from']}+{x['seconds']}s" for x in c["refs"]) or "—"
            L.append(f"| {r['n']} | {r['what']} | {_lines_cell(c, True)} | {_lines_cell(c, False)} | {cid} "
                     f"({c['clip_is']}) | {c['seconds']} ({c['duration']}) | {c['endpoint']} | "
                     f"{c['start_frame']} → {c['end_frame'] or '—'} | {refs} | {c['usd']:.2f} | {c['upscale_usd']:.3f} |")
    return L


def budget_line(t: dict) -> str:
    takes = (f" · {t['takes']} takes of every clip = ${t['usd_all_takes']:.2f}" if int(t.get("takes") or 1) > 1 else "")
    if int(t.get("max_tries") or 1) > int(t.get("takes") or 1):
        takes += f" · up to {t['max_tries']} takes only where one fails = at most ${t['usd_worst']:.2f}"
    return (f"BUDGET · Seedance {t['clip_seconds']} s = ${t['clip_usd']:.2f}{takes} · upscale {t['upscale_seconds']} s = "
            f"${t['upscale_usd']:.2f} · total ${t['spend_usd']:.2f} · plus ElevenLabs: {t['voice_swaps']} on-camera "
            f"locked read(s) sent with the picture in {t['talking_calls']} talking clip(s) and {t['tts_lines']} off-camera line(s) "
            f"({t['tts_chars']} characters)")


def prompts_md(run: Path, res: dict, cfg: dict) -> str:
    t = res["totals"]
    L = [f"# Clips — Seedance 2.5 · {t['calls']} call(s)", "",
         "The pictures are the approved GPT Image 2.5 pictures in `media/` (step 4.4). Seedance does not make "
         "pictures: it only animates the approved picture — the movement, the mouths and the speech. "
         f"Every call is Seedance 2.5 on Higgsfield at {cfg['resolution']}, {cfg['aspect_ratio']}, whole seconds. "
         "A line said ON camera goes in the same call as the picture, as its locked read (Audio 1), and is never typed "
         "into the prompt; lines said OFF camera are not in the clip — they are read by the cloned voice and laid on their own track. "
         "The prompt under each call is exactly what the model receives.", "",
         "Who is visibly in each picture (where the brief's to_camera was wrong for the picture): "
         + ("; ".join(f"{k}: on {', '.join(v.get('on_camera') or []) or '—'} / off {', '.join(v.get('off_camera') or []) or '—'}"
                      f" — {v.get('why', '')}" for k, v in (res.get("overrides") or {}).items() if isinstance(v, dict))
            or "none"), ""]
    L += table(res)
    L += ["", f"**{budget_line(t)}**", ""]
    L += [f"Sent at most {cfg.get('parallel', 6)} at a time; a person's call always starts from the approved picture; only a call with nobody on screen may start from another call's last frame, and it waits for it.", ""]
    L += ["## Off-camera lines (cloned voice, text-to-speech, crisp finish, at their storyboard time)", "",
          "| Line | Section | Person | At (s in the ad) | Words |", "|---|---|---|---|---|"]
    for x in res["tts"]:
        L.append(f"| {x['scene']} | {x['section']} | {x['speaker']} | {x['at']} | {x['text']} |")
    for c in res["calls"]:
        L += ["", f"## {c['section']} · {c['id']} — {c['maker']} ({c['clip_is']})", "",
              f"- **animates**: the approved picture `{c['start_frame']}`"
              + (f" → ends on `{c['end_frame']}`" if c["end_frame"] else ""),
              f"- **model**: {c['model']} on Higgsfield · {c['duration']} s billed for a {c['seconds']} s window · "
              f"{c['params']['resolution']} · {c['params']['aspect_ratio']} · ${c['usd']:.2f}",
              f"- **blurred swipe refs (sent as Video 1…)**: " + (", ".join(f"`{x['file']}` = {x.get('shot') or 'real movement ' + str(x.get('id'))} from {x['from']} s, {x['seconds']} s"
                                                       for x in c["refs"]) or "none"),
              f"- **on camera**: {_lines_cell(c, True)} · **off camera**: {_lines_cell(c, False)}",
              "- **after it lands**: " + " → ".join(c["steps"][1:]),
              "", "```text", c["prompt"], "```"]
    return "\n".join(L) + "\n"


def print_table(res: dict) -> None:
    for line in table(res):
        print(line)


# ------------------------------------------------------------ the step (run.py start … --clips)

def start(a, run: Path, plan_doc: dict, reg: dict) -> int:
    run = Path(run)
    sbf = run / "storyboard.json"
    if not sbf.is_file():
        print("REFUSED --clips: no storyboard.json in the run", file=sys.stderr)
        return 2
    if getattr(a, "storyboard", False):
        print("REFUSED --clips with --storyboard: pictures first, then clips", file=sys.stderr)
        return 2
    cfg = route_cfg(reg, format_of(run, plan_doc))
    only = [x for x in str(getattr(a, "only", "") or "").split(",") if x.strip()] or None
    sb_doc = json.loads(sbf.read_text())
    # A SILENT SCENE SAYS SO (2026-10-09): "None." / "None. Heard: …" in `voice` is a sound note, not a line —
    # nobody speaks it, so it needs no speaker; what is heard rides along as the scene's sound.
    for _sc in plan_doc.get("scenes") or []:
        _v = str(_sc.get("voice") or "").strip()
        if re.match(r"(?i)^none\b", _v):
            _rest = re.sub(r"(?i)^none\.?\s*(heard:\s*)?", "", _v).strip()
            if _rest and not _sc.get("sound"):
                _sc["sound"] = _rest
            _sc["voice"] = ""
    scenes = with_speakers(run, sb_doc, plan_doc.get("scenes") or [])
    # a layers.transitions row of kind continuous / action is the scene's hand-off (P50)
    _ho = {t.get("after_scene"): str(t.get("kind") or "").lower() for t in (plan_doc.get("layers") or {}).get("transitions") or []
           if isinstance(t, dict) and str(t.get("kind") or "").lower() in ("continuous", "action", "match", "whip", "cut")}
    scenes = [{**sc, "hands_off": _ho[sc.get("id")]} if sc.get("id") in _ho and not sc.get("hands_off") else sc
              for sc in scenes]
    unnamed = [sc.get("id") for sc in scenes if str(sc.get("voice") or "").strip() and not sc.get("speaker")]
    if unnamed:
        # never guess a voice from whose hands are in the shot (3 Oct: the doctor's line went to Creator-A)
        print(f"REFUSED --clips: the brief names no speaker for {', '.join(unnamed)} — "
              "every spoken line needs its `speaker` from the swipe's transcript", file=sys.stderr)
        return 2
    res = plan(run, sb_doc, scenes, reg, only=only, cfg=cfg, style=style_line(run, plan_doc))
    for p in res["problems"]:
        print(f"STOP {p}", file=sys.stderr)
    ruled = seedance_ruling()
    if not ruled:
        print("REFUSED --clips: the Model House has no Seedance clip ruling (models.json clips.ruled_2026_10_23)", file=sys.stderr)
        return 2
    print(f"clips (Seedance 2.5, {ruled.get('resolution')}): {len(res['calls'])} call(s) — every one animates "
          f"an approved picture; a talking clip is made WITH its locked voice read in the same call "
          f"(Higgsfield API: {(ruled.get('seedance_paths') or {}).get('talking', '').split(' ')[0]})")
    print_table(res)
    print()
    t = res["totals"]
    print(f"LENGTH · {t['clip_seconds']} s of clips in {t['calls']} call(s) · one take of every clip, another only if it "
          f"fails, three at most")
    (run / "clips").mkdir(exist_ok=True)
    # a look at some sections never replaces the whole ad's plan (3 Oct: `--only` wiped it)
    tag = "-only" if only else ""
    page = run / "clips" / f"PROMPTS{tag}.md"
    page.write_text(prompts_md(run, res, cfg))
    planf = run / "clips" / f"plan{tag}.json"
    planf.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    print(f"prompts: {page}")
    print(f"plan: {planf}" + ("  (sections only — the full plan.json is untouched; `run --only` makes "
                               "sections from the full plan)" if only else ""))
    if res["problems"]:
        print("problems above — nothing will be made until they are cleared", file=sys.stderr)
        return 2
    print(f"to make them (LIVE, on Seedance 2.5 through the Higgsfield API): python3 {HERE / 'clips_run.py'} run {run} --yes")
    return 0


# ------------------------------------------------------------ live: the runner (not run by plan / dry runs)

LOCK = threading.Lock()
# The run folder's names (2026-10-26): clips/ledger.json and clips/calls/<call>/; a run made before keeps the old names
# on disk and clip_kit finds them (ledger_path, calls_dir).
def _kit():
    return _load("clip_kit")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def build_refs(run: Path, calls: list[dict], cfg: dict, teardown: Path, ffmpeg: str = "ffmpeg", runner=None) -> list[str]:
    """The blurred swipe pieces — local ffmpeg only, no network, no money."""
    runner = runner or (lambda cmd: subprocess.run(cmd, check=True, capture_output=True))
    r, out = cfg["refs"], []
    for c in calls:
        for x in c.get("refs") or []:
            dest = Path(run) / x["file"]
            if dest.is_file():
                continue
            if x.get("kind") == "movement":
                out.append(str(_load("movement").make(run, x, ffmpeg, runner)))
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            src = Path(teardown) / "framemap" / "shots" / x["clip"]
            runner([ffmpeg, "-y", "-v", "error", "-ss", f"{x['from']:.2f}", "-t", f"{x['seconds']:.2f}", "-i", str(src),
                    "-an", "-vf", f"scale={int(r['scale'])}:-2,gblur=sigma={r['blur_sigma']}", str(dest)])
            out.append(str(dest))
    return out


def words_of(transcript: dict) -> list[dict]:
    return [w for w in (transcript.get("words") or []) if w.get("type", "word") == "word"]


def find_lines(words: list[dict], lines: list[str], norm=None) -> list[tuple[float, float] | None]:
    """Each line's stretch [first word start, last word end] in the clip's own
    transcript, found by matching its words in order (the model may add or drop
    a word; anything it adds outside the lines is not anybody's line)."""
    norm = norm or (lambda t: re.sub(r"[^\w\s]", " ", (t or "").lower()).split())
    heard = [(norm(w.get("text"))[:1] or [""])[0] for w in words]
    out, pos = [], 0
    for line in lines:
        want = norm(line)
        if not want:
            out.append(None); continue
        sm = difflib.SequenceMatcher(None, heard[pos:], want, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        if not blocks:
            out.append(None); continue
        i0 = pos + blocks[0].a
        i1 = pos + blocks[-1].a + blocks[-1].size - 1
        out.append((float(words[i0]["start"]), float(words[i1]["end"])))
        pos = i1 + 1
    return out


class Ledger:
    def __init__(self, run: Path):
        self.f = _kit().ledger_path(run)
        self.run = Path(run)
        self.d = _read(self.f, {}) or {}

    def get(self, cid):
        self.d = _read(self.f, {}) or self.d
        return self.d.get(cid) or {}

    def put(self, cid, **kw):
        # ONE RECORD, MANY WRITERS (2026-10-28): two jobs on one run (a keep and a make) each held their own copy and
        # wrote it whole, wiping each other's rows. Every write re-reads the file under a file lock and changes one row.
        import fcntl
        with LOCK:
            self.f.parent.mkdir(parents=True, exist_ok=True)
            with open(self.f.with_suffix(".lock"), "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                self.d = _read(self.f, {}) or {}
                self.d.setdefault(cid, {}).update(kw, at=now())
                tmp = self.f.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.d, indent=1) + "\n")
                tmp.replace(self.f)
                fcntl.flock(lk, fcntl.LOCK_UN)

    def spend(self, job, model, seconds, usd, resolution=None):
        with LOCK:
            p = self.run / "ledger.json"
            rows = _read(p, []) or []
            rows.append({"model": model, "job": job, "seconds": seconds, "tier": None, "resolution": resolution,
                         "status": "done", "credits": None, "usd": usd, "at": now(), "shot": job})
            p.write_text(json.dumps(rows, indent=1) + "\n")


def _dur(p) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def crop_box(w: int, h: int, aspect=(9, 16), tol: float = 0.01):
    """The centred box that cuts a w×h picture to the aspect (cover, never stretched or
    padded) — or None when it is already within `tol` of it."""
    want = aspect[0] / aspect[1]
    if not w or not h or abs(w / h - want) <= tol * want:
        return None
    if w / h > want:                                 # too wide: trim the sides
        nw = int(round(h * want))
        x = (w - nw) // 2
        return (x, 0, x + nw, h)
    nh = int(round(w / want))                         # too tall (a 2:3 picture): trim top and bottom
    y = (h - nh) // 2
    return (0, y, w, y + nh)


def to_aspect(picture: Path, out: Path, aspect=(9, 16)) -> Path:
    """The picture as sent to the model: cut to the aspect (2026-10-10 — at 360p the model refused ~14 clips of
    the first song ad as "third-party content" when the start picture was 2:3; at 9:16 most went
    through). A copy beside the call; the approved picture in media/ is never touched."""
    from PIL import Image
    with Image.open(picture) as im:
        box = crop_box(im.width, im.height, aspect)
        if box is None:
            return Path(picture)
        if not out.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            im.crop(box).save(out)
    return out


def _height(p) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0


def upscale_local(clip: Path, out: Path, cfg: dict, runner=None) -> Path:
    """Upscale a clip on this Mac through local-studio's launcher (`local.py upscale`), to the
    format's target height (1080x1920 from the 480p clip). No money spent."""
    up = cfg.get("upscale_local") or {}
    launcher = WORKSPACE / up.get("launcher", "components/local-studio/local.py")
    h = _height(clip)
    scale = max(2, int(round(int(up.get("target_height", 1920)) / h))) if h else 3
    sg = _load("sheet_gates")                   # the Real-ESRGAN sheet, before the local job starts
    sg.raise_on_errors(sg.upscale("real-esrgan", clip, scale=scale), "upscale")
    runner = runner or (lambda cmd: subprocess.run(cmd, check=True))
    runner([sys.executable, str(launcher), "upscale", str(clip), "-o", str(out), "--scale", str(scale),
            "--engine", up.get("engine", "esrgan")])
    return out


def part_window(timing: dict, scene: str, text: str) -> tuple[float, float | None]:
    """Where a split part's own words sit inside its scene's locked read (vo/<scene>.mp3): the read's sentence
    windows (vo/timing.json) whose words are this part's, as seconds from the read's start. (0, None) = all of it."""
    sc = (timing.get("scenes") or {}).get(scene) or {}
    norm = lambda t: " ".join(re.findall(r"[a-z0-9']+", without_tags(t).lower()))
    want = norm(text)
    hit = [w for w in sc.get("lines") or [] if norm(w.get("text")) and norm(w.get("text")) in want]
    if not hit or not isinstance(sc.get("start"), (int, float)):
        return 0.0, None
    a = max(0.0, min(float(w["start"]) for w in hit) - float(sc["start"]) - 0.05)
    z = max(float(w["end"]) for w in hit) - float(sc["start"]) + 0.15
    return round(a, 3), round(z, 3)


def locked_read(run: Path, c: dict, d: Path, ck) -> tuple[Path, float, float | None]:
    """The locked read of every line this call says on camera (VIDEO-RULINGS V4/V5): the line's own read, and
    for a split part only that part's words (P16). Several lines → their reads cut and joined in order.
    A line with no locked read STOPS the call (P15) — voice first, then pictures, then clips (V7)."""
    timing = _read(Path(run) / "vo" / "timing.json", {}) or {}
    part_of = {l["scene"]: l.get("part") for l in c.get("lines") or [] if l.get("on_camera")}
    pieces = []
    for vp in c.get("voice_parts") or []:
        f = Path(run) / "vo" / f"{vp['scene']}.mp3"
        if not f.is_file():
            raise RuntimeError(f"{c['id']}: no locked read for {vp['scene']} (vo/{vp['scene']}.mp3) — the voice is "
                               "made first and nothing is re-voiced (speech-to-speech is retired, 2026-10-21)")
        a, z = part_window(timing, vp["scene"], vp["line"]) if part_of.get(vp["scene"]) else (0.0, None)
        pieces.append((f, a, z))
    if not pieces:
        raise RuntimeError(f"{c['id']}: a talking call with no on-camera line to read")
    if len(pieces) == 1:
        return pieces[0]
    cut = []
    for n, (f, a, z) in enumerate(pieces):
        seg = d / f"read-{n + 1}.wav"
        ck.run_cmd([ck.ffmpeg_path(), "-y", "-ss", f"{a}"] + (["-to", f"{z}"] if z else []) +
                     ["-i", str(f), "-ac", "1", "-ar", "44100", str(seg)])
        cut.append(seg)
    take = d / "locked-reads.wav"
    lst = d / "locked-reads.txt"
    lst.write_text("".join(f"file '{t}'\n" for t in cut))
    ck.run_cmd([ck.ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-ac", "1", "-ar", "44100", str(take)])
    return take, 0.0, None


def clip_model(cfg: dict | None) -> str | None:
    """Which Seedance a format's clips use: its playbook's `stages.clips.model` when that names one the door has (a song
    ad: Seedance 2.0, ruled 2026-10-29, the house's clips.song_ad); None = the house's default (2.5). Never a literal here."""
    try:
        m = _load("playbook").setting((cfg or {}).get("format"), "stages.clips.model")
    except Exception:                                     # noqa: BLE001 — no playbook answer: the default
        return None
    return m if m in _load("seedance").PATHS else None


def seedance_ruling() -> dict | None:
    """The Model House's clip ruling (clips.ruled_2026_10_23, read through house.py) — Seedance 2.5 for every clip — or None."""
    try:
        r = _load("house").model("clips.ruled_2026_10_23")
    except (KeyError, SystemExit, OSError, ValueError):
        return None
    return r if r.get("talking") == "seedance" else None


def make_call(run: Path, c: dict, cfg: dict, led: Ledger, people: dict) -> dict:
    """One call, end to end, resume-safe: each step that already landed is skipped."""
    ck = _load("clip_kit")
    lp = ck.lineparity
    run = Path(run)
    d = _kit().calls_dir(run) / c["id"]
    d.mkdir(parents=True, exist_ok=True)
    # a TAKE (make_picked) lands in its own folder and is never upscaled here — only the pick is (V6)
    raw = d / f"{c['id']}-raw.mp4"
    final = Path(c["final"]) if c.get("final") else run / "clips" / f"{c['id']}.mp4"
    st = led.get(c["id"])
    if st.get("status") == "done" and final.is_file():
        return st
    breaks = handoff_breaks([c])
    if breaks:
        raise RuntimeError("REFUSED " + breaks[0])
    start = cp.picture_file(run, c["start_frame"])
    if start is None:
        raise RuntimeError(f"{c['id']}: the picture {c['start_frame']} is not in media/ yet")
    # THE FACE GATE (2026-10-23): the picture's people must be their banked masters before it is animated — the face
    # lock below compares a clip with its picture, so a wrong picture passed it; this compares the picture with the bank
    FG = _load("face_gate")
    ms = FG.masters_for(run, c.get("people") or [])
    FG.require(start, ms or None, no_people=not (c.get("people") or []))
    k = None                                        # the fal key is read only if a paid upscale on fal is asked for
    # 1 · animate the approved picture — sent at 9:16 (providers.json direct.clip_route.start_picture)
    aspect = tuple((cfg.get("start_picture") or {}).get("aspect") or (9, 16))
    sent = to_aspect(start, d / f"start-{aspect[0]}x{aspect[1]}.png", aspect)
    ruled = seedance_ruling()
    if not ruled:
        raise RuntimeError(f"{c['id']}: the Model House has no Seedance clip ruling (models.json clips.ruled_2026_10_23)")
    if not raw.is_file():
        # DAMON'S RULING 2026-10-23 (components/generative-model-house MODEL-HOUSE.md, Clips): EVERY clip is Seedance 2.5
        # at 480p, upscaled locally; a talking clip goes with its locked read in the SAME call, so the mouth is built to the real words and
        # nothing is re-voiced after; cost never decides.
        SD = _load("seedance")
        t = time.time()
        people = c.get("people") or []
        sdp = (c.get("seedance") or {}).get("prompt")
        if not sdp:
            raise RuntimeError(f"{c['id']}: the plan carries no Seedance prompt — re-plan the run (clips_run.py plan)")
        for x in c.get("refs") or []:
            if x.get("kind") == "movement":          # a real person's movement: prepared here, free, the first time
                _load("movement").make(run, x, ck.ffmpeg_path())
        vids = [run / x["file"] for x in c.get("refs") or []]
        if any(not v.is_file() for v in vids):
            raise RuntimeError(f"{c['id']}: the blurred swipe refs are not made yet — run: clips_run.py refs {run}")
        if c["talking"]:
            take, a_from, a_to = locked_read(run, c, d, ck)
            if a_from or a_to:
                cut = d / f"{c['id']}-read.wav"
                ck.run_cmd([ck.ffmpeg_path(), "-y", "-ss", f"{a_from}"] + (["-to", f"{a_to}"] if a_to else [])
                             + ["-i", str(take), "-ac", "1", "-ar", "44100", str(cut)])
                take = cut
            if _dur(take) < 2.0:
                # the model takes 2 to 15 s of audio a clip: a shorter line is padded with silence after it, never stretched
                padded = d / f"{c['id']}-read-padded.wav"
                ck.run_cmd([ck.ffmpeg_path(), "-y", "-i", str(take), "-af", "apad=whole_dur=2.2", "-ac", "1", "-ar", "44100",
                            str(padded)])
                take = padded
            line = " ".join(p["line"] for p in c.get("voice_parts") or [])
            try:
                res = SD.talk(line, sent, take, raw, seconds=None, masters=ms or None, no_people=not people,
                              resolution=ruled.get("resolution", SD.RES), prompt=sdp, videos=vids, model=clip_model(cfg))
            except (RuntimeError, SystemExit) as e:
                # a content-safety refusal with a real person's movement attached: the same take again without it
                mv = [run / x["file"] for x in c.get("refs") or [] if x.get("kind") == "movement"]
                if "nsfw" not in str(e).lower() or not mv:
                    raise
                vids = [v for v in vids if v not in mv]
                sdp = re.sub(r"\nVideo \d+ is a real person's movement only:[^\n]*", "", sdp)
                led.put(c["id"], movement_dropped=f"refused with it: {str(e)[:160]}")
                res = SD.talk(line, sent, take, raw, seconds=None, masters=ms or None, no_people=not people,
                              resolution=ruled.get("resolution", SD.RES), prompt=sdp, videos=vids, model=clip_model(cfg))
        else:
            end = (cp.picture_file(run, c["end_frame"]) if c.get("end_frame") and c.get("end_frame") != c.get("start_frame")
                   else None)
            res = SD.motion(sdp, sent, raw, seconds=c.get("duration"), end_still=end, masters=ms or None,
                            no_people=not people, resolution=ruled.get("resolution", SD.RES), whole=True, videos=vids, model=clip_model(cfg))
        led.put(c["id"], request_id=res.get("request_id"), raw=str(raw), seconds=round(_dur(raw), 2), engine="seedance",
                model=clip_model(cfg) or "seedance-2.5", model_path=res.get("model"), fallback=False, took_s=round(time.time() - t, 1),
                status="animated",
                voice="made in the same call as the picture (Seedance, ruled 2026-10-23)" if c["talking"] else None)
    return _ship(run, c, cfg, led, raw, start, sent, d, final, k, True, lambda: make_call(run, c, cfg, led, people))


def backup_enabled(cfg: dict) -> bool:
    return bool((cfg.get("backup") or {}).get("enabled"))


def _no_remake():
    raise RuntimeError("the face changed on the backup clip too — it is scored as it is")


def _voice_over(run: Path, c: dict, d: Path, led: Ledger) -> None:
    """A talking clip made by the backup is SILENT (Kling takes no audio): its line's locked read is cut to the clip's part and
    laid under it as an off-camera read. Not lip-synced — the ledger says so, and the edit finds the read in
    clips/fallback-voice.json."""
    ck = _load("clip_kit")
    take, a_from, a_to = locked_read(run, c, d, ck)
    out = Path(run) / "clips" / "offcam" / f"{c['id']}-voiceover.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    ck.run_cmd([ck.ffmpeg_path(), "-y"] + (["-ss", f"{a_from}"] if a_from else []) + (["-to", f"{a_to}"] if a_to else [])
               + ["-i", str(take), "-ac", "1", "-ar", "44100", str(out)])
    f = Path(run) / "clips" / "fallback-voice.json"
    rows = _read(f, []) or []
    rows = [r for r in rows if r.get("call") != c.get("take_of") or c["id"]] + [{
        "call": c.get("take_of") or c["id"], "scenes": c.get("scenes"), "file": str(out.relative_to(run)),
        "at": c.get("at"), "line": " ".join(p["line"] for p in c.get("voice_parts") or []), "lip_sync": False}]
    f.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    led.put(c["id"], voice_over=str(out), lip_sync=False)


def make_backup(run: Path, c: dict, cfg: dict, led: Ledger, people: dict, why: str) -> dict:
    """THE BACKUP CLIP (the owner, 2026-10-26): the same scene on Kling 4.0, because Seedance failed its takes, was refused or is
    down. Kling takes the approved start picture and no audio, so the clip is silent and a talking line goes under it as an
    off-camera read (_voice_over). The same gates, checks and upscale as any clip; the ledger says which model made it and why."""
    ck = _load("clip_kit")
    K = _load("kling")
    run = Path(run)
    kp = (c.get("kling") or {}).get("prompt")
    if not kp:
        raise RuntimeError(f"{c['id']}: the plan carries no Kling prompt — re-plan the run (clips_run.py plan)")
    d = _kit().calls_dir(run) / c["id"]
    d.mkdir(parents=True, exist_ok=True)
    raw = d / f"{c['id']}-backup-raw.mp4"
    final = Path(c["final"]) if c.get("final") else run / "clips" / f"{c['id']}.mp4"
    breaks = handoff_breaks([c])
    if breaks:
        raise RuntimeError("REFUSED " + breaks[0])
    start = cp.picture_file(run, c["start_frame"])
    if start is None:
        raise RuntimeError(f"{c['id']}: the picture {c['start_frame']} is not in media/ yet")
    FG = _load("face_gate")
    ms = FG.masters_for(run, c.get("people") or [])
    FG.require(start, ms or None, no_people=not (c.get("people") or []))
    aspect = tuple((cfg.get("start_picture") or {}).get("aspect") or (9, 16))
    sent = to_aspect(start, d / f"start-{aspect[0]}x{aspect[1]}.png", aspect)
    end = (cp.picture_file(run, c["end_frame"]) if c.get("end_frame") and c.get("end_frame") != c.get("start_frame")
           and not c["talking"] else None)
    t = time.time()
    if not raw.is_file():
        res = K.motion(kp, sent, raw, seconds=c.get("duration"), end_still=end, masters=ms or None,
                       no_people=not (c.get("people") or []), resolution=(cfg.get("backup") or {}).get("resolution", K.RES))
        led.put(c["id"], request_id=res.get("request_id"), raw=str(raw), seconds=round(_dur(raw), 2), engine="kling",
                model="kling-4.0", model_path=res.get("path"), fallback=True, fallback_reason=str(why)[:300],
                lip_sync=False if c["talking"] else None, took_s=round(time.time() - t, 1), status="animated")
    if c["talking"]:
        _voice_over(run, c, d, led)
    return _ship(run, c, cfg, led, raw, start, sent, d, final, None, False, _no_remake)


def _ship(run: Path, c: dict, cfg: dict, led: Ledger, raw: Path, start: Path, sent: Path, d: Path, final: Path, k,
          in_clip_voice: bool, remake) -> dict:
    """Everything after a clip exists, whichever model made it: the line check (only when the voice is in the clip), the face
    lock, the frame-by-frame check, the last frame, the upscale. `remake` makes the clip again when the face changed."""
    ck = _load("clip_kit")
    lp = ck.lineparity
    shipped = raw
    # 2 · the voices said on camera. THE LOCKED READ IS THE VOICE (VIDEO-RULINGS V4): each line's own locked
    #     ElevenLabs v3 read goes into the same call as the picture — for a split part, only that part's own words of
    #     the read (P16). No locked read → the call STOPS; nothing is re-voiced (P15).
    if c["talking"] and in_clip_voice:
        # the voice was made with the picture (above): the line is checked, nothing is re-voiced
        if "line_check" not in led.get(c["id"]):
            led.put(c["id"], line_check=lp.check(raw, " ".join(p["line"] for p in c["voice_parts"]),
                                                 words_out=d / "transcript-words.json"), status="voiced")
        shipped = raw
    else:
        silent = d / f"{c['id']}-silent.mp4"
        if not silent.is_file():
            ck.run_cmd([ck.ffmpeg_path(), "-y", "-i", str(raw), "-an", "-c:v", "copy", str(silent)])
        shipped = silent
    # 3a · FACE LOCK — the person stays the person (eye colour vs the approved picture, the face model
    #      when it can answer). Off by more than the tolerance: remade once, then flagged. A TAKE is never
    #      remade here: the three takes are the guard, and a take whose face changed is not picked (P42).
    fl_cfg = cfg.get("face_lock") or {}
    if fl_cfg and c.get("people") and "face_lock" not in led.get(c["id"]):
        fl = _load("face_lock")
        pk = fl.iris(start)
        ks = [fl.hue_key(x) for x in (fl.iris(f) for f in fl.frames(shipped)) if x]
        drift = round(max(abs(k - fl.hue_key(pk)) for k in ks), 3) if (pk and ks) else None
        # The eyes decide: Gemini reads the eye colour off a close crop of the face, in the
        # picture and in three frames; most frames the other colour = the person changed. (3 Oct: the
        # pixel eye number flagged 14 of 27 good clips — sunglasses, blinks, a second face; a
        # same-person question on whole frames passed the clips where Creator-A's eyes had gone brown.)
        ref = cp.picture_file(run, c.get("face_ref") or c["start_frame"]) or start
        held = fl.eyes_held(shipped, ref)
        judged = held["frames"]
        swapped = not held["ok"]
        ok = held["ok"]
        tries = int(led.get(c["id"]).get("face_tries", 0))
        if swapped and not c.get("take_of") and tries < int(fl_cfg.get("remakes", 1)):
            for f in (raw, d / f"{c['id']}-voiced.mp4", d / f"{c['id']}-silent.mp4"):
                if f.is_file():
                    f.rename(f.with_name(f.stem + f"-drift{tries + 1}" + f.suffix))
            led.put(c["id"], face_tries=tries + 1, status="remake: face changed", line_check=None)
            return remake()
        led.put(c["id"], face_lock={"eyes": held, "eye_drift_note": drift, "ok": ok, "tries": tries})
    # 3 · the frame-by-frame check
    if "qc" not in led.get(c["id"]):
        cmd = [sys.executable, str(HERE / "clip_qc.py"), str(shipped), "--picture", str(sent),
               "--sheet", str(d / f"{c['id']}-qc.jpg")]
        if c["talking"] and in_clip_voice:
            cmd += ["--voice", str(shipped)]
        if c["refs"]:
            cmd += ["--swipe", str(run / c["refs"][0]["file"])]
        q = subprocess.run(cmd, capture_output=True, text=True).stdout
        led.put(c["id"], qc=json.loads(q) if q.strip() else None)
    # 4 · the last frame — only a call with nobody on screen ever starts from it (no hand-offs for people)
    if not c.get("people"):
        cp.last_frame(shipped, run / "media" / f"{c['id']}-LAST.png")
    # 5 · a TAKE ships as made (360p): only the PICKED take is upscaled, by make_picked (VIDEO-RULINGS V6)
    if c.get("defer_upscale"):
        if not final.is_file():
            final.parent.mkdir(parents=True, exist_ok=True)
            ck.run_cmd([ck.ffmpeg_path(), "-y", "-i", str(shipped), "-c", "copy", str(final)])
    else:
        finish(run, c, cfg, led, shipped, final, d, k)
    # the edit hand-off (clip_publish) runs once, in run_live, after every clip — never once per clip (P45)
    led.put(c["id"], file=str(final), status="done")
    return led.get(c["id"])


def finish(run: Path, c: dict, cfg: dict, led: Ledger, shipped: Path, final: Path, d: Path, key=None) -> None:
    """The clip as it ships: at 1080p (or with upscale_below_1080p off) as made; else upscaled — on this Mac
    (`upscale_where: local`, Real-ESRGAN, free) — with our own sound put back."""
    ck = _load("clip_kit")
    if final.is_file() and final.stat().st_mtime >= Path(shipped).stat().st_mtime:
        return                                            # already finished from this take; a newer pick is finished again
    final.parent.mkdir(parents=True, exist_ok=True)
    # NO UPSCALE WHILE SCENES ARE BEING DIALLED IN (2026-10-28: scene by scene first,
    # finishing comes later): the kept take is the clip as made; sharpening is a hand-off step
    if cfg["resolution"] in ("1080p", "4k") or not cfg.get("upscale_below_1080p", True) or not cfg.get("upscale_on_keep", True):
        ck.run_cmd([ck.ffmpeg_path(), "-y", "-i", str(shipped), "-c", "copy", str(final)])
        return
    if cfg.get("upscale_where") == "local":
        big = upscale_local(shipped, d / f"{c['id']}-up.mp4", cfg)
        if c["talking"]:
            ck.remux(big, shipped, final)
        else:
            ck.run_cmd([ck.ffmpeg_path(), "-y", "-i", str(big), "-an", "-c:v", "copy", str(final)])
        led.put(c["id"], upscale="local", upscale_usd=0.0)
        return
    raise SystemExit(f"{c['id']}: the upscale runs on this Mac only (direct.clip_route.upscale_where is 'local'); got {cfg.get('upscale_where')!r}")


# ------------------------------------------------------------ three takes, scored, the best picked (P4, V5/V6)

def heard(f: Path) -> dict:
    """MEASURED: does the take carry sound, and how loud (2026-10-28: a take came back with no voice). A talking take with no audio stream, or one quieter than -45 dB on average, has no voice."""
    import re as _re
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                         "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    if pr.returncode:
        return {}                                        # not a file ffprobe can read: not measured
    has = bool(pr.stdout.strip())
    if not has:
        return {"audio": False, "mean_db": None}
    err = subprocess.run(["ffmpeg", "-v", "info", "-i", str(f), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = _re.search(r"mean_volume:\s*(-?[\d.]+) dB", err)
    return {"audio": True, "mean_db": float(m.group(1)) if m else None}


def score_take(row: dict, judged: dict, talking: bool) -> dict:
    """One take's standing: it passes only when its words were heard (a talking take), its face held, and the
    clip judge passed it; its score is the judge's. A take that failed to make scores nothing."""
    why = []
    lc = row.get("line_check") or {}
    if talking and (lc.get("verdict") not in ("PASS",)):
        why.append(f"words: {lc.get('verdict') or 'not checked'} (match {lc.get('match')})")
    fl = row.get("face_lock") or {}
    if fl and fl.get("ok") is False:
        why.append("the face changed")
    snd = row.get("heard") or {}
    if talking and snd and (not snd.get("audio") or (snd.get("mean_db") is not None and snd["mean_db"] < -45)):
        why.append("no voice: the take has no sound" if not snd.get("audio") else f"no voice: the take is silent ({snd['mean_db']} dB)")
    body = row.get("body") or {}
    if body and body.get("ok") is False:
        # THE BODY CHECK (2026-10-28: an extra arm or a wrong-sized hand): a hard fail
        why.append("body: " + ("; ".join(body.get("problems") or [])[:300] or "an extra arm or hand, or a wrong-sized hand"))
    if not judged.get("pass"):
        why.append("clip judge: " + ("; ".join(str(p.get("what")) for p in judged.get("problems") or [])[:300]
                                     or f"score {judged.get('score')}"))
    return {"score": round(float(judged.get("score") or 0), 2), "pass": not why, "why": why,
            "stop_power": float(judged.get("stop_power") or 0), "judge": judged}


def best_attempt(takes: list[dict]) -> dict | None:
    """The attempt to keep when none passed: of those that made a clip, the highest score; a tie goes to the later one."""
    made = [(i, t) for i, t in enumerate(takes) if t.get("file") and Path(str(t["file"])).is_file()]
    return max(made, key=lambda it: (it[1]["score"], it[0]))[1] if made else None


def pick(takes: list[dict]) -> dict | None:
    """The best take that passed: the highest score, the earliest take on a tie. None when nothing passed."""
    ok = [t for t in takes if t.get("pass")]
    # equal quality: the take that stops a thumb harder wins (stop-power, V24), then the earliest, the locked read
    return max(ok, key=lambda t: (t["score"], float(t.get("stop_power") or 0), -t["take"])) if ok else None


_SLOTS: dict = {}


def _in_flight(cfg: dict):
    """One cap on clip / words / judge calls in flight across every clip of the run (P54, providers.json
    clip_route.in_flight); a 429 backs off inside each door."""
    n = int(cfg.get("in_flight") or 12)
    with LOCK:
        if n not in _SLOTS:
            _SLOTS[n] = threading.BoundedSemaphore(n)
        return _SLOTS[n]


def make_picked(run: Path, c: dict, cfg: dict, led: Ledger, people: dict, make=None, judge=None) -> dict:
    """UP TO THE CONFIGURED MAXIMUM OF ATTEMPTS, EVERY ONE SCORED, THE BEST ONE KEPT (VIDEO-RULINGS V34). Each attempt goes
    through the whole line (the voice made with the picture, words heard, face held, clip_qc) into clips/<calls dir>/<call>/
    takes/ and is scored by the clip judge; when none passes, the backup is the last rung. The chain then keeps the best
    scoring attempt that exists (a tie goes to the later one), marks it `below_criteria` with the plain list of checks it
    failed when it did not pass, and moves on — only the kept one is upscaled (locally). All attempts, scores and the kept
    one go in the clip ledger; the flag travels to the edit. Only when no attempt produced a file at all is there
    nothing to keep. With `takes` 1 and no `max_tries` it is the single call."""
    n = int(cfg.get("takes") or 1)
    tries = max(n, int(cfg.get("max_tries") or n))
    make = make or make_call
    if tries <= 1 and not c.get("take_round"):          # a press on the board is still judged and shown (2026-10-28)
        try:
            return make(run, c, cfg, led, people)
        except RuntimeError as e:
            if not backup_enabled(cfg) or "REFUSED" in str(e) or str(e).startswith(f"{c['id']}: the picture"):
                raise
            return make_backup(run, c, cfg, led, people, f"Seedance did not make it: {e}")
    run = Path(run)
    final = run / "clips" / f"{c['id']}.mp4"
    st = led.get(c["id"])
    if st.get("status") == "done" and final.is_file() and not c.get("take_round"):
        return st                                        # a new round (a press on the board) always makes new takes
    d = _kit().calls_dir(run) / c["id"]
    tk = d / "takes"
    tk.mkdir(parents=True, exist_ok=True)
    scenes = {s.get("id"): s for s in (_read(run / "plan.json", {}) or {}).get("scenes") or []}
    start = cp.picture_file(run, c["start_frame"])
    judge = judge or _load("clip_judge").judge
    r0 = (int(c.get("take_round") or 1) - 1) * tries      # a new round (V2_EXTRA_TAKES) makes new takes, never re-judges
    slots = _in_flight(cfg)

    def held(fn, *a):
        with slots:
            return fn(*a)

    def one_take(t):
        tid = f"{c['id']}-t{t}"
        tc = {**c, "id": tid, "take_of": c["id"], "final": str(tk / f"{tid}.mp4"), "defer_upscale": True}
        try:
            row = held(make, run, tc, cfg, led, people) or {}
        except Exception as e:                          # noqa: BLE001 — one take failing never stops the next
            out = {"take": t, "id": tid, "score": 0.0, "pass": False, "why": [f"not made: {e}"[:300]]}
            led.put(tid, verdict=out)                   # every try keeps its own verdict: the board shows it per try
            return out
        f = Path(row.get("file") or tc["final"])
        judged = held(judge, run, f, c, scenes, start) if f.is_file() else {"score": 0, "pass": False,
                                                                           "problems": [{"what": "no file"}]}
        row = {**row, "heard": heard(f) if f.is_file() else {},
               "body": held(_load("body_check").check, run, f, f"{tid}-body") if f.is_file() else {}}
        out = {"take": t, "id": tid, "file": str(f), "heard": row["heard"], "body": row["body"],
               **score_take(row, judged, bool(c.get("talking")))}
        led.put(tid, verdict={k: v for k, v in out.items() if k != "judge"}, judge=judged)
        return out

    takes, t = [], r0
    while True:                                          # n at once; the next n only when none of them passed (V34)
        with cf.ThreadPoolExecutor(max_workers=n) as ex:
            takes += list(ex.map(one_take, range(t + 1, t + n + 1)))
        t += n
        best = pick(takes)
        if best is not None or t - r0 >= tries:
            break
    picks = _read(run / "clips" / "picks.json", {}) or {}
    # a talking clip never goes to the backup: the backup takes no audio, so its clip has no voice (2026-10-28)
    if best is None and backup_enabled(cfg) and not c.get("take_of") and not c.get("talking"):
        # THE BACKUP (V45): three takes failed or Seedance was refused or down — the same scene on Kling, judged the same way
        why = " | ".join(f"t{x['take']}: {'; '.join(x.get('why') or [])}" for x in takes)[:300]
        bid = f"{c['id']}-bk"
        bc = {**c, "id": bid, "take_of": c["id"], "final": str(tk / f"{bid}.mp4"), "defer_upscale": True}
        try:
            row = held(make_backup, run, bc, cfg, led, people, why) or {}
            bf = Path(row.get("file") or bc["final"])
            judged = held(judge, run, bf, c, scenes, start) if bf.is_file() else {"score": 0, "pass": False,
                                                                                 "problems": [{"what": "no file"}]}
            row = {**row, "heard": heard(bf) if bf.is_file() else {}}
            bk = {"take": "backup", "id": bid, "file": str(bf), "heard": row["heard"],
                  **score_take(row, judged, bool(c.get("talking")))}   # a silent backup of a talking clip has no voice
        except (Exception, SystemExit) as e:           # noqa: BLE001 — a backup that cannot be made is one more failed attempt
            bk = {"take": "backup", "id": bid, "score": 0.0, "pass": False, "why": [f"backup not made: {e}"[:300]]}
        takes.append(bk)
        led.put(bid, verdict={k: v for k, v in bk.items() if k != "judge"}, judge=bk.get("judge"))
        if bk["pass"]:
            best = bk
    below = best is None
    if below:                                           # nothing passed: keep the best-scoring attempt that exists
        best = best_attempt(takes)
    rec = {"takes": [{k: v for k, v in x.items() if k != "judge"} | {"judge_score": (x.get("judge") or {}).get("score")}
                     for x in takes], "at": now()}
    if best is None:
        picks[c["id"]] = {**rec, "picked": None}
        (run / "clips" / "picks.json").write_text(json.dumps(picks, indent=1, ensure_ascii=False) + "\n")
        led.put(c["id"], status="failed", takes=rec["takes"])
        raise RuntimeError(f"{c['id']}: no attempt made a clip (" + " | ".join(
            f"t{x['take']}: {'; '.join(x.get('why') or [])}" for x in takes)[:600] + ")")
    failed = list(best.get("why") or []) if below else []
    picks[c["id"]] = {**rec, "picked": best["take"], "score": best["score"], "below_criteria": below,
                      "failed_checks": failed}
    (run / "clips" / "picks.json").write_text(json.dumps(picks, indent=1, ensure_ascii=False) + "\n")
    finish(run, c, cfg, led, Path(best["file"]), final, d)
    tw = d.parent / best["id"] / "transcript-words.json"            # the picked take's word times are the clip's (the edit reads them)
    if tw.is_file():
        (d / "transcript-words.json").write_bytes(tw.read_bytes())
    src = led.get(best["id"])
    keep = {k: v for k, v in src.items() if k in ("line_check", "face_lock", "qc", "engine", "model", "model_path", "fallback",
                                                  "fallback_reason", "lip_sync", "voice_over")}
    led.put(c["id"], **keep, picked=best["take"], picked_score=best["score"], takes=rec["takes"],
            below_criteria=below, failed_checks=failed, file=str(final), status="done")
    record_spans(run, c, led)
    # no camera moves here: they wait for the edit (2026-10-28)
    return led.get(c["id"])


def keep_take(run: Path, call: dict, take_id: str, by: str, cfg: dict | None = None) -> dict:
    """A PERSON'S PICK (2026-10-28): the take a person chose on the board becomes the call's clip, whatever the scores
    said — finished the same way as the chain's own pick (upscaled locally, its word times carried)."""
    run = Path(run)
    workflow = _load("hook_workflow") if (run / "opening.json").is_file() else None
    state = None
    if workflow:
        workflow.require_clip(run, HERE.parents[2])
        state = workflow.inspect(run, HERE.parents[2])
        old_clip, old_ledger = workflow.clip_of(run, HERE.parents[2])
        if old_clip and old_clip.is_file():
            version = run / "versions" / ("clip-" + workflow.digest(old_clip))
            version.mkdir(parents=True, exist_ok=True)
            import shutil
            if not (version / "clip.mp4").exists(): shutil.copyfile(old_clip, version / "clip.mp4")
            workflow.write(version / "ledger.json", old_ledger)
            for name in ("clip-binding.json", "hook-clip-review.json", "clip-inputs.json"):
                if (run / name).is_file() and not (version / name).exists(): shutil.copyfile(run / name, version / name)
    cfg = cfg or route_cfg(None, call.get("format"))
    if workflow:
        # One requested element, one paid attempt. Review failures on the board.
        cfg = {**cfg, "takes": 1, "max_tries": 1, "backup": {"enabled": False}}
    led = Ledger(run)
    d = _kit().calls_dir(run) / call["id"]
    f = d / "takes" / f"{take_id}.mp4"
    if not f.is_file():
        raise FileNotFoundError(f"{take_id}: no such take")
    final = run / "clips" / f"{call['id']}.mp4"
    if final.is_file():
        final.rename(final.with_name(f"{final.stem}-was-{led.get(call['id']).get('picked') or 'old'}.mp4"))
    finish(run, call, cfg, led, f, final, d)
    tw = d.parent / take_id / "transcript-words.json"
    if tw.is_file():
        (d / "transcript-words.json").write_bytes(tw.read_bytes())
    picks = _read(run / "clips" / "picks.json", {}) or {}
    n = take_id.rsplit("-t", 1)[-1]
    picks[call["id"]] = {**(picks.get(call["id"]) or {}), "picked": int(n) if n.isdigit() else take_id,
                         "picked_by": by, "at": now()}
    (run / "clips" / "picks.json").write_text(json.dumps(picks, indent=1, ensure_ascii=False) + "\n")
    src = led.get(take_id)
    keep = {k: v for k, v in src.items() if k in ("line_check", "face_lock", "qc", "engine", "model", "model_path", "fallback",
                                                  "fallback_reason", "lip_sync", "voice_over")}
    nm = final.with_name(f"{call['id']}-nomoves.mp4")
    if nm.is_file():
        nm.unlink()                                      # the old keep's own copy; this keep gets its moves fresh
    led.put(call["id"], **keep, picked=picks[call["id"]]["picked"], picked_by=by, file=str(final), status="done")
    record_spans(run, call, led)
    # no camera moves here: they wait for the edit (2026-10-28)
    return led.get(call["id"])


def record_spans(run: Path, c: dict, led: "Ledger") -> list:
    """WHERE EACH LINE SITS IN THE KEPT CLIP (2026-10-28): the edit lays each on-camera line by its span inside the
    clip (edit_map spans_of); the 10-21 production change stopped writing them, so a full cut saw her talking with no
    voice. Found on the kept take's own words (clips/calls/<call>/transcript-words.json), no new transcription."""
    tw = _kit().calls_dir(run) / c["id"] / "transcript-words.json"
    if not tw.is_file():
        return []
    words = words_of({"words": json.loads(tw.read_text())})
    spans = find_lines(words, [p["line"] for p in c.get("voice_parts") or []])
    out = [tuple(x) if x else x for x in spans]       # the words' own times: the edit pads and joins them (edit_map)
    led.put(c["id"], spans=out)
    return out


def camera_on_kept(run: Path, call_id: str):
    """CAMERA MOVES ON THE KEPT CLIP (2026-10-28): the scene's planned punch-ins, gliding, full frame at both
    ends, cut into the clip the edit takes (camera_moves.on_kept). A failure here never loses the clip."""
    try:
        return _load("camera_moves").on_kept(run, call_id)
    except Exception as e:                               # noqa: BLE001
        print(f"{call_id}: camera moves not applied: {e}")
        return None


def make_clip(run: Path, call: dict, prompt: str | None = None, cfg: dict | None = None, people: dict | None = None,
              make=None, judge=None) -> dict:
    """ONE CLIP THROUGH THE WHOLE TAKE LOOP, for a caller outside the planner (the Prompt Bench). `call` is a call dict
    as `plan` writes it (or preview's `send`); `prompt`, when given, is sent exactly as written to Seedance in place of
    the built one. Up to the configured attempts on Seedance, then the Kling backup, each scored; the best is kept and
    flagged (V34). Spends money. -> {"file", "rung", "attempts": [...], "below_criteria": [...]}"""
    run = Path(run)
    workflow = _load("hook_workflow") if (run / "opening.json").is_file() else None
    state = None
    if workflow:
        workflow.require_clip(run, HERE.parents[2])
        state = workflow.inspect(run, HERE.parents[2])
        old_clip, old_ledger = workflow.clip_of(run, HERE.parents[2])
        if old_clip and old_clip.is_file():
            version = run / "versions" / ("clip-" + workflow.digest(old_clip))
            version.mkdir(parents=True, exist_ok=True)
            import shutil
            if not (version / "clip.mp4").exists(): shutil.copyfile(old_clip, version / "clip.mp4")
            workflow.write(version / "ledger.json", old_ledger)
            for name in ("clip-binding.json", "hook-clip-review.json", "clip-inputs.json"):
                if (run / name).is_file() and not (version / name).exists(): shutil.copyfile(run / name, version / name)
    cfg = cfg or route_cfg(None, call.get("format"))
    if workflow:
        # One requested element, one paid attempt. Review failures on the board.
        cfg = {**cfg, "takes": 1, "max_tries": 1, "backup": {"enabled": False}}
    c = {**call}
    if prompt is not None:
        c["seedance"] = {**(c.get("seedance") or {}), "prompt": prompt}
        c["prompt"] = prompt
    people = people if people is not None else people_of(run)[0]
    # A PRESS IS A NEW ROUND (2026-10-28): takes already on disk were made with an older prompt and inputs; reusing their
    # numbers re-judged them as this round's attempts and went straight to the backup without making one new take
    n = int(cfg.get("takes") or 1)
    tries = max(n, int(cfg.get("max_tries") or n))
    made = [int(m.group(1)) for f in list((_kit().calls_dir(run) / c["id"] / "takes").glob(f"{c['id']}-t*.mp4"))
            + list(_kit().calls_dir(run).glob(f"{c['id']}-t*")) for m in [re.search(r"-t(\d+)(?:\.mp4)?$", f.name)] if m]
    recovery = None
    if workflow:
        # A retry after a lost connection or failed post-processing resumes the
        # newest saved request until its output has been bound to the workflow.
        bound_at = (run / "clip-binding.json").stat().st_mtime if (run / "clip-binding.json").is_file() else 0
        requests = [p for p in _kit().calls_dir(run).glob(c['id'] + '*/' + c['id'] + '*.request.json')
                    if p.stat().st_mtime > bound_at and (_read(p, {}) or {}).get('state') not in
                    ('failed', 'nsfw', 'cancelled', 'canceled', 'error')]
        if requests:
            pending = max(requests, key=lambda p: p.stat().st_mtime)
            match = re.search(r'-t(\d+)$', pending.parent.name)
            recovery = int(match.group(1)) if match else 0
            if recovery: c['take_round'] = recovery
    if recovery is None and not c.get("take_round") and (made or (run / "clips" / f"{c['id']}.mp4").is_file()):
        c["take_round"] = (max(made) if made else 0) // tries + 1
        if not made:
            c["take_round"] = 2                          # a kept clip with no numbered takes (a backup): still a new round
    led = Ledger(run)
    row = make_picked(run, c, cfg, led, people, make=make, judge=judge)
    if workflow and row.get("file"):
        workflow.write(run / "clip-binding.json", {"sha256": workflow.digest(row["file"]),
            "frame_sha256": workflow.digest(run / "media/S1-F1.png"),
            "setup_signature": state["setup_signature"], "clip_signature": state["clip_signature"]})
    return {"file": row.get("file"), "rung": "kling-4.0" if str(row.get("picked")) == "backup" else "seedance-2.5",
            "attempts": row.get("takes") or [], "below_criteria": list(row.get("failed_checks") or []) if row.get("below_criteria") else []}


def make_tts(run: Path, t: dict, cfg: dict, led: Ledger) -> dict:
    """AN OFF-CAMERA LINE IS ITS LOCKED READ (VIDEO-RULINGS V4/V5, verify 2026-10-21 row 3): the same three reads,
    word check and lock every line gets at the voice step (voice.py → vo/<scene>.mp3, vo/locks.json; the audio gate
    vo/audio-check.json) — never a fresh read at clip time. The locked read gets the same crisp finish an on-camera
    read gets and is written where the edit reads it (`out`). A sound that is not a word, said by someone on camera,
    is cut out of that scene's locked read by its own window. No locked read, or one the audio gate failed: STOP."""
    ck = _load("clip_kit")
    run = Path(run)
    out = run / t["out"]
    key = f"tts-{Path(t['out']).stem}"
    if led.get(key).get("status") == "done" and out.is_file():
        return led.get(key)
    src = run / "vo" / f"{t['scene']}.mp3"
    if not src.is_file():
        raise RuntimeError(f"{t['scene']}: no locked read (vo/{t['scene']}.mp3) — every line, off camera too, is read "
                           "three times, word-checked and locked at the voice step first; nothing is read at clip time")
    heard = ((_read(run / "vo" / "audio-check.json", {}) or {}).get("scenes") or {}).get(t["scene"]) or {}
    if heard and heard.get("pass") is False:
        raise RuntimeError(f"{t['scene']}: the locked read failed its word check ("
                           + "; ".join(str(x) for x in heard.get("problems") or [])[:200] + ") — held, not shipped")
    out.parent.mkdir(parents=True, exist_ok=True)
    plain = out.with_name(out.stem + "-uncrisp.wav")
    a, z = (0.0, None)
    if t.get("sound") and Path(t["out"]).stem.endswith("-sound"):
        a, z = part_window(_read(run / "vo" / "timing.json", {}) or {}, t["scene"], t["text"])
        if z is None:
            raise RuntimeError(f"{t['scene']}: the sound '{t['text']}' has no window of its own in the locked read "
                               "(vo/timing.json) — it is not re-read; the voice step reads it as its own line")
    ck.run_cmd([ck.ffmpeg_path(), "-y", "-ss", f"{a}"] + (["-to", f"{z}"] if z else [])
                 + ["-i", str(src), "-ac", "1", "-ar", "44100", str(plain)])
    ck.crisp(plain, out)
    lock = (_read(run / "vo" / "locks.json", {}) or {}).get(t["scene"]) or {}
    led.put(key, file=str(out), at_in_ad=t["at"], chars=t["chars"], status="done",
            read=f"vo/{t['scene']}.mp3", locked_read=lock.get("locked"), window=[a, z] if z else None)
    return led.get(key)


def chains(calls: list[dict]) -> list[list[dict]]:
    """Calls that hang together by `after` run one after another; chains run side by side."""
    by, out, seen = {c["id"]: c for c in calls}, [], set()
    nxt = {}
    for c in calls:
        if c.get("after") in by:
            nxt[c["after"]] = c
    for c in calls:
        if c["id"] in seen or c.get("after") in by:
            continue
        ch, cur = [], c
        while cur and cur["id"] not in seen:
            ch.append(cur); seen.add(cur["id"]); cur = nxt.get(cur["id"])
        out.append(ch)
    return out


def run_live(run: Path, only: list[str] | None = None, parallel: int = 6, yes: bool = False,
             make=None, tts=None, refs=None, gate=None) -> int:
    run = Path(run)
    res = _read(run / "clips" / "plan.json", {}) or {}
    if res.get("route") != "seedance":
        print("no clips plan — run: run.py start … --clips first", file=sys.stderr)
        return 2
    if res.get("problems"):
        for p in res["problems"]:
            print(f"STOP {p}", file=sys.stderr)
        return 2
    cfg = route_cfg(None, res.get("format") or format_of(run, _read(run / "plan.json", {})))
    calls = [c for c in res["calls"] if not only or c["section_id"] in only or c["id"] in only]
    jobs = [t for t in res["tts"] if not only or t["section"] in only or t["scene"] in only]
    t = res["totals"]
    print(budget_line(t))
    # THE CLIP GATE (the owner, 2026-10-09: "a clean and clear gate that things need to go through") — nothing
    # spends until every picture, reference and prompt of these clips is green (machine/clip_gate.py)
    todo = [c for c in calls if not (led_has_done(run, c["id"]))]
    stop = (gate or _load("clip_gate").ready)(run, todo) if todo else []
    for s_ in stop:
        print(f"GATE {s_}", file=sys.stderr)
    if stop:
        print("held at the clip gate — python3 machine/clip_gate.py check <run>; nothing was spent", file=sys.stderr)
        return 2
    if not yes:
        print("LIVE run — spends money. Re-run with --yes to make them.", file=sys.stderr)
        return 1
    sb = _read(run / "storyboard.json", {}) or {}
    teardown = (HERE / sb["teardown"]).resolve() if sb.get("teardown") else Path(".")
    (refs or build_refs)(run, calls, cfg, teardown)
    led = Ledger(run)
    people, _ = people_of(run)
    make, tts = make or make_picked, tts or make_tts
    parallel = max(1, min(int(parallel), int(cfg.get("parallel", 6))))
    fails = []

    errors = {}

    def one_chain(ch):
        for c in ch:
            kept = led_has_done(run, c["id"])
            try:
                make(run, c, cfg, led, people)
                # a clip already made is KEPT and said so — "done" means it was made now (2026-10-09:
                # a remake printed "done" and made nothing); clip_gate.py remake moves it aside first
                print(f"  {c['id']}: " + ("already made — kept (clip_gate.py remake to make it again)"
                                          if kept else "made"), flush=True)
            except Exception as e:                      # a failed call stops its own chain only
                led.put(c["id"], status="failed", error=str(e)[:400])
                fails.append(f"{c['id']}: {e}")
                errors[c["id"]] = _why(e)
                return

    with cf.ThreadPoolExecutor(max_workers=parallel) as ex:
        list(ex.map(one_chain, chains(calls)))
        for j in jobs:
            try:
                tts(run, j, cfg, led)
            except Exception as e:
                fails.append(f"{j['scene']}: {e}")
    spent = round(sum(float(v.get("clip_usd") or 0) + float(v.get("upscale_usd") or 0) for v in led.d.values()), 2)
    print(f"done: {sum(1 for v in led.d.values() if v.get('status') == 'done')} made · ${spent} on clips · ledger {led.f}")
    try:                                                # the clips + their check results, where the edit reads them
        pub = _load("clip_publish").publish(run)
        print(f"edit hand-off: {len(pub['published'])} scene(s) in media/ with verdicts"
              + (f" · waiting: {pub['held']}" if pub["held"] else ""))
    except Exception as e:
        print(f"clips not handed to the edit: {e}", file=sys.stderr)
    try:                                                # how every voice attaches, for the page and the team
        _load("sound_map").main([str(run)])
    except Exception as e:
        print(f"sound map not written: {e}", file=sys.stderr)
    for f in fails:
        print(f"FAILED {f}", file=sys.stderr)
    # THE COUNT (2026-10-09: "we should not have missing clips") — every planned clip made, or INCOMPLETE,
    # each missing one named; a refusal is held against that exact request at the next gate
    cov = _load("clip_gate").coverage(run, errors)
    print(("COMPLETE" if cov["complete"] else "INCOMPLETE")
          + f" · {cov['planned'] - len(cov['missing'])}/{cov['planned']} clips made")
    for m in cov["missing"]:
        print(f"  MISSING {m['id']} ({m['section']}): {m['why'][:200]}", file=sys.stderr)
    # NO SLOP (2026-10-09: "this can't be happening anymore, no slop at all") — frames of every clip made in this
    # run read for words that are not words (a drawn label); each one is named, and the run is not clean
    slop = _load("clip_gate").frames_check(run, [c["id"] for c in calls]) if calls else {}
    for cid, held in slop.items():
        for h in held:
            print(f"  SLOP {cid} {h}", file=sys.stderr)
        prior = list(led.get(cid).get("failed_checks") or [])
        led.put(cid, below_criteria=True, failed_checks=prior + [f"words that are not words: {h}" for h in held])
    if slop:
        print(f"FLAGGED · {len(slop)} clip(s) carry words that are not words — kept, marked below criteria for the edit, which cuts and never covers (V15)", file=sys.stderr)
    return 1 if fails or not cov["complete"] else 0


def led_has_done(run: Path, cid: str) -> bool:
    row = (_read(_kit().ledger_path(run), {}) or {}).get(cid) or {}
    return row.get("status") == "done" and (Path(run) / "clips" / f"{cid}.mp4").is_file()


def _why(e) -> str:
    """The door's own words for a failure (Higgsfield answers with its message in the error), shortened."""
    return str(e)[:400]


# ------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the clips route (Seedance 2.5)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("run"); p.add_argument("--only")
    r = sub.add_parser("refs"); r.add_argument("run")
    q = sub.add_parser("publish"); q.add_argument("run")
    x = sub.add_parser("run"); x.add_argument("run"); x.add_argument("--only")
    x.add_argument("--parallel", type=int, default=6); x.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    if a.cmd == "plan":
        doc = _read(run / "plan.json", {}) or {}
        ns = argparse.Namespace(only=a.only, storyboard=False)
        return start(ns, run, doc, platform.registry())
    if a.cmd == "refs":
        res = _read(run / "clips" / "plan.json", {}) or {}
        sb = _read(run / "storyboard.json", {}) or {}
        made = build_refs(run, res.get("calls") or [], route_cfg(), (HERE / sb.get("teardown", ".")).resolve())
        print("\n".join(made) or "every blurred ref is already there")
        return 0
    if a.cmd == "publish":
        return _load("clip_publish").main([str(run)])
    only = [s.strip() for s in (a.only or "").split(",") if s.strip()] or None
    return run_live(run, only=only, parallel=a.parallel, yes=a.yes)


if __name__ == "__main__":
    sys.exit(main())
