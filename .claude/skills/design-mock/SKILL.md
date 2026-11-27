---
name: design-mock
description: Turn a page a seat has authored into the committed design mock for one subject of one build — "make this the design mock for the inventory page", "update the reorder planner mock", "/design-mock <build> <subject>". Writes the file under builds/<build>/design/, stamps the mock header and the visible strip, commits the ONE file under `design:` and pushes, then reports path + commit; publishes an artifact only on request or for a reviewer with no clone. Refuses rather than guesses. A page for people to read is not a mock and does not trigger this.
---

# /design-mock <build> <subject>

> **Not a component:** a workflow build at `new-workflow-design/builds/<build>/`.


External dependencies (greppable): `new-workflow-design/builds/<build>/`
(the build must exist), `team/id-tags.json` (every card id in the header
carries its tag), the Artifact tool (publish and republish by `url`), the
roles table row `◆ PLAN · dev-<owner>` in `the-org/positions/product-lead.md`
(the `design:` pen and its kill), `.githooks/commit-msg` (the `design:` path
gate once CLI-21 (design prefix gate) merges).

Why this exists: a maker is headless, with no browser and no claude.ai login,
so a mock that lives only at an artifact URL reaches nobody who builds from it
(root cause verified 2026-09-15). The mock has to be a file in the repo, and
two people's seats have to make that file the same way. Ruled 2026-09-16
(the developer): mocks are named by SUBJECT, one file per surface with anchored
sections, never one file per card; the marker that says "this is a mock, not
a presentation" is the file's location, its commit prefix and a visible strip
on the page, all three stamped by this skill.

Two things a page can be. Say which:

| The person says | It is | What happens |
|---|---|---|
| "make this the design mock for …" / `/design-mock <build> <subject>` | a build input | this skill, all five acts |
| "publish this for … to review" | a presentation | the Artifact tool only; nothing committed unless they add "keep it in the repo", which is a `note:` file |

## Act 1 — RESOLVE, ask once for anything missing, refuse what cannot be

- **build**: must exist as `new-workflow-design/builds/<build>/`. Unknown →
  list the builds and stop.
- **subject**: a kebab slug naming the SURFACE (`inventory-page`,
  `reorder-planner`), never a card id. Target path is
  `new-workflow-design/builds/<build>/design/<subject>.html`. If the file
  exists this is an UPDATE; say so.
- **source page**: the HTML the seat just authored (its scratchpad file) or a
  path the person names. It must be one self-contained HTML file: inline CSS,
  no external images, no script needed to read it. Anything else (markdown,
  code, a folder) is not a mock — say why and stop.
- **covers**: the card ids this mock is the design for, each with its tag.
  May be empty on a first draft; ask once, accept "none yet".
- **anchors**: the element ids in the page that cards will point at. Read
  them from the page (`id="…"` on section-level elements); the person may
  name more.

## Act 2 — STAMP and CHECK

Insert or refresh, at the top of the file, the header comment this skill owns:

```
<!-- design-mock
build:    inventory-tab
subject:  inventory-page
covers:   INV-C14 (looks-good gate), INV-C16 (planner v6)
anchors:  product-order, planner-columns, runway-math, send-by
status:   draft
artifact: https://claude.ai/artifact/…
updated:  2026-09-16T02:40Z by dev-the designer
-->
```

