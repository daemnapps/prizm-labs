#!/usr/bin/env python3
"""THE RUN SHEET: one brief, made the same way from any tool.

    python3 components/briefs/runsheet.py <brief key or number> [--brand b] [--out DIR]
    python3 components/briefs/runsheet.py acme_crush_brief-0004
    python3 components/briefs/runsheet.py brief-0004 --brand acme
    python3 components/briefs/runsheet.py acme_crush_brief-0004 --prompt 1     print step 1's prompt, verbatim

    import runsheet
    runsheet.build("acme_crush_brief-0004")          -> dict (the run.json content)
    runsheet.write("acme_crush_brief-0004")          -> {"md": path, "json": path}
    runsheet.pack(sheet[, folder, role])             -> the hand-off copy: BRIEF.md, RUN.md, run.json, refs/ in
                                                        runs/handoffs/<role>/<brand>/<brief key>/ (the hand-off writers call it)

2026-10-28: every brief runs the same way from any tool (Higgsfield web app, Claude Code, Codex): the workflow and the
briefs are agent-agnostic, and Higgsfield is the core underneath all of them.

The brief says WHAT to make (the ad, the words, the shots). Beside it, the run sheet says exactly HOW: one shared core
of Higgsfield calls (model, prompt, reference elements, settings, output name, return place), then three thin
renderings of that same core: (a) the Higgsfield web app, for a person clicking; (b) Claude Code, for an agent with the
Higgsfield MCP and this repo; (c) Codex or any other agent, as API-shaped steps plus repo commands. Every rendering ends
with the same return step. Written as RUN.md (people) and run.json (machines) into the brief's own deliverable/ folder.

Nothing is written here that a chain also writes: the picture prompt and references are model-inputs' preview builder
(the same builder the Prompt Bench's Make button and the image hand-off use); a clip's prompt is the video chain's own
Seedance builder (preview.build_clip); the model is the Generative Model House's; product elements are the product
index's (runs/ai-elements/PRODUCT-INDEX.json); cast, set and prop elements come from runs/ai-elements/ELEMENTS-INDEX.json
once that index exists. Generates nothing, spends nothing, sends nothing; no key, no network. Every path it writes is
repo-relative or a "Shared Assets/..." label, never a machine path. Python 3.9.
"""
import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
REPO = COMP.parent
CORE = "higgsfield"
RETURN_DIR = "returned"
LANES = {"image": "graphic-designer", "sequence": "graphic-designer", "video": "video-editor"}   # = image-edit handoff.LANES
# What Higgsfield's element tool lists as honouring a <<<element id>>> in the prompt (manage_reference_elements, read
# 2026-10-28), plus gpt_image_2_5, proven by test the same night (generation dec7526e: Higgsfield's own record lists the
# element under reference_elements). seedance_2_5 is still unproven.
ELEMENT_MODELS = ("nano_banana_pro", "nano_banana_2", "gpt_image_2", "gpt_image_2_5", "seedream_v4_5", "seedream_v5_lite",
                  "cinematic_studio_2_5", "cinematic_studio_video_v2", "cinematic_studio_3_0", "seedance_2_0", "kling3_0")
# What the same test showed: an element carries ONE of its pictures into the job (the first), where the file route
# sends every side the step names. For a product shown up close or in a hand, the files are the more faithful path.
ELEMENT_ONE_PICTURE = ("An element sends only its first picture into the job; the refs/ files send every side this "
                       "step names. Where the product is up close or in a hand, use the files.")
PLAIN_MODEL = {"gpt_image_2_5": "GPT Image 2.5", "seedance_2_5": "Seedance 2.5", "seedance_2_0": "Seedance 2.0", "seedream_5_pro": "Seedream 5 Pro",
               "kling4_0": "Kling 4.0", "nano_banana_pro": "Nano Banana Pro"}
ELEMENT_KINDS = {"products": "product", "casting": "cast", "sets": "set", "props": "prop"}


# ------------------------------------------------------------------------------------------------ loading the chain

def _teardown_run(repo, run, brand=None):
    """A picture run's folder on the image-teardown plane: runs/image-teardown/<brand>/<run>/, its one home since
    2026-10-28 (components/naming/WHERE-EVERYTHING-GOES-owner.md item 4). The old lane folder
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


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent))
    spec.loader.exec_module(mod)
    return mod


class Chain:
    """The chain's own builders, loaded on first use. A test hands in its own (no repo, no model, no network)."""

    def __init__(self, repo=None):
        self.repo = Path(repo or REPO)
        self._pv = self._reg = self._house = self._sets = None

    def preview(self):
        if self._pv is None:
            self._pv = _load(self.repo / "components" / "model-inputs" / "preview.py", "runsheet_preview")
        return self._pv

    def register(self):
        if self._reg is None:
            self._reg = _load(self.repo / "tools" / "image-teardown" / "tools" / "briefs.py", "runsheet_register")
        return self._reg

    def lookup(self, what, brand=None):
        """(register key, record) for a brief key, brief-NNNN, pNNN or a bare number."""
        R = self.register()
        k, r = R.get(R.load(), str(what), brand=brand)
        if not r:
            raise SystemExit(f"{what} is not in the brief register (tools/image-teardown/briefs.json)")
        return k, r

    def house(self, job):
        if self._house is None:
            self._house = _load(self.repo / "components" / "generative-model-house" / "model_house.py", "runsheet_house")
        m = self._house.model(job)
        return {"job": job, "registry": m.get("registry_id") or m.get("registry"), "door": m.get("door"),
                "higgsfield_model": m.get("model") or m.get("id")}

    def picture(self, recipe):
        """The exact picture the static chain would send for this recipe (model-inputs preview, no quote)."""
        return self.preview().preview("pictures.generate", recipe, quote=False)

    def variation(self, brief, change, approved):
        return self.preview().variation_brief(brief, change, approved=approved)

    def needs_picture(self, change):
        return self.preview().needs_picture(change)

    def clip(self, run, call=None):
        return self.preview().build_clip({"run": run, **({"call": call} if call else {})})

    def set_change(self, brand, run, variation, change, brief):
        """A picture change on a run with a kept 3D set, as a set request (image-production picture_sets, the same call
        image-edit's vary_recipe makes), or None when the run has no kept set. Nothing is spent."""
        f = self.repo / "tools" / "image-production" / "picture_sets.py"
        if self._sets is None:
            self._sets = _load(f, "runsheet_picture_sets") if f.is_file() else False
        S = self._sets
        found = S.kept(brand, run) if S else None
        if not found:
            return None
        ask = S.change_request(brand, found, variation, change, brief)
        if S.kept_change(brand, found["set"], variation, ask["change"]):
            ask["credits"] = 0                                 # the print is already made
        return ask

    def _image_edit(self):
        folder = str(self.repo / "tools" / "image-edit")
        if folder not in sys.path:
            sys.path.append(folder)
        import image_edit
        return image_edit

    def slides(self, brief_file):
        """(the AI sequence brief's slide-delta rows, why not): image-edit's own reader, so a run sheet takes exactly what
        sequence.py would take."""
        IE = self._image_edit()
        try:
            return IE.deltas_from(brief_file), None
        except IE.BadRequest as e:
            return [], str(e)

    def slide(self, brand, n, change, keep):
        """One later slide's exact instruction and any refusal, from image-edit's resolver: the same delta sequence.py
        sends (kind `slide`, the thread check), nothing spent. The resolver only asks that a reference exists, so a
        stand-in file serves while slide one is not made yet."""
        import tempfile
        IE = self._image_edit()
        with tempfile.NamedTemporaryFile(suffix=".png") as stand_in:
            r = IE.resolve({"brand": brand, "picture": stand_in.name, "change": change, "kind": "slide", "keep": keep,
                            "checks": [IE.engine.thread_check(n)], "dry_run": True})
        return {"instruction": r["instruction"], "refused": r["refused"]}

    def products(self):
        f = self.repo / "runs" / "ai-elements" / "PRODUCT-INDEX.json"
        return json.loads(f.read_text()).get("products", {}) if f.is_file() else {}

    def elements(self):
        """The cast/set/prop element index a later helper builds; {} until it exists."""
        f = self.repo / "runs" / "ai-elements" / "ELEMENTS-INDEX.json"
        try:
            return json.loads(f.read_text()) if f.is_file() else {}
        except ValueError:
            return {}


# ------------------------------------------------------------------------------------------------ small helpers

def rel(p, repo=REPO):
    """A path as a run sheet may print it: repo-relative, or its bare name when it sits outside the repo."""
    if not p:
        return ""
    s = str(p)
    if "(not " in s:                                         # "S1-F1 (not made yet)"
        return s
    try:
        return str(Path(s).resolve().relative_to(Path(repo).resolve()))
    except (ValueError, OSError):
        return Path(s).name


def scrub(text, repo=REPO):
    """A chain's text with any machine path into the repo made repo-relative (a prompt never carries /Users/...)."""
    t = str(text or "")
    for root in {str(Path(repo)), str(Path(repo).resolve())}:
        t = t.replace(root + "/", "").replace(root, ".")
    return t


def exists(p, repo=REPO):
    if not p or "(not " in str(p):
        return False
    q = Path(p)
    return (q if q.is_absolute() else Path(repo) / q).is_file()


def asset_name(key, n, ext):
    return f"{key}_asset-{n:02d}.{ext}"


def handoff_folder(key, brand, role):
    """The hand-off's one folder, repo-relative: runs/handoffs/<role>/<brand>/<brief key> (the Drive copy is the same
    words under Shared Assets/, since 2026-10-28)."""
    return f"runs/handoffs/{role}/{brand}/{key}"


def home_key(key, brand, repo=None):
    """The brief key a run sheet names its hand-off folder and files with: a hand-off folder already there in any
    spelling of the key keeps its name (nothing is renamed), else the catalog form (names.catalog_key, 2026-10-28: the
    catalog id wins, store handles are aliases)."""
    try:
        N = _load(Path(repo or REPO) / "components" / "naming" / "names.py", "runsheet_names")
        forms = N.brief_key_forms(key)
    except Exception:  # noqa: BLE001 — no naming beside this one: the key as given
        return key
    base = Path(repo or REPO) / "runs" / "handoffs"
    for f in [key] + forms:
        if any((base / role / str(brand) / f).is_dir() for role in set(LANES.values())):
            return f
    return forms[0] if forms else key


