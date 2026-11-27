#!/usr/bin/env python3
"""pages — the one page list: every page of every brand, its versions and its tests.

    page_list.py list   [--brand B] [--place P] [--step S]     the pages, by place and step
    page_list.py show   <page ID | old link id | address>     one page, every version, every test
    page_list.py funnel <brand>_<place>                        a funnel: its pages in step order
    page_list.py next   <page ID>                              the version number the next build gets
    page_list.py control <page ID> <vN>                        give vN the control mark (ID and address unchanged)
    page_list.py check  --brand B [--no-fetch]                 the daily check: a live page with no ID is flagged
    page_list.py backfill --brand B [--extra addresses.txt] [--apply]
                                                           give every live page of a brand its ID (never re-points one)

owner, 2026-11-14: ads have a clean naming and brief system and pages did not. A FUNNEL is the whole page
sequence to purchase; a PAGE is one step in it; a PAGE BRIEF is the work order for a new page, a new control or
a variant; a PAGE VERSION is one build of a page. Plan and its revisions: page-naming-owner.md.

THE PAGE ID: `<brand>_<place>_<page>` — lowercase, `-` inside a value, `_` between values, like
`adset_<brand>_<avatar>_<angle>`. `place` is a funnel id from the brand's funnel list, `store`, or another place
recorded here; `page` is read off the address (the path after the place, segments joined by `-`, `.html` dropped;
the place's root is `home`; a store page is `<kind>-<handle>`). Never typed, never coined, never reused or
re-pointed. A page's ID and address never change; versions change.

THREE LENGTHS, like ads: long (run folders, build files) `<ID>_v<N>`; the ID; in Meta only `<place>-<page>`,
kept in `meta` and frozen for every page a live ad already names (page_pick.meta_page reads it). A version never
appears in an ad name: a test runs on the page.

STEPS: landing → cart → checkout → post-purchase (STEPS, KIND_STEP). A page's `kind` says what it is.

VERSIONS: v1, v2, v3 … every build numbered, never reused; exactly one carries `control: true`. A page brief
reserves its version at the start of the run (`reserve_version`); the page chain files the build (`file_build`).

TESTS (words set by owner, 2026-11-14 — the scientific method): one test per page at a time; `hypothesis` written
before it starts, `control` (the version running today) vs `variant` (the one new version), `group` (which one a
visitor got, PostHog's side), `primary_metric` checkout_reached, `confirm_metric` purchase, `stop` set before it
can run, `gate` (compliance pass + the owner's dated approval), `result` variant wins · control holds ·
no difference. Field names are the funnel repos' pv-tests.json names, except that pv-tests' `status`
(draft|live|ended) is kept here as `state`: in this repo `status` holds only draft/approved/deprecated
(builder card rule 5). A design test keeps one offer in both groups; an offer test changes only the offer.

Brand-agnostic: brands, places and stores are data in pages.json and the brands' funnel lists, never named here.
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import names as N  # noqa: E402

WS = N.WS
LIST = HERE / "pages.json"
VAL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PAGE_ID = re.compile(rf"^({VAL})_({VAL})_({VAL})$")
VERSION = re.compile(r"^v([1-9][0-9]*)$")

STEPS = ("landing", "cart", "checkout", "post-purchase")
KIND_STEP = {
    "advertorial": "landing", "salespage": "landing", "presell": "landing", "prelander": "landing",
    "listicle": "landing", "quiz": "landing", "portal": "landing", "offer": "landing", "product": "landing",
    "collection": "landing", "page": "landing", "article": "landing", "blog": "landing", "home": "landing",
    "cart": "cart", "checkout": "checkout",
    "upsell": "post-purchase", "downsell": "post-purchase", "receipt": "post-purchase",
}
JOBS = ("new-page", "new-control", "variant")
RESULTS = ("variant wins", "control holds", "no difference")
TEST_STATES = ("draft", "live", "ended")
TEST_TYPES = ("design", "offer")
PAGE_STATES = ("planned", "live", "archived", "off", "retired")
# archived (2026-11-14): still answers on the web, untouched — but no new ad, brief or test may use it
NUMBERS = ("conversion", "order_value", "upsell_take", "subscribe_rate")
STORE_KIND = {"products": "product", "catalogue": "product", "collections": "collection", "category": "collection",
              "pages": "page", "blogs": "article", "blog": "article"}
PAGE_WORDS = {"landing": "offer"}        # the live Meta names call a funnel's landing page its offer page


# ---------------------------------------------------------------- the list
def load(path=None):
    p = Path(path or LIST)
    if not p.is_file():
        return {"pages": {}, "places": {}}
    d = json.loads(p.read_text())
    d.setdefault("pages", {})
    d.setdefault("places", {})
    return d


def save(data, path=None):
    p = Path(path or LIST)
    data["pages"] = dict(sorted(data["pages"].items()))
    data["places"] = dict(sorted(data["places"].items()))
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- ids
def is_page_id(s):
    return bool(PAGE_ID.match(str(s or "")))


def parse_page_id(s):
    m = PAGE_ID.match(str(s or ""))
    return {"brand": m.group(1), "place": m.group(2), "page": m.group(3)} if m else None


def page_id(brand, place, page):
    pid = f"{N.slug(brand)}_{place}_{page}"
    if not is_page_id(pid):
        raise ValueError(f"not a clean page ID: {pid}")
    return pid


def place_id(brand, place):
    return f"{N.slug(brand)}_{place}"


def long_name(pid, version):
    if not is_page_id(pid) or not VERSION.match(str(version or "")):
        raise ValueError(f"not a page ID and version: {pid} {version}")
    return f"{pid}_{version}"


def run_label(pid, version):
    """The page chain's run folder name under runs/page-chain/<brand>/: `<place>_<page>_<vN>`."""
    p = parse_page_id(pid)
    return f"{p['place']}_{p['page']}_{version}"


