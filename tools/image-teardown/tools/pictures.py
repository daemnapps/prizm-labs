#!/usr/bin/env python3
"""The pictures — the brand step's written frame, made into the ad.

    python3 tools/pictures.py <run> --brand <brand> --product <slug> [--count 2] [--dry-run]

the owner, 2026-10-23, on the first creative-controls run: "These statics are
brilliant. Let's ensure that this is established in our chains." This is the
step that run took by hand, made the chain's own. It reads the run's
`out/03-injection.md` (the picture swap, the creative controls it set, every
zone's words and the art direction) and hands it to image-production as one
direction, with the swipe as the picture reference, so the ad keeps the
swipe's picture with our objects swapped in.

THE DEFAULT IS THE PLAIN PATH (`plain_pictures`, 2026-10-25), built by components/model-inputs preview.py the same
way the board builds it, rules in model-inputs/lessons.json. What follows is the `--controlled` path's history; on the
plain path there is no paste, judge or refusal retry, and a picture is made at 9:16 from the start.

What the first run taught, built in (the --controlled path):
- **The product comes from its real photo, never the 3D placement**, whenever
  it is in frame (`--no-product-3d`): the 3D route left an empty scene or a
  black shape on the neck three times out of four.
- **The picture model's safety filter can refuse the swipe itself** (a body
  diagram, a close-up of skin). A refusal is retried once from the written
  direction alone, without the swipe as reference.
- **The product is never drawn** (the owner, 2026-10-23: "you continuously put in
  product slop ... It shouldn't even be an option"). Every delivered picture with
  the product in frame gets the REAL product pasted over the drawn one: the
  kit's real turntable photo at the matching angle, with a contact shadow from
  its own outline (tools/video-production product_paste.py). A picture the
  real product cannot be laid on is held, never delivered; the drawn version is
  kept beside it in `drawn/` only as a record.
- The ad picture judge holds a picture whose words and picture are not one
  idea (image-production purposes.json, `ad`), so a held picture is a real
  finding, not noise: it is left in `generated/` with the reason.

Writes runs/image-teardown/<brand>/<run>/pictures/ (image-production's own
record beside each picture). Prints what was delivered and what was held.
"""
import argparse, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402
# the swaps record is the writing station's (stage 3), since 2026-10-27; found by walking up, so it holds even when
# another component's `paths` module was loaded first
for _r in HERE.parents:
    if (_r / "tools" / "image-writing" / "tools" / "swaps.py").is_file():
        sys.path.append(str(_r / "tools" / "image-writing" / "tools"))
        break
import swaps as SW  # noqa: E402

MAKE = P.REPO / "tools" / "image-production" / "make.py"
FIT = 0.8   # real NOVA finds fit 0.9+; a neck or a bump mistaken for it fit ~0.6 (2026-10-23)
REFUSED = re.compile(r"rejected by the safety system|moderation_blocked")


def labelled(t, name):
    """A labelled line, whether written `- **NAME:** …` or `**NAME:** …`."""
    m = re.search(r"(?m)^\s*(?:-\s*)?\*\*" + re.escape(name) + r":\*\*\s*(.+)", t)
    return m.group(1).strip() if m else ""


def section(t, a, b):
    """A numbered section, whether headed `**1. NAME**` or `## 1. NAME`."""
    head = lambda s: r"(?:\*\*" + re.escape(s) + r"\*\*|#+\s*" + re.escape(s) + r"[^\n]*)"
    m = re.search(head(a) + r"(.*?)" + head(b), t, re.S)
    return m.group(1).strip() if m else ""


FIDELITY = ("THE FIDELITY: match IMAGE 1's own quality exactly: the same kind of camera, resolution, sharpness, noise, "
            "compression, colour and light. Never cleaner, sharper, glossier or more polished than IMAGE 1: a native post "
            "has to read as the same kind of post in the feed (the owner, 2026-10-25: \"match the granularity of the swipe ... "
            "some of this looks too polished\").")
OWN_COLOURS = ("Keep IMAGE 1's own colours, light and set exactly. A native post is never recoloured to a brand palette "
               "or restyled into a cleaner set: where a swap below changes a colour, a light or the set's look, IMAGE 1 wins.")


def direction(t, with_ref=True, note=None, organic=False):
    head = ("Remake IMAGE 1 (the reference ad) as a new ad: keep its framing, pose, camera, light, layout "
            "and caption placement exactly, and make only the swaps below." if with_ref else
            "Make this ad exactly as described, zone by zone: the layout, framing, light and caption "
            "placement below are the plan.")
    if with_ref:                                   # first, so the swaps below cannot talk it out of the swipe's look
        head += "\n\n" + FIDELITY + (" " + OWN_COLOURS if organic else "")
    parts = [head,
             "WHAT STAYS: " + labelled(t, "STAYS"),
             "THE SWAPS: " + labelled(t, "SWAPS"),
             "WHY IT STILL READS: " + labelled(t, "WHY IT STILL READS"),
             "THE ONE THING THE EYE HITS FIRST: " + labelled(t, "THE STANDOUT"),
             "THE EMOTION: " + labelled(t, "THE EMOTION"),
             "THE WORDS ON THE AD, ZONE BY ZONE (render the 'Our copy' text exactly, with its colours; "
             "nothing else written on the picture; no long dashes): "
             + section(t, "1. THE INJECTED FRAME", "2. THE SUBJECT"),
             "THE PICTURE, ZONE BY ZONE: " + section(t, "3. THE ART DIRECTION", "4. SLOTS"),
             "The words and the picture are one idea, and the words make sense on one read. Never sterile.",
             "Any logo, wordmark, team crest, outfit or famous face the swipe carries is never kept as the real thing: make it a funny, absurd parody of itself (a renamed mark that jokes about the problem, a lookalike that is clearly not the real person), never blank it."]
    if note:
        parts.append("ONE MORE THING FOR THIS PICTURE: " + note)
    return "\n\n".join(p for p in parts if p.split(": ", 1)[-1].strip())


