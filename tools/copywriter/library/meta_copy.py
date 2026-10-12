#!/usr/bin/env python3
"""Our own best Meta ads' words — the first swipes for ad copy. Narrow by design.

    python3 library/meta_copy.py --brand brand-b              the pull (resumes a part-done day)
    python3 library/meta_copy.py --brand brand-b --dry-run    the calls it would make, none made

the owner, 2 Oct 2026: "we're going to pull in the actual copy that exists in the ad account
for brand-b so we can use those as the initial swipes" — and, after a full-account sweep
used 99% of the app's Meta budget: "never pull that much … we need to be specific so we
don't waste credits or trigger red flags." Then: "top 25 by spend and top 25 by lowest
CPA, that's it."

Exactly that, and nothing more:
  1. top 25 ads by lifetime spend                        one insights call, 25 rows
  2. top 25 by lowest CPA among ads that spent at least
     --cpa-min-spend and bought at least --cpa-min-buys   insights filtered to spend over the
                                                          floor, at most --cpa-pages pages
  3. the words of those <=50 ads                         one small call per ad
Every step is saved the moment it lands (insights.json, words.json) and is never asked
again on a rerun the same day. Every reply's usage header is read; at 75% the pull stops,
keeps what it has, and says so. Read-only.

Writes runs/copywriter/<brand>/meta-copy/<date>/: insights.json, words.json and copy.json:
`ads` (one row per ad: why it is in — spend / cpa / both — its numbers, words and media) and,
de-duplicated (the owner: "I don't need duplicates … we can know that it was duplicated, but I just
need to see what the actual thing was"), `copy` — one row per distinct text in each slot — and
`creative` — one row per distinct video or image — each naming every ad that ran it and adding
up their numbers. The list can end up shorter than 50; that is the point.
"""
import argparse, json, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.insert(0, str(WS / "components/meta-upload"))

TOP = 25
STOP_AT = 75                      # percent, on any Meta usage meter
PURCHASE = ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase")
INSIGHT_FIELDS = "ad_id,ad_name,spend,actions,action_values"
CREATIVE = ("creative{body,title,object_type,video_id,image_hash,thumbnail_url,"
            "asset_feed_spec{bodies,titles,descriptions,videos{video_id},images{hash}},"
            "object_story_spec{link_data{message,name,description,image_hash},"
            "video_data{message,title,link_description,video_id,image_hash}}}")
METERS = ("call_count", "total_cputime", "total_time", "acc_id_util_pct")


class Stop(Exception):
    pass


def out_dir(brand, day=None):
    return WS / "runs" / "copywriter" / brand / "meta-copy" / (day or date.today().isoformat())


def latest(brand):
    base = WS / "runs" / "copywriter" / brand / "meta-copy"
    runs = sorted(base.glob("*/copy.json")) if base.is_dir() else []
    return runs[-1] if runs else None


def usage(headers):
    """The highest percentage on any of Meta's usage meters in a reply's headers."""
    top = 0.0
    for h in ("x-business-use-case-usage", "x-ad-account-usage", "x-app-usage"):
        try:
            stack = [json.loads(headers.get(h) or "null")]
        except ValueError:
            continue
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in METERS and isinstance(v, (int, float)):
                        top = max(top, float(v))
                    elif isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(x, list):
                stack += x
    return top


