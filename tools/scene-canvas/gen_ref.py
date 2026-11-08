"""AI shots from our real footage, made one way every time: the house process (the owner, 8 Nov 2026: "this should not be
just some random recipe. This is something that we consistently go through").

  python3 gen_ref.py recipes.json [--dry-run]   runs each recipe once (skips any shot already made), records every step

THE PROCESS (models from the team's Generative Model House, components/generative-model-house/MODEL-HOUSE.md):
  1. Reference   a real frame of our footage in sources/generated/refs/ (`ref`), plus any extra references (`refs`):
                 the creator's face master, a real setting photo. Never an AI picture as the only reference.
  2. Still       only when the frame needs changing (`still`: what to change). GPT Image 2.5 edit, every reference sent,
                 the camera-match clause added (machine/direct_openai.py in the team workspace).
  3. Clip        Seedance 2.5 through the Higgsfield API, 480p, silent, from the still or the frame (machine/seedance.py
                 motion). A person in the picture must pass the face gate against `master` (their real frame) first;
                 a picture with none of our people says `"no_people": true`.
  4. Phone pass  scene_canvas.phone_copy re-shoots the clip at 432 px with grain and drift when a scene uses it, which is
                 also why the house's local upscale step is skipped here.
A recipe: {"name", "ref", "refs": [...], "master": "...", "still": "...", "action": "...", "seconds": 5, "no_people": false}.
Each run writes `made` on the recipe: every step's model, the prompt exactly as sent, the references, the request id,
seconds and time. The Video Studio shows it under "How this AI shot was made".
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as ST  # noqa: E402
G = str(ST.SOURCES / "generated")
TEAM = ST.REPO                                                           # the workspace this component sits in
MACHINE = ST.part("video-production") / "machine"
PROCESS = "house: reference → GPT Image 2.5 still → Seedance 2.5 clip (Higgsfield, 480p) → phone pass"
EDIT = "gpt-image-2.5 (OpenAI, edit)"
I2V = "seedance-2.5 (Higgsfield, image-to-video, 480p)"
# A person's pick for the clip (recipe "clip_model"), from the house's clip choices (the Video Studio's Production view
# offers them). Never chosen by this tool on its own: no pick = the house default.
DEFAULT = "seedance-2.5"
DEFAULT_JOB = "seedance_2_5"
PICKS = {
    "wan-3.0": {"door": "wan", "kw": {}, "job": "wan3_0", "res": "480p", "how": "Higgsfield plan credits",
                "label": "wan-3.0 (Higgsfield plan credits, image-to-video, 480p) - a person's pick"},
    "seedance-2.0": {"door": "seedance", "kw": {"model": "seedance-2.0"}, "job": "seedance_2_0", "res": "480p", "how": "Higgsfield API",
                     "label": "seedance-2.0 (Higgsfield API, image-to-video, 480p) - a person's pick"},
    "kling-4.0": {"door": "kling", "kw": {}, "job": "kling4_0", "res": "720p", "how": "Higgsfield API",
                  "label": "kling-4.0 (Higgsfield API, image-to-video, 720p) - a person's pick"},
}
_CREDITS = {}
LOOK = (" Amateur phone video with exactly the same camera quality as the first frame: same softness, grain, compression and colour,"
        " natural handheld wobble, nothing cinematic, same people, nothing added, no text.")
# the owner 7 Nov: the reference sets the look. A still copies the reference frame's camera, not just the face.
MATCH = (" Match the reference photo's camera exactly: the same phone front-camera quality, softness, sensor noise, compression,"
         " flat white balance and imperfect exposure. It must look like a frame grabbed from the same phone video, not a"
         " professional or AI photo: no cinematic light, no bokeh, no retouching.")


def _team(name):
    sys.path.insert(0, str(MACHINE))
    spec = importlib.util.spec_from_file_location("team_" + name, MACHINE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _door(name):
    """A clip door from the team copy; a door the team copy does not carry yet runs from doors/ here on the team's helpers."""
    if (MACHINE / (name + ".py")).exists():
        return _team(name)
    local = Path(HERE) / "doors" / (name + ".py")
    if not local.exists():
        raise SystemExit(f"no {name} door in the team copy or in doors/")
    sys.path.insert(0, str(MACHINE))
    spec = importlib.util.spec_from_file_location("door_" + name, local)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.HERE = MACHINE
    return mod


