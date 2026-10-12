#!/usr/bin/env python3
"""Build one Meta bulk-import sheet from the production lines' finished elements.

Owns nothing. Reads four inputs, writes one sheet plus the picture files
named exactly as the sheet references them.

    build.py --brand <brand> --lane <lane> --run <copy run> --out <dir>
    build.py --handoff <ad-uploader hand-off folder> --out <dir>    # a drop: its own copy.csv

The brand is the only place a brand name enters: everything else — which
account, which Page, which pixel, where the pictures and copy live, how the
slugs are spelled — is read from `brands/<brand>/meta/account.json`.

Every row lands PAUSED. Nothing here talks to Meta.
"""
import argparse, csv, json, re, shutil, sys
from datetime import date
from pathlib import Path

import naming
from brand import Brand

# Meta recommends 1080x1920 for 9:16 and re-encodes whatever it is given. The
# masters are 1856x3300 PNGs at ~5 MB — 671 MB for a run, which no upload path
# enjoys. Delivering at 1440 wide keeps headroom over Meta's own spec and puts
# a whole run under 50 MB.
DELIVER_W = 1440
JPEG_Q = 92

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N            # parse_any: an ad name in either form -> its fields

# ---- the four inputs -------------------------------------------------------
# None of them are named here. Every one is a path the BRAND declares in
# `brands/<brand>/meta/account.json`, resolved by brand.py, because this
# folder must work for any brand without being edited (workspace rule 7).
QUEUE    = REPO / "tools/image-production/static/queue"   # review + audit, brand-agnostic
HEADERS  = HERE / "template-headers.json"              # Meta's own 143 columns

# ---- what the campaign is --------------------------------------------------
# The name comes from naming.py, never typed here, and follows whatever
# convention the account already runs rather than a new one. STRUCTURE.md says
# why the campaign carries no date and no theme: it has to stay comparable to
# its own last month.
#
# Market, product and funnel come from the brand; the lane comes from the drop
# (`--lane`), because one brand runs several and they never blend.
def creative_qc(tool, stage, run_dir, output, given=None, items=None):
    """THE CREATIVE QC LOOP (the owner, 2026-10-02: "installed for each of my
    production tools … for all stages in the creation process"): the output is
    reviewed against what it was given and the stage's bars
    (components/quality-checks/definitions/stages.json); the round is filed in
    <run>/qc-log/. Never stops the run on its own."""
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "quality-checks" / "marketing_chain_checks").is_dir())
        q = str(comp / "quality-checks")
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        f = review.after_stage(tool, stage, run_dir, output=output, items=items,
                               sources=[given] if given and Path(given).exists() else None)
        bad = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
        if bad:
            print(f"  QC {stage}: {len(bad)} finding(s) — see qc-log/QC-LOG.md")
        return f
    except Exception as e:
        print(f"  QC {stage}: review not run ({type(e).__name__})")
        return {}


def campaign_block(b, lane, funnel=None):
    c = b.campaign
    n = b.naming
    funnel = funnel or c.get("funnel")
    if "{funnel" in n["campaign"]:
        # A brand whose campaign name carries the funnel must say which one,
        # and the funnel must be one its own registry lists — never typed in.
        if not funnel:
            sys.exit(f"{b.name}'s campaign name carries the funnel: pass --funnel")
        reg = REPO / "brands" / b.name / "web" / "funnels" / "funnels.json"
        if reg.is_file():
            ids = [f["id"] for f in json.loads(reg.read_text()).get("funnels", [])]
            if funnel not in ids:
                sys.exit(f"--funnel {funnel} is not in {reg.relative_to(REPO)}: {', '.join(ids)}")
    fields = {"brand": b.name, **c, "lane": lane, "funnel": funnel}
    return {
    "Campaign Name": naming.campaign(fields, n["campaign"],
                                     naming.sep_for(n, "campaign"), spell=b.pretty),
    "Campaign Status": "PAUSED",
    # Proved against the live account 2026-09-11. The template's VALIDATION
    # sheet still lists the legacy objectives, but Meta answers "This objective
    # cannot be published" for Website Conversions — ODAX names only now.
    "Campaign Objective": b.objective,
    "Buying Type": "AUCTION",
    "Campaign Daily Budget": str(b.daily_budget),
    "Campaign Bid Strategy": "Highest volume or value",
    }