# The receipt beside every returned file (2026-10-28): what was really sent, so image-edit reference_check.py can prove it against the step.
RECEIPT_FIELDS = ["asset", "step", "higgsfield_generation_id", "model", "prompt", "inputs", "settings", "made_by", "made_at"]
# Higgsfield's OWN record of the generation, saved unchanged by an agent: the authority reference_check.py reads first
# (the maker's receipt is a person's word; the record is what Higgsfield actually ran). The public API cannot read a
# web-app or MCP generation back, so the agent that made it saves it.
RECORD_WHAT = ("the generation record exactly as the Higgsfield tool returns it (show_generations or "
               "show_generation_by_ids for the generation id: id, model, params.prompt, params.medias, "
               "params.reference_elements, the settings, results), saved unchanged, never retyped or trimmed")


def return_place(key, brand, role):
    tail = f"{handoff_folder(key, brand, role)}/{RETURN_DIR}/"
    return {"role": role, "name_pattern": f"{key}_asset-NN.<ext>", "repo": tail, "drive": f"Shared Assets/{tail}",
            "receipt": {"name_pattern": f"{key}_asset-NN.receipt.json", "fields": RECEIPT_FIELDS,
                        "or_link": f"{key}_asset-NN.link.txt", "checked_by": "tools/image-edit/reference_check.py",
                        "record": {"name_pattern": f"{key}_asset-NN.record.json", "what": RECORD_WHAT,
                                   "who": "an agent with the Higgsfield tools; it outranks the receipt"}},
            "text_from": TEXT_FROM_GITHUB}


def element_of(path, brand, products, elements, repo=REPO):
    """What a reference file IS in the element bank: {kind, id, folder, element: {id, name} | None} or None."""
    r = rel(path, repo)
    m = re.match(r"runs/ai-elements/([^/]+)/(products|casting|sets|props)/([^/]+)/", r)
    if not m:
        return None
    b, group, eid = m.groups()
    kind, folder = ELEMENT_KINDS[group], f"runs/ai-elements/{b}/{group}/{eid}"
    hf = None
    if kind == "product":
        # A product goes by its casting sheet file, never its element: an element carries one picture, frozen when it was
        # made, so it falls behind the sheet. hf stays None, and the step uploads the current sheet instead.
        e = products.get(f"{b}/{eid}") or {}
        name = e.get("name") or eid
    else:
        hf = _element_from_index(elements, b, group, eid, folder)
        name = eid
    hf = {"id": hf.get("id"), "name": hf.get("name")} if hf and hf.get("id") else None
    return {"kind": kind, "id": eid, "name": name, "brand": b, "folder": folder, "element": hf}


def _element_from_index(idx, brand, group, eid, folder):
    """Lenient read of ELEMENTS-INDEX.json (its shape is the later helper's call): any entry keyed or pathed to this
    folder that carries a higgsfield element id."""
    if not idx:
        return None
    pool = idx.get("elements", idx) if isinstance(idx, dict) else idx
    if isinstance(pool, dict) and any(isinstance(pool.get(g), dict) for g in ("people", "sets", "props")):
        # casting's elements_index.py shape: {people|sets|props: {"<brand>/<id>": entry}}, the element on `assets`
        pool = {k: {**v, "higgsfield_element": (v.get("assets") or {}).get("higgsfield_element") or v.get("higgsfield_element")}
                for g in ("people", "sets", "props") for k, v in (pool.get(g) or {}).items() if isinstance(v, dict)}
    items = pool.items() if isinstance(pool, dict) else enumerate(pool if isinstance(pool, list) else [])
    keys = {f"{brand}/{group}/{eid}", f"{brand}/{ELEMENT_KINDS[group]}/{eid}", f"{brand}/{eid}", folder}
    for k, v in items:
        if not isinstance(v, dict):
            continue
        hit = str(k) in keys or v.get("folder") in keys or v.get("path") in keys or (
            v.get("id") == eid and v.get("brand") in (None, brand) and v.get("kind") in (None, ELEMENT_KINDS[group], group))
        if hit:
            hf = v.get("higgsfield_element") or v.get("element") or {}
            if isinstance(hf, str):
                hf = {"id": hf}
            if hf.get("id"):
                return hf
    return None


def product_slug(brand, product, products, repo=REPO):
    """The product index's own slug for a brief's product word (`crush` -> `crush-serum`), off each kit's aliases."""
    if not product:
        return None
    if f"{brand}/{product}" in products:
        return product
    mine = [(k, e) for k, e in sorted(products.items()) if k.startswith(brand + "/")]
    for key, e in mine:                                     # a kit's own alias wins
        kit = (e.get("assets") or {}).get("kit")
        try:
            aliases = (json.loads((Path(repo) / kit).read_text()).get("aliases") or []) if kit else []
        except (OSError, ValueError):
            aliases = []
        if str(product).lower() in [str(a).lower() for a in aliases]:
            return key.split("/", 1)[1]
    hits = [k for k, _ in mine if k.split("/", 1)[1].startswith(str(product) + "-")]
    return hits[0].split("/", 1)[1] if len(hits) == 1 else None


def _title(md, fallback):
    for line in md.splitlines():
        if line.startswith("# ") and "DOCUMENT" not in line.upper():
            # the standard brief's title line is "BRIEF · <brand> · <product> · <name>": the run sheet names the brand itself
            return re.sub(r"^BRIEF\s*·\s*[^·]+·\s*", "", line[2:].strip())
    return fallback


NOT_WORDS = re.compile(r"(?i)^\s*(unchanged|none|n/?a|-|—)?\s*$")


def _words(w):
    """Words on the ad as one line, a line break shown as ' / ' (the brief's own spelling)."""
    return " / ".join(x.strip() for x in str(w).splitlines() if x.strip())


# ------------------------------------------------------------------------------------------------ picture briefs

def _approved(brand, run, repo):
    """The run's approved picture (newest Looks good), its recipe and its plate (the picture without words)."""
    bench = Path(repo) / "runs" / "image-production" / brand / "prompt-bench"
    liked = sorted(bench.glob(f"{run}-*.liked.json"), key=lambda f: f.name) if bench.is_dir() else []
    if not liked:
        return None
    stem = liked[-1].name[:-len(".liked.json")]
    rec = bench / f"{stem}.recipe.json"
    # the plate (no words) sits beside the picture or in generated/ (image-edit's vary_recipe reads both); the picture
    # itself carries its words, so it is the last resort (brief 0341, 2026-10-28: IMAGE 1 went in with its caption)
    plate = next((p for p in (bench / f"{stem}.plate.png", bench / "generated" / f"{stem}.plate.png") if p.is_file()),
                 bench / f"{stem}.png")
    return {"picture": bench / f"{stem}.png", "recipe": rec if rec.is_file() else None, "plate": plate}


def _picture_step(n, key, what, pv, house, brand, products, elements, repo, source):
    refs = []
    for i in pv.get("inputs") or []:
        el = element_of(i["path"], brand, products, elements, repo)
        role = i["role"]
        if i["n"] == 1 and str(i["path"]).endswith(".plate.png"):
            role = "the approved picture without its words (the plate): the variation is an edit of it"
        refs.append({"n": i["n"], "kind": "image", "role": role, "file": rel(i["path"], repo),
                     "exists": exists(i["path"], repo), "element": el})
    f = pv.get("fields") or {}
    s = pv.get("settings") or {}
    send = pv.get("send") or {}
    on_top = f.get("words_mode") == "set on top after"
    zones = f.get("zones") or []
    words = [(zones[i] if i < len(zones) else f"line {i + 1}", _words(w))
             for i, w in enumerate(f.get("words_plain") or f.get("our_copy") or [])]
    words = [(z, w) for z, w in words if not NOT_WORDS.match(w)]
    bars = send.get("bars") or [0, 0]
    return {"n": n, "asset": asset_name(key, n, "png"), "what": what, "medium": "image",
            "job": house["job"], "model_house": {"registry": house["registry"], "door": house["door"]},
            "higgsfield_model": pv.get("vendor_model") or house["higgsfield_model"],
            "model_name": PLAIN_MODEL.get(pv.get("vendor_model") or house["higgsfield_model"], pv.get("vendor_model")),
            "prompt": scrub(pv.get("prompt"), repo), "prompt_source": source,
            "references": refs,
            "settings": {"aspect_ratio": s.get("aspect") or "9:16", "variant": s.get("variant"), "quality": s.get("quality"),
                         "resolution": s.get("resolution"), "count": 1},
            "words_on_top": [{"zone": z, "words": w} for z, w in words] if on_top else [],
            "bars": {"top": bars[0], "bottom": bars[1]} if any(bars) else None,
            "findings": [x["say"] for x in pv.get("findings") or [] if x.get("level") == "error"]}


def _words_only_step(n, key, what, change, plate, repo, zones=()):
    return {"n": n, "asset": asset_name(key, n, "png"), "what": what, "medium": "image", "job": "words-only",
            "model_house": None, "higgsfield_model": None, "model_name": None,
            "prompt": "", "prompt_source": "no new picture: a words-only variation sets new words on the approved plate",
            "references": [{"n": 1, "kind": "image", "role": "the approved picture without its words (the plate)",
                            "file": rel(plate, repo), "exists": exists(plate, repo), "element": None}],
            "settings": {"aspect_ratio": "9:16", "count": 1},
            "words_on_top": [{"zone": zones[i] if i < len(zones) else f"line {i + 1}", "words": _words(w)}
                             for i, w in enumerate(change.get("words") or []) if not NOT_WORDS.match(_words(w))],
            "bars": None, "findings": []}


