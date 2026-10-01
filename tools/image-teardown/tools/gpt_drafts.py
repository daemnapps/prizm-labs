#!/usr/bin/env python3
"""Draft pictures for the briefs the chain already wrote.

    gpt_drafts.py --briefs p152,p153 --out drafts/<brand>/v1
    gpt_drafts.py --brand <brand> --count 2
    gpt_drafts.py --brand <brand> --match-swipe --out drafts/<brand>/v5

**The model — GPT Image 2.5, through OpenAI's own door** (Damon, 2026-09-22:
*"everything image needs to just be gpt now, literally that's it"*). One door
for pictures means one look across a batch and one set of quirks. GPT Image
2.5 takes ANY size whose sides both divide by 16, so 9:16 is 1152x2048 and 4:5
is 1024x1280 natively (asked of the API that day).

**fal is gone** (Damon, 2026-09-22: *"remove anything with fal or flux lora,
we decided to not use these tools"* — the third time it was ruled, after
2026-09-11 and 09-13). This file used to carry `fal-ai/nano-banana-pro/edit`
behind a `--door fal` flag "so a record that says fal is reproducible". The
flag, the queue client and the model id are all removed; the old records still
name what drew them, and nothing here can reach fal again. Renamed off the fal
name the same day.

**--match-swipe** (Damon, 2026-09-17: *"the drafts are NOT close enough to
the inspiration, we need to be way closer"*). Until now the swipe never
reached the generator — it saw the cast, the product and a paragraph, and a
paragraph cannot carry a composition. With this flag `source.jpg` goes in as
the first reference and the prompt opens by saying so: reproduce IMAGE 1's
framing, pose, crop, angle, light and layout exactly; the person, the product
and the words are the only things that change. Where the brief's description
disagrees with the swipe about framing, the swipe wins.

**Elements resolve to pictures, not uuids.** Higgsfield resolves `<<<uuid>>>`
in a prompt into a banked Element — the cast's face, the product's real
geometry. No other door has that, so a uuid would reach the model as literal
punctuation and every face and every tube would be invented. Each uuid is
resolved back to the image it was built from, on Drive, and passed as a
reference: *"the element_id is a pointer into one Higgsfield workspace and is
the disposable half… nothing is lost in the move because the image is the
asset."*
"""
import argparse, base64, json, mimetypes, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.home() / ".daemn"))
import paths as P
import briefs as B
sys.path.insert(0, str(P.IMAGE_PROD / "tools"))
import product_geometry as PGEO
import daemn_keys

ROOT = HERE.parent
MODEL = "gpt-image-2.5 (openai)"
MODEL_WHY = ("one door for pictures (Damon, 2026-09-22). GPT Image 2.5 through "
             "OpenAI directly; it makes 9:16 and 4:5 natively.")
# <media>/brands/<brand>/elements/... — the brand's element pictures, in
# your media folder.
ELEMENTS = P.DRIVE / "brands"


def _uri_to_file(uri, outdir, bid, n):
    """A data uri written to a file the engine can attach. Kept beside the run
    in a `.refs` folder so a roll can be reproduced from what it was given."""
    d = outdir / ".refs" / bid
    d.mkdir(parents=True, exist_ok=True)
    head, _, b64 = uri.partition(",")
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(
        head.split(";")[0].replace("data:", ""), ".png")
    f = d / f"{n:02d}{ext}"
    f.write_bytes(base64.b64decode(b64))
    return f


def data_uri(p: Path):
    mt = mimetypes.guess_type(p.name)[0] or "image/webp"
    return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()


def element_images(brand, prompt):
    """Every `<<<uuid>>>` in the prompt, as the picture it was built from.

    Returns (cleaned prompt, [data uris]). The uuid is stripped out of the
    text: it means nothing to fal, and leaving it in puts angle brackets and
    a hex string into the description the model reads.
    """
    idx = P.BP.brand_path(brand, "ai-elements", "index.json", root=P.BRANDS)
    by_id = {}
    if idx.is_file():
        for e in json.loads(idx.read_text()).get("elements", []):
            by_id[e["element_id"]] = e
    urls, used = [], []
    for uid in re.findall(r"<<<([0-9a-f-]{36})>>>", prompt):
        e = by_id.get(uid)
        if not e:
            print(f"    ! no banked image for {uid[:8]} — skipped")
            continue
        img = P.BP.resolve_rel(brand, e["source"], root=ELEMENTS)   # elements/<cat>/<img> in the index; ai-elements/<plural> on Drive
        if not img.is_file():
            print(f"    ! {e['name']}: image missing at {e['source']}")
            continue
        urls.append(data_uri(img)); used.append(e["name"])
    clean = re.sub(r"<<<[0-9a-f-]{36}>>>\.?\s*", "", prompt).strip()
    return clean, urls, used