# The call to action and creative type are brand settings, both enum constants
# and both rejected in their friendly form. Creative type cannot be blank:
# "Link Ad" is refused, "Link Page Post Ad" and "Photo Page Post Ad" are
# accepted (probed row by row against the account).
UTM = ("utm_source=facebook&utm_medium=paid&utm_campaign={campaign}"
       "&utm_content={ad_name}&utm_term={sub}")

# The ad set is one sub-avatar's drop, so it carries that sub-avatar's own age
# band off its card in adsets.json. the owner's call, 2026-09-11: the avatar is a
# level he steers and reads at, not only a label on the ad.


def expired(offers, when=None):
    """Briefs whose offer bar is dead, with the date it died.

    A picture carries its offer burned into the image. An offer with an end
    date is a picture with an expiry, and nothing in this pipeline knew that
    until 28 Labor Day ads reached the sheet three days after the sale ended
    (2026-09-11). So the build asks before it ships.
    """
    when = when or date.today()
    out = {}
    if not offers or not offers.is_file():
        return out
    for brief, v in json.loads(offers.read_text())["briefs"].items():
        end = v.get("ends")
        if end and date.fromisoformat(end) < when:
            out[brief] = f"{v['offer']} ended {end} — bar reads \u201c{v['bar'][:44]}\u2026\u201d"
    return out


def held_file(brand):
    """The brand's cleared calls: runs/meta-upload/<brand>/held/held.json — written by
    image-production's static/queue/triage.py --apply (meta-upload#14)."""
    return REPO / "runs" / "meta-upload" / brand / "held" / "held.json"


def blocked(brand):
    """Pictures that must never reach the account, with the reason.

    Two gates, both from the review that already happened:
      - the owner killed it
      - the headline audit says the picture does not show what the headline claims,
        unless the brand's held_file(brand) lists it as read and cleared
    """
    out = {}
    rev = QUEUE / "review.json"
    if rev.is_file():
        for name, v in json.loads(rev.read_text()).items():
            if v.get("verdict") == "kill":
                why = (v.get("why") or "").strip().splitlines()
                out[name] = "killed — " + (why[0] if why else "no reason recorded")
    aud = QUEUE / "headline-audit.json"
    held = held_file(brand)
    calls = json.loads(held.read_text())["calls"] if held.is_file() else {}
    if aud.is_file():
        for name, v in json.loads(aud.read_text()).items():
            if v.get("verdict") != "MISMATCH" or name in out:
                continue
            # a mismatch that was read and cleared ships: the judge asked a still
            # photograph to do something no still photograph can do, or judged a
            # headline the picture never carried
            if name in calls:            # read against its picture and cleared
                continue
            out[name] = "headline mismatch — " + (v.get("why") or "").strip().split(".")[0]
    return out


def roster_map(roster):
    """person id -> sub-avatar. Empty when the brand has no roster yet."""
    if not roster or not roster.is_file():
        return {}
    people = json.loads(roster.read_text())["people"]
    out = {}
    for p in people:
        sub = p.get("sub") or (p.get("also_plays") or [None])[0]
        out[p["id"]] = sub
    return out


def units(pictures):
    """Every finished picture, with the unit it belongs to."""
    for batch in sorted(pictures.iterdir()):
        ads = batch / "ads"
        if not ads.is_dir():
            continue
        for unit in sorted(ads.iterdir()):
            man = unit / "manifest.json"
            if not man.is_file():
                continue
            d = json.loads(man.read_text())
            for a in d["ads"]:
                yield d, a, unit / a["file"]


