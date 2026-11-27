"""The design line, steps 1 to 2, for any brand: a calendar window of finished-copy sends in, a job card and a laid-out
email (design/job.json + design/email.json + design/preview.html) per send out, for a person's OK at step 2.

    python3 design/line.py <brand> <YYYY-MM> --from 2026-11-02 [--days 14] [--only nov-03,nov-05] [--dry-run]
    python3 design/line.py <brand> --run <run folder> [--run ...]

Each send's kind (design | letter) and format come from the calendar (marketing-calendar/machine/kinds.py).
Its copy comes from its finished copy run (runs/email-production/<brand>/<label>/deliverable/email.json).
Prompts: prompts/design1-jobcard-v1-owner.md, prompts/design2-layout-v1-owner.md, each written beside its
output as sent. The layout is checked before it is kept: every section is one the engine has, every product
picture is one the brand's look names, every proof id is in the brand's proof index, no picture repeats in
the window. Nothing is generated: a picture still to make stays a `todo` slot until a person OKs it (step 3).
Only pictures someone has looked at are offered (asset-index tag.py's tags.json, for proof and for product photos),
and a real picture's alt is what was seen in it, never what the layout guessed (the team, 2026-10-28).
"""
import argparse
import calendar  # noqa: F401 -- pins the standard library's calendar before marketing-calendar's calendar.py can shadow it (LD-19 (calendar shadow fix))
import datetime
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.insert(0, str(HERE))
import look as L  # noqa: E402

REPO = L.REPO
sys.path.insert(0, str(REPO / "components" / "run-kit"))
sys.path.append(str(REPO / "components" / "marketing-calendar" / "machine"))
import engine as EN  # noqa: E402
import learn as LN  # noqa: E402

PROMPTS = COMP / "prompts"
RUNS = REPO / "runs" / "email-production"

# What each section takes. Read by the layout prompt; the engine (engine.py) is the truth.
GUIDE = {
    "band": "header: the brand's logo over its band ornament. No fields. Opens a design email.",
    "mark": "header for a letter: the logo alone. No fields.",
    "hero_type": "eyebrow (short caps line), headline (<=7 words, one <i>accent</i>), picture. Opens a design email.",
    "hero_photo": "headline, optional sub, picture (a photo or a face, full width). Opens a letter or a design email.",
    "headline": "text (a turn in the argument, <=8 words), optional sub (one sentence).",
    "display": "text: one large line, left-aligned (a letter's opener).",
    "letter": "optional greeting, paras (list of short paragraphs, <=45 words each). Stays live text.",
    "quote": "quote (one real customer line, as written), who (attribution, first name only or 'A <brand> customer').",
    "bigquote": "eyebrow, quote, who: a customer's words as the headline.",
    "example": "picture (that customer's own proof), quote (his or her words), who, ask (one line).",
    "specs": "items: four [number, label] pairs, the product's real numbers.",
    "tiles": "title, tiles: three {picture, name, line<=10 words}.",
    "box": "title, hero {picture, name, line}, tiles: up to four {picture, name, line}. What is in a set, as pictures.",
    "selfies": "title, items: three {picture (customer's own photo), quote (her own words)}, optional note.",
    "photo_card": "picture, optional title (caps label), text (<=30 words) on a card over the picture.",
    "arrows": "title, items: [thing, what it does] pairs (<=8 words each), optional close line.",
    "grid": "pictures: six proof pictures, caption.",
    "picture": "picture, optional caption: one picture alone (a before/after, a wide scene).",
    "product": "picture, name, line (<=20 words), price, optional was (struck through), cta.",
    "offer": "price (the page price), optional was, cta: the price large, then the button.",
    "guarantee": "cta; optional head and line (the brand's guarantee is used word for word by default).",
    "deal": "eyebrow, lines (2-3 short lines): the guarantee as the deal.",
    "cta": "label (<=4 words), optional lead line. The one button.",
    "poster": "picture (the key visual, full bleed), optional title (big, with one <i>accent</i>), sub, cta: the blow-out an email on a moment opens on.",
    "ticker": "text: the moment's words, repeated across a band in the accent colour (e.g. BLACK FRIDAY).",
    "rule": "optional ornament ('rule' in design emails, 'fan' in letters, 'divider' in a theme): a divider.",
    "sign": "optional name and role: the sign-off (defaults to the brand's).",
    "gif": "gif (a run: file), caption, link, optional note: a real clip the brand owns.",
    "foot": "the footer. No fields. Ends every email.",
}

# LD-101 (Brand-B house look): the sections a brand's `house` adds, offered only to a brand that has one. Shapes are
# the boxes' own (BOX): a picture is made at its box's shape, never cut to fit.
HOUSE_GUIDE = {
    "hero_top": "headline (<=7 words, one <i>accent</i>), sub (one line), picture: the top of a dark hero photo (4:5). Follow it with cta {\"variant\": \"dark\"} and then hero_hands with the SAME picture: one photo, split by the live button.",
    "hero_hands": "picture: the SAME picture as the hero_top above it (its lower part). Comes right after the dark cta.",
    "infographic": "title, rows: three {icon: snow|heat|drop|spot, label (2-3 words), text (one sentence)}, final (one serif line): what is going on, as three white cards.",
    "ritual": "title, picture (wide, 16:9), steps: two or three {picture (square), eyebrow, title, text}: how it is used, on the deep brown.",
    "photo_card": "picture (4:5), text (<=30 words), optional title: one picture with its words in a card inside its bottom edge.",
    "finale": "title, sub, quote (one line), picture (3:4): the close on the deep brown, picture beside the headline.",
    "closing": "head (one serif line), sub (one line): the plain close before the last button.",
    "notes": "title, optional sub, notes: two or three {quote (a customer's words exactly as written), who ('A <brand> customer' or a first name)}: customers' words, no picture.",
    "on_camera": "title, optional eyebrow, people: one to three {picture: {\"still\": an id from CLEARED PEOPLE, \"alt\"}, name (her first name), line (her own words from that same clip, exactly, or empty)}: real people on camera, never the same person twice.",
    "cta": "label (<=4 words), optional lead; variant \"dark\" right under hero_top, else none.",
}
HOUSE_RULE = ("HOUSE LOOK: this brand has a house look. Build the email from the house sections above (and band, guarantee, foot) "
              "in the format's own order, each email its own selection and order, never one fixed sequence. Every picture is made "
              "for its own box and job: never the same picture twice in one email (hero_top and hero_hands share one photo by design). "
              "A customer section shows customers' words (notes) or cleared people (on_camera), never a product photo standing in for a "
              "customer and never anyone not on CLEARED PEOPLE.")
