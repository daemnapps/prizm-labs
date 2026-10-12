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
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    The count here was right only while this file sat in the team notes The move
    to components/ on 2026-09-22 made it resolve to ~/Projects, one level too
    high — outside the repo entirely. A marker cannot go quietly wrong the next
    time something moves. AI_WORKSPACE still wins when it names a workspace.
    """
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(start).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError(f"no workspace found upward of {here}")



HERE = Path(__file__).resolve().parent
WORKSPACE = _workspace()
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
safezone = _load("safezone")
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
    """Element uuids in `prompt_text` that brands/<brand>/ai-elements/element-facts.json
    marks as a product (`kind` or `role` == "product"). A brand with no
    facts file — or none named — simply has no products, never an error."""
    ids = ELEMENT.findall(prompt_text or "")
    if not ids or not brand:
        return []
    f = WS / "brands" / brand / "ai-elements" / "element-facts.json"
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
        # the doctrine's ad-framework id (a row's full name is read as its
        # id), or "observed — …"; the gate refuses anything else (brief v15)
        "framework": mi.framework_id(piece.get("framework")),
    }
    table = dict(re.findall(r"\| (.+?) \| \`<<<([0-9a-f-]{36})>>>\` \|", text))
    doc, _ = scenes_mod.json_block(text)
    carried = {k: doc[k] for k in PIECE_ELEMENTS
               if isinstance(doc, dict) and k in doc and doc[k] is not None}
    # AN ENDCARD'S PRODUCT is settled here, once, from the brief's own words
    # (its refs, its plate, the product_lock) when the endcard does not name
    # it — so the item, plan.json and the edit all read the same slug.
    raw = {str(r.get("id")): r for r in (doc or {}).get("scenes") or []
           if isinstance(r, dict)} if isinstance(doc, dict) else {}
    for s in parsed:
        if s.get("kind") == "endcard" and not (s.get("endcard") or {}).get("product"):
            slug, _why = mi.endcard_product(raw.get(s["id"]) or {}, doc, brand)
            if slug:
                s["endcard"]["product"] = s["product"] = slug
    return {
        **carried,
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
                         "cutaways", "to_camera_missing",
                         # ELEMENTS.md §1/§4 (2026-09-23): carried untouched
                         # for the edit — the scroll-stopper and the order a
                         # cutdown cuts in. The unit a version swaps is the
                         # doctrine `section` above (brief v15); v14's
                         # `module` is retired and never carried
                         "opens", "priority")

# ELEMENTS.md §2–§4: the piece-level elements the edit reads, carried from the
# brief's block into plan.json untouched (music and sfx then gain their bank
# row at `start`).
PIECE_ELEMENTS = ("layers", "music", "sfx", "hooks", "song")
# kinds made as one still and no clip; and the kinds that may sit in silence
STILL_ONLY = ("card", "screen", "endcard")
SILENT_OK = ("card", "screen", "endcard", "split")


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
# FEWER SCENES, MORE FRAMES (the owner, 2026-09-18, as corrected the same day). A
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
    first_frame = next((f for f in scene.get("frames", []) if f.get("role") == "first"), {})
    for f in scene.get("frames", []):
        role = f.get("role")
        iid = f"{scene['id']}-{'F1' if role == 'first' else 'FLAST'}"
        contract_id = "still-generate"
        prompt_missing: list[str] = []
        if role != "first" and first_frame.get("viewpoint") and not f.get("viewpoint"):
            # the body geometry travels from the first frame to its edit
            f = {**f, "viewpoint": first_frame["viewpoint"]}
        if role == "first":
            kind = "still"
            params = {"prompt": mi.still_prompt(f, piece)}
            bad = mi.viewpoint_fault(scene, f, f"{scene['id']}'s first frame")
            if bad:
                prompt_missing.append(bad)
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
            "viewpoint": f.get("viewpoint") or "",
            "prompt_missing": prompt_missing,
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
                 timing: dict | None = None, model: str | None = None) -> dict:
    """ONE clip for the scene, in the two shapes the settled door takes
    (the owner's ruling 2026-09-22, after the bake-off) — the door row in
    `model-inputs.json` decides which, never this code:

      * a TALKING scene — the FIRST FRAME as `image_references`, the scene's
        own slice of the one voice track as `audio_references`, and NO
        end_image: the backend refuses a first/last frame beside reference
        media, so the timeline's last beat says in words where it ends;
      * a SILENT scene — the FIRST FRAME as `start_image`, the LAST FRAME as
        `end_image`, no audio: the designed camera move lands.

    **Nothing else travels on the clip.** The first frame already carries
    the identity, the wardrobe, the room and the light; a cast sheet or a
    style frame attached beside it is a second opinion about the same face.
    On the alternate door (first + last + audio together, up to 30 s) the
    same code builds the 2026-09-18 shape from that door's own row."""
    talking = bool(scene.get("to_camera"))
    sid = "talking" if talking else "motion"
    # THE RUN PICKS (the owner, 2026-09-22: "we should have the ability to pick
    # which models we want to run with" — MiniMax's lip sync is the best in
    # the house and its physical cause-and-effect is the worst, so one door
    # for every scene is the wrong shape). Order: the SCENE's own pick, then
    # the run's, then the registry's settled door. A name nothing answers to
    # is a gate finding, never a silent fall back to the settled door.
    pick = str(scene.get("model") or model or "").strip() or None
    frames = scene.get("frames") or []
    first = next((f for f in frames if f.get("role") == "first"), None)
    last = next((f for f in reversed(frames) if f.get("role") == "last"), None)
    row = ((timing or {}).get("scenes") or {}).get(scene["id"], {})
    seconds = clip_seconds_of(scene, row, timing)

    # The last frame is a real input where the door takes one, and words
    # where it does not — the sheet says which, in the door's own reason.
    door_id, end_attached, how = mi.end_image_door(sid, pick)
    end_attached = end_attached and last is not None
    scene = {**scene, "end_frame_attached": end_attached}
    params = {"prompt": mi.clip_prompt(scene, piece, seconds, timing, talking=talking)}
    if piece.get("aspect"):
        params["aspect_ratio"] = piece["aspect"]
    # A door that makes one resolution (the settled clip door: 2K) fixes the
    # clip's; the piece's Resolution still sizes the stills.
    fixed_res = mi.fixed_resolution(sid, pick)
    if fixed_res:
        params["resolution"] = fixed_res
    elif piece.get("resolution"):
        params["resolution"] = piece["resolution"]
    if seconds:
        # ceil, floored at the door's minimum. The CEILING is never clamped:
        # a paragraph past it is refused by name (rule 12) so the scene is
        # split at a beat or routed to the alternate door, never quietly
        # shortened.
        low = (mi.duration_span(sid, pick) or [4])[0]
        params["duration"] = int(max(int(low), math.ceil(float(seconds))))
    # params only some doors take (the alternate's mode and generate_audio)
    # come off the door row, never from here
    for k, v in mi.door_params(sid, pick).items():
        params.setdefault(k, v)

    cast_name = cast_display_name(cast)
    who = (scene.get("who") or cast_name or "").split("·")[0].strip()
    start_id = f"{scene['id']}-F1" if first else None
    last_id = f"{scene['id']}-FLAST" if last else None
    first_role = mi.first_frame_role(sid, pick)
    medias: list[dict] = []
    if start_id:
        medias.append({"role": first_role, "value": start_id})
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
        "first_frame_role": first_role,
        "last_frame": last_id,
        "end_frame": last_id if end_attached else None,
        "door": door_id,
        "model": mi.model_of(sid, pick),
        "model_picked": bool(pick),
        "model_pick_by": ("the scene" if scene.get("model") else
                          ("the run" if model else "the registry")),
        "end_frame_how": how,
        "resolution_fixed": bool(fixed_res),
        "beats": [dict(b) for b in (scene.get("beats") or [])],
        "beat_windows": [list(w) for w in
                         mi.beat_windows(scene, seconds, timing)],
        "frames": [i for i in (start_id, last_id) if i],
        "to_camera": talking,
        # A B-ROLL SCENE IS A SCENE (the owner, 2026-09-19: "there is no B-roll" —
        # every scene was the speaker to camera). Its paragraph is part of the
        # same continuous read and is still recorded and sliced; it just does
        # not travel on the clip. It is laid UNDER the picture at the edit,
        # and the sheet says which file goes over which scene.
        "vo_over": None if talking else (slice_ if scene.get("voice") else None),
        # what the four blocks could not be built from — the gate names each
        # one, and a prompt is never written as a fragment
        "prompt_missing": mi.clip_missing(scene, piece, seconds, timing, talking=talking),
        # a pick nothing answers to is its OWN finding, not a hole in the
        # prompt — the prompt is fine; the door is the thing that does not exist
        "model_missing": [f for f in [mi.model_fault(pick, sid)] if f],
        # clauses the hold sentence could not carry because a beat undoes
        # them — the brief's finding, printed, never silently swallowed
        "hold_dropped": mi.hold_dropped(scene),
    }
    return _carry_scene_metadata(item, scene)


