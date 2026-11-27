#!/usr/bin/env python3
"""leaderboard: every creator, clipper and affiliate of one brand, ranked, with reach, payout and sales.

Normally driven by `winners.py leaderboard --brand <b>` (which pulls first, free). Directly, files only:
    leaderboard.py --brand <brand> [--root REPO]

Reads (all files; the verb makes the pulls):
  runs/creator-machine/<brand>/hub/programs.json            the brand's payout programs (the brief delivery station's);
                                                            rows with "via": "content-rewards" are the paid-per-view
                                                            campaigns: pool, state, name, report link (the link is
                                                            only used to pull; it is never written out)
  runs/winners/<brand>/campaigns.json                       the same list in the old stand-in shape, read only when
                                                            programs.json has none; `aliases` {Trybe name: [handles]}
  runs/creator-machine/<brand>/inbox/inbox.json             people[] {name, instagram, tiktok}: a Trybe creator's
                                                            public handles (local only)
  runs/content-rewards/<brand>/<pool>/<date>/clips.json     each campaign's report, newest pull: clips, views, and
                                                            each account's payout (accounts[].spendCents)
  runs/winners/<brand>/creators/<date>/trybe.json           Trybe since the program began: creator-performance per
                                                            creator + ad results (funnel-tracking's trybe.py)
  runs/winners/<brand>/creators/<date>/week/trybe.json      the same for the last 7 days
  runs/winners/<brand>/sources/<source>-<date>.json         a dated snapshot read off a dashboard with no API (kind
                                                            "snapshot", `read` date, `totals`, `top` people); the
                                                            newest per source counts in all-time, never in the week
  runs/winners/<brand>/bank.json                            which creator videos clear the creator bar

Writes runs/winners/<brand>/leaderboard.json + leaderboard.md, and leaderboard/<date>.json (that day's numbers,
which next week's move and week numbers are counted from).

One row per person. A clipper is their handle (one handle across campaigns is one person). A Trybe creator is
their public handle when the inbox has one, else first name and last initial; a Trybe creator whose handle or
name matches a clipper is the same row. A snapshot's top people are rows of their own, shown as first name and
last initial, with the snapshot's read date. Reach is clip views plus Trybe ad impressions. Paid is Content
Rewards' payout per account plus Trybe earnings plus the snapshots' payouts; the cost per 1,000 views leaves the
snapshots' payouts out (they pay for sales, not views). Sales driven is what the store
credits to the person (Trybe GMV, affiliate sales); the ads' platform purchases are a separate count and are
never added to it. Ranked by all-time reach, then paid, then sales driven; `sales_rank` ranks everyone with sales
driven. Tier: top earner (top 3 by paid or by sales driven), proven (a video clears the creator bar, or the
store credits them with sales), else rising. Someone with nothing yet is left out. Clips and payouts the
sources give no person for count in the totals under `unattributed`, never as a person.
Public handles, first names with an initial, and numbers only. Offline. Stdlib only. Exit 2 on bad input.
"""
import argparse, json, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import bank as B  # noqa: E402

DEFAULT_ROOT = paths.repo(__file__)
TOP = 3
WHOP, TRYBE = "whop", "trybe"
FIELDS = ("views", "clips", "paid", "sales_driven", "orders", "trybe_gmv", "ad_purchases", "ad_purchase_value")
COUNTS = ("views", "clips", "orders")


class BadInput(B.BadInput):
    pass


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def r2(x):
    return round(float(x or 0), 2)


def num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def shown(name):
    """A person's name as first name and last initial: public enough for a leaderboard."""
    t = [w for w in (name or "").split() if w.lower() not in ("and", "&")]
    if t and t[0].lower() == "the":     # a business or channel name, not a person's
        return " ".join(t)
    if not t:
        return "creator"
    return t[0] if len(t) == 1 else f"{t[0]} {t[-1][0].upper()}."


def cpm(paid, views):
    return r2(paid / views * 1000) if views else None


def read(p):
    return B.load_json(p) if p and Path(p).is_file() else None


# ---------- inputs ----------

