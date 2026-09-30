#!/usr/bin/env python3
"""
run.py — the one runner. A brief (or a plan) goes in; the gates run; the
provider decides the models; a fal run submits itself; a Higgsfield run
hands the editor a submit sheet and takes results back; every job lands in
the ledger. Full account: `RUN.md`.

    python3 run.py start  <brief.md | plan.json> --brand B --format F \
                           --label L [--provider P] [--yes] [--dry-run] \
                           [--bank <path>] [--runs-root <path>] [--cast-root <path>]
    python3 run.py record <run-dir> --results <results.json> [--no-parity]
    python3 run.py pack   <run-dir> [--dry-run]

Exit 0 done · 1 declined at the confirm gate · 2 a gate failed, nothing
submitted · 3 bad input.

No brand, model or person name lives in this file. A model slug comes from
`providers.json` through `platform.py`; a brand comes from the run's own
`--brand` / plan.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Path(__file__).resolve() (the FILE, not its parent) — the same count
# prompt.py uses for the same reason: machine/run.py -> ai-video-production
# -> damon -> lab -> the ai-workspace root.
WORKSPACE = Path(__file__).resolve().parents[4]
DEFAULT_RUNS_ROOT = WORKSPACE / "runs"
DEFAULT_BANK = HERE.parent / "formats" / "bank.json"

ELEMENT = re.compile(r"<<<([0-9a-fA-F-]{36})>>>")

# Mutable so a test can point it at a temp workspace without touching disk
# under the real repo. Mirrors prompt.py's own module-level BRAND pattern.
WS = WORKSPACE


def _load(name: str):
    """Load a sibling module by path, never by import — platform.py shadows
    a stdlib name (preflight.py's own trick), and every other module here
    should run the same way regardless of sys.path or cwd."""
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")
preflight = _load("preflight")
prompt_mod = _load("prompt")
plan_from_brief_mod = _load("plan_from_brief")
voice_mod = _load("voice")
lineparity_mod = _load("lineparity")
scenes_mod = _load("scenes")
mi = _load("model_inputs")


# ------------------------------------------------------------- small utils

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1) + "\n")


def products_of(prompt_text: str, brand: str | None) -> list[str]:
    """Element uuids in `prompt_text` that brands/<brand>/element-facts.json
    marks as a product (`kind` or `role` == "product"). A brand with no
    facts file — or none named — simply has no products, never an error."""
    ids = ELEMENT.findall(prompt_text or "")
    if not ids or not brand:
        return []
    f = WS / "brands" / brand / "element-facts.json"
    try:
        book = json.loads(f.read_text()).get("elements", {})
    except Exception:
        return []
    out = []
    for uid in ids:
        row = book.get(uid) or {}
        if row.get("kind") == "product" or row.get("role") == "product":
            out.append(uid)
    return out


def merge_results(run: Path, rows: list[dict]) -> None:
    p = run / "results.json"
    existing = read_json(p, {}) or {}
    for row in rows:
        existing[str(row["id"])] = row
    write_json(p, existing)


# ------------------------------------------------------- brief -> a plan
#
# plan_from_brief.py's own main() parses a brief AND writes it straight to
# <run>/out/plan.json — the Cinema line's old layout. This runner wants the
# plan at <run>/plan.json instead, so the hard part (the two header
# dialects, the field regexes) is called straight out of that module; the
# small assembly around it — the same shape main() builds — is redone here
# rather than shelling out to a script that writes to the wrong path.

def build_plan_from_brief(brief_path: Path, brand: str) -> dict:
    text = brief_path.read_text()
    parsed = scenes_mod.parse(text)
    if parsed and parsed[0].get("shape") == "scene":
        return plan_from_scenes(brief_path, text, parsed, brand)
    return plan_from_timed_brief(brief_path, text, brand)


def speaker_of(scenes: list[dict]) -> str:
    """Whose voice this piece is in — the name the to-camera scenes name most
    often. Nothing is invented: a brief that names nobody returns nothing and
    the voice station says so."""
    counts: dict[str, int] = {}
    for s in scenes:
        who = (s.get("who") or "").split("·")[0].strip()
        if who:
            counts[who] = counts.get(who, 0) + (2 if s.get("to_camera") else 1)
    return max(counts, key=counts.get) if counts else ""


def cast_names_of(text: str) -> list[str]:
    """The names in the brief's own cast block, from its json block. A brief
    with no block has no list, and everything behaves as it did before."""
    doc, _ = scenes_mod.json_block(text)
    if not isinstance(doc, dict):
        return []
    out = []
    for c in doc.get("cast") or []:
        if isinstance(c, dict):
            for key in ("name", "id"):
                if str(c.get(key) or "").strip():
                    out.append(str(c[key]).strip())
                    break
    return out


def plan_from_scenes(brief_path: Path, text: str, parsed: list[dict], brand: str) -> dict:
    """THE SCENE SHAPE (2026-09-18). A scene is one setting, one section, one
    paragraph of voice and a list of frames. The plan carries them through
    unchanged — the run never re-derives what the brief already decided —
    plus the two values declared once for the whole piece, aspect and
    resolution, which no scene may restate."""
    piece = scenes_mod.piece_of(text)
    piece = {
        "aspect": piece.get("aspect") or mi.piece_default("aspect"),
        "resolution": piece.get("resolution") or mi.piece_default("resolution"),
        "style": piece.get("style") or "",
    }
    table = dict(re.findall(r"\| (.+?) \| \`<<<([0-9a-f-]{36})>>>\` \|", text))
    return {
        "brand": brand,
        "brief": brief_path.name,
        "shape": "scene",
        "piece": piece,
        "cast": {"name": speaker_of(parsed), "resolution": piece["resolution"],
                 # every name the brief's own cast block holds — what makes a
                 # scene's `who` a person rather than a description of the shot
                 "names": cast_names_of(text),
                 "elements": [{"name": name, "id": eid, "role": "ref"}
                              for name, eid in table.items()]},
        "scenes": parsed,
        "cutaways": [],
    }


def plan_from_timed_brief(brief_path: Path, text: str, brand: str) -> dict:
    pfb = plan_from_brief_mod
    by_id = pfb.cast_of(brand)

    table = dict(re.findall(r"\| (.+?) \| \`<<<([0-9a-f-]{36})>>>\` \|", text))
    declared = {v: k for k, v in table.items()}

    ss = pfb.scenes_of(text)
    talking = [s for s in ss if s["type"] == "A"]
    inserts = [s for s in ss if s["type"] != "A"]

    def cut_row(s, over):
        return {"id": f"S{s['n']}", "over": over, "at": round(s["start"], 1),
                "seconds": s["seconds"], "why": s["delivery"],
                "place": s["happens"], "subject": s["happens"],
                "action": s["happens"], "look": s["look"], "generate": {}}

    return {
        "brand": brand,
        "brief": brief_path.name,
        "cast": {
            "name": "", "resolution": "720p",
            "face": "", "hands": "", "room": "", "presenter": "", "who": "", "says": "",
            "also": [], "alternates": {},
            "elements": [pfb.element_row(eid, by_id, "ref", name)
                         for eid, name in declared.items()],
        },
        "scenes": [{"id": f"A{s['n']}", "name": s["happens"][:44], "seconds": s["seconds"],
                    "line": s["say"].strip('*"'), "delivery": s["delivery"],
                    "gesture": s["happens"], "generate": {}, "revoice": {}}
                   for s in talking],
        "cutaways": [cut_row(s, (talking[0]["n"] if talking else "VO")) for s in inserts],
        "overrides": ({} if talking else {"aroll": {
            "agreed": 0, "ruled": "2026-09-14", "by": "the brief",
            "why": "Nobody speaks on camera. Every scene is an insert under one continuous "
                   "voice-over, because the source this was torn from never shows the speaker."}}),
    }


# --------------------------------------------------------- plan -> batches

def characters_of(scene: dict, cast: dict) -> list[str]:
    """Who in this scene is a CHARACTER — someone with a face, a cast sheet
    and a reference to hold them to.

    A scene's `who` is not always a person. B-ROLL IS A SCENE (2026-09-19),
    and a B-roll scene's who is what is in frame: the hands, the product, the
    speaker seen and not speaking, nobody. A `who` that names none of the
    brief's cast is a description of the picture, not a person — asking it
    for a cast sheet refuses a scene that has no face in it at all."""
    who = (scene.get("who") or "").split("·")[0].strip()
    if not who:
        who = cast_display_name(cast)
    if not who:
        return []
    names = [n for n in (cast.get("names") or []) if n]
    if not names:
        # an older brief, which carried no cast list — the name is the name
        return [who]
    hit = [n for n in names if n.lower() in who.lower()]
    return hit or []


def cast_display_name(cast: dict) -> str:
    return cast.get("name") or cast.get("presenter") or ""


# The doctrine-bound stages upstream (the teardown machine's ai-lane brief)
# may label a scene or cutaway with its Section / Technique / Emotion /
# Outcome before this machine ever sees it. This module never derives,
# checks or renames those values — it only carries whichever of them the
# brief actually wrote onto the batch item, verbatim, so nothing upstream
# is lost between the brief and the run record.
SCENE_METADATA_FIELDS = ("section", "technique", "emotion", "outcome",
                         "cutaways")


def _carry_scene_metadata(item: dict, source: dict) -> dict:
    for key in SCENE_METADATA_FIELDS:
        if key in source:
            item[key] = source[key]
    return item


def scene_item(scene: dict, cast: dict, brand: str | None) -> dict:
    params = prompt_mod.payload(scene, cast)
    params.pop("model", None)   # the provider decides the model, not the shape
    cast_name = cast_display_name(cast)
    item = {
        "id": scene["id"], "kind": "motion", "params": params, "medias": [],
        "characters": [cast_name] if cast_name else [],
        "products": products_of(params.get("prompt", ""), brand),
        "lines": [scene["id"]],
    }
    return _carry_scene_metadata(item, scene)


def cutaway_item(cut: dict, cast: dict, brand: str | None) -> dict:
    params = prompt_mod.broll(cut)
    params.pop("model", None)
    cast_name = cast_display_name(cast)
    subj_text = " ".join(str(cut.get(k, "")) for k in ("subject", "action", "place")).lower()
    characters = [cast_name] if cast_name and cast_name.lower() in subj_text else []
    item = {
        "id": cut["id"], "kind": "motion", "params": params, "medias": [],
        "characters": characters,
        "products": products_of(params.get("prompt", ""), brand),
        "lines": [],
    }
    return _carry_scene_metadata(item, cut)


def still_item_for(scene_or_cut: dict, cast: dict, brand: str | None) -> dict | None:
    """A scene/cutaway's own `generate` dict, when it names a prompt, becomes
    a machine-hand item (station cast/still/edit, per `generate["kind"]`) run
    BEFORE the motion item that uses it — id `<scene id>-still`, linked back
    via `for` so the SUBMIT.md can tell the editor which file to upload as
    that item's `start_image`. An empty `generate` (the default
    `plan_from_brief.py` writes today) means nothing to make here; the
    scene/cutaway is animated from whatever medias it already carries."""
    gen = scene_or_cut.get("generate") or {}
    prompt = gen.get("prompt")
    if not prompt:
        return None
    kind = gen.get("kind") or "still"
    refs = gen.get("references") or []
    cast_name = cast_display_name(cast)
    item = {
        "id": f"{scene_or_cut['id']}-still", "kind": kind, "for": scene_or_cut["id"],
        "params": {"prompt": prompt},
        "medias": [{"role": "image_references", "value": r} for r in refs],
        "characters": [cast_name] if cast_name else [],
        "products": products_of(prompt, brand),
        "lines": [],
    }
    return _carry_scene_metadata(item, scene_or_cut)


# -------------------------------------------- the scene shape -> items
#
# FEWER SCENES, MORE FRAMES (Damon, 2026-09-18, as corrected the same day). A
# scene is one setting, one paragraph of voice and ONE clip, with exactly TWO
# generated stills:
#
#   · the FIRST FRAME — a generation, carrying the scene's references in the
#     order the door preserves detail in;
#   · the LAST FRAME — an EDIT of the first, naming ONLY the delta.
#
# What happens between them is BEATS: timed spans written into the clip
# prompt's own timeline, one verb each, their timestamps read off the one
# voice track. A beat is never a generated still.
#
# Every field comes from `model-inputs.json` — the door's own contract — so
# nothing here is a session's memory of what a model takes.


def frame_items_of(scene: dict, cast: dict, piece: dict, brand: str | None) -> list[dict]:
    """The scene's two stills: the first frame, then the last as an edit of
    it."""
    items: list[dict] = []
    cast_name = cast_display_name(cast)
    who = (scene.get("who") or cast_name or "").split("·")[0].strip()
    first_id: str | None = None
    first_frame_refs = list(
        (next((f for f in scene.get("frames", []) if f.get("role") == "first"), {})
         ).get("refs") or [])
    for f in scene.get("frames", []):
        role = f.get("role")
        iid = f"{scene['id']}-{'F1' if role == 'first' else 'FLAST'}"
        contract_id = "still-generate"
        if role == "first":
            kind = "still"
            params = {"prompt": mi.still_prompt(f, piece)}
            size = mi.size_for(piece.get("aspect"))
            if size:
                params["size"] = size
            q = mi.house_default(mi.field_named("still-generate", "quality") or {})
            if q:
                params["quality"] = q
            refs = list(f.get("refs") or [])
            edit_of = None
        else:
            # THE LAST FRAME is an edit of the first. Which door it runs on
            # comes from the camera it declares: a push-in or a new angle
            # rescales the face, and that edit goes to the fidelity door —
            # measured live 2026-09-18, where the everyday edit door held the
            # face but under-delivered the camera move.
            route = mi.edit_route(f.get("camera"))
            contract_id = route.get("contract") or "still-edit"
            kind = route.get("kind") or "edit"
            params = {"prompt": mi.edit_prompt(f, contract_id)}
            if contract_id == "still-edit-fidelity":
                size = mi.size_for(piece.get("aspect"))
                if size:
                    params["size"] = size
                q = mi.house_default(mi.field_named(contract_id, "quality") or {})
                if q:
                    params["quality"] = q
                fid = mi.house_default(mi.field_named(contract_id, "input_fidelity") or {})
                if fid:
                    params["input_fidelity"] = fid
            else:
                if piece.get("aspect"):
                    params["aspect_ratio"] = piece["aspect"]
                isz = mi.house_default(
                    mi.field_named(contract_id, "generationConfig.imageConfig.imageSize") or {})
                if isz:
                    params["image_size"] = isz
            edit_of = first_id
            # ALWAYS two references: the frame being edited first, the
            # character's cast sheet second. With the frame alone, the face
            # drifted (live 2026-09-18). The cast sheet is the first
            # reference the scene's own first frame carried.
            first_refs = list(first_frame_refs)
            cast_ref = first_refs[0] if first_refs else ""
            refs = [first_id, cast_ref] + [r for r in (f.get("refs") or [])
                                           if r and r != cast_ref]
        item = {
            "id": iid, "kind": kind, "contract": contract_id, "for": scene["id"],
            "frame": f.get("n"), "frame_role": role, "edit_of": edit_of,
            "delta": f.get("delta") or "",
            "params": params,
            "medias": [{"role": "image_references", "value": r} for r in refs if r],
            "characters": characters_of(scene, cast),
            "products": products_of(params.get("prompt", ""), brand),
            "lines": [],
        }
        _carry_scene_metadata(item, scene)
        items.append(item)
        if role == "first":
            first_id = iid
    return items


def clip_seconds_of(scene: dict, row: dict, timing: dict | None = None) -> float | None:
    """How long the scene runs: its own slice of the ONE voice track, and —
    for a silent scene, which has no slice — the end of its last beat. No
    number is chosen here, and none is chosen by a format."""
    seconds = row.get("seconds")
    if seconds:
        return float(seconds)
    windows = mi.beat_windows(scene, None, timing)
    return float(windows[-1][1]) if windows else None


def clip_item_of(scene: dict, cast: dict, piece: dict, brand: str | None,
                 timing: dict | None = None) -> dict:
    """ONE clip for the scene, in the exact shape of the call that worked
    live 2026-09-18 evening: the FIRST FRAME as `start_image`, the LAST
    FRAME as `end_image`, and — on a to-camera scene — the scene's own slice
    of the one voice track as `audio_references`. **Nothing else travels on
    the clip.** The first frame already carries the identity, the wardrobe,
    the room and the light; a cast sheet or a style frame attached beside it
    is a second opinion about the same face."""
    talking = bool(scene.get("to_camera"))
    sid = "talking" if talking else "motion"
    frames = scene.get("frames") or []
    first = next((f for f in frames if f.get("role") == "first"), None)
    last = next((f for f in reversed(frames) if f.get("role") == "last"), None)
    row = ((timing or {}).get("scenes") or {}).get(scene["id"], {})
    seconds = clip_seconds_of(scene, row, timing)

    # The last frame is a real input where the door takes one, and the
    # timeline's final beat where it does not — the sheet says which.
    door_id, end_attached, how = mi.end_image_door(sid)
    end_attached = end_attached and last is not None
    scene = {**scene, "end_frame_attached": end_attached}
    params = {"prompt": mi.clip_prompt(scene, piece, seconds, timing, talking=talking)}
    if piece.get("aspect"):
        params["aspect_ratio"] = piece["aspect"]
    if piece.get("resolution"):
        params["resolution"] = piece["resolution"]
    if seconds:
        # ceil, floored at the door's minimum. The CEILING is never clamped:
        # a paragraph past it is refused by name so the scene is split at a
        # beat boundary, never quietly shortened.
        low = ((mi.station(sid).get("limits") or {}).get("duration_seconds") or [4])[0]
        params["duration"] = int(max(int(low), math.ceil(float(seconds))))
    ga = mi.house_default(mi.field_named(sid, "generate_audio") or {})
    if ga is not None:
        params["generate_audio"] = ga
    mode = mi.house_default(mi.field_named(sid, "mode") or {})
    if mode:
        params["mode"] = mode

    cast_name = cast_display_name(cast)
    who = (scene.get("who") or cast_name or "").split("·")[0].strip()
    start_id = f"{scene['id']}-F1" if first else None
    last_id = f"{scene['id']}-FLAST" if last else None
    medias: list[dict] = []
    if start_id:
        medias.append({"role": "start_image", "value": start_id})
    if end_attached and last_id:
        medias.append({"role": "end_image", "value": last_id})
    slice_ = row.get("file") or f"vo/{scene['id']}.mp3"
    if talking:
        medias.append({"role": "audio_references", "value": slice_})
    item = {
        "id": scene["id"], "kind": sid, "params": params, "medias": medias,
        "characters": characters_of(scene, cast),
        "products": products_of(params.get("prompt", ""), brand),
        "lines": [scene["id"]] if talking else [],
        "start_frame": start_id,
        "last_frame": last_id,
        "end_frame": last_id if end_attached else None,
        "door": door_id,
        "end_frame_how": how,
        "beats": [dict(b) for b in (scene.get("beats") or [])],
        "beat_windows": [list(w) for w in
                         mi.beat_windows(scene, seconds, timing)],
        "frames": [i for i in (start_id, last_id) if i],
        "to_camera": talking,
        # A B-ROLL SCENE IS A SCENE (Damon, 2026-09-19: "there is no B-roll" —
        # every scene was the speaker to camera). Its paragraph is part of the
        # same continuous read and is still recorded and sliced; it just does
        # not travel on the clip. It is laid UNDER the picture at the edit,
        # and the sheet says which file goes over which scene.
        "vo_over": None if talking else (slice_ if scene.get("voice") else None),
        # what the four blocks could not be built from — the gate names each
        # one, and a prompt is never written as a fragment
        "prompt_missing": mi.clip_missing(scene, piece, seconds, timing, talking=talking),
    }
    return _carry_scene_metadata(item, scene)


def scene_shape_items(plan: dict, brand: str | None, timing: dict | None = None) -> list[dict]:
    cast = plan.get("cast", {}) or {}
    piece = plan.get("piece", {}) or {}
    items: list[dict] = []
    for s in plan.get("scenes", []):
        if str(s.get("held") or "").strip():
            # A HELD SCENE makes nothing (2026-09-19). Its place in the order
            # is kept, its section is on the record and the one fact that
            # would release it is written down — but no door is handed a
            # frame nobody could describe. `cmd_start` says which scenes
            # these are, so a held scene is a finding rather than a silence.
            continue
        items += frame_items_of(s, cast, piece, brand)
        items.append(clip_item_of(s, cast, piece, brand, timing))
    return items


def song_item_of(plan: dict, brand: str | None) -> dict | None:
    """A plan carries its own `song` block only when the format is sung
    (Damon's 2026-09-17 ruling: the song is Lyria 3 Pro, direct, made once
    per run) — this module doesn't need to know which formats those are;
    the plan already decided by including one. `clip` picks the 30s Lyria
    model over the full one; the default is the full song."""
    song = plan.get("song") or {}
    prompt = song.get("prompt")
    if not prompt:
        return None
    return {
        "id": "SONG", "kind": "audio", "params": {"prompt": prompt, "clip": bool(song.get("clip"))},
        "medias": [], "characters": [], "products": products_of(prompt, brand), "lines": [],
    }


def batches_of(plan: dict, brand: str | None, timing: dict | None = None) -> list[dict]:
    cast = plan.get("cast", {}) or {}
    if plan.get("shape") == "scene" or any(s.get("frames") for s in plan.get("scenes", [])):
        items = scene_shape_items(plan, brand, timing)
        song = song_item_of(plan, brand)
        if song:
            items.append(song)
        return items
    items: list[dict] = []
    for s in plan.get("scenes", []):
        si = still_item_for(s, cast, brand)
        if si:
            items.append(si)
        items.append(scene_item(s, cast, brand))
    for c in plan.get("cutaways", []):
        ci = still_item_for(c, cast, brand)
        if ci:
            items.append(ci)
        items.append(cutaway_item(c, cast, brand))
    song = song_item_of(plan, brand)
    if song:
        items.append(song)
    return items


# --------------------------------------------------------- the two hands
#
# Damon's 2026-09-17 ruling: cast, still, edit, voice and song run on the
# machine hand — direct APIs, nobody at a keyboard. Since 2026-09-18 that
# includes motion and the talking beat (Seedance on BytePlus, direct); the
# editor hand — Higgsfield (or fal), from a submit sheet — is what a station
# falls back to when its door says so. Which station is whose hand lives in
# providers.json's own `doors[...].hand`; nothing here decides it by kind
# name.

def hand_of(station: str | None, reg: dict) -> str | None:
    if not station:
        return None
    return (reg.get("doors") or {}).get(station, {}).get("hand")


def station_of(item: dict, reg: dict) -> str | None:
    kind = item.get("kind") or platform.item_kind(item, reg)
    return reg["station_of_kind"].get(kind or "")


def split_by_hand(items: list[dict], reg: dict, forced_provider: bool = False) -> tuple[list[dict], list[dict]]:
    """(machine-hand items, editor-hand items). An item whose station names
    no hand (or resolves to nothing) is left with the editor — the safe
    default, since the editor path is the one a human still reviews.

    `forced_provider` — Damon named a house with `--provider`: the motion
    stations (whose machine door is a direct one) go to that house instead,
    so `--provider higgsfield-ui` still means "the editor animates this".
    Cast, still, edit and the song never leave the machine hand — no house
    is allowed to make those (the 2026-09-17 ruling)."""
    machine, editor = [], []
    for it in items:
        st = station_of(it, reg)
        door = (reg.get("doors") or {}).get(st or "", {})
        to_machine = door.get("hand") == "machine"
        if to_machine and forced_provider and str(door.get("primary", "")).startswith("direct:") \
                and st in ("motion", "talking"):
            to_machine = False
        (machine if to_machine else editor).append(it)
    return machine, editor


def still_for_map(machine_items: list[dict]) -> dict[str, str]:
    """motion/talking item id -> the machine-hand item whose picture it starts
    on. In the scene shape two stills are made for one clip, so the FIRST
    FRAME is the one that maps; anything else would hand the editor the last
    frame as the start image."""
    out: dict[str, str] = {}
    for it in machine_items:
        key = it.get("for")
        if not key:
            continue
        if it.get("frame_role") == "last":
            continue
        if key in out and it.get("frame_role") != "first":
            continue
        out[key] = str(it["id"])
    return out


def _resolve_ref(run: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (run / p)


def _named_ref(run: Path, value: str, item: dict, brand: str | None) -> Path | None:
    """A reference by path, or by the name the brief gives it. `<NAME> cast
    sheet` -> the character's master sheet under brands/<brand>/ai-elements/characters/<name>/
    (old name ai-cast/<name>/)
    (master-sheet.png, then master-portrait.*); `style frame` -> the run's
    own style frame if one is banked (media/style-frame.*), else nothing."""
    low = value.lower().strip()
    p = _resolve_ref(run, value)
    if p.is_file():
        return p
    if low.endswith("cast sheet"):
        name = value[: -len("cast sheet")].strip().rstrip("—-·:").strip()
        for cand in (name, *(item.get("characters") or [])):
            if not cand:
                continue
            home = voice_mod.character_home(brand, str(cand).lower(), None)
            for fn in ("master-sheet.png", "master-sheet.webp", "master-portrait.png",
                       "master-portrait.webp", "master-sheet-sm.jpg", "master-portrait-sm.jpg"):
                f = home / fn
                if f.is_file():
                    return f
        return None
    if "style frame" in low:
        for f in sorted((run / "media").glob("style-frame.*")) if (run / "media").is_dir() else []:
            return f
        return None
    return None


def _audio_of(it: dict, run: Path) -> Path | None:
    """The voice this item carries — `audio` on the old shape, and
    `audio_references` on the talking door, which is the same file under the
    name that door gives the role."""
    for role in ("audio", "audio_references"):
        for m in it.get("medias") or []:
            if m.get("role") == role and m.get("value"):
                return _resolve_ref(run, m["value"])
    return None


def _still_of(it: dict, run: Path, manifest: dict) -> Path | None:
    """The frame a motion/talking item animates from: the scene's FIRST FRAME
    (the scene shape names it on the item as `start_frame`), else the
    `-still` item the machine hand just made for it, else a start_image /
    image_references media it already carries (a path)."""
    for key in ("start_frame",):
        made = manifest.get(str(it.get(key) or "")) or {}
        if made.get("file"):
            return Path(made["file"])
    made = manifest.get(f"{it.get('id')}-still") or {}
    if made.get("file"):
        return Path(made["file"])
    for role in ("start_image", "image_references"):
        for m in it.get("medias") or []:
            if m.get("role") == role and m.get("value") and not platform.is_uuid(str(m["value"])):
                return _resolve_ref(run, m["value"])
    return None


def colour_match_to(item: dict, made_file, manifest: dict) -> bool:
    """After an EDIT, hold it to the frame it came from: resized to that
    frame's exact size and matched to it per channel. An edit door returns
    its own exposure and white balance, and a first/last frame pair that
    disagrees on either reads as two different shots the moment a clip runs
    between them. Mechanical, every time, before the still is verified."""
    ref_id = item.get("edit_of")
    if not (ref_id and made_file):
        return False
    ref = (manifest.get(str(ref_id)) or {}).get("file")
    if not ref:
        return False
    return _load("colour_match").match_file(made_file, ref)


def run_machine_hand(items: list[dict], run: Path, dry_run: bool, brand: str | None = None,
                      openai_transport=None, google_transport=None, byteplus_transport=None,
                      openai_key: str | None = None, google_key: str | None = None,
                      byteplus_key: str | None = None) -> dict:
    """Every machine-hand item (cast · still · edit · the song · motion · talking) runs straight
    to its direct API — no editor, no provider choice. Returns
    `{item id: {file, model, request_id, at, ...}}`, the same manifest
    written to `<run>/direct.json`. `--dry-run` calls each direct client in
    its own dry-run mode: it prints the request and writes nothing, and
    this function writes nothing either (an empty manifest comes back).
    A missing key is a `SystemExit` naming it — never a silent skip;
    `cmd_start` lets that propagate the same way it does for `voice.py`."""
    if not items:
        return {}
    direct_openai = _load("direct_openai")
    direct_google = _load("direct_google")
    direct_byteplus = _load("direct_byteplus")
    reg = platform.registry()
    media_dir = run / "media"
    manifest: dict = {}

    for it in items:
        iid = str(it.get("id", "?"))
        kind = it.get("kind")
        params = it.get("params") or {}
        prompt = params.get("prompt", "")
        # a reference may name a frame this run already made (the scene shape
        # edits frame N off frame N−1), or a path
        refs = []
        for m in (it.get("medias") or []):
            if m.get("role") != "image_references" or not m.get("value"):
                continue
            made = manifest.get(str(m["value"])) or {}
            if made.get("file"):
                refs.append(Path(made["file"]))
                continue
            # the brief names references by what they ARE — "<NAME> cast
            # sheet", "the style frame" — and the brand folder says where
            # that is. A name nothing resolves is a gate finding, never a
            # crash mid-run (found live 2026-09-19 on the first paid run).
            resolved = _named_ref(run, str(m["value"]), it, brand)
            if resolved is None:
                print(f"  {iid}: reference {m['value']!r} resolves to nothing — skipped")
                continue
            refs.append(resolved)

        if kind in ("cast", "still"):
            out = media_dir / f"{iid}.png"
            res = direct_openai.generate(prompt, refs, out, transport=openai_transport,
                                          key=openai_key, dry_run=dry_run)
            model, file_ = res["model"], res.get("file")
            colour_match_to(it, file_, manifest)
        elif kind in ("edit", "restyle"):
            out = media_dir / f"{iid}.png"
            res = direct_google.edit_image(prompt, refs, out, transport=google_transport,
                                            key=google_key, dry_run=dry_run)
            model, file_ = res["model"], res.get("file")
            colour_match_to(it, file_, manifest)
        elif kind == "audio":
            out_wav = media_dir / f"{iid}.wav"
            timing_out = media_dir / f"{iid}-song-timings.txt"
            variant = "clip" if params.get("clip") else "full"
            res = direct_google.song(prompt, out_wav, timing_out, model=variant,
                                      transport=google_transport, key=google_key, dry_run=dry_run)
            model, file_ = res["model"], res.get("wav")
        elif kind in ("motion", "talking"):
            # a scene with a line is the talking beat (its ElevenLabs take
            # rides along as the audio media); a cutaway is silent motion.
            out = media_dir / f"{iid}.mp4"
            still = _still_of(it, run, manifest)
            if still is None and not dry_run:
                raise SystemExit(f"{iid}: nothing to animate from — no still was made for it "
                                  f"and it carries no start_image path")
            audio = _audio_of(it, run)
            talking_door = str((reg.get("doors") or {}).get("talking", {}).get("primary", ""))
            if audio is not None and talking_door == "direct:omni":
                # the controlled-Omni recipe (Damon 2026-09-18): the line is
                # performed from the prompt, then re-voiced into the
                # character's voice; the ElevenLabs take is the voice
                # reference, not an input here.
                omni = _load("omni")
                line_text = lineparity_mod.line_text_of(run, it) if it.get("lines") else ""
                if not line_text and not dry_run:
                    raise SystemExit(f"{iid}: a talking beat with no line text on record")
                voice_id = it.get("voice_id")
                if not voice_id and not dry_run:
                    raise SystemExit(f"{iid}: no voice_id travelled with the line — the character's "
                                      f"voice.json must bind one")
                res = omni.talk(line_text or "<line>", still or Path("<still>"), voice_id or "<voice>",
                                out, seconds=params.get("duration"), prompt_extra=params.get("performance", ""),
                                resolution=params.get("resolution"), aspect_ratio=params.get("aspect_ratio"),
                                dry_run=dry_run)
            elif audio is None and str((reg.get("doors") or {}).get("motion", {}).get("primary", "")) == "direct:omni":
                omni = _load("omni")
                res = omni.motion(prompt, still or Path("<still>"), out,
                                  seconds=int(params.get("duration") or 0) or None,
                                  resolution=params.get("resolution"), aspect_ratio=params.get("aspect_ratio"),
                                  dry_run=dry_run)
            elif audio is not None:
                res = direct_byteplus.talking(
                    prompt, still or Path("<still>"), audio, out,
                    seconds=params.get("duration"), resolution=params.get("resolution"),
                    ratio=params.get("aspect_ratio"),
                    transport=byteplus_transport, key=byteplus_key, dry_run=dry_run)
            else:
                res = direct_byteplus.motion(
                    prompt, still or Path("<still>"), None, out,
                    seconds=int(params.get("duration") or 5), resolution=params.get("resolution"),
                    ratio=params.get("aspect_ratio"),
                    transport=byteplus_transport, key=byteplus_key, dry_run=dry_run)
            model, file_ = res["model"], res.get("file")
        else:
            raise SystemExit(f"run.py's machine hand has no dispatch for kind {kind!r} "
                              f"(item {iid}) — add one")

        if dry_run:
            continue
        row = {"file": file_, "model": model, "request_id": res.get("request_id") or res.get("task_id"), "at": now()}
        if kind in ("motion", "talking"):
            row["usage"] = res.get("usage")
            row["talking"] = _audio_of(it, run) is not None
            for k in ("recipe", "parity_native", "parity_final", "native"):
                if res.get(k) is not None:
                    row[k] = res[k]
            if res.get("parity_final"):
                preflight.verdict(run, iid, "parity", res["parity_final"])
        if kind == "audio":
            row["timing"] = res.get("timing")
            row["timed"] = res.get("timed")
        manifest[iid] = row
        preflight.ledger(run, model, iid, 0.0, "done", brand=brand, shot=iid)

    if not dry_run:
        write_json(run / "direct.json", manifest)
    return manifest


# ------------------------------------------------------------ SUBMIT.md

def write_submit_md(run: Path, items: list[dict], prov: dict, reg: dict,
                     direct_manifest: dict | None = None, still_for: dict | None = None) -> Path:
    direct_manifest = direct_manifest or {}
    still_for = still_for or {}
    lines = [f"# {run.name} — submit sheet", "",
             f"Provider: {prov.get('label', '?')}.",
             "",
             "Submit each block below exactly as written, then hand the results back as "
             "`results.json`:",
             "",
             '    [{"id": "...", "job": "...", "url": "...", "seconds": N, '
             '"status": "done|nsfw|ip_detected|failed"}, ...]',
             "",
             "    python3 machine/run.py record " + str(run) + " --results results.json",
             ""]
    voice_files = sorted((run / "voice").glob("*.mp3")) if (run / "voice").is_dir() else []
    if voice_files:
        lines += ["## Voices", "",
                   "Made first, on the direct ElevenLabs account (Damon's 2026-09-17 "
                   "ruling) — upload each line below to the provider, then use the "
                   "returned media id as the `audio` media on the item(s) that carry it:",
                   ""]
        for f in voice_files:
            lines.append(f"- `{f.relative_to(run)}`")
        lines.append("")
    if direct_manifest:
        lines += ["## Machine-made media", "",
                   "Cast, stills, edits and the song run on the machine hand — direct APIs, "
                   "made before this sheet was written (Damon's 2026-09-17 ruling). Upload "
                   "each file below to the provider, then use the returned media id as the "
                   "matching role (`start_image` for a still/edit) on the item that carries it:",
                   ""]
        for iid, row in sorted(direct_manifest.items()):
            lines.append(f"- `{row.get('file')}` — {row.get('model', '?')} (made for {iid})")
        lines.append("")
    for it in items:
        slug, refusal = platform.resolve_model(it, prov, reg)
        params = it.get("params") or {}
        lines.append(f"## {it.get('id', '?')} — {slug or '?'}" +
                     (f"  (REFUSED: {refusal})" if refusal else ""))
        lines.append("")
        still_id = it.get("start_frame") or still_for.get(str(it.get("id")))
        made = direct_manifest.get(still_id) if still_id else None
        if made:
            lines.append(f"- **start_image (upload first)**: `{made.get('file')}` "
                         f"— made by {made.get('model', '?')} ({still_id})")
        elif still_id:
            lines.append(f"- **start_image (upload first)**: the frame made as `{still_id}`")
        if it.get("end_frame"):
            end_made = direct_manifest.get(it["end_frame"]) or {}
            lines.append(f"- **end image (upload too)**: "
                         f"`{end_made.get('file') or it['end_frame']}` — the scene's "
                         f"last frame, {it.get('end_frame_how', '')}")
        elif it.get("last_frame"):
            last_made = direct_manifest.get(it["last_frame"]) or {}
            lines.append(f"- **last frame**: made as "
                         f"`{last_made.get('file') or it['last_frame']}`, but "
                         f"{it.get('end_frame_how', '')} — the final beat of the "
                         f"timeline below is where the clip has to land")
        if it.get("vo_over"):
            lines.append(f"- **VO over**: `{it['vo_over']}` — this scene is "
                         f"B-roll: the clip carries no audio, and this slice of "
                         f"the one voice track is laid under it at the edit")
        if it.get("beats"):
            lines.append(f"- **beats**: {len(it['beats'])}, timed off the one voice "
                         f"track — the timeline in the prompt below")
        if it.get("door"):
            lines.append(f"- **door**: {it['door']}")
        for k, v in params.items():
            if k == "prompt":
                continue
            lines.append(f"- **{k}**: {v}")
        if it.get("medias"):
            # the exact call: every media by its role, in the order the door
            # takes them, each naming the file that was made for it
            lines.append("- **medias** (in this order):")
            for m in it["medias"]:
                made = (direct_manifest.get(str(m.get("value"))) or {}).get("file")
                lines.append(f"    - **{m.get('role')}**: `{made or m.get('value')}`"
                             + (f" ({m.get('value')})" if made else ""))
        if it.get("characters"):
            lines.append(f"- **characters**: {', '.join(it['characters'])}")
        if it.get("products"):
            lines.append(f"- **products**: {', '.join(it['products'])}")
        lines.append("")
        lines.append("**Prompt — exactly as the model receives it:**")
        lines.append("")
        lines.append("```")
        lines.append(params.get("prompt", ""))
        lines.append("```")
        lines.append("")
    dest = run / "SUBMIT.md"
    dest.write_text("\n".join(lines))
    return dest


# ---------------------------------------------------------------- start

def cmd_start(a, transport=None, download=None, voice_transport=None,
              openai_transport=None, google_transport=None, byteplus_transport=None) -> int:
    runs_root = Path(a.runs_root).resolve() if a.runs_root else DEFAULT_RUNS_ROOT
    run = runs_root / "video-machine" / a.brand / a.label
    run.mkdir(parents=True, exist_ok=True)
    (run / "batches").mkdir(exist_ok=True)

    src = Path(a.source).resolve()
    if not src.exists():
        print(f"no such file: {src}", file=sys.stderr)
        return 3

    if src.suffix.lower() == ".json":
        plan = json.loads(src.read_text())
        shutil.copy2(src, run / "plan.json")
    else:
        shutil.copy2(src, run / "brief.md")
        plan = build_plan_from_brief(src, a.brand)
        write_json(run / "plan.json", plan)
        # THE BRIEF IS THE PROMPT (2026-09-19). Its truth is the json block;
        # the page a person opens is rendered FROM that block, here, so the
        # document a person reads and the one the doors receive can never
        # drift apart. A brief with no block has no view to render.
        doc, _ = scenes_mod.json_block(src.read_text())
        if isinstance(doc, dict) and doc.get("scenes"):
            (run / "brief-view.md").write_text(scenes_mod.render_view(doc))

    run_json_path = run / "run.json"
    existing = read_json(run_json_path, {}) or {}
    fresh = {"machine": "video-machine", "brand": a.brand, "label": a.label,
             "format": a.format, "source_brief": src.name,
             "provider": a.provider, "opened": now()}
    write_json(run_json_path, {**fresh, **existing})   # never overwrite what's already there

    # A scene's line is a PARAGRAPH in the scene shape — the whole run of
    # speech, byte-identical to the script, one entry per scene. That is what
    # the one voice track is chunked on.
    held = [s["id"] for s in plan.get("scenes", []) if str(s.get("held") or "").strip()]
    lines = {s["id"]: (s.get("line") or s.get("voice") or "")
             for s in plan.get("scenes", []) if s["id"] not in held}
    write_json(run / "lines.json", lines)
    for s in plan.get("scenes", []):
        if s["id"] in held:
            print(f"HELD {s['id']} — nothing is made for it: {s['held']}")

    # Voices before anything else generates (Damon's 2026-09-17 ruling): a
    # scene with a line gets its ElevenLabs take made now, on the direct
    # account, so it can be piped into the provider as the audio a talking
    # beat carries. A plan with no line to speak calls this for nothing —
    # voice.run_for is itself a no-op when lines.json has nothing in it. A
    # character with no bindable voice is a hard stop, --dry-run included:
    # nothing here should plan around a voice that cannot actually speak.
    try:
        voice_manifest = voice_mod.run_for(
            run, character=None, dry_run=a.dry_run, cast_root=a.cast_root,
            transport=voice_transport)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    plan_brand = plan.get("brand") or a.brand
    prompt_mod.use_brand(plan_brand)
    # The one voice track was just made, so every beat can be timed against
    # it rather than against a number somebody chose.
    timing = read_json(run / "vo" / "timing.json", {}) or {}
    try:
        items = batches_of(plan, plan_brand, timing)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    # A scene's line carries its own voice take as an audio media — the
    # provider-neutral shape (a path, uploaded later); preflight's rule 4
    # (media UUID required) only looks at role start_image, so a path here
    # is never rejected. In the scene shape the file is the scene's SLICE of
    # the one track, and the talking door takes it under its own role name.
    for it in items:
        for lid in it.get("lines") or []:
            row = voice_manifest.get(lid)
            if row:
                role = "audio_references" if it.get("kind") == "talking" else "audio"
                it.setdefault("medias", [])
                # the scene shape already attached the slice when it built the
                # item; attaching it again sent the door the same audio twice
                if any(m.get("role") == role and m.get("value") == row["file"]
                       for m in it["medias"]):
                    continue
                it["medias"].append({"role": role, "value": row["file"]})
                if row.get("voice_id"):
                    it["voice_id"] = row["voice_id"]

    name, prov, why = platform.resolve_provider(a.provider)
    if a.provider:
        print(f"provider: {name} — {'; '.join(why)}")
    else:
        # one hand (2026-09-18): no house is used unless one is forced; the
        # detected house only lends its batch size to the plan
        print("hand: machine — every station direct (force a house with --provider)")

    reg = platform.registry()
    overall = platform.plan(items, prov, reg, forced=bool(a.provider))
    platform.print_plan(overall)
    if overall["refusals"]:
        for r in overall["refusals"]:
            print(f"REFUSED {r}", file=sys.stderr)
        return 2

    if prov.get("confirm") and not a.yes:
        if not platform.confirm(prov, a.yes):
            print("declined")
            return 1

    bank_path = Path(a.bank) if a.bank else DEFAULT_BANK
    cap = prov.get("batch_max") or len(items) or 1
    chunks = [items[i:i + cap] for i in range(0, len(items), cap)] or [[]]

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        pending = []
        for i, chunk in enumerate(chunks, 1):
            p = tmpdir / f"{i:02d}-motion.json"
            write_json(p, {"items": chunk})
            pending.append(p)
        any_fail = False
        for p in pending:
            fails, warns = preflight.check(p, run, name, bank_path)
            for w in warns:
                print(f"WARNING {w}")
            if fails:
                any_fail = True
                for f in fails:
                    print(f)
        if any_fail:
            print("preflight failed — nothing submitted")
            return 2

    batch_files = sorted((run / "batches").glob("*.json"))
    all_items: list[dict] = []
    for bf in batch_files:
        all_items += platform.load_batch(bf)

    # The two hands (Damon's 2026-09-17 ruling): cast, still, edit and the
    # song run on the machine hand — direct APIs, before the editor ever
    # sees them. Motion and talking stay the editor's. Which hand a station
    # is comes from providers.json's own doors[...].hand, never a kind name
    # written here.
    machine_items, editor_items = split_by_hand(all_items, reg, forced_provider=bool(a.provider))
    try:
        direct_manifest = run_machine_hand(
            machine_items, run, a.dry_run, brand=a.brand,
            openai_transport=openai_transport, google_transport=google_transport,
            byteplus_transport=byteplus_transport)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    still_for = still_for_map(machine_items)

    if not editor_items:
        # every station ran on the machine hand — there is no sheet to write
        # and nobody to hand it to. The run's clips are in media/ and
        # direct.json; `record` still owns line parity and the ledger.
        print(f"machine hand made everything — {len(direct_manifest)} item(s) in {run / 'media'}")
        if not a.dry_run:
            print(f"  python3 machine/run.py record {run} --direct")
        return 0

    # Which family this provider belongs to (fal, higgsfield, ...) comes
    # from providers.json, never from a name written here. A family with its
    # own submission module (providers_<family>.py) submits itself; a family
    # with none is, structurally, a hand-submitted house — write the sheet
    # and hand it to the person who submits there. Machine-hand items never
    # reach either path — they were made directly, above, and no longer
    # appear as things for the editor to make.
    family = prov.get("family", "")
    family_module = HERE / f"providers_{family}.py"
    if family and family_module.is_file():
        pf = _load(f"providers_{family}")
        if a.dry_run:
            pf.print_dry_run(editor_items, prov, reg)
            return 0
        results = pf.run_batch(editor_items, prov, reg, run, a.brand,
                                transport=transport, download=download)
        merge_results(run, results)
        return 0

    # No submission module for this family — nothing here ever calls the
    # network; a session or an editor submits by hand, so --dry-run changes
    # nothing.
    dest = write_submit_md(run, editor_items, prov, reg,
                            direct_manifest=direct_manifest, still_for=still_for)
    print(f"wrote {dest} — hand this to the editor, then:")
    print(f"  python3 machine/run.py record {run} --results <results.json>")
    return 0


# --------------------------------------------------------------- record

def archive_and_download(run: Path, iid: str, url: str, download) -> Path:
    """Never overwrite a prior take — archive it first. Ported from
    pull.py's archive()."""
    media_dir = run / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    pf = _load("providers_fal")
    ext = pf.ext_of(url)
    dest = media_dir / f"{iid}{ext}"
    if dest.exists():
        arch_dir = media_dir / "versions"
        arch_dir.mkdir(parents=True, exist_ok=True)
        n = 1
        while (arch_dir / f"{iid}-v{n}{dest.suffix}").exists():
            n += 1
        dest.rename(arch_dir / f"{iid}-v{n}{dest.suffix}")
    download(url, dest)
    return dest


