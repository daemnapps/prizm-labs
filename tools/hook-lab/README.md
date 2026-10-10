# Hook Lab

The first 90 frames of a video, the opening hook, studied on its own. This is
the working folder for going deep on hooks: why people stop, why they keep
watching, and how to make five tested hooks out of one that already worked.

**The goal:** the first thing a viewer sees is the most important moment in the
whole customer journey, so this is a system built to optimise that one moment.
Everything after the hook only runs for the people the hook stopped.

**Open [`hook-lab.html`](hook-lab.html) in a browser.** It is one page with no
build step. The live copy is at
<https://claude.ai/artifact/XJGkack6J7GLCQdap7o8An>.

## What the page covers

| Section | What it shows |
|---|---|
| Three hooks, three curves | Retention shapes for a hook that overpromised, a first frame that stopped nobody, and a hook that matches its body |
| The funnel strip | The hook owns Stop and Open; the body owns Hold, Believe and Act |
| Anatomy | Frame, text card, spoken line and open loop across frames 1–90 |
| Seven mechanisms | Recognition, open loop, pattern interrupt, stakes, contradiction, payoff first, joke: why each works and how it fails |
| Format lock | Fixed words stay, blanks change, every fill comes from the language bank |
| Awareness rungs | What a hook may name at each level, unaware to most aware |
| Diagnostic | Hook rate, hold rate and CTR in, which part failed out |
| Teardown sheet | One blank card per swiped reel, plus a ship check |

## Where it comes from

The rules are the ones the machine already runs in stage 4b:
[`tools/video-teardown/prompts/stage-4-loop/4b-hook/`](../video-teardown/prompts/stage-4-loop/4b-hook/)
(v18 is the latest). This page draws them; the prompt is still the authority.

## Next

- Tear down the two swiped reels into the sheet:
  `instagram.com/reel/DRvoawJEYYC` and `instagram.com/reel/DdnPSy_R0xa`.
  They need the video files or a screen recording; the scraper could not
  reach them.
- Build a hook library: every swiped hook logged with its mechanism, fixed
  words, blanks, awareness rung and real hook and hold rates.
- Replace the diagnostic's starting thresholds with the account's own medians
  once there are 20 or more ads to compare.
