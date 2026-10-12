# The Meta strategy

**the owner, 2026-10-07:** *"This is just the Meta strategy … dial in on our process to make sure that we're hitting all of our points as well as we possibly can and playing to this algo. That's literally all we're going to do here."*

We are hooked straight into Meta, our data lives in Meta, and every ad and page is made to sell to Meta's audience. So the process is built to what Meta has published (sources and quotes: `components/creative-diversity/META.md`), in Meta's words. Each rule says whose it is: **Meta** = Meta's own guidance · **ours** = our working rule built on it. The machine-readable copy is `rules.json`; `audit.py` grades every brand against it; the approval card enforces it per ad.

Live page: The Diversity System — (team page)

## 1. How Meta picks an ad (why this works)

**Andromeda** narrows tens of millions of ads to a few thousand per person using a fingerprint of each ad, and Meta says it returns "a more diverse set of ad candidates". **GEM** ranks them, reading each ad's "creative representation" against what that person has done. Meta "groups together ads that share key visual and thematic attributes. When multiple ads look or feel alike, these are seen as variations of the same creative." **The creative is the targeting.** Our job: one clean place for Meta to learn, and a steady supply of genuinely different creatives.

## 2. The setup

| Level | Rule | Whose |
|---|---|---|
| Account | Pixel + Conversions API send Purchase with value; ad sets optimise for value | Meta |
| Campaign | One Advantage+ sales campaign per offer, budget on the campaign; every ad links to that offer's one page | Meta + ours |
| Ad set | **Who the offer goes to: one avatar + one angle** (`adset_<brand>_<avatar>_<angle>`). A few angles will hit; each reads on its own. With Advantage+ Audience the ad sets share broad targeting, so the creative carries the match | ours (the owner, 28 Sep, reaffirmed 8 Oct) |
| Ads | 6–10 live creatives per ad set (max 50); each is one persona × angle/awareness × format | ours (Meta: fewer ads) |
| Assets | Each ad is a flexible ad, up to 10 assets: 9:16 video with music/voiceover, 4:5, image, carousel if it fits; different faces and settings; ≥20% of the ad set's assets 9:16 with sound; key messages in the safe zone | Meta |
| Creators | Partnership ads | Meta (19% lower acquisition cost) |

**The one offer:** Brand B → WIDGET (`widget.brand-b.example/widget/`) · Brand A → face scrub (`recipe.brand-a.example/brand-a-facescrub-cpk/landing/`).

**Budget:** each ad set needs about 50 results a week to exit learning (Meta), so the campaign's daily budget is about **7 × cost per purchase × live ad sets** (ours). Face scrub break-even $__: ≈ $__/day per ad set, ≈ $__/day for its two. Add ad sets as budget allows.

## 3. A new creative

Meta: diversification is "truly different in look, feel, storyline, and message", for different personas or use cases. Iteration (same visuals, new text or CTA) "should not replace true creative diversification".

Every new creative must:
1. Be **3+ moves** from the nearest running creative (persona · angle · awareness · format · face · setting · look). Inside one ad set the avatar and angle are fixed, so the moves come from **awareness · format · face · setting · look**. *The threshold is ours; Meta publishes none.*
2. Use **footage the Page hasn't shown**. Meta counts fatigue by the image or video across every campaign on the Page.
3. **Link to the one offer page** and carry the core message.
4. Have **sound** if it's 9:16 video.

Iteration (hook text, caption, CTA, music swap) happens only inside a creative that already counts as new.

## 4. The weekly loop

| When | What | Tool |
|---|---|---|
| Monday | Read: one Meta pull per brand; tag; map; grade | `creative-diversity/pull.py` · `tag.py` · `matrix.py` · `meta-strategy/audit.py` |
| Tuesday | Brief to the gaps; every brief scored before it's made | `creative-diversity/check.py <brand> who=… awareness=…` |
| Thursday | The week's new creatives go into the ad set as **one batch**; out go what Meta marks *creative limited* / *creative fatigue* | approval page (Approve → On) |
| Daily | No edits while learning; the Ad Desk judges each creative against break-even | `components/media-buying` |

## 5. Where it's enforced

| Check | Where | Blocks? |
|---|---|---|
| Ad set = avatar + angle | uploader naming (`brands/<brand>/meta/account.json` → `adset_<brand>_<avatar>_<angle>`) | by construction |
| The one offer page | approval card `offer` | yes |
| Sound on 9:16 | approval card `sound` | yes |
| New footage | approval card `new_footage` | yes |
| 3+ moves | approval card `diversity`, scored when you approve (Gemini reads the ad) | yes (variation blocks; risky passes with a note) |
| Approve On / Paused, new ad set turned on with On | approval page | by construction |
| Account vs the setup | `meta-strategy/audit.py` scorecard | report |

## 6. Not Meta, never build on

"Entity ID" · ">60% similarity score" · "8–15+ ads per ad set" (Meta says fewer ads, more assets) · "similar ads pay higher CPMs".

## 7. Section swaps are graded by Meta (2026-10-08)

Run each section swap (a new hook, proof or offer staging) as its own asset inside the version's flexible ad. Meta then reports spend and purchases per asset (`body_asset`, `title_asset`, `video_asset`, `image_asset`), so every section earns its own score. Confirmed on a live Brand A ad (`creative-diversity/META.md` §7). This is the score the section index and the mix-and-match generator will run on.

**Watch:** when an ad is duplicated in Ads Manager (a "- Copy" ad set) and the original archived, the approval card still holds the old ad id. The daily read has to follow the copy, or results stop joining back to the brief.