def cmd_record(a, download=None, parity_transport=None) -> int:
    if not getattr(a, "results", None) and not getattr(a, "direct", False):
        print("record needs --results <file> or --direct", file=sys.stderr)
        return 2
    pf = _load("providers_fal")
    download = download or pf.fetch
    run = Path(a.run).resolve()
    run_json = read_json(run / "run.json", {}) or {}
    provider_name = run_json.get("provider")
    reg = platform.registry()
    prov = reg["providers"].get(provider_name) if provider_name else None

    by_id = {str(it.get("id")): it for it in preflight.other_batches(run)}
    if getattr(a, "direct", False):
        # the machine hand's own clips (direct.json) — already on disk, so
        # the only work left here is line parity and the results record.
        direct = read_json(run / "direct.json", {}) or {}
        rows = [{"id": iid, "status": "done", "job": iid, "file": r.get("file"),
                 "seconds": (by_id.get(iid, {}).get("params") or {}).get("duration")}
                for iid, r in direct.items()
                if str(r.get("file", "")).endswith(".mp4")]
    else:
        rows = json.loads(Path(a.results).read_text())
        if isinstance(rows, dict):
            rows = rows.get("items", [])

    results = read_json(run / "results.json", {}) or {}
    existing_ledger = read_json(run / "ledger.json", []) or []
    seen = {(r.get("job"), r.get("status")) for r in existing_ledger}
    failed = []

    for row in rows:
        iid = str(row["id"])
        item = by_id.get(iid, {})
        slug = None
        if prov:
            slug, _ = platform.resolve_model(item, prov, reg)
        slug = slug or platform.item_model(item) or "unknown"
        seconds = float(row.get("seconds") or (item.get("params") or {}).get("duration") or 0)
        tier = (item.get("params") or {}).get("tier")
        resolution = (item.get("params") or {}).get("resolution")
        status = row["status"]
        job = row.get("job", "?")
        note = None

        # Download BEFORE ledgering: a failed download must never leave a
        # ledger row for a clip that isn't on disk, and must never stop the
        # rows after it (e.g. an nsfw one with no url at all) from being
        # recorded.
        dest = None
        if row.get("file") and not row.get("url") and Path(row["file"]).is_file():
            dest = Path(row["file"])
            results[iid] = {**row, "file": str(dest.relative_to(run)) if dest.is_relative_to(run) else str(dest)}
        elif row.get("url"):
            try:
                dest = archive_and_download(run, iid, row["url"], download)
                results[iid] = {**row, "file": str(dest.relative_to(run))}
            except Exception as e:
                status = "failed"
                note = f"download failed: {e}"[:200]
                results[iid] = {**row, "status": status, "note": note}
                failed.append(iid)
        else:
            results[iid] = dict(row)

        # Line parity (Damon, 2026-09-18): a downloaded clip that carries a
        # line is transcribed and checked against it before anything else
        # ships on it — the exact defect that slipped through once, a
        # lip-synced clip that said the WRONG words. No key reachable is a
        # printed skip, never a failed record; --no-parity skips it outright.
        if dest is not None and item.get("lines") and not getattr(a, "no_parity", False):
            line_text = lineparity_mod.line_text_of(run, item)
            if line_text:
                parity_key = lineparity_mod.key_of()
                if not parity_key:
                    print(f"{iid}: no ELEVENLABS_API_KEY — skipping line parity")
                else:
                    try:
                        pres = lineparity_mod.check(dest, line_text, transport=parity_transport,
                                                     key=parity_key)
                    except SystemExit as e:
                        print(f"{iid}: line parity skipped — {e}")
                        pres = None
                    if pres:
                        preflight.verdict(run, iid, "parity", pres)
                        print(f"{iid}: parity {pres['verdict']} ({pres['match']}) "
                              f"— heard {pres['heard']!r}")

        # A retried `record` re-sends the same rows; without this a stuck
        # download that eventually gets re-run three times wrote three
        # identical ledger rows for the one job.
        key = (job, status)
        if key in seen:
            continue
        seen.add(key)
        preflight.ledger(run, slug, job, seconds, status, tier=tier,
                          resolution=resolution, brand=run_json.get("brand"),
                          shot=iid, note=note)

    write_json(run / "results.json", results)
    print(f"recorded {len(rows)} row(s)")
    if failed:
        print("failed to download: " + ", ".join(failed))
        return 1
    return 0


