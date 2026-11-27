# <tool-name> — <what it is, in six words>

**<tool-name>** — takes **<what goes in>**, makes **<what comes out>**. Does not
**<what it never does>**. Triggered by `<the command>`.

**Owner:** <who>. **Group:** teardowns | briefs | research | production | quality | shared.

## Steps
Declared once in `machine/run.py` `STEPS`; the page and the runner read that list.

## The four questions
- **Engine + owner:** `machine/`, <who>
- **Definitions + curator:** `prompts/` (one file per step, `-vN-`, highest wins), <who>
- **The plane it emits:** `runs/<tool-name>/<brand>/<label>/` — every prompt as sent, every output, `run.json`, `check.json`
- **Manifest per entry:** `run.json`

## Gates
inputs · elements · copy · media · delivery — which of the five this tool runs, and what each checks here.
