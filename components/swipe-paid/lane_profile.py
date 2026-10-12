#!/usr/bin/env python3
"""Synopsis, copy blocks and pages for the lanes that never had them.

    python3 lane_profile.py            all non-paid lanes
    python3 lane_profile.py own

The competitor lane has had a synopsis, a record per copy block and a
page record per landing page since it was built. Our own ads and the organic
room had none of it — they were a list. This writes the same three things for
them, from the corpus, so every lane reads alike.

What differs is only what each lane can honestly answer:

    own       ranked by SPEND. We know what ours earned; that is the whole
              reason to hold them next to someone else's.
    organic   ranked by how much of the room one creator accounts for. There
              is no spend and no landing page — pretending otherwise would put
              an empty column next to a real one.

Writes <lane>/<source>/PROFILE.md, blocks/NN_<slug>.md and (own only)
_pages/<slug>.md. Regenerated every run; nothing here is hand-kept.
"""
import collections, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "swipe.db")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "naming"))
import names as N


def q(sql, args=()):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def money(n):
    return f"${n:,.0f}" if n else "—"


def bar(part, whole, width=28):
    n = int(round(width * part / whole)) if whole else 0
    return "█" * n + "·" * (width - n)


# ------------------------------------------------------------------- own ---
def profile_own(source):
    ads = q("SELECT * FROM creatives WHERE lane='own' AND source=?", (source,))
    groups = q("""SELECT group_slug, group_label, COUNT(*) n,
                         ROUND(SUM(COALESCE(spend,0))) spend,
                         ROUND(SUM(COALESCE(revenue,0))) revenue,
                         SUM(COALESCE(impressions,0)) imps,
                         SUM(known='named') named
                  FROM creatives WHERE lane='own' AND source=?
                  GROUP BY group_slug ORDER BY spend DESC, n DESC""", (source,))
    spend = sum(a["spend"] or 0 for a in ads)
    rev = sum(a["revenue"] or 0 for a in ads)
    named = sum(a["known"] == "named" for a in ads)
    live = [g for g in groups if g["spend"]]
    top3 = sum(g["spend"] for g in groups[:3])
    # The corpus keeps `url` as the ad's preview link — where WE go to look at
    # it. The landing page is where the CUSTOMER goes, and it only exists in
    # the lane file, so read it from there rather than reporting the wrong one.
    lane_file = os.path.join(HERE, "own", source, "ads.json")
    lps = collections.Counter(
        a["landing_page"].split("?")[0]
        for a in (json.load(open(lane_file))["ads"] if os.path.isfile(lane_file) else [])
        if a.get("landing_page"))

    out = [f"# Our account — {source}\n",
           "**Lane:** ours · **Source:** the ecom_data_sync Supabase tables "
           "(`meta_ads` + `meta_ad_insights`) · regenerated, never hand-kept\n",
           "| | |", "|---|---|",
           f"| Ads held | **{len(ads):,}** |",
           f"| Copy blocks | **{len(groups)}** |",
           f"| Blocks that actually spent | **{len(live)}** |",
           f"| Spend in window | **{money(spend)}** |",
           f"| Revenue attributed | **{money(rev)}** |",
           f"| Blended ROAS | **{rev/spend:.2f}×** |" if spend else "| Blended ROAS | — |",
           f"| Named to the convention | **{named} of {len(ads)}** "
           f"({named/max(1,len(ads)):.0%}) |",
           f"| Landing pages used | **{len(lps)}** |", ""]

    out += ["## What the account is actually betting on\n",
            f"Three blocks carry **{top3/spend:.0%}** of the spend."
            if spend else "Nothing in this window carried spend.\n", ""]
    out += ["| # | Spend | Ads | Copy block | ROAS |", "|---:|---:|---:|---|---:|"]
    for i, g in enumerate(groups[:12], 1):
        roas = f"{g['revenue']/g['spend']:.2f}×" if g["spend"] else "—"
        out.append(f"| {i:02d} | {money(g['spend'])} | {g['n']} | "
                   f"{(g['group_label'] or '')[:78]} | {roas} |")

    out += ["", "## The long tail\n",
            f"{len(groups) - len(live)} of {len(groups)} blocks spent nothing in "
            f"this window — written, uploaded, and never given budget. That is "
            f"the cost of the account nobody sees.\n"]

    if named == 0:
        out += ["## Nothing here is joinable yet\n",
                "Not one ad in this window carries a convention name, so no row "
                "in a Meta export can be traced back to the brief, the angle or "
                "the swipe that produced it. Every ad delivered from now on is "
                "named at the gate; this number is the one to watch.\n"]

    # The funnel, with what it cost to send traffic at it. A page with ads and
    # no spend is a funnel we stopped feeding — worth seeing next to one we did.
    caps_f = os.path.join(HERE, "own", source, "pages.json")
    caps = json.load(open(caps_f)) if os.path.isfile(caps_f) else {}
    bykey = {re.sub(r"^https?://(www\.)?", "", (c.get("url") or "")).rstrip("/"): (sl, c)
             for sl, c in caps.items()}
    lp_spend = collections.defaultdict(float)
    for a in (json.load(open(lane_file))["ads"] if os.path.isfile(lane_file) else []):
        u = (a.get("landing_page") or "").split("?")[0]
        if u:
            lp_spend[re.sub(r"^https?://(www\.)?", "", u).rstrip("/")] += a.get("spend") or 0

    out += ["## The funnel, captured\n",
            "| Page | Type | Height | Ads | Spend behind it |",
            "|---|---|---:|---:|---:|"]
    for u, n in lps.most_common(20):
        k = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
        sl, c = bykey.get(k, (None, {}))
        out.append(f"| `{k[:62]}` | {c.get('type', 'uncaptured')} | "
                   f"{c.get('height', '—')} | {n} | {money(lp_spend.get(k, 0))} |")
    dead = [u for u, n in lps.items()
            if not lp_spend.get(re.sub(r"^https?://(www\.)?", "", u).rstrip("/"))]
    if dead:
        out += ["", f"{len(dead)} of {len(lps)} pages have ads pointing at them and "
                f"no spend in this window — funnels we stopped feeding, still "
                f"wired to live ads.\n"]
    return "\n".join(out) + "\n", groups


