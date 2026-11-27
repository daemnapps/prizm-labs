# Creator kit

**Keys this tool needs:** Gemini, Apify, ElevenLabs (needed); Higgsfield, Drive, OpenAI (helpful). See `kit.json`.

Everything a person who manages clippers and creators needs to run the creator line on their own computer, with
their own accounts: find formats that work, save swipes, write creator briefs, send them, bring footage back, cut
it, send it for approval.

**Start:** open this repo in Claude Code or Codex and say **set me up as a creator manager**. It opens the setup
page (keys typed there, never in chat), links the brand folder you were given from its own repo, and checks the
computer is ready.

| File | What it is |
|---|---|
| `kit.json` | the keys, the loop and the rules, in one place |
| `check.py` | is this computer ready: keys set or missing, brand folders, skills |
| `test_check.py` | tests |
| `../../.claude/skills/creator-kit/SKILL.md` | the front door (also at `.agents/skills/` for Codex) |

Neighbours: [setup page](../onboarding/), [video teardown](../video-teardown/), [brief hand-off](../image-edit/),
[video edit](../video-edit/), [Meta upload](../meta-upload/).
