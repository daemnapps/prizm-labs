#!/usr/bin/env python3
"""The Meta uploader — a drop goes into the ad account with no person in between.

    upload.py <ad-uploader hand-off folder>                 # plan: talks to nothing
    upload.py <hand-off folder> --links <id>,<id>           # only these landing pages
    upload.py <hand-off folder> --go                        # upload — only if approved

**Plan** (the default) reads the drop the hand-off packaged — its pictures or
finished videos, the words in its own `copy.csv`, the landing page per link
id — and writes `runs/meta-upload/<brand>/<hand-off name>/upload/plan.json`:
every campaign, ad set and ad it would make, named by `components/naming`,
with every reason an ad is held. Nothing reaches Meta. Nothing is written
into the hand-off's `returned/upload/` any more (SI-27, 7 Oct 2026).

**Go** does the same plan, then builds it in the account through the
Marketing API: finds the campaign and ad set by name (or makes them, paused),
puts the media into the account library, and makes one flexible ad per ad
unit per landing page — every picture of the unit inside it, Meta rotating
between them, the drop's bodies, headlines and descriptions as the options.
That is exactly the shape of the 42 live 260923a ads, which were built by
hand. Each Meta ad id is written by name to `live-ids.json` in the same runs
home (beside `state.json`, the ids made so far) and to the hand-off's own
`returned/live-ids.json` (the hand-off standard's declared return), and
`handoff take-back` records it in the ledger as `live_meta_<id>`.

**Nothing goes live without the owner.** `--go` refuses unless `approvals.json`
in this folder carries his go for that hand-off (and, before the very first
real upload, the `first_go` line). An approval says which landing pages and
whether the ads start PAUSED or ACTIVE. After the first go, every approved
hand-off runs with no one at the keyboard — `--all-approved` walks them.

**The card road (1 Oct 2026)** — `upload_card(<card folder>)` takes one
finished ad from the Drive (CARD.md) into Meta after the owner's click on the
approval page (`approve.py`); flexible or carousel. approvals.json above is
the legacy hand-off road only.

Re-running is safe: campaign and ad set ids are remembered per brand in
`runs/meta-upload/<brand>/ids.json` (looked up by name only on a miss), and an ad
is looked up by name only when the last run stopped half way through it.
"""
import argparse, json, os, re, sys
from datetime import date, datetime
from pathlib import Path
os.environ.setdefault("CARDS_ROUTE", "mount")   # Meta approve moves card folders: the Drive folder itself (shared_drive.py)
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N
import pace
from brand import Brand
from drop import read_handoff, kind_of, VIDEO

APPROVALS = HERE / "approvals.json"
STAGING = REPO / "lab/damon/print-run/handoffs"
# The ad URL standard (components/funnel-tracking/standard.json, ad_url): every ad this
# uploader makes carries it, flexible, carousel and the bulk sheet alike. Meta fills each {{…}}
# at click time; the funnel keeps utm_* and sub1 on the store's cart and order, so the store's
# own records join back to the ad by name (utm_content) and by id (sub1). (12 Oct 2026: replaces
# the old utm_source={{site_source_name}} / utm_medium=paid_social tags.)
sys.path.insert(0, str(REPO / "components/funnel-tracking/machine"))
import standard as _tracking_standard
URL_TAGS = _tracking_standard.url_tags()
MAX_IMAGES, MAX_TEXTS = 10, 5          # Meta's flexible-ad limits (5 texts per type per group)


def upload_home(brand, name, runs_root=None):
    """Where the hand-off road's run record lives: runs/meta-upload/<brand>/
    <hand-off name>/upload/ (plan.json, state.json, live-ids.json) — the
    runs/<machine>/<brand>/<run-label>/ shape of runs/README.md. Not created
    here. `runs_root` is a test seam; default the workspace's runs/."""
    for field, v in (("brand", brand), ("hand-off name", name)):
        if not v or "/" in v or "\\" in v or v in (".", "..") or v.startswith("."):
            raise SystemExit(f"REFUSED: the {field} {v!r} cannot name a folder under runs/meta-upload/.")
    return Path(runs_root or REPO / "runs") / "meta-upload" / brand / name / "upload"


def brand_runs(brand, runs_root=None):
    """runs/meta-upload/<brand>/ — the brand's small memory: ids.json (campaign and
    ad set ids by name) and page-ads.json (cards.page_ads). A scratch card tree
    ($META_CARDS_ROOT: tests, fake trials) keeps its own under <root>/_runs, so a
    trial never writes the real one; $META_RUNS_ROOT overrides both."""
    if not brand or "/" in brand or "\\" in brand or brand.startswith("."):
        raise SystemExit(f"REFUSED: the brand {brand!r} cannot name a folder under runs/meta-upload/.")
    if runs_root:
        base = Path(runs_root)
    elif os.environ.get("META_RUNS_ROOT"):
        base = Path(os.environ["META_RUNS_ROOT"])
    elif os.environ.get("META_CARDS_ROOT"):
        base = Path(os.environ["META_CARDS_ROOT"]) / "_runs"
    else:
        base = REPO / "runs"
    return base / "meta-upload" / brand


def known_ids(brand, runs_root=None):
    """(file, {"campaigns": {name: id}, "ad_sets": {"<campaign>|<ad set>": id}})."""
    f = brand_runs(brand, runs_root) / "ids.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        d = {}
    d.setdefault("campaigns", {})
    d.setdefault("ad_sets", {})
    return f, d


def remember_ids(f, d):
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f".{f.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, f)


