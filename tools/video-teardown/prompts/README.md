# Prompts — the map

**One rule everywhere: each folder shows exactly one current prompt.** Older
versions live in that folder's own `archive/`. If two prompts sit at the top
of one folder, something's wrong.

```
prompts/
├── stage-0-triage/            triage        classifies the lane
├── stage-1-teardown/          teardown      the objective record
├── stage-1c-doctrine/         doctrine      the source read against the doctrine
├── stage-1b-audience/         audience      who OUR version speaks to
├── stage-2-replication/       spec          brand-free construct
├── stage-2f-compose/          compose       THE SECOND DOOR — writes the construct
│                              from a chosen framework instead of abstracting one
│                              off a swipe. FRAMEWORK lane only (chain.py's
│                              LANE_ONLY); runs in stage 2's slot, output in the
│                              exact shape stage 2 prints
├── stage-3-injection/         injection     substitution, never rewrite
├── stage-4-loop/
│   ├── 4a-read/               reading       lane · opening beat · awareness
│   ├── 4b-hook/                hooks         control + variations
│   ├── 4c-placement/           placement     where the product enters
│   ├── 4d-expansion/           expansion     gated moves + the depth pass
│   ├── 4e-close/               close         objection + proof + anchor + offer
│   ├── 4f-audit/               audit         reports, gates nothing
│   └── 4g-spice/               spice         the creative pass, every item receipted
├── stage-5-brief/
│   ├── creator-lane/          route creator (default) — the original brief, a
│   │   │                      content creator films it
│   │   └── named-creator/     variant addressed to one named creator (dormant)
│   ├── ai-lane/               route ai — the AI video machine generates it
│   └── hook-asset/            when nothing can carry the product (any route)
├── stage-6-frames/            one generated picture per scene
├── stage-7-inject/            puts the pictures into the brief
├── stage-7b-page/             the concept block she reads, written from the spec
├── stage-8-profile/           refreshes her brand-side profile after her run
├── reference/                 VARIABLES.md · CHAIN-QC.md
└── parked/                    written, not in the run
```

**The production route picks the stage-5 brief** (Damon's rulings,
2026-08-30): the route chosen per run — founder, creator or ai (`--route` on
the machine) — selects the lane, and a NONE verdict from 4a still overrides
everything with the hook asset. **The original brief is the creator brief**
(a content creator films it) and creator is the default route; founder has
no brief of its own yet and falls back to the creator brief while still
carrying "founder" into `{production_route}` at stages 3 and 5 — the run's
choice replaces the shared config's pinned "=creator", the pin that used to
mean nobody ever decided. The ai-lane brief is the creator brief re-grammared
for generation: cast / world / camera / product blocks up front, third
person throughout, and **no content of its own** — everything specific sits
in ⟨angle-bracket⟩ slots filled from the teardown record and the brand
files, because the machine is brand-, product- and avatar-agnostic.

## Why the folder names and the shared config's names don't match

