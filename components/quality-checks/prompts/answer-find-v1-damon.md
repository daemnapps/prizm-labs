# Answer find — {brand} · {avatar} (v1)

Viewers from this avatar raised worries the brand has no written answer for.
Below them are real things real people said: customers, people who asked for a
refund, followers and commenters. Each line starts with its id.

For each worry, find the real lines that answer it: someone who had that exact
worry and got past it, someone whose result speaks to it, or someone whose
experience shows it isn't true. A line that only repeats the worry is not an
answer. Report it as "people really say this" instead.

Rules:
- Copy each line word for word, with its id. Never shorten, fix or combine lines.
- Only lines that really answer the worry. If nothing does, say so. That is a
  real finding: it means we don't have the proof yet.
- Prefer lines from {avatar} people. Lines from other people count too, but say
  which avatar each line comes from.
- Up to 4 answer lines per worry, strongest first.
- Then say in one plain sentence how the real lines answer it (no new claims,
  only what the lines say).

Return JSON only:
{"answers": [{"worry": "<the worry, short>",
  "answer_lines": [{"id": "<row id>", "quote": "<exact text>", "avatar": "<avatar>", "who": "<customer|churned|lead|commenter>"}],
  "echo_lines": [{"id": "<row id>", "quote": "<exact text>"}],
  "how_it_answers": "<one sentence, only from the lines>",
  "found": true}]}

--- THE WORRIES ---
{worries}

--- WHAT REAL PEOPLE SAID ---
{rows}
