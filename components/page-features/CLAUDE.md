# components/page-features — numbered features on any personal page

Created 2026-10-21 on the developer's word, relayed verbatim by ◆ PLAN · mn · dev-the developer
[b2bef2]: "just starta as a component, it will be used." Deck:
new-workflow-design/builds/page-features/task-cards.md (PF family). Lab station
skipped on that word (duty-6 flag in the deck). Seed: ◆ PLAN's run-detail
catalog, new-workflow-design/builds/page-features/seed/ (reference).

What it is: each number on a page names a FEATURE, never a DOM position. Each
feature has one of five kinds, shown as a letter before its number (D4, R9):
- D data: a value saved in a data file, shown as it is;
- R rule: the page works it out from data by its own rule, so two pages can
  disagree (promotion moves the rule into data or flags it page-only);
- M media: a picture, clip or voice file on Drive;
- L layout: arrangement, ordering, navigation or help text, no data of its own;
- A action: a button that runs a component's own command and never writes
  records itself.
Each feature says where its data lives (`source`: component · file · field)
and how far it is built (`state`: wired | after-card | not-built). People mark
keep / drop / want-different on the published page. The same features.json
travels into the design mock and is checked mechanically.

## The four new-resident answers (components/CLAUDE.md checklist)

1. Engine + owner: `features.py` (validator + seed conversion), then
   `check.py` (PF-3 (feature check)), `overlay.js` (PF-2 (feature overlay);
   read-only since PF-2c (overlay read-only): marks.js retired 2026-10-21,
   feedback happens in a Claude session by number), `kit/` (PF-4 (page starter kit);
   minimal form built by the email lead 2026-10-21: `kit/serve.py <page>` serves a page on 127.0.0.1 with
   `/data/<name>` from `_templates/<family>.sources.json`, a component's own command; `/runs/` and
   `/p/` files, read-only; no Drive thumbnails yet, `kit/test_serve.py`; `kit/server.py on|off|status|restart|remove|push`,
   PF-14 (page server): one always-on server per person (macOS LaunchAgent) for all their pages, from its own private
   worktree under ~/Library/Caches/upright-page-server/, `kit/test_pf14_page_server.py`), `share.py`
   (`features.py share <draft>`, PF-9 (share check) + PF-9c (share warns): the family owner's draft
   becomes the template unless a button calls lab code or the overlay was edited; every other
   "won't work on another machine yet" finding prints as a warning with its fix and owner, and a
   button through a components/ door counts as routed through the person's own Claude), `promote.py`
   (`features.py promote <draft>`: anyone's reviewed draft becomes the family template on
   the family owner's act, refused unless it passes the going-live check, was cut from the
   template as it is now and adds no share-check blocker; the email lead 2026-10-21, `test_promote.py`). Owner **the email lead**
   (the developer, relayed verbatim by ◆ PLAN [b2bef2], ≤10:15:10Z 2026-10-21: "i want her
   to be the owner as well"; definitions and engine both hers until he splits them).
   Family owners (set `critical`, change _templates/<family>.html, share as template):
   emails the email lead (renamed from emails-demo 2026-10-21: the shared page everyone opens), outlier-demo the owner, run-detail the developer.
   dev-queue the developer: PF-18 (dev-queue view), the team's dev work read from git by `dev_queue.py` (decks, impl request records, merge commits, the decision log; never cards_status.py), `test_pf18_dev_queue.py`; marks wait for PF-18b (review marks), the issue queue for PF-18c (issue queue).
2. Definitions + curator: a page's own `features.json`, kept BESIDE THE PAGE
   (never in this folder), curated by that page's owner. This folder holds
   only the contract (`features.schema.json`, which also fixes the five kinds
   and their letters) and examples (`examples/`).
3. Plane it emits: none — the manifest is the product. No marks are saved
   anywhere (PF-2c (overlay read-only)); each page version's changes live in
   its own <family>.changes.jsonl in git. Runs visible: none
   (O12 (records adapter)) — nothing here runs on a schedule or files a run.
4. What the manifest declares per entry: `n`, `name`, `kind` (data | rule |
   media | layout | action), `state` (wired | after-card | not-built),
   `status` (draft | approved | deprecated — the status words; `state` is
   never a status), `source` {component, file, field} or null (null for
   layout, action and rule, and for anything not-built), optional `place`,
   `note`, `card`, and `where` (a per-version locator for a page with no
   `data-feature` tags; the number stays the identity). The file carries
   `kinds` (letter, name, meaning), `state_words`, `page` or `versions`, and
   its own `status`: a manifest under builder card rule 5.

Runs by: person

## Rules for this folder

- **Buttons run direct by default** (the developer, 2026-10-28, decision log; PF-15 (direct by default)): every wired button on a page here runs through the page server, declared in its family's run table as quick, job, confirm-job or external. Copying a request for Claude is only the fallback when no server serves the page, or an exception written in the table with its reason. External sends follow the wall; a lab-code door is never wired.

- The builder card (components/CLAUDE.md, top) governs.
- Pattern sources, imitated and never imported (builder card rule 6):
  ◆ PLAN's prototype (new-workflow-design/builds/page-features/seed/prototype/)
  and components/page-picture-review (pic-index.js, pic-marks.js).
- overlay.js never touches the artifact runtime and saves nothing; a page's
  change history is read from its own changes.jsonl (PF-2c (overlay read-only)).