def post(path, payload, k):
    req = urllib.request.Request(
        f"{QUEUE}/{path}", data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Key {k}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def get(url, k):
    req = urllib.request.Request(url, headers={"Authorization": f"Key {k}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


PROMPTS = ROOT / "prompts"


def _prompt(name):
    """A stage prompt, verbatim, comments stripped. The file is the only copy
    (DRAFT-STANDARD.md): a change is a new version file, never an edit here."""
    t = (PROMPTS / name).read_text()
    return re.sub(r"<!--.*?-->\s*", "", t, flags=re.S)


def _section(name, after=None, before=None):
    t = _prompt(name)
    if after:
        t = t.split(after, 1)[1]
    if before:
        t = t.split(before, 1)[0]
    return t.strip() + "\n"


# The opening of every draft prompt whose swipe has an adult in it, with the
# {offer} line; then OUR WOMAN, THE WORDS and the cropping clause follow.
MATCH_FILE = "stage7-draft-match-swipe-v2-damon.md"
LEAVE_FILE = "stage7-draft-leave-alone-v1-damon.md"
WORDS_FILE = "stage7-draft-words-v5-damon.md"
MATCH = _prompt(MATCH_FILE).strip() + "\n"          # v2: filled by .replace()
# v4 — the model draws the words again, but told EXACTLY which words, where,
# how big, what colour and — new — how the lettering is MADE, read off the
# swipe. Used whenever the brief carries a type layer. v2 stays for a swipe
# whose text is incidental and has no layer to be specific from.
#
# It replaces v3 (plate-only + compose.py), retired by Damon on 2026-09-25
# the day it was demonstrated: "the nuance of the style of the creative is
# lost… claymation-style text is going to look different than you just
# writing text on an image." A font cannot be moulded clay, and the
# compositor had its own defects besides — it stacked "2016" down the frame
# where the swipe reads "20 16" across. v3 is in superseded/.
WORDS = _prompt(WORDS_FILE).strip() + "\n"
NO_PERSON = _section(LEAVE_FILE, before="<the frame")


def _product_notes(brand, slug):
    """What a product file does not say in a parseable line, the machine
    keeps in its own file: drafts/<brand>/products.json — treats, texture,
    a clean picture. brands/ is read-only to machines (the workspace rules §5)."""
    f = ROOT / "drafts" / brand / "products.json"
    return (json.loads(f.read_text()) if f.is_file() else {}).get(slug, {})


def brand_facts(brand, product=None):
    """What the v2 prompt needs from the brand, read off the brand's own files
    (never typed here — CLAUDE.md rule 7, brand-agnostic): the palette, what
    the product treats, its texture line, its pictures and the range.

    `product` is the brief's own (a variant run carries a different product
    on the same swipe, 2026-09-18); the brand's baseline product otherwise."""
    b = P.BRANDS / brand
    f = {"accent_name": "our accent", "accent_hex": "", "type_hex": "#111111",
         "treats": "the skin the product is for", "treats_short": "that skin",
         "texture": "our product's own texture", "identity": None, "range": []}
    pal = b / "identity/palette.md"
    if pal.is_file():
        rows = re.findall(r"^\| \*\*(.+?)\*\* \| `(#[0-9A-Fa-f]{6})` \|", pal.read_text(), re.M)
        if rows:
            f["accent_name"], f["accent_hex"] = rows[0][0], rows[0][1]
            m = re.search(rf"\| \*\*{re.escape(rows[0][0])}\*\* \| `{rows[0][1]}` \| (.+?) \|", pal.read_text())
            f["accent_desc"] = m.group(1).split(" — ")[0].strip() if m else rows[0][0]
            for n, h in rows:
                if n.lower() == "type":
                    f["type_hex"] = h
    base = json.loads((ROOT / "drafts" / brand / "baseline.json").read_text())
    slug = product or base.get("product", "")
    notes = _product_notes(brand, slug)
    prod = P.product(brand, slug)
    if prod.is_file():
        t = prod.read_text()
        m = re.search(r"## What it is\s*\n+(.+?)\n", t)
        if m:
            m2 = re.search(r"—\s*([^.]+)\.", m.group(1))
            if m2:
                f["treats"] = m2.group(1).strip()
                parts = [x.strip() for x in re.split(r",|\band\b", f["treats"]) if x.strip()]
                f["treats_short"] = " or ".join(parts[:3]) if parts else f["treats"]
        m = re.search(r"Texture:\s*\*\*(.+?)\*\*", t, re.S)
        if m:
            f["texture"] = re.sub(r"\s+", " ", m.group(1))
    for k in ("treats", "treats_short", "texture"):
        if notes.get(k):
            f[k] = notes[k]
    imgs = b / "products/images.json"
    if imgs.is_file():
        d = json.loads(imgs.read_text()).get("products", {})
        me = d.get(slug) or {}
        # identity: the clean tube first, then the same product at an angle
        # in a scene and in a hand — one front view alone got pasted front-on
        # into every scene (Damon, 2026-09-17: "the same cutout of the bottle
        # over and over again regardless of what the subject in the original")
        cands = [x for x in me.get("all", []) if "packshot-tube" in x] + \
                [x for x in (me.get("hero"),) if x] + \
                [x for x in me.get("all", []) if "hand" in x]
        views, seen = [], set()
        # a clean picture the machine made for a product whose brand file
        # has none (drafts/<brand>/products/<slug>-tube.png) goes first
        clean = ROOT / "drafts" / brand / "products" / f"{slug}-tube.png"
        if clean.is_file():
            views.append(clean)
        for c in cands:
            if c not in seen and (b / c).is_file():
                seen.add(c); views.append(b / c)
        f["identity"] = views[0] if views else None
        f["views"] = views[:3]
        for other, rec in d.items():
            if other != slug and rec.get("hero") and (b / rec["hero"]).is_file():
                f["range"].append((rec.get("title", other), b / rec["hero"]))
        f["product_title"] = me.get("title", slug)
    return f


def offer_slots(brand, read, product=None):
    """THE OFFER SLOTS paragraph: the swipe's slots, each filled with ours.

    Damon, 2026-09-17: "the offer is missing and one of the guarantees is
    missing." A slot the swipe has is filled from the bank, never dropped."""
    facts = offer_facts(brand, product)
    price = next((x for x in facts if x.endswith(".00") and "tubes" not in x and "subscribe" not in x), "")
    price = re.sub(r"\$(\d+)\.00", r"$\1", price.split("$")[-1].join(["$", ""])) if price else ""
    multi = next((x for x in facts if "tubes" in x), "")
    multi = re.sub(r"\.00\b", "", multi)
    guar = next((x for x in facts if "Money Back" in x or "Guarantee" in x), "")
    guar_full = (guar.replace("Money Back", "Money-Back") + " Guarantee") if guar and "Guarantee" not in guar else guar
    slots = read.get("offer_slots") or {}
    out = []
    if slots.get("price") and price:
        out.append(f"its price callout reads exactly \"{price}\"")
    if slots.get("guarantee") and guar_full:
        out.append(f"its guarantee reads exactly \"{guar_full}\"")
    if slots.get("discount_bar"):
        # The hero offer, and only the hero: the product at its own price
        # with the guarantee. Damon, 2026-09-18, on a bar that read "3 for
        # <price>": "we should just be focused on the core hero offer for
        # that specific product." The bank's hero slot is unruled, so the
        # one-tube price + guarantee stands in until he rules it; multi-tube
        # and subscribe prices never fill a bar on their own.
        hero = _product_notes(brand, product or json.loads(
            (ROOT / "drafts" / brand / "baseline.json").read_text()).get("product", "")).get("hero_offer")
        bar = hero or " · ".join(x for x in (price, guar_full or guar) if x)
        out.append(f"its discount or urgency bar reads exactly \"{bar}\"")
    if not out:
        return "IMAGE 1 carries no offer, guarantee or price slot."
    return "IMAGE 1 carries these slots; ours keeps every one of them in the same place, filled with ours — " + "; ".join(out) + "."


NOTE = re.compile(r"unchanged|art direction|imagery|§|no text|n/a|see (the|stage|conflicts)"
                  r"|placeholder|tbd|verify against", re.I)
# A percentage is a discount claim. The bank has none (Damon, 2026-09-18: the
# hero offer only — the product at its price with the guarantee), so a words
# entry that carries one is a brief computing a saving off the multi-tube
# tiers, and it is dropped until he rules a discount into the bank.
DISCOUNT = re.compile(r"\d+\s*%|percent|save up to|% off", re.I)


def clean_words(words):
    """The brief's words with stage 6's notes-to-self taken out. Returns the
    'none' line when nothing real is left."""
    entries = re.findall(r'"([^"]+)"', words)
    if not entries:
        return "none — no text anywhere" if NOTE.search(words) else words
    keep = [w for w in entries if not NOTE.search(w) and not DISCOUNT.search(w)]
    return "; ".join(f'"{w}"' for w in keep) if keep else "none — no text anywhere"


def offer_block(brand):
    """v1's THE OFFER line; kept for the record, unused by the v2 prompt."""
    return ("THE OFFER. No price, discount, guarantee, date or offer appears "
            "anywhere unless it is in THE WORDS below.\n")


def offer_facts(brand, product=None):
    """Every number a draft may carry, read off the brand's offer bank, for
    this product (the brief's own; the baseline's otherwise)."""
    base = json.loads((ROOT / "drafts" / brand / "baseline.json").read_text())
    slug = product or base.get("product", "")
    bank = P.BRANDS / brand / "products/offer-bank.md"
    facts = []
    if bank.is_file():
        m = re.search(rf"^## {re.escape(slug)} — (.+?)\n(.*?)(?=^## |\Z)",
                      bank.read_text(), re.S | re.M)
        if m:
            name, body = m.group(1).strip(), m.group(2)
            pm = re.search(r"Price: \*\*(\$[\d.]+)\*\*", body)
            if pm:
                facts.append(f"{name} {pm.group(1)}")
            sm = re.search(r"Sizes: (.+)", body)
            if sm:
                for price, label in re.findall(r"(\$[\d.]+) \(([^)]+)\)", sm.group(1)):
                    n = re.search(r"(\d+) Tubes?", label)
                    if n and int(n.group(1)) > 1:
                        facts.append(f"{n.group(1)} tubes {price}")
            um = re.search(r"Subscribed: \*\*(\$[\d.]+)\*\*", body)
            if um:
                facts.append(f"subscribe {um.group(1)}")
    g = P.BRANDS / brand / "offers/guarantees.json"
    if g.is_file():
        for x in json.loads(g.read_text()).get("guarantees", {}).values():
            facts.append(x.get("short") or x.get("name"))
    return facts


READ_VERSION = 4          # v4 adds `lettering` (Damon, 2026-09-25)


def swipe_has_person(brand, jobs):
    """The swipe, read once and kept: who is in it, what it shows, how it is
    drawn, what slots it carries, what colour it leans on.

    v1 asked two questions (adult? product?). v2 (Damon, 2026-09-17: "we
    need to take note of the style of the original", "the offer is missing",
    "the colour of the text is not on brand") asks the rest, because a thing
    the prompt never heard about is a thing the swipe fills in by default."""
    cache = ROOT / "drafts" / brand / "swipe-subjects.json"
    known = json.loads(cache.read_text()) if cache.is_file() else {}
    todo = [j for j in jobs if known.get(j["brief"], {}).get("v") != READ_VERSION]
    if todo:
        import draft_judge as J
        k = daemn_keys.key("GEMINI_API_KEY")
        q = ("Read this advertising image and reply with JSON only.\n"
             "person: is an ADULT human the subject — an adult's face or body "
             "the main thing in it? A baby or child as the subject is false; an "
             "animal, object, product or scene is false; hands, legs or a lap at "
             "the edge holding something do not count.\n"
             "product: does it show a product — a bottle, tube, jar or package — "
             "anywhere, held, standing or as a packshot?\n"
             "product_count: how many distinct product units are shown (0 if none).\n"
             "style: one of \"photograph\", \"illustration\", \"flat graphic\", "
             "\"3d render\" — how the main image is made.\n"
             "skin_proof: if skin is shown as the proof (a close-up, an inset "
             "box, a before/after), which body part: \"face\", \"hands\", "
             "\"arms\", \"chest\", \"legs\", \"neck\" — else \"none\".\n"
             "offer_slots: {price: bool, guarantee: bool, discount_bar: bool} — "
             "does it carry a price callout, a guarantee line or badge, a "
             "discount/urgency bar?\n"
             "product_texture: does it show the product's contents out of the "
             "package — a smear, a swatch, a spread, a drop?\n"
             "accent_hex: the one chromatic accent colour used on words, badges, "
             "bars or arrows, as a hex, or \"none\".\n"
             "lettering: HOW THE WORDS ARE MADE — the material, surface and "
             "treatment of the letterforms, never a typeface name. Say what a "
             "person would have to do to build them: e.g. \"flat vector sans, "
             "solid fill, no effects\", \"moulded claymation letters, extruded "
             "with soft shadow\", \"hand-lettered marker on paper, uneven "
             "pressure\", \"chrome bevel with reflections\", \"white with a hard "
             "black outline, social-caption style\", \"cut-paper collage\", "
             "\"letterpress serif, slightly inked edges\", \"neon tube glow\", "
             "\"typed system UI caption\". One phrase. If the image carries no "
             "words at all, \"none\".\n"
             "subject: three words.\n"
             "{\"person\": true|false, \"product\": true|false, \"product_count\": n, "
             "\"style\": \"...\", \"skin_proof\": \"...\", \"offer_slots\": {...}, \"product_texture\": true|false, "
             "\"accent_hex\": \"...\", \"lettering\": \"...\", \"subject\": \"...\"}")
        for j in todo:
            src = P.RUNS / j["run"] / "assets/source.jpg"
            r = J.ask([src], q, k)
            known[j["brief"]] = {
                "v": READ_VERSION,
                "person": bool(r.get("person", True)),
                "product": bool(r.get("product", True)),
                "product_count": int(r.get("product_count") or (1 if r.get("product") else 0)),
                "style": r.get("style", "photograph"),
                "skin_proof": r.get("skin_proof", "none"),
                "offer_slots": r.get("offer_slots") or {},
                "product_texture": bool(r.get("product_texture", False)),
                "accent_hex": r.get("accent_hex", "none"),
                # HOW the words are built, not which font. Damon, 2026-09-25:
                # "claymation-style text is going to look different than you
                # just writing text on an image." Nothing recorded this until
                # now, so every draft's lettering was whatever the model felt
                # like — which is exactly the slop the swipe was meant to stop.
                "lettering": r.get("lettering", "plain set type"),
                "subject": r.get("subject", "?")}
        cache.write_text(json.dumps(known, indent=1))
    return known


def product_ref(brand):
    """The banked product picture, always — whether or not the brief named it.

    Twelve of twenty-one briefs never named the product, so the model drew a
    blue tube and a 'DermaWise' for them (2026-09-17)."""
    base = json.loads((ROOT / "drafts" / brand / "baseline.json").read_text())
    uid = (base.get("product_ref") or {}).get("element")
    idx = P.BP.brand_path(brand, "ai-elements", "index.json", root=P.BRANDS)
    if not (uid and idx.is_file()):
        return None, None
    for e in json.loads(idx.read_text()).get("elements", []):
        if e["element_id"] == uid:
            img = P.BP.resolve_rel(brand, e["source"], root=ELEMENTS)   # elements/<cat>/<img> today
            return (data_uri(img), e["name"]) if img.is_file() else (None, None)
    return None, None


def assemble(job):
    """The standard's prompt and references for one brief — the same thing
    the generator gets and the designer gets (worksheet.py), so the two can
    never differ. Returns (prompt, [reference file paths], [names])."""
    prompt, _, _ = element_images(job["brand"], job["prompt"])
    src = P.RUNS / job["run"] / "assets/source.jpg"
    if not src.is_file():
        return None, [], []
    crop = re.search(r"\b(9:16|4:5|1:1)\..*$", prompt, re.S)
    crop = crop.group(0).strip() if crop else ""
    read = job.get("read") or {}
    if job.get("leave_alone"):
        return NO_PERSON + crop, [src], ["swipe"]
    bf = brand_facts(job["brand"], job.get("product"))
    base = json.loads((ROOT / "drafts" / job["brand"] / "baseline.json").read_text())
    reads = (base.get("cast") or {}).get("reads", "a woman")
    words = re.search(r"the words this ad carries[^:]*:\s*(.+?)(?:\. Spell|\. NEGATIVE|$)",
                      prompt, re.S)
    words = words.group(1).strip() if words else "none — no text anywhere"
    words = clean_words(words)
    n = int(read.get("product_count") or 0) if read.get("product", True) else 0
    refs, used = [src], ["swipe"]
    # A PERSON-FREE PLATE MUST NOT BE HANDED A PICTURE OF A PERSON. The
    # product's views include `body-scrub-in-hand` — the scrub on skin — and
    # for a frame that says "no person, no hands" the model copies it rather
    # than the swipe: all twelve rolls of p187-p190 came back as a woman
    # applying product, with the offer text gone and a smear on her shoulder
    # (2026-09-24). The judge caught every one, which is the system working;
    # the reference should not have been sent at all.
    # HANDS, not faces. A frame can say "no faces, no bodies" and still be
    # four hands holding the product — p186 is exactly that, and stripping
    # its in-hand reference took away the only picture we own of the correct
    # grip, which is what made the hands look wrong (Damon, 2026-09-24:
    # "hands are awkwardly holding the tubes"). Strip the skin references
    # only when the frame genuinely has no hands in it.
    # Test the FRAME'S OWN description, not the whole assembled prompt. Two
    # blocks ride on every prompt and describe no particular picture: the
    # 9:16 safe-zone note ("the subject's face, the eye line, the hands, the
    # body part the proof is on") and the NEGATIVE line. Both name hands, so
    # a frame that plainly says "No person, no hands" tested as having them,
    # the skin reference was attached, and all twelve rolls came back as the
    # reference photo rather than the ad (2026-09-24, twice).
    described = re.split(r"COMPOSITION FOR CROPPING|NEGATIVE:", prompt)[0]
    peopleless = bool(re.search(r"\bno (?:hands?|person|people|figures?)\b",
                                described, re.I)) and not re.search(
        r"\bhands?\b", re.sub(
            r"\bno (?:hands?|person|people|figures?)\b", " ", described, flags=re.I), re.I)
    views = bf.get("views") or []
    if peopleless:
        views = [v for v in views
                 if not re.search(r"hand|skin|arm|leg|model|hold", v.stem, re.I)]
    if n > 0 and views:
        for v in views:
            refs.append(v); used.append(v.stem)
    # THE BRIEF WINS OVER THE SWIPE'S PRODUCT COUNT. `n` is how many products
    # the SOURCE showed, and "several in the source, so show our range" is
    # right for a range ad and wrong for every ad that repeats one product.
    # p186 is four of the same tube by decision — its brief says "every tube
    # identical" in its anchors and records in CONFLICTS that the source's
    # catalogue-variety reading deliberately does not survive. The generator
    # read none of that, attached the face scrub and the body cream, and
    # returned jars and boxes (2026-09-24). A brief that says the products
    # are identical is the brief answering this question already.
    one_product = bool(job.get("one_product"))
    if one_product:
        range_rule_note = (" Every unit in frame is the SAME product — ours — "
                           "and no other product of ours appears.")
    else:
        range_rule_note = ""
    if n > 1 and bf.get("range") and not one_product:
        for title, img in bf["range"][:max(0, n - 1)]:
            refs.append(img); used.append(img.parent.parent.name)
        names = [bf.get("product_title", "our product")] + [t for t, _ in bf["range"][:max(0, n - 1)]]
        range_rule = (f"The first {len(views)} reference image(s) after IMAGE 1 show OUR "
                      f"product from several angles — render it at IMAGE 1's angle. IMAGE 1 "
                      "shows several products, so ours shows our range, one each, the "
                      "remaining reference images in order: " + ", ".join(names)
                      + (" — and repeats ours to make up the count." if n > len(names) else "."))
    elif n > 0:
        range_rule = (f"The {len(views)} reference image(s) after IMAGE 1 show the same "
                      "product — ours — from several angles; use them to render it at "
                      "IMAGE 1's angle, in IMAGE 1's light. One product: ours."
                      + range_rule_note)
    # THE OBJECT'S OWN PROPORTION, MEASURED. Every product fact the prompt
    # leaves unsaid is invented at generation time, and when the swipe being
    # rebuilt holds a different SHAPE of container the rebuild inherits that
    # shape — four jar-shaped "tubes" on 2026-09-24, then a second pass that
    # was closer only because the number had been typed into one brief by
    # hand. It is read off the brand's own packshot now, for any brand and
    # any product, so no brief has to carry it and none can get it wrong.
    if n > 0:
        try:
            geo = PGEO.describe(job["brand"], job.get("product") or "")
            # The grip belongs only to a frame that has a hand in it. On a
            # product-only plate it reads as an instruction to add one.
            line = PGEO.sentence(geo, grip=not peopleless)
        except Exception:
            line = ""
        if line:
            range_rule += " " + line
    else:
        range_rule = ("IMAGE 1 shows no product, so ours shows none: no tube, no "
                      "jar, nothing held, nothing on a surface.")
    texture_rule = (f"IMAGE 1 shows the product's contents, so ours does too, and it is ours: {bf['texture']}."
                    if read.get("product_texture") else
                    "IMAGE 1 shows no smear, swatch or spread of product, so ours shows none — the package only.")
    # WHICH PROMPT. A brief that carries a type layer has its words set by the
    # compositor, so the picture must carry none — asking the model for them
    # is how a competitor's headline, code and dates ended up rendered into
    # four of our ads (2026-09-24). A brief with no type layer keeps v2.
    layer = type_layer(job)
    base = WORDS if layer else MATCH
    spec, _v = word_spec({"elements": layer}) if layer else ("", None)
    keep = keep_clear_lines(job, layer)
    prompt = (base.replace("{style}", "a " + str(read.get("style") or "photograph"))
              .replace("{keep_clear}", keep)
              .replace("{reads}", reads)
              .replace("{treats}", bf["treats"]).replace("{treats_short}", bf["treats_short"])
              .replace("{product_count}", str(n))
              .replace("{range_rule}", range_rule)
              .replace("{texture_rule}", texture_rule)
              .replace("{words}", words)
              .replace("{word_spec}", spec)
              .replace("{lettering}", lettering_from(
                  layer, str(read.get("lettering") or "plain set type")))
              .replace("{offer_slots}", offer_slots(job["brand"], read, job.get("product")))
              .replace("{accent_desc}", bf.get("accent_desc", bf["accent_name"]))
              .replace("{accent_name}", bf["accent_name"]).replace("{accent_hex}", bf["accent_hex"])
              .replace("{type_hex}", bf["type_hex"])
              .replace("{crop}", crop))
    return prompt, refs, used


def type_layer(job):
    """The brief's own type layer: every word this ad carries, as data.

    Stage 6 emits it as a fenced json block with an `elements` array, in the
    shape compose.py reads. When it is there the words are SET, not drawn."""
    run = P.RUNS / job["run"] / "out/06-brief.md"
    if not run.is_file():
        return None
    t = run.read_text(errors="replace")
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", t, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        els = d.get("elements")
        if isinstance(els, list) and els and all(
                isinstance(e, dict) and "text" in e for e in els):
            return els
    return None


def num(v, default=None):
    """A number out of the layer, or the default. Layers carry "8", 8, "8%"
    and None in the same field."""
    try:
        return float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return default


WHERE = [(0, 12, "at the very top"), (12, 30, "in the upper third"),
         (30, 55, "across the middle"), (55, 78, "in the lower third"),
         (78, 101, "at the very bottom")]


def _where(top):
    for lo, hi, word in WHERE:
        if lo <= top < hi:
            return word
    return "in the frame"


def _size(cap):
    """Cap height as a share of frame height, said in words as well as a
    number. A model given only "cap_pct: 27" sets it politely; a model told
    "enormous — it dominates the frame" sets it like the swipe does."""
    if cap >= 18:
        return "enormous — it dominates the frame"
    if cap >= 10:
        return "very large — the first thing read"
    if cap >= 5:
        return "large"
    if cap >= 3:
        return "medium"
    return "small"


def lettering_from(layer, fallback):
    """How this ad's letters are made, preferring what the teardown recorded.

    Damon, 2026-09-25: *"we need to get really deep on the teardown record
    itself on these images."* The teardown looks at the swipe properly, once,
    and writes `letterform` per zone; the swipe read in this file is a second,
    shallower look taken only because nothing carried the first one forward.
    So the record wins, and the read is the fallback for runs torn down before
    the field existed.

    The largest element's letterform speaks for the ad — the headline is what
    sets a format's lettering, and a fine-print line set in plain type under a
    moulded headline must not be allowed to describe the whole picture.
    """
    best, big = None, -1.0
    for e in (layer or []):
        lf = str(e.get("letterform") or "").strip()
        if not lf or lf.startswith("[NONE"):
            continue
        cap = num(e.get("cap_pct"), 0) or 0
        if cap > big:
            best, big = lf, cap
    return best or fallback


def word_spec(layer, variant=None):
    """Every line this plate carries, as instructions rather than prose.

    The brief already wrote all of this down and none of it reached the
    model: v2 scraped ONE sentence out of the brief's prose with a regex,
    which is how "2016" and "WEEK 1 / WEEK 3 / WEEK 6" got invented and a
    competitor's quote got copied off the swipe (2026-09-24 and -09-25).

    A type layer carries its headline variants as `file` values — `control`,
    `v0`…`v5` — with `all` on the lines every version shares. The PLATE gets
    the control: the variants are different pictures and belong to stage 5,
    which is the pass that decides what is worth another generation.
    """
    els, seen_variant, dropped = [], variant, []
    for e in layer.get("elements") or []:
        # A PRODUCT'S OWN LABEL IS NOT THE AD'S TYPE. Stage 6 v5 marks any
        # element whose words sit on a package or object in the scene; drawing
        # those prints the ad's own copy across the front of our product. A
        # tube carrying its real label (name, ingredients)
        # came back tan, reading "<the swipe's own product name>" (2026-09-25 — Damon: "our tube is completely wrong…
        # the product's gotta be the product").
        # Honoured in code as well as asked for in the prompt, so a brief that
        # carries the flag is safe whatever the generator decides to do.
        if e.get("on_product") is True:
            dropped.append(str(e.get("text", ""))[:40])
            continue
        who = e.get("file", "all")
        who = [str(w) for w in (who if isinstance(who, list) else [who])]
        if "all" in who:
            els.append(e); continue
        if seen_variant is None:
            seen_variant = who[0]          # the first named variant is the control
        if seen_variant in who:
            els.append(e)
    if dropped:
        print(f"    word list · dropped {len(dropped)} on-product line(s): "
              + "; ".join(repr(x) for x in dropped[:3]))
    if not els:
        return "", None

    out = []
    for i, e in enumerate(els, 1):
        text = str(e.get("text", "")).strip()
        if not text:
            continue
        shown = text.replace("\n", " / ")
        bits = []
        top = num(e.get("top_pct"))
        if top is not None:
            bits.append(f"{_where(float(top))}, {float(top):g}% down")
        cap = num(e.get("cap_pct"))
        if cap is not None:
            bits.append(f"{_size(float(cap))} (cap height {float(cap):g}% of frame height)")
        if e.get("color"):
            bits.append(str(e["color"]))
        case = str(e.get("case", "")).lower()
        if case.startswith("upper"):
            bits.append("ALL CAPS")
        elif case.startswith("lower"):
            bits.append("lower case")
        if str(e.get("weight", "")).strip():
            bits.append(str(e["weight"]).strip())
        if e.get("align"):
            bits.append(f"{e['align']}-aligned")
        # HOW the letters are made, carried from the teardown's own record by
        # stage 6 v3. Per line, because one ad can set a moulded headline over
        # a flat-digital subhead and a rebuild that averages them loses both.
        lf = str(e.get("letterform") or "").strip()
        if lf and not lf.startswith("[NONE"):
            bits.append(f"letters MADE like this: {lf}")
        nl = "  (set on two lines, broken exactly where the slash is)" \
            if "\n" in text else ""
        out.append(f'  {i}. "{shown}"{nl}\n     ' + " \u00b7 ".join(bits))
    return "\n".join(out), seen_variant


def keep_clear_lines(job, layer):
    """The rectangles the compositor needs empty, as measured numbers.

    A model told "leave room for the headline" guesses; a model given
    "18-33% height, 2-98% width" is given the format. The numbers come from
    the type layer itself, so they cannot disagree with where the words land.
    """
    if not layer:
        return ""
    out, seen = [], set()
    for e in layer:
        try:
            t0 = float(e.get("top_pct"))
            l0 = float(e.get("left_pct", 0))
            r0 = float(e.get("right_pct", 100))
            h = float(e.get("cap_pct") or e.get("height_pct") or 6)
        except (TypeError, ValueError):
            continue
        row = (round(t0), round(min(100, t0 + h)), round(l0), round(r0))
        if row in seen:
            continue
        seen.add(row)
        out.append(f"- {row[2]}-{row[3]}% width, {row[0]}-{row[1]}% height — "
                   f"clean, even ground, nothing crossing it.")
    return "\n".join(out) or "- (this format declares no type zones)"


def with_read(brand, jobs):
    """Attach the swipe read and the modes to each job — what assemble() needs."""
    subj = swipe_has_person(brand, jobs)
    for j in jobs:
        slot = ROOT / "drafts" / brand / "slots" / f"{j['brief']}.json"
        kind = json.loads(slot.read_text()).get("swipe_kind", "paid") if slot.is_file() else "paid"
        j["leave_alone"] = kind == "organic" and not subj[j["brief"]]["person"]
        j["swipe_product"] = subj[j["brief"]].get("product", True)
        j["read"] = subj[j["brief"]]
    return jobs


def _engine():
    """The shared image engine, found beside this workspace — its OpenAI door,
    its key handling and its size table, so this file owns none of them."""
    here = Path(__file__).resolve()
    for d in here.parents:
        if (d / "components" / "image-production" / "models.json").is_file():
            path = str(d / "components" / "image-production")
            if path not in sys.path:
                sys.path.append(path)
            import image_production as IP
            return IP
    raise SystemExit("tools/image-production is not beside this workspace")


def openai_rolls(prompt, ref_paths, ratio, count, out_stem, outdir, existing=0):
    """`count` rolls through GPT Image, the references attached in order.

    One call per roll rather than n at once: the edits endpoint answers with a
    single picture, and a roll that fails should cost one roll, not the set.
    Returns (files, note)."""
    IP = _engine()
    entry = IP.route.table()["models"]["gpt-image-edit"]
    files = []
    for i in range(count):
        n = existing + i + 1
        f = outdir / f"{out_stem}-{n}.png"
        IP.providers.generate(entry, prompt, [Path(x) for x in ref_paths], f, ratio)
        files.append(f.name)
    return files, f"{count} roll(s) · gpt-image-edit · {ratio}"


def run_one(job, k, count, outdir, match=False):
    bid = job["brief"]
    prompt, refs, used = element_images(job["brand"], job["prompt"])
    if match:
        prompt, paths, used = assemble(job)
        if prompt is None:
            return bid, None, "no source.jpg to match"
        refs = [data_uri(x) for x in paths]
    # THE ONE DOOR. `paths` exists only on the match-swipe path; the
    # element path hands back data uris, so it is written to temp files
    # the engine can attach.
    try:
        if match:
            ref_paths = list(paths)
        else:
            ref_paths = [_uri_to_file(u, outdir, bid, n) for n, u in enumerate(refs, 1)]
        stem = f"{bid}-roll" if match else f"{bid}-draft"
        existing = 0
        if match:
            while (outdir / f"{stem}-{existing + 1}.png").is_file():
                existing += 1
        files, note = openai_rolls(prompt, ref_paths, job["ratio"], count,
                                   stem, outdir, existing)
        return bid, files, f"{note} · refs: {', '.join(used) or 'none'}"
    except Exception as e:                      # noqa: BLE001 — one brief's failure
        return bid, None, f"{type(e).__name__}: {str(e)[:200]}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand"); ap.add_argument("--briefs")
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--out")
    ap.add_argument("--match-swipe", action="store_true")
    a = ap.parse_args()

    reg = B.load()["briefs"]
    want = {x.strip() for x in a.briefs.split(",")} if a.briefs else None
    jobs = json.loads((ROOT / "drafts" / a.brand / "jobs.json").read_text())["jobs"]
    jobs = [j for j in jobs if (not want or j["brief"] in want)]
    if not jobs:
        sys.exit("no jobs match")

    if a.match_swipe:
        with_read(a.brand, jobs)
        print("left as they are (organic, no adult in it): " + (", ".join(
            j["brief"] for j in jobs if j["leave_alone"]) or "none") + "\n")

    outdir = Path(a.out) if a.out else ROOT / "drafts" / a.brand / "v1"
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)
    k = None
    print(f"{len(jobs)} drafts · {MODEL} · "
          f"{a.count} each → {outdir}\n")

    made = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futs = {pool.submit(run_one, j, k, a.count, outdir, a.match_swipe): j
                for j in jobs}
        for f in as_completed(futs):
            bid, files, note = f.result()
            print(("  ✓ " if files else "  ✗ ") + f"{bid}  {note}"
                  + (f"  [{len(files)}]" if files else ""))
            if files:
                made[bid] = files

    (outdir / "notes.json").write_text(json.dumps({
        "made": date.today().isoformat(),
        "model": MODEL, "why": MODEL_WHY, "engine": "openai", "match_swipe": a.match_swipe, "files": made}, indent=1))
    print(f"\n{len(made)} of {len(jobs)} drafted")


if __name__ == "__main__":
    main()
