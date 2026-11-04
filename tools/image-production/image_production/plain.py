"""The plain picture: one call, the way the owner makes them in Higgsfield.

    from image_production import plain
    plain.make(brand, text, out, references=[<a swipe or a scene's plate>], products=["widget"], aspect="4:5")

the owner, 2026-10-25, on the carousels made this way: "there's a lot of control that I think is messing stuff up" and
then "literally perfect. so much cleaner ... literally 1000000x better than any flex implementation we had in the
past ... not just statics but also video scenes as well". So statics and video scene stills both come through here.

What goes in, and nothing else:
- IMAGE 1 is the caller's reference (the swipe, the slide, the scene's plate), when there is one;
- each product's own real pictures from its kit: `kit.json` `shown.refs` (how it looks on its own: a counter, held up
  to the camera, a product tile) and `in_use.refs` (the side the camera sees in use, a real hold), else the kit's real
  front photo;
- the caller's own lines (what the picture shows, its exact words), then each product's `shown.line`, `in_use.line`
  and its real size (`size_cm`), so it is never drawn small (the owner, 2026-10-25: "pill bottle looks a bit small");
- the people: with a reference, LOOKALIKES of whoever is in it (the owner, 2026-10-25: "you removed that bald guy, he's
  part of what makes it funny. you should just do lookalikes of whoever is in the swipe"), never the real person;
  without one, made-up people.
One call to the picture model. No house prompt, no judge holding the picture, no paste afterwards: the product is
drawn from its real pictures. Returns the record ({file, refs, prompt, model}); the prompt is written beside the file.
"""
import json
import threading
from pathlib import Path

from . import approval, paths as P, product3d, providers as PR, route as R
from .recipe import RecipeRefused, gate, is_sheet_shape, na_of, validate_recipe, is_filled as _is_filled      # noqa: F401

_KEY = {}
_LOCK = threading.Lock()


def _key(entry):
    """Read once per process: many pictures at once asking the Keychain fail."""
    with _LOCK:
        if "v" not in _KEY:
            _KEY["v"] = R.key_value(R.key_name(entry))
    return _KEY["v"]


SHEET_SAYS = ("its product casting sheet: every side of it, labelled, at its true size; the exact shape, label and finish "
              "to copy from whichever side the picture shows")


def product(brand, slug):
    """(name, refs, line) for one product, off its kit: how it looks on its own and in use, and its real size."""
    kit = product3d.find_kit(brand, slug)
    if kit is None:
        return None
    k = json.loads((kit / "kit.json").read_text())
    shown, use = k.get("shown") or {}, k.get("in_use") or {}
    # each picture with what it is, so the model never mixes a front with a back (the owner, 2026-10-25: "some flex look
    # slop" — bristle dots drawn on its smooth back when front and back went in unlabelled)
    pairs = [(r, w) for blk in (shown, use) for r, w in zip(blk.get("refs") or [], (blk.get("refs_are") or []) + [""] * 9)]
    refs = [(kit / r, w) for r, w in pairs if (kit / r).is_file()]
    # THE PRODUCT CASTING SHEET goes in first, every time (the owner, 2026-10-27: "for all product generation or any image
    # that is using a product in it, we must use reference ... the highest quality references"): every side of it,
    # labelled, at true size (video-production product_kit.py sheet)
    sheet = kit / str((k.get("sheet") or {}).get("file") or "model/product-sheet.png")
    if sheet.is_file():
        refs = [(sheet, SHEET_SAYS)] + refs
    if not shown.get("refs"):
        # Every kit holds its front, three-quarter and back photographs; only the front used to go in, so the model
        # invented every angle it was not shown (2026-10-26). All three go in, each saying which side it is, on the
        # opaque white-background photo (the same pixels as the transparent cut, with no alpha to guess at).
        views = [("reference-front", "the FRONT view"), ("reference-34", "the THREE-QUARTER view"),
                 ("reference-back", "the BACK view")]
        got = [(kit / "model" / f"{n}.png", w) for n, w in views if (kit / "model" / f"{n}.png").is_file()]
        refs = (got or [(p, "its real photo") for p in (kit / "model" / "reference-front-transparent.png",
                                                        kit / "model" / "packshot-cutout.png") if p.is_file()][:1]) + refs
    name = str((k.get("aliases") or [slug])[0]).upper()
    cm = k.get("size_cm") or {}
    size = (f"The real {name} is {cm['height']:g} cm tall and {(cm.get('width') or cm.get('diameter')):g} cm wide: draw it "
            "at that true size against hands and faces, never smaller." if cm.get("height") and (cm.get("width") or cm.get("diameter")) else "")
    # how it really works, off the kit's behaviour (the owner, 2026-10-27: "if product is in use, the realism and ... the
    # physics, like how it's used, needs to be 100% accurate. Otherwise, it's awkward"): a model has seen few devices
    # like it, so how it is held and what it never does go in with every picture of it
    bh = k.get("behaviour") or {}
    held = f"How the real {name} is held: {bh['held']}." if bh.get("held") else ""
    never = f"Never show {name}: " + "; ".join(bh["never_show"]) + "." if bh.get("never_show") else ""
    return name, refs, " ".join(x for x in (shown.get("line"), use.get("line"), size, held, never) if x)


