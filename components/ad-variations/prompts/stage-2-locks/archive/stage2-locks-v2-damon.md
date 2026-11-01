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

THE CLOSEST POSTS IN THE BRAND'S OWN CORPUS — computed: the posts that share
the most of what a viewer sees and hears with this ad, their views, and every
variable they differ on. A near-twin that differs on one or two variables is
the brand's own half-run test of those variables: if its views differ a lot,
those variables have been seen to move results.
{siblings}

THE BRAND'S RULES (position, story, likeness, compliance)
{brand_rules}

Call the PARTS, not only the elements. Where stage 1 split an element into
parts (who reacts, the sticker's words, the clip behind a picture-in-picture,
a named public figure), give each part its own row: the layout can be a lock
while the person in it is a lever.

Call it twice when the cuts differ. The brand's corpus is organic posts. A
paid cut plays muted by default, is cropped to 4:5, and has to carry an
offer; an element that is a lock for the organic cut can be a lever for the
paid cut (captions, the end frame, the ask, a subject outside the 4:5 zone).
Say which cut each call is for: `cut` = both, organic or paid.

How to call it:
- LOCK when the corpus shows the brand's top posts converge on this ad's value
  (tendency lock-leaning) AND no near-twin moved results by changing it, or
  when changing it would break what the replication spec marks load-bearing,
  or when a brand rule fixes it.
- LEVER when the top posts vary on it; when a near-twin differs on it and its
  views differ (quote the twin's rank and views); when this ad's value
  conflicts with the audience read or a brand rule; or when the paid cut
  needs it moved. A value the whole corpus shares is not evidence that it
  works — only that nothing else was tried; say so rather than calling it a
  lock on count alone.
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
    {"element": "hook_visual", "part": "who reacts | null", "cut": "both | organic | paid", "call": "LOCK | LEVER", "variables": ["V-hook.07"], "what_this_ad_does": "",
     "evidence": "V-hook.07 comment-reply: 17 posts, 41.3% of views, save rate 0.85% vs …",
     "needs_ruling": null, "impact_rank": null, "impact": "high | medium | low | null",
     "impact_basis": "ESTIMATE — …"}
  ],
  "lever_order": ["element keys, highest estimated impact first"],
  "damon_decides": ["a question only the owner can answer, with the fact that raises it"]
}
```
