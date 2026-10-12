"""THE OMNI CLIPS ROUTE (the owner, 2–3 Oct 2026) — the clips step on the ruled route.

The rulings (providers.json `ruling_2026_10_03*`, THE-CHAIN.md "Voices — where
they are made now"): every clip is Google Gemini Omni Flash 1.1 on fal, 1080p
(`direct.omni_route.resolution`; no upscale step at 1080p), 9:16, 3–10 whole
seconds a call. Omni never makes a picture: the pictures are
the approved GPT Image 2.5 pictures already in media/ (step 4.4); Omni only
ANIMATES them — the movement, the mouths, the speech.

  * talking / staged sections → `image-to-video`: the approved picture as the
    first frame (+ the end picture where the storyboard has one), the lines
    said ON CAMERA written into the prompt in quotes — Omni says them, lip sync
    built in;
  * sections that copy the swipe's movement with NOBODY of ours on screen →
    `reference-to-video`: the approved picture + up to 3 pieces of ≤3 s of the
    swipe's own footage for that span, ALWAYS heavily blurred (scale 720, gblur
    sigma 30) — raw swipe footage swapped in the real creator, so it is never
    sent. A person on screen is always `image-to-video` with the approved
    picture as the first frame (`lock_faces`); the movement is said in words;
  * a line is ON camera only when its speaker's face is in the clip's
    picture: the brief's `to_camera`, corrected per section (or per clip) by
    <run>/clips/on-camera.json. Off-camera lines are NOT in the clip — the
    person on camera listens, silent — they are read later by that person's
    cloned voice (ElevenLabs text-to-speech) and laid at their storyboard time;
  * each storyboard clip is its own window (the sum of its scenes), split at
    line boundaries into calls of ≤10 s, never padded to a round 10 (spare
    seconds make the model improvise laughs); NO HAND-OFFS FOR PEOPLE (3 Oct,
    providers.json ruling_2026_10_03_no_handoffs): a person on screen starts
    EVERY call from the section's approved picture, never from a call's last
    frame — only a call with nobody on screen may start from the real last
    frame of the call before, and a planned or live call that breaks this is
    refused; the person's identity words go in every prompt; cards, plates and the endcard
    get no clip; a reused section is not made twice; a cutaway's own picture
    is its own clip over the swipe shots it drives;
  * after each call (live, `run`): voice — the clip's words found by ONE
    transcript (word timings), each on-camera stretch turned into that
    person's cloned voice (ElevenLabs speech-to-speech) + the crisp finish,
    everything else silent → remux → line check → clip_qc.py → (only below
    1080p: upscale on fal, ByteDance "ugc", sound carried over). (No trim step
    for now — the owner 3 Oct: "focus on generating the clips".) Non-word sounds
    (mm-hmm, uh-huh, hmm, um) are never said in a clip: the person nods, lips
    closed, and the sound is its own track at the edit. Who says a line is the
    brief's `speaker` — a voiced line without one is refused.

Every slug, price and fixed sentence comes from providers.json
`direct.omni_route`; voice ids from each person's casting voice.json (the
run's elements.json → folder). This file names no model, brand or person.

    python3 machine/omni_clips.py plan <run> [--only G05,G12]   (= run.py start … --clips)
    python3 machine/omni_clips.py refs <run>                    local ffmpeg only: the blurred refs
    python3 machine/omni_clips.py run  <run> [--only …] [--parallel 6] --yes   LIVE — spends money
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
    """The route's settings; a format with its own row under `by_format` (a song ad:
    360p, upscaled locally, every section a clip — the owner 2026-10-10) is laid over them."""
    reg = reg if reg is not None else platform.registry()
    c = ((reg.get("direct") or {}).get("omni_route"))
    if not c:
        raise SystemExit("providers.json has no direct.omni_route — the Omni clips route reads every slug, "
                         "price and fixed sentence from there")
    over = ((c.get("by_format") or {}).get(fmt) or {}) if fmt else {}
    if over:
        c = {**c, **{k: v for k, v in over.items() if k != "ruled"}, "format": fmt}
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

COMPOSITION = re.compile(
    r"close-?up|medium (close|shot)|wide shot|two-shot|\bframing\b|\bframed\b|centred|centered|\bcrop|zoom|"
    r"push-?in|\d+\s*[–-]\s*\d+\s*%|in frame|out of frame|frame edge|edge of the frame|head and shoulders", re.I)


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
            # only a person who SPEAKS needs a voice (2026-10-07: the athlete's staff member
            # and press pack never say a word and held the clips); the per-line
            # checks below still stop any line whose speaker has none
            if it.get("speaks"):
                problems.append(f"{pid}: no cloned voice — {vf or 'no casting folder in elements.json'} has no voice_id")
            v = {}
        ident = identity_words(WORKSPACE / folder) if folder else ""
        out[pid] = {"noun": noun, "identity": ident, "pron": {"f": "she", "m": "he"}.get(g, "they"),
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
    at 360p with only a picture, Omni turned Nova's blue-grey eyes brown and moved her spots)."""
    spec = _read(Path(folder) / "spec.json", {}) or {}
    text = " ".join(str(v) for v in _walk_strings(spec))
    keep = []
    for part in re.split(r"(?<=[.;])\s+", text):
        if re.search(r"\beyes?\b|spot|freckl|mole|scar|tattoo|birthmark|\bbob\b|hair", part, re.I) and len(part) < 700:
            t = part.strip().rstrip(";.")
            if t and t not in keep:
                keep.append(t)
    return "; ".join(keep[:6])


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


