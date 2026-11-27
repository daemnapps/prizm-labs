# components/ad-variations — the variation planner

**ad-variations** — takes **one proven ad's video-teardown run** (with its post
metrics and the brand's context), makes **a variation plan**: every element
marked lock or lever with evidence from the brand's whole corpus, N one-lever
variations, new formats recombined from what the corpus proves, a merge recipe
per variation (seconds reused, what AI makes, route, cost), QC gates and
congruence links. Does not **generate anything** — production is NOT built
yet. One reader since 2026-11-18: `machine/next_ask.py <plan folder>` files the
plan's next variation as an ask the writing tools read (`asks/<ask>/ask.json`,
and `next-ask.json`: what is next, asked, held by the plan and left, and the winner
it is for), so a plan reaches the queue as the next ask; the winners queue source
reads `next-ask.json`. The ask's `variation` block is read by no writing tool yet.
`proposed/` holds what is written and not live (a locks prompt with the order
of the layers, the across-forms rule); nothing reads it. Triggered by
`python3 machine/run.py plan <post id | teardown run> --brand <brand>` (add
`--dry-run` to fill every prompt and spend nothing).

Built 2026-09-27 on the owner's ask: "create a new component for creating
variations from a replication spec of an existing ad that has worked … we can
literally start adjusting the highest-impact opportunities, as well as build
new formats." Plus, the same day: "we should have the index of variables to
adjust, since our teardown is ultra thorough now" — the Variable Index.

## The new-resident answers

- **Engine + owner:** `machine/` — the owner.
- **Definitions + curator:** `definitions/` (variables.json — the Variable
  Index definitions; elements.json — the fixed element list; routes.json —
  production routes and rates; gates.json — QC gates;
  variations.schema.json — the contract) and `prompts/` — the owner. Every entry
  seeds `draft` — on the entry itself (rule 6, triage page 15;
  SI-78 (variations entry status) moved elements/gates/routes from one
  file-level status to one per entry).
- **Plane it emits:** `runs/ad-variations/<brand>/<label>/` per plan
  (`variation-plan.json` is the contract, `VARIATIONS.md` its mirror,
  `deliverable/` both) and `runs/ad-variations/<brand>/variable-index/` per
  brand (`variable-index.json`, `VARIABLE-INDEX.md`, `coded/`), and
  `runs/ad-variations/<brand>/higgsfield/` — the brand-filled Higgsfield
  hand-off and its brief list; `prompts/higgsfield-handoff/` holds the slotted
  template (SI-88 (higgsfield template)).
- **What the manifest declares per entry:** variables.json — id, name, family,
  read_from, type, how (`rule:` or `coder:`), change_by (route ids),
  cost_class, status. routes.json — id, unit, $ per unit, locked or TEST.
