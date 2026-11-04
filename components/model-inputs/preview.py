#!/usr/bin/env python3
"""The preflight: for any job, exactly what would be sent to the model, checked against that model's rulebook, with the
cost quoted for free. It generates nothing, spends nothing, and sends nothing.

    import preview
    r = preview.preview("pictures.generate", {"brand": "brand-b", "run": "brand-b-batch-grandma-church-after-fight",
                                              "product": "brilliance-face-scrub"})
    r["prompt"]; r["inputs"]; r["settings"]; r["findings"]; r["cost"]; r["ladder"]; r["ok"]

    python3 preview.py pictures.generate brief.json          # brief.json, or a JSON string; --json prints the whole answer
    python3 preview.py clips.seedance '{"run": "brand-b/yai-sun-spots-back", "call": "G01-C1-1"}'
    python3 preview.py --fields pictures.generate            # which fields a brief for this job takes

THE GATE: the command exits 1 when the rulebook finds an error (and 2 when the builder cannot assemble the job), so a
chain can run it first and refuse to spend. A warning is shown and does not stop anything.

WHAT IT IS MADE OF. Nothing is written here that a chain also writes. Each job has a BUILDER in BUILDERS: a function
that takes the brief and calls the chain's OWN builder (the picture text and references from
image-teardown/tools/pictures.py picture_inputs → image_production/plain.py plan(); the clip prompt from
video-production/machine/clips_run.py plan() → seedance_prompt.py build()). A new job plugs in without touching this
file: add a line to `builders.json` ({"clips.backup": "path/relative/to/components/file.py:function"}) or call
`register(job, fn)`. A builder returns {"model", "door", "prompt", "inputs": [{"n","role","path"}], "settings": {...},
"fields": {...}, "notes": [...]}; this file adds the House answer, the rulebook findings, the quote and the ladder.

No credential, no network except the free Higgsfield quote (`higgsfield generate cost`), which is skipped with its reason
when the command line is not signed in. Python 3.9.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
REPO = COMP.parent
sys.path.insert(0, str(HERE))
import input_rules as IR                                   # noqa: E402

BUILDERS = {}
BUILDERS_FILE = HERE / "builders.json"

# What takes over when the first rung fails or is refused: House jobs in order (resolved live from the House, so a model
# change there shows here), plus plain-words rungs. Only the Model House says which model; this says the order.
LADDER = {
    "pictures.generate": ["retry once", "pictures.backup", "pictures.object", "pictures.safety_net", "pictures.overflow"],
    "pictures.edit": ["retry once", "pictures.backup", "pictures.object", "pictures.safety_net", "pictures.overflow"],
    "pictures.backup": ["pictures.object", "pictures.safety_net"],
    "pictures.object": ["none yet"],
    "clips.seedance": ["another take (three at most)", "clips.backup", "the best take is kept and flagged below_criteria"],
    "clips.backup": ["the best take is kept and flagged below_criteria"],
    "swipe_footage.swap": ["swipe_footage.motion_transfer when the swap kept the original face"],
    "swipe_footage.motion_transfer": ["none yet"],
}


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


def register(job, fn):
    BUILDERS[job] = fn


def _load(path):
    p = Path(path)
    p = p if p.is_absolute() else COMP / p
    spec = importlib.util.spec_from_file_location("pv_" + re.sub(r"\W", "_", str(p)), p)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(p.parent))
    spec.loader.exec_module(mod)
    return mod


def builder_for(job):
    if job in BUILDERS:
        return BUILDERS[job]
    if BUILDERS_FILE.is_file():
        ref = json.loads(BUILDERS_FILE.read_text()).get(job)
        if ref:
            path, _, fn = ref.partition(":")
            return getattr(_load(path), fn)
    raise KeyError(f"no preview builder for job {job!r} yet (have: {', '.join(sorted(jobs()))}); a job plugs in by a line in "
                   f"components/model-inputs/builders.json")


def jobs():
    out = set(BUILDERS)
    if BUILDERS_FILE.is_file():
        out |= {k for k in json.loads(BUILDERS_FILE.read_text()) if not k.startswith("_")}
    return sorted(out)


# ------------------------------------------------------------------------------------------------ the pictures

def _image_chain():
    root = str(COMP / "image-production")
    if root not in sys.path:
        sys.path.append(root)
    import image_production as IP                          # noqa: F401
    from image_production import plain
    return plain


def _lane_run(brand, run):
    p = _teardown_run(REPO, run, brand)
    if not (p / "out" / "03-injection.md").is_file():
        raise ValueError(f"{brand}/{run}: no brand step yet ({p}/out/03-injection.md)")
    return p


PICTURE_FIELDS = {
    "brand": "the brand folder name", "run": "the image-teardown run (its brand step, swipe and real pieces are read from it)",
    "product": "the product kit slug, or empty for no product", "swaps": "THE SWAPS text (default: the run's)",
    "words": "the words on the picture (default: the run's 'Our copy' zones)", "note": "one more line for this picture only",
    "with_ref": "the swipe goes in as IMAGE 1 (default true)", "people": "lookalike or made-up (default: by whether there is a swipe)",
}


COPY_ROW = re.compile(r"^(\|\s*(?:Zone\b|[A-Z]\b)[^|]*\|[^|]*\|[^|]*\|)([^|]*)(\|\s*)$", re.M)  # "Zone A" or "A — top offer note"


def _our_copy(words):
    """The 'Our copy' cell of each zone row in the brand step's words table: [(zone, text)]."""
    return [(m.group(1).split("|")[1].strip(), m.group(2).strip()) for m in COPY_ROW.finditer(words or "")
            if not m.group(1).split("|")[1].strip().lower() == "zone"]


def _set_copy(words, new):
    it = iter(new)

    def sub(m):
        if m.group(1).split("|")[1].strip().lower() == "zone":
            return m.group(0)
        v = next(it, None)
        return m.group(0) if v is None else f"{m.group(1)} {v} {m.group(3)}"
    return COPY_ROW.sub(sub, words)


DIAL_ROW = re.compile(r"^\s*-\s*`?([a-z_]+)`?\s*:\s*(?:(-?\d)\s*(?:→|->)\s*)?(-?\d)\s*\(([^)]*)\)\s*:\s*(.+)$", re.M)
INGREDIENTS = (("scene", "THE SCENE"), ("subject", "THE SUBJECT"), ("details", "THE DETAILS"), ("place_light", "THE PLACE AND LIGHT"),
               ("photo_style", "THE PHOTO STYLE"), ("colours", "THE COLOURS"), ("camera", "THE CAMERA"))
KEEP = {"face": "the face", "label": "the product label", "background": "the background"}


def controls():
    """components/creative-controls controls.json (the dials, presets, emotions, techniques and guards)."""
    return json.loads((COMP / "creative-controls" / "controls.json").read_text())


def brief_dials(t):
    """The brand step's own dial lines (THE DIALS): {dial: {"level", "name", "line"}}, the words it wrote for each."""
    block = t.split("**THE DIALS:**", 1)[-1].split("\n\n**", 1)[0] if "**THE DIALS:**" in t else ""
    return {m.group(1): {"level": int(m.group(3)), "name": m.group(4).strip(), "line": m.group(5).strip()} for m in DIAL_ROW.finditer(block)}


def _zone_where(words):
    return [m.group(1).split("|")[2].strip() for m in COPY_ROW.finditer(words or "") if m.group(1).split("|")[1].strip().lower() != "zone"]


PICTURE_DIALS = HERE / "picture-dials.json"


def picture_dials():
    return json.loads(PICTURE_DIALS.read_text())


def dial_send(dial_id):
    """'picture', 'writing' or 'film': how a dial reaches a still picture (PSH-10 (dials as picture words))."""
    return (picture_dials()["dials"].get(dial_id) or {}).get("send", "writing")


def dial_words(dial_id, level, own=None):
    """The ONE picture instruction a visual dial sends: the brand step's own line for this picture when it wrote one at
    this level, else the picture phrase for the level. A writing or film dial sends nothing."""
    own = own or {}
    if dial_send(dial_id) != "picture":
        return ""
    if dial_id in own and own[dial_id]["level"] == level:
        t_ = clean_md(own[dial_id]["line"]).strip().rstrip(".")
        return t_[:1].upper() + t_[1:] + "."
    return (picture_dials()["dials"][dial_id].get("levels") or {}).get(str(level), "")


def picture_extras(brief, t, own, pic):
    """The lines a person adds on the bench, each labelled, appended to THE PICTURE: ingredients, dials, emotions,
    techniques, people, keep-exactly and do-not lines. Nothing here is sent unless a person set it."""
    out = []
    if brief.get("send_stays"):
        # the rows a person kept on the board win over the teardown's own STAYS block (the board's rows are the swap list)
        ms = (brief.get("swap_list") or {}).get("stays") if isinstance(brief.get("swap_list"), dict) else None
        out.append("WHAT STAYS: " + ("; ".join(str(x).rstrip(".") for x in ms) + "." if ms else clean_swaps(pic.labelled(t, "STAYS"))))
    ing = brief.get("ingredients") or {}
    out += [f"{lab}: {ing[k].strip()}" for k, lab in INGREDIENTS if str(ing.get(k) or "").strip()]
    out += [x.strip() for x in brief.get("draw_lines") or [] if x.strip()]
    dl = [dial_words(k, int(v), own) for k, v in (brief.get("dials") or {}).items()]
    if any(dl):
        out.append("THE LOOK OF THE PICTURE:\n" + "\n".join("- " + x for x in dl if x))
    c = controls()
    em = [e for e in c["emotions"] if e["id"] in (brief.get("emotions") or [])]
    if em:
        out.append("THE FEELING: " + " ".join(f"{e['name']}: {(e.get('image') or e['what']).rstrip('.')}." for e in em))
    # techniques are how the ad was written; the swaps already draw them, so their names are not sent (PSH-10)
    out += ["THE PEOPLE, ALSO: " + x.strip() for x in brief.get("people_lines") or [] if x.strip()]
    keep = [KEEP[k] for k in brief.get("keep") or [] if k in KEEP]
    if keep:
        out.append("KEEP EXACTLY AS IN IMAGE 1: " + ", ".join(keep) + ".")
    out += ["DO NOT: " + x.strip() for x in brief.get("do_not") or [] if x.strip()]
    return out


# What the model is sent is only what to draw: the brief's working notes, markdown, the source's old words, counts and
# self-checks stay in the run record for people (the GPT Image rulebook: notes and reasoning in a prompt are read as
# picture content). PSH-9 (draw-only prompt).
REASONING = re.compile(r"\bit rhymes\b|rhymes because|why it rhymes|characters \(source|source copy|nothing to fill|nothing cut|"
                       r"no run of three|self-check|\bthe source measure", re.I)


def clean_md(t):
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", str(t or ""))
    t = t.replace("**", "").replace("`", "")
    t = re.sub(r"\bthe source's\b", "IMAGE 1's", t, flags=re.I)
    who = r"(woman|man|person|girl|guy|lady|model|creator|subject|picture|image|photo|post|ad|frame|layout|shot|swipe|caption|scene)"
    t = re.sub(r"\b[Tt]he source " + who + r"'s\b", "IMAGE 1's", t)
    t = re.sub(r"\b[Tt]he source " + who + r"\b", r"the \1 in IMAGE 1", t)
    return t


def swaps_block(t):
    """The whole SWAPS block of the brand step (every bullet), not only its first line."""
    # stops at the next bold label, a numbered section (**1. THE INJECTED FRAME**), a heading or a rule
    m = re.search(r"\*\*SWAPS:\*\*(.*?)(?=\n\s*(?:[-*]\s+)?\*\*(?:[A-Z][A-Z ']+:|\d+\.)|\n\s*(?:[-*]\s+)?THE [A-Z ']+:|\n\s*#|\n---|\Z)", t, re.S)
    return m.group(1).strip() if m else ""


def clean_swaps(swaps):
    """Each swap as plain drawing instructions: the 'Why it rhymes' explanations and reasoning sentences dropped."""
    out = []
    for line in str(swaps or "").splitlines():
        line = re.sub(r"\*\*Why it [^*]*\*\*.*$", "", line.strip(), flags=re.I)
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"\s*\([^()]*\b(?:ruled|ruling|rhym\w*|because|see conflicts|source)\b[^()]*\)", "", line, flags=re.I)
        line = re.sub(r",?\s*(?:a |the )?(?:perfect |near |visual )?rhyme\b[^.;]*", "", line, flags=re.I)
        keep = [x for x in re.split(r"(?<=[.!?])\s+", clean_md(line)) if x.strip() and not REASONING.search(x)]
        if keep:
            out.append(" ".join(keep))
    return "\n".join(out)


def plain_words(copy):
    """One zone's words as they read on the picture: no backticks or quotes, each ' / ' a line break."""
    return "\n".join(x.strip() for x in str(copy or "").replace("`", "").strip().strip('"').split(" / ") if x.strip())


def clean_words(words):
    """The words on the picture as one clean instruction per zone: the exact words in quotes, line by line, where they
    sit and in what type; the source's old words, counts and notes left out."""
    out = []
    for m in COPY_ROW.finditer(words or ""):
        cells = [c.strip() for c in m.group(0).strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() == "zone" or set(cells[0]) <= set(":- "):
            continue
        zone = re.sub(r"^Zone\s+\w+\s*[—-]\s*", "", cells[0]).strip()
        ours = cells[-1].replace("`", "").strip().strip('"')
        if not ours or ours.lower() in ("none", "—", "-", "n/a"):
            continue
        lines = [x.strip() for x in ours.split(" / ") if x.strip()]
        say = " then, on the next line, ".join(f'"{x}"' for x in lines)
        where = re.sub(r"\s*\d+ lines?,?\s*", " ", re.sub(r",?\s*measure \d+\.?", "", clean_md(cells[1]))).strip().rstrip(".")
        where = re.sub(r"[\s,;]+$", "", where)
        out.append(f"{zone[:1].upper() + zone[1:]}: write exactly {say}. It sits {where}.")
    return ("\n".join(out) + "\nNothing else is written anywhere in the picture.") if out else ""


# ------------------------------------------------------------- the swap list: what goes in is worked out from it

SWAP_KINDS = ("cast", "product", "library", "drawn", "words")
NEEDS_PICTURE = ("cast", "library")
ON_TOP_LINE = re.compile(r"^\W*(?:the |our |a )?(?:caption|headline|words?|text|copy|title)\b", re.I)


def swap_list(run, file=None):
    """The teardown's swap list for a run (out/swaps.json): whether the product is in the frame and which sides show, what
    stays, every swap with its kind and the real picture it needs, and whether the words are set on top. None when the run
    has none yet: the sheet shows it missing and nothing is guessed."""
    p = Path(file) if file else Path(run) / "out" / "swaps.json"     # `file`: a sample list, for a test or a what-if
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text())
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def swap_key(sw):
    """What makes two swap lists the same for the picture: each row's from, to and kind, the product answer, the stays."""
    if not sw:
        return None
    return (json.dumps([[x.get("from"), x.get("to"), x.get("kind"), x.get("ref")] for x in sw.get("swaps") or []]),
            bool(sw.get("product_in_frame")), json.dumps(sw.get("stays") or []), sw.get("words"))


def matrix_list(m, base):
    """A person's matrix laid over the teardown's swap list: their rows, stays, product answer and words, every other key
    (evidence, product kit, sides) kept from the teardown's list."""
    out = dict(base or {})
    for k in ("swaps", "stays", "product_in_frame", "product_where", "product_sides", "words"):
        if k in m:
            out[k] = m[k]
    out["swaps"] = [{"from": str(x.get("from") or "").strip(), "to": str(x.get("to") or "").strip(),
                     "kind": x.get("kind") if x.get("kind") in SWAP_KINDS else "drawn", "ref": x.get("ref")}
                    for x in out.get("swaps") or [] if str(x.get("to") or "").strip()]
    out["source"] = "matrix"
    return out


LOWER_FIRST = {"A", "An", "The", "One", "Two", "Three", "Four", "Five", "Six", "Our", "Its", "His", "Her", "Their", "Some"}


def matrix_text(sw, kept_back=()):
    """The swap words rebuilt from the matrix, one line per swap: what is in IMAGE 1 and what it becomes. Words set on top
    are not drawn, so their row sends nothing; a swap the person turned back to 'keep' is said as a keep."""
    out = []
    for x in (sw or {}).get("swaps") or []:
        if x["kind"] == "words" and sw.get("words") == "set_on_top":
            continue
        frm = x["from"].rstrip(".") or "This part of IMAGE 1"
        to = x["to"].rstrip(".")
        if to.split(" ", 1)[0] in LOWER_FIRST:                 # "becomes three raised spots", but "becomes Grandma Yai"
            to = to[:1].lower() + to[1:]
        if x["kind"] == "library" and x.get("own_light"):       # the room printed from 3D brings its own light (2026-10-28)
            to = to + ", in IMAGE 1's grain and phone-photo quality"
        elif x["kind"] == "library" and any(y.get("own_light") for y in (sw or {}).get("swaps") or []):
            to = to + ", lit by the room picture's own light, in IMAGE 1's grain and phone-photo quality"
        elif x["kind"] == "library":                            # a swapped-in element takes IMAGE 1's light and quality (2026-10-27)
            to = to + ", lit, framed and photographed exactly as IMAGE 1 is, in its light, grain and quality"
        out.append(f"{frm[:1].upper() + frm[1:]} in IMAGE 1 becomes {to}.")
    out += [f"Keep {str(k).rstrip('.')[:1].lower() + str(k).rstrip('.')[1:]} exactly as in IMAGE 1." for k in kept_back]
    return "\n".join(out)