def near_duplicates(paths, within=15):
    """Pictures that are the same picture, inside one concept.

    A concept ships three variations so Meta has three shots at the same
    idea. That only works if they differ. Several formats here —
    distressedposter, faceoff, apology, checklist — were producing renders a
    perceptual hash cannot tell apart: Beto's faceoff a01 and a03 came back
    one bit apart out of 256. Three ad slots, one picture, the budget split
    three ways for a single read. the owner, looking at them: "Same here we're
    doing the same images bro".

    dHash on the picture only — the ink bands top and bottom are identical on
    every asset, and including them makes everything look alike.

    Returns the names to drop, keeping the first of each cluster.
    """
    from PIL import Image
    def h(p, n=16):
        im = Image.open(p).convert("L")
        w, ht = im.size
        im = im.crop((0, int(ht * 0.18), w, int(ht * 0.80))).resize((n + 1, n), Image.LANCZOS)
        px = list(im.getdata())
        b = 0
        for r in range(n):
            for c in range(n):
                b = b * 2 + (1 if px[r * (n + 1) + c] > px[r * (n + 1) + c + 1] else 0)
        return b
    keep, drop = [], {}
    for name, path in paths:
        hv = h(path)
        twin = next((k for k, kh in keep if bin(hv ^ kh).count("1") <= within), None)
        if twin:
            drop[name] = f"same picture as {(N.parse_any(twin) or {}).get('asset') or twin.rsplit('-', 1)[-1]} of its own concept"
        else:
            keep.append((name, hv))
    return drop


def utm_slug(name):
    """A campaign name as it can safely live in a query string.

    The account's names carry a ™ and spaces around pipes. Both survive a
    URL only as percent-escapes, which makes the tag unreadable in analytics
    and easy to mangle on the way through. So: ascii, lower, hyphens.
    """
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def copy_for(book, fmt, sub, turn):
    """The copy for this format and sub-avatar, rotating through alternates.

    The copy bank sometimes holds more than one variation under the same
    (format, sub-avatar) key — checklist has three headlines written for
    sub-one, and four other formats do the same. Taking the first
    and dropping the rest threw away ten written variations and left 138 ads
    carrying only 37 distinct headlines.

    Since one picture is one ad, alternates have somewhere real to go: spread
    them across that format's pictures. Two ads of the same format then differ
    in their words as well as their picture, and because they are separate ads
    the report still says which won — which is the whole point, and what
    stacking them inside one ad would cost.

    `turn` counts how many CONCEPTS of this (format, sub-avatar) have been
    built so far — not how many pictures. Every variation of one concept
    carries the same words; that is what makes it a variation rather than a
    second ad. Rotating per picture (which this did for a few hours on
    2026-09-11) hands each of a concept's three pictures a different headline
    and quietly turns one test into three untested ones. the owner, seeing it:
    "these are literally the same concept not 3 unique concepts".
    """
    blk = book.get(fmt)
    if not blk:
        return None
    opts = [v for v in blk["v"] if v["for"] == sub]
    return opts[turn % len(opts)] if opts else None



def ad_set_value(b, field, value):
    """An ad-name value in the brand's own list spelling.

    Ad names in the old form squash their words (`avatarfour`,
    `tonememory`); the lists now hyphenate (`avatar-four`,
    `pigment-memory`). Match on the letters alone, so either form lands on
    the list id — and a value no list holds is refused, never coined."""
    if not value:
        sys.exit(f"an ad name carries no {field}, so it has no ad set")
    key = lambda s: str(s).replace("-", "").lower()
    base = REPO / "brands" / b.name
    if field == "avatar":
        ids = [d.name for d in (base / "core-avatars").iterdir() if d.is_dir()]
    elif field == "angle":
        angles = json.loads((base / "strategy/angles.json").read_text())["angles"]
        ids = [a["id"] for a in angles if a.get("status") == "active"]
        was = {key(a["was"]): a["id"] for a in angles if a.get("was") and a.get("status") == "active"}
        if key(value) in was:
            return was[key(value)]
    else:
        return value
    hit = next((i for i in ids if key(i) == key(value)), None)
    if not hit:
        sys.exit(f"{field} `{value}` is not in {b.name}'s list: {', '.join(ids)}")
    return hit


