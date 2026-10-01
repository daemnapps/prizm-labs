# Context awareness — why the chain got a scout

Added 2026-08-24, on Damon's call: *"we need to start really building
contextual awareness and the ability to sift through all brand context when
writing copy — this is the type of logic that turns our marketing from AI
templates into true breakthrough."*

## What was wrong

The chain read exactly four brand files, hard-wired into the runner:

- `customer/avatar.md`
- `customer/language-bank.md`
- `offers/offer-bank-legacy.md`
- the product file named on the command line

That is ~61 KB out of ~400 KB of readable brand context. Everything else
<brand> knows was invisible to the copy stages, on every run, regardless of
what the video was about:

| Ignored | Why it mattered |
|---|---|
| `customer/objection-bank.md` | The real answers to the doubts a video leaves hanging. Copy was written without them. |
| `creative/hook-ledger.md` | Exists **specifically** so a stage "treats a spent verbatim as ground it may not build on again." The video chain reads it; the copy chain didn't — so copy variations could recycle spent lines forever. This is the template failure in one file. |
| `channels/creators/<person>.md` | The profile of the creator **in the video we ran twice**. Copy written in her voice, never having read who she is. |
| `identity-anchors.md` | Likeness rights and what may be claimed about whom. |
| `competitive/evora/*` | A full competitor ad-library teardown and transfer matrix. |
| `customer-language/evidence/*` | 86 KB of raw voice-of-customer — focus group, Gorgias tickets, interviews. Where real language actually lives. |

Same four files every time is the definition of a template. The output was
true about the brand and indifferent to the video.

Separately, the chain had **no idea what day it was**. Stage 3 wrote "a
cardigan in July" because the source video said July — not because anything
checked a calendar. Right by luck in August; wrong the moment a flight runs
past summer.

## What changed

**A new stage — the context scout (`stage0`, displayed as `1b`).** It runs
*after* the concept brief, because it chooses from it.

1. `context.py` walks `brands/<brand>/` at run time and builds an index of
   every file: path, size, title, first real sentence, and the `status`,
   `contested` and `known-issues` lines the file declares about itself.
   Nothing is written to `brands/` — the index is derived, so it cannot
   drift from the files.
2. The scout gets that index plus the concept brief and picks what *this*
   video's copy needs. It must finish the sentence *"the copy will be
   different because this was read, in this way"* for every file it selects,
   and it must publish what it deliberately left out — that section is how
   the choice gets checked.
3. What it picks is loaded within a character budget and passed to stages 3
   and 4 as `{brand_context}`. Anything selected but not loaded is named in
   the bundle itself, so a stage can never mistake a dropped file for one it
   considered.
4. Files too large for a prompt (the raw Evora JSON, the 243 KB ranked ad
   CSV) are indexed as `NOT LOADABLE` rather than hidden — a stage should
   know they exist and that a person has to work through them.

**Real date awareness.** `{today}` now reaches stage 0, 3 and 4. Stage 3 is
told to write to the calendar it is actually in, never the source video's;
stage 4 treats a stale month as a correctness failure and cuts it. The scout
says in one line whether the date bears on the concept at all — and is told
not to invent a seasonal angle just to have something to write.

**Stage 4 gained a sixth check:** anything the chosen brand context
contradicts — a spent hook rebuilt on anyway, an objection answered
differently than the objection bank answers it, a creator detail that isn't
hers — is a correctness failure, fixed like a bad claim.

## What this does not do yet

- **The scout's choice is unreviewed.** It publishes its reasoning and its
  omissions on the board, which is what makes it correctable, but nobody has
  yet checked a selection against what a person would have picked. That is
  the next real calibration.
- **No cross-run memory.** Each run scouts fresh. Two videos for the same
  creator will re-read the same files and can still land on the same angle —
  the hook ledger blocks spent *verbatims*, not spent *ideas*.
- **The budget is blunt.** 60 KB of selection, first-fit, no ranking within
  the cut. A scout that picks well and then loses the best file to arrival
  order is a real failure mode and has not been tested for.
- **One brand.** Only <brand> has enough context files for the sifting to
  mean anything. <brand> has none of this on file yet.
