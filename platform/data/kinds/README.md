# platform/data/kinds/ — manifest-driven review types

Moved here from `lab/the developer/prompt-optimizer/review/kinds/` on 2026-08-25
(card DP-2). Two kinds stayed behind under a ruled carve-out — `e2e-brief`
and `e2e-runs`, pending item I-54 — and the platform still resolves the lab
home as a fallback, so both serve unchanged.

One JSON manifest per review type ("kind"). Standing up a new review
process = adding a manifest here (+ items in the workspace) — the
review-app serves it through the generic API with **no app change and
no redeploy**. Same tier-zero property as views/: manifests are data;
the app applies them through validation, never executes them.

## Manifest schema (v1)

```json
{
  "kind": "task-cards",            // [a-z0-9-], must equal the filename
  "title": "Task-card review",
  "note": "shown to reviewers",
  // ONE of:
  "items": [ {"id": "x", "label": "…", "content": "… or object"} ],
  "items_file": "repo/path.json",  // JSON array (or object: set items_key)
  "items_key": "cards",            // optional: key holding the array
  "item_id": "id",                 // field used as item id (default "id")
  "item_label": "title",           // field used as label (default "title")
  // passed through to viewers untouched — the server never interprets it:
  "verdict_fields": [ {"key": "ok", "type": "boolean", "label": "…"} ],
  // optional (records-API fix, 2026-09-01): "history" = /api/reviews serves
  // EVERY record for an item, ascending — for kinds whose records are an
  // event history folded on read (tasks, inbox). Absent = latest write wins
  // per (reviewer, item), the original contract every other kind's readers
  // were built on. See BLOCKER-2026-08-31-records-api.md (pm-tool build).
  "serve_records": "history"
}
```

`items_file` (and any per-item `file`) must be under the app's
READ_PREFIXES allowlist (`lib/github.ts` in ai-dev) — extending the
allowlist is an ai-dev change (the developer's).

## API (the whole contract)

Auth: reviewer key, either the browser cookie or
`Authorization: Bearer <your-reviewer-key>` (for standalone viewers).
Optional `X-Client: <name>` identifies your viewer in every record
(lineage — defaults to `review-app`).

- `GET /api/items?kind=<kind>` → `{kind, title, note, verdict_fields,
  reviewer, items: [{id, label, content, section?, reviewedBy,
  doneByMe}]}`. For `md-sections` kinds, `section` is the `##` heading
  the item sits under (its phase/group in the source file).
- `POST /api/review` body `{kind, item, verdict: {…}, notes?}` →
  appends one immutable record under `../records/<kind>/`
  (`<ts>--<reviewer>--<item>.json`). Verdict is any JSON object ≤16KB;
  `verdict_fields` above is the shape viewers should render, but the
  server stores what it gets — interpretation lives with the kind's
  owner.

## Verdict schema v2 — card-refinement convention (2026-08-19)

For kinds whose purpose is refining a card deck (element-level review +
card disposition), viewers write this verdict shape. The server still
treats it as opaque; this section is the convention viewers and the
refinement pass agree on:

```json
{
  "disposition": "approve | revise | decline | move",
  "elements": {
    "story":     { "approve": true },
    "done_when": { "approve": false, "feedback": "not checkable as written" }
  },
  "move_to": "after:SE-4",
  "feedback": "card-level note"
}
```

- Element keys are the card's field labels, lowercased,
  non-alphanumerics → `_` (`Done when` → `done_when`).
- `disposition` rules: `approve` = every element approved; `revise` =
  any element not approved (each such element carries its own
  feedback); `decline` = card shouldn't exist (card-level `feedback`
  required); `move` = card is fine but sits in the wrong place
  (`move_to` = `before:<id>` / `after:<id>`, card-level `feedback`
  states why).
- A "move" is a PROPOSAL recorded as review data — reviewers never
  mutate the source deck; whoever refines the md enacts accepted moves.

Records are create-never-edit: a re-review is a new file. On read-back,
latest write wins per (reviewer, item) — except kinds declaring
`"serve_records": "history"` (tasks, inbox), whose full record history is
served and folded by the viewer. `smoke.json` is a disposable test kind —
records under `../records/smoke/` carry no meaning.

## Validating manifests (QC floor)

`python3 lab/the developer/prompt-optimizer/review/validate_kinds.py` (from the repo
root; any cwd works — the validator finds both kind homes itself) checks
every manifest here against the platform's real parsing rules — ported
verbatim from `lib/kinds.ts` in ai-dev. It FAILs on what makes the
platform throw (bad JSON, kind/filename mismatch, missing items source,
md-sections file missing or yielding zero items) and WARNs on what the
platform silently swallows: a `###` heading that produces no item (e.g.
a prose heading like `### What She Wants`), items whose id fails
`ITEM_ID_RE`, duplicate ids. `--kind <name>` checks one kind. Exit is
non-zero on any FAIL. Run it after adding or editing a manifest or an
md items file, before committing.

## Verdict schema v3 — inventory→workflow (2026-08-19, supersedes v2 for inventory kinds)

Card verdicts: `disposition: approve | revise | archive | add` (`move`
retired — position lives in the assembly). `archive` = irrelevant but
kept, requires feedback. `add` = reviewer-drafted card (open_items
kind), verdict carries the full `card:{…}` draft. Workflow membership,
order, and now/later development scope live in the companion assembly
kind's snapshot records (see email-campaign-workflow.json) — one whole
snapshot per save, latest per reviewer wins, convergence across
reviewers is a human discussion.
