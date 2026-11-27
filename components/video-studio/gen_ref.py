"""AI shots from our real footage, made one way every time: the house process (the owner, 8 Nov 2026: "this should not be
just some random recipe. This is something that we consistently go through").

  python3 gen_ref.py recipes.json [--dry-run]   runs each recipe once (skips any shot already made), records every step

THE PROCESS (models from the team's Generative Model House, components/generative-model-house/MODEL-HOUSE.md):
  0. Spec        every shot fills one swipe shot (`shot`) and is made only from its complete, AI-routed shot spec
                 (shot_spec.py: route, our product's use, the team's per-shot teardown, swaps and breakdown). The clip's
                 words are the spec's; a recipe's own `action` is refused (spec_gate).
  1. Reference   a real frame of our footage in sources/generated/refs/ (`ref`), plus any extra references (`refs`):
                 the creator's face master, a real setting photo. Never an AI picture as the only reference.
  2. Still       only when the frame needs changing (`still`: what to change). Made by image production (purpose
                 video-still, an edit of the frame, every reference sent; its standing rules ride on it), camera-match clause added.
  3. Clip        Motion first (rule 2026-11-12: every AI clip's motion comes from real footage of the same action; a
                 still with model-invented motion is not a fill): the swipe shot's own seconds (the frame map's span of
                 `shot`), or the recipe's `motion` ({"source", "from", "to"} or {"scene": <dir whose motion passed its checks>}),
                 run through the motion chain (components/motion: tracked, read, rehearsed in 3D, checked, all
                 free), then the clip made by take.py from the still with that
                 motion (Seedance 2.5, 480p, silent). A person in the picture must pass the face gate against `master`
                 (their real frame) first; a picture with none of our people says `"no_people": true`. The face master
                 leads the still's references unless the recipe says `"master_first": false`.
  4. Phone pass  video_studio.phone_copy re-shoots the clip at 432 px with grain and drift when a scene uses it, which is
                 also why the house's local upscale step is skipped here.
A recipe: {"name", "ref", "refs": [...], "master": "...", "still": "...", "action": "...", "seconds": 5, "no_people": false,
"set": "<a filed 3D set (image-production picture_sets.py): a still with people in it is made from its kept print>",
"scene_master": "<name of the scene's first shot>", "continue_from": "<name of the shot before, when there is no cut>"}.
Shots in one scene are made in order as a sequence (BRIEF-SPEC "Scenes and shots"): `scene_master` puts the first
shot's still in front of this shot's references, so the same people stand in the same place; `continue_from` starts
this shot from the last frame of the shot before it.
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
PROCESS = "house: reference → GPT Image 2.5 still → Seedance 2.5 clip (Higgsfield plan credits, else the API wallet; 480p) → phone pass"
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


PLAN = "seedance-2.5 (Higgsfield plan credits, CLI, exact start frame, 480p, silent)"


def plan_motion(prompt, still, out, seconds=None, masters=None, no_people=False, dry_run=False):
    """A silent Seedance 2.5 clip on the signed-in Higgsfield plan's credits, through the same command-line route the
    Studio's takes use (take.py `seedance@higgsfield`): the picture is the exact start frame. The face gate runs first,
    as on the API route. Raises RuntimeError when the plan refuses, so the API wallet is tried next."""
    sd = _team("seedance")
    text = sd.motion_prompt(prompt, no_people=no_people)
    secs = int(max(4, round(float(seconds or 5))))
    if dry_run:
        print(json.dumps({"route": "seedance@higgsfield (plan)", "start": str(still), "seconds": secs, "prompt": text}, indent=1))
        return {"model": PLAN, "prompt": text}
    sd._load("face_gate").require(Path(still), masters, no_people=no_people)
    spec = importlib.util.spec_from_file_location("studio_take", os.path.join(HERE, "take.py"))
    tk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tk)
    args = ["--prompt", text, "--mode", "omni_reference", "--start-image", str(still), "--duration", str(secs),
            "--resolution", "480p", "--aspect_ratio", "9:16", "--generate_audio", "false"]
    job, _url = _plan_job(tk, args, str(out))
    return {"model": PLAN, "request_id": str(job), "prompt": text, "credits": _credits(DEFAULT_JOB, "480p") and round(_credits(DEFAULT_JOB, "480p") * secs / 5, 2)}


def _plan_job(tk, args, out):
    """take.py's command-line create and wait, with the download made by curl: this Mac's IPv6 route to the result host
    stalls, and curl falls back to IPv4 where Python's urllib waits out every IPv6 address first."""
    import subprocess
    sp, fp = tk.guard("seedance_2_5", args) if hasattr(tk, "guard") else (None, None)
    r = subprocess.run([tk.HF, "--json", "generate", "create", "seedance_2_5"] + args, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError("higgsfield seedance_2_5: " + (r.stderr or r.stdout).strip()[:400])
    ids = json.loads(r.stdout or "null")
    job = ids[0] if isinstance(ids, list) else (ids or {}).get("id")
    if sp:
        sp.record("seedance_2_5", fp, str(job), out)
    w = subprocess.run([tk.HF, "--json", "generate", "wait", str(job)], capture_output=True, text=True, timeout=3600)
    body = json.loads(w.stdout or "{}")
    if str(body.get("status", "")).lower() != "completed" or not body.get("result_url"):
        raise RuntimeError(f"higgsfield seedance_2_5 ended '{body.get('status')}' (job {job})")
    subprocess.run(["curl", "-sS", "-L", "--retry", "3", "-o", out, body["result_url"]], check=True, timeout=600)
    return job, body["result_url"]


def ref_path(rel):
    p = os.path.join(G, "refs", rel) if not os.path.isabs(rel) else rel
    if not os.path.exists(p):
        raise SystemExit("reference not found: " + p)
    return p


def _made_still(name):
    """The still a made shot started from (its scene master), or None."""
    p = os.path.join(G, "refs", name + "-still.png")
    return p if os.path.exists(p) else None


def last_frame(name):
    """The last frame of a made shot, kept beside it as refs/<name>-last.png, or None when the shot is not made."""
    clip = os.path.join(G, name + ".mp4")
    if not os.path.exists(clip):
        return None
    out = os.path.join(G, "refs", name + "-last.png")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(clip):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.05", "-i", clip, "-frames:v", "1", out], check=True)
    return out


def _brand_of(r):
    """The recipe's brand, or the brand its production's writing run names."""
    brand = r.get("brand")
    if not brand and r.get("brief"):                 # the production's writing run names its brand
        b = json.load(open(ST.BRIEFS / r["brief"] / "brief.json"))
        brand = json.load(open(ST.WRITING / b["brief"] / "run.json")).get("brand")
    if not brand:
        raise SystemExit(f"{r['name']}: no brand (give the recipe a \"brand\" or a \"brief\")")
    return brand


def image_production_still(r, direction, frame, refs, still, dry_run=False):
    """The still is made by image production (ruled 2026-11-09: an AI shot's picture is made by image production; owner,
    10 Nov 2026: "all of this should be running through the tools we already made"). Purpose video-still, an edit of the
    real frame, the other references attached; image production's standing rules (one exposure among them) ride on it."""
    import shutil
    sys.path.append(str(TEAM / "components" / "image-production"))
    import image_production as IP
    brand = _brand_of(r)
    req = {"brand": brand, "purpose": "video-still", "direction": direction, "out": str(still.parent / (r["name"] + "-ip")),
           "from_image": str(frame), "references": [str(x) for x in refs], "people": not r.get("no_people"),
           "label": r["name"], "assets": False}
    if r.get("set"):       # GATE-4 (2026-11-10): a people still is made from the recipe's filed 3D set; its kept print is
        req["set"] = r["set"]                     # the base, and the real frame rides along as a reference only
        lead = [str(refs[0])] if r.get("master_first", True) and refs else []   # the person's real face leads
        req["references"] = lead + [str(frame)] + [x for x in req["references"] if x != str(frame) and x not in lead]
        req.pop("from_image")
    if dry_run:
        ok, resolved = IP.dry_run(req)
        return {"model": "image-production (dry run)", "note": "resolved" if ok else "missing inputs"}
    res = IP.make(req)
    got = (res.get("delivered") or [p.get("file") for p in res.get("pictures") or [] if p.get("file")])
    if not got:
        raise SystemExit(f"{r['name']}: image production made no still ({res.get('check')})")
    shutil.copy(got[0], still)
    return {"model": res.get("model"), "note": "image production · video-still · " + (res.get("model_why") or ""),
            "request_id": res.get("out")}


# THE SHOT SPEC FIRST (owner, 10 Nov 2026: a missing shot is a mini teardown into a replication spec into an injection,
# from the chain that exists, and that is the only way a shot gets made). Every shot this makes fills a swipe shot
# (`shot`), and that shot's spec (shot_spec.py: route, our product's use, the team's per-shot teardown, swaps and
# breakdown) must be complete, routed AI and free of problems. The clip's words are the spec's, never the recipe's.
KEEP_PRINT = "Keep the 3D-set print exactly"


def motion_ref(r):
    """The real footage this shot's motion comes from: the recipe's `motion`, else the swipe shot's own span in the
    frame map. Refuses a shot with neither: a still with model-invented motion is not a fill (rule 2026-11-12)."""
    m = r.get("motion")
    if isinstance(m, dict) and (m.get("scene") or m.get("source")):
        return m
    sc = importlib.util.spec_from_file_location("shot_copy_mr", os.path.join(HERE, "shot_copy.py"))
    SC = importlib.util.module_from_spec(sc)
    sc.loader.exec_module(SC)
    import shot_spec as SPEC
    k = (SPEC.require(r["brief"], r["shot"]).get("swipe") or {}).get("shot")
    fm_dir = SC._framemap(r["brief"])
    fm = json.load(open(fm_dir.parent / "framemap.json"))
    row = next((x for x in (fm.get("shots") or []) if x.get("id") == k), None)
    src = fm_dir.parent.parent / "source.mp4"
    if not (k and row and src.is_file()):
        raise SystemExit(f"{r['name']}: no motion reference: the swipe shot {k or '(none)'} has no span in the frame map; "
                         "give the recipe `motion` (real footage of the same action: owned, else TikTok/YouTube)")
    return {"source": str(src), "from": float(row["start"]), "to": float(row["end"]), "swipe_shot": k}


def motion_clip(r, prompt, still, out, master=None, dry_run=False):
    """The clip with real motion: the face gate on the still, the reference run through the motion chain on the shot's
    own folder (components/motion/motion_chain.py), then take.py makes it from the still with that motion. Returns the
    step record."""
    sd = _team("seedance")
    no_people = bool(r.get("no_people"))
    ref = motion_ref(r)
    sdir = Path(G) / "motion" / r["name"]
    directed = False
    if not ref.get("scene"):
        # every generative clip, a single B-roll shot too, is made the way a scene is (2026-11-15): the shot written as
        # its own take, put into the production capabilities of the swipe shot it re-makes, and directed (our own moves
        # and camera, rendered as the rehearsal). Only a shot whose swipe was never torn down goes the older way below.
        sdir.mkdir(parents=True, exist_ok=True)
        tf = sdir / "take.json"
        if not tf.exists():
            line = (r.get("line") or "").strip()
            tf.write_text(json.dumps({
                "cast": r.get("cast") or {}, "seconds": r.get("seconds"),
                "script": [{"speaker": next(iter(r.get("cast") or {}), ""), "say": line, "do": prompt}],
                "staging": prompt, "motion": {k: ref[k] for k in ("source", "from", "to") if k in ref} | (
                    {"copies": [ref["swipe_shot"]]} if ref.get("swipe_shot") else {}),
                "why": "one shot of the ad (%s), re-making the swipe's shot %s" % (r["name"], ref.get("swipe_shot") or "")},
                indent=1, ensure_ascii=False))
        import production_inject as PI
        if PI.run_of(sdir, json.loads(tf.read_text())) is not None:
            if dry_run:
                print(json.dumps({"route": "production: spec → injection → our direction → take.py", "shot": str(sdir)}, indent=1))
                return {"model": "seedance-2.5 + our direction (take.py)", "prompt": prompt}
            PI.ensure(sdir)
            directed = (json.loads((sdir / "motion" / "motion.json").read_text()) if (sdir / "motion" / "motion.json").exists() else {}).get("kind") == "directed"
    if not dry_run:
        sd._load("face_gate").require(Path(still), [Path(master)] if master else None, no_people=no_people)
        if ref.get("scene"):
            sdir = Path(ref["scene"])
        elif directed:
            pass                                      # our own direction is the motion
        else:
            # the motion chain's one door (components/motion): the reference tracked, read, rehearsed in 3D by the real
            # skeletons and checked against itself, all free, before the take is paid for
            home = str(ST.part("motion"))
            if home not in sys.path:
                sys.path.insert(0, home)
            import motion_chain as MC
            ctx = {"staging": prompt, "cast": r.get("cast") or {}, "seconds": r.get("seconds"),
                   "why": "one shot of the ad, made to move like the swipe's own shot %s" % (ref.get("swipe_shot") or "")}
            span = [(float(ref.get("from", 0.0)), float(ref["to"]))] if ref.get("to") else None
            if no_people:                                  # no bodies to rehearse: the camera's own path is the motion
                MC.prepare(sdir, ctx, source=ref["source"], spans=span, clip=None if span else ref["source"], only=["track"], kind="swipe",
                           camera_only=True)
            else:
                # the chain decides by itself: the motion passes on its own checks or is held with the reasons (after one
                # more read and rehearsal of its own). Nobody is asked; held motion makes no take.
                st = MC.prepare(sdir, ctx, source=ref["source"], spans=span, clip=None if span else ref["source"],
                                only=["track", "read", "rehearse", "preview"], kind="swipe")
                won = st.get("approve") or {}
                if not won.get("ok"):
                    raise SystemExit("%s: the motion is held by its own checks (%s). See %s; give the shot a better reference "
                                     "(the recipe's `motion`) and run it again. No take is paid for from held motion."
                                     % (r["name"], " · ".join(won.get("held") or [won.get("short") or (st.get("track") or {}).get("short") or "it did not run"]),
                                        sdir / "motion" / "preview.mp4"))
    spec = importlib.util.spec_from_file_location("studio_take_m", os.path.join(HERE, "take.py"))
    tk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tk)
    cast = r.get("cast") or {}
    who = next(iter(cast), "PERSON")
    take = {"out": str(out), "model": "seedance@higgsfield", "backups": [], "seconds": int(max(4, round(float(r.get("seconds") or 4)))),
            "picture": str(still), "cast": cast, "speakers": {},
            "script": [{"speaker": who, "say": "", "moves": {}, "camera": "the camera moves as in the motion reference"}],
            "staging": prompt, "motion": {"scene": str(sdir)}, "camera": {},
            "look": "Real handheld phone video, natural light, real skin and fabric, no text, no music, nobody speaks."}
    if directed:                                      # the shot's own rows and our camera, from its production sheet
        own = json.loads((sdir / "take.json").read_text())
        take.update({k: own[k] for k in ("script", "staging", "camera", "lineup") if own.get(k)})
    if dry_run:
        print(json.dumps({"route": "take.py seedance@higgsfield + motion", "motion": ref, "start": str(still)}, indent=1))
        return {"model": "seedance-2.5 + motion (take.py)", "prompt": prompt}
    res = tk.make(take)
    return {"model": "seedance-2.5 + motion from %s (take.py)" % (ref.get("swipe_shot") or "the motion reference"),
            "request_id": res.get("request_id"), "prompt": prompt, "motion": ref}