# ---- landing pages ----------------------------------------------------------
def funnels(brand):
    """The brand's funnels still taking ads: one whose status is "off" is passed over."""
    f = REPO / "brands" / brand / "web/funnels/funnels.json"
    every = json.loads(f.read_text()).get("funnels", []) if f.is_file() else []
    return [x for x in every if (x.get("status") or "").strip().lower() != "off"]


def page_for(link, brand):
    """A link record -> (url, funnel id, note). The URL goes on the brand's own
    domain: a catalog link sometimes carries the build host (netlify.app) while
    the funnel registry — and every live ad — uses the brand domain, and the
    pixel only counts purchases on the brand domain."""
    url = (link or {}).get("url") or ""
    path, host = urlparse(url).path or "/", urlparse(url).netloc
    best = None
    # a funnel on the page's own host wins over one that only shares the path ("/" on method.brand-a.com is the
    # quiz, not the brand-a.com store: 9 Oct 2026); the longest path breaks a tie
    rank = lambda f: (urlparse(f["url"]).netloc == host, len(urlparse(f["url"]).path))
    for f in funnels(brand):
        fu = urlparse(f.get("url") or "")
        if fu.path and path.startswith(fu.path) and (not best or rank(f) > rank(best)):
            best = f
    if not best:
        return url, None, "no funnel in the brand's registry matches this page"
    # the owner, 17 Oct 2026: BRAND-A's "icon" and "flex-cpk" funnels both sat at method.brand-a.com/icon/, so the
    # first one listed won silently and ads split across two campaigns. Two funnels on one page is now a stop.
    tied = [f["id"] for f in funnels(brand) if urlparse(f.get("url") or "").path
            and path.startswith(urlparse(f["url"]).path) and rank(f) == rank(best)]
    if len(tied) > 1:
        return url, None, (f"two funnels claim this page ({', '.join(tied)}) — the brand's funnel list "
                           "must name one, or the ad lands in the wrong campaign")
    fu = urlparse(best["url"])
    fixed = f"{fu.scheme}://{fu.netloc}{path}"
    note = f"host {urlparse(url).netloc} → {fu.netloc} (the brand domain)" if fixed != url else ""
    return fixed, best["id"], note


def campaign_name(b, funnel, product=None):
    """naming.campaign over the brand's own template, product per funnel."""
    import build
    c = {**b.campaign, **({"product": product} if product else {})}
    return build.naming.campaign({"brand": b.name, **c, "lane": "", "funnel": funnel}, b.naming["campaign"],
                                 build.naming.sep_for(b.naming, "campaign"), spell=b.pretty)


def funnel_product(brand, funnel):
    return next((f.get("product") for f in funnels(brand) if f["id"] == funnel), None)


# ---- the plan ---------------------------------------------------------------
# The three joins every ad needs — ad set, campaign, page vs product — shared
# by the hand-off plan below and the approval card (cards.py, card_plan).
def ad_set_for(b, fields):
    """The ad set an ad goes into, from its avatar + angle -> (name, why)."""
    import build
    nm = b.naming
    try:
        key = {k: build.ad_set_value(b, k, fields.get(k)) for k in nm.get("ad_set_by", [])}
        return build.naming.render(nm["ad_set"], {"brand": b.name, **key}, build.naming.sep_for(nm, "ad_set"), b.pretty), None
    except SystemExit as e:
        return None, f"no ad set: {e}"


def product_clash(b, funnel, fields):
    """Why an ad may not go to this page (it sells another product), else None."""
    def same(a, c):                                            # one product under its catalog id or an alias (2026-10-28)
        try:
            ia, ic = N.product_id(b.name, a), N.product_id(b.name, c)
            if ia and ic and ia == ic:
                return True
        except Exception:                                      # noqa: BLE001
            pass
        return N.slug(a).replace("-", "") == N.slug(c).replace("-", "")
    if (funnel and fields.get("product") and funnel_product(b.name, funnel)
            and not same(fields["product"], funnel_product(b.name, funnel))):
        return f"the ad sells {fields['product']} but the page {funnel} sells {funnel_product(b.name, funnel)}"
    return None


def campaign_for(b, funnel, fields):
    """The campaign sells one product to one funnel: the funnel's product,
    else the ad's own, else the brand's fallback -> (name, why)."""
    product = funnel_product(b.name, funnel) or (N.slug(fields["product"]) if fields.get("product") else None)
    try:
        name = campaign_name(b, funnel, product)
    except SystemExit as e:
        return None, f"no campaign: {e}"
    return name, new_campaign(b.name, name)


def spending_campaigns(brand):
    """Campaign names the warehouse has seen spend for this brand (funnel-tracking's views data, never a Meta
    read). A campaign made by hand is in use even though no upload remembered it — Brand-B's body scrub CPK
    campaign, 17 Oct 2026. In the uploader's naming, so another brand's campaign never counts."""
    f = REPO / "runs" / "funnel-tracking" / "views-data.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return set()
    out, todo, lead = set(), [d], f"campaign_{brand}_"
    while todo:
        x = todo.pop()
        if isinstance(x, dict):
            c = x.get("campaign")
            if isinstance(c, str) and c.startswith(lead):
                out.add(c)
            todo.extend(x.values())
        elif isinstance(x, list):
            todo.extend(x)
    return out


def campaign_options(brand):
    """Every campaign an ad of this brand may go into: the ones uploads remembered and the ones the warehouse
    sees spending, for the approval page's picker."""
    _, ids = known_ids(brand)
    names = set(ids["campaigns"]) | spending_campaigns(brand)
    return [{"name": n, "id": ids["campaigns"].get(n)} for n in sorted(names)]


