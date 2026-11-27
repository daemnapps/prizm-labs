# Hypothesis — the big swings, one test each (v3)

<!-- v3 (2026-11-14): up to THREE big swings, each its own hypothesis for its own 50/50 test, ranked by the money
counted in code; the owner picks one. Small fixes do not come here — they go to the team's fix list. Everything in
v2 stands for each swing. -->

You write the big swings for a 50/50 page test, from counted evidence. Each test runs the page as it is (the
control) against one new version (the variant), decided by how many visitors reach checkout; orders must not drop.
The owner reads up to three and picks one, so each must be a real alternative, not a variation of another.

The page: {page_id} — step {step}, kind {kind}, product {product}, address {url}
Control today: version {control_version}, offer {control_offer}.

What the page was built to do:
{plan}

The page, top to bottom, as sections (depth bands are estimates from section length):
{page_map}

The leak (last {days} days): {visitors} visitors, {reached_next} reached checkout ({reach_rate}),
revenue per visitor {revenue_per_visitor}.

The big-swing findings, with what each is worth (dollars a month at stake, counted in code; an upper bound):
{swings}

Every finding, for context ({n_left} who left, {n_converted} who reached checkout):
{patterns}

Rules, for each swing:
- One change, big enough to move checkout by 20% or more; small changes cannot be read at this traffic.
- Say what the variant changes in plain words a page builder can build from. Name the section by its § label and
  what it is, and what it becomes or where it moves. Do not write copy for the whole page. Do not invent facts the
  page does not have (ratings, counts, quotes); say "the page's own reviews" instead.
- type is "design" unless the swing is the price or the offer itself; a design test keeps the offer
  ({control_offer}); an offer test changes only the offer and names the new one in variant_offer.
- The hypothesis sentence: "Change X → more reach checkout, because Y (seen in N of {n_left})." One sentence,
  35 words at most.
- The change is ONE move. At most three edits, every one serving that move.
- Up to 3 moments that show the problem best, for the approval card.
- "from": the numbers of the findings it answers (1 = the first finding listed above).

Write 1 to 3 swings, the most money first. Fewer is fine when the findings hold fewer real alternatives.

Reply with JSON only:
{"swings": [{"type": "design" | "offer", "hypothesis": "...", "change": "...", "variant_offer": "...",
  "clips": [{"recording_id": "...", "at_s": <second>, "note": "..."}], "from": [<finding numbers>]}]}
