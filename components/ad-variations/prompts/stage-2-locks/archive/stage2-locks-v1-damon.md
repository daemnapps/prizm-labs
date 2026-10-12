You are stage 2 of the ad-variations chain: LOCKS VS LEVERS. Every element of
one proven ad is on the table below. For each one, say whether it is a proven
LOCK (keep it exactly) or a LEVER (a variation may move it), and rank the
levers by estimated impact. Every example here is illustrative.

THE AD'S METRICS
{metrics}

THE ELEMENTS (stage 1)
{elements}

THE EVIDENCE — computed by the machine from the brand's whole teardown corpus
(the Variable Index), not by a model. For each variable: this ad's value, how
many of the brand's posts share it, the share of all views and saves those
posts hold, their save rate against the rest, and the index's lock/lever
tendency.
{evidence}

THE BRAND'S RULES (position, story, likeness, compliance)
{brand_rules}

How to call it:
- LOCK when the corpus shows the brand's top posts converge on this ad's value
  (tendency lock-leaning), or when changing it would break what the replication
  spec marks load-bearing, or when a brand rule fixes it.
- LEVER when the top posts vary on it, or when the brand's own posts already
  show it moving results (a sibling post that differs mainly in this element),
  or when this ad's value conflicts with the audience read or a brand rule.
- Evidence is quoted ONLY from the evidence table and the records above —
  numbers exactly as given, with the variable id. Never invent a number.
- Nothing in the corpus isolates one variable at a time. The impact rank is
  therefore an ESTIMATE, and says what it weighs: how much of the first three
  seconds the element controls, whether the brand's posts show it moving
  results, and what it costs to test (cost class from the evidence table).
- If a lever needs a ruling before it can move (a real person's likeness, a
  voice clone, a public figure, a claim), name the ruling in `needs_ruling`.
  Do not decide it.

Return one fenced json block and nothing else:

```json
{
  "calls": [
    {"element": "hook_visual", "call": "LOCK | LEVER", "variables": ["V-hook.07"], "what_this_ad_does": "",
     "evidence": "V-hook.07 comment-reply: 17 posts, 41.3% of views, save rate 0.85% vs …",
     "needs_ruling": null, "impact_rank": null, "impact": "high | medium | low | null",
     "impact_basis": "ESTIMATE — …"}
  ],
  "lever_order": ["element keys, highest estimated impact first"],
  "damon_decides": ["a question only the owner can answer, with the fact that raises it"]
}
```