def _named(m, edge, name, parent):
    for x in m.paged(f"{parent}/{edge}", fields="id,name,effective_status", limit=500):
        if x["name"] == name and x.get("effective_status") not in ("ARCHIVED", "DELETED"):
            return x["id"]


def campaign_id(m, brand, name):
    """A campaign's id: remembered, else found by its name in the account on this press (then remembered)."""
    ids_f, ids = known_ids(brand)
    cid = ids["campaigns"].get(name) or _named(m, "campaigns", name, f"act_{m.ACCOUNT}")
    if cid and ids["campaigns"].get(name) != cid:
        ids["campaigns"][name] = cid
        remember_ids(ids_f, ids)
    return cid


def copy_ad(m, ad_id, adset_id, name, status):
    """Meta's own copy of a live ad into another ad set — same creative, same words, same page — renamed back to
    its own name (Meta adds " - Copy"). Returns the new ad's id."""
    r = m.post(f"{ad_id}/copies", adset_id=adset_id, status_option="ACTIVE" if status == "ACTIVE" else "PAUSED")
    new = r.get("copied_ad_id") or r.get("id")
    if not new:
        raise SystemExit(f"Meta made no copy of {ad_id}: {r}")
    m.post(new, name=name)
    return new


def move_card(folder, campaign, by, m=None, log=print):
    """A live card's ads, copied into `campaign` (the owner, 17 Oct 2026: "duplicate the ad … into the main
    campaign"). Each copy goes into the ad set of the same name inside that campaign and starts the way the
    original runs. The originals are left alone — pausing the old campaign is its own press. Returns the card."""
    import cards as C
    folder = Path(folder)
    card = C.load(folder)
    if C.where(folder)["state"] != "3-live":
        raise SystemExit("only a live ad can be copied into another campaign")
    if by not in approvers():
        raise SystemExit("REFUSED: pick who is deciding first (a name on approvers.json)")
    b = Brand(card["brand"])
    if campaign not in {o["name"] for o in campaign_options(b.name)}:
        raise SystemExit(f"{campaign} is not one of {b.name}'s campaigns")
    if m is None:
        from meta import Meta
        m = Meta(b)
    cid = campaign_id(m, b.name, campaign)
    if not cid:
        raise SystemExit(f"{campaign} was not found in the account")
    ids_f, ids = known_ids(b.name)
    at = datetime.now().isoformat(timespec="seconds")
    there = {x.get("copied_from") for x in card.get("meta") or [] if x.get("campaign") == campaign}
    rows = [r for r in card.get("meta") or [] if r.get("campaign") != campaign and r["ad_id"] not in there]
    if not rows:
        raise SystemExit(f"this ad is already in {campaign}")
    made = []
    for r in rows:
        k = f"{campaign}|{r['ad_set']}"
        sid = ids["ad_sets"].get(k) or _named(m, "adsets", r["ad_set"], cid)
        if not sid:
            raise SystemExit(f"{campaign} has no ad set {r['ad_set']} — launch one ad into it first")
        if ids["ad_sets"].get(k) != sid:
            ids["ad_sets"][k] = sid
            remember_ids(ids_f, ids)
        new = copy_ad(m, r["ad_id"], sid, r["meta_ad_name"], r.get("status"))
        log(f"  copied {r['meta_ad_name']} -> {campaign} ({new})")
        made.append(dict(r, ad_id=new, campaign=campaign, campaign_id=cid, ad_set_id=sid, at=at,
                         copied_from=r["ad_id"], by=by))
    card["meta"] += made
    card.setdefault("history", []).append({"at": at, "by": by, "what": f"copied into {campaign}",
                                           "ads": [x["ad_id"] for x in made]})
    C.save(folder, card)
    with (LIVE or C.root() / "live.jsonl").open("a") as f:
        for x in made:
            f.write(json.dumps({"ad_name": card["ad_name"], "meta_ad_name": x["meta_ad_name"], "ad_id": x["ad_id"],
                                "brand": card["brand"], "lane": card.get("lane"), "at": at,
                                "campaign": campaign, "copied_from": x["copied_from"]}) + "\n")
    return card


def set_campaign_status(brand, campaign, status, by, m=None):
    """Switch a whole campaign off (PAUSED) or on (ACTIVE), on an approver's press only. One line per change
    goes to runs/meta-upload/<brand>/campaign-changes.jsonl."""
    if by not in approvers():
        raise SystemExit("REFUSED: pick who is deciding first (a name on approvers.json)")
    if status not in ("ACTIVE", "PAUSED"):
        raise SystemExit("status must be ACTIVE or PAUSED")
    b = Brand(brand)
    if campaign not in {o["name"] for o in campaign_options(b.name)}:
        raise SystemExit(f"{campaign} is not one of {b.name}'s campaigns")
    if m is None:
        from meta import Meta
        m = Meta(b)
    cid = campaign_id(m, b.name, campaign)
    if not cid:
        raise SystemExit(f"{campaign} was not found in the account")
    m.post(cid, status=status)
    f = brand_runs(b.name) / "campaign-changes.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as fh:
        fh.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "by": by, "campaign": campaign,
                             "campaign_id": cid, "status": status}) + "\n")
    return cid


def new_campaign(brand, name):
    """Why an ad may not go: it would open a campaign the brand has never used. the owner, 17 Oct 2026: a funnel
    change sent BRAND-A ads into a second campaign nobody asked for. Once a brand has campaigns, a new one is
    only made when $META_NEW_CAMPAIGN names it; otherwise the card fails its campaign check and says so."""
    _, ids = known_ids(brand)
    have = set(ids["campaigns"]) | spending_campaigns(brand)
    if not have or name in have or os.environ.get("META_NEW_CAMPAIGN") == name:
        return None
    return (f"no campaign: this would open a NEW campaign {name} — in use: {', '.join(sorted(have))}")


