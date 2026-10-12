#!/usr/bin/env python3
"""Build a brand swipe from an AdPlexity advertiser sweep.

Stages:
  cluster   group the sweep's ads into copy blocks (angles), rank by volume
  resolve   pull /ads/<id> for ONE ad per angle to learn its landing page
  harvest   download every creative into the Drive mirror
  records   write the .md record set from blocks.json
  capture   screenshot every landing page, mobile, full-page

Usage:
  build.py cluster <ALL.json> <brand-slug>
  build.py resolve <brand-slug>
  build.py harvest <brand-slug>
  build.py records <brand-slug>
  build.py capture <brand-slug>

Writes <brand-slug>/blocks.json next to this script. Nothing here spends
credits except `resolve`, which costs exactly one credit per angle.
"""
import json, os, re, sys, collections
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
# The AdPlexity client, its ad cache and its market.db live inside this
# component, under capture/. They used to sit in ~/devel/daemn/research/dropship;
# the folder was copied here and the copy went ahead, but these lines kept
# pointing at the old one until 2026-09-23. Nothing this machine needs is
# outside the workspace any more.
CLIENT_DIR = os.path.join(HERE, "capture")


def norm_body(d):
    """Strip the Meta ad id AdPlexity appends to every primary text.

    Without this every ad looks like its own copy block. Validated against
    the Competitor A sweep: 830 ads collapse to exactly 18 blocks, matching the
    hand-built teardown.
    """
    return re.sub(r"\d{9,}$", "", (d or "").strip()).strip()



# ----------------------------------------------------------------- stage ---
# Funnel stage by pattern on headline + primary text. A heuristic, not truth:
# the rules are here to be read and corrected, and `stage` is recomputed on
# every cluster run, so editing these re-labels the whole library for free.
#
# Ranking without this mixes a retargeting scarcity ad in with an education
# angle. They are both real, but you build from them very differently.
STAGE_RULES = [
    ("bottom", [                       # most aware — offer, scarcity, guarantee
        r"low stock", r"out of stock", r"restock", r"sold out", r"final \d",
        r"\d+% ?off", r"save \d+%", r"\bsale\b", r"discount", r"\bdeal\b",
        r"money back", r"risk[- ]free", r"guarantee", r"last chance",
        r"ends (tonight|today)", r"limited time", r"buy \d", r"free shipping",
    ]),
    ("mid", [                          # solution/product aware — proof, story, result
        r"^i \b", r"\bi thought\b", r"\bi wish\b", r"\bi tried\b", r"\bi returned\b",
        r"gone in \d", r"clear in \w+", r"in (days|weeks)\b", r"\d+ years of",
        r"results?\b", r"before and after", r"\bmy \w+ (is|was|got)",
        r"over botox", r"instead of", r"switched to", r"actually work",
        r"changed my", r"ended\b", r"reviews?\b",
        # Named, aged testimonial and social proof — the proof middle, whoever
        # is running it.
        r"obsessed", r"verified", r"switching to", r"[-—]\s*\w+,\s*\d{2}\b",
        r"\d[\d,]{2,}\+? (women|men|customers|people)",
    ]),
    ("top", [                          # unaware/problem aware — education, callout
        r"understand", r"why \w+", r"\bhow \b", r"nobody told", r"don.?t want you",
        r"the truth", r"mistake", r"\bcauses?\b", r"reason", r"stop \w+ing",
        r"\d+ (reasons|things|lies|ways)", r"destroy", r"suffering",
        r"\?",                       # a question anywhere is a problem callout
        r"secret", r"method", r"science", r"dermatologist", r"ingredient",
        # Mechanism-and-origin hooks. A headline that names WHERE a thing comes
        # from or WHAT it is made of is teaching, not selling — and without
        # these 81% of our own account read unclassified while every one of its
        # headlines was doing exactly that ("Ancient Thai Dark Spot Remedy").
        r"ancient", r"remed(y|ies)", r"ritual", r"recipe", r"traditional",
        r"root cause", r"\bhack\b", r"\btrick\b", r"what .{0,20}actually",
        r"perch[eé]", r"errore", r"segreto",           # IT: why / mistake / secret
        r"you have to read",
    ]),
]

# Non-English patterns, checked after the English pass. the competitor runs most of
# its library in Italian; without these, 78% of the brand reads unclassified.
STAGE_RULES_INTL = [
    ("bottom", [r"sconto", r"offerta", r"garanzia", r"rimborsat", r"scorte",
                r"esaurit", r"ultimi\b", r"promo", r"prezzo"]),
    ("mid",    [r"risultat", r"ho provato", r"la svolta", r"addio\b", r"ciao ciao",
                r"altro che", r"invece di", r"#1\b", r"la ferrari", r"la scelta"]),
    ("top",    [r"rughe", r"flaccid", r"compatt", r"viso", r"collo", r"pelle",
                r"crema"]),
]


# A dated promotion is not a strategy. Competitor C's single biggest block by
# variant weight — LOW STOCK WARNING, 461 variants — is a Back To School
# sale running "August 14-23 only". Ranked raw, a 10-day promo outranks
# everything the brand actually believes year-round, so flag it instead.
SEASONAL = [
    r"back.?to.?school", r"back ?2 ?school", r"black friday", r"cyber monday",
    r"summer sale", r"spring sale", r"holiday sale", r"christmas", r"boxing day",
    r"new year", r"prime day", r"memorial day", r"labor day", r"labour day",
    r"valentine", r"mother.?s day", r"father.?s day", r"halloween",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\s*[-–—]\s*\d{1,2}\b",
]


def is_seasonal(headline, body=""):
    t = f"{headline or ''} {body or ''}".lower()
    return 1 if any(re.search(p, t) for p in SEASONAL) else 0