def _credits(job, res):
    """Plan credits for a 5 s silent take, read from the Higgsfield CLI's own estimate (cached)."""
    if (job, res) not in _CREDITS:
        import shutil
        import subprocess
        exe, val = shutil.which("higgsfield"), None
        if exe:
            base = [exe, "generate", "cost", job, "--prompt", "estimate", "--resolution", res, "--duration", "5", "--aspect_ratio", "9:16"]
            for extra in (["--generate_audio", "false"], []):      # a model without a sound switch is priced without it
                try:
                    r = subprocess.run(base + extra, capture_output=True, text=True, timeout=30)
                except (OSError, subprocess.SubprocessError):
                    break
                head = (r.stdout or "").strip().split(" ")[0]
                if r.returncode == 0 and head.replace(".", "", 1).isdigit():
                    val = float(head)
                    break
        _CREDITS[(job, res)] = val
    return _CREDITS[(job, res)]


def clip_choices():
    """The clip models a person can pick for a shot: the house default first, then the house's other clip choices
    (components/generative-model-house, choices('clips.seedance')), each marked wired here or not, with its price."""
    house = []
    try:
        spec = importlib.util.spec_from_file_location("team_model_house", ST.part("generative-model-house") / "model_house.py")
        mh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mh)
        house = [c["registry_id"] for c in mh.choices("clips.seedance")]
    except Exception:  # noqa: BLE001 - the list still shows what is wired here
        house = [DEFAULT]
    order = [DEFAULT] + [i for i in house if i != DEFAULT] + [p for p in PICKS if p not in house]
    out = []
    for rid in dict.fromkeys(order):
        p = PICKS.get(rid) or {}
        job, res = (DEFAULT_JOB, "480p") if rid == DEFAULT else (p.get("job"), p.get("res", "480p"))
        out.append({"id": rid, "default": rid == DEFAULT, "wired": rid == DEFAULT or rid in PICKS, "in_house": rid in house,
                    "how": "Higgsfield API" if rid == DEFAULT else p.get("how"), "resolution": res,
                    "credits_5s": _credits(job, res) if job else None})
    return out


def _recipe_file(name):
    for f in sorted(Path(G).glob("recipes*.json")):
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            continue
        if isinstance(d, list) and any(r.get("name") == name for r in d):
            return f
    raise SystemExit(f"no recipe named {name!r}")


def _save_recipe(f, r):
    d = json.load(open(f))                 # re-read: other runs may have written the file meanwhile
    d = [r if x.get("name") == r["name"] else x for x in d]
    json.dump(d, open(f, "w"), indent=1)


def set_pick(name, model=None):
    """Save a person's clip-model pick on a shot's recipe (None or the default = no pick)."""
    pick = None if model in (None, "", DEFAULT) else model
    if pick and pick not in PICKS:
        raise SystemExit(f"{model!r} is not a clip model this tool can make (wired: {DEFAULT}, {', '.join(PICKS)})")
    f = _recipe_file(name)
    r = [x for x in json.load(open(f)) if x.get("name") == name][0]
    if pick:
        r["clip_model"] = pick
    else:
        r.pop("clip_model", None)
    _save_recipe(f, r)
    return r


def remake(name, model=None):
    """A new take of one shot on the picked clip model. The current clip moves to rejected/ with a note and comes back
    if the new take fails, so the scene never loses its shot."""
    r = set_pick(name, model)
    f = _recipe_file(name)
    out = Path(G) / (name + ".mp4")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    moved = []
    for src in (out, out.with_suffix(".request.json")):
        if src.exists():
            dst = Path(G) / "rejected" / (name + "-" + stamp + src.name[len(name):])
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            moved.append((src, dst))
    note = f"{stamp}: replaced by a new take on {r.get('clip_model') or DEFAULT} (Video Studio)"
    if moved:
        r.setdefault("rejected", []).append(note)
    try:
        make(r, str(out))
    except (RuntimeError, SystemExit) as e:
        for src, dst in moved:
            if not src.exists():
                dst.rename(src)
        if note in r.get("rejected", []):
            r["rejected"].remove(note)
        r["error"] = str(e)
        _save_recipe(f, r)
        raise
    _save_recipe(f, r)
    return {"name": name, "model": r.get("clip_model") or DEFAULT, "made": r.get("made")}


