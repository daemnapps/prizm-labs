---
name: triage
description: Open, refresh or explain a triage list in Claude, no shared link needed. Use when someone says "/triage operations", "show me the operations triage list", "refresh the components triage", "what's on my triage list", "explain action 2 on the operations list", "why is this signal P0", "how does triage work", or wants to note a finding for their theme's two-week evaluation.
---

# /triage <theme> [explain <n | action id | item id>]

> **Activates component:** `components/triage` — opens or refreshes a triage list.


External dependencies (greppable):
- `components/triage/tools/file_record.py` (files one act to the decision log; reads `platform/data/kinds/triage.json`);
- `components/triage/` (README.md, CLAUDE.md, themes/<theme>.json, approach-two-themes.html, triage-atlas-page.html);
- `new-workflow-design/builds/atlas/tools/metrics_insights.py` (operations detectors) and `tools/triage_page.py` (the page renderer, Python 3.9-clean);
- `new-workflow-design/builds/atlas/triage/queue/model-components-*.json` (the newest components model).
- `new-workflow-design/builds/atlas/tools/triage_dryrun.py`, `triage_rederive.py`, `triage_fill.py` and `triage_rulings.py` (the components pipeline);
- `components/triage/rulings.json` (rulings the list must show as ruled; seeded with K2 (brands write wall) and K3 (the email lead triage reach));
- `components/CLAUDE.md` Residents (the PARKED mark, K1 (parked status word)).