def _clean(s):
    s = re.sub(r"\.html?$", "", str(s or "").lower())
    s = re.sub(r"_\d+$", "", s)                      # a store handle's trailing record number
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def norm_url(u):
    u = str(u or "").strip().split("?")[0].split("#")[0]
    u = re.sub(r"\.html?$", "", u).rstrip("/").lower()
    return re.sub(r"^https?://(www\.)?", "", u)


# ---------------------------------------------------------------- reading an address
def page_part(path, store=False):
    """(page part, kind or None) of a path relative to its place. Store paths name their kind."""
    segs = [s for s in str(path or "").split("/") if s]
    if store:
        if segs and re.fullmatch(r"[a-z]{2}", segs[0]):
            segs = segs[1:]                            # a language prefix (`/en/about-us/`)
        if not segs:
            return "home", "home"
        if segs[0] in ("cart", "checkout"):
            return segs[0], segs[0]
        if segs[0] == "catalogue" and len(segs) > 2 and segs[1] == "category":
            return "collection-" + _clean(segs[2]), "collection"
        kind = STORE_KIND.get(segs[0])
        if kind == "article":
            if len(segs) == 2:
                return "blog-" + _clean(segs[1]), "blog"
            return ("article-" + _clean(segs[-1]), "article") if len(segs) > 2 else (None, None)
        if kind and len(segs) > 1:
            return f"{kind}-{_clean(segs[-1])}", kind
        return "page-" + _clean("-".join(segs)), "page"
    if not segs:
        return "home", None
    return _clean("-".join(segs)), None


def kind_of(page):
    """What a funnel page is, read off its name. None when the name says nothing."""
    p = str(page or "")
    if p.startswith(("product-", "collection-", "page-", "article-", "blog-")):
        return p.split("-", 1)[0]
    if p in ("cart",):
        return "cart"
    if p.startswith("checkout") or p.endswith("-checkout"):
        return "checkout"
    if p.startswith(("receipt", "thank-you")):
        return "receipt"
    if p.startswith("oto-dw"):
        return "downsell"
    if p.startswith("oto-"):
        return "upsell"
    if p.startswith("quiz"):
        return "quiz"
    if p.startswith("portal"):
        return "portal"
    if p.startswith("salespage"):
        return "salespage"
    if p.startswith("prelander"):
        return "prelander"
    if p.startswith("listicle"):
        return "listicle"
    if p.startswith("presell"):
        return "presell"
    if p in ("adv",) or p.startswith("advertorial"):
        return "advertorial"
    if p.startswith(("landing", "select", "offer")):
        return "offer"
    if p == "home":
        return "home"
    return None


def step_of(kind):
    return KIND_STEP.get(kind or "")


# ---------------------------------------------------------------- places
def brand_funnels(brand, root=None):
    f = Path(root or WS) / "brands" / N.slug(brand) / "web/funnels/funnels.json"
    try:
        return json.loads(f.read_text()).get("funnels") or []
    except (OSError, ValueError):
        return []


def places_for(brand, data=None, root=None):
    """Every place of a brand: {place: {url, kind, state, product}} — the brand's funnels, then the places the
    page list itself records (a store with no funnel entry)."""
    out = {}
    for f in brand_funnels(brand, root):
        if not f.get("id") or not f.get("url"):
            continue
        out[f["id"]] = {"url": f["url"], "kind": "store" if f["id"] == "store" else "funnel",
                        "state": "off" if str(f.get("status") or "").startswith("off") else "live",
                        "product": f.get("product"), "code_slug": f.get("code_slug")}
    for k, v in ((data or load()).get("places") or {}).items():
        b, _, place = k.partition("_")
        if b == N.slug(brand) and place not in out and v.get("url"):
            out[place] = {"url": v["url"], "kind": v.get("kind") or "funnel", "state": v.get("state") or "live",
                          "product": v.get("product"), "code_slug": None}
    return out