def _set_step(n, key, what, ask, change, zones, brand, products, elements, repo):
    """A variation that changes the kept 3D set: built and printed in Higgsfield 3D Jutsu from its set request, never
    sent as a flat picture. `prompt` is the print's words; the numbered work is the request's own `steps`."""
    refs = []
    for path, role in ((ask.get("kept_print"), "the set's kept print: what the changed set must still look like"),
                       ((ask.get("product") or {}).get("sheet"), "the product's casting sheet: upload it fresh for the print")):
        if path:
            refs.append({"n": len(refs) + 1, "kind": "image", "role": role, "file": rel(Path(repo) / path, repo), "exists": exists(path, repo),
                         "look_only": "kept print" in role,        # compared against, never sent to the print
                         "element": element_of(Path(repo) / path, brand, products, elements, repo)})
    return {"n": n, "asset": asset_name(key, n, "png"), "what": what, "medium": "image", "job": "set-change",
            "model_house": None, "higgsfield_model": None, "model_name": "Higgsfield 3D Jutsu",
            "prompt": scrub(ask.get("print_words"), repo), "prompt_source": "image-production picture_sets: the print's words",
            "references": refs, "settings": {"aspect_ratio": "9:16", "resolution": "2k", "count": 1},
            "words_on_top": [{"zone": zones[i] if i < len(zones) else f"line {i + 1}", "words": _words(w)}
                             for i, w in enumerate(change.get("words") or []) if not NOT_WORDS.match(_words(w))],
            "bars": None, "findings": [], "set_request": json.loads(scrub(json.dumps(ask, ensure_ascii=False), repo))}


def picture_steps(key, rec, chain, products, elements, repo):
    brand, run = rec["brand"], rec["run"]
    house = chain.house("pictures.generate")
    ap = _approved(brand, run, repo)
    if ap and ap["recipe"]:
        approved = json.loads(ap["recipe"].read_text())
        recipe = {"brief": approved["brief"], "sheet": {k: v for k, v in (approved.get("sheet") or {}).items()
                                                        if (v or {}).get("source") == "person"}}
        source = (f"model-inputs preview builder, replaying the approved picture's own recipe "
                  f"({rel(ap['recipe'], repo)})")
    else:
        approved = {"brief": {"brand": brand, "run": run, "product": rec.get("product") or ""}}
        recipe = approved["brief"]
        source = "model-inputs preview builder, from the brief's run (no approved picture yet)"
    steps = [_picture_step(1, key, "the main picture" + (" (the approved one: remake only if it is lost)" if ap else ""),
                           chain.picture(recipe), house, brand, products, elements, repo, source)]
    vf = _teardown_run(repo, run, brand) / "out" / "variations.json"
    vs = json.loads(vf.read_text()) if vf.is_file() else {}
    for v in (vs.get("variations") or []) if vs.get("source") == "stage5" else []:
        n = len(steps) + 1
        change = {k: v[k] for k in ("words", "picture", "swap", "stays_drop", "people", "person") if v.get(k) is not None}
        what = f"variation {v.get('id')}: {v.get('label') or ''}".strip()
        plate = ap["plate"] if ap else None
        if not chain.needs_picture(change):
            zones = [w["zone"] for w in steps[0]["words_on_top"]]
            steps.append(_words_only_step(n, key, what, change, plate or "(not made yet: the approved plate)", repo, zones))
            continue
        b = chain.variation(approved["brief"], change, plate if (plate and Path(plate).is_file()) else None)
        ask = chain.set_change(brand, run, v.get("id"), change, b)
        if ask:
            zones = [w["zone"] for w in steps[0]["words_on_top"]]
            steps.append(_set_step(n, key, what, ask, change, zones, brand, products, elements, repo))
            continue
        pv = chain.picture({"brief": b, "sheet": recipe.get("sheet") if isinstance(recipe, dict) and "sheet" in recipe else {}})
        steps.append(_picture_step(n, key, what, pv, house, brand, products, elements, repo,
                                   "model-inputs variation_brief + preview builder: ONE change off the approved picture"
                                   if plate else "model-inputs variation_brief + preview builder (no approved picture yet: "
                                   "made from the swipe, not as an edit)"))
    return steps


# ------------------------------------------------------------------------------------------------ carousel briefs

def sequence_steps(key, rec, bf, chain, products, elements, repo):
    """A carousel: slide one is a picture like any other (replayed from its approved recipe, or from the brief's run);
    every later slide is ONE edit off slide one, the brief's own slide-deltas block read as image-edit sequence.py reads
    it. Returns (steps, gaps): a brief with no block, or a refused slide, is said by name, never guessed around."""
    brand, run = rec["brand"], rec["run"]
    house = chain.house("pictures.generate")
    ap = _approved(brand, run, repo)
    if ap and ap["recipe"]:
        approved = json.loads(ap["recipe"].read_text())
        recipe = {"brief": approved["brief"], "sheet": {k: v for k, v in (approved.get("sheet") or {}).items()
                                                        if (v or {}).get("source") == "person"}}
        source = f"model-inputs preview builder, replaying slide one's approved recipe ({rel(ap['recipe'], repo)})"
    else:
        recipe = {"brand": brand, "run": run, "product": rec.get("product") or ""}
        source = "model-inputs preview builder, from the brief's run (slide one not approved yet)"
    steps = [_picture_step(1, key, "slide 1: the plate every later slide is edited from"
                           + (" (the approved one: remake only if it is lost)" if ap else ""),
                           chain.picture(recipe), house, brand, products, elements, repo, source)]
    gaps = []
    if not ap:
        gaps.append("Slide one has no approved picture yet: step 1 makes it, and every later slide is an edit of it, "
                    "so check step 1 before going on.")
    rows, why = chain.slides(bf) if bf else ([], "no written brief")
    if why:
        gaps.append(f"Only slide 1 is on this sheet: {why}")
    first = steps[0]
    plate = (rel(ap["plate"], repo) if ap else f"{first['asset']} (not made yet: step 1 makes it, before its words go on)")
    for r in rows:
        n, change = int(r["slide"]), str(r["change"]).strip()
        got = chain.slide(brand, n, change, list(r.get("keep") or []))
        layer = [t for t in r["type"] if isinstance(t, dict)] if isinstance(r.get("type"), list) else []   # or a slide-type word
        if got["refused"]:
            gaps.append(f"slide {n}: the edit rule refuses it ({got['refused']}) Narrow it in the brief.")
        steps.append({"n": len(steps) + 1, "asset": asset_name(key, len(steps) + 1, "png"),
                      "what": f"slide {n}: one change off slide 1", "medium": "image", "job": first["job"],
                      "model_house": first["model_house"], "higgsfield_model": first["higgsfield_model"],
                      "model_name": first["model_name"], "prompt": scrub(got["instruction"], repo),
                      "prompt_source": "image-edit's edit instruction (the one sequence.py sends): ONE change off slide 1",
                      "references": [{"n": 1, "kind": "image", "exists": exists(plate, repo), "file": plate, "element": None,
                                      "role": "the approved picture without its words (the plate): this slide is an edit of it"
                                      if ap else "slide 1 without its words (the plate): this slide is an edit of it"}],
                      "settings": dict(first["settings"]),
                      "words_on_top": [{"zone": t.get("element") or f"line {i + 1}", "words": _words(t.get("text"))}
                                       for i, t in enumerate(layer) if not NOT_WORDS.match(_words(t.get("text")))],
                      "type_layer": layer, "bars": None, "findings": [], "slide": n})
    return steps, gaps


# ------------------------------------------------------------------------------------------------ video briefs

def _video_run(rec, key, repo):
    base = Path(repo) / "runs" / "video-production" / rec["brand"]
    for name in (key, str(rec.get("run") or "").rstrip("/").split("/")[-1]):
        if name and (base / name / "storyboard.json").is_file() and (base / name / "plan.json").is_file():
            return f"{rec['brand']}/{name}"
    return None


def _cast_folders(prun, repo):
    """person NAME -> its casting folder, off the production run's elements lock."""
    f = Path(repo) / "runs" / "video-production" / prun / "elements-lock.json"
    out = {}
    try:
        for it in json.loads(f.read_text()).get("items") or []:
            m = re.match(r"^(person|setting|product|prop)\s+(.+?)\s+→\s*(\S*)$", str(it))
            if m and m.group(3):
                out[(m.group(1), m.group(2).strip())] = m.group(3).rstrip("/")
    except (OSError, ValueError):
        pass
    return out


def _el_for_folder(folder, brand, products, elements, repo):
    return element_of(str(Path(repo) / folder) + "/x", brand, products, elements, repo) if folder else None


def clip_steps(key, rec, prun, chain, products, elements, repo):
    house = chain.house("clips.seedance")
    first = chain.clip(prun)
    lock = _cast_folders(prun, repo)
    steps = []
    for c in first.get("calls") or []:
        b = first if c["id"] == (first.get("fields") or {}).get("call") else chain.clip(prun, c["id"])
        s, send = b.get("settings") or {}, b.get("send") or {}
        talking = bool(s.get("audio"))
        refs = []
        for i in b.get("inputs") or []:
            role = i.get("role", "")
            # the door's roles: a talking clip (or one with motion references) carries the start picture as an image
            # reference beside the voice; a silent one carries start and end pictures (the two cannot mix)
            if i.get("kind") == "audio":
                mrole = "audio_references"
            elif i.get("kind") == "video":
                mrole = "video_references"
            elif talking or send.get("videos"):
                mrole = "image_references"
            else:
                mrole = "start_image" if "start" in role else "end_image"
            refs.append({"n": len(refs) + 1, "kind": i.get("kind", "image"), "role": role, "media_role": mrole,
                         "file": rel(i["path"], repo), "exists": exists(i["path"], repo), "element": None})
        cast = []
        for who in send.get("masters_people") or []:
            folder = lock.get(("person", who))
            cast.append({"who": who, "folder": folder, "element": (_el_for_folder(folder, rec["brand"], products, elements, repo)
                                                                  or {}).get("element")})
        mode = "reference-to-video" if (talking or send.get("videos")) else "image-to-video"
        steps.append({"n": len(steps) + 1, "asset": asset_name(key, len(steps) + 1, "mp4"),
                      "what": f"clip {c['id']} · {', '.join(c.get('scenes') or [])} · {s.get('duration')} s · "
                              + ("talking, lips to the voice read" if talking else "silent"),
                      "medium": "video", "job": house["job"],
                      "model_house": {"registry": house["registry"], "door": house["door"]},
                      "higgsfield_model": house["higgsfield_model"],
                      "model_name": PLAIN_MODEL.get(house["higgsfield_model"], house["higgsfield_model"]),
                      "prompt": scrub(b.get("prompt"), repo),
                      "prompt_source": f"the video chain's own Seedance builder (model-inputs preview.build_clip on "
                                       f"runs/video-production/{prun}, call {c['id']})",
                      "references": refs, "cast": cast,
                      "settings": {"aspect_ratio": s.get("aspect") or "9:16", "duration": s.get("duration"),
                                   "resolution": s.get("resolution"), "generate_audio": talking,
                                   "endpoint": f"bytedance/seedance-2.5/{mode}", "count": 1},
                      "words_on_top": [], "bars": None, "findings": []})
    return steps