The tools move into `components/triage/` with the refactor (open issue triage #11); update these paths then.

Themes today: `operations` (the designer) and `components` (the email lead; the theme file is `themes/atlas.json`). Anything else is refused, with this list.

## Act 1: fresh, then build the list

1. `git pull --no-rebase` (never reset or rebase in a shared clone). Say if it fails.
2. Stamp: `date -u +%Y%m%dT%H%MZ`. The run folder is `runs/triage/<theme>/<stamp>/`.
3. Build:
   - **operations**: `python3 new-workflow-design/builds/atlas/tools/metrics_insights.py --out runs/triage/operations/<stamp>/model.json`. This reads the dashboards' data on the plane, which the mini refreshes daily. No credential is needed.
   - **components**: five steps, each a script, in this order (R = `runs/triage/components/<stamp>`, T = `new-workflow-design/builds/atlas/tools`):
     1. dry run: `python3 T/triage_dryrun.py R/dryrun.json` (every open issue on the component pages, re-checked at HEAD);
     2. re-derive: `python3 T/triage_rederive.py <newest model> R/dryrun.json --out R/model.json`. The newest model is the newest `runs/triage/components/*/model.json`, else the newest `new-workflow-design/builds/atlas/triage/queue/model-components-*.json`; say which. Items, actions and briefs carry over by issue id; gone ids are listed; PARKED components are set aside; new ids join the shared action for their theme, else `L-<component>`;
     3. fill: `python3 T/triage_fill.py R/model.json` (eight-part summaries from the sidecars);
        then **write the In short paragraphs and any owed new-issue briefs** yourself, in this session — no model call, no API key (the developer, 2026-10-08: "In short in-session, no key", "briefs in-session too"): for each action, 3–5 plain sentences into `action["in_short"]` — the common thread across ALL its issues (never the lead issue's text, never stitched), why it matters, who decides what, what is left — matching `new-workflow-design/builds/atlas/triage/in-short-style.md`, from `action["in_short_input"]` when the model carries it, else from the action's issues, decides and can_do; and for each NEW issue id that has only the dry run's line, its eight-part brief from its flow. Ids carry their tags. Anything left unwritten renders as OWED with a count;
     4. rulings: `python3 T/triage_rulings.py R/model.json`. A question already ruled shows as the ruling. If it prints FAILED, stop and say so: nothing was written, and a real question would have been lost;
     5. render, step 4 below.
     Report the rederive line (items, actions, new, gone, parked) and the rulings lines (asks remaining per ruling, actions relabelled "Ruled, ready to work"). Asks remaining above 0 means a ruling's wording has drifted: list the places, and add a pattern to `components/triage/rulings.json` (engine owner's file) before the list is published.
4. Render: `python3 new-workflow-design/builds/atlas/tools/triage_page.py runs/triage/<theme>/<stamp>/model.json runs/triage/<theme>/<stamp>/page.html`.
   - Before publishing, check two things on the rendered page: every action carries its eight-part summary (if any does not, say OWED with the count and the action ids, and run triage_fill on the model before rendering again); and nothing already ruled is drawn as an open question (a proposal or a decision option card whose question has a decide record or a rulings.json match is left off the page). Ruled history belongs in the decision log, not on the list (the developer, 2026-10-08).
5. Open it: `open runs/triage/<theme>/<stamp>/page.html` on a Mac; otherwise give the path. Then, in a few lines:
   - items, actions, and the P0 to P3 counts;
   - the data cutoffs (operations), and any data-health item, which holds that brand's other signals;
   - the top three actions: headline, who decides, who can do it.
   - the shared pages, from the theme file's `pages`: the published list (`pages.queue`) and the approach page (`pages.approach`, https://claude.ai/artifact/4BsAyTeRYP7Z1UWBgcpx6s). Those links work for anyone the developer has shared them with; the local page is always today's.

## Act 2: explain, from the data and not the page

Read `runs/triage/<theme>/<stamp>/model.json` (or the newest run) and the theme file. For "explain action 2", "why is X P0" or "what should I do about Y", answer from:
- the action's `summary` and its items' `fields`: the eight parts;
- `decides`, `can_do` and `impacted`;
- the theme file's `grouping` and `priority`, for why it was grouped and ranked that way.

Cite item ids. Each action's `ask_claude` is the do-prompt; offer it, and run it only when the person asks. "How does triage work" opens `components/triage/approach-two-themes.html`, summarises `components/triage/README.md`, and gives the published approach page: https://claude.ai/artifact/4BsAyTeRYP7Z1UWBgcpx6s.

## Act 3: findings, only when asked

When the person says "note that" or "that's wrong", add one line to `components/triage/themes/<theme>-FEEDBACK.md`, creating it with a header if missing:
`- <item or action id> · what's wrong · change wanted · theme|engine`
Use `theme` if the change is to the theme file (theirs to make), and `engine` if every theme would feel it (the developer's). Commit only the FEEDBACK file, with prefix `note:`, and only when they say so.

## Act 4: record an act in the decision log

Every act on an item is one record, filed with `python3 components/triage/tools/file_record.py <act> --item <id> --who <person> …`. Run it with `--dry-run` first and show the person.

**A change in someone else's component (Option 3, ruled 2026-10-02).** All four limits must hold, or stop and draft instead:
1. the issue's summary names the fix, and a test proves it (add the test if none exists);
2. no test check is weakened or removed;
3. it changes no live pipeline (a run a person or the mini depends on today). If it would, it's a `draft` for the owner to land;
4. it is recorded.

The steps: make the fix and its test, then commit them. Then file the record:

`file_record.py change --item <component>#<n> --who <triage owner> --theme components --commit <that sha> --test <test id> --areas path:components/<component> --why "<one line>"`

Commit the record. Then mark the issue resolved with the commit as evidence (SCHEMA §5a). Tell the owner in one line, giving the record's path.

**An undo (the owner).** `git revert <commit>`, commit, then:

`file_record.py undo --item <id> --who <owner> --undoes <change record file name> --why "<one line>"`

Commit it. The issue reopens (SCHEMA §5a): clear its `resolved` and `resolved_by` by hand until a reader does it. the email lead's Claude reads the undo and does not retry.

**"What has triage changed in my components?"** List `platform/data/records/triage/*.json` whose `verdict.act` is `change` and whose `areas` name the person's components, newest first. For each give the item, the why, the commit, the test, and the one-line undo (`git revert <commit>`). Note any `undo` that already reverses one.

Other acts: `close --evidence path:line@sha`, `answer --words`, `forward --forwarded-to`, `draft`, `sign`, `decide --ruling`. A refusal names what's missing; fix that, never work around it.

**A ruling that settles an item or an action.** File it with `decide`: `file_record.py decide --item <action id or component#n> --who <person who ruled> --ruling "<decision-log pointer>" --words "<the ruling, one line>"`. The rulings step (Act 1, step 4) reads every `decide` record: the named action's whole question, or the named issue's Decider, then shows as the ruling, and an action with nothing left to decide reads "Ruled, ready to work". A ruling that answers the same question across many actions (K2 (brands write wall), K3 (the email lead triage reach)) goes into `components/triage/rulings.json` instead, with the clause patterns that find the question; that file is the engine owner's.

## Rules

- Read-only on every source: no warehouse, no sends, no edits to the dashboards' data.
- Never commit a run folder unless asked. Runs are re-creatable, and a components page is about 3 MB.
- Every id carries its tag from `team/id-tags.json`. Stamps come from `date -u`, never estimated.
- Refuse a theme with no file in `components/triage/themes/`. Name the two that exist.

Reuses the triage renderer and the operations detectors; could be reused by any later theme that brings a theme file and a reader.