# --------------------------------------------------------------- organic ---
def profile_organic(source):
    items = q("SELECT * FROM creatives WHERE lane='organic' AND source=?", (source,))
    groups = q("""SELECT group_slug, group_label, COUNT(*) n
                  FROM creatives WHERE lane='organic' AND source=?
                  GROUP BY group_slug ORDER BY n DESC""", (source,))
    plats = collections.Counter(
        (g["group_slug"].split("-")[0] for g in groups for _ in range(g["n"])))
    withcover = sum(1 for i in items if i["thumb"])
    top10 = sum(g["n"] for g in groups[:10])

    out = [f"# The room — {source.replace('--', ' · ')}\n",
           "**Lane:** organic · **Source:** `swipe-organic/records/avatar-feeds/` "
           "· regenerated, never hand-kept\n",
           "| | |", "|---|---|",
           f"| Posts held | **{len(items):,}** |",
           f"| Creators | **{len(groups)}** |",
           f"| Platforms | **{', '.join(f'{k} {v}' for k, v in plats.most_common())}** |",
           f"| Posts with a cover we can still show | **{withcover:,}** |",
           f"| Share carried by the top 10 creators | **{top10/max(1,len(items)):.0%}** |",
           "",
           "## Who the room is\n",
           "No spend and no landing pages here — nobody paid to put these in "
           "front of anyone. What ranks a creator is how much of the feed they "
           "account for, which is the closest organic gets to conviction.\n",
           "| # | Creator | Posts | Share |", "|---:|---|---:|---|"]
    for i, g in enumerate(groups[:20], 1):
        out.append(f"| {i:02d} | {g['group_label']} | {g['n']} | "
                   f"`{bar(g['n'], groups[0]['n'], 18)}` |")

    tail = [g for g in groups if g["n"] == 1]
    out += ["", f"{len(tail)} creators appear exactly once. A room is mostly "
            f"strangers — the recurring names above are the ones worth a "
            f"profile.\n"]
    return "\n".join(out) + "\n", groups