def _add(out, row, why):
    if why:
        out["held"].append({**row, "why": why})
    else:
        out["ads"].append(row)
        out["campaigns"].setdefault(row["campaign"], {"funnel": row.get("funnel"), "ad_sets": {}})
        out["campaigns"][row["campaign"]]["ad_sets"].setdefault(row["ad_set"], 0)
        out["campaigns"][row["campaign"]]["ad_sets"][row["ad_set"]] += 1


def plan(folder, only_links=None):
    d = read_handoff(folder)
    b = Brand(d["brand"])
    out = {"handoff": d["handoff"], "brand": b.name, "batch": d["batch"], "account": b.account_id,
           "made": datetime.now().isoformat(timespec="seconds"), "campaigns": {}, "ads": [], "held": []}
    for u in d["units"]:
        why = []
        if u["missing"]:
            why.append(f"{len(u['missing'])} file(s) not found")
        if u["kind"] in ("none", "mixed"):
            why.append("no pictures or videos" if u["kind"] == "none" else "pictures and videos mixed in one unit")
        if not u["bodies"]:
            why.append("no primary text in the drop's copy.csv")
        if not u["titles"]:
            why.append("no headlines in the drop's copy.csv (the writer's HEADLINES list) — not invented here")
        if len(u["media"]) > MAX_IMAGES:
            why.append(f"{len(u['media'])} pictures, Meta takes {MAX_IMAGES} in one ad")
        f = N.parse_any(u["old_name"]) or {}
        try:
            head = N.brief_header(b.name, f.get("brief"), f.get("product")) or {}
        except N.AmbiguousBrief as e:
            head = {}
            why.append(str(e))
        fields = {**head, **{k: v for k, v in f.items() if v}}
        ad_set, w = ad_set_for(b, fields)
        why += [w] if w else []
        for a in u["ads"]:
            if only_links and a["link_id"] not in only_links:
                continue
            link = d["links"].get(a["link_id"])
            url, funnel, note = page_for(link, b.name)
            ad_why = list(why)
            if not link:
                ad_why.append(f"link {a['link_id']} not in the hand-off")
            elif not (link.get("page_check") or {}).get("ok", True):
                ad_why.append(f"page {url} failed its check")
            if not funnel:
                ad_why.append(note)
            elif product_clash(b, funnel, fields):
                ad_why.append(product_clash(b, funnel, fields))
            camp = None
            if funnel:
                camp, w = campaign_for(b, funnel, fields)
                ad_why += [w] if w else []
            row = {"meta_ad_name": a["meta_ad_name"], "unit": u["unit"], "old_name": u["old_name"],
                   "brief_id": u["brief_id"], "link_id": a["link_id"], "url": url, "url_note": note,
                   "campaign": camp, "ad_set": ad_set, "kind": u["kind"], "funnel": funnel,
                   "media": [str(p) for p in u["media"]][:MAX_IMAGES],
                   "bodies": u["bodies"][:MAX_TEXTS], "titles": u["titles"][:MAX_TEXTS],
                   "descriptions": u["descriptions"][:MAX_TEXTS], "cta": b.cta}
            _add(out, row, ad_why)
    return out


# ---- approvals --------------------------------------------------------------
def approvals():
    return json.loads(APPROVALS.read_text()) if APPROVALS.is_file() else {"first_go": None, "approved": []}


def approval_for(name):
    a = approvals()
    if not a.get("first_go"):
        raise SystemExit("REFUSED: no first go from the owner recorded in approvals.json — nothing has ever been "
                         "uploaded by this tool, and the first real upload is his call.")
    hit = next((x for x in a["approved"] if x["handoff"] == name), None)
    if not hit:
        raise SystemExit(f"REFUSED: {name} is not approved in approvals.json.")
    return hit


# ---- the ad -----------------------------------------------------------------
# Every Advantage+ creative "enhancement" off: the ad runs as the drop made it.
# Meta adds new keys every few months (three in Jun 2026) — refresh this list.
OPT_OUT = ["adapt_to_placement", "image_touchups", "video_auto_crop", "text_optimizations",
           "image_templates", "image_uncrop", "image_background_gen", "image_brightness_and_contrast",
           "image_animation", "video_filtering", "video_uncrop", "enhance_cta", "creative_stickers",
           "inline_comment", "reveal_details_over_time", "text_translation", "pac_relaxation",
           "add_text_overlay", "description_automation", "product_extensions"]


def targeting(b):
    """What the live ad sets run (read off the 260923a ad set): the brand's
    countries and ages, Advantage+ audience on, no placement list — so Meta
    places freely and the campaign stays an Advantage+ sales campaign."""
    return {"age_min": b.age[0], "age_max": b.age[1],
            "geo_locations": {"countries": b.countries, "location_types": ["frequently_in", "home", "recent"]},
            "targeting_automation": {"advantage_audience": 1}}