def stage_of(headline, body=""):
    """Classify on the HEADLINE first — the hook carries the awareness level.

    Reading the body pulls nearly everything to "bottom": almost every
    direct-response body mentions a guarantee or an offer somewhere, which
    would file an education hook like "Understand your acne type" as a
    scarcity ad. The body is only a fallback when the headline says nothing.
    """
    def match(text, rules):
        t = (text or "").lower()
        for name, pats in rules:
            if any(re.search(p, t) for p in pats):
                return name
        return None
    return (match(headline, STAGE_RULES) or match(headline, STAGE_RULES_INTL)
            or match(body, STAGE_RULES) or match(body, STAGE_RULES_INTL)
            or "unclassified")


def slugify(s, n=52):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return (s[:n].rstrip("-")) or "no-title"


def load_sweep(path):
    """Accept either a client ALL/offset file ({"items": [...]}) or a bare
    deduped list, as competitor-a_uniq.json is. A single --pages run writes a
    complete ALL file; a library swept across several invocations only has
    its full set in the deduped list."""
    d = json.load(open(path))
    return d if isinstance(d, list) else d["items"]


def cmd_cluster(all_json, brand):
    items = load_sweep(all_json)
    seen, uniq = set(), []
    for it in items:                      # sweeps can overlap across pages
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        uniq.append(it)

    groups = collections.OrderedDict()
    for it in uniq:
        key = ((it.get("title") or "").strip(), norm_body(it.get("description")))
        groups.setdefault(key, []).append(it)

    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    angles = []
    for i, ((title, body), ads) in enumerate(ranked, 1):
        vids = [a for a in ads if a.get("video_url")]
        angles.append({
            "nn": f"{i:02d}",
            "slug": f"{i:02d}_{slugify(title)}",
            "headline": title or "NO_TITLE",
            "primary_text": body,
            "count": len(ads),
            "video_count": len(vids),
            "image_count": len(ads) - len(vids),
            "rep_ad_id": ads[0]["id"],          # the one we spend a credit on
            "ad_ids": [a["id"] for a in ads],
            # meta_group_ads_count = how many near-identical ad variants run
            # this creative. Heat signal #1: nobody iterates a loser.
            "stage": stage_of(title, body),
            "seasonal": is_seasonal(title, body),
            "variants": sum((a.get("meta_group_ads_count") or 1) for a in ads),
            "max_variants": max((a.get("meta_group_ads_count") or 1) for a in ads),
            "media": {str(a["id"]): {"video": a.get("video_url") or "",
                                     "image": a.get("image_url") or "",
                                     "variants": a.get("meta_group_ads_count") or 1}
                      for a in ads},
            "landing_page": None,
        })

    out_dir = os.path.join(HERE, brand)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "blocks.json")

    # Carry resolved landing pages across a re-cluster. They cost a credit
    # each and the sweep cannot return them, so losing them to a re-run
    # would mean paying twice for data already in hand.
    if os.path.exists(path):
        prior = {b["slug"]: b.get("landing_page")
                 for b in json.load(open(path))["blocks"] if b.get("landing_page")}
        kept = 0
        for a in angles:
            if prior.get(a["slug"]):
                a["landing_page"] = prior[a["slug"]]; kept += 1
        if kept:
            print(f"  carried {kept} resolved landing pages forward")
    json.dump({"brand": brand, "source": os.path.basename(all_json),
               "creatives": len(uniq), "blocks": len(angles),
               "video": sum(a["video_count"] for a in angles),
               "image": sum(a["image_count"] for a in angles),
               "blocks": angles}, open(path, "w"), indent=1)
    print(f"{len(uniq)} creatives -> {len(angles)} angles  ->  {path}")
    for a in angles[:15]:
        print(f"  {a['count']:>4}  {a['nn']}  {a['headline'][:64]}")
    if len(angles) > 15:
        print(f"  … {len(angles)-15} more")


def cmd_resolve(brand):
    sys.path.insert(0, CLIENT_DIR)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "apx", os.path.join(CLIENT_DIR, "adplexity_client.py"))
    apx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(apx)

    path = os.path.join(HERE, brand, "blocks.json")
    doc = json.load(open(path))
    todo = [a for a in doc["blocks"] if not a.get("landing_page")]
    print(f"resolving {len(todo)} angles — {len(todo)} credits")

    spent = 0
    for a in todo:
        # An ad detail already pulled is already paid for. The client saves
        # every /ads/ response to raw/ad_<id>.json, so a re-run of resolve —
        # after a re-cluster, say — should cost nothing rather than buying
        # the same eight rows again.
        cached = os.path.join(CLIENT_DIR, "raw", f"ad_{a['rep_ad_id']}.json")
        if os.path.exists(cached):
            data, err = json.load(open(cached)), None
        else:
            data, err = apx.call(f"/ads/{a['rep_ad_id']}")
            spent += 1
        if err:
            print(f"  {a['nn']}  FAILED {err[:60]}")
            continue
        rec = data.get("data", data) if isinstance(data, dict) else data
        lps = rec.get("landing_pages") or []
        a["landing_page"] = lps[0].get("url") if lps else None
        print(f"  {a['nn']}  {a['count']:>4}  {a['landing_page'] or 'NO LP'}")
        json.dump(doc, open(path, "w"), indent=1)   # checkpoint every call

    # The client bills 1 credit per /ads/ call. Log it, or the ledger in
    # scan_runs silently under-reports every resolve run.
    if spent:
        con = apx.log_run("adplexity /ads/<id> (swipe resolve)",
                          {"brand": brand, "blocks": len(todo)}, spent,
                          f"one detail pull per angle; credits={spent}", "competitor")
        con.execute("UPDATE scan_runs SET cost_usd=? WHERE run_id=last_insert_rowid()",
                    (spent * 99.0 / 5000,))
        con.commit()

    got = sum(1 for a in doc["blocks"] if a.get("landing_page"))
    print(f"\n{got}/{len(doc['blocks'])} angles have a landing page · ~{spent} credits")
    pages = collections.Counter(a["landing_page"] for a in doc["blocks"] if a.get("landing_page"))
    print(f"{len(pages)} distinct landing pages:")
    for u, n in pages.most_common():
        print(f"  {n:>3} angles  {u}")


