---
name: winners
description: A brand's proven ads and what they did for the writing prompts. Audit its creatives for a time frame (every ad that spent, copies merged, ranked by purchases, tagged, the Core set marked, on one board), keep the bank of winners, feed the hook prompt, and score which prompts and borrowed winners made money. Use whenever someone says "audit <brand>", "top creatives for <brand>", "what's working on <brand>", "score <brand>", "which hooks are winning", "winner bar", "set the bar", "show me the winners", "bank the winners", "what do we brief next", "which winners have no brief", "categorize the winning messages", or names a brand and a period to analyse ads for.
---

# Winners

> **Activates component:** `components/winners`: `winners.py`, the one command for Results, Audit, Bank, Feed and Score.

External dependencies: `components/winners/` (the engine; `CLAUDE.md` is the contract, `README.md` the how-to), the warehouse (read through funnel-tracking), Meta (read only, through meta-upload's brand config), `components/video-teardown` and `components/image-teardown` (teardowns, on a person's go), `runs/winners/<brand>/` (where everything lands). Keys by name only, through `components/keys/loader.py`; never printed, never asked for in chat.

The person says the brand and the time frame. You run everything and hand back the result. Never show a key, an id or a path. Report facts: the numbers and what the tags say. Never a verdict; the person decides what's right. Run with `/usr/bin/python3` from the workspace root.

## Which one they asked for

| They said | Do |
|---|---|
| "where is <brand>", "what's missing for <brand>", "is <brand> ready", "run the winners system" | `winners.py system --brand <brand or all>`: every step from ad results to a brief, its state and the next step. Run each free `todo` it lists in order; stop at `owner` (the bar, a new message group, profile sign-off) and `spend` (teardowns) and say what waits |
| "show me the winners", "what's in the bank" | `winners.py status --brand <brand or all>` |
| "audit <brand>", "top creatives", "what's working on <brand>" | steps 1 to 5 below |
| "score <brand>", "which hooks are winning" | `winners.py score --brand <b> [--days N]`; report the roll-ups from that day's `score.md` |
| "winner bar", "set the bar" | `winners.py bar --brand <b> --min-spend N --max-cpa N --min-roas N` with the numbers the person gave. No numbers: run `bar --brand <b>` and read back the bar. The bar is theirs; never pick one. `--open` clears it. |
| "bank the winners" | `winners.py bank --brand <b>`, then `winners.py status --brand <b>`, then step 6 |
| "what do we brief next", "fill our gaps", "which winners have no brief", "categorize the winning messages" | step 6 |

## 1 · Pin the brand and the window

- Brand = the warehouse brand key. A brand that is not in the warehouse needs its own Meta connection in meta-upload's brand config; if it has none, say once that the brand's Meta access is missing and stop.
- Window: turn the person's words into dates ("last week" = the previous Monday to Sunday; "Q3" = Jul 1 to Sep 30; "this year" = Jan 1 to yesterday). No window given: the trailing 90 days to yesterday.
- Reading Meta for days the warehouse lacks is read only, and it happens only because the person asked for this audit.

## 2 · Run it

`python3 components/winners/winners.py audit --brand <b> --since <d> --until <d> --title "<BRAND AS WRITTEN>"`

It pulls, merges, ranks, fetches pictures, copy and links, writes contact sheets for anything the brand's tag memory lacks, and builds the board. If nothing is left to tag it banks the window and rebuilds the feed, and you skip to step 4. If it says creatives still need tags, go to step 3.

## 3 · Tag what the memory lacks