def flexible_ad(ad, b, st, m):
    """Meta's flexible ad format (marketing-api/flexible-ad-format, v25): every
    picture or video of the unit in one ad, Meta choosing per person.

    It goes on POST /ads as `creative_asset_groups_spec`, never on the creative
    (there it turns the ad set into a dynamic-creative one), and the first asset
    of the group must be the creative's own picture or video (error 3858355).
    No dynamic-creative ad set is needed, so many ads share one ad set."""
    media = [st["media"][f] for f in ad["media"]]
    cta = {"type": ad["cta"], "value": {"link": ad["url"]}}
    story = {"page_id": b.page_id, **({"instagram_user_id": b.instagram_id} if b.instagram_id else {})}
    texts = ([{"text": t, "text_type": "primary_text"} for t in ad["bodies"]]
             + [{"text": t, "text_type": "headline"} for t in ad["titles"]]
             + [{"text": t, "text_type": "description"} for t in ad.get("descriptions") or []])   # 4 Oct: video ads dropped them
    if ad["kind"] == "video":
        thumbs = [st["media"][f"{v}#thumb"] for v in media]
        story["video_data"] = {"video_id": media[0], "image_hash": thumbs[0], "message": ad["bodies"][0],
                               "title": ad["titles"][0], "call_to_action": cta}
        group = {"videos": [{"video_id": v, "image_hash": t} for v, t in zip(media, thumbs)]}
    else:
        story["link_data"] = {"link": ad["url"], "image_hash": media[0], "message": ad["bodies"][0],
                              "name": ad["titles"][0], "call_to_action": cta,
                              **({"description": ad["descriptions"][0]} if ad["descriptions"] else {})}
        group = {"images": [{"hash": h} for h in media]}
    return {"creative": {"name": ad["meta_ad_name"], "object_story_spec": story, "url_tags": URL_TAGS,
                         **_advantage_off()},
            "creative_asset_groups_spec": {"groups": [{**group, "texts": texts, "call_to_action": cta}]}}


def _advantage_off():
    return {"degrees_of_freedom_spec": {"creative_features_spec": {k: {"enroll_status": "OPT_OUT"} for k in OPT_OUT}},
            "contextual_multi_ads": {"enroll_status": "OPT_OUT"}}


def carousel_ad(ad, b, st, m=None):
    """One swipeable ad, the slides in the card's order (object_story_spec.
    link_data.child_attachments). multi_share_optimized off so Meta keeps the
    order, no end card, the primary text as the message, every slide going to
    the page. A slide that is a video carries its id + a thumbnail hash.
    A slide's headline is its own when the card has one per slide, else the first."""
    cta = {"type": ad["cta"], "value": {"link": ad["url"]}}
    titles = ad["titles"]
    kids = []
    for i, f in enumerate(ad["media"]):
        ref = st["media"][f]
        kid = {"link": ad["url"], "name": titles[i] if len(titles) == len(ad["media"]) else titles[0],
               "call_to_action": cta}
        if Path(f).suffix.lower() in VIDEO:
            kid.update(video_id=ref, image_hash=st["media"][f"{ref}#thumb"])
        else:
            kid["image_hash"] = ref
        if ad["descriptions"]:
            kid["description"] = ad["descriptions"][0]
        kids.append(kid)
    story = {"page_id": b.page_id, **({"instagram_user_id": b.instagram_id} if b.instagram_id else {}),
             "link_data": {"link": ad["url"], "message": ad["bodies"][0], "child_attachments": kids,
                           "multi_share_optimized": False, "multi_share_end_card": False,
                           "call_to_action": cta}}
    return {"creative": {"name": ad["meta_ad_name"], "object_story_spec": story, "url_tags": URL_TAGS,
                         **_advantage_off()}}