def place_of(brand, url, places):
    """(place, path after the place) for an address: the longest place path the address starts with on the same
    host, a live place before an off one; a host's other paths fall to that host's live place."""
    u = urlparse(url or "")
    host, path = u.netloc.lower().replace("www.", ""), u.path or "/"
    best = None
    for name, p in places.items():
        pu = urlparse(p["url"])
        if pu.netloc.lower().replace("www.", "") != host:
            continue
        pp = pu.path or "/"
        if not path.startswith(pp) and path.rstrip("/") != pp.rstrip("/"):
            continue
        rank = (len(pp), p.get("state") != "off")
        if not best or rank > best[0]:
            best = (rank, name, path[len(pp):] if path.startswith(pp) else "")
    if best:
        return best[1], best[2]
    same = [n for n, p in places.items() if urlparse(p["url"]).netloc.lower().replace("www.", "") == host
            and p.get("state") != "off"]
    return (same[0], path) if len(same) == 1 else (None, None)


def id_for_url(brand, url, places):
    """(page ID, kind) an address would carry, or (None, None)."""
    place, rest = place_of(brand, url, places)
    if not place:
        return None, None
    store = places[place]["kind"] == "store"
    part, kind = page_part(rest, store=store)
    if not part:
        return None, None
    pid = f"{N.slug(brand)}_{place}_{part}"
    return (pid, kind or kind_of(part)) if is_page_id(pid) else (None, None)


# ---------------------------------------------------------------- finding a page
def find(any_ref, data=None):
    """(page ID, entry) for a page ID, an old catalog link id, a version's address, the page's address or its Meta
    piece — or (None, None)."""
    data = data or load()
    pages = data["pages"]
    s = str(any_ref or "").strip()
    if s in pages:
        return s, pages[s]
    n = norm_url(s) if ("/" in s or "." in s) else None
    for pid, e in pages.items():
        if s in (e.get("old_ids") or []) or (s and s == e.get("meta")):
            return pid, e
        if n and (norm_url(e.get("url")) == n or any(norm_url(v.get("url")) == n for v in e.get("versions") or [])
                  or any(norm_url(u) == n for u in e.get("also_urls") or [])):
            return pid, e
    return None, None


def meta(any_ref, data=None):
    """The page part of a Meta ad name for a page (frozen for pages live ads already name), or None."""
    _, e = find(any_ref, data)
    return (e or {}).get("meta")


def usable(any_ref, data=None):
    """May a NEW ad, brief or test use this page? False for an archived, off or retired page (it may still answer
    on the web; what already points at it stays). True for a page the list does not hold (the list has no say)."""
    pid, e = find(any_ref, data)
    return e is None or e.get("state") in ("live", "planned")


def control(entry):
    v = [x for x in (entry or {}).get("versions") or [] if x.get("control")]
    return v[0] if v else None


def funnel(brand_place, data=None):
    """A funnel: {place, steps: {step: [page IDs]}} in step order, live pages only."""
    data = data or load()
    b, _, place = str(brand_place).partition("_")
    steps = {s: [] for s in STEPS}
    for pid, e in data["pages"].items():
        if e.get("brand") == b and e.get("place") == place and e.get("state") == "live" and e.get("step") in steps:
            steps[e["step"]].append(pid)
    return {"place": brand_place, "steps": steps, **((data.get("places") or {}).get(brand_place) or {})}


# ---------------------------------------------------------------- entries
def _day(today):
    return today if isinstance(today, str) else (today or date.today()).isoformat()


def new_entry(brand, place, part, url, *, kind=None, product=None, meta_name=None, old_ids=None, state="live",
              today=None):
    kind = kind or kind_of(part)
    today = _day(today)
    m = meta_name or N.slug(f"{place}-{PAGE_WORDS.get(part, part)}")
    return {
        "brand": N.slug(brand), "place": place, "page": part, "step": step_of(kind), "kind": kind,
        "url": url, "product": product, "format": None, "avatar": None, "angle": None, "subs": [],
        "meta": m if N.SLUG.match(m) else None, "old_ids": list(old_ids or []),
        "forwards_to": None, "also_urls": [], "notes": [], "status": "draft", "state": state, "since": today,
        "versions": ([{"version": "v1", "control": True, "url": url, "offer": None, "brief": None, "run": None,
                       "built": None, "since": today, "gate": None, "numbers": {}}] if state == "live" else []),
        "tests": [],
    }


def next_version(entry):
    nums = [int(VERSION.match(v["version"]).group(1)) for v in (entry or {}).get("versions") or []
            if VERSION.match(str(v.get("version") or ""))]
    return f"v{max(nums or [0]) + 1}"