def product_name(brand, slug):
    f = P.product(brand, slug)
    first = next((l for l in f.read_text().splitlines() if l.startswith("# ")), "# " + slug) if f.is_file() else "# " + slug
    return re.sub(r"[™®]", "", first[2:].split()[0]).strip()


def organic_swipe(run):
    """A swipe from an organic feed (a native post), read off the run's source record."""
    import json
    f = run / "assets" / "source.json"
    try:
        return json.loads(f.read_text()).get("swipe_kind") == "organic" if f.is_file() else False
    except ValueError:
        return False


NO_WORDS = ("NO WORDS IN THE PICTURE: no caption, headline, overlay text or lettering of any kind anywhere in it (the words are "
            "set on afterwards). Take the caption out of IMAGE 1 and paint what is behind it, so the band where it sat is plain "
            "picture. Lettering that belongs to an object named in THE SWAPS stays on that object.")
NO_WORDS_FRESH = ("NO WORDS IN THE PICTURE: no caption, headline, overlay text or lettering of any kind anywhere in it (the words "
                  "are set on afterwards). Lettering that belongs to an object named in THE SWAPS stays on that object.")


def picture_inputs(run, swaps, words, with_ref, note=None):
    """The plain picture's text and reference pictures, from the brand step's swaps and words. Pure: reads the run's
    swipe and vars/extra-refs.json, calls nothing. plain_pictures sends this; components/model-inputs preview.py shows it."""
    import json
    src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    rec = SW.load(run)
    on_top = bool(rec) and rec.get("words") == "set_on_top" and not words     # swaps rule 4: no words in = set on top after
    text = "\n\n".join(x for x in [
        "THE SWAPS: " + swaps,
        NO_WORDS if on_top and with_ref else NO_WORDS_FRESH if on_top else
        "THE WORDS ON THE PICTURE (exactly these words, in IMAGE 1's own type style and places; nothing else "
        "written; no long dashes):\n" + words if words else "",
        ("ONE MORE THING FOR THIS PICTURE: " + note) if note else ""] if x)
    # The run's real pieces (vars/extra-refs.json, the same list the old path reads): a real before/after, the cast
    # member's banked photo. They go in after the swipe, each with the role it plays, never redrawn.
    refs = [src] if (with_ref and src) else []
    extra = run / "vars" / "extra-refs.json"
    if extra.is_file():
        roles = []
        for x in json.loads(extra.read_text()):
            if Path(x["path"]).is_file():
                refs.append(Path(x["path"]))
                roles.append(f"IMAGE {len(refs)} is {x['role']}: show it exactly as it is, its own pixels and words, never redrawn.")
        if roles:
            text += "\n\nTHE REAL PIECES: " + " ".join(roles)
    return text, refs


def product_in_frame(t, name):
    """Whether the brand step puts the product in frame ("no NOVA in this picture" names it too: only a mention that is
    not negated counts)."""
    frame = section(t, "1. THE INJECTED FRAME", "2. THE SUBJECT") + section(t, "3. THE ART DIRECTION", "4. SLOTS")
    neg_before = r"\b(no|not|never|without|leaves out|out of frame)\b[^.\n]{0,40}$"
    neg_after = r"^[^.\n]{0,25}\b(does not appear|doesn't appear|is not in|isn't in|is absent|stays out|is left out|never appears)"
    return any(not re.search(neg_before, frame[:m.start()], re.I) and not re.search(neg_after, frame[m.end():], re.I)
               for m in re.finditer(r"\b" + re.escape(name) + r"\b", frame))


def product_in_frame_for(run, t, name):
    """swaps rule 2: the swaps record's yes or no when the run has one; the old reading of the text only when it has none."""
    rec = SW.load(run)
    if rec and isinstance(rec.get("product_in_frame"), bool):
        return rec["product_in_frame"]
    return product_in_frame(t, name)