and, as the first element inside the page's content, the visible strip
(fixed markup, styled from the page's own tokens):

```
<div class="design-mock-strip">Design mock · inventory-tab · inventory-page ·
covers INV-C14 (looks-good gate), INV-C16 (planner v6) · updated 2026-09-16 ·
source: new-workflow-design/builds/inventory-tab/design/inventory-page.html</div>
```

Then check, and stop on the first failure, naming it:
1. every anchor in `anchors:` exists as an element id in the page;
2. every card id in `covers:` carries its tag, and the tag matches
   `team/id-tags.json` where one is on file;
3. on an update, an anchor that existed in the previous version and is gone
   now is listed as RENAMED OR REMOVED in the report — cards may cite it.
   The skill never silently drops one.
`status:` is `draft` until the person says the mock is agreed; then `agreed`.
`updated:` is `date -u`, never estimated.

## Act 3 — COMMIT once; PUBLISH on request

**THE FILE IS THE TRUTH. A PAGE IS FOR PEOPLE WITHOUT THE REPO.** (the developer,
2026-09-16: "is it better that we work off the html rather than the shareable
artifact, and only generate an artifact if it needs sharing?" — yes.)

New mock, DEFAULT: stage the ONE file, commit, push. The header carries
`artifact: (not published)` and the visible strip omits the link. Nothing is
published.

PUBLISH only when one of these is true:
- the person says so ("and publish it", or later "publish the <subject> mock");
- a NAMED reviewer cannot open the file — they have no clone;
- a fold is coming that will be read FROM THE PAGE rather than from the repo.

When you do publish a new mock, the order is today's: publish with the Artifact
tool (favicon, and a one-line description beginning "Design mock:"), write the
returned link into `artifact:`, commit, push, republish so the live page
carries its own link.

Update to an existing mock: stage, commit, push. If it already holds a link,
republish with that `url` — **also only on request**, by the same three tests.

Why the default is the file, and these are the three reasons the developer heard:
**makers read files** — a maker is headless, with no browser and no claude.ai
login, so a mock that exists only as a link is a mock no maker can open (the
2026-09-15 root cause behind the gantt's fidelity gaps); **publish rights are
per session**, so a page one seat can republish another cannot; and **a
share-version pin leaves viewers on a stale page** while the live one moves on
without them.

KILL (recorded with the amendment): reviewers stop looking at mocks because
there is no link → the default flips back to publish.

The commit message: `design: <build>/<subject> — <one line on what changed>`,
every id tagged. Staged paths: exactly the one file. If anything else is
staged, stop; a `design:` commit carrying anything but a mock is the
kill-condition on the design pen for everyone.

Where the seat sits in a clone shared with a worker (the mini's
`~/Projects/ai-workspace`), commit through a throwaway worktree on a temp
branch and `git push origin HEAD:main`; never touch that clone's index. On a
personal clone, a plain add, commit, push.

## Act 4 — REPORT

One line to the person, in a fenced block: path · short commit · covers —
and the artifact link ONLY when the mock was published. Anyone with the repo
opens the mock at its path after a pull; a link is for people without one. Then one pointer line per covered card, for the lead's carding:
`INV-C14 (looks-good gate): design/inventory-page.html#planner-columns`. The
lead copies the pointer onto the card and the dispatch names it; the person
folds nothing.

## Act 5 — NOTHING ELSE

This skill does not touch cards, tags, the decision log, workflows.json or
any registry; it does not build anything; it does not redesign the page. If
the person wants the mock in a different build, that is a new mock in that
build, not a move.

## Rules this skill obeys

- The `design:` pen and its kill, roles table row `◆ PLAN · dev-<owner>`
  (2026-09-15, naming amended to subjects 2026-09-16).
- Every id in the header, the strip and the commit message carries its tag
  (CLI-13 (id-tag lint) shape).
- Refusal is explicit: say what is missing or wrong and stop; never guess a
  build, a subject or a covers list.
- Kill-condition for the anchor convention: a maker builds against a stale or
  missing pointer → a worker-compiled `design/index.json` from these headers
  becomes mandatory and cards are linted against it; until then the RENAMED OR
  REMOVED line in Act 2 is the guard.

Reuses / could be reused by: reuses the Artifact tool's publish-by-url and
the `design:` pen; the header-plus-strip marker could be reused by the
`note:` pen for handoffs if they ever need the same "what is this file"
signal; the anchor check could be reused by a card lint.