class Door:
    """GET only, one call at a time, a pause between, every reply's meter read."""

    def __init__(self, brand, say=print, opener=None, tok=None, account=None):
        from meta import BASE
        self.base, self.say, self.calls, self.peak = BASE, say, 0, 0.0
        if account is None:
            from brand import Brand
            from meta import token
            b = Brand(brand)
            account, tok = b.account_id, token(b.token_key)
        self.account, self.tok = account, tok
        self.open = opener or (lambda req: urllib.request.urlopen(req, timeout=120))

    def get(self, path, **params):
        if self.peak >= STOP_AT:
            raise Stop(f"Meta usage at {self.peak:.0f}%, stopped before call {self.calls + 1}")
        params["access_token"] = self.tok
        req = urllib.request.Request(f"{self.base}/{path.lstrip('/')}?{urllib.parse.urlencode(params)}")
        try:
            with self.open(req) as r:
                body, headers = r.read(), r.headers
        except urllib.error.HTTPError as e:
            raise Stop(f"Meta {e.code}: {e.read().decode('utf8', 'replace')[:400]}")
        self.calls += 1
        self.peak = max(self.peak, usage(headers))
        time.sleep(1)
        return json.loads(body or b"{}")


def bought(actions, kinds=PURCHASE):
    got = {a.get("action_type"): float(a.get("value") or 0) for a in actions or []}
    return next((got[k] for k in kinds if k in got), 0.0)


def row(r):
    spend, buys, value = float(r.get("spend") or 0), bought(r.get("actions")), bought(r.get("action_values"))
    return {"ad_id": r["ad_id"], "ad_name": r.get("ad_name"), "spend": round(spend, 2), "purchases": buys,
            "value": round(value, 2), "cpa": round(spend / buys, 2) if buys else None,
            "roas": round(value / spend, 2) if spend else None}


def pick(top_spend, cpa_pool, min_buys):
    """The <=50 ads, each with why it is in."""
    by_cpa = sorted((r for r in cpa_pool if r["purchases"] >= min_buys and r["cpa"]), key=lambda r: r["cpa"])[:TOP]
    why = {}
    for r in top_spend[:TOP]:
        why[r["ad_id"]] = {"spend"}
    for r in by_cpa:
        why.setdefault(r["ad_id"], set()).add("cpa")
    rows = {r["ad_id"]: r for r in list(cpa_pool) + list(top_spend)}
    return [dict(rows[a], why=sorted(w)) for a, w in why.items()]


def words_of(cr):
    cr = cr or {}
    afs, oss = cr.get("asset_feed_spec") or {}, cr.get("object_story_spec") or {}
    ld, vd = oss.get("link_data") or {}, oss.get("video_data") or {}
    clean = lambda xs: list(dict.fromkeys(x.strip() for x in xs if x and x.strip()))
    return {"primary": clean([b.get("text") for b in afs.get("bodies") or []] + [cr.get("body"), ld.get("message"), vd.get("message")]),
            "headlines": clean([t.get("text") for t in afs.get("titles") or []] + [cr.get("title"), ld.get("name"), vd.get("title")]),
            "descriptions": clean([d.get("text") for d in afs.get("descriptions") or []] + [ld.get("description"), vd.get("link_description")]),
            "object_type": cr.get("object_type"), "thumbnail": cr.get("thumbnail_url"),
            "media": clean([f"video:{v.get('video_id')}" for v in afs.get("videos") or [] if v.get("video_id")]
                           + [f"image:{i.get('hash')}" for i in afs.get("images") or [] if i.get("hash")]
                           + [f"video:{x}" for x in (cr.get("video_id"), vd.get("video_id")) if x]
                           + [f"image:{x}" for x in (cr.get("image_hash"), ld.get("image_hash")) if x]
                           + ([f"image:{vd.get('image_hash')}"] if vd.get("image_hash") and not vd.get("video_id") else []))}


def norm(s):
    """Two texts are the same text when they differ only in spacing, case or punctuation."""
    import re
    return re.sub(r"[^a-z0-9$%]+", " ", (s or "").lower()).strip()


