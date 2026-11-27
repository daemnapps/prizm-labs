---
name: ad-variations
description: Make variations from a proven winner, video or static. Static (a winning image ad): the winner as it ran, locked, with one-change rows (one line of words, or one element in the same picture). Video — re-tell an ad that already sells in fresh format swipes, square by square through the video chain to a finished brief. Use whenever someone says "make video variations", "variations of <winning ad>", "put <winner> into these formats", "new variation batch", "run the variations", "run the queue", "where are the variations", names a winning ad and some swipes, or asks to take a proven ad into new formats; for an image ad also "make variations of these winning image ads", "variations of our best statics", "black friday versions of the winners".
---

# Video variations — proven ad → new format

> **Activates component:** `components/ad-variations` — runs a proven winner through new formats, stage by stage.


External dependencies: `components/ad-variations/` (the engine `machine/proven_to_format.py`, batch files in `definitions/proven-to-format/`, the winner slot `prompts/stage-3-winner-slot/`, the doc `PROVEN-TO-FORMAT-owner.md`, the grid page `page/creative-run-builder.html`), `components/video-teardown/` (the chain every square runs on: `machine/run.py`, its working runs in `machine/runs/`), `components/swipe-organic/` (the format swipes and their format reads), `brands/<brand>/` (product, offer, avatar — read only), the winners record named in each batch's `sources`.

the owner, 2026-10-07: "let's standardize this process of creating video ad variations since we will do it a lot moving forward."

## What it is

A **winner** is one of our own ads that already sells (top by sales, already torn down). A **format** is a fresh swipe whose shape we borrow. Every **square** of the grid = one winner told in one format. The winner gives *what is said*; the format gives *how it's told*; the brand gives the product and the one offer.

## The chain, in the system's own stage names