# the shape (width / height) of each house box that holds a picture; finale's comes from its style (split = tall)
BOX = {("hero_top", "picture"): 0.8, ("hero_hands", "picture"): 0.8, ("ritual", "steps"): 1.0, ("photo_card", "picture"): 0.8}
CUSTOMER_SECTIONS = ("selfies", "example", "grid", "picture", "bigquote", "quote")


def sections_text(lk):
    """The section list the layout prompt is offered: the general GUIDE, and for a brand with a house its sections
    and the house rule."""
    secs = "\n".join("%s: %s" % (k, v) for k, v in GUIDE.items() if k in EN.SECTIONS)
    if (lk.get("house") or {}).get("sections"):
        have = set((lk.get("house") or {})["sections"])
        secs += "\n\nHOUSE SECTIONS (this brand's own; prefer them):\n" + "\n".join(
            "%s: %s" % (k, v) for k, v in HOUSE_GUIDE.items() if k in have and k in EN.SECTIONS) + "\n\n" + HOUSE_RULE
    return secs


def _ratio(x):
    """A shape as width / height: 1.25, "16/9", "16:9", "2.1"; None when it is none of them."""
    try:
        if isinstance(x, (int, float)):
            return float(x)
        a, sep, b = str(x).replace(":", "/").partition("/")
        return float(a) / float(b) if sep else float(a)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def box_of(sec, where):
    """The shape of the box a house section's picture fills; None for a box that takes the picture's own shape."""
    st = sec.get("style") or {}
    if sec.get("s") == "ritual":
        return _ratio(st.get("pic_ratio", "2.1")) if where == "picture" else 1.0
    if sec.get("s") == "finale":
        return 0.75 if st.get("split") else 1.0
    return BOX.get((sec.get("s"), where))


def _house_pics(sec):
    """(where, picture) for every picture a house section holds."""
    if isinstance(sec.get("picture"), dict):
        yield "picture", sec["picture"]
    for x in sec.get("steps") or []:
        if isinstance(x.get("picture"), dict):
            yield "steps", x["picture"]


def box_ratios(spec, lk):
    """Every picture still to make in a house email takes its box's shape (`ratio`), so the picture chain makes it at
    that shape and nothing is cut to fit. Styles are the house's (EN.house). Returns the spec, changed in place."""
    if spec.get("look") != "house":
        return spec
    merged = EN.house(spec, lk)["sections"]
    for sec, m in zip(spec["sections"], merged):
        for where, p in _house_pics(m):
            r = box_of(m, where)
            if r and "todo" in p:
                p["ratio"] = r
        for (_, p), (_, q) in zip(_house_pics(sec), _house_pics(m)):
            if "ratio" in q:
                p["ratio"] = q["ratio"]
    return spec


def _read(p, limit=None):
    try:
        t = Path(p).read_text()
    except OSError:
        return "(none on file)"
    return t[:limit] if limit else t


def dna_of(brand):
    """The brand's visual DNA: brands/<brand>/email-sms/design-formats/visual-dna.md when filed, else the runs proposal."""
    for f in (REPO / "brands" / brand / "email-sms" / "design-formats" / "visual-dna.md",
              REPO / "runs" / "brand-dna" / brand / "visual-dna.md"):
        if f.exists():
            return f.read_text()
    return "(no visual DNA on file yet)"


def products_of(lk):
    return {k: v for k, v in (lk.get("products") or {}).items() if not k.startswith("_")}


def product_key(brand, folder):
    """The product the brand declares for a picture's Drive folder name. The look names product pictures by their
    Drive folder (nova-face-brush) and the brand may declare the product under a shorter key (flex): read
    products/images.json's drive_folder, so the image engine is handed a product it knows (the team, 2026-10-22).
    A folder no product claims is returned as it is."""
    try:
        rows = json.loads((Path(L.brandpath.brand_root(brand, REPO / "brands")) / "products" / "images.json")
                          .read_text()).get("products", {})
    except (OSError, ValueError):
        return folder
    for key, row in rows.items():
        if isinstance(row, dict) and str(row.get("drive_folder") or "").rstrip("/").rsplit("/", 1)[-1] == folder:
            return key
    return folder


def proof_of(brand, limit=220):
    """The brand's real pictures for the layout: the proof index, with what is IN each picture when it has been tagged
    (tools/asset-index/machine/tag.py → tags.json). Tagged, clean (no baked-in words), best quality first;
    pictures whose product looks wrong are left out."""
    d = REPO / "runs" / "asset-index" / brand / "proof"
    f = d / "proof.json"
    if not f.exists():
        return [], "(no proof index yet: every proof slot is a todo)"
    items = json.loads(f.read_text())["items"]
    ex = d / "exclude.json"
    excl = set(json.loads(ex.read_text()).get("ids", [])) if ex.exists() else set()
    tags = json.loads((d / "tags.json").read_text()) if (d / "tags.json").exists() else {}
    items = [e for e in items if e.get("media") == "image" and e.get("state") != "excluded" and e["id"] not in excl]
    def rank(e):
        g = tags.get(e["id"])
        if not g:
            return (2, 0)
        bad = g.get("baked_text") == "large" or g.get("product_ok") is False
        return (1 if bad else 0, -int(g.get("quality") or 0))
    # a picture no one has looked at is not offered: from its name alone the layout writes what it guesses is in it
    # (the team, 2026-10-28); tag it first (asset-index tag.py)
    items = [e for e in items if e["id"] in tags and tags[e["id"]].get("product_ok") is not False]
    if not items:
        return [], "(no proof described yet: every proof slot is a todo — describe it with asset-index tag.py)"
    items.sort(key=rank)
    lines = []
    for e in items[:limit]:
        g = tags[e["id"]]
        lines.append("%s · %s · %s · holding %s · q%s · words %s · use %s · %s" % (
            e["id"], g.get("shot"), g.get("people"), g.get("holding"), g.get("quality"), g.get("baked_text"),
            "/".join(g.get("use_for") or []), g.get("one_line", "")))
    return [e["id"] for e in items], "\n".join(lines)


PHOTO_KINDS = ("lifestyle", "packshot", "texture", "ugc", "ingredients")
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _photos_by_name(lk, never):
    """photos_of's refs, in its order, listed BY NAME through gdrive-creator's reach.list_tree (LD-16 (email
    design by API)): names only, NOTHING DOWNLOADED — the tree can be gigabytes; a picture is fetched only when
    Look.path() resolves the one ref the email uses. No key is the engine's SystemExit; the caller catches it."""
    rows = L.reach().list_tree(["brands", lk.brand, "products"]) or []
    keyed = []
    for rel, _ in rows:
        bits = rel.split("/")          # <product>/<kind>/.../<file>
        if len(bits) < 3 or bits[1] not in PHOTO_KINDS:
            continue
        name = bits[-1]
        if Path(name).suffix.lower() in PHOTO_EXTS and not any(n in name.lower() for n in never):
            keyed.append(((bits[0], PHOTO_KINDS.index(bits[1]), tuple(bits[2:])),
                          "drive:brands/%s/products/%s" % (lk.brand, rel)))
    return [ref for _, ref in sorted(keyed)]


