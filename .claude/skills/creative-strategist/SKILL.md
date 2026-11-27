---
name: creative-strategist
description: Find an ad idea from research, with no swipe — one sub-avatar in, what is true about him (every line with its receipt), the insight, scored ideas and one idea ready for statics, video or email. Use whenever someone says "research first", "creative strategy for <sub-avatar>", "find the insight", "what's true about <sub-avatar>", "ideas from research", "original concepts for <brand>", "no swipe", "run creative strategy on all the sub-avatars", "what research are we missing", "pick idea <n>", or "send this idea to statics / video".
---

# Creative strategist

> **Activates component:** `components/creative-strategist` — `machine/strategy.py` (evidence, think, check, forms, choose, ask, hand, show). The swipe route (`ask.py`) is the other way in and is unchanged.

External dependencies: `brands/<brand>/` (sub-avatar cards, language bank, position, objections, culture map; read only), `components/marketing-doctrine/` (awareness, sophistication, desire), `components/image-teardown/` + `components/image-writing/` (statics), `components/video-writing/` (`scratch.py`, video with no swipe), `components/research-gatherer/` (fills a gap; it spends, so the owner says yes first).

## Run it

1. `strategy.py evidence --brand <b> --avatar <a> --sub <sub> --product <p> --label <date>-<sub>`: free. Read the gaps it prints.
2. `strategy.py think <run>`: the truths, tensions, insight and ideas. One at a time across an avatar, so each sees what the others were given. Exit 1 means something is held; run it again, never edit the answer.
3. `strategy.py copy <run>`: headlines and a body from his own words and what has sold. The thinking's sentences are notes, never copy. Show the owner the copy first; the thinking, the facts, what is not cleared and what is missing sit behind it. **Choosing is the owner's.**
4. `strategy.py choose <run> --by <name> [--idea N]`, then for a static `strategy.py forms <run>` (three forms that fit; a swipe lends form only).
5. `strategy.py ask <run> --ask <label> --said "<his words>" --funnel "<line>" [--form NO]`, then `strategy.py hand <run> --ask <label> --to image|video` and run what it prints. A static opens its run on the form's own picture from the Drive.

## Never

- Never start from a swipe, a format or a holiday on this route.
- Never write or fix an observation, a receipt, an insight or a line by hand. A wrong one goes back through `think`.
- Never use what `not_cleared` names until the owner clears it.
- Never fill a gap with a guess. Say what is missing; a pull that costs money needs a yes and a cap.
- A sub-avatar with few of his own rows is said so next to the idea.

## Report

Per sub-avatar, one line each: the best headlines, how many facts hold, how many are his own words, what is missing. Plain words, no paths.
