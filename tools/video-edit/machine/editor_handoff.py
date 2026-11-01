"""The video editor's handoff: one video brief, packaged so the video editor — a person in their own editing software,
or an agent — makes the finished ad from it (the owner, Tella 2026-10-27: "final handoff capabilities for both the team and
the team"; "make this name agnostic. and the name of the folders need to be the same for both repo and drive ... briefs
should come from final stages of the chains, not some random set up").

Only a production run made from the writing chain's final stage, and filed by it, is taken; a test run is refused by
name. The folder is the Hand-off Standard's (handoff.md in its eight sections, manifest.json, briefs/, assets/,
references/, returned/) at runs/handoffs/video-editor/<brand>/<brief key>/, and at the same path below Shared Assets/
on the drive: every scene's clip, first and last frame and voice line, the whole voice read, the music and sound
effects, the brief, the script, the edit notes and the swipe, every file named with the brief key. The kit is read by
kit_from_run.build (the join), never re-derived here. The finished videos come back into returned/ of that folder,
named <brief key>-control.mp4, <brief key>-v1.mp4 …, where the delivery check reads them. Nothing is generated and
nothing is spent."""
import importlib.util
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
ROLE = "video-editor"   # the role, never a person (the owner, 2026-10-27: "make this name agnostic")
sys.path.insert(0, str(HERE))
import kit_from_run as K  # noqa: E402
import kit_paths as KP  # noqa: E402


class Refused(Exception):
    pass


def frame():
    """The delivered frame: the edit's own canvas (machine/defaults.json), 9:16 only."""
    c = json.loads((HERE / "defaults.json").read_text())["canvas"]
    return {"width": c["width"], "height": c["height"], "fps": c["fps"], "ratio": "9:16"}


def repo():
    return KP.repo() or HOME.parents[1]


def _sibling(component, *parts):
    return repo() / "components" / component / Path(*parts)


def _load(name, path):
    if str(path.parent) not in sys.path:
        sys.path.append(str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(repo().resolve()))
    except ValueError:
        return Path(p).name


# ---------------------------------------------------------------- the brief, its register record, the delivery folder
def register():
    """The brief register (tools/image-teardown tools/briefs.py, its one reader)."""
    return _load("it_briefs_register", _sibling("image-teardown", "tools", "briefs.py")).load()


def brief_of(vm, run, reg=None):
    """(register key, record) of this production run's VIDEO brief. The run's own `brief` is checked against the
    register: a number the register gives to a picture brief is refused by name (two briefs on one number would send
    the finished cut to the wrong brief), never guessed past."""
    reg = reg or register()
    label = run.get("label") or vm.name
    brand = run.get("brand") or vm.parent.name
    # numbers count per brand: another brand's brief-0236 is not this one's
    rows = [(k, r) for k, r in dict.items(reg["briefs"]) if isinstance(r, dict) and r.get("brand") in (None, brand)]
    by_run = [(k, r) for k, r in rows if str(r.get("type", "")).startswith("video")
              and str(r.get("run") or "").rstrip("/").split("/")[-1] == label]
    said = run.get("brief") or (run.get("name") or {}).get("brief")
    if said:
        same = [(k, r) for k, r in rows if said in (k, r.get("brief"))]
        vids = [(k, r) for k, r in same if str(r.get("type", "")).startswith("video")]
        mine = [(k, r) for k, r in vids if str(r.get("run") or "").rstrip("/").split("/")[-1] == label]
        if mine:
            return mine[-1]
        if vids:
            k, r = vids[-1]
            raise Refused(f"{label} says it is {said}, but the register gives {said} to another video ({k}, run "
                          f"{r.get('run')}). One number, two briefs: this video needs its own number before it can be "
                          "handed off")
        if same:
            k, r = same[-1]
            raise Refused(f"{label} says it is {said}, but the register gives {said} to another brief, a {r.get('type')} one "
                          f"({k}, run {r.get('run')}). One number, two briefs: the video needs its own number before "
                          "it can be handed off")
    if by_run:
        return by_run[-1]
    raise Refused(f"{label} has no video brief number in the register yet")


TEST_RUN = re.compile(r"(^|[-_])(v\d*test|batchtest|test|dry|dryrun|dry-run|scratch|proof|sandbox|smoke)([-_]|$)|^fw-v\d")
FINAL_STAGE = "5-brief.md"   # the writing chain's last stage (tools/video-writing): the brief production is made from


