---
name: mini-run
description: Run a component on the shared Mac mini for you — files the request under your own name (it bills your own Claude plan), with the arguments the component's door expects, then tells you how to follow it. Use when someone says "run this on the mini", "send it to the mini", "run image teardown for Brand B on the mini", "do a dry run on the mini", "file a mini run", "mini run", "/mini-run". Commits and pushes one request record; changes nothing else.
---

# mini-run — file one run on the mini, as you

> **Activates component:** `components/run-kit` — files a run request for the mini.


the developer, 2026-10-19: "Be able to run it with the right command." The second of three
`mini-` skills (mini-list → mini-run → mini-status).

External dependencies (rules file: pointers outside this folder are listed here):
- `components/run-kit/mini_run.py` — `list` and `file` subcommands (LD-9 (mini run filer)).
- `.claude/skills/mini-compare/compare.py` — the pre-filing drift check.
- `team/people/*/identity.json` — who you are, matched from `git config user.email`.
- `platform/data/records/workflow-requests/` — where the request record lands.

## Before filing — the four checks (each one has broken a real run)

1. **You are you.** `git config user.email` must be on your `team/people/<you>/identity.json`;
   mini_run.py refuses otherwise and names the email. The run bills the Claude plan of the
   person it is filed as — never file under someone else's name.
2. **Your code is on origin.** The mini runs what is on GitHub `main`, not your Mac. Run
   `/usr/bin/python3 .claude/skills/mini-compare/compare.py <component>` (mini-compare; it
   checks the whole component). `mini_run.py file` now checks on its own before it writes
   anything (LD-45 (mini-run refuses on RED)): it runs the component's dry run here under the
   trace (about 10 s for video-teardown) and REFUSES on a NEW RED (a file you changed) or on
   a file the dry run opened outside the checkout, its run folder and Shared Assets. Older
   REDs are shown, those on lines the dry run reached first — say them to the person; the
   filing goes on. A door with no dry run: only NEW REDs refuse. Any AMBER line
   (uncommitted, untracked, unpushed, unpulled, a folder only here) is shown and they choose —
   commit + push first, or run the mini's version knowingly.
3. **Your inputs are reachable.** Every file the run reads must be in git or on Shared
   Assets on Drive — never only on your Mac (video-edit failed 2026-10-18/19 on clips that
   lived only on one Mac).
4. **Nothing goes out.** Mini runs never switch a Meta ad live and never send a Klaviyo
   email (the developer's ruling, week of 2026-10-19). If the ask needs that, stop and say so.

## Do this

1. `git pull --no-rebase -q origin main`, then `python3 components/run-kit/mini_run.py list`
   and find the component (or use mini-list). Map the person's words to the door's
   arguments: each `--name <value>` is filed as `name=value`; a routed door takes
   `command=<route>`.
2. If this component has never run for this person, or the args are new, **offer a dry run
   first** (`--dry-run`; refused for a door that declares none).
3. **Show the exact command and get a yes before filing** — filing spends the person's
   plan. Then run it:

   ```
   python3 components/run-kit/mini_run.py file <component> --brand <brand> [--label <label>] [--dry-run] name=value ...
   ```

   **Always pass `label=<label>` too when the list shows "see <script>" for the door
   (no manifest): such a door may require `--label` and mini_run.py cannot see it — video-edit
   failed in 0 s on exactly that (2026-10-19, kojic-acid-doctor-20261019).**
   Labels: lowercase-with-dashes, unique (default `<component>-<YYYYMMDD-HHMM>`). It
   commits the one record and pushes; if the push is refused it prints the commands —
   run them.
4. Report: the label, the commit, and "the mini picks it up within a minute or two; I'm
   watching it and will say one line when it ends" (LD-57 (mini-run watch), the developer
   2026-10-20). A long run (an email month, a video) takes 20–60 minutes.
5. Watch it: right after filing, start this as a BACKGROUND command (run_in_background,
   one wake at its exit; not a Monitor, and never cut short with head or grep -m1):
   ```bash
   python3 components/run-kit/mini_run.py watch <label>
   ```
   It is silent while the run waits or runs and ends with ONE line: `PASSED … outputs at …`
   (exit 0), `FAILED … — <error line>` (exit 1; offer mini-status for the full reason, or
   mini-debug), or `stopped watching after 90 min …` (exit 3; offer to watch again). Say that
   line to the person when it arrives. A run held for review (an audit hold) currently
   ends as FAILED; mini-status shows why.

## Never

- Never hand-write a request record — mini_run.py writes it, so the fields are right.
- Never file as another person, never set `scheduled`, never edit grants, `brands/` or `.claude/`.
- Never re-file a failed run blindly — read why it failed first (mini-status).