def write_pages(lane, source, root):
    """_PAGE.md, filled. Whatever a creative actually sends you to.

    For us that is a funnel page, captured. For organic it is the creator's
    account — a post sends you nowhere else, and calling that "no pages" would
    be tidier than it is true.
    """
    d = os.path.join(root, "_pages")
    os.makedirs(d, exist_ok=True)
    if lane == "own":
        f = os.path.join(root, "pages.json")
        if not os.path.isfile(f):
            return 0
        caps = json.load(open(f))
        ads = json.load(open(os.path.join(root, "ads.json")))["ads"]
        n, sp, blocks = collections.Counter(), collections.defaultdict(float), collections.defaultdict(set)
        for a in ads:
            u = (a.get("landing_page") or "").split("?")[0]
            if not u:
                continue
            k = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
            n[k] += 1; sp[k] += a.get("spend") or 0
            blocks[k].add(norm_label(a.get("body") or a.get("title")))
        for slug, c in caps.items():
            k = re.sub(r"^https?://(www\.)?", "", c.get("url", "")).rstrip("/")
            body = [f"# {slug}\n",
                    f"**Type:** {c.get('type', 'unknown')}",
                    f"**URL:** {c.get('url','')}",
                    f"**Page height:** {c.get('height','?')}px",
                    f"**Copy blocks served:** {len(blocks.get(k, []))}",
                    f"**Ads pointing here:** {n.get(k, 0)}",
                    f"**Spend behind it:** {money(sp.get(k, 0))}",
                    f"**Capture:** `own/{source}/_pages/{slug}/`", "",
                    "## Copy blocks that land here\n"]
            for b in sorted(blocks.get(k, []))[:12]:
                body.append(f"- {b[:110] or '*no body copy*'}")
            body += ["", "## Media\n",
                     "- `page.png` — full-page mobile capture (390x844 @2x)",
                     "- `page.html` — rendered DOM at capture time",
                     "- `page.txt` — extracted visible text"]
            open(os.path.join(d, f"{slug}.md"), "w").write("\n".join(body) + "\n")
        return len(caps)

    # organic: the creator account is the destination
    rows = q("""SELECT group_slug, group_label, COUNT(*) n,
                       MIN(url) one_url, SUM(thumb IS NOT NULL) withcover
                FROM creatives WHERE lane='organic' AND source=?
                GROUP BY group_slug ORDER BY n DESC""", (source,))
    for r in rows[:60]:
        plat = r["group_slug"].split("-")[0]
        handle = (r["group_label"] or "").split(" · ")[0]
        prof = {"instagram": f"https://instagram.com/{handle.lstrip('@')}",
                "tiktok": f"https://tiktok.com/@{handle.lstrip('@')}",
                "youtube": f"https://youtube.com/@{handle.lstrip('@')}"}.get(plat, "")
        posts = q("""SELECT title, url FROM creatives
                     WHERE lane='organic' AND source=? AND group_slug=?
                     ORDER BY posted DESC LIMIT 8""", (source, r["group_slug"]))
        body = [f"# {handle}\n",
                f"**Type:** creator account · {plat}",
                f"**URL:** {prof or r['one_url'] or ''}",
                f"**Posts held:** {r['n']}",
                f"**Posts with a cover we can still show:** {r['withcover']}", "",
                "## What lands here\n"]
        for pst in posts:
            body.append(f"- [{(pst['title'] or '*no caption*')[:100]}]({pst['url']})")
        open(os.path.join(d, f"{r['group_slug'][:60]}.md"), "w").write(
            "\n".join(body) + "\n")
    return min(len(rows), 60)