def _preview():
    """components/model-inputs/preview.py (the Prompt Bench's builder), loaded by path."""
    import importlib.util
    root = str(P.REPO / "components" / "model-inputs")
    if root not in sys.path:
        sys.path.append(root)
    spec = importlib.util.spec_from_file_location("it_mi_preview", P.REPO / "components" / "model-inputs" / "preview.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dry_ok(run):
    """True when the copy sign-off is switched off for this run on purpose (vars/copy-review.md says `off`): the full
    automatic route the owner turns on once the words are trusted ("for a while until we're ready for full auto")."""
    f = run / "vars" / "copy-review.md"
    return f.is_file() and f.read_text().strip().lower().startswith("off")


def plain_pictures(run, brand, slug, t, out, count, with_ref, in_frame, note=None, rnd=1):
    """The plain way, the default since 2026-10-25 (the owner, on the carousels made this way: "literally 1000000x better
    than any flex implementation we had in the past ... not just statics but also video scenes as well"): ONE call per
    picture through tools/image-production plain.make: the swipe as IMAGE 1, the brand step's swap and its exact
    words, the product's real pictures and line from its kit. No house prompt, judge hold, paste or grain. The 4:5 is
    kept in generated/; the delivered 9:16 is the same picture sized to 1080x1920 (made 9:16 from the start)."""
    import json
    sys.path.append(str(P.REPO / "tools" / "image-production"))
    import image_production as IP
    from image_production import plain
    # ONE prompt builder for pictures: exactly what the Prompt Bench sends (components/model-inputs preview.build_picture):
    # every swap (not only the first line), the clean words, the creative lines, the real pieces with their roles, the
    # product's views; the brief writer's notes, markdown, tables and self-checks stay out (PSH-9).
    PV = _preview()
    brief = {"brand": brand, "run": run.name, "product": slug if in_frame else "", "product_slug": slug, "note": note or "", "with_ref": bool(with_ref)}
    # the same filled sheet the board sends (the owner, 2026-10-27: "the board is just a visual representation of the chains
    # themselves, never its own brain"): the dial levels the sheet fills (the swipe's own look, the never-sterile floor)
    # reach a chain run exactly as they reach a picture made on the board
    brief = PV.full_brief(PV.fill_defaults({"brief": brief}))
    built = PV.build_picture(brief)
    send = built["send"]
    # the copy sign-off (the owner, 2026-10-27): "before images are generated in general, the actual copy needs to be
    # reviewed". No first picture from words a person has not approved (tools/image-writing tools/copy_ok.py).
    ok = P.REPO / "tools" / "image-writing" / "tools" / "copy_ok.py"
    words = [w for w in (built.get("fields") or {}).get("our_copy") or [] if str(w).strip()]
    if words and not dry_ok(run):
        import importlib.util
        spec = importlib.util.spec_from_file_location("it_copy_ok", ok)
        CO = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(CO)
        not_yet = CO.approved(run, words)
        if not_yet:
            print(f"  ✗ the words are not approved yet: {' | '.join(not_yet)} "
                  f"(python3 tools/image-writing/tools/copy_ok.py approve {run.name} --by <name>)")
            return []
    # EVERY picture passes the variable sheet: filled from the brief and the brand files first; a blank that cannot be filled
    # stops the picture before any spend, naming the variable. The cost approval is the chain's own production approval
    # (the queue), not a person pressing Make, so this recipe is validated without it.
    recipe = {**PV.fill_defaults({"brief": brief}), "_for_make": False}
    rec = SW.load(run)
    layer = (send.get("type_layer") or SW.words_layer(run)) if rec and rec.get("words") == "set_on_top" else None   # the send carries OUR copy in each element
    made = []
    (out / "generated").mkdir(parents=True, exist_ok=True)
    for i in range(1, count + 1):
        name = f"{run.name}-pictures" + (f"-r{rnd}" if rnd > 1 else "") + f"-{i:02d}.png"
        raw = out / "generated" / name
        try:
            plain.make(send["brand"], send["text"], raw, references=[Path(x) for x in send["references"]],
                       products=send["products"], aspect="9:16", people=send["people"], ref_roles=send.get("ref_roles"),
                       product_refs={k: [Path(x) for x in v] for k, v in (send.get("product_refs") or {}).items()} or None,
                       product_lines=send.get("product_lines"), recipe=recipe, ref_says=send.get("ref_says"),
                       people_lines=send.get("people_lines") or (), rules_lines=send.get("rules_lines") or ())
        except (Exception, SystemExit) as e:
            print(f"  ✗ {name}: {type(e).__name__}: {str(e)[:200]}")
            continue
        pic = out / name
        plain.to_frame(raw, pic)          # made at 9:16 from the start: only sized to 1080x1920, nothing painted
        if any(send.get("bars") or []):   # the swipe's black bars, as the board's make step puts them (lessons.json L-1)
            PV.put_bars(pic, *send["bars"])
        if layer:                         # swaps rule 4: made with no words in it; the brief's own type layer is set on top, the plate kept
            from image_production import words
            r = words.set_on_top(pic, layer, plate=out / "plates" / pic.name)
            if not r["ok"]:
                # a picture whose words could not be set is never delivered without them (the board refuses the same)
                print(f"  ✗ {pic.name}: the words could not be set ({r['notes']}), so it is held back")
                continue
            print(f"  words set on top: {r['elements']} element(s)")
        made.append(pic)
        print(f"  ✓ {pic}")
    return made


def make(run, brand, slug, t, out, count, with_ref, in_frame, dry, note=None, rnd=1):
    cmd = [sys.executable, str(MAKE), "--brand", brand, "--purpose", "ad", "--aspect", "4:5",
           "--count", str(count), "--people", "--direction", direction(t, with_ref, note, organic_swipe(run)),
           "--out", str(out), "--label", f"{run.name}-pictures" + (f"-r{rnd}" if rnd > 1 else "")]
    if with_ref:
        src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
        if src:
            cmd += ["--ref", str(src)]
    # REAL PIECES THE PICTURE MUST CARRY (the owner, 2026-10-25: "the best review ... should be a before and after ...
    # use one of our before and afters"): a run may list real images in vars/extra-refs.json, each with the role it
    # plays in the picture; they go in as IMAGE 2, 3 ... and the direction says where each one sits, unchanged.
    extra = run / "vars" / "extra-refs.json"
    if extra.is_file():
        import json as _json
        roles = []
        for i, x in enumerate(_json.loads(extra.read_text()), 2 if with_ref else 1):
            if Path(x["path"]).is_file():
                cmd += ["--ref", x["path"]]
                roles.append(f"IMAGE {i} is {x['role']}: show it exactly as it is, its own pixels and words, never redrawn.")
        if roles:
            i_dir = cmd.index("--direction") + 1
            cmd[i_dir] = cmd[i_dir] + "\n\nTHE REAL PIECES: " + " ".join(roles)
    if in_frame:
        cmd += ["--product", slug, "--no-product-3d", "--product-after"]
    if dry:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True)