def spec_gate(r):
    import shot_spec as SPEC
    if not r.get("shot") or not r.get("brief"):
        raise SystemExit(f"{r['name']}: name its `brief` and the swipe `shot` it fills; the shot is defined first: "
                         "shot_spec.py <idea> <shot>")
    s = SPEC.require(r["brief"], r["shot"])
    if r.get("action") and r["action"].strip() != s["clip_words"].strip():
        raise SystemExit(f"{r['name']}: its action is written by hand; the clip's words come from the shot spec "
                         f"({r['shot']}): leave `action` out")
    if r.get("still") and not (r["still"].startswith(KEEP_PRINT) or r["still"].strip() == s["still_words"].strip()):
        raise SystemExit(f"{r['name']}: its still is written by hand; a still is the shot spec's words or the 3D print kept as it is")
    r["action"] = s["clip_words"]
    return {"shot": r["shot"], "fingerprint": s.get("fingerprint"), "route": s["route"]["route"], "use": s["use"]["our_does"]}


def make(r, out, dry_run=False):
    """One shot through the house process; every step recorded on the recipe."""
    spec = spec_gate(r)
    made = {"process": PROCESS, "ref": os.path.join("refs", r["ref"]), "steps": [], "spec": spec}
    r["made"] = made                     # kept even when a later step fails, so the studio shows what did run
    frame = ref_path(r["ref"])
    extra = [ref_path(x) for x in r.get("refs") or []]
    if r.get("continue_from"):           # no cut: this shot starts where the one before it ended
        lf = last_frame(r["continue_from"])
        if lf is None:
            raise SystemExit(f"{r['name']}: continues from {r['continue_from']}, which is not made yet (make the scene in order)")
        frame = lf
        made["continues_from"] = r["continue_from"]
    if r.get("scene_master"):            # the same people in the same place as the scene's first shot
        sm = _made_still(r["scene_master"]) or last_frame(r["scene_master"])
        if sm is None:
            raise SystemExit(f"{r['name']}: its scene master {r['scene_master']} is not made yet (make the scene in order)")
        extra = [sm] + [x for x in extra if x != sm]
        made["scene_master"] = r["scene_master"]
    master = ref_path(r["master"]) if r.get("master") else None
    if r.get("set") and not r.get("still"):   # GATE-4: a clip straight from the set's kept 3D print, nothing remade
        sys.path.append(str(TEAM / "components" / "image-production"))
        from image_production import set_gate as _SG
        b = _brand_of(r)
        kp = _SG.kept_print(b, _SG.set_name(r["set"]))
        if kp is None:
            raise SystemExit(f"{r['name']}: set {r['set']} has no kept print (the 3d-print skill makes and files it)")
        frame = str(kp)
        made["from_print"] = str(kp)
    if r.get("still"):
        still = os.path.join(G, "refs", r["name"] + "-still.png")
        if not os.path.exists(still):
            t0 = time.time()
            prompt = r["still"] + MATCH
            mf = r.get("master_first", True)   # the real face leads (a drifted face was the one fix that held, 12 Nov)
            refs = ([Path(master)] if mf and master else []) + [Path(frame)] + [Path(x) for x in extra if x != master or not mf]
            res = image_production_still(r, prompt, Path(frame), [x for x in refs if x != Path(frame)], Path(still), dry_run)
            made["steps"].append({"what": "still", "model": res.get("model") or res.get("rung") or EDIT, "note": res.get("note"), "sent": {"prompt": prompt,
                                  "references": [os.path.relpath(x, G) for x in [frame] + extra]},
                                  "out": os.path.relpath(still, G), "request_id": res.get("request_id"),
                                  "seconds": round(time.time() - t0), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            print("still", r["name"], flush=True)
        frame = still
    t0 = time.time()
    prompt = r["action"] + (LOOK.replace(" same people,", "") if r.get("no_people") else LOOK)
    sd = _team("seedance")
    kw = dict(seconds=r.get("seconds", 5), masters=[Path(master)] if master else None, no_people=bool(r.get("no_people")), dry_run=dry_run)
    backup_note = None
    pick = r.get("clip_model")           # a person's pick from the house's clip choices; none = the house default (Seedance 2.5)
    pick = None if pick in (None, "", DEFAULT) else pick
    if pick and pick not in PICKS:
        raise SystemExit(f"{r['name']}: clip_model {pick!r} has no door here (wired: {', '.join(PICKS)}; none = {DEFAULT})")
    if not pick:                         # the house route: motion from real footage, through the take (rule 2026-11-12)
        res = motion_clip(r, prompt, Path(frame), Path(out), master, dry_run)
    elif pick:
        res = _door(PICKS[pick]["door"]).motion(prompt, Path(frame), Path(out), **kw, **PICKS[pick]["kw"])
    else:
        try:                             # Seedance 2.5 on the plan's credits first, the route the hook's take uses
            res = plan_motion(prompt, Path(frame), Path(out), **kw)
        except RuntimeError as e0:
            try:                         # then the Higgsfield API wallet
                res = sd.motion(prompt, Path(frame), Path(out), **kw)
                backup_note = "plan route failed (" + str(e0)[:100] + "); made through the Higgsfield API wallet"
            except RuntimeError as e:    # the house's backup: Kling 4.0 when Seedance fails or refuses (MODEL-HOUSE.md, Clips)
                backup_note = "Seedance refused (" + str(e)[:120] + "); made on the house backup, Kling 4.0"
                print("backup", r["name"], backup_note, flush=True)
                res = _team("kling").motion(prompt, Path(frame), Path(out), **kw)
    made["steps"].append({"what": "clip", "model": res.get("model") or I2V, "note": backup_note or (PICKS[pick]["label"] if pick else None),
                          "sent": {"prompt": res.get("prompt") or sd.motion_prompt(prompt),
                          "resolution": PICKS[pick]["res"] if pick else sd.RES, "seconds": r.get("seconds", 5), "image": os.path.relpath(frame, G),
                          "face_master": os.path.relpath(master, G) if master else None},
                          "out": os.path.relpath(out, G), "request_id": res.get("request_id"),
                          "seconds": round(time.time() - t0), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    r["made"] = {"edit": EDIT if r.get("still") else None, "clip": PICKS[pick]["label"] if pick else (res.get("model") or I2V), "frame": os.path.relpath(frame, G), **made}
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