def card_item_of(scene: dict, cast: dict, piece: dict, brand: str | None) -> dict:
    """A CARD (the owner, 2026-09-23: cards are made at production, not left for
    the edit). ONE still on the same door every first frame uses — the plate,
    the picture with no words in it — and no clip. Type is a layer, never a
    generation: the card's exact words, the moment they land on and their
    sound travel on the item (and in plan.json) as `card`, for the edit to
    set on the plate."""
    card = dict(scene.get("card") or {})
    params = {"prompt": mi.plate_prompt(card.get("plate", ""), piece)}
    size = mi.size_for(piece.get("aspect"))
    if size:
        params["size"] = size
    q = mi.house_default(mi.field_named("still-generate", "quality") or {})
    if q:
        params["quality"] = q
    names = [n for n in (cast.get("names") or []) if n]
    plate = str(card.get("plate") or "").lower()
    suffix = mi.card_plate().get("item_suffix") or "PLATE"
    item = {
        "id": f"{scene['id']}-{suffix}", "kind": "still", "contract": "still-generate",
        "for": scene["id"], "frame": 1, "frame_role": "plate", "edit_of": None,
        "delta": "", "viewpoint": "", "prompt_missing": [],
        "params": params,
        "medias": [{"role": "image_references", "value": r}
                   for r in (card.get("refs") or []) if r],
        # a card has nobody in it unless its plate names someone from the cast
        "characters": [n for n in names if n.lower() in plate],
        "products": products_of(params["prompt"], brand),
        "lines": [],
        "card": {k: card.get(k) for k in ("lines", "lands_on", "sfx")},
        "to_camera": False,
        # a card may sit over a slice of the one read; like B-roll, that
        # slice is laid under it at the edit and never travels on a door
        "vo_over": f"vo/{scene['id']}.mp3" if scene.get("voice") else None,
    }
    return _carry_scene_metadata(item, scene)


def _plate_still(scene: dict, cast: dict, piece: dict, brand: str | None,
                 plate: str, suffix: str, refs: list, carry_key: str, carry: dict) -> dict:
    """ONE text-free still on the first-frame door — the card's shape, for
    a screen and a greenscreen's background (ELEMENTS.md §1). The words that
    will be read on it never enter the prompt; they travel as `carry`."""
    params = {"prompt": mi.plate_prompt(plate, piece)}
    size = mi.size_for(piece.get("aspect"))
    if size:
        params["size"] = size
    q = mi.house_default(mi.field_named("still-generate", "quality") or {})
    if q:
        params["quality"] = q
    names = [n for n in (cast.get("names") or []) if n]
    item = {
        "id": f"{scene['id']}-{suffix}", "kind": "still", "contract": "still-generate",
        "for": scene["id"], "frame": 1, "frame_role": "plate", "edit_of": None,
        "delta": "", "viewpoint": "", "prompt_missing": [],
        "params": params,
        "medias": [{"role": "image_references", "value": r} for r in refs if r],
        "characters": [n for n in names if n.lower() in plate.lower()],
        "products": products_of(params["prompt"], brand),
        "lines": [],
        carry_key: carry,
        "to_camera": False,
    }
    return _carry_scene_metadata(item, scene)


def _plate_kinds() -> dict:
    return (mi.elements().get("plate_kinds") or {})


def screen_item_of(scene: dict, cast: dict, piece: dict, brand: str | None) -> dict:
    """A SCREEN — a review, a comment, a thread, a site, an order page — made
    as one plate with every word left blank; the legible text is the edit's."""
    s = dict(scene.get("screen") or {})
    item = _plate_still(scene, cast, piece, brand, s.get("plate", ""),
                        _plate_kinds().get("screen", {}).get("item_suffix") or "PLATE",
                        s.get("refs") or [], "screen",
                        {k: s.get(k) for k in ("surface", "lines", "lands_on")})
    item["vo_over"] = f"vo/{scene['id']}.mp3" if scene.get("voice") else None
    return item


def greenscreen_item_of(scene: dict, cast: dict, piece: dict, brand: str | None) -> dict:
    """A GREENSCREEN's BACKGROUND — one text-free still. The presenter is the
    talker scene's own clip; the edit keys one over the other."""
    g = dict(scene.get("greenscreen") or {})
    return _plate_still(scene, cast, piece, brand, g.get("background", ""),
                        _plate_kinds().get("greenscreen", {}).get("item_suffix") or "BG",
                        g.get("refs") or [], "greenscreen",
                        {k: g.get(k) for k in ("talker_scene", "layout")})


def endcard_item_of(scene: dict, cast: dict, piece: dict, brand: str | None,
                    doc: dict | None = None) -> dict:
    """An ENDCARD — an EDIT of the brand's REAL packshot into the plate the
    brief describes, never a product generated from words (ELEMENTS.md §1).
    The packshot is the edit's first and only product reference; the offer
    lines, the CTA and the guarantee travel as data for the edit to set."""
    e = dict(scene.get("endcard") or {})
    bf = mi._brandfiles()
    product, why_p = mi.endcard_product({"kind": "endcard", "endcard": e}, doc, brand)
    shot, why = (bf.packshot_of(brand, product) if product else (None, why_p))
    keep = _clean_line(mi.elements().get("endcard_keep_line"))
    base = mi.plate_prompt(e.get("plate", ""), piece)
    params = {"prompt": " ".join(p for p in (keep, base) if p)}
    size = mi.size_for(piece.get("aspect"))
    if size:
        params["size"] = size
    q = mi.house_default(mi.field_named("still-edit-fidelity", "quality") or {})
    if q:
        params["quality"] = q
    fid = mi.house_default(mi.field_named("still-edit-fidelity", "input_fidelity") or {})
    if fid:
        params["input_fidelity"] = fid
    others = [r for r in (e.get("refs") or []) if r and "packshot" not in r.lower()]
    refs = ([str(shot)] if shot else []) + others
    item = {
        "id": f"{scene['id']}-{_plate_kinds().get('endcard', {}).get('item_suffix') or 'PACKSHOT'}",
        "kind": "edit", "contract": "still-edit-fidelity",
        "for": scene["id"], "frame": 1, "frame_role": "packshot", "edit_of": None,
        # the edit names its change: the brief's own plate sentence
        "delta": e.get("plate", ""), "viewpoint": "",
        "prompt_missing": [] if shot else [f"the real packshot ({why})"],
        "params": params,
        "medias": [{"role": "image_references", "value": r} for r in refs],
        "characters": [],
        "products": [product] if product else [],
        "packshot": {"product": product, "file": str(shot) if shot else None, "why": why},
        "lines": [],
        "endcard": {k: e.get(k) for k in ("offer_lines", "cta", "guarantee")},
        "to_camera": False,
        "vo_over": f"vo/{scene['id']}.mp3" if scene.get("voice") else None,
    }
    return _carry_scene_metadata(item, scene)


def _clean_line(s) -> str:
    return " ".join(str(s or "").split())


def split_items_of(scene: dict, cast: dict, piece: dict, brand: str | None,
                   timing: dict | None = None, model: str | None = None) -> list[dict]:
    """A SPLIT — two B-roll pictures on one screen. Each side is made exactly
    like B-roll: its first frame, its last frame as an edit of it, and one
    silent clip; the side's clip runs as long as the split's own slice of the
    read. The paragraph is laid under the pair once, on the left."""
    x = dict(scene.get("split") or {})
    timing = dict(timing or {})
    rows = dict(timing.get("scenes") or {})
    items: list[dict] = []
    for side in ("left", "right"):
        s = dict(x.get(side) or {})
        if not s:
            continue
        if scene["id"] in rows:
            rows[s["id"]] = rows[scene["id"]]
        s = {**s, **{k: scene[k] for k in ("section", "opens", "priority") if k in scene}}
        t = {**timing, "scenes": rows}
        side_items = frame_items_of(s, cast, piece, brand) + [
            clip_item_of(s, cast, piece, brand, t, model)]
        for it in side_items:
            it["split"] = {"of": scene["id"], "side": side, "layout": x.get("layout"),
                           "labels": x.get("labels") or []}
        clip = side_items[-1]
        clip["vo_over"] = (f"vo/{scene['id']}.mp3" if side == "left" and scene.get("voice")
                           else None)
        items += side_items
    return items