def norm_label(t):
    return re.sub(r"\s+", " ", (t or "")).strip()[:400]


# ------------------------------------------------- the standard records ---
# Every source fills the same records in the same order, whatever lane it is
# in — the folder rule is "same headings, same order, same fields". What
# changes between lanes is only the words for the same slot: a competitor's
# "landing page" is our "funnel page" and organic's "creator account", because
# that is where each one actually sends you.
LANE_WORDS = {
    "paid":    dict(unit="copy block", dest="landing page", who="brand"),
    "own":     dict(unit="copy block", dest="funnel page",  who="account"),
    "organic": dict(unit="creator",    dest="creator account", who="room"),
}


def write_block_records(lane, source, groups, root, extra=None):
    """_BLOCK.md, filled. One per unit — a copy block, or a creator."""
    w = LANE_WORDS[lane]
    d = os.path.join(root, "blocks")
    os.makedirs(d, exist_ok=True)
    total = len(groups)
    for i, g in enumerate(groups[:60], 1):
        rows = q("""SELECT swipe_id, ref, title, body, spend, revenue, impressions,
                           media, ratio, url, known, verdict, thumb
                    FROM creatives WHERE lane=? AND source=? AND group_slug=?
                    ORDER BY COALESCE(spend,0) DESC, ref DESC""",
                 (lane, source, g["group_slug"]))
        vids = sum(r["media"] == "video" for r in rows)
        spend = g.get("spend") or 0
        rev = g.get("revenue") or 0
        dest = collections.Counter(
            (e or "").split("?")[0] for e in (extra or {}).get(g["group_slug"], []))
        body = [f"# {i:02d} · {(g['group_label'] or 'no label')[:110]}\n",
                f"**{g['n']} live creatives** — {vids} video, {g['n']-vids} image"]
        if lane == "own":
            body += [f"**Spend:** {money(spend)} · **Revenue:** {money(rev)} · "
                     f"**ROAS:** {rev/spend:.2f}×" if spend else
                     "**Spend:** — (never funded)"]
        body += [f"**{w['dest'].title()}:** " +
                 (f"`{list(dest)[0][:90]}`" if dest else "`—`"),
                 f"**Rank:** {i:02d} of {total} by "
                 + ("spend" if lane == "own" else "share of the room"), ""]
        if lane == "own":
            full = max((r["body"] or "" for r in rows), key=len, default="")
            body += ["## The copy, verbatim\n", "> " +
                     (full.replace("\n", "\n> ") or "*no body copy*"), ""]
        else:
            body += ["## What they post\n"]
            for r in rows[:6]:
                body.append(f"- {(r['title'] or '').strip()[:110] or '*no caption*'}")
            body.append("")
        body += ["## The creatives\n",
                 "| swipe id | " + ("spend | ROAS | " if lane == "own" else "")
                 + "media | where |",
                 "|---|" + ("---:|---:|" if lane == "own" else "") + "---|---|"]
        for r in rows[:40]:
            perf = ""
            if lane == "own":
                roas = f"{r['revenue']/r['spend']:.2f}×" if r["spend"] else "—"
                perf = f" {money(r['spend'] or 0)} | {roas} |"
            link = f"[open]({r['url']})" if r["url"] else "—"
            body.append(f"| `{r['swipe_id']}` |{perf} {r['media']} | {link} |")
        if len(rows) > 40:
            body.append(f"\n… and {len(rows)-40} more.")
        open(os.path.join(d, f"{i:02d}_{g['group_slug'][:60]}.md"), "w").write(
            "\n".join(body) + "\n")
    return min(total, 60)