def reserve_version(pid, brief, job, *, data=None, path=None, url=None, offer=None, today=None):
    """Hold the next version number for a page brief at the start of its run. A new page is entered as planned.
    Returns the version. The number is never handed out again, built or not."""
    if job not in JOBS:
        raise ValueError(f"job must be one of {', '.join(JOBS)}, not {job!r}")
    if not is_page_id(pid):
        raise ValueError(f"not a page ID: {pid!r}")
    own = data is None
    data = data or load(path)
    today = _day(today)
    e = data["pages"].get(pid)
    if e is not None and e.get("state") in ("archived", "off", "retired"):
        raise ValueError(f"{pid} is {e['state']} — no new version is built for it")
    if e is None:
        if job != "new-page":
            raise KeyError(f"{pid} is not on the page list — a {job} is for an existing page")
        p = parse_page_id(pid)
        e = data["pages"][pid] = new_entry(p["brand"], p["place"], p["page"], url, state="planned", today=today)
    elif job == "new-page" and e.get("versions"):
        raise ValueError(f"{pid} already has versions — this is a new control or a variant, not a new page")
    for v in e.get("versions") or []:
        if v.get("brief") == brief:
            return v["version"]                        # one brief, one version, for ever
    ver = next_version(e)
    e.setdefault("versions", []).append({
        "version": ver, "control": False, "url": url, "offer": offer, "brief": brief, "run": None, "built": None,
        "job": job, "since": today, "gate": None, "numbers": {}})
    if own:
        save(data, path)
    return ver


def file_build(pid, version, run, site=None, *, data=None, path=None, today=None):
    """The page chain's finished build, filed as that version (run and site are repo-relative paths)."""
    own = data is None
    data = data or load(path)
    _, e = find(pid, data)
    if not e:
        raise KeyError(f"no page {pid}")
    v = next((x for x in e.get("versions") or [] if x.get("version") == version), None)
    if not v:
        raise KeyError(f"{pid} has no version {version} — a build is filed against a reserved version")
    v.update({"run": run, "site": site, "built": _day(today)})
    for t in e.get("tests") or []:                   # a drafted test's variant: served under its page (/quiz/v7/)
        if t.get("state") == "draft" and (t.get("variant") or {}).get("version") == version \
                and not t["variant"].get("path") and (t.get("control") or {}).get("path"):
            t["variant"]["path"] = t["control"]["path"].rstrip("/") + f"/{version}/"
    if own:
        save(data, path)
    return v


def set_control(pid, version, *, data=None, path=None):
    """Move the control mark to `version`. The page ID, its address and every version number stay."""
    own = data is None
    data = data or load(path)
    _, e = find(pid, data)
    if not e:
        raise KeyError(f"no page {pid}")
    if not any(v.get("version") == version for v in e.get("versions") or []):
        raise KeyError(f"{pid} has no version {version}")
    for v in e["versions"]:
        v["control"] = v.get("version") == version
    if e.get("state") == "planned":
        e["state"] = "live"
    if own:
        save(data, path)
    return e


# ---------------------------------------------------------------- tests
def test_problems(entry, test):
    """Why a test entry cannot be live — [] when it can. Same rules as the funnel repos' edge (whyNotLive)."""
    bad = []
    vs = {v.get("version") for v in entry.get("versions") or []}
    c, v = test.get("control") or {}, test.get("variant") or {}
    if c.get("version") not in vs or v.get("version") not in vs:
        bad.append("control and variant must both be versions of this page")
    if c.get("version") == v.get("version"):
        bad.append("control and variant are the same version")
    if test.get("type") not in TEST_TYPES:
        bad.append(f"type must be one of {', '.join(TEST_TYPES)}")
    elif test["type"] == "design" and c.get("offer") != v.get("offer"):
        bad.append("a design test keeps the same offer in both groups")
    elif test["type"] == "offer" and c.get("offer") == v.get("offer"):
        bad.append("an offer test changes the offer")
    if not str(test.get("hypothesis") or "").strip():
        bad.append("hypothesis is written before the test starts")
    if not test.get("stop"):
        bad.append("the stop point is set before the test starts")
    g = test.get("gate") or {}
    if g.get("compliance") != "pass" or not g.get("compliance_run"):
        bad.append("compliance check has not passed")
    if not g.get("approved_on"):
        bad.append("no dated approval")
    return bad


def add_test(pid, test, *, data=None, path=None):
    """Record a test on a page (state draft). One test per page at a time."""
    own = data is None
    data = data or load(path)
    _, e = find(pid, data)
    if not e:
        raise KeyError(f"no page {pid}")
    if any(t.get("state") in ("draft", "live") for t in e.get("tests") or []):
        raise ValueError(f"{pid} already has a test open — one test per page at a time")
    t = {"page_id": pid, "type": test.get("type"), "hypothesis": test.get("hypothesis") or "",
         "control": test.get("control"), "variant": test.get("variant"),
         "primary_metric": test.get("primary_metric") or "checkout_reached",
         "confirm_metric": test.get("confirm_metric") or "purchase", "split": test.get("split", 50),
         "stop": test.get("stop"), "gate": test.get("gate") or
         {"compliance": None, "compliance_run": None, "approved_by": None, "approved_on": None},
         "state": "draft", "result": None}
    e.setdefault("tests", []).append(t)
    if own:
        save(data, path)
    return t


def end_test(pid, result, *, data=None, path=None):
    """Close the open test with its result; `variant wins` moves the control mark to the variant."""
    if result not in RESULTS:
        raise ValueError(f"result must be one of {', '.join(RESULTS)}")
    own = data is None
    data = data or load(path)
    _, e = find(pid, data)
    t = next((x for x in (e or {}).get("tests") or [] if x.get("state") in ("draft", "live")), None)
    if not t:
        raise KeyError(f"{pid}: no open test")
    t.update({"state": "ended", "result": result, "ended": date.today().isoformat()})
    if result == "variant wins":
        set_control(pid, t["variant"]["version"], data=data)
    if own:
        save(data, path)
    return t