def labels(refs, first):
    """'IMAGE n is <what>' for each product picture, numbered after the caller's own references."""
    return " ".join(f"IMAGE {first + i} is the real {nm}: {w}." for i, (nm, w) in enumerate(refs) if w)


PEOPLE = {
    "lookalike": ("Every person is a LOOKALIKE of the person in that same spot in IMAGE 1: the same look, age, build, hair, "
                  "style and energy. A celebrity or known influencer stays recognisable as a nod, with a "
                  "slightly different face, never the real person. Any real brand name or logo becomes a parody of it, never "
                  "the real one."),
    "made-up": ("Every person is a realistic made-up person, never anyone from a reference picture. Any real brand name or "
                "logo becomes a parody of it, never the real one."),
}


FRAME = ("This picture is 9:16, vertical, made at that size from the start. Its centre 4:5 (full width, from 15% to 85% of "
         "the height) is the SAFE ZONE: every face, hand, product, headline, word and badge sits inside it, clear of its edges. "
         "The top 15% and the bottom 15% are bleed: more of the same scene (wall, floor, ceiling, sky, counter), nothing that "
         "must be seen. The scene continues naturally to the top and bottom edge; never a band, never empty space.")


# The brief's own lines, each in its own labelled section after THE PICTURE (the owner, 2026-10-26: the dials, what stays, the
# feeling and the techniques used to be dropped on the way to the model). Any other filled sheet variable gets a section
# named after itself, so nothing is dropped. A variable that is not applicable is left out of the prompt (it is still
# recorded beside the picture).
SHEET_SECTIONS = (("stays", "WHAT STAYS"), ("emotion", "THE FEELING"), ("dials", "THE DIALS"), ("techniques", "TECHNIQUES"))


def sheet_sections(sheet):
    """[(header, body)] for every FILLED variable of the sheet, the known four first and in their order, then the rest in
    the order given. `sheet` maps a name to a value, or to {"na": "reason"} for not applicable."""
    filled = {k: v for k, v in (sheet or {}).items() if _is_filled(v)}
    out, known = [], {k for k, _ in SHEET_SECTIONS}
    for k, head in SHEET_SECTIONS:
        if k in filled:
            out.append((head, _as_text(filled[k])))
    for k, v in filled.items():
        if k not in known:
            out.append((k.replace("_", " ").upper(), _as_text(v)))
    return out


def _is_filled(v):
    if isinstance(v, dict) and "na" in v:
        return False
    if v is None:
        return False
    if isinstance(v, (str, list, tuple, dict)):
        return bool(v)
    return True


