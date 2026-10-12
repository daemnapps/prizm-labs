#!/usr/bin/env python3
"""page_pick — the landing page, chosen when the brief is written.

    page_pick.py pick   --brand acme --brief brief-0289 [--product …] [--offer …]
                                         what it would pick, and why — writes nothing
    page_pick.py record --brand acme --brief brief-0289 [--product …]
                                         pick and write it onto the brief record
    page_pick.py meta-page link_acme_cpk_quiz
                                         the page part of a Meta ad name (body-scrub-cpk-quiz)

the owner, 2 Oct 2026: the landing page belongs to the brief — the only step that
knows the product, the offer and the swipe's page type. Everything after it
(hand-off, delivery, the approval card) inherits the brief's page.

THE PICK, in order:
  1. sells the brief's product — the page's funnel is that product's
     (brands/<brand>/web/funnels/funnels.json), or its offers / its store
     product page carry it (the store catalog: $CATALOG_JSON, default
     brands/_catalog/catalog.json). A page that
     only sells it inside a set is used only when nothing sells it alone, and
     the why says so.
  2. carries the brief's offer, when the brief names one.
  3. is the same page type as the page the SWIPE sent people to — advertorial,
     quiz, offer page or store page. The swipe's page is read from what the
     teardown kept (the swipe block's "Landing page:" line, its pages.json
     type, or a landing page in the run's run.json). A store page and an offer
     page stand in for each other (both take the money) when there is no exact
     match. No swipe page recorded → the product's main live page (the one
     with the most live ads), and the why says so.
  4. is live — answers HTTP 200 now. A page that does not is skipped and named.

Written onto the brief as `landing_page`:
    {"link_ids": [...], "why": "...", "swipe_page": {url, type, from} | null,
     "checked": {link id: status}, "picked": "YYYY-MM-DD", "by": "page_pick"}
— on the register record (components/image-teardown/briefs.json, which the
hand-off reads; its `links` filled when empty). A brief with no register record
gets a PROPOSAL at runs/naming/<brand>/landing-proposals/briefs.json instead:
a machine never writes the brand's brief header (K2 (brands write wall), SI-97 (brand research proposals)); a person commits an
accepted pick into brands/<brand>/briefs/briefs.json. Readers (landing_page,
landing_ids) take the register, then the proposal, then the brand header.
Links a person already set are kept; the picker's own answer is written beside
them as `picker_would`.

META AD NAMES. `meta_page(link_id)` is the one place the page part of a Meta ad
name is made: `<funnel id>-<page>` — the way the live ads already read
(`…_body-scrub-cpk-quiz`, `…_body-scrub-cpk-offer`; the funnel's landing page
is its offer page). handoff.funnel_of and the card uploader both call it.
"""
import argparse, json, os, re, sys, urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))          # appended: naming's deliver.py must not shadow a lane's own
import names as N  # noqa: E402

WS = N.WS
CATALOG = Path(os.environ.get("CATALOG_JSON") or (WS / "brands" / "_catalog" / "catalog.json"))   # yours, never shipped
SWIPES = Path(os.environ.get("SWIPES_DIR") or (WS / "components/swipe-paid"))                      # the paid-swipe library, where you keep one
TYPES = ("advertorial", "quiz", "offer", "store")
WORD = {"advertorial": "advertorial", "quiz": "quiz", "offer": "offer page", "store": "store page"}
NEAR = {"store": "offer", "offer": "store"}           # both take the money
PAGE_WORDS = {"landing": "offer"}                     # the live Meta names call the landing page the offer page

_CAT = {}


# ---------------------------------------------------------------- the lists
def catalog(path=None):
    p = Path(path or CATALOG)
    if p not in _CAT:
        _CAT[p] = json.loads(p.read_text()) if p.is_file() else {}
    return _CAT[p]


def records(brand, cat=None):
    return ((catalog() if cat is None else cat).get("brands") or {}).get(N.slug(brand), {}).get("records") or {}


