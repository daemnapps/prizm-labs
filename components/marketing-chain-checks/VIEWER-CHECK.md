# The Viewer Check

Page: (private page) · source `viewer-check.html` · prompt `prompts/viewer-check-v1-damon.md`

**LIVE 2026-10-02 in the video and statics chains** (the owner: "slide this into the chains and lets ride it"). Code: `marketing_chain_checks/viewer.py`. Prompts: `viewer-check`, `viewer-card`, `viewer-cut` (all `-v1-damon.md`).

## What runs today
| Chain | Where | A fail goes back to |
|---|---|---|
| Video briefs | `tools/video-teardown/machine/run.py` `viewer_gate`, last stage-5 gate; also `_agent_stage.py done` | openings → 4b hooks · middle/giveaway → 4c placement · close → 4e close |
| Statics & carousels | `tools/image-teardown/tools/run.py` `viewer_step`, after the stage-6 copy gate | openings → 4 headlines · middle/giveaway → 5 variations · close → 6 brief |
| Landing pages | not yet — a page is reached from an ad, not seen in a feed; needs its own viewer | — |

- **Blocks.** A fail re-makes that step with the viewers' words; a fresh set reads it. 2 fails → HOLD for the owner. "Not for me" → HOLD at once. Passes with `--approve-structure V` (video) or the `viewer` gate in check.json (statics).
- **5 viewers.** With 3, an unchanged brief failed one round and passed the next. With 5, three rounds on Silent Chair all passed (watch-time 3, 5, 4 of 5; 5/5 stopped; 100% vs 20–33% for the real posts).
- **Fallback.** Gemini refuses <brand> profiles (PROHIBITED_CONTENT) → GPT-5.5 / GPT-5.4-mini answer. Each verdict lists the models used.
- **Sub-avatar.** The viewers are the sub-avatar the brief names. The feed falls back to the core feed if the sub has none.
- **One translation per brief.** The brief → what-a-viewer-sees step is cached per brief, so every round reads the same thing.
- Each round is filed at `<run>/viewer-check/r<N>/` (sent, answers, VERDICT.md) and in `<run>/qc-log/`. Off: `QC_VIEWER=0`. Tests: `python3 test_viewer.py`.

The last check after the writing stages. The ad is dropped into its avatar's real feed and scrolled by fresh viewers who aren't marketers. They're asked: do you stop, when do you leave, would you tap? Taken from Andrei Lunev's "Toilet Mike" (GreekOut II Mykonos 2026, Day 1).

## First test: Silent Chair (<brand> glow-up, 2 Oct 2026)

| | |
|---|---|
| Viewers who stopped on our ad | 3 / 3 |
| Stops on the real posts around it | 3 / 27 |
| Second all 3 knew it was an ad | 0:08, the device hold and room going quiet |
| Left before the end card | 2 / 3, at 0:12 |
| Would tap | 3 / 3 (to check comments, not to buy) |

Files: `trials/2026-10-02-silent-chair/` (what each viewer was sent, their answers, where our ad sat).

## From Toilet Mike
- The viewer isn't a marketer. Their only questions: does this stop your scroll, and what do you feel?
- The agent that wrote it never grades it.
- Check the script before any money goes on pictures or video.
- A "no" goes back to the step that broke, and a fresh viewer reads the rewrite. Usually 2 rounds or fewer.
- The same complaint over and over means the writer's prompt gets fixed.
- His scorecard rewarded "looks real" and two fake ads won #1 and #2. We don't score realism.
- the owner sets the taste. Live results check the viewer every week.

## How one check runs
1. Viewer card: first person, plain, taken from the avatar profile.
2. Feed: 9 real posts from that avatar's feed, shuffled, with ours at a random spot and marked sponsored.
3. 3 fresh viewers, each seeing only the card and the feed.
4. Code scores against the feed. The viewer never knows which post is ours.
5. Send it back or let it through. After 2 rounds it goes to the owner.