def _grain(im):
    """How grainy a picture is: the mean gap between it and its own 3-pixel median."""
    from PIL import ImageChops, ImageFilter, ImageStat
    g = im.convert("L")
    return ImageStat.Stat(ImageChops.difference(g, g.filter(ImageFilter.MedianFilter(3)))).mean[0]


def swipe_fidelity(src):
    """What the swipe's pixels are like: its height, its grain and its JPEG quality."""
    from PIL import Image
    im = Image.open(src)
    q = None
    lum = list((getattr(im, "quantization", None) or {}).get(0, []))
    if lum:
        scale = (sum(lum) / len(lum)) / 57.6 * 100          # libjpeg's base luminance table averages ~57.6
        q = int(max(10, min(95, (200 - scale) / 2 if scale <= 100 else 5000 / scale)))
    return {"height": im.size[1], "grain": _grain(im.convert("RGB")), "quality": q}


def native_finish(pic, src, keep_dir):
    """Bring one made picture down to the swipe's own fidelity: no sharper (its resolution), no cleaner (its
    grain), no crisper (its compression). The polished original is kept beside it. A picture model always
    draws cleaner than a phone; this is the programmed half of matching the swipe (the owner, 2026-10-25)."""
    import io, shutil
    from PIL import Image, ImageChops
    s = swipe_fidelity(src)
    keep_dir.mkdir(exist_ok=True)
    shutil.copy2(pic, keep_dir / pic.name)
    im = Image.open(pic).convert("RGB")
    w, h = im.size
    if s["height"] < h * 0.9:                                   # the swipe is softer than our render: match it
        k = s["height"] / h
        im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS).resize((w, h), Image.BILINEAR)
    add = max(0.0, s["grain"] - _grain(im))
    if add > 0.3:                                               # mono grain, centred on zero, at the gap's strength
        n = Image.effect_noise((w, h), add * 2.5).convert("L")
        im = Image.merge("RGB", [ImageChops.add(c, n, 1.0, -128) for c in im.split()])
    if s["quality"]:
        b = io.BytesIO(); im.save(b, "JPEG", quality=s["quality"]); b.seek(0); im = Image.open(b).convert("RGB")
    im.save(pic)
    return {"height": s["height"], "grain_added": round(add, 2), "jpeg_quality": s["quality"]}


def text_boxes(pic):
    """Every line of words macOS Vision reads on a picture: (left, top, width, height) in pixels, and the words."""
    exe, src = HERE / "vision" / ".build" / "textboxes", HERE / "vision" / "textboxes.swift"
    if not exe.is_file() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], capture_output=True)
    if not exe.is_file():
        return []
    from PIL import Image
    W, H = Image.open(pic).size
    boxes = []
    for line in subprocess.run([str(exe), str(pic)], capture_output=True, text=True).stdout.splitlines():
        nums, _, words = line.partition("\t")
        l, t, w, h = (float(x) for x in nums.split())
        boxes.append(((l * W, t * H, w * W, h * H), words))
    return boxes


def words_on_top(pic, drawn):
    """The words stay over the product, as on the swipe (the owner, 2026-10-25: products pasted in "look like cut-outs"
    when the real one is laid over the caption it sat behind). Each line of words read on the drawn picture is put
    back over the pasted one: its white letters and their dark outline and shadow, nothing else in the line's box."""
    from PIL import Image, ImageChops, ImageFilter
    if not drawn.is_file():
        return 0
    a, d = Image.open(pic).convert("RGB"), Image.open(drawn).convert("RGB")
    if a.size != d.size:
        return 0
    W, H = a.size
    content = drawn.parent.parent / "generated" / drawn.name
    if content.is_file():
        # the words as the model first set them: a picture laid in twice has already lost them from drawn/
        sys.path.append(str(P.REPO / "tools" / "image-production"))
        from image_production import providers as PR
        c = Image.open(content).convert("RGB")
        box = PR.zone_box(*c.size, W, H)
        d = d.copy()
        d.paste(c.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])
        drawn = drawn.parent / ("_words-" + drawn.name)
        d.save(drawn)
    content = drawn.parent.parent / "generated" / drawn.name
    if content.is_file():
        # the words as the model first set them: a picture laid in twice has already lost them from drawn/
        c = Image.open(content).convert("RGB")
        d = c.resize((W, H), Image.LANCZOS)               # made at 9:16: the same frame as the delivered picture
        import tempfile
        drawn = Path(tempfile.mkdtemp()) / drawn.name                # read by Vision, then left to the temp folder
        d.save(drawn)
    r, g, b = d.split()
    lo, hi = ImageChops.darker(ImageChops.darker(r, g), b), ImageChops.lighter(ImageChops.lighter(r, g), b)
    lit = ImageChops.multiply(lo.point(lambda v: 255 if v > 205 else 0),             # white letters, not tinted
                              ImageChops.subtract(hi, lo).point(lambda v: 255 if v < 30 else 0))
    keep = Image.new("L", (W, H), 0)
    n = 0
    for (l, t, w, h), _words in text_boxes(drawn):
        pad = max(4, int(h * 0.35))
        box = (max(0, int(l - pad)), max(0, int(t - pad)), min(W, int(l + w + pad)), min(H, int(t + h + pad)))
        grow = max(3, int(h * 0.18)) | 1                    # the outline and the hard shadow around each letter
        m = lit.crop(box).filter(ImageFilter.MaxFilter(grow))
        keep.paste(ImageChops.lighter(keep.crop(box), m), box[:2])
        n += 1
    if n:
        Image.composite(d, a, keep.filter(ImageFilter.GaussianBlur(0.8))).save(pic)
    return n


