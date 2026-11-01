# General briefs — written to no one, filmed by anyone

*18 September 2026. the owner: "we need to begin building our more direct
response creator swipe briefs. these can be executed literally by any
creator, doesn't need to be built by replicating their top videos."*

## The source set

the owner's Instagram saves (`components/swipe-organic/records/damon-saves/`),
categories `skincare-product-promo` (28) and `body-scrub-exfoliation` (13)
— the "link in bio / shop here" product videos. 35 had the video on disk in
`records/swipe-videos/<code>/video.mp4`; 33 made it into the queue. Views
first (the owner's rule). Artifact: General Brief Swipes (URL in
`context/artifacts.md`).

## Routing

- body-scrub-exfoliation → `glow-body-scrub`
- skincare-product-promo → `glow-face-scrub`

## How they run

`machine/runs/_general-queue.txt` (label · product · video; a copy of today's is `notes/general-queue-2026-09-18.txt`), driven by
`machine/general_run.sh` (a copy runs from `machine/runs/`) under nohup — one after another, `--route
creator --no-frames` (no pictures reach a brief any more; stage 7 now takes
the brief as-is without frames). Log: `machine/runs/_general-run.log`.
Re-running the script skips anything already finished.

Each run lands as one Doc + its video in the brand's shared folder
`creators/brand-a/GENERAL — any creator/BRIEFS/`, with a Start-here of its
own ("Hey, there!" wording — nothing about a creator's own feed). The brief
count on the page counts the brand's general briefs.

## Open

- ~20 min a run; the queue was started 18 Sep 18:39 and restarted 19:15
  after the frames fix. Check the log before assuming it finished.
- Brand B general briefs: the `looksmax-glowup` saves (5) fit; not queued.
- Creators still cannot upload into DELIVERABLES without a Google account
  — the machine account needs Content Manager on Team Drive (the developer), or
  the owner flips the folders himself.


## Batch 2 — the shop-style saves (2026-09-24)

the owner: "we need general briefs for brand-a now, find some TikTok Shop style
swipes for that brand. <competitor> has a ton."

**<competitor> could not be pulled.** Both Apify accounts are over their monthly
cap (STARTER `fluffy_hosta` $__ of $__ cycle from 09-14; FREE `daemn`
$__ of $__ cycle from 09-10), so the TikTok doors in `components/apify/`
return 403. `yt-dlp` reaches @creator directly (122 posts, no
quota) but that account is brand/event content — pop-ups, wellness clubs,
8k–41k views — not the shop-style DR videos. The affiliate videos live
behind TikTok search and the hashtag, which answer with a CAPTCHA to a
logged-out browser. **Fresh <competitor> swipes wait on the Apify cap.**

What ran instead: the shop-style swipes already downloaded in the saves
library — `comment-gate-funnel`, `gadget-product-promo`,
`skin-authority-explainer`, `skincare-product-promo`,
`body-scrub-exfoliation`, `hair-removal-waxing` — brand_fit brand-a, not
already briefed. 49 candidates, 20 dropped as off-avatar (waxing, ingrowns,
feet, derm conditions), **29 queued** (`notes/general-queue-2026-09-24.txt`).
Face/body decided by the caption's own words; views first.


## Batch 3 — the owner's own TikTok Shop swipes (2026-09-24)

He handed over 13 .mp4 files: "here are the swipes I want to build creator
briefs for". TikTok ids, downloaded by him. **108M views combined**, the
biggest 26.1M. Several are explicitly TikTok Shop (#tiktokshopstockup,
#weeklydeals), and <competitor> runs through them — which is what he was after
when the Apify cap blocked the pull.

Filed into `components/swipe-organic/records/swipe-videos/<tiktok-id>/`
(video, strip, meta.json) with `pool: tiktok-shop`. The ids resolve without
Apify: `m.tiktok.com/v/<id>.html` through yt-dlp gives uploader and view
count, and TikTok's oembed gives the caption and author — worth remembering
while the cap is spent.

Read off the frames, product routed by what the video argues for: 5 face, 8
body. Two ("stop over-exfoliating", @creator 14.7M and @creator
5.1M) argue AGAINST scrubs — the strongest angle on the sheet for a
twice-a-week scrub, but only if the brief takes that turn deliberately;
flagged to him rather than decided. Two have a man on camera.

Queue: `machine/runs/_queue-tonight.txt` — his 13 first, then batch 2's 29.
Fires itself at 00:05 via `~/Library/LaunchAgents/com.daemn.general-briefs.plist`
(the model's weekly limit resets then). Artifact: TikTok Shop Swipes.
