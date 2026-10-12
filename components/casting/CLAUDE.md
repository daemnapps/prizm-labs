# casting — one engine that answers "who plays this role?"

**casting** — takes **a brand and a role**, makes **the person already banked
for it, or the gap and the nine steps that close it**. Does not **register
anyone, write into a brand, write the words, or invent a name**. Triggered by
`import casting` (a library) or
`python3 components/casting/cast.py who --brand <b> --role "<role>"`.

**Owner:** the owner (engine and definitions both).

the owner, 2026-09-22: *"what tools actually generate avatars by the way? check
our system for this please so we can take it out of and put it into its own
component so other tools can leverage it correctly."*

**This is an EXTRACTION, not an invention.** Every part already worked
somewhere: the nine steps, the three generating prompts, the fal door and the
"a DIFFERENT person" rule come from `the team notes/avatar-builder`; the registry
reading and the "never invent a person for a role the bank covers" rule come
from `the team notes/casting`; the footage search is
`tools/image-production`'s asset reader, imported rather than rewritten;
the gates, the dry-run report, the path walking and the filing come from
`tools/image-production`, `components/quality-checks` and
`components/run-kit`. Each module's docstring names what it was lifted from
and what it changed.

**Nothing has been switched over yet.** `the team notes/avatar-builder` and
`the team notes/casting` are untouched and still work exactly as before. They get
retired later, side by side, once this is proven — a working chain is never
rewired on assumption.

---

## THE RULE THE WHOLE CHAIN TURNS ON

**Identity comes from an IMAGE, never from a paragraph.** A character written
as prose is a different person every roll, which is the exact failure the cast
bank exists to prevent. So the first real step is finding a frame, not writing
a description, and a build with no baseline is REFUSED at the inputs gate.

The baseline is a real frame from owned footage. What carries from it is the
**world** — the room, the framing, the light, the camera register, the
wardrobe category — so a generated shot cuts against filmed footage without a
visible change of world. **What must never carry is the person.** Baseline,
not likeness. The master prompt says so out loud, the standing rules say it
again, and the judge is asked it as a test.

## THE STANDING RULE ON WHO IS CURRENT (the owner, 2026-09-29)