# ---- go ---------------------------------------------------------------------
def go(folder, p, approval, m=None, state_f=None, log=print, runs_root=None):
    """Build plan `p` in the account. `m` is a Meta (a fake one in tests);
    `state_f` where the ids made so far are kept (default state.json in the
    hand-off's runs home, upload_home). A hand-off half done before 7 Oct 2026
    resumes from its legacy returned/upload/state.json when the runs copy is
    absent; that file is read, never rewritten or deleted."""
    b = Brand(p["brand"])
    if m is None:
        from meta import Meta
        m = Meta(b)
    status = "ACTIVE" if approval.get("start") == "ACTIVE" else "PAUSED"
    load_f = None
    if state_f is None:
        state_f = upload_home(p["brand"], p.get("handoff") or Path(folder).resolve().name, runs_root) / "state.json"
        legacy = Path(folder) / "returned" / "upload" / "state.json"
        if not state_f.is_file() and legacy.is_file():
            load_f = legacy
            log(f"  resumed from the legacy state {legacy} (saves go to {state_f})")
    state_f = Path(state_f)
    load_f = load_f or state_f
    state_f.parent.mkdir(parents=True, exist_ok=True)
    resumed = load_f.is_file()              # a run before this one got part of the way
    st = json.loads(load_f.read_text()) if resumed else {"campaigns": {}, "ad_sets": {}, "media": {}, "ads": {}}
    save = lambda: state_f.write_text(json.dumps(st, indent=1))
    if load_f != state_f:
        save()                              # the runs copy starts as the legacy state, even if nothing is left to do

    DEAD = ("ARCHIVED", "DELETED")

    def find(edge, name, parent):
        """The live one by name — an archived or deleted twin with the same name is passed over (2026-10-12)."""
        for x in m.paged(f"{parent}/{edge}", fields="id,name,effective_status", limit=500):
            if x["name"] == name and x.get("effective_status") not in DEAD:
                return x["id"]

    def alive(oid):
        """A remembered id still takes ads. the owner, 2026-10-12: a card kept posting into an ad set that had been
        archived since its first try ("Archived ad sets may only contain archived or deleted ads") while a live
        ad set of the same name sat beside it. A lookup that fails is taken as alive — Meta answers the post."""
        try:
            return m.get(oid, fields="effective_status").get("effective_status") not in DEAD
        except (SystemExit, Exception):  # noqa: BLE001
            return True

    acct = f"act_{m.ACCOUNT}"
    ids_f, ids = known_ids(b.name, runs_root)   # name -> id per brand: Meta is asked by name only on a miss

    def keep(kind, key, val):
        if ids[kind].get(key) != val:
            ids[kind][key] = val
            remember_ids(ids_f, ids)

    for camp, c in p["campaigns"].items():
        if camp not in st["campaigns"]:
            cid = ids["campaigns"].get(camp) or find("campaigns", camp, acct)
            if not cid:                         # a new funnel: its campaign, paused, budget on the campaign
                cid = m.post(f"{acct}/campaigns", name=camp, objective="OUTCOME_SALES", status="PAUSED",
                             special_ad_categories=[], daily_budget=int(b.daily_budget) * 100,
                             bid_strategy="LOWEST_COST_WITHOUT_CAP")["id"]
                st.setdefault("made", []).append(cid)
            st["campaigns"][camp] = cid
            save()
        keep("campaigns", camp, st["campaigns"][camp])
        for ad_set in c["ad_sets"]:
            k = f"{camp}|{ad_set}"
            if k in st["ad_sets"] and alive(st["ad_sets"][k]):
                keep("ad_sets", k, st["ad_sets"][k])
                continue
            sid = ids["ad_sets"].get(k)
            if sid and not alive(sid):
                sid = None                      # archived since we remembered it: find the live one by name
            sid = sid or find("adsets", ad_set, st["campaigns"][camp])
            if not sid:
                # an ad set is made only when the owner signed it new, or it is a promo one (ad_sets.py, 2026-10-27)
                import ad_sets as AS
                closed = AS.why_closed(b.name, ad_set, runs_root)
                if closed:
                    raise SystemExit(closed)
                sid = m.post(f"{acct}/adsets", name=ad_set, campaign_id=st["campaigns"][camp], status="PAUSED",
                             billing_event="IMPRESSIONS", optimization_goal=b.optimization_goal,
                             targeting=targeting(b),
                             promoted_object={"pixel_id": b.pixel_id, "custom_event_type": b.conversion_event},
                             **attribution(b))["id"]
                st.setdefault("made", []).append(sid)
            st["ad_sets"][k] = sid
            save()
            keep("ad_sets", k, sid)

    for i, ad in enumerate(p["ads"], 1):
        if ad["meta_ad_name"] in st["ads"]:
            continue
        sid = st["ad_sets"][f"{ad['campaign']}|{ad['ad_set']}"]
        # the ads list is read only when the last run stopped half way through THIS ad (its media went
        # up, no ad id came back) — the one case where the ad may exist without its id on file
        if resumed and any(f in st["media"] for f in ad["media"]):
            have = find("ads", ad["meta_ad_name"], sid)
            if have:
                st["ads"][ad["meta_ad_name"]] = have
                save()
                continue
        # send every file first, then wait for all the videos at once (one status read for all), thumbnails after
        is_video = lambda f: Path(f).suffix.lower() in VIDEO
        for f in ad["media"]:
            if f not in st["media"]:
                if is_video(f) and any(is_video(x) for x in st["media"]):
                    pace.between_videos(log)      # one video at a time, with a person's pause between (pace.json)
                st["media"][f] = (m.send_video(f, name=Path(f).name[:100]) if is_video(f)
                                  else m.upload_image(f, name=Path(f).name[:100]))
                save()
        waiting = {st["media"][f]: Path(f).name for f in ad["media"]
                   if is_video(f) and f"{st['media'][f]}#thumb" not in st["media"]}
        if waiting:
            m.wait_videos(list(waiting), waiting)
        for f in ad["media"]:
            if is_video(f) and f"{st['media'][f]}#thumb" not in st["media"]:
                st["media"][f"{st['media'][f]}#thumb"] = thumb_for(m, ad, f, st["media"][f])
                save()
        ad_body = (carousel_ad if ad.get("format") == "carousel" else flexible_ad)(ad, b, st, m)
        ad_body.update(name=ad["meta_ad_name"], adset_id=sid, status=status)
        st["ads"][ad["meta_ad_name"]] = m.post(f"{acct}/ads", **ad_body)["id"]
        save()
        log(f"  {i}/{len(p['ads'])}  {ad['meta_ad_name']} -> {st['ads'][ad['meta_ad_name']]}")
    if status == "ACTIVE":
        switch_on(m, p, st, log)
        save()
    return st


def attribution(b):
    """The ad set's attribution window, from the brand's account file (the owner,
    2026-10-08): 7-day click · 1-day view · 1-day engaged view while learning,
    1-day click once scaling. Nothing set -> Meta's own default."""
    a = (getattr(b, "d", None) or {}).get("attribution") or {}
    spec = a.get(a.get("use", "learning"))
    return {"attribution_spec": spec} if spec else {}


def switch_on(m, p, st, log=print):
    """'On' means the ad runs. the owner, 7 Oct 2026: the Creator-A face scrub ad was
    approved Paused by default and its new ad set was made paused, so nothing ran.
    A campaign or ad set this upload made is switched on with the ad. One that
    already existed and is paused is left alone (it may hold other ads) and
    written on the card as a warning."""
    made = set(st.get("made", []))
    st["warnings"] = []
    for camp in {a["campaign"] for a in p["ads"]}:
        cid = st["campaigns"][camp]
        if cid in made:
            m.post(cid, status="ACTIVE")
            log(f"  campaign on: {camp}")
    for k in {f"{a['campaign']}|{a['ad_set']}" for a in p["ads"]}:
        sid = st["ad_sets"][k]
        if sid in made:
            m.post(sid, status="ACTIVE")
            log(f"  ad set on: {k.split('|')[1]}")
    # No read-back from Meta (the owner, 2026-10-08: no direct Meta reads). The card
    # shows what was set; delivery comes from the warehouse.
    st["delivery"] = {}


