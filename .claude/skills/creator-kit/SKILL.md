---
name: creator-kit
description: The front door for whoever runs the clippers and creators, on their own computer with their own accounts. Sets the computer up for the creator line, then runs it in plain sentences — find formats that work, save swipes, write creator briefs, send them, bring footage back, cut it, send it for approval. Use when someone says "set me up as a creator manager", "creator kit", "set up the creator line", "is my computer ready for creators", "run my creators", "make creator briefs", "what do I do next for my creators", or "creator kit check".
---

# Creator kit

For the person who manages clippers and creators. Everything runs on their own computer, with their own keys and
their own Higgsfield; nothing is billed to anyone else and nothing goes live from here. Talk in plain words and run
every command yourself; never ask them to run one, and never ask for a key in chat.

## Set up (once)

1. If `.env` is missing, follow "activate Prizm Lab" in `.claude/CLAUDE.md` steps 1–2 (it starts the setup page,
   `python3 components/onboarding/serve.py`). Give them the page's link.
2. On the page: **link the brand folder** they were given (step 1, "My brand folder already lives in its own
   repo"). It is a private repo shared with them; clone it next to this folder first, then link it. Never copy a
   brand folder into this repo.
3. On the page: the **needed keys** — Gemini, Apify, ElevenLabs — and Higgsfield if they make pictures or clips.
   The full list with why is in `components/creator-kit/kit.json`.
4. Run `python3 components/creator-kit/check.py` and tell them the result in one line. Fix any ✗ with them on
   the page, then check again.

## The loop

Each step is its own skill. Read that skill's `SKILL.md` and follow it; this page only says the order.

| Step | They say | Skill |
|---|---|---|
| Find what works for the avatar | "run a research round for &lt;avatar&gt; of &lt;brand&gt;" | research-round |
| Save the picks | "add these swipes for &lt;brand&gt;" | swipe-intake |
| Write the creator brief | "tear down this video for a creator, brand &lt;brand&gt;" | video-teardown (creator route) |
| A picture brief for a creator | "tear down this static for a creator to shoot" | image-teardown (--route creator) |
| Send it to the creator | "hand brief &lt;number&gt; to the creator" | brief-handoff |
| Bring the footage back | "check what came back for brief &lt;number&gt;" | brief-handoff |
| Cut it | "edit brief &lt;number&gt;" | video-edit |
| One change to a cut | "on brief &lt;number&gt;, move the hook to the start" | recut |
| Send it for approval | "send brief &lt;number&gt; to the approval page" | meta-upload |

When they ask "what do I do next", look at where each of their briefs stands (`python3 components/briefs/make.py
waiting --role video-editor`, and the brief register) and name the next step for each, one line each.

## Rules

- Their keys, their usage. Never use or ask for anyone else's.
- Nothing goes live. Filing to the approval page is as far as this goes; going live is the owner's click.
- The brand folder stays in its own repo, linked in. Never commit it, copy it or paste its contents anywhere else.
