"""THE EMAIL PICTURE CHAIN: every made email picture goes the way picture ads go (2026-10-29).

the owner asked on 2026-10-28 whether the email chain calls on image production. It did, the old way: design/line.py sent
each picture to the image engine's own prompt and judge, and simple_email.py called video-production's OpenAI door
straight. Picture ads had moved on (tools/image-production/CLAUDE.md, "Every picture: a 3D set, printed, then the
words"). Now every email picture both doors make takes the same three steps:

1. THE PRODUCT FROM ITS CASTING SHEET. A picture that shows one of the brand's products names its kit
   (runs/ai-elements/<brand>/products/<kit>/), and the kit's product casting sheet goes in as the reference
   (image-production `plain.product` puts it first). A product with no casting sheet is held, never drawn from words.
2. AT REST: A 3D SET, PRINTED. A product shown at rest (on a plinth, a shelf, a sink edge: not in a hand, not on skin)
   is a scene built in Higgsfield 3D Jutsu at true size and printed with the casting sheet (image-production
   `picture_sets.py`). The kept print IS the picture: nothing is generated. With no kept print yet, the picture is held
   and its set request is written beside the run (media/sets/<label>.json) for the session that builds it.
   Anything else (no product, or the product in use) is ONE plain picture call (image-production `plain.make`), the
   casting sheet in, the email's concept and culture as its recipe.
3. THE WORDS ON TOP. Words a picture brief quotes are lifted out of what the model is told (it keeps their space clear
   and draws no writing but the product's own label) and set over the finished picture by image-production's word
   setter, so they are letter-exact.

The email line's own concept step (EMAIL-LINE.md step 1b) is kept: the job card's concept and culture ride in the
picture's recipe and its prompt. Every picture is made 9:16 and cut to the email's frame from the centre 4:5 safe zone.

    python3 design/picture_chain.py <brand> <run folder>                     every picture's route, nothing spent
    python3 design/picture_chain.py <brand> <run folder> --make N --out DIR   picture N made into DIR; the email untouched
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
IMAGE_PRODUCTION = REPO / "tools" / "image-production"

# A product in a hand, on skin or being used is drawn from its casting sheet; anything else of ours in frame is at rest
IN_USE = re.compile(r"(?i)\b(held|holds?|holding|grip\w*|in (?:his|her|a|the|one|their) (?:real )?hands?|hand holding|"
                    r"squeez\w*|appl(?:y|ying|ied)|lather\w*|scrub(?:s|bing|bed)?|brush(?:es|ing)|on (?:his|her|the) "
                    r"(?:skin|face|cheek|jaw|neck|arm|leg)|in the shower|under (?:the )?(?:running )?water|in use)\b")
QUOTED = re.compile(r'["“]([^"“”]{1,80})["”]')
# "exact words:" / "reading" / "that says" before a quote is about the words, so it goes with them
WORDS_LEAD = re.compile(r'(?i)(?:,?\s*(?:its |the |with the )?(?:exact )?(?:words?|text|reading|that says|saying|labelled)\s*:?\s*)$')
SIDES = (("left", re.compile(r"(?i)\bleft\b")), ("right", re.compile(r"(?i)\bright\b")))
CLEAR = "a clean, empty space where words are set on top afterwards"
RULES = ("No words, letters, numbers or logos anywhere in the picture except the product's own printed label: every word "
         "this picture carries is set on top afterwards, so the spaces the picture names for words stay clean and plain.",
         "This is a picture for an email: it is cut to the centre 4:5 safe zone, so everything that matters sits there.")


def _image_production():
    if str(IMAGE_PRODUCTION) not in sys.path:
        sys.path.append(str(IMAGE_PRODUCTION))      # appended, never ahead of this machine
    from image_production import plain, product3d, words
    return plain, product3d, words


def _picture_sets():
    """image-production's picture_sets.py, read by path (its command file), or None when this checkout lacks it."""
    f = IMAGE_PRODUCTION / "picture_sets.py"
    if not f.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("email_picture_sets", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kits(brand):
    """{kit slug: [the words that name it]} for every product kit the brand has."""
    out = {}
    for kj in sorted((REPO / "runs" / "ai-elements" / brand / "products").glob("*/kit.json")):
        try:
            k = json.loads(kj.read_text())
        except ValueError:
            continue
        slug = kj.parent.name
        out[slug] = sorted({slug, *[str(a).lower() for a in k.get("aliases") or []]}, key=len, reverse=True)
    return out


def products_in(brand, slot, text):
    """The kits a picture shows: the slot's named product first, then every kit whose name the brief says, as a word."""
    found = []
    named = str(slot.get("product") or "").lower()
    ks = kits(brand)
    # the look's short key ("body-scrub") is the one kit whose name ends on it ("brilliance-body-scrub") (2026-10-30)
    tail = [slug for slug in ks if named and slug.endswith("-" + named)]
    for slug, names in ks.items():
        if named and (named == slug or named in names or slug.startswith(named) or named.startswith(slug)
                      or (tail == [slug])):
            found.append(slug)
        elif any(re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", text, re.I) for n in names):
            found.append(slug)
    return found


def _is_words(before, quote, joined):
    """A quote is words to set when the brief says so ("exact words:", "reading"), when it is joined by "and" or a comma
    to a quote that was, or when it is written in capitals. A quoted word inside a sentence ("the "real" one") is not."""
    letters = [c for c in quote if c.isalpha()]
    return bool(WORDS_LEAD.search(before) or joined or (letters and sum(c.isupper() for c in letters) >= 0.6 * len(letters)))


def lift_words(text):
    """(the brief with its words to set taken out, [{"text", "side"}]). A line's side is the panel (LEFT / RIGHT) its
    sentence names last before it, else the centre."""
    words, out, last, lifted = [], [], 0, False
    for m in QUOTED.finditer(text):
        before = text[last:m.start()]
        joined = lifted and re.fullmatch(r"\s*(?:,|and|,\s*and)\s*", before) is not None
        if not _is_words(before, m.group(1), joined):
            out.append(text[last:m.end()])
            last, lifted = m.end(), False
            continue
        start = max(text.rfind(". ", 0, m.start()), 0)
        hits = [(h.start(), name) for name, rx in SIDES for h in rx.finditer(text, start, m.start())]
        side = max(hits)[1] if hits else "centre"
        words.append({"text": m.group(1).strip(), "side": side})
        lead = WORDS_LEAD.search(before)
        if joined:
            out.append("")
        else:
            out.append((before[:lead.start()] if lead else before) + " (" + CLEAR + ")")
        last, lifted = m.end(), True
    out.append(text[last:])
    return re.sub(r"[ \t]+", " ", "".join(out)).strip(), words


def at_rest(text, products):
    return bool(products) and not IN_USE.search(text)


def find_set(brand, label):
    """The newest kept print of a 3D set whose set.json names this picture's label, or None
    (runs/image-production/<brand>/sets/*/set.json, the record picture_sets.py keeps)."""
    base = REPO / "runs" / "image-production" / brand / "sets"
    for sj in sorted(base.glob("*/set.json")) if base.is_dir() else []:
        try:
            d = json.loads(sj.read_text())
        except ValueError:
            continue
        if label in (d.get("runs") or []):
            kept = [p for p in d.get("prints") or [] if str(p.get("note", "")).startswith("kept") and (sj.parent / p["file"]).is_file()]
            if kept:
                return sj.parent / kept[-1]["file"]
    return None


# the concept is the email's world, which names the email's other pictures too: drawn, one picture holds them all
CONCEPT_MARK = "(the whole email's world, for mood only; never draw it: draw only THE PICTURE) "


def recipe(slot, concept, culture, direction, products, words):
    """The picture's variable sheet (image-production's flat recipe): every variable filled or not applicable with why."""
    na = lambda why: {"na": why}
    return {"concept": (CONCEPT_MARK + concept) if concept else na("this email's copy carries no concept card"),
            "culture": culture or na("this email's copy carries no culture line"),
            "picture": direction, "use": slot.get("use") or "story",
            "products": products or na("no product of the brand's is in this picture"),
            "words": [w["text"] for w in words] or na("no words sit on this picture"),
            "words_how": "set on top afterwards by the word setter; the model draws none",
            "frame": "9:16, cut to the centre 4:5 safe zone for the email"}


def plan(brand, slot, label, concept=None, culture=None):
    """What the chain will do with one picture slot, built without any call. `slot` carries `todo` and/or `brief`
    (what the picture shows), `use` and optionally `product`."""
    said = " ".join(x for x in (slot.get("todo"), slot.get("brief"), slot.get("prompt")) if x).strip()
    direction, words = lift_words(said)
    products = products_in(brand, slot, said)
    plain, product3d, _ = _image_production()
    sheets, missing = {}, []
    named = str(slot.get("product") or "").strip()
    if named and not products:
        missing.append(named)                       # named, but no kit: no casting sheet to draw it from
    for p in products:
        kit = product3d.find_kit(brand, p)
        k = json.loads((kit / "kit.json").read_text()) if kit else {}
        sheet = kit / str((k.get("sheet") or {}).get("file") or "model/product-sheet.png") if kit else None
        if sheet and sheet.is_file():
            sheets[p] = str(sheet.relative_to(REPO))
        else:
            missing.append(p)
    route = "held" if missing else "set" if at_rest(direction, products) else "plain"   # the scene, never its words
    out = {"label": label, "route": route, "products": products, "sheets": sheets, "words": words,
           "direction": direction, "concept": concept, "culture": culture, "use": slot.get("use") or "story",
           "recipe": recipe(slot, concept, culture, direction, products, words)}
    if missing:
        out["held"] = "no product casting sheet for " + ", ".join(missing) + ": a product is never drawn from words"
    if route == "set":
        printed = find_set(brand, label)
        out["set_print"] = str(printed.relative_to(REPO)) if printed else None
        if not printed:
            out["held"] = ("its product rests in the scene, so it is a 3D set printed with the casting sheet; no kept print "
                           "names this picture yet (set request: media/sets/%s.json)" % label)
    if route == "plain":
        pl = plain.plan(brand, direction, products=products, sections=_sections(concept, culture), rules_lines=RULES)
        out["prompt"], out["references"] = pl["prompt"], [str(Path(r).relative_to(REPO)) if str(r).startswith(str(REPO)) else str(r) for r in pl["refs"]]
    return out


def plain_text(text):
    """The concept or culture line without markdown marks (** and `): it quotes the culture map as written, and a mark in
    a picture prompt is drawn (model-inputs refuses it; brand-a nov-05/06/07, 2026-10-30)."""
    return re.sub(r"\*\*|`", "", text) if text else text


def _sections(concept, culture):
    """The email's concept (step 1b) as the world this picture belongs to, its own words to set lifted out of it: the
    concept quotes the email's headlines, and a quote in a prompt is a quote drawn."""
    concept = lift_words(concept)[0] if concept else ""
    body = "\n".join(x for x in (concept, ("Borrowed from: " + culture) if culture else "") if x)
    return [("THE EMAIL'S CONCEPT (the world this picture belongs to; draw only THE PICTURE, one photograph: never the "
             "email's other parts, no message cards, screens, buttons or labels, no product shot from another section; "
             "brand-b nov-05, 2026-10-30)", body)] if body else []


def set_request(brand, run_dir, p):
    """The 3D set a held at-rest picture needs, written to media/sets/<label>.json: what the session building it in
    Higgsfield 3D Jutsu needs, and the print's words built the way picture_sets builds them."""
    _, product3d, _ = _image_production()
    items = []
    for slug in p["products"]:
        kit = product3d.find_kit(brand, slug)
        k = json.loads((kit / "kit.json").read_text())
        jutsu = kit / "model" / "sheet" / "jutsu" / "angles.json"
        proj = (json.loads(jutsu.read_text()).get("project") or {}) if jutsu.is_file() else {}
        items.append({"kit": slug, "sheet": p["sheets"].get(slug), "size_cm": k.get("size_cm"),
                      "jutsu_project": proj.get("id"), "rests": (k.get("behaviour") or {}).get("rests"),
                      "never_show": (k.get("behaviour") or {}).get("never_show")})
    ps = _picture_sets()
    req = {"set": p["label"], "brand": brand, "scene": p["direction"], "concept": p["concept"], "culture": p["culture"],
           "products": items, "words_space": [w["text"] for w in p["words"]],
           "frame": "9:16 at 2k, the centre 4:5 holds the scene; headroom left clear where the words go",
           "print_prompt_maker": "image-production picture_sets.print_prompt" if ps else None,
           "then": ("picture_sets.py put %s %s --render R --print P --note 'kept: ...', and add '%s' to that set.json's "
                    "runs; the email's picture step then takes the print as the picture" % (brand, p["label"], p["label"]))}
    f = Path(run_dir) / "media" / "sets" / (p["label"] + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(req, indent=1, ensure_ascii=False) + "\n")
    return f


MAKEABLE = {"9:16": 9 / 16, "3:4": 3 / 4, "4:5": 4 / 5, "1:1": 1.0, "3:2": 3 / 2, "16:9": 16 / 9}   # every picture model's shapes


def aspect_for(ratio):
    """The shape the picture models make that is nearest a box's (width / height): a house picture is made at its
    box's shape (LD-101 (Brand-B house look)), so nothing is cut to fit."""
    import math
    return min(MAKEABLE, key=lambda k: abs(math.log(MAKEABLE[k] / float(ratio))))


def to_frame(src, out, ratio=0.8):
    """Cut a 9:16 picture to the email's frame (width / height = `ratio`) from its centre, the safe zone."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w / h < ratio:
        nh = round(w / ratio)
        top = (h - nh) // 2
        im = im.crop((0, top, w, top + nh))
    else:
        nw = round(h * ratio)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return Path(out)


def word_layer(words, tokens=None):
    """The type layer for the lifted words: one column per side the brief named (left / right, else the centre), each
    side's first line as its title in the display serif, the rest as labels under it, inside the frame's top half."""
    tokens = tokens or {}
    ink = tokens.get("ink") or "#FFFFFF"
    accent = tokens.get("accent") or tokens.get("eyebrow") or ink
    sides = [s for s in ("left", "centre", "right") if any(w["side"] == s for w in words)]
    span = {"centre": (6, 94)} if sides == ["centre"] else {"left": (4, 48), "right": (52, 96), "centre": (6, 94)}
    els = []
    for side in sides:
        top, first = 6.0, True
        for w in [w for w in words if w["side"] == side]:
            h = 16.0 if first else 5.0
            els.append({"element": "%s-%d" % (side, len(els)), "text": w["text"], "top_pct": top, "height_pct": h,
                        "max_lines": 3 if first else 1, "left_pct": span[side][0], "right_pct": span[side][1],
                        "align": "center", "cap_pct": 4.4 if first else 1.9, "color": ink if first else accent,
                        "font": "high-contrast-serif" if first else "geometric-sans", "case": "upper",
                        "tracking": 0 if first else 25, "file": "all"})
            top, first = top + h + 1.0, False
    return {"elements": els}


def cast_refs(brand, direction):
    """The brand's own person for a picture with someone in it, as (references, ref_says): the face is kept, the pose is
    the picture's. Nothing found = no reference, never a stop (the mount may be away)."""
    _image_production()                             # puts the engine on the path
    from image_production import assets as AS
    try:
        rows, _ = AS.pick(brand, direction, want_people=True, limit=1)
    except Exception:                               # a slow or absent mount never stops a run
        return [], {}
    refs = [Path(r["path"]) for r in rows if r.get("path") and Path(r["path"]).is_file()]
    return refs, {i: f"IMAGE {i + 1} is a real person from the brand's cast: keep the face, take the pose from the words."
                  for i in range(len(refs))}


def make(brand, slot, label, out, concept=None, culture=None, ratio=0.8, tokens=None, run_dir=None, people=False, aspect="9:16"):
    """One email picture through the chain into `out` (a .png), generated at `aspect` (a house email passes its box's,
    aspect_for(ratio); every other email 9:16, as before). Returns the plan with what happened: `file` (the
    finished picture), `plate` (before the words), `made_by`; or `held` with why, and no file."""
    concept, culture = plain_text(concept), plain_text(culture)
    p = plan(brand, slot, label, concept, culture)
    out = Path(out)
    if p.get("held"):
        if p["route"] == "set" and run_dir:
            p["set_request"] = str(set_request(brand, run_dir, p))
        return p
    plain, _, words = _image_production()
    if aspect != "9:16":                                # the recipe says the shape the picture is made at
        p["recipe"]["frame"] = "%s, the box's own shape: nothing is cut" % aspect
    raw = out.with_name(out.stem + ".9x16.png")
    if p["route"] == "set":
        import shutil
        raw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / p["set_print"], raw)
        p["made_by"] = "picture-set"                    # the print is the picture: nothing generated
    else:
        refs, says = cast_refs(brand, p["direction"]) if people else ([], {})
        cast = {"references": refs, "ref_says": says} if refs else {}
        rec = plain.make(brand, p["direction"], raw, products=p["products"], aspect=aspect, recipe=p["recipe"],
                         sections=_sections(concept, culture), rules_lines=RULES, **cast)
        p.update({"made_by": rec.get("made_by") or rec.get("model"), "prompt": rec["prompt"], "references": rec["refs"]})
    to_frame(raw, out, ratio)
    p["file"] = str(out)
    if p["words"]:
        plate = out.with_name(out.stem + ".plate.png")
        got = words.set_on_top(out, word_layer(p["words"], tokens), out=out, plate=plate)
        p["plate"], p["words_set"] = got.get("plate"), got
        if not got.get("ok"):
            p["words_missing"] = "the words could not be set on top: " + "; ".join(got.get("notes") or [])
    return p


def _rel(x):
    """A stored path is repo-relative (builder card rule 4), never this machine's."""
    s = str(x)
    return s[len(str(REPO)) + 1:] if s.startswith(str(REPO) + "/") else s


def note_record(run_dir, rel, got):
    """Write how the chain made (or held) the picture into its record.json (picture_record.keep's file): the route, the
    casting sheets, the prompt as sent, the words set on top, the set print or set request. Returns `rel`."""
    f = Path(run_dir) / rel
    if not f.is_file():
        return rel
    rec = json.loads(f.read_text())
    rec["chain"] = {"route": got.get("route"), "products": got.get("products"), "sheets": got.get("sheets"),
                    "words_on_top": [w["text"] for w in got.get("words") or []], "made_by": got.get("made_by"),
                    "set_print": got.get("set_print"), "set_request": _rel(got["set_request"]) if got.get("set_request") else None,
                    "plate": _rel(got["plate"]) if got.get("plate") else None, "words_missing": got.get("words_missing")}
    if got.get("prompt"):
        rec["prompt"] = got["prompt"]
    if got.get("references"):
        rec["chain"]["references"] = [_rel(r) for r in got["references"]]
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    return rel


def slots_of(spec):
    """Every picture slot in an email's design spec, in order: (section index, the slot dict). A slot is a picture
    still to make (`todo`) or one made before (`source: made`, its brief kept)."""
    got = []

    def walk(x, i):
        if isinstance(x, dict):
            if "todo" in x or (x.get("source") == "made" and (x.get("brief") or x.get("alt"))):
                got.append((i, x))
            for v in list(x.values()):
                walk(v, i)
        elif isinstance(x, list):
            for v in x:
                walk(v, i)
    for i, s in enumerate(spec.get("sections") or []):
        walk(s, i)
    return got


def job_card(run_dir):
    f = Path(run_dir) / "design" / "job.json"
    j = json.loads(f.read_text()) if f.is_file() else {}
    return j.get("concept"), j.get("culture")


def as_slot(x):
    """A made slot as the chain reads it: its brief is what it shows (its alt when it kept no brief)."""
    return {"todo": x.get("todo") or ("" if x.get("brief") else x.get("alt")), "brief": x.get("brief") or "",
            "use": x.get("use"), "product": x.get("product")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("brand")
    ap.add_argument("run")
    ap.add_argument("--make", type=int, help="make this picture (1 = the first) into --out; the email is not changed")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    run_dir = Path(a.run).resolve()
    spec = json.loads((run_dir / "design" / "email.json").read_text())
    concept, culture = job_card(run_dir)
    sys.path.insert(0, str(HERE))
    import look as L
    tokens = (L.load(a.brand, run_dir).get("tokens") or {})
    for n, (i, x) in enumerate(slots_of(spec), 1):
        label = "%s-n%d" % (run_dir.name, n)
        if a.make and n != a.make:
            continue
        if a.make:
            got = make(a.brand, as_slot(x), label, Path(a.out) / (label + ".png"), concept, culture,
                       ratio=1.0 if x.get("use") == "gift" else 0.8, tokens=tokens, run_dir=run_dir)
        else:
            got = plan(a.brand, as_slot(x), label, concept, culture)
        print(json.dumps({"picture": n, "section": i, **{k: v for k, v in got.items() if k != "recipe"}}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