# ---------------------------------------------------------------- harvest ---
DRIVE = str(swipe_home.root("paid"))


def _fetch(url, dest):
    import urllib.request
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "skip"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())
        return "ok"
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        return f"FAIL {e}"


def cmd_harvest(brand, workers=8):
    """Download every creative into the Drive mirror. Costs no credits."""
    from concurrent.futures import ThreadPoolExecutor
    doc = json.load(open(os.path.join(HERE, brand, "blocks.json")))
    jobs = []
    for a in doc["blocks"]:
        base = os.path.join(DRIVE, brand, "blocks", a["slug"])
        for aid, m in a["media"].items():
            if m.get("video"):
                os.makedirs(os.path.join(base, "video"), exist_ok=True)
                jobs.append((m["video"], os.path.join(base, "video", f"{aid}.mp4")))
                if m.get("image"):   # AdPlexity's image_url is the poster frame
                    jobs.append((m["image"], os.path.join(base, "video", f"{aid}_poster.jpg")))
            elif m.get("image"):
                os.makedirs(os.path.join(base, "photos"), exist_ok=True)
                jobs.append((m["image"], os.path.join(base, "photos", f"{aid}.jpg")))

    print(f"{brand}: {len(jobs)} files -> {os.path.join(DRIVE, brand)}")
    tally = collections.Counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, res in enumerate(ex.map(lambda j: _fetch(*j), jobs), 1):
            tally[res.split()[0]] += 1
            if i % 200 == 0:
                print(f"  {i}/{len(jobs)}")
    have = sum(1 for _, d in jobs if os.path.exists(d) and os.path.getsize(d) > 0)
    print(f"  landed {have}/{len(jobs)}  ({dict(tally)})")
    return have, len(jobs)


# ---------------------------------------------------------------- records ---
def page_slug(url):
    """Stable folder name for a landing page, ignoring query strings.

    Query strings on these links are attribution tokens (competitor-a's ?trybe=,
    Meta's ?fbclid=), not page variants — captures under different tokens
    came back byte-identical, so they must not fork the slug.
    """
    u = re.sub(r"^https?://", "", (url or "").split("?")[0]).rstrip("/")
    host, _, path = u.partition("/")
    base = path or host.split(".")[0]
    return slugify(base.replace("/", "-"), 60)


def cmd_records(brand):
    # the capture stage's own record of every page it shot, when it exists
    _pj = os.path.join(HERE, brand, "pages.json")
    caps = json.load(open(_pj)) if os.path.exists(_pj) else {}
    """Write the .md record set from blocks.json. No network, no credits."""
    doc = json.load(open(os.path.join(HERE, brand, "blocks.json")))
    root = os.path.join(HERE, brand)
    os.makedirs(os.path.join(root, "blocks"), exist_ok=True)
    os.makedirs(os.path.join(root, "_pages"), exist_ok=True)
    drive_root = swipe_home.label("paid", brand)
    total = len(doc["blocks"])

    # page slug -> the angles that land on it
    pages = collections.OrderedDict()
    for a in doc["blocks"]:
        if not a.get("landing_page"):
            continue
        pages.setdefault(page_slug(a["landing_page"]),
                         {"url": a["landing_page"], "blocks": []})["blocks"].append(a)

    for a in doc["blocks"]:
        lp = a.get("landing_page")
        slug = page_slug(lp) if lp else None
        media = []
        if a["video_count"]:
            media.append(f"- `video/` — {a['video_count']} x `<ad_id>.mp4`, "
                         f"each with a matching `<ad_id>_poster.jpg` frame")
        if a["image_count"]:
            media.append(f"- `photos/` — {a['image_count']} x `<ad_id>.jpg` "
                         f"(the static creative itself)")
        media.append(f"- `page/` — the landing page this angle sends to, "
                     f"copied from `_pages/{slug}/`" if slug else
                     "- no `page/` — this angle has no resolvable landing page")
        ids = a["ad_ids"]
        body = a["primary_text"] or "_(no primary text — merge-tag failure or image-only ad)_"
        out = (f"# {a['nn']} · {a['headline']}\n\n"
               f"**{a['count']} live creatives** — {a['video_count']} video, "
               f"{a['image_count']} image  \n"
               f"**{a.get('variants', a['count'])} ad variants** — most-cloned single "
               f"creative ran {a.get('max_variants', 1)}x _(heat signal: nobody clones a loser)_  \n"
               f"**Landing page:** `{lp or 'none — unresolved'}`  \n"
               f"**Drive:** `{drive_root}/blocks/{a['slug']}/`  \n"
               f"**Rank:** {a['nn']} of {total} by creative volume\n\n"
               f"## Headline\n\n> {a['headline']}\n\n"
               f"## Primary text (verbatim)\n\n> {body}\n\n"
               f"## Media (on Drive)\n\n" + "\n".join(media) + "\n\n"
               f"Ad IDs: `{ids[0]}` … `{ids[-1]}` ({len(ids)} total). "
               f"Source records in `_raw/`.\n")
        open(os.path.join(root, "blocks", f"{a['slug']}.md"), "w").write(out)

    for slug, p in pages.items():
        listed = "\n".join(f"- {x['nn']} · {x['headline']} ({x['count']} creatives)"
                            for x in p["blocks"])
        ads = sum(x["count"] for x in p["blocks"])
        # what the capture stage learned about this page, when it has run:
        # pages.json carries the structural type and the real pixel height.
        cap = caps.get(slug, {})
        kind = cap.get("type") or "_pending capture_"
        tall = f"{cap['height']:,}px" if cap.get("height") else "_pending capture_"
        out = (f"# {slug}\n\n"
               f"**Type:** {kind}  \n"
               f"**URL:** {p['url']}  \n"
               f"**Page height:** {tall}  \n"
               f"**Angles served:** {len(p['blocks'])} ({ads} creatives)  \n"
               f"**Drive:** `{drive_root}/_pages/{slug}/`\n\n"
               f"## Angles that land here\n\n{listed}\n\n"
               f"## Media (on Drive)\n\n"
               f"- `page.png` — full-page mobile capture (390x844 @2x)\n"
               f"- `page.html` — rendered DOM at capture time\n"
               f"- `page.txt` — extracted visible text\n")
        open(os.path.join(root, "_pages", f"{slug}.md"), "w").write(out)

    print(f"{brand}: {len(doc['blocks'])} angle files, {len(pages)} page files")
    return pages