# ---------------------------------------------------------------- hypotheses (the automatic testing loop)
HYPOTHESIS_NEEDS = ("page_id", "type", "control", "hypothesis", "change", "primary_metric", "confirm_metric",
                    "stop", "evidence")


def read_hypothesis(path):
    """A session-teardown hypothesis record (runs/session-teardown/<brand>/<label>/hypothesis.json), checked.
    -> the record. Raises ValueError naming every missing or wrong field."""
    h = json.loads(Path(path).read_text())
    bad = [f"missing {k}" for k in HYPOTHESIS_NEEDS if not h.get(k)]
    if h.get("kind") not in (None, "hypothesis"):
        bad.append(f"kind is {h.get('kind')!r}, not hypothesis")
    if h.get("page_id") and not is_page_id(h["page_id"]):
        bad.append(f"page_id {h['page_id']!r} is not a page ID")
    if h.get("type") and h["type"] not in TEST_TYPES:
        bad.append(f"type must be one of {', '.join(TEST_TYPES)}")
    c = h.get("control") or {}
    if h.get("control") and not VERSION.match(str(c.get("version") or "")):
        bad.append("control.version is not vN")
    vo = h.get("variant_offer", c.get("offer"))
    if h.get("type") == "design" and vo != c.get("offer"):
        bad.append("a design test keeps the control's offer")
    if h.get("type") == "offer" and vo == c.get("offer"):
        bad.append("an offer test changes the offer")
    if h.get("status", "draft") not in ("draft", "approved", "deprecated"):
        bad.append("status is draft/approved/deprecated only")
    if bad:
        raise ValueError(f"{path}: " + "; ".join(bad))
    return h


def test_from_hypothesis(pid, version, h, hypothesis_file, *, data):
    """Draft the page's test from a hypothesis record once its variant version is reserved: control = the version
    holding the mark now (it must still be the one the hypothesis was written against), variant = `version`."""
    _, e = find(pid, data)
    c = control(e)
    if not c or c["version"] != h["control"]["version"]:
        raise ValueError(f"{pid}: the hypothesis was written against {h['control']['version']}, "
                         f"the control is now {c['version'] if c else 'nothing'} — write it again")
    vo = h.get("variant_offer", h["control"].get("offer"))
    t = add_test(pid, {"type": h["type"], "hypothesis": h["hypothesis"],
                       "control": {"version": c["version"], "path": urlparse(c.get("url") or "").path,
                                   "offer": h["control"].get("offer")},
                       "variant": {"version": version, "path": None, "offer": vo},
                       "primary_metric": h["primary_metric"], "confirm_metric": h["confirm_metric"],
                       "split": h.get("split", 50), "stop": h["stop"]}, data=data)
    t["hypothesis_id"] = h.get("id")
    t["hypothesis_file"] = hypothesis_file
    t["change"] = h["change"]
    return t


# ---------------------------------------------------------------- fix lists (team fixes from session-teardown)
FIX_NEEDS = ("id", "page_id", "control", "fixes")


def read_fix_list(path):
    """A session-teardown fix list (runs/session-teardown/<brand>/<label>/fixes.json), checked. -> the record."""
    f = json.loads(Path(path).read_text())
    bad = [f"missing {k}" for k in FIX_NEEDS if not f.get(k)]
    if f.get("kind") not in (None, "fix-list"):
        bad.append(f"kind is {f.get('kind')!r}, not fix-list")
    if f.get("page_id") and not is_page_id(f["page_id"]):
        bad.append(f"page_id {f['page_id']!r} is not a page ID")
    if f.get("control") and not VERSION.match(str((f["control"] or {}).get("version") or "")):
        bad.append("control.version is not vN")
    for x in f.get("fixes") or []:
        if not x.get("id") or not (x.get("fix") or x.get("what")):
            bad.append(f"a fix without an id or a change: {str(x)[:60]}")
    if f.get("status", "draft") not in ("draft", "approved", "deprecated"):
        bad.append("status is draft/approved/deprecated only")
    if bad:
        raise ValueError(f"{path}: " + "; ".join(bad))
    return f


def open_problems(pid, control_version, data):
    """Why a new control or a variant cannot be started on a page now — [] when it can."""
    _, e = find(pid, data)
    if e is None:
        return [f"{pid} is not on the page list"]
    bad = []
    if e.get("state") not in ("live",):
        bad.append(f"{pid} is {e.get('state')}")
    c = control(e)
    if not c or c["version"] != control_version:
        bad.append(f"written against {control_version}, the control is now {c['version'] if c else 'nothing'}")
    if any(t.get("state") in ("draft", "live") for t in e.get("tests") or []):
        bad.append("a test is open on this page — no fix lands until it ends")
    return bad


