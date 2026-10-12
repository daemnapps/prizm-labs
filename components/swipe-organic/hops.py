#!/usr/bin/env python3
"""Graph hops — the feed discovers new sources the way a person does.

Nobody finds content by search; they follow edges: a winning post → its
creator → who that creator runs with. This walks the edges that are
open WITHOUT a login (the persona accounts unlock the rest later):

  1. CREATOR hop   — creators behind winning posts become candidate
                     account sources
  2. MENTION hop   — @handles inside winning captions are edges the
                     creators drew themselves
  3. CROSS hop     — a TikTok winner's handle checked on Instagram;
                     same person, second platform

Every candidate enters sources.json with status "probation" and a
receipt naming the exact winner that surfaced it. Probation sources get
pulled like any other — they earn a permanent seat (or retirement) by
what they deliver. Every adoption is logged to discoveries.jsonl.

    python3 hops.py --avatar brand-b--avatar-two [--max 8] [--dry-run]

A winner = a post with views >= 50k, or rising >= 10%/day between
observations. No human input feeds this (the owner's ruling 2026-08-30).
"""
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import apify as A

HERE = Path(__file__).resolve().parent
WIN_VIEWS, WIN_RISE = 50_000, 10.0

def winners(root):
    items = json.loads((root / "items.json").read_text())["items"]
    obs = {}
    for line in (root / "observations.jsonl").read_text().splitlines():
        o = json.loads(line)
        if o.get("views"):
            obs.setdefault(o["item"], []).append(o)
    out = []
    for key, it in items.items():
        rows = obs.get(key, [])
        views = rows[-1]["views"] if rows else 0
        rise = 0.0
        if len(rows) >= 2 and rows[0]["views"]:
            def ts(s):
                d = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            t0, t1 = ts(rows[0]["at"]), ts(rows[-1]["at"])
            days = max((t1 - t0).total_seconds() / 86400, 0.25)
            rise = (rows[-1]["views"] / rows[0]["views"] - 1) / days * 100
        if views >= WIN_VIEWS or (rise >= WIN_RISE and views >= 10_000):
            out.append({"key": key, "it": it, "views": views, "rise": round(rise, 1)})
    return sorted(out, key=lambda w: -w["views"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--max", type=int, default=8, help="max new candidates per run")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = HERE / "records/avatar-feeds" / args.avatar
    S = json.loads((root / "sources.json").read_text())
    have = {(s["platform"], s["value"].lower()) for s in S["sources"]}
    exclude = {h.lower() for h in S.get("exclude", [])}  # the brand's own handles, per-feed data
    wins = winners(root)
    print(f"{len(wins)} winners over the bar")

    # collect candidate edges, best winner first
    cands = []  # (platform, handle, receipt)
    for w in wins:
        it, plat = w["it"], w["it"]["platform"]
        why = f'{w["views"]:,} views' + (f' · rising {w["rise"]}%/day' if w["rise"] >= WIN_RISE else "")
        if it.get("author"):
            cands.append((plat, it["author"], f'creator hop: authored winner {it["url"]} ({why})'))
        for m in re.findall(r"@([A-Za-z0-9_.]{3,30})", it.get("caption") or ""):
            cands.append((plat, m, f'mention hop: named in winner {it["url"]} ({why})'))
        if plat == "tiktok" and it.get("author"):
            cands.append(("instagram", it["author"],
                          f'cross hop: TikTok winner {it["author"]} checked on IG ({why})'))

    fresh, seen = [], set()
    for plat, handle, receipt in cands:
        k = (plat, handle.lower())
        if k in have or k in seen or handle.lower() in exclude:
            continue
        if plat not in ("tiktok", "instagram"):
            continue  # yt gives display names, not pullable handles — needs a channel puller first
        seen.add(k)
        fresh.append((plat, handle, receipt))
        if len(fresh) >= args.max:
            break
    for plat, handle, receipt in fresh:
        print(f"  candidate [{plat}] {handle} — {receipt[:90]}")
    if args.dry_run or not fresh:
        return

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    adopted = []
    for plat, handle, receipt in fresh:
        if plat == "instagram":
            # verify the account exists and is a real page before seating it
            try:
                d = A.run(A.POSTS_IG, {"directUrls": [f"https://www.instagram.com/{handle}/"],
                                       "resultsType": "details"})
                fol = (d[0] or {}).get("followersCount") if d else None
                if not fol or fol < 1_000:
                    print(f"  skip ig {handle}: followers={fol}")
                    continue
                receipt += f" · verified on IG, {fol:,} followers"
            except Exception as e:
                print(f"  skip ig {handle}: {str(e)[:60]}")
                continue
        S["sources"].append({"platform": plat, "kind": "account", "value": handle,
                             "status": "probation", "receipt": receipt, "seated": now})
        adopted.append((plat, handle, receipt))
    (root / "sources.json").write_text(json.dumps(S, indent=1) + "\n")
    with (root / "discoveries.jsonl").open("a") as L:
        for plat, handle, receipt in adopted:
            L.write(json.dumps({"at": now, "platform": plat, "value": handle,
                                "receipt": receipt, "status": "probation"}) + "\n")
    print(f"seated {len(adopted)} probation sources · sources now {len(S['sources'])}")

if __name__ == "__main__":
    main()