def funnels(brand, root=None):
    f = Path(root or WS) / "brands" / N.slug(brand) / "web/funnels/funnels.json"
    try:
        return json.loads(f.read_text()).get("funnels") or []
    except (OSError, ValueError):
        return []


def _norm_url(u):
    return str(u or "").strip().split("?")[0].split("#")[0].rstrip("/").lower()


def funnel_of_url(brand, url, fl=None):
    """The funnel a page sits in: the longest funnel path the page's path starts
    with (the host may be the build host — upload.page_for reads it the same way)."""
    path = urlparse(url or "").path or "/"
    host = urlparse(url or "").netloc.lower()
    best = None
    for f in fl if fl is not None else funnels(brand):
        fu = urlparse(f.get("url") or "")
        fp = fu.path or "/"
        if not path.startswith(fp):
            continue
        if fp in ("", "/") and fu.netloc.lower() != host:
            continue           # a bare domain funnel only claims its own host
        if not best or len(fp) > len(urlparse(best["url"]).path or "/"):
            best = f
    return best


# ---------------------------------------------------------------- page types
def type_of_url(url, known=None):
    """advertorial | quiz | offer | store | None, from the page's URL and any
    type the swipe library already gave it (pages.json)."""
    u = urlparse(url or "")
    path = u.path.lower()
    known = (known or "").lower()
    if "quiz" in path or "quiz" in u.netloc.lower() or known == "quiz":
        return "quiz"
    if known in ("product-page",) or "/products/" in path or "/catalogue/" in path:
        return "store"
    if known in ("advertorial", "listicle", "prelander", "salespage", "blog", "review-page", "comparison"):
        return "advertorial"
    if re.search(r"(^|[/_-])(adv|advertorial|article|presell|salespage|listicle|reasons|blog)", path):
        return "advertorial"
    if re.search(r"(^|[/_-])(landing|offer|special|order|select|checkout|lp)([/_.-]|$)", path):
        return "offer"
    return None


def link_type(rec):
    """Our own page's type: an explicit `page_type` on the record wins."""
    if rec.get("page_type") in TYPES:
        return rec["page_type"]
    t = type_of_url(rec.get("url"))
    if t:
        return t
    if (rec.get("surface_kind") or "").startswith("storefront"):
        return "store"
    return "offer"          # a funnel's own sales page takes the money


def live_ads(rec):
    m = re.search(r"(\d+)\s+live ads?", str(rec.get("label") or rec.get("page") or ""))
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------- sells it?
def _pslug(s):
    return N.slug(re.sub(r"[™®]", "", str(s or "")))


def product_id(brand, product, cat=None):
    """The catalog's product id for a brief's product (`serum` → product_acme_glow-serum)."""
    if not product:
        return None
    want = _pslug(product)
    prods = {k: r for k, r in records(brand, cat).items() if r.get("type") == "product"}
    exact = f"product_{N.slug(brand)}_{want}"
    if exact in prods:
        return exact
    named = [k for k, r in prods.items() if want in {_pslug(x) for x in r.get("old_names") or []}]
    if len(named) == 1:
        return named[0]
    pre = [k for k in prods if k.split("_", 2)[2].startswith(want + "-")]
    return pre[0] if len(pre) == 1 else None


def _item_product(recs, item):
    """An offer's item → (product ids sold alone, product ids sold in a set)."""
    r = recs.get(item) or {}
    if r.get("type") == "variant":
        return {r.get("product")}, set()
    if r.get("type") == "product":
        return {item}, set()
    if r.get("type") == "bundle":
        inside = set()
        for c in r.get("components") or []:
            alone, _ = _item_product(recs, c.get("item"))
            inside |= alone
        return set(), inside
    return set(), set()


def _offers_sell(recs, offers, pid):
    best = None
    for o in offers or []:
        alone, inside = _item_product(recs, (recs.get(o) or {}).get("item"))
        if pid in alone:
            return "direct", o
        if pid in inside and not best:
            best = ("in-set", o)
    return best or (None, None)