def _as_text(v):
    if isinstance(v, (list, tuple)):
        return "\n".join(str(x) for x in v if str(x).strip())
    if isinstance(v, dict):
        return "\n".join(f"{k}: {x}" for k, x in v.items())
    return str(v).strip()


def prompt(text, names, lines, has_ref, people=None, inputs="", sheet=None, people_lines=(), rules_lines=(), sections=()):
    """THE INPUT STANDARD (the owner, 2026-10-26): every picture's prompt has the same labelled sections in the same order,
    and a section with nothing in it is left out. prompts/input-standard-v1-owner.md is the page that shows it.
        INPUTS      which image is which
        THE PICTURE what the caller asked for (scene, subject, details, exact words)
        WHAT STAYS · THE FEELING · THE DIALS · TECHNIQUES · any other filled sheet variable, each its own section
        THE PRODUCT keep-it-exact line, then the kit's own lines and true size
        THE PEOPLE  lookalikes or made-up
        THE FRAME   9:16 with its safe zone
        RULES       change only what THE PICTURE says; no other writing"""
    ins = []
    if has_ref:
        ins.append("IMAGE 1 is the reference. Make ours from it: the same layout, look, light, photo style and text "
                   "style and placement, changed only as THE PICTURE says.")
    if inputs:
        ins.append(inputs)
    prod = []
    if names:
        prod.append(f"The product images are photographs of the real {', '.join(names)}, each marked with the side it "
                    "shows. Preserve its geometry, colour and label legibility exactly, whichever side faces the camera; "
                    "do not restyle it, relabel it or invent any side that is not shown.")
    prod += [l for l in lines if l]
    rules = ["No writing in the picture except the exact words THE PICTURE gives."]
    if has_ref:
        rules.insert(0, "Apart from what THE PICTURE changes, do not change anything else in IMAGE 1.")
    # "cast": the caller names each cast member and the IMAGE that carries their face in `people_lines` (a swap list's cast swap)
    head = [] if people == "cast" else [PEOPLE[people or ("lookalike" if has_ref else "made-up")]]
    ppl = "\n".join(head + [str(x).strip() for x in people_lines if str(x).strip()])
    rls = "\n".join([" ".join(rules)] + [str(x).strip() for x in rules_lines if str(x).strip()])
    secs = ([("INPUTS", "\n".join(ins)), ("THE PICTURE", text.strip())] + sheet_sections(sheet) + list(sections)
            + [("THE PRODUCT", "\n".join(prod)), ("THE PEOPLE", ppl), ("THE FRAME", FRAME), ("RULES", rls)])
    return "\n\n".join(f"{h}\n{b}" for h, b in secs if b)


def _rules():
    """components/model-inputs, found beside this component: the limits and rules live there, not here."""
    import sys as _sys
    root = str(P.sibling("model-inputs"))
    if root not in _sys.path:
        _sys.path.append(root)
    import input_rules
    return input_rules


MODEL = _rules().model_of("pictures.generate")          # asked of the Model House, never named here
MAX_IMAGES = _rules().limits(MODEL)["max_images"]                     # OpenAI: up to 16 images per call
QUALITIES = tuple(q for q in _rules().qualities(MODEL) if q != "auto")


def valid_size(size):
    return _rules().valid_size(size, MODEL)