# ---------------------------------------------------------------- capture ---
def classify(text, html):
    """Decide page type structurally, not by how it looks.

    Order matters: a quiz app is a quiz even though it has a cart; a
    numbered list is a listicle even inside an advertorial masthead.
    """
    t = (text or "").lower()
    if re.search(r"question \d+|step \d+ of|\bquiz\b", t) or "quiz." in (html or "")[:2000].lower():
        return "quiz"
    numbered = len(re.findall(r"^\s*\d{1,2}[\.\)]\s+\S", text or "", re.M))
    if numbered >= 5:
        return "listicle"
    if re.search(r"add to cart|add to bag|buy now|sold out", t):
        return "product-page"
    if len(text or "") > 4000:
        return "advertorial"
    return "unknown"


def _dismiss_overlay(pg, out_dir):
    """Shoot the entry modal to popup.png, then dismiss it. True if one was there.

    Detected by CONTENT, not by CSS position. These modals are not always
    fixed overlays — Competitor C's renders inline in the document flow, so a
    position:fixed probe finds nothing while the capture is still half
    covered by an email-capture block. What they do share is vocabulary: an
    email field, a discount, and an opt-out that a real visitor clicks.
    """
    DECLINE = ["I want to pay full price", "No thanks", "No, thanks",
               "No Thanks", "I'll pay full price", "Continue without",
               "Maybe later", "Not now", "Close", "Dismiss", "Skip"]

    def find_modal():
        """Return the modal's bounding element handle, or None."""
        return pg.evaluate_handle("""(declines) => {
            const seen = [];
            // an email field is the reliable anchor for a capture modal
            for (const inp of document.querySelectorAll(
                    'input[type=email], input[name*=email i], input[placeholder*=email i]')) {
                const r = inp.getBoundingClientRect();
                if (!r.width || !r.height) continue;
                let el = inp;
                for (let i = 0; i < 6 && el.parentElement; i++) {
                    el = el.parentElement;
                    const t = (el.innerText || '');
                    if (declines.some(d => t.includes(d)) || /%\s*off/i.test(t)) {
                        seen.push(el); break;
                    }
                }
            }
            if (!seen.length) return null;
            // smallest container that still holds the whole modal
            return seen.sort((a,b) => a.innerText.length - b.innerText.length)[0];
        }""", DECLINE)

    # These modals are on a timer, not on load. Measured on competitor-c:
    # absent at 2.5s and 5s, present at 9s. Probing once on arrival finds
    # nothing and reports a clean capture that is in fact half covered, so
    # poll instead of guessing a single wait.
    el = None
    for _ in range(14):                      # up to ~14s
        handle = find_modal()
        el = handle.as_element() if handle else None
        if el:
            break
        pg.wait_for_timeout(1000)
    if not el:
        return False
    try:
        el.screenshot(path=os.path.join(out_dir, "popup.png"), timeout=15000)
    except Exception:
        pg.screenshot(path=os.path.join(out_dir, "popup.png"))   # viewport fallback

    # Click the opt-out the way a visitor would.
    for word in DECLINE:
        try:
            btn = pg.get_by_text(word, exact=False).first
            if btn and btn.is_visible():
                btn.click(timeout=2000)
                pg.wait_for_timeout(700)
                break
        except Exception:
            continue
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # Whatever survived, take it out of the page shot.
    still = find_modal()
    node = still.as_element() if still else None
    if node:
        pg.evaluate("(el) => { el.style.display = 'none'; "
                    "document.body.style.overflow = 'auto'; }", node)
    return True