def campaigns(root, brand):
    """[{pool, state, name, link}] and {norm(Trybe name): [handles]}."""
    root = Path(root)
    progs = read(root / "runs/creator-machine" / brand / "hub/programs.json") or {}
    camps = [{"pool": p["pool"], "state": p.get("state"), "name": p.get("name"), "link": p.get("report")}
             for p in progs.get("programs") or [] if p.get("via") == "content-rewards" and p.get("pool")]
    stand = read(B.brand_dir(root, brand) / "campaigns.json") or {}
    if not camps:
        camps = [dict(c, link=c.get("link") or c.get("report")) for c in stand.get("campaigns") or []]
    aliases = {norm(k): list(v) for k, v in (stand.get("aliases") or {}).items()}
    for p in (read(root / "runs/creator-machine" / brand / "inbox/inbox.json") or {}).get("people") or []:
        hs = [h for h in (p.get("tiktok"), p.get("instagram")) if h]
        if hs and p.get("name"):
            aliases.setdefault(norm(p["name"]), [])
            aliases[norm(p["name"])] += [h for h in hs if h not in aliases[norm(p["name"])]]
    return camps, aliases


def newest(ps):
    ps = sorted(ps, key=lambda p: p.parent.name if p.parent.name != "week" else p.parent.parent.name)
    return ps[-1] if ps else None


def cr_snapshot(root, brand, pool):
    return newest(list((Path(root) / "runs/content-rewards" / brand / pool).glob("*/clips.json")))


def trybe_files(root, brand):
    d = B.brand_dir(root, brand) / "creators"
    return newest(list(d.glob("*/trybe.json"))), newest(list(d.glob("*/week/trybe.json")))


def snapshots(root, brand):
    """The newest dated snapshot per source."""
    best = {}
    for f in sorted((B.brand_dir(root, brand) / "sources").glob("*.json")):
        d = read(f)
        if d and d.get("kind") == "snapshot" and d.get("source") and str(d.get("read")) >= str(best.get(d["source"], {}).get("read", "")):
            best[d["source"]] = dict(d, _path=B.rel(root, f))
    return list(best.values())


# ---------- people ----------

def blank(key, name):
    return {"key": key, "name": name, "handles": [], "platforms": [], "social": [], "campaigns": [],
            "proven_videos": [], "snapshot_read": None, "all_time": dict.fromkeys(FIELDS, 0.0), "week": dict.fromkeys(FIELDS, 0.0)}


def add(p, part, **v):
    for k, x in v.items():
        p[part][k] += x


def tag(p, field, value):
    if value and value not in p[field]:
        p[field].append(value)


def from_content_rewards(root, brand, camps, people, week_from, loose):
    """Each campaign's clips and payouts into people. Clips with no resolved account and payouts made to the
    campaign (not to an account) go into `loose`: counted in the totals, never a person."""
    out = []
    for c in camps:
        f = cr_snapshot(root, brand, c["pool"])
        if not f:
            out.append({"pool": c["pool"], "state": c.get("state"), "name": c.get("name"), "pulled": None})
            continue
        d = B.load_json(f)
        clips, accts = d.get("clips") or [], (d.get("accounts") or {}).get("accounts") or []
        for x in clips:
            acc = x.get("postingAccount") or {}
            h, v = acc.get("handle"), num(x.get("views"))
            fresh = (x.get("submittedAt") or "")[:10] >= week_from
            if not h:
                add(loose, "all_time", views=v, clips=1)
                if fresh:
                    add(loose, "week", views=v, clips=1, paid=num(x.get("spend")) / 100)
                continue
            p = people.setdefault(norm(h), blank(norm(h), "@" + h))
            tag(p, "handles", h); tag(p, "platforms", WHOP); tag(p, "social", acc.get("platform")); tag(p, "campaigns", c["pool"])
            add(p, "all_time", views=v, clips=1)
            if fresh:
                add(p, "week", views=v, clips=1, paid=num(x.get("spend")) / 100)
        for a in accts:
            k = norm(a.get("handle"))
            add(people[k] if a.get("handle") and k in people else loose, "all_time", paid=num(a.get("spendCents")) / 100)
        views, paid = sum(num(x.get("views")) for x in clips), sum(num(a.get("spendCents")) for a in accts) / 100
        out.append({"pool": c["pool"], "state": c.get("state"), "name": c.get("name") or (clips[0].get("campaignName") if clips else None),
                    "pulled": d.get("pulled"), "clips": len(clips), "views": int(views), "paid": r2(paid),
                    "cost_per_1000_views": cpm(paid, views)})
    return out


