---
name: task-breakdown
description: Break any problem, workflow, meeting transcript, or written ask into task cards per the workspace decomposition convention. Use when someone says "break this down", "task breakdown", "card this workflow", "turn this transcript / these notes into task cards", hands over a step-by-step workflow to assess, or describes repeated work that needs decomposing before design or automation. Drafts cards only — people correct them; it never binds decisions.
---

# Task breakdown

> **Standalone skill:** activates no component — breaks a problem into task cards; touches no component.


Turn a raw input — meeting transcript, typed notes, a dictated ask, or a
workflow someone hands over already written out — into draft task cards
under the workspace decomposition convention. The convention itself
(card format, stop-test, runbook) is defined in
`new-workflow-design/intake-template.md`; read its "Task cards" section
before running, and follow it over this file wherever they differ.

## What to do

1. **Locate or create the build.** Ask which problem this belongs to if
   unclear. Existing build → work in `new-workflow-design/builds/<build>/`.
   New problem → create the folder with `intake.md` scaffolded from
   `new-workflow-design/intake-template.md`, an `inputs/` folder, an
   empty `task-cards.md`, and add the row to
   `new-workflow-design/problems.md` (mark unknowns TBD). Fill the
   template's `Interface` field only when the input states or clearly
   implies the key deliverable's type; otherwise TBD with the default
   note — never guess a type (ruled 2026-08-20).
2. **File the input** unedited into `inputs/<date>-<short-name>.md`. If
   the input was given as chat text, save it verbatim with its source
   and date noted. It is evidence — never rewrite it.
3. **Sort every statement** into five buckets:
   - outcome someone needs → a card's story line
   - how-it's-done-today (tools, platforms, habits) → that card's Today
     field, quoted
   - watchout / constraint → a done-when line or a never
   - decision claim ("let's just use X") → the decided-or-open list
   - pain or numbers → the build's money line
4. **Draft one card per task** in the template's format: Story (no
   tool/platform nouns) · Done when · **Today block** (Process + Done
   by — evidence of how it runs now and who runs it; tool nouns live
   only here; DECIDED markers only where a human already bound one —
   never mint one yourself) · **Proposal block** (Process + Done by —
   the proposed way and occupant, with the human ground or the
   load-path named; a proposal until built and proven). Two-block form
   per the template (adopted 2026-08-19); never emit the old flat
   Today/Done-by pair on new cards. Leave the template's **Shared
   parts:** line in place but EMPTY — it is the lead's to fill at
   carding (rule of three, 2026-09-02), never a drafter's guess.
5. **Question the labels — stop-test both directions.** Something
   called one task may hide several or be a whole workflow; something
   called a workflow decomposes until every card sits on one ladder
   step and one side of the builder-or-occupant cut. Propose splits
   with reasoning; flag tasks nobody named as NEW.
6. **Cite or ask.** Every field cites an input line or an owner's
   answer. No source → write an open question instead. Never fill a gap
   with a guess — visible gaps are the feature.
7. **Finish with three lists:** open questions grouped by who can
   likely answer them · the decided-or-open list for the human who
   binds · tasks surfaced as NEW. Offer to run the gap interviews (one
   question at a time, async fine).
8. **Visualize the cards — standard output, every run.** Generate one
   Mermaid-based markdown view for Obsidian (changed from HTML
   2026-08-13, the developer) at `builds/<build>/task-cards-view.md`. Layout:
   - Header: build name, ledger ID, date, DRAFT status, counts (cards ·
     NEW tasks · gaps · open decisions), and a "GENERATED VIEW —
     regenerate, never hand-edit; `task-cards.md` is the record" line.
   - One `mermaid` flowchart of the carded workflow: one node per card
     (id + short name), edges following the workflow's real sequence /
     dependency structure, `classDef` styling: NEW tasks green, cards
     carrying a gap red, assumption-marked cards amber (a card that is
     both NEW and gapped shows red — gaps outrank). Keep node labels
     short; details live in the card sections below, not in the diagram.
   - Then one section per card mirroring the card fields exactly, using
     Obsidian callouts for the highlights — the highlights are the
     point: `> [!missing]`/`> [!danger]` for gaps, `> [!warning]` for
     assumptions/(unchecked), `> [!question]` for open/empty fields.
   - Close with the three lists (step 7) in plain markdown.
   Plain fenced ```mermaid blocks and standard callouts only — no HTML
   tags, no plugins beyond Obsidian defaults. The view is regenerated
   whole on every run (overwrite, don't patch); it is a projection of
   `task-cards.md`, which remains the only record. Also send/render the
   file to the user in-session where the surface supports it.

## Walls

- Draft-only: cards stay drafts until people who know the work correct
  them; the person who does the work outranks the card.
- Never bind a DECIDED marker, never sign a card, never present a
  ladder placement as settled — placements are proposals until built
  and proven.
- Brand-agnostic (workspace rule 7): no brand names in cards' stories;
  brand context enters via the `brands/<brand>/` layer at run time.
