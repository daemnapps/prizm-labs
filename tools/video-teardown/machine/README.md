# The swipe machine

A competitor's video goes in one end. A brief comes out the other. Every
prompt and every output is visible on the way through.

Markdown mirror of the session artifact (2026-08-20). Damon reads the HTML
board; this file is the version for anyone working in the repo.

## The conveyor

Nine stages, one video at a time. Each takes the last one's output and hands
on its own — nothing is re-derived, nothing is skipped.

| # | Stage | What it does | Engine |
|---|---|---|---|
| 0 | Triage | Cheap first look: which lane, and is a real human on camera | Gemini (video) |
| 1 | Teardown | The objective record — scenes, mechanics, psychology. **Frozen** | Gemini (video) |
| 1c | Doctrine | The source read against the doctrine, and banked | Claude |
| 1b | Audience | Which avatar, which funnel, which market state | Claude |
| 2 | Spec | The record abstracted into a brand-free construct | Gemini (text) |
| 3 | Injection | Substitution, never rewrite — their transcript is the template | Claude + brand files |
| 4a | Placement | Lane, product entry, awareness in/out, the runtime budget | Claude |
| 4b | Hooks | Control + five variations. All ship to test; the machine never picks | Claude + hook ledger |
| 4c | Expansion | Gated moves — each names the baseline line it serves or stays out | Claude |
| 4d | Close | Objection at the flinch, then the guarantee-led close | Claude |
| 5 | Brief | The product. General lane, or creator lane for her own formats | Claude |

Stages 0–2 read *their* material. 3–4d put *ours* into it. 5 is where the two
meet.

## Running it

    python3 run.py <video>                     one video, all the way
    python3 run.py --queue                     everything sitting in queue/
    python3 run.py <video> --only 4b --redo    re-run one stage after a prompt edit
    python3 run.py <video> --from 4a           pick up where a stopped run left off
    python3 run.py --board                     just rebuild the page

    --brand <brand>        which brand map to resolve variables from (chain.py)
    --lane general|creator which stage-5 prompt runs
    --var video_count=2    supply a run-time variable the creator lane needs

Damon never runs these — a session runs them on his behalf. The interface he
uses is the sentence "run these five" and the board.

## What a run leaves behind

    runs/<slug>/
      run.json          state for every stage: status, model, seconds, sizes
      doctrine.json     the doctrine read of the source, as the bank reads it
      0-triage.md …     one output file per stage
      prompts/          the exact prompt that was sent, brand material filled in
      source.mp4        symlink to the video (never committed)
      poster.jpg        first frame, for the board

`board.html` is rebuilt after **every** stage, so the page fills in while a
run is going. It shows, for each stage, the prompt on the left and what came
back on the right, and flips any prompt between the editable version and the
filled-in version that actually got sent. That pairing is the whole point:
the work is reading the output and tightening the prompt that caused it.

## The framework bank

Damon's ruling, 2026-09-18: *"every time we run a swipe, we'll run it through
a marketing doctrine step too so we have full awareness of it and can clearly
identify the unique framework of that video and bank it for later."*

Stage 1c reads one swipe against the doctrine — the shape it follows, the
sections it carries, the awareness it picks the viewer up at and puts them
down at, what it leads with, the want it rides, the moves it uses, the mood,
and one line on what is worth keeping. It ends in a fenced `json` block, which
`run.py` files as `runs/<slug>/doctrine.json`.

`framework_bank.py` puts every one of those on one shelf:

    python3 framework_bank.py                        rebuild the bank
    python3 framework_bank.py --awareness problem-aware --signature mechanism
    python3 framework_bank.py --technique concentration
    python3 framework_bank.py --query "guarantee"    free text, whole row
    python3 framework_bank.py --json                 rows, for something that reads

It writes `runs/framework-bank.json` and `runs/framework-bank.md` — one row
per swipe, with a link back to the run it came from. A filter prints the
matching rows and leaves the written bank alone.

It is rebuilt at the end of every run and it never stops one: it only
compiles what stage 1c already filed, a reading it cannot parse is skipped
with the reason printed under **Not banked**, and the bank failing to compile
at all is a `python3 framework_bank.py` away.

Regenerate, never hand-edit — a correction belongs on the run it came from.

## The second door — composing from a choice

Damon's ruling, 2026-09-18: *"with all of the different sections we should
begin to assemble actual frameworks to create ads strategically. We use
swipes as the baseline, but since we have a fundamental system and
understanding of who we are speaking to and how and what formats they're
receptive to, we can pump out mounds of video and photo ads."*