def meta_name(a, funnel):
    """The ad's name in Meta. A short-form picture (brand_product_brief_batch
    _asset-NN) launches as its batch: the folder name plus the funnel
    (names.short_meta), so a batch's variations share one name and each
    launch to a page is its own. Anything else keeps the name it arrived with."""
    d = N.parse_any(Path(a["file"]).name) or N.parse_any(a["name"]) or {}
    if funnel and d.get("form") == "short":
        return N.short_meta(d["ad_name"], funnel)
    return a["name"]


def fields_of(brand, a):
    """What the picture is — from its name, filled from its brief. A short
    name carries only brand, product, brief and batch; avatar, angle and the
    rest are the brief's (names.brief_header)."""
    f = N.parse_any(Path(a["file"]).name) or N.parse_any(a["name"]) or {}
    # the product off the name picks between briefs sharing a number (numbers count per brand+product)
    head = N.brief_header(brand, f.get("brief"), f.get("product")) if f.get("brief") not in (None, "none") else None
    return {**(head or {}), **{k: v for k, v in f.items() if v not in (None, "")}}


def sheet_from_handoff(folder, out, links=None):
    """The import sheet for a drop, read the way the uploader reads it
    (drop.py: the drop's own copy.csv, its pictures, the hand-off's pages).

    The fallback for an account whose API is not open: one row per picture
    per landing page, every row PAUSED, the first headline and description
    as the row's. Videos cannot travel by sheet — Meta's template has no
    video file column — so a video ad is listed in summary.json as API-only."""
    import upload
    p = upload.plan(folder, links)
    b = Brand(p["brand"])
    headers = json.loads(HEADERS.read_text())
    out = Path(out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows, api_only = [], []
    for ad in p["ads"]:
        if ad["kind"] == "video":
            api_only.append(ad["meta_ad_name"])
            continue
        for f in ad["media"]:
            img = Path(f).name
            if not (out / "images" / img).is_file():
                shutil.copy2(f, out / "images" / img)
            r = dict.fromkeys(headers, "")
            r.update({
                "Campaign Name": ad["campaign"], "Campaign Status": "PAUSED",
                "Campaign Objective": b.objective, "Buying Type": "AUCTION",
                "Campaign Daily Budget": str(b.daily_budget), "Campaign Bid Strategy": "Highest volume or value",
                "Ad Set Name": ad["ad_set"], "Ad Set Run Status": "PAUSED",
                "Link Object ID": b.page_id, "Link": ad["url"],
                "Ad Name": ad["meta_ad_name"], "Ad Status": "PAUSED",
                "Title": ad["titles"][0], "Body": ad["bodies"][0],
                "Link Description": (ad["descriptions"] or [""])[0],
                "Image File Name": img, "Call to Action": b.cta, "Creative Type": b.creative_type,
                "URL Tags": upload.URL_TAGS,
            })
            rows.append(r)
    with (out / "import.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    (out / "summary.json").write_text(json.dumps({
        "brand": b.name, "handoff": p["handoff"], "rows": len(rows), "ads": len(p["ads"]),
        "api_only_videos": api_only, "held_back": [{"ad": h["meta_ad_name"], "why": h["why"]} for h in p["held"]],
    }, indent=2, ensure_ascii=False))
    print(f"{len(rows)} rows · {len(p['ads'])} ads · {len(p['held'])} held · {len(api_only)} video ads API-only")
    print(f"sheet:  {out / 'import.csv'}")
    return 0