def person_for(people, name, aliases, platform):
    hs = aliases.get(norm(name)) or []
    p = next((people[norm(h)] for h in hs if norm(h) in people), None) or people.get(norm(name))
    if p is None:
        k = norm(hs[0]) if hs else norm(name)
        p = people[k] = blank(k, "@" + hs[0] if hs else shown(name))
    for h in hs:
        tag(p, "handles", h)
    tag(p, "platforms", platform)
    return p


def from_trybe(doc, people, part, aliases, won, week_from=None):
    if not doc:
        return
    for r in doc.get("rows") or []:
        p = person_for(people, r.get("creator"), aliases, TRYBE)
        new = 1 if week_from is None or (r.get("created") or "")[:10] >= week_from else 0
        add(p, part, views=num((r.get("meta") or {}).get("impressions")), clips=new)
        if part == "all_time" and r.get("trybe_id") in won:
            tag(p, "proven_videos", r["trybe_id"])
    for x in doc.get("people") or []:
        p = person_for(people, x.get("creator"), aliases, TRYBE)
        g = num(x.get("trybe_gmv"))
        add(p, part, paid=num(x.get("earnings")), trybe_gmv=g, sales_driven=g, orders=num(x.get("trybe_conversions")),
            ad_purchases=num(x.get("purchases")), ad_purchase_value=num(x.get("purchase_value")))


def from_snapshots(snaps, people, aliases, loose):
    """A snapshot's top people become rows; its totals less theirs go to `loose`. All-time only."""
    out = []
    for s in snaps:
        t, top = s.get("totals") or {}, s.get("top") or []
        for x in top:
            p = person_for(people, x.get("name"), aliases, s["source"])
            add(p, "all_time", sales_driven=num(x.get("sales")), orders=num(x.get("orders")), paid=num(x.get("paid")))
            p["snapshot_read"] = s.get("read")
        add(loose, "all_time", paid=num(t.get("paid")) - sum(num(x.get("paid")) for x in top),
            sales_driven=num(t.get("sales")) - sum(num(x.get("sales")) for x in top),
            orders=num(t.get("orders")) - sum(num(x.get("orders")) for x in top))
        out.append({"source": s["source"], "read": s.get("read"), "file": s["_path"], "note": "a dated snapshot, not live",
                    **{k: t.get(k) for k in ("sales", "orders", "paid", "ready_unpaid", "ready_unpaid_affiliates",
                                             "affiliates_enrolled") if k in t}})
    return out


# ---------- history ----------

def history(root, brand, today):
    """The leaderboard/<date>.json closest to 7 days old, between 6 and 10 days old, or None."""
    best = None
    for f in (B.brand_dir(root, brand) / "leaderboard").glob("*.json"):
        try:
            age = (today - date.fromisoformat(f.stem)).days
        except ValueError:
            continue
        if 6 <= age <= 10 and (best is None or abs(age - 7) < abs(best[0] - 7)):
            best = (age, f)
    return B.load_json(best[1]) if best else None


# ---------- build ----------

def tidy(a, not_per_view=0.0):
    """Rounded numbers plus the cost per 1,000 views, on the payouts made for views (a snapshot's affiliate payouts
    are for sales, so they are left out of that rate)."""
    out = {k: (int(round(a[k])) if k in COUNTS else r2(a[k])) for k in FIELDS}
    out["cost_per_1000_views"] = cpm(out["paid"] - not_per_view, out["views"])
    return out


def totals(rows, part, not_per_view=0.0):
    t = dict.fromkeys(FIELDS, 0.0)
    for r in rows:
        for k in FIELDS:
            t[k] += r[part][k]
    return tidy(t, not_per_view)


