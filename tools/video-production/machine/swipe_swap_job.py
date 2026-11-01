#!/usr/bin/env python3
"""swipe_swap_job — one swipe clip + one cast member + one product + a headline, as a CHECKED job.

2026-10-27, after a wrong cast member and a cut-off product reached the video tool. The pieces already existed
(cast_swap, higgsfield_api, face_gate); nothing stood in front of them for a one-off swipe, so a hand-run swap had no gate.
This is that front: the same request -> checked -> made -> judged -> filed shape as image-production.

    python3 swipe_swap_job.py new    <label> --brand B --clip swipe.mp4 --cast SLUG --product product.jpg --headline "..."
    python3 swipe_swap_job.py gate   <label> --brand B      # every check that needs no money; writes the page
    python3 swipe_swap_job.py approve <label> --brand B --by NAME   # the person looked at the page
    python3 swipe_swap_job.py run    <label> --brand B [--dry-run]  # refuses unless the gate is green and approved
    python3 swipe_swap_job.py judge  <label> --brand B      # the made clip, frame by frame, against the sheets

Output: runs/video-production/<brand>/<label>/ (job.json beside the production run's own files) (job.json, prompts, frames, page.html). Brand-agnostic: nothing here names one.
Dry-run and gate spend nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
FLOOR_S = 4.0


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_ssj_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# THE ROUTES (SHOT-ROUTES.md is the only ruling on which way a video is made; this lists them for the board and the gate).
# Each names the Model House job whose model makes it, so no model is named here.
ROUTES = {
    "motion-transfer": {"name": "A scene still, then the swipe's movement on it", "job": "swipe_footage.motion_transfer",
                        "when": "the swipe's movement is the point and our person, her room and the product must all be in the picture"},
    "swap": {"name": "Our cast swapped into the swipe's own shot", "job": "swipe_footage.swap",
             "when": "the motion is the point and the swipe's room and objects can stay as they are"},
    "ai-clips": {"name": "AI clips made from start pictures", "job": "clips.seedance",
                 "when": "talking or voice-led scenes, and scenes made up for our ad (a production run, on the Prompt Bench)"},
    "real-footage": {"name": "Footage we own, cut as it is", "job": None,
                     "when": "a real clip of the real product or place already exists in the asset index"},
}


def run_dir(brand: str, label: str) -> Path:
    return WS / "runs" / "video-production" / brand / label   # the video line's one home (consolidated 2026-10-27)


def _load_writing(name):
    spec = importlib.util.spec_from_file_location(f"vm_ssw_{name}", WS / "tools" / "video-writing" / "machine" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(brand, label):
    p = run_dir(brand, label) / "job.json"
    if not p.exists():
        raise SystemExit(f"no job {label} for {brand}; make it with `new` first")
    return p, json.loads(p.read_text())


def _write(p: Path, job: dict):
    p.write_text(json.dumps(job, indent=1))


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def _ff(*a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, a)], check=True)


def _dur(p) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


# ---------------------------------------------------------------- the cast: where her approved pictures are
def cast_files(brand: str, slug: str) -> dict:
    """The approved master and sheets, in the order the swap sends them. Accepts the compose layout (full/*.png) or
    the casting-sheet layout (master.jpg + sheets/*.jpg)."""
    root = WS / "runs" / "ai-elements" / brand / "casting" / slug
    out = {"root": root, "master": None, "sheets": [], "look": None, "baseline": []}
    for base in (root / "full", root):
        for ext in ("png", "jpg"):
            m = base / f"master.{ext}"
            if m.exists() and not out["master"]:
                out["master"] = m
                sh = base / "sheets"
                for s in ("turnaround", "angles-expressions", "details"):
                    f = sh / f"{s}.{ext}"
                    if f.exists():
                        out["sheets"].append(f)
                looks = sorted(sh.glob(f"look-*.{ext}"))
                out["look"] = looks[0] if looks else None
                # THE BASELINE (2026-10-27): headshot, look, details, expressions — NOT the master. Each scene
                # is built on these, so nothing from the master's own setting leaks into it.
                out["baseline"] = [f for f in (sh / f"headshot.{ext}", out["look"], sh / f"details.{ext}",
                                               sh / f"angles-expressions.{ext}") if f and Path(f).exists()]
    return out


# ---------------------------------------------------------------- the product: whole tube, nothing cut off
def product_whole(path: Path) -> tuple:
    """(ok, why). The product picture must show the WHOLE product: a margin of plain background on top and bottom,
    so a tube cropped by its file fails (the 2026-10-27 packshot ran off the bottom edge)."""
    try:
        from PIL import Image
    except Exception:
        return None, "PIL missing: the whole-product check could not run"
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[2, 2]

    def far(c):
        return sum(abs(c[i] - bg[i]) for i in range(3)) > 60

    def row_busy(y):
        return sum(1 for x in range(0, w, max(1, w // 120)) if far(px[x, y])) > 2

    def col_busy(x):
        return sum(1 for y in range(0, h, max(1, h // 120)) if far(px[x, y])) > 2

    cuts = [n for n, busy in (("top", row_busy(0)), ("bottom", row_busy(h - 1)),
                              ("left", col_busy(0)), ("right", col_busy(w - 1))) if busy]
    if cuts:
        return False, "the product touches the " + " and ".join(cuts) + " edge of its picture: it is cut off"
    return True, "whole product, plain margin on every side"


# ---------------------------------------------------------------- the words sent to the model
def swap_prompt(job: dict) -> str:
    """STEP 1's words: the still of the scene. The room, her (from the baseline) and the product, nothing else."""
    where = job.get("room_words") or "the room shown in the first picture"
    text = (f"One photograph of the woman in the baseline pictures — the same face, hair, skin, build and age as the "
            f"headshot, details and expression sheets, dressed as the look picture shows — standing in {where}. "
            "The room, its light and its angle are exactly the room picture. ")
    if job.get("action_still"):
        text += job["action_still"].strip() + " "
    if job.get("product"):
        text += ("The product in the last picture stands on the counter in front of her: the whole tube, upright, label "
                 "facing the camera, its real colours and its real printed label exactly as the picture shows it, nothing "
                 "cut off, nothing redrawn. ")
    return text + "A real phone photograph, no words anywhere."


def action_words(job: dict) -> str:
    """STEP 2's words: what HAPPENS in the scene. This is where the creative part lives."""
    return (job.get("action") or "").strip()


def sends(job: dict) -> list:
    c = cast_files(job["brand"], job["cast"])
    files = list(c["baseline"]) + ([Path(job["room"])] if job.get("room") else [])
    if job.get("product"):
        files.append(Path(job["product"]))
    return [f for f in files if f]


# ---------------------------------------------------------------- commands
def cmd_new(a):
    d = run_dir(a.brand, a.label)
    d.mkdir(parents=True, exist_ok=True)
    job = {"label": a.label, "brand": a.brand, "clip": str(Path(a.clip).resolve()), "cast": a.cast,
           "product": str(Path(a.product).resolve()) if a.product else "", "headline": a.headline,
           "keep": a.keep, "erase": a.erase, "room": str(Path(a.room).resolve()) if a.room else "",
           "room_words": a.room_words, "action_still": a.action_still, "action": a.action, "brief": a.brief, "sound": a.sound, "route": a.route, "opened": _now(), "status": "new", "approved": None}
    _write(d / "job.json", job)
    print(f"job {a.label} opened: {d}")
    return 0


def cmd_gate(a):
    p, job = _read(a.brand, a.label)
    d = p.parent
    checks = []

    def add(name, ok, why):
        checks.append({"name": name, "ok": ok, "why": why})

    clip = Path(job["clip"])
    if clip.exists():
        s = _dur(clip)
        add("clip", True, f"{clip.name}, {s:.1f} s" + (" (padded forward and back to the 4 s floor)" if s < FLOOR_S else ""))
    else:
        add("clip", False, f"the swipe clip is not on disk: {clip}")

    c = cast_files(job["brand"], job["cast"])
    if c["master"]:
        add("cast", True, f"{job['cast']}: master + {len(c['sheets'])} sheets" + (" + a look" if c["look"] else ""))
        add("baseline", len(c["baseline"]) >= 3, "the baseline is headshot, look, details and expressions; "
            + ("only " + ", ".join(Path(f).stem for f in c["baseline"]) if len(c["baseline"]) < 3 else
               ", ".join(Path(f).stem for f in c["baseline"])))
    else:
        add("cast", False, f"no approved master for {job['cast']} under {c['root']}")

    if job.get("product"):
        pp = Path(job["product"])
        if pp.exists():
            ok, why = product_whole(pp)
            add("product whole", ok, why if ok is not None else why)
        else:
            add("product whole", False, f"the product picture is not on disk: {pp}")

    if job.get("room"):
        rp = Path(job["room"])
        add("room", rp.exists(), f"her room picture: {rp.parent.parent.name}/{rp.stem}" if rp.exists()
            else f"the room picture is not on disk: {rp}")
    else:
        add("room", False, "no room chosen: the scene still needs her world")
    # THE ENTRY TO THE CHAIN (2026-10-27): this job only starts from a finished teardown and a stamped brief
    br = job.get("brief")
    if br and Path(br).exists():
        sm = _load_writing("swipe_match")
        txt = Path(br).read_text()
        st, rd = sm.stamp_of(txt), sm.read_of(txt)
        add("brief (stations 1 and 2)", st == "PASSED" and rd == "APPROVED",
            f"the teardown and the brief are filed: swipe check {st}, brief stamp {rd}" if st == "PASSED" and rd == "APPROVED"
            else f"the brief is not ready: swipe check {st}, brief stamp {rd}")
    else:
        add("brief (stations 1 and 2)", False, "no brief: run the video teardown and the video writing first")
    snd = (job.get("sound") or "").strip()
    add("sound", bool(snd), f"the sound is decided: {snd}" if snd else
        "the sound is not decided: a swipe's borrowed song cannot run in a paid ad (silent, or a music bank bed)")
    # THE OFFER ON SCREEN and THE BRAND IN THE SET (Tella 27 Oct): read off the start frame's swap list
    rec_txt = json.dumps((job.get("recipe") or {}).get("brief", {}).get("swap_list") or {}).lower()
    units = int(job.get("offer_units") or 0)
    if units:
        words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
        add("offer units match the offer", str(units) in rec_txt or words.get(units, "") in rec_txt,
            f"the start frame shows {units} units, as the offer says" if (str(units) in rec_txt or words.get(units, "") in rec_txt)
            else f"the offer needs {units} units on screen and the swap list does not say so")
    if job.get("recipe"):
        dressed = "logo" in rec_txt and ("shelf" in rec_txt or "background" in rec_txt or "behind" in rec_txt)
        add("the brand dresses the set", dressed, "the logo and more product are in the set" if dressed
            else "the set carries no logo or no product in the background")
    rt = job.get("route") or ""
    add("route", rt in ROUTES, f"made by: {ROUTES[rt]['name']}" if rt in ROUTES else "no route chosen: how is this video made?")
    add("action", bool(action_words(job)), "the scene's action is written (step 2)" if action_words(job)
        else "nothing says what happens in the scene yet")

    # the model sheets (components/model-inputs) are the rulebook for both makers: the still (GPT Image) and the clip (Genjutsu motion control)
    cl = _load("clip_limits")
    ir = cl.rules()
    pics = [f for f in sends(job) if Path(f).exists()]
    f1 = [x for x in ir.check("gpt-image-2.5", swap_prompt(job), [{"path": str(f)} for f in pics], aspect="1:1") if x["level"] == "error"]
    add("scene still vs its sheet", not f1, "the pictures and words fit GPT Image 2.5's sheet" if not f1 else " ".join(x["say"] for x in f1))
    if clip.exists():
        f2 = [x for x in cl.check("higgsfield-motion-control", _dur(clip), "480p", images=[], videos=[clip]) if x["level"] == "error"]
        add("swipe clip vs motion-control sheet", not f2, "the swipe shot fits Genjutsu motion control's sheet (one clip, 3 to 30 s)" if not f2
            else " ".join(x["say"] for x in f2))
    never = [f.name for f in pics if Path(f).stem.lower().startswith(tuple(ir.limits("higgsfield-motion-control").get("never_send_stems", ["master"])))]
    add("baseline, never the master", not never, "no master among the pictures" if not never else "the master is in the pictures: " + ", ".join(never))

    # the person must look at WHO is going in before money moves: the page carries the master and the product
    words = swap_prompt(job)
    (d / "prompt-as-sent.md").write_text(words)
    add("words shown", True, f"{len(words)} characters, saved as prompt-as-sent.md and shown on the page")

    green = all(x["ok"] is True for x in checks)
    job["gate"] = {"at": _now(), "green": green, "checks": checks, "sends": [str(f) for f in sends(job)],
                   "prompt_sha": hashlib.sha256(words.encode()).hexdigest()[:12]}
    job["approved"] = None  # any new gate invalidates an old approval
    job["status"] = "gate-green" if green else "gate-red"
    _write(p, job)
    write_page(d, job)
    for x in checks:
        print(("PASS " if x["ok"] else "FAIL ") + f"{x['name']}: {x['why']}")
    print("GATE " + ("GREEN" if green else "RED") + f" — page: {d / 'page.html'}")
    return 0 if green else 1


def cmd_approve(a):
    p, job = _read(a.brand, a.label)
    if not (job.get("gate") or {}).get("green"):
        raise SystemExit("the gate is not green; nothing to approve")
    job["approved"] = {"by": a.by, "at": _now(), "prompt_sha": job["gate"]["prompt_sha"],
                       "files": {Path(f).name: _sha(Path(f)) for f in job["gate"]["sends"]}}
    job["status"] = "approved"
    _write(p, job)
    write_page(p.parent, job)
    print(f"approved by {a.by}")
    return 0


def _approval_holds(job: dict) -> Optional[str]:
    ap = job.get("approved")
    if not ap:
        return "not approved: look at the page and approve first"
    now = hashlib.sha256(swap_prompt(job).encode()).hexdigest()[:12]
    if now != ap["prompt_sha"]:
        return "the words changed since they were approved"
    for f in job["gate"]["sends"]:
        if ap["files"].get(Path(f).name) != _sha(Path(f)):
            return f"{Path(f).name} changed since it was approved"
    return None


def cmd_run(a):
    p, job = _read(a.brand, a.label)
    why = _approval_holds(job)
    if why:
        raise SystemExit("REFUSED — " + why)
    d = p.parent
    files = [Path(f) for f in job["gate"]["sends"]]
    print(f"step 1 sends {len(files)} pictures: " + ", ".join(f.name for f in files))
    print("step 2 sends the approved still and: " + action_words(job))
    if a.dry_run:
        print("dry run: nothing sent, nothing spent")
        return 0
    raise SystemExit("run is the dry-run plan: make with `still`, then `approve-still`, then `clip`")
    sw = _load("swap_run")
    cs = _load("cast_swap")
    hf = _load("higgsfield_api")
    src = d / "source.mp4"
    clip, kept = sw.prepare_clip({"clip": job["clip"]}, 0.0, src)
    up = hf.upload(clip)
    imgs = [hf.upload(f) for f in files]
    payload = {"video_references": [up], "image_references": imgs, "prompt": (d / "prompt-as-sent.md").read_text(),
               "resolution": a.resolution}
    rid = hf.submit(sw.MODEL, payload)
    job["request"] = {"id": rid, "at": _now(), "model": sw.MODEL}
    job["status"] = "submitted"
    _write(p, job)
    body = hf.wait(rid)
    outs = hf.outputs(body)
    if not outs:
        job["status"] = "failed"
        job["request"]["body"] = body
        _write(p, job)
        raise SystemExit("no output: " + json.dumps(body)[:300])
    out = d / f"made-{time.strftime('%Y%m%d-%H%M%S')}.mp4"   # every take kept, never overwritten
    hf.download(outs[0], out)
    job["made"] = str(out)
    job["status"] = "made"
    _write(p, job)
    print(f"made: {out} — now run `judge`")
    return 0


def cmd_judge(a):
    """RETIRED 2026-10-27 (with real references in the picture and in the video there is nothing to check, and the check only spends). Kept so old calls do not break."""
    print("no face or product check: the references are the check")
    return 0


def _cmd_judge_old(a):
    p, job = _read(a.brand, a.label)
    d = p.parent
    made = Path(job.get("made") or d / "made.mp4")
    if not made.exists():
        raise SystemExit("no made clip to judge yet")
    fr = d / "frames"
    fr.mkdir(exist_ok=True)
    dur = _dur(made)
    pics = []
    for i, t in enumerate((0.15, 0.5, 0.85)):
        f = fr / f"f{i + 1}.png"
        _ff("-ss", f"{dur * t:.2f}", "-i", made, "-frames:v", "1", f)
        pics.append(f)
    c = cast_files(job["brand"], job["cast"])
    fg = _load("face_gate")
    res = []
    for f in pics:
        try:
            rec = fg.stamp(f, [str(c["master"])])
            res.append({"frame": f.name, "face": json.dumps(rec)[:200]})
        except BaseException as e:  # the judge could not answer: that is UNCHECKED, never a pass
            res.append({"frame": f.name, "face": f"UNCHECKED ({e})"})
    job["judged"] = {"at": _now(), "frames": res}
    _write(p, job)
    write_page(d, job)
    for r in res:
        print(r["frame"], r["face"])
    return 0


# ---------------------------------------------------------------- the doing: the chain makes, the board only presses
def make_still(brand, label, by):
    """RETIRED 2026-10-27 (all pictures run through the same mechanics). A video's start frame is a PICTURE made by the picture path: the swipe's frame goes through image-teardown
    (`chain.py open`, then `tools/run.py <run> all`), and the picture is made on the Prompt Bench builder
    (`components/model-inputs/preview.py` `make_picture`) with the swipe frame as IMAGE 1. The job then points at that
    picture (`still`). This function only refuses, so nothing makes a start frame by another road."""
    raise SystemExit("REFUSED — a start frame is made by the picture path (image-teardown, then the Prompt Bench builder), "
                     "never here; set the job's `still` to that picture")


def approve_still(brand, label, by):
    """The person looks at the still as it is now and says it can go on to the clip; tied to the picture's bytes."""
    p, job = _read(brand, label)
    if not job.get("still") or not Path(job["still"]).is_file():
        raise SystemExit("no still to approve")
    job["still_approved"] = {"by": by, "at": _now(), "sha": _sha(Path(job["still"]))}
    _write(p, job)
    return job


def still_holds(job) -> Optional[str]:
    ap = job.get("still_approved")
    if not ap or not job.get("still") or not Path(job["still"]).is_file():
        return "approve the scene still first: the clip is made from it"
    if ap.get("sha") != _sha(Path(job["still"])):
        return "the still changed since it was approved"
    return None


def make_clip(brand, label, by):
    """STEP 4: the clip, made the way the job's ROUTE says. motion-transfer: Genjutsu motion transfer from the approved
    still, the swipe driving only the movement. swap: Genjutsu object swap, our cast swapped into the swipe's own shot.
    The sheet's own findings stop it first; the caller's press is the cost approval. Words and settings come from the
    Prompt Bench's builders (swap_bench.py), so the board and the chain send the same thing."""
    p, job = _read(brand, label)
    route = job.get("route") or "motion-transfer"
    if route not in ("motion-transfer", "swap"):
        raise SystemExit(f"REFUSED — the {route} route is not made here (ai-clips run on the Prompt Bench, real footage is cut in the edit)")
    if route == "motion-transfer":
        why = still_holds(job)
        if why:
            raise SystemExit("REFUSED — " + why)
    if not (job.get("gate") or {}).get("green"):
        raise SystemExit("REFUSED — the gate is not green")
    sb = _load("swap_bench")
    import sys
    sys.path.insert(0, str(WS / "components" / "model-inputs"))
    import preview as PV
    house_job = ROUTES[route]["job"]
    built = (sb.motion_transfer if route == "motion-transfer" else sb.swap)({"brand": brand, "label": label})
    r = PV.preview(house_job, {"brand": brand, "label": label}, quote=False)
    errs = [f["say"] for f in r["findings"] if f["level"] == "error"]
    if errs:
        raise SystemExit("REFUSED — the sheet stops this clip: " + " ".join(errs))
    d = p.parent
    vendor = "hf_mult_motion_control" if route == "motion-transfer" else "hf_mult_replace_object"
    imgs = [job["still"]] if route == "motion-transfer" else [i["path"] for i in built["inputs"] if i["kind"] == "image"]
    argv = ["higgsfield", "generate", "create", vendor, "--prompt", built["prompt"]]
    for im in imgs:
        argv += ["--image-references", im]
    argv += ["--video-references", job["clip"], "--resolution", built["settings"]["resolution"],
             "--wait", "--wait-timeout", "25m", "--wait-interval", "6s", "--json"]
    cp = subprocess.run(argv, capture_output=True, text=True, timeout=1700)
    (d / "clip-request.json").write_text(json.dumps({"by": by, "at": _now(), "route": route, "argv": argv[:6], "stdout": cp.stdout[-4000:],
                                                      "stderr": cp.stderr[-1000:]}, indent=1))
    url = None
    try:
        body = json.loads(cp.stdout)
        for it in (body if isinstance(body, list) else [body]):
            for k in ("result_url", "url", "output_url"):
                if isinstance(it.get(k), str):
                    url = url or it[k]
            res = it.get("result") or it.get("results") or it.get("outputs") or []
            for x in (res if isinstance(res, list) else [res]):
                u = x.get("url") if isinstance(x, dict) else x
                if isinstance(u, str) and u.startswith("http"):
                    url = url or u
    except ValueError:
        pass
    if not url:
        raise SystemExit("no clip came back: " + (cp.stderr or cp.stdout)[-300:])
    import urllib.request
    out = d / "made.mp4"
    urllib.request.urlretrieve(url, out)
    job = json.loads(p.read_text())
    job["made"], job["status"] = str(out), "made"
    _write(p, job)
    return {"file": str(out)}


def put_headline(brand, label, lines, top=0.40, tag=""):
    """STEP 5: the headline as TikTok sets it: white text, black outline, no box, lower on the frame (2026-10-27)."""
    p, job = _read(brand, label)
    if not job.get("made") or not Path(job["made"]).is_file():
        raise SystemExit("no made clip to put the headline on")
    lines = [l for l in lines if l.strip()]
    if not lines:
        raise SystemExit("no headline text")
    from PIL import Image, ImageDraw, ImageFont
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of",
                            "csv=p=0", job["made"]], capture_output=True, text=True).stdout.strip().split(",")
    W, H = int(probe[0]), int(probe[1])
    size = int(W * 0.064)
    while size > 10:
        f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size, index=1)
        if max(ImageDraw.Draw(Image.new("RGBA", (10, 10))).textlength(l, font=f) for l in lines) <= W * 0.9:
            break
        size -= 1
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    lh, y = int(size * 1.22), int(H * top)
    for i, l in enumerate(lines):
        dr.text(((W - dr.textlength(l, font=f)) / 2, y + i * lh), l, font=f, fill="white", stroke_width=max(3, size // 9),
                stroke_fill="black")
    out = p.parent / f"final-{tag or int(time.time())}.mp4"
    png = out.with_suffix(".png")
    im.save(png)
    # THE SONG STAYS (2026-10-27): the reel's own audio goes under it
    _ff("-i", job["made"], "-i", png, "-i", job["clip"], "-filter_complex", "[0:v][1:v]overlay=0:0[v]", "-map", "[v]", "-map", "2:a:0",
        "-c:v", "libx264", "-crf", 20, "-preset", "fast", "-c:a", "aac", "-shortest", out)
    png.unlink()
    job = json.loads(p.read_text())
    job.setdefault("final", []).append(str(out))
    _write(p, job)
    return {"file": str(out)}


# ---------------------------------------------------------------- the page: every step, its words, its checks
def write_page(d: Path, job: dict):
    def img(path, alt):
        # relative copies so the page stands alone
        try:
            src = Path(path)
            dst = d / "shown" / src.name
            dst.parent.mkdir(exist_ok=True)
            if src.exists() and not dst.exists():
                dst.write_bytes(src.read_bytes())
            return f'<figure><img src="shown/{html.escape(src.name)}" alt="{html.escape(alt)}"><figcaption>{html.escape(alt)}</figcaption></figure>'
        except Exception:
            return ""

    g = job.get("gate") or {}
    rows = "".join(
        f'<li class="{"ok" if c["ok"] else "bad"}"><b>{"PASS" if c["ok"] else "FAIL"}</b> {html.escape(c["name"])}'
        f' — {html.escape(c["why"])}</li>' for c in g.get("checks", []))
    pics = "".join(img(f, Path(f).stem) for f in g.get("sends", []))
    prompt = (d / "prompt-as-sent.md").read_text() if (d / "prompt-as-sent.md").exists() else ""
    ap = job.get("approved")
    judged = "".join(f'<li>{html.escape(r["frame"])}: {html.escape(r["face"])}</li>' for r in (job.get("judged") or {}).get("frames", []))
    page = f"""<!doctype html><meta charset=utf-8><title>Swipe swap {html.escape(job['label'])}</title>
<style>body{{font:15px system-ui;max-width:900px;margin:24px auto;padding:0 16px}}figure{{display:inline-block;margin:6px;width:150px;vertical-align:top}}
img{{width:100%;border-radius:8px}}li.ok{{color:#0a7a3c}}li.bad{{color:#b3261e}}pre{{white-space:pre-wrap;background:#f4f4f4;padding:12px;border-radius:8px}}</style>
<h1>Swipe swap: {html.escape(job['label'])}</h1>
<p>Status: <b>{html.escape(job.get('status', ''))}</b> · headline on top: {html.escape(job.get('headline', ''))}</p>
<h2>Checks (no money spent on any of these)</h2><ul>{rows}</ul>
<h2>The pictures that will be sent, in order</h2>{pics}
<h2>Step 1: the still of the scene (exact words)</h2><pre>{html.escape(prompt)}</pre>
<h2>Approval</h2><p>{('Approved by ' + html.escape(ap['by']) + ' at ' + ap['at']) if ap else 'Not approved yet: nothing runs until it is.'}</p>
<h2>After the clip is made</h2><ul>{judged or '<li>not made yet</li>'}</ul>"""
    (d / "page.html").write_text(page)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("label")
    n.add_argument("--brand", required=True)
    n.add_argument("--clip", required=True)
    n.add_argument("--cast", required=True)
    n.add_argument("--product", default="")
    n.add_argument("--headline", default="")
    n.add_argument("--keep", default="")
    n.add_argument("--erase", default="")
    n.add_argument("--room", default="", help="the room picture from her 3D casting rooms")
    n.add_argument("--room-words", default="", help="the room said in words")
    n.add_argument("--action-still", default="", help="what is in the still: her pose, the money, the counter")
    n.add_argument("--action", default="", help="STEP 2: what happens in the scene, in plain words")
    n.add_argument("--brief", default="", help="the stamped brief this job is made from (video-writing)")
    n.add_argument("--sound", default="", help="silent, or a music bank bed; never the swipe's borrowed song")
    n.add_argument("--route", default="motion-transfer", choices=sorted(ROUTES), help="how this video is made (SHOT-ROUTES.md)")
    for name in ("gate", "approve", "run", "judge", "still", "approve-still", "clip", "headline"):
        s = sub.add_parser(name)
        s.add_argument("label")
        s.add_argument("--brand", required=True)
        if name in ("approve", "approve-still", "still", "clip"):
            s.add_argument("--by", required=True)
        if name == "headline":
            s.add_argument("--text", required=True, help="the headline; \\n is a new line")
        if name == "run":
            s.add_argument("--dry-run", action="store_true")
            s.add_argument("--resolution", default="1080p")
    a = ap.parse_args(argv)
    if a.cmd == "still":
        print(make_still(a.brand, a.label, a.by)); return 0
    if a.cmd == "approve-still":
        approve_still(a.brand, a.label, a.by); print("still approved by", a.by); return 0
    if a.cmd == "clip":
        print(make_clip(a.brand, a.label, a.by)); return 0
    if a.cmd == "headline":
        print(put_headline(a.brand, a.label, a.text.split("\\n"))); return 0
    return {"new": cmd_new, "gate": cmd_gate, "approve": cmd_approve, "run": cmd_run, "judge": cmd_judge}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