def write_brand_record(lane, source, stats, root):
    """_BRAND.md, filled — the counts card every source carries."""
    w = LANE_WORDS[lane]
    lines = [f"# {stats['title']}\n",
             f"**Lane:** {lane} · **{w['who'].title()}:** `{source}`",
             f"**Source:** {stats['origin']}",
             f"**Pulled:** {stats['pulled']}", "",
             "## Counts\n", "| | |", "|---|---|"]
    for k, v in stats["counts"]:
        lines.append(f"| {k} | **{v}** |")
    for head in ("what", "offer", "stack", "caveat"):
        if stats.get(head):
            lines += ["", f"## {stats[head][0]}\n", stats[head][1]]
    open(os.path.join(root, "_BRAND.md"), "w").write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- blocks ---
def write_blocks(lane, source, groups, root):
    d = os.path.join(root, "blocks")
    os.makedirs(d, exist_ok=True)
    for i, g in enumerate(groups[:60], 1):
        rows = q("""SELECT swipe_id, title, ref, spend, revenue, impressions,
                           media, ratio, url, known, verdict
                    FROM creatives WHERE lane=? AND source=? AND group_slug=?
                    ORDER BY COALESCE(spend,0) DESC LIMIT 40""",
                 (lane, source, g["group_slug"]))
        spend = g.get("spend") or 0
        body = [f"# {i:02d} — {(g['group_label'] or 'no label')[:100]}\n",
                f"`{g['n']} creatives`"
                + (f" · `{money(spend)} spent`" if spend else "") + "\n"]
        if lane == "own":
            body += ["## The copy, as it ran\n", "> " +
                     (g["group_label"] or "*no body copy*") + "\n"]
        body += ["## The creatives\n",
                 "| id | " + ("spend | ROAS | " if lane == "own" else "")
                 + "media | what it is |",
                 "|---|" + ("---:|---:|" if lane == "own" else "") + "---|---|"]
        for r in rows:
            perf = ""
            if lane == "own":
                roas = f"{r['revenue']/r['spend']:.2f}×" if r["spend"] else "—"
                perf = f" {money(r['spend'] or 0)} | {roas} |"
            body.append(f"| `{r['swipe_id']}` |{perf} {r['media']} | "
                        f"{(r['title'] or '')[:60]} |")
        open(os.path.join(d, f"{i:02d}_{g['group_slug'][:60]}.md"), "w").write(
            "\n".join(body) + "\n")
    return min(len(groups), 60)


def own_stats(source, ads, groups, lps):
    spend = sum(a["spend"] or 0 for a in ads)
    rev = sum(a["revenue"] or 0 for a in ads)
    named = sum(a["known"] == "named" for a in ads)
    live = [g for g in groups if g["spend"]]
    vids = sum(a["media"] == "video" for a in ads)
    return {
        "title": f"Our account — {source}",
        "origin": "the ecom_data_sync Supabase tables (`meta_ads` + "
                  "`meta_ad_insights`), which the sync repo refreshes on a schedule",
        "pulled": "regenerated from the corpus, never hand-kept",
        "counts": [("Ads held", f"{len(ads):,}"),
                   ("Distinct copy blocks", len(groups)),
                   ("Blocks that ever spent", len(live)),
                   ("Video creatives", f"{vids:,}"),
                   ("Static creatives", f"{len(ads)-vids:,}"),
                   ("Spend in window", money(spend)),
                   ("Revenue attributed", money(rev)),
                   ("Blended ROAS", f"{rev/spend:.2f}×" if spend else "—"),
                   ("Named to the convention", f"{named} of {len(ads)} "
                    f"({named/max(1,len(ads)):.0%})"),
                   ("Funnel pages used", len(lps))],
        "what": ("What we sell",
                 "One catalogue, two products, two voices: the **Glow Body "
                 "Scrub** (turmeric, centella, ginger, sea salt, shea) and the "
                 "**face scrub**. Every body-scrub block speaks as a named woman "
                 "in her sixties; every face-scrub block speaks as a young woman "
                 "at a rooftop bar. They share an account and nothing else."),
        "offer": ("Offer mechanics",
                  "A 60-day risk-free trial is the standing risk reversal, quoted "
                  "inside the ad copy itself rather than held back for the page. "
                  "Discount codes run as their own destination (`/discount/MOM25`) "
                  "rather than as a line in the offer."),
        "stack": ("Where the traffic goes",
                  "Two hosts, and they are not equivalent. `try.brand-a.com` "
                  "serves the advertorials; `brand-a.com/catalogue` serves the "
                  "product pages. The money goes to the first."),
        "caveat": ("Capture caveat",
                   "Spend, revenue and impressions are the sync window only — an "
                   "ad with no row in that window reads as unfunded here, not as "
                   "never funded. Revenue is Meta-attributed, so it is the "
                   "platform's number, not the ledger's."),
    }


