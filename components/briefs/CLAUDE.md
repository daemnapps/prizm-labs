# components/briefs — every brief style, one home

**A brief is a PROJECTION of a record.** The record (a teardown, a research
read, an idea) is the expensive half; the brief is what you print from it for
somebody to act on. Measured 2026-09-25: a teardown run costs ~25 minutes, the
brief stage off the end of it 21 seconds. **Seventy to one.**

That ratio is the whole reason this folder exists. If a brief style is one file
and the records are already paid for, then a new brief style prints against
every record ever made — 532 videos in the swipe library, 11,618 swipes
indexed. The ceiling is not how many brief styles there are; it is whether the
record captured enough to project from.

Established 2026-09-30 on the owner's word: *"We're going to create a folder that
is specific, like it's a component for briefs. All of our tools can just round
through whatever brief needs to be built based off whatever records we have."*

## What was wrong (the audit, `lab/the owner/BRIEF-PATCHBAY.md`, 2026-09-25)

21 brief styles across 8 machines. 412 briefs produced in ~10 days, by 8 lanes.
Three faults:

1. **Naming.** Eight lanes, eight conventions. `copywriter` and
   `email-production` BOTH write `stage9--brief.md`; `outlier-brief` writes one
   brief under two names. A filename said where in a chain a brief sat, never
   what it was.
2. **Dead versions read as live.** 11 superseded prompts sat beside current
   ones in live folders — which is how a regression config ended up pinned
   three versions behind.
3. **A record is trapped in the chain that made it.** A copy teardown's
   construct could not be printed as a video brief without a person carrying it.

## THIS FOLDER REGISTERS; IT DOES NOT MOVE (the intake precedent)

Every brief style stays where its machine keeps it and is **declared here**.
Nothing is moved, renamed or rewired by establishing this component — the 8
machines that produce 412 briefs a fortnight keep working untouched.

That is deliberate, and it is how `components/intake` was built: one place to
read every swipe as one list, while the swipe folders stay the tools they
always were. A style MIGRATES into this folder one at a time, on the owner's word,
when it is worth it — never as a big bang against machines other sessions edit
daily.

## The naming rule

    brief--<asset>--<actor>.md

`brief--video--creator.md` · `brief--static--designer.md` ·
`brief--email--builder.md`. **The stage number leaves the filename.** A brief
is named for what it IS and who acts on it, not for where in some chain it
happened to sit. Stage numbers are a property of a chain; a brief outlives the
chain that first printed it.

## What every entry declares

| field | what it says |
|---|---|
| `id` | `<asset>--<actor>` — the name a tool asks for |
| `record` | the record it reads (what it projects FROM) |
| `asset` | video · static · carousel · email · page · copy · any |
| `actor` | creator · designer · generator · builder · buyer · approver |
| `prompt` | where the prompt lives today, repo-relative |
| `writes` | the filename its machine writes today (kept honest until migration) |
| `status` | `draft` · `approved` · `deprecated` — components rule 6; the owner's approval word |
| `state` | `live` · `parked` — activity only, from the evidence |
| `evidence` | what proved the state — a run count and a date, never a guess |

Which style each image-teardown brief type (`components/image-teardown/tools/briefs.py` `TYPES`) is lives here, in `briefs.json` `teardown_types`, read by `tools/briefs.py` `style_for()` (SI-137 (brief vocabulary map)).

## Every brief ships with its run sheet (2026-10-28)

the owner, 2026-10-28: *"we need to make this entire workflow agent-agnostic, and
these briefs agent-agnostic ... The underlying processing is that this is all
going to run through Higgsfield, so that's the core of it."*

The brief says WHAT to make; its **run sheet** says exactly HOW, the same way
for any tool. `runsheet.py` writes `RUN.md` (people) and `run.json` (machines)
into the brief's own `deliverable/` folder:

    python3 components/briefs/runsheet.py <brief key or number> [--brand b] [--out DIR]
    python3 components/briefs/runsheet.py <brief key> --prompt N     step N's prompt, verbatim

- **The core is Higgsfield.** One step per picture or clip: the Model House
  job and its Higgsfield model id, the exact prompt (model-inputs' preview
  builder for pictures, the video chain's Seedance builder for clips), the
  references as Higgsfield elements where they exist (products from
  `runs/ai-elements/PRODUCT-INDEX.json`; cast, sets and props from
  `runs/ai-elements/ELEMENTS-INDEX.json` once it exists) plus repo files for
  the rest, the settings, and the output name `<brief key>_asset-NN.<ext>`.
- **Three thin renderings of that same core**: (a) the Higgsfield web app, for
  a person clicking; (b) Claude Code with the Higgsfield MCP; (c) Codex or any
  other agent, as API-shaped steps plus repo commands. A change to what gets
  made goes in the core (the brief, the prompt bench), never in one rendering.
- **One return step, the same in every rendering**: files named
  `<brief key>_asset-NN.<ext>` go to
  `runs/handoffs/<role>/<brand>/<brief key>/returned/`, or the same path under
  `Shared Assets/` on Drive. Beside each file, a receipt: `<asset>.receipt.json` (what was really sent: generation id,
  model, prompt, inputs in order; `return.receipt` in run.json, a filled-in example in the step), or in the web app a
  one-line `<asset>.link.txt`; image-edit `reference_check.py` proves the file against its step with it.
  **An agent saves Higgsfield's own record too** (2026-10-28): `<asset>.record.json`, the generation record exactly as
  its Higgsfield tool returns it (`return.receipt.record` in run.json); it outranks the receipt, because a retyped
  prompt came back corrupted ("Shaved" → "Shared", symbols lost, never-rules dropped) and only the record showed it.
  The return step and section B's `LEAN` say: read BRIEF.md, RUN.md and run.json from GitHub (the Drive connector
  can change text), take media from the Drive, and pass each step's prompt out of run.json unchanged, never retyped.
  `element_swap_line(x)` is read by image-edit `reference_check.py` (the one wording of an element put in for its
  files); its signature is public.