The folders above are named for **when a stage runs** (4a is first, 4f is
last). The team's shared chain config (`lab/dayu/prompt-optimizer/regression/
chain_config.json`) names stages for **what Dayu built them as** — and his
file has `@stage4a`/`@stage4b`-style references baked into it that can't be
renamed without breaking his config. So the machine keeps his internal names
and only changes what's *displayed*.

| Shown as (run order) | Folder | Shared config's own name |
|---|---|---|
| 4a | `4a-read/` | `stage4r` |
| 4b | `4b-hook/` | `stage4b` |
| 4c | `4c-placement/` | `stage4a` |
| 4d | `4d-expansion/` | `stage4c` |
| 4e | `4e-close/` | `stage4d` |
| 4f | `4f-audit/` | `stage4e` |
| 4g | `4g-spice/` | `stage4g` (new 2026-09-18 — folder and key agree) |

If you're ever tracing a run back to Dayu's file, use the right-hand column.
Everywhere else — the board, `run.py --stages`, this README — use the
left-hand one.

Run order: 0 → 1 → 1c → 1b → 2 → 3 → 4a → 4b → 4c → 4d → 4e → 4f → 4g → 5 → 6
→ 7 → 7b → 8.

## The current version of each prompt

Bumped 2026-09-18 when Schwartz's frameworks became the doctrine the chain
runs on (`components/marketing-doctrine/`). **A framework is never restated
in a prompt** — the stage binds the slice it needs by path and the doctrine
stays the one place the five levels, the five stages, the seven techniques
and the sections are written down.

| Shown as | File | Doctrine it binds |
|---|---|---|
| 0 | `triage-v2-damon.md` | — |
| 1 | `stage1-teardown-v9-damon.md` | sections |
| 1c | `stage1c-doctrine-v1-damon.md` | sections · awareness · sophistication · techniques · desire · mood |
| 1b | `stage1b-audience-v6-damon.md` | desire · awareness · sophistication · 1c's read |
| 2 | `stage2-replication-v3-damon.md` | sophistication · 1c's read |
| 2f · FRAMEWORK lane only | `stage2f-compose-v1-damon.md` | sections · techniques · awareness · sophistication |
| 3 | `stage3-injection-v9-damon.md` | techniques |
| 4a | `stage4r-read-v4-damon.md` | awareness |
| 4b | `stage4b-hook-v12-damon.md` | awareness |
| 4c | `stage4a-placement-v10-damon.md` | — |
| 4d | `stage4c-expansion-v12-damon.md` | techniques · sections · sophistication · research |
| 4e | `stage4d-close-v7-damon.md` | offer-close · verification |
| 4f | `stage4e-audit-v4-damon.md` | awareness · sophistication |
| 4g | `stage4g-spice-v3-damon.md` | research-questions · techniques · mood · delivery · spoken · research · voiceprint |
| 5 · creator | `stage5-creator-brief-v26-damon.md` | — |
| 5 · ai | `stage5-ai-brief-v10-damon.md` | delivery · spoken (reads 4g's sheet; `voice` IS its spoken paragraph) |
| 5 · hook asset | `stage5-hookasset-v2-damon.md` | — |
| 6 | `stage6-frames-v2-damon.md` | — |
| 7 | `stage7-inject-v1-damon.md` | — |
| 7b | `stage7b-concept-v5-damon.md` | — |
| 8 | `stage8-profile-v2-damon.md` | — |

**Stage 1c — the doctrine read (Damon's ruling, 2026-09-18).** "Every time
we run a swipe, we'll run it through a marketing doctrine step too so we have
full awareness of it and can clearly identify the unique framework of that
video and bank it for later." Between the teardown and the audience pass, one
stage reads the **source as swiped** against the doctrine: the framework it
follows (a crosswalk row from the section list, or a plain description — never
a coined name), the sections it carries in the order it plays them, the
awareness level its viewer enters and exits on, the stage-move it runs, the
one desire it rides in the source's own words, the techniques visible per
section, the mood register, and one line on what makes the combination worth
banking. Everything is cited to a timestamp in the teardown record; an
uncited slot is left blank. It reads, it never improves, and it decides
nothing about our version.

It ends in one fenced `json` block, which `run.py` files as
`<run>/doctrine.json`. `machine/framework_bank.py` compiles every one of
those into the **framework bank** — one shelf, one row per swipe, queryable
(`--awareness problem-aware --signature mechanism`). That is the bank Damon
pulls a shape off later.

**Two reads of the same thing were removed to make room for it.** Stage 1
no longer prints `FRAMEWORK:` or `SECTIONS CARRIED:` — scene-level section
labels stay in stage 1, but the whole-asset read is 1c's. Stage 1b and stage
2 now receive `{doctrine_read}` and take the source's awareness and
sophistication from it rather than re-deriving them: 1b's job is the answer
for OUR reader, and stage 2 carries the signature forward.

**Stage 2f — the compose, the second door (Damon's ruling, 2026-09-18).**
"With all of the different sections we should begin to assemble actual
frameworks to create ads strategically. We use swipes as the baseline, but
since we have a fundamental system and understanding of who we are speaking
to and how and what formats they're receptive to, we can pump out mounds of
video and photo ads." Every other construct in this chain is abstracted off
a swiped source; this one has none — a run on the FRAMEWORK lane is opened
from a CHOICE (`components/video-teardown/machine/compose.py`: avatar x
awareness x format x framework), and stage 2f WRITES the construct that
choice implies instead of reading one off a video. It runs in stage 2's own
slot (`chain.py`'s `LANE_ONLY` + the FRAMEWORK route's `substitute`), phase
by phase off the chosen row in `components/marketing-doctrine/
ad-frameworks.json` — each phase naming its section id, its technique, the
technique's own scene shape and the mandate — in the EXACT shape stage 2
prints, so stage 3 v9 onward runs unchanged. The framework is a plan, not a
law: a section the market state does not call for is dropped, with a line
saying so.

**Stage 4g — the spice (Damon's ruling, 2026-09-18).** Clean injection first,
then the spice. After the words are locked and before the brief is written,
one pass asks what makes this format land for THIS avatar: the
format-relevance line, which cast voice it is spoken in (cloned, then
adjusted — with the rights entry named), the lookalike-type B-roll character,
the styling, the mood register per section. **Its research questions are
answered by the gatherer, never guessed** — an unanswered question is
`[UNFILLED]` and the item it would have supported is cut. It never changes
the SENSE of the script, and the brief reads its sheet as `{spice_sheet}`.

**Stage 4g v3 — THE SPOKEN SCRIPT (Damon's ruling, 2026-09-19: "humans
don't use em dashes when speaking").** Measured that day: a paragraph
written with em-dashes was read by the voice model with 1.3–1.7 s of
silence at every dash; a 7 s paragraph took 11 s. So the spice pass's
section 4 now rewrites every paragraph for the mouth — fragments,
contractions, the room's own markers, a pause as a full stop, a question
and its answer — at the colloquialism level the sub-avatar's dials and
research rows support (level 3 and above only in words the rows carry,
quoted), its rhythm matched to the brand's measured creators
(`{voiceprint}` — `brands/<brand>/creators/VOICEPRINTS.md`, off their own
audio), printed the way the voice model reads it, with the level and the
receipt on every change and a voice-settings line per section. The rules
are the doctrine's `{spoken}` slice. **The AI brief v10's `voice` field IS
that paragraph**, never re-flattened, and the video machine's gate refuses
an em-dash, a semicolon, a parenthesis or an ellipsis in it by name.

**The lane is recommended, not defaulted (Damon's ruling, 2026-09-18).**
Stage 1b now prints `ROUTE RECOMMENDED` alongside the market state. A run
started without `--route` takes that recommendation and prints it in the
start banner — the default "creator" survives only for a run where 1b has
not spoken yet. `run.json` records `production_route` and `market_state`.

**Stage 7b — the concept (Christine's round-two feedback and Damon's
rulings, 2026-09-18; supersedes the one sheet of 2026-09-02).** One run, two
documents, still. Stage 5 writes the spec — every frame with its source
line, wardrobe, sound and timing, which the pictures, the audit and the
editor need. Stage 7b writes the concept the creator reads, in the shape of
the very first brief creators said was easy to follow: format · inspired by
· product · length · core idea · two hook directions · five story beats ·
must-have shots · product points — then the script, straight through, which
the machine lifts from the spec. 180–280 words before the script. No
pictures anywhere in the Doc ("we literally don't need the pictures in the
google doc"); no six openings, no locked lines, no wardrobe, no light. The
one sheet (v3) went out to fifteen creators and was still too much — one
opted out, several went silent — so it is archived, not tuned. Still one
Doc per video ("I still want the separated briefs"). Her folder also holds
one **Start here** Doc — the brand's four shared sections from
`brands/<brand>/channels/creators/brief-intro.md` — built by
`machine/simplify.py`, which is also how an existing creator's briefs get
rebuilt in the new shape (staged in unshared `work/` until `--send`).

**Stage 8 — the profile refresh (Damon's ruling, 2026-08-30).** After a run
of a creator's OWN content, her brand-side profile rebuilds itself from
everything the machine holds on her — her record, all her teardown runs, her
existing profile — to the spec her brand declared. Creator runs only; swipe
runs record it skipped. The machine never knows where profiles live: the
brand says so in `brands/<brand>/channels/creators/profile-home.json`
(`spec` + `home`, workspace-relative), and a brand without that file keeps
no profiles. A stage-8 failure never stops the run — the brief and its Doc
still get made, and the profile can be re-run alone with `--only 8` or by
hand with `machine/creator_profile.py <handle> --brand <brand>`.