def ref_path(rel):
    p = os.path.join(G, "refs", rel) if not os.path.isabs(rel) else rel
    if not os.path.exists(p):
        raise SystemExit("reference not found: " + p)
    return p


def make(r, out, dry_run=False):
    """One shot through the house process; every step recorded on the recipe."""
    made = {"process": PROCESS, "ref": os.path.join("refs", r["ref"]), "steps": []}
    r["made"] = made                     # kept even when a later step fails, so the studio shows what did run
    frame = ref_path(r["ref"])
    extra = [ref_path(x) for x in r.get("refs") or []]
    master = ref_path(r["master"]) if r.get("master") else None
    if r.get("still"):
        still = os.path.join(G, "refs", r["name"] + "-still.png")
        if not os.path.exists(still):
            t0 = time.time()
            prompt = r["still"] + MATCH
            refs = ([Path(master)] if r.get("master_first") and master else []) + [Path(frame)] + [Path(x) for x in extra if x != master or not r.get("master_first")]
            res = _team("direct_openai").generate(prompt, refs, Path(still), dry_run=dry_run)
            made["steps"].append({"what": "still", "model": res.get("model") or res.get("rung") or EDIT, "note": res.get("note"), "sent": {"prompt": prompt,
                                  "references": [os.path.relpath(x, G) for x in [frame] + extra]},
                                  "out": os.path.relpath(still, G), "request_id": res.get("request_id"),
                                  "seconds": round(time.time() - t0), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            print("still", r["name"], flush=True)
        frame = still
    t0 = time.time()
    prompt = r["action"] + LOOK
    sd = _team("seedance")
    kw = dict(seconds=r.get("seconds", 5), masters=[Path(master)] if master else None, no_people=bool(r.get("no_people")), dry_run=dry_run)
    backup_note = None
    pick = r.get("clip_model")           # a person's pick from the house's clip choices; none = the house default (Seedance 2.5)
    pick = None if pick in (None, "", DEFAULT) else pick
    if pick and pick not in PICKS:
        raise SystemExit(f"{r['name']}: clip_model {pick!r} has no door here (wired: {', '.join(PICKS)}; none = {DEFAULT})")
    if pick:
        res = _door(PICKS[pick]["door"]).motion(prompt, Path(frame), Path(out), **kw, **PICKS[pick]["kw"])
    else:
        try:
            res = sd.motion(prompt, Path(frame), Path(out), **kw)
        except RuntimeError as e:        # the house's backup: Kling 4.0 when Seedance fails or refuses (MODEL-HOUSE.md, Clips)
            backup_note = "Seedance refused (" + str(e)[:120] + "); made on the house backup, Kling 4.0"
            print("backup", r["name"], backup_note, flush=True)
            res = _team("kling").motion(prompt, Path(frame), Path(out), **kw)
    made["steps"].append({"what": "clip", "model": res.get("model") or I2V, "note": backup_note or (PICKS[pick]["label"] if pick else None),
                          "sent": {"prompt": res.get("prompt") or sd.motion_prompt(prompt),
                          "resolution": PICKS[pick]["res"] if pick else sd.RES, "seconds": r.get("seconds", 5), "image": os.path.relpath(frame, G),
                          "face_master": os.path.relpath(master, G) if master else None},
                          "out": os.path.relpath(out, G), "request_id": res.get("request_id"),
                          "seconds": round(time.time() - t0), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    r["made"] = {"edit": EDIT if r.get("still") else None, "clip": PICKS[pick]["label"] if pick else I2V, "frame": os.path.relpath(frame, G), **made}
    r.pop("error", None)
    print("clip", r["name"], flush=True)


def main(path, dry_run=False):
    recipes = json.load(open(path))
    for r in recipes:
        out = os.path.join(G, r["name"] + ".mp4")
        if os.path.exists(out) and not dry_run:
            continue
        try:
            make(r, out, dry_run=dry_run)
        except (RuntimeError, SystemExit) as e:
            r["error"] = str(e)
            print("refused", r["name"], e, flush=True)
    if not dry_run:
        json.dump(recipes, open(path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], dry_run="--dry-run" in sys.argv)
