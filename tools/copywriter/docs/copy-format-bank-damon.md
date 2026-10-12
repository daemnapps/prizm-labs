# Copy Format Bank — rebuilt from real ads only (2 Oct 2026)

the owner: "We're first going to use the formats that directly came from the ad account, nothing that we generated or wrote. We're just going to use foundational copy that we already sourced, not generated." Each brand and each avatar has its own formats, and every format shows where it came from.

## How a format gets into the bank
Ad account (top 25 by spend + top 25 by lowest CPA, nothing else, `library/meta_copy.py`) → the words exactly as they ran → with their numbers (spend, purchases, CPA, ROAS, dates) → stripped to a format by the copy teardown (named blanks, nothing added) → filed under brand › avatar (avatar from the ad set name, else read from the words with the line that shows it; the owner confirms the unclear ones).

To write a new ad: brief (brand + avatar + angle) → pick a format from that brand + avatar, best numbers first → fill the blanks from the language bank (hard fills, like hooks) → card, each text naming its format and source ad.

## One row per real thing, never duplicates
the owner: "I don't need duplicates … we can know that it was duplicated, but I just need to see what the actual thing was." The pull writes two de-duplicated indexes: **copy** (one row per distinct primary text / headline / description) and **creative** (one row per distinct video or image). Each row lists every ad that ran it, adds up spend, purchases, CPA and ROAS across them, and says why it is in (top spend, low CPA, both). Copy rows and creative rows point at each other. The list can be shorter than 50. The ad account's results get indexed the same way next.

## What every format carries
Id `copyformat_<brand>_<avatar>_NN` · the source ad (id, Meta name, dates) · numbers (spend, purchases, CPA, ROAS, why it is in) · the original words · the format with named blanks · slot (primary text / headline / description) · brand › avatar with evidence.

## Taken out
- competitor-c (35 primary texts) and competitor-d (88 headlines, 50 pages) — removed from the library.
- The 4 tool formats (short-form, caption, long-form, social proof) — written by us; retired for ad copy once the real bank has formats.
- 250 bodies the copy tool wrote across 56 runs — tool output, never a format.
- The copy set (short / standard / proof, 2 Oct) — invented structure, withdrawn.

## Where it stands
Brand B: the 25 + 25 pull is built and tested offline; runs once Meta's usage meter is back down (~55 small calls). Brand A: same pull, after Brand B.

## The raw material, pulled 2 Oct from our database (no Meta calls)
the owner: "if that data has already been pulled, then we can just use that. Same with Brand A." Read from the warehouse's nightly copy of Meta (`meta_ad_insights`, `meta_ads`) with `library/meta_copy.py --brand <b> --from-db`.
- **Brand B** (1 Jan – 23 Sep 2026, 1,094 ads): 47 picked → 45 distinct primary texts, 40 headlines, 63 distinct videos/images. Biggest: "<ad 1 headline>" ($__, CPA $__, n ads) and "<ad 2 headline>" ($__, CPA $__, n ads).
- **Brand A** (19 Nov 2024 – 1 Oct 2026, 1,198 ads): 46 picked → 7 distinct primary texts, 26 distinct videos/images. Biggest: "<ad 1 headline>" ($__, CPA $__, n ads). 7 ads have no words on file.
- Near-identical texts (97%+ the same, e.g. one link line changed) are one row; the edits are kept as versions. A flexible ad's numbers count toward every text in it.
- Meta's stored pictures expire after a few days; each creative links to its Instagram post instead.
- Files: `runs/copywriter/<brand>/meta-copy/2026-10-02-db/copy.json`.
