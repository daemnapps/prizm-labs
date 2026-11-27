"""The reference pictures a talking clip carries beside its first frame (2026-10-30): the same depth a picture gets.

A clip starts from its approved picture (Image 1) and also sees what that picture was made from: the person's face and
angles, her outfit and accessories, the room. Worked out from the run, so every video gets them the same way.
Public: for_call(run, call, root) -> [{"file", "job"}]; notes(run, call, root) -> the product's size, grip and never-show lines.
"""
import json
import re
import sys
from pathlib import Path

# the start picture's own inputs, by what the picture chain called them -> what the clip is told to use them for
FROM_PICTURE = (("outfit", "the outfit: the fabric, drape and how it moves"),
                ("accessor", "the accessories: keep each one the same throughout"),
                ("room picture", "the room: keep its depth, light and haze"),
                ("worn by", "the outfit: the fabric, drape and how it moves"))
SMALL = {"a", "an", "the", "of", "small", "pile"}


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def model_of(root, run=None):
    """The run's clip model: its format's playbook `stages.clips.model`, else the house default."""
    fmt = (read(Path(run) / "plan.json").get("format") or read(Path(run) / "run.json").get("format")) if run else None
    if fmt:
        pb = read(Path(root) / "components/video-production/formats/playbooks" / f"{fmt}.json")
        got = ((pb.get("stages") or {}).get("clips") or {}).get("model")
        if got:
            return got
    return "seedance-2.5"


def limit(root, run=None):
    """The clip model's own picture limit, less the first frame."""
    sheet = read(Path(root) / "components/model-inputs/inputs" / f"{model_of(root, run)}.json")
    return int((sheet.get("limits") or {}).get("max_images", 30)) - 1


def brand_of(run):
    return read(Path(run) / "run.json").get("brand") or read(Path(run) / "plan.json").get("brand")


def in_scenes(run, call, kind):
    """The run's elements of one kind that this clip's scenes use."""
    scenes = set(call.get("scenes") or [])
    items = list(read(Path(run) / "elements.json").get("items") or [])
    parent = read(Path(run) / "run.json").get("parent_run")
    if parent:                                  # a variation's scene also holds what the scene it replaces held
        items += read(Path(run).parents[len(Path(parent).parts) + 1] / parent / "elements.json").get("items") or []
    return [i for i in items if i.get("kind") == kind and scenes & {str(x).rstrip(":") for x in i.get("scenes") or []}]


def scene_text(run, call):
    """Everything written about what happens in this clip's scenes."""
    plan = read(Path(run) / "plan.json")
    rows = [s for s in plan.get("scenes") or [] if s.get("id") in (call.get("scenes") or [])]
    keys = ("happens", "gestures", "beats", "shots", "first_frame")
    return json.dumps([{k: s.get(k) for k in keys} for s in rows], ensure_ascii=False).lower()


def person_refs(run, call, root):
    banks = {i.get("id"): i.get("bank_id") for i in read(Path(run) / "elements.json").get("items") or [] if i.get("kind") == "person"}
    out = []
    for who in call.get("people") or []:
        d = Path(root) / "runs/ai-elements" / str(brand_of(run)) / "casting" / str(banks.get(who) or who).lower() / "sheets"
        for name, job in (("headshot.jpg", "the face up close: keep it exactly, every line and mark"),
                          ("angles-expressions.jpg", "the same person from every angle and with every expression: use it when the head turns")):
            if (d / name).is_file():
                out.append({"file": str((d / name).relative_to(root)), "job": job})
    return out


def picture_refs(run):
    out = []
    for row in read(Path(run) / "picture-preview.json").get("inputs") or []:
        role = str(row.get("role") or "").lower()
        job = next((j for key, j in FROM_PICTURE if key in role), None)
        if job and row.get("path") and "stand-in" not in role and "grey" not in role:
            out.append({"file": row["path"], "job": job})
    return out


# What a product is called in a script: a word of this kind that names no banked product is a plan stop (clip rule 12).
PRODUCT_WORDS = ("cream", "lotion", "oil", "jelly", "scrub", "serum", "balm", "gel", "mask", "cleanser", "moisturiser",
                 "moisturizer", "toner", "exfoliant", "bundle", "duo", "kit")


def bank_products(run, root) -> list:
    """The brand's banked products (each with a casting folder), by id."""
    d = Path(root) / "runs/ai-elements" / str(brand_of(run)) / "products"
    return sorted(x.name for x in d.iterdir() if x.is_dir() and ((x / "kit.json").is_file() or (x / "model").is_dir())) \
        if d.is_dir() else []


def actions_of(run, call) -> str:
    """What the clip's scenes DO (the beats' actions and what happens), the part a model draws."""
    plan = read(Path(run) / "plan.json")
    sids = set(call.get("scenes") or [])
    rows = [s for s in plan.get("scenes") or [] if s.get("id") in sids]
    out = [str(s.get("happens") or "") for s in rows]
    out += [str(b.get("do") or "") for s in rows for b in s.get("beats") or [] if isinstance(b, dict)]
    cm = read(Path(run) / "clips" / "camera-motion.json").get("scenes") or {}
    out += [str(b.get("do") or "") for sid in sids for b in ((cm.get(sid) or {}).get("motion") or {}).get("beats") or []
            if isinstance(b, dict)]
    return " \n ".join(out).lower()


