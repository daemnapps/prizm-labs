---
name: focus
description: Compact this session's context around ONE piece of work without parking or re-hatting — "focus this session on the review component", "/focus <the work to keep>", "compact but keep the RV work", "I want to shrink context before the trigger". Sweeps first (nothing you named as keep may be unfiled), assembles the /compact instruction from a fixed template, and hands you the exact line to paste — /compact is user-typed only, no skill can run it. Works on a hat seat (★ lead, ◆ plan) and in a normal session.
---

# /focus <the work to keep>

> **Standalone skill:** activates no component — compacts this session around one piece of work; touches no component.


External dependencies (greppable): `team/plans/dev-<owner>.md` (a hat's plan
file — the record the sweep checks), `team/id-tags.json` (the tag every id
carries), `.claude/hooks/post-compact.sh` (the re-grounding that runs after
the compaction, registered in `.claude/settings.json` under PostCompact).

Compaction summarises the transcript; whatever was only in the transcript and
not in the record is gone after it. This skill exists so a session can shrink
its context mid-work — before the auto trigger, on purpose — and lose nothing
that matters: the record is made complete FIRST, then the instruction says
what the summary keeps in full, what it collapses to a pointer, and what it
drops. Origin: 2026-09-08, ◆ PLAN · dev-the developer, mid-wave and wide; the developer ruled it
a team skill for hats and normal sessions alike (batch 58 of
`team/plans/dev-developer.md`).

**Product facts (Claude Code 2.1.263):** `/compact <instruction>` is strictly
user-typed — no skill, tool or hook can invoke it or alter its instruction.
PreCompact and PostCompact hooks can run commands. There is no preserve list
and no custom compaction prompt in settings; the instruction line IS the
preserve list.

## Act 1 — SWEEP (refuse to go on while something named as keep is unfiled)

Run and read, in this order:

```
git fetch origin --quiet && git status -sb | head -1
git status --short
```

Uncommitted or unpushed work is the compaction's blind spot: the summary may
describe it, the disk may not have it. Then, by session kind:

- **A hat seat** (title carries ★ or ◆): the park protocol's sweep half, and
  nothing less. Every ruling, fold and open item of the named work is in the
  plan file at HEAD, with its batch number; the open-on-the-owner list is
  current; custody is named (artifact URLs and watches, monitors, tmux
  sessions, anything only this session holds). Write the missing batch now,
  commit with the plan prefix, push. A hat that cannot complete its sweep
  PARKS instead — the park protocol is the fallback, not a shortcut around it.
- **A normal session**: list the uncommitted files and the unfinished threads
  you can see, and ASK the person which to commit or write down first. Do
  not compact over an answer you have not got.

Refusal is explicit: say what is unfiled and stop. The person decides whether
to file it or drop it; the skill never drops it silently.

## Act 2 — ASSEMBLE the instruction from the template

One paragraph, no line breaks (it is pasted after `/compact`). Three parts,
in this order, with these words:

1. **Keep in full:** identity and rules (hat name and id, the pen and its
   commit prefix, where folds go and to whom, the id-tag rule, `date -u`
   before every stamp, freshness before belief, any clone-sharing rule);
   the named work with EVERY id and its tag from `team/id-tags.json`, the
   rulings that bind it and their batch numbers, its status with a time
   stamp; what is open on the person; custody held (the URLs themselves —
   a summary cannot recover a URL it dropped).
2. **Collapse to one line with its batch number (or commit):** each settled
   thread, named. A collapsed thread survives as a pointer the successor can
   re-open by reading the batch; it does not survive as detail.
3. **Drop entirely:** memo text from bench seats, tool outputs, the contents
   of files already committed, SVG or HTML markup of published artifacts.

Everything the person named as keep goes in part 1; nothing they named goes
in parts 2 or 3. If part 1 alone runs past ~400 words, the named work is not
one piece of work — say so and ask them to narrow it, or to keep more than
one and accept the size.

## Act 3 — HAND the line, and say what to verify after

Print the exact line for the person to paste, in a fenced block:

```
/compact Keep in full: … Collapse to one line with its batch number: … Drop entirely: …
```

Then, in two sentences: after it runs, the first act is freshness
(`git fetch && git status -sb`) and a re-read of the named batches, which is
how the session verifies the summary against the record before trusting it.
The PostCompact hook prints the branch state, the last commits and the plan
file's last three batch headers automatically; the re-read of the batches is
the session's own act.

## Rules this skill obeys, and one it proposes

- Auto-compaction on a hat stays forbidden (the 2026-08-26 rule). This skill
  is the manual, swept path; it is not permission for the automatic one. A
  PostCompact hook firing with trigger `auto` on a hat means the enforcement
  setting (`autoCompactEnabled: false` in the hat seats' settings) was not
  applied — apply it; that setting is a launcher-side change and is proposed,
  not ruled.
- Proposed rule text for the rotation row of the position card, the developer's to
  rule: *a hat may compact in place after /focus's sweep; auto-compaction on
  a hat stays forbidden; a hat that fails its sweep parks instead.*
- Kill-condition: a focused-compacted session asserts something from a
  collapsed thread that the record contradicts, twice → the SWEEP step is
  tightened (it was incomplete); the compaction itself is never the thing
  dropped.

Reuses / could be reused by: reuses the park protocol's sweep half (CLI-12
(parked-seat sweep) shape) and the skills-folder rules; reusable by every hat
seat in every scope and by any teammate's normal session.