def photos_of(lk, limit=220):
    """The brand's own real photos on the drive (brands/<brand>/products/<product>/<kind>/), never made or 3D ones.
    Off the mount when it lists here; else listed BY NAME through the Drive API (_photos_by_name), nothing downloaded."""
    never = [n.lower() for n in (lk.get("check") or {}).get("never_names", [])]
    refs = None
    try:
        import drive_index
        m = drive_index.mount()
        if m:
            root = Path(m) / "brands" / lk.brand / "products"
            refs = []
            for prod in sorted(p for p in root.iterdir() if p.is_dir()):
                for kind in PHOTO_KINDS:
                    d = prod / kind
                    if not d.is_dir():
                        continue
                    for f in sorted(d.rglob("*")):
                        if f.suffix.lower() in PHOTO_EXTS and not any(n in f.name.lower() for n in never):
                            refs.append("drive:brands/%s/products/%s/%s/%s" % (lk.brand, prod.name, kind, f.relative_to(d)))
    except OSError:
        refs = None                     # the mount does not list here (launchd: no Full Disk Access)
    if refs is None:
        try:
            refs = _photos_by_name(lk, never)
        except (Exception, SystemExit) as e:
            print("photos_of: no Drive API listing either — %s: %s" % (type(e).__name__, e), file=sys.stderr)
            return set(), "(the shared drive is not mounted: no brand photos offered)"
    shown = refs[:limit]
    return set(refs), "\n".join(shown) or "(none on the drive)"


def photo_tags(brand):
    """What is IN each brand photo, keyed by its drive: reference (asset-index tag.py), from every collection: a
    photo the index keeps under another collection (stills) is still the brand's photo."""
    out = {}
    for f in sorted((REPO / "runs" / "asset-index" / brand).glob("*/tags.json")):
        try:
            tags = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        out.update({_nfc(g["ref"]): g for g in tags.values() if isinstance(g, dict) and g.get("ref")})
    return out


def _nfc(ref):
    """One spelling for a name: the mount lists "Ferrán" with a separate accent (NFD), the index with one letter (NFC)."""
    return unicodedata.normalize("NFC", ref) if isinstance(ref, str) else ref


def described_photos(lk, limit=220):
    """photos_of, narrowed to the photos someone has looked at, each line saying what is in it. A photo listed by
    name only is never offered: the layout would pick it for its file name and describe what it guesses."""
    refs, txt = photos_of(lk, limit=100000)
    if not refs:
        return refs, txt
    tags = photo_tags(lk.brand)
    seen = [r for r in txt.splitlines() if _nfc(r) in tags and tags[_nfc(r)].get("product_ok") is not False][:limit]
    if not seen:
        return set(), "(no brand photo described yet: describe them with asset-index tag.py --label products)"
    lines = ["%s · %s · %s %s · shows %s · q%s · words %s · %s" % (
        r, g.get("shot"), g.get("people"), g.get("skin_tone") or "", ", ".join(g.get("products") or []) or "no product",
        g.get("quality"), g.get("baked_text"), g.get("one_line", "")) for r, g in ((r, tags[_nfc(r)]) for r in seen)]
    return set(r for r in refs if _nfc(r) in tags), "\n".join(lines)


def seen_in(brand):
    """{proof id or photo ref: what a person sees in it}, from the tags."""
    out = {ref: g.get("one_line") for ref, g in photo_tags(brand).items() if g.get("one_line")}
    f = REPO / "runs" / "asset-index" / brand / "proof" / "tags.json"
    try:
        out.update({i: g.get("one_line") for i, g in json.loads(f.read_text()).items() if isinstance(g, dict) and g.get("one_line")})
    except (OSError, ValueError):
        pass
    return out


def true_alts(spec, seen):
    """A real picture's alt is what was seen in it: the layout never saw the picture, so its own words are dropped."""
    def walk(x):
        if isinstance(x, dict):
            if "s" not in x:
                ref = _nfc(x.get("proof") or x.get("photo"))
                if ref in seen:
                    x["alt"] = seen[ref]
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(spec.get("sections", []))
    return spec


def product_truth(brand):
    """Every product's physical truth, read from brands/<brand>/products/<slug>/product.md (the section that starts
    'What it physically looks like' / the table under it). Returns (text for the prompts, {slug: [forbidden forms]}).
    The forbidden forms are the 'not a X or a Y' words in its Container row ('A squeeze tube, not a jar or a bottle')."""
    root = REPO / "brands" / brand / "products"
    out, banned = [], {}
    for f in sorted(root.glob("*/*.md")):
        t = f.read_text()
        i = t.find("## What it physically looks like")
        if i < 0:
            continue
        j = t.find("\n## ", i + 5)
        block = t[i:j if j > 0 else None].strip()
        name = f.parent.name if f.name == "product.md" else f.stem
        out.append("### %s\n%s" % (name, block))
        m = re.search(r"\*\*Container\*\*\s*\|\s*([^|\n]+)", block)
        if m:
            banned[name] = re.findall(r"\b(?:not a|or a|never a)\s+(\w+)", m.group(1))
    return "\n\n".join(out) or "(no product files)", banned


def form_problems(text, banned):
    """Words naming a product in a form it never takes (a 'jar' for a tube). A "never …" / "no …" / "not …" clause, up to
    its stop (. ; : ! ? brackets, a quote, a line end), is the product truth repeated and is read past (2026-10-30)."""
    text = re.sub(r"\b(?:never|not|no|nor)\b[^.;:!?()\[\]\"\n]*", " ", text, flags=re.I)
    words = sorted({w for ws in banned.values() for w in ws})
    hits = sorted({w for w in words if re.search(r"\b%ss?\b" % re.escape(w), text, re.I)})
    return ["calls the product a %s: the product file says it never is one" % w for w in hits]


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{%s}" % k, v if isinstance(v, str) else json.dumps(v, indent=1, ensure_ascii=False))
    return tpl


def answer_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("the answer has no JSON object")
    return json.loads(m.group(0))


