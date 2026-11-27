---
name: dev-issues
description: File a session's pending dev list into the Dev-queue's Issue queue, or move an issue along — each item sorted into an issue, a follow-up or a context note, with the person's own words and the session it came from. Use when someone says "file these as issues", "put this list in the issue queue", "raise this as a dev issue", "file what we found in this session", "this is a follow-up for the email lead", "move this issue to discussing", "card this issue", "won't do this one because …", "tick that follow-up done", "what's in the issue queue", "/dev-issues".
---

# dev-issues — the Dev-queue's way in

> **Activates component:** `components/page-features` — `dev_issues.py`, PF-18c (issue queue).

An issue is a PM task tagged `dev`. The Dev-queue page (PF-18 (dev-queue view)) shows them in its
Issue queue column: Raised → Discussing → Carded or Won't do. This skill turns what someone said in a
session into those records, then commits them. It never edits a card, a deck or a brand file.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/dev_issues.py` — the only writer; its docstring is the item format.
- `components/run-kit/run_kit/people.py` — who is filing, from the git email.
- `platform/data/records/tasks/` — where the records land.

## File a list

1. **Who:** `python3 components/run-kit/run_kit/people.py whoami` → `--by`. If it refuses, ask.
2. **Sort, never copy.** One item per thing. A line that says "this is broken, and the email lead should check X"
   is TWO items: an issue, and a follow-up whose `parent` is that issue's `ref` (the 29 Oct list split
   item 11 into 11a and 11b). Kinds:
   - `issue` — something wrong or missing that may become a card. Proposed fixes go in `fixes`.
   - `follow-up` — a small task with a named `person`; it is ticked done, never carded.
   - `context` — a fact worth keeping on an issue or a card; never parentless.
3. **Keep the words.** `quote` is the person's own words, verbatim; `session` is the source session id;
   `said_by` when the quote is not from the filer. `parent`: a card id WITHOUT its tag (the command refuses
   the tagged form), an issue's `ref` in the same list, a dev task id, or none.
4. **Hold what was held.** An item the person said "not yet" to is NOT filed. Show the sorted list and
   ask before filing anything they did not ask to file.
5. **Dry run first**, from the repo root, the list on stdin:
   `python3 components/page-features/dev_issues.py file - --by <id> --dry-run`
   Exit 2 = refused, every problem named, nothing written: fix the list and rerun.
6. **File** (same command without `--dry-run`), then commit exactly the paths it printed, in ONE command
   (the mini's worker commits the shared index — never stage and wait):
   `git add -- <paths> && git commit -m "issues: <n> filed from session <id> by <person>" -- <paths>`
   then `git push origin main` (rejected → `git pull --no-rebase` then push). Show the commit output;
   a hook refusal means nothing landed.
7. Report each filed item as one line: kind, title, parent, task id.

## Move one

| They say | Run (add `--dry-run` to preview) |
|---|---|
| "move <task> to discussing [with the email lead]" | `dev_issues.py discussing <task> --by <id> [--with the email lead]` |
| "card <task> as <card id>" | `dev_issues.py card <task> <card id> --by <id>` |
| "won't do <task> because …" | `dev_issues.py wont <task> --reason "…" --by <id>` |
| "tick <task> done" (follow-ups only) | `dev_issues.py done <task> --by <id>` |
| "<task> was fixed by <commit>" / "close it as fixed" (an issue fixed with no card) | `dev_issues.py fixed <task> <sha> --by <id> [--note <why>]` — the sha must be on main; the issue leaves the queue, PF-18l (fixed move) |
| "add a fix to <task>: …" | `dev_issues.py fix <task> "…" --by <id>` |
| "what's in the issue queue" | `dev_issues.py show` (writes nothing) |

All under `python3 components/page-features/`; commit what a move prints the same way as step 6.
`card` links the task only — making the card itself is the lead's act, through a fold.