# Sounds that are not words — "mm-hmm", "uh-huh", "hmm", "um". Omni mouths them badly (the owner, 3 Oct:
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
        out.append({**sc, "speaker": b["speaker"]} if b.get("speaker") and not sc.get("speaker") else sc)
    return out


def speaker_of(scene: dict, people: dict) -> str | None:
    """Who SAYS the line: the brief's own `speaker` (it matches the swipe's transcript) — and only
    that. Never whose hands or face are in the shot (`who`), never the voice map (`speaks`): 3 Oct,
    going by `who` put "A little glycolic peel." in Nova's mouth because the shot is NOVA's hands
    (in the swipe it is the doctor talking over the cut), and the voice map gave Nova's "Why?" to
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


def no_composition(text: str) -> str:
    """Drop every sentence or clause that restates framing — the approved
    picture carries the composition (2026-10-02: 'close-up' made the model zoom)."""
    parts = re.split(r"(?<=[.;])\s+|,\s+", text or "")
    return ", ".join(p.strip().rstrip(".;") for p in parts if p.strip() and not COMPOSITION.search(p)).strip()


def style_clean(text: str) -> str:
    """The style lock with any framing clause dropped (the picture carries the framing), its
    sentences kept as sentences."""
    out = []
    for sent in re.split(r"(?<=[.;])\s+", (text or "").strip()):
        end = sent[-1] if sent[-1:] in ".;" else "."
        parts = [p for p in re.split(r",\s+", sent.rstrip(".;")) if p.strip() and not COMPOSITION.search(p)]
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
# prompt still described her face spots, so Omni pushed in and painted a dark patch back onto the cheek
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


def build_prompt(call: dict, scenes: dict, people: dict, words: dict, style: str, lead: str | None) -> str:
    """The prompt, in the order that worked live (bench A and C, 3 Oct): keep
    the first frame; (the blurred clips, movement only); the camera; what
    happens and who says what, in order; hold still; the look; no text, no music."""
    W = words
    on_ids = [l["speaker"] for l in call["lines"] if l["on_camera"]]
    who_cam = on_ids[0] if on_ids else lead
    poss = people.get(who_cam, {}).get("poss", "their")
    # the run's style lock FIRST (2026-10-10: on the first song ad it came last, after the
    # rules, and the 3D-animated look was the first thing the model let go of)
    out = [style_clean(style)] if style and style_clean(style) else []
    out.append(W["keep"])
    start_scene = scenes.get(str(call.get("start_frame") or "").split("-")[0]) or {}
    even = scene_even(start_scene)
    idl = [f"{desc(pid, people, cap=True)} stays exactly the same person in every frame: "
           f"{identity_for(people[pid]['identity'], even, W, people[pid].get('poss', 'their'))}."
           for pid in call.get("people") or [] if people.get(pid, {}).get("identity")]
    if idl:
        out.append(" ".join(idl) + " " + W.get("identity_hold", ""))
    if call.get("end_frame"):
        out.append(W["keep_end"])
    n = len(call.get("refs") or [])
    if n:
        plural = n > 1
        out.append(_fill(W["refs"], videos="videos" if plural else "video", are="are" if plural else "is a",
                         clips="clips" if plural else "clip", them="them" if plural else "it"))
    cam = W["camera_" + call["camera"]]
    cam = _fill(cam, her=poss)
    if n:
        cam = _fill(W["camera_ref_prefix"], videos="videos" if n > 1 else "video") + " " + cam
    out.append(cam)
    body, done_happens, last_off = [], set(), False
    for l in call["lines"]:
        sc = scenes.get(l["scene"]) or {}
        if l.get("sound") and not l["on_camera"] and l.get("nod"):
            # a sound, not words: the brief's "murmurs"/"hums" would move the lips — only the nod is said
            body.append(_fill(W["nod"], who=desc(l["speaker"], people, cap=True)))
            last_off = False
            continue
        h = no_composition(swap_names(sc.get("happens"), people))
        who = no_composition(swap_names(sc.get("who"), people))
        talker_only = (not l["on_camera"] and "hand" not in str(sc.get("who") or "").lower()
                       and l["speaker"] and str(sc.get("who") or "").strip() == l["speaker"])
        # a beat cued on words (on "reach what your hands can't") goes to the part of a split line that SAYS
        # those words — 2026-10-08, the athlete S7: the gesture landed on part 1 ("that's the most important thing")
        # and Omni drew a hairbrush; an uncued beat stays on part 1
        cue = re.search(r'on ["\u201c]([^"\u201d]+)["\u201d]', str(sc.get("happens") or ""))
        part_ok = (_words_in(cue.group(1), l.get("text", "")) if cue and l.get("part")
                   else not str(l.get("part", "1/")).startswith(("2/", "3/", "4/")))
        if h and not talker_only and l["scene"] not in done_happens and part_ok:
            done_happens.add(l["scene"])
            s = f"{who} {h}".strip() if who else h
            body.append(s[:1].upper() + s[1:].rstrip(".") + ".")
        if l["on_camera"]:
            tone = tone_of(sc)
            body.append(_fill(W["speak"], who=desc(l["speaker"], people, cap=True),
                              tone=f" in a {tone} voice" if tone else "",
                              pos=people.get(l["speaker"], {}).get("poss", "their"),
                              line=l["text"].strip()))
            last_off = False
        elif not last_off:
            listeners = [p for p in call["people"] if p != l["speaker"]]
            if listeners:
                verb_s = len(listeners) == 1
                names = " and ".join(desc(p, people) for p in listeners)
                body.append(_fill(W["off"], visible=names, listen="listens" if verb_s else "listen",
                                  react="reacts" if verb_s else "react"))
            else:
                body.append(W["off_none"])
            last_off = True
    # a scene with no words still has its action (2026-10-10: every wordless clip of the first song
    # ad went out with no action line at all — the model was told only to keep the picture)
    for sid in call.get("scenes") or []:
        sc = scenes.get(sid) or {}
        if sid in done_happens or (sc.get("voice") or "").strip():
            continue
        h = no_composition(swap_names(sc.get("happens"), people))
        who = no_composition(swap_names(sc.get("who"), people))
        if h:
            s_ = f"{who} {h}".strip() if who and not h.lower().startswith(("she ", "he ", "they ")) else h
        else:
            # no `happens` written: the scene's first picture says what is there, and it comes alive
            ff = next((f for f in sc.get("frames") or [] if f.get("role") in (None, "first")), None) or sc.get("first_frame") or {}
            act = no_composition(swap_names(ff.get("action") or "", people))
            raw_subj = swap_names(ff.get("subject") or "", people)
            subj = no_composition(raw_subj) or raw_subj.strip()       # "a framed photo" is a thing, not framing
            alive = W.get("alive", "Everything in the picture moves gently and naturally: {subject}")
            s_ = act or (alive.format(subject=subj) if subj else alive.split(":")[0])
        if s_:
            done_happens.add(sid)
            body.append(s_[:1].upper() + s_[1:].rstrip(".") + ".")
    if body:
        out.append(" ".join(body))
    if any(l["on_camera"] for l in call["lines"]):
        out.append(W["hold"])
    else:
        out.append(W["silent"])
    out.append(W["finish"])
    return "\n\n".join(out)


# ------------------------------------------------------------ the plan

def _section_people(g: dict) -> list[str]:
    return [e.split(" · ")[1] for e in g.get("elements") or [] if e.startswith("person · ")]


def cut_from_footage(scene_ids, by_id: dict) -> bool:
    """Every scene of a section is CUT from our own footage (footage.py's gate,
    2026-10-05): the section is made from that footage, no clip is generated."""
    ids = [s for s in scene_ids or [] if s]
    return bool(ids) and all((by_id.get(s) or {}).get("source_plan") == "cut"
                             and (by_id.get(s) or {}).get("owned_file") for s in ids)


def plan(run: Path, sb: dict, scenes: list[dict], reg: dict | None = None, only: list[str] | None = None,
         cfg: dict | None = None, people: dict | None = None, style: str = "") -> dict:
    """-> {"calls", "sections", "tts", "totals", "problems"}. Pure: reads the
    run's files, writes nothing, calls nothing."""
    run = Path(run)
    cfg = cfg or route_cfg(reg)
    problems = []
    if people is None:
        people, pp = people_of(run)
        problems += pp
    by_id = {s["id"]: s for s in scenes}
    ov = overrides_of(run)
    span, max_s = cfg["seconds_range"], float(cfg["seconds_range"][1])
    res_ = cfg["resolution"]
    rate = float(cfg["usd_per_s"][res_])
    up_rate = float(cfg["upscale"]["usd_per_s"])
    up_on = bool(cfg.get("upscale_below_1080p", True))  # 2026-10-09: 720p ships as made
    lead = ((sb.get("people_map") or {}).get("lead") or [None])[0]
    want = None
    if only:
        want = set()
        for x in only:
            m = re.match(r"^(?:G|Section\s*)?0*(\d+)$", x.strip(), re.I)
            want.add(f"G{int(m.group(1)):02d}" if m else x.strip())
    voice_at = {v["scene"]: v["at"] for v in ((sb.get("layers") or {}).get("voice") or [])}
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
        if not g.get("clips"):
            row["note"] = "no clip — the approved picture is shown for its time"
            if cfg.get("every_section_a_clip") and g.get("maker") not in ("plate", "packshot edit", "endcard plate"):
                problems.append(f"{sbp.section_no(gid)} has no clip — every section of a {cfg.get('format') or 'this format'} "
                                f"is a clip, never a still or a hold (providers.json direct.omni_route.by_format)")
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
            t0 = min(a for a, _ in ts) if ts else 0.0
            t1 = max(z for _, z in ts) if ts else float(c.get("seconds") or 0)
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
                said, sound = split_sound(sc["voice"].strip())
                ln = {"scene": sid, "speaker": spk, "text": said or sc["voice"].strip(), "a": a, "z": z,
                      "on_camera": cam and bool(said)}
                if sound:
                    ln["sound"] = sound                 # on its own track at the edit, never in the clip
                    ln["nod"] = cam                     # the speaker is on screen: a nod, lips closed
                sec_lines.append(ln)
            parts = split_calls(sec_lines, u["t0"], u["t1"], max_s, float(span[0]))
            for pi, (a, z, ls) in enumerate(parts):
                call_id = u["cid"] + (f"-{pi + 1}" if len(parts) > 1 else "")
                # the set-up this clip is in: the picture of the latest set-up at or before its first scene
                setup_pic = None
                order = list(g.get("scenes") or [])
                first_sc = (ls[0]["scene"] if ls else None) or (u.get("scenes") or [None])[0]
                for spic in pics.get("setups") or []:
                    if first_sc in order and spic["scene"] in order and order.index(spic["scene"]) <= order.index(first_sc):
                        setup_pic = spic["id"]
                if u["chain"] and g_people:
                    # ROOT CAUSE, 3 Oct (Nova): a clip started from the clip before's last frame copies a
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
                refs = ref_pieces(wins, shots, a, z, u["keep"], cfg["refs"]) if movement else []
                if refs and _section_people(g):
                    refs = []        # a person on screen: lock the approved picture as the first frame (always)
                endpoint = "reference-to-video" if refs else "image-to-video"
                in_shots = [shots[k] for k, x, y in wins if y > a + 0.01 and x < z - 0.01 and
                            (u["keep"] is None or k in u["keep"])]
                seconds = round(z - a, 2)
                # nobody speaks on camera here: the clip only has to MOVE, not hold a line — made shorter and
                # played slower at the edit (providers.json silent_share; never below the edit's 0.75x)
                silent = not any(l["on_camera"] for l in ls)
                share = max(0.75, min(1.0, float(cfg.get("silent_share") or 1.0))) if silent else 1.0
                dur = billed(seconds * share, span)
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
                    # THE CLIP'S OWN PEOPLE (2026-10-08, the athlete): the brief names who is in each scene's frame
                    # (`looks`); describing everyone in the section had Omni bring the staff member — in S2 only —
                    # into every later clip, and pull back to show the press. Fallback: the section's people.
                    "people": clip_people(g_people, [l["scene"] for l in ls_in] or (u.get("scenes") or []), by_id, lead),
                    "lines": [{k: l[k] for k in ("scene", "speaker", "text", "on_camera", "at", "until")}
                              | ({"part": l["part"]} if l.get("part") else {})
                              | ({"sound": l["sound"], "nod": l["nod"]} if l.get("sound") else {}) for l in ls_in],
                    "refs": [{**r, "file": f"clips/refs/{call_id}-ref{i + 1}.mp4"} for i, r in enumerate(refs)],
                }
                call["talking"] = any(l["on_camera"] for l in call["lines"])
                call["voice_parts"] = [{"scene": l["scene"], "person": l["speaker"], "line": l["text"],
                                        "voice_id": (people.get(l["speaker"]) or {}).get("voice_id")}
                                       for l in call["lines"] if l["on_camera"]]
                call["prompt"] = build_prompt(call, by_id, people, cfg["words"], style, lead)
                call["params"] = {"prompt": call["prompt"], "duration": dur, "aspect_ratio": cfg["aspect_ratio"],
                                  "resolution": res_}
                call["usd"] = round(dur * rate, 4)
                call["upscale_usd"] = (0.0 if res_ in ("1080p", "4k") or not up_on or cfg.get("upscale_where") == "local"
                                       else round(seconds * up_rate, 4))
                call["upscale"] = (None if res_ in ("1080p", "4k") or not up_on else
                                   "local" if cfg.get("upscale_where") == "local" else "fal")
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
                    "model_id": p.get("model_id") or cfg["tts"]["model_id"], "settings": p.get("settings") or {},
                    "out": f"clips/offcam/{sid_out}.mp3", "finish": "crisp", "chars": len(l["text"])})
    totals = {"calls": len(calls), "omni_seconds": sum(c["duration"] for c in calls),
              "omni_usd": round(sum(c["usd"] for c in calls), 2),
              "upscale_seconds": round(sum(c["seconds"] for c in calls if c["upscale_usd"]), 2),
              "upscale_usd": round(sum(c["upscale_usd"] for c in calls), 2),
              "talking_calls": sum(1 for c in calls if c["talking"]),
              "voice_swaps": sum(len(c["voice_parts"]) for c in calls),
              "tts_lines": len(tts), "tts_chars": sum(t["chars"] for t in tts)}
    totals["fal_usd"] = round(totals["omni_usd"] + totals["upscale_usd"], 2)
    problems += handoff_breaks(calls)
    return {"route": "omni", "format": cfg.get("format"), "calls": calls, "sections": rows, "tts": tts,
            "totals": totals, "problems": problems, "overrides": ov}


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
    s = [f"animate: Omni {call['endpoint']} on fal, {call['duration']} s, from the approved picture "
         f"{call['start_frame']}" + (f" to {call['end_frame']}" if call.get("end_frame") else "")]
    if call["talking"]:
        who = ", ".join(sorted({p["person"] or "?" for p in call["voice_parts"]}))
        s += [f"voice: one transcript (word timings) → each on-camera line turned into {who}'s cloned voice "
              "(ElevenLabs speech-to-speech) + crisp finish; everything else silent",
              "remux: the new sound on the untouched video",
              "line check: every on-camera word heard"]
    else:
        s.append("sound: none kept (silent clip; the cut carries the sound)")
    s.append("clip_qc.py: framing · scene · camera · lips")
    if call.get("upscale") == "local":
        s.append("upscale: on this Mac (local-studio upscale, Real-ESRGAN) → 1080x1920, no cost")
    elif call.get("upscale_usd"):
        s.append("upscale: fal ByteDance → 1080p (ugc), sound carried over")
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
         "| Endpoint | Start → end picture | Blurred refs | Omni $ | Upscale $ |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["sections"]:
        if not r["calls"]:
            L.append(f"| {r['n']} | {r['what']} | — | — | — | {r['seconds']} | — | — | — | 0 | 0 — {r['note']} |")
            continue
        for cid in r["calls"]:
            c = calls[cid]
            refs = ", ".join(f"{x['shot']}@{x['from']}+{x['seconds']}s" for x in c["refs"]) or "—"
            L.append(f"| {r['n']} | {r['what']} | {_lines_cell(c, True)} | {_lines_cell(c, False)} | {cid} "
                     f"({c['clip_is']}) | {c['seconds']} ({c['duration']}) | {c['endpoint']} | "
                     f"{c['start_frame']} → {c['end_frame'] or '—'} | {refs} | {c['usd']:.2f} | {c['upscale_usd']:.3f} |")
    return L


