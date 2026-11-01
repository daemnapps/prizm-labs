"""The model inputs: what a picture or clip model takes, what works, what to avoid. One file per model in inputs/.

    import input_rules as IR
    IR.for_job("pictures.edit")                      # the rules of whatever model the Model House gives that job
    IR.limits("gpt-image-2.5")                       # the numbers (max images, size rule, prompt length)
    IR.check("gpt-image-2.5", prompt, images=[{"path": ..., "role": ...}], size="1152x2048", quality="high")
    IR.render("gpt-image-2.5")                       # the slice a prompt binds as {model_inputs}

`check` returns findings, each {id, level: "error"|"warn", say}. An error means the model would refuse the request or
the request breaks a rule we hold; the engine stops on an error. A warning is shown and sent anyway.
No credential, no network. Python 3.9: no `X | Y` type hints.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = "gpt-image-2.5"      # only when a caller names no job; a chain asks for_job() so the house decides
SECTIONS = ("INPUTS", "THE PICTURE", "THE PRODUCT", "THE PEOPLE", "THE FRAME", "RULES")


_HOUSE = []


def _house():
    """components/generative-model-house/model_house.py, loaded by path (the folder has a hyphen): the house says
    which model does which job, and this component answers what that model takes."""
    if not _HOUSE:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mi_model_house", HERE.parent / "generative-model-house" / "model_house.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _HOUSE.append(mod)
    return _HOUSE[0]


def model_of(job):
    """The registry id the Model House gives a job ('pictures.edit' -> 'gpt-image-2.5', 'clips.seedance' -> 'seedance-2.5')."""
    got = _house().model(job)
    rid = got.get("registry_id") if isinstance(got, dict) else None
    if not rid:
        raise KeyError(f"the Model House answers job {job!r} without a single registry id")
    return rid


def for_job(job):
    """The input rules of the model the house sends this job to. Refused by name when that model has no file yet."""
    rid = model_of(job)
    try:
        return load(rid)
    except KeyError:
        raise KeyError(f"the Model House sends {job!r} to {rid!r}, which has no inputs file in components/model-inputs yet")


KINDS = {"voice-tts": "voice", "voice-design": "voice", "music": "music", "upscale-video": "upscale", "3d-from-image": "3d", "judge-vision": "judge"}


def coverage(everything=False):
    """Every picture and clip job in the house, the model it names, and whether its rules are on file and filled.
    `everything=True` also lists the jobs behind the line (voice, music, upscale, 3D, judge), whose files say
    their medium as voice / music / upscale / 3d / judge. Each row carries the sheet's depth (`counts`) and
    whether every structure rule and avoid item names its source (`sourced`)."""
    out = []
    house = _house()

    def walk(node, path):
        for k, v in node.items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            if "registry" in v:
                cap = str(v.get("capability", ""))
                medium = "image" if cap.startswith("image") else ("video" if cap.startswith("video") else None)
                if medium is None and everything:
                    medium = KINDS.get(cap)
                if medium:
                    rid = v["registry"] if isinstance(v["registry"], str) else None
                    f = HERE / "inputs" / f"{rid}.json"
                    d = json.loads(f.read_text()) if f.is_file() else {}
                    out.append({"job": path + k, "registry_id": rid, "medium": medium, "door": v.get("door"),
                                "file": f.is_file(), "filled": bool(d.get("inputs")),
                                "counts": {x: len(d.get(x, [])) for x in ("inputs", "structure", "avoid", "qualities")},
                                "sourced": bool(d) and all(e.get("source") for x in ("structure", "avoid") for e in d.get(x, []))})
            else:
                walk(v, path + k + ".")

    walk(house.house(), "")
    return out


def load(model=DEFAULT):
    f = HERE / "inputs" / f"{model}.json"
    if not f.is_file():
        raise KeyError(f"no inputs file for {model!r} (have: {', '.join(sorted(p.stem for p in (HERE / 'inputs').glob('*.json')))})")
    return json.loads(f.read_text())


def limits(model=DEFAULT):
    return load(model)["limits"]


def qualities(model=DEFAULT):
    return tuple(q for q in load(model).get("qualities", []))


def valid_size(size, model=DEFAULT):
    """None when the size is allowed, else why not (OpenAI's custom-size rule)."""
    r = limits(model).get("size")
    if not r:
        return f"{model} has no size rule on file"
    try:
        w, h = (int(x) for x in str(size).lower().split("x"))
    except ValueError:
        return f"{size!r} is not WIDTHxHEIGHT"
    if w % r["multiple_of"] or h % r["multiple_of"]:
        return f"both edges must be multiples of {r['multiple_of']}"
    if max(w, h) > r["max_edge"]:
        return f"an edge is over {r['max_edge']}"
    if max(w, h) / min(w, h) > r["max_ratio"]:
        return f"the ratio is over {r['max_ratio']}:1"
    if not r["min_pixels"] <= w * h <= r["max_pixels"]:
        return f"the pixel count must be {r['min_pixels']:,} to {r['max_pixels']:,}"
    return None


def check(model, prompt, images=(), size=None, quality=None, aspect="9:16", door=None, resolution=None, variant=None, mask=False, duration=None, audio=0, videos=0):
    """The request against the model's limits and the prompt against the structure that works. `door` names the
    door the call goes through when it is not the maker's own: a door may sell fewer inputs (Higgsfield has no mask,
    no WxH size) and has its own defaults."""
    d = load(model)
    hf = (d.get("doors") or {}).get(door) if door and door != "openai" else None
    L = d["limits"]
    out = []

    def add(id_, level, say):
        out.append({"id": id_, "level": level, "say": say})

    n = len(images)
    if n > L.get("max_images", 10 ** 6):
        add("max-images", "error", f"{n} images is more than the model takes ({L['max_images']}).")
    for i, im in enumerate(images, 1):
        p = Path(str(im.get("path") if isinstance(im, dict) else im))
        ext = p.suffix.lower().lstrip(".")
        if ext and L.get("image_formats") and ext not in L["image_formats"]:
            add("image-format", "error", f"IMAGE {i} is .{ext}; the model takes {', '.join(L['image_formats'])}.")
        if p.is_file() and L.get("max_image_mb") and p.stat().st_size > L["max_image_mb"] * 1024 * 1024:
            add("image-size", "error", f"IMAGE {i} is over {L['max_image_mb']} MB.")
        if f"IMAGE {i}" not in prompt.upper().replace("IMAGE  ", "IMAGE ") and f"image {i}" not in prompt.lower():
            add("number-inputs", "warn", f"IMAGE {i} is attached but the prompt never says what it is.")
    if d.get("medium") == "video":               # a clip: its length and its reference counts
        lo, hi = (L.get("duration_seconds") or [0, 10 ** 6])
        if duration is not None and not lo <= duration <= hi:
            add("duration", "error", f"{duration} s is outside what the model makes ({lo} to {hi} s).")
        if audio > L.get("max_audio_clips", 10 ** 6):
            add("max-audio", "error", f"{audio} voice clips is more than the model takes ({L['max_audio_clips']}).")
        if videos > L.get("max_videos", 10 ** 6):
            add("max-videos", "error", f"{videos} reference videos is more than the model takes ({L['max_videos']}).")
        if n + audio + videos > L.get("max_references_total", 10 ** 6):
            add("max-references", "error", f"{n + audio + videos} reference files is more than the model takes ({L['max_references_total']}).")
        for tok, have, what in (("Image", n, "image"), ("Audio", audio, "voice clip"), ("Video", videos, "reference video")):
            for i in range(1, have + 1):
                if f"{tok.lower()} {i}" not in prompt.lower():
                    add("number-inputs", "warn", f"{tok} {i} ({what}) is sent but the prompt never says what it is.")
    if len(prompt) > L.get("max_prompt_chars", 10 ** 9):
        add("prompt-length", "error", f"the prompt is {len(prompt):,} characters; the limit is {L['max_prompt_chars']:,}.")
    if hf:
        if mask and "mask (no region edit)" in " ".join(hf.get("not_available", [])):
            add("door-no-mask", "error", f"the {door} door has no mask: a region edit cannot go through it.")
        if size and hf.get("resolutions"):
            add("door-no-size", "error", f"the {door} door takes a resolution tier ({', '.join(hf['resolutions'])}) and an aspect ratio, not a WxH size.")
        if resolution and hf.get("resolutions") and resolution not in hf["resolutions"]:
            add("resolution", "error", f"resolution {resolution!r} is not one of {', '.join(hf['resolutions'])}.")
        if variant and hf.get("variants") and variant not in hf["variants"]:
            add("variant", "error", f"variant {variant!r} is not one of {', '.join(hf['variants'])}.")
        missing = [n for n, have, key in (("variant", variant, "variants"), ("quality", quality, "qualities"), ("resolution", resolution, "resolutions"))
                   if hf.get(key) and have is None]
        if missing:
            add("door-defaults", "error", f"the {door} door has defaults you do not want (see its section); the call must name {', '.join(missing)}.")
        if quality and hf.get("qualities") and quality not in hf["qualities"]:
            add("quality", "error", f"quality {quality!r} is not one of {', '.join(hf['qualities'])}.")
        if hf.get("aspect_ratios") and aspect not in hf["aspect_ratios"]:
            add("aspect", "error", f"aspect {aspect!r} is not one the {door} door makes.")
    else:
        if size:
            bad = valid_size(size, model)
            if bad:
                add("size", "error", f"size {size}: {bad}.")
        if quality and d.get("qualities") and quality not in d["qualities"]:
            add("quality", "error", f"quality {quality!r} is not one of {', '.join(d['qualities'])}.")
    if model.startswith("gpt-image"):
        need = ["THE PICTURE", "RULES"] + (["THE FRAME"] if aspect == "9:16" else [])
        missing = [x for x in need if re.search(r"^" + re.escape(x) + r"$", prompt, re.M) is None]
        if missing:
            add("labelled-sections", "warn", "the prompt is missing the section(s): " + ", ".join(missing) + ".")
        if n and "is the reference" in prompt.lower() and "do not change anything else" not in prompt.lower() and "change only" not in prompt.lower():
            add("preserve-then-change", "warn", "images are attached but the prompt never says what must not change.")
        if re.search(r"[\"“][^\"”]{2,}[\"”]", prompt) and "no writing" not in prompt.lower() and "no extra text" not in prompt.lower():
            add("exact-words", "warn", "there are quoted words but nothing says no other writing.")
        if aspect == "9:16" and "safe zone" not in prompt.lower():
            add("frame-zone", "warn", "a 9:16 picture needs the safe zone stated in the prompt.")
    if d.get("medium") == "image":                          # PSH-9 (draw-only prompt): notes are read as picture content
        hits = [n for n, rx in (("markdown bold", r"\*\*"), ("a table", r"(?m)^\s*\|.*\|\s*$"), ("backticks", r"`"),
                                ("'source copy'", r"(?i)source copy"), ("a character count", r"(?i)characters \(source"),
                                ("'Why it rhymes'", r"(?i)why it rhymes"))
                if re.search(rx, prompt)]
        try:                                                 # PSH-10 (dials as picture words): no level definition verbatim
            cc = json.loads((HERE.parent / "creative-controls" / "controls.json").read_text())
            defs = [sc["what"].rstrip(".") for d_ in cc["dials"] for sc in d_["scale"] if len(sc["what"]) > 24]
            sent = [x for x in defs if x in prompt]
            if sent:
                add("dial-definition", "error", "a dial's dictionary definition is in the prompt, which the model draws literally: "
                    + "; ".join(f"“{x}”" for x in sent[:3]) + ".")
        except (OSError, ValueError, KeyError):
            pass
        if hits:
            add("notes-in-prompt", "error", "the prompt carries brief notes the model would draw: " + ", ".join(hits) + ".")
    for a in d.get("avoid", []):
        if a.get("pattern"):
            m = re.search(a["pattern"], prompt, re.I)
            if m:
                add(a["id"], "warn", f"{a['text']} Found: “{m.group(0)}”.")
    return out


def render(model=DEFAULT):
    d = load(model)
    L = []
    w = L.append
    w(f"# {d['label']} — what it takes, and what works\n")
    w(f"*Rendered from `components/model-inputs/inputs/{model}.json` (read {d['read']}, status {d['status']}) by `input_rules.py render`; never hand-edited.*\n")
    if not d.get("inputs"):
        w("Nothing on file yet for this model. " + (d.get("source_of_truth") and f"The field-level contract is `{d['source_of_truth']}`." or "") + "\n")
        return "\n".join(L)
    w("## Limits\n")
    L_ = d["limits"]
    if "max_image_mb" in L_ and "size" in L_:                    # a picture model
        w(f"- Images per call: up to {L_['max_images']}, each {', '.join(L_['image_formats'][:3])} under {L_['max_image_mb']} MB.")
        w(f"- Prompt: up to {L_['max_prompt_chars']:,} characters.")
        s = L_["size"]
        w(f"- Size: WxH, both multiples of {s['multiple_of']}, each edge up to {s['max_edge']}, ratio up to {s['max_ratio']}:1, "
          f"{s['min_pixels']:,} to {s['max_pixels']:,} pixels (above {s['experimental_above_pixels']:,} is experimental).")
        w(f"- Quality: {', '.join(d['qualities'])}.")
        w(f"- House: quality {d['house']['quality']} (video stills {d['house']['quality_video_stills']}), frame {d['house']['frame']}.\n")
    else:                                        # a clip model: its numbers as the file gives them
        for k, v in L_.items():
            if k in ("house", "note"):
                continue
            w(f"- {k.replace('_', ' ')}: {v if not isinstance(v, list) else ' to '.join(str(x) for x in v)}")
        if L_.get("house"):
            w("- House: " + "; ".join(f"{k} {v}" for k, v in L_["house"].items()))
        if L_.get("note"):
            w(f"- {L_['note']}")
        w("")
    w("## The prompt structure that works\n")
    for r in d["structure"]:
        w(f"- **{r['rule']}**")
    w("\n## Avoid\n")
    for a in d["avoid"]:
        w(f"- {a['text']}")
    hf = (d.get("doors") or {}).get("higgsfield")
    if hf:
        w("\n## Through Higgsfield (differs from the maker's own door)\n")
        for k in ("variants", "qualities", "resolutions", "backgrounds", "aspect_ratios", "references", "house", "differs_from_openai", "differs"):
            if k in hf:
                v = hf[k]
                v = ", ".join(map(str, v)) if isinstance(v, list) else (", ".join(f"{a} {b}" for a, b in v.items()) if isinstance(v, dict) else v)
                w(f"- {k.replace('_', ' ')}: {v}")
        for k in ("variant", "quality", "resolution"):
            if hf.get(k + "_default"):
                w(f"- default {k}: {hf[k + '_default']}")
        if hf.get("not_available"):
            w("- Not available: " + "; ".join(hf["not_available"]) + ".")
    return "\n".join(L) + "\n"


def write_slices():
    for f in sorted((HERE / "inputs").glob("*.json")):
        (HERE / "slices" / f"{f.stem}.md").write_text(render(f.stem))
        print("wrote", HERE / "slices" / f"{f.stem}.md")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "render":
        write_slices()
    elif cmd == "check":
        sys.exit("usage: import input_rules and call check(model, prompt, images, size, quality)")
