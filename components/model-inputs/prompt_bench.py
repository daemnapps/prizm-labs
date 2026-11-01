"""The Prompt Bench's server half: the Picture Bench (image-production/bench/serve.py) routes /prompt* here.

    GET  /prompt              the page (prompt_bench.html)
    GET  /api/prompt-options  real picture briefs and video runs, each with its thumbnail
    POST /api/prompt-preview  {"job", "brief"} -> preview.preview(...)  (a free quote; nothing is made or spent)
    POST /api/prompt-make     {"brief"} -> makes ONE picture from exactly what the preview shows (a person's click)
    GET  /api/prompt-job?id=  where that picture is
    POST /api/prompt-delivery       {"brand"} -> image-edit delivery.check: everyone's new deliveries, matched to briefs, filed
    POST /api/prompt-delivery-card  {"brand", "label"} -> image-edit delivery.send: that delivery onto one approval card
    POST /api/prompt-handoff        {"run", "brand", "kind"} -> image-edit handoff.py: the brief packaged for its maker, on the Drive
    GET  /api/prompt-handoff?run=&kind=  that brief's handoff link, either lane

Make runs the preflight first and refuses on a rulebook error; then one image_production.plain.make call with the
previewed text, references and product, the same call the static chain sends. Pictures land in
runs/image-production/<brand>/prompt-bench/. Python 3.9.
"""
import json
import re
import threading
import time
from pathlib import Path

import preview as PV

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

# THE BOARD NEVER RUNS STALE CODE (2026-10-27): the server is started once and runs for days, so a fix to the picture
# builder, the picture engine or the writing tools reached it only on a restart. A BRAND-A picture came out with no words
# because the running board still looked for a file the image-writing split had moved. Every route asks fresh() first:
# when any of those files changed since they were loaded, they are loaded again.
WATCH = [HERE, REPO / "tools/image-production/image_production", REPO / "tools/image-teardown/tools",
         REPO / "tools/image-writing/tools", REPO / "components/generative-model-house"]
_LOADED = [0.0]


def _newest():
    m = 0.0
    for d in WATCH:
        for f in d.glob("*.py"):
            try:
                m = max(m, f.stat().st_mtime)
            except OSError:
                pass
    return m


def fresh():
    global PV
    m = _newest()
    if m <= _LOADED[0]:
        return
    import importlib
    import sys
    for name in list(sys.modules):
        if name in ("preview", "input_rules") or name.startswith("image_production") or name.startswith("it_") or name.startswith("image_edit_model_inputs"):
            sys.modules.pop(name, None)
    PV = importlib.import_module("preview")
    _LOADED[0] = m


_LOADED[0] = _newest()
class _Jobs(dict):
    """Jobs the board started. A job that runs in its own process (board_job.py) carries `status_file`; its state is
    read from that file, so it is right after a board restart too."""
    def get(self, k, d=None):
        v = super().get(k, d)
        if v is None:
            import hashlib
            key_file = JOB_DIR / "keys" / (hashlib.sha256(str(k).encode()).hexdigest() + ".json")
            if key_file.is_file():
                v = _read_json(key_file)
        if isinstance(v, dict) and v.get("status_file"):
            try:
                status_path = Path(v["status_file"])
                status_path = status_path if status_path.is_absolute() else REPO / status_path
                got = json.loads(status_path.read_text())
            except (OSError, ValueError):
                return v
            if got.get("state") == "running" and v.get("running_as"):
                got["state"] = v["running_as"]
            elif got.get("state") == "done" and v.get("done_as"):
                got["state"] = v["done_as"]
            return {**v, **got}
        return v


JOBS, LOCK = _Jobs(), threading.Lock()
JOB_DIR = REPO / "runs" / "prompt-bench" / "jobs"


def _spawn(fn, args, jid=None, shot_key=None, running_as=None, done_as=None):
    """Start one job in ITS OWN PROCESS (board_job.py): the board only starts it and reads its status file, so a board
    restart never kills a make, a keep or a remake (2026-10-28)."""
    import subprocess
    import sys
    jid = jid or f"m{int(time.time() * 1000)}"
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    st = JOB_DIR / f"{jid}.json"
    st.write_text(json.dumps({"state": "running", "started": time.time(), "fn": fn}))
    entry = {"state": "running", "started": time.time(), "status_file": str(st)}
    with LOCK:
        JOBS[jid] = dict(entry)
        if shot_key:
            SHOT_JOBS[shot_key] = {**entry, "running_as": running_as, "done_as": done_as}
            import hashlib
            key_dir = JOB_DIR / "keys"
            key_dir.mkdir(exist_ok=True)
            (key_dir / (hashlib.sha256(shot_key.encode()).hexdigest() + ".json")).write_text(json.dumps(
                {**SHOT_JOBS[shot_key], "status_file": str(st.relative_to(REPO))}))
    subprocess.Popen([sys.executable, str(HERE / "board_job.py"), str(st), fn, json.dumps(args, default=str)],
                     cwd=str(REPO), start_new_session=True, stdout=subprocess.DEVNULL,
                     stderr=open(JOB_DIR / f"{jid}.log", "a"))
    return jid


def _title(lane, run, brand):
    """A plain name: the brief's own title ("# BRIEF · Brand · Product · <title>"), else the run name in words."""
    bf = lane / "out" / "06-brief.md"
    if bf.is_file():
        head = next((l for l in bf.read_text().splitlines() if l.startswith("# BRIEF")), "")
        if "·" in head:
            return head.split("·")[-1].strip()
    return _short(run, brand).capitalize()


def _made(brand, run):
    a = list((REPO / "runs" / "image-teardown" / brand / run / "pictures").glob("*.png"))
    b = list((REPO / "runs" / "image-production" / brand / "prompt-bench").glob(f"{run}-*.png"))
    return len(a) + len(b)


def _short(run, brand):
    s = re.sub(r"^" + re.escape(brand) + r"-(batch-)?", "", run)
    s = re.sub(r"-[0-9a-f]{6,8}$", "", s)
    return s.replace("-", " ")


def _product_of(brief_md, kits, aliases=None):
    """The product kit the brief names in its title line, if any."""
    head = next((l for l in brief_md.splitlines() if l.startswith("# BRIEF")), "").lower()
    words = set(re.findall(r"[a-z0-9]+", head))
    whole = [k for k in kits if set(k.split("-")) <= words]  # "FLEX™ Pro Vibrating Face Brush" names flex-face-brush
    if whole:
        return max(whole, key=lambda k: len(k.split("-")))
    parts = [x.strip() for x in head.split("·")]
    named = set(re.findall(r"[a-z0-9]+", parts[2])) if len(parts) > 3 else set()   # "# BRIEF · BRAND-A · FLEX · <title>"
    by_alias = [k for k in kits if named & set(aliases.get(k) or [])]
    return by_alias[0] if len(by_alias) == 1 else ""


READY = {}                                                   # (brand, run, product) -> (signature, answer)


def _signature(lane):
    """What the readiness answer depends on: the run's brief files, its swap list, and the sheet and builder themselves."""
    files = [f for d in ("out", "vars", "assets") for f in (lane / d).glob("*") if f.is_file()]
    files += [PV.SHEET_FILE, PV.PICTURE_DIALS, HERE / "preview.py"]
    return max((f.stat().st_mtime for f in files if f.exists()), default=0), len(files)


def readiness(brand, run, product):
    """Ready or not, from the sheet gate without the cost approval or a cost quote (PSH-1 (inputs all set)):
    {"ready", "missing": count, "first": the first missing item's plain name}. Cached until the run's files change."""
    lane = PV._teardown_run(REPO, run, brand)
    key, sig = (brand, run, product), _signature(lane)
    hit = READY.get(key)
    if hit and hit[0] == sig:
        return hit[1]
    try:
        probs = PV.validate(PV.fill_defaults({"brief": {"brand": brand, "run": run, "product": product}}), for_make=False)
        names = list(dict.fromkeys(x["name"] for x in probs))
        ans = {"ready": not names, "missing": len(names), "first": names[0] if names else ""}
    except Exception as e:                                   # noqa: BLE001  a brief that cannot be read is not ready
        ans = {"ready": False, "missing": 1, "first": "the brief could not be read (" + type(e).__name__ + ")"}
    READY[key] = (sig, ans)
    return ans


_ETHN = ("white American", "African American", "Black", "Thai", "Korean", "Japanese", "Chinese", "Filipino", "Vietnamese",
         "Indian", "Latina", "Latino", "Mexican", "Middle Eastern", "Arab", "white", "Caucasian", "Asian")


