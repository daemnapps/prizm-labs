# Teardown — what the recordings show, section by section (v2)

<!-- v2 (2026-11-14): the page under test arrives as SECTIONS (page-teardown's structure, as a page map with each
section's share of the page's depth), and every recording is read in the video teardown's frame-map shape — shots
(one page each) and moments (one thing done, with its second). Patterns now name the section ("never got past
§6 offer box"), not a bare scroll %. Everything in v1 stands. -->

You are reading recordings of real visitors on one page of a direct-response funnel. Each recording is a timeline:
seconds from the start, what they did (opened, tapped with the words on what they tapped, rage-tapped, left the page
after scrolling N%, reached checkout, bought), and how it ended. When a visitor left the page under test, the line
also names the deepest SECTION they reached ("· furthest §4 bulleted list").

The page: {page_id} — step {step}, kind {kind}, product {product}.
The page's address: {url}

The page, top to bottom, as sections (from the page's own teardown; each section's depth band is an estimate from
its length):
{page_map}

How far each group got — the deepest section reached on this page, counted in code from the recordings:
{reach}

There are two groups:
- LEFT: {n_left} visitors who opened this page and never reached checkout.
- CONVERTED: {n_converted} visitors who opened this page and reached checkout.

Count behaviour, do not guess motives. A pattern is something you can point at in the timelines: which section they
stopped in, what they tapped, where they stopped, what they tapped repeatedly, which page they went to instead, how
long they stayed. Name the section by its § label and what it is ("never got past §5 offer box"); use a scroll % only
when there is no page map. For every pattern give how many LEFT recordings show it and how many CONVERTED recordings
show it. A pattern worth reporting is common in LEFT and rare in CONVERTED. Report 3 to 6 patterns, the strongest
first. For each pattern name up to 2 moments (recording id + second) that show it best.

Use only what is in the timelines and the counts above. If the recordings are too few or too thin to see a pattern,
say so in "notes" and report what little you can see.

Reply with JSON only, this shape:
{"patterns": [{"pattern": "<plain words, what they did, naming the section>", "section": "<§ label or empty>",
  "left": <count>, "converted": <count>,
  "moments": [{"recording_id": "<id>", "at_s": <second>, "note": "<what happens there>"}]}],
 "notes": "<anything a reader must know about the evidence>"}

## LEFT
{left_timelines}

## CONVERTED
{converted_timelines}