def scene_shape_items(plan: dict, brand: str | None, timing: dict | None = None,
                      model: str | None = None, doc: dict | None = None) -> list[dict]:
    cast = plan.get("cast", {}) or {}
    piece = plan.get("piece", {}) or {}
    model = model or plan.get("clip_model")
    items: list[dict] = []
    for s in plan.get("scenes", []):
        if s.get("kind") == "card":
            items.append(card_item_of(s, cast, piece, brand))
            continue
        if s.get("kind") == "screen":
            items.append(screen_item_of(s, cast, piece, brand))
            continue
        if s.get("kind") == "endcard":
            items.append(endcard_item_of(s, cast, piece, brand, doc))
            continue
        if s.get("kind") == "split":
            items += split_items_of(s, cast, piece, brand, timing, model)
            continue
        if s.get("source_plan") == "cut" and s.get("owned_file"):
            # CUT FROM OUR FOOTAGE (2026-10-05): the footage step matched this
            # B-roll scene to a clip we own (owned_file, owned_in–owned_out);
            # the edit cuts it, nothing is generated for it.
            continue
        if str(s.get("held") or "").strip():
            # A HELD SCENE makes nothing (2026-09-19). Its place in the order
            # is kept, its section is on the record and the one fact that
            # would release it is written down — but no door is handed a
            # frame nobody could describe. `cmd_start` says which scenes
            # these are, so a held scene is a finding rather than a silence.
            continue
        items += frame_items_of(s, cast, piece, brand)
        items.append(clip_item_of(s, cast, piece, brand, timing, model))
        if s.get("kind") == "greenscreen":
            items.append(greenscreen_item_of(s, cast, piece, brand))
    return items


