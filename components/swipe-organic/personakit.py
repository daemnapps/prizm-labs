#!/usr/bin/env python3
"""Persona seed kit — everything a trained persona account starts from.

A persona account is a real, dedicated account (never a brand account)
whose For You page gets trained to BE the avatar's feed. This builds
its starter pack from data we already own — no invention:

  - the avatar feed's sources (permanent + probation, receipts intact)
  - creators behind the feed's current winners
  - creators from the owner's saves catalog, in the categories this
    avatar's config names
  - the sounds those saves ran on (TikTok trains hard on audio)

Config per kit (data, not code — the script stays brand-agnostic):
    records/persona-kits/<brand>--<avatar>/config.json
      {"avatar": "...", "saves_categories": ["...", ...]}

    python3 personakit.py --avatar brand-b--avatar-two

Output: kit.json (machine) + kit.md (readable) in the kit folder.
Account creation is a human step; the kit is everything after that.
"""
import argparse, json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--avatar", required=True)
    args = ap.parse_args()
    kdir = HERE / "records/persona-kits" / args.avatar
    cfg = json.loads((kdir / "config.json").read_text())
    feed = HERE / "records/avatar-feeds" / args.avatar

    follows, seen = [], set()
    def add(platform, handle, receipt):
        k = (platform, handle.lower())
        if handle and k not in seen:
            seen.add(k)
            follows.append({"platform": platform, "handle": handle, "receipt": receipt})

    # 1) the feed's account sources, receipts carried over
    S = json.loads((feed / "sources.json").read_text())
    for s in S["sources"]:
        if s["kind"] == "account":
            add(s["platform"], s["value"], f'feed source ({s.get("status","permanent")}): {s["receipt"]}')

    # 2) creators behind current winners
    import hops
    for w in hops.winners(feed)[:40]:
        it = w["it"]
        if it["platform"] in ("tiktok", "instagram") and it.get("author"):
            add(it["platform"], it["author"],
                f'feed winner: {w["views"]:,} views — {it["url"]}')

    # 3) the owner's saves, in this kit's categories; and their sounds
    rows = json.loads((HERE / "records/damon-saves/catalog.json").read_text())["rows"]
    cats = set(cfg["saves_categories"])
    sounds = Counter()
    for r in rows:
        if r.get("category") in cats or r.get("category2") in cats:
            add("instagram", r.get("author"),
                f'the owner save, category {r.get("category")} — {r["url"]}')
            if r.get("sound"):
                sounds[r["sound"]] += 1

    hashtags = [{"platform": s["platform"], "tag": s["value"], "receipt": s["receipt"]}
                for s in S["sources"] if s["kind"] == "hashtag"]

    kit = {"avatar": args.avatar, "config": cfg, "follows": follows,
           "hashtags": hashtags, "sounds": [s for s, _ in sounds.most_common(15)]}
    (kdir / "kit.json").write_text(json.dumps(kit, indent=1) + "\n")

    by_p = Counter(f["platform"] for f in follows)
    md = [f"# Persona seed kit — {args.avatar}",
          "",
          "The starter pack for this avatar's trained persona account: a real,",
          "dedicated account (never a brand account) whose For You page gets",
          "trained until it IS the avatar's feed. Everything below is sourced —",
          "no invented handles.",
          "",
          f"**Follow list: {len(follows)} accounts** ({', '.join(f'{v} {k}' for k, v in by_p.items())})",
          ""]
    for f in follows:
        md.append(f"- **{f['handle']}** ({f['platform']}) — {f['receipt']}")
    md += ["", f"**Hashtags to engage** ({len(hashtags)}):",
           ""] + [f"- #{h['tag']} ({h['platform']}) — {h['receipt']}" for h in hashtags]
    if kit["sounds"]:
        md += ["", "**Sounds to watch through** (from the saves this avatar's categories ran on):",
               ""] + [f"- {s}" for s in kit["sounds"]]
    md += ["", "## Warm-up protocol",
           "",
           "1. Fresh account on a dedicated device/profile — never the brand's.",
           "2. Days 1–3: follow the list above a few at a time; watch their",
           "   recent posts to the end. Completion is the strongest signal.",
           "3. Days 3–10: open the hashtags daily; watch what the FYP serves;",
           "   rewatch and like only what the avatar would. Never post.",
           "4. From day 10: the FYP is the product. Capture it into the feed",
           "   backend as its own source (`kind: persona-fyp`).",
           ""]
    (kdir / "kit.md").write_text("\n".join(md))
    print(f"kit: {len(follows)} follows · {len(hashtags)} hashtags · {len(kit['sounds'])} sounds")

if __name__ == "__main__":
    main()
