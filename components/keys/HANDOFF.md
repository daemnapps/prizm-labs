# components/keys — handoff to the ★ LEAD

From ◆ PLAN · dev-developer, 2026-09-29, read from `a170788df`. the developer asked for
this folder to be created, with the three plans inside it. PLAN may commit
notes and pages but not a CLAUDE.md, so the items below are yours to file.
Whether they wait for the developer's direct word is your call, under the
relayed-word rule.

## 1. `components/keys/CLAUDE.md` (draft)

```
# components/keys — the names of every key, and the one way to load them

Owners (components/CLAUDE.md rule 6): engine — Operator B (loader, checks);
definitions — the ops lead (template, register; approves every change:
draft → approved → deprecated). Account owner: the developer.
Status: PROPOSED 2026-09-29 (the developer asked for the folder); nothing built yet.
Context: CONTEXT.md. Plans for review: plans/1–3 (open in a browser).

Contract (rule 2):
  - key(NAME) / load(): environment → managed file → personal file;
    warns on override; the mini never loads a personal file.
  - template: every variable name, grouped personal · common · mini only.
  - register: name · vendor · holder · kind · scope · rotated · due.
  - checks: file vs template (names only) · no key in a command line ·
    every template name hidden from the worker's jobs.
  - results: names-only check records on the plane.

Walls: this folder and its outputs never hold a key value. The per-job
grants stay in platform/workers/mini-worker/job_env.py. Delivery of files
is out of scope until D1 is ruled.
Kill: <~5 tools on the loader a month after phase 1 → fold into the worker;
a value ever lands here → rotate it and fix the check that missed it.
```

## 2. The first card

"The one loader" is phase 1 of plan 3:
- **Scope:** the loader, the template seeded from
  `platform/workers/mini-worker/env.template`, and the file-vs-template
  check.
- **Readers to switch first:**
  - `components/audio-teardown/keys.py`
  - `tools/video-teardown/machine/keys.py`
  - the path readers `hf.py`, `mytasks.py`, `drive_ids.py` and
    `check_live.sh`
  
  This is the R4 (keys by path) fix.
- **Keep `env.template`'s path working** (a pointer or a phased move),
  because `/system-ready` and `test_env_template.py` read it there.
- **Card id:** your prefix to mint.

## 3. Decision-log lines, when the developer confirms to you directly

D2 (two files per machine), D3 (personal keys for paid AI services; brand
systems per brand) and D4 (the ops lead and Operator B admins, the developer owner, two-factor
on all three) were answered by the developer on 2026-09-29, typed to PLAN.

When filed, they supersede:
- 2026-08-24, "the mini holds the only key copy"
- I-101 (secrets stack)'s "no manager on the mini"
- R1's "Keychain later"

D1 (the secure delivery method) is open.

## 4. Atlas nodes, in `manual-nodes.json` (JSON, yours)

- **Components:** `component:keys`
- **Integrations:** "Personal key files"
- **Runtime:** "Team laptops"
- **Views:** "Key health" (proposed)
- **People resources:** "Key SOP", the column's first entry

Plan 2 shows the intended placement.

## 5. Related, already in flight

- **WM-108 (no argv credential):** merged. The six-script follow-on gates the
  database password rotation.
- **`SLACK_USER_TOKEN_DEVELOPER`:** CLOSED by WM-109 (person tokens held),
  5384c65657: a prefix holdback in `job_env.py` keeps person tokens out of
  every job (keys#7, 2026-10-07).

Reuses / could be reused by: see `CONTEXT.md`.

## 6. 2026-10-09 — keys Track A and Claude seats (◆ PLAN [fab344], read from 2a378e7fa8)

- Track A (loader, readers, template, report-only checks) is carded as SI-192 (keys loader) to SI-196 (key checks report-only), with three guards; SI-193 (video-teardown keys reader) was reverted the same day, and SI-192b (loader skips key file) fixes it. The plan page `plans/3-implementation-plan.html` (v13+) carries the split.
- D6, each person's Claude on the mini, has its own test folder: `plans/2026-10-09-claude-seats-test/` (HANDOFF, CHECKLIST, RESULTS). The stream session running that test starts from its HANDOFF.md.