# ---------------------------------------------------------------- going live (one rule for fixes and variants)
def version_problems(entry, version):
    """Why a built version cannot take the control mark — [] when it can: built, compliance passed with its run,
    and a dated approval click."""
    v = next((x for x in (entry or {}).get("versions") or [] if x.get("version") == version), None)
    if not v:
        return [f"no version {version}"]
    bad = []
    if not v.get("built"):
        bad.append("not built yet")
    g = v.get("gate") or {}
    if g.get("compliance") != "pass" or not g.get("compliance_run"):
        bad.append("compliance check has not passed")
    if not g.get("approved_on") or not g.get("approved_by"):
        bad.append("no dated approval click")
    if any(t.get("state") == "live" for t in entry.get("tests") or []):
        bad.append("a test is running on this page")
    return bad


def approve_version(pid, version, by, *, compliance_run, data=None, path=None, today=None):
    """Record the gate (compliance passed in `compliance_run`, `by` clicked on `today`) and, for a new control,
    move the control mark. A variant's approval opens its test's gate instead; the result moves the mark."""
    own = data is None
    data = data or load(path)
    _, e = find(pid, data)
    v = next((x for x in (e or {}).get("versions") or [] if x.get("version") == version), None)
    if not v:
        raise KeyError(f"{pid} has no version {version}")
    who = (data.get("approvers") or {}).get("variant" if v.get("job") == "variant" else "new-control")
    if who is not None and by not in who:
        raise ValueError(f"{by!r} is not an approver for this page change (approvers: {', '.join(who)})")
    v["gate"] = {"compliance": "pass", "compliance_run": compliance_run, "approved_by": by, "approved_on": _day(today)}
    bad = version_problems(e, version)
    if bad:
        raise ValueError(f"{pid} {version}: " + "; ".join(bad))
    if v.get("job") == "variant":
        for t in e.get("tests") or []:
            if t.get("state") == "draft" and t["variant"]["version"] == version:
                t["gate"] = dict(v["gate"])
    else:
        set_control(pid, version, data=data)
    if own:
        save(data, path)
    return e


# ---------------------------------------------------------------- a page's build record, for readers
def page_context(pid, data=None, root=None):
    """What a reader (session-teardown) needs about one page: its entry, its control version, the page brief that
    built that version and its page-chain run with the section jobs from structure.json. Pages built before the
    page chain have no brief and no sections (None)."""
    data = data or load()
    pid, e = find(pid, data)
    if not e:
        return None
    c = control(e)
    out = {"page_id": pid, "entry": e, "control": c, "brief": None, "run": None, "sections": None}
    if c and c.get("brief"):
        try:
            sys.path.append(str(WS / "components" / "image-teardown" / "tools"))
            reg = json.loads((WS / "components" / "image-teardown" / "briefs.json").read_text())
            out["brief"] = reg["briefs"].get(c["brief"])
        except (OSError, ValueError, KeyError):
            pass
    run = (c or {}).get("run")
    if run:
        out["run"] = run
        if (Path(root or WS) / run / "page.json").is_file():
            out["page_json"] = f"{run}/page.json"
        st = Path(root or WS) / run / "structure.json"
        try:
            out["sections"] = [{"job": x.get("job"), "move": x.get("move"), "form": x.get("form")}
                               for x in json.loads(st.read_text()).get("sections") or []]
        except (OSError, ValueError):
            pass
    return out


# ---------------------------------------------------------------- live addresses
def fetch_status(url, timeout=15, tries=4):
    """(status, final url) — redirects followed; a rate limit (429) is waited out and asked again."""
    import time
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (pages)"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.geturl()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            return e.code, url
        except Exception:
            return 0, url
    return 0, url


def _listed(how):
    """An address a store's own sitemap lists is live by the store's word — no fetch (and no rate limit)."""
    return str(how).endswith("sitemap")


def sitemap_urls(root_url, fetch_text=None):
    """Every address a store's sitemap lists (its child sitemaps followed; market copies like /en-fr/ skipped)."""
    def get(u):
        if fetch_text:
            return fetch_text(u)
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (pages)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            return ""
    base = root_url.rstrip("/") + "/sitemap.xml"
    out, seen, todo = [], set(), [base]
    while todo:
        u = todo.pop(0)
        if u in seen:
            continue
        seen.add(u)
        body = get(u)
        locs = [x.replace("&amp;", "&").strip() for x in re.findall(r"<loc>([^<]+)</loc>", body)]
        if "<sitemapindex" in body:
            todo += [x for x in locs if not re.search(r"/[a-z]{2}-[a-z]{2}/", urlparse(x).path)]
        else:
            out += [x for x in locs if urlparse(x).netloc == urlparse(root_url).netloc
                    and not re.search(r"\.(md|xml|jpg|png|webp)$", x)
                    and not re.match(r"^/[a-z]{2}-[a-z]{2}(/|$)", urlparse(x).path)]
    return out


