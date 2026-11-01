"""The graphic designer's handoff: one approved picture ad, packaged so the designer makes the rest by hand in Higgsfield
Supercomputer (the owner, Tella 2026-10-27, 33:11: "for the images, we can work on the handoff process for Higgsfield
Supercomputer so [the designer] can just get to work on the image ads"; 15:00: "from here we're just gonna hand off brief
for Higgsfield execution because [the designer] is gonna go into Supercomputer and handle the rest of the variations, and
checking"). Named by the role, never the person; one path in the repo and on the Drive; only a brief from the chain's
final stage (the owner, 2026-10-27).

The chain ends at the approved first picture. This writes everything the rest needs into runs/handoffs/graphic-designer/
<brand>/<brief key>/ and copies it to Shared Assets/runs/handoffs/graphic-designer/<brand>/<brief key>/: the approved picture, its clean picture, the swipe, the bars overlay, and per variation the
exact prompt the chain would send (vary_recipe, dry run: model-inputs' variation_brief + build_picture), every
reference picture named as that prompt numbers it, and a words guide; the rules (model-inputs lessons) and a one-page
HANDOFF.md. Nothing is generated and nothing is spent: the words guides are the chain's own free type layer."""
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from . import paths as P
from .engine import BadRequest, vary_recipe

HOME = Path(__file__).resolve().parent.parent
FRAME = (1080, 1920)
ROLE = "graphic-designer"          # the lane is named by the role, never by who fills it (the owner, 2026-10-27)
HANDOFFS = "handoffs"               # runs/handoffs/<role>/<brand>/<brief key>/ here; Shared Assets/runs/handoffs/<role>/... on the Drive
RETURNED = "returned"               # the finished work comes back into the handoff's own folder (the Hand-off Standard's)
TEST_RUN = re.compile(r"dryrun|dry-run|batchtest|v2test|-test\b|^test-", re.I)


def folder_of(brand, key, role=ROLE, repo=None):
    """The one place a brief's handoff lives: runs/handoffs/<role>/<brand>/<brief key>/ in the repo, and the same words
    under Shared Assets on the Drive (2026-10-27)."""
    return Path(repo or P.repo()) / "runs" / HANDOFFS / role / brand / home_key(brand, key, role, repo)


def home_key(brand, key, role=ROLE, repo=None):
    """The folder name a brief's hand-off is written under: the folder already there in any spelling of the key (an
    old `acme_widget_brief-0007` keeps its name, nothing is renamed), else the catalog form (names.catalog_key,
    2026-10-28: the catalog id wins, store handles are aliases)."""
    if not key:
        return key
    try:
        import sys
        folder = str(P.sibling("naming"))
        if folder not in sys.path:
            sys.path.append(folder)
        import names as N  # noqa: E402
        forms = N.brief_key_forms(key)
    except Exception:  # noqa: BLE001 — no naming beside this one: the key as given
        return key
    base = Path(repo or P.repo()) / "runs" / HANDOFFS / role / brand
    return next((f for f in [key] + forms if (base / f).is_dir()), forms[0] if forms else key)


def drive_parts(folder, repo=None):
    """The Drive folder names for a handoff folder: its repo path from runs/ down, word for word (2026-10-28: the Drive copy is Shared Assets/runs/handoffs/...,
    the repo path itself; it was Shared Assets/handoffs/... until then)."""
    rel = Path(folder).resolve().relative_to(Path(repo or P.repo()).resolve())
    return list(rel.parts)


def _teardown_run(repo, run, brand=None):
    """A picture run's folder on the image-teardown plane: runs/image-teardown/<brand>/<run>/, its one home since
    2026-10-28 (components/naming/WHERE-EVERYTHING-GOES-damon.md item 4). The old lane folder
    tools/image-teardown/runs/<run>/ is read for one release, for a checkout that has not moved its runs."""
    root = Path(repo) / "runs" / "image-teardown"
    run = Path(str(run)).name
    hits = ([root / str(brand).lower() / run] if brand else []) + sorted(root.glob(f"*/{run}"))
    work = [d for d in hits if (d / "out").is_dir() or (d / "vars").is_dir()]
    old = Path(repo) / "tools" / "image-teardown" / "runs" / run
    if work:
        return work[0]
    if old.is_dir():
        return old
    return next((d for d in hits if d.is_dir()), hits[0] if hits else root / "_unfiled" / run)


