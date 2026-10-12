#!/usr/bin/env python3
"""Put a lane on every post in a feed, without a model.

    python3 sift_rules.py --avatar brand-b--sub-two [--dry-run]

sift.py is the real sorter: it sends each post to a model and gets back a lane,
a kind and a reason. This is its stand-in for when that call cannot be made —
on 2 Oct 2026 the `claude` CLI's OAuth session had expired, and 1,095 posts
across three feeds had no lane at all, so every one of them leaked into every
lane filter on the board.

It reads the caption and the hashtags and decides on stated rules, written out
below so the call can be argued with. Records are tagged `feed-sift-rules-v1`,
never `feed-sift-v3`, so they are plainly not a model read and
`sift.py --redo` will replace them once the login is back.

Lanes are sift's own, never new ones: entertainment · educational · selling ·
junk. Which of them a feed KEEPS is the feed's own `keep_lanes`.
"""
import argparse, json, re
import desklib as D

# Someone is being sold something: an affiliate marker, a discount, a code, a
# link out, or a brand partnership tag. This is checked first — a tutorial that
# ends in a discount code is still a sale.
SELLING = re.compile(
    r"#\w*partner\b|\bpartner(ship)?\b|link in bio|link in my bio|click my avatar|"
    r"\bcode\b|\bcod \w+|discount|% ?off|\bsale\b|shop now|buy|order|checkout|"
    r"use my link|swipe up|\bad\b|sponsored|#\w*ad\b|comment [\"'“]?\w+[\"'”]? and|"
    r"dm me|available now|sold out|restock|limited time", re.I)

# Someone is being taught: a reason, a method, a routine, a correction.
EDUCATIONAL = re.compile(
    r"\bhow to\b|\bhere'?s (how|why|what)\b|\bwhy (your|you|it|this)\b|\bthe reason\b|"
    r"tutorial|routine|step ?\d|\btips?\b|\bguide\b|explain|myth|mistake|"
    r"doesn'?t work|stop (doing|using)|what i (use|do)\b|ingredients?\b|"
    r"dermatolog|science|study|according to", re.I)

# Nothing to read: no caption and no tags to judge on.
def blank(cap, tags):
    return not (cap or "").strip() and not tags


def lane_for(cap, tags, author=None, brand_accounts=()):
    text = (cap or "") + " " + " ".join(tags or [])
    if blank(cap, tags):
        return "junk", "no caption and no tags to read"
    # The brand posting on its own account is selling even with no partner tag
    # and no code — "Have you tried BASED Body Lotion yet?" is an ad. A feed
    # names its own accounts in sources.json; nothing is guessed from a name.
    if author and author.lower() in brand_accounts:
        return "selling", "the brand's own account posting its own product"
    if SELLING.search(text):
        return "selling", "carries a selling marker (partner tag, code, link or offer)"
    if EDUCATIONAL.search(text):
        return "educational", "explains or teaches something"
    return "entertainment", "no selling marker and nothing taught — watched for its own sake"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = D.FEEDS / a.avatar
    S = json.loads((root / "sources.json").read_text())
    cat = json.loads((root / "items.json").read_text())
    keep_lanes = set(S.get("keep_lanes") or ["entertainment", "educational"])
    brand_accounts = {a.lower() for a in (S.get("brand_accounts") or [])}
    # A post with a sift record but no lane counts as unsorted: his own saves
    # are written by saves_feed.py with `"lane": null` — he saved it, so it is
    # kept, but nothing ever said what it IS. Fill the lane, leave the rest of
    # that record alone (its `what` and its `why` are his, not ours).
    todo = [k for k, it in cat["items"].items()
            if not it.get("sift") or not it["sift"].get("lane")]
    if not todo:
        print(f"{a.avatar}: every post already has a lane")
        return
    tally, kept = {}, 0
    for k in todo:
        it = cat["items"][k]
        lane, why = lane_for(it.get("caption"), it.get("hashtags"),
                             it.get("author"), brand_accounts)
        keep = lane in keep_lanes
        kept += keep
        tally[lane] = tally.get(lane, 0) + 1
        if not a.dry_run:
            rec = it.get("sift") or {}
            it["sift"] = {**rec, "keep": keep if not rec else rec.get("keep", keep),
                          "lane": lane, "kind": rec.get("kind") or it.get("kind"),
                          "lang": rec.get("lang") or "none", "what": rec.get("what"),
                          "format": rec.get("format") or "unread",
                          "why": rec.get("why") or why,
                          "at": D.now(), "prompt": "feed-sift-rules-v1"}
    if not a.dry_run:
        (root / "items.json").write_text(json.dumps(cat, indent=1) + "\n")
    shape = " · ".join(f"{l} {n}" for l, n in sorted(tally.items(), key=lambda x: -x[1]))
    print(f"{a.avatar}: {len(todo)} sorted — {shape} · kept {kept}" + ("  (dry run)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