- **Runs by:** person (a session runs it on the owner's word).

## Rules for working here

1. **Reads the teardown's contract only** — the filed run folder
   `runs/video-teardown/<brand>/<slug>/` and the swipe manifest that names it.
   Never the teardown machine's internals.
2. **Brand-agnostic.** Brand content comes only from `brands/<brand>/`
   (`machine/brandctx.py`). The prompts name no brand; a test enforces it.
3. **Numbers are the machine's, never the model's.** Evidence tables are
   computed from the index; costs are units × `routes.json`; forced gates come
   from the routes a recipe uses. A prompt quotes numbers, it never makes them.
4. **Prompts are the product.** A prompt change is a new `-vN-` file; the old
   one moves to that folder's `archive/`. Every prompt is rendered verbatim on
   the Ad Variations page (`machine/page.py`) and in The New Prompts.
5. **Plans only.** Nothing here calls a generation model or spends on
   production. The only model calls are the planning stages (Claude, through
   run-kit) and the index coder.

## Second capability: video variations — proven ad → new format (added 2026-10-05, standardized 2026-10-07)

the owner, 2026-10-07: "let's standardize this process of creating video ad variations since we will do it
a lot moving forward." The team skill is `.claude/skills/ad-variations/`; the plain-words doc is
`PROVEN-TO-FORMAT-owner.md`; the engine is `machine/proven_to_format.py`.

- **Run:** `check → prep → inject → squares → step (loop) → page → elements → approve → produce → editor`, each `<batch>` a file in
  `definitions/proven-to-format/` (winners × formats + brand, product, avatar, offer, route).
- **Definitions + curator:** the batch files and `prompts/stage-3-winner-slot/` — the owner.
- **Plane it emits:** `runs/ad-variations/<brand>/p2f-<winner>__<format>/` (`sent.md`, `3-injection.md`),
  each square's chain run filed at `runs/video-teardown/<brand>/sq-*` and each format's at `fmt-*`, and the
  grid page `page/creative-run-builder.html` (the Creative Run Builder artifact).
- **Exception to rule 1, on purpose:** this capability DRIVES the video chain (`components/video-teardown/
  machine/run.py`, by its command line) and works in its run folders (`machine/runs/sq-*`, `fmt-*`), because
  every square is a real chain run through 5 Brief and the Viewer Check. It changes no chain code. If the
  chain's run-folder shape or its 40-character run-name limit changes, `check`, `inject`, `squares`, `step`
  and `page` are what break.
- **Holds:** the swipe's own format holds pass (the owner, 2026-10-06); audit fails on claims, the offer or brand
  rules are fixed, never passed.
- **Runs by:** person (a session runs it; Claude stages written in-session).

## Third capability: winning statics, one change at a time (added 2026-11-23)

Ruled 2026-11-23: the winner variation workflow existed for video only, so a winning image ad went down the new-ad
path (teardown → new concept → new copy) and came back reinvented. This is the image side of the same process: go
deeper into what already won, the elements in the picture and the copy on it. Never a new concept, setting or format.

1. **Pick:** `components/winners/winners.py statics --brand <b> [--days 30] [--min-spend 100] [--min-roas <x>]` lists
   the image ads proven on their own numbers and ties each to its brief, its chain run, its approved picture and its
   3D set (`runs/winners/<brand>/statics/<date>/statics.json`).
2. **Read the winner as it ran:** a records-only run on its live picture (`components/image-teardown/chain.py open
   --file <live picture>` then `tools/run.py <run> 1,1k,2,2b`). Its own original run is never rewritten.
3. **Plan:** `machine/static_plan.py --brand <b> --winner-run <run> --label <name> [--ad <Meta ad name> --statics
   <statics.json>] [--set <3D set>] [--ask <ask.json>] [--rows 6] [--dry-run]` → locks, levers and N rows
   (`prompts/stage-static-plan/`). A copy row changes ONE word zone in the winner's own format and leaves the picture;
   a picture row changes ONE element in the same setting and leaves every word. Checked with no model (one change,
   the winner's words kept on picture rows, every zone present, banned lines from the ask, offer-bank prices only),
   sent back once, a row still broken dropped and named. Writes `runs/ad-variations/<brand>/<label>/`
   (`winner.json`, `variation-plan.json`, `variations.json` in image-writing's row shape, `VARIATIONS.md`, the prompt
   as sent, the answers).
4. **Owner sign-off** on the rows (the copy sign-off gate: no picture from unapproved words).
5. **Make:** copy rows set the words on the winner's picture; picture rows become a change to the winner's own 3D set
   and go through the 3D print runner (casting sheet only, one print first, the real product pasted).
6. **Check and file:** product against its casting sheet, words exact, offer against the bank, then naming and the
   versions inside the winner's own approval card.

**Plan v2 (2026-11-24):** rows that moved the light, steam or camera a step came back looking like the same picture. The
plan now dresses the winner for the order's moment first (the `control`, written as its own row), every row builds on it
and passes the feed test (2 cm wide, a different ad; a lever that small is refused in code), copy rows read the run's
customer-language pull when it is the order's avatar's, and the product's rules come off its kit.

**Sprint (2026-11-24):** `machine/static_sprint.py prep|hand <sprint.json>` packs a round of these plans as the graphic
designer's hand-offs: one image-edit design assignment per winner (through `assignment.build`), one required delivery slot per version.
`prep` sends nothing; `hand --by --only` runs after the owner's sign-off on the rows.

**Natural statics (2026-11-24):** `machine/natural_statics.py start|comments|copy|check|draft|page|number|file|status` runs a
whole round of natural static ads from one `sprint.json`: pictures we own with the words set in code (layouts story, tag,
letter, note, comments, plate, all 1080 x 1920), one changed line per version, copy that already ran, one page, then one
card per ad on the approval page. No model call, nothing generated, no gate turned off, nothing approved or uploaded.
Front door: the `statics-sprint` skill. Tests: `machine/test_natural_statics.py`.

Tests: `machine/test_static_plan.py` (no model, no network). Steps 5–6 use the existing image-edit and image-production
doors; making a winner's row needs the winner's recipe or set on record (open where a winner was made outside the chain).

## Our own ad multiplier and swipe edit (2026-11-25)

`machine/multiply.py plan|make`: one finished ad in, versions out, each with one shot changed to footage we own, the sound, the
length and every other shot untouched, free. A person, product or place change is priced for that shot only and never sent from
here. `components/video-edit/machine/swipe_edit.py read|plan|cut` puts our footage on a swipe's cutting and refuses while any
shot is missing. Both cut through `components/video-edit/machine/shot_engine.py` (whole frames on one clock; footage is searched
in the asset index, and any piece with words burned in is refused by reading its frames on this machine). Both write a
`look-first.png`: nothing is used before it has been looked at. Tests: `components/video-edit/tests/test_shot_engine.py`.