def swipe_reads(run):
    """What the teardown read off the swipe: its 29 dial levels (out/controls-swipe.json) and its element labels
    (out/elements.json: format, style, framework, awareness). Empty when the run has none."""
    out = {}
    for name, key in (("controls-swipe.json", "dials"), ("elements.json", "labels")):
        p = Path(run) / "out" / name
        try:
            d = json.loads(p.read_text()) if p.is_file() else {}
        except ValueError:
            d = {}
        v = d.get(key) or {}
        out[key] = {k: (x.get("level") if isinstance(x, dict) else x) for k, x in v.items()} if key == "dials" else v
    return out


def _side(view):
    w = str(view or "").lower()
    return next((x for x in ("three-quarter", "front", "back", "side", "top", "bottom") if x in w), w)


USE_WORDS = re.compile(r"\b(hand|hands|hold|holds|held|holding|grip|gripping|palm|fingers|pressed|pressing|presses|in use|"
                       r"using|uses|against (?:his|her|the) |on (?:his|her|the) (?:skin|face|cheek|jaw|jawline|neck|nape|head|"
                       r"scalp|chin|forehead))", re.I)


def in_use(sw):
    """The swap list puts the product in a hand or on skin (its product_where), not resting or shown on its own."""
    return bool(sw and sw.get("product_in_frame") and USE_WORDS.search(str(sw.get("product_where") or "")))


def _in_use_refs(prefs):
    """The product's in-use pictures (its kit's in_use.refs), as the paths plain.product returned them."""
    for p, _ in prefs:
        kit = next((d for d in Path(p).parents if (d / "kit.json").is_file()), None)
        if kit:
            try:
                return {kit / r for r in (json.loads((kit / "kit.json").read_text()).get("in_use") or {}).get("refs") or []}
            except ValueError:
                return set()
    return set()


def _wants_side(view, sides):
    if not sides:
        return True
    want = {_side(x) for x in sides} | {str(x).lower() for x in sides}
    return _side(view) in want or any(str(x).lower() in str(view).lower() for x in sides)


def cast_photo(brand, ref):
    """The cast member's FACE reference: her plain headshot (sheets/headshot.jpg) when she has one, else her master photo.
    2026-10-27, on a cast photo whose turban and sunglasses came into the picture: "this is what the character
    sheet had, which is fine, but we didn't properly leverage it" (V49 (one face reference)): a styled look photo hides
    the face it is meant to give."""
    d = REPO / "runs" / "ai-elements" / brand / "casting" / str(ref)
    return d / "sheets" / "headshot.jpg" if (d / "sheets" / "headshot.jpg").is_file() else d / "master.jpg"


def cast_skin(brand, ref):
    """The cast member's skin up close (sheets/skin-closeup.*), only for a person whose headshot is not yet at macro detail.
    Since 2026-10-28 the headshot IS the real macro-detail face, one reference only, so a
    rebuilt person has no separate close-up and this returns None. Lessons L-39."""
    d = REPO / "runs" / "ai-elements" / brand / "casting" / str(ref) / "sheets"
    return next((d / f"skin-closeup{e}" for e in (".jpg", ".png") if (d / f"skin-closeup{e}").is_file()), None)


def cast_sheet(brand, ref):
    """The cast member's reference sheet, when there is one and the picture model takes its file type. Her BASELINE
    angles-and-expressions sheet first (2026-10-27: the person goes in from the cast baseline, never the master;
    a face drifted with the master sheet in); the old master sheet only when she has no baseline sheet."""
    base = REPO / "runs" / "ai-elements" / brand / "casting" / str(ref) / "sheets" / "angles-expressions.jpg"
    if base.is_file():
        return base
    p = REPO / "runs" / "ai-elements" / brand / "casting" / str(ref) / "reference" / "master-sheet.webp"
    try:
        ok = p.suffix.lstrip(".").lower() in IR.limits(IR.model_of("pictures.generate")).get("image_formats", [])
    except Exception:                                      # noqa: BLE001  no rulebook: the sheet stays out
        ok = False
    return p if ok and p.is_file() else None


def library_photo(ref):
    """A library swap's photo: the file, or the first picture in its folder (as the teardown's swaps.py reads it). A
    picture of a cast member's outfit or body goes in headless (see `headless`)."""
    p = Path(str(ref or ""))
    p = p if p.is_absolute() else REPO / p
    if p.is_dir():
        p = next(iter(sorted(p.glob("*.jp*g")) + sorted(p.glob("*.png"))), p)
    if p.is_file() and "/casting/" in str(p) and "/worlds/" not in str(p) and not re.search(r"headshot|angles-expressions|details|headless|^outfit-|closeup", p.name):
        try:
            return headless(p)
        except Exception:                                  # noqa: BLE001  no face finder here: the photo goes as it is
            return p
    return p


# THE HEADSHOT IS THE ONLY FACE (2026-10-27). Any
# picture of a cast member that is not her face reference — an outfit, a look, a full body — goes in with every face on
# it blanked to the picture's own background, so it gives clothes, build and pose only, never a second face. Made once,
# kept beside the original as <name>-headless.jpg. Lessons L-35.
def headless(pic):
    pic = Path(pic)
    out = pic.with_name(pic.stem + "-headless.jpg")
    if out.is_file() and out.stat().st_mtime >= pic.stat().st_mtime:
        return out
    from PIL import Image, ImageDraw
    G = _load("video-production/machine/swipe_guide.py")
    img = Image.open(pic).convert("RGB")
    probe = pic if pic.suffix.lower() in (".jpg", ".jpeg") else out.with_suffix(".probe.jpg")
    if probe != pic:
        img.save(probe, quality=92)
    found = [r for r in (G.found(probe) or []) if r[0] == "face"]
    if probe != pic:
        probe.unlink()
    W, H = img.size
    bg = img.getpixel((5, 5))
    d = ImageDraw.Draw(img)
    for _k, x, y, w, h in found:
        # the whole head: the face box grown out to the hair and ears, up past the crown, down to the chin
        d.ellipse([(x - 0.35 * w) * W, (y - 0.75 * h) * H, (x + 1.35 * w) * W, (y + 1.15 * h) * H], fill=bg)
    img.save(out, quality=92)
    return out


def swap_rows(brand, sw):
    """One row per swap: from, becomes, kind, the picture it needs (or why none) and whether that picture is on file."""
    rows = []
    for i, x in enumerate((sw or {}).get("swaps") or []):
        k = x.get("kind")
        row = {"i": i, "from": x.get("from") or "", "to": x.get("to") or "", "kind": k, "ref": x.get("ref"), "key": None,
               "needs": "", "path": None, "exists": None}
        if k == "cast":
            p = cast_photo(brand, x.get("ref"))
            row.update(key=f"cast:{x.get('ref')}", needs=f"{row['to'].split(',')[0].strip()}'s cast photo", path=str(p), exists=p.is_file())
        elif k == "library":
            p = library_photo(x.get("ref"))
            row.update(key=f"library:{i}", needs=f"the library photo of {row['to']}", path=str(p), exists=bool(x.get("ref")) and p.is_file())
        elif k == "product":
            row["needs"] = "the product photos" if sw.get("product_in_frame") else "none: the product is not in this frame"
        elif k == "words":
            row["needs"] = "none: set on top after" if sw.get("words") == "set_on_top" else "none: drawn in the picture"
        elif k == "drawn":
            row["needs"] = "none: drawn from words"
        else:
            row["needs"] = f"unknown kind {k!r}"
        rows.append(row)
    return rows


def product_answer(sw):
    """'yes: <where>' or 'no: <the brief's reason>' (never blank when there is a swap list)."""
    if not sw or sw.get("product_in_frame") is None:
        return ""
    if sw["product_in_frame"]:
        sides = ", ".join(sw.get("product_sides") or [])
        return "yes: " + "; ".join(x for x in (sw.get("product_where") or "", ("sides shown: " + sides) if sides else "") if x)
    why = str((sw.get("evidence") or {}).get("product") or sw.get("product_where") or "").replace("`", "").strip()
    why = re.split(r"\s+-\s+", why)[-1].strip() if " - " in why else why       # the brief's own sentence, not the excerpt before it
    why = why.lstrip("-•* ").strip()
    if not why and str(sw.get("source") or "") not in ("backfill", "teardown"):
        why = str(sw.get("source")).strip()
    return "no: " + why


EDIT_NO_WORDS = ("NO WORDS ADDED: IMAGE 1 carries no caption; add no caption, headline or overlay text (the words are "
                 "set on afterwards). Every object in IMAGE 1 that carries lettering (a tag, a label, a pouch, a pendant) "
                 "stays in the picture with its lettering, exactly as IMAGE 1 shows it.")


SAFE_TOP = (16 / 9 - 5 / 4) / 2 / (16 / 9) * 100          # the centre 4:5 of a 9:16 frame starts 14.8% down
SAFE_SPAN = 100 - 2 * SAFE_TOP                             # and is 70.3% of its height