def candidates(brand, places, root=None, cat=None, fetch_text=None, extra=()):
    """Every address a brand is known to serve: funnel page lists, catalog links, store sitemaps, extra addresses.
    -> [(url, old link id or None, how it was found)]."""
    brand = N.slug(brand)
    out = []
    import page_pick as PP
    for k, r in PP.records(brand, cat).items():           # catalog first: its links carry the frozen Meta piece
        if r.get("type") == "link" and r.get("url"):
            out.append((r["url"], k, f"catalog {k}"))
    for f in brand_funnels(brand, root):
        if not f.get("url") or str(f.get("status") or "").startswith("off"):
            continue
        for p in f.get("pages") or []:
            if " " in p:
                continue                                    # a stray copy in the repo, never a page
            slash = "/" if f.get("code_slug") else ""
            out.append((f["url"].rstrip("/") + "/" + p + slash, None, f"funnel list {f['id']}"))
    for name, p in places.items():
        if p["kind"] == "store" and p.get("state") != "off":
            for u in sitemap_urls(p["url"], fetch_text):
                out.append((u, None, f"{name} sitemap"))
            out.append((p["url"].rstrip("/") + "/cart", None, f"{name} cart"))
    for u in extra:
        out.append((u, None, "extra"))
    return out


# ---------------------------------------------------------------- the daily check
def check(brand, *, data=None, root=None, cat=None, fetch=None, fetch_text=None, extra=(), today=None):
    """Every address the brand serves that answers 200 and has no page ID, and every page listed live that no
    longer answers. -> {"missing": [...], "dead": [...], "checked": n}."""
    data = data or load()
    brand = N.slug(brand)
    fetch = fetch or fetch_status
    places = places_for(brand, data, root)
    missing, dead, seen = [], [], set()
    cands = candidates(brand, places, root, cat, fetch_text, extra)
    for url, link, how in cands:
        n = norm_url(url)
        if n in seen:
            continue
        seen.add(n)
        pid, _ = find(url, data)
        if pid or (link and find(link, data)[0]):
            continue
        st, final = (200, url) if _listed(how) else fetch(url)
        if st == 200 and not find(final, data)[0]:
            want, _ = id_for_url(brand, final, places)
            missing.append({"url": url, "found_by": how, "would_be": want})
    listed = {norm_url(u) for u, _, how in cands if _listed(how)}
    stores = {n for n, p in places.items() if p["kind"] == "store"}
    for pid, e in data["pages"].items():
        if e.get("brand") != brand or e.get("state") != "live" or not e.get("url") or e.get("fetch") is False:
            continue
        if e.get("place") in stores and e.get("kind") not in ("cart", "checkout"):
            if norm_url(e["url"]) not in listed:
                dead.append({"page": pid, "url": e["url"], "answered": "not in the store's sitemap"})
            continue
        st, _ = fetch(e["url"])
        if st != 200:
            dead.append({"page": pid, "url": e["url"], "answered": st})
    return {"brand": brand, "date": _day(today), "checked": len(seen),
            "missing": missing, "dead": dead}


def write_check(result, root=None):
    d = Path(root or WS) / "runs" / "naming" / result["brand"] / "page-check" / result["date"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "check.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    lines = [f"# Page check — {result['brand']} — {result['date']}", "",
             f"{result['checked']} addresses checked · {len(result['missing'])} live with no page ID · "
             f"{len(result['dead'])} listed live, not answering", ""]
    for m in result["missing"]:
        lines.append(f"- NO ID: {m['url']} (found in {m['found_by']}; would be `{m['would_be']}`)")
    for x in result["dead"]:
        lines.append(f"- NOT ANSWERING: `{x['page']}` {x['url']} → {x['answered'] or 'nothing'}")
    (d / "check.md").write_text("\n".join(lines) + "\n")
    return d


# ---------------------------------------------------------------- backfill
def _join(e, link, cat, report, pid):
    """An old catalog link id joins a page: kept as an alias, and its Meta piece (what live ads already say) wins."""
    import page_pick as PP
    if link and link not in e["old_ids"]:
        e["old_ids"].append(link)
        report["joined"].append((link, pid))
        frozen = PP.meta_page(link, cat)
        if frozen and len(e["old_ids"]) == 1:
            e["meta"] = frozen


