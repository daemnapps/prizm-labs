# The standard brief: one static ad

Every static brief is this page, filled in. Same title line, same box, same nine
sections, same order, same tables, every time. Ruled by the owner, 2026-10-02:
*"we need a standardized briefing document literally."*

v2 (2026-10-27): the separate Headline options and Picture options sections are
one **Variations** section: the five rows stage 5 wrote as data, each ONE
change off the approved picture. The approved picture plus those five is the
batch of six (the owner: *"It'd be 6 total images in that batch: 5 unique
variations from the initial one that we made."*).

v3 (2026-10-29): section **3 · The picture** is written for the picture chain of 2026-10-28 (components/
image-production, "Every picture: a 3D set, printed, then the words"). It opens with the concept and the moment's
palette (stage 3 v13, THE CONCEPT), then says what the 3D set holds: every surface and prop at its real size, the
moment's name on its prop, the camera and the light as facts, the product from its own true-size build. Same title
line, same box, same nine sections, same order.

How to fill it:

- Copy everything between the two `=====` lines. Replace each `<…>` with the
  real thing. Keep every heading and every table header exactly as written.
- Plain words. Someone who has never seen the swipe, and reads English as a
  second language, must understand it. No stage names, no file paths, no
  internal ids, no jargon.
- A section with nothing in it says `None.`. It is never removed or renamed.
- Words that go ON the ad are written exactly as they will be set, in
  `code style`, one line per line on the ad.
- Anything a person must decide goes in section 9, numbered, one question per
  line, so the owner can answer "1 yes, 2 no".
- Every brief ships with its run sheet: `RUN.md` and `run.json` beside it in
  `deliverable/`, written by `components/briefs/runsheet.py <brief key>`. The
  brief says what to make; the run sheet says how, for any tool (the Higgsfield
  web app, Claude Code, Codex). Its core is Higgsfield. The run sheet is never
  pasted into the brief, and the nine sections above do not change for it.

=====
# BRIEF · <brand> · <product> · <short name of this ad>

| | |
|---|---|
| **Core message** | <the breakdown's `Core message:` line, word for word: the one belief this ad leaves behind. Every zone on the ad carries it or sets it up.> |
| **For** | <the sub-avatar, or the avatar, by name> · <what she wants, in her own words> |
| **Built on** | <the swipe: brand and ad name> · <where it was captured> |
| **Made by** | <who makes it, from the order; otherwise "the statics designer"> |
| **Size** | 9:16 (1080×1920). Everything that matters sits inside the centre 4:5. |
| **Offer** | <the offer in full, in the order's own words> |
| **Deadline** | <the deadline line, word for word, or "None"> |

## 1 · The ad in one line
<One sentence: what the ad shows and why it stops her.>

## 2 · Who it's for
<Two sentences: who she is and what she already believes that this ad answers.>
> "<one quote in her own words>" — <where it came from>

## 3 · The picture
**Concept:** <the concept in one line, from THE CONCEPT; or "none (made before the concept step)">
**Moment palette:** <three or four colours with hexes; or "the brand palette">
**The set:** <every surface and prop in the order the eye meets them, each at its real size in cm and what it is made of; the moment's name on its prop, word for word>
**The person:** <who is in frame, pose and the one thing the face does; or "none">
**The product:** <where it rests and which side shows, from its own true-size build; or "No product in frame.">
**Camera and light:** <where the camera stands (height, distance, lens) and the light as facts: where it comes from, how hard, what colour, where the shadow lands>
**How it is made:** 3D set at true sizes, printed into a photo with the product's casting sheet, the words set on top inside the centre 4:5.

## 4 · The words on the ad
| Where on the ad | Words, exactly |
|---|---|
| <headline> | `<words>` |
| <every other line, top to bottom> | `<words>` |

## 5 · The offer
| Line | Words, exactly | Can it change? |
|---|---|---|
| <offer line> | `<words>` | No |

## 6 · Variations
The approved picture first, then the five variations, each ONE change off it. Six pictures in the batch.
| # | What changes | Words on the ad, exactly | The picture change |
|---|---|---|---|
| 0 | Nothing: the approved picture | `<the main headline>` | None |
| 1 | <the row's label> | `<the row's words, every zone, / where a line breaks>` | <the row's picture change, or "None: words only"> |
| 2 | <…> | `<…>` | <…> |
| 3 | <…> | `<…>` | <…> |
| 4 | <…> | `<…>` | <…> |
| 5 | <…> | `<…>` | <…> |

## 7 · Never on this ad
- <one thing per line>

## 8 · Check before you hand it in
- [ ] <one yes/no check per line, 3 to 6 of them>

## 9 · Questions for the owner
1. <one decision per line, or "None.">
=====