def plan(brand, text, references=(), products=(), product_refs=None, product_lines=None, people=None, ref_roles=None,
         sheet=None, people_lines=(), rules_lines=(), sections=(), ref_says=None):
    """What ONE call would send, built without any call: the prompt, and every image in order with its role. `ref_says`
    ({index: sentence}) replaces the 'show it exactly as it is' line for a reference that is not pasted in as it is (a cast
    member's photo: the face is kept, the pose is the swipe's)."""
    names, refs, lines, labelled = [], [Path(r) for r in references], [], []
    given_roles = list(ref_roles or [])
    roles = [("the reference" if i == 0 else (given_roles[i] if i < len(given_roles) and given_roles[i] else "a real piece the caller named")) for i in range(len(refs))]
    says = {int(k): v for k, v in (ref_says or {}).items()}
    named = " ".join(says.get(i) or f"IMAGE {i + 1} is {roles[i]}: show it exactly as it is, its own pixels and words, never redrawn." for i in range(1, len(refs)))
    for slug in products:
        p = product(brand, slug)
        if p is None:
            continue
        name, prefs, line = p
        names.append(name)
        given = [Path(r) for r in (product_refs or {}).get(name, [])]
        side = {Path(r): w for r, w in prefs}                 # a ticked subset keeps the side each photo shows
        use = [(r, side.get(r, "")) for r in given] or [(r, w) for r, w in prefs]
        refs += [r for r, _ in use]
        roles += [f"the real {name}" + (f": {w}" if w else "") for _, w in use]
        labelled += [(name, w) for _, w in use]
        lines.append((product_lines or {}).get(name, line))
    lab = " ".join(x for x in (named, labels(labelled, len(references) + 1)) if x)
    if len(refs) > MAX_IMAGES:
        raise ValueError(f"{len(refs)} images is more than the model takes ({MAX_IMAGES})")
    return {"prompt": prompt(text, names, lines, bool(references), people, lab, sheet, people_lines, rules_lines, sections),
            "refs": refs, "roles": roles, "products": names}


def make(brand, text, out, references=(), products=(), aspect="9:16", product_refs=None, product_lines=None, people=None, quality=None, ref_roles=None, size=None, resolution=None,
         recipe=None, people_lines=(), rules_lines=(), sections=(), kind="picture", ref_says=None):
    """One plain picture. `kind` is "picture" (a static ad or a Prompt Bench picture: carries the variable sheet) or "slide" (a
    carousel slide: no slide sheet exists yet, so the recipe gate does not apply to it, recorded in models.json). `product_refs` / `product_lines` ({NAME: …}) override a kit's own for this call."""
    gate(recipe, kind=kind)                       # no blank reaches a door
    approval.check_bases(references)               # a picture of ours is a base only when approved
    pl = plan(brand, text, references, products, product_refs, product_lines, people, ref_roles,
              sheet=None if is_sheet_shape(recipe) else recipe,     # a variable-sheet recipe's text is built by its own builder
              people_lines=people_lines, rules_lines=rules_lines, sections=sections, ref_says=ref_says)
    text_, refs, names = pl["prompt"], pl["refs"], pl["products"]
    entry = R.table()["models"]["gpt-image-person"]
    if quality:                                   # a test can ask for another quality for one call
        if quality not in QUALITIES:
            raise ValueError(f"quality {quality!r} is not one of {', '.join(QUALITIES)}")
        entry = {**entry, "params": {**(entry.get("params") or {}), "quality": quality}}
    hf = entry.get("provider") == "higgsfield"
    if size and not hf:                           # a test can ask for another frame size for one call (OpenAI door only)
        bad = valid_size(size)
        if bad:
            raise ValueError(f"size {size}: {bad}")
        entry = {**entry, "sizes": {**(entry.get("sizes") or {}), aspect: size}}
    if resolution and hf:                         # Higgsfield takes a tier, not a WxH size
        entry = {**entry, "params": {**(entry.get("params") or {}), "resolution": resolution}}
    prm = entry.get("params") or {}
    found = _rules().check(MODEL, text_, [{"path": str(r)} for r in refs], size=None if hf else R.size_for(entry, aspect),
                           quality=prm.get("quality"), aspect=aspect, door="higgsfield" if hf else None,
                           resolution=prm.get("resolution") if hf else None, variant=prm.get("variant") if hf else None)
    stop = [f["say"] for f in found if f["level"] == "error"]
    if stop:
        raise ValueError("components/model-inputs refuses this request: " + " ".join(stop))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rungs = R.rungs("gpt-image-person", entry)
    if len(rungs) == 1:
        rec = PR.generate(entry, text_, refs, out, aspect, key=None if hf else _key(entry))
    else:                                           # GPT first, then Seedream, then Nano Banana Pro, then the net
        rec = PR.generate_ladder(rungs, text_, refs, out, aspect)
    out.with_suffix(".prompt.txt").write_text(text_ + "\n\n[references]\n" + "\n".join(str(r) for r in refs) + "\n")
    # the filled sheet beside the picture, so a later run can replay it exactly (and the not-applicable variables are on record)
    out.with_suffix(".recipe.json").write_text(P.portable(json.dumps({     # stored paths portable (rule 4)
        "recipe": recipe, "not_applicable": na_of(recipe),
        "request": {"brand": brand, "text": text, "references": [str(r) for r in references], "products": list(products),
                    "aspect": aspect, "quality": quality, "resolution": resolution, "size": size, "people": people,
                    "ref_roles": list(ref_roles or []), "people_lines": list(people_lines), "rules_lines": list(rules_lines)},
        "prompt": text_, "images": [{"n": i + 1, "path": str(r), "role": role} for i, (r, role) in enumerate(zip(refs, pl["roles"]))],
        "settings": {"provider": entry.get("provider"), "model": entry.get("vendor_model"), "params": entry.get("params")},
        "made_by": (rec or {}).get("made_by"), "ladder": (rec or {}).get("ladder"), "checks": found,
        # a base that was below criteria carries its flag onto what is made from it
        "chosen": True,                       # no output judge on this path: the one attempt is the chosen one
        "below_criteria": [],
        "below_criteria_inputs": [str(r) for r in references if approval.flag_of(r)],
        "carries_below_criteria": any(approval.flag_of(r) for r in references)}, indent=1, ensure_ascii=False)))
    return {"file": str(out), "refs": [str(r) for r in refs], "prompt": text_, "model": entry.get("vendor_model"),
            "products": names, "checks": found, **{k: v for k, v in (rec or {}).items() if k in ("request_id", "usage", "made_by", "ladder")}}