- **Carousels too** (sequence briefs): slide one is a picture step; each later
  slide is one edit off it, the brief's slide-deltas block read by image-edit's
  own `deltas_from` and `resolve`, the same instruction `sequence.py` sends. A
  brief with no block, or a refused slide, is named under the sheet's gaps.
- **Every hand-off folder carries it, self-contained** (2026-10-28):
  `runsheet.pack(sheet, folder, role)` writes `BRIEF.md`, `RUN.md`, `run.json`
  and `refs/` (every reference file the sheet names, renamed by step and role,
  `refs/step-01-image-1-swipe.jpg`, element files by element,
  `refs/product-<id>-sheet.png`, `refs/cast-<id>-headshot.jpg`) into
  `runs/handoffs/<role>/<brand>/<brief key>/`. In that copy every reference
  reads `local` (`refs/…`), `file` (repo path) and `drive` (`Shared Assets/…`
  label); the Higgsfield element stays first choice in sections A and B, the
  `refs/` file its fallback. Both hand-off writers call it
  (image-edit `image_edit/handoff.py`, video-edit `machine/editor_handoff.py`)
  and mirror the whole folder to the Drive; `refs/` is git-ignored.
- **Made in Claude Code** (the owner, 2026-10-28: "we're just going to Claude Code everything"): `make.py` holds the
  exact parts so the maker's Claude never retypes them. `waiting [--role]` lists the hand-offs on the Drive with an
  empty `returned/`. `plan <brief> <step>` fetches that step's files from the Drive and prints the uploads in order
  plus the Higgsfield call (`agent_call`, the prompt out of run.json unchanged). `save <brief> <step> --record <file>`
  takes Higgsfield's own record, downloads, names and saves to `returned/` here and on the Drive, then runs image-edit's
  reference check (`save <brief> cut --file` for the video cut). Tests: `tests/test_make.py`.
- Repo-relative paths and `Shared Assets/...` labels only, never a machine
  path. Generates nothing, spends nothing, no key, no network.
- Tests: `/usr/bin/python3 components/briefs/tests/test_runsheet.py`.

## The hand-off folder and the queue (2026-10-28)

Where a hand-off lives, what makes it ready, and what the queue does with it automatically is defined in
`HANDOFF-QUEUE.md`. The folder is the only "ready for the maker" mark; `queue_check.py` (in Outlier) tests the connection.

## The briefs index — one brief key, every station (2026-10-28)

Run folders keep their labels (one ad is `<swipe>-<brand>` at teardown and something else at production;
links and other sessions lean on them). Instead every run record carries `brief_key` and one index joins them:

    python3 components/briefs/briefs_index.py                 runs/BRIEFS-INDEX.json + runs/BRIEFS.md
    python3 components/briefs/briefs_index.py find <key>      one brief (either product spelling, or brief-NNNN --brand b)
    python3 components/briefs/backfill_brief_key.py [--apply] stamp `brief_key` (one line, never a re-dump) into each run.json

- Per brief key (catalog form, `names.catalog_key`; `forms` maps every spelling to it): each station's run folder
  (repo path + `Shared Assets/` label), its hand-off folders with their `returned/` files, its Meta cards
  (`runs/meta-upload/<brand>/ADS-INDEX.json`), and `old_names` — hand-off folders under an older spelling, never renamed.
- A run is placed only when the register agrees (its `run`/`brief_file` label, its own `brief_key`, a hand-off folder's
  name, or the run it was made from); a number the register gives to another run is left unplaced and says why.
- New hand-off folders take the catalog form; one already there keeps its spelling (`runsheet.home_key`,
  image-edit `handoff.home_key`, video-edit `editor_handoff.home_key`). Tests: `tests/test_briefs_index.py`.
- **Who a brief is for** (2026-11-25): `aim.py` `aim_of(brand, brief_key)` answers avatar, sub, demographic, desire,
  awareness, stage, doubt and claim from what is on file (the brief's record, then its runs' `aim`, then their older
  fields, then its sprint), says which file answered, and leaves the rest None. Read by winners `who` and the finished
  ads index. Tests: `tests/test_aim.py`.

## The four new-resident questions

- **Engine + owner.** `tools/briefs.py` — a resolver, no model, no credential,
  no network. Owner the owner.
- **Definitions + curator.** `briefs.json`, the register. Curator the owner: a
  style's `status` is his ruling, not a session's; its `state` follows the evidence.
- **The plane it emits.** The caller prints the brief into its run folder.
  Ledger exports live in `runs/queue/`; the named usage adapter writes request
  and session JSON under `runs/brief-usage/`. See README for shared workflow
  sources, public surfaces, coverage and sync requirements.
- **Runs by:** both (session pickup hooks and read-only workload view); person (optional OTLP launcher).
- **What the manifest declares.** The nine fields above, per entry.

## Rules

1. **State is evidence-backed.** `live` needs a run count and a date. A style
   nothing has produced in 30 days is `parked`, not `live`, whatever its
   config says.
2. **Nothing is deleted.** `deprecated` is a status (the `retired` state until 2026-10-07), and the prompt moves to its
   folder's own `archive/`. the owner rules the kill list.
3. **Research is not a brief** and is deliberately out of scope — it becomes
   its own component (the owner, 2026-09-30).