Every run above starts from somebody else's asset: swipe it, read it,
abstract it, inject ours. `compose.py` is the other way in — no swipe, no
video. A run starts from a CHOICE instead: an avatar, an awareness level, a
format and a framework (from
`components/marketing-doctrine/ad-frameworks.json`), and the machine WRITES
the construct those four choices imply rather than abstracting one off a
source.

    python3 compose.py plan --brand <brand> --avatar spot-hider \
        --sub sun-damage-reckoner --awareness problem-aware \
        --format single-presenter --framework mechanism-led --route ai
    python3 compose.py run   ...same flags...          plan, then run the chain
    python3 compose.py grid --brand <brand> --avatar spot-hider \
        --awareness problem-aware,solution-aware \
        --formats single-presenter,demonstration \
        --frameworks mechanism-led,pas [--go]

`plan` never calls a model — it opens the run folder (`triage_lane:
FRAMEWORK`), files stand-ins for the four stages that would have read a
source (a SOURCE record saying there is no swipe; the market state in stage
1b's own labelled-slot shape, so every parser downstream is unchanged), and
resolves every variable of every stage so a refusal arrives before any money
is spent. Unknown ids — a framework, a format, an awareness level, an avatar
— are refused **by name**, with the ids that do exist printed. `run` does
the same and then hands off to this file's own `run_video()` — there is no
second copy of the chain in `compose.py`.

On the FRAMEWORK lane, stage 2 is replaced by **stage 2f — the compose**: it
writes the replication spec straight from the chosen framework's sections,
phase by phase (each phase naming its section, its technique and the scene
shape that technique takes), in the exact shape stage 2 prints, so stage 3
onward runs completely unchanged. The board shows a FRAMEWORK run like any
other.

`framework_bank.py --promote <run-label>` copies a run's OBSERVED framework
(its `doctrine.json`) into `ad-frameworks.json` as a new row, status `seed`.
**Run this only on Damon's own word** — `ad-frameworks.json` is curated
doctrine, not a compiled shelf, and the two must never quietly become the
same file.

## Where the pieces come from

Nothing here re-implements the chain. `chain.py` is the only file that names
a stage, a prompt path, or a brand file; it points at the existing prompts in
`content-machine/prompts/` and the existing runners in `content-machine/tools/`.
Change a prompt in its own folder and the machine picks it up on the next run.

Brand variables resolve through `chain.py`'s `BRANDS` map, which mirrors
`brands/<brand>/chain-variables.md`. If a path moves there, it moves here in
the same commit.

## Known trap

Placeholder checking runs against the prompt **template**, before
substitution — never after. `brands/<brand>/identity-anchors.md` documents its
own `{identity_anchors}` variable in prose, so a post-substitution check
false-alarms and halts the chain. `gemini_text.py` hit the same trap first and
carries the same note.

**Tests and the live `runs/` folder.** `test_compose.py` opens run folders
exactly the way `compose.py run` does, and one of its tests uses the real
default label of the <brand> / spot-hider / sun-damage-reckoner choice. On
2026-09-18 its tearDown removed a real, in-flight run under that label four
times in one hour while another session was running the chain for real —
"something keeps deleting the run folder". Since then the suite redirects
every run folder to a throwaway temp root at import (`run.RUNS` and
`chain.runs_root`, patched before anything opens a folder) and its cleanup
refuses to touch anything outside that root. What follows from it:

- A test never opens a folder under `machine/runs/`. A new test patches the
  root the way `test_compose.py` does, at import, before any folder opens.
- `compose.py`'s default label is deterministic — two sessions running the
  same choice land in ONE folder and overwrite each other's `run.json`. Name
  the run with `--label` whenever that can happen.
- Nothing else on this Mac prunes `machine/runs/`: no launchd job, not
  `board.py`, `serve.py` or `doctor.py`, and not the hourly pull (a plain
  fast-forward, never a clean). If a folder disappears, look first for a test
  or a tool holding the same label.

## Not built

- Scraping creators' top posts in automatically (Apify) — the machine starts
  from videos already on the machine. Next up: pulling in Instagram
  influencer videos this way, straight into the swipe library, so the
  teardown/brief chain can run on them (Damon, 2026-08-24).
- The image lane is separate and already exists at `content-machine/image-lane/`.
- Programmed editing — turning a finished brief into a cut asset — is the next
  half, and is not part of this conveyor yet.
- **Editable, versioned briefs (Damon, 2026-08-24).** Right now a brief is
  one shot: stage 5 writes it, stage 6 draws its frames, stage 7 assembles
  it, done. Wanted next: reopen a finished brief and regenerate a single
  scene's image without rebuilding the whole thing; edit the brief's own
  copy directly (not just re-prompting stage 5) and have that edit kept as
  its own version, same as a prompt change is; and have those hand-edits be
  readable back — so a session can see what Damon actually changed on a
  brief and use that to tighten the stage 5/6 prompts, the way version
  tabs already let him compare prompt output today.