def refinish(run, brand, slug):
    """The finishing steps again on the delivered pictures, from what the model first made (generated/, already 9:16):
    for a fix to finishing that should not cost a re-draw."""
    import datetime as dt, shutil
    from PIL import Image
    out = P.REPO / "runs" / "image-teardown" / brand / run.name / "pictures"
    pics = [p for p in sorted(out.glob("*.png")) if (out / "generated" / p.name).is_file()]
    if not pics:
        print(f"{run.name}: no delivered picture with its original in generated/ — nothing to refinish")
        return 1
    old = out.parent / f"pictures-before-{dt.datetime.now():%Y%m%d%H%M%S}"
    old.mkdir()
    src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    for pic in pics:
        shutil.copy2(pic, old / pic.name)
        base = Image.open(out / "drawn" / pic.name if (out / "drawn" / pic.name).is_file() else pic).convert("RGB")
        Image.open(out / "generated" / pic.name).convert("RGB").resize(base.size, Image.LANCZOS).save(pic)
    print(f"{run.name} · refinishing {len(pics)} pictures (earlier versions in {old.name}/)")
    real_product(brand, slug, product_name(brand, slug), pics, out)
    if src:
        for pic in pics:
            if pic.is_file():
                print(f"  matched to the swipe's fidelity: {pic.name} ({native_finish(pic, src, out / 'polished')})")
    return 0


def text_boxes(pic):
    """Every line of words macOS Vision reads on a picture: (left, top, width, height) in pixels, and the words."""
    exe, src = HERE / "vision" / ".build" / "textboxes", HERE / "vision" / "textboxes.swift"
    if not exe.is_file() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], capture_output=True)
    if not exe.is_file():
        return []
    from PIL import Image
    W, H = Image.open(pic).size
    boxes = []
    for line in subprocess.run([str(exe), str(pic)], capture_output=True, text=True).stdout.splitlines():
        nums, _, words = line.partition("\t")
        l, t, w, h = (float(x) for x in nums.split())
        boxes.append(((l * W, t * H, w * W, h * H), words))
    return boxes


def words_on_top(pic, drawn):
    """The words stay over the product, as on the swipe (the owner, 2026-10-25: products pasted in "look like cut-outs"
    when the real one is laid over the caption it sat behind). Each line of words read on the drawn picture is put
    back over the pasted one: its white letters and their dark outline and shadow, nothing else in the line's box."""
    from PIL import Image, ImageChops, ImageFilter
    if not drawn.is_file():
        return 0
    a, d = Image.open(pic).convert("RGB"), Image.open(drawn).convert("RGB")
    if a.size != d.size:
        return 0
    W, H = a.size
    r, g, b = d.split()
    lo, hi = ImageChops.darker(ImageChops.darker(r, g), b), ImageChops.lighter(ImageChops.lighter(r, g), b)
    lit = ImageChops.multiply(lo.point(lambda v: 255 if v > 205 else 0),             # white letters, not tinted
                              ImageChops.subtract(hi, lo).point(lambda v: 255 if v < 30 else 0))
    keep = Image.new("L", (W, H), 0)
    n = 0
    for (l, t, w, h), _words in text_boxes(drawn):
        pad = max(4, int(h * 0.35))
        box = (max(0, int(l - pad)), max(0, int(t - pad)), min(W, int(l + w + pad)), min(H, int(t + h + pad)))
        grow = max(3, int(h * 0.18)) | 1                    # the outline and the hard shadow around each letter
        m = lit.crop(box).filter(ImageFilter.MaxFilter(grow))
        keep.paste(ImageChops.lighter(keep.crop(box), m), box[:2])
        n += 1
    if n:
        Image.composite(d, a, keep.filter(ImageFilter.GaussianBlur(0.8))).save(pic)
    return n


def is_grid(run):
    """A swipe laid out as tiles (a 2x2 checklist, a collage): its tall version is the grid on black, the way the
    app shows a slideshow photo, never a painted strip that runs one tile's scene into its neighbour's."""
    spec = run / "out" / "02-replication-spec.md"
    t = spec.read_text(errors="replace") if spec.is_file() else ""
    return len(re.findall(r"\bquadrants?\b", t, re.I)) >= 2 or bool(re.search(r"\b2\s*[x×]\s*2\b|\bcollage\b", t, re.I))