def _brief_json(md):
    m = re.search(r"```json\n(.*?)\n```", md, re.S)
    try:
        d = json.loads(m.group(1)) if m else {}
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}          # a carousel's first block can be its slide-deltas list


def _cast_master(folder, repo):
    for f in ("full/master.png", "master.png", "master.jpg", "sheets/master-reference.jpg", "sheets/headshot.jpg"):
        if (Path(repo) / folder / f).is_file():
            return f"{folder}/{f}"
    return None


def draft_steps(key, rec, md, chain, products, elements, repo):
    """No production run yet: one start picture and one clip per scene, drafted from the brief's own scene record.
    Marked as drafts: the exact prompts come from video production once it has built the run."""
    d = _brief_json(md)
    brand = rec["brand"]
    ph, ch = chain.house("pictures.generate"), chain.house("clips.seedance")
    piece = d.get("piece") or {}
    song_ad = piece.get("format") == "song-ad"
    res = str(piece.get("resolution") or "480p")
    cast = {}
    for c in d.get("cast") or []:
        bank = c.get("bank_id")
        folder = f"runs/ai-elements/{brand}/casting/{bank}" if bank and bank != "NEW" and (Path(repo) / "runs" / "ai-elements" / brand / "casting" / bank).is_dir() else None
        el = _el_for_folder(folder, brand, products, elements, repo) if folder else None
        cast[c.get("id") or c.get("name")] = {"who": c.get("name") or c.get("id"), "folder": folder,
                                              "master": _cast_master(folder, repo) if folder else None,
                                              "element": (el or {}).get("element")}
    slug = product_slug(brand, piece.get("product") or rec.get("product"), products, repo)
    steps = []
    for sc in d.get("scenes") or []:
        ff = sc.get("first_frame") or {}
        who = [w for w in cast if w and w in str(sc.get("who") or "")]
        refs = []
        for w in who:
            c = cast[w]
            refs.append({"n": len(refs) + 1, "kind": "image", "role": f"{c['who']}, our cast member (face and body)",
                         "file": c["master"] or f"{w} (not banked yet)", "exists": exists(c["master"], repo),
                         "element": ({"kind": "cast", "id": Path(c["folder"]).name, "name": c["who"], "folder": c["folder"],
                                      "element": c["element"]} if c["folder"] else None)})
        prompt = "\n".join(x for x in (
            ff.get("subject"), ff.get("composition"), ff.get("action"), ff.get("location"),
            ff.get("lighting"), ff.get("camera"), ff.get("style")) if x)
        if not prompt:
            continue
        n = len(steps) + 1
        steps.append({"n": n, "asset": asset_name(key, n, "png"), "what": f"start picture for {sc.get('id')}",
                      "medium": "image", "job": ph["job"], "model_house": {"registry": ph["registry"], "door": ph["door"]},
                      "higgsfield_model": ph["higgsfield_model"], "model_name": PLAIN_MODEL.get(ph["higgsfield_model"]),
                      "prompt": prompt, "prompt_source": "DRAFT from the brief's scene record (first_frame); video "
                      "production has not built this brief yet, so this is not the chain's exact prompt",
                      "references": refs, "settings": {"aspect_ratio": "9:16", "variant": "sunburst", "quality": "high",
                                                       "resolution": "2k", "count": 1},
                      "words_on_top": [], "bars": None, "findings": [], "draft": True})
        shot_lines = []
        for sh in sc.get("shots") or []:
            g = sh.get("gestures")
            g = "; ".join(g) if isinstance(g, list) else (g or "")
            says = " ".join(str(l.get("say") or "") for l in sh.get("lines") or [])
            shot_lines.append(" ".join(x for x in (
                f"{sh.get('id')}: {sh.get('angle') or ''}, {sh.get('camera_move') or 'hold'}.",
                f"Face: {sh.get('face')}." if sh.get("face") else "", f"Hands: {g}." if g else "",
                f"{'Song lyric timing reference' if song_ad else 'Says'}: \"{says}\"" if says else "", f"Ends on: {sh.get('ends_on')}." if sh.get("ends_on") else "") if x))
        talking = bool(sc.get("to_camera")) if song_ad else bool(sc.get("voice"))
        ch = chain.house("clips.song_ad" if song_ad and talking else "clips.seedance")
        endpoint = ch["registry"]
        n = len(steps) + 1
        steps.append({"n": n, "asset": asset_name(key, n, "mp4"), "what": f"clip for {sc.get('id')} · "
                      + ("singing to the approved Suno slice" if song_ad and talking else "talking, lips to the voice read" if talking else "silent"),
                      "medium": "video", "job": ch["job"], "model_house": {"registry": ch["registry"], "door": ch["door"]},
                      "higgsfield_model": ch["higgsfield_model"], "model_name": PLAIN_MODEL.get(ch["higgsfield_model"]),
                      "prompt": "Image 1 is the first frame: keep this exact person, clothing, props, room and light.\n"
                                + (f"{sc.get('happens')}.\n" if sc.get("happens") else "") + "\n".join(shot_lines)
                                + (f"\nStyle: {piece.get('style')}" if piece.get("style") else ""),
                      "prompt_source": "DRAFT from the brief's shots; video production has not built this brief yet, "
                      "so this is not the chain's exact Seedance prompt",
                      "references": [{"n": 1, "kind": "image", "role": "the start picture",
                                      "media_role": "image_references" if talking else "start_image",
                                      "file": f"{asset_name(key, n - 1, 'png')} (not made yet: step {n - 1} makes it)", "exists": False,
                                      "element": None}]
                      + ([{"n": 2, "kind": "audio", "role": f"the approved Suno song slice for {sc.get('id')}" if song_ad else f"the voice read of {sc.get('id')}", "media_role": "audio_references",
                           "file": (f"{sc.get('id')}.wav (not sliced yet: approve the Suno master and align its lyrics first)" if song_ad else f"{sc.get('id')}.mp3 (not read yet: the cast's banked voice reads the line first)"),
                           "exists": False, "element": None}] if talking else []),
                      "cast": [cast[w] for w in who],
                      "settings": {"aspect_ratio": "9:16", "duration": None, "resolution": res if res in ("480p", "720p", "1080p") else "480p",
                                   "generate_audio": talking, "endpoint": f"bytedance/{endpoint}/"
                                   + ("reference-to-video" if talking else "image-to-video"), "count": 1},
                      "words_on_top": [], "bars": None, "findings": (["BLOCKED: approve the Suno master, align lyrics, and rebuild exact clip timings before generation. Lyrics are sung in the song; do not commission spoken voice reads."] if song_ad else []), "draft": True})
    return steps, slug


# ------------------------------------------------------------------------------------------------ the core

def _brief_file(rec, kind, repo):
    repo = Path(repo)
    if rec.get("brief_file") and (repo / rec["brief_file"]).is_file():
        return repo / rec["brief_file"]
    run = str(rec.get("run") or "").rstrip("/").split("/")[-1]
    if kind in ("picture", "sequence"):
        for f in (repo / "runs" / "image-teardown" / rec["brand"] / run / "deliverable" / "06-brief.md",
                  _teardown_run(repo, run, rec["brand"]) / "out" / "06-brief.md"):
            if f.is_file():
                return f
    else:
        d = repo / "runs" / "video-writing" / rec["brand"] / run / "deliverable"
        for f in (d / "7-final-brief.md", d / "5-brief.md"):
            if f.is_file():
                return f
    return None


def _kind(rec):
    t = str(rec.get("type") or "image")
    if t.startswith("video"):
        return "video"
    if t.startswith("sequence"):
        return "sequence"
    if t.startswith("image") or t == "None" or not rec.get("type"):
        return "picture"
    raise SystemExit(f"{rec.get('id')} is a {t} brief: run sheets cover picture, carousel and video briefs")