def index(ads):
    """The best assets, each once. Copy: one row per distinct text in each slot. Creative: one row
    per distinct video or image. Each row: the thing, every ad that ran it (the duplicates, named,
    not repeated), why it is in, and its numbers added up across those ads."""
    def blank(**k):
        return dict(k, ads=[], why=set(), spend=0.0, purchases=0.0, value=0.0)
    copy, creative = {}, {}
    for a in ads:
        for slot in ("primary", "headlines", "descriptions"):
            for txt in a.get(slot) or []:
                g = copy.setdefault((slot, norm(txt)), blank(slot=slot, text=txt))
                add(g, a)
                g.setdefault("creatives", set()).update(a.get("media") or [])
        for m in a.get("media") or []:
            g = creative.setdefault(m, blank(media=m, kind=m.split(":")[0], thumbnail=a.get("thumbnail")))
            add(g, a)
            for slot in ("primary", "headlines"):
                g.setdefault(slot, {}).update({norm(x): x for x in a.get(slot) or []})
    def done(rows):
        out = []
        for g in rows.values():
            g["why"] = sorted(g["why"])
            g["duplicates"] = len(g["ads"]) - 1
            if "versions" in g:
                g["versions"] = list(dict.fromkeys(g["versions"]))
            g["spend"], g["value"] = round(g["spend"], 2), round(g["value"], 2)
            g["cpa"] = round(g["spend"] / g["purchases"], 2) if g["purchases"] else None
            g["roas"] = round(g["value"] / g["spend"], 2) if g["spend"] else None
            if "creatives" in g:
                g["creatives"] = sorted(g["creatives"])
            for k in ("primary", "headlines"):
                if isinstance(g.get(k), dict):
                    g[k] = list(g[k].values())
            out.append(g)
        return sorted(out, key=lambda g: -g["spend"])
    return {"copy": done(merge_near(copy)), "creative": done(creative)}


def add(g, a):
    if any(x["ad_id"] == a["ad_id"] for x in g["ads"]):
        return
    g["ads"].append({"ad_id": a["ad_id"], "ad_name": a.get("ad_name"), "spend": a["spend"],
                     "purchases": a["purchases"], "value": a.get("value") or 0, "cpa": a.get("cpa")})
    g["why"].update(a.get("why") or [])
    g["spend"] += a["spend"]
    g["purchases"] += a["purchases"]
    g["value"] += a.get("value") or 0


SAME = 0.9      # two texts this alike are one text with a small edit (a link line, an emoji space)


def merge_near(copy):
    """Fold texts that are the same ad with a small edit into one row; the edits stay as `versions`."""
    from difflib import SequenceMatcher
    rows = sorted(copy.values(), key=lambda g: -g["spend"])
    kept = []
    for g in rows:
        home = next((k for k in kept if k["slot"] == g["slot"] and
                     SequenceMatcher(None, norm(k["text"]), norm(g["text"])).ratio() >= SAME), None)
        if not home:
            g.setdefault("versions", [g["text"]])
            kept.append(g)
            continue
        home["versions"].append(g["text"])
        for x in g["ads"]:
            add(home, dict(x, why=g["why"]))
        home.setdefault("creatives", set()).update(g.get("creatives") or [])
    return {(g["slot"], norm(g["text"])): g for g in kept}


def rel(p):
    try:
        return p.relative_to(WS)
    except ValueError:
        return p


