---
name: page-change
description: Change something on one of your page drafts — by its number ("change L9 on my outlier draft: make it a grid") or in plain words ("make the queue a grid", "add priorities for me", "move the status to the top") — then log the change and commit and share it. Use when someone says "change L9 on my <page>", "on my <page> draft, …", "make the <thing> on my page …", "add <something> to my page", "page change", "/page-change". Edits drafts only; a live page is never edited (it offers to make a draft first).
---

# page-change — one change to your draft, logged and shared

> **Activates component:** `components/page-features` — changes a page draft.


A thin wrapper over PF-1c (plain-words changes)'s `features.py change`. Every change is
one line in the draft's change log plus a commit of exactly that person's files.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/page-features/features.py` — the `change` and `sync` verbs, and the
  family-list validator (`features.py <family>.features.json`).
- `platform/views/viewers/_templates/<family>.features.json` — the family's number
  list: every number, its kind letter (D data · R rule · M media · L layout ·
  A action), `state`, `source`, `place`, `note`, and `retired` numbers.
- `platform/views/viewers/<you>/drafts/<family>--<name>.html` and its `.changes.jsonl`.
- `components/page-features/kit/server.py` — `status` (is the page server on); `team/people/<you>/identity.json` — `page_server_port`.

## 1. Find the draft

- They named a draft, or have exactly one draft of that family → that one
  (`python3 components/page-features/features.py pages` lists them).
- Several drafts of that family → ask which, listing names.
- They named a LIVE page (`viewers/<you>/<family>.html`), or have only a live page
  → do not touch it. Say "a live page is never edited directly — shall I make a
  draft of your live <family> first?" and on yes use page-draft (`--live`).
- Someone else's page → refuse; a person changes only their own drafts.

## 2. Find the number

Read the family list. By number ("L9", "9") → that entry; if it is missing or in
`retired`, say so and stop. In plain words → match the words against each entry's
`name`, `place` and `note`, then:

1. **One clear match** → apply it; log with `--resolved claude --match "<one
   sentence: why this number>"`.
2. **Several matches** → ask, listing each as tag + name (e.g. "L9 The stage
   columns, L12 The card grid"). Change nothing yet.
3. **Partly exists** → say what exists (by number) and what is missing, then go on
   with 4 or 5 for the missing part.
4. **Layout over data that already exists** → add a NEW number: the next free `n`
   (above every feature AND every `retired` n — never reuse or renumber), kind
   `layout`, state `wired`, status `draft`, `source` null, `anchor` = the number as
   text, `added_by` = you, `added` = today's date. Then mark the element in the
   draft with `data-feature="<n>"`, run
   `python3 components/page-features/features.py sync <draft> <family list>`,
   and log with `--family-list <family list>`.
5. **Needs data that nothing has** → add a NOT-BUILT number: state `not-built`,
   `source` null, `added_by`, and a `needs` block {`data`, `where`, and
   `written_by` / `component` when known}. Build nothing on the page and NEVER
   fake the data. Log with `--missing --needs '<the same needs as JSON>'
   --family-list <family list>`. Tell the person it is logged as not built and who
   would have to build the data.

After 4 or 5, run `python3 components/page-features/features.py <family list>`; it
must say `valid`. If not, fix the entry before logging.

## 3. Make the change and log it

1. Edit the draft's HTML on the element(s) carrying `data-feature="<n>"`. Never edit
   inside the block marked `page-features overlay: component-owned`.
2. From the repo root:
   ```
   python3 components/page-features/features.py change <draft> --n <n> --said "<their words, verbatim>" [--resolved claude --match "…"] [--missing --needs '<json>'] [--family-list <family list>]
   ```
   Add `--person <folder>` if your viewers folder name differs from your git email's
   first part (the email lead's is `the email lead`).
3. Print the result line as it is: `saved and shared`, `saved, not shared: <git's
   reason>`, or `refused: <why>` (exit 2; nothing logged — show it and stop).
4. One line after: "open <address> to see it; when it's right, say 'make this
   draft live'" (page-live), where <address> is the page-server ADDRESS, never the file (a page that reads /data, /stamp or /act
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

- Never edit a live page, a template (`_templates/<family>.html`) or another
  person's draft.
- Never renumber, reuse a retired number, or fake data for a not-built number.
- Never commit by hand around the command; it commits exactly the draft, its log
  and (when passed) the family list.
