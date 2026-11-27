---
name: mini-status
description: Check on your runs on the shared Mac mini — is it queued, running, done or failed, why it failed, where the results are, and how much Claude it used and on whose plan. Use when someone asks "status of my mini run", "is my run done", "did it work on the mini", "why did my mini run fail", "where are the results", "how much Claude did that use", "mini status", "/mini-status". Reads only; files nothing.
---

# mini-status — what happened to a run on the mini

> **Activates component:** `components/run-kit` — reads a mini run's status.


the developer, 2026-10-19: "check on the status of the run itself." The third of three `mini-`
skills (mini-list → mini-run → mini-status). Read-only.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/run-kit/mini_run.py` — `status` subcommand (LD-9 (mini run filer)).
- `platform/data/records/lab-runs/<person>/<label>.json` — the run's result record
  (credential, claude_calls, claude_usage — WM-140 (runs lane token), WM-161 (claude usage per run)).
- `platform/data/records/lab-runs/<person>/<label>/` — the run's text outputs, mirrored.

## Do this

1. `python3 components/run-kit/mini_run.py status <label>` (it fetches first). No label:
   it lists this person's last 10 requests and each one's state — ask which one, or take
   the newest.
2. If the state is `done` or `failed`, read the result record (pull first):
   `platform/data/records/lab-runs/<person>/<label>.json`. Report from it:
   - **Result** — `status`, `exit_code`, `started` → `finished` (say the duration).
   - **Why it failed** — the last meaningful lines of `stdout_tail` / `stderr_tail`. Quote
     the error line, not the whole tail; a run can exit 0 and still have held or skipped
     work — read the tail's summary line (e.g. "2 built, 0 held, 1 failed").
   - **Where the results are** — `out` is the folder on the mini; the text files are
     mirrored to `platform/data/records/lab-runs/<person>/<label>/` in git; media go to
     Drive at the same `runs/…` path.
   - **Claude use** — `credential`: `token:<person>` = billed to that person's own plan,
     `login` = the mini's sign-in (the developer's plan). `claude_calls` = calls made (0 = none;
     absent = not measured). `claude_usage` (token runs only) = exact input / output /
     cache tokens per model; `_calls_without_transcript` > 0 means some calls could not be
     measured.
   If it `failed` and the cause is not obvious from the tail, offer the `mini-debug`
   skill: it opens a thread to the developer's lead with the label, exit code and last error
   lines filled in (`status` prints the exact command on a failed run).
3. If it is still `queued` for more than ~5 minutes, or `running` far past its usual time,
   say so plainly and suggest the `slots` skill to see what the mini is busy with — never
   re-file to "unstick" it (a second copy just queues behind the first).

## Never

- Never print a token, a key or anything from `~/.claude-tokens` — the record holds
  names and numbers only, and so does your answer.
- Never edit or re-file anything — this skill only reads. Re-running is mini-run's job,
  after the failure is understood.