def song_item_of(plan: dict, brand: str | None) -> dict | None:
    """THE LEGACY SONG — a prompt-shaped `song` block, made on the Lyria
    ALTERNATE. Since 2026-09-23 the song door is ElevenLabs Music (providers.json) and a
    brief's song block with `sections` is printed by song.py in cmd_start
    (SONG-CHAIN.md); that block has no `prompt`, so it never becomes an item
    here. A plan carries its own `song` block only when the format is sung
    — this module doesn't need to know which formats those are;
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


def batches_of(plan: dict, brand: str | None, timing: dict | None = None,
               model: str | None = None) -> list[dict]:
    cast = plan.get("cast", {}) or {}
    if plan.get("shape") == "scene" or any(s.get("frames") for s in plan.get("scenes", [])):
        items = scene_shape_items(plan, brand, timing, model)
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
        if c.get("source_plan") == "cut" and c.get("owned_file"):
            continue   # cut from our footage (2026-10-05) — nothing generated
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
# the owner's 2026-09-17 ruling: cast, still, edit, voice and song run on the
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

    `forced_provider` — the owner named a house with `--provider`: the motion
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
    # a frame this run made in an earlier pass (a picture redone alone with --only: S10-FLAST edits S10-F1,
    # which is on disk but not in this pass's manifest — 2026-10-08 it resolved to nothing)
    for ext in ("png", "jpg", "webp"):
        f = run / "media" / f"{value}.{ext}"
        if f.is_file():
            return f
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
        # the banked element (runs/ai-elements/<brand>/casting/<id>/master.*) — where people live since 2026-09-23
        EP = _load("element_paths")
        for cand in (name, *(item.get("characters") or [])):
            slug = re.sub(r"[^a-z0-9]+", "-", str(cand or "").lower()).strip("-")
            if not slug:
                continue
            home = EP.casting_home(brand, slug)
            for fn in ("master.jpg", "master.png", "master.webp"):
                if (home / fn).is_file():
                    return home / fn
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


def piece_first_frame(items: list[dict], made: dict) -> Path | None:
    """The piece's FIRST FRAME — the first scene's first frame, in play
    order, that is on disk. Every clip is matched to it (ELEMENTS.md §5)."""
    for it in items:
        if it.get("frame_role") == "first":
            f = (made.get(str(it.get("id"))) or {}).get("file")
            if f and Path(f).is_file():
                return Path(f)
    return None


def colour_match_clip(run: Path, iid: str, clip, ref: Path | None) -> dict | None:
    """The post step after a clip lands: matched to the piece's first frame,
    on a copy, the original archived in media/versions. Printed either way —
    a skipped match is said, never silent."""
    if not clip or ref is None:
        if clip:
            print(f"  {iid}: clip colour skipped — the piece's first frame is not on disk")
        return None
    res = _load("colour_match").match_clip(clip, ref, archive_dir=run / "media" / "versions",
                                           stem=iid)
    print(f"  {iid}: clip colour {'matched' if res['matched'] else 'not matched'} — {res['why']}")
    return res


def review_pictures(run, items, made):
    try:
        q = str(HERE.parent.parent.parent / "components" / "quality-checks")
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        sb = _load("storyboard_plan"); idm = _load("identity")
        plan = read_json(run / "storyboard.json", {}) or {}
        td = plan.get("teardown")
        shots = (HERE / td / "framemap" / "shots").resolve() if td else None
        rows = []
        for it in items:
            iid = str(it.get("id")); f = (made.get(iid) or {}).get("file")
            if it.get("kind") != "still" or not f:
                continue
            compare = []
            k = it.get("swipe_camera")
            if k and shots:
                fr = sb.usable_frame(shots, k)
                if fr:
                    compare.append(fr)
            compare += idm.masters_of(it.get("medias"))
            rows.append({"id": iid, "output": [f], "compare": compare})
        if rows:
            res = review.after_stage("video-production", "pictures", run, items=rows)
            bad = [k for k, v in res.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
            print(f"picture review: {len(rows) - len(bad)} pass, {len(bad)} sent back — {run / 'qc-log' / 'QC-LOG.md'}")
    except Exception as e:
        print(f"picture review not run ({type(e).__name__}: {e})")



def public_safe(gen, prompt, refs, out, **kw):
    """One picture call; when the image door refuses it as a PUBLIC FIGURE, the swipe frames among the references
    (anything under a teardown's framemap/) are sent again once with every head covered — the frame stays sharp,
    only faces are masked (swipe_guide.make). the owner ruled 2026-10-08 the swipe is used whole, people included; a
    celebrity swipe (the athlete's press conference) is the one case the door will not take, and no real public figure's
    face may be lifted into ours. Any other refusal is raised as it was."""
    try:
        return gen(prompt, refs, out, **kw)
    except RuntimeError as e:
        if "public-figure" not in str(e) and "public_figure" not in str(e):
            raise
        sg = _load("swipe_guide")
        covered = []
        for r in refs:
            rp = Path(r)
            if "framemap" in rp.parts:
                dst = rp.with_name(rp.stem + "-faces-covered.jpg")
                if not dst.exists():
                    sg.make(rp, dst)
                covered.append(str(dst))
            else:
                covered.append(r)
        if covered == list(refs):
            raise
        print(f"  {Path(out).stem}: refused as a public figure — sent again with the swipe frame's faces covered")
        try:
            return gen(prompt, covered, out, **kw)
        except RuntimeError as e2:
            if "public-figure" not in str(e2) and "public_figure" not in str(e2):
                raise
        # the person is known by more than the face (the athlete's jersey and team backdrop): the swipe frame stays out
        # of this picture — the written composition, the cast and the set carry it, as before 2026-10-08
        kept = [r for r in refs if "framemap" not in Path(r).parts]
        print(f"  {Path(out).stem}: still refused — sent without the swipe frame")
        return gen(prompt, kept, out, **kw)

def faces_of(it, res, iid, dry_run):
    """THE FACE CHECK, every still with one of our people in it (2026-10-02):
    each person against their own reference, three asks, the majority wins.
    A CHECK ONLY — it changes nothing; a DIFFERENT is printed and filed on the
    picture's record for the picture review and the owner's read."""
    if dry_run or not res.get("file"):
        return
    idm = _load("identity")
    for master in idm.masters_of(it.get("medias")):
        faces = idm.check(res["file"], [master])
        it.setdefault("face_check", []).extend(faces)
        print(f"  {iid}: face {Path(master).parent.parent.name} = {faces[0]['verdict']}")


def ruled_model(reg, station, used):
    """THE MODEL LOCK (the owner, 2026-10-02: "you switched the model … that should
    have never happened … this cannot happen again"). A picture, edit or clip
    made on any model but the one ruled for its station in providers.json stops
    the run, named. A model changes only by the owner's ruling, written there."""
    door = (reg.get("doors") or {}).get(station) or {}
    want = door.get("model")
    if want and used and str(used) != str(want):
        raise SystemExit(f"MODEL NOT RULED: {station} was made on {used!r}; the ruled model is {want!r} "
                         f"(providers.json doors.{station}, ruled {door.get('ruled', '?')}). Only the owner changes it.")


def product_gate(refs, iid: str = "?"):
    """THE PRODUCT KIT GATE (2026-10-02, PRODUCT-KITS.md): any picture made from
    a real photo of one of our products needs that product's truth kit first.
    A reference that is a photo of a product with no usable kit STOPS the run
    before anything is paid for, with one plain line naming the product.
    Returns (brand, slug, kit.json) of the product in the references, or None."""
    pk = _load("product_kit")
    for r in refs:
        who = pk.product_of_path(r)
        if not who:
            continue
        why = pk.gate(*who)
        if why:
            raise SystemExit(f"{iid}: {why}")
        return who[0], who[1], pk.home(*who) / "kit.json"
    return None


def product_of(it, res, iid, prompt, refs, out, dry_run, transport=None, key=None):
    """THE PRODUCT CHECK, every still with the real product in it (2026-10-02):
    its shape is measured against the product's kit (product_check.py: length
    over width of its exact cut-out). Off by more than the tolerance, twice at
    most, the
    picture kept and only the product replaced from its kit (product_fix.py,
    the image-edit "Wrong product" fix on the ruled edit door); the closest take
    is kept and the verdict filed on the item. The kit is found by brand + slug
    from the product photo among the references (product_kit.product_of_path);
    a product with no kit never gets here — product_gate stopped the run."""
    if dry_run or not res.get("file"):
        return res
    got = product_gate(refs, iid)
    if got is None:
        return res
    brand, slug, kit_path = got
    # the fix keeps the picture and replaces only the product (product_fix.py)
    v = _load("product_fix").fix(res["file"], kit_path)
    it["product_check"] = v
    want = json.loads(kit_path.read_text())["outline"].get("axis_ratio")
    print(f"  {iid}: {brand}/{slug} shape {v['shape'].get('measured')} (real {want}) — {'PASS' if v['ok'] else 'HELD: ' + '; '.join(v['why'])}")
    return res


def run_machine_hand(items: list[dict], run: Path, dry_run: bool, brand: str | None = None,
                      openai_transport=None, google_transport=None, byteplus_transport=None,
                      openai_key: str | None = None, google_key: str | None = None,
                      byteplus_key: str | None = None, clip_colour: bool = True,
                      zone_caller=None) -> dict:
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
    # >>> APPROVAL-PAGE LEARNINGS HOOK (components/meta-upload/learnings.py) — prints recent rejections to the run log; changes no prompt
    try:
        import importlib.util as _iu
        _ls = _iu.spec_from_file_location("meta_learnings", Path(__file__).resolve().parents[2].parent / "components" / "meta-upload" / "learnings.py")
        _L = _iu.module_from_spec(_ls); _ls.loader.exec_module(_L)
        _L.show("video-production", 5, brand)
    except Exception:
        pass
    # <<< APPROVAL-PAGE LEARNINGS HOOK
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
        # AN ENDCARD edits the brand's REAL packshot and nothing else will
        # do: a declared photo that is a URL is fetched through
        # image-production's cache now, and if there is still no file the
        # run STOPS rather than let the edit door draw a product from words.
        shot = it.get("packshot")
        if shot is not None:
            f = shot.get("file")
            if not (f and Path(f).is_file()):
                got, why = mi._brandfiles().packshot_of(brand, shot.get("product"),
                                                        fetch=not dry_run)
                if got is not None and Path(str(got)).is_file():
                    it = {**it, "medias": [{"role": "image_references", "value": str(got)}]
                          + [m for m in it.get("medias") or [] if m.get("value") != f]}
                elif not dry_run:
                    raise SystemExit(f"{iid}: no real packshot on this machine for "
                                     f"{shot.get('product')!r} ({why}) — an endcard is an "
                                     f"edit of the brand's own photograph; nothing is drawn "
                                     f"from words")
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
            if kind == "still":
                product_gate(refs, iid)            # a product with no truth kit stops here, before the spend
            res = public_safe(direct_openai.generate, prompt, refs, out, transport=openai_transport,
                              key=openai_key, dry_run=dry_run)
            if not dry_run:
                ruled_model(reg, "cast" if kind == "cast" else "still", res.get("model"))
            if kind == "still":
                faces_of(it, res, iid, dry_run)
                res = product_of(it, res, iid, prompt, refs, out, dry_run, openai_transport, openai_key)
            model, file_ = res["model"], res.get("file")
            colour_match_to(it, file_, manifest)
        elif kind in ("edit", "restyle"):
            out = media_dir / f"{iid}.png"
            if not refs and not dry_run:
                # an edit with nothing to edit is a generation from words — a stranger in another room came back
                # for S10-FLAST (2026-10-08). It stops, named.
                raise SystemExit(f"{iid}: an edit with no reference resolved — nothing is drawn from words")
            # ONE IMAGE DOOR (the owner, 2026-09-18: "gpt for all image work both
            # initial reference gen and edits"): the registry's edit door
            # decides, and today it is direct:openai — images/edits with the
            # previous frame first and the cast sheet second. direct:google
            # stays the alternate the registry can flip back to.
            edit_door = ((reg.get("doors") or {}).get("edit") or {}).get("primary", "")
            if edit_door == "direct:openai":
                res = public_safe(direct_openai.generate, prompt, refs, out, transport=openai_transport,
                                  key=openai_key, dry_run=dry_run)
            else:
                res = direct_google.edit_image(prompt, refs, out, transport=google_transport,
                                                key=google_key, dry_run=dry_run)
            if not dry_run:
                ruled_model(reg, "edit", res.get("model"))
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
            held = zone_held(it, manifest)
            if held:
                print(f"  {iid}: clip NOT made — {held}")
                continue
            still = _still_of(it, run, manifest)
            if still is None and not dry_run:
                raise SystemExit(f"{iid}: nothing to animate from — no still was made for it "
                                  f"and it carries no start_image path")
            audio = _audio_of(it, run)
            talking_door = str((reg.get("doors") or {}).get("talking", {}).get("primary", ""))
            if audio is not None and talking_door == "direct:omni":
                # the controlled-Omni recipe (the owner 2026-09-18): the line is
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

        zone = None
        if kind in ("still", "edit", "restyle") and safezone.is_frame(it):
            if dry_run:
                zone_plan_line(iid)
            else:
                zone, file_ = zone_gate(it, file_, refs, manifest, run, brand, zone_caller,
                                        google_transport, openai_transport, openai_key)
        if dry_run:
            continue
        row = {"file": file_, "model": model, "request_id": res.get("request_id") or res.get("task_id"), "at": now()}
        if zone is not None:
            row["subject_box"] = zone.get("subject_box")
            row["zone"] = {k: zone.get(k) for k in ("verdict", "outside", "remade", "why",
                                                     "subject_box_still", "size", "zone", "frame")
                           if zone.get(k) is not None}
        if kind in ("motion", "talking"):
            row["usage"] = res.get("usage")
            row["talking"] = _audio_of(it, run) is not None
            for k in ("recipe", "parity_native", "parity_final", "native"):
                if res.get(k) is not None:
                    row[k] = res[k]
            if res.get("parity_final"):
                preflight.verdict(run, iid, "parity", res["parity_final"])
            if clip_colour:
                cm = colour_match_clip(run, iid, file_, piece_first_frame(items, manifest))
                if cm:
                    row["colour"] = cm
        if kind == "audio":
            row["timing"] = res.get("timing")
            row["timed"] = res.get("timed")
        if it.get("face_check"):
            row["face_check"] = it["face_check"]
            preflight.verdict(run, iid, "face", {"verdict": "FAIL" if any(
                f["verdict"] == "DIFFERENT" for f in it["face_check"]) else "PASS", "faces": it["face_check"]})
        manifest[iid] = row
        preflight.ledger(run, model, iid, 0.0, "done", brand=brand, shot=iid, usage=(res or {}).get("usage"))

    if not dry_run:
        write_json(run / "direct.json", manifest)
        record_subject_boxes(run, items, manifest)
    else:
        n = sum(1 for it in items if safezone.is_frame(it))
        if n:
            print(f"  subject zone: {n} frame(s) would be checked — about "
                  f"${n * safezone.CHECK_USD:.3f}, plus at most {n} fix edit(s) "
                  f"(~${safezone.FIX_USD:.2f} each) for frames found outside")
    return manifest


# ------------------------------------------------------- the subject zone
#
# Every still production makes — first and last frames, card / screen /
# split / greenscreen plates, the endcard packshot — is measured against the
# centred 4:5 zone of the 9:16 frame (the owner, 2026-09-23; safezone.py). A
# frame outside it gets ONE edit, the frame-edit discipline (the frame first,
# the cast sheet second, the one change, the keep-line), and is measured
# again; still outside, it is HELD — no clip is made from it and `pack`
# refuses the run. A frame the judge could not measure is recorded as
# UNCHECKED and is not shippable either. Never shipped silently.

def zone_plan_line(iid: str) -> None:
    print(f"  {iid}: subject zone — would send the still to "
          f"{safezone_entry().get('vendor_model')} with {safezone.prompt_path().name} "
          f"(~${safezone.CHECK_USD:.3f}); outside the 4:5 zone → one fix edit "
          f"(~${safezone.FIX_USD:.2f}) and one more check")


def safezone_entry() -> dict:
    return safezone._ip()[1].judge_entry()


def zone_held(it: dict, manifest: dict) -> str | None:
    """Why a clip may not be made from its frame, or None. Only a MEASURED
    failure after the one fix holds the clip; an unchecked frame does not
    stop the run, it stops the pack."""
    row = (manifest.get(str(it.get("start_frame") or "")) or
           manifest.get(f"{it.get('id')}-still") or {})
    z = row.get("zone") or {}
    if z.get("verdict") == "FAIL":
        return (f"its frame's {', '.join(z.get('outside') or ['subject'])} is outside the "
                f"4:5 zone after one fix — remake the frame (remake.py order --element frame)")
    return None


def zone_gate(it: dict, file_, refs: list, manifest: dict, run: Path, brand: str | None,
              zone_caller, google_transport, openai_transport, openai_key):
    """Check one frame; on FAIL, one fix edit and one re-check. Returns
    (zone result, the file that now stands for the frame)."""
    iid = str(it.get("id"))
    caller = zone_caller or safezone.default_caller(google_transport)
    z = safezone.check(file_, caller=caller)
    if z["verdict"] == "FAIL":
        direct_openai = _load("direct_openai")
        delta = safezone.move_delta(z)
        prompt = mi.edit_prompt({"delta": delta, "viewpoint": it.get("viewpoint")},
                                "still-edit-fidelity")
        versions = run / "media" / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        before = versions / f"{iid}-offzone{Path(file_).suffix}"
        shutil.copy2(file_, before)
        edited_from = str((manifest.get(str(it.get("edit_of") or "")) or {}).get("file") or "")
        others = [r for r in refs if str(r) != edited_from and str(r) != str(file_)]
        fix_refs = [Path(file_)] + others[:1]
        res = direct_openai.generate(prompt, fix_refs, Path(file_), transport=openai_transport,
                                     key=openai_key)
        _load("colour_match").match_file(file_, before)
        preflight.ledger(run, res["model"], f"{iid}-zone-fix", 0.0, "done", brand=brand, shot=iid,
                         note=f"subject zone fix: {delta}")
        first = z
        z = safezone.check(file_, caller=caller)
        z["remade"] = {"delta": delta, "prompt": prompt, "before": str(before),
                       "first_outside": first.get("outside")}
        if z["verdict"] == "PASS":
            print(f"  {iid}: subject zone — {', '.join(first.get('outside') or [])} moved into the 4:5 zone by one edit")
    if z["verdict"] == "FAIL":
        print(f"  {iid}: HELD — {', '.join(z.get('outside') or [])} still outside the 4:5 zone after one fix")
    elif z["verdict"] == "UNCHECKED":
        print(f"  {iid}: subject zone UNCHECKED — {z.get('why')} (not shippable until checked)")
    preflight.verdict(run, iid, "subject_zone",
                      {k: v for k, v in z.items() if k not in ("raw",)})
    return z, file_


def record_subject_boxes(run: Path, items: list[dict], manifest: dict) -> None:
    """Every frame's `subject_box` into plan.json, for the edit to keep words
    off the face: `subject_boxes` by item id, and on the scene's own frame."""
    boxes = {iid: row.get("subject_box") for iid, row in manifest.items() if "zone" in row}
    p = run / "plan.json"
    if not boxes or not p.is_file():
        return
    plan = read_json(p, {}) or {}
    plan["subject_boxes"] = {**(plan.get("subject_boxes") or {}), **boxes}
    by_id = {str(it.get("id")): it for it in items}
    for sc in plan.get("scenes") or []:
        for f in sc.get("frames") or []:
            for iid, box in boxes.items():
                it = by_id.get(iid) or {}
                if it.get("for") == sc.get("id") and it.get("frame_role") == f.get("role"):
                    f["subject_box"] = box
    write_json(p, plan)


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
                   "Made first, on the direct ElevenLabs account (the owner's 2026-09-17 "
                   "ruling) — upload each line below to the provider, then use the "
                   "returned media id as the `audio` media on the item(s) that carry it:",
                   ""]
        for f in voice_files:
            lines.append(f"- `{f.relative_to(run)}`")
        lines.append("")
    if direct_manifest:
        lines += ["## Machine-made media", "",
                   "Cast, stills, edits and the song run on the machine hand — direct APIs, "
                   "made before this sheet was written (the owner's 2026-09-17 ruling). Upload "
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
        first_role = it.get("first_frame_role") or "start_image"
        if made:
            lines.append(f"- **{first_role} (upload first)**: `{made.get('file')}` "
                         f"— made by {made.get('model', '?')} ({still_id})")
        elif still_id:
            lines.append(f"- **{first_role} (upload first)**: the frame made as `{still_id}`")
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
            if k == "resolution" and it.get("resolution_fixed"):
                lines.append(f"- **{k}**: {v} — the only resolution this door makes; "
                             f"the piece's own Resolution sized the stills")
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
              openai_transport=None, google_transport=None, byteplus_transport=None,
              song_transport=None, song_stt_transport=None, zone_caller=None) -> int:
    runs_root = Path(a.runs_root).resolve() if a.runs_root else DEFAULT_RUNS_ROOT
    run = runs_root / "video-production" / a.brand / a.label
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
        # THE SWIPE MATCH (the owner, 2026-09-24: "literally this cannot happen
        # again UNLESS I DISCRETELY SAY SO. THE WHOLE POINT IS TO TAKE A SWIPE
        # AND ADAPT, not ruin it"). A brief from a swipe is made only when the
        # teardown's swipe match stamped it PASSED — its places, people,
        # camera and order checked against the swipe, shot by shot. HELD,
        # never checked, or edited since the check: refused, --dry-run
        # included. Only a brief composed WITHOUT a swipe skips it, and says
        # so (--composed).
        if not getattr(a, "composed", False):
            _sm_spec = importlib.util.spec_from_file_location(
                "swipe_match", HERE.parents[1] / "video-teardown" / "machine" / "swipe_match.py")
            _sm = importlib.util.module_from_spec(_sm_spec); _sm_spec.loader.exec_module(_sm)
            _stamp = _sm.stamp_of(src.read_text())
            if _stamp != "PASSED":
                why = {"HELD": "the swipe match HELD it — it changes the swipe (see SWIPE-MATCH.md in the teardown run)",
                       "STALE": "it was edited after its swipe match — check it again",
                       None: "it was never checked against its swipe"}[_stamp]
                print(f"REFUSED swipe match: {why}. Check: python3 tools/video-teardown/machine/swipe_match.py "
                      f"<teardown run> [--approve-structure M1,…] — or --composed for a brief made without a swipe.",
                      file=sys.stderr)
                print("the brief is not ready for production — nothing was made", file=sys.stderr)
                return 2
            # THE MANIFEST (the owner, 2026-09-24: "a manifest at the end of every
            # brief … before we can go into ai production — i do not have time
            # to babysit this anymore"). Re-checked here, right before anything
            # is spent — the judge is not re-asked for the same brief, only the
            # elements and prices are looked at again — and refused unless
            # COMPLETE for this exact brief.
            _mf_spec = importlib.util.spec_from_file_location(
                "manifest", HERE.parents[1] / "video-teardown" / "machine" / "manifest.py")
            _mf = importlib.util.module_from_spec(_mf_spec); _mf_spec.loader.exec_module(_mf)
            _tdrun = src.resolve().parent.parent
            if src.resolve().parent.name == "stages" and (_tdrun / "stages" / "2-spec.md").exists():
                try:
                    _mf.check(_tdrun, a.brand, src.name)
                except Exception as e:
                    print(f"WARNING the manifest could not be re-checked: {e}", file=sys.stderr)
            _mstat = _mf.status_of(src.read_text())
            if _mstat != "COMPLETE":
                import re as _re
                _line = (_re.search(r"^MANIFEST: [^\n]*", src.read_text(), _re.M) or [None])[0] if _mstat else None
                print("REFUSED the brief's manifest is not complete — "
                      + ({None: "the brief has no manifest (manifest.py <teardown run>)",
                          "STALE": "the brief changed after its manifest — re-check it"}.get(_mstat) or _line),
                      file=sys.stderr)
                print("the brief is not ready for production — nothing was made", file=sys.stderr)
                return 2
            # DAMON READS THE BRIEF (2026-09-24: "i always need to see a written
            # brief before moving on to the production stage … so I can
            # actually read the script before it goes out"). His read is
            # stamped only on his word, tied to this exact brief.
            _read = _sm.read_of(src.read_text())
            if _read != "APPROVED":
                print("REFUSED the owner has not read this brief" + (" since it was edited" if _read == "STALE" else "")
                      + " — show him the written brief; on his word: swipe_match.py <teardown run> --damon-read",
                      file=sys.stderr)
                print("the brief is not ready for production — nothing was made", file=sys.stderr)
                return 2
            # WORTH MAKING? (the owner, 2026-10-02: "if it's not ready for us to
            # make, then we're not going to even do it"). The last word before
            # any credit is spent: did 5 viewers from the avatar, scrolling it
            # inside their real feed, stop, stay and want to tap? A brief with a
            # stamp is answered free; one never checked is checked now — text
            # only, cents — and refused if they passed it by. the owner passes one
            # by hand with --approve-structure V at the teardown.
            if src.resolve().parent.name == "stages" and (_tdrun / "run.json").exists() \
                    and os.environ.get("QC_VIEWER", "1") != "0":
                _q = str(HERE.parents[1].parent / "components" / "quality-checks")
                if _q not in sys.path:
                    sys.path.insert(0, _q)
                from marketing_chain_checks import viewer as _vw
                _tst = json.loads((_tdrun / "run.json").read_text())
                _aud = _tst.get("declared_audience") or {}
                _au2 = _tst.get("audience") or {}
                try:
                    _okv, _why, _ = _vw.worth_making(_tdrun, a.brand, _aud.get("avatar") or _au2.get("_avatar"),
                                                     src, kind="video", sub=_aud.get("sub") or _au2.get("_sub_avatar"))
                except Exception as e:
                    _okv, _why = False, f"the viewer check could not run ({type(e).__name__}: {str(e)[:120]})"
                if not _okv:
                    print(f"REFUSED not worth making yet: {_why}", file=sys.stderr)
                    print("the brief is not ready for production — nothing was made", file=sys.stderr)
                    return 2
                print(f"worth making: {_why}")
        # THE PRODUCTION GATE (the owner, 2026-09-23: "clean up each stage
        # properly so the next stage is able to just do what it's supposed to
        # do"). Before a voice or a frame is paid for, --dry-run included:
        # every scene says whether it is the speaker, every card is a plate
        # and its words, and every row of the swipe's make-list is carried to
        # a scene of the right kind or dropped with a reason. A brief written
        # before the roll sheet existed is warned, never refused.
        if plan.get("shape") == "scene":
            g_fails, g_warns = mi.production_gate(src.read_text(), plan.get("scenes") or [],
                                                  brand=a.brand)
            # The brief contract preflight enforces at spend time is asked here
            # too, --dry-run included (2026-10-01: the gates "passed", then
            # preflight refused 15 hand shots with no viewpoint — a pass that
            # was not one).
            g_fails = g_fails + [f for f in mi.brief_violations(src.read_text()) if f not in g_fails]
            for w in g_warns:
                print(f"WARNING {w}")
            if g_fails:
                for f in g_fails:
                    print(f"REFUSED {f}", file=sys.stderr)
                print("the brief is not ready for production — nothing was made",
                      file=sys.stderr)
                return 2

    # THE BANKS (ELEMENTS.md §3, 2026-09-23). Music and every sound effect
    # the brief names are picked from a bank made once, and `{bank_id, file}`
    # is written into plan.json for the edit. A row the bank has not made is
    # a refusal naming it — never a silent fallback, --dry-run included.
    if plan.get("music") or plan.get("sfx"):
        b_fails = _load("banks").resolve(plan, getattr(a, "banks", None))
        if b_fails:
            for f in b_fails:
                print(f"REFUSED {f}", file=sys.stderr)
            print("the banks cannot supply this brief's sound — nothing was made",
                  file=sys.stderr)
            return 2
        write_json(run / "plan.json", plan)
        m = plan.get("music") or {}
        if m.get("bank_id"):
            print(f"music: {m['bank_id']} — {m['file']}")
        for c in plan.get("sfx") or []:
            print(f"sfx {c.get('cue')}: {c.get('bank_id')} — {c.get('file')}")

    # OUR OWN FOOTAGE FIRST (the owner, 2026-10-05: "we need to make sure that the
    # footage step properly runs … whatever needs to be generated, we can just
    # generate"). Before any still or clip is made, --dry-run included, every
    # B-roll scene is looked up in the brand's indexed footage on Shared
    # Assets (machine/footage.py → tools/asset-index). A confident match
    # is CUT from that clip (owned_file + owned_in/owned_out on the scene) and
    # nothing is generated for it; the rest are generated, each carrying its
    # nearest real clip's frame as a picture reference. The presenter is
    # never the library's. --no-footage skips it.
    footage_cut: set = set()
    if getattr(a, "footage", True):
        try:
            fm = _load("footage")
            f_res = fm.gate(plan, a.brand)
        except Exception as e:
            f_res = None
            print(f"WARNING the footage step could not run ({type(e).__name__}: {e}) — every B-roll scene is generated")
        if f_res is not None:
            footage_cut = set(f_res["cut"])
            saved = None
            if footage_cut:
                try:
                    # priced as if generated: the items these scenes would have made
                    def _as_generated(rows):
                        return [{k: v for k, v in r.items() if k != "source_plan"}
                                for r in rows or [] if r.get("id") in footage_cut]
                    would = batches_of({**plan, "scenes": _as_generated(plan.get("scenes")),
                                        "cutaways": _as_generated(plan.get("cutaways"))},
                                       plan.get("brand") or a.brand)
                    _pn, _prov, _ = platform.resolve_provider(a.provider)
                    est = platform.plan(would, _prov, platform.registry(), forced=bool(a.provider))
                    saved = {"items": len(would), "credits": est.get("total_credits"), "usd": est.get("total_usd")}
                except Exception:
                    saved = {"items": 0}
            fm.report(f_res, saved)
            for s in (plan.get("scenes") or []) + (plan.get("cutaways") or []):
                if s.get("id") in footage_cut:
                    print(f"  cut {s['id']} from our footage · {s.get('owned_in')}–{s.get('owned_out')}s of "
                          f"{s.get('owned_file')}")
            if f_res.get("indexed"):
                write_json(run / "plan.json", plan)

    # THE RUN'S PICK (the owner, 2026-09-22) lands on the plan, so the batches,
    # the board and a re-read of this run all say the same model. A scene's
    # own `model` still wins over it.
    pick = getattr(a, "clip_model", None)
    if pick:
        bad = mi.model_fault(pick, "motion")
        if bad:
            print(bad, file=sys.stderr)
            return 3
        plan["clip_model"] = pick
        write_json(run / "plan.json", plan)

    run_json_path = run / "run.json"
    existing = read_json(run_json_path, {}) or {}
    # WHICH MODEL MADE THIS RUN, on the record. the owner, 2026-09-22: "we need
    # to run through a few more briefs before I can confidently switch models
    # for different video gen usages" — the split is a decision waiting on
    # evidence, so every run writes down what made it and who chose, and the
    # evidence accumulates without anyone keeping a list.
    fresh = {"machine": "video-production", "brand": a.brand, "label": a.label,
             "format": a.format, "source_brief": src.name,
             # the brief's own path, so the brief index can join this run back
             # to the brief it made (2026-09-30: "index briefs at a high level")
             "brief_from": str(src.resolve()),
             "provider": a.provider, "opened": now(),
             "clip_model": plan.get("clip_model") or mi.model_of("motion"),
             "clip_model_by": "the run" if plan.get("clip_model") else "the registry",
             "scene_models": {s["id"]: (s.get("model") or plan.get("clip_model")
                                        or mi.model_of("talking" if s.get("to_camera") else "motion"))
                              for s in (plan.get("scenes") or [])
                              if s.get("id") and s.get("kind") not in STILL_ONLY}}
    # THE BRIEF NUMBER TRAVELS WITH THE PIECE (the owner, 2026-10-09): the brief got its brief-NNNN when it was
    # written; production copies it from the brief's own run.json so delivery (video-edit/deliver.py reads
    # this run.json `brief`) names the files and the Meta ad with the same number. Never coined here.
    for rj in (src.resolve().parent.parent / "run.json", src.resolve().parent / "run.json"):
        b = (read_json(rj, {}) or {}).get("brief") if rj.is_file() else None
        if b:
            fresh["brief"] = b
            break
    write_json(run_json_path, {**fresh, **existing})   # never overwrite what's already there

    # A scene's line is a PARAGRAPH in the scene shape — the whole run of
    # speech, byte-identical to the script, one entry per scene. That is what
    # the one voice track is chunked on.
    held = [s["id"] for s in plan.get("scenes", []) if str(s.get("held") or "").strip()]
    lines = {s["id"]: (s.get("line") or s.get("voice") or "")
             for s in plan.get("scenes", []) if s["id"] not in held
             # a silent card, screen, split or endcard has no slice to claim
             and not (s.get("kind") in SILENT_OK and not s.get("voice"))}
    write_json(run / "lines.json", lines)
    # A placeholder left in a spoken line would be read out loud (found 2026-09-23:
    # Nova's brief S5 carried "[SLOT: how much per use …]"). Refused before the voice.
    left = {sid: t for sid, t in lines.items() if re.search(r"\[(SLOT|UNFILLED)[^\]]*\]", str(t or ""), flags=re.I)}
    if left:
        for sid, t in left.items():
            ph = re.search(r'\[(SLOT|UNFILLED)[^\]]*\]', t, flags=re.I).group(0)[:90]
            print(f"STOP {sid}: its spoken line still has a placeholder — {ph}", file=sys.stderr)
        print("Fill it from the brand files at the brief (stage 5), or cut the sentence. Nothing was voiced.", file=sys.stderr)
        return 2
    for s in plan.get("scenes", []):
        if s["id"] in held:
            print(f"HELD {s['id']} — nothing is made for it: {s['held']}")

    # THE SECTION-FIT GATE (the owner, 2026-09-23: "are they actually aligned with
    # the script?"). Every scene's words must do the job of the doctrine section
    # it is labelled with, because a wrong label breaks every section swap made
    # from it. One check, before the voice or any frame is paid for; a misfit
    # stops the run, named, and the brief is fixed at its source (stage 5).
    labelled = any(sc.get("section") for sc in plan.get("scenes") or [])
    if not labelled and getattr(a, "section_fit", False):
        print("section fit: no scene carries a section (an older brief) — nothing to check")
    if labelled and not a.dry_run and getattr(a, "section_fit", False):
        sectionfit = _load("sectionfit")
        try:
            fit = sectionfit.check(plan, out_dir=run / "section-fit")
        except Exception as e:
            print(f"section fit could not be checked ({type(e).__name__}: {e}) — STOP", file=sys.stderr)
            return 2
        sectionfit.report(fit)
        if not fit["pass"]:
            print("STOP — a scene's words don't do the job of its section. Fix the brief's section labels "
                  "(or its order) at stage 5, then start again. Nothing was made.", file=sys.stderr)
            return 2
    elif labelled and a.dry_run and getattr(a, "section_fit", False):
        print("section fit: would check every scene's words against its section (one model call) — skipped on a dry run")

    # THE ELEMENTS LOCK (the owner, 2026-09-23: "the system should prompt to
    # confirm the elements before going into actual production … if elements
    # need to be generated we need to go through that step"). Every person
    # (their look per scene, their own voice), every setting, the product and
    # every prop must be BANKED — documented, from a real reference — and
    # the owner must have confirmed this exact set. Before any voice or picture is
    # paid for. `<run>/elements.json` is the make-list and the page's source.
    if getattr(a, "elements_lock", False) and src.suffix.lower() == ".md":
        ec = _load("elements_check")
        e_fails, e_notes = ec.gate(run, src.read_text(), a.brand, a.dry_run)
        for n in e_notes:
            print(f"WARNING {n}")
        if e_fails:
            for f in e_fails:
                print(f"REFUSED {f}", file=sys.stderr)
            print(f"the elements are not ready — make what is listed, show the elements "
                  f"page, confirm; nothing was made ({run / 'elements.json'})", file=sys.stderr)
            return 2

    # EVERY WORD IN A SPOKEN LINE IS A WORD (the owner, 2026-10-01: "br- br-" was
    # read aloud as "bar, bar"). Before a voice is paid for, every scene's line
    # is checked for a fragment (a cut-off word, a repeated non-word).
    try:
        _scp = WS / "tools" / "video-teardown" / "machine" / "spoken_check.py"
        import importlib.util as _ilu2
        _sp2 = _ilu2.spec_from_file_location("spoken_check", _scp)
        _sck = _ilu2.module_from_spec(_sp2); _sp2.loader.exec_module(_sck)
        _bdoc = json.loads(re.findall(r"```json\s*\n(.*?)\n```", src.read_text(), re.S)[-1]) \
            if src.suffix.lower() == ".md" and "```json" in src.read_text() else {}
        _frag = _sck.check_lines([(x.get("id"), x.get("voice") or "") for x in _bdoc.get("scenes") or []])
    except Exception as _e:
        _frag = []
        print(f"WARNING the spoken-word check could not run ({_e})")
    if _frag:
        for f in _frag:
            print(f"REFUSED {f['id']}: {'; '.join(f['found'])} — not a word a voice can say: {f['text'][:90]}",
                  file=sys.stderr)
        print("fix the line in the brief (the stumble in real words, or dropped); nothing was made", file=sys.stderr)
        return 2

    # The read of every line, made here (the owner's 2026-09-17 ruling). Since
    # 2026-10-03 (providers.json ruling_2026_10_03_voice_first_retired) it is
    # NOT what a clip says: on the Omni route (--clips, the default) Omni says
    # the on-camera lines inside the clip and ElevenLabs speech-to-speech turns
    # them into the person's cloned voice; off-camera lines are text-to-speech
    # in the cloned voice (omni_clips.py). This read stays the storyboard's
    # timing ruler and the line check's reference, and feeds only the legacy
    # clip doors (--legacy-clips). A plan with no line to speak calls this for nothing —
    # voice.run_for is itself a no-op when lines.json has nothing in it. A
    # character with no bindable voice is a hard stop, --dry-run included:
    # nothing here should plan around a voice that cannot actually speak.
    # TAKES ALREADY MADE ARE KEPT (2026-10-02): a run that already holds a
    # recording for every line in lines.json reuses them — the owner's approved
    # voices are never re-recorded by starting the next step. To record again,
    # move vo/ aside first.
    _lines = read_json(run / "lines.json", {}) or {}
    _man = read_json(run / "vo" / "manifest.json", {}) or {}
    _need = [sid for sid, t in _lines.items() if t]
    kept_voices = bool(_need) and (run / "vo" / "timing.json").exists() and all(
        (run / "vo" / f"{sid}.mp3").exists() and sid in _man for sid in _need)
    if kept_voices:
        voice_manifest = {sid: _man[sid] for sid in _need}
        print(f"voices: kept — {len(_need)} recorded take(s) already in vo/, none re-recorded")
    else:
      try:
        voice_manifest = voice_mod.run_for(
            run, character=None, dry_run=a.dry_run, cast_root=a.cast_root,
            transport=voice_transport)
      except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    # THE AUDIO GATE (the owner, 2026-09-23: the script and the audio drive the
    # video; the clips only show what is said). The read is heard now, scene
    # by scene, before any frame or clip is paid for: it says its line, the
    # line finishes, the sound is not broken. A failing slice is remade once,
    # voice only; still failing, the run stops here, named.
    if not a.dry_run and (run / "vo" / "timing.json").exists():
        audiocheck = _load("audiocheck")
        # a kept take is never remade by the check — a failure stops the run, named
        heard = audiocheck.check_run(run, fix=not kept_voices, voice_transport=voice_transport)
        audiocheck.report(heard)
        if not heard["pass"]:
            print("STOP — the voice is wrong, so nothing is made from it. Fix the line or the read, then start again.",
                  file=sys.stderr)
            return 2

    # THE SONG (the owner, 2026-09-23: "a specific protocol / chain … so we
    # remove all hallucination and variables and can just print";
    # SONG-CHAIN.md). A sung brief's song block is printed by song.py when
    # the song door (providers.json doors.audio) is song.py's: the words only from the script, the
    # sound only from a style row, then the song gate. Like the voice, it is
    # made and heard BEFORE any picture is paid for. --dry-run writes the
    # request and spends nothing. A legacy prompt-shaped song (no sections)
    # still goes to the Lyria alternate on the machine hand, below.
    song_block = plan.get("song") if isinstance(plan.get("song"), dict) else {}
    if song_block.get("sections"):
        song_mod = _load("song")
        shut = song_mod.door_closed()
        if shut:
            print(f"REFUSED {shut}", file=sys.stderr)
            return 2
        try:
            sung = song_mod.make(run, plan=plan, dry_run=a.dry_run, transport=song_transport,
                                 stt_transport=song_stt_transport)
        except SystemExit as e:
            print(f"REFUSED {e}", file=sys.stderr)
            return 2
        song_mod.report(sung)
        if not sung["pass"]:
            print("STOP — the song does not sing its lines, so nothing is made from it.", file=sys.stderr)
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
    # THE BANKED ELEMENTS ARE THE REFERENCES (2026-09-23): every first frame
    # carries the masters, looks, set plate, packshot and props its scene uses
    if (run / "brief.md").is_file() and getattr(a, "elements_lock", False):
        for n in _load("element_refs").bind(items, (run / "brief.md").read_text(), plan_brand, run):
            print(f"refs {n}")

    # THE STORYBOARD DECIDES THE PICTURES (the owner, 2026-10-01: "establish the
    # sections and just design the start frame and end frame … cut down the
    # number of images generated while getting better outcome"). With
    # --storyboard, only the pictures storyboard.json lists are made — a start
    # (and end) frame per section, a plate per card, the endcard — and no clip:
    # clips are the next step, section by section, after the owner approves these.
    if getattr(a, "storyboard", False):
        sbp = run / "storyboard.json"
        if not sbp.is_file():
            print("REFUSED --storyboard: no storyboard.json in the run — storyboard_plan.py makes it", file=sys.stderr)
            return 2
        sb_mod = _load("storyboard_plan")
        sb_doc = json.loads(sbp.read_text())
        if footage_cut:
            # a scene cut from our footage gets no picture (2026-10-05)
            for g in sb_doc.get("sections") or []:
                dropped = [f for f in g.get("frames") or [] if f.get("from") in footage_cut]
                for f in dropped:
                    print(f"storyboard: {f.get('from')} {f.get('what')} not made — cut from our footage")
                g["frames"] = [f for f in g.get("frames") or [] if f.get("from") not in footage_cut]
        items, sb_problems = sb_mod.picture_jobs(sb_doc, items)
        for pr in sb_problems:
            print(f"REFUSED {pr}", file=sys.stderr)
        if sb_problems:
            return 2
        print(f"storyboard: {len(items)} picture(s), no clips")
        # QC'S PICTURE FIXES (2026-10-02): a picture QC sends back is made again
        # with the reviewer's words added — <run>/picture-fixes.json, {id: words}
        fixes = read_json(run / "picture-fixes.json", {}) or {}
        for it in items:
            add = fixes.get(str(it.get("id")))
            if add and isinstance(it.get("params"), dict) and add not in it["params"].get("prompt", ""):
                it["params"]["prompt"] = (it["params"].get("prompt", "").rstrip() + " " + add).strip()
        if getattr(a, "only", None):
            want = {x.strip() for x in a.only.split(",") if x.strip()}
            items = [it for it in items if str(it.get("id")) in want]
            print(f"only: {len(items)} picture(s) — {', '.join(sorted(want))}")

    # THE STORYBOARD DECIDES THE CLIPS (2026-10-02) — the step after its
    # pictures are approved: only the clips storyboard.json calls for, each
    # from an approved picture, on the ruled clip door (clips_plan.py).
    # THE OMNI ROUTE (the owner 2-3 Oct 2026, providers.json direct.omni_route): Omni on fal
    # animates each approved picture; it is the --clips default while the registry says
    # default_for_clips (omni_clips.py). --legacy-clips keeps the old door's planner (not the
    # ruled clip model — kept for the record); both refuse a person's clip that would start
    # from a clip's last frame (no hand-offs for people, 2026-10-03).
    if getattr(a, "clips", False):
        reg_ = platform.registry()
        omni_default = bool(((reg_.get("direct") or {}).get("omni_route") or {}).get("default_for_clips"))
        if getattr(a, "omni", False) or (omni_default and not getattr(a, "legacy_clips", False)):
            return _load("omni_clips").start(a, run, plan, reg_)
        return _load("clips_plan").start(a, run, plan, reg_, timing=timing, ruled=ruled_model)

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
    # ONLY THIS START'S ITEMS (2026-10-02): batches/ keeps files from earlier
    # starts (the three-doctors run made two 1-Oct frames on top of its 22 pictures).
    # Whatever this start planned is the whole job; anything else is left alone.
    wanted = {str(it.get("id")) for it in items}
    all_items = [it for it in all_items if str(it.get("id")) in wanted]
    seen_ids: set = set()
    all_items = [it for it in all_items if not (str(it.get("id")) in seen_ids or seen_ids.add(str(it.get("id"))))]

    # The two hands (the owner's 2026-09-17 ruling): cast, still, edit and the
    # song run on the machine hand — direct APIs, before the editor ever
    # sees them. Motion and talking stay the editor's. Which hand a station
    # is comes from providers.json's own doors[...].hand, never a kind name
    # written here.
    machine_items, editor_items = split_by_hand(all_items, reg, forced_provider=bool(a.provider))
    try:
        direct_manifest = run_machine_hand(
            machine_items, run, a.dry_run, brand=a.brand,
            openai_transport=openai_transport, google_transport=google_transport,
            byteplus_transport=byteplus_transport,
            clip_colour=getattr(a, "clip_colour", True), zone_caller=zone_caller)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    still_for = still_for_map(machine_items)
    # THE PICTURE REVIEW, every batch (2026-10-02 — it was a session agent run
    # by hand): each picture against the swipe shot it copies and its people's
    # references, filed in qc-log/ (components/quality-checks review.after_stage)
    if getattr(a, "storyboard", False) and not a.dry_run and direct_manifest:
        review_pictures(run, machine_items, direct_manifest)

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
        # the take being replaced was colour-matched: its pre-colour original
        # goes with it, so the NEW take is matched too
        pre = arch_dir / f"{iid}-precolour{dest.suffix}"
        if pre.exists():
            pre.rename(arch_dir / f"{iid}-v{n}-precolour{dest.suffix}")
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

        # CLIP COLOUR (ELEMENTS.md §5, 2026-09-23): every clip that lands is
        # matched to the piece's first frame, on a copy, the original
        # archived — a post step, on by default, off with --no-clip-colour.
        if dest is not None and item.get("kind") in ("motion", "talking") \
                and getattr(a, "clip_colour", True):
            made = read_json(run / "direct.json", {}) or {}
            cm = colour_match_clip(run, iid, dest,
                                   piece_first_frame(list(by_id.values()), made))
            if cm:
                results[iid] = {**results.get(iid, {}), "colour": cm}

        # Line parity (the owner, 2026-09-18): a downloaded clip that carries a
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
                        if pres["verdict"] == "CUT_OFF":
                            # the owner, 2026-09-23: a clip that stops mid-line is an
                            # error — made again, never shipped flagged. The order
                            # goes on the run; the remake-clip skill carries it out.
                            remake = _load("remake")
                            remake.main(["order", str(run), "--scene", iid, "--why", "cut-off",
                                         "--heard", pres["heard"]])

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
    # CLIPS FROM THE STORYBOARD (2026-10-02): the last frames the next clips
    # start from, then the clip review — as review_pictures does for pictures
    if (run / "clips" / "plan.json").is_file():
        _load("clips_plan").after_record(run, results)
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

def cmd_models(a) -> int:
    """THE MENU — every clip model a run can be pointed at, what it is good
    at, what it is weak at, and what it costs. Read off providers.json, so
    the day a model is measured the menu says so without a code change."""
    rates = platform.registry().get("credits_per_dollar") or {}
    per_dollar = float(rates.get("higgsfield") or 0) or None
    for station_name in (a.station or ["motion", "talking"]):
        print(f"\n{station_name.upper()}")
        for r in mi.clip_models(station_name):
            cps = r.get("credits_per_second")
            price = ""
            if cps:
                price = f"{cps} cr/s"
                if per_dollar:
                    price += f"  ~${cps * 6 / per_dollar:.2f} / 6 s"
            cap = f"up to {r['max_seconds']}s" if r.get("max_seconds") else ""
            mark = "  ← the settled door" if r["settled"] else ""
            print(f"  {r['model']}   {price}   {cap}{mark}")
            for g in r["good_at"]:
                print(f"      good at   {g}")
            for w in r["weak_at"]:
                print(f"      weak at   {w}")
    print("\npick one for a whole run with --clip-model <id>, or put a "
          "`model` key on one scene.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)

    s = sub.add_parser("start")
    s.add_argument("source", help="a brief (.md) or a plan (.json)")
    s.add_argument("--brand", required=True)
    s.add_argument("--format", required=True)
    s.add_argument("--label", required=True)
    s.add_argument("--provider")
    s.add_argument("--clip-model", dest="clip_model",
                   help="which clip model this run's scenes go to — "
                        "`run.py models` lists them. A scene's own `model` "
                        "wins over it; absent, the registry's settled door.")
    s.add_argument("--yes", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--only", help="with --storyboard: make only these picture ids (comma-separated), e.g. the ones QC sent back")
    s.add_argument("--storyboard", action="store_true",
                   help="make only the pictures the run's storyboard.json lists (no clips)")
    s.add_argument("--clips", action="store_true",
                   help="plan only the clips the run's storyboard.json calls for, from its approved pictures "
                        "(--only G05,G12 picks sections) — on the Omni route by default (omni_clips.py)")
    s.add_argument("--omni", action="store_true",
                   help="with --clips: the Omni route (fal, animates each approved picture) — the default today")
    s.add_argument("--legacy-clips", dest="legacy_clips", action="store_true",
                   help="with --clips: the old clip door's planner (clips_plan.py) instead of the Omni route — "
                        "NOT the ruled clip model (Omni on fal, 2026-10-03); only on the owner's ruling")
    s.add_argument("--no-section-fit", dest="section_fit", action="store_false", default=True, help="skip the check that every scene's words do its section's job (not for real briefs)")
    s.add_argument("--composed", action="store_true",
                   help="the brief was composed without a swipe, so there is no swipe to match it to")
    s.add_argument("--no-elements-lock", dest="elements_lock", action="store_false", default=True,
                   help="skip the elements lock (tests and fixtures only — never a real brief)")
    s.add_argument("--no-footage", dest="footage", action="store_false", default=True,
                   help="skip the footage step (our own clips first) — every B-roll scene is generated")
    s.add_argument("--bank")
    s.add_argument("--runs-root")
    s.add_argument("--cast-root", help="test/override root for a character's "
                    "cast folder; defaults to runs/ai-elements/<brand>/casting/ (element_paths.py)")
    s.add_argument("--banks", help="a banks folder other than "
                   "tools/video-production/banks (music + sfx index.json)")
    s.add_argument("--no-clip-colour", dest="clip_colour", action="store_false",
                   help="do not colour-match each clip the machine hand makes to "
                        "the piece's first frame (on by default)")

    r = sub.add_parser("record")
    r.add_argument("run")
    r.add_argument("--results", help="the editor's results.json (Higgsfield / fal)")
    r.add_argument("--direct", action="store_true",
                   help="record the machine hand's own clips from direct.json instead")
    r.add_argument("--no-parity", action="store_true",
                    help="skip the automatic line-parity check on downloaded clips")
    r.add_argument("--no-clip-colour", dest="clip_colour", action="store_false",
                   help="do not colour-match each recorded clip to the piece's "
                        "first frame (on by default; the original is archived)")

    m = sub.add_parser("models", help="the clip models a run can pick from")
    m.add_argument("--station", action="append",
                   help="motion (B-roll) or talking; both by default")

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
        if a.verb == "models":
            return cmd_models(a)
    except (SystemExit, ValueError, OSError) as e:
        if isinstance(e, SystemExit) and isinstance(e.code, int):
            return e.code
        print(e, file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    sys.exit(main())