def validate(spec, lk, proof_ids, used, photo_refs=None, cleared=None, product="", slugs=None):
    """Problems that stop a layout being kept. `cleared` = {still id: {"creator", "products", ...}}: the people a house
    email may show (LD-101 (Brand-B house look)); `product` = the email's own product slug, which every still must show
    (`slugs` = the brand's products, read from brands/<brand>/products/ when not given)."""
    probs = []
    prods = products_of(lk)
    def pics(x):
        if isinstance(x, dict):
            if any(k in x for k in ("stage", "glow", "proof", "todo", "photo", "band", "still")) and "s" not in x:
                yield x
            for v in x.values():
                yield from pics(v)
        elif isinstance(x, list):
            for v in x:
                yield from pics(v)
    for s in spec.get("sections", []):
        if s.get("s") not in EN.SECTIONS:
            probs.append("no section called %r" % s.get("s"))
    for p in pics(spec.get("sections", [])):
        for k in ("stage", "glow"):
            if k in p and str(p[k]).startswith("product:") and p[k].split(":", 1)[1] not in prods:
                probs.append("product picture %r is not in the brand's look" % p[k])
        if "photo" in p and photo_refs is not None and str(p["photo"]).startswith("drive:") and p["photo"] not in photo_refs:
            probs.append("photo %r is not one of the brand's own photos" % p["photo"])
        if "photo" in p and p["photo"] in used:
            probs.append("photo %r is already used in %s" % (p["photo"], used[p["photo"]]))
        if "proof" in p and p["proof"] not in proof_ids:
            probs.append("proof %r is not in the proof index" % p["proof"])
        if "proof" in p and p["proof"] in used:
            probs.append("proof %r is already used in %s" % (p["proof"], used[p["proof"]]))
        if not p.get("alt"):
            probs.append("a picture has no alt text")
    try:                                       # a layout that will not render is sent back, never kept
        test = json.loads(json.dumps(spec))
        def strip(x):
            if isinstance(x, dict):
                for k in ("proof", "photo", "stage", "glow", "band", "still"):
                    if k in x and "s" not in x:
                        x.clear(); x.update({"todo": "test", "alt": "test"})
                        return
                for v in x.values():
                    strip(v)
            elif isinstance(x, list):
                for v in x:
                    strip(v)
        strip(test.get("sections", []))
        EN.sections({"sections": test.get("sections", []), "theme": None, "label": "test"}, lk)
    except Exception as e:
        probs.append("the layout does not render: %s %s" % (type(e).__name__, e))
    if spec.get("look") == "house":
        probs += house_problems(spec, lk, cleared or {})
        slugs = slugs if slugs is not None else brand_products(lk.brand)
        if product and product in slugs:       # a send with no product ("none") is not checked
            probs += still_product_problems(spec, cleared or {}, product, slugs)
    names = [s.get("s") for s in spec.get("sections", [])]
    if names and names[-1] != "foot":
        probs.append("the email does not end on the footer")
    if spec.get("kind") == "letter" and names.count("letter") == 0:
        probs.append("a letter with no letter block")
    return probs


def _ref(p):
    for k in ("still", "photo", "proof", "stage", "glow", "band", "todo"):
        if k in p:
            return "%s:%s" % (k, p[k])
    return None


def house_problems(spec, lk, cleared):
    """LD-101 (Brand-B house look), the team's picture rule (2026-10-30): no picture twice in one email (hero_top and
    hero_hands are one photo split by design), no person twice, no picture made at another box's shape, nobody not
    cleared for email, and no customer picture from the proof index (no proof picture is cleared for email)."""
    probs, seen, people = [], {}, {}
    secs = spec.get("sections", [])
    merged = EN.house(spec, lk)["sections"] if (lk.get("house") or {}).get("styles") else secs
    def walk(x, i):
        if isinstance(x, dict):
            if "s" not in x and _ref(x):
                yield i, x
            for v in x.values():
                yield from walk(v, i)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v, i)
    hero = {i for i, s in enumerate(secs) if s.get("s") in ("hero_top", "hero_hands")}
    for i, p in (y for i, s in enumerate(secs) for y in walk(s, i)):
        r = _ref(p)
        if r in seen and not (seen[r] in hero and i in hero):
            probs.append("one picture twice (%s, parts %d and %d): every picture is made for its own box" % (r, seen[r] + 1, i + 1))
        seen.setdefault(r, i)
        if "still" in p:
            who = (cleared.get(p["still"]) or {}).get("creator")
            if p["still"] not in cleared:
                probs.append("still %r is not on CLEARED PEOPLE: only creators cleared for email may be shown" % p["still"])
            elif who in people:
                probs.append("the same person twice (%s, parts %d and %d)" % (who, people[who] + 1, i + 1))
            people.setdefault(who, i)
        if "still" in p and secs[i].get("s") != "on_camera":
            probs.append("still %r in a %s section: cleared people show only through on_camera" % (p["still"], secs[i].get("s")))
        if "proof" in p:
            probs.append("customer picture %r from the proof index: none is cleared for email; show cleared people (on_camera) or the customers' words (notes)" % p["proof"])
    for s, m in zip(secs, merged):
        for where, p in _house_pics(m):
            box, have = box_of(m, where), _ratio(p.get("ratio"))
            if box and have and abs(have - box) > 0.02:
                probs.append("a picture made at another shape than its box (%s %s: %.2f, the box is %.2f)" % (s.get("s"), where, have, box))
    return probs


def brand_products(brand):
    """The brand's product slugs: each folder under brands/<brand>/products/ that holds a product.md."""
    root = REPO / "brands" / brand / "products"
    return sorted(f.parent.name for f in root.glob("*/product.md")) if root.is_dir() else []


def _words(text):
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in re.findall(r"[a-z0-9]+", str(text).lower())]


def _name_of(slug, slugs):
    """A product's name in a record: the last words of its slug, at least two, that no other product ends on
    (brilliance-body-scrub -> "body scrub"; a one-word slug is itself)."""
    w = _words(slug.replace("-", " "))
    tails = [_words(o.replace("-", " ")) for o in slugs if o != slug]
    for n in range(min(2, len(w)), len(w) + 1):
        if not any(t[-n:] == w[-n:] for t in tails if len(t) >= n):
            return w[-n:]
    return w


def names_product(text, slug, slugs):
    """True when a clip's record names this product (its name as adjacent words, plurals read as one)."""
    name, have = _name_of(slug, slugs), _words(text)
    return any(have[i:i + len(name)] == name for i in range(len(have) - len(name) + 1))


def still_shows(info, product, slugs):
    """(shows the email's product, [other products it names]) for one cleared still, from its clip's record: the
    products seen in the clip and what the scene shows."""
    text = " | ".join(list(info.get("products") or []) + [info.get("shows") or ""])
    return names_product(text, product, slugs), [o for o in slugs if o != product and names_product(text, o, slugs)]