def cmd_capture(brand, lane="paid"):
    """Capture every landing page once, mobile, full-page, after lazy-load.

    Works for any lane that HAS landing pages. The competitor lane reads them
    off its angle file; our own lane reads them off the ads pulled from the
    account. Organic has none — a post is not a funnel — and asking for them
    there returns nothing rather than inventing an empty folder.
    """
    from playwright.sync_api import sync_playwright
    pages = collections.OrderedDict()
    if lane == "own":
        f = os.path.join(HERE, "own", brand, "ads.json")
        for a in json.load(open(f))["ads"]:
            u = (a.get("landing_page") or "").split("?")[0]
            if u.startswith("http"):
                pages.setdefault(page_slug(u), u)
        out_root = os.path.join(HERE, "own", brand, "_pages")
    else:
        doc = json.load(open(os.path.join(HERE, brand, "blocks.json")))
        for a in doc["blocks"]:
            if a.get("landing_page"):
                pages.setdefault(page_slug(a["landing_page"]), a["landing_page"])
        out_root = os.path.join(DRIVE, brand, "_pages")
    results = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)
        for slug, url in pages.items():
            d = os.path.join(out_root, slug)
            os.makedirs(d, exist_ok=True)
            ctx = br.new_context(viewport={"width": 390, "height": 844},
                                 device_scale_factor=2,
                                 user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                             "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                                             "Version/17.0 Mobile/15E148 Safari/604.1"))
            pg = ctx.new_page()
            try:
                pg.goto(url, timeout=60000, wait_until="domcontentloaded")
                pg.wait_for_timeout(2500)
                # An entry modal (email capture, discount wheel, age gate) sits
                # over the page and hides what we came to look at. Keep it —
                # it is part of the funnel — but as its own capture, then get
                # it out of the way before shooting the page itself.
                popup = _dismiss_overlay(pg, d)
                pg.wait_for_timeout(600)
                # force lazy-loaded sections to render before measuring height
                pg.evaluate("""async () => {
                    await new Promise(res => {
                        let y = 0;
                        const t = setInterval(() => {
                            window.scrollBy(0, 900); y += 900;
                            if (y >= document.body.scrollHeight) { clearInterval(t); res(); }
                        }, 120);
                        setTimeout(() => { clearInterval(t); res(); }, 15000);
                    });
                }""")
                pg.wait_for_timeout(1200)
                pg.evaluate("window.scrollTo(0, 0)")
                height = pg.evaluate("document.body.scrollHeight")
                # A 45,000px page at 2x is ~90,000px of raster and Chrome
                # times out rendering it in one pass. Drop to 1x for the
                # giants — a readable shot beats a failed one.
                if height > 28000:
                    pg.evaluate("document.body.style.zoom = '1'")
                    ctx2 = br.new_context(viewport={"width": 390, "height": 844},
                                          device_scale_factor=1,
                                          user_agent=pg.evaluate("navigator.userAgent"))
                    p2 = ctx2.new_page()
                    p2.goto(url, timeout=60000, wait_until="domcontentloaded")
                    _dismiss_overlay(p2, d)
                    p2.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    p2.wait_for_timeout(2500)
                    p2.evaluate("window.scrollTo(0, 0)")
                    p2.screenshot(path=os.path.join(d, "page.png"),
                                  full_page=True, timeout=180000)
                    ctx2.close()
                else:
                    pg.screenshot(path=os.path.join(d, "page.png"),
                                  full_page=True, timeout=120000)
                html = pg.content()
                text = pg.inner_text("body")
                open(os.path.join(d, "page.html"), "w").write(html)
                open(os.path.join(d, "page.txt"), "w").write(text)
                kind = classify(text, html)
                results[slug] = {"height": height, "type": kind, "url": url,
                                 "popup": popup}
                print(f"  {slug:<46} {kind:<13} {height}px"
                      f"{'  + popup' if popup else ''}")
            except Exception as e:
                results[slug] = {"height": None, "type": "FAILED", "url": url,
                                 "error": str(e)[:160]}
                print(f"  {slug:<46} FAILED  {str(e)[:70]}")
            ctx.close()
        br.close()

    pages_json = os.path.join(os.path.dirname(out_root), "pages.json") \
        if lane == "own" else os.path.join(HERE, brand, "pages.json")
    json.dump(results, open(pages_json, "w"), indent=1)
    ok = sum(1 for r in results.values() if r["type"] != "FAILED")
    print(f"{brand}: captured {ok}/{len(results)} pages")
    return results


# ----------------------------------------------------------------- brief ---
def cmd_brief(brand, domain="", swept="", credits="", replace=False):
    """Write _BRAND.md and teardown.md. Judgment sections stay empty slots."""
    root = os.path.join(HERE, brand)
    if os.path.exists(os.path.join(root, "teardown.md")) and not replace:
        sys.exit(f"{brand}/teardown.md exists and holds hand-written judgment — nothing written; pass --replace to overwrite it")
    doc = json.load(open(os.path.join(root, "blocks.json")))
    pj = os.path.join(root, "pages.json")
    caps = json.load(open(pj)) if os.path.exists(pj) else {}

    blocks = doc["blocks"]
    n_ads, n_ang = doc["creatives"], len(doc["blocks"])
    heads = len({b["headline"] for b in blocks})
    per = round(n_ads / n_ang, 1) if n_ang else 0
    drive_root = swipe_home.label("paid", brand)

    pages = collections.OrderedDict()
    for a in blocks:
        if a.get("landing_page"):
            sl = page_slug(a["landing_page"])
            e = pages.setdefault(sl, {"url": a["landing_page"], "blocks": 0, "ads": 0})
            e["blocks"] += 1; e["ads"] += a["count"]
    types = collections.Counter(caps.get(sl, {}).get("type", "uncaptured") for sl in pages)

    counts = (
        "| | |\n|---|---|\n"
        f"| Creatives live in window | **{n_ads}** |\n"
        f"| Distinct copy blocks (angles) | **{n_ang}** |\n"
        f"| Distinct headlines | **{heads}** |\n"
        f"| Unique video files | **{doc['video']}** |\n"
        f"| Static creatives | **{doc['image']}** |\n"
        f"| Creatives per angle | **{per} average**, {blocks[0]['count']} at the top |\n"
        f"| Landing pages | **{len(pages)}** — "
        + ", ".join(f"{n} {t}" for t, n in types.most_common()) + " |\n")

    open(os.path.join(root, "_BRAND.md"), "w").write(
        f"# {brand}\n\n"
        f"**Domain:** `{domain}`  \n"
        f"**Swept:** {swept} · **Window:** 30d  \n"
        f"**Source:** AdPlexity Social API `/search/ads` · "
        f"`search_mode=advertiser.lp_url_redirect_outbound`, `meta_grouping_id=2`  \n"
        f"**Pulled by:** `swipe/build.py` · **Credits:** ~{credits}  \n"
        f"**Drive:** `{drive_root}/`\n\n"
        f"## Counts\n\n{counts}\n"
        f"## What they sell\n\n<!-- JUDGMENT SLOT -->\n\n"
        f"## Offer mechanics\n\n<!-- JUDGMENT SLOT -->\n\n"
        f"## Their stack\n\n<!-- JUDGMENT SLOT -->\n\n"
        f"## Capture caveat\n\n<!-- note anything odd about the capture run -->\n")

    def fmt(a):
        if a["video_count"] and not a["image_count"]:
            return "video"
        if a["image_count"] and not a["video_count"]:
            return "static"
        return f'{a["video_count"]}v/{a["image_count"]}s'

    lp_rows = "\n".join(
        "| {c} | {h} | {f} | `{lp}` |".format(
            c=a["count"], h=a["headline"][:70], f=fmt(a),
            lp=a["landing_page"] or "unresolved")
        for a in blocks)

    copy_blocks = "\n".join(
        f"### {a['nn']}. {a['headline']}\n\n"
        f"`{a['count']} creatives` · `{a['video_count']}v/{a['image_count']}s` · "
        f"`{a['landing_page'] or 'unresolved'}`\n\n"
        f"> {a['primary_text'] or '_(no primary text)_'}\n"
        for a in blocks)

    page_rows = "\n".join(
        f"| `{p['url']}` | {caps.get(sl,{}).get('height') or '—'} | "
        f"{p['blocks']} | {p['ads']} | {caps.get(sl,{}).get('type','uncaptured')} |"
        for sl, p in sorted(pages.items(), key=lambda kv: -kv[1]["ads"]))

    open(os.path.join(root, "teardown.md"), "w").write(
        f"# {brand} — creative strategy teardown\n\n"
        f"**Pulled:** {swept} · **Source:** AdPlexity Social API `/search/ads` · "
        f"**Query:** `search_query={domain}`, 30-day window  \n"
        f"**Pulled by:** `swipe/build.py` · **Raw:** `_raw/` · **Credits spent:** ~{credits}  \n"
        f"**Media:** `{drive_root}/`\n\n"
        f"## The number that matters\n\n{counts}\n"
        f"## Structural findings\n\n<!-- JUDGMENT SLOT — not machine-written. -->\n\n"
        f"## Angle → landing page map\n\n"
        f"| Creatives | Angle | Format | Landing page |\n|---:|---|---|---|\n{lp_rows}\n\n"
        f"## The {n_ang} copy blocks, verbatim\n\n{copy_blocks}\n"
        f"## The funnel, captured\n\n"
        f"Pages captured in headless Chrome at 390x844 (2x), full-page, after forced lazy-load scroll.\n\n"
        f"| Page | Height | Angles | Creatives | Type |\n|---|---:|---:|---:|---|\n{page_rows}\n\n"
        f"## Offer mechanics\n\n<!-- JUDGMENT SLOT -->\n\n"
        f"## Their stack\n\n<!-- JUDGMENT SLOT -->\n\n"
        f"## Local library\n\n"
        f"Words in `components/swipe-paid/{brand}/`, media on Drive at `{drive_root}/`.\n\n"
        f"## What to take, and what to beat\n\n"
        f"<!-- JUDGMENT SLOT — not machine-written. -->\n\n**Take:**\n\n**Beat:**\n\n"
        f"## Next\n\n")
    print(f"{brand}: _BRAND.md + teardown.md written ({n_ang} angles, {len(pages)} pages)")


# -------------------------------------------------------------------- db ---
DB = os.path.join(HERE, "swipe.db")

BRAND_META = {   # domain + sweep date per brand, as pulled
    "competitor-a":       ("competitor-a.example", "2026-08-19"),
    "brand-c":       ("brand-c.shop", "2026-09-01"),
    "competitor-b":    ("competitor-b.example", "2026-08-20"),
    "competitor-c": ("competitor-c.example", "2026-08-20"),
    "competitor-f":  ("competitor-f.example", "2026-09-19"),
    "competitor-g":         ("competitor-g.example", "2026-09-19"),
    "competitor-h":         ("competitor-h.example", "2026-09-20"),
}


def cmd_db(*_):
    """(Re)build swipe.db from every brand's blocks.json + pages.json."""
    import sqlite3
    con = sqlite3.connect(DB)
    # Drop first: the schema is edited as the pipeline learns, and
    # CREATE TABLE IF NOT EXISTS would silently keep an outdated shape.
    # Nothing here is authoritative, so rebuilding is always correct.
    for v in ("block_page", "copy_lock", "swipe_creatives", "to_judge", "swiped"):
        con.execute(f"DROP VIEW IF EXISTS {v}")
    for t in ("brands", "blocks", "ads", "pages"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.executescript(open(os.path.join(HERE, "schema.sql")).read())

    brands = sorted(d for d in os.listdir(HERE)
                    if os.path.isdir(os.path.join(HERE, d))
                    and os.path.exists(os.path.join(HERE, d, "blocks.json")))

    for brand in brands:
        root = os.path.join(HERE, brand)
        doc = json.load(open(os.path.join(root, "blocks.json")))
        pjs = os.path.join(root, "pages.json")
        caps = json.load(open(pjs)) if os.path.exists(pjs) else {}
        drive_root = swipe_home.label("paid", brand)
        domain, swept = BRAND_META.get(brand, ("", ""))

        page_stats = collections.OrderedDict()
        for a in doc["blocks"]:
            if not a.get("landing_page"):
                continue
            sl = page_slug(a["landing_page"])
            e = page_stats.setdefault(sl, {"url": a["landing_page"], "blocks": 0, "ads": 0})
            e["blocks"] += 1
            e["ads"] += a["count"]

        con.execute("INSERT INTO brands VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (brand, domain, swept, doc["creatives"], len(doc["blocks"]),
                     len(page_stats), doc["video"], doc["image"],
                     round(doc["creatives"] / len(doc["blocks"]), 2) if doc["blocks"] else 0,
                     drive_root))

        for sl, p in page_stats.items():
            c = caps.get(sl, {})
            con.execute("INSERT INTO pages VALUES (?,?,?,?,?,?,?,?)",
                        (brand, sl, p["url"], c.get("type", "uncaptured"),
                         c.get("height"), p["blocks"], p["ads"],
                         f"{drive_root}/_pages/{sl}"))

        for a in doc["blocks"]:
            sl = page_slug(a["landing_page"]) if a.get("landing_page") else None
            con.execute("INSERT INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (brand, a["nn"], a["slug"], a["headline"], a["primary_text"],
                         a.get("stage", "unclassified"), a.get("seasonal", 0),
                         a["count"], a["video_count"], a["image_count"],
                         a.get("variants", a["count"]), a.get("max_variants", 1),
                         a.get("landing_page"), sl,
                         f"{drive_root}/blocks/{a['slug']}"))
            for aid, m in a["media"].items():
                is_v = bool(m.get("video"))
                # The convention's fields, written by swipe_fields.py. Absent
                # until that has run, so default rather than fail: a corpus
                # that will not build is worse than one with a column to fill.
                f = m.get("fields") or {}
                con.execute("INSERT OR REPLACE INTO ads VALUES "
                            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (aid, brand, a["slug"], "video" if is_v else "image",
                             m.get("variants", 1),
                             m.get("video") or "", m.get("image") or "",
                             f"{drive_root}/blocks/{a['slug']}/"
                             + (f"video/{aid}.mp4" if is_v else f"photos/{aid}.jpg"),
                             m.get("swipe_id") or f"swipe:{brand}:{aid}",
                             f.get("media", "video" if is_v else "static"),
                             f.get("source", "unclassified"),
                             f.get("talent", "unclassified"),
                             f.get("problem", "unclassified"),
                             f.get("angle", "unclassified"),
                             f.get("concept", "unclassified"),
                             f.get("format", "unclassified"),
                             f.get("ratio", "unknown"),
                             m.get("verdict", "")))
    con.commit()

    for t in ("brands", "blocks", "ads", "pages"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<8} {n:>5}")
    print(f"\n{DB}")
    con.close()