def generate(send, out, recipe=None, quality=None, resolution=None):
    """ONE picture from what the preflight shows: `send` is `preview(...)["send"]` (brand, text, references, products,
    product_refs, product_lines, ref_roles, people). It goes down the picture ladder (GPT Image 2.5 on Higgsfield, one more
    try, Seedream 5 Pro on a refusal, Nano Banana Pro, then OpenAI direct as the last rung) and comes back as
    {"file", "rung", "attempts", "below_criteria", "prompt", "checks"}. This path has no output judge, so `below_criteria`
    lists only the flags carried from the pictures it was made from. The recipe record is written beside the file."""
    pr = send.get("product_refs") or None
    rec = make(send["brand"], send["text"], out, references=[Path(x) for x in send.get("references") or []],
               products=send.get("products") or [], aspect=send.get("aspect") or "9:16",
               product_refs={k: [Path(x) for x in v] for k, v in pr.items()} if pr else None,
               product_lines=send.get("product_lines"), people=send.get("people") or None, quality=quality,
               ref_roles=send.get("ref_roles"), resolution=resolution, recipe=recipe, ref_says=send.get("ref_says"),
               people_lines=send.get("people_lines") or (), rules_lines=send.get("rules_lines") or ())
    carried = [str(x) for x in send.get("references") or [] if approval.flag_of(x)]
    on_top = None
    if send.get("type_layer"):                    # swaps rule 4: made with no words in it; the brief's type layer is set over it now
        from . import words
        on_top = words.set_on_top(rec["file"], send["type_layer"])
    got = {"file": rec["file"], "rung": rec.get("made_by"), "attempts": rec.get("ladder") or [],
           "below_criteria": carried, "prompt": rec["prompt"], "checks": rec.get("checks") or []}
    if on_top is not None:
        got["words_on_top"] = on_top
    return got


def to_frame(picture, out, w=1080, h=1920):
    """A picture made at 9:16 from the start, sized to the delivered 1080x1920. Nothing is painted or placed."""
    from PIL import Image
    im = Image.open(picture).convert("RGB")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out