def main():
    if "--handoff" in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--handoff", required=True, help="an ad-uploader hand-off folder (reads its drop's copy.csv)")
        ap.add_argument("--out", required=True)
        ap.add_argument("--links", help="only these link ids, comma-separated")
        a = ap.parse_args()
        return sheet_from_handoff(a.handoff, a.out, a.links.split(",") if a.links else None)
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True,
                    help="which brand's account.json to read — the only place "
                         "a brand name enters these tools")
    ap.add_argument("--lane", required=True,
                    help="the drop's lane, e.g. avatarone. Lanes never blend, "
                         "so each gets its own campaign")
    ap.add_argument("--run", required=True,
                    help="the copy run under the brand's copy folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--strict", action="store_true",
                    help="fail if any picture has no copy, instead of listing it")
    ap.add_argument("--png", action="store_true",
                    help="ship the full-size PNG masters instead of delivery JPEGs")
    # --- the drop: one batch of creative, one ad set (or as many as the
    #     50-cap forces). STRUCTURE.md, "One drop, one ad set".
    ap.add_argument("--shipped", default=date.today().strftime("%y%m%d"),
                    help="YYMMDD the batch goes into the account (default today)")
    ap.add_argument("--funnel", default="",
                    help="the funnel the drop's ads send to, by its id in "
                         "brands/<brand>/web/funnels/funnels.json — needed when the "
                         "brand's campaign name carries the funnel")

    ap.add_argument("--allow-expired", action="store_true",
                    help="ship pictures whose offer bar has already expired. "
                         "Only for a deliberate re-run of an old drop.")
    ap.add_argument("--hashes",
                    help="a JSON map of ad name -> image hash. Meta binds a "
                         "picture already in the account library by hash, so "
                         "with this the sheet needs no images folder and the "
                         "whole drop imports in one go instead of ten.")
    ap.add_argument("--adset-ids",
                    help="a JSON map of ad set name -> id, for ad sets that "
                         "already exist. Without it every import makes new "
                         "ones, and the pixel has to be set again on each.")
    ap.add_argument("--campaign-id", default="",
                    help="attach to this existing campaign instead of creating "
                         "a new one. Without it Meta makes a fresh campaign per "
                         "import, which is how RUN-01 ended up doubled.")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)

    b = Brand(args.brand)
    nm = b.naming
    CAMPAIGN = campaign_block(b, args.lane, args.funnel)

    headers = json.loads(HEADERS.read_text())
    book    = json.loads((b.copy / args.run / "copy.json").read_text())["formats"]
    pages   = json.loads(b.pages.read_text())
    sets    = json.loads(b.adsets.read_text()) if b.adsets else {"sub_avatars": {}, "_common": {}}
    talent  = roster_map(b.roster)

    stop = blocked(b.name)
    dead = {} if args.allow_expired else expired(b.offers)
    hashes = json.loads(Path(args.hashes).read_text()) if args.hashes else {}
    adset_ids = json.loads(Path(args.adset_ids).read_text()) if args.adset_ids else {}
    short = {}
    rows, gaps, held, seen_names = [], [], [], set()
    turns = {}                  # (format, sub-avatar) -> {concept: its turn}
    for d, a, src in units(b.pictures):
        if a["name"] in stop:
            held.append((a["name"], stop[a["name"]]))
            continue
        sub = talent.get(d["talent"])
        seen_c = turns.setdefault((d["format"], sub), {})
        if d["concept"] not in seen_c:
            seen_c[d["concept"]] = len(seen_c)
        turn = seen_c[d["concept"]]
        c    = copy_for(book, d["format"], sub, turn)
        if not c:
            gaps.append((d["format"], sub, d["talent"], a["name"]))
            continue
        tgt = sets["sub_avatars"].get(sub)
        if not tgt:
            gaps.append((d["format"], sub, d["talent"],
                         a["name"] + " [sub-avatar not in adsets.json]"))
            continue
        # the name is read by field, in either form (`…-p140-9x16-260902a-a01`
        # or `…_brief-0140_9x16_batch-…_asset-01`); offers.json keys briefs on
        # the old code, so both spellings are tried against it
        f = N.parse_any(a["name"]) or {}
        problem, who = f.get("problem") or d.get("problem"), d["talent"]
        brief = f.get("brief") or d.get("brief")
        dead_hit = next((dead[x] for x in N.brief_forms(brief) if x in dead), None)
        if dead_hit:
            held.append((a["name"], dead_hit))
            continue
        if not src.is_file():
            gaps.append((d["format"], sub, d["talent"], a["name"] + " [file missing]"))
            continue

        # The delivery filename is short on purpose: it only has to match the
        # sheet's own Image File Name, and the 13-field name lives in Ad Name,
        # which is what Meta reports on. The masters keep their full names.
        if a["name"] in hashes:
            img = None                 # bound by hash; no file needs shipping
        elif a["file"] in short:
            img = short[a["file"]]
        else:
            img = (a["file"] if args.png
                   else f"{len(short) + 1:03d}-{f.get('talent') or d['talent']}-{f.get('asset_id') or a['name'][-3:]}.jpg")
            short[a["file"]] = img
        if img and img not in seen_names:
            if args.png:
                shutil.copy2(src, out / "images" / img)
            else:
                from PIL import Image
                im = Image.open(src).convert("RGB")
                h = round(DELIVER_W * im.height / im.width)
                im.resize((DELIVER_W, h), Image.LANCZOS).save(
                    out / "images" / img, "JPEG", quality=JPEG_Q,
                    optimize=True, progressive=True)
            seen_names.add(img)

        link = pages["by_sub_avatar"].get(sub, pages["_entry"])
        r = dict.fromkeys(headers, "")
        r.update(CAMPAIGN)
        r.update({
            # ad set — budgets stay blank so the campaign budget rules (CBO)
            "Ad Set Name": "",            # dealt after the loop, once n is known
            "Ad Set Run Status": "PAUSED",
            "Optimization Goal": sets["_common"]["Optimization Goal"],
            "Billing Event": sets["_common"]["Billing Event"],
            "Countries": sets["_common"]["Countries"],
            "Gender": sets["_common"]["Gender"],
            "Age Min": str(tgt["age_min"]),
            "Age Max": str(tgt["age_max"]),
            "Publisher Platforms": sets["_common"]["Publisher Platforms"],
            "Link Object ID": b.page_id,
            "Link": link,
            # ad — one row per picture
            "Ad Name": meta_name(a, args.funnel),
            "Ad Status": "PAUSED",
            "Title": c["title"],
            "Body": c["body"],
            "Link Description": c["desc"],
            "Display Link": b.display_link,
            **({"Image Hash": hashes[a["name"]]} if a["name"] in hashes
               else {"Image File Name": img}),
            "Call to Action": b.cta,
            "Creative Type": b.creative_type,
            "URL Tags": UTM.format(campaign=utm_slug(CAMPAIGN["Campaign Name"]),
                                   ad_name=a["name"], sub=sub),
            "_problem": problem,
            "_fields": fields_of(b.name, a),
        })
        if args.campaign_id:
            r["Campaign ID"] = args.campaign_id
        rows.append(((sub, who, problem), r))

    # ---- cut the drop into ad sets ----------------------------------------
    # Round-robin so every ad set gets the same mix and the shards stay
    # interchangeable. naming.py explains why sliced would lie to us.
    # One ad set per sub-avatar. A sub-avatar with more than 50 ads is split,
    # and only then; the shards of one avatar are dealt so they stay
    # interchangeable, which is what naming.deal exists for.
    # One ad set per (sub-avatar, man, promise) — the three things Meta must
    # not be allowed to choose between. naming.ad_set carries the reasoning.
    by_sub = {}
    for (sub, _t, _p), _ in rows:
        by_sub[sub] = by_sub.get(sub, 0) + 1
    by = nm.get("ad_set_by")
    if by:
        rows = [(tuple(ad_set_value(b, k, r["_fields"].get(k)) for k in by), r)
                for _, r in rows]
    by_key = {}
    for key, _ in rows:
        by_key[key] = by_key.get(key, 0) + 1
    ordered = []
    for key in sorted(by_key, key=lambda k: (-by_key[k], k)):
        mine = [kr for kr in rows if kr[0] == key]
        if by:
            # One ad set per value of `ad_set_by` (Brand A: avatar + angle),
            # holding every batch — no date, no part number. Past Meta's
            # 50-ad cap the brand has not ruled what happens, so stop.
            name = naming.render(nm["ad_set"], {"brand": b.name, **dict(zip(by, key))},
                                 naming.sep_for(nm, "ad_set"), b.pretty)
            if len(mine) > naming.ADS_PER_AD_SET:
                sys.exit(f"{name} would get {len(mine)} ads from this drop alone, "
                         f"over Meta's {naming.ADS_PER_AD_SET}. What a full ad set "
                         f"does is not ruled yet — split the drop or rule it.")
            for _, r in mine:
                r["Ad Set Name"] = name
                if name in adset_ids:
                    r["Ad Set ID"] = adset_ids[name]
            ordered += mine
            continue
        parts = naming.deal(mine)
        for i, part in enumerate(parts, 1):
            name = naming.ad_set(
                {"avatar": key[0], "talent": key[1], "problem": key[2],
                 "shipped": args.shipped, "lane": args.lane},
                i, len(parts), nm["ad_set"],
                naming.sep_for(nm, "ad_set"), spell=b.pretty)
            for _, r in part:
                r["Ad Set Name"] = name
                if name in adset_ids:
                    r["Ad Set ID"] = adset_ids[name]
            ordered += part
    rows = [r for _, r in ordered]
    for r in rows:
        r.pop("_problem", None)
        r.pop("_fields", None)

    sheet = out / "import.csv"
    with sheet.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    # THE CREATIVE QC LOOP (2026-10-02): the sheet against the brand's naming
    # bank, account file and offers (stages.json "meta-upload")
    creative_qc("meta-upload", "sheet", out, sheet)

    by_set = {}
    for r in rows:
        by_set.setdefault(r["Ad Set Name"], 0)
        by_set[r["Ad Set Name"]] += 1

    (out / "summary.json").write_text(json.dumps({
        "brand": b.name,
        "lane": args.lane,
        "run": args.run,
        "campaign": CAMPAIGN["Campaign Name"],
        "daily_budget": CAMPAIGN["Campaign Daily Budget"],
        "ads": len(rows),
        "ad_sets": by_set,
        "ads_per_ad_set_cap": naming.ADS_PER_AD_SET,
        "by_sub_avatar": by_sub,
        "images": len(seen_names),
        "links": {s: pages["by_sub_avatar"].get(s, pages["_entry"]) for s in by_sub},
        "gaps": [{"format": f, "sub_avatar": s, "talent": t, "ad": n} for f, s, t, n in gaps],
        "held_back": [{"ad": n, "why": w} for n, w in held],
    }, indent=2))

    print(f"{CAMPAIGN['Campaign Name']}")
    print(f"{len(rows)} ads · {len(by_set)} ad sets · {len(seen_names)} images")
    for s, c in sorted(by_set.items()):
        print(f"   {s:38s} {c:3d} ads")
    print("   sub-avatars, which pick the copy and the page, not the audience:")
    for s, c in sorted(by_sub.items()):
        print(f"      {s:20s} {c:3d} ads   {pages['by_sub_avatar'].get(s, pages['_entry'])}")
    if held:
        print(f"\n{len(held)} pictures held back by the review — never reach the account:")
        for n, w in held:
            print(f"   {n[-46:]}  {w[:70]}")
    print(f"\nsheet:  {sheet}")
    if gaps:
        print(f"\n{len(gaps)} pictures left out, no copy for their format + sub-avatar:")
        for f, s, t, n in gaps:
            print(f"   {f:17s} {str(s):18s} {t}")
        if args.strict:
            sys.exit(2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
