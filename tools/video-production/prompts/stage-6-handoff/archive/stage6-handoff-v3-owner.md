# Stage 6 · Handoff — v3

*v3 (2026-09-18): two additions from the scene-authoring and
intimate-copy doctrine (09-17/09-18) — THE LOOP, a new section after
POST naming the piece's one open loop and its payoff; and the scene arc,
a table appended to THE INTENDED SHAPE mapping emotion/outcome/breathing
room per scene. No new variables.*

*v2 (2026-09-17): four new sections after KNOWN ISSUES — LINE COVERAGE, POST, THE RECEIPT, THE NAME. The session pastes two new variables: `{ledger}` — the run's `ledger.json` — and `{lines}` — the run's `lines.json`.*

Write the handoff pack: what the editor receives with this scene set, and
what it guarantees.

**Every example in this prompt is illustrative only.**

The editor did not sit in on the production. This document is the only
thing standing between them and a list of questions nobody is around to
answer. Write it for someone competent who knows nothing about this piece.

---

THE PRODUCTION DOCUMENT

{production_document}

THE SCENE SET AS GENERATED

{scene_manifest}

THE QC REPORT

{qc_report}

THE LEDGER

{ledger}

THE LINES

{lines}

---

Return exactly these sections.

## WHAT THIS IS

Two sentences: what the piece is, who it is for, and where it runs.

## THE SCENES

A table, one row per delivered scene.

| # | File | Function | Runtime | Contains | Flags |
|---|---|---|---|---|---|

**Contains** is what the editor can actually cut from it: the dialogue
line, the action, the moment. Written so they can find a beat without
scrubbing.

**Flags** carries anything the QC gate could not clear on that scene,
verbatim, or `clean`. A flagged scene is delivered, not hidden — the
editor decides whether it is usable at the size it plays. A flag whose
defect class is `ceiling` says so in the cell: the editor should know it
was never going to be re-rolled.

## THE INTENDED SHAPE

The cut this set was built for: which scene opens, the order, roughly what
each segment should run, and where the piece slows down. This is a
starting point, not an instruction — the editor may find a better cut, and
the set is built so they can.

Where the production generated an ALT scene, say what the choice is and
what each option does to the opening.

**The scene arc.** One row per scene, mapping the emotional curve of the
piece:

| Scene | Emotion carried | Outcome reached | Where it breathes |
|---|---|---|---|

The edit's job is to preserve this arc: scene count and scene length are
authored choices serving it, never a generation limit. If the delivered
cut's lengths are not explained by this table, the edit drifted from the
scenes as authored — fix the edit, not the scenes.

## WHAT IS LOCKED, AND WHAT IS FREE

**Locked** — things the edit must not break: the speaker on their own
line, the claim boundary at the offer, the product's label legibility
where it plays large, and any continuity the ledgers protect.

**Free** — pace, trims, shot order within a beat, music, captions.

## KNOWN ISSUES

Everything the QC gate flagged, gathered in one place, each with a plain
statement of whether it can be fixed at the cut, needs a re-roll, or is
acceptable at the size it plays. If nothing was flagged, say so.

## LINE COVERAGE

A table, one row per line in THE LINES: the line id, the line as written,
and the scene file that carries it.

| Line | As written | Carried by |
|---|---|---|

Every line is carried by exactly one scene. A line with no scene is an
uncovered line, and **an uncovered line means the pack is not
deliverable** — say so in this section, in those words, name the line,
and do not soften it into a note. A line carried by two scenes is named
too, so the editor knows which one to keep.

## POST

The edit-time list, gathered from every scene's `Post (edit-time, never
generated):` slot: what the editor builds that the model did not —
picture-in-picture, circles, borders, keying, captions and on-screen text,
push-ins, transitions, music. One row per item, with the scene it belongs
to. Nothing here was generated into a clip; if it was, that is a KNOWN
ISSUE, not a POST item.

## THE LOOP

The one open loop planted in the opening ten seconds of this piece, and
exactly where it pays off. One line each, so the editor knows what to
protect: the loop is the reason the viewer watched to the end, and a cut
that closes it early kills the piece.

## THE RECEIPT

From THE LEDGER, and only from it:

- jobs submitted, by station and by model slug **as recorded** — the slug
  the ledger holds, never the marketing name;
- credits and dollars, total;
- of which re-rolls — how many jobs and how much;
- **billing-ambiguous jobs listed separately** — blocked, refused,
  stuck — with their status, never folded into the billed total.

If the ledger has gaps, say what is missing rather than estimating. A
receipt is a record, not a guess.

## THE NAME

The `ad_name` and the manifest the naming gate produced
(`machine/deliver.py`), verbatim. Nothing leaves a run unnamed: if the
naming gate has not run, this section says so and the pack is not
deliverable.

## THE SOURCE

Where the scene files live, what the naming means, and where the
production document and prompts live if the editor needs to see why a
scene is the way it is.

---

Write the pack and nothing else.