def sells(brand, rec, pid, cat=None, fl=None):
    """("direct" | "in-set" | None, how) — does this page sell the product?"""
    if not pid:
        return None, "no product"
    recs = records(brand, cat)
    f = funnel_of_url(brand, rec.get("url"), fl)
    if f and f.get("product") and product_id(brand, f["product"], cat) == pid:
        return "direct", f"in the {f['id']} funnel, which sells it"
    offers = list(rec.get("offers") or [])
    url = _norm_url(rec.get("url"))
    for k, r in recs.items():            # a placement on the same page carries its offers
        if r.get("type") == "placement" and url and _norm_url(r.get("url")) == url:
            offers += r.get("offers") or []
    how, o = _offers_sell(recs, offers, pid)
    if how:
        label = (recs.get(o) or {}).get("label") or o
        return how, (f"its offer {label}" if how == "direct" else f"it ends on {label}, which has it in the set")
    m = re.search(r"/products/([^/?#]+)", rec.get("url") or "")
    if m:
        handle = m.group(1).lower()
        for k, r in recs.items():
            refs = {str(x.get("handle") or "").lower() for x in r.get("store_refs") or []}
            if handle in refs and r.get("type") == "product" and k == pid:
                return "direct", f"its own store product page ({handle})"
    return None, "does not sell it"


# ---------------------------------------------------------------- the swipe's page
def _block_page(competitor, block_file=None, ad_id=None, slug_hint=None):
    """(url, type) of a swipe block's landing page, from the swipe library."""
    d = SWIPES / competitor
    if not d.is_dir():
        return None, None
    url = None
    if block_file:
        f = d / "blocks" / block_file
        if f.is_file():
            m = re.search(r"\*\*Landing page:\*\*\s*`([^`]+)`", f.read_text())
            url = m.group(1) if m else None
    if not url and (ad_id or slug_hint):
        try:
            blocks = json.loads((d / "blocks.json").read_text()).get("blocks") or []
        except (OSError, ValueError):
            blocks = []
        for b in blocks:
            ids = b.get("ad_ids")
            ids = json.loads(ids) if isinstance(ids, str) else (ids or [])
            if ad_id and (int(ad_id) in ids or str(ad_id) in (b.get("media") or {})):
                url = b.get("landing_page")
                break
            if slug_hint and N.slug(b.get("slug", "").replace("_", "-")).startswith(slug_hint):
                url = b.get("landing_page")
                break
    if not url:
        return None, None
    known = None
    try:
        pages = json.loads((d / "pages.json").read_text())
        for p in pages.values():
            if _norm_url(p.get("url")) == _norm_url(url):
                known = p.get("type")
                break
    except (OSError, ValueError):
        pass
    return url, type_of_url(url, known)


def _run_json(run):
    p = WS / str(run) / "run.json"
    try:
        return json.loads(p.read_text()) if p.is_file() else {}
    except ValueError:
        return {}


def swipe_page(brand, reg_rec=None, header=None):
    """{url, type, from} — the page the swipe sent people to, or None."""
    for rec in (reg_rec or {}, header or {}):
        sw = rec.get("swipe") or {}
        url = sw.get("landing_page") or sw.get("page") or rec.get("swipe_page")
        if url:
            return {"url": url, "type": type_of_url(url), "from": "the brief record"}
        if sw.get("brand") and sw.get("block_file"):
            url, t = _block_page(N.slug(sw["brand"]), sw["block_file"])
            if url:
                return {"url": url, "type": t, "from": f"swipe block {sw['brand']}/{sw['block_file']}"}
    run = (reg_rec or {}).get("run")
    if run and "/" in str(run):
        rj = _run_json(run)
        url = rj.get("landing_page") or (rj.get("swipe") or {}).get("landing_page")
        if url:
            return {"url": url, "type": type_of_url(url), "from": f"{run}/run.json"}
        # a run named after its swipe: <competitor prefix>-<ad id | block slug>
        label = Path(run).name.lower()
        toks = label.split("-")
        comps = [c.name for c in SWIPES.iterdir() if c.is_dir() and not c.name.startswith(("_", "."))] if SWIPES.is_dir() else []
        cand = [c for c in comps if toks and len(toks[0]) >= 3 and c.startswith(toks[0])]
        if len(cand) == 1:
            ad = next((t for t in toks if t.isdigit() and len(t) >= 6), None)
            url, t = _block_page(cand[0], ad_id=ad, slug_hint=None if ad else "-".join(toks[1:4]))
            if url:
                return {"url": url, "type": t, "from": f"swipe {cand[0]} ({'ad ' + ad if ad else 'block ' + '-'.join(toks[1:4])})"}
    return None