def stills_as_stills(spec, cleared):
    """A cleared person's still the layout wrote as a proof id ({"proof": "<clip>@<s>"}) is the still it names: read back
    as {"still": ...} so the house checks see it (brand-b nov-04's first run, 2026-10-30)."""
    def walk(x):
        if isinstance(x, dict):
            if "s" not in x and x.get("proof") in cleared:
                x["still"] = x.pop("proof")
                if x.get("source") == "proof":
                    x.pop("source")
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(spec.get("sections", []))
    return spec


def still_product_problems(spec, cleared, product, slugs):
    """LD-101 (Brand-B house look), the team 2026-10-30: a customer section's stills show the email's own product. A still
    of another product, or one whose record names no product, holds the email."""
    probs = []
    def walk(x):
        if isinstance(x, dict):
            if "still" in x and "s" not in x:
                yield x
            for v in x.values():
                yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)
    for p in walk(spec.get("sections", [])):
        info = cleared.get(p["still"])
        if not info:
            continue                   # house_problems names a still that is not cleared
        own, others = still_shows(info, product, slugs)
        if others:
            probs.append("still %r shows %s, not this email's %s: show a still of %s or the customers' words (notes)"
                         % (p["still"], " and ".join(others), product, product))
        elif not own:
            probs.append("still %r names no product in its record, so nobody can say it shows %s: pick a still whose "
                         "record shows %s, or the customers' words (notes)" % (p["still"], product, product))
    return probs


def _asset_index():
    """tools/asset-index/machine/search.py and shared_paths.py, loaded by file (the folder name has a hyphen)."""
    import importlib.util
    mods = {}
    for name in ("asset_index_search", "asset_index_shared_paths"):
        if name in sys.modules:
            mods[name] = sys.modules[name]
            continue
        f = REPO / "tools" / "asset-index" / "machine" / ("search.py" if name.endswith("search") else "shared_paths.py")
        sys.path.insert(0, str(f.parent))
        spec = importlib.util.spec_from_file_location(name, f)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
        mods[name] = m
    return mods["asset_index_search"], mods["asset_index_shared_paths"]


PEOPLE_ASKS = ("woman smiling at the camera holding the {p}", "woman showing her skin after using the {p}",
               "woman talking to the camera about the {p}", "woman using the {p} in her bathroom")


def cleared_people(brand, product="", per_person=2, limit=24, slugs=None):
    """LD-101 (Brand-B house look): the people a house email may show, from the asset-index search with use="email"
    (one rights list: the brand's usage-rights register). ({id: {"creator", "clip_id", "t", "shows", "says", "path"}},
    the lines offered to the layout). An id is "<clip id>@<second>"; a person comes at most `per_person` times.
    With a product, only stills whose clip record shows that product, and no other, are offered (the team, 2026-10-30)."""
    slugs = slugs if slugs is not None else brand_products(brand)
    try:
        S, _ = _asset_index()
    except Exception as e:  # noqa: BLE001 -- no index here means no people offered, named
        return {}, "(no asset index on this Mac: %s: show the customers' words (notes))" % e
    got, count = {}, {}
    for ask in PEOPLE_ASKS:
        # with a product the filter below drops most hits, so the search reads deep (12 deep found one person, 2026-10-30)
        deep = 400 if product and product in slugs else 12
        for h in S.search(ask.format(p=product or "product"), brand=brand, per=deep, use="email", exclude_talking=False):
            who = h["rights"].get("creator") or "?"
            t = round(((h.get("in") or 0) + (h.get("out") or h.get("in") or 0)) / 2, 1)
            key = "%s@%s" % (h["clip_id"], t)
            if key in got or count.get(who, 0) >= per_person:
                continue
            if product and product in slugs and still_shows(h, product, slugs) != (True, []):
                continue
            count[who] = count.get(who, 0) + 1
            got[key] = {"creator": who, "clip_id": h["clip_id"], "t": t, "drive_id": h.get("drive_id"),
                        "shows": h.get("shows") or "", "says": h.get("says") or "", "path": h.get("shared_path"),
                        "products": list(h.get("products") or [])}
            if len(got) >= limit:
                break
    lines = ["%s · %s · shows: %s · says: %s" % (k, v["creator"], v["shows"][:140], v["says"][:160] or "(nothing)") for k, v in got.items()]
    return got, "\n".join(lines) or "(no creator cleared for email fits: show the customers' words (notes))"


def resolve_stills(spec, run_dir, cleared, fetch=None):
    """Each {"still": id} in the layout becomes the frame itself, fetched once into <run>/media/ at the clip's own
    shape (720 px wide), as {"photo": "run:media/still-<clip>-<s>.jpg", "ratio": its own w/h}. `fetch(id, info, out)`
    writes the picture (tests); the default reads the clip by its Drive id through the key, a ranged seek only."""
    from PIL import Image
    def walk(x):
        if isinstance(x, dict):
            if "still" in x and "s" not in x:
                yield x
            for v in list(x.values()):
                yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)
    for p in list(walk(spec.get("sections", []))):
        info = cleared.get(p["still"])
        if not info:
            continue
        out = Path(run_dir) / "media" / ("still-%s-%s.jpg" % (info["clip_id"], str(info["t"]).replace(".", "_")))
        if not out.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            (fetch or _fetch_still)(p["still"], info, out)
        with Image.open(out) as im:
            w, h = im.size
        sid = p.pop("still")
        p.update({"photo": "run:media/" + out.name, "ratio": round(w / h, 4), "source": "creator", "still": sid,
                  "creator": info["creator"], "alt": p.get("alt") or "%s, on camera" % info["creator"]})
    return spec


def _fetch_still(sid, info, out):
    _, SP = _asset_index()
    src, hdr = SP._media_request(info["drive_id"] or info["clip_id"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-headers", hdr, "-ss", str(info["t"]), "-i", src, "-frames:v", "1",
                    "-vf", "scale=720:-2", "-q:v", "3", str(out)], check=False, timeout=180)
    if not out.is_file():
        raise RuntimeError("no frame came back for %s" % sid)


MOMENT_ALIASES = {}


def moment_of(slot):
    """The moment a send sits on: its occasion's key (black-friday, halloween…), or None."""
    occ = (slot.get("occasion") or "").split(":")[0].strip()
    if not occ or occ in ("none", "affiliate"):
        return None
    # a moment is a key (nba-regular-season); the calendar's prose occasions ("a recorded problem — …", "HELD OPEN —
    # live") are not, and asking research for them held 23 November emails for files no one could write (2026-10-27)
    return occ if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", occ) else None


