---
name: page-draft
description: Make a new draft of a page — from your own live page or from the family's template — saved under your drafts with an empty change log, committed and shared. Use when someone says "make a draft of my live run-detail", "make a draft of the outlier-demo template", "start a new draft of the emails page", "copy my live page to a draft", "I want a draft to try something", "page draft", "/page-draft <page>". Never overwrites a draft; never copies another person's live page.
---

# page-draft — a new draft, from your live page or the template

> **Activates component:** `components/page-features` — makes a page draft.


A thin wrapper over the page-features `draft` verb. A draft is where every change
happens; a live page is never edited directly.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — the `draft` verb (`draft.py` beside it).
- `new-workflow-design/builds/personal-views/personal_view.py` — PV-1 (personal-view skill)'s
  base stamp, used by draft.py.
- `platform/views/viewers/_templates/<family>.html` and `<family>.features.json`.
- `components/page-features/kit/server.py` — `status` (is the page server on); `team/people/<you>/identity.json` — `page_server_port`.

## Do this

1. Work out two things from what they said:
   - the FAMILY (the page's file name: `run-detail`, `outlier-demo`, `emails` …;
     `ls platform/views/viewers/_templates/*.features.json` lists them);
   - the SOURCE: "my live <page>" → add `--live`; "the <page> template", or no
     source named → the template.
2. The NAME: if they gave one, use it (lowercase words joined by hyphens). If not,
   ask once: "what should I call it? (or I'll use today's date)". On "any" or
   no answer, leave `--name` off and the date is used.
3. From the repo root run:
   ```
   python3 components/page-features/features.py draft <family> [--live] [--name <name>]
   ```
   If your viewers folder name differs from your git email's first part (the email lead's is
   `the email lead`), add `--person <folder>`.
4. Print the output as it is. It names the new draft, its empty change log, any
   note, and `shared` / `not shared: <git's reason>`. Exit 2 is a refusal: show its
   one line and stop. The refusals say what to do (no live page yet → use the
   template; a name taken → pick another; another person's live page → never).
5. A note saying "made from a live page, which carries no sidebar" means that
   draft cannot go live until the sidebar is back, and restoring it is not built
   yet. Say that plainly; a draft from the template has the sidebar.
6. Next step: "open <address>; tell me what to change, by number or in plain
   words" (page-change), where <address> is the page-server ADDRESS, never the file (a page that reads /data, /stamp or /act
   cannot load from a file: "Failed to fetch"):
   - port: `page_server_port` in `team/people/<you>/identity.json`;
   - the family reads from the server when
     `platform/views/viewers/_templates/<family>.sources.json` exists. Then run
     `python3 components/page-features/kit/server.py status`: "on" → give
     `http://localhost:<port>/p/<you>/drafts/<file>`; off or not installed → say
     "turn your page server on first ('turn my page server on'), then open
     http://localhost:<port>/p/<you>/drafts/<file>";
   - no sources.json → the file path works too (nothing to fetch).

## Never

- Never copy another person's live page, and never overwrite a draft — the
  command refuses both; do not work around it by hand.
- Never `git add -A`; the command commits exactly the two new files.
