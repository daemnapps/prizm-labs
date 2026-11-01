# The Viewer Check

**Live 2026-10-02 in the video and statics chains** (the owner: *"slide this into the
chains and lets ride it"*). Code: `marketing_chain_checks/viewer.py`. Prompts:
`viewer-check` (v2), `viewer-card`, `viewer-cut`, and for the chain
`objection-match`, `answer-find`, `belief-drivers`, `viewer-fix`, `hidden-boxes`.
The highest `-vN-damon.md` of each is the one that runs.

The last check after the writing stages. The ad is dropped into its avatar's real
feed and scrolled by fresh viewers who aren't marketers. They're asked: do you
stop, when do you leave, would you tap? Taken from Andrei Lunev's "Toilet Mike"
(GreekOut II Mykonos 2026, Day 1).

## Where it runs
| Chain | Where | A fail goes back to |
|---|---|---|
| Video briefs | video-teardown, the last stage-5 gate | openings → hooks · middle/giveaway → placement · close → close |
| Statics & carousels | image-teardown, after the stage-6 copy gate | openings → headlines · middle/giveaway → variations · close → brief |
| Landing pages | not yet — a page is reached from an ad, not seen in a feed | — |

- **Blocks.** A fail re-makes that step with the viewers' words; a fresh set reads it. 2 fails → hold for a person. "Not for me" → hold at once.
- **5 viewers.** With 3, an unchanged brief failed one round and passed the next. With 5 it held steady.
- **Claude by default** (`QC_VIEWER_ENGINE=claude`). Headless `claude -p` first; when that isn't signed in, each question is written as a numbered `*.prompt.md` in `<run>/hand/` (or `VIEWER_HAND_DIR`) and the run waits for the `*.answer.md` beside it, so the Claude session running the brief answers it — one fresh helper per prompt, so no viewer ever sees another viewer, the brief or the bank. `QC_VIEWER_ENGINE=gemini` runs Gemini, then OpenAI when Gemini refuses a profile.
- **Sub-avatar.** The viewers are the sub-avatar the brief names. The feed falls back to the core feed if the sub has none.
- **One translation per brief.** The brief → what-a-viewer-sees step is cached per brief, so every round reads the same thing.
- Each round is filed at `<run>/viewer-check/r<N>/` (what each viewer was sent, their answers, VERDICT.md, REPORT.html) and in `<run>/qc-log/`. Off: `QC_VIEWER=0`.

## From Toilet Mike
- The viewer isn't a marketer. Their only questions: does this stop your scroll, and what do you feel?
- The agent that wrote it never grades it.
- Check the script before any money goes on pictures or video.
- A "no" goes back to the step that broke, and a fresh viewer reads the rewrite.
- The same complaint over and over means the writer's prompt gets fixed.
- His scorecard rewarded "looks real" and two fake ads won #1 and #2. We don't score realism.

## How one check runs
1. **Viewer card** — first person, plain, from the avatar profile (cached per profile version).
2. **Cut** — the brief turned into only what a viewer sees and hears, second by second.
3. **Feed** — 9 real posts from that avatar's feed, shuffled, with ours at a random spot, marked sponsored.
4. **Scroll** — 5 fresh viewers, 2 of them with the sound off, each seeing only the card and the feed.
5. **Score** — code, against the real posts in the same scroll. The viewer never knows which post is ours.
6. **Belief** — the ad is read against the brand's belief index: the reasons real customers gave for buying. It passes when it gives at least 2 of the top reasons, and one of them is proof (real results or reviews).
7. **New to Meta** — when a creative-diversity checker is installed, the brief's moves are compared with what is running and what is already written; too close fails.
8. **Route** — a fail goes back to the step that broke, carrying the viewers' words.

## Scorecard (code, never the viewer)
| Check | Pass when |
|---|---|
| Stop | most viewers stop |
| Beats the feed | our stop rate is above the real posts' in the same scroll |
| Stays to the offer | most still watching when the offer shows (videos only) |
| Not an ad before the stop | nobody clocks it as an ad before stopping |
| Would act | most would tap or text a friend |
| Not fake | at most 1 says it looked fake, staged or AI-made |
| Not a pitch | at most 1 says it felt like selling before the offer (the offer itself is allowed to sell) |
| Works muted | most of the sound-off viewers got it |
| Belief | the ad gives the reasons real buyers bought (the viewers' own "believe" is shown, not scored) |
| New to Meta | far enough from running ads and written briefs (when installed) |

## Where a "no" goes
| What the viewers did | Goes back to |
|---|---|
| Didn't stop, or left in the first 2 seconds | the openings |
| Stopped, then left before the offer | the middle |
| Clocked it as an ad at the same moment, then left | that moment (the giveaway) |
| Said it looked fake or staged | the shot as directed |
| Said it felt like a pitch | the lines that sound like selling |
| Sound-off viewers didn't get it | the on-screen words |
| Doesn't give why real buyers bought | the proof |
| Too close to what's running | what makes it new: who, awareness, format, face, place, look |
| Stayed, wouldn't tap | the close |
| "Not for me" / "didn't get it" | who it's for — a person's call |

## Worth making? — the last word before credits are spent
the owner: *"If it's not ready for us to make, then we're not going to even do it."*
- **Predicted numbers** from the viewers' own seconds: hook rate against the real feed, average watch, reach-the-price, would-act, save/share/comment, and second-by-second retention. A guess until measured against live results, and always labelled so.
- **The stamp.** `viewer-check/STAMP.json` is tied to the brief's json block. `viewer.worth_making()` answers from the stamp for free, or checks a never-checked brief first (text only). Production refuses to spend on a brief without a pass; `viewer.approve()` records a person's override.

## What the avatar feed is
`<VIEWER_FEEDS>/<brand>--<avatar>/items.json`: real organic posts from accounts
that avatar follows — `{author, caption, sift: {keep, what}}`, where `what` is a
plain description of the post. Posts with `sift.keep` are preferred.