def moment_world(brand, avatar, moment, bdir, profile, culture, dry=False):
    """The moment's world for this avatar. Read from brands/<brand>/core-avatars/<avatar>/moments/<moment>.md
    when a person has filed it there; else from runs/moment-research/<brand>/<avatar>/<moment>.md, which this
    writes once from the research beside it (<moment>.research.md) by prompt design0 and every email in that
    moment reuses. A machine never writes brands/ (K2): the runs copy is the proposal a person folds in.
    No research anywhere → None, and the email is held."""
    from run_kit import model as M
    import promises as PM
    lean_call = PM.lean()                    # LD-62 (lean model calls)
    filed = bdir / "core-avatars" / avatar / "moments" / (moment + ".md")
    if filed.exists():
        return filed.read_text()
    d = REPO / "runs" / "moment-research" / brand / avatar
    world, research = d / (moment + ".md"), d / (moment + ".research.md")
    if not research.exists():
        research = bdir / "core-avatars" / avatar / "moments" / (moment + ".research.md")
    if world.exists():
        return world.read_text()
    if not research.exists() or dry:
        return None
    truth, banned = product_truth(brand)
    p0 = fill(_read(PROMPTS / "design0-moment-v1-owner.md"), learnings=LN.block(brand, ("design", "picture", "copy")), moment=moment, research=research.read_text(), product_truth=truth,
              avatar=profile, culture=culture, position=_read(bdir / "brand-identity" / "position.md", 12000))
    d.mkdir(parents=True, exist_ok=True)
    (d / (moment + ".prompt.md")).write_text(p0)
    model, _ = M.pick("designs", len(p0))
    out = M.call(p0, model, label="design0-%s-%s" % (avatar, moment), runner=lean_call.design_runner(M))
    for _ in range(2):                       # a world that draws a tube as a jar is rewritten, never kept
        probs = form_problems(out, banned)
        if not probs:
            break
        out = M.call(p0 + "\n\nYOUR LAST ANSWER WAS HELD FOR: " + "; ".join(probs) + ". Rewrite it with every product exactly as PRODUCT TRUTH describes it.", model, label="design0-fix", runner=lean_call.design_runner(M))
    world.write_text("# %s · %s · the moment world\n\nWritten by prompts/design0-moment-v1-owner.md from %s.\n\n%s\n" % (
        avatar, moment, research.name, out.strip()))
    return world.read_text()