# ---------------------------------------------------------------- live?
def fetch_status(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (page_pick)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# ---------------------------------------------------------------- the pick
def brief_record(brand, brief, product=None):
    """(register key, register record, brand-file header) for the brief."""
    hit = N.find_brief(brand, brief, product)
    if not hit:
        return None, None, None
    reg = hit.get("register")
    return (reg or {}).get("key"), ({k: v for k, v in reg.items() if k not in ("key", "_table")} if reg else None), hit.get("header")


def _offer_of(reg_rec, header):
    for rec in (reg_rec or {}, header or {}):
        o = rec.get("offer") or (rec.get("declares") or {}).get("offer")
        if o:
            return o if isinstance(o, str) else (o[0] if o else None)
    return None


def pick(brand, brief=None, product=None, offer=None, *, reg_rec=None, header=None,
         cat=None, fl=None, fetch=None, today=None):
    """The landing page for one brief. Returns the `landing_page` dict
    (`link_ids` empty when nothing fits, and the why says what is missing)."""
    brand = N.slug(brand)
    fetch = fetch or fetch_status
    if brief and reg_rec is None and header is None:
        _, reg_rec, header = brief_record(brand, brief, product)
    product = product or (reg_rec or {}).get("product") or (header or {}).get("product")
    offer = offer or _offer_of(reg_rec, header)
    fl = funnels(brand) if fl is None else fl
    pid = product_id(brand, product, cat)
    out = {"link_ids": [], "why": "", "swipe_page": None, "checked": {},
           "picked": (today or date.today()).isoformat(), "by": "page_pick"}
    if not pid:
        out["why"] = f"the brief's product ({product or 'not recorded'}) is not a {brand} product in the catalog"
        return out
    sp = swipe_page(brand, reg_rec, header)
    out["swipe_page"] = sp
    want = (sp or {}).get("type")
    cands = []
    for lid, r in records(brand, cat).items():
        if r.get("type") != "link" or r.get("status") != "live" or not r.get("url"):
            continue
        how, said = sells(brand, r, pid, cat, fl)
        if not how:
            continue
        t = link_type(r)
        type_rank = 2 if want and t == want else (1 if want and NEAR.get(want) == t else 0)
        offer_rank = 1 if offer and offer in (r.get("offers") or []) else 0
        cands.append({"id": lid, "rec": r, "type": t, "sells": how, "said": said,
                      "rank": (type_rank, 1 if how == "direct" else 0, offer_rank, live_ads(r))})
    if not cands:
        out["why"] = f"no live {brand} page in the catalog sells {product}"
        return out
    cands.sort(key=lambda c: c["rank"], reverse=True)
    dead = []
    for c in cands:
        st = fetch(c["rec"]["url"])
        out["checked"][c["id"]] = st
        if st != 200:
            dead.append(f"{c['id']} answered {st or 'nothing'}")
            continue
        r = c["rec"]
        page = f"{c['id']} ({r.get('url')})"
        if want and c["rank"][0] == 2:
            lead = f"the swipe went to {'a' if want != 'offer' else 'an'} {WORD[want]} ({sp['url']}, from {sp['from']}); this is our live {WORD[c['type']]} that sells {product}"
        elif want and c["rank"][0] == 1:
            lead = (f"the swipe went to a {WORD[want]} ({sp['url']}, from {sp['from']}); we have no live {WORD[want]} "
                    f"that sells {product}, so the nearest kind — our {WORD[c['type']]}")
        elif want:
            lead = (f"the swipe went to {'an' if want in ('advertorial', 'offer') else 'a'} {WORD[want]} ({sp['url']}, from {sp['from']}); "
                    f"we have no live {WORD[want]} that sells {product}, so the main live page for {product}")
        else:
            lead = f"no swipe landing page is recorded for this brief, so the main live page for {product}"
        bits = [lead, f"sells it: {c['said']}"]
        if c["sells"] == "in-set":
            bits.append(f"no live page sells {product} on its own")
        if offer:
            bits.append(f"offer {offer} {'is on this page' if c['rank'][2] else 'is not on any live page that sells it — the page was chosen without it'}")
        if live_ads(r):
            bits.append(f"{live_ads(r)} live ads already point here")
        bits.append("answers 200 today")
        if dead:
            bits.append("skipped: " + "; ".join(dead))
        out["link_ids"] = [c["id"]]
        out["page"] = r.get("url")
        out["page_type"] = c["type"]
        out["why"] = " · ".join(bits)
        return out
    out["why"] = f"every live page that sells {product} failed its check: " + "; ".join(dead)
    return out


# ---------------------------------------------------------------- writing it down
def _write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def landing_proposals_file(brand, root=None):
    """The machine's landing picks for briefs with no register record — a
    proposal under runs/, never the brand's briefs.json."""
    return Path(root or WS) / "runs" / "naming" / N.slug(brand) / "landing-proposals" / "briefs.json"


def _proposals(brand, root=None):
    f = landing_proposals_file(brand, root)
    try:
        d = json.loads(f.read_text()) if f.is_file() else {}
    except Exception:
        d = {}
    return f, (d if isinstance(d.get("briefs"), list) else {"briefs": []})


def proposed_landing(brand, brief, product=None, root=None):
    """The open proposal's `landing_page` for (brief, product), or None."""
    _, d = _proposals(brand, root)
    for e in d["briefs"]:
        if e.get("brief") == brief and e.get("product") == product:
            return e.get("landing_page")
    return None


def _propose(brand, header, lp, root=None):
    f, d = _proposals(brand, root)
    entry = {"brief": header.get("brief"), "product": header.get("product"), "landing_page": lp,
             "proposed": date.today().isoformat()}
    d["briefs"] = [e for e in d["briefs"]
                   if not (e.get("brief") == entry["brief"] and e.get("product") == entry["product"])] + [entry]
    f.parent.mkdir(parents=True, exist_ok=True)
    _write_json(f, d)


def record(brand, brief, product=None, lp=None, *, register=None, root=None, fetch=None):
    """Pick (unless `lp` is given) and write `landing_page` onto the brief's
    register record — or, with no register record, as a proposal under runs/
    (never the brand's briefs.json). Links already set by a person are kept;
    the pick goes beside them as `picker_would`. Returns
    (landing_page as written, [where it was written])."""
    brand = N.slug(brand)
    key, reg_rec, header = brief_record(brand, brief, product)
    if reg_rec is None and header is None:
        raise KeyError(f"{brand} {brief}: no such brief")
    lp = lp or pick(brand, brief, product, reg_rec=reg_rec, header=header, fetch=fetch)
    had = [x if isinstance(x, str) else (x or {}).get("id") for x in (reg_rec or {}).get("links") or []]
    had = [x for x in had if x] or list(((header or {}).get("landing_page") or {}).get("link_ids") or [])
    if had and had != lp.get("link_ids"):
        lp = {"link_ids": had, "why": "chosen by hand before the picker existed — kept",
              "picker_would": lp.get("link_ids"), "picker_why": lp.get("why"),
              "swipe_page": lp.get("swipe_page"), "checked": lp.get("checked"),
              "picked": lp.get("picked"), "by": "page_pick"}
    where = []
    if reg_rec is not None:
        reg_path = Path(register or N.register_file())
        reg = json.loads(reg_path.read_text())
        rec = reg["briefs"][key]
        rec["landing_page"] = lp
        if lp["link_ids"] and not rec.get("links"):
            rec["links"] = list(lp["link_ids"])
        _write_json(reg_path, reg)
        where.append(f"{reg_path.relative_to(WS) if reg_path.is_relative_to(WS) else reg_path}#{key}")
    elif header is not None:
        _propose(brand, header, lp, root)
        where.append(f"runs/naming/{N.slug(brand)}/landing-proposals/briefs.json#{header.get('brief')}")
    return lp, where


def _landing(brand, brief, product=None, root=None):
    """(landing_page or None, register record) — the register, then the open
    proposal, then the brand header; each only when it carries link ids."""
    if not brief or brief == "none":
        return None, None
    try:
        _, reg_rec, header = brief_record(brand, brief, product)
    except N.AmbiguousBrief:
        return None, None
    cands = [(reg_rec or {}).get("landing_page")]
    if header is not None:
        cands += [proposed_landing(brand, header.get("brief"), header.get("product"), root),
                  header.get("landing_page")]
    for lp in cands:
        if (lp or {}).get("link_ids"):
            return lp, reg_rec
    return None, reg_rec


def landing_page(brand, brief, product=None, root=None):
    """The brief's landing page dict (register, then proposal, then brand
    header), or None when none carries link ids."""
    return _landing(brand, brief, product, root)[0]


def landing_ids(brand, brief, product=None, root=None):
    """The brief's landing page link ids — what the hand-off, the card writer and
    the feeders use when nobody names a page. [] when none is recorded."""
    lp, reg_rec = _landing(brand, brief, product, root)
    if lp:
        return list(lp["link_ids"])
    links = [x if isinstance(x, str) else (x or {}).get("id") for x in (reg_rec or {}).get("links") or []]
    return [x for x in links if x]


# ---------------------------------------------------------------- Meta names
def meta_page(link_id, cat=None, fl=None):
    """The page part of a Meta ad name: `<funnel id>-<page>` (body-scrub-cpk-quiz,
    body-scrub-cpk-offer). None when the link or its funnel is not known —
    the caller keeps its old spelling then."""
    parts = str(link_id or "").split("_")
    if len(parts) < 3 or parts[0] != "link":
        return None
    brand = parts[1]
    r = records(brand, cat).get(link_id) or {}
    url = r.get("url")
    if not url:
        return None
    f = funnel_of_url(brand, url, fl)
    if not f:
        return None
    rest = urlparse(url).path[len(urlparse(f["url"]).path or "/"):] if urlparse(url).path.startswith(urlparse(f["url"]).path or "/") else ""
    segs = [s for s in rest.split("/") if s]
    page = re.sub(r"\.html?$", "", segs[-1]) if segs else (f.get("entry_page") or "")
    page = PAGE_WORDS.get(page, page)
    name = N.slug(f"{f['id']}-{page}" if page else f["id"])
    return name if N.SLUG.match(name) else None


# ---------------------------------------------------------------- command line
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("pick", "record"):
        p = sub.add_parser(name)
        p.add_argument("--brand", required=True)
        p.add_argument("--brief", required=True, nargs="+")
        p.add_argument("--product")
        p.add_argument("--offer")
    m = sub.add_parser("meta-page")
    m.add_argument("link_ids", nargs="+")
    a = ap.parse_args()
    if a.cmd == "meta-page":
        for lid in a.link_ids:
            print(f"{lid}  →  {meta_page(lid) or '(not known — old spelling stands)'}")
        return
    for b in a.brief:
        try:
            if a.cmd == "pick":
                lp = pick(a.brand, b, a.product, a.offer)
                where = []
            else:
                lp, where = record(a.brand, b, a.product)
        except (KeyError, N.AmbiguousBrief) as e:
            print(f"{b}: {e}")
            continue
        print(f"{b}: {', '.join(lp['link_ids']) or 'NO PAGE'}")
        print(f"   why: {lp['why']}")
        if lp.get("picker_would") is not None:
            print(f"   picker would: {', '.join(lp['picker_would']) or 'nothing'} — {lp.get('picker_why')}")
        for w in where:
            print(f"   written: {w}")


if __name__ == "__main__":
    main()