# ------------------------------------------------------------------- top ---
STAGE_ORDER = ["top", "mid", "bottom", "unclassified"]
STAGE_LABEL = {
    "top":    "TOP  — education / problem callout  (build creative strategy from these)",
    "mid":    "MID  — proof, story, result         (the persuasion middle)",
    "bottom": "BOTTOM — offer, scarcity, guarantee (volume plays; print these, don't strategise them)",
    "unclassified": "UNCLASSIFIED — rules didn't match; read and re-file",
}


def cmd_top(brand=None, pct="80"):
    """Per-brand shortlist, grouped by funnel stage.

    Ranked on variant replication, not creative volume: how many creatives
    they built says how much they made, how many near-identical variants
    they cloned says how much they believe.

    Stage matters as much as rank. A scarcity ad at the top of a brand's
    list is a bottom-funnel volume play, not an angle to build from.
    """
    import sqlite3
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    cutoff = float(pct) / 100.0
    brands = [brand] if brand else [r[0] for r in con.execute(
        "SELECT brand FROM brands ORDER BY brand")]

    for b in brands:
        allrows = con.execute("SELECT * FROM blocks WHERE brand=? ORDER BY variants DESC",
                              (b,)).fetchall()
        seasonal = [r for r in allrows if r["seasonal"]]
        rows = [r for r in allrows if not r["seasonal"]]
        total = sum(r["variants"] for r in rows) or 1
        keep, run = [], 0
        for r in rows:
            keep.append(r); run += r["variants"]
            if run / total >= cutoff:
                break

        print(f"\n{'='*78}\n{b.upper()}  —  {len(keep)} of {len(rows)} evergreen blocks carry "
              f"{pct}% of evergreen variant weight\n{'='*78}")
        if seasonal:
            sv = sum(r["variants"] for r in seasonal)
            av = sum(r["variants"] for r in allrows) or 1
            print(f"  [{len(seasonal)} dated-promo blocks held out — {sv} variants, "
                  f"{100*sv//av}% of this brand. Volume plays, not strategy:")
            for r in seasonal[:3]:
                print(f"     {r['variants']:>4}  {(r['headline'] or '')[:52]}")
            print("   ]")

        by_stage = collections.defaultdict(list)
        for r in keep:
            by_stage[r["stage"]].append(r)
        for st in STAGE_ORDER:
            grp = by_stage.get(st)
            if not grp:
                continue
            share = 100 * sum(r["variants"] for r in grp) // total
            print(f"\n  {STAGE_LABEL[st]}")
            print(f"  {share}% of this brand's variant weight · {len(grp)} blocks")
            print(f"    {'nn':<4} {'creat':>5} {'vars':>5} {'max':>4}  {'page type':<13} headline")
            for r in grp:
                pt = con.execute("SELECT page_type FROM pages WHERE brand=? AND slug=?",
                                 (b, r["page_slug"] or "")).fetchone()
                print(f"    {r['nn']:<4} {r['creatives']:>5} {r['variants']:>5} "
                      f"{r['max_variants']:>4}  {(pt[0] if pt else '—'):<13} "
                      f"{(r['headline'] or '')[:46]}")

        print(f"\n  PAGES — where this brand's weight lands")
        for r in con.execute("SELECT * FROM pages WHERE brand=? ORDER BY ads_served DESC LIMIT 6",
                             (b,)):
            print(f"    {r['ads_served']:>4} creatives · {r['blocks_served']:>3} angles · "
                  f"{r['page_type']:<13} {str(r['height'] or '—'):>7}px  {r['slug'][:40]}")

        hot = con.execute("SELECT * FROM ads WHERE brand=? ORDER BY variants DESC LIMIT 3",
                          (b,)).fetchall()
        print(f"\n  MOST-CLONED SINGLE CREATIVES")
        for r in hot:
            print(f"    {r['variants']:>3}x  {r['media_type']:<6} {r['drive_file'].split('/',3)[-1]}")
    con.close()