def run_send(brand, run_dir, slot, lk, proof_ids, proof_txt, used, dry):
    from run_kit import model as M
    import promises as PM
    lean_call = PM.lean()                    # LD-62 (lean model calls)
    photo_refs, photos_txt = described_photos(lk)
    seen = seen_in(brand)
    copy = json.loads((run_dir / "deliverable" / "email.json").read_text())
    rj = json.loads((run_dir / "run.json").read_text()) if (run_dir / "run.json").exists() else {}
    avatar = rj.get("avatar") or slot.get("avatar") or ""
    bdir = REPO / "brands" / brand
    culture = _read(bdir / "core-avatars" / avatar / "culture-map.md", 14000)
    profile = _read(bdir / "core-avatars" / avatar / "profile.md", 10000)
    hand = sorted((bdir / "core-avatars" / avatar).glob("culture-map.hand-*.md")) if avatar else []
    if hand:
        culture += "\n\n" + _read(hand[-1], 8000)
    moment = moment_of(slot)
    world = moment_world(brand, avatar, moment, bdir, profile, culture, dry) if moment else None
    world_txt = world or ("(no moment)" if not moment else "(NO RESEARCH ON FILE for %s: the email is held until it is researched)" % moment)
    kind = {"kind": slot.get("kind", "design"), "format": slot.get("format"), "why": slot.get("kind_why", "")}
    rules = json.dumps(lk.get("design_rules") or {}, indent=1, ensure_ascii=False)
    send = {k: slot.get(k) for k in ("id", "date", "type", "category", "segments", "occasion", "product", "offer", "why")}
    d = run_dir / "design"
    d.mkdir(exist_ok=True)
    truth, banned = product_truth(brand)
    themes = {k: v.get("_what", "") if isinstance(v, dict) else "" for k, v in (lk.get("themes") or {}).items() if not k.startswith("_")}
    used_concepts = [v for k, v in used.items() if k.startswith("concept:")]
    p1 = fill(_read(PROMPTS / "design1-jobcard-v1-owner.md"), learnings=LN.block(brand, ("design", "copy")), send=send, kind=kind, copy=copy,
              themes=json.dumps(list(themes)) if themes else "(none yet)", used_concepts=json.dumps(used_concepts) if used_concepts else "(none)",
              position=_read(bdir / "brand-identity" / "position.md", 12000), avatar=profile, culture=culture, moment_world=world_txt, design_rules=rules,
              product_truth=truth, visual_dna=dna_of(brand))
    (d / "design1--prompt.md").write_text(p1)
    if dry:
        print("  %s: prompt 1 written (%d chars), nothing spent" % (run_dir.name, len(p1)))
        return None
    model, _ = M.pick("designs", len(p1))
    job = answer_json(M.call(p1, model, label="design1-" + run_dir.name, runner=lean_call.design_runner(M)))
    if form_problems(json.dumps(job), banned):
        job = answer_json(M.call(p1 + "\n\nYOUR LAST ANSWER WAS HELD FOR: " + "; ".join(form_problems(json.dumps(job), banned)) + ". Every product exactly as PRODUCT TRUTH describes it.", model, label="design1-fix", runner=lean_call.design_runner(M)))
    (d / "job.json").write_text(json.dumps(job, indent=1, ensure_ascii=False) + "\n")
    secs = sections_text(lk)
    is_house = bool((lk.get("house") or {}).get("sections"))
    cleared = {}
    if is_house:                         # LD-101 (Brand-B house look): no proof picture is cleared for email
        cleared, people_txt = cleared_people(brand, send.get("product") or "")
        proof_ids, proof_txt = [], "CLEARED PEOPLE (creators cleared for email; show them only through on_camera, each at most once):\n" + people_txt
    p2 = fill(_read(PROMPTS / "design2-layout-v1-owner.md"), learnings=LN.block(brand, ("design", "picture")), job=job, copy=copy, kind=kind, sections=secs,
              products="\n".join(products_of(lk)), proof=proof_txt, photos=photos_txt, used=json.dumps(used), moment_world=world_txt, design_rules=rules,
              product_truth=truth, visual_dna=dna_of(brand))
    (d / "design2--prompt.md").write_text(p2)
    spec, probs = None, ["not run"]
    for attempt in range(2):
        model, _ = M.pick("designs", len(p2))
        spec = answer_json(M.call(p2 + ("" if not attempt else "\n\nYOUR LAST ANSWER WAS HELD FOR: " + "; ".join(probs) + ". Fix exactly those."), model, label="design2-" + run_dir.name, runner=lean_call.design_runner(M)))
        true_alts(spec, seen)
        if is_house:
            spec["look"] = "house"
            stills_as_stills(spec, cleared)
        import gaps as GP
        probs = validate(spec, lk, set(proof_ids), used, photo_refs, cleared=cleared,
                         product=send.get("product") if is_house else "") + form_problems(json.dumps(spec), banned) + [
            "an unfinished sequence: it says \"%s\" but has no card for step %s — give every step its own card in the same form as the others"
            % (claim, " or ".join(map(str, missing)))
            for _, missing, claim in GP.sequence_gaps(spec)]
        if not probs:                        # whole? every promise the email makes is kept (any brand, product, offer)
            import promises as PM
            try:
                probs = PM.problems(PM.check(run_dir, spec, job, copy))
            except Exception as e:  # noqa: BLE001 — a reader that won't answer never sinks the layout; it is noted
                print("   promise check not run: %r" % e)
        if not probs:
            break
    spec.update(brand=brand, label=run_dir.name, date=slot.get("date"), format=slot.get("format"),
                concept=job.get("concept"), culture=job.get("culture"), segments=segments_of(slot),
                link=(copy.get("button") or {}).get("link", ""), job=job)
    if spec.get("kind") == "design" and dna_of(brand).startswith("(no visual DNA"):
        probs = probs + ["no visual DNA on file for %s: a designed email is held until the brand's DNA is written" % brand]
    if moment and not world:
        probs = probs + ["no research on file for the moment `%s` for %s: add runs/moment-research/%s/%s/%s.research.md" % (moment, avatar, brand, avatar, moment)]
    th = spec.get("theme")
    if th and th not in (lk.get("themes") or {}):
        probs = probs + ["no %s look for the moment `%s` yet: make it (the brand's moment looks) before this email builds" % (brand, th)]
    used["concept:" + run_dir.name] = job.get("concept", "")
    if cleared and not probs:
        try:
            resolve_stills(spec, run_dir, cleared)
        except Exception as e:  # noqa: BLE001 -- a still that will not come is a held layout, named
            probs = probs + ["a cleared person's still could not be fetched: %s" % e]
    spec["held"] = probs
    (d / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    for key in ('"proof": "', '"photo": "'):
        for p in json.dumps(spec["sections"]).split(key)[1:]:
            used[p.split('"', 1)[0]] = run_dir.name
    try:
        html = EN.render(spec, L.load(brand, run_dir))
        (d / "preview.html").write_text('<!doctype html><meta charset="utf-8"><body style="margin:0;background:#222"><div style="max-width:400px;margin:24px auto">%s</div>' % html)
    except (Exception, SystemExit) as e:  # a picture that will not render is a held layout, never a crash of the batch
                                          # (proof.py's lookup exits on an unknown id)
        spec["held"].append("preview: %s" % e)
        (d / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    print("  %-28s %-6s %2d sections%s" % (run_dir.name, spec.get("kind"), len(spec.get("sections", [])), "  HELD: " + "; ".join(spec["held"]) if spec["held"] else ""))
    return spec


USE_PURPOSE = {"key-visual": "email-key-visual", "gift": "email-gift", "story": "email-story"}


def make_pictures(brand, run_dir, lk, dry=False):
    """Every picture slot still to make in this email, sent through the email picture chain (design/picture_chain.py,
    2026-10-29): the way picture ads are made. A product in the picture comes from its product casting sheet; a product
    at rest is a 3D set printed in Higgsfield (held, with its set request written, until a kept print names it); words
    the brief quotes are set on top, never drawn. The job card's concept and culture ride in every picture's recipe."""
    import picture_chain as C
    f = run_dir / "design" / "email.json"
    spec = json.loads(f.read_text())
    import picture_record as PR
    concept, culture = C.job_card(run_dir)
    slots, where = [], []
    def walk(x, i):
        if isinstance(x, dict):
            if "todo" in x:
                slots.append(x); where.append(i)
            for v in list(x.values()):
                walk(v, i)
        elif isinstance(x, list):
            for v in x:
                walk(v, i)
    house = spec.get("look") == "house"
    if house:
        box_ratios(spec, lk)             # LD-101 (Brand-B house look): every picture made at its own box's shape
    for i, s in enumerate(spec["sections"]):
        walk(s, i)
    for n, p in enumerate(slots):
        req = {"brand": brand, "purpose": USE_PURPOSE.get(p.get("use"), "email-story"),
               "direction": p["todo"] + ". " + p.get("brief", ""), "out": str(run_dir / "media"),
               "label": "%s-p%s" % (run_dir.name, __import__("hashlib").sha1((p["todo"] + p.get("brief", "") + (
                   "@%.3f" % _ratio(p["ratio"]) if house and _ratio(p.get("ratio")) else "")).encode()).hexdigest()[:8]),
               "people": in_frame(p)}          # the brand's cast rides along only when a person is in the picture
        ratio = 0.8 if p.get("use") != "gift" else 1.0
        if house and _ratio(p.get("ratio")):
            ratio = _ratio(p["ratio"])
        if dry:
            pl = C.plan(brand, p, req["label"], concept, culture)
            print("   would make %-6s %-16s %s" % (pl["route"], req["purpose"], p["todo"][:80]))
            if pl.get("held"):
                print("      held: %s" % pl["held"])
            continue
        done = run_dir / "media" / ("%s-01.png" % req["label"])
        rec, unchecked = None, None
        # the label is the picture's own brief, never its position (2026-10-18: a slot added mid-email took the first
        # slot's label and inherited the hero's file); the same brief made before is reused, never paid twice
        if done.exists():
            path = done
            old = run_dir / "media" / "records" / req["label"] / "record.json"
            rec = str(old.relative_to(run_dir)) if old.is_file() else None
            got = {}
        else:
            try:
                got = C.make(brand, p, req["label"], done, concept, culture, ratio=ratio, tokens=lk.get("tokens"), run_dir=run_dir, people=req["people"],
                             **({"aspect": C.aspect_for(ratio)} if house else {}))
            except Exception as e:           # one refused picture never sinks the email
                print("   REFUSED %s: %s" % (p["todo"][:60], str(e)[:160]))
                p["refused"] = str(e)[:300]
                p["record"] = PR.keep(run_dir, req["label"], where[n], req, error=str(e)[:300])
                f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
                continue
            req.update({"product": ",".join(got.get("products") or []) or None, "references": got.get("references") or []})
            if got.get("held"):
                print("   HELD %s: %s" % (p["todo"][:60], got["held"]))
                p["held"] = got["held"]
                p["record"] = C.note_record(run_dir, PR.keep(run_dir, req["label"], where[n], req, held=got["held"]), got)
                f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
                continue
            path = Path(got["file"])
            rec = C.note_record(run_dir, PR.keep(run_dir, req["label"], where[n], req, made=path), got)   # how it was made
        PR.mirror(brand, run_dir, path)       # LD-75 (design pictures to Drive): made or reused, onto the run's Drive media/
        brief = dict(p)
        p.clear()
        p.update({"photo": "run:media/" + path.name, "ratio": ratio, "focus": [0.5, 0.4],
                  "alt": brief["todo"], "source": "made", "use": brief.get("use"), "brief": brief.get("brief", ""),
                  "route": got.get("route"), "record": rec})
        print("   made %-6s %-16s %s" % (got.get("route") or "reused", req["purpose"], path.name))
        f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")


_NOT = re.compile(r"\b(no|without|never)\s+(?:[a-z-]+,?\s+){0,1}[a-z-]+", re.I)
_NOBODY = re.compile(r"\b(no (people|person|one)|nobody|empty of people)\b", re.I)
_PRODUCT_WORDS = re.compile(r"\b(face (wash|quench|towel|brush|scrub|serum|cream)|face-wash|bristle face)\b", re.I)   # a name, not a face
_SOMEBODY = re.compile(r"\b(m[ae]n|wom[ae]n|person|people|customer|he|she|his|her|hands?|face|neck|jaw|arm|skin)\b", re.I)


def in_frame(p):
    """Is a person in this picture? The image engine hands the brand's own cast as references only when told yes
    (the team, 2026-10-28: every email picture went out with nobody saying, so every face was drawn from words alone).
    The slot's own `people` wins; a gift picture has nobody; otherwise read from the direction, its "no people / no
    one" first (a picture of hands with "no face" still has a person), then any person, face or hand once the negated
    phrases and product names (Face Wash, Face Quench) are taken out. None when nothing says."""
    if isinstance(p.get("people"), bool):
        return p["people"]
    if p.get("use") == "gift":
        return False
    text = "%s. %s" % (p.get("todo", ""), p.get("brief", ""))
    if _NOBODY.search(text):
        return False
    return True if _SOMEBODY.search(_NOT.sub(" ", _PRODUCT_WORDS.sub(" ", text))) else None


def unjudged(found):
    """The reason, when a picture was held or passed only because the picture judge could not run (no credits, no
    key: Brand-B nov-04's two pictures were thrown away on 2026-10-21 for a 402 and the slots sat empty for a week).
    None when the judge did look."""
    for x in json.loads(json.dumps(found or [], default=str)) if not isinstance(found, str) else [found]:
        for t in (x if isinstance(x, list) else [x]):
            t = t if isinstance(t, str) else json.dumps(t, default=str)
            if "judge did not run" in t:
                return t[t.index("judge did not run"):][:200]
    return None


def runs_for(brand, slot):
    """The copy runs for one calendar send: <brand>-<id> and its per-avatar versions."""
    base = RUNS / brand
    out = [p for p in sorted(base.glob("%s-%s*" % (brand, slot["id"]))) if (p / "deliverable" / "email.json").exists()]
    return out


def slot_from_run(run_dir, sid, fmt):
    """The send a run stands for when no calendar slot carries its id (an ad-hoc or relabelled run): its segment and
    day come from the copy run's own copy-argv.json, a list of argv strings, a flag's value the next one (LD-67 (design
    keeps segment)). A missing file, or one that is not a JSON list, adds nothing and never raises."""
    slot = {"id": sid, "type": fmt, "kind": "design", "format": None}
    try:
        argv = json.loads((Path(run_dir) / "copy-argv.json").read_text())
    except (OSError, ValueError):
        return slot
    if not isinstance(argv, list):
        return slot
    for flag, key in (("--segment", "segment"), ("--send-date", "date")):
        if flag in argv[:-1]:
            v = argv[argv.index(flag) + 1]
            if isinstance(v, str) and v:
                slot[key] = v
    return slot


def segments_of(slot):
    """The send's segments, only non-empty names: a missing segment is [] on the card, never [null] (LD-67 (design
    keeps segment))."""
    segs = slot.get("segments")
    if not (isinstance(segs, list) and segs):
        segs = [slot.get("segment")]
    return [s for s in segs if isinstance(s, str) and s]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("brand")
    ap.add_argument("month", nargs="?")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--only")
    ap.add_argument("--run", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pictures", action="store_true", help="also make every picture slot through the email picture chain")
    a = ap.parse_args()
    if a.month and a.run:   # a month lays out its whole window; with --run too, every send in it was redesigned (2026-10-28)
        sys.exit("give a month window or --run, not both: `line.py %s --run <run folder>` lays out that email only" % a.brand)
    import kinds
    import paths as CP
    lk = L.load(a.brand)
    proof_ids, proof_txt = proof_of(a.brand)
    used = {}
    todo = []
    if a.month:
        slots = kinds.apply(json.loads((CP.month_dir(a.brand, a.month) / "slots.json").read_text()), CP.brand_root(a.brand))
        slots = kinds.window(slots, a.start, a.days)
        if a.only:
            slots = [s for s in slots if s["id"] in a.only.split(",")]
        for s in slots:
            rs = runs_for(a.brand, s)
            if not rs:
                print("  %s %s: no finished copy yet (copy comes first: run the copy chain for this send)" % (s["date"], s["id"]))
            todo += [(r, s) for r in rs]
    for r in a.run:
        r = Path(r).resolve()
        rj = json.loads((r / "run.json").read_text())
        sid = r.name.replace(a.brand + "-", "").split("--")[0]
        mo = None
        for m_ in sorted((REPO / "runs" / "marketing-calendar" / a.brand).glob("20*")):
            f = m_ / "slots.json"
            if f.exists():
                for s in kinds.apply(json.loads(f.read_text()), CP.brand_root(a.brand)):
                    if s["id"] == sid:
                        mo = s
        todo.append((r, mo or slot_from_run(r, sid, rj.get("format"))))
    print("%s · %d email(s) to lay out" % (a.brand, len(todo)))
    for r, s in todo:
        run_send(a.brand, r, s, lk, proof_ids, proof_txt, used, a.dry_run)
        if a.pictures:
            make_pictures(a.brand, r, L.load(a.brand, r), a.dry_run)


if __name__ == "__main__":
    main()