def organic_stats(source, items, groups):
    plats = collections.Counter(g["group_slug"].split("-")[0]
                                for g in groups for _ in range(g["n"]))
    once = sum(1 for g in groups if g["n"] == 1)
    top10 = sum(g["n"] for g in groups[:10])
    return {
        "title": f"The room — {source.replace('--', ' · ')}",
        "origin": "`swipe-organic/records/avatar-feeds/` — posts harvested from "
                  "the feeds the avatar actually watches",
        "pulled": "regenerated from the corpus, never hand-kept",
        "counts": [("Posts held", f"{len(items):,}"),
                   ("Creators", len(groups)),
                   ("Creators seen exactly once", once),
                   ("Share carried by the top 10", f"{top10/max(1,len(items)):.0%}"),
                   ("Platforms", ", ".join(f"{k} {v}" for k, v in plats.most_common())),
                   ("Posts with a usable cover",
                    f"{sum(1 for i in items if i['thumb']):,}")],
        "what": ("What this room is",
                 "Nobody paid to put any of this in front of anyone, so there is "
                 "no spend column and there never will be. What ranks a creator "
                 "here is how much of the feed they account for — the closest "
                 "organic gets to conviction."),
        "caveat": ("Capture caveat",
                   "Covers are hotlink-protected and time-limited. Instagram and "
                   "YouTube survive; **TikTok signatures expire within days**, so "
                   "an older TikTok row has a dead cover and the post itself is "
                   "the only way to see it."),
    }


def run(lane_filter=None):
    for lane in ("own", "organic"):
        if lane_filter and lane != lane_filter:
            continue
        for s in q("SELECT source FROM sources WHERE lane=?", (lane,)):
            src = s["source"]
            root = os.path.join(HERE, lane, src)
            os.makedirs(root, exist_ok=True)
            if lane == "own":
                text, groups = profile_own(src)
                ads = q("SELECT * FROM creatives WHERE lane='own' AND source=?", (src,))
                lane_file = os.path.join(root, "ads.json")
                raw = json.load(open(lane_file))["ads"] if os.path.isfile(lane_file) else []
                lps = {(a.get("landing_page") or "").split("?")[0] for a in raw
                       if a.get("landing_page")}
                extra = collections.defaultdict(list)
                for a in raw:
                    extra[f"{0:02d}"]  # touch
                stats = own_stats(src, ads, groups, lps)
                dest = collections.defaultdict(list)
                for r in q("SELECT group_slug FROM creatives WHERE lane='own' AND source=?", (src,)):
                    pass
                by_block = collections.defaultdict(list)
                for a in raw:
                    by_block[norm_label(a.get("body") or a.get("title"))].append(
                        a.get("landing_page"))
                extra = {g["group_slug"]: by_block.get(
                    norm_label(g["group_label"]) if g["group_label"] != "— no body copy —" else "", [])
                    for g in groups}
            else:
                text, groups = profile_organic(src)
                items = q("SELECT * FROM creatives WHERE lane='organic' AND source=?", (src,))
                stats = organic_stats(src, items, groups)
                extra = None
            open(os.path.join(root, "PROFILE.md"), "w").write(text)
            write_brand_record(lane, src, stats, root)
            n = write_block_records(lane, src, groups, root, extra)
            pg = write_pages(lane, src, root)
            print(f"  {lane:<8} {src:<22} _BRAND.md · PROFILE.md · "
                  f"{n} blocks · {pg} pages")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
