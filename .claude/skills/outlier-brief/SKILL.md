---
name: outlier-brief
description: Run the outlier brief — the second door. the owner's own idea (a few sentences, no swipe) plus a brand goes in; one rounded-out, format-free concept brief comes out and STOPS for his approval; only after approval are the formats picked and the hand-offs written. Use whenever someone says "I have an idea: …", "brief this idea for <brand>", "outlier brief", "turn this into a concept brief", "approve the brief", "send it back", "pick the formats for that brief", or names an idea and a brand with no swipe behind it.
---

# Outlier brief

> **Not a component:** runs lab code in `lab/the owner/outlier-brief` — runs lab code.


External dependencies: `lab/the owner/outlier-brief/` (the machine; `SPEC.md` is the spec and is the owner's), `brands/<brand>/` (position, story, offer bank, objection bank, avatars, angles — read at run time), `components/marketing-doctrine` (awareness, sophistication, frameworks — bound as slices), `components/elements` (the format, style and framework lists), `components/language-layer` (the customer's own words).

**Two commands — the second refuses without his approval on file.**

```
# 1 · the idea → the concept brief, then STOP (awaiting approval)
python3 lab/the owner/outlier-brief/tools/run.py <idea.md or "-"> --brand <brand> [--avatar <a>] [--sub <s>] [--angle <id>] [--offer <key>] [--answers "…"]
python3 lab/the owner/outlier-brief/tools/run.py <idea> --brand <brand> --dry-run

# 2 · his verdict → the formats → the hand-offs
python3 lab/the owner/outlier-brief/tools/approve.py <label> --brand <brand> [--note "…"] [--media video,image,copy,page,email] [--route ai|creator|founder] [--product <p>]
python3 lab/the owner/outlier-brief/tools/approve.py <label> --brand <brand> --send-back --note "…"
python3 lab/the owner/outlier-brief/tools/approve.py <label> --brand <brand> --formats video:<format id>[+<style id>]     # his own pick, no model call
```

- The idea is a `.md`/`.txt` file of a few sentences, or `-` piped in.
- `--brand` is required; there is no default. `--avatar`, `--sub`, `--angle`,
  `--offer` are looked up in the brand's own files; an unknown one is refused
  with the real ones named.
- **`--dry-run` on either command spends nothing** — resolves and fills every
  prompt, shows the model per step and where it would file; the approval dry
  run records no approval.
- After a send-back: `run.py … --rerun-from idea3` rewrites the brief and is
  told the note. To edit the brief by hand before approving, edit
  `idea3--concept-brief.md` in the run; the approval re-runs the checks on it.

## What it does

Round the idea out (what it really is, who it is for, what it promises,
questions for him) → the awareness read from the doctrine → the concept
brief, format-free → check it against the brand's files → **STOP**. Then,
after approval: pick the formats only from the element library → write a
hand-off file per medium with the approved brief word for word. **Nothing is
started** — each hand-off prints the command its chain is started with.

## The rules the command enforces — do not work around any of them

1. **The review stop is a person, not a check.** `run.py` always ends there.
   The later steps refuse without an approval on file, and refuse if the
   brief changed after it was approved.
2. **Looked up, never coined.** Avatar, sub-avatar, angle, offer against the
   brand; awareness, sophistication, every framework, format and style
   against the doctrine and the element library. A row still saying
   `[TO DEFINE` may be named as a candidate, flagged "named, not defined
   yet", and is not handed off.
3. **Three gates:** inputs · elements (after the awareness read, the brief and
   the format pick) · copy (the brief in its nine parts; no UNFILLED note;
   every price one the offer bank sells; no claim the brand's files do not
   carry). A held brief cannot be approved.
4. **The doctrine is bound, never re-typed.** A test fails if a prompt spells
   an awareness level.
5. **Nothing is written into `brands/`.**

## What comes back

`runs/outlier-brief/<brand>/<label>/` — `idea.md`, the four step outputs,
`deliverable/concept-brief.md`, `run.json` (with `review.state`: awaiting ·
approved · sent back), `check.json`, every prompt as sent; after approval,
`formats.json` and `deliverable/handoff--<medium>.md` / `handoff--video.json`.
The brief and its approval state live in the run folder above.

Report after step 1: the brief itself (he reads it), the round-out's
questions, and "awaiting your approval". After step 2: the formats picked and
which chains have a hand-off waiting.

Reply with the result and the folder it landed in (repo path or Drive folder name).