def build(brief_key, brand=None, repo=None, chain=None):
    """The run sheet for one brief, as a dict (what run.json holds)."""
    repo = Path(repo or REPO)
    chain = chain or Chain(repo)
    key, rec = chain.lookup(brief_key, brand)
    reg_key, key = key, home_key(key, rec.get("brand") or brand, repo)
    kind = _kind(rec)
    bf = _brief_file(rec, kind, repo)
    md = bf.read_text() if bf else ""
    products, elements = chain.products(), chain.elements()
    brand = rec["brand"]
    gaps = []
    prun = None
    if kind == "picture":
        steps = picture_steps(key, rec, chain, products, elements, repo)
        role = LANES["image"]
    elif kind == "sequence":
        steps, gaps = sequence_steps(key, rec, bf, chain, products, elements, repo)
        role = LANES["sequence"]
    else:
        role = LANES["video"]
        prun = _video_run(rec, key, repo) or (_video_run(rec, reg_key, repo) if reg_key != key else None)
        if prun:
            steps = clip_steps(key, rec, prun, chain, products, elements, repo)
        else:
            steps, _ = draft_steps(key, rec, md, chain, products, elements, repo)
            gaps.append("No video production run for this brief yet, so every prompt here is a DRAFT from the brief; run "
                        "it through video production and rebuild this sheet for the exact Seedance prompts.")
    slug = product_slug(brand, rec.get("product"), products, repo)
    # every element the steps lean on, once
    seen, els = set(), []
    for s in steps:
        for r in s["references"]:
            e = r.get("element")
            if e and (e["kind"], e["id"]) not in seen:
                seen.add((e["kind"], e["id"]))
                els.append({**e, "covers": []})
            if e:
                next(x for x in els if (x["kind"], x["id"]) == (e["kind"], e["id"]))["covers"].append(f"step {s['n']} IMAGE {r['n']}")
        for c in s.get("cast") or []:
            k = ("cast", Path(c["folder"]).name if c.get("folder") else c["who"])
            if k not in seen:
                seen.add(k)
                els.append({"kind": "cast", "id": k[1], "name": c["who"], "folder": c.get("folder"),
                            "element": c.get("element"), "covers": []})
            next(x for x in els if (x["kind"], x["id"]) == k)["covers"].append(f"step {s['n']}")
    if slug and ("product", slug) not in seen:
        e = products.get(f"{brand}/{slug}") or {}
        hf = (e.get("assets") or {}).get("higgsfield_element") or {}
        els.append({"kind": "product", "id": slug, "name": e.get("name") or slug, "brand": brand,
                    "folder": f"runs/ai-elements/{brand}/products/{slug}",
                    "element": {"id": hf["id"], "name": hf.get("name")} if hf.get("id") else None,
                    "covers": ["the brief's product (laid on in the edit or drawn from these pictures)"]})
    for e in els:
        e["drive"] = None
        if e["kind"] == "product":
            pe = products.get(f"{brand}/{e['id']}") or {}
            d = ((pe.get("assets") or {}).get("drive") or {})
            e["drive"] = next((d[k]["label"] for k in ("packshot", "product-kit/3d-model") if (d.get(k) or {}).get("files")),
                              next((v.get("label") for v in d.values() if v.get("files")), None))
        if not e.get("element") and e["kind"] != "product":
            gaps.append(f"{e['kind']} {e['name']} has no Higgsfield element yet: its files go in by hand"
                        " (cast, set and prop elements arrive with runs/ai-elements/ELEMENTS-INDEX.json)")
    for s in steps:
        for r in s["references"]:
            if not r["exists"] and "(not " not in r["file"]:
                gaps.append(f"step {s['n']} IMAGE {r['n']} ({r['role'][:60]}) is not on this machine: {r['file']}")
            elif "(not " in r["file"] and not s.get("draft") and not s.get("slide"):
                gaps.append(f"step {s['n']}: {r['role']} is {r['file']}")
        for f in s.get("findings") or []:
            gaps.append(f"step {s['n']}: the model rulebook says: {f}")
        for f in (s.get("set_request") or {}).get("flags") or []:
            gaps.append(f"step {s['n']}: the set change: {f}")
    pe = products.get(f"{brand}/{slug}") or {} if slug else {}
    pname = str(pe.get("name") or "").strip()
    if pname:
        for s in steps:
            named = re.search(r"\b" + re.escape(pname) + r"\b", s.get("prompt") or "")
            has = any((r.get("element") or {}).get("kind") == "product" for r in s["references"])
            edit = (s["references"] or [{}])[0].get("role", "").startswith("the approved picture")
            if named and not has and not edit and s.get("medium") == "image":
                hf = ((pe.get("assets") or {}).get("higgsfield_element") or {})
                gaps.append(f"step {s['n']}'s prompt names {pname} but carries no picture of it (the chain's swap list says "
                            "the product is not in frame); the product is then drawn from words. To show the real one, add "
                            + (f"the element @{hf['name']}" if hf.get("name") else "its casting sheet")
                            + " or lay the real photo in at the edit.")
    if any(r["exists"] for s in steps for r in s["references"]):
        gaps.append("Reference files are named by their repo path. Someone without the repo needs the Drive copies: the "
                    "hand-off folder carries them once the hand-off writers include this run sheet.")
    models = {s["higgsfield_model"] for s in steps if s.get("higgsfield_model")}
    if any(e.get("element") and e["kind"] == "product" for e in els):
        gaps.append(ELEMENT_ONE_PICTURE)
    if any(e.get("element") for e in els) and not models & set(ELEMENT_MODELS):
        gaps.append("Higgsfield's element tool lists gpt_image_2 and seedance_2_0 as honouring <<<element>>> placeholders, "
                    f"not {', '.join(sorted(models))}: until one test call confirms it, the reference FILES are the sure path "
                    "and the element is the shortcut.")
    out = {"runsheet": 1, "built": datetime.now().isoformat(timespec="seconds"), "core": CORE,
           "brief_key": key, "brief": rec.get("brief") or key, "brand": brand, "product": slug or rec.get("product"),
           "kind": kind, "format": (_brief_json(md).get("piece") or {}).get("format"), "title": _title(md, rec.get("title") or key),
           "brief_file": rel(bf, repo) if bf else None, "run": rec.get("run"),
           "production_run": f"runs/video-production/{prun}" if prun else None,
           "return": return_place(key, brand, role), "elements": els, "steps": steps,
           "gaps": list(dict.fromkeys(gaps))}
    out["deliverable"] = rel(bf.parent, repo) if bf and bf.parent.name == "deliverable" else None
    if any(st["medium"] == "video" for st in steps):
        out["cut"] = cut_plan(out)
    return out


# The clips are not the ad: a video brief ends in ONE cut (2026-10-28: the first run sheet stopped at 30 loose clips). The rules are video-edit's hard rules, in the maker's words.
CUT_RULES = [
    "Lay the clips end to end in step order (asset-01 first). Every clip keeps its own sound: the voice is already in "
    "it. Never lay a second voice over a talking clip.",
    "Cut between clips, never mid-word or mid-breath: start a hair before the first word, end a breath after the last.",
    "Captions: the words as spoken, 2-4 words at a time, in the bottom band (inside the centre 4:5), never over a face "
    "or a mouth. A headline the brief puts on screen sits at the top.",
    "Music and sound effects only where the brief calls for them; music sits 18 dB under the voice.",
    "9:16, 1080x1920. Master to -14 LUFS.",
]


def cut_plan(sheet):
    key = sheet["brief_key"]
    return {"asset": f"{key}-control.mp4", "order": [st["asset"] for st in sheet["steps"]], "rules": (["Use the approved Suno master as the continuous soundtrack. Mute all generated clip audio; never replace lyrics with spoken voice reads.", "Align every scene and lip-sync slice to the actual song timing before cutting. Durations are pending until the master is approved.", "Use only video clips in the cut; start pictures are references. Captions follow the sung words and stay clear of faces.", "9:16, 1080x1920. Master to -14 LUFS."] if sheet.get("format") == "song-ad" else CUT_RULES),
            "brief": "BRIEF.md (what the ad says, any headline, music or sound effect it calls for)"}


def cut_step(sheet):
    c = sheet.get("cut")
    if not c:
        return []
    return ([f"**The cut · `{c['asset']}`.** When every clip above is made, cut them into ONE video. Read {c['brief']}.", ""]
            + [f"- {r}" for r in c["rules"]] + ["", f"Save it as `{c['asset']}` beside the clips.", ""])


# ------------------------------------------------------------------------------------------------ the renderings

def _fence(text, lang="text"):
    t = str(text)
    ticks = "````" if "```" in t else "```"
    return f"{ticks}{lang}\n{t}\n{ticks}"


def _setting_line(s):
    st = s["settings"]
    if s["medium"] == "image":
        bits = [f"aspect {st.get('aspect_ratio')}"] + [f"{k} {st[k]}" for k in ("variant", "quality", "resolution") if st.get(k)]
    else:
        bits = [f"aspect {st.get('aspect_ratio')}", f"{st.get('duration') or 'as the voice read runs (4-30)'} s",
                f"{st.get('resolution')}", "audio ON" if st.get("generate_audio") else "audio OFF"]
    return " · ".join(bits + [f"count {st.get('count', 1)}"])


def receipt_example(sheet):
    """One filled-in receipt for the first step that calls a model: the shape every receipt takes."""
    s = next((x for x in sheet["steps"] if x.get("job") not in ("words-only", "set-change")), None)
    if not s:
        return None
    ins, seen = [], set()
    for r in s["references"]:
        hf = ((r.get("element") or {}).get("element")) or {}
        if hf and hf["id"] in seen:                       # one element carries several IMAGEs: one input
            continue
        seen.add(hf.get("id"))
        ins.append({"n": r["n"], "kind": r.get("kind", "image"), "file": _f(r).split("/")[-1],
                    "media_id": "<its Higgsfield media id, if you have it>"} if not hf else
                   {"n": r["n"], "kind": "element", "file": hf.get("name") or hf["id"], "media_id": hf["id"]})
    return {"asset": s["asset"], "step": s["n"], "higgsfield_generation_id": "<the generation or job id>",
            "model": s.get("higgsfield_model"), "prompt": "<the prompt exactly as you sent it>", "inputs": ins,
            "settings": {k: v for k, v in s["settings"].items() if k != "endpoint"},
            "made_by": "<your name, or the agent>", "made_at": "<date and time>"}


def _compact(d):
    """A receipt as people read it: one field a line, each input on its own line."""
    j = lambda v: json.dumps(v, ensure_ascii=False)                      # noqa: E731
    rows = []
    for k, v in d.items():
        if k == "inputs":
            rows.append(f' "inputs": [\n' + ",\n".join(f"  {j(x)}" for x in v) + "\n ]")
        else:
            rows.append(f" {j(k)}: {j(v)}")
    return "{\n" + ",\n".join(rows) + "\n}"


def return_step(sheet):
    r = sheet["return"]
    first = sheet["steps"][0]["asset"] if sheet["steps"] else r["name_pattern"]
    out = (f"**Return.** Name every file `{r['name_pattern']}` (the asset name each step gives: "
           f"`{first}`, and so on) and drop them in "
           f"`{r['repo']}`, or the same folder on Drive: `{r['drive']}`. Nothing goes anywhere else.")
    ex = receipt_example(sheet)
    if not ex:
        return out
    stem = ex["asset"].rsplit(".", 1)[0]
    return (out + "\n\n" + TEXT_FROM_GITHUB + " Read each step's prompt out of run.json with code and pass that string "
            "unchanged; never retype a prompt."
            + "\n\n**Higgsfield's own record, beside every file (an agent).** Save `<asset name without its ending>"
            f".record.json` next to it (`{stem}.record.json`): {RECORD_WHAT}. It is the proof: the check reads the "
            "prompt, the references and the settings from it, not from anyone's account of them."
            + "\n\n**Receipt, beside every file.** Save `<asset name without its ending>.receipt.json` next to it "
            f"(`{stem}.receipt.json`): what you actually sent, copied, not retyped. It is how we prove the references "
            "went in. One input per reference, in the order you gave them (an element: its name and id). A step with "
            "no model call needs none. Step " + str(ex["step"]) + "'s, filled in:\n\n"
            + _fence(_compact(ex), "json")
            + f"\n\nIn the web app and can't make the JSON? Paste the generation's link into `{stem}.link.txt` "
            "instead, one line.")


