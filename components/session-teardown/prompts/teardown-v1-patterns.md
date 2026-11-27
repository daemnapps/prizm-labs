# Teardown — what the recordings show (v1)

You are reading recordings of real visitors on one page of a direct-response funnel. Each recording is a timeline:
seconds from the start, what they did (opened, tapped with the words on what they tapped, rage-tapped, scrolled
N% before leaving, reached checkout, bought), and how it ended.

The page: {page_id} — step {step}, kind {kind}, product {product}.
The page's address: {url}

There are two groups:
- LEFT: {n_left} visitors who opened this page and never reached checkout.
- CONVERTED: {n_converted} visitors who opened this page and reached checkout.

Count behaviour, do not guess motives. A pattern is something you can point at in the timelines: how far people
scrolled, what they tapped, where they stopped, what they tapped repeatedly, which page they went to instead,
how long they stayed. For every pattern give how many LEFT recordings show it and how many CONVERTED recordings
show it. A pattern worth reporting is common in LEFT and rare in CONVERTED. Report 3 to 6 patterns, the
strongest first. For each pattern name up to 2 moments (recording id + second) that show it best.

Use only what is in the timelines. If the recordings are too few or too thin to see a pattern, say so in "notes"
and report what little you can see.

Reply with JSON only, this shape:
{"patterns": [{"pattern": "<plain words, what they did>", "left": <count>, "converted": <count>,
  "moments": [{"recording_id": "<id>", "at_s": <second>, "note": "<what happens there>"}]}],
 "notes": "<anything a reader must know about the evidence>"}

## LEFT
{left_timelines}

## CONVERTED
{converted_timelines}