**AI characters are made only from existing assets and customer information,
always with reference files; a character without a casting sheet is not
current and is not used in new work until it gets one.** A casting sheet is
the Person element in `tools/video-production/PRODUCTION-ELEMENTS.md` —
`runs/ai-elements/<brand>/casting/<id>/` with `character.md`, the master, the
sheets, `reference/` holding the REAL files the master was edited from, and
`provenance.json`. The brand's `casting/cards-v6.json` records
`casting-sheet: yes|no` per character and `status: not current — no casting
sheet` for anyone without one; the Talent Cards page lists them first, greyed.
Every card is on the one talent-card schema (Naming Standard, "Talent card
fields", v6 2026-09-29): id = first name, `handle` its own field, and closed
lists for `kind`, `role`, `gender`, `ethnic-appearance`, `age-band` and their
`-source` fields. `casting/cards.py` (`validate`, `validate_file`) refuses a
card with a value outside its list; the page builder calls it before drawing.
A card that says `not current` is an answer of "nobody current plays this
role yet — build the sheet", never a person to cast.

## THE SECOND RULE: a role the bank covers NEVER gets a new face

That is the whole point of a bank. A second face for a role that already has
one breaks the first face across everything already shipped. So `cast()`
answers with the banked person, and `build()` is held at the inputs gate when
the bank already covers the role — naming who, and where the record is.

---

## The request contract

One shape, whatever the caller is. **A field nothing on this list names is
REFUSED, not ignored** — a silently dropped field is a caller that thinks it
asked for something.

### The question

| Field | | What |
|---|---|---|
| `brand` | **required** | a folder under `brands/`. Never a default |
| `role` | **required** | the role, in words. The one thing this component cannot read from anywhere else |

**Back:** `{brand, role, covered, person, where, why, candidates, castable,
gap, bank, problems}`.

### A build, when the answer is a gap

Everything above, plus:

| Field | | What |
|---|---|---|
| `id` | **required** | the character's folder name under the brand's cast folder. A person chooses it; this component never coins a name |
| `kind` | **required** | `authority` (the credentialed voice that fronts a script) or `roster` (the person with the problem). It decides which record the proposed row belongs in, and is never read out of the role |
| `who` | **required** | the character — what makes this person this person |
| `wardrobe` | **required** | the wardrobe, completely. Never left to inference |
| `world` | **required** | the room, the framing and the light the baseline carries |
| `noun` | **required** | the word the model is given for the subject. **Never defaulted** — a vague noun is a vague face, and a default is this component deciding something about a brand's person that nobody asked it to decide |
| `baseline` | optional | a frame on this machine. Omitted: the best candidate the search found, which the dry run prints with its reason |
| `detail` | optional | the continuity board the format leans on. **Never a default** — the board is whatever the format needs that a face does not carry |
| `like` | optional | the words to search the footage with. Default: the role's |
| `collection` | optional | only this footage collection |
| `style`, `format` | optional | ids on the element library's `style/image` and `format/image` lists |
| `out`, `label` | optional | where the run is filed, and the folder's name |
| `name`, `lane`, `fronts`, `problem`, `reads`, `hair`, `build`, `face`, `setting`, `register`, `age`, `note` | optional | fields carried straight into the PROPOSED registry row. Nothing is invented for one that is absent |
| `checks`, `rules` | optional | extra judge tests, extra standing rules |

**Back:** `{out, brand, role, id, kind, baseline, steps[], prompts, sheets,
filed, drive, register, held, still_open, check}`.

## The nine steps, as declared steps

    1 GAP       a brief names a role the bank has no one for      files
    2 SEARCH    the owned footage, for that archetype             files
    3 BASELINE  one frame — a real shot of a real room            files
    4 MASTER    reference in, a DIFFERENT person out              GENERATE
    5 ANCHOR    the 3x3 sheet off the master                      GENERATE
    6 DETAIL    the continuity board the format leans on          GENERATE
    7 BIBLE     character.md — who they are, what is load-bearing files
    8 REGISTER  the proposed row — a person registers it          files
    9 MIRROR    Drive: the sheets, and a small copy               files

**The anchor references the MASTER, never the last output.** That one
substitution is what stops drift compounding, because nothing is ever derived
from a derivative. A step whose reference was held is SKIPPED and says so.

**`run_kit.stage.Chain` was not used, and here is why.** `Chain` runs a step
as one text prompt to `claude -p`, reuses a finished step by prompt-sha, and
writes a `<key>--<label>.md` per step. Six of these nine steps make no model
call at all, and the three that do send a picture to an image door and get a
picture back — there is no text answer to save, reuse or diff. Forcing them
through `Chain` would mean lying about what a step is. What `run-kit` DOES
give this component is used: `run_kit.prompts` for the numeric `-vN-` rule and
the prompt sha, and `run_kit.filing`'s run path.

## The four questions

- **Engine + owner:** `casting/` (`paths` every path, found by walking up ·
  `bank` the registry, read only · `search` the baseline, through
  image-production's asset reader · `prompting` the three prompts ·
  `generate` the picture door · `judge` this component's questions, through
  image-production's judge · `gates` the three gates · `filing` where things
  go · `registration` the proposal · `engine` the request and the nine steps ·
  `dryrun` the free dry run), plus `cast.py`, the thin CLI. **the owner.**
- **Definitions + curator:** `prompts/*-vN-damon.md` — the master, the anchor,
  the detail board and the standing rules. **the owner** holds the approval gate.
  The element lists are NOT here — they are `components/elements`' and are
  asked, never copied. **The cast records are NOT here** — they are the
  brand's, curated by people, and this component only reads them.
- **The plane it emits:** **the caller's run.** Text lands in `out` (default
  `runs/casting/<brand>/<label>/`): `<step>--prompt-as-sent.txt`,
  `elements.json`, `check.json`, `run.json`, `held/<step>-why.md`,
  `register/proposed-row.json`, `register/REGISTER.md`, `bible/character.md`.
  Pictures land in `brands/<brand>/ai-cast/<id>/` exactly as
  `the team notes/avatar-builder/build.py` already files them, and are mirrored to
  `Team Drive/brands/<brand>/ai-cast/<id>/`. Media is never git (workspace
  rule 3; `.gitignore` already catches `brands/**/*.png`).
- **Manifest per entry:** `run.json` — the request, the bank's answer before
  the build, the baseline and why, every step with its status, every sheet
  with its verdict, what was filed, the proposed row, what is held, and
  `state` (`filed` or `held`).

## Gates

Three of the five shared gates (`components/quality-checks`, via `hold()` → a
gate-keyed `check.json` in the run folder). `--gates warn` records the same
verdict and carries on.