def grid_on_black(pic, content):
    """The 9:16 asset of a grid: the made 4:5 grid exactly where the finish taped it down, black above and below
    (the owner, 2026-10-25, on the tier list: the painted strips put a tile wall under the cookies)."""
    from PIL import Image
    sys.path.append(str(P.REPO / "tools" / "image-production"))
    from image_production import providers as PR
    if not content.is_file():
        return False
    im = Image.open(pic).convert("RGB")
    cw, ch = Image.open(content).size
    box = PR.zone_box(cw, ch, *im.size)
    tall = Image.new("RGB", im.size, (0, 0, 0))
    tall.paste(im.crop(box), box[:2])
    tall.save(pic)
    return True


def text_boxes(pic):
    """Every line of words macOS Vision reads on a picture: (left, top, width, height) in pixels, and the words."""
    exe, src = HERE / "vision" / ".build" / "textboxes", HERE / "vision" / "textboxes.swift"
    if not exe.is_file() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], capture_output=True)
    if not exe.is_file():
        return []
    from PIL import Image
    W, H = Image.open(pic).size
    boxes = []
    for line in subprocess.run([str(exe), str(pic)], capture_output=True, text=True).stdout.splitlines():
        nums, _, words = line.partition("\t")
        l, t, w, h = (float(x) for x in nums.split())
        boxes.append(((l * W, t * H, w * W, h * H), words))
    return boxes


def words_on_top(pic, drawn):
    """The words stay over the product, as on the swipe (the owner, 2026-10-25: products pasted in "look like cut-outs"
    when the real one is laid over the caption it sat behind). Each line of words read on the drawn picture is put
    back over the pasted one: its white letters and their dark outline and shadow, nothing else in the line's box."""
    from PIL import Image, ImageChops, ImageFilter
    if not drawn.is_file():
        return 0
    a, d = Image.open(pic).convert("RGB"), Image.open(drawn).convert("RGB")
    if a.size != d.size:
        return 0
    W, H = a.size
    content = drawn.parent.parent / "generated" / drawn.name
    if content.is_file():
        # the words as the model first set them: a picture laid in twice has already lost them from drawn/
        sys.path.append(str(P.REPO / "tools" / "image-production"))
        from image_production import providers as PR
        c = Image.open(content).convert("RGB")
        box = PR.zone_box(*c.size, W, H)
        d = d.copy()
        d.paste(c.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])
        import tempfile
        drawn = Path(tempfile.mkdtemp()) / drawn.name                # read by Vision, then left to the temp folder
        d.save(drawn)
    r, g, b = d.split()
    lo, hi = ImageChops.darker(ImageChops.darker(r, g), b), ImageChops.lighter(ImageChops.lighter(r, g), b)
    lit = ImageChops.multiply(lo.point(lambda v: 255 if v > 205 else 0),             # white letters, not tinted
                              ImageChops.subtract(hi, lo).point(lambda v: 255 if v < 30 else 0))
    keep = Image.new("L", (W, H), 0)
    n = 0
    for (l, t, w, h), _words in text_boxes(drawn):
        pad = max(4, int(h * 0.35))
        box = (max(0, int(l - pad)), max(0, int(t - pad)), min(W, int(l + w + pad)), min(H, int(t + h + pad)))
        grow = max(3, int(h * 0.18)) | 1                    # the outline and the hard shadow around each letter
        m = lit.crop(box).filter(ImageFilter.MaxFilter(grow))
        keep.paste(ImageChops.lighter(keep.crop(box), m), box[:2])
        n += 1
    if n:
        Image.composite(d, a, keep.filter(ImageFilter.GaussianBlur(0.8))).save(pic)
    return n


def is_grid(run):
    """A swipe laid out as tiles (a 2x2 checklist, a collage): its tall version is the grid on black, the way the
    app shows a slideshow photo, never a painted strip that runs one tile's scene into its neighbour's."""
    spec = run / "out" / "02-replication-spec.md"
    t = spec.read_text(errors="replace") if spec.is_file() else ""
    return len(re.findall(r"\bquadrants?\b", t, re.I)) >= 2 or bool(re.search(r"\b2\s*[x×]\s*2\b|\bcollage\b", t, re.I))


def grid_on_black(pic, content):
    """The 9:16 asset of a grid: the made 4:5 grid exactly where the finish taped it down, black above and below
    (the owner, 2026-10-25, on the tier list: the painted strips put a tile wall under the cookies)."""
    from PIL import Image
    sys.path.append(str(P.REPO / "tools" / "image-production"))
    from image_production import providers as PR
    if not content.is_file():
        return False
    im = Image.open(pic).convert("RGB")
    cw, ch = Image.open(content).size
    box = PR.zone_box(cw, ch, *im.size)
    tall = Image.new("RGB", im.size, (0, 0, 0))
    tall.paste(im.crop(box), box[:2])
    tall.save(pic)
    return True


