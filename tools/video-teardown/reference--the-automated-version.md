# The video teardown machine

A swiped video goes in. A shot-ready creator brief comes out — script, hooks,
wardrobe, and a picture on every scene.

## What it actually does

1. **Reads the video.** Watches it (Gemini), decides what kind of video it
   is, and writes down every scene shot by shot — what's on screen, what's
   said, the wardrobe.
2. **Makes it ours.** Substitutes our brand into the format that already
   works, without changing anything that's *worn* or *revealed on camera* —
   only what's held up or referred to.
3. **Runs the DR loop.** Writes the opening hooks straight off the source,
   then decides where our product enters, then (if the source needs it)
   builds out the middle, then closes it, then checks the whole thing
   against the source and the rules.
4. **Writes the brief.** One document — the concept, the shots, the wardrobe
   on every scene, a picture for every scene. Nothing the maker doesn't need.
5. **Makes the pictures.** One generated reference image per scene, seeded
   so the room and the person stay consistent shot to shot.
6. **Puts it in the Drive.** The finished brief becomes a real Google Doc
   in the run's own folder — editable, pictures in it, beside the source
   video. Re-running the same brief updates that Doc rather than leaving
   a second copy, so a link you have sent stays the right one.

## The one decision that changes everything: the lane

The very first stage (**Triage**) looks at the source and calls one of four
lanes. Everything downstream reads that call:

| Lane | What it means | What changes |
|---|---|---|
| **ALREADY AN AD** | The source already has a hook, a proof beat, an offer | **Expansion is skipped.** Nothing gets added — a proof run added zero beats to an ad and it still worked. The close builds straight off the injection. |
| **ORGANIC** | No pitch anywhere in the source | **Full chain runs.** Nothing commercial exists yet — the hooks, the placement, the expansion, all of it gets built from nothing. |
| **STATIC / SEQUENTIAL** | Not a video — a still or a carousel | This chain stops. Belongs in the image lane instead. |

### The tracker is the list, not a copy of it (2026-08-27)

`tracker.py` reads the brand's own creator sheet through the service account.
`--check` says what the sheet has that the machine doesn't and the other way
round; `--sync` rewrites `creators.json` from it. The sheet id lives in
`brands/<brand>/tracker.json`, never here.

This exists because a hand-typed copy silently went stale: a signed partner sat
on the sheet marked *waiting for brief* and the machine had never heard of her,
and two more appeared during a single afternoon. Run `--check` before a pull;
a row that contradicts itself gets said out loud rather than quietly doing
nothing.

### Views come first (Damon, 2026-08-27)

Any list of creators or posts is sorted by view count, biggest first, before
anything else is applied. Fit, usability and how many videos someone still
owes are filters laid over that order — never a reordering. Reach is the thing
being bought; a list re-sorted on someone's judgement hides it.

### What counts as a source (Damon, 2026-08-27)

Only **video ads** get torn down: the creator performing, on screen. A quote
card over stock footage, a still, a carousel, or b-roll whose whole content is
the caption over it is not a source, no matter how well it scored.

Triage will not stop these — its STATIC / SEQUENTIAL lane tests the *file*, so
anything that arrives as a real mp4 with motion and sound passes as ORGANIC
and the full chain runs. And the sourcing rank will not stop them either: that
is `views + likes + comments` with no eyes on it. **The check happens before
the run, by whoever picks the post — look at the thumbnail.** A quote card
ranked first on a creator's page on 2026-08-26 and took thirteen stages to
produce a brief with nobody in it.

A second decision happens after placement: it asks not just *"where does our
product go"* but *"where does the viewer cross into recognising their own
problem"* — because on organic sources, that crossing is usually a **problem
named on screen**, with no product in frame yet, not a product shot. Only if
neither exists at all does a brief become a *hook asset* (an opening that
earns a click and hands off, never asked to sell).

## The chain, in the order it actually runs

Labels below match run order — not the order they sit in the shared team
config (`chain_config.json`), which uses its own lettering for its own
reasons. See `prompts/README.md` for the mapping between the two if you ever
need to trace a stage back to the shared file.

| # | Stage | Reads or writes |
|---|---|---|
| 0 | Triage | reads — decides the lane |
| 1 | Teardown | reads — the objective record, scene by scene |
| 2 | Spec | reads — abstracted into a brand-free construct |
| 3 | Injection | writes — our brand substituted in, never a worn/revealed object |
| 4a | Read | reads — lane, opening beat, awareness entry (before the hooks exist) |
| 4b | Hooks | writes — control + five variations, all filmed, none picked here |
| 4c | Placement | writes — where the product enters, seeing the hooks first |
| 4d | Expansion | writes — gated moves, skipped entirely on an already-ad |
| 4e | Close | writes — the objection, the offer |
| 4f | Audit | reads — seven checks against the source, reports only |
| 5 | Brief | writes — the one document the maker receives |
| 6 | Frames | writes — a generated reference picture per scene |
| 7 | Final brief | assembles — pictures placed into the brief, nothing else touched |
| 8 | Document | lays the brief out for Google Docs, pictures in place |
| 9 | Doc | creates it in the Drive folder, editable, link on the run |

## Where the prompts live

`prompts/` — one folder per stage. **Each folder shows exactly one current
prompt.** Every earlier version is in that folder's own `archive/`. If two
prompts sit at the top of the same folder, something is wrong — the machine
always resolves to the highest version number, so an old file left visible is
confusing, not dangerous, but it shouldn't happen.

The machine picks up a new version automatically — drop a file in, bump the
number, nothing else to change or point anywhere.

## Where this lives

> **PRIMARY, SETTLED 2026-08-25 (Dayu).** Nothing was ahead in
> `~/devel/daemn` when this moved — confirmed by Dayu, not an open question.
> Work here directly; the sandbox mirror is retired for this build.
>
> **GRADUATED 2026-08-25 (Dayu ruling): THIS folder is primary.** The line
> below recorded the pre-graduation state and is kept for history. From today
> Damon works here directly — same prompts, same sessions, same board, new
> path — and the `~/devel/daemn` mirror stops. Damon's correction pass on
> this note outranks it.

Source of truth *(pre-graduation)*: `~/devel/daemn/video-teardown-machine/` (Damon's private
repo). Mirrored into `ai-workspace/lab/damon/video-teardown-machine/` so the
team can see it — that copy is a bridge, not a fork. Changes get made in
daemn first, then re-bridged the same way; the ai-workspace copy is never
edited directly.

## Running it

    python3 run.py <video>              one video, the whole chain
    python3 run.py --source <folder>    every video in a folder, skips what's done
    python3 run.py --stages             see the current prompt for every stage
    python3 board.py                    rebuild the live page

The board (`board.html`, served on your Mac) is the working surface — every
prompt beside its output, version tabs per video, a self-check that runs
every 10 minutes and flags anything it can't fix on its own.
