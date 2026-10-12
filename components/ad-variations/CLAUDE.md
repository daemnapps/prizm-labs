# components/ad-variations — the variation planner

**ad-variations** — takes **one proven ad's video-teardown run** (with its post
metrics and the brand's context), makes **a variation plan**: every element
marked lock or lever with evidence from the brand's whole corpus, N one-lever
variations, new formats recombined from what the corpus proves, a merge recipe
per variation (seconds reused, what AI makes, route, cost), QC gates and
congruence links. Does not **generate anything** — production is NOT built
yet: no component reads `variation-plan.json` today (2026-10-08) — no reader
yet. Triggered by
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
a lot moving forward." The team skill is `.claude/skills/video-variations/`; the plain-words doc is
`PROVEN-TO-FORMAT-damon.md`; the engine is `machine/proven_to_format.py`.

- **Run:** `check → prep → inject → squares → step (loop) → page → elements → approve → produce → editor`, each `<batch>` a file in
  `definitions/proven-to-format/` (winners × formats + brand, product, avatar, offer, route).
- **Definitions + curator:** the batch files and `prompts/stage-3-winner-slot/` — the owner.
- **Plane it emits:** `runs/ad-variations/<brand>/p2f-<winner>__<format>/` (`sent.md`, `3-injection.md`),
  each square's chain run filed at `runs/video-teardown/<brand>/sq-*` and each format's at `fmt-*`, and the
  grid page `page/creative-run-builder.html` (the Creative Run Builder artifact).
- **Exception to rule 1, on purpose:** this capability DRIVES the video chain (`tools/video-teardown/
  machine/run.py`, by its command line) and works in its run folders (`machine/runs/sq-*`, `fmt-*`), because
  every square is a real chain run through 5 Brief and the Viewer Check. It changes no chain code. If the
  chain's run-folder shape or its 40-character run-name limit changes, `check`, `inject`, `squares`, `step`
  and `page` are what break.
- **Holds:** the swipe's own format holds pass (the owner, 2026-10-06); audit fails on claims, the offer or brand
  rules are fixed, never passed.
- **Runs by:** person (a session runs it; Claude stages written in-session).