def words_of(run, call) -> str:
    """Every word written or said in this clip's scenes: what happens, the beats and their lines, what is said, the
    shots, and the camera and motion plan's beats (never the prompt, whose negative lines name things to leave out)."""
    plan = read(Path(run) / "plan.json")
    sids = set(call.get("scenes") or [])
    rows = [s for s in plan.get("scenes") or [] if s.get("id") in sids]
    keys = ("happens", "beats", "say", "lines")
    cm = read(Path(run) / "clips" / "camera-motion.json").get("scenes") or {}
    more = [((cm.get(sid) or {}).get("motion") or {}).get("beats") for sid in sids]
    lines = [x.get("text") or x.get("line") for x in call.get("lines") or [] if isinstance(x, dict)]
    out = []

    def walk(v):                                         # the values only: a field's name is never a word said
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, str) and not re.search(r"[/\\]|\.\w{2,4}\b", v):   # never a file or a path
            out.append(v)
    walk([{k: s.get(k) for k in keys} for s in rows] + more + lines)
    return " \n ".join(out).lower()


def named_products(run, call, root) -> tuple:
    """(ids, unmatched): the banked products this clip's words name, and the product words that name none. A product
    is named by its full name, a pair of its words no other product shares, or a word only it has; an ambiguous word
    goes to a product the run already uses. A word that is part of one of the scene's props (a cream vessel) is the
    prop, never a product."""
    bank = bank_products(run, root)
    d = Path(root) / "runs/ai-elements" / str(brand_of(run)) / "products"
    every = sorted(x.name for x in d.iterdir() if x.is_dir()) if d.is_dir() else bank
    text = words_of(run, call)
    props = " ".join(str(i.get("id") or "").lower().replace("-", " ") for i in in_scenes(run, call, "prop"))
    used = {str(i.get("bank_id") or "") for i in in_scenes(run, call, "product")} | \
           {str(i.get("bank_id") or "") for i in read(Path(run) / "elements.json").get("items") or [] if i.get("kind") == "product"}
    toks = {b: b.split("-") for b in bank}
    count = {}
    for b in every:                                     # a word shared with ANY product folder is not unique
        for w in set(b.split("-")):
            count[w] = count.get(w, 0) + 1
    pairs = {}
    for b in every:
        t = b.split("-")
        for i in range(len(t) - 1):
            pairs.setdefault(" ".join(t[i:i + 2]), set()).add(b)

    def said(phrase):
        hits = [m for m in re.finditer(r"\b" + re.escape(phrase) + r"s?\b", text)]
        return bool(hits) and not re.search(r"\b" + re.escape(phrase) + r"\b", props)

    got, covered = set(), set()
    for b, t in toks.items():
        if said(" ".join(t)):
            got.add(b)
            covered |= set(t)
    for ph, owners in pairs.items():
        if len(owners) == 1 and said(ph) and next(iter(owners)) in toks:
            got |= owners
            covered |= set(ph.split())
    for b, t in toks.items():
        for w in t:
            # a lone word names a product only when it is a product-type word ("cream", "serum"): "face" or "body"
            # alone is a part of a person, never a product
            if w not in PRODUCT_WORDS:
                continue
            if said(w) and (count[w] == 1 or b in used):
                if count[w] == 1 or not any(b2 in used for b2 in bank if b2 != b and w in toks[b2]):
                    got.add(b)
                    covered.add(w)
    acts = actions_of(run, call)
    unmatched = sorted({w for w in PRODUCT_WORDS if w not in covered and said(w)
                        and not any(w in toks[b] for b in got)
                        and re.search(r"\b" + re.escape(w) + r"s?\b", acts)})   # drawn only when it is acted
    return sorted(got), unmatched


def products(run, call, root):
    """[(name, refs, line)] for each product the clip's scenes use — the run's own product elements AND every banked
    product the scene's words or beats name (owner, 2026-11-20: a cream named in a line was drawn as an invented jar) —
    off its kit, the same call a picture makes."""
    path = str(Path(root) / "components/image-production")
    if path not in sys.path:
        sys.path.append(path)
    from image_production import plain
    ids = [call["_only"]] if call.get("_only") else product_ids(run, call, root)
    got = [plain.product(brand_of(run), b) for b in ids]
    return [g for g in got if g]


# The sections that show the problem: our product is never the thing that fails or the thing that hurts, so a scene
# in one of these shows no brand product (a "face wash that doesn't work" shelf gets plain unbranded bottles).
PROBLEM_SECTIONS = {"problem", "failed-solutions", "agitation"}


