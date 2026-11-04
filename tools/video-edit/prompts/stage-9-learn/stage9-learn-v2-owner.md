# Stage 9 — learn from his changes (v2)

*v2 (2026-10-16, the owner: "with any changes we make, they need to be banked and leveraged as knowledge for chain
updates and optimizations in real time as soon as we hit render ... a fully closed loop"). Runs every time Render is
pressed on the timeline page. New over v1: every row names the STAGE of the video line it teaches, so a lesson about
a picture goes to production, a lesson about a line goes to the brief, and only edit lessons bind the cut. The typed
feedback that produced changes is read too. Every rule of v1 survives.*

the owner (or the editor he trained) changed an edit on the timeline. Your job is to turn what changed into lessons the
whole video line can use, without over-reading one instance.

**Never invent an example.** Work only from the changes, the feedback and the rules on file below.

## What you are given

- `{ad}` — the edit: its brief, title, brand and format
- `{changes}` — each save on the timeline: when, the reason typed with it (`why`, may be empty), and `detail` — every
  bar changed: which track, what it was, what it is now (times in seconds, words, position on the frame in % of
  width and height, taken out, or cut in two). Also any scene remade, words changed, or prompt/model rewritten
- `{feedback}` — what was typed into "Ask AI" before those changes, in their words, and what was done for it
- `{learned}` — the rules and observations already on file for the cut

## What to do

For each real change (ignore a change undone by a later one), write one row:

- `id` — a short kebab-case name for the rule, the same id as an existing rule or observation when it points to the
  same thing
- `what_changed` — the measurable difference (the hook moved from 16% to 30% of the height; B-roll at 12.1s cut to
  2s; a caption word respelled; a scene's clip prompt rewritten to keep the hands in frame)
- `his_words` — his reason or feedback, quoted exactly, or an empty string when he gave none
- `rule` — the general rule this points to, one plain sentence the stage could follow. If he gave a reason, the rule
  comes from the reason, not from the numbers
- `stage` — which part of the line should learn it, one of:
  `edit` (cut, timing, B-roll placement, pacing) · `captions` (caption and headline words, looks, placement) ·
  `production-picture` (how a still was made: framing, faces, hands, product) · `production-clip` (how a clip moves,
  its prompt, its model) · `voice` (how a line is said, a word's sound) · `brief` (what is said, the words of a line,
  the order of the argument) · `teardown` (what was read off the swipe)
- `scope` — `this ad only` · `this format` · `this brand` · `every edit`. **Default to the narrowest scope the
  evidence supports.** One change is never `every edit` unless he said so
- `seen` — how many times a change pointing to this same rule is now on file (count `{learned}` too)
- `conflicts_with` — any rule already on file this contradicts. Do not resolve it; name it. The ruling is his

A rule is PROMOTED (bound into what the stage obeys) only when `seen` is 2 or more, or when he stated it as a rule
himself ("always", "never", "from now on", "every time"). Until then it is an observation.

## Answer

JSON only, no prose around it:

```
{"rows": [{"id": "...", "what_changed": "...", "his_words": "...", "rule": "...", "stage": "edit", "scope": "this format", "seen": 1, "conflicts_with": ""}],
 "promote": ["ids of rows that are now rules"],
 "observations": ["ids of rows kept as observations"]}
```
