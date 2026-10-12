# What Meta wants — the source of every diversity rule

the owner, 2026-10-07: *"Everything that we do here needs to strictly revolve around exactly what they want, and that needs to go into the vocabulary that we use in our actual system and process. We are becoming hyper-optimized towards marketing on this platform."*

Every rule in `dimensions.json` traces to a line here. **Meta's own words only** in sections 1–4; anything else is marked. Read 2026-10-07. Help-center pages carry no dates.

## 1. How Meta's machine picks an ad

| Stage | What Meta says | Source |
|---|---|---|
| **Andromeda (retrieval)** | Narrows "tens of millions of ad candidates into a few thousand"; "precomputed ad embeddings"; "a hierarchical index"; delivers "a more diverse set of ad candidates"; GenAI made "more than 15 million ads in a month" | [engineering.fb.com, 2 Dec 2024](https://engineering.fb.com/2024/12/02/production-engineering/meta-andromeda-advantage-automation-next-gen-personalized-ads-retrieval-engine/) |
| | "as businesses upload more and more creatives to support a diversification strategy, Meta Andromeda works behind the scenes… to pick the right creative" | [Meta for Business, 27 Mar 2025](https://www.facebook.com/business/news/ai-innovation-in-metas-ads-ranking-driving-advertiser-performance) |
| **GEM (ranking)** | Features include "ad format, and creative representation"; user "sequences of up to thousands of events"; +5% conversions IG, +3% FB Feed | [engineering.fb.com, 10 Nov 2025](https://engineering.fb.com/2025/11/10/ml-applications/metas-generative-ads-model-gem-the-central-brain-accelerating-ads-recommendation-ai-innovation/) |
| | "semantic content features from foundation models" alongside behaviour signals (helps new ads) | [engineering.fb.com, 5 Aug 2026](https://engineering.fb.com/2026/08/05/ml-applications/from-user-sequences-to-scaling-laws-a-multi-stage-architecture-for-metas-ads-ranking/) |
| **Generative Recommender** | "using LLMs to reason about ad content and user preferences together" (in retrieval since Q2 2026) | Q2-2026 earnings call, 29 Jul 2026 |
| **Grouping** | "groups together ads that share key visual and thematic attributes. When multiple ads look or feel alike, these are seen as variations of the same creative" — learnings and delivery "shared at the creative level" | [Demystifying Creative Diversification, 16 Dec 2025](https://www.facebook.com/business/news/demystifying-creative-diversification) |
| **Fatigue** | "We consider all recent exposures of the ad's image or video, including those from other campaigns from your Page." Fix: new image or video "materially different from the original creative." *Creative limited* = cost per result above past ads, under 2x; *Creative fatigue* = 2x or more | [Help: creative fatigue](https://www.facebook.com/business/help/1346816142327858) |

## 2. Meta's vocabulary — the system's vocabulary

| Meta's term | Meta's meaning | Replaces our |
|---|---|---|
| **creative diversification** | "unique campaign assets tailored to different potential customer personas or use cases"; "truly different in look, feel, storyline, and message"; "truly distinct in their visuals, messaging, and formats" | big moves |
| **creative iteration** | "two ads with identical visuals, but different text CTAs" — "should not replace true creative diversification" | small moves |
| **variations of the same creative** | ads that "look or feel alike" — grouped | duplicate |
| **creative similarity** | "when ad images are visually too alike, even if technically different assets" | — |
| **creative fatigue / creative limited** | overexposure of one image/video (see thresholds above) | burnt out |
| **persona · use case · motivation** | who it's for and why ("emotional appeal" vs "product features") | avatar · sub-avatar · desire |
| **flexible ad · assets** | one ad, up to 10 images/videos; Meta picks the mix per person ([help](https://www.facebook.com/business/help/835561738423867)) | ad unit |
| **hook** | "the text, visual, and audio components that grab and hold attention in the first few seconds" — value promise · statement of intent · question/invitation ([source](https://www.facebook.com/business/news/the-science-of-the-hook-how-to-supercharge-your-reels-performance)) | hook |
| **partnership ad** | an ad run with a creator's handle | creator ad |

## 3. What Meta says works (Meta's numbers)

- **9.1% lower CPA**: ad sets with "a diverse mix of images, videos and 9:16 vertical video with audio" (1M+ ad sets, Apr–Jun 2025). [Advantage+ sales](https://www.facebook.com/business/ads/meta-advantage-plus/sales-campaigns)
- **7% lower CPA**: at least 20% of assets are 9:16 video with audio (~530k ad sets, Sep 2025). Same page.
- "Go beyond formats: Vary your visuals, messages and storytelling approaches to give the ad delivery system more options to work with." Same page.
- **7.3% lower CPA**: ad sets with at least an image, a video and vertical video with audio; "The static, single-asset approach is dead." [Cyber 5 2025](https://www.facebook.com/business/news/cyber-5-2025-what-worked)
- **19% lower acquisition cost**: partnership ads with creators. Same page.
- **Up to 13% more incremental conversions**: music or voiceover in Reels. [Science of the Hook](https://www.facebook.com/business/news/the-science-of-the-hook-how-to-supercharge-your-reels-performance)
- **34.5% lower cost per result** vs image ads: 9:16 video with audio, key messages in the safe zone. [Reels ads](https://www.facebook.com/business/ads/facebook-instagram-reels-ads) · [safe zone](https://www.facebook.com/business/help/980593475366490)
- **Fewer ads, more assets**: "Decrease ads per ad set, but maintain diverse creative assets per ad set. One ad can contain multiple (up to 10) creative assets." [Managing ad volume](https://www.facebook.com/business/help/2720085414702598) · max 50 ads per ad set; learning ends ~50 results/week.

## 4. Not Meta — do not build on these

| Claim | Status |
|---|---|
| "Entity ID" — similar ads share one ID | Agency term. Meta confirms grouping only. |
| ">60% similarity score" suppresses an ad | No Meta source; Meta says similarity diagnostics are "continuing to test". |
| "8–15+ ads per ad set" | Meta says the opposite (fewer ads, more assets each). |
| Similar ads pay higher CPMs | Not stated. |

## 5. The rule this produces (in `dimensions.json`)

- **Meta's dimensions → our moves:** persona/use case → who · message → angle + awareness · storyline → format/structure · look and feel → face + setting + style · format → media.
- **New creative = 3+ moves from the nearest live creative.** *The threshold is ours, not Meta's* — Meta publishes none. Calibrate against the tagged library.
- **Portfolio per ad set (Meta's numbers):** an image + a video + a 9:16 video with audio; ≥20% of assets 9:16 with audio; fewer ads, each a flexible ad with up to 10 diverse assets; no image/video already shown on the Page; music or voiceover on every Reel; key messages in the safe zone; creators via partnership ads.
- **Iteration** (hook text, caption, CTA, music swap) is allowed only *inside* a creative that already counts as new.

Research reports behind this: three researchers, 2026-10-07 (Meta engineering + earnings calls; Meta business help + news; Meta-authored papers incl. arXiv 2402.17152 HSTU, 2512.09200 Lattice, 2507.21983 AdLlama).

## 7. Meta grades each piece of a flexible ad (confirmed 2026-10-08)

The Insights API breaks one ad's results down by asset: `breakdowns=body_asset`, `title_asset` (and `video_asset` / `image_asset` for the media). Read live on "Brand A's Grandma – Advertorial #2", last 30 days:

| Piece | Spend | Purchases |
|---|---|---|
| Text "My grandmother pulled turmeric from the ground…" | $__ | 84 |
| Text "Refined women are OBSESSED…" | $__ | 35 |
| Headline "Ancient Thai Dark Spot Remedy" | $__ | 92 |
| Headline "Fade Dark Spots" | $__ | 37 |

**What it means for the system:** a section swap run as its own asset inside a flexible ad gets its own spend and purchases from Meta. That is the score the section index is built on (the owner: "mix and match the best elements from each asset"). Read it in the daily pull, never by polling.