- Before tagging, if the brand's board is already published, read its saved recategorizations (the `recat` collection, through the artifact data tool) and fold them into the file you pass to `tag` as `{"<creative name>": {"group": .., "on_screen": ..}}`.
- **What's on screen:** look at every `sheet_NN.jpg` in the window's folder (labels R<rank>) and pick one type per ad from the fixed list in `audit.py` (`ON_SCREEN`). More than about 3 sheets: split them across helper agents on the top model, because these tags drive the analysis, each with the list and two reference pictures of the brand's founder if it has one. Spot-check 30 at random yourself.
- **Caption line** (saved as `message`): from `to_tag.json` (headline and opening line). It sorts the board; it never says why an ad sold. The message is the teardown's, in step 6. Reuse the brand's existing message names from its `tags.json` first; same copy as an already-tagged ad = same message; add a new name only when none fits.
- Save: write the tags to a scratch file as `{"R12": {"on_screen": .., "message": ..}, ...}`, then `python3 components/winners/winners.py tag --brand <b> --window <since>_<until> --tags <file>`. That saves them, rebuilds the board, banks the window and rebuilds the feed.

## 4 · Publish

- One board per brand, kept for good, so the link survives every re-run. Look up "<BRAND> Top Creatives" among the person's artifacts. Found: read it, then republish `board.html` over that link. New brand: publish it as a new artifact with capabilities `{db: {rules: [{path: "", read: "view", write: "admin"}]}}`, which keeps the Type picker working.
- `summary.md` beside the board is the written copy for the team.

## 5 · Report

The board link, the Core set's size and share of purchases, the top 3 types, then each core message with its sales and cost per sale (step 6). Facts only. Nothing about the machinery.

## 6 · Every analysis ends here: winners by core message, and what to brief next

The message is already written: every teardown ends with THE CORE MESSAGE, the spec says what is load-bearing, the doctrine read names the desire. Read those. Never group by caption, hook or your own reading of a script.

1. `python3 components/video-writing/machine/winner_index.py build --brand <b>`: every winner's numbers with its message, as its run wrote it.
2. `winners.py messages status --brand <b>`: who is stuck, at which gate (proof, teardown, message, group, rules).
3. **Group** what is stuck there: compare the core message line with the brand's core messages in `runs/winners/<b>/messages/messages.json` and put it under the one that says the same thing. None does: show the person the line; a new core message is their yes.
4. **Rules:** read its load-bearing list against the brand's rulings, `runs/rulings/<b>.md` and the offer file. `whole` = nothing cut; `swap` = something cut can be refilled with a true thing (name both); `breaks` = a rule removes what the ad stands on. A reason, a price or a gift that is no longer true is always a cut.
5. `winners.py messages check --brand <b>` has to pass. Then `messages page --brand <b>` and republish "<BRAND> Brief Gaps" over its link.
6. Report `messages next`: the first three to brief, and what to tear down.

Each winner's story shape (after step 1): `winners.py shapes --brand <b> todo` lists the winners with no shape call and the files to read; write one call per winner into `runs/winners/<b>/shapes/calls.json` off its own teardown (arc, devices and formats only from the existing lists), then `shapes check` and `shapes build`. The writing's winner lane reads the built shape as the winner's section plan.

Brief one, on the person's pick: `messages start <run> --brand <b>` prints the command. It refuses a winner that is not through every gate. `--winner` is always named, so the script step reads that winner's message. When the brief is filed, add its code to that winner's `briefs`.

## Teardowns, only on the person's go, because they spend

`winners.py videos --brand <b> --window <since>_<until> --top <core size>` downloads the Core videos (the Facebook video page gives the original size; Instagram is the backup; ads whose videos were never posted publicly can't be fetched, so say which). Then the video-teardown machine (`components/video-teardown`) and the image-teardown machine for statics. File each teardown as `teardown.md` with its `transcript.txt` under the window's `teardowns/<NN-name>/`, mark the creative with `tag` (`{"<name>": {"teardown": true}}`), then `winners.py bank` picks up its words.

## Rules

- Read only on every ad account. No budget, no status, nothing goes live.
- Running the machine, moving files and lookups may go to a cheaper model; tagging, teardown reads and anything the person reads stay on the top model.
- Pictures, videos and contact sheets stay out of git.
- The bar stays open until the brand owner sets it. While it is open, every row is a candidate; say "candidate", not "winner", about a row.
