#!/usr/bin/env python3
"""Draft pictures on fal, from the jobs the chain already wrote.

    fal_drafts.py --briefs p152,p153 --out drafts/<brand>/v1
    fal_drafts.py --brand <brand> --count 2
    fal_drafts.py --brand <brand> --match-swipe --out drafts/<brand>/v5

**--match-swipe** (Damon, 2026-09-17: *"the drafts are NOT close enough to
the inspiration, we need to be way closer"*). Until now the swipe never
reached the generator — it saw the cast, the product and a paragraph, and a
paragraph cannot carry a composition. With this flag `source.jpg` goes in as
the first reference and the prompt opens by saying so: reproduce IMAGE 1's
framing, pose, crop, angle, light and layout exactly; the person, the product
and the words are the only things that change. Where the brief's description
disagrees with the swipe about framing, the swipe wins.

Damon, 2026-09-15: *"generate with fal, not higgsfield."*

**Why this is not a straight swap.** Higgsfield resolves `<<<uuid>>>` in a
prompt into a banked Element — the cast's face, the product's real geometry.
fal has no such thing, so those uuids would reach the model as literal
punctuation and every face and every tube would be invented. That is the
device-slop failure by a different route.

The elements index anticipated this: *"the element_id is a pointer into one
Higgsfield workspace and is the disposable half… nothing is lost in the move
because the image is the asset."* So each uuid is resolved back to the image
it was built from, on Drive, and passed to fal as a reference.

**The model.** `fal-ai/nano-banana-pro/edit`, and that is a constraint rather
than a preference: fal does not host GPT Image 2 at all, and its gpt-image-1
offers only 1024x1024, 1536x1024 and 1024x1536 — neither of our ratios. This
one takes 4:5 and 9:16, 2K, and reference images.
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
import daemn_keys

ROOT = HERE.parent
MODEL = "fal-ai/nano-banana-pro/edit"
MODEL_WHY = ("fal has no GPT Image 2, and its gpt-image-1 cannot do 4:5 or "
             "9:16. This one takes both, plus reference images.")
QUEUE = "https://queue.fal.run"
# Shared Assets/brands/<brand>/elements/... — P.DRIVE points at the lab
# subtree, and the brand elements sit beside it, not under it.
ELEMENTS = P.DRIVE.parent.parent / "brands"


def key():
    return daemn_keys.key("FAL_KEY")


def data_uri(p: Path):
    mt = mimetypes.guess_type(p.name)[0] or "image/webp"
    return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()


def element_images(brand, prompt):
    """Every `<<<uuid>>>` in the prompt, as the picture it was built from.

    Returns (cleaned prompt, [data uris]). The uuid is stripped out of the
    text: it means nothing to fal, and leaving it in puts angle brackets and
    a hex string into the description the model reads.
    """
    idx = P.BRANDS / brand / "elements" / "index.json"
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
        img = ELEMENTS / brand / e["source"]
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
MATCH = _prompt(MATCH_FILE).strip() + "\n"          # v2: filled by .replace()
NO_PERSON = _section(LEAVE_FILE, before="<the frame")


def _product_notes(brand, slug):
    """What a product file does not say in a parseable line, the machine
    keeps in its own file: drafts/<brand>/products.json — treats, texture,
    a clean picture. brands/ is read-only to machines (CLAUDE.md §5)."""
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
    pal = P.brand(brand)["palette"]            # brand-identity/palette.md, old identity/
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
        # with the guarantee. Damon, 2026-09-18, on a bar that read "3 tubes
        # for $74": "we should just be focused on the core hero offer for
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
    bank = P.BRANDS / brand / "offers/offer-bank.md"
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


READ_VERSION = 3


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
             "subject: three words.\n"
             "{\"person\": true|false, \"product\": true|false, \"product_count\": n, "
             "\"style\": \"...\", \"skin_proof\": \"...\", \"offer_slots\": {...}, \"product_texture\": true|false, "
             "\"accent_hex\": \"...\", \"subject\": \"...\"}")
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
                "subject": r.get("subject", "?")}
        cache.write_text(json.dumps(known, indent=1))
    return known


def product_ref(brand):
    """The banked product picture, always — whether or not the brief named it.

    Twelve of twenty-one briefs never named the product, so the model drew a
    blue tube and a 'DermaWise' for them (2026-09-17)."""
    base = json.loads((ROOT / "drafts" / brand / "baseline.json").read_text())
    uid = (base.get("product_ref") or {}).get("element")
    idx = P.BRANDS / brand / "elements" / "index.json"
    if not (uid and idx.is_file()):
        return None, None
    for e in json.loads(idx.read_text()).get("elements", []):
        if e["element_id"] == uid:
            img = ELEMENTS / brand / e["source"]
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
    if n > 0 and bf.get("views"):
        for v in bf["views"]:
            refs.append(v); used.append(v.stem)
    if n > 1 and bf.get("range"):
        for title, img in bf["range"][:max(0, n - 1)]:
            refs.append(img); used.append(img.parent.parent.name)
        names = [bf.get("product_title", "our product")] + [t for t, _ in bf["range"][:max(0, n - 1)]]
        range_rule = (f"The first {len(bf['views'])} reference image(s) after IMAGE 1 show OUR "
                      f"product from several angles — render it at IMAGE 1's angle. IMAGE 1 "
                      "shows several products, so ours shows our range, one each, the "
                      "remaining reference images in order: " + ", ".join(names)
                      + (" — and repeats ours to make up the count." if n > len(names) else "."))
    elif n > 0:
        range_rule = (f"The {len(bf['views'])} reference image(s) after IMAGE 1 show the same "
                      "product — ours — from several angles; use them to render it at "
                      "IMAGE 1's angle, in IMAGE 1's light. One product: ours.")
    else:
        range_rule = ("IMAGE 1 shows no product, so ours shows none: no tube, no "
                      "jar, nothing held, nothing on a surface.")
    texture_rule = (f"IMAGE 1 shows the product's contents, so ours does too, and it is ours: {bf['texture']}."
                    if read.get("product_texture") else
                    "IMAGE 1 shows no smear, swatch or spread of product, so ours shows none — the package only.")
    prompt = (MATCH.replace("{style}", "a " + str(read.get("style") or "photograph"))
              .replace("{reads}", reads)
              .replace("{treats}", bf["treats"]).replace("{treats_short}", bf["treats_short"])
              .replace("{product_count}", str(n))
              .replace("{range_rule}", range_rule)
              .replace("{texture_rule}", texture_rule)
              .replace("{words}", words)
              .replace("{offer_slots}", offer_slots(job["brand"], read, job.get("product")))
              .replace("{accent_desc}", bf.get("accent_desc", bf["accent_name"]))
              .replace("{accent_name}", bf["accent_name"]).replace("{accent_hex}", bf["accent_hex"])
              .replace("{type_hex}", bf["type_hex"])
              .replace("{crop}", crop))
    return prompt, refs, used


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


def run_one(job, k, count, outdir, match=False):
    bid = job["brief"]
    prompt, refs, used = element_images(job["brand"], job["prompt"])
    if match:
        prompt, paths, used = assemble(job)
        if prompt is None:
            return bid, None, "no source.jpg to match"
        refs = [data_uri(x) for x in paths]
    payload = {"prompt": prompt, "image_urls": refs,
               "aspect_ratio": job["ratio"], "resolution": "2K",
               "num_images": count, "output_format": "png"}
    try:
        q = post(MODEL, payload, k)
    except urllib.error.HTTPError as e:
        return bid, None, f"submit failed {e.code}: {e.read()[:160].decode('utf8','replace')}"
    status_url = q.get("status_url")
    # fal's queue is slower than a poll loop is patient; 10 minutes is past
    # anything this model has taken and short of hanging a session.
    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(6)
        try:
            s = get(status_url, k)
        except Exception:
            continue
        if s.get("status") == "COMPLETED":
            res = get(q["response_url"], k)
            files = []
            for n, im in enumerate(res.get("images", []), 1):
                raw = urllib.request.urlopen(im["url"], timeout=120).read()
                        # every roll is a roll until the judge picks one
                if match:
                    # a second round keeps the first round's rolls: numbering
                    # continues from the next free slot
                    m = n
                    while (outdir / f"{bid}-roll-{m}.png").is_file():
                        m += count
                    f = outdir / f"{bid}-roll-{m}.png"
                else:
                    f = outdir / (f"{bid}-draft.png" if n == 1 else f"{bid}-draft-{n}.png")
                f.write_bytes(raw); files.append(f.name)
            return bid, files, f"refs: {', '.join(used) or 'none'}"
        if s.get("status") in ("FAILED", "ERROR"):
            return bid, None, f"failed: {json.dumps(s)[:180]}"
    return bid, None, "timed out after 10 minutes"


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
    k = key()
    print(f"{len(jobs)} drafts · {MODEL} · {a.count} each → "
          f"{outdir}\n")

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
        "made": date.today().isoformat(), "model": MODEL, "why": MODEL_WHY,
        "engine": "fal", "match_swipe": a.match_swipe, "files": made}, indent=1))
    print(f"\n{len(made)} of {len(jobs)} drafted")


if __name__ == "__main__":
    main()
