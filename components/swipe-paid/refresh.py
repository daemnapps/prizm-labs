#!/usr/bin/env python3
"""Fold a fresh advertiser sweep into a brand's existing swipe.

    python3 refresh.py <brand> <sweep-ALL.json> <YYYY-MM-DD> [--resolve]

The brand keeps its slugs and numbers (they name folders on the Drive mirror,
which are never renamed), so a refresh only ever adds:
  - new ads join the block with the same headline + primary text
  - copy never seen before opens a new block, numbered after the last one
  - every ad carries `swept` (the date it was pulled), every block `live_now`
    (ads from the newest sweep) and `first_swept`
  - a block's landing page is carried; new blocks are looked up with --resolve,
    one credit each, through the client in capture/ (never the ~/devel copy)

Needs ADPLEXITY_API_KEY in the environment for --resolve.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # norm_body, slugify, stage_of, is_seasonal


def main(brand, sweep_path, day, resolve):
    path = os.path.join(HERE, brand, "blocks.json")
    doc = json.load(open(path))
    blocks = doc["blocks"]
    items = json.load(open(sweep_path))["items"]

    for b in blocks:                          # first refresh: stamp what is already there
        b.setdefault("first_swept", doc.get("swept") or "before " + day)
        for m in b["media"].values():
            m.setdefault("swept", b["first_swept"])
    by_key = {(b["headline"], b["primary_text"]): b for b in blocks}
    known = {str(i) for b in blocks for i in b["ad_ids"]}

    added_ads = new_blocks = 0
    for it in items:
        if str(it["id"]) in known:            # a returning ad: still live, so it counts in live_now
            b = next(b for b in blocks if str(it["id"]) in {str(i) for i in b["ad_ids"]})
            b["media"][str(it["id"])]["swept"] = day
            continue
        key = ((it.get("title") or "").strip(), build.norm_body(it.get("description")))
        b = by_key.get(key)
        if b is None:
            n = len(blocks) + 1
            b = {"nn": f"{n:02d}", "slug": f"{n:02d}_{build.slugify(key[0])}",
                 "headline": key[0] or "NO_TITLE", "primary_text": key[1],
                 "count": 0, "video_count": 0, "image_count": 0,
                 "rep_ad_id": it["id"], "ad_ids": [], "media": {},
                 "stage": build.stage_of(*key), "seasonal": build.is_seasonal(*key),
                 "variants": 0, "max_variants": 1, "landing_page": None,
                 "first_swept": day}
            blocks.append(b); by_key[key] = b; new_blocks += 1
        v = it.get("meta_group_ads_count") or 1
        b["ad_ids"].append(it["id"]); b["count"] += 1
        b["variants"] += v; b["max_variants"] = max(b["max_variants"], v)
        b["video_count" if it.get("video_url") else "image_count"] += 1
        b["media"][str(it["id"])] = {"video": it.get("video_url") or "",
                                     "image": it.get("image_url") or "",
                                     "variants": v, "swept": day,
                                     "first_seen": it.get("first_seen"),
                                     "page_name": it.get("meta_page_name")}
        added_ads += 1

    for b in blocks:
        b["live_now"] = sum(1 for m in b["media"].values() if m.get("swept") == day)

    if resolve:
        sys.path.insert(0, os.path.join(HERE, "capture"))
        import adplexity_client as c
        for b in blocks:
            if b.get("landing_page"):
                continue
            newest = next((a for a in b["ad_ids"][::-1] if b["media"][str(a)].get("swept") == day), b["rep_ad_id"])
            data, err = c.call(f"/ads/{newest}")
            if err:
                print(f"  {b['nn']} FAILED {err[:60]}"); continue
            rec = data.get("data", data)
            json.dump(rec, open(os.path.join(HERE, "capture", "raw", f"ad_{newest}.json"), "w"), indent=1)
            lps = rec.get("landing_pages") or []
            b["landing_page"] = lps[0].get("url") if lps else None
            print(f"  {b['nn']}  {b['count']:>4}  {(b['landing_page'] or 'NO LP')[:90]}")

    doc["creatives"] = sum(b["count"] for b in blocks)
    doc["video"] = sum(b["video_count"] for b in blocks)
    doc["image"] = sum(b["image_count"] for b in blocks)
    doc["swept"] = day
    json.dump(doc, open(path, "w"), indent=1)
    print(f"{brand}: +{added_ads} ads, +{new_blocks} new blocks -> {doc['creatives']} creatives, "
          f"{len(blocks)} blocks, {sum(b['live_now'] for b in blocks)} live in the newest sweep")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], "--resolve" in sys.argv)
