# components/keys — the names of every key, and the one way to load them

Owners (components/CLAUDE.md rule 6), CONFIRMED by the developer 2026-10-07 (triage action 3 (definition lines and
registry rows); decision log): engine — Operator B (loader, checks);
definitions — the ops lead (template, register; approves every change:
draft → approved → deprecated). Account owner: the developer.
Status: PROPOSED 2026-09-29 (the developer asked for the folder; filed by the lead from ◆ PLAN's draft in
HANDOFF.md §1). A resident once the owners were confirmed — its row is in components/CLAUDE.md.
Context: CONTEXT.md. Plans for review: plans/1–3 (open in a browser).

Contract (rule 2):
  - key(NAME) / load(): environment → managed file → personal file;
    warns on override; the mini never loads a personal file.
  - template: every variable name, grouped personal · common · mini only.
  - register: name · vendor · holder · kind · scope · rotated · due.
  - checks (D5, ruled 2026-09-30): personal setups are NOT checked. Keys are
    checked and migrated when work enters the system path — /system-fit,
    /system-ready, /system-review: file vs template (names only) · no key in
    a command line · every template name hidden from the worker's jobs.
    Always on, whatever the path: the walls · the mini runs on its managed
    file only · old shared keys stop working on announced dates.
  - results: names-only check records on the plane. **The plane it emits: none
    yet** — nothing here emits (only `pg_argv.py` is built), and
    `platform/data/kinds/` holds no kind for these records.
  - **Records (O12 (records adapter)):** none: no runs by design, for now — the names-only checks will file under runs/keys/ with a records adapter carded WITH the checks, not separately (the developer, 2026-10-07, triage page 7).

Built so far: `pg_argv.py` ONLY (WM-108b (other argv sites), 2026-09-29, on the developer's "go 108b") — stdlib,
no credential read, no I/O: splits a Postgres URL into a password-free URL for psql's argv plus
`PGPASSWORD` for the child's env. Every psql caller in the repo imports it; the "no key in a command
line" check starts here. Nothing else above is built.

Walls: this folder and its outputs never hold a key value. The per-job
grants stay in platform/workers/mini-worker/job_env.py. Delivery of files
is out of scope until D1 is ruled.
Kill: <~5 tools on the loader a month after phase 1 → fold into the worker;
a value ever lands here → rotate it and fix the check that missed it.
