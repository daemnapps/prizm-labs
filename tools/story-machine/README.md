# story-machine

Writes narrated story videos — the format where a voice reads a story at about
double speed over satisfying footage, one word on screen at a time — in two
lanes:

- **organic**: fiction for a story channel. No product, no claims.
- **ad**: built only from real customer quotes a brand hands over; the product
  enters at the turn.

| Stage | Prompt | Makes |
|---|---|---|
| 1 Story Mine | `prompts/01-story-mine-v1-damon.md` | 6–10 seeds |
| 2 Write the Short | `prompts/02-write-short-v1-damon.md` | a 690–970-word narration (~2½ min) |
| 3 Full Story | `prompts/03-write-full-v1-damon.md` | the ~14-minute version (organic) |
| 4 Visual Plan | `prompts/04-visual-plan-v1-damon.md` | shot list: satisfying B-roll or AI-animated |
| 5 The Cut | `prompts/05-cut-v2-damon.md` | over-long trims and the 90 / 60 / 45 s paid cuts |

`run.py` fills a prompt's `{slots}`, calls the model, and checks length in
code. The model cannot count its own words, so stage 5 has it rank sentences
and the code fills the word budget — every cut lands in its band and is made
only of lines from the full script.

```
python3 run.py prompts/02-write-short-v1-damon.md slots.json out.md --words 690-970
```

Brand context (world, voice, receipts, product line) arrives in `slots.json`
at run time. Nothing here names a brand. The full teardown and research are in
`story-machine-damon.md`.