def refinish(run, brand, slug):
    """The finishing steps again on the delivered pictures, from what the model first made (generated/, the 4:5)
    taped back into the 9:16 it was finished to (drawn/): for a fix to finishing that should not cost a re-draw."""
    import datetime as dt, shutil
    from PIL import Image
    sys.path.append(str(P.REPO / "tools" / "image-production"))
    from image_production import providers as PR
    out = P.REPO / "runs" / "image-teardown" / brand / run.name / "pictures"
    pics = [p for p in sorted(out.glob("*.png")) if (out / "generated" / p.name).is_file()]
    if not pics:
        print(f"{run.name}: no delivered picture with its original in generated/ — nothing to refinish")
        return 1
    old = out.parent / f"pictures-before-{dt.datetime.now():%Y%m%d%H%M%S}"
    old.mkdir()
    src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    grid = is_grid(run)
    for pic in pics:
        shutil.copy2(pic, old / pic.name)
        base = Image.open(out / "drawn" / pic.name if (out / "drawn" / pic.name).is_file() else pic).convert("RGB")
        c = Image.open(out / "generated" / pic.name).convert("RGB")
        box = PR.zone_box(*c.size, *base.size)
        base.paste(c.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])
        base.save(pic)
        if grid:
            grid_on_black(pic, out / "generated" / pic.name)
    print(f"{run.name} · refinishing {len(pics)} pictures (earlier versions in {old.name}/)" + (" · a grid" if grid else ""))
    real_product(brand, slug, product_name(brand, slug), pics, out)
    if src:
        for pic in pics:
            if pic.is_file():
                print(f"  matched to the swipe's fidelity: {pic.name} ({native_finish(pic, src, out / 'polished')})")
    return 0


def real_product(brand, slug, name, pictures, out):
    """The drawn product out, the real one in, on every delivered picture. Nothing drawn ships."""
    import importlib.util, json, shutil
    mach = P.REPO / "tools" / "video-production" / "machine"

    def load(n):
        spec = importlib.util.spec_from_file_location(n, str(mach / (n + ".py")))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    kit = load("element_paths").product_kit(brand, slug)
    paste = load("product_paste")
    # what the finder looks for: the kit's own words for the product (kit.json `what`), so any product with a kit
    # can be laid in, not only the one this line was first written for
    import json as _json
    looks = (_json.loads((kit / "kit.json").read_text()).get("what") if kit and (kit / "kit.json").is_file() else None) \
        or "the product"
    what = f"the {name} product ({looks})"
    # what the finder looks for: the kit's own words for the product (kit.json `what`), so any product with a kit
    # can be laid in, not only the one this line was first written for
    looks = (json.loads((kit / "kit.json").read_text()).get("what") if kit and (kit / "kit.json").is_file() else None) \
        or "the product"
    what = f"the {name} product ({looks})"
    for pic in pictures:
        if not pic.is_file():
            continue
        (out / "drawn").mkdir(exist_ok=True)
        shutil.copy2(pic, out / "drawn" / pic.name)
        r = paste.run(str(pic), str(kit), str(pic), what=what, shadow=True) \
            if kit else {"ok": False, "why": [f"no product kit for {slug}"]}
        if r.get("ok") and not r.get("skipped") and (r.get("overlap") or 0) < FIT:
            r = {"ok": False, "why": [f"the found shape fits the real product only {r.get('overlap')}: likely not the product (a neck, a bump)"]}
            shutil.copy2(out / "drawn" / pic.name, pic)
        if r.get("ok") and not r.get("skipped"):
            n = words_on_top(pic, out / "drawn" / pic.name)
            print(f"  real {name} laid in: {pic.name} (angle {r.get('angle')}, fit {r.get('overlap')}"
                  + (f", {n} lines of words kept on top" if n else "") + ")")
            continue
        why = r.get("skipped") or "; ".join(r.get("why") or ["the paste failed"])
        (out / "rejected").mkdir(exist_ok=True)
        shutil.move(str(pic), str(out / "rejected" / pic.name))
        (out / "rejected" / (pic.stem + "-why.md")).write_text(
            f"HELD: the real {name} could not be laid over the drawn one ({why}). A drawn product never ships.\n")
        print(f"  ✗ {pic.name} held: the real {name} could not be laid in ({why})")