# ----------------------------------------------------------------- watch ---
def fold_delta(doc, fresh, today):
    """Fold fresh ads into doc's blocks in place; return the brand-new block count.

    doc["blocks"] stays the list; the count goes under doc["block_count"].
    """
    # Fold into existing blocks, or open new ones for copy never seen before.
    by_key = {(a["headline"], a["primary_text"]): a for a in doc["blocks"]}
    added_blocks = 0
    for it in fresh:
        key = ((it.get("title") or "").strip(), norm_body(it.get("description")))
        a = by_key.get(key)
        if a is None:
            a = {"nn": "--", "slug": f"new_{slugify(key[0])}", "headline": key[0] or "NO_TITLE",
                 "primary_text": key[1], "count": 0, "video_count": 0, "image_count": 0,
                 "rep_ad_id": it["id"], "ad_ids": [], "media": {},
                 "stage": stage_of(*key), "seasonal": is_seasonal(*key),
                 "variants": 0, "max_variants": 1, "landing_page": None,
                 "first_seen": today}
            doc["blocks"].append(a); by_key[key] = a; added_blocks += 1
        v = it.get("meta_group_ads_count") or 1
        a["ad_ids"].append(it["id"]); a["count"] += 1
        a["variants"] = a.get("variants", 0) + v
        a["max_variants"] = max(a.get("max_variants", 1), v)
        a["video_count" if it.get("video_url") else "image_count"] += 1
        a["media"][str(it["id"])] = {"video": it.get("video_url") or "",
                                     "image": it.get("image_url") or "", "variants": v}
    doc["creatives"] = sum(a["count"] for a in doc["blocks"])
    doc["block_count"] = len(doc["blocks"])
    doc["video"] = sum(a["video_count"] for a in doc["blocks"])
    doc["image"] = sum(a["image_count"] for a in doc["blocks"])
    return added_blocks