def pull(brand, *, cpa_min_spend=500.0, cpa_min_buys=5, cpa_pages=3, say=print, door=None, day=None):
    d = out_dir(brand, day)
    d.mkdir(parents=True, exist_ok=True)
    ins_f, words_f = d / "insights.json", d / "words.json"
    door = door or Door(brand, say)
    acct = f"act_{door.account}"
    words = {}
    try:
        ins = json.loads(ins_f.read_text()) if ins_f.is_file() else {}
        if "top_spend" not in ins:
            res = door.get(f"{acct}/insights", level="ad", date_preset="maximum", fields=INSIGHT_FIELDS,
                           sort="spend_descending", limit=TOP)
            ins["top_spend"] = [row(r) for r in res.get("data", [])][:TOP]
            ins_f.write_text(json.dumps(ins, indent=1))
            say(f"  1/3 top {TOP} by spend: {len(ins['top_spend'])} ads ({door.calls} call, meter {door.peak:.0f}%)")
        if "cpa_pool" not in ins:
            pool, after = [], None
            for _ in range(cpa_pages):
                p = dict(level="ad", date_preset="maximum", fields=INSIGHT_FIELDS, sort="spend_descending", limit=200,
                         filtering=json.dumps([{"field": "spend", "operator": "GREATER_THAN", "value": cpa_min_spend}]))
                if after:
                    p["after"] = after
                res = door.get(f"{acct}/insights", **p)
                pool += [row(r) for r in res.get("data", [])]
                after = ((res.get("paging") or {}).get("cursors") or {}).get("after")
                if not (res.get("paging") or {}).get("next"):
                    break
            ins["cpa_pool"], ins["cpa_rule"] = pool, {"min_spend": cpa_min_spend, "min_purchases": cpa_min_buys}
            ins_f.write_text(json.dumps(ins, indent=1))
            say(f"  2/3 ads over ${cpa_min_spend:,.0f} spend: {len(pool)} ({door.calls} calls, meter {door.peak:.0f}%)")
        ads = pick(ins["top_spend"], ins["cpa_pool"], cpa_min_buys)
        words = json.loads(words_f.read_text()) if words_f.is_file() else {}
        for a in ads:
            if a["ad_id"] not in words:
                words[a["ad_id"]] = words_of(door.get(a["ad_id"], fields=CREATIVE).get("creative"))
                words_f.write_text(json.dumps(words, indent=1, ensure_ascii=False))
        say(f"  3/3 words for {len(words)}/{len(ads)} ads ({door.calls} calls, meter {door.peak:.0f}%)")
    except Stop as e:
        say(f"  STOPPED: {e}. Everything so far is saved in {rel(d)}; a rerun picks up from here.")
        return None
    out = [dict(a, **words.get(a["ad_id"], {})) for a in ads]
    (d / "copy.json").write_text(json.dumps({
        "brand": brand, "pulled": date.today().isoformat(),
        "rule": f"top {TOP} by spend + top {TOP} by lowest CPA (spend over ${cpa_min_spend:,.0f}, {cpa_min_buys}+ purchases)",
        "calls": door.calls, "meter_peak": door.peak, "ads": out, **index(out)}, indent=1, ensure_ascii=False) + "\n")
    say(f"wrote {rel(d / 'copy.json')}: {len(out)} ads, {door.calls} calls, meter peak {door.peak:.0f}%")
    return out


# ---------- from our own database: no Meta calls ----------

def db_query(sql):
    """One read-only query against the Supabase warehouse (SUPABASE_DB_URL in the Keychain) -> json."""
    import subprocess
    sys.path.insert(0, str(Path.home() / ".daemn"))
    import daemn_keys
    r = subprocess.run(["psql", daemn_keys.key("SUPABASE_DB_URL"), "-At", "-v", "ON_ERROR_STOP=1",
                        "-c", "set default_transaction_read_only = on; " + sql],
                       capture_output=True, text=True, timeout=180)
    if r.returncode:
        raise SystemExit(f"database: {r.stderr.strip()[:400]}")
    text = r.stdout.split("SET\n", 1)[-1].strip()      # json_agg breaks lines between rows
    return json.loads(text) if text else None


