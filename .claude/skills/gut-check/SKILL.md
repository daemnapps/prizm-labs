---
name: gut-check
description: Adversarial review of an artifact by two fresh, blind bench seats. Use for expensive-to-reverse decisions — governance amendments, schema binds, position cards, anything entering the-org — or for an artifact the calling session authored itself, since self-review is structurally weak. Say "gut check this", "gut-check the amendment", "have the bench break this". Routine artifacts are covered by normal plan/lead cross-checking; a gut-check costs roughly 130k tokens across two frontier seats, so it is for the decisions worth that. Advisory only — it decides nothing and files nothing.
---

# Gut check

> **Standalone skill:** activates no component — two fresh blind reviewers read an artifact; touches no component.


Two independent bench seats try to break an artifact before it binds. They are
spawned **fresh and blind** — no transcript, no authoring reasoning — because
what they don't know is the whole value.

**Why this exists, in one line:** on 2026-08-26 two blind seats found three
blockers in a governance amendment that four exchanges of author-plus-lead
review had missed. Self-review and familiar-reviewer review both failed on the
same artifact; blindness is what worked.

## What it decides

Nothing. It returns memos into the calling session. **Agents gate, owners
bind** — the caller folds the findings, the owner rules. This skill files no
record, edits no registry, and sends nothing.

## Run it

**1. Take the artifact.** A file path or pasted text. If the artifact lives
inside a larger file (a plan file with many parts, a card deck with many
cards), **extract the part under review and pass it inline** — a reviewer sent
to read a whole file will review the wrong thing.

**2. Pick two seats.** `technical-advisor` always — it carries the gut-check
charter. Match the second to the artifact's centre of gravity:

| Artifact is about | Second seat |
|---|---|
| org design, roles, people, who-owns-what | `human-leverage-advisor` |
| spend, pricing, economics, build-vs-buy cost | `business-advisor` |
| an AI approach, model choice, agent design | `ai-advisor` |

The caller may override with an explicit lens list. When the artifact
genuinely spans two, pick the one whose objection would be *most expensive to
discover later*, and say in the summary which lens you did not run.

**3. Spawn both in ONE message so they run concurrently**, each with the
template below and nothing else.

**4. Consolidate.** Verdicts first, then issues ordered by severity across
both memos. Where the seats disagree, say so plainly and do not average them —
a split verdict is a finding.

## The blindness rail — the load-bearing line

Pass **only** the artifact text and repo pointers. Never the calling session's
transcript, never its reasoning, never "context that might help."

The urge to add context is the urge to defend the artifact. A reviewer who
knows why you did it reviews your reasoning; a reviewer who doesn't reviews
the thing. Only the second one is worth 130k tokens.

## The reviewer template — pass verbatim

> You are a fresh, independent reviewer. Your job is to BREAK this if it can
> be broken — flaws, contradictions with standing rulings, unpriced
> consequences, failure modes. You have deliberately NOT been given the
> authoring session's reasoning — your independence is the point. You may read
> the repo to verify claims against the standing record. Return a memo: VERDICT
> first (sound / sound-with-fixes / unsound), then each issue with severity
> (blocker / fix-before-bind / note), each traced to a file you actually
> checked, then your own kill-condition for the proposal. Flag every claim you
> could not verify. Raw memo, no pleasantries.

Then the artifact. Nothing after it.

## Rails

- **Advisory only.** No decisions, no records, no registry edits, no sends.
- **Reviewers read, never write** — the advisor agents' tool sets enforce it.
- **Brand-agnostic** (workspace rule 7): brand context enters only from
  `brands/<brand>/`, never from this skill.
- **Flagged-not-verified is a finding.** A memo's "could not verify" list is
  as useful as its blockers — surface it, never quietly drop it.

## Kill-condition

If gut-checks start returning empty verdicts on routine artifacts, the trigger
has eroded — tighten the description or retire the skill. Registered in
`the-org/org.md`.