def _f(r):
    """A reference as a person or an agent in the hand-off folder reaches it: its refs/ file, else its repo path."""
    return r.get("local") or r["file"]


def _refs_for(s):
    """The step's references split: the ones an element carries, and the files that go in by hand."""
    by_el, files = {}, []
    for r in s["references"]:
        e = r.get("element") or {}
        if e.get("element"):
            by_el.setdefault(e["element"]["id"], {"el": e, "images": []})["images"].append(r["n"])
        else:
            files.append(r)
    return by_el, files


def set_how(s):
    """A set change in the words every rendering uses: the request's own steps, then the words and the name."""
    ask = s["set_request"]
    out = [f"**A change to the 3D set, in Higgsfield 3D Jutsu, never a flat picture.** "
           f"The change: {ask.get('change')}. Set request: `{ask.get('set')}` ({ask.get('credits')} credits to print).", ""]
    out += [f"{i}. {x}" for i, x in enumerate(ask.get("steps") or [], 1)]
    out += ["", f"Print with the Step {s['n']} prompt from the core, word for word. Name the result `{s['asset']}`."]
    if s["words_on_top"]:
        out.append(f"Set these on top {TYPE_STYLE}: " + "; ".join(f"{w['zone']}: `{w['words']}`" for w in s["words_on_top"]) + ".")
    return out + [""]


def render_core(sheet):
    L = ["## The core: what gets made, on Higgsfield", "",
         "Every tool below makes exactly these steps. The prompt is the one place to change what a picture says; "
         "change it here (the brief and the prompt bench), never in one tool's section.", ""]
    if sheet["elements"]:
        L += ["### Elements", "", "| Kind | What | Higgsfield element | Its files | Used in |", "|---|---|---|---|---|"]
        for e in sheet["elements"]:
            hf = e.get("element")
            L.append(f"| {e['kind']} | {e['name']} | " + (f"`{hf['name']}` · `<<<{hf['id']}>>>`" if hf else "none yet") +
                     f" | `{e.get('folder') or '-'}`" + (f" · Drive `{e['drive']}`" if e.get("drive") else "") +
                     ("".join(f" · here `{x}`" for x in e.get("refs") or [])) +
                     f" | {', '.join(e['covers'][:6])}{' …' if len(e['covers']) > 6 else ''} |")
        L.append("")
    for s in sheet["steps"]:
        L += [f"### Step {s['n']} · `{s['asset']}` · {s['what']}", ""]
        if s["job"] == "words-only":
            L += ["No Higgsfield call: the approved plate gets these words set on top.", ""]
        elif s["job"] == "set-change":
            L += ["A change to the kept 3D set: built and printed in Higgsfield 3D Jutsu, not as a flat picture.", ""]
        else:
            L += ["| Job | Model | Higgsfield model id | Settings |", "|---|---|---|---|",
                  f"| {s['job']} ({s['model_house']['registry']}, {s['model_house']['door']}) | {s['model_name']} | "
                  f"`{s['higgsfield_model']}` | {_setting_line(s)} |", ""]
            if s["medium"] == "video":
                L += [f"Endpoint the chain calls: `{s['settings']['endpoint']}`.", ""]
        if s["references"]:
            packed = any(r.get("local") for r in s["references"])
            L += ["| # | What it is | Element | " + ("File (this folder · repo · Drive) |" if packed else "File (repo) |"),
                  "|---|---|---|---|"]
            for r in s["references"]:
                e = r.get("element") or {}
                hf = e.get("element")
                tag = "IMAGE" if r["kind"] == "image" else r["kind"].upper()
                where = (f"`{r['local']}` · `{r['file']}` · `{r['drive']}`" if r.get("local") else f"`{r['file']}`")
                L.append(f"| {tag} {r['n']} | {r['role']} | " + (f"`{hf['name']}`" if hf else "-") +
                         f" | {where}" + ("" if r["exists"] or "(not " in r["file"] else " (missing)") + " |")
            L.append("")
        for c in s.get("cast") or []:
            hf = c.get("element")
            fb = c.get("fallback") or {}
            L.append(f"- Cast in this step: {c['who']} · " + (f"element `{hf.get('name') or hf['id']}` `<<<{hf['id']}>>>`" if hf
                     else "no Higgsfield element yet") + (f" · `{c['folder']}`" if c.get("folder") else "")
                     + (f" · picture `{fb['local']}` (Drive `{fb['drive']}`)" if fb.get("local") else ""))
        if s.get("cast"):
            L.append("")
        if s["prompt"]:
            L += [f"Prompt ({s['prompt_source']}):", "", _fence(s["prompt"]), ""]
        if s["words_on_top"]:
            L += ["Words set on top afterwards (never drawn by the model):", ""]
            L += [f"- {w['zone']}: `{w['words']}`" for w in s["words_on_top"]]
            L.append("")
        if s.get("bars"):
            L += [f"Black bars as on the swipe: top {s['bars']['top']:.0%}, bottom {s['bars']['bottom']:.0%} of the frame.", ""]
    return L


# The words are set by a person or an agent after the picture: say exactly what to copy (the 0232 Supercomputer test,
# 2026-10-28, had to guess the font, outline and size because "the swipe's type style" named nothing to look at).
TYPE_STYLE = ("in the swipe's type style: copy the words on the swipe picture (step 1's IMAGE 1) for font look, size, "
              "colour, outline and place; where this folder has a `words-guide.png`, match it exactly. Finish the picture "
              "at 1080×1920")


# The Drive is the storage, never the tool's own (2026-10-28): an agent that copied a whole video folder into Supercomputer filled its storage and stalled.
# Text from GitHub, media from the Drive (2026-10-28, the Supercomputer agent): the Drive connector changes text when
# it reads or writes it (an element id came back with an extra 0, a LEARNINGS line was reworded), and a retyped prompt
# came back corrupted ("Shaved" -> "Shared", symbols lost, never-rules dropped).
TEXT_FROM_GITHUB = ("Read BRIEF.md, RUN.md and run.json from GitHub (company-team/workspace, the same path as on the "
                    "Drive); the Drive connector can change text. Take pictures, clips and voice files from the Drive.")
LEAN = ("**Work one step at a time.** Fetch only that step's files from refs/, make it, save the result straight to "
        "returned/ on the Drive, then go on to the next step. Never copy the whole folder into your own workspace: "
        "the Drive is the storage. " + TEXT_FROM_GITHUB + " Read each step's prompt out of run.json with code and "
        "pass that string unchanged; never retype a prompt.")


def element_swap_line(x):
    """The one change the prompt takes when an element goes in instead of its files (the 2026-10-28 project test: the
    agent had to reword the IMAGE lines itself). Everything else in the prompt stays word for word."""
    imgs = sorted(x["images"])
    first = imgs[0]
    el = x["el"]
    # a cast element's index entry carries no name (2026-10-28: "supplied as the element None"); Higgsfield names it
    # <brand>-<id>, and a person is copied by face and build, not "shape, label and finish"
    name = (el.get("element") or {}).get("name") or (f"{el['brand']}-{el['id']}" if el.get("brand") and el.get("id")
                                                    else el.get("name"))
    if el.get("kind") == "cast":
        what = (f"\"IMAGE {first} is {el['name']}, our cast member, supplied as the element {name}: keep this exact "
                f"person, the same face, skin and build.\"")
    else:
        what = (f"\"IMAGE {first} is the real {el['name']}, supplied as the element {name}: every side of it, at its "
                f"true size; copy the exact shape, label and finish.\"")
    return (f"When the element goes in, the prompt's line(s) for IMAGE {', '.join(map(str, imgs))} become this one line: "
            f"{what} Any IMAGE numbered after {imgs[-1]} moves down by {len(imgs) - 1}. Nothing else in the prompt "
            f"changes.")


def render_web(sheet):
    L = ["## A · Higgsfield web app (a person clicking)", ""]
    for s in sheet["steps"]:
        L += [f"**Step {s['n']} · {s['asset']}**", ""]
        if s["job"] == "words-only":
            L += [f"1. No generation. Open the plate `{_f(s['references'][0])}` in your design tool.",
                  f"2. Set these words on it {TYPE_STYLE}: "
                  + "; ".join(f"{w['zone']}: `{w['words']}`" for w in s["words_on_top"]) + f". Save as `{s['asset']}`.", ""]
            continue
        if s["job"] == "set-change":
            L += set_how(s)
            continue
        by_el, files = _refs_for(s)
        page = "Image → Create Image" if s["medium"] == "image" else "Video → Create Video"
        n = 1
        L.append(f"{n}. Open higgsfield.ai, go to **{page}**, and pick the model **{s['model_name']}**.")
        for eid, x in by_el.items():
            n += 1
            fall = [r for r in s["references"] if r["n"] in x["images"] and r["kind"] == "image"]
            L.append(f"{n}. First choice: in the prompt box type **@{x['el']['element']['name']}** (the {x['el']['name']} "
                     f"element). It carries IMAGE {', '.join(map(str, x['images']))}. If the model will not take the "
                     "@-mention, upload these files instead, in this order: "
                     + ", ".join(f"`{_f(r)}`" for r in fall) + ". " + element_swap_line(x))
        ups = [r for r in files]
        if ups:
            n += 1
            what = "; ".join(f"{('IMAGE' if r['kind'] == 'image' else r['kind'].upper())} {r['n']}: `{_f(r)}`"
                             + (f" as the **{r['media_role'].replace('_', ' ')}**" if r.get("media_role") else "")
                             for r in ups)
            L.append(f"{n}. Upload, in this order: {what}.")
        for c in s.get("cast") or []:
            fb = (c.get("fallback") or {}).get("local")
            if c.get("element"):
                n += 1
                L.append(f"{n}. First choice: @-mention **{c['element'].get('name') or c['element']['id']}** for {c['who']}."
                         + (f" If the model will not take it, upload `{fb}` instead." if fb else ""))
            elif fb:
                n += 1
                L.append(f"{n}. {c['who']} has no Higgsfield element yet: upload `{fb}` as the picture of them.")
        n += 1
        L.append(f"{n}. Paste the Step {s['n']} prompt from the core, word for word. Change nothing.")
        st = s["settings"]
        n += 1
        if s["medium"] == "image":
            L.append(f"{n}. Settings: aspect ratio **{st.get('aspect_ratio')}**, variant **{st.get('variant')}**, quality "
                     f"**{st.get('quality')}**, resolution **{st.get('resolution')}**, **1** image.")
        else:
            L.append(f"{n}. Settings: aspect ratio **{st.get('aspect_ratio')}**, duration **"
                     f"{st.get('duration') or 'the length of the voice read (4-30 s)'}**, resolution **{st.get('resolution')}**, "
                     f"audio **{'on' if st.get('generate_audio') else 'off'}**, **1** take.")
        n += 1
        L.append(f"{n}. Generate. Download the result and name it `{s['asset']}`.")
        if s["words_on_top"]:
            n += 1
            L.append(f"{n}. The model draws no words on this one. Set these on top {TYPE_STYLE}: "
                     + "; ".join(f"{w['zone']}: `{w['words']}`" for w in s["words_on_top"]) + ".")
        L.append("")
    L += cut_step(sheet) + [return_step(sheet), ""]
    return L