def _funnel_of(link_id):
    sys.path.insert(0, str(REPO / "lab/damon/handoff-standard/skill"))
    import handoff as H
    return H.funnel_of(link_id)


def link_url(brand, link_id):
    """A catalog link id -> its URL (the catalog the hand-off reads)."""
    sys.path.insert(0, str(REPO / "lab/damon/handoff-standard/skill"))
    import handoff as H
    try:
        return H.Catalog(H.DEFAULT_CATALOG, brand).url(link_id)
    except Exception:
        return None


def card_fields(card):
    return {k: card.get(k) for k in ("product", "avatar", "angle", "brief_id") if card.get(k)}


def thumb_for(m, ad, f, vid):
    """The picture shown before a video plays: the card's designed thumbnail for this video (put in the account's
    picture library), else Meta's own preferred frame."""
    t = (ad.get("thumbs") or {}).get(f)
    if t and Path(t).is_file():
        return m.upload_image(t, name=Path(t).name[:100])
    return m.thumbnail_hash(vid)


def card_plan(folder, card):
    """A card -> the same plan shape as plan(): one ad per landing page, named
    <ad name>_<funnel_of(link id)>, into the campaign / ad set the brand's
    naming gives. Every reason an ad cannot go is in `held`."""
    folder = Path(folder)
    b = Brand(card["brand"])
    fields = card_fields(card)
    w = card.get("words") or {}
    media = [folder / f for f in card.get("media") or []]
    out = {"card": card.get("ad_name"), "brand": b.name, "account": b.account_id,
           "made": datetime.now().isoformat(timespec="seconds"), "campaigns": {}, "ads": [], "held": []}
    ad_set, why = ad_set_for(b, fields)
    if card.get("ad_set"):                  # an ad set picked for this card (the owner, 24 Oct 2026: promo ads get their own)
        ad_set, why = card["ad_set"], None
    why = [why] if why else []
    missing = [p.name for p in media if not p.is_file()]
    if missing:
        why.append(f"{len(missing)} file(s) not found: {', '.join(missing[:3])}")
    if not w.get("primary"):
        why.append("no primary text")
    if not w.get("headlines"):
        why.append("no headline")
    for pg in card.get("pages") or []:
        link_id = pg.get("link_id") or ""
        url, funnel, note = page_for({"url": pg.get("url") or link_url(b.name, link_id) or ""}, b.name)
        ad_why = list(why)
        try:
            meta_name = N.short_meta(card["ad_name"], _funnel_of(link_id))
        except (ValueError, KeyError) as e:
            meta_name, ad_why = f"{card.get('ad_name')}_?", ad_why + [f"no Meta ad name: {e}"]
        camp = None
        if not funnel:
            ad_why.append(note)
        else:
            if product_clash(b, funnel, fields):
                ad_why.append(product_clash(b, funnel, fields))
            camp, cw = campaign_for(b, funnel, fields)
            if card.get("campaign"):            # picked on the approval page (the owner, 17 Oct 2026)
                camp, cw = card["campaign"], new_campaign(b.name, card["campaign"])
            ad_why += [cw] if cw else []
        row = {"meta_ad_name": meta_name, "unit": card.get("ad_name"), "old_name": card.get("old_name"),
               "brief_id": card.get("brief_id"), "link_id": link_id, "url": url, "url_note": note,
               "campaign": camp, "ad_set": ad_set, "funnel": funnel,
               "kind": kind_of(media), "format": card.get("format", "flexible"),
               "media": [str(p) for p in media][:MAX_IMAGES],
               "thumbs": {str(folder / v): str(folder / t) for v, t in (card.get("thumbs") or {}).items()},
               "bodies": [_plain(x) for x in (w.get("primary") or [])][:MAX_TEXTS],
               "titles": [_plain(x) for x in (w.get("headlines") or [])][:MAX_TEXTS],
               "descriptions": [_plain(x) for x in (w.get("descriptions") or [])][:MAX_TEXTS], "cta": b.cta}
        _add(out, row, ad_why)
    if not card.get("pages"):
        out["held"].append({"meta_ad_name": card.get("ad_name"), "why": ["no landing page on the card"]})
    return out


def _plain(t):
    from to_check import plain
    return plain(t)


LIVE = None   # default: the Drive tree, meta/live.jsonl — never the shared checkout (it would block the hourly pull)


def approvers():
    """The names whose approve sends a card in (approvers.json — the owner adds people)."""
    return json.loads((Path(__file__).resolve().parent / "approvers.json").read_text())["approvers"]


