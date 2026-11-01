"""swap_bench — the Prompt Bench's builders for the Genjutsu jobs (swipe_footage.motion_transfer, swipe_footage.swap).

components/model-inputs/builders.json plugs each job in by a line pointing here. A builder takes the brief
({"brand", "label"} of a swipe swap job, machine/swipe_swap_job.py) and returns what the Bench shows before anything is
made: the words, every input in order, the settings, and the fields. Nothing here makes or spends anything; the make
press stays a person's.

The rules for each come from its sheet (components/model-inputs/inputs/higgsfield-motion-control.json and
higgsfield-object-swap.json), read by input_rules.check inside preview(): the scene still is the person and the room
and the product, the swipe drives only the movement, never the master, 9:16 on both.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _job_mod():
    spec = importlib.util.spec_from_file_location("vm_swb_job", HERE / "swipe_swap_job.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seconds(path) -> float:
    try:
        return round(_job_mod()._dur(path), 1)
    except Exception:
        return 0.0


def _still(job: dict, d: Path) -> str:
    """The approved scene still, once made: the job's own `still`, or the newest file in its still folder."""
    for cand in [job.get("still")] + sorted((str(p) for p in (d / "still").glob("*.png")), reverse=True) if (d / "still").is_dir() else [job.get("still")]:
        if cand and Path(cand).exists():
            return str(cand)
    return "the scene still (not made yet)"


def _bl(brief: dict):
    """The job a brief names: {brand, label}, or the Prompt Bench's card id run="swap:<brand>/<label>"."""
    if brief.get("label"):
        return brief["brand"], brief["label"]
    b, _, l = str(brief.get("run") or "").split(":", 1)[-1].partition("/")
    return b, l


def _bench(job: dict, still: str, secs: float, scene: str) -> dict:
    """What the Prompt Bench's video steps show: the one clip, what goes in, and the fields step 3 lets a person change."""
    return {"calls": [{"id": "S1", "seconds": int(round(secs)) or 14, "talking": False, "start": still if Path(still).exists() else ""}],
            "choices": [{"key": "start", "label": "The start frame (made in Picture ad)", "path": still, "on": True, "fixed": True},
                        {"key": "swipe", "label": "The swipe: it drives the movement", "path": job["clip"], "kind": "video",
                         "on": True, "fixed": True}],
            "fields_extra": {"scene": scene, "scene_id": "S1", "call": "S1", "face": "", "gestures": "", "camera": "hold",
                             "style": "", "spice": 2}}


def _sheet(rid: str, filled: dict) -> dict:
    """The Prompt Bench checklist for a Genjutsu job: every input the model's sheet lists, filled with what this job sends,
    or not applicable with the sheet's own reason. Nothing here decides a value; the sheet and the job do."""
    import json
    d = json.loads((HERE.parents[1] / "model-inputs" / "inputs" / f"{rid}.json").read_text())
    rows = []
    for i in d.get("inputs") or []:
        name, send = str(i.get("name")), str(i.get("we_send") or "")
        key = name.split(" ")[0]
        if key in filled:
            v = filled[key]
            rows.append({"id": key, "name": name, "group": "inputs", "state": "filled" if v and "(not " not in str(v) else "missing",
                         "value": v, "problem": "" if v and "(not " not in str(v) else f"{name}: {v or 'missing'}"})
        else:
            na = send.lower().startswith(("not used", "not available", "not sent", "not "))
            rows.append({"id": key, "name": name, "group": "inputs", "state": "not_applicable" if na else "filled",
                         "value": send, "reason": send})
    return {"rows": rows, "groups": [{"id": "inputs", "name": "What the model takes"}], "flags": [], "needs": [],
            "recipe": {"sheet": {}}}