def agent_call(s, prompt=None, media=None):
    """One step as a Higgsfield tool call: (tool, {"model", "prompt", settings, "medias", "count"}). Every reference goes
    in `medias` in step order (the files route, the one proven byte for byte). `prompt` and `media(r)` fill the real
    values (briefs/make.py); left out, they are the placeholders section B prints."""
    tool = "generate_image" if s["medium"] == "image" else "generate_video"
    st = s["settings"]
    params = {"model": s["higgsfield_model"],
              "prompt": s["prompt"] if prompt is True else (prompt or f"<steps[{s['n'] - 1}].prompt>"),
              "aspect_ratio": st.get("aspect_ratio")}
    if s["medium"] == "image":
        params.update({k: st[k] for k in ("variant", "quality", "resolution") if st.get(k)})
        params["medias"] = [{"role": "image_references", "value": media(r) if media else f"<media id of IMAGE {r['n']}>"}
                            for r in s["references"]]
    else:
        if st.get("generate_audio") or any(r.get("media_role") == "video_references" for r in s["references"]):
            params["mode"] = "omni_reference"
        params.update({"duration": st.get("duration") or "<seconds of the voice read, 4-30>", "resolution": st.get("resolution"),
                       "generate_audio": bool(st.get("generate_audio"))})
        params["medias"] = [{"role": r.get("media_role") or "image_references",
                             "value": media(r) if media else f"<media id of {r['kind']} {r['n']}>"} for r in s["references"]]
    params["count"] = 1
    return tool, params


def render_claude(sheet):
    key = sheet.get("brief_key") or ""
    L = ["## B · Claude Code (Higgsfield MCP + this repo)", "",
         "**The short way, one step at a time** (2026-10-28, how the makers work):", "",
         f"1. `python3 components/briefs/make.py plan {key} <step>`: fetches the step's files from the Drive and prints "
         "the files to upload, in order, and the exact Higgsfield call with the prompt word for word.",
         "2. Upload each file with `media_upload` (PUT the bytes, then `media_confirm`) and put each media id where the "
         "plan says. Change nothing else. Make the call; the person approves it.",
         "3. When it has finished, save the `show_generation_by_ids` reply for it to a file, unchanged, then "
         f"`python3 components/briefs/make.py save {key} <step> --record <that file>`: the result is named, saved to "
         "`returned/` here and on the Drive, and checked against this step.", "",
         "The same, written out per step (a Higgsfield Supercomputer project follows these too):", "",
         LEAN, ""]
    for s in sheet["steps"]:
        L += [f"**Step {s['n']} · {s['asset']}**", ""]
        if s["job"] == "words-only":
            L += [f"No Higgsfield call. Set `steps[{s['n'] - 1}].words_on_top` on `{_f(s['references'][0])}` "
                  "(image-edit's type layer) and save it as the asset name.", ""]
            continue
        if s["job"] == "set-change":
            L += set_how(s)
            continue
        by_el, files = _refs_for(s)
        k = [0]

        def say(x):
            k[0] += 1
            L.append(f"{k[0]}. {x}")
        if by_el:
            ids = ", ".join(f"`<<<{x['el']['element']['id']}>>>` ({x['el']['element']['name']}, IMAGE "
                            f"{', '.join(map(str, x['images']))})" for x in by_el.values())
            fall = [r for r in s["references"] if any(r["n"] in x["images"] for x in by_el.values()) and r["kind"] == "image"]
            say(f"Elements first: {ids}. Put the placeholder in the prompt and leave those files out of `medias`; never "
                "put an element id in `medias`. Fallback, when the model does not honour the element: upload "
                + ", ".join(f"`{_f(r)}`" for r in fall) + " too and pass every IMAGE in `medias`, in number order.")
            for x in by_el.values():
                say(element_swap_line(x))
        for c in s.get("cast") or []:
            fb = (c.get("fallback") or {}).get("local")
            if c.get("element"):
                say(f"{c['who']}: `<<<{c['element']['id']}>>>` in the prompt where the person is named first"
                    + (f"; fallback, upload `{fb}` as an image reference." if fb else "."))
            elif fb:
                say(f"{c['who']} has no element yet: upload `{fb}` as an image reference.")
        if s["references"]:
            say("Upload the reference files in order with `media_upload` (PUT the bytes, then `media_confirm`): "
                + ", ".join(f"`{_f(r)}`" for r in (files if by_el else s["references"])) + ".")
        tool, params = agent_call(s)
        say(f"Call `{tool}` with" + (" (on the element route, drop the element's IMAGEs from `medias`):" if by_el else ":"))
        L += ["", _fence(json.dumps({"params": params}, indent=1), "json"), ""]
        say(f"Download the result as `{s['asset']}`.")
        if s["words_on_top"]:
            say(f"Set `steps[{s['n'] - 1}].words_on_top` on it (image-edit's type layer).")
        L.append("")
    L += cut_step(sheet) + [return_step(sheet), ""]
    return L


def render_other(sheet):
    key = sheet["brief_key"]
    L = ["## C · Codex or any other agent", "",
         "Plain steps against Higgsfield. `run.json` beside this file holds every value; print one step's prompt with "
         f"`python3 components/briefs/runsheet.py {key} --prompt N`. The Higgsfield command line (`higgsfield`, signed in) "
         "or its HTTP API (keys `HIGGSFIELD_KEY_ID` / `HIGGSFIELD_KEY_SECRET` from the one keys file) both work."
         + (" Every `refs/` file is in this hand-off folder: run from it, or from the repo with the folder's path in "
            "front." if sheet.get("handoff") else ""), ""]
    for s in sheet["steps"]:
        L += [f"**Step {s['n']} · {s['asset']}**", ""]
        if s["job"] == "words-only":
            L += [f"No model call: set the step's `words_on_top` on `{s['references'][0]['file']}`; save as `{s['asset']}`.", ""]
            continue
        if s["job"] == "set-change":
            L += set_how(s)
            continue
        st = s["settings"]
        if s["medium"] == "image":
            cmd = (f"higgsfield generate create {s['higgsfield_model']} \\\n  --prompt \"$(python3 components/briefs/runsheet.py {key} "
                   f"--prompt {s['n']})\" \\\n  --aspect_ratio {st.get('aspect_ratio')} --variant {st.get('variant')} "
                   f"--quality {st.get('quality')} --resolution {st.get('resolution')} \\\n"
                   + "".join(f"  --image-references {_f(r)} \\\n" for r in s["references"]) + "  --wait --json")
            L += ["```bash", cmd, "```", ""]
            if not s.get("draft"):
                L.append(f"Check first, free: `python3 components/model-inputs/preview.py pictures.generate "
                         f"'{json.dumps({'brand': sheet['brand'], 'run': sheet['run'], 'product': sheet['product'] or ''})}' --no-quote` "
                         "(step 1's prompt; a variation adds its one change).")
        else:
            body = {"prompt": f"<steps[{s['n'] - 1}].prompt>", "resolution": st.get("resolution"), "aspect_ratio": st.get("aspect_ratio"),
                    "duration": st.get("duration") or "<seconds of the voice read + 0.6, 4-30>",
                    "generate_audio": bool(st.get("generate_audio")), "output_format": "mp4"}
            for r in s["references"]:
                fld = {"start_image": "image_url", "end_image": "end_image_url", "image_references": "image_urls",
                       "audio_references": "audio_urls", "video_references": "video_urls"}.get(r.get("media_role"), "image_urls")
                if fld.endswith("s"):
                    body.setdefault(fld, []).append(f"<uploaded {_f(r)}>")
                else:
                    body[fld] = f"<uploaded {_f(r)}>"
            L += [f"POST `{st['endpoint']}` (upload each file first, pass its URL):", "", _fence(json.dumps(body, indent=1), "json"), ""]
            if sheet.get("production_run") and not s.get("draft"):
                L.append(f"Check first, free: `python3 components/model-inputs/preview.py clips.seedance "
                         f"'{json.dumps({'run': sheet['production_run'].split('runs/video-production/', 1)[1], 'call': s['what'].split()[1]})}' --no-quote`.")
        if s["words_on_top"]:
            L.append(f"Then set the step's `words_on_top` on the picture {TYPE_STYLE}.")
        L += [f"Save the result as `{s['asset']}`.", ""]
    L += cut_step(sheet) + [return_step(sheet), ""]
    return L