def refinish(run, brand, slug):
    """The finishing steps again on the delivered pictures, from what the model first made (generated/, the 4:5)
    taped back into the 9:16 it was finished to (drawn/): for a fix to finishing that should not cost a re-draw."""
    import datetime as dt, shutil
    from PIL import Image
    sys.path.append(str(P.REPO / "tools" / "image-production"))
    from image_production import providers as PR
    out = P.REPO / "runs" / "image-teardown" / brand / run.name / "pictures"
    pics = [p for p in sorted(out.glob("*.png")) if (out / "generated" / p.name).is_file()]
    if not pics:
        print(f"{run.name}: no delivered picture with its original in generated/ — nothing to refinish")
        return 1
    old = out.parent / f"pictures-before-{dt.datetime.now():%Y%m%d%H%M%S}"
    old.mkdir()
    src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    grid = is_grid(run)
    for pic in pics:
        shutil.copy2(pic, old / pic.name)
        base = Image.open(out / "drawn" / pic.name if (out / "drawn" / pic.name).is_file() else pic).convert("RGB")
        c = Image.open(out / "generated" / pic.name).convert("RGB")
        box = PR.zone_box(*c.size, *base.size)
        base.paste(c.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS), box[:2])
        base.save(pic)
        if grid:
            grid_on_black(pic, out / "generated" / pic.name)
    print(f"{run.name} · refinishing {len(pics)} pictures (earlier versions in {old.name}/)" + (" · a grid" if grid else ""))
    real_product(brand, slug, product_name(brand, slug), pics, out)
    if src:
        for pic in pics:
            if pic.is_file():
                print(f"  matched to the swipe's fidelity: {pic.name} ({native_finish(pic, src, out / 'polished')})")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("--brand", required=True); ap.add_argument("--product", required=True)
    # one picture each (the owner: "Stop doing 3 versions each, remove that from the process"; V33 "just do 1 per")
    ap.add_argument("--count", type=int, default=1); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--note", help="one more line for this picture only, e.g. what a held picture got wrong")
    ap.add_argument("--fresh", action="store_true", help="made from the written plan alone, without the swipe as picture reference (the swipe's real face or logo keeps coming back)")
    ap.add_argument("--no-product", action="store_true", help="the picture shows no product at all (upper funnel may run without it); nothing drawn can slip in")
    ap.add_argument("--product-at", help="put the product in the picture at this spot, whatever the brand step said, e.g. 'on the barber's counter beside the clippers' (the owner, 2026-10-25: \"just put the device in the image in a relevant position\"); the drawn one is then swapped for the real product")
    ap.add_argument("--round", type=int, default=1, help="a later round of the same concept: new file names, never over the earlier pictures (a concept ships as six)")
    ap.add_argument("--controlled", action="store_true", help="the old path: image-production make.py with its house prompt, judge and holds, then the real product pasted over and the swipe's grain (the plain one call is the default since 2026-10-25)")
    ap.add_argument("--refinish", action="store_true", help="re-run every step after the picture model (the real product, the words on top, the swipe's fidelity) on the pictures already made, from the model's own originals; nothing is drawn again and the earlier versions are set aside, never deleted")
    ap.add_argument("--refinish", action="store_true", help="re-run every step after the picture model (the grid, the real product, the words on top, the swipe's fidelity) on the pictures already made, from the model's own originals; nothing is drawn again and the earlier versions are set aside, never deleted")
    a = ap.parse_args()
    run = Path(a.run)
    if not run.is_absolute():
        run = (HERE.parent / a.run) if (HERE.parent / a.run).is_dir() else P.run_dir(a.run, a.brand)
    if a.refinish:
        sys.exit(refinish(run, a.brand, a.product))
    if a.refinish:
        sys.exit(refinish(run, a.brand, a.product))
    inj = run / "out" / "03-injection.md"
    if not inj.is_file():
        sys.exit(f"{run.name}: no brand step yet (out/03-injection.md) — run stage 3 first")
    t = inj.read_text()
    # NEVER STERILE (the owner, 2026-10-23: "we don't want any sterile ads at all"):
    # a brand step whose dials sit under the floor, whichever account wrote it,
    # is not made into pictures. Re-run stage 3 on a login that clears it.
    import importlib.util
    spec = importlib.util.spec_from_file_location("creative_controls", str(P.REPO / "components/creative-controls/creative_controls.py"))
    cc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cc)
    sterile = cc.floor_problems(t)
    if sterile:
        sys.exit(f"{run.name}: HELD, the brand step is under the never-sterile floor: " + "; ".join(sterile))
    if not labelled(t, "SWAPS") or not section(t, "1. THE INJECTED FRAME", "2. THE SUBJECT"):
        sys.exit(f"{run.name}: HELD, the brand step's swap or its words could not be read; the picture would copy the swipe")
    name = product_name(a.brand, a.product)
    in_frame = product_in_frame_for(run, t, name)
    if a.product_at:
        in_frame = True
        a.note = ((a.note + " ") if a.note else "") + (f"The {name} (exactly as in the product reference, at its real size) sits {a.product_at}, "
                                                        "resting naturally, clearly visible, nothing covering it; it is part of the scene, not the subject.")
    elif a.no_product:
        in_frame = False
        a.note = ((a.note + " ") if a.note else "") + f"No {name}, no product and no device anywhere in the picture."
    out = P.REPO / "runs" / "image-teardown" / a.brand / run.name / "pictures"
    print(f"{run.name} · product {'in frame' if in_frame else 'not in frame'} ({name}) → {out}")
    if not a.controlled and not a.dry_run:
        print(f"{run.name} · the plain way (one call; --controlled for the old path)")
        made = plain_pictures(run, a.brand, a.product, t, out, a.count, not a.fresh, in_frame, a.note, a.round)
        sys.exit(0 if made else 1)
    r = make(run, a.brand, a.product, t, out, a.count, not a.fresh, in_frame, a.dry_run, a.note, a.round)
    if r.returncode and REFUSED.search(r.stdout + r.stderr):
        print("  the picture model refused the swipe as reference; once more from the words alone")
        r = make(run, a.brand, a.product, t, out, a.count, False, in_frame, a.dry_run, a.note, a.round)
    if is_grid(run) and not a.dry_run:
        for m in re.findall(r"✓ (\S+\.png)", r.stdout + r.stderr):
            pic = Path(m) if Path(m).is_absolute() else P.REPO / m
            if pic.is_file() and grid_on_black(pic, out / "generated" / pic.name):
                print(f"  a grid: the tall version is the grid on black ({pic.name})")
    if in_frame and not a.dry_run:
        real_product(a.brand, a.product, name, [Path(m) for m in re.findall(r"✓ (\S+\.png)", r.stdout + r.stderr)], out)
    src = next((p for p in (run / "assets").glob("source.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
    if src and not a.fresh and not a.dry_run:
        for m in re.findall(r"✓ (\S+\.png)", r.stdout + r.stderr):
            pic = Path(m) if Path(m).is_absolute() else P.REPO / m
            if pic.is_file():
                f = native_finish(pic, src, out / "polished")
                print(f"  matched to the swipe's fidelity: {pic.name} ({f})")
    tail = [l for l in (r.stdout + r.stderr).splitlines() if re.search(r"delivered|✓|✗|nothing was generated|Error", l)]
    print("\n".join("  " + l.strip()[:240] for l in tail[-6:]))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