- **inputs** — before any model runs. The brand is real · the role is named ·
  the registry is readable · **the role is one the bank does NOT already
  cover** · `id`, `kind`, `who`, `wardrobe`, `world` and `noun` are given ·
  the baseline exists and is a file ON THIS MACHINE (a remote url is a
  declaration the model never sees; nothing here downloads).
- **elements** — before any model runs. Every `style` and `format` named is a
  real, DEFINED row in the element library. An unknown id is refused naming
  the real ids; a row whose `what` starts `[TO DEFINE` is refused as named but
  not defined yet. Recorded in `elements.json`.
- **media** — after the judge. A generated sheet the judge failed is HELD: it
  is never filed into the brand's cast folder, no later step references it,
  and the reason is written to `held/<step>-why.md`. **The gate does not
  judge.** A hold is a work item, not a verdict: fix the prompt, never the
  picture.

## Keys

Read **by name**, never by path: the process environment first, then the macOS
Keychain via `security find-generic-password` (service `daemn-<NAME>`, account
`damon`). Never out of a file in the repo or the home folder, never printed,
never logged, never written into a run record. Read at CALL time, never at
import time — a declared test proves it in a fresh interpreter with no key and
an empty `HOME`.

The key the generating steps spend is the one `casting/generate.py` names
(`KEY`), through `tools/image-production`'s edit row; the judge's key is
`tools/image-production`'s judge's, which owns that route.

## The free dry run

`--dry-run` on every path, and `who` / `find` are free always. It prints the
role, whether the bank already covers it and who, every baseline candidate
with its reason, the baseline it would pick, **the prompts exactly as they
would be sent**, whether the door and the key are on this machine, what the
judge would ask, what the gates would say, and where every file would land.
**It starts no model, makes no model call, judges nothing, writes no file and
touches nothing on Drive.** Exit 1 when anything required is missing or a gate
would hold.

## Rules this component holds itself to

1. **No brand, product, person or model name in code or in a prompt.** Two
   tests enforce it against the real `brands/` tree — one for brand folder
   names, one for every banked person's id.
2. **`brands/` is read-only to this component** (`the team notes/CLAUDE.md` rule
   5), with the one exception the lab tool already had and which was not
   changed on assumption: the built PICTURES land in the brand's
   `ai-cast/<id>/`, as they do today. Every WORD — the row, the bible — is
   proposed into the run folder and moved by a person.
3. **Refused, never guessed.** An unknown element, an undeclared `kind`, a
   missing `noun`, a role already cast — each stops the work and names what to
   do instead.
4. **Nothing is ever deleted on the Drive mount.** A rebuild gets a new id and
   every link already handed out dies; supersede into `_superseded-<date>/`.
5. **Filing never stops a delivery.** A mirror that cannot be written prints
   SKIP and the reason; the sheets are already on this machine.
6. **`sys.path.append`, never insert at 0** — a folder at position 0 shadows
   the stdlib. No file here is named after a stdlib module, and a test checks.
7. **A changed prompt is a NEW file** `-v<N+1>-damon.md` beside the old one;
   highest number wins, numerically. Never edited in place.
8. **This component never coins a name.** The `id`, the character's name, the
   role: all the caller's. A name not given is a field left out of the
   proposed row, never a guess.

## Two things a reader should know about the records

**The registry is mid-move, and this only reads it.** On 2026-09-22 the
brand's `core-avatars/casting` folder was moved to `ai-cast/casting` on the
Drive, and a working tree on this machine has already moved it in the repo
too. Both paths are looked for, in that order, and the first on disk wins;
finding BOTH is reported as a problem, because two registries for one brand
splits a cast silently. Nothing here writes to either.

**The two brands on disk keep their cast two different ways.**
`the team notes/casting/build_cast.py` renders from `roster.json` +
`authority.json` and REFUSES a brand that has neither. This component answers
that brand anyway, from its `ai-cast/<id>/character.md` bibles — refusing
would mean saying "no one plays that role" about a brand whose people are all
sitting one folder away, which is the failure the bank exists to prevent
arriving from the other side. On a bible-only brand the match is over the
bible's LEAD (its title and the paragraph before the first sub-heading),
because that is the only part that says what a character is FOR; a near-tie
between two people is reported with both, never resolved silently.

Tests: `python3 components/casting/tests/test_casting.py` — 51 tests, stdlib
`unittest`, must pass on `/usr/bin/python3` (3.9). Stubbed element library,
footage reader, generator door and judge; temp dirs only. No network, no
model, no model call, no real key, and nothing written outside `tempfile` — in
particular never the real `brands/`, `runs/` or any Drive mount.