def backfill(brand, *, data=None, root=None, cat=None, fetch=None, fetch_text=None, extra=(), today=None):
    """Give every live address of a brand its page ID. An ID already on the list is never re-pointed; a catalog
    link's Meta piece is frozen from today's ad names; an address that is a version of a listed page stays one.
    -> (data, report)."""
    import page_pick as PP
    data = data or load()
    brand = N.slug(brand)
    fetch = fetch or fetch_status
    places = places_for(brand, data, root)
    report = {"added": [], "joined": [], "skipped": []}
    for url, link, how in candidates(brand, places, root, cat, fetch_text, extra):
        pid, e = find(url, data)
        if pid:
            _join(e, link, cat, report, pid)
            continue
        rec = PP.records(brand, cat).get(link) or {} if link else {}
        state = "off" if (rec.get("status") or "").lower() == "off" else "live"
        st, final = (200, url) if _listed(how) else fetch(url)
        if st == 429:
            st = 200                                   # rate limited, not gone: the store is answering
        if st != 200 and state != "off":
            report["skipped"].append((url, f"answered {st or 'nothing'}", how))
            continue
        if st == 200 and norm_url(final) != norm_url(url):
            pid, e = find(final, data)
            if pid:
                _join(e, link, cat, report, pid)
                continue
            url = final
        pid, kind = id_for_url(brand, url, places)
        if not pid:
            report["skipped"].append((url, "sits in no place", how))
            continue
        if pid in data["pages"]:
            e = data["pages"][pid]
            _join(e, link, cat, report, pid)
            if norm_url(url) != norm_url(e.get("url")):       # another address of the same page (a store's
                e.setdefault("also_urls", []).append(url)       # product sizes each get one) — one page, not two
                report["joined"].append((url, pid))
            continue
        p = parse_page_id(pid)
        frozen = PP.meta_page(link, cat) if link else None
        e = new_entry(brand, p["place"], p["page"], url, kind=kind,
                      product=places[p["place"]].get("product"), meta_name=frozen,
                      old_ids=[link] if link else [], state=state, today=today)
        if st != 200:
            e["notes"].append(f"answered {st or 'nothing'} on {e['since']}")
        data["pages"][pid] = e
        report["added"].append((pid, how))
    return data, report


# ---------------------------------------------------------------- command line
def _print_page(pid, e):
    print(f"{pid}  [{e.get('step')} · {e.get('kind')} · {e.get('state')}]  meta {e.get('meta')}")
    print(f"   {e.get('url')}")
    if e.get("old_ids"):
        print(f"   was: {', '.join(e['old_ids'])}")
    for v in e.get("versions") or []:
        print(f"   {v['version']}{' ✓control' if v.get('control') else ''}  {v.get('url') or ''}"
              f"{'  brief ' + v['brief'] if v.get('brief') else ''}{'  run ' + v['run'] if v.get('run') else ''}")
    for t in e.get("tests") or []:
        print(f"   test [{t['state']}] {t['type']}: {t['control']['version']} vs {t['variant']['version']}"
              f" → {t.get('result') or '—'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--brand"); ls.add_argument("--place"); ls.add_argument("--step", choices=STEPS)
    sh = sub.add_parser("show"); sh.add_argument("ref")
    fu = sub.add_parser("funnel"); fu.add_argument("place")
    nx = sub.add_parser("next"); nx.add_argument("page")
    co = sub.add_parser("control"); co.add_argument("page"); co.add_argument("version")
    ck = sub.add_parser("check"); ck.add_argument("--brand", required=True); ck.add_argument("--no-fetch", action="store_true")
    bf = sub.add_parser("backfill"); bf.add_argument("--brand", required=True); bf.add_argument("--extra")
    bf.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    data = load()
    if a.cmd == "list":
        for pid, e in data["pages"].items():
            if (a.brand and e["brand"] != N.slug(a.brand)) or (a.place and e["place"] != a.place) \
                    or (a.step and e.get("step") != a.step):
                continue
            c = control(e)
            print(f"{pid:70} {e.get('step') or '?':13} {e.get('state'):8} {c['version'] if c else '-'}")
    elif a.cmd == "show":
        pid, e = find(a.ref, data)
        if not pid:
            sys.exit(f"no page for {a.ref}")
        _print_page(pid, e)
    elif a.cmd == "funnel":
        f = funnel(a.place, data)
        for s in STEPS:
            print(f"{s}: {', '.join(x.split('_', 2)[2] for x in f['steps'][s]) or '—'}")
    elif a.cmd == "next":
        print(next_version(find(a.page, data)[1]))
    elif a.cmd == "control":
        set_control(a.page, a.version, data=data)
        save(data)
        print(f"{a.page}: {a.version} holds the control mark")
    elif a.cmd == "check":
        fetch = (lambda u: (200, u)) if a.no_fetch else None
        r = check(a.brand, data=data, fetch=fetch)
        d = write_check(r)
        print(f"{r['checked']} checked · {len(r['missing'])} live with no ID · {len(r['dead'])} not answering"
              f" → {d.relative_to(WS)}")
        for m in r["missing"]:
            print(f"   NO ID  {m['url']}  ({m['found_by']}) → {m['would_be']}")
        for x in r["dead"]:
            print(f"   DEAD   {x['page']}  {x['url']} → {x['answered']}")
        sys.exit(1 if r["missing"] else 0)
    elif a.cmd == "backfill":
        extra = [l.strip() for l in Path(a.extra).read_text().splitlines() if l.strip()] if a.extra else []
        data, rep = backfill(a.brand, data=data, extra=extra)
        for pid, how in rep["added"]:
            print(f"   + {pid}  ({how})")
        for link, pid in rep["joined"]:
            print(f"   = {link} → {pid}")
        for url, why, how in rep["skipped"]:
            print(f"   - {url}: {why} ({how})")
        print(f"{len(rep['added'])} added · {len(rep['joined'])} old ids joined · {len(rep['skipped'])} skipped")
        if a.apply:
            save(data)
            print(f"written: {LIST.relative_to(WS)}")


if __name__ == "__main__":
    main()