- Winner side (must already exist): **1 Teardown** (with transcript) + **1b Doctrine**.
- Format side: **0 Triage → 1 Teardown → 2 Spec**.
- Per square: **3 Injection** (the chain's own stage-3 prompt + the winner slot) → **4a Reading · 4b Hooks · 4c Placement · 4e Close · 4f Audit · 4g Spice** → **5 Brief** (AI lane) → **Viewer Check** (automatic) → stop. **6 Frames** and pictures wait for the owner's sign-off on the brief.

## The steps

```
python3 components/ad-variations/machine/proven_to_format.py check   <batch>          # both sides broken down?
python3 components/ad-variations/machine/proven_to_format.py prep    <batch> --go     # formats to 2 Spec
python3 components/ad-variations/machine/proven_to_format.py inject  <batch>          # 3 Injection prompts; WAITING = write 3-injection.md
python3 components/ad-variations/machine/proven_to_format.py squares <batch>          # each written Injection → its own chain run
python3 components/ad-variations/machine/proven_to_format.py step    <batch> <square> # one step: WAITING / FIX / STOPPED / DONE
python3 components/ad-variations/machine/proven_to_format.py page    <batch>          # rebuild the grid
python3 components/ad-variations/machine/proven_to_format.py elements <batch>         # Station 3.1: element list per green ad (free)
python3 components/ad-variations/machine/proven_to_format.py approve  <batch>         # the owner's "elements ok" — every ready ad at once
python3 components/ad-variations/machine/proven_to_format.py produce  <batch> --go    # hand approved ads to production (Station 4)
python3 components/ad-variations/machine/proven_to_format.py editor   <batch> --go    # ads with clips → the editor's queue, one folder per brief
```

1. **Start a batch.** Copy a file in `definitions/proven-to-format/`, list the winners (path + their ad name from the winners record) and the formats (code, swipe record, library format id, Drive video). Brand, product, avatar, offer and route come from the brand — never typed from memory.
2. **`check`.** Every winner needs 1 Teardown + 1b Doctrine + transcript; every format needs 2 Spec. `prep --go` fills format gaps through the chain.
3. **`inject`.** Each square prints `WAITING <sent.md>`: write `3-injection.md` beside it from that prompt.
4. **`squares`**, then **`step`** each square in a loop: on `WAITING <prompt>` write `<same name>.md` beside it; on `FIX <run> <ids>` fix exactly those audit lines in `stages/4e-close.md` and `hand/4e-close.md`, delete `hand/4f-audit*`, touch `hand/fixed-<ids>`; stop on `STOPPED` or `DONE`.
5. **`page`**, publish over the Creative Run Builder, push.
6. **Production (once a brief is green).** `elements` lists every person, look, voice, place, prop and product per ad as **banked** or **to make**, each to-make item with its real swipe frames attached (the teardown saves every frame at 8/s and crops each element; all mirrored to the swipe's Drive folder). Make the to-make items with the video-production makers (`make_character.py`, `make_set.py`, `make_voice.py` — voice option 1 is the default pick; props are real photos or a crop of the swipe frame, never generated). The grid shows every element as a picture. When the owner says **"elements ok"**, run `approve` — one lock for every ad with nothing left to make (an ad with a gap is named, never approved past it) — then `produce --go`.
7. **To the editor (once clips are made).** `editor --go` gives every ad with clips its brief number, its edit kit and an editor brief, in one folder named `brand_product_brief` under `Shared Assets/runs/handoffs/video-editor/<brand>/` — the editor's queue; the owner assigns a brief number and the editor opens that folder (the owner, 2026-10-09). Look at the clips first and list any fault in the folder's `handoff.md` under Known faults.

## the owner's standing rulings for AI-lane variations (2026-10-07)

- The swipe's hook stays as the format has it. No "results may vary / photos may differ" small print. The demo shows the product working, dramatized: product on a visible spot → wiped off → even skin. Real proof lives on the landing page. Write these into each run's `RULINGS.md` (every stage reads it).
- Aim at the audience the product is for: a face product goes to the face sub-group (spot-hider `face-dark-marks`), not the core avatar whose spots are on hands and arms — the Viewer Check will say so.

## Rules that never bend

- **One square first, then small batches.** Take one square all the way to 5 Brief, read it, fix what breaks, then a few at a time. Never 28 at once.
- **Efficient by design:** read each stage prompt once (large reads, never in many pieces); the chain fills each big block once; **Sonnet** writes 4a Reading and 4f Audit, **Opus** writes everything else.
- **Holds:** the swipe's own format/structure holds pass (the owner, 2026-10-06 — "if it's the swipe, we put it in"); audit fails on **claims, the offer or brand rules are fixed, never passed** (banned words, dated result promises, the allergy line a product file requires).
- **Facts are never invented.** An opening or line that needs a fact not on file stays blank and comes out of the production block with a note — never filled with a guess.
- **One offer per brand, from the brand's files.** No other price, discount or bundle anywhere.
- **the owner picks the squares.** Never queue for him. Questions go to him in chat, plainly. Names are the system's: winners by ad name, formats by library name, squares by chain stage.
- **One cut per winner** (the top seller when winners are the same ad). **Formats must fit the avatar.** **Video → video only** unless he says otherwise.
- **Check the brief's top "Core message" line** — stage 5 can carry the swipe's message there; replace it with the brand's.
- Claude stages are written in-session; never raise the chain's sign-in with the owner.

## Where things land

Injections `runs/ad-variations/<brand>/p2f-<winner>__<format>/` · each square's chain run `runs/video-teardown/<brand>/sq-<winner>-x-<format>/` (working copy in `components/video-teardown/machine/runs/`) · formats `runs/video-teardown/<brand>/fmt-*` · the grid: the Creative Run Builder artifact (page source `components/ad-variations/page/creative-run-builder.html`).

## Static winners — one change at a time (2026-11-23)

A winning IMAGE ad is never sent down the new-ad path (teardown → new concept → new copy): that reinvents it. It runs
the static side of the winner variation workflow, whose steps and commands live in `components/ad-variations/CLAUDE.md`
("Third capability"):

1. `python3 components/winners/winners.py statics --brand <b>` — the winning image ads, each tied to its brief, run, approved picture and 3D set.
2. A records-only run on the winner's live picture (`components/image-teardown/chain.py open --file <live picture>`, then `tools/run.py <run> 1,1k,2,2b`).
3. `python3 components/ad-variations/machine/static_plan.py --brand <b> --winner-run <run> --label <name> --ad "<Meta ad name>" --statics <statics.json> [--set <3D set>] [--ask <ask.json>] --dry-run`, then without `--dry-run`. The ask must name the avatar the winner was made for.
4. Show the owner the rows (winner as it ran, locks, each row's one change) and wait for the sign-off.
5. Make through image-edit `vary.py <approved picture> --brand <b> --from-brief <plan>/variations.json` (picture rows become set requests) and the 3D print runner with a cap and the owner's go.