def cmd_watch(brand, domain=None, page=25, maxpages=8):
    """Daily delta: pull only what is new since the last sweep.

    A full re-sweep bills one credit per ad returned — ~2,000 a day across
    three brands, which no plan survives. This orders by `newest` and stops
    at the first ad id already in blocks.json, so the bill is roughly the
    number of genuinely new ads plus one page of overlap.

    Writes deltas/<date>.json and folds the new ads into blocks.json.
    """
    sys.path.insert(0, CLIENT_DIR)
    import importlib.util
    from datetime import date, timedelta
    spec = importlib.util.spec_from_file_location(
        "apx", os.path.join(CLIENT_DIR, "adplexity_client.py"))
    apx = importlib.util.module_from_spec(spec); spec.loader.exec_module(apx)

    root = os.path.join(HERE, brand)
    doc = json.load(open(os.path.join(root, "blocks.json")))
    known = {str(i) for a in doc["blocks"] for i in a["ad_ids"]}
    domain = domain or BRAND_META.get(brand, ("",))[0]
    end = date.today(); start = end - timedelta(days=29)

    fresh, spent, stop = [], 0, False
    for p in range(maxpages):
        data, err = apx.call("/search/ads", {
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "search_query": domain,
            "search_mode": "advertiser.lp_url_redirect_outbound",
            "count": page, "offset": p * page, "order": "newest",
            "meta_grouping_id": 2})
        if err:
            print(f"  page {p} FAILED — {err[:70]}"); break
        items = data.get("data", []) if isinstance(data, dict) else (data or [])
        spent += ((data.get("meta") or {}).get("credits_cost") or len(items))
        for it in items:
            if str(it["id"]) in known:
                stop = True                      # caught up with the last sweep
                break
            fresh.append(it)
        if stop or len(items) < page:
            break

    con = apx.log_run("adplexity watch /search/ads",
                      {"brand": brand, "domain": domain}, len(fresh),
                      f"daily delta; credits={spent}", "competitor")
    con.execute("UPDATE scan_runs SET cost_usd=? WHERE run_id=last_insert_rowid()",
                (spent * 99.0 / 5000,))
    con.commit()

    os.makedirs(os.path.join(root, "deltas"), exist_ok=True)
    out = os.path.join(root, "deltas", f"{end.isoformat()}.json")
    json.dump({"brand": brand, "date": end.isoformat(), "new": len(fresh),
               "credits": spent, "items": fresh}, open(out, "w"), indent=1)

    print(f"{brand}: {len(fresh)} new creatives · ~{spent} credits · {out}")
    if not fresh:
        return 0

    added_blocks = fold_delta(doc, fresh, end.isoformat())
    json.dump(doc, open(os.path.join(root, "blocks.json"), "w"), indent=1)
    print(f"  folded in · {added_blocks} brand-new copy blocks")
    return len(fresh)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("db", "top"):
        (cmd_db if sys.argv[1] == "db" else cmd_top)(); sys.exit(0)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "cluster":
        cmd_cluster(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "resolve":
        cmd_resolve(sys.argv[2])
    elif sys.argv[1] == "harvest":
        cmd_harvest(sys.argv[2])
    elif sys.argv[1] == "records":
        cmd_records(sys.argv[2])
    elif sys.argv[1] == "capture":
        cmd_capture(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "paid")
    elif sys.argv[1] == "brief":
        cmd_brief(*[x for x in sys.argv[2:] if x != "--replace"], replace="--replace" in sys.argv[2:])
    elif sys.argv[1] == "db":
        cmd_db()
    elif sys.argv[1] == "top":
        cmd_top(*sys.argv[2:])
    elif sys.argv[1] == "watch":
        cmd_watch(*sys.argv[2:])
    else:
        sys.exit(__doc__)