def problem_scene(run, call) -> bool:
    """True when every scene of this clip is a problem-side scene (PROBLEM_SECTIONS, from plan.json's `section`)."""
    secs = {s.get("id"): str(s.get("section") or "").lower() for s in read(Path(run) / "plan.json").get("scenes") or []}
    scenes = [str(x).rstrip(":") for x in call.get("scenes") or []]
    return bool(scenes) and all(secs.get(x) in PROBLEM_SECTIONS for x in scenes)


def product_ids(run, call, root) -> list:
    """The banked products this clip shows: the run's own product elements of its scenes, then every banked product
    its words or beats name (clip rule 12). [] for a problem-side scene (PROBLEM_SECTIONS)."""
    if problem_scene(run, call):
        return []
    ids = [i.get("bank_id") for i in in_scenes(run, call, "product")]
    try:
        ids += [b for b in named_products(run, call, root)[0] if b not in ids]
    except Exception:  # noqa: BLE001 -- a bank that cannot be read leaves the run's own elements
        pass
    return [b for b in ids if b]


def texture_sheet(model: Path, pid: str):
    """The product's texture sheet (`model/formula/<product>-formula.*`, its photos and words in one picture), or None."""
    d = Path(model) / "formula"
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if (d / (pid + "-formula" + ext)).is_file():
            return d / (pid + "-formula" + ext)
    return next(iter(sorted(d.glob("*-formula.*"))), None) if d.is_dir() else None


def product_refs(run, call, root):
    """EXACTLY TWO PICTURES A PRODUCT (owner, 2026-11-20: "you just send the texture sheets in with the product sheets.
    It's as simple as that."): its casting sheet (`model/product-sheet.png`) and its texture sheet
    (`model/formula/<product>-formula.*`), each named in the prompt. A product with no casting sheet falls back to its
    kit's own photos (image-production plain.product) so it is never left out."""
    out = []
    home = Path(root) / "runs/ai-elements" / str(brand_of(run)) / "products"
    for pid in product_ids(run, call, root):
        model = home / pid / "model"
        sheet = model / "product-sheet.png"
        name = pid.replace("-", " ").upper()
        if sheet.is_file():
            out.append({"file": str(sheet.resolve().relative_to(Path(root).resolve())),
                        "job": f"the product's casting sheet ({name}): the real product, its exact shape, size, colour "
                               f"and label"})
            tex = texture_sheet(model, pid)
            if tex:
                out.append({"file": str(tex.resolve().relative_to(Path(root).resolve())),
                            "job": f"the texture sheet of {name}: copy the colour and texture of what comes out of it "
                                   f"exactly, as the sheet shows it"})
            continue
        got = products(run, {**call, "_only": pid}, root)
        for nm, refs, _ in got:
            out += [{"file": str(Path(f).resolve().relative_to(Path(root).resolve())),
                     "job": f"the real {nm}: {says or 'how it really looks'}"} for f, says in refs]
    return out


def prop_picture(d):
    return next((d / n for n in ("picture.jpg", "picture.png") if (d / n).is_file()), None)


def prop_refs(run, call, root):
    """Each prop this shot actually shows, by its picture. Only what the action names goes in: a picture of something
    not in the shot would bring it into the shot. A prop on the scene's element list counts when the action names what
    it is (the last word of its name)."""
    bank = Path(root) / "runs/ai-elements" / str(brand_of(run)) / "props"
    text = scene_text(run, call)
    named = [str(i.get("bank_id")) for i in in_scenes(run, call, "prop")
             if re.search(r"\b%s" % re.escape(str(i.get("bank_id")).split("-")[-1].rstrip("s")), text)]
    out = []
    for d in sorted(bank.iterdir()) if bank.is_dir() else []:
        words = [w for w in d.name.split("-") if w not in SMALL]
        said = bool(words) and bool(re.search(r"\b%s" % re.escape(" ".join(words)), text))   # named as one thing, never two far-apart words
        if re.search(r"pasted|graphic|cartoon|cross-section|overlay", d.name):
            continue                # the edit's layer, never an object in the shot (2026-10-31)
        pic = prop_picture(d)
        if pic and any(n == d.name or (said and n in d.name) for n in named):      # on the scene's own list, never a word match alone
            out.append({"file": str(pic.relative_to(root)), "job": "the real " + " ".join(words) + ": its true shape, size and material"})
    return out


def for_call(run, call, root, people=True):
    """What the shot needs, most important first: people, product, props, then what made the picture — on EVERY call,
    talking or silent (owner, 2026-11-20: "all of the AI video prompts always need to have the same setup that's already
    in the chain"; a silent call is sent in reference mode when it carries them, seedance.motion). `people=False` leaves
    out the people's sheets only (a talking long take carried by its start picture); the product and the props always go."""
    seen, out = set(), []
    for ref in (person_refs(run, call, root) if people else []) + product_refs(run, call, root) + prop_refs(run, call, root) \
            + picture_refs(run):
        if ref["file"] not in seen and (Path(root) / ref["file"]).is_file():
            seen.add(ref["file"])
            out.append(ref)
    return out[:limit(root, run)]


def notes(run, call, root):
    """How each product really behaves: size, grip, what it never does."""
    return [line for _, _, line in products(run, call, root) if line]