def _read_person(text):
    """Age, sex and ethnicity as the person's own description says them; blank when it does not say. Never guessed."""
    t = " ".join(str(text or "").split())
    m = re.search(r"(?i)\bage:\s*(?:about\s*)?(\d{2})|\babout (\d{2}|\w+-\w+)\b|\b(\d{2})-year-old|\bin (?:her|his) "
                  r"((?:early |mid-|late )?(?:\d{2}s|\w+ies))|\b((?:early|mid|late)[- ]\w+ies)|\b(\d{2})s\b", t)
    age = next((g for g in (m.groups() if m else ()) if g), "")
    sex = "woman" if re.search(r"(?i)\b(woman|grandmother|grandma|mother|she)\b", t) else \
          "man" if re.search(r"(?i)\b(man|grandfather|father|he)\b", t) else ""
    eth = next((e for e in _ETHN if re.search((r"\b" if e[0].isupper() and e not in ("white",) else r"(?i)\b") + re.escape(e) + r"\b", t)), "")
    return age, sex, eth


def _castable(brand):
    """Who the chains can cast: the brand's roster and authority records, by id, with the avatar each serves."""
    out = {}
    for f in ("roster.json", "authority.json"):
        p = REPO / "brands" / brand / "ai-elements" / "characters" / "casting" / f
        try:
            for x in json.loads(p.read_text()).get("people") or []:
                if isinstance(x, dict) and x.get("id"):
                    out[x["id"]] = x
        except (OSError, ValueError):
            pass
    return out


def cast_list():
    """Every cast member per brand with a master photo, grouped by the avatar they serve: what the description says
    (age, sex, ethnicity) and whether they are WORKING (on the brand's roster or authority list, so a chain can cast them,
    with their sheets made). runs/ai-elements/<brand>/casting."""
    out = {}
    for b in sorted((REPO / "runs" / "ai-elements").glob("*")):
        rec = _castable(b.name)
        for d in sorted((b / "casting").glob("*")):
            if d.name.startswith("_") or d.is_symlink() or not (d / "master.jpg").is_file():
                continue
            name = d.name.replace("-", " ").title()
            folder_name = name
            try:
                name = json.loads((d / "spec.json").read_text()).get("name") or name
            except (ValueError, OSError):
                pass
            label = f"{name} · {folder_name}" if folder_name.lower() not in str(name).lower() else str(name)
            r = rec.get(d.name) or {}
            ch = (d / "character.md").read_text() if (d / "character.md").is_file() else ""
            idm = re.search(r"## Identity block[^\n]*\n>\s*([^\n]+)", ch)          # the paste-ready line: who she is, in one line
            age, sex, eth = _read_person(idm.group(1) if idm else str(r.get("reads") or ""))
            sheets = (d / "sheets").is_dir() and any((d / "sheets").glob("headshot.*")) or any((d / "sheets").glob("turnaround.*"))
            # a person with casting sheets can be cast (2026-10-27, on BRAND-A's cast all marked "not on the brand's
            # cast list": that list was emptied on 2026-09-29 and everyone since was built with sheets, never added back)
            working = bool(sheets)
            why = "" if working else "sheets not made"
            out.setdefault(b.name, []).append({"id": d.name, "name": str(name), "label": label, "thumb": str(d / "master.jpg"),
                                               "avatar": str(r.get("lane") or r.get("avatar") or "no avatar yet"),
                                               "role": str(r.get("role") or ""), "age": age, "sex": sex, "ethnicity": eth,
                                               "working": working, "why": why})
    for v in out.values():
        v.sort(key=lambda c: (not c["working"], c["avatar"], c["name"]))
    return out


def anatomy():
    """What the winning swipes do, per dial and per label (runs/ad-anatomy/scoreboard.json, built by ad_anatomy.py); {} until
    it is built. The per-swipe rows stay on disk."""
    p = REPO / "runs" / "ad-anatomy" / "scoreboard.json"
    try:
        d = json.loads(p.read_text())
    except (ValueError, OSError):
        return {}
    return {k: v for k, v in d.items() if k != "per_swipe"}


_SWAP_JOB = {"motion-transfer": "swipe_footage.motion_transfer", "swap": "swipe_footage.swap"}


# THE BOARD READS THE QUEUE (2026-10-27). The Queue writes runs/queue/brief-index.json every minute; each card takes its stage from there by brief
# number (or by a run label the Queue knows it under). In Meta (launch: approved and uploaded; live) leaves the board.
STAGE_WORDS = {"idea": "Idea", "brief": "Brief written", "brief-needs-you": "Brief waiting on you", "making": "Being made",
               "editing": "Being edited", "final-needs-you": "Made, waiting on your OK", "launch": "In Meta", "live": "Live"}
IN_META = ("launch", "live")


def _queue():
    try:
        recs = json.loads((REPO / "runs" / "queue" / "brief-index.json").read_text()).get("briefs") or {}
    except (OSError, ValueError):
        return {}, {}
    by_label = {(r.get("brand"), l): r for r in recs.values() for l in r.get("labels") or []}
    return recs, by_label


def _queue_stage(brand, run, recs, by_label):
    """(brief number, queue stage) for one picture run, from its filed record's brief number, else a Queue run label."""
    try:
        num = json.loads((REPO / "runs" / "image-teardown" / brand / run / "run.json").read_text()).get("brief") or ""
    except (OSError, ValueError):
        num = ""
    m = re.search(r"(\d{4})", str(num))
    rec = recs.get(f"{brand}/{m.group(1)}") if m else None
    rec = rec or by_label.get((brand, run))
    return (m.group(1) if m else (rec or {}).get("brief_id") or ""), (rec or {}).get("stage") or ""


def _is_review(lane, run):
    """A real customer review handed in as the swipe (2026-10-26, "a swipe of a real customer review i had"): its words
    are the customer's, never invented (2026-10-27)."""
    try:
        block = json.loads((lane / "assets" / "source.json").read_text()).get("block") or ""
    except (OSError, ValueError):
        block = ""
    return block.startswith("review-") or "-review-" in run