def motion_transfer(brief: dict) -> dict:
    """Genjutsu motion transfer: the approved scene still is the person, her room and the product; the swipe's one
    clean shot drives only the movement. Settings are the sheet's own defaults (standard tier, 480p, video orientation,
    the room from the still, the swipe's sound off)."""
    jm = _job_mod()
    brand, label = _bl(brief)
    p, job = jm._read(brand, label)
    d = p.parent
    clip = job["clip"]
    secs = _seconds(clip)
    words = ("Image 1 is the woman, her room and the product on the counter: keep all three exactly as the picture shows. "
             "Video 1 is the movement only: copy its timing, gestures, expression and camera. No new objects, no words or "
             "captions anywhere. One continuous take. Every product on the counter stays where it stands, behind her hands in "
             "depth; her hands and the money pass in front of it and never through it.")   # props-away-from-hands (the sheet)
    scene = brief.get("scene") if brief.get("scene") is not None else jm.action_words(job)
    if brief.get("scene"):                                   # a person's change on step 3 of the Prompt Bench
        words += " What happens: " + brief["scene"].strip()
    inputs = [
        {"n": 1, "kind": "image", "role": "the approved scene still (her, her room, the product)", "path": _still(job, d)},
        {"n": 1, "kind": "video", "role": "the swipe's movement (it drives only the movement)", "path": clip},
    ]
    c = jm.cast_files(job["brand"], job["cast"])
    stand_in = job.get("still") if job.get("still") and Path(job["still"]).exists() else (str(c["baseline"][0]) if c["baseline"] else "")
    return {"prompt": words, "inputs": inputs, "medium": "video",
            # the price is asked of Higgsfield for free; this model takes only a prompt, a resolution and the two references
            "quote_args": ["generate", "cost", "hf_mult_motion_control", "--prompt", words, "--resolution", "480p",
                           "--image-references", stand_in, "--video-references", clip, "--json"],
            "settings": {"duration": max(3, int(round(secs))) if secs else 14, "aspect": "9:16", "resolution": "480p",
                         "vendor_model": "hf_mult_motion_control", "mode": "std", "character_orientation": "video",
                         "background_source": "input_image", "keep_original_sound": False},
            **{k: v for k, v in _bench(job, inputs[0]["path"], secs, scene).items() if k != "fields_extra"},
            "sheet": _sheet("higgsfield-motion-control", {"image_references": inputs[0]["path"], "video_references": clip,
                                                           "prompt": words, "resolution": "480p", "duration": f"{secs} s, the swipe's own length",
                                                           "aspect": "9:16"}),
            "fields": {**_bench(job, inputs[0]["path"], secs, scene)["fields_extra"], "label": job["label"], "cast": job["cast"],
                       "sound": job.get("sound") or "", "headline": job.get("headline") or "", "brief": job.get("brief") or "",
                       "made": job.get("made") or "", "finals": list(job.get("final") or []),
                       "recipe": job.get("recipe")},   # the start frame's own picture recipe: the bench opens it in the picture steps
            "notes": ["Genjutsu motion transfer: the swipe's shot drives the movement; the still gives the person, the room and "
                      "the product. The product is checked in every clip afterwards (the maker says props can drop).",
                      f"the swipe shot is {secs} s; the maker's range is 3 to 30 s"],
            "send": {"job": f"{brand}/{label}", "prompt": words, "still": inputs[0]["path"], "video": clip}}


def swap(brief: dict) -> dict:
    """Genjutsu object swap, the fallback: our cast swapped into the swipe's own shot, keeping its motion. It replaces and
    never adds, so a product must already be in the swipe's hand or counter; the baseline goes in, never the master."""
    jm = _job_mod()
    brand, label = _bl(brief)
    p, job = jm._read(brand, label)
    c = jm.cast_files(job["brand"], job["cast"])
    inputs = [{"n": 1, "kind": "video", "role": "the swipe's own shot", "path": job["clip"]}]
    for i, f in enumerate(c["baseline"], 1):
        inputs.append({"n": i, "kind": "image", "role": f"{job['cast']}: {Path(f).stem}", "path": str(f)})
    names = [Path(f).stem.replace("-", " ") for f in c["baseline"]]
    bound = " ".join(f"Image {i} is her {nm}." for i, nm in enumerate(names, 1))
    words = ("Video 1 is the source shot. " + bound + " She replaces the person in the source: the same face, hair, skin, "
             "build and age, dressed as the look picture shows. "
             "Nothing of the original person remains. Keep everything else exactly as in the source video: the money in her "
             "hands, the room, the camera and the light. One continuous take. No words anywhere.")
    qa = ["generate", "cost", "hf_mult_replace_object", "--prompt", words, "--resolution", "480p"]
    for i in inputs:
        if i["kind"] == "image":
            qa += ["--image-references", i["path"]]
    return {"prompt": words, "inputs": inputs, "medium": "video", "quote_args": qa + ["--video-references", job["clip"], "--json"],
            "settings": {"duration": max(4, int(round(_seconds(job["clip"]) or 14))), "aspect": "9:16", "resolution": "480p",
                         "vendor_model": "hf_mult_replace_object"},
            "fields": {"label": job["label"], "cast": job["cast"]},
            "notes": ["Genjutsu object swap replaces and never adds: it cannot put the tube on the counter. Use motion "
                      "transfer from a scene still for that."],
            "send": {"job": f"{brand}/{label}", "prompt": words}}