def build(root, brand, today=None):
    today = today or date.today()
    week_from = str(today - timedelta(days=7))
    camps, aliases = campaigns(root, brand)
    life, week = trybe_files(root, brand)
    bank_p = B.bank_path(root, brand)
    bank = B.load_bank(bank_p, brand) if bank_p.is_file() else {"bar": {}, "rows": []}
    won = {r["trybe_id"] for r in bank["rows"] if r.get("trybe_id") and r.get("state") == "winner"}
    people, loose = {}, blank("unattributed", "unattributed")
    camp_rows = from_content_rewards(root, brand, camps, people, week_from, loose)
    from_trybe(read(life), people, "all_time", aliases, won)
    from_trybe(read(week), people, "week", aliases, won, week_from)
    rest = blank("unattributed-snapshots", "unattributed")      # a snapshot's totals less its named people
    snap_rows = from_snapshots(snapshots(root, brand), people, aliases, rest)
    rows = [r for r in people.values() if any(r["all_time"].values()) or any(r["week"].values())]
    prev = history(root, brand, today)
    before = {p["key"]: p for p in (prev or {}).get("people", [])}
    if prev:   # a week-old leaderboard: the week is the change since it, for every number
        for r in rows + [loose]:
            b = (before.get(r["key"]) or (prev if r is loose else {}).get("unattributed") or {}).get("all_time") or {}
            r["week"] = {k: max(0.0, r["all_time"][k] - num(b.get(k))) for k in FIELDS}
    rows.sort(key=lambda r: (-r["all_time"]["views"], -r["all_time"]["paid"], -r["all_time"]["sales_driven"], r["name"]))
    top_paid = [r["key"] for r in sorted(rows, key=lambda r: -r["all_time"]["paid"]) if r["all_time"]["paid"] > 0][:TOP]
    sellers = [r for r in sorted(rows, key=lambda r: -r["all_time"]["sales_driven"]) if r["all_time"]["sales_driven"] > 0]
    sales_rank = {r["key"]: i for i, r in enumerate(sellers, 1)}
    for i, r in enumerate(rows, 1):
        r["rank"], r["sales_rank"] = i, sales_rank.get(r["key"])
        was = before.get(r["key"], {}).get("rank")
        r["move"] = (was - i) if was else None
        r["tier"] = ("top earner" if r["key"] in top_paid or (r["sales_rank"] or TOP + 1) <= TOP else
                     "proven" if r["proven_videos"] or r["all_time"]["sales_driven"] > 0 else "rising")
        r["all_time"], r["week"] = tidy(r["all_time"]), tidy(r["week"])
    snap_paid = sum(num(s.get("paid")) for s in snap_rows)
    t_all, t_week = totals(rows + [loose, rest], "all_time", snap_paid), totals(rows + [loose], "week")
    platforms = sorted({pl for r in rows for pl in r["platforms"]})
    keep = ("rank", "sales_rank", "move", "tier", "name", "handles", "platforms", "social", "campaigns", "proven_videos",
            "snapshot_read", "all_time", "week", "key")
    return {"brand": brand, "made": datetime.now().isoformat(timespec="seconds"), "status": "draft",
            "as_of": str(today), "updated": str(today),
            "week": {"from": week_from, "to": str(today),
                     "basis": (f"change since the leaderboard of {prev['as_of']}" if prev else
                               "first week: clips posted in the last 7 days; Trybe's last 7 days")},
            "creator_bar": bank.get("creator_bar") or bank.get("bar"),
            "sources": {"campaigns": camp_rows, "snapshots": snap_rows,
                        "trybe": {"all_time": B.rel(root, life) if life else None, "week": B.rel(root, week) if week else None}},
            "totals": {"views": t_all["views"], "clips": t_all["clips"], "paid": t_all["paid"],
                       "sales_driven": t_all["sales_driven"], "cost_per_1000_views": t_all["cost_per_1000_views"],
                       "earning_this_week": sum(1 for r in rows if r["week"]["paid"] > 0),
                       "people": len(rows), "all_time": t_all, "week": t_week,
                       "by_platform": {pl: totals([r for r in rows if pl in r["platforms"]] + ([loose] if pl == WHOP else [])
                                                  + ([rest] if pl in {x["source"] for x in snap_rows} else []), "all_time",
                                                  snap_paid if pl in {x["source"] for x in snap_rows} else 0.0)
                                       for pl in platforms}},
            "unattributed": {part: dict(totals([loose, rest] if part == "all_time" else [loose], part),
                                        cost_per_1000_views=None) for part in ("all_time", "week")},
            "people": [{k: r[k] for k in keep} for r in rows],
            "creators": [{"rank": r["rank"], "sales_rank": r["sales_rank"], "handle": r["name"],
                          "platform": " + ".join(r["platforms"]), "views": r["all_time"]["views"], "paid": r["all_time"]["paid"],
                          "sales_driven": r["all_time"]["sales_driven"], "tier": r["tier"],
                          "move": "new" if r["move"] is None else r["move"], "snapshot_read": r["snapshot_read"]}
                         for r in rows]}


