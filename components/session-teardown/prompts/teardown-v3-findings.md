# Teardown — what the recordings show, sorted into fixes and big swings (v3)

<!-- v3 (2026-11-14, the owner: "how users are actually navigating our page experience … reducing friction at certain
elements, rewriting certain words to reduce confusion, possibly improving the positioning of the offer itself …
buttons are too small or too large … then it's when I'm going into my big swings … all the other
micro-optimizations … that's what the team can work on"): every finding is now sorted into a FIX (one element, the
team ships it) or a SWING (the offer, its positioning, the page's order or angle — the owner's call, tested 50/50).
The page arrives with what it was BUILT to do (its build record) and friction already counted in code. Money is
counted in code after this step, from your counts. Everything in v2 stands. -->

You are reading recordings of real visitors on one page of a direct-response funnel. Each recording is a timeline:
seconds from the start, what they did (opened, tapped with the words on what they tapped, rage-tapped, tapped where
nothing happened, left the page after scrolling N%, reached checkout, bought), and how it ended. When a visitor left
the page under test, the line also names the deepest SECTION they reached ("· furthest §4 items").

The page: {page_id} — step {step}, kind {kind}, product {product}.
The page's address: {url}

What the page was built to do:
{plan}

The page, top to bottom, as sections — each with the job it was written to do (depth bands are estimates from
section length):
{page_map}

How far each group got — the deepest section reached on this page, counted in code:
{reach}

Friction, counted in code — elements that fought back (rage taps, taps where nothing happened, the same element
tapped 3+ times):
{friction}

There are two groups:
- LEFT: {n_left} visitors who opened this page and never reached checkout.
- CONVERTED: {n_converted} visitors who opened this page and reached checkout.

Count behaviour, do not guess motives. A finding is something you can point at in the timelines or the counts: the
section they stopped in, what they tapped, what fought back, what they tapped instead of the button, where a section
failed its job. For every finding give how many LEFT recordings show it and how many CONVERTED recordings show it. A
finding worth reporting is common in LEFT and rare in CONVERTED. Name the section by its § label.

Sort every finding:
- "fix" — one element, fixable without changing what the page says it offers or how it argues: a tap target that
  does nothing or should do something, a button too small, too large or out of sight, words that confuse (people tap
  them, re-read them, or go looking for an answer the line should give), something broken or slow, spacing that hides
  the next step. Say the exact change in "fix" — which element, what it becomes. fix_kind: friction (taps that fight
  back), words, size, broken, layout.
- "swing" — changing it changes the deal or the argument: the offer, its price or positioning, the order of the page,
  the angle, what the page leads with, a section that fails its job for most who reach it. Do not write the change;
  the next step does, from the swings you name.

Report 4 to 10 findings, the strongest first. For each, up to 2 moments (recording id + second) that show it best.
Use only what is in the timelines and the counts. If the evidence is thin, say so in "notes".

Reply with JSON only, this shape:
{"findings": [{"finding": "<plain words, what they did, naming the section>", "section": "<§ label or empty>",
  "kind": "fix" | "swing", "fix_kind": "friction" | "words" | "size" | "broken" | "layout" | "",
  "fix": "<for a fix: the exact change; empty for a swing>", "left": <count>, "converted": <count>,
  "moments": [{"recording_id": "<id>", "at_s": <second>, "note": "<what happens there>"}]}],
 "notes": "<anything a reader must know about the evidence>"}

## LEFT
{left_timelines}

## CONVERTED
{converted_timelines}