def _writing():
    import importlib.util
    import sys
    tools = P.sibling("image-writing", "tools")
    if str(tools) not in sys.path:
        sys.path.append(str(tools))
    spec = importlib.util.spec_from_file_location("image_writing_stages", tools / "writing.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def final_stage(run, brand, repo=None, stages=None, sequence=False):
    """A handoff takes only a brief that came out of its chain's final stage, read from the chain's own output (the owner,
    2026-10-27: "briefs should come from final stages of the chains, not some random set up"). For a picture: the
    chain filed the run (its run record says `filed`), the writing chain's last stage is among its stages and on disk,
    and the variation list is the one stage 5 wrote. A carousel (`sequence`) has no variation list: its slides are in
    the brief. Returns None, or why not."""
    repo = Path(repo or P.repo())
    if TEST_RUN.search(run):
        return f"{run} is a test run, not a brief the chain made"
    stages = stages or _writing().STAGES
    last = stages[max(stages, key=lambda k: int(re.sub(r"\D", "", k) or 0))][1]
    filed = repo / "runs" / "image-teardown" / brand / run / "run.json"
    rec = json.loads(filed.read_text()) if filed.is_file() else {}
    if rec.get("state") != "filed":
        return f"{run} was never filed by the picture chain (no filed run record), so its brief did not come out of the chain"
    if last not in (rec.get("stages") or []) or not (_teardown_run(repo, run, brand) / "out" / last).is_file():
        return f"{run} never reached the chain's final stage ({last})"
    if sequence:
        return None
    vf = _teardown_run(repo, run, brand) / "out" / "variations.json"
    if (json.loads(vf.read_text()) if vf.is_file() else {}).get("source") != "stage5":
        return f"{run}'s variation list was not written by the chain's variations stage"
    return None


def _rel(p, repo):
    """A path as the record stores it: repo-relative, never a machine path (builder card rule 4)."""
    try:
        return str(Path(p).resolve().relative_to(Path(repo).resolve()))
    except ValueError:
        return Path(p).name


def approved_of(run, brand, repo=None):
    """The run's approved picture: the newest one a person pressed Looks good on (its `.liked.json`)."""
    repo = Path(repo or P.repo())
    liked = sorted((repo / "runs" / "image-production" / brand / "prompt-bench").glob(f"{run}-*.liked.json"),
                   key=lambda f: f.stat().st_mtime)
    if not liked:
        raise BadRequest(f"{run} has no approved picture yet: press Looks good on its first picture first")
    pic = liked[-1].with_name(liked[-1].name.replace(".liked.json", ".png"))
    if not pic.is_file():
        raise BadRequest(f"the approved picture {pic.name} is not on this machine")
    return pic


LANES = {"image": "graphic-designer", "sequence": "graphic-designer", "video": "video-editor"}   # brief type -> role


def _register():
    import sys
    tools = P.sibling("image-teardown", "tools")
    if str(tools) not in sys.path:
        sys.path.append(str(tools))
    import briefs as B  # noqa: E402
    return B


def resolve(what, brand=None, repo=None, reg=None):
    """What one handoff is for: a brief ID (`brief-0325` or its register key), a picture teardown run, or a video
    production run folder. Returns {lane: the role (graphic-designer | video-editor), brief, key, brand, run} with `run` the teardown run (picture)
    or the production run folder (video). The brief register decides the lane by the brief's type; never guessed."""
    repo = Path(repo or P.repo())
    B = _register()
    reg = reg or B.load()
    rows = [(k, r) for k, r in dict.items(reg["briefs"]) if isinstance(r, dict)]
    p = Path(what)
    vm = p if p.is_absolute() else repo / p
    if (vm / "run.json").is_file() and (vm / "storyboard.json").is_file():          # a video production run folder
        hits = [(k, r) for k, r in rows if str(r.get("type", "")).startswith("video")
                and str(r.get("run") or "").rstrip("/").split("/")[-1] == vm.name]
        k, r = hits[-1] if hits else (None, {})
        return {"lane": "video-editor", "brief": r.get("brief"), "key": k, "brand": r.get("brand") or vm.parent.name, "run": str(vm)}
    k, r = None, None
    if re.search(r"(?i)brief[\s_-]?\d{3,4}|^p\d{3}$", str(what)):
        try:
            k, r = B.get(reg, str(what), brand=brand)
        except ValueError as e:                                # two brands or products share the number
            raise BadRequest(f"{e}: give the brand, or the full brief key")
        if not r:
            raise BadRequest(f"{what} is not in the brief register")
    else:
        hits = [(kk, rr) for kk, rr in rows if rr.get("run") == what and (not brand or rr.get("brand") == brand)]
        if hits:
            k, r = hits[-1]
        elif brand:
            return {"lane": ROLE, "brief": None, "key": None, "brand": brand, "run": str(what)}
        else:
            raise BadRequest(f"{what} is neither a brief ID nor a run the brief register knows")
    lane = LANES.get(str(r.get("type") or "image").split("-")[0])
    if not lane:
        raise BadRequest(f"{r.get('brief') or k} is a {r.get('type')} brief: no handoff is built for that kind yet")
    run = str(r.get("run") or "")
    if lane == "video-editor":
        cands = [repo / "runs" / "video-production" / r.get("brand", "") / run.rstrip("/").split("/")[-1], repo / run]
        vm = next((c for c in cands if (c / "run.json").is_file()), None)
        if not vm:
            raise BadRequest(f"{r.get('brief')} has no video production run on this machine yet ({run}): nothing to hand off")
        run = str(vm)
    return {"lane": lane, "brief": r.get("brief") or k, "key": k, "brand": r.get("brand") or brand, "run": run,
            "sequence": str(r.get("type") or "").startswith("sequence")}


def brief_of(run):
    """(register key, brief number) of the run from image-teardown's brief register, or refused by name."""
    reg = _register().load()
    hits = [(k, r) for k, r in dict.items(reg["briefs"]) if (r or {}).get("run") == run]
    if not hits:
        raise BadRequest(f"{run} has no brief number in the register yet (image-teardown tools/briefs.py open)")
    k, r = hits[-1]
    return k, r.get("brief") or k


def _plain_model(rid):
    try:
        import sys
        folder = P.sibling("model-inputs")
        if str(folder) not in sys.path:
            sys.path.append(str(folder))
        import input_rules as IR  # noqa: E402
        return IR.load(rid).get("label") or rid
    except Exception:  # noqa: BLE001
        return rid or "the model the brief names"


def bars_overlay(top, bottom, out):
    """A see-through 1080x1920 picture with only the swipe's black bars on it, to lay over a finished picture."""
    from PIL import Image, ImageDraw
    w, h = FRAME
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if top:
        d.rectangle([0, 0, w, round(h * top / 100) - 1], fill=(0, 0, 0, 255))
    if bottom:
        d.rectangle([0, h - round(h * bottom / 100), w, h], fill=(0, 0, 0, 255))
    im.save(out)
    return out


def words_guide(plate, layer, overlay, out):
    """The clean approved picture with this variation's words set on it by the chain's own type layer, at the delivered
    size, with the bars: where the words sit and how big. Free; None when the compositor cannot run here."""
    from PIL import Image
    P.image_production()
    from image_production import words  # noqa: E402
    work = Path(tempfile.mkdtemp(prefix="handoff-words-"))
    try:
        shutil.copy2(plate, work / "plate.png")
        got = words.set_on_top(work / "plate.png", layer, out=work / "set.png", plate=work / "plate.png")
        if not got.get("ok") or not (work / "set.png").is_file():
            return None
        im = Image.open(work / "set.png").convert("RGBA").resize(FRAME, Image.LANCZOS)
        im.alpha_composite(Image.open(overlay).convert("RGBA"))
        im.convert("RGB").save(out)
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def caption_says(layer):
    """The type layer's settings in plain words, one line per block of words."""
    out = []
    for el in (layer or {}).get("elements") or []:
        col = str(el.get("color") or "#FFFFFF")
        bits = [f"{el.get('weight', '')} {el.get('font', 'sans')}".strip().replace("-", " "),
                {"#FFFFFF": "white", "#000000": "black"}.get(col.upper(), f"colour {col}")]
        if el.get("letterform"):
            bits.append(str(el["letterform"]).split(" — ")[0].replace("-", " "))
        bits.append(f"{el.get('align', 'center')}ed between {el.get('left_pct', 0)}% and {el.get('right_pct', 100)}% across")
        bits.append(f"its top {el.get('top_pct')}% down the picture")
        if el.get("height_pct"):
            bits.append(f"about {el['height_pct']}% of the picture tall")
        if el.get("max_lines"):
            bits.append(f"at most {el['max_lines']} lines (break the line rather than shrink it)")
        out.append(", ".join(bits))
    return out


def _words(v):
    return " / ".join(v.get("words") or [])


def build(run, brand, out=None, picture=None, brief=None, vary=None, guides=True, repo=None, check_stage=True,
          runsheet="auto"):
    """Write the handoff folder for one approved ad. Returns the record (also written as `handoff.json`). `runsheet`:
    "auto" packs the brief's run sheet (BRIEF.md, RUN.md, run.json, refs/) into the folder when it is the hand-off's
    own home, True always, False never, a dict packs that sheet (a test's)."""
    repo = Path(repo or P.repo())
    pic = Path(picture) if picture else approved_of(run, brand, repo)
    key, number = brief or brief_of(run)
    key = home_key(brand, key, repo=repo)          # the catalog form, or the folder already there
    label = key
    why = final_stage(run, brand, repo) if check_stage else None
    if why:
        raise BadRequest(why)
    root = Path(out) if out else folder_of(brand, key, repo=repo)
    run_dir = _teardown_run(repo, run, brand)
    vf = run_dir / "out" / "variations.json"
    if not vf.is_file():
        raise BadRequest(f"{run} has no variation list yet (image-writing step 5 writes out/variations.json)")
    rows = json.loads(vf.read_text()).get("variations") or []
    if not rows:
        raise BadRequest(f"{run}'s variation list is empty")
    # the chain's own variations, dry: the exact prompt and numbered inputs per row, nothing spent
    scratch = Path(tempfile.mkdtemp(prefix="handoff-dry-"))
    try:
        s = (vary or vary_recipe)({"brand": brand, "baseline": str(pic), "variations": rows, "dry_run": True, "out": str(scratch)})
        made = {r["id"]: json.loads((scratch / r["id"] / "edit.json").read_text()) for r in s["variations"]}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    refused = {k: r.get("refused") for k, r in made.items() if r.get("state") == "refused"}
    if refused:
        raise BadRequest("the chain refuses these variations, so they cannot be handed off: " +
                         "; ".join(f"{k}: {v}" for k, v in refused.items()))
    (root / "00-approved").mkdir(parents=True, exist_ok=True)   # a second run writes over the same names, deletes nothing
    first = next(iter(made.values()))
    plate = Path(first["plate"])
    plate = plate if plate.is_absolute() else repo / plate
    stem = key
    shutil.copy2(pic, root / "00-approved" / f"{stem}-approved.png")
    shutil.copy2(plate, root / "00-approved" / f"{stem}-approved-clean.png")
    src = next((x for x in (run_dir / "assets").glob("source.*") if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")), None)
    if src:
        shutil.copy2(src, root / "00-approved" / f"swipe{src.suffix.lower()}")
    bars = [float(x) for x in (first.get("bars") or [0, 0])]
    overlay = bars_overlay(bars[0], bars[1], root / "00-approved" / "black-bars-overlay.png")
    rid = first.get("model")
    st = first.get("settings") or {}
    (root / RETURNED).mkdir(exist_ok=True)
    record = {"brand": brand, "run": run, "role": ROLE, "brief": number, "brief_key": key, "label": label,
              "approved": _rel(pic, repo), "made": datetime.now().isoformat(timespec="seconds"),
              "model": rid, "settings": st, "bars": bars, "variations": [], "drive": None}
    for v in rows:
        r = made[v["id"]]
        vdir = root / v["id"]
        vdir.mkdir(exist_ok=True)
        files = []
        ask = r.get("set_request") if r.get("route") == "set" else None
        if ask:
            files = set_files(ask, vdir, repo)
        elif r.get("makes_picture"):
            (vdir / "prompt.md").write_text(r["prompt"].rstrip() + "\n")
            for i in r.get("inputs") or []:
                p = Path(i["path"])
                p = p if p.is_absolute() else repo / p
                name = f"IMAGE-{i['n']}{p.suffix.lower()}"
                shutil.copy2(p, vdir / name)
                files.append({"name": name, "is": i.get("role") or ""})
        guide = None
        if guides and r.get("type_layer"):
            guide = words_guide(plate, r["type_layer"], overlay, vdir / "words-guide.png")
        record["variations"].append({
            "id": v["id"], "label": v.get("label") or v["id"], "words": v.get("words") or [],
            "change": v.get("picture") or "", "makes_picture": bool(r.get("makes_picture")),
            "inputs": files, "prompt": r.get("prompt") if r.get("makes_picture") and not ask else None,
            "route": r.get("route"), "set_request": (ask or {}).get("set"), "print_credits": (ask or {}).get("credits"),
            "caption": caption_says(r.get("type_layer")), "words_guide": bool(guide),
            "name": f"{stem}-{v['id']}.png"})
    record["lessons"] = first.get("lessons") or []
    record["runsheet"] = pack_runsheet(key, brand, root, repo, runsheet if runsheet != "auto" else out is None)
    (root / "rules.md").write_text(rules_md(record["lessons"]))
    (root / "HANDOFF.md").write_text(handoff_md(record))
    (root / "handoff.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    _refresh_index(root, repo)
    return {**record, "folder": str(root)}


def _runsheet_module():
    """components/briefs/runsheet.py, through its public surface (build, pack)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("briefs_runsheet_for_handoff", P.sibling("briefs", "runsheet.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pack_runsheet(key, brand, root, repo=None, how=True, role=ROLE):
    """The brief's run sheet made self-contained in the hand-off folder (2026-10-28: someone in Higgsfield
    Supercomputer with Google Drive and GitHub opens ONE folder and makes the brief with nothing from this Mac):
    BRIEF.md, RUN.md, run.json and refs/ (components/briefs runsheet.pack). Returns what went in, or why not, never
    stopping the hand-off; None when not asked."""
    if how is False or how is None:
        return None
    try:
        RS = _runsheet_module()
        sheet = how if isinstance(how, dict) else RS.build(key, brand=brand, repo=repo)
        got = RS.pack(sheet, folder=root, role=role, repo=repo)
        return {"files": got["files"], "refs": len(got["refs"]), "missing": got["missing"],
                "folder": got["folder"], "drive": got["drive"]}
    except (Exception, SystemExit) as e:  # noqa: BLE001 — the hand-off stands; the record says what is missing
        return {"error": f"{type(e).__name__}: {e}"}


def _refresh_index(root, repo):
    """runs/handoffs/INDEX.md + index.json rebuilt after a handoff lands in its home (2026-10-28). Here only; the CLI copies it to the Drive."""
    try:
        Path(root).resolve().relative_to((Path(repo) / "runs" / HANDOFFS).resolve())
    except ValueError:
        return None                                  # an --out elsewhere is not a hand-off in the queue
    import importlib.util
    spec = importlib.util.spec_from_file_location("image_edit_handoff_index", HOME / "handoff_index.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.quiet_refresh(repo=repo, drive=False)


def set_files(ask, vdir, repo):
    """A picture change on a run with a kept 3D set: the row's set request and the pictures it builds from, never a flat
    prompt (image-production picture_sets.change_request, written by vary_recipe). A flat prompt.md left by an earlier
    pack says where to go instead."""
    (vdir / "set-request.json").write_text(json.dumps(ask, indent=1, ensure_ascii=False) + "\n")
    old = vdir / "prompt.md"
    if old.is_file():
        old.write_text("No flat prompt for this variation: it is a change to the 3D set. Follow set-request.json.\n")
    files = []
    for rel, name, what in ((ask.get("kept_print"), "kept-print", "the set's kept print"),
                            ((ask.get("product") or {}).get("sheet"), "product-sheet", "the product's casting sheet")):
        p = Path(repo) / rel if rel else None
        if p and p.is_file():
            shutil.copy2(p, vdir / f"{name}{p.suffix.lower()}")
            files.append({"name": f"{name}{p.suffix.lower()}", "is": what})
    return files


def rules_md(lessons):
    lines = ["# The rules every picture keeps", "",
             "What the picture chain has learned from the owner's reviews. Each one holds for this ad too.", ""]
    for x in lessons:
        lines.append(f"- **{x['id']}** ({x.get('status', 'draft')}): {x['rule']}")
    return "\n".join(lines) + "\n"


def handoff_md(rec):
    st, key = rec["settings"], rec["brief_key"]
    model = _plain_model(rec["model"])
    knobs = ", ".join(f"{k} {v}" for k, v in st.items() if v and k not in ("size",))
    top, bot = rec["bars"]
    vs = rec["variations"]
    back = f"`{RETURNED}/` in this folder"
    L = [f"# Higgsfield handoff · {rec['brief']} ({key})", "",
         f"For the {rec.get('role', ROLE).replace('-', ' ')}. " + f"the owner approved the first picture of this ad. Make the {len(vs)} variations in Higgsfield Supercomputer, check "
         f"each one, put the words on, and save the finished pictures in {back}.", "",
         "## What is in this folder", "",
         f"- `00-approved/{key}-approved.png`: the approved ad. Every variation should look like this, with one change.",
         f"- `00-approved/{key}-approved-clean.png`: the same picture with no words and no bars. It is IMAGE-1 in every prompt.",
         "- `00-approved/swipe.*`: the ad we copied, for reference only.",
         "- `00-approved/black-bars-overlay.png`: see-through, with the black bars at the swipe's heights. Lay it on top last.",
         "- One folder per variation: `prompt.md` (paste it as is), the `IMAGE-n` pictures it names, and `words-guide.png` "
         "(where the words go and how big).",
         "- `rules.md`: the rules every picture keeps.",
         "- `BRIEF.md`, `RUN.md`, `run.json` and `refs/`: the brief and its run sheet, every step's model, prompt and "
         "settings, with every reference picture it names inside `refs/`. RUN.md section A is for a person clicking in "
         "Higgsfield, section B for an agent." if (rec.get("runsheet") or {}).get("files") else "", "",
         "## Settings in Supercomputer", "",
         f"- Model: **{model}**. {knobs}." if knobs else f"- Model: **{model}**.",
         "- Upload the folder's `IMAGE-n` pictures in number order, so IMAGE-1 is the first picture, IMAGE-2 the second.",
         "- Paste `prompt.md` exactly. Don't add to it or reword it.", "",
         "## The variations", "",
         "| # | What changes | Words on it | How to make it |", "|---|---|---|---|"]
    for v in vs:
        how = (f"3D set change: `{v['id']}/set-request.json`, then the words" if v.get("route") == "set" else
               f"New picture: `{v['id']}/prompt.md` with " + " + ".join(f"`{f['name']}`" for f in v["inputs"])
               if v["makes_picture"] else
               (f"No new picture. `{v['id']}/words-guide.png` is it, already finished: check the words and save it"
                if v["words_guide"] else "No new picture. Put these words on `approved-clean`"))
        L.append(f"| {v['id']} | {v['change'] or 'only the words'} | {_words(v)} | {how} |")
    sets = [v for v in vs if v.get("route") == "set"]
    if sets:
        spend = sum(float(v.get("print_credits") or 0) for v in sets)
        L += ["", "## Variations that change the 3D set", "",
              f"{', '.join(v['id'] for v in sets)}: this ad was printed from a 3D set, so these are made by changing that set, "
              "never as a flat picture. Work in Higgsfield 3D Jutsu from the variation's `set-request.json`: its `steps` in "
              f"order, its `print_words` pasted as they are, and its `flags` read first. {spend:g} credits to print "
              "(one print each; the set and its renders are free). A variation already printed shows 0 credits.", ""]
    L += ["", "## Check every new picture before the words go on", "",
          "Hold it next to `approved-clean`:", "",
          "1. The one change in the table is there and easy to see.",
          "2. Nothing else moved: her face, hair, clothes, pose, the room, the light and the framing are the same.",
          "3. Same grain, softness and colour as the approved picture. Never sharper or cleaner.",
          "4. No writing was added. Lettering on objects (a poster, a label) is still there as it was.",
          "5. One face only, and it is our cast member's face as the approved picture shows it.", "",
          "If it fails, run it once more. If the second is still off, keep the closer one and leave a short note beside "
          "it saying what is off.", "",
          "## Words and finish", ""]
    caps = next((v["caption"] for v in vs if v["caption"]), [])
    if caps:
        L += [f"- Type: {c}." for c in caps]
    L += ["- Match `words-guide.png` in each variation's folder: same place, same size, same style.",
          "- Write the words exactly as the table says. A ` / ` is a new line. Nothing else goes on the picture.",
          f"- Size the finished picture to {FRAME[0]}x{FRAME[1]}, then lay `black-bars-overlay.png` on top"
          + (f" (black bars: top {top}%, bottom {bot}%)." if (top or bot) else "."), "",
          "## Naming", "",
          f"Save each finished picture into {back} as `{key}-<variation>.png`:", ""]
    L += [f"- `{v['name']}`" for v in vs]
    L += ["", f"One folder per brief, named `{key}`. The brief number ({rec['brief']}) stays in the folder name and every "
          "file name, with the brand and product in front of it, because two brands or products can share a number: that "
          "is how the delivery check finds each picture's brief and puts it on the Meta approval page.", ""]
    return "\n".join(L)


def mirror_folder(folder, svc=None, find_engine=None, repo=None):
    """One hand-off folder onto the Shared Assets drive under the same words as its repo path, through gdrive-creator by
    key (builder card rule 4), with its `returned` folder. Same name = updated in place; nothing is deleted. Returns
    {"link", "label", "id", "files"}."""
    import sys
    gc = P.sibling("gdrive-creator")
    if str(gc) not in sys.path:
        sys.path.append(str(gc))
    from gdrive_creator import engine as E, reach  # noqa: E402
    E = find_engine() if find_engine else E
    parts = drive_parts(folder, repo)
    svc = svc or E.service()
    dest = reach.folder_id(parts, svc, make=True, find_engine=lambda: E)
    ids = E.mirror_tree(str(folder), dest, svc)
    E.folder(RETURNED, dest, svc=svc)
    return {"id": dest, "label": "Shared Assets/" + "/".join(parts), "link": f"https://drive.google.com/drive/folders/{dest}",
            "files": ids}


def to_drive(rec, svc=None, find_engine=None, repo=None):
    """Copy the folder to the Shared Assets drive under the same words as its repo path (runs/handoffs/<role>/<brand>/
    <brief key>/), with its empty `returned` folder for what comes back. Returns {"link", "label", "id", "files"}; a missing key
    or drive is refused by name, never guessed around."""
    import sys
    folder = P.sibling("gdrive-creator")
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    from gdrive_creator import engine as E, reach  # noqa: E402
    E = find_engine() if find_engine else E
    parts = drive_parts(rec["folder"], repo)
    svc = svc or E.service()
    dest = reach.folder_id(parts, svc, make=True, find_engine=lambda: E)
    ids = E.mirror_tree(rec["folder"], dest, svc)
    E.folder(RETURNED, dest, svc=svc)
    out = {"id": dest, "label": "Shared Assets/" + "/".join(parts), "link": f"https://drive.google.com/drive/folders/{dest}",
           "files": ids}
    f = Path(rec["folder"]) / "handoff.json"
    saved = json.loads(f.read_text())
    saved["drive"] = {k: out[k] for k in ("id", "label", "link")}
    f.write_text(json.dumps(saved, indent=1, ensure_ascii=False))
    return out
