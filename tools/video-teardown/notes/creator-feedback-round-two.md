# The brief from her side — round two

*18 September 2026. the creator manager (content manager) on the Brand A and Brand B
briefs: "a bit overwhelming for the creators with all the long texts and
explanations… some HTML sections… a creator decided to opt out and some
went silent after receiving the brief." Her ask: back to the very first
brief's shape — simple video ideas, suggested shots, key direction — and
the same four intro sections for both brands. Artifact: The Creator Brief,
Simplified (URL in `context/artifacts.md`).*

## What went out (read from the Docs, 18 Sep)

65 Google Docs across 15 creators, one per video, 1,329 words each on
average. Every Brand A Doc was the round-one one-sheet (7b v3): the idea,
six locked "say these" lines, the one shot, 8–13 beats, six openings,
wear · where, the full script, four AI pictures. 4bu_m's four Brand B Docs
were the image machine's designer work orders (JSON, plate prompts, build
data) — the "HTML sections".

| Creator | Docs | Words |
|---|---|---|
| 4bu_m | 5 | 12,711 |
| briluv50 · danisidor · just-janci | 5 each | ~6,700 each |
| ambrosial-jax · glamwithpammie · jodileabeauty · selfcarebykerin · lucianapatton · jojo-moran · elenaglow50 | 5 each | 5,500–6,200 each |
| thekeziahaynes | 4 | 4,559 |
| mara-creator | 3 | 3,783 |
| creator-handle | 2 | 2,976 |
| rudystylee | 1 | 1,087 |

## The diagnosis

Round one split the spec from the page but kept the page a *shot list*:
still six openings, still a script, still one Doc per video with no cover.
The brief creators said was easy (the first one, Creator E's, 2,050 words for
five concepts) was one document: intro, education guide, delivery
requirements, brand direction, offer — then five concepts at ~250 words
each with two hooks, five beats, must-have shots, product points.

## the owner's rulings on the first sample (18 Sep)

"I still want the separated briefs" · "we still want the script too but
that's it really" · "remove the image from the google doc itself" — then,
on a pictures file beside the brief: "we literally don't need the pictures
in the google doc." So: one Doc per video, concept + script, words only.
Video inspiration is shared by hand.

## The fix (built 18 Sep)

- **Stage 7b v5 — the concept.** Format · inspired by · product · length ·
  core idea · two hook directions · five beats · must-have shots · product
  points; the machine appends the script from the spec. 180–280 words
  before the script. No pictures. v3 (one-sheet) and v4 (concept with a
  picture, for a per-creator pack that was dropped) are archived.
- **`machine/simplify.py` — rebuild a creator's folder.** A "Start here"
  Doc (the brand's `channels/creators/brief-intro.md`: introduction,
  Creator Education Guide, Content Delivery Requirements, Brand Direction,
  Offer & CTA Direction) plus each of her briefs rebuilt. Staged in the
  unshared `work/<handle>/` by default; `--send` updates the Doc she already
  has in place (same link, same title) and puts Start-here beside it.
- **run.py.** The per-run Doc still goes to BRIEFS as before; only its
  contents changed. The script block is appended for every 7b version.
- **Brand intros.** Brand A's lifted verbatim from the first brief;
  Brand B's written in the same four sections from `position.md`,
  `offers/guarantees.json` and `offers/offer-bank.md`.

## Sample built, nothing sent

Creator E's folder, staged: Start here (519 words) + two briefs (895 and 790
words, were 1,643 and 1,333). The rest wait on the owner's word.

## Open

- Brand B has no creator contact address (`contact.md` says OPEN) and no
  Creator Education Guide; the Start-here carries the short version.
- 4bu_m's four image work orders should leave his BRIEFS folder.
