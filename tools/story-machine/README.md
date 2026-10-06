# story-machine

Writes narrated story videos — the format where a voice reads a story at about
double speed over satisfying footage, one word on screen at a time — in two
lanes:

- **organic**: fiction for a story channel. No product, no claims.
- **ad**: built only from real customer quotes a brand hands over; the product
  enters at the turn.

| Stage | Prompt / code | Makes |
|---|---|---|
| Pack | `pack.py` | the language pack: never-used customer sentences from the brand's language layer, spent phrases removed |
| 0 Discovery | `prompts/00-discovery-v1-damon.md` | territories: a real-life drama, where her skin collides with it, the exact words to build with and why |
| 1 Story Mine | `prompts/01-story-mine-v3-damon.md` | seeds (lanes: organic · ad · story-ad) |
| 2 Write the Story | `prompts/02-write-story-v3-damon.md` | the narration, as long as the story needs, with a words-used and claim check |
| 3 Full Story | `prompts/03-write-full-v2-damon.md` | the long version with more rounds (organic) |
| 4 Visual Plan | `prompts/04-visual-plan-v1-damon.md` | shot list: satisfying B-roll or AI-animated |
| 5 The Cut | `prompts/05-cut-v2-damon.md` | a shorter version, only when one is asked for |
| Render | `render.py` | voice → sped to the format's pace → one-word captions → post card → B-roll rotated by category → end card → mp4 |

No length limits: a story runs as long as it needs. `run.py` fills a
prompt's `{slots}` and calls the model. A shorter cut happens only when asked
for: the model ranks sentences and code fills the requested time, so the cut
is made only of lines from the full script.

```
python3 pack.py --root <workspace> --brand <brand> --avatar <avatar> --out pack.md --spent spent.txt
python3 run.py prompts/00-discovery-v1-damon.md slots.json territories.md
python3 run.py prompts/02-write-story-v3-damon.md slots.json story.md
python3 render.py job.json
python3 run.py --cut story.md cut.md 60 --product NAME
```

The story-ad lane is fiction told in the customer's real words; every video
carries "Dramatized story" on screen and claims only what the product line
allows.

Brand context (world, voice, receipts, product line) arrives in `slots.json`
at run time. Nothing here names a brand. The full teardown and research are in
`story-machine-damon.md`.
