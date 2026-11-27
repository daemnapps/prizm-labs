---
name: mini-compare
description: Compare your machine against what a run on the shared Mac mini actually gets — code you changed but did not commit or push, commits you have not pulled, files and folders that exist only on your machine, paths into your own home or Drive, Python that breaks on the mini's 3.9.6, keys the mini does not hand out, packages it does not have. Use when someone asks "is the mini in sync with me", "compare my components to the mini", "will this run on the mini", "why does it work here but not on the mini", "what's different on the mini", "mini compare", "/mini-compare". Reads only; never reaches the mini.
---

# mini-compare — your machine vs what a mini run gets

> **Activates component:** `components/run-kit` — `mini_compare.py`, reads only.


the developer, 2026-10-19: "compare what is on the mini vs their own … he might be making changes to
his components that get out of sync with the mini. But he has no way to know it … also
check for things for example a folder that only exists in his machine." The fourth `mini-`
skill (mini-list · mini-run · mini-status · mini-compare). Read-only.

**The fact it rests on:** a mini run is a fresh checkout of GitHub `main` at the moment it
is picked up. So code and in-repo files compare EXACTLY from git, and nobody needs access to
the mini. Only packages, tools and models live outside git; those come from the list the
mini publishes (WM-162 (mini inventory)) — until it exists, those lines say "not checked".

External dependencies (rules file: pointers outside this folder are listed here):
- `compare.py` (this folder) — a shim; the check itself is `components/run-kit/mini_compare.py`
  (LD-41 (mini-compare false REDs)), stdlib, runs under /usr/bin/python3.
- `platform/workers/mini-worker/job_env.py` — the keys a mini lab run is handed (`JOB_ENV["lab-run"]`).
- `platform/data/mini-inventory/index.json` — the mini's installed packages / tools / models (WM-162).
- `team/people/*/identity.json` — who you are, from `git config user.email`.

## Do this

1. From the repo root, run (it fetches first; never pulls, never changes your files):

   ```
   /usr/bin/python3 .claude/skills/mini-compare/compare.py <component ...>          # will it run there
   /usr/bin/python3 .claude/skills/mini-compare/compare.py                          # every component, counts
   ```

   Every run checks EVERY file of the component (LD-42 (full check default); `--full` is
   accepted and ignored). REDs split two ways: **NEW** — in files you changed and have not
   pushed, shown line by line first; **ALREADY IN THE CODE** — a count, lines with `--detail`.
   No component named: one line per component, `new / already / amber`, worst first, in about
   a minute; `--all` adds the clean ones.
2. Report per component, worst first, in plain words — NEW REDs first, they are yours:
   - **RED — won't run the same on the mini**: Python 3.9.6 breaks (a syntax error, or an
     `X | Y` type hint without `from __future__ import annotations`), a path into this
     machine's home or Drive mount (the mini cannot see it — inputs belong in git or Shared
     Assets), a key the mini does not hand to lab runs, a package the mini does not have.
   - **AMBER — the mini runs different code than you tested**: edits not committed, new files
     git does not track, folders that exist only here (a `.venv`, models, local output — a mini
     run is a fresh checkout and has none of them), commits not pushed, commits on `main` you
     have not pulled (you are testing older code than the mini runs).
   - **?** — not checked yet (a package, until the mini publishes its list).
   - **NOTE** — other components it names that also differ here (inferred, not traced).
3. End with the fix for each RED/AMBER line, smallest first: commit + push; pull; move an
   input into Shared Assets; add the `__future__` import; ask the developer or the designer for a key.
   When everything is clean: "nothing found — a dry run on the mini (mini-run) is still the
   last proof; a path built at runtime from a setting is invisible to this check."

## Never

- Never commit, push, pull, stash or delete for the person — say what to run; they run it.
- Never claim "in sync" from a run that said NOT FETCHED.
- Never print a key or token value — the check reads key NAMES only.