## Scorecard (code)
| Check | Pass when |
|---|---|
| Stop | 2 of 3 stop |
| Beats the feed | Our stop rate is above the real posts' stop rate in the same scroll |
| Stays to the offer | 2 of 3 still watching when the offer shows |
| Not an ad before the stop | Nobody clocks it as an ad before stopping |
| Would act | 2 of 3 would tap or text a friend |

Silent Chair: passes everything except "stays to the offer" (1 of 3).

## Where a "no" goes
| What the viewers did | Goes back to |
|---|---|
| Didn't stop, or left in the first 2 seconds | Openings (hooks) |
| Stopped, then left before the offer | Middle (placement / expansion) |
| Clocked as an ad, left right after | The moment they named (placement, or spice if it was the words) |
| Stayed, wouldn't tap | Close |
| "Not for me" / "didn't get it" | Audience pick |
| Same complaint on 3 briefs in a row | The writing prompt itself |

## Where it sits
- Video: after the brief (stage 5), before the final brief and elements.
- Statics / carousels: after the brief (stage 6), before the draft picture.
- Landing pages: after the page words (stage 6), before layout.

## Gaps the test found
1. Feed posts have a caption only, with no second-by-second, so our ad was described in more detail than the posts around it.
2. The feeds hold organic posts only. Paid swipes are kept separately.
3. In-session briefs skipped the reviewer — FIXED: the viewer check runs on both paths.

## Decided (2026-10-02)
A fail blocks: back to writing automatically, the owner after 2 failed rounds; "not for me" goes straight to the owner.

## Worth making? — the last word before credits are spent (2026-10-02)
the owner: *"If it's not ready for us to make, then we're not going to even do it."*
- **Predicted numbers** from the 5 viewers' own seconds: hook rate against the real feed, average watch, reach-the-price, would-act, and second-by-second retention. They are a guess until the loop check measures them against Meta.
- **The stamp.** `viewer-check/STAMP.json` is tied to the brief's json block. `viewer.worth_making()` answers from the stamp for free, or checks a never-checked brief first (text only).
- **Gates.** video-production `start` refuses without a pass, as the 4th gate after swipe match, manifest and the owner's read. Statics `gpt_drafts.py` skips briefs the viewers passed by. `--approve-structure V` writes the stamp.
- **Silent Chair, live.** Worth making: hook 100% vs feed 36%, average watch 20s of 25s, 60% reach the price, 100% would act.
- **The page** now opens with a playable walk-through: a brief walks the chain, 5 phones scroll the real feed, and the numbers land. Silent Chair is real; "a weak ad" and "fails twice" are labelled examples.

## Version 2: belief and more (2 Oct 2026, the owner: "we need belief, and so on")
New questions for every viewer who stopped: believe it would work for you, and what made you doubt it · looked fake, staged or AI-made · felt like someone selling at you, and which line · for someone like you · save, share, comment or nothing, and the comment word for word. Two of the five viewers scroll with the sound off, and every viewer is asked "did you get it?". "Looks real" is never scored.

**New pass checks:**
- Most of those who stopped believe it.
- No more than 1 viewer says fake.
- No more than 1 viewer says pitch.
- Most of the sound-off viewers got it.

**Where a fail goes:**
- Fake → where the shot is directed.
- Pitch → the spice step that writes the lines.
- Sound off → the on-screen words.
- Not believed → the step that writes the mechanism and proof.
- "Not for me" → straight to the owner.

**Silent Chair on v2: FAILED.**
- Belief: 0 of 5. All five said "not sure".
- Pitch: 5 of 5. The refund card.
- Stop 5/5, watched to the offer 5/5, nothing fake, sound-off 2/2, 80% would save.
- The refund line is the website's wording, so changing it is the owner's call.
- Run filed at `trials/2026-10-02-silent-chair-v2/`.
