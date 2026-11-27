# components/image-writing — the writing station of the picture line

**image-writing** — takes **a torn-down static ad (an image-teardown run, steps 1, 2 and 2b done)** and writes **our
version of it for the brand: the injection with its swaps record, the headlines, the brief's five variations as data
and the brief**. It does not **read the swipe** (image-teardown does that), **make the first picture**
(image-production) or **make the variations** (image-edit, through model-inputs).

**Owner:** the owner. Split out of `components/image-teardown` on 2026-10-27, the same way `components/video-writing`
left `video-teardown` on 2026-10-19: the writing code and its prompts moved here, the teardown hands off at step 3,
every reader was repointed in the same commit. The run data did not move.

The picture line, one station each:

    1 image-teardown     the swipe's records: 1 teardown, 2 the format, 2b element labels, the dial read
    2 image-writing      3 injection (+ out/swaps.json), 4 headlines, 5 variations (out/variations.json), 6 the brief
    3 image-production   the first picture
    4 image-edit         the five variations, through components/model-inputs (prompt writer + the input check)
    5 Model House        picks the model

## The four new-resident questions

- **Engine + owner:** `tools/writing.py` (the four steps: their prompts, their inputs, what each does once its answer
  is on file), `tools/swaps.py` (the swaps record, moved from the teardown), `tools/variation_rows.py` (the variations
  record) and `run.py` (the command). Owner the owner.
- **Definitions + curator:** `prompts/` — every writing step's prompt (stage 3 injection, 4b headlines, 4e variations,
  6 the brief on each branch, the swaps reader for backfills), and `templates/` — the standard brief (the newest
  `-vN-` is the one filled and held to). Curator the owner. The highest `-vN-` at the top of `prompts/` is the live one;
  `archive/`, `superseded/` and `parked/` never run. A changed prompt is a new file, never an edit.
- **Plane:** none of its own. It writes into the teardown run it is handed,
  `runs/image-teardown/<brand>/<run>/out/` (the run's one home since 2026-10-28, image-teardown `paths.run_dir`; the
  old `components/image-teardown/runs/<run>/` is read for one release), and the teardown files the record beside it.
