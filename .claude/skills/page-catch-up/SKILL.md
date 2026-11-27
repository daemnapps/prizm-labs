---
name: page-catch-up
description: Bring your own live page up to today's team template — a new draft from the current template, your logged changes replayed onto it one at a time, or a side-by-side compare when your page was edited by hand. Use when someone says "catch up my emails page", "catch up my <family> page", "my page is behind the team version", "bring my page up to date", "update my page to the new template", "/page-catch-up". Never touches the live page; the person makes the new draft live themselves.
---

# page-catch-up — your page on today's template

> **Activates component:** `components/page-features` — the `catchup` and `catchup-mark` verbs, PF-19b (catch up).

A page that is behind its team template says so on its status strip, the home page and
`/page-list` (PF-19 (behind notice)); its direct buttons may fall back to copying a request
until it catches up. This skill makes the catch-up draft and carries the person's own
changes onto it. The live page is never written.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — `catchup`, `catchup-mark` (code in `draft.py`).
- `components/page-features/features.py change` — the `/page-change` route each replayed change goes through.
- `components/page-features/kit/server.py` — `status` (is the page server on); `team/people/<you>/identity.json` — `page_server_port`.

## Do this

1. Who: `python3 components/run-kit/run_kit/people.py whoami`. Only the person's own page;
   another person's page → refuse ("ask them to run it").
2. Run, from the repo root, and print the output as it is:
   `python3 components/page-features/features.py catchup <family>`
   It makes `drafts/<family>--catchup-<date>.html` from today's template and names ONE case:
   - **no changes** — "nothing to replay: the new draft IS your page on today's template".
     Give the draft's address (step 4) and say: "check it, then say 'make this draft live'" (page-live).
   - **changes to replay** — it lists each logged change in order (step number, the words,
     who, when) and writes a plan beside the draft; changes whose number or anchor left the
     template are already marked skipped. Go to step 3.
   - **hand edits** — "your page was changed by hand"; it lists the lines that differ and
     never guesses a merge. Open both side by side with `/page-compare` (the live page and the
     new draft), walk the person through each difference in plain words, and for each one they
     want kept, make it on the DRAFT through `/page-change` in their words. Then step 4.
3. **Replay** (changes case): for each step in order, apply the change's own words to the
   draft through `/page-change` (the same route, so it is logged on the new draft), then mark it:
   `python3 components/page-features/features.py catchup-mark <draft> <step> applied|skipped|needs-a-person [--why "<reason>"]`
   - `applied` — the change landed and the draft still works;
   - `skipped` — the template already does it, or its target is gone (say which);
   - `needs-a-person` — it cannot be applied without a choice; ask the person, never guess.
   `catchup <family> --status` prints the plan at any point.
4. Hand over the draft's page-server ADDRESS, never the file (a page that reads /data cannot
   load from a file): port from `team/people/<you>/identity.json`; if
   `platform/views/viewers/_templates/<family>.sources.json` exists, check
   `python3 components/page-features/kit/server.py status` — "on" → give
   `http://localhost:<port>/p/<you>/drafts/<family>--catchup-<date>.html`; off → "turn your
   page server on first ('turn my page server on'), then open …".
5. The person checks it and says "make this draft live" (page-live). That go-live records
   today's template and button table, so the behind line clears and direct buttons return.

## Never

- Never write the live page, its logs, or another person's draft.
- Never guess a merge of hand edits; each kept difference is the person's choice.
- Never mark a change `applied` without opening the draft after it.