def options():
    fresh()
    recs, by_label = _queue()
    prods = {}
    for b in sorted((REPO / "runs" / "ai-elements").glob("*")):
        prods[b.name] = sorted(k.name for k in (b / "products").glob("*") if (k / "kit.json").is_file())
    aliases = {}
    for b, slugs in prods.items():
        for k in slugs:
            try:
                aliases[k] = [str(x).lower() for x in json.loads((REPO / "runs" / "ai-elements" / b / "products" / k / "kit.json").read_text()).get("aliases") or []]
            except ValueError:
                pass
    pics = []
    for b in sorted((REPO / "runs" / "image-teardown").glob("*")):
        if b.name.startswith("_") or not b.is_dir():
            continue
        for r in b.glob("*"):
            lane = PV._teardown_run(REPO, r.name, b.name)   # the run works in its record folder since 2026-10-28
            if not (lane / "out" / "03-injection.md").is_file():
                continue
            src = next((p for p in (lane / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
            bf = lane / "out" / "06-brief.md"
            num, stage = _queue_stage(b.name, r.name, recs, by_label)
            if stage in IN_META:
                continue
            made = _made(b.name, r.name) or int(stage in ("making", "editing", "final-needs-you"))
            product = _product_of(bf.read_text() if bf.is_file() else "", prods.get(b.name, []), aliases)
            if not product:      # no brief yet (it is written after the first picture, 2026-10-27): the swaps record's kit
                try:
                    kit = json.loads((lane / "out" / "swaps.json").read_text()).get("product_kit")
                    product = kit if kit in prods.get(b.name, []) else product
                except (OSError, ValueError):
                    pass
            pics.append({"brand": b.name, "run": r.name, "name": _title(lane, r.name, b.name), "made": made,
                         "brief": num, "stage": STAGE_WORDS.get(stage, ""), "review": _is_review(lane, r.name),
                         "thumb": str(src) if src else "", "product": product,
                         "t": (lane / "out" / "03-injection.md").stat().st_mtime})
            pics[-1].update(readiness(b.name, r.name, pics[-1]["product"]))
    pics.sort(key=lambda x: -x["t"])
    vids = []
    for b in sorted((REPO / "runs" / "video-production").glob("*")):
        if b.name.startswith("_") or not b.is_dir():
            continue
        candidates = list(b.glob("*"))
        # Opening batches are production runs too. Only indexed, active batches
        # belong on the board; held experiments stay out of the picker.
        for index in b.glob("*/*/index.json"):
            batch = _read_json(index)
            if not isinstance(batch, dict):
                continue
            if "held" in str(batch.get("state", batch.get("status", ""))):
                continue
            for opening in batch.get("openings") or []:
                ident = str(opening.get("id") or "")
                if re.fullmatch(r"h\d+", ident):
                    candidates.append(index.parent / ident)
        for r in candidates:
            if not ((r / "plan.json").is_file() and (r / "storyboard.json").is_file()) or re.search(r"dryrun|dry-run|batchtest", r.name):
                continue
            th = next(iter(sorted((r / "media").glob("S*-F1.png"))), None)
            made = (r / "clips" / "calls").is_dir() or any((r / "prompt-bench").glob("*.mp4"))
            vids.append({"brand": b.name, "run": str(r.relative_to(b.parent)), "name": PV._video_title(r), "made": int(made),
                         "thumb": str(th) if th else "", "t": (r / "plan.json").stat().st_mtime})
    for jf in (REPO / "runs" / "video-production").glob("*/*/job.json"):  # a video made from a swipe (Genjutsu), same four steps
        try:
            jb = json.loads(jf.read_text())
        except ValueError:
            continue
        if not (jb.get("gate") or {}).get("green"):
            continue
        frame = jf.parent / "swipe-frame.jpg"
        vids.append({"brand": jf.parent.parent.name, "run": f"swap:{jf.parent.parent.name}/{jf.parent.name}",
                     "name": jb.get("title") or jf.parent.name.replace("-", " ").capitalize(),
                     "job": _SWAP_JOB.get(jb.get("route") or "motion-transfer", "swipe_footage.motion_transfer"),
                     "made": int(bool(jb.get("made"))), "thumb": jb.get("still") or (str(frame) if frame.is_file() else ""),
                     "t": jf.stat().st_mtime})
    vids.sort(key=lambda x: -x["t"])
    swaps = []                                              # the Genjutsu jobs (video-production machine/swipe_swap_job.py)
    for jf in sorted((REPO / "runs" / "video-production").glob("*/*/job.json"), key=lambda f: -f.stat().st_mtime):
        try:
            jb = json.loads(jf.read_text())
        except ValueError:
            continue
        swaps.append({"brand": jf.parent.parent.name, "label": jf.parent.name, "cast": jb.get("cast"), "state": jb.get("status"),
                      "gate": bool((jb.get("gate") or {}).get("green")), "headline": jb.get("headline") or ""})
    c = PV.controls()
    image = [d for d in c["dials"] if "image" in d["media"]]
    send = {k: v.get("send", "writing") for k, v in PV.picture_dials()["dials"].items()}
    return {"pictures": pics, "products": prods, "videos": vids, "swaps": swaps, "kit": kit_pictures(prods), "cast": cast_list(),
            "anatomy": anatomy(), "dial_send": send, "deliverers": _deliverers(),
            "designer": next((x["name"] for x in _deliverers() if x["delivers"] == "pictures"), "the designer"),
            "controls": {"dials": [{k: d.get(k) for k in ("id", "name", "what", "image", "scale")} for d in image],
                         "presets": [{k: p.get(k) for k in ("id", "name", "what", "levels")} for p in c["presets"]],
                         "emotions": [{k: e.get(k) for k in ("id", "name", "what")} for e in c["emotions"]],
                         "techniques": [{k: x.get(k) for k in ("id", "name", "what", "family")} for x in c["techniques"]],
                         "guards": [{k: g.get(k) for k in ("id", "name", "what")} for g in c["guards"]]}}


def recipes_dir(brand):
    return REPO / "runs" / "image-production" / brand / "prompt-bench" / "recipes"


def save_recipe(body):
    """A named recipe: everything the bench holds for one picture, replayable by the chain
    (python3 components/model-inputs/preview.py pictures.generate <recipe.json>)."""
    brief = body.get("brief") or {}
    name = re.sub(r"[^a-z0-9-]+", "-", str(body.get("name") or "").lower()).strip("-")
    if not (brief.get("brand") and brief.get("run") and name):
        return 400, {"error": "give the recipe a name"}
    d = recipes_dir(brief["brand"])
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{name}.json"
    if f.exists():
        return 400, {"error": "a recipe with that name already exists; pick another name"}
    rec = {"name": body.get("name"), "brief": brief, "variation_of": body.get("variation_of"), "changed": body.get("changed"),
           "saved": time.strftime("%Y-%m-%dT%H:%M:%S")}
    f.write_text(json.dumps(rec, indent=1))
    return 200, {"path": str(f)}


def recipes(brand, run=None):
    d = recipes_dir(brand)
    out = []
    for f in sorted(d.glob("*.json"), key=lambda x: -x.stat().st_mtime) if d.is_dir() else []:
        r = json.loads(f.read_text())
        if run in (None, r["brief"].get("run")):
            out.append({**r, "file": f.name})
    return out


def kit_pictures(prods):
    """Every real product photo in each brand's kits, for 'Add a picture'."""
    out = {}
    for brand, slugs in prods.items():
        rows = []
        for slug in slugs:
            kit = REPO / "runs" / "ai-elements" / brand / "products" / slug
            for f in sorted(kit.glob("model/reference-*.png")) + sorted(kit.glob("refs/*.png")) + sorted(kit.glob("refs/*.jpg")):
                rows.append({"path": str(f), "label": f"{slug.replace('-', ' ')}, {f.stem.replace('reference-', '').replace('-', ' ')}"})
        out[brand] = rows[:60]
    return out


def upload(body):
    fresh()
    """A picture a person adds from their own files: saved once under runs/image-production/_bench-uploads/."""
    import base64
    d = REPO / "runs" / "image-production" / "_bench-uploads"
    d.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]", "-", Path(body.get("name") or "picture.png").name)
    if Path(name).suffix.lower() not in (".png", ".jpg", ".jpeg"):
        return 400, {"error": "Only png or jpg pictures can be added."}
    f = d / f"{int(time.time() * 1000)}-{name}"
    f.write_bytes(base64.b64decode(str(body.get("data") or "").split(",", 1)[-1]))
    return 200, {"path": str(f)}


def looks_good(body):
    fresh()
    """'Looks good': an optional note beside the picture. It is not a gate: the chosen record is the recipe
    (PSH-5 (chosen references))."""
    f = Path(body.get("file") or "")
    if not (f.is_file() and (REPO / "runs") in f.parents):
        return 400, {"error": "no such picture"}
    f.with_suffix(".liked.json").write_text(json.dumps({"liked": time.strftime("%Y-%m-%dT%H:%M:%S"), "brief": body.get("brief")}, indent=1))
    return 200, {"ok": True}


def preview(body):
    fresh()
    job, brief = body.get("job") or "pictures.generate", body.get("brief") or {}
    try:
        r = PV.preview(job, brief, quote=bool(body.get("quote", True)))
        r.pop("send", None)
        r["can_make"] = PV._house().model(job).get("door") is not None and job.startswith("pictures.")
        return 200, r
    except (KeyError, ValueError, OSError) as e:
        return 400, {"error": str(e)[:400]}


def _make_clip(jid, brief):
    """The clip Make button: the press is the cost approval (CSH-5 (no spend unpressed)); make_clip gates first."""
    j = JOBS[jid]
    try:
        got = PV.make_clip(PV.recipe_of(brief), "a person on the Prompt Bench, " + time.strftime("%Y-%m-%d %H:%M"))
        if not got.get("file"):
            raise ValueError("no attempt made a clip: " + "; ".join(str(a) for a in got.get("attempts") or []))
        j.update(state="done", file=got["file"], rung=got.get("rung"), below_criteria=got.get("below_criteria") or [])
    except BaseException as e:                               # noqa: BLE001  (a refusal is a SystemExit in the chain's door)
        j.update(state="failed", error=f"{str(e)[:400]}")


def _make_swap(jid, brief):
    """A video made from a swipe: the press approves the start frame as it is now and makes the clip through the chain's
    own door (video-production machine/swipe_swap_job.py `clip`), run as ITS OWN PROCESS so a restart of this board never
    kills a clip already paid for (2026-10-27: a restart two minutes after a press lost the clip). The job's state is the
    status file the process writes; job() reads it."""
    import subprocess
    import sys
    brand, label = str(brief["run"]).split(":", 1)[1].split("/", 1)
    who = "a person on the Prompt Bench, " + time.strftime("%Y-%m-%d %H:%M")
    d = REPO / "runs" / "video-production" / brand / label
    st = d / "clip-status.json"
    st.write_text(json.dumps({"state": "running", "started": time.time()}))
    code = ("import json,sys,importlib.util,time;"
            "sp=importlib.util.spec_from_file_location('sj',sys.argv[1]);sj=importlib.util.module_from_spec(sp);sp.loader.exec_module(sj);"
            "st=sys.argv[5]\n"
            "try:\n sj.approve_still(sys.argv[2],sys.argv[3],sys.argv[4]);r=sj.make_clip(sys.argv[2],sys.argv[3],sys.argv[4]);"
            "open(st,'w').write(json.dumps({'state':'done','file':r['file']}))\n"
            "except BaseException as e:\n open(st,'w').write(json.dumps({'state':'failed','error':str(e)[:400]}))\n")
    subprocess.Popen([sys.executable, "-c", code, str(REPO / "tools/video-production/machine/swipe_swap_job.py"), brand, label, who, str(st)],
                     start_new_session=True, stdout=subprocess.DEVNULL, stderr=open(d / "clip-run.log", "a"))
    JOBS[jid].update(status_file=str(st))


def _make(jid, brief):
    """The Make button: the person's press is the cost approval; preview.make_picture runs the sheet gate and the
    rulebook first and refuses by name."""
    j = JOBS[jid]
    try:
        got = PV.make_picture(PV.recipe_of(brief), "a person on the Prompt Bench, " + time.strftime("%Y-%m-%d %H:%M"))
        if brief.get("video_job"):                           # a video's start frame, made in the picture steps: the video takes it
            vb, _, vl = str(brief["video_job"]).partition("/")
            jf = REPO / "runs" / "video-production" / vb / vl / "job.json"
            if jf.is_file():
                jb = json.loads(jf.read_text())
                rc = PV.recipe_of(dict(brief))
                rc["brief"].pop("video_job", None)
                jb.update(still=got["file"], still_approved=None, recipe=rc, status="still-made")
                jf.write_text(json.dumps(jb, indent=1))
        shot = brief.get("video_shot") or {}
        if not shot.get("run"):                               # the shot's own swap list says which video it is for
            try:
                shot = json.loads((PV._teardown_run(REPO, brief["run"]) / "out" / "swaps.json")
                                  .read_text()).get("for_video") or {}
            except (OSError, ValueError, KeyError):
                shot = {}
        if shot.get("run") and shot.get("picture"):            # a shot's start picture: the video run's clip step takes it
            dst = REPO / "runs" / "video-production" / shot["run"] / "media" / f"{shot['picture']}{Path(got['file']).suffix}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            opening_run = dst.parent.parent
            is_opening = (opening_run / "opening.json").is_file()
            if is_opening:
                if dst.is_file():
                    old = opening_run / "versions" / ("frame-" + _sha(dst) + dst.suffix)
                    old.parent.mkdir(exist_ok=True)
                    if not old.exists(): old.write_bytes(dst.read_bytes())
                (opening_run / "picture-recipe.json").write_text(json.dumps(PV.recipe_of(brief), indent=2))
            dst.write_bytes(Path(got["file"]).read_bytes())
            bc = body_check(REPO / "runs" / "video-production" / shot["run"], dst)
            n = int(brief.get("body_retry") or 0)
            if not is_opening and bc.get("ok") is False and n < BODY_RETRIES:
                # A WRONG BODY IS REMADE BEFORE A PERSON SEES IT (2026-10-28): the check's own words become the scene's
                # note, the swaps are rewritten with it, and the picture is made again, up to BODY_RETRIES times
                return _body_retry(jid, brief, shot, bc, n)
            got = {**got, "shot_picture": str(dst)}
        j.update(state="done", **got)
    except Exception as e:                                   # noqa: BLE001
        j.update(state="failed", error=f"{str(e)[:400]}")


# THE SHOTS STEP (2026-10-27).
# A video's clips start from one picture per swipe shot. Each picture is made on the picture steps like any picture
# ad: the swipe's own first frame of that shot is opened as a picture run (image-teardown `chain.py open` + its chain),
# so IMAGE 1 is the swipe frame and only our elements swap in. The made picture lands in the video run's media/ under
# the id the clip plan asks for. Each shot also lists its effects — made on their own, laid on in the edit.
SHOT_JOBS = _Jobs()


def _video_run(run):
    d = REPO / "runs" / "video-production" / run
    if not (d / "storyboard.json").is_file():
        raise ValueError(f"no scene plan for {run}")
    return d


def _teardown_of(d):
    rj = json.loads((d / "run.json").read_text()) if (d / "run.json").is_file() else {}
    b = rj.get("brief_from") or ""
    t = Path(b).parent.parent if b else None
    if t is not None and not t.is_absolute():
        t = REPO / t
    if t is None or not (t / "framemap").is_dir():
        t = REPO / "runs" / "video-teardown" / "_work" / d.name
    return t


def _shot_slug(run, gid):
    brand, _, label = run.partition("/")
    label = label.replace("/", "-")
    slug = f"{brand}-batch-{label}-{gid.lower()}-start"[:60].rstrip("-")
    plain = re.sub(r"[^a-z0-9-]+", "-", slug.lower())       # the picture chain's own spelling of a label with underscores
    if slug != plain and not (REPO / "runs" / "image-teardown" / brand / slug).is_dir():
        slug = plain
    return slug, f"{label}-{gid.lower()}-start"


def shots(run):
    d = _video_run(run)
    sb = json.loads((d / "storyboard.json").read_text())
    plan = json.loads((d / "plan.json").read_text())
    workflow = PV._load("video-production/machine/hook_workflow.py").inspect(d, REPO) if (d / "opening.json").is_file() else {}
    lines = {s["id"]: (s.get("voice") or "").strip() for s in plan.get("scenes") or []}
    cp = PV._load("video-production/machine/clips_plan.py")
    td = _teardown_of(d)
    out = []
    for n, g in enumerate(sb.get("sections") or [], 1):
        pid = cp.picture_ids(g).get("start")
        made = cp.picture_file(d, pid) if pid else None
        ks = (g.get("swipe") or {}).get("shots") or []
        sw = td / "framemap" / "shots" / ks[0]["first"] if ks and ks[0].get("first") else None
        slug, _ = _shot_slug(run, g["id"])
        it = PV._teardown_run(REPO, slug)
        state = ("ready" if (it / "out" / "swaps.json").is_file() else
                 (SHOT_JOBS.get(slug) or {}).get("state") or ("none" if sw else "no swipe frame"))
        out.append({"n": n, "id": g["id"], "maker": g.get("maker"), "seconds": g.get("seconds"),
                    "swipe_shot": ks[0]["id"] if ks else None,
                    "swipe_frame": workflow.get("base") or (str(sw) if sw and sw.is_file() else ""),
                    "swipe_video": str(td / "source.mp4") if (td / "source.mp4").is_file() else "",
                    "swipe_span": (g.get("swipe") or {}).get("span") or [],
                    "picture": pid, "made": str(made) if made else "", "same_as": g.get("same_picture_as"),
                    "lines": [lines.get(s, "") for s in g.get("scenes") or [] if lines.get(s)],
                    "picture_run": slug, "picture_state": state,
                    "picture_recipe": _read_json(d / "picture-recipe.json") if len(sb.get("sections") or []) == 1 else {},
                    "error": (SHOT_JOBS.get(slug) or {}).get("error", ""),
                    "effects": g.get("effects") or [],
                    "breakdown": _breakdown(d, g["id"]),
                    "clips": _scene_clips(d, g["id"]),
                    "effect_ids": [e["id"] for e in (g.get("effects") or [])],
                    "effecting": [e["id"] for e in (g.get("effects") or [])
                                  if (SHOT_JOBS.get("effect:" + run + ":" + e["id"]) or {}).get("state") == "running"],
                    "effect_clips": [str(f) for e in (g.get("effects") or []) for f in
                                     ([d / "effects" / e["id"] / "clip.mp4"]
                                      + sorted((d / "effects" / e["id"] / "versions").glob("*.mp4"))) if f.is_file()],
                    "approved": _approved(d, g["id"], made),
                    "body": _body(d, made),
                    "notes": (_read_json(d / "shot-notes.json").get(g["id"]) or []),
                    "remaking": (SHOT_JOBS.get("remake:" + run + ":" + g["id"]) or {}).get("state") == "running",
                    "keeping": (SHOT_JOBS.get("keep:" + run + ":" + g["id"]) or {}).get("state") == "keeping",
                    "card": g.get("maker") in ("plate", "packshot edit", "endcard plate")})
    if workflow and not workflow.get("can_edit"):
        for scene in out:
            for candidate in scene["clips"]:
                candidate["kept"] = False
    rj = json.loads((td / "run.json").read_text()) if (td / "run.json").is_file() else {}
    brand, _, label = run.partition("/")
    cut = REPO / "runs" / "video-edit" / brand / label / "renders" / "control.mp4"
    ej = SHOT_JOBS.get("edit:" + run) or {}
    if workflow:
        cut = Path(workflow["cut"]) if workflow.get("cut") else d / "no-reviewed-cut"
    child_openings = []
    for index in d.glob("*/index.json"):
        batch = _read_json(index)
        if not isinstance(batch, dict) or "held" in str(batch.get("state", batch.get("status", ""))):
            continue
        for row in batch.get("openings") or []:
            ident = str(row.get("id") or "")
            if re.fullmatch(r"h\d+", ident) and (index.parent / ident / "opening.json").is_file():
                child = index.parent / ident
                status = PV._load("video-production/machine/hook_workflow.py").inspect(child, REPO)
                child_openings.append({"run": str(child.relative_to(REPO / "runs/video-production")),
                                       "name": row.get("title") or ident, "line": row.get("text"),
                                       "complete": sum(bool(s['complete']) for s in status.get('stages', [])),
                                       "cut": status.get('cut') or ''})
    hj = SHOT_JOBS.get("hook:" + run) or {}
    return {"run": run, "brand": brand, "product": rj.get("product") or "", "shots": out,
            "workflow": workflow, "openings": child_openings,
            "workflow_job": {k: hj.get(k) for k in ("state", "error", "action")},
            "editing": ej.get("state") == "running", "edit_error": ej.get("error") if ej.get("state") == "failed" else "",
            "effects_made": [{"id": f.parent.name, "file": str(f)} for f in sorted((d / "effects").glob("*/clip.mp4"))],
            "cut": str(cut) if cut.is_file() else "", "cut_at": cut.stat().st_mtime if cut.is_file() else None}


def _breakdown(d, gid):
    """The swipe's scene read to its smallest elements, and the list the clip judge checks each take against."""
    br = _read_json(d / "scene-breakdown.json").get(gid) or {}
    if br:
        sb = PV._load("video-production/machine/scene_breakdown.py")
        br = {**br, "judge_checks": [x[2:] for x in sb.judge_lines(br).splitlines() if x.startswith("- ")]}
    return br


def _scene_clips(d, gid):
    """Every clip try made for this scene, in the order it was tried, with the chain's own checks (clips/ledger.json):
    the clip judge's score and reasons, and the tries the model refused or never made (no video, the reason only)."""
    led = _read_json(d / "clips" / "ledger.json")

    def order(tid):
        n = tid.rsplit("-", 1)[-1]
        return (tid.rsplit("-", 1)[0], 999 if n == "bk" else int(n[1:]) if n[1:].isdigit() else 998)

    files = {f.stem: f for f in (d / "clips" / "calls").glob(f"{gid}-*/takes/*.mp4")}
    tried = set(files) | {k for k, v in led.items() if k.startswith(gid + "-") and isinstance(v, dict) and v.get("verdict")
                          and k.rsplit("-", 1)[-1] not in ("C1", "C2", "C3", "C4")}
    out = []
    for tid in sorted(tried, key=order):
        f, rec = files.get(tid), led.get(tid) or {}
        qc, v = rec.get("qc") or {}, rec.get("verdict") or {}
        call = tid.rsplit("-", 1)[0]
        moved = f.parent.parent / "moves" / f.name if f else None   # the same take with its camera moves (camera_moves.py)
        out.append({"file": str(f) if f else "", "take": tid, "words": (rec.get("line_check") or {}).get("verdict"),
                    "kept": str((led.get(call) or {}).get("picked")) == tid.rsplit("-t", 1)[-1],
                    "moved": str(moved) if moved and moved.is_file() else "",
                    "score": v.get("score"), "pass": v.get("pass"), "why": v.get("why") or [], "heard": v.get("heard"),
                    "made_at": f.stat().st_mtime if f else None,
                    "lips_ok": (qc.get("lips") or {}).get("ok"), "ok": qc.get("ok"), "seconds": rec.get("seconds")})
    # One-attempt routes write a call result without a numbered take. Show it
    # as a review candidate too; absence of a takes/ folder is not absence of video.
    if (d / "opening.json").is_file():
        for candidate in out:
            candidate.update(kept=False, review_only=True)
    if not out or (d / "opening.json").is_file():
        for cid, rec in led.items():
            if not cid.startswith(gid + "-C") or not isinstance(rec, dict) or not rec.get("file"):
                continue
            f = Path(rec["file"])
            f = f if f.is_absolute() else REPO / f
            if not f.is_file():
                continue
            review = _read_json(d / "hook-clip-review.json")
            kept = bool(review.get("approved_sha256") and
                        review["approved_sha256"] == PV._load("video-production/machine/hook_workflow.py").digest(f))
            qc = rec.get("qc") or {}
            out.append({"file": str(f), "take": cid, "review_only": True, "kept": kept,
                        "words": (rec.get("line_check") or {}).get("verdict"), "made_at": f.stat().st_mtime,
                        "lips_ok": (qc.get("lips") or {}).get("ok"), "why": [], "score": None})
    return out


def hook_action(body):
    run, action = body.get("run") or "", body.get("action") or ""
    if action not in ("check_frame", "approve_frame", "check_clip", "approve_clip", "make_voice", "reuse_control_frame"):
        return 400, {"error": "Unknown opening workflow action"}
    d = _video_run(run)
    state = PV._load("video-production/machine/hook_workflow.py").inspect(d, REPO)
    if not state.get("can_" + action):
        return 400, {"error": "Complete the preceding workflow checks first."}
    previous = SHOT_JOBS.get("hook:" + run) or {}
    if previous.get("state") == "running":
        return 400, {"error": "This opening already has a check running."}
    jid = _spawn("_hook_job", [run, action], shot_key="hook:" + run)
    return 200, {"id": jid}


def _hook_job(jid, run, action):
    return PV._load("video-production/machine/hook_workflow.py").act(_video_run(run), REPO, action)


def hook_update(body):
    run = body.get("run") or ""
    if any((SHOT_JOBS.get(prefix + run) or {}).get('state') == 'running' for prefix in ('hook:', 'clip:', 'picture:', 'edit:')):
        return 400, {"error": "Wait for this opening's running job before changing its inputs."}
    try:
        result = PV._load("video-production/machine/hook_workflow.py").revise(
            _video_run(run), REPO, body.get("part"), body.get("value"))
        return 200, result
    except (ValueError, KeyError) as e:
        return 400, {"error": str(e)}


def _read_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def _sha(p):
    import hashlib
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()[:16] if p and Path(p).is_file() else ""


BODY_RETRIES = 2


def _body_retry(jid, brief, shot, bc, n):
    run = shot["run"]
    got = shots(run)
    s = next((x for x in got["shots"] if x.get("picture") == shot.get("picture")), None)
    if not s:
        return None
    d = _video_run(run)
    notes = _read_json(d / "shot-notes.json")
    notes.setdefault(s["id"], []).append("Body check (automatic): " + "; ".join(bc.get("problems") or [])[:400]
                                         + ". Exactly two arms and two hands, each plainly from the person's own shoulder, normal size.")
    (d / "shot-notes.json").write_text(json.dumps(notes, indent=1, ensure_ascii=False))
    _sh(["tools/video-production/machine/shot_swaps.py", str(d), s["id"], "--frame", s["swipe_frame"],
         "--write", s["picture_run"]], timeout=600)
    return _make(jid, {**brief, "body_retry": n + 1})


def body_check(run_dir, pic):
    """THE BODY CHECK on a scene's start picture (2026-10-28): arms, hands and
    hand size, read before any clip is made from it; the result is kept by the picture's bytes in body-checks.json."""
    got = PV._load("video-production/machine/body_check.py").check(Path(run_dir), Path(pic), f"{Path(pic).stem}-body")
    f = Path(run_dir) / "body-checks.json"
    allr = _read_json(f)
    allr[Path(pic).name] = {**got, "sha": _sha(pic)}
    f.write_text(json.dumps(allr, indent=1))
    return got


def _body(d, made):
    r = _read_json(d / "body-checks.json").get(Path(made).name) if made else None
    return r if r and r.get("sha") == _sha(made) else None


def _approved(d, gid, made):
    a = _read_json(d / "shot-approvals.json").get(gid) or {}
    return bool(a) and bool(made) and a.get("sha") == _sha(made)


def shot_approve(body):
    """Approve one scene's start picture, tied to its exact bytes (a remade picture is not approved)."""
    run, gid = body.get("run") or "", body.get("section") or ""
    if (_video_run(run) / "opening.json").is_file():
        return hook_action({"run": run, "action": "approve_frame"})
    s = next((x for x in shots(run)["shots"] if x["id"] == gid), None)
    if not s or not s["made"]:
        return 400, {"error": f"{gid}: no picture to approve"}
    d = _video_run(run)
    a = _read_json(d / "shot-approvals.json")
    a[gid] = {"picture": s["made"], "sha": _sha(s["made"]), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (d / "shot-approvals.json").write_text(json.dumps(a, indent=1))
    return 200, {"ok": True}


def shot_keep(body):
    """A person keeps one clip take for its call: it becomes the scene's clip (clips_run.keep_take)."""
    run, take = body.get("run") or "", str(body.get("take") or "")
    call_id = take.rsplit("-t", 1)[0]
    if not call_id or call_id == take:
        return 400, {"error": "which take?"}
    jid = _spawn("_keep_job", [run, call_id, take], shot_key="keep:" + run + ":" + call_id.split("-")[0],
                 running_as="keeping")
    return 200, {"ok": True, "id": jid}


def _keep_job(jid, run, call_id, take):
    """Runs in its own process: the kept take becomes the call's clip, upscaled on this Mac (clips_run.keep_take)."""
    send = PV.build_clip({"run": run, "call": call_id})["send"]
    got = PV._clip_chain().keep_take(Path(send["run"]), send["call"], take, "person (board)")
    return {"picked": got.get("picked")}


def edit_make(body):
    """THE EDIT, the step after the scenes (2026-10-28): the video-edit line on
    the scenes' kept clips, with every effect laid in over its words, as its own job."""
    run = body.get("run") or ""
    if not run:
        return 400, {"error": "which video?"}
    if (_video_run(run) / "opening.json").is_file():
        if any((SHOT_JOBS.get(prefix + run) or {}).get('state') == 'running' for prefix in ('hook:', 'clip:', 'picture:', 'edit:')):
            return 400, {"error": "Wait for this opening's running job before making its cut."}
        try:
            PV._load("video-production/machine/hook_workflow.py").require_edit(_video_run(run), REPO)
        except ValueError as e:
            return 400, {"error": str(e)}
    jid = _spawn("_edit_job", [run], shot_key="edit:" + run)
    return 200, {"id": jid}


def _edit_job(jid, run):
    """Runs in its own process: each scene effect's current clip becomes the edit's B-roll of the same name, then the
    video-edit line cuts the draft (tools/video-edit/machine/line.py --draft --no-file)."""
    import shutil
    d = _video_run(run)
    if (d / "opening.json").is_file():
        return PV._load("video-edit/machine/hook_edit.py").render(d, REPO)
    brand, _, label = run.partition("/")
    e = REPO / "runs" / "video-edit" / brand / label
    (e / "broll").mkdir(parents=True, exist_ok=True)
    for fx in sorted((d / "effects").glob("*/clip.mp4")):
        shutil.copyfile(fx, e / "broll" / f"{fx.parent.name}.mp4")
    # the scenes are approved: the edit only cuts them together, its checks are listed, nothing is regenerated
    _sh(["tools/video-edit/machine/line.py", str(d), "--draft", "--approved", "--no-file"], timeout=5400)
    cut = e / "renders" / "control.mp4"
    if not cut.is_file():
        raise ValueError("the edit line made no cut")
    return {"file": str(cut)}


def effect_make(body):
    """Remake one scene effect (video-production effects.py), as its own job: the old still and clip are kept under
    versions/ beside it, the new one is made on our own scene's object in the swipe's style."""
    run, eid = body.get("run") or "", str(body.get("effect") or "")
    d = _video_run(run) / "effects" / eid
    if not eid or not (d / "effect.json").is_file():
        return 400, {"error": f"{eid}: no such effect"}
    jid = _spawn("_effect_job", [str(_video_run(run)), eid], shot_key="effect:" + run + ":" + eid)
    return 200, {"id": jid}


def _effect_job(jid, run_dir, eid):
    """Runs in its own process: the effect's old picture and clip are moved to versions/<time>-*, then it is made again."""
    d = Path(run_dir) / "effects" / eid
    stamp = time.strftime("%Y%m%d-%H%M")
    (d / "versions").mkdir(exist_ok=True)
    for n in ("still.png", "clip.mp4", "clip-made.mp4"):
        if (d / n).is_file():
            (d / n).rename(d / "versions" / f"{stamp}-{n}")
    got = PV._load("video-production/machine/effects.py").make(Path(run_dir), only=[eid])
    rec = (got or [{}])[0]
    if not rec.get("clip"):
        raise ValueError(rec.get("refused") or "the effect clip was not made")
    return {"file": str(Path(run_dir) / rec["clip"])}


def shot_change(body):
    """A person's feedback on one scene: kept on that shot (shot-notes.json, read by shot_swaps into the picture's words)
    and the scene's start picture is remade with it — the same make, the same passes, nothing else touched."""
    run, gid, note = body.get("run") or "", body.get("section") or "", str(body.get("note") or "").strip()
    if not note:
        return 400, {"error": "say what to change"}
    got = shots(run)
    s = next((x for x in got["shots"] if x["id"] == gid), None)
    if not s or s["picture_state"] != "ready":
        return 400, {"error": f"{gid}: this scene's picture run is not ready"}
    d = _video_run(run)
    n = _read_json(d / "shot-notes.json")
    n.setdefault(gid, []).append(note)
    (d / "shot-notes.json").write_text(json.dumps(n, indent=1, ensure_ascii=False))
    jid = _spawn("_change_job", [str(d), gid, s["swipe_frame"], s["picture_run"],
                                 {"brand": got["brand"], "run": s["picture_run"], "product": got["product"], "skip": [], "added": []}],
                 shot_key="remake:" + run + ":" + gid)
    return 200, {"id": jid}


def _change_job(jid, video_dir, gid, frame, picture_run, brief):
    """Runs in its own process (2026-10-28: every board job is its own process): the swaps are rewritten with the
    person's note, then the start picture is made again the same way as the first time."""
    _sh(["tools/video-production/machine/shot_swaps.py", video_dir, gid, "--frame", frame, "--write", picture_run],
        timeout=600)
    return _make(jid, brief)


def shot_open(body):
    """Open the swipe frame of one shot as a picture run and run its chain (in the background, a few minutes)."""
    run, gid = body.get("run") or "", body.get("section") or ""
    got = shots(run)
    s = next((x for x in got["shots"] if x["id"] == gid), None)
    if not s or not s["swipe_frame"]:
        return 400, {"error": f"{gid}: no swipe frame for this shot"}
    slug, name = _shot_slug(run, gid)
    if (SHOT_JOBS.get(slug) or {}).get("state") == "opening":
        return 200, {"state": "opening"}
    _spawn("_open_job", [got["brand"], got["product"], s["swipe_frame"], name, slug, str(_video_run(run)), gid],
           shot_key=slug, running_as="opening", done_as="ready")
    return 200, {"state": "opening"}


def _open_job(jid, brand, product, frame, name, slug, video_dir, gid):
    """Runs in its own process: the shot's swipe frame opened as a picture run, its chain run, its swaps written."""
    _sh(["tools/image-teardown/chain.py", "open", "--brand", brand, "--file", frame,
         "--name", name, "--source", "organic", "--route", "ai", "--form", "single"], timeout=300)
    # the records only: a video scene's swaps come from its brief, so the picture chain's writing stages are never used here
    cmd = ["tools/image-teardown/tools/run.py", slug, "1,1k,2,2b", "--brand", brand, "--gates", "warn"]
    if product:
        cmd += ["--product", product]
    _sh(cmd, timeout=3600)
    # the shot's swaps come from the VIDEO BRIEF, never the picture chain's own new concept (2026-10-27)
    _sh(["tools/video-production/machine/shot_swaps.py", video_dir, gid, "--frame", frame, "--write", slug], timeout=600)
    # THE SWIPE SCENE BROKEN DOWN (L-50, L-51) with the frame, so no clip is ever made without it; a failed read never
    # stops the frame — the scene card then shows no breakdown and a new Get the swipe frame ready reads it
    if gid not in _read_json(Path(video_dir) / "scene-breakdown.json"):
        try:
            _sh(["tools/video-production/machine/scene_breakdown.py", video_dir, gid], timeout=900)
        except Exception:                                   # noqa: BLE001
            pass


def make(body):
    fresh()
    brief = body.get("brief") or {}
    if not brief.get("run"):
        return 400, {"error": "pick a brief first"}
    job_ = body.get("job") or ""
    if job_.startswith("swipe_footage."):                    # already its own process (clip-status.json)
        jid = f"m{int(time.time() * 1000)}"
        with LOCK:
            JOBS[jid] = {"state": "running", "started": time.time()}
        _make_swap(jid, brief)
        return 200, {"id": jid}
    shot = brief.get("video_shot") or {}
    run = brief["run"] if job_ == "clips.seedance" else shot.get("run")
    key = ("clip:" if job_ == "clips.seedance" else "picture:") + run if run else None
    if key and (SHOT_JOBS.get(key) or {}).get("state") == "running":
        return 400, {"error": "This element already has a generation running."}
    return 200, {"id": _spawn("_make_clip" if job_ == "clips.seedance" else "_make", [brief], shot_key=key)}


def job(jid):
    j = JOBS.get(jid)
    if j is None and (JOB_DIR / f"{jid}.json").is_file():   # a job started before this board restarted
        j = {"status_file": str(JOB_DIR / f"{jid}.json")}
    j = j or {"state": "unknown"}
    if j.get("status_file"):                                  # a clip made by its own process: its status file is the truth
        try:
            return {**j, **json.loads(Path(j["status_file"]).read_text())}
        except (OSError, ValueError):
            pass
    return j


def made(brand=None):
    out = []
    for f in (REPO / "runs" / "image-production").glob("*/prompt-bench/*.png"):
        if brand in (None, f.parent.parent.name):
            out.append((f.stat().st_mtime, f))
    return [str(f) for _, f in sorted(out, reverse=True)[:12]]


# ------------------------------------------------ the batch: the approved picture + 5, then the Meta card (2026-10-27)
# the owner: "we're gonna run batches of ads through this tool right here … we need to see all the 6 variations of the
# headlines at this stage … let's make the one and then we make the variations." The board drives the same components
# the chain does, nothing of its own: image-writing writes the five (stage 5) and keeps the copy sign-off, image-edit
# makes them on the picture path, meta-upload files the card. Every step is a job the page polls.

def _brief_row(run):
    """The register's row for a run (image-teardown briefs.json): its brief number, product and avatar."""
    f = REPO / "tools/image-teardown/briefs.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return {}
    rows = d if isinstance(d, list) else list((d.get("briefs") or d).values())
    return next((r for r in rows if isinstance(r, dict) and r.get("run") == run), {})


def _run_dir(run):
    return PV._teardown_run(REPO, run)


def _bg(jid, fn):
    def go():
        try:
            JOBS[jid].update(state="done", **(fn() or {}))
        except BaseException as e:                         # noqa: BLE001  (a refusal is a SystemExit)
            JOBS[jid].update(state="failed", error=str(e)[:600])
    with LOCK:
        JOBS[jid] = {"state": "running", "started": time.time()}
    threading.Thread(target=go, daemon=True).start()
    return 200, {"id": jid}


def _sh(cmd, timeout=1800):
    import subprocess
    import sys
    r = subprocess.run([sys.executable] + cmd, cwd=str(REPO), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise ValueError(((r.stderr or "") + (r.stdout or "")).strip()[-600:] or "it stopped")
    return r.stdout


def batch(run, brand=None):
    """Where a run's batch stands: the approved picture, the five rows (words, picture change), the copy sign-off,
    the five pictures made, and whether the card is filed."""
    fresh()
    rd = _run_dir(run)
    out = {"run": run, "brief": _brief_row(run)}
    vf = rd / "out" / "variations.json"
    out["variations"] = json.loads(vf.read_text()).get("variations") if vf.is_file() else []
    aw = rd / "out" / "approved-words.md"
    out["approved_words"] = [l.split("`")[1] for l in aw.read_text().splitlines() if l.count("`") >= 2] if aw.is_file() else []
    ok = rd / "out" / "copy-approved.json"
    out["copy_approved"] = json.loads(ok.read_text()) if ok.is_file() else None
    brand = brand or out["brief"].get("brand") or run.split("-")[0]
    # the board's own home and the chain's pictures folder: a first picture the chain made is approved here too
    homes = [REPO / "runs/image-production" / brand / "prompt-bench", REPO / "runs/image-teardown" / brand / run / "pictures"]
    liked = sorted((f for h in homes if h.is_dir() for f in h.glob(f"{run}*.liked.json")), key=lambda f: f.stat().st_mtime)
    out["approved_picture"] = str(liked[-1]).replace(".liked.json", ".png") if liked else None
    made = sorted((f for h in homes if h.is_dir() for f in h.glob(f"{run}*.png")
                   if not f.name.endswith(".plate.png")), key=lambda f: f.stat().st_mtime)
    out["newest_picture"] = str(made[-1]) if made else None          # a reload of the board shows it again
    made_dir = REPO / "runs/image-edit" / brand / f"{run}--batch"
    out["made"] = {}
    for v in out["variations"]:
        f = next(iter(sorted((made_dir / v["id"]).glob("*--" + v["id"] + ".png"))), None) if (made_dir / v["id"]).is_dir() else None
        if f:
            out["made"][v["id"]] = str(f)
    cf = rd / "out" / "meta-card.json"
    out["card"] = json.loads(cf.read_text()) if cf.is_file() else None     # where the 6 were filed, said by the filer
    hf = REPO / "runs/handoffs/graphic-designer" / brand / (out["brief"].get("id") or run) / "handoff.json"
    out["handoff"] = (json.loads(hf.read_text()).get("drive") or {"link": None}) if hf.is_file() else None   # said by the handoff
    return out


def paths_brand(run):
    """The brand a run belongs to, from its own folder (runs/image-teardown/<brand>/<run>)."""
    d = _run_dir(run)
    return d.parent.name if d else ""


def batch_write(body):
    """Write the five (image-writing stage 5) off the approved picture: its words in its shape, from her real lines."""
    fresh()
    run = body.get("run") or ""
    row = _brief_row(run)
    # the register's product is the product FILE (brands/<b>/products/<slug>.md); the page's is the photo kit's name. A
    # brief gets its number only once it is finished (after these five), so a new one has no register row yet: its own
    # order (vars/ask.md → ask.json) names the product, the avatar and the offer (2026-10-28: the button wrote nothing)
    ask_path = ""
    try:
        ask_path = (_run_dir(run) / "vars" / "ask.md").read_text().strip()
        ask = json.loads((REPO / ask_path).read_text()) if ask_path else {}
    except (OSError, ValueError):
        ask = {}
    brand = row.get("brand") or ask.get("brand") or body.get("brand")
    product = row.get("product") or ask.get("product") or body.get("product")
    avatar = row.get("avatar") or ask.get("avatar")
    if not (run and brand and product):
        return 400, {"error": "this brief has no brand or product in the register or its order"}
    cmd = (["tools/image-writing/run.py", run, "5,6", "--brand", brand, "--product", product]
           + (["--avatar", avatar] if avatar else []) + (["--ask", ask_path] if ask_path else []))
    return _bg(f"w{int(time.time() * 1000)}", lambda: {"log": _sh(cmd)[-1500:], "batch": batch(run, brand)})


def batch_make(body):
    """The person's words for the five (edited on the page) are saved, approved by that press, and the five are made on
    the picture path by image-edit, each an edit of the approved picture."""
    fresh()
    run = body.get("run") or ""
    st = batch(run, body.get("brand"))
    if not st["approved_picture"]:
        return 400, {"error": "approve the first picture first (Looks good)"}
    rd = _run_dir(run)
    vf = rd / "out" / "variations.json"
    d = json.loads(vf.read_text())
    edits = body.get("words") or {}
    for v in d.get("variations") or []:
        if edits.get(v["id"]):
            new = [str(x).strip() for x in edits[v["id"]] if str(x).strip()]
            if new and new != v.get("words"):
                d.setdefault("edits", []).append({"by": "a person on the board", "at": time.strftime("%Y-%m-%dT%H:%M"),
                                                  "id": v["id"], "from": v.get("words"), "to": new})
                v["words"] = new
    vf.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    brand = body.get("brand") or st["brief"].get("brand")
    by = (body.get("by") or "the owner") + ", on the board"

    def go():
        _sh(["tools/image-writing/tools/copy_ok.py", "approve", run, "--by", by], 120)
        log = _sh(["tools/image-edit/vary.py", st["approved_picture"], "--brand", brand, "--from-brief", str(vf),
                   "--label", f"{run}--batch"])
        return {"log": log[-1500:], "batch": batch(run, brand)}
    return _bg(f"v{int(time.time() * 1000)}", go)


def batch_card(body):
    """The approved picture and the five on one card in the Meta approval page's 1-check (meta-upload to_check)."""
    fresh()
    run = body.get("run") or ""
    st = batch(run, body.get("brand"))
    row = st["brief"]
    media = [st["approved_picture"]] + [st["made"][v["id"]] for v in st["variations"] if v["id"] in st["made"]]
    if not st["approved_picture"] or len(media) < 2:
        return 400, {"error": "make the variations first"}
    if not row.get("brief"):
        # an ad written before briefs were numbered at the writing step gets its number from the chain's own register
        # step now (image-writing writing.number_brief), never a refusal (2026-10-27)
        rd0 = _run_dir(run)
        import re as _re
        av = rd0 / "vars" / "avatar.md"
        m = _re.search(r"avatar:\s*([a-z0-9][a-z0-9-]*)", av.read_text()) if av.is_file() else None
        prod = body.get("product") or row.get("product")
        if not prod:
            return 400, {"error": "this ad has no brief number yet, and no product to number it under"}
        _sh(["tools/image-teardown/tools/briefs.py", "open", run, "--brand", row.get("brand") or body.get("brand"),
             "--type", "image-ai", "--product", prod] + (["--avatar", m.group(1)] if m else []), 300)
        row = _brief_row(run)
        if not row.get("brief"):
            return 400, {"error": "this ad could not be given a brief number"}
    rd = _run_dir(run)
    cf = rd / "out" / "meta-card.json"
    before = json.loads(cf.read_text()) if cf.is_file() else {}
    # the naming grammar: a date + a letter. A batch sent before keeps its name, so a second press updates that card
    # (still in To check) instead of filing a second one
    batch_name = before.get("batch") or "batch-" + time.strftime("%Y-%m-%d") + "-a"
    cmd = ["components/meta-upload/to_check.py", "--brand", row["brand"], "--lane", "image", "--product", row.get("product") or "",
           "--brief", row["brief"], "--batch", batch_name,
           "--media"] + media + ["--tool", "image-edit", "--run", f"runs/image-edit/{row['brand']}/{run}--batch", "--replace"]
    if row.get("avatar"):
        cmd += ["--avatar", row["avatar"]]

    def go():
        log = _sh(cmd, 3600)
        # the filer's own word, never assumed: its summary line starts with what it did (filed, replaced, skipped: …)
        said = next((l for l in log.splitlines() if l.startswith(("REFUSED", "filed", "replaced", "skipped"))), "")
        if not said.startswith(("filed", "replaced")):
            raise SystemExit(said or ("the filer said nothing it did: " + log[-300:]))
        rec = {"state": "1-check", "said": said.split()[0], "name": said.split()[-1].split("/")[-1], "batch": batch_name,
               "at": time.strftime("%Y-%m-%dT%H:%M"), "pictures": len(media)}
        words = re.search(r"primary (\d+) · headlines (\d+) · descriptions (\d+) · pages (\d+)", log)
        if words:
            rec.update(dict(zip(("primary", "headlines", "descriptions", "pages"), map(int, words.groups()))))
        cf.write_text(json.dumps(rec, indent=1))
        return {"log": log[-1500:], "card": rec}
    return _bg(f"c{int(time.time() * 1000)}", go)


# ------------------------------------------------ new deliveries: the graphic designer's pictures, the video editor's videos
# the owner, 2026-10-27: "check for [the graphic designer's] recent delivery", "for [the video editor] as well on the video
# side, everything needs to run through the same process", "make this name agnostic". The check, the matching to briefs
# and bringing it in are image-edit's (tools/image-edit/delivery.py); the card is meta-upload's to_check. The board
# only asks and shows.

def _deliverers():
    """The roles the board's delivery button checks, named by role (2026-10-27):
    `name` is the role in words, `filled_by` who fills it today, both from image-edit's delivery.json."""
    try:
        roles = json.loads((REPO / "tools/image-edit/delivery.json").read_text()).get("roles") or {}
    except (OSError, ValueError):
        return []
    return [{"id": k, "name": "the " + k.replace("-", " "), "filled_by": v.get("filled_by"), "delivers": v.get("delivers")}
            for k, v in roles.items()]


def _delivery():
    import importlib.util
    spec = importlib.util.spec_from_file_location("image_edit_delivery", REPO / "tools/image-edit/delivery.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def delivery_check(body):
    """Check every role's hand-off returned/ folders for the brand: what is new, matched to its brief, brought in."""
    brand = body.get("brand") or ""
    if not brand:
        return 400, {"error": "pick a brand"}

    def go():
        D = _delivery()
        res = D.check(brand)
        return {"result": res, "delivered": D.delivered(brand), "said": D.say(res)}
    return _bg(f"d{int(time.time() * 1000)}", go)


def delivery_card(body):
    """One delivery's files onto one card in the Meta approval page's To check (`brief` is the delivery's label)."""
    brand, brief = body.get("brand") or "", body.get("label") or body.get("brief") or ""
    if not (brand and brief):
        return 400, {"error": "pick a delivered brief"}

    def go():
        D = _delivery()
        return {"card": D.send(brand, brief), "delivered": D.delivered(brand)}
    return _bg(f"dc{int(time.time() * 1000)}", go)


# ------------------------------------------------ the Higgsfield handoff (2026-10-27)
# the owner: "once I feel confident, I'll have something called a Higgsfield handoff, so that way you can just work directly
# in Supercomputer." The package (prompts, numbered pictures, words, rules, HANDOFF.md) and its copy on the Drive are
# image-edit's (tools/image-edit/handoff.py); the board only presses it and shows the link.

def _handoff_target(body):
    """What the handoff front door is asked for: a video run ("brand/run" on the board) by its folder, a picture by its
    teardown run."""
    run = body.get("run") or ""
    if body.get("kind") == "clip" or (REPO / "runs/video-production" / run / "run.json").is_file():
        return "runs/video-production/" + run, "clip"
    return run, "pic"


def handoff_state(run, kind=None):
    """The Drive link of a brief's handoff when it has one, from the handoff's own record (either lane)."""
    what, kind = _handoff_target({"run": run, "kind": kind})
    rec = _brief_row(run) if kind == "pic" else next(
        (r for r in _register_rows() if str(r.get("type", "")).startswith("video")
         and str(r.get("run") or "").rstrip("/").split("/")[-1] == run.split("/")[-1]), {})
    if not rec.get("id"):
        return {"link": None, "brief": None}
    role = "graphic-designer" if kind == "pic" else "video-editor"        # the handoff's one place: runs/handoffs/<role>/...
    hf = REPO / "runs/handoffs" / role / (rec.get("brand") or "") / rec["id"] / "handoff.json"
    d = (json.loads(hf.read_text()).get("drive") or {}) if hf.is_file() else {}
    return {"link": d.get("link"), "brief": rec.get("brief")}


def _register_rows():
    try:
        d = json.loads((REPO / "tools/image-teardown/briefs.json").read_text())
    except (OSError, ValueError):
        return []
    return [r for r in (d.get("briefs") or {}).values() if isinstance(r, dict)]


def handoff(body):
    """One brief's handoff for the role that makes the rest by hand, either lane, through image-edit's front door
    (handoff.py), which reads the brief's lane from the register; the board only presses it and shows the link."""
    what, kind = _handoff_target(body)
    if not what:
        return 400, {"error": "pick an ad first"}
    if kind == "pic":
        st = batch(what, body.get("brand"))
        if not st["approved_picture"]:
            return 400, {"error": "approve the first picture first (Looks good)"}
        if not st["variations"]:
            return 400, {"error": "write the 5 variations first"}
    brand = body.get("brand") or ""

    def go():
        if kind == "pic" and not _brief_row(what).get("brief"):
            # a finished brief gets its number here, from its own order (2026-10-28: a new brief reached the handoff
            # with none, and the button refused)
            try:
                ap = (_run_dir(what) / "vars" / "ask.md").read_text().strip()
                ask = json.loads((REPO / ap).read_text()) if ap else {}
            except (OSError, ValueError):
                ask = {}
            b = brand or ask.get("brand") or ""
            _sh(["tools/image-teardown/tools/briefs.py", "open", what, "--brand", b, "--type", "image-ai"]
                + (["--product", ask["product"]] if ask.get("product") else [])
                + (["--avatar", ask["avatar"]] if ask.get("avatar") else [])
                + sum((["--link", l] for l in ask.get("links") or []), []), 300)
        if kind == "pic":
            # the run's record is filed again first, so it lists the brief the board just wrote (2026-10-28: a written
            # brief was refused as "never reached the final stage" because the record was filed before it was written)
            _sh(["-c", "import sys; sys.path.insert(0, 'tools/image-teardown/tools'); import gates, paths; "
                       f"gates.file_record({(brand or paths_brand(what))!r}, {what!r})"], 300)
        log = _sh(["tools/image-edit/handoff.py", what] + (["--brand", brand] if brand else []), 1800)
        link = next((l.split("link: ", 1)[1].strip() for l in log.splitlines() if l.startswith("link: ")), None)
        if not link:
            raise SystemExit("the handoff said no Drive link: " + log[-300:])
        return {"log": log[-1500:], "link": link, **({"batch": batch(what, brand)} if kind == "pic" else {})}
    return _bg(f"h{int(time.time() * 1000)}", go)