- **Manifest per entry:** none. The prompts are versioned files; the teardown's `run.json` records the run.
- **Runs by:** person (the teardown's mini door runs it inside `chain.py start`).

## How to run it

    python3 components/image-writing/run.py <run> [3,4,5,6 | all] --brand <b> --product <p> [--avatar <a>] [--dry-run]

or let the teardown hand off: `components/image-teardown/chain.py start ...` and
`components/image-teardown/tools/run.py <run> all` run steps 3 to 6 through this station.

## The variations record — `out/variations.json` (2026-10-27)

the owner, 2026-10-27: *"It'd be 6 total images in that batch: 5 unique variations from the initial one that we made."*
So stage 5 (`stage4e-image-variations-v3-owner.md`) writes exactly five rows, each ONE change off the approved
picture, as a fenced json block (THE VARIATIONS RECORD); `writing.after` reads it into `out/variations.json` with
`variation_rows.from_stage5` and checks its shape the way the swaps record is checked: exactly five, unique `id`, a
`label`, at least one change, only the keys components/image-edit `vary_recipe` reads (`words` one string per caption
zone with " / " as the line break, `picture`, `swap`, `stays_drop`, `people` cast|made-up, `person` who/age/look/
wardrobe). A broken record is sent back once with the reason, then left unwritten and said so. A `variations.json`
already in the run that stage 5 did not write (the hand-written grandma one) is kept beside it as
`variations.by-hand.json`, never lost. image-edit makes the batch from it:
`vary.py <approved.png> --brand <b> --from-brief <run>/out/variations.json`.

Stage 6 (`stage6-image-brief-v11-owner.md`, the AI single brief) is handed the same file as `{variation_rows}` and
lists the five as one section, **6 · Variations**, in the standard brief v2 (`templates/brief-standard-static-v2-owner.md`,
nine sections), in place of v1's separate Headline options (5) and Picture options (4).

Choices made here while the owner was away (2026-10-27), each his to overrule:
- **The five follow the hand-written example's h1–h5:** each row takes one of the headline set's five variation
  headlines, word for word, plus the one picture change that makes it true. A row changes the person only when its
  headline cannot be true of the approved picture's person. This replaces v2's "three headlines × two pictures"
  (2026-10-25) with his 2026-10-27 batch rule.
- **ids are `v1`–`v5`** (the example's `h`/`p` split no longer applies: every row is one change).
- **Stage 5 is handed the swap list** (`{swaps_record}`, the run's `out/swaps.json`) so a row that changes a person
  names the swap-list row it replaces by its exact `from`.
- **Only the AI single brief changed.** The sequence and creator briefs still read the stage 5 answer as text
  (`{image_variations}`); they get their own new version when the owner asks.
- **The brief template's sections were renumbered** (Never 8→7, Check 9→8, Questions 10→9); the swaps backfill now
  finds "Never on this ad" by name, whatever its number.

## The copy sign-off, the approved headline and the spice (2026-10-27)

the owner, 2026-10-27: *"before images are generated in general, the actual copy needs to be reviewed so [we] can actually
put some sauce on it for a while until we're ready for full auto, because awareness levels and verbatims and spice are
the foundation of what we're doing here."*

- **A person's yes on a first picture is recorded by `tools/approve_picture.py`** (their words required; any brand), into
  the one home the steps, the run sheet and the hand-off read. `--real-photo`: a real person's photo is never changed and
  every variation is words only. A viewer rewrite that changes the approved picture, its words or row 0 is kept beside the
  brief as `06-brief.viewer-rewrite.md`, never as the brief (2026-11-25).
- **No picture from unapproved words.** `tools/copy_ok.py show|approve|check <run>` keeps `out/copy-approved.json`
  (who, when, the exact words). The teardown's `tools/pictures.py` (the first picture) and components/image-edit
  `vary_recipe` (the variations) refuse any line not in it, word for word. `vars/copy-review.md` saying `off` turns it
  off for a run: full auto, his call.
- **The variations vary the approved headline** (stage 5 v4, v5): `{approved_words}` is the words actually on the
  approved picture (`writing.approved_words`: its recipe's own words, else the brand step's Our copy), written to
  `out/approved-words.md`. Every variation keeps its shape, names the problem in her word for it on a problem-aware
  ad, and reads cold. No approved picture yet = missing; stage 5 waits for the approval.
- **Spice in the headline and the variations** (stage 4b v5, stage 4e v5): `{spice_bank}`, the language layer's own
  `spice` stage, pulled by the teardown engine.
- **Every language pull is the run's avatar at the swipe's awareness level** (`image-teardown/tools/run.py`
  `language(…, avatar)`, `awareness_of(run)` from the teardown's MARKET STATE); it fell back to every avatar's top rows
  before, a niacinamide acne story on a dark-spots ad.

## The swaps record — `out/swaps.json`

Moved here with stage 3; the contract and its rules are unchanged and stated once in `tools/swaps.py`. Stage 3 v6
writes it as its section 6 and `writing.after` reads it in (sent back once if it breaks the contract); stage 6 carries
it unchanged. `swaps.py backfill` writes one for runs made before it existed. Readers load it from here:
the teardown's `tools/pictures.py`, `components/model-inputs/preview.py`.

## Tests

    /usr/bin/python3 -m unittest discover -s components/image-writing/tests

Spends nothing. Proves: the writing prompts live here and the teardown holds none; the teardown runs 3 to 6 from here
and every writing prompt's `{slot}` has a source; the command refuses a record step and a run that does not exist; the
variations record holds its shape and stage 5 writes it, sending a broken one back once; the swaps record (moved with
its tests); the standard brief v2 and its gate; the hook ledger opens in the run, never under `brands/`; no brand
named in the code, prompts or templates.

## What it leans on (not moved, on purpose)

- **The chain engine is the teardown's.** Filling a prompt, calling the model, the language rows, the dry run, the
  elements gate in front of step 3, the copy gate and the filing: `components/image-teardown/tools/run.py`,
  `gates.py`, `paths.py`. `writing.py` takes the engine as `E`, the names the teardown declares as its writing seam
  (its CLAUDE.md), and reads `paths` and `gates` from the teardown's tools.
- **The swipe's dial read stays a record:** `out/controls-swipe.*` is the teardown's (`run.py swipe_controls`); stage 3
  is handed it. The aim (`vars/controls-target.md`) and the never-sterile floor are written here.
- **The viewer check** after the brief (`writing.viewer_step`) moved with stage 6.

## Not done in this move

- `components/image-edit/CLAUDE.md` still says stage 5 writes its variations as text and `variations.json` is written
  by hand. That folder is another session's live work; the note is theirs to change now that stage 5 writes it.
- `components/image-production/image_production/words.py` names `components/image-teardown/tools/swaps.py` in its
  docstring (no code reads it). Left alone: image-production is out of this move.
- The old `tools/build_prompt_library.py` and `tools/build_artifact.py` copies in the teardown point at prompt folders
  that were already gone before this move; the live prompt library is the teardown's top-level
  `build_prompt_library.py`, repointed here.
