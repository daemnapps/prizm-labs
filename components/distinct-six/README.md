# distinct-six

## How to use it → (team dashboard)

**One concept, written as N genuinely different ads.** Meta groups ads that "look or feel alike" into one creative, so six hooks on one ad are one ticket. Six versions that differ in awareness, format, face, setting and look are six. Built 2026-10-08 on the owner's word: "six unique versions of that same concept, same brief".

**Off to the side of the video chain** (the developer is working in it). It reads a finished chain run and touches nothing in the chain. It gets wired in as stage 4v after the developer's merge.

```bash
python3 components/distinct-six/run.py runs/video-teardown/<brand>/<run> --angle <angle-id> [--avatar <id>] [--n 6]
```

- **Reads:** the run's close-stage script, hooks, culture read and the **section map** from the doctrine stage (1c), plus the brand's settings, cast, formats, styles, core message and the running library (crowded and open cells).
- **Writes:** `runs/distinct-six/<brand>/<run>/` → `sent.md` (the prompt as sent), `versions.json`, `page.html` (colour bars by section, plus a grid of moves between every pair).
- **Sections:** the doctrine's own 15 (`components/elements/library/doctrine.section.json`). No second grouping.
- **Rule:** every pair is 3+ moves apart and none copies what's running (`creative-diversity/check.py`). Failures go back once for a rewrite.
- **Prompt:** `prompts/stage4v-distinct-v1-damon.md`. Claude runs on the owner's plan (`claude -p`). Meta is never called.

Page: The Distinct Six, (team page)
