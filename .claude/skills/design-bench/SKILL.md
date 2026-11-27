---
name: design-bench
description: Put two or more models on the SAME design brief and read their mocks blind, side by side — "design test: brief <path>, constraints <path>, arms kimi-k3, fable, astra", "bench these arms on this brief", "which model designs this better", "/design-bench". Resolves the sentence to a run folder, prepares every arm identically, collects the replies and writes a local compare.html where the arms are unlabelled. Refuses by name rather than guessing. It does not judge, does not pick a winner, and publishes nothing.
---

# /design-bench — one brief, N models, read blind

> **Not a component:** a workflow build at `new-workflow-design/builds/design-bench/bench.py`.


External dependencies (greppable): `new-workflow-design/builds/design-bench/bench.py`
(DB-1 (bench runner) and DB-2 (compare page) — `prepare`, `collect`, `compare`),
`new-workflow-design/builds/design-bench/task-cards.md` (the deck this serves),
`components/models/models.json` (the arm registry — THIS SKILL checks it, see
act 1), `platform/data/records/workflow-requests/` (where an OpenRouter request
record is queued — VERIFIED by running `prepare` 2026-09-18; the build's
`INFER_RECORDS_REL` names `infer-runs/`, which is where the ANSWER lands,
not the ask), `team/id-tags.json` (every card id in prose carries its tag).

**LEAD-EXECUTED, and it can never be otherwise.** This file lives under
`.claude/`, and makers are path-banned from there — so a maker can build the
bench but never this entry point. DB-3 (bench skill) says so on its own card.

Why this exists: `bench.py` is three commands with a person-shaped gap in the
middle — the OpenRouter arms need a record committed and pushed, and the
claude/codex arms need commands run in a seat. Somebody has to hold the order,
and holding it by memory is how one arm silently gets a different brief from the
others. That would not produce a wrong answer; it would produce a confident one,
which is worse.

## What it is not

| It does NOT | Because |
|---|---|
| judge, score, or name a winner | the page is for a PERSON to read blind; a bench that also judges is the thing it was built to replace |
| publish `compare.html` as an artifact | STRUCK by the developer 2026-09-16: "db2 shoudl be local HTML first to demo, skip the dashboard ui for now". On request, later — not built |
| mint a review round | same ruling, same status: one line, on request, later |
| call a model itself | every call goes through a route that already exists; this skill writes files and reports paths |

## The sentence

```
design test: brief <path>, constraints <path>, arms <id>, <id>, <id>
```

`arms` is two or more. An arm rides one of three routes — `openrouter`,
`claude`, `codex` — and the route is the arm's, not the run's, so one run can
mix them. An arm on `claude` or `codex` needs NO registry row; an arm on
`openrouter` needs one, which is act 1.

## Act 1 — RESOLVE, and refuse by name before writing anything

Refusals are named and early, because everything after this costs money or a
person's attention. Refuse, say which of these it was, and stop:

1. **An arm id that is not in `components/models/models.json`** — for
   `openrouter` arms only. `bench.py` does NOT check this and will happily
   prepare a run that the infer action then refuses downstream, after the
   person has committed a record. Check it HERE, name the id, and list the ids
   that are there. A `draft` row is FINE: the bench sets `allow_draft` on its
   own request records deliberately, so an arm may be benched before it is
   approved for general use — say the row is draft rather than blocking on it.
2. **A route outside `("openrouter", "claude", "codex")`** — `bench.py` refuses
   this too, with the known routes named; do not duplicate its message, let it
   speak.
3. **A run folder outside this build.** Runs live under
   `new-workflow-design/builds/design-bench/runs/<run>/` and nowhere else.
4. **A brief or constraints path that does not exist.** Read them before
   building the run, not after.

Then build the run folder: `brief.md`, `constraints.md`, optional `refs/`, and
`spec.json` with `max_tokens` and the arms in the order the person said them.
**Panel order on the page is NOT this order** — DB-2 (compare page) derives it
from `sha256(run + NUL + arm id)` so a reader of `spec.json` cannot map the
labels. Do not try to be helpful by reordering anything here.

## Act 2 — PREPARE

```
python3 new-workflow-design/builds/design-bench/bench.py prepare <run>
```

It writes one prompt per arm from the SAME brief, plus an OpenRouter request
record per `openrouter` arm, and prints what remains for a person. Read its
output back to the person as the two kinds of thing it is:

- **`openrouter <arm>: copy <record> to <queue target>, then commit and push it`**
  — THE PERSON'S ACT. Committing and pushing a request record is what spends
  money, and this skill never does it for them. There is also a retry record,
  to be used ON FAILURE ONLY; say that, or a helpful reader queues both and
  pays twice.
- **`<route> <arm>: <command>`** — a seat runs it, ON THE PERSON'S WORD. Ask
  before running; do not batch them silently.

**Every arm gets a byte-identical brief.** `prepare` records a
`source_sha256` over spec, brief, constraints and refs. If the brief is edited
after `prepare`, the run is no longer a fair test — start a NEW run name rather
than re-preparing, which `collect` also enforces by refusing when the prepared
arms no longer match `spec.json`.

## Act 3 — COLLECT, then COMPARE

```
python3 new-workflow-design/builds/design-bench/bench.py collect <run>
python3 new-workflow-design/builds/design-bench/bench.py compare <run>
```

`collect` reads replies and writes `out/<arm>.html` and `results.json`.
`compare` writes two files and reports both:

- **`runs/<run>/compare.html`** — ONE self-contained file, every mock embedded
  by `srcdoc`, no external byte. Give the person the local path. It opens by
  double-click; it does not need a server and does not need this skill.
- **`runs/<run>/key.json`** — label → arm. **Do not open it, do not read it
  aloud, and do not summarise it, until the person has looked at the page.**
  The blinding is the whole method; a skill that narrates the key has removed
  the reason the page exists.

Each arm lands in exactly one of three states, and say all three plainly —
a bench that shows two arms out of three while sounding complete is lying:

| State | Means |
|---|---|
| embedded | self-contained mock, on the page |
| FAILED FORMAT | the mock reached outside itself (a CDN, a font, a remote image) — listed, not embedded. It failed the brief; this is a RESULT, not an error to work around |
| no output | that arm's reply errored — named on the page, never dropped |

## Act 4 — REPORT

Say, in this order: the run folder, the local path to `compare.html`, the count
per state, and that the key is on disk and unread. Nothing else. Do not offer an
opinion on the mocks — you have seen the arm ids and the person has not.

## Rules this skill obeys

- The person commits and pushes anything that spends money. Always.
- A run folder is never reused after its brief changes; a new name is free.
- No file is written outside
  `new-workflow-design/builds/design-bench/runs/<run>/` except the OpenRouter
  request records, which go where `prepare` says.
- Kill, from the build's own card: after two runs the judges only ever prefer
  one arm against Claude → the bench collapses to "variation from another
  model" and this skill shrinks to exactly that.
