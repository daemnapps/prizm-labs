# story-machine

Writes narrated story videos — the format where a voice reads a story at about
double speed over satisfying footage, one word on screen at a time — in two
lanes:

- **organic**: fiction for a story channel. No product, no claims.
- **ad**: built only from real customer quotes a brand hands over; the product
  enters at the turn.

| Stage | Prompt | Makes |
|---|---|---|
| 1 Story Mine | `prompts/01-story-mine-v2-damon.md` | 6–10 seeds |
| 2 Write the Story | `prompts/02-write-story-v2-damon.md` | the narration, as long as the story needs |
| 3 Full Story | `prompts/03-write-full-v2-damon.md` | the long version with more rounds (organic) |
| 4 Visual Plan | `prompts/04-visual-plan-v1-damon.md` | shot list: satisfying B-roll or AI-animated |
| 5 The Cut | `prompts/05-cut-v2-damon.md` | a shorter version, only when one is asked for |

No length limits: a story runs as long as it needs. `run.py` fills a
prompt's `{slots}` and calls the model. A shorter cut happens only when asked
for: the model ranks sentences and code fills the requested time, so the cut
is made only of lines from the full script.

```
python3 run.py prompts/02-write-story-v2-damon.md slots.json out.md
python3 run.py --cut out.md cut.md 60 --product NAME
```

Brand context (world, voice, receipts, product line) arrives in `slots.json`
at run time. Nothing here names a brand. The full teardown and research are in
`story-machine-damon.md`.