def from_db(brand, *, cpa_min_spend=500.0, cpa_min_buys=5, say=print):
    """The same 25 + 25, read from the warehouse's nightly copy of Meta (meta_ad_insights,
    meta_ads) — the owner, 2 Oct: "if that data has already been pulled, then we can just use that"."""
    from brand import Brand
    acct = Brand(brand).account_id
    per_ad = db_query(f"""select coalesce(json_agg(x), '[]') from (
        select ad_id, max(ad_name) ad_name, sum(spend) spend, sum(purchases) purchases,
               sum(purchase_value) purchase_value, min(date) first_day, max(date) last_day
        from meta_ad_insights where account_id = '{acct}' group by ad_id) x""")
    rows = [{"ad_id": r["ad_id"], "ad_name": r["ad_name"], "spend": round(float(r["spend"] or 0), 2),
             "purchases": float(r["purchases"] or 0), "value": round(float(r["purchase_value"] or 0), 2),
             "first_day": r["first_day"], "last_day": r["last_day"]} for r in per_ad]
    for r in rows:
        r["cpa"] = round(r["spend"] / r["purchases"], 2) if r["purchases"] else None
        r["roas"] = round(r["value"] / r["spend"], 2) if r["spend"] else None
    window = (min((r["first_day"] for r in rows), default=None), max((r["last_day"] for r in rows), default=None))
    top_spend = sorted(rows, key=lambda r: -r["spend"])[:TOP]
    pool = [r for r in rows if r["spend"] > cpa_min_spend]
    ads = pick(top_spend, pool, cpa_min_buys)
    ids = ",".join(f"'{a['ad_id']}'" for a in ads) or "''"
    got = {r["ad_id"]: r for r in db_query(f"""select coalesce(json_agg(x), '[]') from (
        select ad_id, raw->'creative' creative, thumbnail_url, preview_link, instagram_permalink_url, created_time,
               landing_page_url from meta_ads where ad_id in ({ids})) x""")}
    out = []
    for a in ads:
        m = got.get(a["ad_id"]) or {}
        w = words_of(m.get("creative"))
        w["thumbnail"] = m.get("thumbnail_url") or w.get("thumbnail")
        out.append(dict(a, **w, created=m.get("created_time"), landing_page=m.get("landing_page_url"),
                        instagram=m.get("instagram_permalink_url"), preview=m.get("preview_link"),
                        words_on_file=bool(m)))
    d = out_dir(brand, date.today().isoformat() + "-db")
    d.mkdir(parents=True, exist_ok=True)
    ix = index(out)
    (d / "copy.json").write_text(json.dumps({
        "brand": brand, "pulled": date.today().isoformat(), "source": "warehouse (meta_ad_insights, meta_ads) — no Meta calls",
        "window": {"from": window[0], "to": window[1]}, "ads_in_window": len(rows),
        "rule": f"top {TOP} by spend + top {TOP} by lowest CPA (spend over ${cpa_min_spend:,.0f}, {cpa_min_buys}+ purchases)",
        "ads": out, **ix}, indent=1, ensure_ascii=False) + "\n")
    prim = sum(1 for g in ix["copy"] if g["slot"] == "primary")
    say(f"{brand}: {len(rows)} ads {window[0]}..{window[1]} → {len(out)} picked → {prim} distinct primary texts, "
        f"{len(ix['creative'])} distinct creatives · {rel(d / 'copy.json')}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--cpa-min-spend", type=float, default=500.0)
    ap.add_argument("--cpa-min-buys", type=int, default=5)
    ap.add_argument("--cpa-pages", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-db", action="store_true", help="read our warehouse's copy of Meta instead — no Meta calls")
    a = ap.parse_args()
    if a.from_db:
        from_db(a.brand, cpa_min_spend=a.cpa_min_spend, cpa_min_buys=a.cpa_min_buys)
        return
    if a.dry_run:
        print(f"1 call: top {TOP} ads by lifetime spend ({INSIGHT_FIELDS})\n"
              f"<= {a.cpa_pages} calls: ads over ${a.cpa_min_spend:,.0f} spend, same fields, 200 a page -> lowest CPA "
              f"with {a.cpa_min_buys}+ purchases, top {TOP}\n<= {2 * TOP} calls: one per picked ad, its words only\n"
              f"stops at {STOP_AT}% on any Meta meter; nothing called now")
        return
    pull(a.brand, cpa_min_spend=a.cpa_min_spend, cpa_min_buys=a.cpa_min_buys, cpa_pages=a.cpa_pages)


if __name__ == "__main__":
    main()