def upload_card(folder, m=None, log=print):
    """An approved card (in 2-approved, approval written by the page) -> Meta.

    On success: card["meta"] gets one row per ad, one line per ad goes into
    live.jsonl, and the folder moves to 3-live. On a Meta error the card stays
    in 2-approved with the error on it (card["upload_error"]) for a retry.
    Returns (new folder, card). Re-run safe: everything is found by name first."""
    import cards as C
    folder = Path(folder)
    card = C.load(folder)
    ap = card.get("approval") or {}
    if ap.get("decision") != "approve" or ap.get("by") not in approvers():
        raise SystemExit("REFUSED: this card has no approve on it from a name on approvers.json "
                         "(only the approval page writes one).")
    if C.where(folder)["state"] != "2-approved":
        raise SystemExit(f"REFUSED: the card is in {C.where(folder)['state']}, not 2-approved.")
    p = card_plan(folder, card)
    if p["held"]:
        raise SystemExit("held: " + "; ".join(w for h in p["held"] for w in h["why"]))
    pace.before_card(card["brand"], log=log)      # never two ads back to back (pace.json between_ads)
    try:
        st = go(folder, p, ap, m=m, state_f=folder / "upload-state.json", log=log)
    except SystemExit as e:
        card["upload_error"] = {"at": datetime.now().isoformat(timespec="seconds"), "error": str(e)[:1500]}
        C.save(folder, card)
        raise
    at = datetime.now().isoformat(timespec="seconds")
    card["meta"] = [{"link_id": a["link_id"], "meta_ad_name": a["meta_ad_name"], "ad_id": st["ads"][a["meta_ad_name"]],
                     "campaign": a["campaign"], "campaign_id": st["campaigns"].get(a["campaign"]),
                     "ad_set": a["ad_set"], "ad_set_id": st["ad_sets"].get(f"{a['campaign']}|{a['ad_set']}"),
                     "status": "ACTIVE" if ap.get("start") == "ACTIVE" else "PAUSED",
                     "delivery": (st.get("delivery") or {}).get(a["meta_ad_name"]), "at": at} for a in p["ads"]]
    if st.get("warnings"):
        card["start_warnings"] = st["warnings"]
    else:
        card.pop("start_warnings", None)
    card.pop("upload_error", None)
    C.save(folder, card)
    import cards as _C
    with (LIVE or _C.root() / "live.jsonl").open("a") as f:
        for r in card["meta"]:
            f.write(json.dumps({"ad_name": card["ad_name"], "meta_ad_name": r["meta_ad_name"], "ad_id": r["ad_id"],
                                "brand": card["brand"], "lane": card.get("lane"), "at": at}) + "\n")
    pace.card_done(card["brand"], card["ad_name"])
    new = C.move(folder, "3-live")
    return new, card


def _take_back_module():
    """ad-handoff's take_back, loaded by path (SI-143 (take-back home))."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ad_handoff_take_back", REPO / "components/ad-handoff/take_back.py")
    TB = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(TB)
    return TB


def write_back(folder, p, st, runs_root=None):
    """Meta ad id per ad name into live-ids.json in the hand-off's runs home
    (upload_home) and into the hand-off's returned/live-ids.json (the hand-off
    standard's declared return, which take-back reads), then take-back
    records each as live_meta_<id> in the hand-off ledger."""
    folder = Path(folder).resolve()
    rows = [{"ad_name": a["meta_ad_name"], "unit": a["unit"], "old_name": a["old_name"],
             "channel": "meta", "platform_id": st["ads"].get(a["meta_ad_name"])} for a in p["ads"]]
    text = json.dumps(rows, indent=1) + "\n"
    (folder / "returned" / "live-ids.json").write_text(text)
    home = upload_home(p["brand"], p.get("handoff") or folder.name, runs_root)
    home.mkdir(parents=True, exist_ok=True)
    (home / "live-ids.json").write_text(text)
    TB = _take_back_module()
    man = json.loads((folder / "manifest.json").read_text())
    staging = folder.parent.parent.parent
    TB.take_back(man["role"], man["brand"], man["name"], staging, staging / "ledger.jsonl")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("handoff", nargs="?", help="an ad-uploader hand-off folder")
    ap.add_argument("--links", help="only these link ids, comma-separated (default: the approval's, else all)")
    ap.add_argument("--go", action="store_true", help="upload — refused unless approved")
    ap.add_argument("--all-approved", action="store_true", help="upload every approved hand-off not yet done")
    a = ap.parse_args()

    if a.all_approved:
        for x in approvals()["approved"]:
            if x.get("done"):
                continue
            f = REPO / x["path"]
            print(f"== {x['handoff']}")
            run(f, x.get("links"), True)
        return
    if not a.handoff:
        ap.error("name a hand-off folder, or --all-approved")
    run(Path(a.handoff), a.links.split(",") if a.links else None, a.go)


def run(folder, links, do_go, runs_root=None):
    folder = Path(folder).resolve()
    name = json.loads((folder / "manifest.json").read_text())["name"]
    approval = approval_for(name) if do_go else None
    links = links or (approval or {}).get("links")
    p = plan(folder, links)
    out = upload_home(p["brand"], name, runs_root)
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"{p['handoff']}: {len(p['ads'])} ads ready, {len(p['held'])} held")
    for c, v in p["campaigns"].items():
        print(f"  {c}")
        for s, n in v["ad_sets"].items():
            print(f"     {s}: {n} ads")
    for h in p["held"][:12]:
        print(f"  held {h['meta_ad_name']}: {'; '.join(h['why'])}")
    if not do_go:
        print(f"plan only — nothing sent to Meta. {out / 'plan.json'}")
        return
    st = go(folder, p, approval, runs_root=runs_root)
    rows = write_back(folder, p, st, runs_root=runs_root)
    a = approvals()
    for x in a["approved"]:
        if x["handoff"] == name:
            x["done"] = date.today().isoformat()
            x["ads"] = len([r for r in rows if r["platform_id"]])
    APPROVALS.write_text(json.dumps(a, indent=1) + "\n")
    print(f"done: {len(rows)} ads in Meta, ids in {out / 'live-ids.json'}, {folder / 'returned' / 'live-ids.json'} "
          f"and the ledger")


if __name__ == "__main__":
    main()