# ----------------------------------------------------------------- pack

def asks_section(plan: dict, results: dict, lines: dict, claims: dict) -> list[str]:
    """The six asks, mechanically, from what the plan already holds — the shape
    in ASKS-SPEC.md. A line the plan cannot decide gets the default, never a
    blank: a blank is a decision nobody made."""
    scenes = plan.get("scenes", [])
    hooks = [h for h in (plan.get("hooks") or plan.get("openings") or []) if h]
    primary = hooks[0] if hooks else None
    spare = [h for h in hooks[1:]] if hooks else []
    uncovered = [lid for lid in lines if not claims.get(lid)]
    flagged = [iid for iid, r in results.items() if r.get("checks")]
    L = []
    if spare:
        L.append(f"- **SCROLL STOPPERS** — {len(spare)}, one per hook not used as the opener: "
                 + "; ".join(str(h)[:80] for h in spare))
    else:
        L.append("- **SCROLL STOPPERS** — 3 (default): three alternative first three seconds, "
                 "same scene-1 setting, each from a different hook in the brief")
    L.append("- **HEADLINES** — 5 (default): opener-card lines under eight words, taken from the "
             "hooks, THE LOOP and the offer as written")
    L.append("- **VARIATIONS** — 2 (default): one alternate take of the opening scene and one of "
             "the offer scene, same line, different framing")
    if uncovered or flagged:
        L.append("- **EXTRA SCENES** — " + ", ".join(
            [f"insert for uncovered line {u}" for u in uncovered] +
            [f"cover for flagged clip {f}" for f in flagged]))
    else:
        L.append("- **EXTRA SCENES** — none — every line is carried and nothing is flagged")
    L.append(f"- **FORMATS** — 9:16 only, nothing at 4:5 or 1:1; a 15-second cutdown map over "
             f"{len(scenes) or '?'} scene(s), and a 4:5 safe-crop check: every face, product and word "
             f"inside the middle 70% of the frame")
    L.append("- **STYLES** — none — no style variation was asked for in the plan")
    return L


