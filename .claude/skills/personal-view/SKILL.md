---
name: personal-view
description: Mint your own personal copy of a dashboard view — "my own copy of the pm view", "personal view of performance", "split a view for me", "/personal-view <tool>", "how far has my personal view drifted" (--check). Runs in YOUR Claude Code session on your machine; commits the copy by path; optionally publishes a frozen artifact copy that wakes your session on comments. Never touches the shared template.
---

# /personal-view <tool> [--force] [--check] [--artifact]

> **Not a component:** a workflow build at `new-workflow-design/builds/personal-views/personal_view.py`.


External dependencies (greppable): `new-workflow-design/builds/personal-views/personal_view.py`
(the engine, PV-1 (personal-view skill)), `platform/views/viewers/_templates/<tool>.html`
(the shared template), `new-workflow-design/builds/personal-views/CLAUDE.md`
(the family rule and PV-3 (merge-back template)).

A PERSONAL VIEW is your own copy of a shared dashboard page:
`platform/views/viewers/<you>/<tool>.html`. The platform serves it to YOU at
the same URL everyone else uses (dashboard.the company.com/<tool> —
never a /v/<person>/<tool> link); everyone else keeps the shared page. You
edit it however you like — by hand, with this session, or by commenting on
a frozen artifact copy. Nothing you do to it touches the shared page. The
term is "personal view", never "twin".

## Steps

1. **Sanity.** You are in a clone of ai-workspace on `main`, up to date
   (`git fetch origin --quiet && git merge --ff-only origin/main`). `git config user.email` is listed in a
   team/people/<id>/identity.json (`python3 components/run-kit/run_kit/people.py whoami`
   prints the id; never the address's local part, LD-77 (one person resolver)); if it
   refuses, stop and say so — the engine will
   refuse with the same reason, and `--person` is for the lead only.
2. **Mint (or check).** Run exactly:
   ```
   python3 new-workflow-design/builds/personal-views/personal_view.py <tool> [--force] [--check]
   ```
   - default: creates `platform/views/viewers/<you>/<tool>.html` = the shared
     template plus ONE banner line ("your personal <tool> · see shared", with
     the template's sha stamped). A second run refuses; `--force` re-mints
     and DISCARDS your edits — say that before running it.
   - `--check`: reports drift (lines that differ, the sha you cut from vs
     today's template) and writes nothing. Exit 1 means drifted, not broken.
   Show the engine's output to the person verbatim.
3. **Commit by path** (default mint only — `--check` commits nothing):
   ```
   git add platform/views/viewers/<you>/<tool>.html
   git commit -m "view: <you>'s personal <tool>"
   git push origin main
   ```
   Only that one path is ever staged. If the pre-commit hook blocks, do not
   bypass it — report the message.
4. **`--artifact` (optional).** Load the `artifact-design` skill, then publish
   the personal file with the Artifact tool (favicon on first publish, a
   short `<title>` naming the tool, e.g. "the owner's performance view"). Tell
   the person: the artifact is a FROZEN copy for comments; their live page
   is the URL above. If comment auto-replies are available in this session,
   the publish arms them — comments on the artifact then wake this session,
   which edits the personal file and republishes.
5. **Say what comes next.** `/personal-view <tool> --check` any time; when
   something in the copy is worth sharing, it goes back through a card —
   the merge-back path in `new-workflow-design/builds/personal-views/CLAUDE.md`
   (PV-3 (merge-back template)). Never copy a personal file over a template.

## Never
- No write outside `platform/views/viewers/<you>/`. No template edit. No
  promotion (a personal file needs none). No `--person` for anyone but the
  lead. No `git add -A`.
