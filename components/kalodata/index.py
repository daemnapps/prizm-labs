#!/usr/bin/env python3
"""The TikTok Shop swipe index: what is running right now, and what is growing fast.

    index.py plan  <config.json>                                     what it will read and the most it can cost; sends nothing
    index.py build <config.json> --label <l> --max-credits <n>       needs the owner's yes first

  running   an ad still in front of people that pays back: most money in the last 7 days, return over the config's line
  growing   money rising: sorted by Kalodata's growth over the last 7 days, then checked on the daily trend
Same view floor for both, never padded. Who posted it, how many followers they have, and AI or human are never filters.
A video is on one list only (growing wins). Money is Kalodata's estimate: rank by it, never quote it.
"""
import argparse, json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kalodata as K  # noqa: E402
def cost(c): return {"find the category": 0.1, "growing": K.rank_cost(c["read"]), "running": K.rank_cost(c["read"]), "daily trend on the keepers": round(0.1 * c["check"] * 2, 2)}
def rising(trend, days=3):
    """last days of money over the same days before; None when there is too little to say"""
    t = [x or 0 for x in trend or []]
    if len(t) < days * 2: return None
    a, b = sum(t[-days:]), sum(t[-2 * days:-days])
    return None if not b else round(a / b, 2)
def once(rows, c, taken=()):
    """one video per creator, nothing under the floor, nothing already on the other list"""
    out, who = [], set()
    for v in rows:
        if (v.get("views") or 0) < c["view_floor"] or v["video_id"] in taken or v.get("belonged_creator_handle") in who: continue
        out.append(v); who.add(v.get("belonged_creator_handle"))
    return out
def build(c, purse, send):
    ids = {x["category_name"].strip().lower(): x["category_id"] for x in K.ranking("categories", {"days": 7, "level": 1, "rows": 100}, purse, send)}
    cat = [ids[n.lower()] for n in c["categories"] if n.lower() in ids]
    if not cat: raise SystemExit("none of the categories were found: %s" % c["categories"])
    base = {"days": 7, "category": cat, "views": ">%d" % c["view_floor"], "revenue": ">%d" % c["money_floor"], "rows": c["read"]}
    grow = once(K.ranking("videos", dict(base, sort="revenue_growth_rate"), purse, send), c)[:c["check"]]
    run = once([v for v in K.ranking("videos", dict(base, sort="revenue", roas=">%s" % c["min_roas"]), purse, send) if v.get("ad")], c, {v["video_id"] for v in grow})[:c["check"]]
    for v in grow + run:
        try: purse.take(0.1)
        except K.OverCeiling: break
        v["detail"] = send("/tiktok/video/detail", {"region": "US", "language": "en-US", "currency": "USD", "date_range": "last7Day", "video_id": v["video_id"]}) or {}
        v["rising"] = rising(v["detail"].get("revenue_trend"))
    grow = [v for v in grow if v.get("rising") is None or v["rising"] >= 1]          # growth that already stopped is not growth
    run.sort(key=lambda v: -(v.get("revenue") or 0))
    return {"growing": grow[:c["keep"]], "running": run[:c["keep"]]}
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("plan", "build")); ap.add_argument("config"); ap.add_argument("--label"); ap.add_argument("--max-credits", type=float); a = ap.parse_args()
    c = json.loads(Path(a.config).read_text()); k = cost(c)
    for n, v in k.items(): print("%-28s up to %.1f credits" % (n, v))
    print("%-28s up to %.1f credits, about $%.2f" % ("all of it", sum(k.values()), sum(k.values()) * 0.1))
    if a.cmd == "plan": return
    if c.get("state") != "approved": sys.exit("not sent: the config is held until the owner approves it")
    if not a.label or a.max_credits is None: sys.exit("build needs --label and --max-credits")
    purse = K.Purse(a.max_credits)
    try: out = build(c, purse, K.post)
    except K.OverCeiling as e: sys.exit("stopped: %s" % e)
    for n, rows in out.items(): K.save(a.label, n, rows, purse)
if __name__ == "__main__": main()