def build_editor_pack(run: Path, ad_name: str | None) -> str:
    run_json = read_json(run / "run.json", {}) or {}
    lines = read_json(run / "lines.json", {}) or {}
    ledger_rows = read_json(run / "ledger.json", []) or []
    results = read_json(run / "results.json", {}) or {}
    verdicts = read_json(run / "verdicts.json", None)
    plan = read_json(run / "plan.json", {}) or {}
    reg = platform.registry()
    claims = preflight.claims_in(preflight.other_batches(run), reg)

    L = [f"# {run_json.get('label', run.name)} — editor pack", "",
         f"**{run_json.get('brand', '?')} · {run_json.get('format', '?')} · "
         f"provider {run_json.get('provider', '?')}**", "",
         "## WHAT THIS IS", "",
         f"Video machine run `{run_json.get('label', run.name)}`, brand "
         f"`{run_json.get('brand', '?')}`, format `{run_json.get('format', '?')}`. "
         f"Source brief: `{run_json.get('source_brief', '?')}`.", "",
         "## THE CLIPS", ""]
    for iid, row in sorted(results.items()):
        who = [lid for lid, ids in claims.items() if iid in ids]
        flags = row.get("checks") or ([row["status"]] if row.get("status") not in (None, "done") else [])
        bit = f"- **{iid}** — `{row.get('file', '?')}` — {row.get('seconds', '?')}s"
        if who:
            bit += f" — carries {', '.join(who)}"
        if flags:
            bit += f" — FLAGGED: {', '.join(flags)}"
        L.append(bit)
    L += ["", "## LINE COVERAGE", ""]
    for lid in lines:
        who = claims.get(lid)
        L.append(f"- {lid}: " + (f"carried by {', '.join(who)}" if who else "UNCOVERED"))
    L += ["", "## POST", ""]
    post_notes = [s.get("post") for s in plan.get("scenes", []) if s.get("post")]
    L += [f"- {p}" for p in post_notes] if post_notes else ["none recorded"]
    L += ["", "## THE ASKS", ""] + asks_section(plan, results, lines, claims)
    L += ["", "## THE RECEIPT", ""]
    t = preflight.totals(ledger_rows)
    L.append(f"- billed: {t['billed_credits']} cr · ${t['billed_usd']:.3f}")
    L.append(f"- ambiguous: {t['ambiguous_credits']} cr · ${t['ambiguous_usd']:.3f}  (nsfw / ip_detected)")
    L.append(f"- re-rolls: {t['rerolls']}" + (f"  ({', '.join(t['rerolled_shots'])})" if t["rerolls"] else ""))
    L.append(f"- grand total: {t['grand_credits']} cr · ${t['grand_usd']:.3f}  over {t['rows']} row(s)")
    if verdicts:
        L += ["", "### Verdicts", ""]
        for cid, layers in verdicts.items():
            if not isinstance(layers, dict):
                continue
            for layer, v in layers.items():
                if not isinstance(v, dict):
                    continue
                bits = [f"{k}={v[k]}" for k in ("verdict", "half_second", "notes", "note")
                        if v.get(k) is not None]
                L.append(f"- {cid} · {layer}: " + (", ".join(bits) if bits else "recorded"))
    L += ["", "## THE NAME", "", ad_name or "(dry run — no name assigned)"]
    return "\n".join(L) + "\n"


