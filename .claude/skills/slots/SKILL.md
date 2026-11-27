---
name: slots
description: Show every worker slot on the mini — what each one is running, since when, its last job and result, and the waiting queue in pick order. Use when someone asks "what are the slots doing", "is a slot free", "what's queued", "is my job running", "slot status", "/slots". Reads the pulled clone; no key needed.
---

# slots — every worker slot, from your clone

> **Not a component:** runs `platform/tools/slots.py` — reads the mini's worker slots; not a component.


the developer, 2026-10-01: "is there a way that the designer can easily check the status of all the slots from claude?" WM-131 (slots readout).

External dependencies (rules file: pointers outside this folder are listed here):
- `platform/tools/slots.py` — the read-out itself (read-only, writes nothing, no network unless a key is in the environment).

1. Pull first: `git fetch origin --quiet && git merge --ff-only origin/main` (the table is only as fresh as your last pull; if the pull is refused, say so and show the table marked "unpulled").
2. Run `python3 platform/tools/slots.py` (add `--since 6h` to narrow "last job"; `--json` for machines).
3. Show the table as printed: one row per slot (NOW, SINCE, LAST JOB, RESULT), then the waiting queue, oldest first, with each job's requester.
4. The ALIVE column needs `REVIEWER_KEY_TEAM` in the environment (heartbeats live on the dashboard, not in git). If it reads "needs the dashboard", say that once; never ask for the key in chat, never read a key from a file.