def final_stage(vm, run):
    """Refuse, by name, a run that is not the video line's own output: a test or dry run, a brief that is not the
    writing chain's final stage, or one whose final-stage file is gone (the owner, 2026-10-27: "briefs should come from
    final stages of the chains, not some random set up"). Returns the final-stage brief's path."""
    label = run.get("label") or vm.name
    if TEST_RUN.search(label):
        raise Refused(f"{label} is a test run, not the video line's output: only a brief from the writing chain's "
                      "final stage, produced for real, is handed off")
    src = str(run.get("brief_from") or "")
    m = re.search(r"((?:runs|components)/.+/stages/" + re.escape(FINAL_STAGE) + ")$", src)
    if not m:
        raise Refused(f"{label} was made from {Path(src).name or 'no recorded brief'}, not the writing chain's final "
                      f"stage ({FINAL_STAGE})")
    f = repo() / m.group(1)
    slug = f.parent.parent.name
    filed = repo() / "runs" / "video-writing" / (run.get("brand") or vm.parent.name) / slug / "deliverable"
    if not filed.is_dir():
        raise Refused(f"{label}'s brief ({slug}) was never filed by the writing chain (no runs/video-writing/"
                      f"{run.get('brand') or vm.parent.name}/{slug}/deliverable/)")
    if not f.is_file():
        # the teardown's working folder is scratch; the writing chain's filed copy of the same final stage stands in
        if (filed / FINAL_STAGE).is_file():
            return filed / FINAL_STAGE
        raise Refused(f"{label}'s final-stage brief ({m.group(1)}) is no longer in the workspace")
    return f


def swipe_of(run):
    """The swipe the brief copies: the teardown's own source video, found from where the brief came from."""
    src = str(run.get("brief_from") or "")
    m = re.search(r"(runs/video-teardown/.+?|tools/video-teardown/machine/runs/.+?)/stages/", src)
    places = [repo() / m.group(1)] if m else []
    places.append(repo() / "runs" / "video-teardown" / "_work" / (run.get("label") or ""))
    for d in places:
        for name in ("source.mp4", "source.mov"):
            if (d / name).is_file():
                return d / name, (d / "poster.jpg" if (d / "poster.jpg").is_file() else None)
    return None, None


# ---------------------------------------------------------------- the folder
def _num(sid):
    m = re.match(r"S(\d+)(\w*)$", sid or "")   # S3B -> S03B: the letter keeps S3, S3B and S3C apart
    return f"S{int(m.group(1)):02d}{m.group(2)}" if m else sid


VIA = "tools/video-edit/handoff.py"


def place(brand, key):
    """The handoff folder, the same words in the repo and on the drive (the owner, 2026-10-27: "the name of the folders
    need to be the same for both repo and drive"): runs/handoffs/<role>/<brand>/<brief key>/ here, and the same path
    below Shared Assets/ there — the Hand-off Standard's home. The Drive copy is the repo path itself, runs/ included
    (2026-10-28; it was Shared Assets/handoffs/ until then)."""
    rel = f"runs/handoffs/{ROLE}/{brand}/{home_key(brand, key)}"
    return repo() / rel, "Shared Assets/" + rel


def home_key(brand, key):
    """The folder name for a brief's hand-off: the folder already there in any spelling of the key (nothing is
    renamed), else the catalog form (names.catalog_key, 2026-10-28: the catalog id wins, store handles are aliases)."""
    try:
        N = _load("eh_names", _sibling("naming", "names.py"))
        forms = N.brief_key_forms(key)
    except Exception:  # noqa: BLE001 — no naming beside this one: the key as given
        return key
    base = repo() / "runs" / "handoffs" / ROLE / str(brand)
    return next((f for f in [key] + forms if (base / f).is_dir()), forms[0] if forms else key)