def cmd_pack(a) -> int:
    run = Path(a.run).resolve()
    uncovered, dupes, not_shippable, concept_weak = preflight.coverage(run)
    if uncovered or dupes or not_shippable or concept_weak:
        for u in uncovered:
            print(f"uncovered: {u}")
        for d in dupes:
            print(f"duplicated: {d}")
        for m in not_shippable:
            print(m)
        for c in concept_weak:
            print(c)
        print(f"{len(uncovered)} uncovered, {len(dupes)} duplicated, "
              f"{len(not_shippable)} not shippable, {len(concept_weak)} concept-weak — not deliverable")
        return 2

    deliverable = run / "deliverable"
    deliverable.mkdir(parents=True, exist_ok=True)
    results = read_json(run / "results.json", {}) or {}
    media_dir = run / "media"
    for iid, row in results.items():
        if row.get("status") != "done":
            continue
        src = next(iter(sorted(media_dir.glob(f"{iid}.*"))), None)
        if src and src.exists():
            dst = deliverable / src.name
            if not dst.exists():
                shutil.copy2(src, dst)

    deliver_mod = _load("deliver")
    run_json = read_json(run / "run.json", {}) or {}
    fields = dict(media="video", source="ugc", talent="none", ratio="9x16", brief="none")
    fields.update({k: v for k, v in run_json.items() if k in ("brand", "format")})
    try:
        fields.update(deliver_mod.read_brief(run))
    except Exception:
        pass

    missing = [f for f in deliver_mod.N.AD_FIELDS if f != "batch" and not fields.get(f)]
    if missing:
        print("the brief does not state " + ", ".join(missing) +
              " — state them in the brief (run.json / brief.json / brief-final.md); "
              "a field guessed at pack time is a field the report cannot be trusted on")
        return 2

    try:
        ad, _rows = deliver_mod.D.deliver(str(deliverable), fields, batch=None, dry=a.dry_run)
    except SystemExit as e:
        print(str(e))
        return 2

    pack_md = build_editor_pack(run, ad)
    (deliverable / "EDITOR-PACK.md").write_text(pack_md)
    print(f"packed — {deliverable / 'EDITOR-PACK.md'}")
    return 0


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    s = sub.add_parser("start")
    s.add_argument("source", help="a brief (.md) or a plan (.json)")
    s.add_argument("--brand", required=True)
    s.add_argument("--format", required=True)
    s.add_argument("--label", required=True)
    s.add_argument("--provider")
    s.add_argument("--yes", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--bank")
    s.add_argument("--runs-root")
    s.add_argument("--cast-root", help="test/override root for a character's "
                    "characters folder; defaults to brands/<brand>/ai-elements/characters/ "
                    "(old name ai-cast/)")

    r = sub.add_parser("record")
    r.add_argument("run")
    r.add_argument("--results", help="the editor's results.json (Higgsfield / fal)")
    r.add_argument("--direct", action="store_true",
                   help="record the machine hand's own clips from direct.json instead")
    r.add_argument("--no-parity", action="store_true",
                    help="skip the automatic line-parity check on downloaded clips")

    p = sub.add_parser("pack")
    p.add_argument("run")
    p.add_argument("--dry-run", action="store_true")

    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        if a.verb == "start":
            return cmd_start(a)
        if a.verb == "record":
            return cmd_record(a)
        if a.verb == "pack":
            return cmd_pack(a)
    except (SystemExit, ValueError, OSError) as e:
        if isinstance(e, SystemExit) and isinstance(e.code, int):
            return e.code
        print(e, file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    sys.exit(main())