def render_md(sheet):
    r = sheet["return"]
    head = [f"# RUN SHEET · {sheet['brand'].upper()} · {sheet['title']} · {sheet['brief_key']}", "",
            "How to make this brief, from any tool. The brief says what to make; this says how. The core is Higgsfield: "
            "every tool below runs the same calls.", "",
            "| | |", "|---|---|",
            f"| **Brief** | `{sheet['brief_key']}` · `{sheet['brief_file'] or 'no brief file found'}` |",
            f"| **Makes** | {len(sheet['steps'])} asset(s): `{sheet['steps'][0]['asset'] if sheet['steps'] else '-'}`"
            + (f" to `{sheet['steps'][-1]['asset']}`" if len(sheet["steps"]) > 1 else "") + " |",
            f"| **Product** | {sheet['product'] or 'none'} |",
            f"| **Core** | Higgsfield · " + ", ".join(sorted({f"{s['model_name']} (`{s['higgsfield_model']}`)" for s in sheet["steps"] if s.get("higgsfield_model")})) + " |",
            f"| **Return to** | `{r['repo']}` · Drive `{r['drive']}` |",
            f"| **Built** | {sheet['built']} by `components/briefs/runsheet.py` |", ""]
    h = sheet.get("handoff")
    if h:
        head[-1:] = [f"| **This folder** | `{h['folder']}/` · Drive `{h['drive']}/` |",
                     f"| **In it** | `BRIEF.md` (the brief), this `RUN.md`, `run.json`, and `refs/`: all {len(h['refs'])} "
                     "reference file(s) this sheet names, so nothing outside this folder is needed |", "",
                     "Open this folder on Google Drive. A person follows **section A**; an agent follows **section B** "
                     "(or C). Put the finished files in `returned/`.", ""]
    if sheet["gaps"]:
        head += ["**Open before a perfect run:**", ""] + [f"- {g}" for g in sheet["gaps"]] + [""]
    return "\n".join(head + render_core(sheet) + render_web(sheet) + render_claude(sheet) + render_other(sheet)).rstrip() + "\n"


def write(brief_key, out_dir=None, brand=None, repo=None, chain=None, sheet=None):
    """Write RUN.md and run.json into the brief's deliverable/ folder (or `out_dir`). Returns their paths."""
    repo = Path(repo or REPO)
    sheet = sheet or build(brief_key, brand=brand, repo=repo, chain=chain)
    if out_dir is None:
        if not sheet.get("deliverable"):
            raise SystemExit(f"{sheet['brief_key']} has no deliverable/ folder: give --out")
        out_dir = repo / sheet["deliverable"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md, js = out / "RUN.md", out / "run.json"
    md.write_text(render_md(sheet))
    js.write_text(json.dumps(sheet, indent=1, ensure_ascii=False) + "\n")
    return {"md": str(md), "json": str(js)}


# ------------------------------------------------------------------------------------------------ the hand-off copy

REFS = "refs"
STEM_WORD = {"product-sheet": "sheet", "master": "master", "master-reference": "master", "headshot": "headshot"}


def _slug(text, n=4):
    w = [x for x in re.findall(r"[a-z0-9]+", str(text).lower()) if x not in ("the", "a", "an", "its", "our", "of", "in", "for")]
    return "-".join(w[:n]) or "file"


def _ref_name(r, step_n, shared):
    """A reference's name in refs/: an element's file by its element (`product-<id>-sheet.png`, `cast-<id>-headshot.jpg`),
    anything else by step and role (`step-01-image-1-swipe.jpg`); one used by several steps by its role alone."""
    src = str(r["file"])
    ext = Path(src).suffix.lower() or ".bin"
    e = r.get("element") or {}
    if e.get("kind") in ELEMENT_KINDS.values():
        stem = Path(src).stem
        return f"{e['kind']}-{e['id']}-{STEM_WORD.get(stem) or _slug(stem, 3)}{ext}"
    if src.endswith(".plate.png"):
        role = "approved-plate"
    elif "/assets/source." in src:
        role = "swipe"
    else:
        role = _slug(re.split(r"[:,(]", str(r.get("role") or "file"))[0], 3)
    if shared:
        return f"{role}{ext}"
    tag = "image" if r.get("kind", "image") == "image" else r["kind"]
    return f"step-{step_n:02d}-{tag}-{r['n']}-{role}{ext}"


def pack(sheet, folder=None, role=None, repo=None):
    """The run sheet made SELF-CONTAINED in a hand-off folder (2026-10-28: a Higgsfield Supercomputer user with
    Google Drive and GitHub opens ONE folder and makes the brief with nothing from this Mac). Writes into
    runs/handoffs/<role>/<brand>/<brief key>/ (or `folder`): BRIEF.md (the brief), RUN.md and run.json, and refs/ with
    every reference file the sheet names, copied in and renamed by step and role, element files by their element. In
    this copy every reference reads `local` (refs/<name>, this folder), `file` (its repo path) and `drive` (its
    "Shared Assets/..." label); `source` keeps where it came from. The Higgsfield element stays the first choice, the
    refs/ file its fallback. A file that is not on this machine stays named and stays a gap. Never deletes; a second
    pack writes over the same names. Returns {"folder", "drive", "files", "refs", "missing"}."""
    import copy
    import shutil
    repo = Path(repo or REPO)
    s = copy.deepcopy(sheet)
    key, brand = s["brief_key"], s["brand"]
    role = role or s["return"]["role"]
    s["return"] = return_place(key, brand, role)
    home = handoff_folder(key, brand, role)
    root = Path(folder) if folder else repo / home
    try:
        home = str(root.resolve().relative_to(repo.resolve()))
    except ValueError:
        pass                                                  # written elsewhere (a test, a preview): named by its home
    drive = f"Shared Assets/{home}"
    bf = repo / s["brief_file"] if s.get("brief_file") else None
    if not bf or not bf.is_file():
        raise ValueError(f"{key} has no written brief on this machine ({s.get('brief_file') or 'none found'}): "
                         "nothing to hand off")
    (root / REFS).mkdir(parents=True, exist_ok=True)
    (root / RETURN_DIR).mkdir(exist_ok=True)
    uses = {}
    for st in s["steps"]:
        for r in st["references"]:
            if r.get("exists"):
                uses.setdefault(r["file"], set()).add(st["n"])
    named, refs, missing = {}, [], []

    def place(src, name):
        """Copy one repo file into refs/ once; returns its three forms."""
        if src not in named:
            n, i = name, 2
            while n in {x["name"] for x in refs}:
                n = f"{Path(name).stem}-{i}{Path(name).suffix}"
                i += 1
            shutil.copy2(repo / src, root / REFS / n)
            named[src] = n
            refs.append({"name": n, "source": src, "local": f"{REFS}/{n}", "file": f"{home}/{REFS}/{n}",
                         "drive": f"{drive}/{REFS}/{n}"})
        n = named[src]
        return {"source": src, "local": f"{REFS}/{n}", "file": f"{home}/{REFS}/{n}", "drive": f"{drive}/{REFS}/{n}"}

    for st in s["steps"]:
        for r in st["references"]:
            if not r.get("exists"):
                if "(not " not in str(r["file"]):
                    missing.append(f"step {st['n']} {r['kind']} {r['n']}: {r['file']}")
                continue
            r.update(place(r["file"], _ref_name(r, st["n"], len(uses[r["file"]]) > 1)))
        for c in st.get("cast") or []:
            m = _cast_master(c["folder"], repo) if c.get("folder") else None
            if m:
                c["fallback"] = place(m, f"cast-{Path(c['folder']).name}-{STEM_WORD.get(Path(m).stem) or _slug(Path(m).stem, 3)}"
                                         f"{Path(m).suffix.lower()}")
    for e in s["elements"]:
        mine = [x["local"] for x in refs if x["source"].startswith(str(e.get("folder") or "\0") + "/")]
        if not mine and e.get("folder"):
            f = (f"{e['folder']}/model/product-sheet.png" if e["kind"] == "product" else _cast_master(e["folder"], repo))
            if f and (repo / f).is_file():
                mine = [place(f, f"{e['kind']}-{e['id']}-{STEM_WORD.get(Path(f).stem) or _slug(Path(f).stem, 3)}"
                                 f"{Path(f).suffix.lower()}")["local"]]
        e["refs"] = mine
    shutil.copy2(bf, root / "BRIEF.md")
    s["gaps"] = [g for g in s["gaps"] if not g.startswith("Reference files are named by their repo path")]
    s["handoff"] = {"folder": home, "drive": drive, "role": role,
                    "brief": {"local": "BRIEF.md", "file": f"{home}/BRIEF.md", "drive": f"{drive}/BRIEF.md", "source": s["brief_file"]},
                    "refs": refs, "missing": missing}
    (root / "RUN.md").write_text(render_md(s))
    (root / "run.json").write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")
    return {"folder": home, "drive": drive, "files": ["BRIEF.md", "RUN.md", "run.json"] + [x["local"] for x in refs],
            "refs": refs, "missing": missing, "sheet": s}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", help="brief key (acme_crush_brief-0004), brief-NNNN, pNNN or a number")
    ap.add_argument("--brand")
    ap.add_argument("--out", help="write here instead of the brief's deliverable/ folder")
    ap.add_argument("--prompt", type=int, help="print step N's prompt verbatim (from run.json when it is written)")
    a = ap.parse_args(argv)
    if a.prompt:
        chain = Chain()
        key, rec = chain.lookup(a.brief, a.brand)
        bf = _brief_file(rec, _kind(rec), REPO)
        js = (Path(a.out) if a.out else (bf.parent if bf else Path("."))) / "run.json"
        sheet = json.loads(js.read_text()) if js.is_file() else build(key, a.brand, chain=chain)
        step = next((s for s in sheet["steps"] if s["n"] == a.prompt), None)
        if not step:
            print(f"no step {a.prompt} (this sheet has {len(sheet['steps'])})", file=sys.stderr)
            return 2
        sys.stdout.write(step["prompt"])
        return 0
    sheet = build(a.brief, a.brand)
    paths = write(sheet["brief_key"], a.out, sheet=sheet)
    print(f"{sheet['brief_key']}: {len(sheet['steps'])} step(s), {len(sheet['elements'])} element(s), {len(sheet['gaps'])} open")
    print(f"  {rel(paths['md'])}\n  {rel(paths['json'])}")
    for g in sheet["gaps"]:
        print(f"  open: {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
