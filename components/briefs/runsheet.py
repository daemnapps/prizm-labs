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
    components/image-teardown/runs/<run>/ is read for one release, for a checkout that has not moved its runs."""
    root = Path(repo) / "runs" / "image-teardown"
    run = Path(str(run)).name
    hits = ([root / str(brand).lower() / run] if brand else []) + sorted(root.glob(f"*/{run}"))
    work = [d for d in hits if (d / "out").is_dir() or (d / "vars").is_dir()]
    old = Path(repo) / "components" / "image-teardown" / "runs" / run
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
            self._reg = _load(self.repo / "components" / "image-teardown" / "tools" / "briefs.py", "runsheet_register")
        return self._reg

    def lookup(self, what, brand=None):
        """(register key, record) for a brief key, brief-NNNN, pNNN or a bare number."""
        R = self.register()
        k, r = R.get(R.load(), str(what), brand=brand)
        if not r:
            raise SystemExit(f"{what} is not in the brief register (components/image-teardown/briefs.json)")
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
        f = self.repo / "components" / "image-production" / "picture_sets.py"
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

    def first_set(self, brand, run):
        """The run's main picture under GATE-4 (2026-11-10): {"kept": {set, print}} when a kept 3D set print exists (the
        print IS the picture), else {"ask": the first print's request (picture_sets.first_print)}. Nothing is spent."""
        f = self.repo / "components" / "image-production" / "picture_sets.py"
        if self._sets is None:
            self._sets = _load(f, "runsheet_picture_sets") if f.is_file() else False
        S = self._sets
        if not S:
            return None
        found = S.kept(brand, run)
        if found:
            return {"kept": found}
        try:
            return {"ask": S.first_print(brand, run)}
        except Exception as ex:                               # noqa: BLE001  a run with no brief yet still gets the step
            return {"ask": {"print_words": None, "why": str(ex)[:200]}}

    def _image_edit(self):
        folder = str(self.repo / "components" / "image-edit")
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
                        "or_link": f"{key}_asset-NN.link.txt", "checked_by": "components/image-edit/reference_check.py",
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


SONG_FIRST = ("SONG FIRST, the editor's own step: make the song in Suno from the brief's song block, pick the master "
              "(every line heard, in order), align its lyrics and slice each sung scene to <scene>.wav; those slices are "
              "the audio inputs of the singing clips. Lyrics are sung, never spoken voice reads.")

PRINT_STEPS = [
    "In 3D Jutsu on your own Higgsfield account: `scene_builder_3d_list_projects`; use the project named `{project}`, or "
    "create it with that name (a project id from someone else's account does not open on yours).",
    "Build the blockout at true size from the prompt: a plain figure per person at their true build, where the scene "
    "puts them, products at their real size, the room's surfaces and light. Camera 9:16. Look-only references show "
    "pose, build and place; they are never sent to the print.",
    "Render it fresh in a `scene_builder_3d_query_python` call (608 x 1080, EEVEE, 8 samples, the size every 3D recipe sets; publish it with "
    "`artifacts.file`). Every print needs its own fresh render: an old render or another project's render fails "
    "with INVALID_GENERATION_REFERENCE.",
    "Upload the print reference today (`media_upload`, PUT the bytes, `media_confirm`); an upload older than a day fails.",
    "Print it: `scene_builder_3d_generate_angles` with the render's operationId and artifactId, the prompt word for "
    "word, referenceMediaId = the upload, 9:16, 2k, a new requestId. Then `scene_builder_3d_get_generation` until it "
    "has succeeded, and look at it against the references: people as their sheets show them, never slimmer or younger.",
    "Wrong: fix the blockout or the prompt and print again (never patch the print). Right: save the get_generation "
    "reply unchanged to a file and run the step's `then` command.",
]


def as_print(st):
    """A picture the editor makes as a 3D print (image-production RULE GATE-4), on their own Higgsfield account: same
    asset, prompt and references; the door is 3D Jutsu's print, never a flat picture call. The look-only references
    (the swipe's frames) shape the blockout; the rest are the print's reference, one picture (a board when several)."""
    st = dict(st)
    sent = [r for r in st.get("references") or [] if not r.get("look_only")]
    st.update({"job": "3d-print", "model_house": None, "higgsfield_model": None, "model_name": "Higgsfield 3D Jutsu",
               "settings": {"aspect_ratio": "9:16", "resolution": "2k", "count": 1},
               "print": {"credits": 2.5, "reference": [r["file"] for r in sent],
                         "prompt_tail": "Keep the blockout's camera, framing, sizes, depth and light exactly. Nothing of "
                                        "the blockout's flat colours carries over. No writing, no captions, no logos."}})
    return st


def print_how(s, key=""):
    """A 3D print step in the words every rendering uses."""
    out = [f"**A 3D print in Higgsfield 3D Jutsu, on your own account, never a flat picture** ({s['print']['credits']} "
           "credits; the blockout and renders are free).", ""]
    how = s["print"].get("how")                 # a hand-off that carries its own 3D builds (3d/JUTSU.md) says it its way
    if not how:
        out += [RECIPES, ""]
    out += [f"{i}. {x.format(project=s['print'].get('project') or key + ' sets')}"
            for i, x in enumerate(how or PRINT_STEPS, 1)]
    ref = s["print"]["reference"]
    out += ["", "Print reference: " + (f"`{ref[0]}`" if len(ref) == 1 else
                                       "one board of " + ", ".join(f"`{r}`" for r in ref) if ref else "none (the blockout and the words carry it)") + ".",
            f"Print with the Step {s['n']} prompt from the core, word for word. Name the result `{s['asset']}`.", ""]
    return out


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
    # GATE-4 (2026-11-10): the main picture is the run's kept 3D set print, never a flat picture made by hand
    fs = getattr(chain, "first_set", lambda *_: None)(brand, run)
    if fs and fs.get("kept"):
        kp = fs["kept"]
        steps = [_set_step(1, key, f"the main picture: set {kp['set']}'s kept print (nothing to make)",
                           {"kept_print": rel(Path(kp["print"]), repo), "print_words": None}, {}, [], brand, products,
                           elements, repo)]
        steps[0]["job"] = "set-print"
    elif fs is not None:
        steps = [_set_step(1, key, "the main picture: build the 3D set in Jutsu at true size, render, print it "
                           "(cast board for people: image-production cast_board.py), file it with picture_sets.py put",
                           fs["ask"], {}, [], brand, products, elements, repo)]
        steps[0]["job"] = "set-build"
    else:
        steps = [_picture_step(1, key, "the main picture" + (" (the approved one: remake only if it is lost)" if ap else ""),
                               chain.picture(recipe), house, brand, products, elements, repo, source)]
    if fs is not None:                       # the words still go on top in the swipe's zones (nothing is spent here)
        try:
            steps[0]["words_on_top"] = _picture_step(1, key, "", chain.picture(recipe), house, brand, products, elements,
                                                     repo, source)["words_on_top"]
        except Exception:                    # noqa: BLE001  a brief with no picture yet keeps the set step alone
            pass
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


def _run_style(rec, repo):
    """The ad's style and the runs it came from, from its writing run (style_id, forked_from, source_run)."""
    try:
        rj = json.loads((Path(repo) / "runs" / "video-teardown" / "_work" / str(rec.get("run") or "") / "run.json").read_text())
    except (OSError, ValueError):
        return None, []
    srcs = [rec.get("run"), rj.get("forked_from"), Path(str(rj.get("source_run") or "")).name]
    return rj.get("style_id"), [s for s in srcs if s]


def _cast_master(folder, repo, style=None):
    """The person's master picture IN THE AD'S STYLE first (casting/<person>/styles/<style>/, 18 Nov: a family-3d ad
    handed the maker the person's photoreal master as IMAGE 1), else the person's own master."""
    roots = ([f"{folder}/styles/{style}"] if style and style not in ("photoreal", "phone-ugc") else []) + [folder]
    for root in roots:
        for f in ("full/master.png", "master.png", "master.jpg", "sheets/master-reference.jpg", "sheets/headshot.jpg"):
            if (Path(repo) / root / f).is_file():
                return f"{root}/{f}"
    return None


def _banked_since(name, brand, repo, sources):
    """A person the brief marks NEW who was banked afterwards from this ad's own swipe (the style chain makes new people
    in the ad's style): casting/<name>/ whose provenance names one of the ad's runs. None when there is none."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    d = Path(repo) / "runs" / "ai-elements" / brand / "casting" / slug
    try:
        prov = (d / "provenance.json").read_text()
    except OSError:
        return None
    return f"runs/ai-elements/{brand}/casting/{slug}" if slug and any(s in prov for s in sources) else None


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
    style, sources = _run_style(rec, repo)
    for c in d.get("cast") or []:
        bank = c.get("bank_id")
        folder = f"runs/ai-elements/{brand}/casting/{bank}" if bank and bank != "NEW" and (Path(repo) / "runs" / "ai-elements" / brand / "casting" / bank).is_dir() else None
        if not folder and sources:
            folder = _banked_since(c.get("name") or c.get("id"), brand, repo, sources)
        el = _el_for_folder(folder, brand, products, elements, repo) if folder else None
        cast[c.get("id") or c.get("name")] = {"who": c.get("name") or c.get("id"), "folder": folder,
                                              "identity": c.get("identity_block") or "", "adjust": c.get("adjustments"),
                                              "master": _cast_master(folder, repo, style) if folder else None,
                                              "element": (el or {}).get("element")}
    slug = product_slug(brand, piece.get("product") or rec.get("product"), products, repo)
    steps = []
    # THE EDITOR BUILDS THE CAST FIRST (owner, 2026-11-17): every person the brief marks NEW gets one cast sheet, the
    # swipe's own frames giving build and pose only, before any start picture uses them
    for cid, c in cast.items():
        if c["folder"]:
            continue
        # the swipe frames the brief's ELEMENTS row names for this person (| KORY | person | NEW | … | swipe K02 and K14 |)
        row = re.search(r"^\|\s*" + re.escape(str(c["who"])) + r"\s*\|\s*person\s*\|(.*)$", md or "", re.M)
        ks = sorted(set(re.findall(r"K(\d{2,3})", row.group(1)))) if row else []
        wr = Path(repo) / "runs" / "video-teardown" / "_work" / str(rec.get("run") or "") / "framemap" / "shots"
        frames = [wr / f"K{k}-mid.jpg" for k in ks if (wr / f"K{k}-mid.jpg").is_file()]
        sheet_refs = [{"n": i + 1, "kind": "image", "role": f"the swipe's person {c['who']} stands in for (pose, build, look only; never the face)",
                       "file": rel(f, repo), "exists": True, "element": None, "look_only": True} for i, f in enumerate(frames)]
        n = len(steps) + 1
        steps.append({"n": n, "asset": asset_name(key, n, "png"), "what": f"cast sheet for {c['who']}: build once, every picture after uses this",
                      "medium": "image", "job": ph["job"], "model_house": {"registry": ph["registry"], "door": ph["door"]},
                      "higgsfield_model": ph["higgsfield_model"], "model_name": PLAIN_MODEL.get(ph["higgsfield_model"]),
                      "prompt": (f"Casting sheet of {c['who']}, an original person resembling no real one: front, three-quarter and profile "
                                 "head shots, and one full body, on a plain light background, "
                                 + ("phone-grade light, real skin with visible pores. " if not style or style in ("photoreal", "phone-ugc")
                                    else f"made in the ad's style ({style}), never photoreal. ")
                                 + (f"Who this is: {c['identity']} " if c.get("identity") else "")
                                 + (f"Changes from the swipe's person: {', '.join(c['adjust']) if isinstance(c['adjust'], list) else c['adjust']}. " if c.get("adjust") else "")
                                 + "The reference pictures give build, presence and posture only, never the face."),
                      "prompt_source": "the brief's NEW cast row; the editor builds the cast first (2026-11-17)",
                      "references": sheet_refs, "settings": {"aspect_ratio": "9:16", "variant": "sunburst", "quality": "high",
                                                              "resolution": "2k", "count": 1},
                      "words_on_top": [], "bars": None, "findings": [], "draft": True, "cast_sheet": True})
        c["master"] = c["master"] or f"{asset_name(key, n, 'png')} (step {n} makes it)"
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
        kind = str(sc.get("kind") or "")
        plate = str((((sc.get(kind) or {}) if kind in ("screen", "card", "endcard") else {}).get("plate")
                     or (sc.get("plate") if kind in ("screen", "card", "endcard") else "")) or "")
        if kind in ("screen", "card", "endcard") and plate:
            # THE PLATE IS A PICTURE (2026-11-19): a screen, card or end card the brief describes as a plate is made
            # (the picture, no words in it; the words are set at the edit) — 3 of 13 scenes of an animated brief had no
            # step. An animated piece's product on the plate comes from its 3D build (VIDEO-RULINGS V58).
            prompt = "\n".join(x for x in (plate, "No words, letters or numbers anywhere in the picture: the words are "
                                            "set on it at the edit.", piece.get("style")) if x)
            try:
                import importlib.util as _iu
                _sp = _iu.spec_from_file_location("rs_product_route", Path(repo) / "components/video-production/machine/product_route.py")
                _pr = _iu.module_from_spec(_sp); _sp.loader.exec_module(_pr)
                if _pr.in_look(piece) and piece.get("product") and re.search(r"\b(FLEX|brush|bottle|product|jar|tube|box)\b", plate, re.I):
                    got, _why = _pr.endcard_ref(brand, piece.get("product"))
                    if got:
                        refs.append({"n": len(refs) + 1, "kind": "image", "role": "the product's 3D build: make it in the "
                                     "picture's own look, same shape, colour and label layout", "file": rel(got, repo),
                                     "exists": exists(got, repo), "element": None})
                        prompt += "\n" + _pr.IN_LOOK_LINE
            except Exception:  # noqa: BLE001 — a plate without its product reference is still a plate
                pass
        if not prompt:                   # every scene gets its picture (2026-11-17 walkthrough: 13 of 20 were in the sheet)
            if kind in ("screen", "card", "endcard"):
                continue                 # no plate described: made in the edit (a screen recording or a card)
            prompt = "\n".join(x for x in (sc.get("happens"), sc.get("setting_id") and f"Place: {sc.get('setting_id')}",
                                            piece.get("style")) if x)
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


def production_route(rec, repo=None):
    """Resolve the maker route from the writing run and registry, never a generation fallback.

    Missing route on legacy video records remains AI. Explicit conflicting routes refuse.
    A shot's REAL/SWAP/AI route and free-text production notes are not maker routes.
    """
    repo = Path(repo or REPO)
    known = ("ai", "creator", "founder")
    claims = []
    route = rec.get("production_route")
    if route in known:
        claims.append(("register.production_route", route))
    typ = str(rec.get("type") or "").split("-", 1)
    if len(typ) == 2 and typ[0] == "video" and typ[1] in known:
        claims.append(("register.type", typ[1]))
    run = str(rec.get("run") or "")
    candidates = [repo / run / "run.json",
                  repo / "runs/video-writing" / str(rec.get("brand") or "") / Path(run).name / "run.json"] if run else []
    for f in dict.fromkeys(candidates):
        if f.is_file():
            doc = json.loads(f.read_text())
            if doc.get("production_route") in known:
                claims.append((rel(f, repo), doc["production_route"]))
    if len({v for _, v in claims}) > 1:
        raise ValueError("Conflicting production routes: " + ", ".join(k + "=" + v for k, v in claims))
    return claims[0][1] if claims else "ai"


def filming_assignment(key, rec, bf, md, route, repo):
    """A creator/founder assignment. Keep source instructions verbatim; invent no shots."""
    doc = _brief_json(md)
    shots = doc.get("filming") or doc.get("scenes") or []
    if not isinstance(shots, list):
        shots = []
    takes = []
    for i, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            continue
        instruction = shot.get("film") or shot.get("action") or shot.get("visual") or shot.get("description")
        if not instruction:
            continue
        takes.append({"asset_id": f"{key}_asset-{i:02d}", "scene": str(shot.get("id") or f"S{i}"),
                      "instructions": instruction, "words": shot.get("voice") or shot.get("words") or "",
                      "expected_takes": shot.get("expected_takes", 1)})
    # v1 creator/founder briefs use labelled Film blocks rather than an AI scenes object.
    if not takes:
        blocks = list(re.finditer(r"(?m)^\*\*Film:\*\*\s*(.+?)(?=^\*\*Film:\*\*|\Z)", md, re.S))
        for i, block in enumerate(blocks, 1):
            takes.append({"asset_id": f"{key}_asset-{i:02d}", "scene": f"S{i}",
                          "instructions": block.group(1).strip(), "words": "", "expected_takes": 1})
    gaps = []
    if not bf or bf.name != "7-final-brief.md":
        gaps.append("A final 7-final-brief.md is required before filming.")
    if not takes:
        gaps.append("No explicit filming instructions found; finish the filming assignment upstream.")
    for take in takes:
        n = take["expected_takes"]
        if type(n) is not int or not 1 <= n <= 100:
            gaps.append(take["asset_id"] + ": expected_takes must be an integer from 1 to 100.")
    ret = return_place(key, rec["brand"], LANES["video"])
    ret.pop("receipt", None)  # Real footage does not require an AI generation receipt.
    ret["manifest"] = "returned/return-manifest.json"
    ret["next"] = "components/image-edit/delivery.py --brand <brand> --ingest-filming <this-folder>"
    template = {"schema": "filming-return/v1", "brief_key": key, "production_route": route, "takes": []}
    for take in takes:
        for n in range(1, take["expected_takes"] + 1 if type(take["expected_takes"]) is int and 1 <= take["expected_takes"] <= 100 else 1):
            template["takes"].append({"asset_id": take["asset_id"], "take": n,
                                      "file": f"{take['asset_id']}_take-{n:02d}.mp4", "sha256": None,
                                      "accepted": False, "reviewer": None, "roll": None, "talks": None, "words": []})
    return {"runsheet": 1, "built": datetime.now().isoformat(timespec="seconds"), "core": "filming",
            "brief_key": key, "brief": rec.get("brief") or key, "brand": rec["brand"], "product": rec.get("product"),
            "kind": "video", "production_route": route, "packet_kind": "filming-assignment",
            "state": "draft" if gaps else "ready", "execution_ready": not gaps,
            "readiness": {"ready": not gaps, "blockers": gaps}, "title": _title(md, rec.get("title") or key),
            "brief_file": rel(bf, repo) if bf else None, "run": rec.get("run"), "production_run": None,
            "deliverable": rel(bf.parent, repo) if bf else None, "return": ret, "return_manifest": template,
            "takes": takes, "steps": [], "elements": [], "gaps": gaps}


FORMATS_DIR = "components/video-production/formats"


def format_home(fid, brand, repo=REPO):
    """Where this brief's format is defined and how it is run (components/video-production/formats/README.md, "One home
    per format"). A format with a home folder gets its FORMAT.md, LEARNINGS.md, skill and workflow command; a format without
    one says so, so the maker runs the shared chain and the run's lessons start that format's home."""
    repo = Path(repo)
    if not fid:
        return {"id": None, "home": None, "note": "The brief names no format. Name it before production: a run is refused without one."}
    folder = repo / FORMATS_DIR / fid
    if not (folder / "format.json").is_file():
        return {"id": fid, "home": None,
                "note": "This format has no home folder yet. Make it with the shared chain; what the run teaches is written "
                        "for the format's first home (" + FORMATS_DIR + "/README.md, One home per format)."}
    doc = json.loads((folder / "format.json").read_text())
    skill = repo / ".claude" / "skills" / fid / "SKILL.md"
    return {"id": fid, "name": doc.get("name") or fid, "status": doc.get("status"), "signed": doc.get("signed"),
            "home": f"{FORMATS_DIR}/{fid}", "format_md": f"{FORMATS_DIR}/{fid}/FORMAT.md",
            "learnings": f"{FORMATS_DIR}/{fid}/LEARNINGS.md",
            "skill": f".claude/skills/{fid}/SKILL.md" if skill.is_file() else None,
            "run": f"python3 components/video-production/machine/workflow.py run {fid} --brand {brand} --label <label>"}


def _run_format(prun, repo):
    """The format a video production run names in its run.json (it wins over the brief's own field)."""
    try:
        return json.loads((Path(repo) / "runs" / "video-production" / prun / "run.json").read_text()).get("format")
    except (OSError, ValueError, TypeError):
        return None


def format_lines(sheet):
    """The run sheet's format section: which format this is, where its instructions live, how to run it, where lessons go."""
    fh = sheet.get("format_home")
    if not fh:
        return []
    lines = ["## The format", ""]
    if not fh.get("home"):
        return lines + [f"Format: `{fh.get('id') or 'none'}`. {fh['note']}", ""]
    local = ((sheet.get("handoff") or {}).get("format") or {})
    lines += [f"Format: **{fh['name']}** (`{fh['id']}`) · {fh['status']}" + (" · signed" if fh.get("signed") else " · unsigned") + ".", "",
              "Every rule of this format lives in its home folder. Read it before making anything.", "",
              "| | |", "|---|---|",
              f"| **Instructions** | `{fh['format_md']}`" + (f" · copy in this folder: `{local['format_md']}`" if local.get("format_md") else "") + " |",
              f"| **Lessons** | `{fh['learnings']}`" + (f" · copy in this folder: `{local['learnings']}`" if local.get("learnings") else "") + " |"]
    if fh.get("skill"):
        lines.append(f"| **Skill** | `{fh['skill']}` (Claude Code: say \"produce this {fh['name'].lower()}\") |")
    lines += [f"| **Run it** | `{fh['run']}` (in the team workspace; it hands out one step at a time and stops at every review) |", "",
              "What the run teaches goes into `returned/learned.md`, one line per lesson, each with its home from the routing "
              "table in the lessons file. A home is changed only after the owner says yes.", ""]
    return lines


def build(brief_key, brand=None, repo=None, chain=None):
    """The run sheet for one brief, as a dict (what run.json holds)."""
    repo = Path(repo or REPO)
    chain = chain or Chain(repo)
    key, rec = chain.lookup(brief_key, brand)
    reg_key, key = key, home_key(key, rec.get("brand") or brand, repo)
    kind = _kind(rec)
    bf = _brief_file(rec, kind, repo)
    md = bf.read_text() if bf else ""
    route = production_route(rec, repo) if kind == "video" else None
    if route in ("creator", "founder"):
        return filming_assignment(key, rec, bf, md, route, repo)
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
    blockers = []
    if not steps:
        blockers.append("No production steps.")
    # an approved, numbered video brief with no production run is the EDITOR's to build, picture to clip (owner,
    # 2026-11-17): a drafted prompt and an input an earlier step makes are the work itself, never a blocker. Every
    # picture in it is a 3D print the editor makes on their own Higgsfield account (image-production RULE GATE-4)
    editor_builds = kind == "video" and not prun and bool(re.search(r"brief-\d+", key))
    made_here = lambda f: bool(re.search(r"\(step \d+ makes it\)|\(not made yet: step \d+ makes it\)|not read yet|not banked yet|not sliced yet", str(f)))  # noqa: E731
    if editor_builds:
        steps[:] = [as_print(st) if st["medium"] == "image" and st.get("job") not in ("words-only", "set-change") else st
                    for st in steps]
    for st in steps:
        if st.get("draft") and not editor_builds:
            blockers.append(f"step {st['n']}: draft prompt; finish production upstream.")
        for ref in st.get("references") or []:
            if not ref.get("exists") and not (editor_builds and made_here(ref.get("file"))):
                blockers.append(f"step {st['n']}: unresolved input {ref.get('file')}")
        if editor_builds:                # the maker's own work, in order, never a stop that waits on the owner
            st["findings"] = [SONG_FIRST if str(x).startswith("BLOCKED: approve the Suno master") else x
                              for x in st.get("findings") or []]
        blockers.extend(f"step {st['n']}: {x}" for x in st.get("findings") or [] if str(x).startswith("BLOCKED"))
    if editor_builds and any(SONG_FIRST in (st.get("findings") or []) for st in steps):
        out["gaps"] = out["gaps"] + [SONG_FIRST]
    if editor_builds:
        out["editor_builds"] = True
        out["gaps"] = out["gaps"] + ["The editor builds this brief end to end: the cast sheet first, then every start picture "
                                     "from it (each one a 3D print in Higgsfield 3D Jutsu, on the editor's own account), then "
                                     "every clip, then the cut. Drafted prompts are the brief's own words; tighten them "
                                     "against BRIEF.md as you go."]
    out.update({"production_route": route, "packet_kind": "generation", "state": "draft" if blockers else "ready",
                "execution_ready": not blockers, "readiness": {"ready": not blockers, "blockers": blockers}})
    out["deliverable"] = rel(bf.parent, repo) if bf and bf.parent.name == "deliverable" else None
    if kind == "video":
        out["format_home"] = format_home((_run_format(prun, repo) if prun else None) or out["format"], brand, repo)
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
    return {"asset": f"{key}-control.mp4", "order": [st["asset"] for st in sheet["steps"] if st.get("medium") != "image"], "rules": (["Use the approved Suno master as the continuous soundtrack. Mute all generated clip audio; never replace lyrics with spoken voice reads.", "Align every scene and lip-sync slice to the actual song timing before cutting. Durations are pending until the master is approved.", "Use only video clips in the cut; start pictures are references. Captions follow the sung words and stay clear of faces.", "9:16, 1080x1920. Master to -14 LUFS."] if sheet.get("format") == "song-ad" else CUT_RULES),
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
    s = next((x for x in sheet["steps"] if x.get("job") not in ("words-only", "set-change", "3d-print")), None)
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


RECIPES = ("**Not in your Higgsfield account?** Rebuild it, free, from `components/3d-recipes/` on GitHub: its README lists "
           "every product and world and how to run one in any account. A set that has no recipe is built fresh from this "
           "brief, on the product's recipe.")


def set_how(s):
    """A set change in the words every rendering uses: the request's own steps, then the words and the name."""
    ask = s["set_request"]
    out = [f"**A change to the 3D set, in Higgsfield 3D Jutsu, never a flat picture.** "
           f"The change: {ask.get('change')}. Set request: `{ask.get('set')}` ({ask.get('credits')} credits to print).", ""]
    out += [RECIPES, ""]
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
            L.append(f"| {e['kind']} | {e['name']} | " + (f"`{hf.get('name') or e['name']}` · `<<<{hf['id']}>>>`" if hf else "none yet") +
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
        elif s["job"] == "3d-print":
            L += ["A 3D print in Higgsfield 3D Jutsu, made on the editor's own account, not a flat picture.", ""]
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
                L.append(f"| {tag} {r['n']} | {r['role']} | " + (f"`{hf.get('name') or e.get('name') or hf.get('id')}`" if hf else "-") +
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
TEXT_FROM_GITHUB = ("Read BRIEF.md, RUN.md and run.json from GitHub (company-team/ai-workspace, the same path as on the "
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
        if s["job"] == "3d-print":
            L += print_how(s, sheet.get("brief_key") or "")
            continue
        by_el, files = _refs_for(s)
        page = "Image → Create Image" if s["medium"] == "image" else "Video → Create Video"
        n = 1
        L.append(f"{n}. Open higgsfield.ai, go to **{page}**, and pick the model **{s['model_name']}**.")
        for eid, x in by_el.items():
            n += 1
            fall = [r for r in s["references"] if r["n"] in x["images"] and r["kind"] == "image"]
            if not x["el"]["element"].get("name"):  # an element with no name cannot be @-mentioned: its files go in
                L.append(f"{n}. The {x['el']['name']} element has no name to @-mention in the web app: upload these files, "
                         "in this order: " + ", ".join(f"`{_f(r)}`" for r in fall) + ".")
                continue
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
            if c.get("element") and c["element"].get("name"):
                n += 1
                L.append(f"{n}. First choice: @-mention **{c['element']['name']}** for {c['who']}."
                         + (f" If the model will not take it, upload `{fb}` instead." if fb else ""))
            elif c.get("element") and fb:       # an element with no name cannot be @-mentioned in the web app
                n += 1
                L.append(f"{n}. {c['who']}'s Higgsfield element has no name to @-mention here: upload `{fb}` as the "
                         "picture of them.")
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
        if s["job"] == "3d-print":
            L += print_how(s, sheet.get("brief_key") or "")
            continue
        by_el, files = _refs_for(s)
        k = [0]

        def say(x):
            k[0] += 1
            L.append(f"{k[0]}. {x}")
        if by_el:
            ids = ", ".join(f"`<<<{x['el']['element']['id']}>>>` ({x['el']['element'].get('name') or x['el'].get('name')}, IMAGE "
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
        if s["job"] == "3d-print":
            L += print_how(s, sheet.get("brief_key") or "")
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
    if sheet.get("packet_kind") == "filming-assignment":
        lines = [f"# FILMING ASSIGNMENT · {sheet['brief_key']}", "",
                 f"Route: {sheet['production_route']} · {sheet['state']}. Read BRIEF.md in full before filming.", "",
                 "Keep each raw take separate; do not generate AI substitutes. Asset IDs stay with the takes.", ""]
        for gap in sheet["gaps"]:
            lines.append("BLOCKED: " + gap)
        for take in sheet["takes"]:
            lines += [f"## {take['asset_id']} · {take['scene']} · {take['expected_takes']} take(s)", "",
                      str(take["instructions"]), "", str(take["words"]), ""]
        lines += ["## Return", "", "Copy RETURN-MANIFEST.template.json to returned/return-manifest.json. Put raw files in returned/.",
                  "Fill each take's file, SHA-256, roll (a/b), talks, timed words for speech, and acceptance/reviewer after review.",
                  "Unaccepted or incomplete returns stay blocked. The intake produces edit-kit.json for video-edit's existing start door.",
                  "Raw takes are never a finished ad or a Meta delivery.", "",
                  "`python3 components/image-edit/delivery.py --brand " + sheet["brand"] + " --ingest-filming <this-folder>`", ""]
        return "\n".join(lines)
    r = sheet["return"]
    head = [f"# RUN SHEET · {sheet['brand'].upper()} · {sheet['title']} · {sheet['brief_key']}", "",
            "How to make this brief, from any tool. The brief says what to make; this says how. The core is Higgsfield: "
            "every tool below runs the same calls.", "",
            "| | |", "|---|---|",
            f"| **Brief** | `{sheet['brief_key']}` · `{sheet['brief_file'] or 'no brief file found'}` |",
            f"| **Readiness** | {sheet.get('state', 'legacy')} · execution ready: {sheet.get('execution_ready', 'not recorded')} |",
            f"| **Makes** | {len(sheet['steps'])} asset(s): `{sheet['steps'][0]['asset'] if sheet['steps'] else '-'}`"
            + (f" to `{sheet['steps'][-1]['asset']}`" if len(sheet["steps"]) > 1 else "") + " |",
            f"| **Product** | {sheet['product'] or 'none'} |",
            f"| **Core** | Higgsfield · " + ", ".join(sorted({f"{s['model_name']} (`{s['higgsfield_model']}`)" for s in sheet["steps"] if s.get("higgsfield_model")})) + " |",
            f"| **Return to** | `{r['repo']}` · Drive `{r['drive']}` |",
            f"| **Built** | {sheet['built']} by `components/briefs/runsheet.py` |", ""]
    h = sheet.get("handoff")
    if h:
        head[-1:] = [f"| **This folder** | `{h['folder']}/` · Drive `{h['drive']}/` |",
                     f"| **In it** | `BRIEF.md` (the brief), this `RUN.md`, `run.json`, and `refs/`: the {len(h['refs'])} "
                     "file(s) the steps below send" + (", plus each clip's own folder `refs/<clip>/`" if h.get("per_clip") else "")
                     + ", so nothing outside this folder is needed |", "",
                     "Open this folder on Google Drive. A person follows **section A**; an agent follows **section B** "
                     "(or C). Put the finished files in `returned/`.", ""]
    head += format_lines(sheet)
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


def swipe_into(folder, run, repo=None):
    """THE SWIPE TRAVELS WITH THE BRIEF (2026-11-19: a hand-off reached the editor without the video it remakes).
    Copies the writing run's swipe video into <folder>/swipe/swipe.mp4 and writes swipe/SOURCE.md (where it came
    from). Looks in the working run, then the filed teardown. Returns the copied path, or None when the run has none."""
    import shutil
    repo = Path(repo or REPO)
    run = str(run or "").strip()
    if not run:
        return None
    cands = [repo / "runs" / "video-teardown" / "_work" / run / "source.mp4"]
    cands += sorted((repo / "runs" / "video-teardown").glob(f"*/{run}/source.mp4"))
    src = next((c for c in cands if c.is_file() and c.stat().st_size > 50000), None)
    if not src:
        return None
    out = Path(folder) / "swipe"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / "swipe.mp4"
    if not dst.is_file() or dst.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dst)
    try:
        rj = json.loads((src.parent / "run.json").read_text())
    except (OSError, ValueError):
        rj = {}
    link = rj.get("post_url") or rj.get("source_url") or rj.get("swipe") or ""
    (out / "SOURCE.md").write_text("# The swipe\n\n`swipe.mp4` is the video this ad remakes: watch it before the "
                                   "first clip.\n\n- Writing run: `%s`\n- Original: %s\n" % (run, link or "not recorded"))
    return dst


def profile_into(root, s, repo):
    """The full profile the piece was written from (creative-strategist who.attach), as PROFILE.md and profile.json beside
    BRIEF.md. A brief written before profiles has none, and nothing is made up for it."""
    import shutil
    run, bf = str(s.get("run") or ""), s.get("brief_file")
    places = [repo / run, repo / "runs" / "video-teardown" / "_work" / run.rstrip("/").split("/")[-1]] + ([(repo / bf).parent, (repo / bf).parent.parent] if bf else [])
    for d in places:
        if (d / "profile.json").is_file():
            shutil.copy2(d / "profile.json", root / "profile.json")
            if (d / "profile.md").is_file():
                shutil.copy2(d / "profile.md", root / "PROFILE.md")
            return True
    return False


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
    if s.get("packet_kind") != "filming-assignment":
        s["return"] = return_place(key, brand, role)
    elif role != LANES["video"]:
        raise ValueError("Filming assignments use the existing video-editor handoff lane.")
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
    swipe_into(root, s.get("run"), repo)        # the swipe video travels with the brief (2026-11-19)
    profile_into(root, s, repo)                 # and the full profile of who it is for (2026-11-25)
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

    style = _run_style({"run": s.get("run")}, repo)[0]          # the ad's style: its people's masters in that style
    for st in s["steps"]:
        for r in st["references"]:
            if not r.get("exists"):
                if "(not " not in str(r["file"]):
                    missing.append(f"step {st['n']} {r['kind']} {r['n']}: {r['file']}")
                continue
            r.update(place(r["file"], _ref_name(r, st["n"], len(uses[r["file"]]) > 1)))
        for c in st.get("cast") or []:
            m = _cast_master(c["folder"], repo, style) if c.get("folder") else None
            if m:
                c["fallback"] = place(m, f"cast-{Path(c['folder']).name}-{STEM_WORD.get(Path(m).stem) or _slug(Path(m).stem, 3)}"
                                         f"{Path(m).suffix.lower()}")
    for e in s["elements"]:
        mine = [x["local"] for x in refs if x["source"].startswith(str(e.get("folder") or "\0") + "/")]
        if not mine and e.get("folder"):
            f = (f"{e['folder']}/model/product-sheet.png" if e["kind"] == "product" else _cast_master(e["folder"], repo, style))
            if f and (repo / f).is_file():
                mine = [place(f, f"{e['kind']}-{e['id']}-{STEM_WORD.get(Path(f).stem) or _slug(Path(f).stem, 3)}"
                                 f"{Path(f).suffix.lower()}")["local"]]
        e["refs"] = mine
    shutil.copy2(bf, root / "BRIEF.md")
    s["gaps"] = [g for g in s["gaps"] if not g.startswith("Reference files are named by their repo path")]
    s["handoff"] = {"folder": home, "drive": drive, "role": role,
                    "brief": {"local": "BRIEF.md", "file": f"{home}/BRIEF.md", "drive": f"{drive}/BRIEF.md", "source": s["brief_file"]},
                    "refs": refs, "missing": missing}
    extra = []
    if s.get("kind") == "video":
        delivery = _load(HERE / "video_delivery.py", "briefs_video_delivery")
        extra += delivery.pack(root)
    fh = s.get("format_home") or {}
    if fh.get("home"):
        # the format's instructions and lesson routing travel with the folder, so a maker without the repo has them;
        # the home folder stays the live copy
        (root / "format").mkdir(exist_ok=True)
        local = {}
        for k, name in (("format_md", "FORMAT.md"), ("learnings", "LEARNINGS.md")):
            src = repo / fh[k]
            if src.is_file():
                (root / "format" / name).write_text(f"<!-- Copy of {fh[k]} as packed {s['built'][:10]}. The live copy is that file. -->\n"
                                                    + src.read_text())
                local[k] = f"format/{name}"
                extra.append(f"format/{name}")
        s["handoff"]["format"] = local
    if s.get("packet_kind") == "filming-assignment":
        template = "RETURN-MANIFEST.template.json"
        (root / template).write_text(json.dumps(s["return_manifest"], indent=2) + "\n")
        extra.append(template)
    (root / "RUN.md").write_text(render_md(s))
    (root / "run.json").write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")
    contract = _load(HERE / "delivery_contract.py", "briefs_delivery_contract")
    if contract.pack(root, record=s):
        extra += ["DELIVERY-REQUIREMENTS.json", "DELIVERY-CHECKLIST.md", "delivery-state.json"]
        extra += [str(p.relative_to(root)) for p in (root / "revisions").rglob("*.json")]
    return {"folder": home, "drive": drive, "files": ["BRIEF.md", "RUN.md", "run.json"] + extra + [x["local"] for x in refs],
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