def budget_line(t: dict) -> str:
    return (f"BUDGET · Omni {t['omni_seconds']} s = ${t['omni_usd']:.2f} · upscale {t['upscale_seconds']} s = "
            f"${t['upscale_usd']:.2f} · fal total ${t['fal_usd']:.2f} · plus ElevenLabs: {t['voice_swaps']} on-camera "
            f"voice swap(s) in {t['talking_calls']} talking clip(s) and {t['tts_lines']} off-camera line(s) "
            f"({t['tts_chars']} characters)")


def prompts_md(run: Path, res: dict, cfg: dict) -> str:
    t = res["totals"]
    L = [f"# Clips — the Omni route · {t['calls']} call(s)", "",
         "The pictures are the approved GPT Image 2.5 pictures in `media/` (step 4.4). Omni does not make "
         "pictures: it only animates the approved picture — the movement, the mouths and the speech. "
         f"Every call is Omni Flash 1.1 on fal at {cfg['resolution']}, {cfg['aspect_ratio']}, 3–10 whole seconds. "
         "Lines said ON camera are in the prompt (Omni says them; each person's cloned voice is swapped in after); "
         "lines said OFF camera are not in the clip — they are read by the cloned voice and laid on their own track. "
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
              f"- **model**: {c['model']} on fal · {c['duration']} s billed for a {c['seconds']} s window · "
              f"{c['params']['resolution']} · {c['params']['aspect_ratio']} · ${c['usd']:.2f}",
              f"- **blurred swipe refs**: " + (", ".join(f"`{x['file']}` = {x['shot']} from {x['from']} s, {x['seconds']} s"
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
    scenes = with_speakers(run, sb_doc, plan_doc.get("scenes") or [])
    unnamed = [sc.get("id") for sc in scenes if str(sc.get("voice") or "").strip() and not sc.get("speaker")]
    if unnamed:
        # never guess a voice from whose hands are in the shot (3 Oct: the doctor's line went to Nova)
        print(f"REFUSED --clips: the brief names no speaker for {', '.join(unnamed)} — "
              "every spoken line needs its `speaker` from the swipe's transcript", file=sys.stderr)
        return 2
    res = plan(run, sb_doc, scenes, reg, only=only, cfg=cfg, style=style_line(run, plan_doc))
    for p in res["problems"]:
        print(f"STOP {p}", file=sys.stderr)
    print(f"clips (Omni route): {len(res['calls'])} call(s) — every one animates an approved picture; "
          f"{', '.join(sorted({c['model'] for c in res['calls']}))}")
    print_table(res)
    print()
    print(budget_line(res["totals"]))
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
    print(f"to make them (LIVE, spends ≈ ${res['totals']['fal_usd']:.2f} on fal + ElevenLabs): "
          f"python3 {HERE / 'omni_clips.py'} run {run} --yes")
    return 0


# ------------------------------------------------------------ live: the runner (not run by plan / dry runs)

LOCK = threading.Lock()


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
        self.f = Path(run) / "clips" / "omni-ledger.json"
        self.run = Path(run)
        self.d = _read(self.f, {}) or {}

    def get(self, cid):
        return self.d.get(cid) or {}

    def put(self, cid, **kw):
        with LOCK:
            self.d.setdefault(cid, {}).update(kw, at=now())
            self.f.parent.mkdir(parents=True, exist_ok=True)
            self.f.write_text(json.dumps(self.d, indent=1) + "\n")

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
    """The picture as sent to Omni: cut to the aspect (2026-10-10 — at 360p Omni refused ~14 clips of
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
    format's target height (a song ad: 360p → 1080x1920, the owner 2026-10-10). No money spent."""
    up = cfg.get("upscale_local") or {}
    launcher = WORKSPACE / up.get("launcher", "components/local-studio/local.py")
    h = _height(clip)
    scale = max(2, int(round(int(up.get("target_height", 1920)) / h))) if h else 3
    runner = runner or (lambda cmd: subprocess.run(cmd, check=True))
    runner([sys.executable, str(launcher), "upscale", str(clip), "-o", str(out), "--scale", str(scale),
            "--engine", up.get("engine", "esrgan")])
    return out


def make_call(run: Path, c: dict, cfg: dict, led: Ledger, people: dict) -> dict:
    """One call, end to end, resume-safe: each step that already landed is skipped."""
    omni = _load("omni")
    pf, lp = omni.providers_fal, omni.lineparity
    run = Path(run)
    d = run / "clips" / "omni" / c["id"]
    d.mkdir(parents=True, exist_ok=True)
    raw, final = d / f"{c['id']}-raw.mp4", run / "clips" / f"{c['id']}.mp4"
    st = led.get(c["id"])
    if st.get("status") == "done" and final.is_file():
        return st
    breaks = handoff_breaks([c])
    if breaks:
        raise RuntimeError("REFUSED " + breaks[0])
    start = cp.picture_file(run, c["start_frame"])
    if start is None:
        raise RuntimeError(f"{c['id']}: the picture {c['start_frame']} is not in media/ yet")
    k = omni.fal_key_of()
    if not k:
        raise SystemExit("no FAL_KEY in the environment or the Keychain")
    # 1 · animate the approved picture — sent at 9:16 (providers.json direct.omni_route.start_picture)
    aspect = tuple((cfg.get("start_picture") or {}).get("aspect") or (9, 16))
    sent = to_aspect(start, d / f"start-{aspect[0]}x{aspect[1]}.png", aspect)
    if not raw.is_file():
        body = dict(c["params"])
        if c["endpoint"] == "reference-to-video":
            body["image_urls"] = [_data_url(sent)]
            body["reference_video_urls"] = [_data_url(run / x["file"]) for x in c["refs"]]
        else:
            body["image_url"] = _data_url(sent)
            if c.get("end_frame"):
                body["end_image_url"] = _data_url(to_aspect(cp.picture_file(run, c["end_frame"]),
                                                            d / f"end-{aspect[0]}x{aspect[1]}.png", aspect))
        t = time.time()
        sub = pf.submit(c["model"], body, k, pf.http_transport)
        res = pf.wait(sub["status_url"], sub["response_url"], k, pf.http_transport, c["model"])
        pf.fetch(pf.media_urls(res)[0], raw)
        secs = _dur(raw)
        usd = round(c["duration"] * float(cfg["usd_per_s"][cfg["resolution"]]), 4)
        led.put(c["id"], request_id=sub.get("request_id"), raw=str(raw), seconds=round(secs, 2), omni_usd=usd,
                took_s=round(time.time() - t, 1), status="animated")
        led.spend(c["id"], c["model"], c["duration"], usd, cfg["resolution"])
    shipped = raw
    # 2 · the voices said on camera — from ONE transcript (word timings)
    if c["talking"]:
        voiced = d / f"{c['id']}-voiced.mp4"
        if not voiced.is_file():
            native = d / "native.wav"
            omni.run_cmd([omni.ffmpeg_path(), "-y", "-i", str(raw), "-vn", "-ac", "1", "-ar", "44100",
                          "-c:a", "pcm_s16le", str(native)])
            ek = lp.key_of()
            boundary = lp._boundary()
            body = lp._multipart_body({"model_id": lp.STT_MODEL_ID, "timestamps_granularity": "word"},
                                      [("file", native)], boundary)
            stt, _h, out = lp.http_transport("POST", lp.ELEVEN_STT, {"xi-api-key": ek,
                                             "Content-Type": f"multipart/form-data; boundary={boundary}"}, body)
            if stt is None or stt >= 400:
                raise RuntimeError(f"{c['id']}: speech-to-text {stt}: {out[:200]!r}")
            words = words_of(json.loads(out.decode()))
            (d / "transcript-words.json").write_text(json.dumps(words, indent=1))
            spans = find_lines(words, [p["line"] for p in c["voice_parts"]])
            total = _dur(native)
            segs = []
            for n, (p, s) in enumerate(zip(c["voice_parts"], spans)):
                if not s:
                    continue
                a0, z0 = max(0.0, s[0] - 0.08), min(total, s[1] + 0.08)
                seg = d / f"seg{n}.wav"
                omni.run_cmd([omni.ffmpeg_path(), "-y", "-ss", f"{a0:.3f}", "-t", f"{z0 - a0:.3f}", "-i", str(native),
                              "-c:a", "pcm_s16le", str(seg)])
                segs.append((a0, omni.revoice_file(seg, p["voice_id"], d / f"seg{n}-v.mp3", key=ek)))
            ins, flt = [], []
            for n, (a0, f) in enumerate(segs):
                ins += ["-i", str(f)]
                flt.append(f"[{n}:a]adelay={int(a0 * 1000)}|{int(a0 * 1000)}[d{n}]")
            ins += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=44100:cl=mono"]
            fc = ";".join(flt) + (";" if flt else "") + "".join(f"[d{n}]" for n in range(len(segs))) + \
                f"[{len(segs)}:a]amix=inputs={len(segs) + 1}:normalize=0[o]"
            mixed = d / "mixed.wav"
            omni.run_cmd([omni.ffmpeg_path(), "-y", *ins, "-filter_complex", fc, "-map", "[o]", "-t", f"{total:.3f}", str(mixed)])
            crisp = omni.crisp(mixed, d / "voice-crisp.wav")
            omni.remux(raw, crisp, voiced)
            check = lp.check(voiced, " ".join(p["line"] for p in c["voice_parts"]))
            led.put(c["id"], voiced=str(voiced), line_check=check, spans=spans, status="voiced")
        shipped = voiced
    else:
        silent = d / f"{c['id']}-silent.mp4"
        if not silent.is_file():
            omni.run_cmd([omni.ffmpeg_path(), "-y", "-i", str(raw), "-an", "-c:v", "copy", str(silent)])
        shipped = silent
    # 3a · FACE LOCK — the person stays the person (eye colour vs the approved picture, the face model
    #      when it can answer). Off by more than the tolerance: remade once, then flagged.
    fl_cfg = cfg.get("face_lock") or {}
    if fl_cfg and c.get("people") and "face_lock" not in led.get(c["id"]):
        fl = _load("face_lock")
        pk = fl.iris(start)
        ks = [fl.hue_key(x) for x in (fl.iris(f) for f in fl.frames(shipped)) if x]
        drift = round(max(abs(k - fl.hue_key(pk)) for k in ks), 3) if (pk and ks) else None
        # The eyes decide: Gemini on fal reads the eye colour off a close crop of the face, in the
        # picture and in three frames; most frames the other colour = the person changed. (3 Oct: the
        # pixel eye number flagged 14 of 27 good clips — sunglasses, blinks, a second face; a
        # same-person question on whole frames passed the clips where Nova's eyes had gone brown.)
        ref = cp.picture_file(run, c.get("face_ref") or c["start_frame"]) or start
        held = fl.eyes_held(shipped, ref)
        judged = held["frames"]
        swapped = not held["ok"]
        ok = held["ok"]
        tries = int(led.get(c["id"]).get("face_tries", 0))
        if swapped and tries < int(fl_cfg.get("remakes", 1)):
            for f in (raw, d / f"{c['id']}-voiced.mp4", d / f"{c['id']}-silent.mp4"):
                if f.is_file():
                    f.rename(f.with_name(f.stem + f"-drift{tries + 1}" + f.suffix))
            led.put(c["id"], face_tries=tries + 1, status="remake: face changed", line_check=None)
            return make_call(run, c, cfg, led, people)
        led.put(c["id"], face_lock={"eyes": held, "eye_drift_note": drift, "ok": ok, "tries": tries})
    # 3 · the frame-by-frame check
    if "qc" not in led.get(c["id"]):
        cmd = [sys.executable, str(HERE / "clip_qc.py"), str(shipped), "--picture", str(sent),
               "--sheet", str(d / f"{c['id']}-qc.jpg")]
        if c["talking"]:
            cmd += ["--voice", str(shipped)]
        if c["refs"]:
            cmd += ["--swipe", str(run / c["refs"][0]["file"])]
        q = subprocess.run(cmd, capture_output=True, text=True).stdout
        led.put(c["id"], qc=json.loads(q) if q.strip() else None)
    # 4 · the last frame — only a call with nobody on screen ever starts from it (no hand-offs for people)
    if not c.get("people"):
        cp.last_frame(shipped, run / "media" / f"{c['id']}-LAST.png")
    # 5 · at 1080p — or below it when upscale_below_1080p is off (720p, 2026-10-09) — the clip ships as made;
    #     otherwise upscale on fal, sound carried over
    if not final.is_file() and (cfg["resolution"] in ("1080p", "4k") or not cfg.get("upscale_below_1080p", True)):
        omni.run_cmd([omni.ffmpeg_path(), "-y", "-i", str(shipped), "-c", "copy", str(final)])
    if not final.is_file() and cfg.get("upscale_where") == "local":
        big = upscale_local(shipped, d / f"{c['id']}-up.mp4", cfg)
        if c["talking"]:
            omni.remux(big, shipped, final)
        else:
            omni.run_cmd([omni.ffmpeg_path(), "-y", "-i", str(big), "-an", "-c:v", "copy", str(final)])
        led.put(c["id"], upscale="local", upscale_usd=0.0)
    if not final.is_file():
        up = cfg["upscale"]
        body = {"video_url": _data_url(shipped), "target_resolution": up["target_resolution"],
                "enhancement_preset": up["enhancement_preset"]}
        sub = pf.submit(up["model"], body, k, pf.http_transport)
        res = pf.wait(sub["status_url"], sub["response_url"], k, pf.http_transport, up["model"])
        big = d / f"{c['id']}-1080p.mp4"
        pf.fetch(pf.media_urls(res)[0], big)
        if c["talking"]:
            omni.remux(big, shipped, final)          # the upscaler's sound is never trusted: ours goes back on
        else:
            omni.run_cmd([omni.ffmpeg_path(), "-y", "-i", str(big), "-an", "-c:v", "copy", str(final)])
        secs = _dur(shipped)
        usd = round(secs * float(up["usd_per_s"]), 4)
        led.put(c["id"], upscale_request_id=sub.get("request_id"), upscale_usd=usd)
        led.spend(c["id"] + "-upscale", up["model"], round(secs, 2), usd, up["target_resolution"])
    led.put(c["id"], file=str(final), status="done")
    return led.get(c["id"])


def make_tts(run: Path, t: dict, cfg: dict, led: Ledger) -> dict:
    omni = _load("omni")
    lp = omni.lineparity
    out = Path(run) / t["out"]
    key = f"tts-{Path(t['out']).stem}"
    if led.get(key).get("status") == "done" and out.is_file():
        return led.get(key)
    out.parent.mkdir(parents=True, exist_ok=True)
    url = cfg["tts"]["url"].format(voice_id=t["voice_id"]) + "?output_format=" + cfg["tts"]["output_format"]
    body = json.dumps({"text": lp.say_numbers(t["text"]), "model_id": t["model_id"],
                       "voice_settings": t["settings"]}).encode()
    stt, _h, raw = lp.http_transport("POST", url, {"xi-api-key": lp.key_of(), "Content-Type": "application/json",
                                                  "Accept": "audio/mpeg"}, body)
    if stt is None or stt >= 400:
        raise RuntimeError(f"{t['scene']}: text-to-speech {stt}: {raw[:200]!r}")
    plain = out.with_name(out.stem + "-uncrisp.mp3")
    plain.write_bytes(raw)
    omni.crisp(plain, out)
    led.put(key, file=str(out), at_in_ad=t["at"], chars=t["chars"], status="done")
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
    if res.get("route") != "omni":
        print("no Omni plan — run: run.py start … --clips first", file=sys.stderr)
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
    make, tts = make or make_call, tts or make_tts
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
                errors[c["id"]] = _fal_detail(e)
                return

    with cf.ThreadPoolExecutor(max_workers=parallel) as ex:
        list(ex.map(one_chain, chains(calls)))
        for j in jobs:
            try:
                tts(run, j, cfg, led)
            except Exception as e:
                fails.append(f"{j['scene']}: {e}")
    spent = round(sum(float(v.get("omni_usd") or 0) + float(v.get("upscale_usd") or 0) for v in led.d.values()), 2)
    print(f"done: {sum(1 for v in led.d.values() if v.get('status') == 'done')} made · ${spent} on fal · ledger {led.f}")
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
    if slop:
        print(f"NOT CLEAN · {len(slop)} clip(s) carry words that are not words — fix or cover before the edit", file=sys.stderr)
    return 1 if fails or not cov["complete"] or slop else 0


def led_has_done(run: Path, cid: str) -> bool:
    row = (_read(Path(run) / "clips" / "omni-ledger.json", {}) or {}).get(cid) or {}
    return row.get("status") == "done" and (Path(run) / "clips" / f"{cid}.mp4").is_file()


def _fal_detail(e) -> str:
    """The model's own words for a refusal when fal gives them (a 422 body), else the error."""
    m = re.search(r"https://queue\.fal\.run/\S+/requests/[\w-]+", str(e))
    if m:
        try:
            import urllib.request, urllib.error
            k = _load("omni").fal_key_of()
            req = urllib.request.Request(m.group(0), headers={"Authorization": f"Key {k}"})
            try:
                body = urllib.request.urlopen(req, timeout=30).read()
            except urllib.error.HTTPError as he:
                body = he.read()
            d = json.loads(body.decode())
            msg = "; ".join(x.get("msg", "") for x in d.get("detail") or [] if isinstance(x, dict))
            if msg:
                return f"refused by the model: {msg}"
        except Exception:
            pass
    return str(e)[:400]


# ------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the Omni clips route")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("run"); p.add_argument("--only")
    r = sub.add_parser("refs"); r.add_argument("run")
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
    only = [s.strip() for s in (a.only or "").split(",") if s.strip()] or None
    return run_live(run, only=only, parallel=a.parallel, yes=a.yes)


if __name__ == "__main__":
    sys.exit(main())
