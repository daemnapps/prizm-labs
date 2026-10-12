# Video variations — proven ad → new format (the owner's copy)

Take ads that already sold, tell them again in a fresh format someone else proved, and run each one through the chain to a brief. One batch at a time, as many times as you like.

Page: **Creative Run Builder** — (team page)

## The 5 steps

1. **The grid.** Proven winners down the side, fresh format swipes across the top.
2. **Winners broken down.** Each winner has its 1 Teardown, 1b Doctrine and transcript.
3. **Formats broken down.** Each format goes 0 Triage → 1 Teardown → 2 Spec. The spec is the format's shot-by-shot baseline.
4. **You pick squares.** Each picked square runs the chain below.
5. **Again.** A new batch is a new file; the page rebuilds from it.

## The chain, per square

- **Winner:** 1 Teardown → 1b Doctrine (the content we carry: script, mechanism, proof, offer logic)
- **Format:** 0 Triage → 1 Teardown → 2 Spec (the baseline)
- **3 Injection** — the winner's content + the product + the offer go into the format's 2 Spec
- **Stage 4 loop** — 4a Reading · 4b Hooks · 4c Placement · 4d Expansion · 4e Close · 4f Audit · 4g Spice (you pick which run)
- **5 Brief**, AI lane
- **Viewer Check** (Marketing Chain Checks) — runs by itself after every brief. Fails go back: opening → 4b Hooks, middle → 4c Placement, close → 4e Close; two fails → held for you
- **6 Frames**
- **7 Final brief**

## Standing rules

- Video winner → video format only, for now.
- Face scrub runs ONE offer: buy 2, get 1 free.
- One cut per winner — when two winners are essentially the same ad, keep the top seller.
- A format has to fit the avatar.
- You pick the squares. Nothing is ever queued for you.
- Questions come to you in chat, plainly — never on the page.
- The page is the grid: nothing above it, no tabs. Each square shows its chain stage, a "Run to" picker and Activate. Thumbnails play the video. The chain sits under the grid.

## Start a new batch

Say **"new batch"** and name the winners and the formats (or say "same winners, new formats"). The session copies the last batch file, fills in your list, checks both sides are broken down, runs whatever's missing, and rebuilds the page at the same link.

## Trigger words

- **"new batch"** — start a new grid from your list of winners and formats.
- **"run the queue"** — the session takes the squares you activated through the chain, to the stage you picked.

## 3 Injection — how the winner gets in (live 2026-10-05)

The chain's own stage 3 Injection prompt is filled for the format (its 2 Spec, brand files, product, AI lane). One new section is added to it: **the winner's content** — its full transcript (from 1 Teardown) and its 1b Doctrine — with five rules: the format's structure stays locked; what's said comes from the winner, in the winner's order; anything the format can't carry is listed as DROPPED FROM THE WINNER; product facts only from the brand files; one offer only. That section is its own prompt file: `prompts/stage-3-winner-slot/stage3-winner-slot-v1-damon.md`. Each square's full prompt is saved as `runs/ad-variations/<brand>/p2f-<winner>__<format>/sent.md`, and its Injection as `3-injection.md` beside it.


## Running the squares efficiently (2026-10-07)

Why it was burning usage: every stage was hand-written inside a chat session, which reads a ~550 KB prompt in pieces and re-sends it each time (4–5× the cost), the prompts pasted big blocks several times (brand position 6×, story 4×, product 3×), every stage ran on the top model, and 28 squares went at once so every rework multiplied by 28.

What runs now:
1. **Each stage's prompt is read once**, never re-read in pieces.
2. **Each block once.** A long block (position, story, product, identity…) goes in at its first mention; later mentions point back to it. Roughly halves the biggest prompts.
3. **Right model per stage.** 4a Reading and 4f Audit on Sonnet (they read and check); every writing stage on Opus.
4. **One square first, then small batches.** Take one square all the way to 5 Brief, read it, fix what breaks, then run the rest a handful at a time.
5. **Holds:** the swipe's own format holds pass automatically; audit fails on claims, the offer or brand rules get fixed (one call), never passed.

Claude stages are written from this session (the owner, 2026-10-07: the sign-in is not important — just work).