def into_safe_zone(layer, run):
    """THE WORDS IN THE SAFE ZONE (2026-10-28). Every picture is 9:16 with the centre 4:5 as the safe zone; the picture step held to it
    but the words were set at the swipe's own positions, so a square swipe's headline landed 5% from the top. A swipe
    that is not 9:16 has its whole frame mapped into the safe zone (tops, heights, gutters, marks, keep-clear boxes, the
    top and bottom margins); a 9:16 swipe's elements are moved inside it where they fall outside."""
    src = next((p for p in (Path(run) / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")), None)
    try:
        from PIL import Image
        w, h = Image.open(src).size if src else (9, 16)
    except Exception:                                      # noqa: BLE001  an unreadable swipe is treated as 9:16
        w, h = 9, 16
    tall = w / h < 0.6
    # every line gets its own height from the swipe's zone table ("| Zone C | ... | Top: 54% ..."), never only "below the
    # line above": with the line above emptied, the rest slid to the top of the picture, outside the safe zone (2026-10-28)
    spec = next((f for f in (Path(run) / "out" / "02-replication-spec.md", Path(run) / "02-replication-spec.md") if f.is_file()), None)
    tops = {m.group(1).lower(): float(m.group(2)) for m in
            re.finditer(r"\|\s*Zone\s+([A-Z])\s*\|[^|\n]*\|[^|\n]*?Top:\s*([\d.]+)%", spec.read_text())} if spec else {}
    for el in layer.get("elements") or []:
        k = re.match(r"(?i)zone_([a-z])$", str(el.get("element") or ""))
        if el.get("top_pct") is None and k and k.group(1).lower() in tops:
            el["top_pct"] = tops[k.group(1).lower()]
    y = lambda v: None if v is None else round(SAFE_TOP + float(v) * SAFE_SPAN / 100, 2)
    d = lambda v: None if v is None else round(float(v) * SAFE_SPAN / 100, 2)
    lay = layer.setdefault("layout", {}) if isinstance(layer.get("layout"), dict) or "layout" not in layer else layer["layout"]
    for el in layer.get("elements") or []:
        if not tall:
            for k, f in (("top_pct", y), ("height_pct", d), ("gutter_pct", d), ("cap_pct", d)):
                if isinstance(el.get(k), (int, float)):
                    el[k] = f(el[k])
        elif isinstance(el.get("top_pct"), (int, float)):
            hp = float(el.get("height_pct") or 0)
            el["top_pct"] = round(min(max(float(el["top_pct"]), SAFE_TOP), 100 - SAFE_TOP - hp), 2)
    if not tall and isinstance(lay, dict):
        for m in lay.get("marks") or []:
            if isinstance(m.get("top_pct"), (int, float)):
                m["top_pct"] = y(m["top_pct"])
        for k in lay.get("keep_clear") or []:
            for side in ("top", "bottom"):
                if isinstance(k.get(side), (int, float)):
                    k[side] = y(k[side])
        mg = lay.get("margins") or {}
        for side in ("top", "bottom"):
            if isinstance(mg.get(side), (int, float)):
                mg[side] = round(SAFE_TOP + float(mg[side]) * SAFE_SPAN / 100, 2)
    return layer


def type_layer(run, brief, words):
    """The brief's own type layer (the teardown's swaps.py words_layer), set over the finished picture by plain.generate
    when the words are set on top. Each element carries OUR words (the brand step's 'Our copy', or a person's edit), zone
    by zone in order: the words the Bench shows are the words set on the picture."""
    # the swaps record's reader moved to image-writing with the brief's writing (2026-10-27); the old home still reads
    rel = next((r for r in ("image-writing/tools/swaps.py", "image-teardown/tools/swaps.py") if (COMP / r).is_file()), None)
    if not rel:
        # words set on top with no way to read them is an input that is missing, never a picture shipped without words
        # (three variations went out wordless on 2026-10-27 when this file moved mid-run and this returned None)
        raise ValueError("the words are set on top, but the brief's type layer cannot be read: no swaps.py in "
                         "image-writing/tools or image-teardown/tools")
    layer = _load(rel).words_layer(run)
    if not layer:
        return None
    layer = into_safe_zone(json.loads(json.dumps(layer)), run)
    kept = set_print(brief.get("brand"), brief.get("run"))
    design = json.loads((kept.parent / "set.json").read_text()).get("design") if kept else None
    if design:                                               # the set's designed layout replaces the stamped type
        layer["design"] = design
    rows = _our_copy(words)
    if rows:
        # by zone letter (element "zone_d" takes the "Zone D" row); a zone with no words of its own, such as a picture
        # field, would otherwise push every later line one place down (2026-10-28: the price landed in no zone)
        by = {}
        for z, c in rows:
            m = re.match(r"(?i)(?:zone\s+)?([a-z])\b", z)
            if m:
                by[m.group(1).lower()] = c
        els = layer.get("elements") or []
        keyed = [re.match(r"(?i)zone_([a-z])$", str(el.get("element") or "")) for el in els]
        # a zone a person emptied has no row left: it stays empty in its own place, never pulling the next words up into
        # it (2026-10-28: emptying the top line put SALE at the very top, outside the safe zone)
        pairs = ([(el, by.get(k.group(1).lower(), "")) for el, k in zip(els, keyed)]
                 if by and all(keyed)
                 else list(zip(els, [c for _, c in rows])))
        bullets = _bulleted_zones(run)
        extra = []
        for el, txt in pairs:
            el["text"] = set_words(txt)
            # the swipe's coloured pieces of a line ("$118 ", "-> ", "$39") are ITS words: ours replace them, or the
            # compositor sets the swipe's old price (2026-10-28, a Black Friday ad came out "$118 -> $39")
            el.pop("segments", None)
            # an arrow at the end of our words is the swipe's mark: drawn by the setter's mark font, never as a
            # character the type's own font may not have (2026-10-28: the offer bar's arrow disappeared)
            m_arrow = re.search(r"\s*([\u2192\u2794\u279C\u27A1]|->)\s*$", el["text"])
            if m_arrow and not el.get("mark"):
                el["text"] = el["text"][:m_arrow.start()]
                el["mark"] = {"glyph": "\u2794", "color": el.get("color") or "#FFFFFF"}
            tn = type_notes(txt)
            if tn.get("color"):
                el["color"] = tn["color"]
                if el.get("mark"):
                    el["mark"]["color"] = tn["color"]
            if tn.get("bar"):
                el["box"] = {**(el.get("box") or {}), "fill": tn["bar"], "pad_pct": max(1.0, float((el.get("box") or {}).get("pad_pct") or 0)),
                             "radius_pct": float((el.get("box") or {}).get("radius_pct") or 0.3)}
            for w, c in tn.get("accent") or []:
                t = el["text"]
                i = t.find(w)
                if i >= 0:                                   # our accent word in its own colour, the swipe's way
                    el["segments"] = [x for x in ({"text": t[:i], "color": el.get("color")}, {"text": w, "color": c},
                                                  {"text": t[i + len(w):], "color": el.get("color")}) if x["text"]]
            if el.get("segments") and "\n" in el["text"]:
                # the setter draws a two-colour piece as ONE line: the lines above the accent line become their own
                # block on top of it, same type, the accent line keeps its colours (2026-10-28: a two-line headline
                # lost its first line, cut off at the top)
                lines = el["text"].split("\n")
                at = next(n for n, l in enumerate(lines) if any(w in l for w, _ in tn["accent"]))
                if at > 0:
                    n = len(lines)
                    hgt = float(el.get("height_pct") or 0) or float(el.get("cap_pct") or 3) * 1.4 * n
                    lead = {**json.loads(json.dumps(el)), "element": str(el["element"]) + "_lead",
                            "text": "\n".join(lines[:at]), "max_lines": at, "height_pct": round(hgt * at / n, 2)}
                    lead.pop("segments", None)
                    rest = "\n".join(lines[at:])
                    w, c = next((w, c) for w, c in tn["accent"] if w in rest)
                    j = rest.find(w)
                    el["segments"] = [x for x in ({"text": rest[:j], "color": el.get("color")}, {"text": w, "color": c},
                                                  {"text": rest[j + len(w):], "color": el.get("color")}) if x["text"]]
                    el["text"] = rest
                    if isinstance(el.get("top_pct"), (int, float)):
                        el["top_pct"] = round(float(el["top_pct"]) + hgt * at / n, 2)
                    el["height_pct"] = round(hgt * (n - at) / n, 2)
                    el["max_lines"] = n - at
                    extra.append((el, lead))
            k = re.match(r"(?i)zone_([a-z])$", str(el.get("element") or ""))
            if k and k.group(1).lower() in bullets and el.get("text"):
                # the swipe's list has bullets: one at each item, a line that starts lower-case carries the item before
                # and the swipe's spacing: a clear gap between items, none inside one (2026-10-28). The bullet hangs left of the text; every line of an item starts on one axis.
                items = []
                for l in el["text"].split("\n"):
                    if l[:1].isupper() or l[:1].isdigit() or not items:
                        items.append([l])
                    else:
                        items[-1].append(l)
                el["text"] = "\n\n".join("\n".join(it) for it in items)
                starts, n = [], 0
                for it in items:
                    starts.append(n)
                    n += len(it) + 1
                el["bullet"] = {"glyph": "\u2022", "lines": starts, "of": el["text"].count("\n") + 1}
                el["max_lines"] = el["text"].count("\n") + 1
            # the emoji stays on the ad: the compositor draws it in colour after the last line (2026-10-28: dropped)
            el["emoji"] = "".join(EMOJI.findall(str(txt))).replace("\uFE0F", "") or el.get("emoji") or ""
        for el, lead in extra:                               # each lead block goes in just before its accent line
            els.insert(els.index(el), lead)
    italic = _italic_zones(run)
    for el in layer.get("elements") or []:
        k = re.match(r"(?i)zone_([a-z])", str(el.get("element") or ""))
        if k and k.group(1).lower() in italic:
            el["italic"] = True                               # the swipe's italic is the swipe's look (2026-10-28)
    for c in layer.get("composited") or []:
        # the swipe's torn white paper behind a line of words (2026-10-28: dropped, the words floated on the picture):
        # it follows the words it carries, so it stays with them when they move into the safe zone
        if re.search(r"(?i)\bpaper\b", str(c.get("note") or "")):
            # the words it carries: the block nearest below its top (the safe zone may have moved them up a little)
            under = [e for e in layer.get("elements") or [] if isinstance(e.get("top_pct"), (int, float))
                     and float(e["top_pct"]) >= float(c.get("top_pct") or 0) - 12]
            if under:
                e = min(under, key=lambda e: abs(float(e["top_pct"]) - float(c.get("top_pct") or 0) - 5))
                left = float(c.get("left_pct") or 5)
                e["paper"] = {"left_pct": left, "right_pct": left + float(c.get("span_pct") or 90),
                              "rotate_deg": float(c.get("rotate_deg") or 0),
                              "above_pct": 3.0,
                              "below_pct": 4.0, "fill": "#FFFFFF"}
    return layer


EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def _italic_zones(run):
    """The zones the swipe's teardown sets in italic (its zone table's Type & Treatment column says "italic")."""
    rec = next((f for f in (Path(run) / "out" / "01-teardown.md", Path(run) / "01-teardown.md") if f.is_file()), None)
    out = set()
    for line in (rec.read_text().splitlines() if rec else []):
        m = re.match(r"\s*\|\s*Zone\s+([A-Z])\b", line)
        if m and re.search(r"(?i)\bitalic", line.split("|")[-2] if line.count("|") > 2 else line):
            out.add(m.group(1).lower())
    return out


def _bulleted_zones(run):
    """The swipe's zones its read calls a bulleted list ("ELEMENT ... (Zone B)" then a MANDATE naming bullets)."""
    spec = next((f for f in (Path(run) / "out" / "02-replication-spec.md", Path(run) / "02-replication-spec.md") if f.is_file()), None)
    out, zone = set(), None
    for line in (spec.read_text().splitlines() if spec else []):
        m = re.search(r"\(Zone\s+([A-Z])\)", line)
        if m and "ELEMENT" in line:
            zone = m.group(1).lower()
        elif zone and "MANDATE" in line and re.search(r"(?i)\bbullet", line):
            out.add(zone)
    return out


LESSONS = HERE / "lessons.json"


def lessons(medium=None):
    """What the chain has learned from reviews, as rules for any ad (lessons.json): [{id, said, rule, status}]."""
    try:
        rows = json.loads(LESSONS.read_text())["lessons"]
    except (OSError, ValueError, KeyError):
        return []
    return [{k: x[k] for k in ("id", "said", "rule", "status", "source")} for x in rows
            if x.get("status") != "deprecated" and (medium is None or x.get("medium") == medium)]


def swipe_bars(src):
    """(top %, bottom %) of the solid black bars the swipe was posted with, (0, 0) when it has none. the owner, 2026-10-27,
    on a remake without them: "First and foremost, you're missing the black box at the top and bottom." """
    try:
        from PIL import Image, ImageStat
        im = Image.open(src).convert("L")
    except Exception:  # noqa: BLE001
        return 0.0, 0.0
    w, h = im.size
    dark = lambda y: (lambda s: s.mean[0] < 18 and s.stddev[0] < 12)(ImageStat.Stat(im.crop((0, y, w, y + 1))))
    top = 0
    while top < h // 3 and dark(top):
        top += 1
    bot = 0
    while bot < h // 3 and dark(h - 1 - bot):
        bot += 1
    # under 2% is a dark edge, not a bar; a bar never reaches past the frame's 15% bleed into the safe middle
    pct = lambda n: min(15.0, round(n / h * 100, 1)) if n / h >= 0.02 else 0.0
    return pct(top), pct(bot)


def put_bars(picture, top, bottom):
    """Paint the swipe's black bars onto a made picture, in place (the safe middle never reaches them)."""
    from PIL import Image, ImageDraw
    im = Image.open(picture).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    if top:
        d.rectangle([0, 0, w, round(h * top / 100) - 1], fill=(0, 0, 0))
    if bottom:
        d.rectangle([0, h - round(h * bottom / 100), w, h], fill=(0, 0, 0))
    im.save(picture)
    return picture


def set_words(cell):
    """The words of an 'Our copy' cell as they go on the picture. Only the quoted words when the cell quotes them (a
    writer's note beside them, "(white fill, black outline ...)", is about the type, never type itself: it went onto a
    picture as words on 2026-10-27); " / " is a line break; an emoji the caption font cannot draw is left out, and a
    line that was only an emoji goes with it."""
    s = cell.replace("`", "").replace("**", "").strip()
    # the writer's note in brackets at the end is about the type, never words: dropped BEFORE the quotes are read, or a
    # word the note names ("Gold on \"BUMPING UP\"") was set twice (2026-10-28)
    s = re.sub(r"\s*\([^()]*\)\s*$", "", s)
    lines = []
    # " / " outside the quotes splits lines; inside one quoted string it is a line break too
    for group in re.split(r' / (?=(?:[^"\u201c\u201d]*["\u201c\u201d][^"\u201c\u201d]*["\u201c\u201d])*[^"\u201c\u201d]*$)', s):
        quoted = re.findall(r'["\u201c]([^"\u201d]+)["\u201d]', group)
        # quoted pieces joined with "+" are one line in two colours: one line, never two
        lines += ("".join(quoted) if quoted else group).split(" / ")
    lines = [EMOJI.sub("", l).strip() for l in lines]
    return "\n".join(l for l in lines if l)


HEX6 = r"#[0-9A-Fa-f]{6}"


def num_or(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def type_notes(cell):
    """What the writer's note on an 'Our copy' cell says about the type (2026-10-28, the swipe read had missed the accent
    word and the offer bar): {"accent": [(words, colour)], "color": the type's colour, "bar": the bar's fill}."""
    note = " ".join(re.findall(r"\(([^()]*)\)", cell or ""))
    got = {"accent": [(w, c) for c, w in re.findall(rf"({HEX6})\s+on\s+[\"\u201c]([^\"\u201d]+)[\"\u201d]", note)]}
    m = re.search(rf"({HEX6})\)?\s+type\s+on\s+an?\s+[^#]*?({HEX6})\)?\s+(?:bar|box|button|pill|block|panel)", note)
    if m:
        got["color"], got["bar"] = m.group(1), m.group(2)
    return got


def build_picture(brief, job="pictures.generate"):
    """The picture the static chain would send for this brief. A person may leave a picture out (`skip`: "swipe",
    "product:<n>"), add one (`added`: [{path, label}]), change the words on the picture (`our_copy`, one per zone),
    the swap text (`swaps`), who is in it (`people`) and whether the product shows (`product`, "" for none)."""
    plain = _image_chain()
    sys.path.insert(0, str(COMP / "image-teardown" / "tools"))
    pic = _load("image-teardown/tools/pictures.py")
    brand, runname = brief["brand"], brief["run"]
    run = _lane_run(brand, runname)
    t = (run / "out" / "03-injection.md").read_text()
    skip = set(brief.get("skip") or [])
    swaps0 = clean_swaps(swaps_block(t) or pic.labelled(t, "SWAPS"))
    words0 = pic.section(t, "1. THE INJECTED FRAME", "2. THE SUBJECT")
    sw_file = Path(brief["swap_file"]) if brief.get("swap_file") else run / "out" / "swaps.json"
    sw0 = swap_list(run, sw_file)
    sw, kept_back = sw0, []
    if isinstance(brief.get("swap_list"), dict):             # the matrix: a person's own swap list, row by row
        sw = matrix_list(brief["swap_list"], sw0)
        kept_back = [x for x in brief["swap_list"].get("kept_back") or [] if str(x).strip()]
    edited = sw is not sw0 and swap_key(sw) != swap_key(sw0)
    if not str(swaps0 or "").strip() and sw0 and sw0.get("swaps"):
        # a brand step written before it carried THE SWAPS line still has its swap list: the line is written from it
        # (2026-10-27)
        swaps0 = matrix_text(sw0, [])
    if sw0 and sw0.get("from_brief"):
        # a video shot's start picture (video-production shot_swaps.py, 2026-10-27): the swaps are the video brief's,
        # and its words are set on top in the edit — the picture chain's own injection never reaches the prompt
        swaps0, words0 = matrix_text(sw0, []), ""
    swaps = brief.get("swaps") if brief.get("swaps") is not None else (matrix_text(sw, kept_back) if edited else swaps0)
    words = brief.get("words") if brief.get("words") is not None else words0
    if brief.get("our_copy") is not None:
        words = _set_copy(words, brief["our_copy"])
    with_ref = brief.get("with_ref", True) and "swipe" not in skip
    words_mode = brief.get("words_mode") or ({"set_on_top": "set on top after", "drawn": "drawn"}.get((sw or {}).get("words")) if sw else None)
    on_top = words_mode == "set on top after"
    # words set on top after: the picture is made with no writing at all; THE WORDS block is left out
    swap_text = clean_swaps(swaps)
    if on_top:                                               # the swap of the words is done on top, not drawn
        swap_text = "\n".join(x for x in swap_text.splitlines() if not ON_TOP_LINE.search(x))
    text, refs = pic.picture_inputs(run, swap_text, "" if on_top else clean_words(words), with_ref, brief.get("note") or None)
    base = Path(brief["base"]) if brief.get("base") else None
    if base is not None and not base.is_absolute():
        base = REPO / base
    if base is not None and with_ref and not base.is_file():
        raise ValueError("The approved base picture is missing: " + str(brief["base"]))
    if base is not None and with_ref and refs:
        refs[0] = base                                    # a variation: IMAGE 1 is the approved picture, not the swipe
        # its no-words rule keeps the objects it already lettered: "no lettering of any kind" with only the one change
        # named made the model delete the K-GLOW pouch in three of five variations (2026-10-27)
        text = text.replace(pic.NO_WORDS, EDIT_NO_WORDS)
    own = brief_dials(t)
    rows = swap_rows(brand, sw) if sw else []
    cast_in = brief.get("people") in (None, "cast") and any(r["kind"] == "cast" and r["exists"] and r["key"] not in skip for r in rows)
    if cast_in:
        # One face per person (2026-10-27: a run's saved likeness photo of another woman went in beside the cast member
        # picked on the board, and the picture took neither face cleanly). With our cast member in, a run's extra piece
        # that is a FACE is left out; any other real piece (a before/after, a product) stays, renumbered.
        xf = run / "vars" / "extra-refs.json"
        xs = [x for x in (json.loads(xf.read_text()) if xf.is_file() else []) if Path(x["path"]).is_file()]
        if any(re.search(r"\bface\b", x.get("role", ""), re.I) for x in xs):
            keep = [x for x in xs if not re.search(r"\bface\b", x.get("role", ""), re.I)]
            text = text.split("\n\nTHE REAL PIECES: ")[0]
            refs = refs[:1] if (with_ref and refs) else []
            lines = []
            for x in keep:
                refs.append(Path(x["path"]))
                lines.append(f"IMAGE {len(refs)} is {x['role']}: show it exactly as it is, its own pixels and words, never redrawn.")
            if lines:
                text += "\n\nTHE REAL PIECES: " + " ".join(lines)
    eb = brief
    if cast_in and int((brief.get("dials") or {}).get("cultural_casting", 0)) >= 3:
        # a cast member is our own person: the lookalike-of-a-known-figure line would undo the face kept from the cast photo
        eb = {**brief, "dials": {k: v for k, v in brief["dials"].items() if k != "cultural_casting"}}
    extra = picture_extras(eb, t, own, pic)
    if with_ref:
        # made from a swipe: the light is IMAGE 1's, so a dial line's light words go ("tight jaw, wide eyes; hard light"
        # put hard sun on a soft beauty-filter selfie, 2026-10-27); a valence line, which is only light, stays when set
        extra = [re.sub(r";\s*[^;\n]*\blight\b\.?(?=\n|$)", ".", x) if x.startswith("THE LOOK OF THE PICTURE") else x
                 for x in extra]
    if sw0 and sw0.get("from_brief"):
        # a video shot's mood is its brief's (2026-10-27: the picture chain's own "strong reaction: tight jaw" / "Disgust"
        # turned a flat, matter-of-fact opening into a grimace — "mood is fine ... that's not what the face should be
        # doing"): the generic lines go, the brief's face and feeling for the shot's first moment come in
        extra = [x for x in extra if not x.startswith(("THE LOOK OF THE PICTURE", "THE FEELING"))]
        if sw0.get("notes"):
            # the person's own feedback on this shot (the board's Change it): it outranks anything above
            extra.append("CHANGES ASKED FOR THIS SHOT (they outrank anything above): " + " ".join(
                str(n).rstrip(".") + "." for n in sw0["notes"]))
        lt = sw0.get("light") or {}
        if lt:
            # the shot's light as facts, read off its own 3D scene (2026-10-28, movie-level depth)
            extra.append("THE LIGHT ON THE PERSON (one photograph, the room's own light): " + "; ".join(
                f"{k}: {v}" for k, v in lt.items() if v) + ".")
        # A hook variation supplies its own first-moment direction; the parent
        # shot's old spoken-word gestures must not leak into the new opening.
        fe = brief.get("shot_direction") or sw0.get("feeling") or {}
        if fe.get("face") or fe.get("emotion"):
            extra.append("THE FEELING: " + "; ".join(x for x in (
                (fe.get("emotion") or "").strip(), f"the face: {fe['face']}" if fe.get("face") else "",
                f"the hands: {fe['gesture']}" if fe.get("gesture") else "") if x) + ".")
    if extra:
        text = text + "\n\n" + "\n".join(extra)
    roles = [None] * len(refs)
    says, people_lines, rules_lines = {}, [], []
    lead = None                                          # (subject, possessive) of the first cast member
    swap_choices = []
    for r in rows:                                          # a cast photo per cast swap, a library photo per library swap
        if r["kind"] not in NEEDS_PICTURE:
            continue
        swap_choices.append({"key": r["key"], "label": r["needs"][:1].upper() + r["needs"][1:], "path": r["path"], "for": f"{r['from']} → {r['to']}",
                             "exists": r["exists"], "on": bool(r["exists"]) and r["key"] not in skip})
        if not swap_choices[-1]["on"]:
            continue
        refs.append(Path(r["path"]))
        n = len(refs)
        if r["kind"] == "cast":
            who = r["to"].split(",")[0].strip()                        # "Grandma Yai, Thai grandmother, 72" → "Grandma Yai"
            spot = clean_md(r["from"].split(",")[0].strip()) or "the person"
            spot = spot if "IMAGE 1" in spot else f"{spot[:1].lower() + spot[1:]} in IMAGE 1"
            roles.append(f"{who}, our cast member")
            # the cast member's own pronouns, from their bank (video-production shot_swaps.pronouns): never "her" by default
            sj, _ob, ps = _load("video-production/machine/shot_swaps.py").pronouns(
                REPO / "runs" / "ai-elements" / brand / "casting" / str(r["ref"]), r["to"])
            lead = lead or (sj, ps)
            if brief.get("cast_age") == "swipe":
                # her younger self at the swipe person's age (2026-10-27)
                says[n - 1] = (f"IMAGE {n} is {who}, our cast member: {ps} face, made younger to the age of IMAGE 1's person, "
                               f"{ps} own younger self (the same bone structure, eyes, nose, mouth and skin tone; the problem "
                               f"THE PICTURE shows on {ps} skin kept); {ps} hairstyle, clothes, jewellery and anything on {ps} head are IMAGE 1's person's, "
                               "never this photo's; in the pose, place and light IMAGE 1 shows.")
                people_lines.append(f"The person in IMAGE {n} is {who} as {ps} younger self, at the age of {spot}: plainly the "
                                    f"same person as IMAGE {n}, years younger, the problem on {ps} skin kept. Any real brand name or logo becomes a parody of it, as THE SWAPS say; never the real one.")
            else:
                says[n - 1] = f"IMAGE {n} is {who}, our cast member: use this face exactly ({ps} features, skin, age and hair colour; {ps} hairstyle, clothes, jewellery and anything on {ps} head are IMAGE 1's person's, never this photo's), in the pose, place and light IMAGE 1 shows."
                people_lines.append(f"The person in IMAGE {n} is {r['to']}. Keep {who}'s face exactly: the same features, skin, "
                                    f"age and hair, in the place of {spot}. Any real brand name or logo becomes a parody of it, as THE SWAPS say; never the real one.")
            sh = cast_sheet(brand, r["ref"])
            key = f"cast-sheet:{r['ref']}"
            if sh:
                swap_choices.append({"key": key, "label": f"{who}'s reference sheet", "path": str(sh), "for": f"{r['from']} → {r['to']}",
                                     "exists": True, "on": key not in skip})
                if key not in skip:
                    refs.append(sh)
                    roles.append(f"{who}'s reference sheet")
                    says[len(refs) - 1] = (f"IMAGE {len(refs)} is {who}'s reference sheet: the same person from other angles, "
                                           "only to keep the face right. Do not copy its layout.")
            sk = cast_skin(brand, r["ref"])
            key = f"cast-skin:{r['ref']}"
            if sk:
                swap_choices.append({"key": key, "label": f"{who}'s skin up close", "path": str(sk), "for": f"{r['from']} → {r['to']}",
                                     "exists": True, "on": key not in skip})
                if key not in skip:
                    refs.append(sk)
                    roles.append(f"{who}'s skin up close")
                    says[len(refs) - 1] = (f"IMAGE {len(refs)} is {who}'s skin up close: copy {ps} skin exactly as it is here — its "
                                           f"pores, peach fuzz, fine lines, texture and tone — and the life in {ps} eyes; never smoother. "
                                           "Do not copy its framing or light.")
            real_people = True
        else:
            roles.append(f"the real {r['to']}")
    if locals().get("real_people") and any(r.get("kind") == "library" for r in rows):
        # ONE PHOTOGRAPH, NOT A CUT-OUT (2026-10-28)
        sj, ps = lead or ("they", "their")
        ob = {"she": "her", "he": "him"}.get(sj, "them")
        is_, holds, stands = ("are", "hold", "stand") if sj == "they" else ("is", "holds", "stands")
        rules_lines.append(f"ONE PHOTOGRAPH, ONE MOMENT: the person was really standing in this room when it was taken. {sj.capitalize()} {is_} lit by "
                           f"the room's own light — the same direction, colour and softness as everything around {ob}, the window "
                           f"light wrapping {ps} edges, {ps} front no brighter than the room allows; {ps} skin and clothes take the "
                           f"room's colour. Real contact: soft shadows where {ps} hands, arms and the things {sj} {holds} meet the surface "
                           f"and each other, {ps} shadow falling where the light sends it. Real depth: the camera focused on {ob}, the "
                           f"room behind {ob} softly out of focus the way a phone lens blurs it, light falling off toward the back. "
                           f"Never a cut-out, never pasted in, never sharper or brighter than the photograph {sj} {stands} in.")
    if locals().get("real_people"):
        # REAL HUMANS (2026-10-28)
        rules_lines.append("THE PEOPLE ARE REAL PEOPLE, photographed: unretouched human skin with pores, peach fuzz, fine lines, "
                           "creases with shadow in them and a natural sheen; real eyes with feeling in them, wet lid lines, individual "
                           "lashes and catchlights; stray hairs. Never smoothed, waxy, airbrushed, plastic or AI-glossy.")
    if with_ref:
        # the swipe's photo quality, never a cleaner one (2026-10-27)
        rules_lines.append("THE PHOTO QUALITY is IMAGE 1's exactly: its grain, softness, filter, colour cast and compression. "
                           "Never sharper, cleaner, glossier or more polished than IMAGE 1.")
    # measured on the run's swipe itself, so a variation (IMAGE 1 = the approved picture) gets the same bars as the first
    src0 = next((x for x in (run / "assets").glob("source.*") if x.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    bars = swipe_bars(src0) if (with_ref and src0 and brief.get("bars", True)) else (0.0, 0.0)
    if on_top and "NO WORDS IN THE PICTURE" not in text and "NO WORDS ADDED" not in text:   # picture_inputs may already say it
        rules_lines.append("No writing anywhere in the picture: no captions, labels, signs or letters. Leave the places where "
                           "IMAGE 1 has words clear; the words are set on top afterwards.")
    added = [a for a in brief.get("added") or [] if Path(a.get("path", "")).is_file()]
    for a in added:                                          # an added picture may say its own job (a variation's approved picture)
        if a.get("says"):
            says[len(refs) + added.index(a)] = f"IMAGE {len(refs) + added.index(a) + 1} is {a['says']}"
    roles += [a.get("label") or "a picture the person added" for a in added]
    refs = refs + [Path(a["path"]) for a in added]
    slug = brief.get("product") or brief.get("product_slug") or None
    in_frame = None
    if sw is not None:                                       # the swap list answers whether the product is in the frame
        in_frame = bool(sw.get("product_in_frame")) if brief.get("show_product") is None else bool(brief["show_product"])
        if not in_frame:
            slug = None
    people = brief.get("people") or ("cast" if people_lines else None)
    product_refs, views, got = None, [], None
    if slug:
        got = plain.product(brand, slug)
        if got:
            pname, prefs, _ = got
            views = [(i, p, w) for i, (p, w) in enumerate(prefs)]
            if sw is not None and brief.get("show_product") is None:
                # IN USE (in a hand, on skin): the kit's in-use pictures, its back and a real hand holding it, the
                # recipe of the carousels the owner approved on 2026-10-25 ("1000000x better than any ... implementation we
                # had in the past"); the front photos say "never on skin" and go in only when it is shown on its own.
                # The side filter below dropped the back and the hold photo from every in-use board picture
                # (2026-10-27)
                use = _in_use_refs(prefs)
                sheet = lambda w: str(w).startswith("its product casting sheet")   # every side: kept whatever the use
                if use and in_use(sw):
                    views = [(i, p, w) for i, p, w in views if p in use or sheet(w)]
                else:                                         # only the sides the swap list names
                    views = [(i, p, w) for i, p, w in views if sheet(w) or (p not in use and _wants_side(w, sw.get("product_sides")))] or views
            kept = [p for i, p, _ in views if f"product:{i}" not in skip]
            if len(kept) < len(prefs):
                product_refs = {pname: kept}
    product_lines = None
    if slug and brief.get("product_lines"):
        got = got if slug else None
        if got:
            product_lines = {got[0]: " ".join([got[2]] + [x for x in brief["product_lines"] if x.strip()])}
    if people != "cast":
        people_lines = []
    pl = plain.plan(brand, text, refs, [slug] if slug else [], product_refs=product_refs, product_lines=product_lines,
                    people=people, ref_roles=roles, people_lines=people_lines, rules_lines=rules_lines, ref_says=says)
    # every picture that could go in, ticked or not, for the page's tick boxes
    src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    if base and base.is_file():
        src = base
    choices = ([{"key": "swipe", "label": "The approved picture" if base and base.is_file() else "The ad we copy", "path": str(src), "for": "the layout", "exists": True, "on": "swipe" not in skip}] if src else [])
    choices += swap_choices
    choices += [{"key": f"product:{i}", "label": "Real product, " + (re.sub(r"(?i)^the |\s*view$", "", w or "photo").lower().replace("three-quarter", "angle")),
                 "path": str(p), "for": "the product", "exists": True, "on": f"product:{i}" not in skip} for i, p, w in views]
    choices += [{"key": f"added:{i}", "label": a.get("label") or "Added picture", "path": a["path"], "on": True} for i, a in enumerate(added)]
    return {"prompt": pl["prompt"], "inputs": [{"n": i + 1, "role": r, "path": str(p)} for i, (p, r) in enumerate(zip(pl["refs"], pl["roles"]))],
            "fields": {"swaps": swaps, "words": words, "note": brief.get("note") or "", "product": slug or "", "with_ref": with_ref,
                       "people": people or ("lookalike" if with_ref else "made-up"),
                       "swap_list": sw, "swap_file": str(sw_file), "swap_sample": bool(brief.get("swap_file")), "swap_rows": rows,
                       "swap_list_original": sw0, "swap_edited": edited, "kept_back": kept_back,
                       "swipe_dials": swipe_reads(run).get("dials", {}), "labels": swipe_reads(run).get("labels", {}),
                       "stays_list": list((sw or {}).get("stays") or []), "words_mode": words_mode,
                       "product_in_frame": in_frame, "product_answer": product_answer(sw) if brief.get("show_product") is None
                       else ("yes: turned on by a person" if brief["show_product"] else "no: turned off by a person"),
                       "cast": [r["to"] for r in rows if r["kind"] == "cast"],
                       "our_copy": [c for _, c in _our_copy(words)], "zones": [z for z, _ in _our_copy(words)],
                       "our_copy_original": [c for _, c in _our_copy(words0)], "swaps_original": swaps0,
                       "zones_where": _zone_where(words), "dials_brief": own,
                       "dials_sent": {k: dial_words(k, int(v), own) for k, v in (brief.get("dials") or {}).items()},
                       "words_plain": [set_words(c) for _, c in _our_copy(words)], "stays": pic.labelled(t, "STAYS"),
                       "standout": pic.labelled(t, "THE STANDOUT"),
                       "bars": {"top": bars[0], "bottom": bars[1], "on": brief.get("bars", True)},
                       "cast_age": brief.get("cast_age") or "as-on-file",
                       "lessons": lessons("image")},
            "choices": choices,
            "aspect": "9:16", "notes": [], "medium": "image", "plain": plain,
            # what plain.make takes to send exactly this (the Prompt Bench's Make button)
            "send": {"brand": brand, "text": text, "references": [str(r) for r in refs], "products": [slug] if slug else [],
                     "product_refs": {k: [str(x) for x in v] for k, v in (product_refs or {}).items()} or None,
                     "product_lines": product_lines,
                     "ref_roles": roles, "people": people, "ref_says": says or None,
                     "people_lines": people_lines, "rules_lines": rules_lines,
                     "type_layer": type_layer(run, brief, words) if on_top else None, "bars": list(bars)}}


def _picture_settings(job, door, model_rid, vendor, plain):
    """Settings the call names every time. The first rungs read the picture engine's own route row; a backup reads its
    rulebook's door defaults (nothing is invented here)."""
    if job in ("pictures.generate", "pictures.edit"):
        try:
            e = plain.R.table()["models"]["gpt-image-person"]
        except (KeyError, SystemExit):                        # the engine's route row and the House disagree for now
            hf = ((IR.load(model_rid).get("doors") or {}).get(door) or {}).get("house") or {}
            return ({"variant": hf.get("variant"), "quality": hf.get("quality"), "resolution": hf.get("resolution"),
                     "aspect": "9:16", "size": None, "vendor_model": vendor, "route_mismatch": True},
                    {"provider": door, "vendor_model": vendor, "must_name": (),
                     "params": {k: hf[k] for k in ("variant", "quality", "resolution") if hf.get(k)}})
        prm = dict(e.get("params") or {})
        if e.get("provider") == "higgsfield":
            return {"variant": prm.get("variant"), "quality": prm.get("quality"), "resolution": prm.get("resolution"),
                    "aspect": "9:16", "size": None, "vendor_model": e.get("vendor_model")}, e
        return {"quality": prm.get("quality"), "size": (e.get("sizes") or {}).get("9:16"), "aspect": "9:16",
                "vendor_model": e.get("vendor_model")}, e
    hf = (IR.load(model_rid).get("doors") or {}).get("higgsfield") or {}
    return {"resolution": hf.get("resolution_default"), "variant": hf.get("variant_default"), "quality": hf.get("quality_default"),
            "aspect": "9:16", "vendor_model": vendor}, {"provider": door, "vendor_model": vendor, "params": {
                k: v for k, v in (("resolution", hf.get("resolution_default")), ("variant", hf.get("variant_default")),
                                  ("quality", hf.get("quality_default"))) if v}, "must_name": ()}


# ------------------------------------------------------------------------------------------------ the clips

CLIP_FIELDS = {
    "run": "the video run, brand/run-name under runs/video-production (its storyboard and brief are read from it)",
    "call": "the clip call, e.g. G01-C1-1 (default: the first)",
    "scene": "the scene to edit: its `happens` line", "scene_id": "which scene the edit above is for (default: the call's first)",
    "face": "what the face does in the scene's first shot", "gestures": "what the hands do in the scene's first shot",
    "camera_move": "push-in · pan · tilt · arc · handheld · hold", "style": "the one look for the piece (default: the run's)",
}


def _clip_chain():
    return _load("video-production/machine/clips_run.py")


def _run_dir(run):
    base = REPO / "runs" / "video-production"
    p = Path(run) if Path(run).is_absolute() else base / run
    if not (p / "storyboard.json").is_file():
        raise ValueError(f"no video run at {p} (needs storyboard.json and plan.json)")
    return p


def build_clip(brief, job="clips.seedance"):
    cr = _clip_chain()
    run = _run_dir(brief["run"])
    doc = json.loads((run / "plan.json").read_text())
    sb = json.loads((run / "storyboard.json").read_text())
    opening = json.loads((run / "opening.json").read_text()) if (run / "opening.json").is_file() else {}
    saved_inputs = json.loads((run / "clip-inputs.json").read_text()) if (run / "clip-inputs.json").is_file() else {}
    motion_defaults = json.loads((run / "motion.json").read_text()) if (run / "motion.json").is_file() else {}
    brief = {**({"movement_id": "none"} if motion_defaults.get("use_movement_reference") is False else {}), **saved_inputs, **brief}
    # the same preparation clips_run.start() does before it plans: silent scenes say so, each scene carries its speaker
    scenes = json.loads(json.dumps(doc.get("scenes") or []))
    for sc in scenes:
        v = str(sc.get("voice") or "").strip()
        if re.match(r"(?i)^none\b", v):
            rest = re.sub(r"(?i)^none\.?\s*(heard:\s*)?", "", v).strip()
            if rest and not sc.get("sound"):
                sc["sound"] = rest
            sc["voice"] = ""
    scenes = cr.with_speakers(run, sb, scenes)
    scenes = cr.one_cut(sb, scenes)                         # one swipe cut, one continuous take (clips_run.one_cut)
    ho = {t.get("after_scene"): str(t.get("kind") or "").lower() for t in (doc.get("layers") or {}).get("transitions") or []
          if isinstance(t, dict) and str(t.get("kind") or "").lower() in ("continuous", "action", "match", "whip", "cut")}
    scenes = [{**sc, "hands_off": ho[sc.get("id")]} if sc.get("id") in ho and not sc.get("hands_off") else sc for sc in scenes]
    # the person's edits, applied to the scene before the chain's own planner reads it
    sid = brief.get("scene_id")
    first = next((c for c in cr.plan(run, sb, scenes, style=cr.style_line(run, doc))["calls"]
                  if brief.get("call") in (None, c["id"])), None)
    if first is None:
        raise ValueError(f"no call {brief.get('call')!r} in {run.name}")
    sid = sid or (first.get("scenes") or [None])[0]
    for sc in scenes:
        if sc.get("id") != sid:
            continue
        if brief.get("scene") is not None:
            sc["happens"] = brief["scene"]
            sc["beats"] = []
        shots = sc.get("shots") or []
        if shots and any(brief.get(k) is not None for k in ("face", "gestures", "camera_move")):
            shots[0] = {**shots[0], **{k: brief[k] for k in ("face", "gestures", "camera_move") if brief.get(k) is not None}}
    style = brief["style"] if brief.get("style") is not None else cr.style_line(run, doc)
    res = cr.plan(run, sb, scenes, style=style)
    call = dict(next(c for c in res["calls"] if c["id"] == first["id"]))
    if brief.get("movement_id") is not None:
        movement = cr._load("movement")
        call["refs"] = [r for r in call.get("refs", []) if r.get("kind") != "movement"] + movement.for_call(
            call, " ".join(str(s.get("happens") or "") for s in scenes), brief["movement_id"])
    # the person's clip settings, applied to the call; the prompt is then the chain's own builder's (CSH-2 (maker's four blocks))
    skip = set(brief.get("skip") or [])
    if brief.get("spice") is not None:
        call["spice_level"] = int(brief["spice"])
        lay = cr.spice_layers(int(brief["spice"]))
        call["spice_layers"] = sorted(lay) if lay is not None else None
    has_end = bool(call.get("end_frame")) and call.get("end_frame") != call.get("start_frame") and not call.get("talking")
    if "end" in skip and has_end:
        call["end_frame"] = call["start_frame"]
    for r in call.get("refs") or []:
        if r.get("kind") == "movement":                       # a real person's movement, prepared locally so the board can play it
            try:
                cr._load("movement").make(run, r)
            except Exception:
                pass
    call["refs"] = [r for i, r in enumerate(call.get("refs") or []) if f"motion:{i}" not in skip]
    people, _ = cr.people_of(run)
    cfg = cr.route_cfg(None, cr.format_of(run, doc))
    lead = ((sb.get("people_map") or {}).get("lead") or [None])[0]
    by_id = {x["id"]: x for x in scenes}
    sb_ = cr._load("scene_breakdown")
    br_ = sb_.of_call(run, call)
    call["swipe_elements"] = sb_.prompt_lines(br_)                    # the swipe's elements for this scene (2026-10-28)
    call["camera_held"] = bool((br_.get("drift") or {}).get("held"))
    sp = cr._load("seedance_prompt")
    built_sp = sp.build(call, by_id, people, cfg["words"], style, lead)
    prompt = built_sp["prompt"]
    tone = clip_tone(brief)
    if tone:                                                  # CSH-3 (changed dials said): one sentence in the look block
        blocks = prompt.split("\n\n")
        blocks[1] = blocks[1].rstrip() + " " + tone
        prompt = "\n\n".join(blocks)
    inputs = []
    has_end = bool(call.get("end_frame")) and call.get("end_frame") != call.get("start_frame") and not call.get("talking")
    pics = [call.get("start_frame")] + ([call.get("end_frame")] if has_end else [])
    for i, pid in enumerate([p for p in pics if p], 1):
        f = cr.cp.picture_file(run, pid)
        inputs.append({"n": i, "kind": "image", "role": "the start picture" if i == 1 else "the end picture", "path": str(f) if f else f"{pid} (not made yet)"})
    voice = []
    for l in call.get("voice_parts") or []:
        f = run / "vo" / f"{l['scene']}.mp3"
        voice.append({"n": len(voice) + 1, "kind": "audio", "role": f"the voice read of {l['scene']}", "path": str(f) if f.is_file() else f"{f.name} (not read yet)"})
    vids = [{"n": i + 1, "kind": "video", "role": ("a real person's movement (no colour, no sound)" if r.get("kind") == "movement" else "motion from the ad (blurred)"),
             "path": str(run / r.get("file")) if r.get("file") else ""} for i, r in enumerate(call.get("refs") or [])]
    sc0 = next((x for x in scenes if x.get("id") == sid), {})
    sh0 = (sc0.get("shots") or [{}])[0]
    # what the picker shows: every candidate, ticked or not
    choices = [{"key": "start", "label": "The start picture", "path": inputs[0]["path"] if inputs else "", "on": True, "fixed": True}]
    end_raw = next((c for c in res["calls"] if c["id"] == first["id"]), {})
    if brief.get("movement_id") is not None:
        end_raw = {**end_raw, "refs": call["refs"]}
    if end_raw.get("end_frame") and end_raw.get("end_frame") != end_raw.get("start_frame") and not end_raw.get("talking"):
        f = cr.cp.picture_file(run, end_raw["end_frame"])
        choices.append({"key": "end", "label": "The end picture", "path": str(f) if f else "", "on": "end" not in skip})
    for v in voice:
        choices.append({"key": "voice", "label": "The voice read", "path": v["path"], "kind": "audio", "on": True, "fixed": True})
    for i, r in enumerate(end_raw.get("refs") or []):
        choices.append({"key": f"motion:{i}", "label": "Real human movement" if r.get("kind") == "movement" else "Motion from the ad",
                        "path": str(run / r.get("file")) if r.get("file") else "",
                        "kind": "video", "on": f"motion:{i}" not in skip})
    who = (call.get("lines") or [{}])[0].get("speaker") if call.get("lines") else None
    who = who or lead
    pinfo = people.get(who) or {}
    calls = [{"id": c["id"], "seconds": c["duration"], "talking": bool(c.get("talking")), "scenes": c.get("scenes"),
              "start": str(cr.cp.picture_file(run, c.get("start_frame")) or "")} for c in res["calls"]]
    level = call.get("spice_level") or 2
    real = cr.realism_rows(call.get("realism_format") or cr.REALISM_FORMAT.get(call.get("camera")), cr.CLIP_FAMILIES, call.get("realism"),
                           level=int(level))[:4]
    return {"prompt": prompt, "inputs": inputs + voice + vids, "medium": "video", "choices": choices,
            "settings": {"duration": call["duration"], "aspect": "9:16", "resolution": call["resolution"], "endpoint": call["endpoint"],
                         "audio": bool(call.get("talking")), "takes": call.get("takes")},
            "fields": {"scene": sc0.get("happens") or "", "scene_id": sid, "face": cr._as_text(sh0.get("face")), "gestures": cr._as_text(sh0.get("gestures")),
                       "camera_move": sh0.get("camera_move") or "", "camera": cr.camera_move_of(sc0) or call.get("camera") or "still",
                       "style": style, "call": call["id"], "spice": level, "who": cr.desc(who, people) if who in people else "",
                       "who_id": who, "marks": str(pinfo.get("marks") or "").strip(), "own_gestures": str(pinfo.get("gestures") or "").strip(),
                       "has_people": bool(call.get("people")), "emotion": cr._as_text(sh0.get("emotion") or sc0.get("emotion")),
                       "hand_off": str(sh0.get("hands_off") or sc0.get("hands_off") or call.get("hands_off") or "").strip().lower(), "ends_on": cr._as_text(cr.last_shot(sc0).get("ends_on")),
                       "line": " ".join(l.get("text", "") for l in call.get("lines") or [] if l.get("on_camera")),
                       "realism": [r["prompt"].strip() for r in real], "windows": built_sp["windows"], "dropped": built_sp["dropped"],
                       "creative_controls": (opening.get("matrix_row") or {}).get("controls") or {},
                       "brand": doc.get("brand") or run.parent.name, "video": run.name, "title": _video_title(run), "end_frame": end_raw.get("end_frame"),
                       "split_line": any(l.get("part") for l in call.get("lines") or []), "acting": built_sp.get("acting") or []},
            "calls": calls,
            "notes": [f"estimate from the chain's own price list: ${call['usd']} for this call"] + [f"the chain's plan stops: {p}" for p in res["problems"] if call["id"] in p or sid in p],
            "estimate_usd": call["usd"], "calls_in_run": [c["id"] for c in res["calls"]],
            "send": {"run": str(run), "call": call, "prompt": prompt, "masters_people": call.get("people") or [],
                     "start": inputs[0]["path"] if inputs else None, "end": inputs[1]["path"] if len(inputs) > 1 else None,
                     "voice": voice[0]["path"] if voice else None, "videos": [v["path"] for v in vids],
                     "line": " ".join(p_["line"] for p_ in call.get("voice_parts") or [])}}


def _video_title(run):
    f = Path(run) / "brief.md"
    if f.is_file():
        h = next((l for l in f.read_text().splitlines() if l.startswith("# ")), "")
        if h:
            return h[2:].strip()
    return Path(run).name.replace("-", " ").capitalize()


def clip_tone(brief):
    """CSH-3 (changed dials said): the dials, feelings and techniques a person changed, as one sentence."""
    c = controls()
    bits = []
    for k, v in (brief.get("dials") or {}).items():
        d = next((x for x in c["dials"] if x["id"] == k), None)
        sc = next((x for x in (d or {}).get("scale", []) if x["level"] == int(v)), None)
        if sc:
            bits.append(f"{d['name'].lower()} {sc['name']}, {sc['what'].rstrip('.').lower()}")
    for e in c["emotions"]:
        if e["id"] in (brief.get("emotions") or []):
            bits.append(f"the feeling is {e['name'].lower()}: {e.get('video') or e['what']}".rstrip("."))
    for x in c["techniques"]:
        if x["id"] in (brief.get("techniques") or []):
            bits.append(f"{x['name'].lower()}: {x['what'].rstrip('.').lower()}")
    return ("Tone: " + "; ".join(bits) + ".") if bits else ""


# ------------------------------------------------------------------------------------------------ the preview

def _house():
    return IR._house()


def _quote(built, job, door, vendor, params, aspect, plain):
    """The credits Higgsfield would charge, asked for free. A reason in words when it cannot be asked."""
    try:
        if door != "higgsfield":
            return {"credits": None, "say": f"the {door} door prices in dollars on its bill, not credits"}
        if built["medium"] == "image":
            c = plain.PR.higgsfield_cost({"vendor_model": vendor, "params": {k: v for k, v in params.items() if v}, "must_name": ()},
                                         built["prompt"], [], aspect)
        else:
            import subprocess
            exe = plain.PR._HfShell().which()
            plain.PR.higgsfield_ready_exe(plain.PR._HfShell())
            s = built["settings"]
            argv = [exe] + list(built["quote_args"]) if built.get("quote_args") else [
                exe, "generate", "cost", vendor, "--prompt", built["prompt"], "--duration", str(int(s["duration"])),
                "--resolution", s["resolution"], "--aspect_ratio", s["aspect"], "--json"]   # a builder whose model takes other params says its own
            p = subprocess.run(argv, capture_output=True, text=True, timeout=120)
            c = float(json.loads(p.stdout)["credits"])
        return {"credits": c, "say": f"{c:g} credits"}
    except Exception as e:                                   # noqa: BLE001
        return {"credits": None, "say": f"no quote: {str(e)[:160]}"}


PLAIN_MODEL = {"gpt-image-2.5": "GPT Image 2.5", "seedream-5-pro-edit": "Seedream 5 Pro", "gemini-3-pro-image": "Nano Banana Pro",
               "seedance-2.5": "Seedance 2.5", "kling-4.0": "Kling"}


def plain_rung(x):
    """One rung of the backup ladder in plain words, in the order the engine tries them."""
    if not x.get("model"):
        return {"retry once": "Try again", "another take (three at most)": "Try again (up to three times)",
                "the best take is kept and flagged below_criteria": "Keep the best try and flag it"}.get(x["rung"], x["rung"])
    name = PLAIN_MODEL.get(x["model"], x["model"])
    return name + (" (OpenAI direct)" if x.get("door") == "openai" else f" ({x['door']})" if x["rung"].endswith("overflow") else "")


def _ladder(job):
    out = []
    for rung in LADDER.get(job, []):
        if "." in rung and rung.split(".")[0] in ("pictures", "clips", "swipe_footage") and " " not in rung:
            try:
                m = _house().model(rung)
                out.append({"rung": rung, "model": m.get("registry_id"), "door": m.get("door")})
            except KeyError:
                node = _house().house()
                for part in rung.split("."):
                    node = node.get(part) if isinstance(node, dict) else None
                if isinstance(node, dict) and node.get("registry"):      # a row the reader does not route, read as written
                    out.append({"rung": rung, "model": node["registry"], "door": node.get("door"), "say": node.get("state") or "listed, not routed"})
                # a rung the House does not have today is left out: the ladder is what the engine would try

        else:
            out.append({"rung": rung})
    return out


# ------------------------------------------------------------------------------------------------ the picture sheet

SHEET_FILE = HERE / "picture-sheet.json"
FILLED, NA, MISSING = "filled", "not_applicable", "missing"
APPROVAL = "cost_approval"


def sheet_file(kind="picture"):
    return HERE / f"{kind}-sheet.json"


def sheet_def(kind="picture"):
    """Every variable a picture (picture-sheet.json) or a clip (clip-sheet.json) takes, with the creative dials of that
    medium and the 9 guards added from creative-controls."""
    d = json.loads(sheet_file(kind).read_text())
    c = controls()
    pick = {"presets": [p["id"] for p in c["presets"]], "emotions": [e["id"] for e in c["emotions"]],
            "techniques": [x["id"] for x in c["techniques"]]}
    out = []
    for v in d["variables"]:
        v = dict(v)
        if v.get("allowed_from"):
            v["allowed"] = pick[v.pop("allowed_from")]
        out.append(v)
    floor = c.get("floor", {})
    for x in c["dials"]:
        if d.get("dial_media") and d["dial_media"] not in x["media"]:
            continue
        req = x["id"] in d["required_dials"]
        out.append({"id": "dial." + x["id"], "group": "creative", "name": x["name"], "means": x["what"].split(". ")[0].rstrip(".") + ".",
                    "kind": "level", "allowed": [l["level"] for l in x["scale"]], "scale": {l["level"]: l["name"] for l in x["scale"]},
                    "floor": floor.get("levels", {}).get(x["id"]), "floor_when_set": x["id"] in floor.get("when_set", []),
                    "na": [] if req else list(d["dial_na"]), "required": req})
    for g in c["guards"]:
        out.append({"id": "guard." + g["id"], "group": "guards", "name": g["name"], "means": g["what"].split(". ")[0].rstrip(".") + ".",
                    "kind": "on", "allowed": ["on"], "na": [], "required": True})
    return {"groups": d["groups"], "variables": out}


MADE_HERE = ("runs/image-production/", "runs/image-teardown/", "runs/video-production/", "runs/image-edit/")


def chosen_record(path):
    """PSH-5 (chosen references): None when a picture may go in (a real photo, or a made picture with a chosen record);
    else why not. Returns (ok, below_criteria): below_criteria is the failed-check list a chosen picture carries."""
    p = Path(str(path))
    rel = str(p.resolve()).replace(str(REPO.resolve()) + "/", "")
    if not rel.startswith(MADE_HERE) or "/ai-elements/" in rel or "/_bench-uploads/" in rel:
        return True, []
    if rel.startswith("runs/image-teardown/") and "assets" in Path(rel).parts[3:5]:
        return True, []                                      # the swipe itself: a picture run's assets/ (its home since 2026-10-28)
    if rel.startswith("runs/video-production/") and p.parent.name == "media":
        return True, []                                      # the picture a video run chose for its scene
    if p.stem.endswith(".plate"):                           # a plate is its picture before the words: the picture's record decides
        stem = p.stem[:-len(".plate")]
        for pic in (p.with_name(stem + p.suffix), p.parent.parent / (stem + p.suffix)):
            if pic.is_file() and chosen_record(pic)[0]:
                return chosen_record(pic)
        return False, []
    rec = p.with_suffix(".recipe.json")
    if not rec.is_file():
        return False, []
    try:
        r = json.loads(rec.read_text())
    except ValueError:
        return False, []
    chosen = r.get("chosen") or p.with_suffix(".chosen.json").is_file() or p.with_suffix(".liked.json").is_file()
    return bool(chosen), list(r.get("below_criteria") or [])


def validate(recipe, for_make=True):
    """Every problem with a filled sheet, each naming the variable in plain words. [] means the sheet is complete.
    MISSING, a value outside its allowed set, a not-applicable without an allowed reason, a not-applicable on a dial or
    guard the guards require, and a floor dial under the never-sterile floor are all refused. `for_make=False` leaves
    out the cost approval, which the person gives by pressing Make."""
    sheet = (recipe or {}).get("sheet") or {}
    kind = (recipe or {}).get("kind") or "picture"
    out = []

    def bad(v, say):
        out.append({"id": v["id"], "name": v["name"], "say": f"{v['name']}: {say}"})

    for v in sheet_def(kind)["variables"]:
        if v["id"] == APPROVAL and not for_make:
            continue
        e = sheet.get(v["id"]) or {"state": MISSING}
        st = e.get("state")
        if st == NA:
            if v.get("required") or not v.get("na"):
                bad(v, "cannot be not applicable (" + ("PSH-3 (guard dials set)" if v.get("required") else "PSH-1 (inputs all set)") + ").")
            elif e.get("reason") not in v["na"]:
                bad(v, "not applicable needs one of these reasons (PSH-1 (inputs all set)): " + "; ".join(v["na"]) + ".")
            continue
        if st != FILLED:
            bad(v, "missing (PSH-1 (inputs all set)).")
            continue
        val, k = e.get("value"), v["kind"]
        if k in ("text",) and not str(val or "").strip():
            bad(v, "missing (PSH-1 (inputs all set)).")
        elif k in ("choice", "on") and val not in v.get("allowed", [val]):
            bad(v, f"{val!r} is not one of: {', '.join(map(str, v['allowed']))}.")
        elif k == "list":
            if not isinstance(val, list) or not [x for x in val if str(x).strip()]:
                bad(v, "missing (PSH-1 (inputs all set)).")
            elif v.get("allowed") and any(x not in v["allowed"] for x in val):
                bad(v, "has a value that is not allowed: " + ", ".join(str(x) for x in val if x not in v["allowed"]) + ".")
        elif k == "yesno":
            m = re.match(r"^(yes|no)\s*:\s*(.*)$", str(val or ""), re.S)
            if not m:
                bad(v, "missing: yes or no (PSH-11 (inputs from the swaps)).")
            elif m.group(1) == "no" and not m.group(2).strip():
                bad(v, "'no' needs the brief's reason (PSH-11 (inputs from the swaps)).")
        elif k == "swaps":
            if not isinstance(val, list) or not val:
                bad(v, "missing (PSH-11 (inputs from the swaps)).")
            else:
                for r in val:
                    if r.get("kind") not in SWAP_KINDS:
                        bad(v, f"'{r.get('from')}' has the kind {r.get('kind')!r}, not one of {', '.join(SWAP_KINDS)}.")
                    elif r.get("kind") in NEEDS_PICTURE and not r.get("exists"):
                        bad(v, f"{r.get('needs')} is not on file ({r.get('path')}), so '{r.get('from')} → {r.get('to')}' "
                               "cannot be made (PSH-11 (inputs from the swaps)).")
        elif k == "level":
            if val not in v["allowed"]:
                bad(v, f"{val!r} is not a level of this dial ({', '.join(map(str, v['allowed']))}).")
            elif v.get("floor") is not None and val < v["floor"]:
                bad(v, f"{val} is under the floor of {v['floor']} (PSH-4 (sterile floor)).")
    pin = sheet.get("pictures_in") or {}
    if kind == "clip":
        pin = {"paths": [(sheet.get(k) or {}).get("path") for k in ("start_picture", "end_picture") if (sheet.get(k) or {}).get("path")],
               "value": [n for k, n in (("start_picture", "The start picture"), ("end_picture", "The end picture")) if (sheet.get(k) or {}).get("path")]}
    for path, lab in zip(pin.get("paths") or [], pin.get("value") or []):
        ok, _ = chosen_record(path)
        if not ok:
            out.append({"id": "pictures_in", "name": "Pictures going in",
                        "say": f"Pictures going in: '{lab}' was made by the system and has no chosen record (PSH-5 (chosen references))."})
    return out


def flags(recipe):
    """Amber notes that never stop a flow (PSH-8 (outputs never stop)): a reference carrying below_criteria."""
    pin = ((recipe or {}).get("sheet") or {}).get("pictures_in") or {}
    out = []
    for path, lab in zip(pin.get("paths") or [], pin.get("value") or []):
        ok, below = chosen_record(path)
        if ok and below:
            out.append({"id": "pictures_in", "name": "Pictures going in",
                        "say": f"'{lab}' was chosen below criteria ({'; '.join(below)}). The flag travels with this picture."})
    return out


def pick_best(attempts):
    """PSH-8 (outputs never stop): attempts scored by their failed checks ({"id", "failed": [...]}); the one with the
    fewest is chosen; it is marked below_criteria with those checks when any failed. Never raises on a failed check."""
    if not attempts:
        raise ValueError("no attempts to choose from")
    best = min(attempts, key=lambda a: len(a.get("failed") or []))
    return {**best, "chosen": True, "below_criteria": list(best.get("failed") or [])}


def _run_ask(run):
    """The order a teardown run was made for (vars/ask.md names its ask.json), or {}."""
    try:
        p = (run / "vars" / "ask.md").read_text().strip()
        return json.loads((REPO / p).read_text()) if p else {}
    except (OSError, ValueError):
        return {}


def _row(md, label):
    m = re.search(r"^\|\s*\*\*" + re.escape(label) + r"\*\*\s*\|\s*(.+?)\s*\|\s*$", md, re.M)
    return m.group(1).strip() if m else ""


def _f(value, source):
    return {"state": FILLED, "value": value, "source": source}


def _na(reason):
    return {"state": NA, "reason": reason, "source": "filled from the brief"}


def recipe_of(x):
    """A recipe from a recipe or a bare brief."""
    if isinstance(x, dict) and isinstance(x.get("brief"), dict):
        return x
    x = dict(x or {})
    sheet = x.pop("sheet", None) or {}                        # the Bench sends its brief with the person's sheet entries inside
    return {"brief": x, "sheet": sheet}


def brief_of(recipe):
    """The brief the picture builder takes, with every value a person set on the sheet applied."""
    r = recipe_of(recipe)
    b = json.loads(json.dumps(r["brief"]))
    clip = r.get("kind") == "clip"
    for k, e in (r.get("sheet") or {}).items():
        if (e or {}).get("state") != FILLED or e.get("source") != "person":
            continue
        v = e.get("value")
        if clip:
            m = {"happens": "scene", "face": "face", "hands": "gestures", "camera": "camera_move", "look": "style", "spice": "spice"}
            if k in m:
                b[m[k]] = int(v) if k == "spice" else v
            elif k in ("emotion", "techniques"):
                b["emotions" if k == "emotion" else "techniques"] = v
            elif k.startswith("dial."):
                b.setdefault("dials", {})[k[5:]] = int(v)
            continue
        if k == "product_in_frame":
            b["show_product"] = str(v).startswith("yes")
        elif k == "words_mode":
            b["words_mode"] = v
        elif k == "scene":
            b["swaps"] = v
        elif k in ("subject", "details", "place_light", "photo_style", "colours", "camera"):
            b.setdefault("ingredients", {})[k] = v
        elif k == "words":
            b["our_copy"] = [str(x).split(" — sits ")[0].replace("\n", " / ") for x in v]
        elif k == "people_mode":
            b["people"] = v
        elif k in ("people_who", "people_age", "people_look", "wardrobe"):
            lab = {"people_who": "who", "people_age": "age", "people_look": "look", "wardrobe": "wearing"}[k]
            b["people_lines"] = [l for l in b.get("people_lines") or [] if not l.startswith(lab + ": ")] + [f"{lab}: {v}"]
        elif k == "keep_exactly":
            b["keep"] = [x for x, lab in KEEP.items() if lab in v]
        elif k == "emotion":
            b["emotions"] = v
        elif k == "techniques":
            b["techniques"] = v
        elif k.startswith("dial."):
            b.setdefault("dials", {})[k[5:]] = int(v)
    return b


SWIPE_LOOK = "the swipe, as IMAGE 1 shows it (no line sent)"


def full_brief(filled):
    """PSH-6 (every input sent): the brief with every FILLED dial, feeling, technique and keep item, so the picture
    builder writes them all into labelled lines. NOT_APPLICABLE items are left out."""
    b = brief_of(filled)
    s = filled.get("sheet") or {}
    filled_ = lambda k: (s.get(k) or {}).get("state") == FILLED
    b["dials"] = {k[5:]: int(e["value"]) for k, e in s.items() if k.startswith("dial.") and filled_(k) and dial_send(k[5:]) == "picture"
                  and e.get("source") != SWIPE_LOOK}       # IMAGE 1 already shows the swipe's own look: no line for it
    if filled_("emotion"):
        b["emotions"] = list(s["emotion"]["value"])
    if filled_("techniques"):
        b["techniques"] = list(s["techniques"]["value"])
    if filled_("keep_exactly"):
        b["keep"] = [k for k, lab in KEEP.items() if lab in s["keep_exactly"]["value"]]
    return b


def fill_defaults(recipe, built=None):
    """The sheet filled from what the brief, its brand step and the house files already say; a person's own entries
    (source 'person') win. Returns the recipe with its full sheet and `needs`: the variables still MISSING."""
    r = recipe_of(recipe)
    b = brief_of(r)
    built = built or build_picture(b)
    f = built["fields"]
    run = _lane_run(b["brand"], b["run"])
    t = (run / "out" / "03-injection.md").read_text()
    bf = run / "out" / "06-brief.md"
    md = bf.read_text() if bf.is_file() else ""
    with_ref = f.get("with_ref")
    ch = built.get("choices") or []
    s = {"brand": _f(b["brand"], "the brief")}
    s["product"] = _f(b.get("product") or b.get("product_slug"), "the brief") if (b.get("product") or b.get("product_slug")) else {"state": MISSING}
    s["avatar"] = _f(_row(md, "For"), "the brief's 'For'") if _row(md, "For") else {"state": MISSING}
    s["angle"] = _f(_row(md, "Core message"), "the brief's core message") if _row(md, "Core message") else {"state": MISSING}
    off = _row(md, "Offer")
    s["offer"] = _na("no offer on this ad") if (not off or off.lower().startswith("none")) else _f(off, "the brief's offer")
    if not md:
        # No brief yet: since 2026-10-27 the brief is written after the first picture is approved (its variations
        # vary the approved words), so the first picture fills these from the run's own order and brand step.
        ask = _run_ask(run)
        if ask.get("avatar"):
            s["avatar"] = _f(ask["avatar"], "the run's order (ask.json), no brief yet")
        why = re.search(r"\*\*WHY IT STILL READS:\*\*\s*(.+)", t)
        if why:
            s["angle"] = _f(why.group(1).strip(), "the brand step's 'Why it still reads', no brief yet")
        lines = (ask.get("offer") or {}).get("lines") or []
        if lines:
            s["offer"] = _f("; ".join(lines), "the run's order (ask.json), no brief yet")
    s["swipe"] = (_f(_row(md, "Built on") or b["run"], "the brief's 'Built on'") if with_ref
                  else _na("made from the written plan alone, no ad copied"))
    on = [c["label"] for c in ch if c["on"]]
    s["pictures_in"] = ({**_f(on, "the pictures ticked"), "paths": [c["path"] for c in ch if c["on"]]} if on
                        else _na("a fresh picture with no reference pictures"))
    sw = f.get("swap_list")
    if sw is None:                                           # PSH-11 (inputs from the swaps): never guessed
        for k in ("swap_list", "product_in_frame", "swaps", "stays", "words_mode"):
            s[k] = {"state": MISSING}
    else:
        s["swap_list"] = (_f("set in the matrix", "person") if f.get("swap_edited") else
                          _f(f["swap_file"].replace(str(REPO) + "/", ""), "a sample list, not the teardown's" if f.get("swap_sample") else "the teardown"))
        ans = f.get("product_answer") or ""
        s["product_in_frame"] = _f(ans, "the swap list" if b.get("show_product") is None else "person") if ans else {"state": MISSING}
        rows = f.get("swap_rows") or []
        s["swaps"] = _f(rows, "the swap list") if rows else _na("the swipe is copied with nothing swapped")
        st = f.get("stays_list") or []
        s["stays"] = _f(st, "the swap list") if st else _na("the swap list names nothing that stays")
        wm = f.get("words_mode")
        s["words_mode"] = _f(wm, "the swap list") if wm else (_na("no words on this ad") if not f.get("our_copy") else {"state": MISSING})
    s["scene"] = _f(f.get("swaps"), "the brand step's swap") if str(f.get("swaps") or "").strip() else {"state": MISSING}
    ing = b.get("ingredients") or {}
    std = f.get("standout") or ""
    s["subject"] = (_f(ing["subject"], "person") if ing.get("subject") else _f(std, "the brand step's standout") if std
                    else _na("kept from the ad we copy") if with_ref else {"state": MISSING})
    for k in ("details", "place_light", "photo_style", "colours", "camera"):
        s[k] = _f(ing[k], "person") if ing.get(k) else (_na("kept from the ad we copy") if with_ref else {"state": MISSING})
    words = [plain_words(c) for c in f.get("our_copy") or []]
    s["words"] = ({**_f(words, "the brand step's words"), "where": list(f.get("zones_where") or [])} if [w for w in words if w]
                  else _na("no words on this ad"))
    slug = f.get("product") or None                          # the product actually in the frame (none when the swap list says no)
    sides = [c["label"] for c in ch if c["key"].startswith("product:") and c["on"]]
    if slug:
        s["product_kit"] = _f(slug, "the brief")
        s["product_sides"] = _f(sides, "the pictures ticked") if sides else {"state": MISSING}
        m = re.search(r"is ([\d.]+ cm tall and [\d.]+ cm wide)", built["prompt"])
        s["product_size"] = _f(m.group(1), "the product kit") if m else _na("the kit has no measured size yet")
    else:
        for k in ("product_kit", "product_sides", "product_size"):
            s[k] = _na("the product is not in this picture")
    s["people_mode"] = _f(f.get("people") or ("lookalike" if with_ref else "made-up"), "the brief")
    for k in ("people_who", "people_age", "people_look", "wardrobe"):
        s[k] = _na("lookalike of the person in the ad") if s["people_mode"]["value"] == "lookalike" else {"state": MISSING}
    if s["people_mode"]["value"] == "cast":
        s["people_who"] = _f(", ".join(f.get("cast") or []), "the swap list's cast swaps")
        for k in ("people_age", "people_look", "wardrobe"):
            s[k] = _na("the cast photo sets it")
    s["shape"] = _f("9:16", "the house frame")
    s["safe_zone"] = _f("centre 4:5", "the house frame")
    s["keep_exactly"] = (_f(["everything the swap does not change"] + [KEEP[k] for k in b.get("keep") or [] if k in KEEP], "the house rules")
                         if with_ref else _na("made from the written plan alone, no ad copied"))
    s["no_other_writing"] = _f("yes", "the house rules")
    tgt = run / "vars" / "controls-target.md"
    tt = tgt.read_text() if tgt.is_file() else ""
    pm = re.search(r"^Preset: .*?\((\S+)\)", tt, re.M)
    c = controls()
    # a brief written before its run named a preset takes the chain's own default, the one the writing step opens every
    # run with (image-writing controls_target: maxed), never a red stop (2026-10-27)
    house = next((p for p in c["presets"] if p["id"] == "maxed"), c["presets"][0])
    s["preset"] = _f(pm.group(1), "the brief's preset") if pm else _f(house["id"], "the chain's default preset (the brief names none)")
    if not pm:
        tt += "".join(f"\n- {k}: {v}" for k, v in (house.get("levels") or {}).items())
    emo_line = pic_label(t, "THE EMOTION")
    emos = list(b.get("emotions") or []) or [e["id"] for e in c["emotions"] if re.search(r"\b" + re.escape(e["name"]) + r"\b", emo_line, re.I)]
    # a brand step written before it named THE EMOTION takes the swipe's own read of it (out/controls-swipe.json), the
    # way the dials do (2026-10-27)
    sread = {}
    if (run / "out" / "controls-swipe.json").is_file():
        try:
            sread = json.loads((run / "out" / "controls-swipe.json").read_text())
        except ValueError:
            sread = {}
    emo_from = "the brand step's emotion" if not b.get("emotions") else "person"
    if not emos and isinstance(sread.get("emotion"), dict):
        said = " ".join(str(sread["emotion"].get(k) or "") for k in ("primary", "secondary"))
        emos = [e["id"] for e in c["emotions"] if re.search(r"\b(" + re.escape(e["id"]) + "|" + re.escape(e["name"]) + r")\b", said, re.I)]
        emo_from = "the swipe's own read"
    s["emotion"] = _f(emos, emo_from) if emos else {"state": MISSING}
    tech_ids = {x["id"] for x in c["techniques"]}
    tl = pic_label(t, "THE TECHNIQUES").lower()
    techs = list(b.get("techniques") or []) or [x["id"] for x in c["techniques"]
                                                if re.search(r"(?<![a-z-])" + re.escape(x["id"]) + r"(?![a-z-])", tl) or x["name"].lower() in tl]
    tech_from = "the brand step's techniques"
    if not techs and sread.get("techniques"):
        techs = [x for x in sread["techniques"] if x in tech_ids]
        tech_from = "the swipe's own read"
    s["techniques"] = _f(sorted(set(techs)), tech_from) if techs else {"state": MISSING}
    aims = {m.group(1): int(m.group(2)) for m in re.finditer(r"^- ([a-z_]+): (-?\d)", tt, re.M)}
    own = f.get("dials_brief") or {}
    # A picture made FROM a swipe keeps the swipe's own look (2026-10-27). The preset aim is every
    # ad's default and fought IMAGE 1; the swipe's own dial read (out/controls-swipe.json) is the default for a picture
    # dial, and a level IMAGE 1 already shows is sent as no line. A person's level and the brand step's own line win.
    swipe_read = {}
    if with_ref and (run / "out" / "controls-swipe.json").is_file():
        try:
            swipe_read = {k: int(v["level"]) for k, v in json.loads((run / "out" / "controls-swipe.json").read_text())
                          .get("dials", {}).items() if isinstance(v, dict) and v.get("level") is not None}
        except (ValueError, TypeError):
            swipe_read = {}
    for x in c["dials"]:
        k = x["id"]
        if (b.get("dials") or {}).get(k) is not None:
            s["dial." + k] = _f(int(b["dials"][k]), "person")
        elif dial_send(k) == "film":
            s["dial." + k] = _na(picture_dials()["film_reason"])
        elif dial_send(k) == "writing" and k not in json.loads(SHEET_FILE.read_text())["required_dials"]:
            s["dial." + k] = _na(picture_dials()["writing_reason"])
        elif k in own:
            s["dial." + k] = _f(own[k]["level"], "the brand step's dial line" + ("" if dial_send(k) == "picture" else "; carried by the swaps and the words, not sent as a line"))
        elif dial_send(k) == "picture" and k in swipe_read:
            # the never-sterile floor still holds (PSH-4): a swipe calmer than the floor is raised to it, and that line is sent
            fl = (c.get("floor") or {}).get("levels", {}).get(k)
            if fl is not None and swipe_read[k] < fl:
                s["dial." + k] = _f(fl, "the swipe, raised to the never-sterile floor")
            else:
                s["dial." + k] = _f(swipe_read[k], SWIPE_LOOK)
        elif k in aims:
            s["dial." + k] = _f(aims[k], "the brief's preset aim" + ("" if dial_send(k) == "picture" else "; carried by the swaps and the words, not sent as a line"))
        elif "image" not in x["media"]:
            s["dial." + k] = _na("not used in a still picture")
        elif k in json.loads(SHEET_FILE.read_text())["required_dials"]:
            s["dial." + k] = {"state": MISSING}
        else:
            s["dial." + k] = _na("the brief sets no level for this dial and the ad does not use it")
    for g in c["guards"]:
        s["guard." + g["id"]] = _f("on", "always on")
    s["backups"] = _f([plain_rung(x) for x in _ladder("pictures.generate")], "the Model House")
    s["run_label"] = _f(b["run"], "the brief")
    s[APPROVAL] = {"state": MISSING}
    for k, e in (r.get("sheet") or {}).items():              # a person's word wins
        if e and (e.get("source") == "person" or e.get("state") == NA and e.get("source") != "filled from the brief"):
            s[k] = e
    out = {**r, "sheet": s}
    out["needs"] = [x["name"] for x in validate(out)]
    return out


def pic_label(t, name):
    m = re.search(r"(?m)^\s*(?:-\s*)?\*\*" + re.escape(name) + r":\*\*\s*(.+)", t)
    return m.group(1).strip() if m else ""


def sheet_view(recipe):
    """The filled sheet as rows for a page: group, plain name, meaning, state, value or reason, allowed reasons."""
    d = sheet_def(recipe.get("kind") or "picture")
    s = recipe.get("sheet") or {}
    bad = {x["id"]: x["say"] for x in validate(recipe)}
    rows = []
    for v in d["variables"]:
        e = s.get(v["id"]) or {"state": MISSING}
        val = e.get("value")
        if v["id"] == "words" and isinstance(val, list):      # the words as they read, line breaks kept, and how they go on
            how = (s.get("words_mode") or {}).get("value")
            val = " · ".join(f"“{w}”" for w in val if w) + (f" · {how}" if how else "")
        if v["kind"] == "swaps" and isinstance(val, list):     # one plain line per swap for a page; the rows stay in the recipe
            val = [f"{x.get('from')} → {x.get('to')} ({x.get('needs')}" + ("" if x.get("exists") is not False else ", not on file") + ")"
                   for x in val]
        rows.append({"id": v["id"], "group": v["group"], "name": v["name"], "means": v["means"], "kind": v["kind"],
                     "state": e.get("state", MISSING), "value": val, "reason": e.get("reason"), "source": e.get("source"),
                     "allowed": v.get("allowed"), "scale": v.get("scale"), "na": v.get("na"), "problem": bad.get(v["id"])})
    return {"groups": d["groups"], "rows": rows}


def _same(a, b):
    a, b = a or {"state": MISSING}, b or {"state": MISSING}
    return (a.get("state"), a.get("value"), a.get("reason")) == (b.get("state"), b.get("value"), b.get("reason"))


def make_frame_pair(recipe, delta):
    """The second picture of a set (a last frame for a first frame): an exact copy of the first sheet with ONLY the
    declared change. `delta` is {variable: value}; a locked variable (person, wardrobe, product, place, light, style,
    colours, camera, shape) cannot be in it."""
    d = json.loads(SHEET_FILE.read_text())
    locked = [k for k in delta if k in d["locked_in_a_set"]]
    if locked:
        raise ValueError("a frame pair cannot change a locked variable: " + ", ".join(locked))
    first = fill_defaults(recipe)
    second = json.loads(json.dumps({k: v for k, v in first.items() if k != "needs"}))
    for k, v in delta.items():
        second["sheet"][k] = {"state": FILLED, "value": v, "source": "person"}
    second["pair"] = {"of": first["brief"].get("run"), "delta": sorted(delta)}
    second.pop(APPROVAL, None)
    return second


def validate_pair(a, b):
    """PSH-7 (one sheet per scene): every locked variable identical, anything else that differs in b's declared delta.
    Returns the mismatches, each named; [] means the pair holds. A mismatch is an output finding: it scores the
    attempt (choose_pair), it never stops the flow (PSH-8 (outputs never stop))."""
    d = json.loads(SHEET_FILE.read_text())
    names = {v["id"]: v["name"] for v in sheet_def()["variables"]}
    sa = (a if "sheet" in a and a["sheet"] else fill_defaults(a))["sheet"]
    sb = (b if "sheet" in b and b["sheet"] else fill_defaults(b))["sheet"]
    delta = set((b.get("pair") or {}).get("delta") or [])
    out = []
    for k in sorted(set(sa) | set(sb)):
        if k in d["free_in_a_set"] or _same(sa.get(k), sb.get(k)):
            continue
        if k in d["locked_in_a_set"]:
            out.append({"id": k, "say": f"{names.get(k, k)}: not the same in both frames (PSH-7 (one sheet per scene))."})
        elif k not in delta:
            out.append({"id": k, "say": f"{names.get(k, k)}: changed but not declared (PSH-7 (one sheet per scene))."})
    return out


def choose_pair(first, attempts):
    """PSH-8 (outputs never stop): each second-frame attempt scored by validate_pair against the first; the best is
    chosen, marked below_criteria with its mismatches when it has any."""
    scored = [{"id": i, "attempt": x, "failed": [p["say"] for p in validate_pair(first, x)]} for i, x in enumerate(attempts)]
    return pick_best(scored)


def gate(recipe, for_make=True):
    """PSH-1 (inputs all set): raise ValueError, one plain line naming every blank, before any spend."""
    probs = validate(recipe, for_make)
    if probs:
        raise ValueError("Stopped before any spend, not set: " + ", ".join(dict.fromkeys(p["name"] for p in probs)) + ".")
    return True


# MAKE REAL, THEN SHOOT IT ON THE MEDIUM'S CAMERA (2026-10-28).
# One generation carrying a dozen references loses skin fidelity, so a picture with one of our people gets two passes
# after it is made: (1) REALISM — one edit that changes only the person's skin, with two pictures: the made picture and
# her macro-detail headshot; (2) LENS — the medium's own camera texture (lenses.json; a brief's `lens`, default
# iphone-15). The picture as made is kept as <name>-made.png, the realism pass as <name>-real.png. Lessons L-40.
REALISM = ("Change ONE thing in IMAGE 1: the skin of the person, on the face, neck, chest, arms and hands. Make it real human "
           "skin exactly like IMAGE 2's (the same person photographed up close): individual pores, fine peach fuzz catching the "
           "light, fine lines and creases with shadow in them, the micro-texture of skin at their age, a natural matte finish "
           "with only a faint sheen where skin really shines. Remove every trace of gloss, plastic, wax, airbrush or smoothing. "
           "The person's FACE SHAPE is IMAGE 2's: the same width, roundness and proportions of the face, jaw and cheeks, never "
           "narrower, longer or slimmer (2026-10-28). "
           "Keep EVERYTHING else exactly as IMAGE 1: the expression, the eyes' direction, the clothes, jewellery, the "
           "product and its label, the hands' position, the room, the light direction and shadows, the framing, colours and focus.")


def lens_pass(img, lens):
    from PIL import Image, ImageFilter, ImageChops
    import io
    w, h = img.size
    small = img.resize((lens["width"], round(h * lens["width"] / w)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(lens["soften"]))
    small = ImageChops.add(small, Image.effect_noise(small.size, lens["grain"]).convert("RGB"), scale=1.0, offset=-128)
    buf = io.BytesIO(); small.save(buf, "JPEG", quality=lens["quality"]); buf.seek(0)
    return Image.open(buf).convert("RGB").resize((w, h), Image.LANCZOS)


def finish_people(out, brand, brief, recipe):
    """The realism and lens passes on a made picture with one of our people in it (see above). {} when it does not apply."""
    sw = brief.get("swap_list") if isinstance(brief.get("swap_list"), dict) else None
    if sw is None:
        try:
            sw = json.loads((_lane_run(brand, brief["run"]) / "out" / "swaps.json").read_text())
        except (OSError, ValueError, KeyError):
            sw = {}
    cast = [x for x in sw.get("swaps") or [] if x.get("kind") == "cast" and x.get("ref")]
    if not cast or brief.get("finish") is False or sw.get("words") == "set_on_top":
        return {}
    from PIL import Image
    out = Path(out)
    made = out.with_name(out.stem + "-made.png"); made.write_bytes(out.read_bytes())
    real = out.with_name(out.stem + "-real.png")
    done = {"made": str(made)}
    try:
        _load("video-production/machine/direct_openai.py").generate(REALISM, [made, cast_photo(brand, cast[0]["ref"])], real)
        done["real"] = str(real)
    except Exception as e:                                   # noqa: BLE001  the made picture stands; the miss is recorded
        done["realism_failed"] = str(e)[:300]
        real = made
    lenses = json.loads((HERE / "lenses.json").read_text())
    lens = lenses.get(brief.get("lens") or lenses.get("_default", "iphone-15"))
    img = Image.open(real).convert("RGB")
    if lens:
        img = lens_pass(img, lens); done["lens"] = brief.get("lens") or lenses.get("_default")
    img.resize(Image.open(made).size).save(out)
    return done


ON_SKIN = re.compile(r"(?i)\b(?:on|against|to|across|along|over) (?:his|her|their|the) (?:skin|face|cheek|jaw|jawline|"
                     r"neck|nape|head|scalp|chin|forehead|body|arm|leg|back)\b|\b(?:scrubbing|massaging|brushing|rubbing|"
                     r"applying|in use|being used|using it)\b")


HELD = re.compile(r"(?i)\b(?:hand|hands|held|holds|holding|grip|gripped|fingers|palm)\b")


def real_product(out, brand, brief, plate=None):
    """THE REAL PRODUCT (2026-10-28). A
    product in the picture that is held up, shown or resting (not on skin) is the REAL product: video-production's
    product_paste swaps the kit's real cut-out, at the matching angle, over the drawn one, fingers kept on top, on the
    finished picture and on its word-free plate (the variations start from the plate). A product on skin stays drawn
    from its in-use pictures (the 2026-10-25 approved way). Returns {"pasted", "angle", "overlap"} or {"skipped"} or
    {"held": reason}; a paste that cannot find the product is a flag on the picture, never a stop."""
    # 2026-10-28: the product is drawn from its product casting sheet in the picture call; no photo is pasted over it
    return {"skipped": "drawn from its product casting sheet"}
    sw = swap_list(_lane_run(brand, brief["run"]), brief.get("swap_file")) if brief.get("run") else None
    if not (sw and sw.get("product_in_frame")):
        return {"skipped": "no product in this picture"}
    if ON_SKIN.search(str(sw.get("product_where") or "")):
        return {"skipped": "the product is on skin: drawn from its in-use pictures"}
    kit = REPO / "runs" / "ai-elements" / brand / "products" / str(sw.get("product_kit") or brief.get("product") or "")
    if not (kit / "kit.json").is_file():
        return {"held": f"the real product could not go in: no kit at {kit.relative_to(REPO)}"}
    pp = _load("video-production/machine/product_paste.py")
    what = str(sw.get("product_where") or "the product")[:120]
    # a product that RESTS on something (not held) lies on it with its shadows, never floats (2026-10-28)
    resting = not HELD.search(what)
    done = {}
    for f in [p for p in (out, plate) if p and Path(p).is_file()]:
        try:
            got = pp.run(str(f), kit, out=str(f), what=what, shadow=resting)
        except Exception as e:                               # noqa: BLE001  the made picture stands; the miss is a flag
            got = {"ok": False, "why": [f"{type(e).__name__}: {str(e)[:160]}"]}
        if Path(f) == Path(out):
            done = {"pasted": bool(got.get("ok")) and not got.get("skipped"), "angle": got.get("angle"),
                    "overlap": got.get("overlap")}
            if not got.get("ok"):
                done["held"] = "the real product was not swapped in: " + "; ".join(got.get("why") or ["not found"])
    return done


def _image_words():
    """image-production's words step (set_on_top), loaded as its package so its relative imports work."""
    ip = str(COMP / "image-production")
    if ip not in sys.path:
        sys.path.append(ip)
    from image_production import words
    return words


def set_print(brand, run):
    """The newest kept print of the run's picture set (runs/image-production/<brand>/sets/*/set.json naming the run), or
    None. image-production `picture_sets.py` records them."""
    if not run:
        return None
    base = REPO / "runs" / "image-production" / brand / "sets"
    for sj in sorted(base.glob("*/set.json")) if base.is_dir() else []:
        try:
            d = json.loads(sj.read_text())
        except ValueError:
            continue
        if run in (d.get("runs") or []):
            kept = [p for p in d.get("prints") or [] if str(p.get("note", "")).startswith("kept") and (sj.parent / p["file"]).is_file()]
            if kept:
                return sj.parent / kept[-1]["file"]
    return None


def make_picture(recipe, approved_by, out_dir=None):
    """ONE picture from a complete sheet: the gate first (the cost approval included), then the picture engine's own
    entry point (image_production.plain.generate), which walks the backup ladder. Writes the picture and its recipe under
    runs/image-production/<brand>/prompt-bench/, or under `out_dir` when a caller (image-edit's variations) names one."""
    import time
    r = recipe_of(recipe)
    r = {**r, "sheet": {**(r.get("sheet") or {}), APPROVAL: {"state": FILLED, "value": approved_by, "source": "person"}}}
    r = fill_defaults(r)
    gate(r)
    b = brief_of(r)
    pv = preview("pictures.generate", r, quote=False)
    if not pv["ok"]:
        raise ValueError("the rulebook stops this picture: " + " ".join(f["say"] for f in pv["findings"] if f["level"] == "error"))
    s = pv["send"]
    if (pv.get("fields") or {}).get("words_mode") == "set on top after" and not s.get("type_layer"):
        raise ValueError("the words are set on top, but this brief has no type layer to set them with")
    plain = _image_chain()
    out_dir = Path(out_dir) if out_dir else REPO / "runs" / "image-production" / s["brand"] / "prompt-bench"
    name = f"{b['run']}-{time.strftime('%Y%m%d-%H%M%S')}.png"
    raw = out_dir / "generated" / name
    # the picture engine's own entry point walks the House ladder (GPT Image 2.5, one more try, Seedream 5 Pro, Nano
    # Banana Pro, OpenAI direct last), refuses an incomplete sheet by name and writes the recipe beside its file
    printed = set_print(s["brand"], b.get("run"))
    if printed:
        # THE PICTURE SET (image-production picture_sets, 2026-10-28): the run's scene was built in 3D at true sizes and
        # printed into a real photo in Higgsfield; that print IS the picture (depth, sizes and light programmed, not
        # prompted), so nothing is generated: the words go on top of it
        raw.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        plate_f = raw.with_name(raw.stem + ".plate.png")
        from PIL import Image
        Image.open(printed).convert("RGB").save(plate_f)
        shutil.copy(plate_f, raw)
        got = {"file": str(raw), "rung": "picture-set", "attempts": 0, "words_on_top": {"plate": str(plate_f)},
               "below_criteria": [], "set_print": str(Path(printed).relative_to(REPO))}
    else:
        got = plain.generate(s, raw, recipe={k: v for k, v in r.items() if k != "needs"})
        # GEOMETRY FROM PIXELS, NEVER FROM WORDS (research/diffusion-fundamentals.md rule 1; 2026-10-28): a picture with the product in it and no printed 3D set took its sizes, depth and light
        # from words alone; it is flagged so the set is built, never shipped as if it were
        swl = swap_list(_lane_run(s["brand"], b["run"]), b.get("swap_file")) if b.get("run") else None
        if swl and swl.get("product_in_frame"):
            got["below_criteria"] = list(got.get("below_criteria") or []) + [
                "no 3D set: sizes, depth and light came from words; build the set and print it (image-production picture_sets.py)"]
    out = out_dir / name
    plate = (got.get("words_on_top") or {}).get("plate")
    if plate and Path(plate).is_file() and s.get("type_layer"):
        # the real product goes in on the word-free plate FIRST, then the words are set on top again: pasted after,
        # it covered a headline (2026-10-28, "SALE" vanished under the brush)
        real = real_product(Path(plate), s["brand"], b)
        try:
            wd = _image_words()
            wd.set_on_top(Path(plate), s["type_layer"], out=Path(got["file"]), plate=Path(plate))
        except Exception as e:                               # noqa: BLE001  the made picture stands; the miss is a flag
            real["held"] = f"the words could not be set again over the real product: {str(e)[:160]}"
        plain.to_frame(got["file"], out)
    else:
        plain.to_frame(got["file"], out)
        real = real_product(out, s["brand"], b)
    finished = finish_people(out, s["brand"], b, r)
    if any(s.get("bars") or []):
        put_bars(out, *s["bars"])                            # the swipe's black bars, top and bottom, as it was posted
    out.with_suffix(".recipe.json").write_text(json.dumps({**{k: v for k, v in r.items() if k != "needs"}, "model": pv["model"],
                                                           "made": time.strftime("%Y-%m-%dT%H:%M:%S"), "picture": name,
                                                           "rung": got.get("rung"), "attempts": got.get("attempts"),
                                                           "real_product": real,
                                                           # PSH-8 (outputs never stop): the engine's chosen picture; flags travel on
                                                           "chosen": True, "below_criteria": list(got.get("below_criteria") or [])
                                                           + [f["say"] for f in flags(r)]
                                                           + ([real["held"]] if real.get("held") else [])},
                                                          indent=1, default=str))
    return {"file": str(out), "prompt": pv["prompt"], "model": pv["model"], "rung": got.get("rung"), "attempts": got.get("attempts"),
            "words_on_top": got.get("words_on_top"), "raw": str(got["file"]), "finished": finished,
            "plate": (got.get("words_on_top") or {}).get("plate") or str(got["file"])}


APPROVED_SAYS = ("the approved picture this is a version of: keep its light, grain, colours, framing and every detail "
                 "exactly as it is here, except THE ONE CHANGE.")


def variation_brief(brief, change, approved=None):
    """A variation of an approved picture, as a brief the same builder takes: the approved picture's own brief with ONE
    change from its brief's variation list applied, nothing else touched (2026-10-27).

    `change` keys, each optional:
      words       our words, one per zone ("LINE ONE / LINE TWO"): only the words set on top change
      picture     the one change to the picture, in the brief's words: sent as THE ONE CHANGE, with the approved
                  picture riding along as its own IMAGE so everything else holds
      swap        swap-list rows to put in: a row whose `from` matches an existing row replaces it, else it is added
      stays_drop  'what stays' lines the change undoes
      people      'cast' or 'made-up' (a variation that changes the person drops the cast member's face)
    A change with no `picture`, `swap` or `people` makes no new picture: the approved plate gets the new words."""
    b = json.loads(json.dumps(brief))
    if change.get("words") is not None:
        b["our_copy"] = list(change["words"])
    if change.get("swap") or change.get("stays_drop"):
        sl = b.get("swap_list") if isinstance(b.get("swap_list"), dict) else None
        if sl is None:
            raise ValueError("this picture has no swap list in its recipe; its variations cannot name swaps")
        rows = list(sl.get("swaps") or [])
        for new in change.get("swap") or []:
            at = next((i for i, r in enumerate(rows) if r.get("from") == new.get("from")), None)
            row = {"from": new.get("from") or "", "to": new.get("to") or "", "kind": new.get("kind") or "drawn", "ref": new.get("ref")}
            if at is None:
                rows.append(row)
            else:
                rows[at] = row
        drop = set(change.get("stays_drop") or [])
        sl = {**sl, "swaps": rows, "stays": [x for x in sl.get("stays") or [] if x not in drop]}
        b["swap_list"] = sl
    if change.get("people"):
        b["people"] = change["people"]
        if change["people"] == "made-up" and isinstance(b.get("dials"), dict):
            # the casting dial's line asks for a lookalike of a known figure: wrong for a made-up person
            b["dials"] = {k: x for k, x in b["dials"].items() if k != "cultural_casting"}
    if approved and needs_picture(change):
        # an edit, not a remake: the approved picture is IMAGE 1 and the swaps are only THE ONE CHANGE (the edit rule:
        # the instruction carries the delta, the reference carries everything else). A remake from the swipe moved
        # the eyes, the tag and the background on 2026-10-27, and the judge held it.
        b["base"] = str(approved)
        one = (change.get("picture") or "").strip().rstrip(".")
        rows = "; ".join(f"{r.get('from')} becomes {r.get('to')}" for r in change.get("swap") or [])
        b["swaps"] = "THE ONE CHANGE to IMAGE 1: " + (one or rows) + ". Everything else stays exactly as IMAGE 1 shows it."
    elif change.get("picture"):
        b["note"] = "THE ONE CHANGE: " + change["picture"].strip().rstrip(".") + "."
    return b


def needs_picture(change):
    """True when a variation changes the picture itself; a words-only variation reuses the approved plate."""
    return bool(change.get("picture") or change.get("swap") or change.get("people") or change.get("stays_drop"))


def fill_defaults_clip(recipe, built=None):
    """PSH-2 (defaults first) for a clip: every variable the video run, its brief, the cast and the house files state."""
    r = recipe_of(recipe)
    r = {**r, "kind": "clip"}
    b = brief_of(r)
    built = built or build_clip(b)
    f, st = built["fields"], built["settings"]
    talking = bool(st.get("audio"))
    s = {"brand": _f(f["brand"], "the video run"), "video": _f(f["title"], "the video's brief"),
         "clip_id": _f(f["call"], "the clip plan"), "scene": _f(f["scene_id"], "the clip plan")}
    start = next((i for i in built["inputs"] if i["role"] == "the start picture"), None)
    s["start_picture"] = ({**_f(Path(start["path"]).name, "the video run's chosen picture"), "path": start["path"]}
                          if start and "(not " not in start["path"] else {"state": MISSING})
    end = next((i for i in built["inputs"] if i["role"] == "the end picture"), None)
    s["end_picture"] = ({**_f(Path(end["path"]).name, "the video run's chosen picture"), "path": end["path"]} if end
                        else _na("a talking clip takes no end picture") if talking else _na("the clip ends where it starts"))
    vo = next((i for i in built["inputs"] if i.get("kind") == "audio"), None)
    s["voice"] = (_f(Path(vo["path"]).name, "the locked read") if vo and "(not " not in vo["path"] else
                  {"state": MISSING} if talking else _na("a silent clip"))
    mv = [i["label"] for i in built.get("choices") or [] if i["key"].startswith("motion:") and i["on"]]
    s["motion_refs"] = _f(mv, "the swipe's motion pieces") if mv else _na("this section does not copy the swipe's movement")
    s["frames_match"] = (_na("a talking clip takes no end picture") if talking else
                         _na("the video run chose both pictures") if end else _na("the clip ends where it starts"))
    s["happens"] = _f(f["scene"], "the brief's scene") if str(f.get("scene") or "").strip() else {"state": MISSING}
    emo = str(f.get("emotion") or "").strip()
    s["shot_emotion"] = _f(emo, "the brief's shot") if emo else _na("the brief writes no emotion for this shot")
    # CSH-6 (emotion is visible): with an emotion, the face and gestures must be written
    for k, src in (("face", "face"), ("hands", "gestures")):
        s[k] = (_f(f[src], "the brief's shot") if f.get(src) else {"state": MISSING} if emo
                else _na("the brief writes no emotion for this shot"))
    c0 = controls()
    bank = [e for e in c0["emotions"] if emo and (re.search(r"\b" + re.escape(e["name"].lower()), emo.lower()) or e["id"] in emo.lower())]
    s["emotion_video"] = (_f("; ".join(f"{e['name']}: {e.get('video') or e['what']}" for e in bank), "the emotion bank") if bank
                          else _na("the brief writes no emotion for this shot") if not emo
                          else _na("the brief's feeling has no match in the emotion bank"))
    notes = f.get("acting") or []
    gaps = [n for n in notes if "missing" in str(n.get("status", "")).lower()]
    s["acting"] = ({"state": MISSING, "note": "; ".join(f"{n['shot']} {n['field']}: {n['status']}" for n in gaps)} if gaps
                   else _f("; ".join(f"{n['shot']} {n['field']}: {n['status']}" for n in notes) or "every shot set", "the clip builder")
                   if notes or f.get("has_people") else _na("no people in this clip"))
    ho = f.get("hand_off") or ""
    s["hand_off"] = _f(ho, "the brief's shot") if ho in ("cut", "continuous", "action", "match", "whip") else _na("the last clip of the video")
    cam = b.get("camera_move") or f.get("camera") or "still"
    s["camera"] = _f(cam, "person" if b.get("camera_move") else "the brief's shot")
    s["look"] = _f(f["style"], "the video's look") if str(f.get("style") or "").strip() else {"state": MISSING}
    s["ends_on"] = _f(f["ends_on"], "the brief's last shot") if f.get("ends_on") else _na("the brief sets no end for this take")
    s["who"] = _f(f["who"], "the cast") if f.get("who") else _na("no people in this clip")
    lv = int(f.get("spice") or 2)
    nobody = not f.get("has_people") and not f.get("who")
    s["marks"] = (_na("no people in this clip") if nobody else _na("no character file") if not f.get("marks")
                  else _na("spice level 1 leaves marks out") if lv < 2 else _f(f["marks"], "the character file"))
    s["own_gestures"] = (_na("no people in this clip") if nobody else _na("no character file") if not f.get("own_gestures")
                         else _na("the shot names its own gestures") if f.get("gestures")
                         else _na("spice level 1 or 2 leaves them out") if lv < 3 else _f(f["own_gestures"], "the character file"))
    s["duration"] = _f(str(st["duration"]), "the read's length")
    s["resolution"] = _f(st["resolution"], "the house setting")
    s["shape"] = _f("9:16", "the house frame")
    s["spice"] = _f(str(f.get("spice") or 2), "person" if b.get("spice") is not None else "the video's spice level")
    s["realism"] = _f(f["realism"], "the realism index") if f.get("realism") else _na("the format has no realism rows")
    s["no_subtitles"] = _f("yes" if "No subtitles" in built["prompt"] else "no", "the clip prompt")
    s["no_music"] = _f("yes" if "No background music" in built["prompt"] else "no", "the clip prompt")
    line = str(f.get("line") or "").strip().rstrip(",.")
    s["line_not_typed"] = (_na("a silent clip") if not talking else
                           _f("no" if line and line.lower() in built["prompt"].lower() else "yes", "the clip prompt"))
    c = controls()
    pr, aims = c["presets"][0], {}
    try:
        import importlib.util as _u
        sp_ = _u.spec_from_file_location("pv_cc", COMP / "creative-controls" / "creative_controls.py")
        cc = _u.module_from_spec(sp_)
        sp_.loader.exec_module(cc)
        pr, aims = cc.target("maxed", f["brand"], "video")
    except Exception:                                        # noqa: BLE001
        pass
    s["preset"] = _f(pr["id"], "the house preset (the video brief names none)")
    s["emotion"] = (_f(b["emotions"], "person") if b.get("emotions") else _f([e["id"] for e in bank], "the emotion bank") if bank
                    else _na("the brief writes no emotion for this shot") if not emo else _na("the brief's feeling has no match in the emotion bank"))
    s["techniques"] = _f(b["techniques"], "person") if b.get("techniques") else _na("the scene copies the swipe's own moves")
    for x in c["dials"]:
        if "video" not in x["media"]:
            continue
        k = x["id"]
        if (b.get("dials") or {}).get(k) is not None:
            s["dial." + k] = _f(int(b["dials"][k]), "person")
        elif k in (f.get("creative_controls") or {}):
            control = f["creative_controls"][k]
            s["dial." + k] = ({**_na("not used in a clip"), "evidence": control["not_applicable"]} if control.get("not_applicable")
                              else _f(control["level"], "the hook matrix: " + control.get("evidence", "")))
        elif k in aims:
            s["dial." + k] = _f(aims[k], "the house preset")
        else:
            s["dial." + k] = _na("the video brief sets no level for this dial")
    for g in c["guards"]:
        s["guard." + g["id"]] = _f("on", "always on")
    s["backups"] = _f([plain_rung(x) for x in _ladder("clips.seedance")], "the Model House")
    s["run_label"] = _f(f["video"], "the video run")
    s[APPROVAL] = {"state": MISSING}
    for k, e in (r.get("sheet") or {}).items():
        if e and (e.get("source") == "person" or e.get("state") == NA and e.get("source") != "filled from the brief"):
            s[k] = e
    out = {**r, "sheet": s}
    out["needs"] = [x["name"] for x in validate(out)]
    return out


def make_clip(recipe, approved_by, dry_run=False):
    """ONE clip from a complete clip sheet (CSH-5 (no spend unpressed)): the gate first, then the clip chain's own take
    loop (clips_run.make_clip: Seedance takes, then the Kling backup, scored, the best kept and flagged) with exactly the
    previewed prompt. `dry_run` prints the Seedance request and spends nothing."""
    import time
    r = recipe_of(recipe)
    r = {**r, "kind": "clip", "sheet": {**(r.get("sheet") or {}), APPROVAL: {"state": FILLED, "value": approved_by, "source": "person"}}}
    r = fill_defaults_clip(r)
    gate(r)
    pv = preview("clips.seedance", r, quote=False)
    if not pv["ok"]:
        raise ValueError("Stopped before any spend: " + " ".join(f["say"] for f in pv["findings"] if f["level"] == "error"))
    s = pv["send"]
    sd = _load("video-production/machine/seedance.py")
    cr = _clip_chain()
    run = Path(s["run"])
    if (run / "opening.json").is_file():
        _load("video-production/machine/hook_workflow.py").require_clip(run, REPO)
    out_dir = run / "prompt-bench"
    name = f"{s['call']['id']}-{time.strftime('%Y%m%d-%H%M%S')}.mp4"
    if dry_run:                                               # the request as Seedance would get it, nothing spent
        got = (sd.talk(s["line"], s["start"], s["voice"], out_dir / name, dry_run=True, prompt=s["prompt"], videos=s["videos"])
               if s["voice"] else sd.motion(s["prompt"], s["start"], out_dir / name, seconds=pv["settings"]["duration"],
                                            end_still=s["end"], dry_run=True, whole=True, videos=s["videos"]))
        return {**got, "attempts": [], "prompt": pv["prompt"]}
    if (run / "opening.json").is_file():
        # Keep the board's exact clip-level changes as dependencies of this take.
        prior = json.loads((run / "clip-inputs.json").read_text()) if (run / "clip-inputs.json").is_file() else {}
        current = brief_of(r)
        keys = ("scene", "face", "gestures", "camera_move", "style", "spice", "movement_id", "skip", "dials", "emotions", "techniques")
        saved = {**prior, **{k: current[k] for k in keys if k in current}}
        if saved != prior:
            (run / "clip-inputs.json").write_text(json.dumps(saved, indent=2))
    # the clip chain's own take loop: Seedance takes up to the configured number, then the Kling backup, each scored,
    # the best kept and flagged below_criteria (PSH-8 (outputs never stop)); the prompt is sent exactly as previewed
    doc = json.loads((run / "plan.json").read_text())
    got = cr.make_clip(run, s["call"], prompt=s["prompt"], cfg=cr.route_cfg(None, cr.format_of(run, doc)))
    if got.get("file"):
        Path(got["file"]).with_suffix(".recipe.json").write_text(json.dumps(
            {**{k: v for k, v in r.items() if k != "needs"}, "model": got.get("rung"), "made": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "chosen": True, "attempts": got.get("attempts"), "below_criteria": got.get("below_criteria") or []}, indent=1, default=str))
    return {**got, "prompt": pv["prompt"]}


def preview(job, brief, quote=True):
    """The whole preflight for one job. Raises KeyError for a job with no builder and ValueError for a brief that cannot be built."""
    house = _house().model(job)
    rid, door = house.get("registry_id"), house.get("door")
    vendor = house.get("model") or house.get("id")
    recipe = filled = None
    if job.startswith("pictures."):
        recipe = recipe_of(brief)
        filled = fill_defaults(recipe)
        brief = full_brief(filled)
    elif job == "clips.seedance":
        recipe = {**recipe_of(brief), "kind": "clip"}
        brief = brief_of(recipe)
    built = builder_for(job)(brief)
    if job == "clips.seedance":
        filled = fill_defaults_clip(recipe, dict(built))
    plain = built.pop("plain", None) or _image_chain()
    params = dict(built.pop("params", None) or {})
    if "settings" not in built:                              # a picture builder gives the prompt; its settings are the job's
        built["settings"], entry = _picture_settings(job, door, rid, vendor, plain)
        params = dict(entry.get("params") or {})
    settings = built["settings"]
    try:
        has_rules = IR.load(rid) is not None
    except KeyError:
        has_rules = False
    findings = []
    if has_rules:
        imgs = [{"path": i["path"]} for i in built["inputs"] if i.get("kind", "image") == "image"]
        kw = dict(door=door, resolution=settings.get("resolution"), variant=settings.get("variant"), quality=settings.get("quality"),
                  aspect=settings.get("aspect", "9:16"))
        if built["medium"] == "video":
            kw.update(duration=settings.get("duration"), audio=sum(1 for i in built["inputs"] if i.get("kind") == "audio"),
                      videos=sum(1 for i in built["inputs"] if i.get("kind") == "video"))
        else:
            kw["size"] = settings.get("size")
        findings = IR.check(rid, built["prompt"], imgs, **kw)
    else:
        findings = [{"id": "no-rulebook", "level": "warn", "say": f"{rid} has no rulebook on file yet, so nothing was checked."}]
    if settings.get("route_mismatch"):
        findings.append({"id": "route-mismatch", "level": "warn", "say": "The picture engine's route row and the Model House name "
                         "different doors right now; the preview uses the House's door and its rulebook defaults."})
        settings = {k: v for k, v in settings.items() if k != "route_mismatch"}
    missing = [i for i in built["inputs"] if "(not " in str(i.get("path"))]
    for i in missing:
        findings.append({"id": "input-missing", "level": "warn", "say": f"input {i['n']} ({i['role']}) is {i['path']}: it must exist before anything is sent."})
    cost = _quote(built, job, door, settings.get("vendor_model") or vendor, params or {k: settings.get(k) for k in ("variant", "quality", "resolution")},
                  settings.get("aspect", "9:16"), plain) if quote else {"credits": None, "say": "quote skipped"}
    if built.get("estimate_usd") is not None:
        cost["estimate_usd"] = built["estimate_usd"]
    sheet = built.get("sheet")                              # a builder whose job has no recipe sheet hands its own checklist
    if filled is not None:
        sheet = {**sheet_view(filled), "needs": filled["needs"], "flags": flags(filled),
                 "recipe": {k: v for k, v in filled.items() if k != "needs"}}
        for p in validate(filled, for_make=False):          # PSH-1 (inputs all set): the input gate is hard
            findings.append({"id": "sheet", "level": "error", "say": p["say"], "var": p["id"]})
        for p in sheet["flags"]:                             # PSH-8 (outputs never stop): flags only
            findings.append({"id": "below-criteria", "level": "warn", "say": p["say"]})
    elif sheet:
        for r in sheet.get("rows") or []:                    # the builder's checklist holds the same way: a missing input stops
            if r.get("state") == "missing":
                findings.append({"id": "sheet", "level": "error", "say": r.get("problem") or (r["name"] + ": missing"), "var": r["id"]})
    errors = [f for f in findings if f["level"] == "error"]
    return {"sheet": sheet, "job": job, "model": rid, "vendor_model": settings.get("vendor_model") or vendor, "door": door, "prompt": built["prompt"],
            "words": len(built["prompt"].split()), "chars": len(built["prompt"]), "inputs": built["inputs"],
            "settings": {k: v for k, v in settings.items() if k != "vendor_model"}, "fields": built.get("fields", {}),
            "findings": findings, "errors": len(errors), "warnings": len(findings) - len(errors), "ok": not errors,
            "cost": cost, "ladder": _ladder(job), "notes": built.get("notes", []), "send": built.get("send"), "choices": built.get("choices"), "calls": built.get("calls")}


for _j in ("pictures.generate", "pictures.edit", "pictures.backup", "pictures.object"):
    BUILDERS[_j] = (lambda b, _j=_j: build_picture(b, _j))
BUILDERS["clips.seedance"] = build_clip


def fields_of(job):
    return CLIP_FIELDS if job.startswith("clips.") else PICTURE_FIELDS


def render_text(r):
    L = [f"{r['job']} → {r['model']} through {r['door']}   [{'OK' if r['ok'] else 'STOPPED: ' + str(r['errors']) + ' error(s)'}]", "",
         "PROMPT", r["prompt"], "", "INPUTS"]
    L += [f"  {i.get('kind', 'image').capitalize()} {i['n']}: {i['role']}  ({i['path']})" for i in r["inputs"]] or ["  none"]
    L += ["", "SETTINGS  " + ", ".join(f"{k} {v}" for k, v in r["settings"].items() if v is not None), "", "RULEBOOK"]
    L += [f"  {f['level'].upper():5} {f['say']}" for f in r["findings"]] or ["  clean"]
    L += ["", "COST  " + r["cost"]["say"] + (f"  (estimate ${r['cost']['estimate_usd']})" if r["cost"].get("estimate_usd") is not None else ""), "", "IF IT FAILS"]
    L += ["  " + " → ".join(x["rung"] + (f" ({x['model']} · {x['door']})" if x.get("model") else (" (" + x["say"] + ")" if x.get("say") else "")) for x in r["ladder"])]
    return "\n".join(L)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    if a and a[0] == "--fields":
        print(json.dumps(fields_of(a[1]), indent=1))
        return 0
    if len(a) >= 2 and a[0] in ("check", "make"):
        rec = json.loads(Path(a[1]).read_text())
        try:
            filled = fill_defaults(rec)
        except (KeyError, ValueError, OSError) as e:
            print(f"CANNOT READ {a[1]}: {e}", file=sys.stderr)
            return 2
        probs = validate({**filled, "sheet": {**filled["sheet"], **({APPROVAL: rec["sheet"][APPROVAL]} if (rec.get("sheet") or {}).get(APPROVAL) else {})}})
        if a[0] == "check":
            print("COMPLETE" if not probs else "NOT COMPLETE")
            for p in probs:
                print("  " + p["say"])
            return 1 if probs else 0
        appr = ((rec.get("sheet") or {}).get(APPROVAL) or {}).get("value")
        if probs or not appr:
            print("REFUSED: " + (" ".join(p["say"] for p in probs) or "no cost approval in the recipe"), file=sys.stderr)
            return 1
        print(json.dumps(make_picture(rec, appr), indent=1))
        return 0
    if len(a) < 2:
        print(__doc__)
        return 2
    job, src = a[0], a[1]
    try:
        brief = json.loads(src) if src.lstrip().startswith("{") else json.loads(Path(src).read_text())
        brief = brief.get("brief", brief) if isinstance(brief.get("brief"), dict) else brief     # a saved recipe replays as is
        r = preview(job, brief, quote="--no-quote" not in a)
    except (KeyError, ValueError, OSError) as e:
        print(f"CANNOT BUILD {job}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=1) if as_json else render_text(r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
