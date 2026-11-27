---
name: statics-sprint
description: Run a whole round of natural static ads from one line, start to loaded — our winners and our own swipe library in, the first picture of each ad with the words set in code, one page to look at, then a brief per ad handed to the graphic designer for the five versions, then the approval page. Use whenever someone says "statics sprint", "new static sprint for <brand>", "run statics for <brand>", "more offer statics", "natural statics", "<moment> statics" (Black Friday, Christmas, Valentine's), "reskin the statics for <moment>", "use the <winner> angle for statics", "statics off our last 14 days", "hand the statics to the designer" (or to the designer by name), "turn the statics into briefs", "hand off the statics", or "load the statics".
---

# Statics sprint

> **Activates component:** `components/ad-variations` — `machine/natural_statics.py` (start, comments, copy, check, draft, page, number, file, status).

External dependencies: `components/ad-variations/`, `components/winners/` (the winning statics and the bank), `components/swipe-paid/` and `components/swipe-organic/` (our swipe library), `components/image-production/` (story captions), `components/meta-upload/` (copy that ran, the approval page), `components/promo-calendar/` (the moment and its window), `brands/<brand>/` (offer bank, rulings, customer words; read only), the Drive folder `Shared Assets/brands/<brand>/` (customer photos, product pictures).

One line starts it: **"statics sprint · <brand> · <moment> · <n> ads"**. Anything left out is read, never asked: the moment is the one running now (next one if it starts within 7 days), the avatar is the brand's core one, the count is 5, the page is the cheapest per sale right now.

## Run it straight through. Two stops, both the owner's.

| | Step | Stop? |
|---|---|---|
| 1 | Read the facts | no |
| 2 | Find why men bought | no |
| 3 | Pick swipes and pictures we own | no |
| 4 | Write and draft | no |
| 5 | Show the page | **look** |
| 6 | Number, hand the versions to the designer | no, once the owner says hand off |
| 7 | Approve | **the owner's click, never ours** |

Never stop between 1 and 5 to show a plan, a table of options or a list of swipes. The first thing the owner sees is finished drafts.

### 1 · Facts
Offer line, window, banned lines and guarantee wording, word for word from `brands/<brand>/products/offer-bank.md`, `rulings.md`, `team/owner-rulings.md` and the promo calendar. Stock: what is low is not promised, what is not true now is not said. These fill `offer`, `moment`, `until`, `never`, `prices`. The page is the cheapest per sale over 7 days; the same ads on both pages settle a tie.

### 2 · Why they bought (before any picture)
- **Each ad speaks to one sub-avatar** (`sub`, `awareness`, `desire`, `pain` on the ad): his card in `brands/<brand>/core-avatars/` gives the picture, the line and the caption, at his awareness stage. An ad with its own `copy` opens in his signed angle or a customer's words; the second text already ran.
- `python3 components/winners/winners.py statics --brand <b> --days 14`, then the bank for older winners.
- `natural_statics.py comments --brand <b> --ads <ids>`: the ad's own comments, most liked first. Read what people say back to it.
- Customer words from the brand's language bank.
- Name the reason per ad in two or three words (straight talk, the push to stop waiting, owners vouch, risk on us, a gift he'll use). **What sold is the reason and the voice, never the lighting or the prop.** A variation that moves a prop is the same ad.

### 3 · Swipes and pictures
- **Our library first**, banked swipes and our own ads. Never a fresh outside pull unless the owner asks.
- Natural beats designed: a real phone photo, a story bubble, handwriting, a note, a comment thread. Real photo or AI-made, whichever this person is likeliest to stop for; never one source for a whole round. AI-made goes through `image-production`.
- **Open every picture before using it.** One with words already on it is refused unless our words fully cover them; an old price showing is the usual fault.
- Holiday creative is dressed for the moment everywhere: picture, words and the copy beside it. No line from another moment.
- A customer-voice post stays in that customer's voice. Never turn it into a sales line.

- **The creative matrix first.** `python3 components/creative-diversity/creative_matrix.py make <brand> <batch> --people <sub>:<n>,…`, then `check` and `lock`; each run gets its row with `cell`. Nothing is made until the grid passes. Before drafting, `python3 components/creative-diversity/creative_plan.py board <brand> --who <sub-avatar>` (what is taken), then `creative_plan.py claim <brand> <id> who=… …` for each ad: every one 3 or more moves from all others. The five headline versions are one creative.

### 4 · Write and draft
`natural_statics.py start …`, then `natural_statics.py who <sprint>` (who each ad is for and the one doubt it closes: read it before a line is written), fill `sprint.json` (each ad names `sub_avatar`, `desire`, `awareness`, `doubt`), then `copy`, `check`, `draft`.

| Layout | It is |
|---|---|
| `story` | a real photo, story bubbles |
| `tag` | a real photo, a tilted tag (covers a caption already on it) |
| `note` | a typed phone note |
| `letter` | black letter, product cutout, big headline |
| `comments` | real comments word for word, names hidden, real like counts, each with its source |
| `plate` | a clean photo, headline above, gold plates (`boxes` covers a plate already in it) |
| `list` | a phone checklist, everyone ticked off but him |
| `thread` | a text thread, one answer changes; a link card carries the offer |
| `search` | a search, its suggestions, the one answer (no search company's look) |

- **We make the first picture of each ad; the graphic designer makes the five versions** (owner, 2026-11-25). All six lines are still written here: the control and exactly five versions (`check` refuses any other count), **each version changes one line only**. More different ads beats more versions. `lines` uses ` / ` for a line break.
- Every ad carries `why` and `receipt` (the winner, swipe or customer words it comes from).
- **Copy beside the ad is never freehand.** Two or three primary texts, two or three headlines, two descriptions, chosen from `copy` (lines that ran). Only the offer may be matched to today's. `check` refuses a line that never ran, because the card would read "Copy not checked".
- `check` must print clean. `draft` makes the first picture of each ad. Then look at every one in `drafts/` and fix what you see: overlaps, old words showing, a smudge, a cut-off. The owner never finds it first.

**Never on a picture:** an old price, a banned line, a long dash, a made-up comment, a claim that is not true today, a man's face without his yes, the founder's face unless this round's order asks for it. A reused campaign keeps its reason and drops its story when the story is over (a closing-down campaign comes back with no closing in it).

### 5 · The page
`natural_statics.py page …`, published over the brand's one statics page (same link every round; follow the `owner-pages` skill when it is available). On top: what needs the owner now. Then each ad with its reason, its first picture and the five lines the designer gets, then the copy. The reply in chat is the link and one question: **hand these to the designer?**

### 6 · Number and hand off (after the owner says hand off, turn them into briefs, or names the designer)
Before packing: no expired freebie, price or date in any line or caption (the owner's latest word outranks copy that ran).
`number`, then `assign` (packs one design assignment per ad: the first picture, the clean photo, five exact lines, and its delivery checklist with six slots), then `assign --publish` puts them on the Drive, where the designer's waiting list picks them up. Never message the designer. Her pictures come back through the `brief-handoff` skill, with the checklist filled.

When the five are in: `file --dry-run`, read every card, then `file`, then `status` (it refuses an ad with fewer than six pictures). Ask for load in one question that names every gate that will hold the round.

All must read ready, copy checked, our copy, right picture count.

Two gates hold natural statics today. The tool never turns them off:
- **Picture origin** (image-production GATE-5): refuses a picture not made by the image tool.
- **Lowest-cost words** (meta-upload): swaps the card's words for the cheapest proven ones, which on a promo card can be copy from a finished campaign.

If the owner's yes named the gate for this round, record that exception for exactly these files with their words and date, and file. If it did not, stop and ask once. Never carry a yes from an earlier round. If a gate was changed for good by its owner, follow the gate.

After filing, `status` must show `our_copy: true`. Swapped words (the dry run already shows them) go back only when the owner's yes named that gate; with no yes, report the swap and ask.

### 7 · Hand over
One line: how many are loaded, the approval page link, what must come down and when. Approve is the owner's click; never approve, upload, go live or spend. Save the round's folder and update the session's card.

## Next moment, same ads ("reskin for <moment>")
Copy the round's folder to a new label, change `moment`, `until`, `offer`, `never` (add the old moment's words), rewrite the lines in the same voices, keep the pictures. Run from step 4. A card still waiting is re-filed with `--replace`; one already approved or live is left alone and the reskin files as new.

## Where it lands
`runs/ad-variations/<brand>/<label>/` (sprint.json, drafts/, page/, briefs.json, words.json) and one run per ad beside it. Pictures never enter git.