Run it:
```
python3 machine/proven_to_format.py run brand-a-face-scrub-2026-10 --square <one square run name>   # one square first
python3 machine/proven_to_format.py run brand-a-face-scrub-2026-10 --limit 5                        # then a few at a time
python3 machine/proven_to_format.py page brand-a-face-scrub-2026-10                                 # refresh the grid
```
Squares resume from the repo (`runs/video-teardown/<brand>/<run>`) on any machine and file back there when done. Status of every square: `runs/ad-variations/<brand>/<run>`.

## Into production (2026-10-08)

Once a brief is green: **elements** (what each ad needs — banked or to make, each shown as a picture) → the missing ones get made from the real swipe frames → you say **"elements ok"** once for every ad → **production** takes it from there. The teardown now saves every frame (8 a second) and cuts each person, place and prop out of its frames, all on the Drive beside the swipe, so elements start from the real thing and the picture generator gets the swipe frame it's recreating.

## To the editor (2026-10-09)

Once an ad's clips are made it goes into **the editor's queue**: one folder per ad on the Drive under the shared drive → handoffs → video-editor → <brand>, named by its brief number (`brand-a_glow-face-scrub_brief-0292`). Inside: the clips in scene order, the voice, music and sounds, the timing, and an editor brief (what the ad is, every scene's words, what can't change, known clip faults, where to drop the finished cut). You assign a brief number; the editor opens that folder.

---

## For sessions (technical)

Batch files: `definitions/proven-to-format/<batch>.json` (today: `brand-a-face-scrub-2026-10.json`, schema in its `_schema` line). Engine: `machine/proven_to_format.py`, standard library only.

```
python3 machine/proven_to_format.py check <batch>             # readiness, both sides, plain words
python3 machine/proven_to_format.py prep  <batch> [--go]      # run.py commands to fill gaps (--go runs them)
python3 machine/proven_to_format.py page  <batch> [--refresh] # rebuilds page/creative-run-builder.html
python3 machine/proven_to_format.py queue [<artifact url | requests.json>]  # how to work the page's requests
```

- `--root <dir>` on check/prep/page reads an alternate tree when this checkout is behind the shared one.
- `prep` builds `tools/video-teardown/machine/run.py` commands: formats to `--to 2` with `--route ai`, label `fmt-<name>-<code>` (the chain lowercases it into the run folder); winners resumed `--from 1|1b --to 1b`. It never queues a square.
- **Claude stages are written by the session, always** (the owner, 5 Oct 2026). Every `prep` command sets `DAEMN_HAND_DIR` to a `hand/` folder inside its run. At a Claude stage the run stops and leaves `<stage>.prompt.md` there; the session writes `<stage>.md` beside it, then runs the same command again with `--from <that stage>`. Every check still applies. This is the normal path — never ask the owner to sign in. (Today's two format runs, `fmt-tv-shop-dd7gvdvprzl` and `fmt-creator-a-dd12vx6inuo`, had 1b Doctrine written this way.)
- `page` caches thumbnails, Drive play links and sales stats in `page/builder/cache/<batch>/` (`--refresh` rebuilds from the Drive mount and the winner record `the team notes`). Template: `page/builder/proven_to_format_template.html`. It writes the file; publishing over the same link is a separate step.
- Doctrine file name: 1b Doctrine writes `stages/1c-doctrine.md` (chain.py `FILE_ID`/`DISPLAY_ID`).
- The old one-step shortcut `machine/format_swap.py` + `prompts/stage-format-swap/` is superseded by this chain; kept for the 3 earlier specs.
- Pending (the owner's sign-off): a winner-content input slot in `tools/copywriter/prompts/video/stage-3-injection/stage3-injection-v*-damon.md` (winner's 1 Teardown transcript + 1b Doctrine). Do not edit that prompt without it.

**Known gap (2026-10-06):** stage 5 Brief fills its top "Core message:" line from the SWIPE's teardown (THE CORE MESSAGE), so a proven-ad → new-format brief opened with the swipe's message (food tests, mascara). Fixed by hand on the written briefs with Brand A's core message from `the team notes`. In this chain the line must come from the winner/brand, not the swipe — check it on every brief until stage 5 reads it from the winner.