def build(vm, out=None, reg=None, kit=None, runsheet="auto"):
    """Write the video editor's handoff for one production run, in the Hand-off Standard's shape (handoff.md,
    manifest.json, briefs/, assets/, references/, returned/), plus the brief's run sheet made self-contained (BRIEF.md,
    RUN.md, run.json, refs/). Returns the record (also written as `manifest.json`). `runsheet`: "auto" packs it when the
    folder is the hand-off's own home, True always, False never, a dict packs that sheet (a test's)."""
    vm = Path(vm).resolve()
    run = json.loads((vm / "run.json").read_text()) if (vm / "run.json").is_file() else {}
    if not run:
        raise Refused(f"{vm.name} is not a video production run (no run.json)")
    final = final_stage(vm, run)
    key, rec = brief_of(vm, run, reg)
    bid, brand = rec["brief"], rec.get("brand") or run.get("brand")
    key = home_key(brand, key)          # the catalog form, or the folder already there
    stem = key   # the brief key (brand_product_brief): a number two brands or products share stays apart
    kit, notes = kit if kit else K.build(vm)
    # L-80: our side ends at the scene pictures the owner approved. No clips yet but approved pictures = the pictures hand-off
    pictures = {} if kit.get("clips") else approved_pictures(vm)
    if not kit.get("clips") and not pictures:
        raise Refused(f"{bid} has no scenes made yet and no approved scene pictures: nothing to hand off")
    home, label = place(brand, key)
    root = Path(out) if out else home
    old = root / "manifest.json"
    if old.is_file() and json.loads(old.read_text()).get("via") != VIA:   # the handoff skill's own folders stay its own
        raise Refused(f"{_rel(root)} already holds a handoff another tool staged ({json.loads(old.read_text()).get('via') or 'the handoff skill'}); "
                      "it is not written over")
    bdir = f"briefs/{bid}"
    for d in (bdir, "assets/clips", "assets/stills", "assets/voice", "assets/music-and-sound", "references", "returned"):
        (root / d).mkdir(parents=True, exist_ok=True)   # a second run writes over the same names, deletes nothing
    files, missing = [], []

    def put(src, sub, name, what):
        p = KP.resolve(src, None) if src else None
        if not p or not Path(p).is_file():
            missing.append(f"{what} ({src or 'none recorded'})")
            return None
        shutil.copy2(p, root / sub / name)
        files.append({"file": f"{sub}/{name}", "is": what})
        return f"{sub}/{name}"

    held = {n.split(":")[0]: n.split(":", 1)[1].strip() for n in notes if re.match(r"S\d+:", n)}
    scenes = []
    for c in kit["clips"]:
        sid, n = c["scene"], _num(c["scene"])
        talks = bool(c.get("talks"))
        row = {"scene": sid, "n": n, "section": c.get("section"), "kind": c.get("kind"), "talks": talks,
               "line": c.get("line") or "", "approved": bool(c.get("approved")), "flag": held.get(sid)}
        row["clip"] = put(c.get("src"), "assets/clips", f"{stem}-{n}-clip{Path(str(c.get('src') or '.mp4')).suffix}",
                          f"scene {sid} clip")
        row["start"] = put(str(vm / "media" / f"{sid}-F1.png"), "assets/stills", f"{stem}-{n}-start.png", f"scene {sid} start still") \
            if (vm / "media" / f"{sid}-F1.png").is_file() else None
        row["end"] = put(str(vm / "media" / f"{sid}-FLAST.png"), "assets/stills", f"{stem}-{n}-end.png", f"scene {sid} end still") \
            if (vm / "media" / f"{sid}-FLAST.png").is_file() else None
        v = (c.get("voice") or {}).get("src") or (str(vm / "vo" / f"{sid}.mp3") if (vm / "vo" / f"{sid}.mp3").is_file() else None)
        row["voice"] = put(v, "assets/voice", f"{stem}-{n}-voice.mp3", f"scene {sid} voice") if v else None
        scenes.append(row)
    if pictures:
        scenes = pictures_rows(vm, pictures, stem, put)
    full = vm / "vo" / "track.mp3"
    voice_full = put(str(full), "assets/voice", f"{stem}-voice-full.mp3", "the whole voice read") if full.is_file() else None
    music = None
    if kit.get("music"):
        m = kit["music"]
        music = {"file": put(m.get("src"), "assets/music-and-sound", f"{stem}-music-{m.get('bank_id') or 'bed'}.mp3", "music bed"),
                 "bank_id": m.get("bank_id"), "bpm": m.get("tempo_bpm"), "mood": m.get("mood")}
    sfx, seen = [], {}
    for s in kit.get("sfx") or []:
        name = f"{stem}-sfx-{s.get('bank_id') or s.get('cue')}{Path(str(s.get('src') or '.mp3')).suffix}"
        if name not in seen:
            seen[name] = put(s.get("src"), "assets/music-and-sound", name, f"sound effect {s.get('cue')}")
        sfx.append({"scene": s.get("scene"), "cue": s.get("cue"), "at": s.get("at_words"), "file": seen[name]})
    swipe, poster = swipe_of(run)
    swipe_f = put(str(swipe), "references", f"{stem}-swipe{swipe.suffix}", "the swipe it copies") if swipe else None
    if poster:
        put(str(poster), "references", f"{stem}-swipe-poster.jpg", "the swipe's cover frame")
    if not swipe:
        missing.append("the swipe video (no teardown source found)")
    hf = higgsfield(vm, run, root, key, put, only=pictures or None)
    shutil.copy2(final, root / bdir / "brief.md")
    files.append({"file": f"{bdir}/brief.md", "is": "the brief (the writing chain's final stage)"})
    (root / bdir / "brief.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    record = {"schema": "handoff/1", "name": key, "role": ROLE, "brand": brand,
              "date": datetime.now().strftime("%Y-%m-%d"), "via": VIA,
              "brief": bid, "key": key, "product": rec.get("product"), "title": rec.get("title") or bid,
              "run": _rel(vm), "final_stage": _rel(final), "made": datetime.now().isoformat(timespec="seconds"),
              "frame": frame(), "gdoc": rec.get("gdoc_url"), "place": label,
              "returned_to": label + "/returned",
              "scenes": scenes, "voice_full": voice_full, "music": music, "sfx": sfx, "swipe": swipe_f,
              "wanted": kit.get("wanted") or {}, "overlays": kit.get("overlays") or [], "hooks": kit.get("hooks") or [],
              "caption_read": kit.get("caption_read"), "files": files, "missing": missing, "drive": None,
              "hook_clips": [], "higgsfield": hf, "stops_at": "nothing goes live; hands back only"}
    if pictures:
        record["stage"] = "pictures"   # approved scene pictures + each scene's clip prompt; the clips and the edit are the editor's
    elif len(record["hooks"]) > 1:
        missing.append(f"the opening clips for variations 1 to {len(record['hooks']) - 1} (not made yet)")
    record["returned"] = [o["name"] for o in outputs(record)]
    record["runsheet"] = pack_runsheet(key, brand, root, runsheet if runsheet != "auto" else root == home)
    (root / bdir / "script.md").write_text(script_md(record))
    files.append({"file": f"{bdir}/script.md", "is": "the script, scene by scene"})
    (root / bdir / "edit-notes.md").write_text(edit_notes_md(record))
    files.append({"file": f"{bdir}/edit-notes.md", "is": "scene order, words on screen, captions, music and sound"})
    (root / "returned" / "README.md").write_text(
        "# returned/\n\nWhat comes back from the video editor, named with the brief key:\n\n"
        + "".join(f"- `{n}`\n" for n in record["returned"])
        + "\nThe delivery check reads this folder and files each video to its brief. Nothing here is live.\n")
    (root / "handoff.md").write_text(start_md(record))
    (root / "manifest.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    if root == home:
        refresh_index(drive=False)
    return {**record, "folder": str(root)}


def pack_runsheet(key, brand, root, how=True):
    """The brief's run sheet made self-contained in this folder (components/briefs runsheet.build + pack, its public
    surface): BRIEF.md, RUN.md, run.json and refs/ with every file the sheet names, so someone in Higgsfield
    Supercomputer with Google Drive and GitHub needs nothing from this Mac (2026-10-28). Returns what went in, or
    why not; never stops the hand-off. None when not asked."""
    if how is False or how is None:
        return None
    try:
        RS = _load("briefs_runsheet_for_editor_handoff", _sibling("briefs", "runsheet.py"))
        sheet = how if isinstance(how, dict) else RS.build(key, brand=brand, repo=repo())
        got = RS.pack(sheet, folder=root, role=ROLE, repo=repo())
        return {"files": got["files"], "refs": len(got["refs"]), "missing": got["missing"],
                "folder": got["folder"], "drive": got["drive"]}
    except (Exception, SystemExit) as e:  # noqa: BLE001 — the hand-off stands; the record says what is missing
        return {"error": f"{type(e).__name__}: {e}"}


def refresh_index(drive=False):
    """runs/handoffs/INDEX.md + START-HERE.md rebuilt through the hand-off front door's own indexer
    (tools/image-edit/handoff_index.py, its command surface). Never stops the hand-off."""
    try:
        return _load("image_edit_handoff_index", _sibling("image-edit", "handoff_index.py")).quiet_refresh(drive=drive)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- remakes in Higgsfield
HIGGSFIELD = "higgsfield"   # one folder per made clip: the exact request, so any scene can be remade in Supercomputer


def _plain_model(mid):
    """seedance_2_5 -> the model's own label from model-inputs (Seedance 2.5); the id itself when none is filed."""
    try:
        folder = str(_sibling("model-inputs"))
        if folder not in sys.path:
            sys.path.append(folder)
        import input_rules as IR  # noqa: E402
        for rid in (mid, re.sub(r"_(\d)_(\d)$", r"-\1.\2", mid or ""), (mid or "").replace("_", "-")):
            try:
                return IR.load(rid).get("label") or mid
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    return mid


def approved_pictures(vm):
    """{section id: picture file} for each scene start picture the owner approved on the board (shot-approvals.json), only
    where the file is still the exact bytes he approved (L-80: our side of a video brief ends at these pictures)."""
    f = Path(vm) / "shot-approvals.json"
    if not f.is_file():
        return {}
    import hashlib
    out = {}
    for gid, a in (json.loads(f.read_text()) or {}).items():
        pic = (a or {}).get("picture")
        p = (Path(pic) if Path(str(pic or "")).is_absolute() else repo() / str(pic or "")) if pic else None
        if p and p.is_file() and hashlib.sha1(p.read_bytes()).hexdigest()[:16] == a.get("sha"):
            out[gid] = p
    return out


def pictures_rows(vm, pictures, stem, put):
    """One scene row per approved section, its approved picture filed under assets/stills/ and no clip."""
    plan = Path(vm) / "clips" / "plan.json"
    calls = (json.loads(plan.read_text()).get("calls") or []) if plan.is_file() else []
    rows, seen = [], set()
    for c in calls:
        gid = c.get("section_id")
        if gid not in pictures or gid in seen or not c.get("scenes"):
            continue
        seen.add(gid)
        sid = c["scenes"][0]
        n = _num(sid)
        rows.append({"scene": sid, "n": n, "section": c.get("section"), "kind": None, "talks": bool(c.get("talking")),
                     "line": " ".join(str(x.get("text") or "") for x in c.get("lines") or []), "approved": True, "flag": None,
                     "clip": None, "end": None, "voice": None,
                     "start": put(str(pictures[gid]), "assets/stills", f"{stem}-{n}-start.png", f"scene {sid} approved picture")})
    return rows


def higgsfield(vm, run, root, key, put, only=None):
    """Every clip the video line made, as Higgsfield Supercomputer takes it (the owner, 2026-10-27: the video editor also
    works in Higgsfield Supercomputer, so every handoff has to work there too): per clip, prompt.md with the prompt word
    for word as it was sent (the clip's own mcp-request.json, else the plan's), the model and settings, and the pictures
    and voice it names, numbered IMAGE-1, IMAGE-2, AUDIO-1. Read from clips/plan.json; nothing is sent or spent."""
    plan = vm / "clips" / "plan.json"
    if not plan.is_file():
        return []
    calls = json.loads(plan.read_text()).get("calls") or []
    models = run.get("scene_models") or {}
    rows, used, by_call = [], set(), {}
    for c in calls:
        if not c.get("prompt") or not c.get("scenes"):
            continue
        if only is not None and c.get("section_id") not in only:   # pictures hand-off: approved scenes only
            continue
        req_f = vm / "clips" / "omni" / c["id"] / "mcp-request.json"
        req = json.loads(req_f.read_text()) if req_f.is_file() else {}
        name = "-".join(_num(s) for s in c["scenes"])
        k = 2
        while name in used:
            name = f"{'-'.join(_num(s) for s in c['scenes'])}-part{k}"
            k += 1
        used.add(name)
        by_call[c["id"]] = name
        sub = f"{HIGGSFIELD}/{name}"
        (root / sub).mkdir(parents=True, exist_ok=True)
        ins = []

        def pic(tag, frame, given=None):
            src = given if given and Path(given).is_file() else (str(vm / "media" / f"{frame}.png") if frame else None)
            if not src or not Path(src).is_file():
                return None
            f = put(src, sub, f"{key}-{name}-{tag}.png", f"{name} {tag} for Higgsfield")
            ins.append({"tag": tag, "file": f, "is": frame})
            return f
        start = pic("IMAGE-1", c.get("start_frame"), req.get("start") or (
            str(only[c["section_id"]]) if only is not None and not str(c.get("start_frame") or "").endswith("-LAST") else None))
        if not start and c.get("start_frame"):   # a split scene starts on the last frame of the clip before it
            ins.append({"tag": "IMAGE-1", "file": None, "is": by_call.get(re.sub(r"-LAST$", "", c["start_frame"]), c["start_frame"])})
        if c.get("end_frame"):
            pic("IMAGE-2", c["end_frame"], req.get("end"))
        voice = req.get("voice") or (str(vm / "vo" / f"{c['scenes'][0]}.mp3") if c.get("talking") else None)
        if voice and Path(voice).is_file():
            ins.append({"tag": "AUDIO-1", "file": put(voice, sub, f"{key}-{name}-AUDIO-1.mp3", f"{name} voice for Higgsfield"),
                        "is": "the voice line"})
        model = req.get("model") or models.get(c["scenes"][0]) or run.get("clip_model") or c.get("model")
        row = {"name": name, "scenes": c["scenes"], "call": c["id"], "model": _plain_model(model),
               "seconds": req.get("duration") or c.get("duration"), "resolution": req.get("resolution") or c.get("resolution"),
               "ratio": req.get("aspect_ratio") or "9:16", "talks": bool(c.get("talking")),
               "lines": [x.get("text") for x in c.get("lines") or []], "inputs": ins,
               "prompt": req.get("prompt") or c["prompt"], "sent": bool(req)}
        (root / sub / "prompt.md").write_text(hf_prompt_md(row, key))
        rows.append({k: v for k, v in row.items() if k != "prompt"} | {"folder": sub})
    return rows


def hf_prompt_md(row, key):
    def says(i):
        return {"IMAGE-1": "the first frame", "IMAGE-2": "the last frame", "AUDIO-1": "the voice line"}[i["tag"]]
    L = [f"# Higgsfield · {key} · scene {', '.join(_num(s) for s in row['scenes'])}", "",
         f"Remakes this scene's clip in Higgsfield Supercomputer. "
         + ("This is the prompt the video line sent, word for word." if row["sent"] else
            "This is the prompt the video line wrote for it; it was not sent yet."), "",
         "## Settings", "",
         f"- Model: **{row['model']}**",
         f"- {row['ratio']} · {row['resolution'] or '720p'} · {row['seconds']} seconds"]
    L += [f"- **{i['tag']}**: `{Path(i['file']).name}`, {says(i)}" if i["file"] else
          f"- **{i['tag']}**: {says(i)}: the last frame of the `{i['is']}` clip, taken from that clip once it's made"
          for i in row["inputs"]]
    if row["talks"]:
        L.append("- Upload AUDIO-1 with it: the person says that line, lips on the words.")
    L += ["- Upload the pictures in number order, then paste the prompt below exactly. Don't add to it or reword it.",
          "- Make 3 takes and keep the one that matches IMAGE-1 best: same person, same place, the lips on every word.", "",
          "## Prompt", "", "```text", row["prompt"], "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- the words he reads
def _who(r):
    return "talks to camera (use the clip's own sound)" if r["talks"] else "picture over the voice"


def script_md(rec):
    L = [f"# {rec['brief']} · {rec['title']} — the script", "",
         "Every line, in order. A talking scene keeps the sound inside its clip; every other scene runs over its "
         "voice file.", "", "| Scene | Section | Who | Line |", "|---|---|---|---|"]
    for r in rec["scenes"]:
        L.append(f"| {r['n']} | {r['section'] or ''} | {_who(r)} | {r['line'].replace('|', '/')} |")
    return "\n".join(L) + "\n"


def edit_notes_md(rec):
    f, bid = rec["frame"], rec["brief"]
    L = [f"# {bid} · {rec['title']} — edit notes ({rec['key']})", "",
         "## Delivery", "",
         f"- **{f['ratio']}, {f['width']}x{f['height']}, {f['fps']} fps**, H.264 .mp4. No 4:5 or 1:1 version, ever.",
         "- Keep faces, words and the product inside the middle 4:5 area: nothing in the top 15% or the bottom 35% "
         "except the captions, which sit low but clear of the app buttons; nothing in the right 15% (the like and share buttons).",
         "- Sound: music about 18 dB under the voice, a sound effect two frames before its picture, the finished file "
         "around -14 LUFS with peaks under -1 dB.",
         "- Captions at the bottom, headlines at the top. Words never sit on a face or a mouth.", "",
         "## Scene order", "",
         "| # | Clip | Who | Line | Check |", "|---|---|---|---|---|"]
    for r in rec["scenes"]:
        chk = "ready" if r["approved"] else f"**look first:** {r['flag'] or 'not passed by the machine'}"
        L.append(f"| {r['n']} | `{Path(r['clip']).name if r['clip'] else ('the editor makes it' if rec.get('stage') == 'pictures' else 'MISSING')}` | {_who(r)} | "
                 f"{r['line'].replace('|', '/')} | {chk} |")
    L += ["", "A scene marked **look first** did not pass the machine's check. Use it if it looks right to you; if it "
          "doesn't, cut around the bad part as best you can and name the scene when you say the cut is in.", ""]
    if rec["overlays"]:
        L += ["## Words on screen", ""]
        L += [f"- **{o.get('text')}** — {o.get('look') or ''} (with scene {o.get('with') or 'all'})." for o in rec["overlays"]]
        L.append("")
    if rec.get("caption_read"):
        L += ["## Captions", "", rec["caption_read"], "",
              "Write captions exactly as the script spells them (brand and product names, prices, numbers).", ""]
    w = rec.get("wanted") or {}
    if w.get("music") or rec["sfx"]:
        L += ["## Music and sound", ""]
        if w.get("music"):
            L.append(f"- Music: {w['music']}" + (f" File: `{Path(rec['music']['file']).name}`." if rec.get("music") and rec["music"].get("file") else ""))
        for s in rec["sfx"]:
            L.append(f"- {s['scene']}: **{s['cue']}** on \"{s['at']}\"" + (f" (`{Path(s['file']).name}`)" if s.get("file") else ""))
        L.append("")
    L += ["## What must not change", "",
          "- The words: every spoken line and every word on screen, as written.",
          "- The product: the real product as the clips show it. Never redraw, recolour or reshape it.",
          "- The offer and the guarantee, word for word.",
          "- Do not add music, effects, stickers or transitions the brief doesn't ask for.", ""]
    if rec["missing"]:
        L += ["## Not in this package yet", ""] + [f"- {m}" for m in rec["missing"]] + [""]
    return "\n".join(L)


def outputs(rec):
    """The finished videos, named the way both lanes name them: the brief key, then the variation (control, v1 …)."""
    hooks = rec["hooks"] or [{"id": "Control", "text": ""}]
    return [{"id": "control" if i == 0 else f"v{i}", "hook": h, "name": f"{rec['key']}-{'control' if i == 0 else f'v{i}'}.mp4"}
            for i, h in enumerate(hooks)]


def start_md(rec):
    """handoff.md, the Hand-off Standard's eight sections, written for the role so a person or an agent carries it
    out the same way."""
    bid, key, f = rec["brief"], rec["key"], rec["frame"]
    outs = outputs(rec)
    bd = f"briefs/{bid}"
    L = [f"# {key}", "", f"*Video editor hand-off · {rec['brand']} · {rec['date']} · handoff/1*", "",
         "## 1 What this is",
         (f"**{rec['title']}**: the scene pictures the owner approved, one per scene, and each scene's clip prompt word for "
            "word. The clips, the edit, B-roll and effects are the editor's job: make each clip from its picture and prompt "
            f"(`{HIGGSFIELD}/`), then cut the control and its {len(outs) - 1} variations." if rec.get("stage") == "pictures" else
            f"**{rec['title']}**: every scene the video line made for it — a clip, a first and last frame and a voice line "
         "per scene, the whole voice read, the music and sound effects, the brief, the script and the swipe. Cut the "
         f"control and its {len(outs) - 1} variations from it."), "",
         "## 2 Who it's for",
         "The **video editor**: a person in their own editing software, or an agent. The folder is the instruction, so "
         "either does the same job.", "",
         "## 3 What's inside (by id)",
         "| brief | product | brief file | scenes |", "|---|---|---|---|",
         f"| `{bid}` (`{key}`) | `{rec.get('product') or ''}` | `{bd}/brief.md` | {len(rec['scenes'])} |", "",
         f"- `{bd}/edit-notes.md`: every scene in order with its line and its check, the words on screen, the captions, "
         "the music and every sound-effect cue.",
         f"- `{bd}/script.md`: the script, scene by scene." + (f" The brief as a Google Doc: {rec['gdoc']}" if rec.get("gdoc") else ""),
         f"- `assets/clips/`: one clip per scene, in order (`{key}-S01-clip.mp4` …).",
         "- `assets/stills/`: each scene's first and last frame, to check the clips against.",
         f"- `assets/voice/`: each scene's voice line, and the whole read (`{key}-voice-full.mp3`).",
         "- `assets/music-and-sound/`: the music bed and the sound effects the brief calls for.",
         "- `references/`: the swipe, the ad we copied. Match its pace, its cuts and its caption style.",
         f"- `{HIGGSFIELD}/`: one folder per clip, ready for Higgsfield Supercomputer: `prompt.md` with the model, the "
         "settings and the prompt word for word, and the `IMAGE-n` pictures and `AUDIO-1` voice it names. "
         "Use it to remake a scene that looks wrong, or to make a missing opening."]
    if (rec.get("runsheet") or {}).get("files"):
        L.append("- `BRIEF.md`, `RUN.md`, `run.json` and `refs/`: the brief and its run sheet, every clip's model, prompt and "
                 "settings, with every reference file it names inside `refs/`. RUN.md section A is for a person in "
                 "Higgsfield, section B for an agent.")
    L += ["",
         "## 4 What to do",
         f"1. Cut the **control**: every scene in the order `{bd}/edit-notes.md` gives. **{f['ratio']}, {f['width']}x"
         f"{f['height']}, {f['fps']} fps**, H.264 .mp4. Never a 4:5 or 1:1 version.",
         "2. A scene where the person talks to camera keeps the sound inside its clip. Every other scene runs over its "
         "voice line.",
         "3. Words on screen and captions as the edit notes say: captions at the bottom, headlines at the top, never on "
         "a face or a mouth; faces, words and the product inside the middle 4:5 of the frame.",
         "4. Music about 18 dB under the voice, a sound effect two frames before its picture, finish around -14 LUFS.",
         "5. Each variation is the control with only its opening scene and title card swapped:", "",
         "| # | First line | Title card | How to make it |", "|---|---|---|---|"]
    for o in outs:
        h = o["hook"]
        opener = next((r["folder"] for r in rec.get("higgsfield") or [] if h.get("opener_scene") in r["scenes"]),
                      (rec.get("higgsfield") or [{}])[0].get("folder"))
        how = ("the whole ad" if o["id"] == "control" else
               ("the control with this opening" if rec.get("hook_clips") else
                (f"make its opening in Supercomputer from `{opener}/`, changing only what it shows: {h.get('take')}"
                 if opener and h.get("take") else "waits for its opening clip (not made yet)")))
        L.append(f"| {o['id']} | {h.get('text') or ''} | {(h.get('card') or '').replace(' / ', ' · ')} | {how} |")
    L += ["", "A scene marked **look first** in the edit notes did not pass the machine's check. Use it if it looks "
          f"right. If not, remake it in Higgsfield Supercomputer from its folder in `{HIGGSFIELD}/` (upload the "
          "pictures in number order, paste `prompt.md`'s prompt as is); if the remake is still off, cut around the bad "
          "part and name the scene in `returned/`'s note.", "",
          "## 5 What must not change",
          "- **Product**: the real product as the clips show it. Never redrawn, recoloured or reshaped.",
          "- **Words**: every spoken line and every word on screen, exactly as the script writes them.",
          "- **Offer**: the offer and the guarantee, word for word.",
          "- **Names**: every returned file carries the brief key. Nothing added the brief doesn't ask for.", "",
          "## 6 Links",
          "No landing page is set in a video edit; the ad's link is added at upload.", "",
          "## 7 Checks before you're done",
          "1. Every scene is there, in order, and every line is heard whole.",
          "2. Talking scenes are in sync.",
          "3. Words and captions are exactly the script's: names, prices, numbers.",
          "4. Nothing on a face, a mouth, or the app's button areas.",
          "5. Each finished file is named below. Nothing goes live; the owner approves first.", "",
          "## 8 How to send it back",
          f"Save each finished video into **`returned/`** in this folder — on the Drive, `{rec['returned_to']}/`:", ""]
    L += [f"- `{o['name']}`" for o in outs]
    L += ["", f"The brief key ({key}) stays in every name, brand and product in front of the number, because two brands "
          "or products can share a number: that is how the delivery check finds each video's brief and puts it on the "
          "Meta approval page. Save only finished videos there, never the clips in this folder.", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- onto the drive
def to_drive(rec, svc=None, find_engine=None):
    """Copy the folder to the drive at the same path below Shared Assets/, through gdrive-creator with the person's
    own key (builder card rule 4). Returns {"link", "label", "id", "files"}; a missing key is refused by name."""
    folder = _sibling("gdrive-creator")
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    from gdrive_creator import engine as E, reach  # noqa: E402
    E = find_engine() if find_engine else E
    parts = [x for x in rec["place"].split("/")[1:] if x]
    svc = svc or E.service()
    dest = reach.folder_id(parts, svc, make=True, find_engine=lambda: E)
    ids = E.mirror_tree(rec["folder"], dest, svc)
    out = {"id": dest, "label": rec["place"], "link": f"https://drive.google.com/drive/folders/{dest}", "files": ids}
    f = Path(rec["folder"]) / "manifest.json"
    saved = json.loads(f.read_text())
    saved["drive"] = {k: out[k] for k in ("id", "label", "link")}
    f.write_text(json.dumps(saved, indent=1, ensure_ascii=False))
    return out