def money(x):
    return "—" if x is None else f"${x:,.0f}"


def render(d):
    a, w = d["totals"]["all_time"], d["totals"]["week"]
    out = [f"# Creator leaderboard — {d['brand']} — {d['as_of']}", "",
           "| | Reach (views) | Clips / videos | Paid out | Cost per 1,000 views | Sales driven (store) | Ad purchases (platform) |",
           "|---|---|---|---|---|---|---|"]
    for label, t in (("All-time", a), ("This week", w)):
        out.append(f"| {label} | {t['views']:,} | {t['clips']:,} | {money(t['paid'])} | "
                   f"{'—' if t['cost_per_1000_views'] is None else '$%.2f' % t['cost_per_1000_views']} | "
                   f"{money(t['sales_driven'])} ({t['orders']:,} orders) | {t['ad_purchases']:g} (${t['ad_purchase_value']:,.0f}) |")
    u = d["unattributed"]["all_time"]
    out += ["", f"Week: {d['week']['basis']}."]
    for s in d["sources"]["snapshots"]:
        out.append(f"{s['source']}: a snapshot read {s['read']}, not live — {money(s.get('sales'))} sales from "
                   f"{s.get('orders') or 0:,} orders, {money(s.get('paid'))} paid out.")
    out += [f"Totals include {u['views']:,} views, {u['clips']} clips, {money(u['paid'])} paid and {money(u['sales_driven'])} "
            "sales the sources give no named person for.", "",
            "| Rank | Move | Who | Tier | Where | Views | Paid | Sales driven | Views this week |", "|---|---|---|---|---|---|---|---|---|"]
    for p in d["people"]:
        mv = "new" if p["move"] is None else ("▲%d" % p["move"] if p["move"] > 0 else "▼%d" % -p["move"] if p["move"] < 0 else "—")
        where = " + ".join(p["platforms"]) + (f" (snapshot {p['snapshot_read']})" if p["snapshot_read"] else "")
        out.append(f"| {p['rank']} | {mv} | {p['name']} | {p['tier']} | {where} | {p['all_time']['views']:,} | "
                   f"{money(p['all_time']['paid'])} | {money(p['all_time']['sales_driven'])} | {p['week']['views']:,} |")
    return "\n".join(out) + "\n"


def write(root, brand, today=None):
    d = build(root, brand, today)
    home = B.brand_dir(root, brand)
    (home / "leaderboard").mkdir(parents=True, exist_ok=True)
    text = json.dumps(d, indent=1, ensure_ascii=False) + "\n"
    (home / "leaderboard.json").write_text(text)
    (home / "leaderboard" / f"{d['as_of']}.json").write_text(text)
    (home / "leaderboard.md").write_text(render(d))
    return home / "leaderboard.json", d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    a = ap.parse_args(argv)
    try:
        out, d = write(Path(a.root), a.brand)
    except B.BadInput as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    t = d["totals"]["all_time"]
    print(f"{a.brand}: {d['totals']['people']} people, {t['views']:,} views, ${t['paid']:,.2f} paid, "
          f"${t['sales_driven']:,.2f} sales driven -> {B.rel(Path(a.root), out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
