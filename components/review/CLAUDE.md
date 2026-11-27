# components/review/ — the review record grammar, and the surfaces over it

One kind — `review` — carrying a **request → verdict → close** grammar over any
asset by warehouse pointer, plus the module, panels and adapters that make it
usable. Built under the `review-component` build (prefix **RV**); cards in
`new-workflow-design/builds/review-component/task-cards.md`.

**Design of record:** the artifact "Review Component Design"
(claude.ai/code/artifact/f3c962be-b283-41d8-827b-5ccce2a6228b) plus
`team/plans/dev-developer.md` batches 51–54. The rulings are in
`the-org/decision-log.md`, 2026-09-08 — the artifact and the plan are the
reasoning, the log is the law.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

1. **Engine + owner — the developer.** The engine is the record grammar plus
   `review_request.py` (RV-2 (review request module)): `file_request`,
   `list_open`, `latest_verdicts`, `is_accepted`, writing by git-commit by
   default and by `POST /api/review` when a review key is in the environment.
   the developer owns the code, the platform route and the merge word on anything that
   deploys.
2. **Definitions + curator — the email lead.** The definitions are the record grammar
   and the reference panels: what a request means, what a lane is called, how
   a type renders. She holds the approval gate on those — and, per the freeze
   below, on any change to the manifest at all.
3. **The plane it emits — `platform/data/records/review/`.** One append-only
   record per event, `<ts>--<reviewer>--<item>.json`, served through
   `/api/reviews?kind=review` as a full history (`serve_records: "history"`).
   Nothing else is emitted: there is no run directory, no output folder, and
   **no merged index record** — discovery is a kind-wide read plus the declared
   index view RV-8 (review queue index view) adds.
   **Declared dependency (review#8):** `review_request.py` loads
   `platform/workers/mini-worker/plane_caps.py` by path (the verdict cap's one
   home, WM-25 (verdict cap one source)); without it the module will not import
   (it keeps no second copy of the cap) — as I-140 (qc worker dependency) did for qc-checks.
4. **What the manifest declares per entry** — `platform/data/kinds/review.json`.
   An entry is a REQUEST, item id `RQ-<id>`, and every record on it declares
   exactly one `event` (`request | verdict | close`). A `request` declares
   `type` (text | md | image | video | doc | link | page), `asset`
   (`{warehouse: repo|drive|blob|supabase|url, ref, title, at?, viewport?}`),
   `reviewers`, `lane`, and optionally `due` and `on_accept`. `url` and the
   optional `viewport` (`mobile | desktop`, **absent means unstated**) are
   the developer's ruling of 2026-09-10, card RV-34 (url and viewport): `blob` means a
   capture WE MADE and hold, so a Figma file or a Netlify preview is a `url`
   and `ref` is the link itself with tracking params stripped. `at` stays
   repo-only — version binding for a link is the capture (RV-35 (page
   capture)), never a commit. `page` is the developer's ruling of 2026-09-10, card RV-47 (type page)
   (type page): the two species of `url` are declared beside each other —
   `page` is a deployed web page, FRAMED at a declared width, and `link` is a
   thing we deliberately do NOT embed, a Figma frame whose comments belong in
   Figma. The distinction is not where the thing lives (both are `url`); it is
   whether the panel embeds it. The species is DECLARED by the filer and never
   inferred from a hostname, at any layer. A `verdict` declares `verdict`
   (approve | reject | fix) with `reasons[]` and `note`. A `close` declares
   `decision` (accepted | rejected | parked). The manifest also declares
   `media_inventory: "media"` — the record field listing media rows, which the
   generalized `/api/media` (RV-4 (media route per-kind)) reads.

Runs by: both

(the developer, 2026-10-07, triage action 3 (definition lines and registry rows); SI-6 (intent line): a person files and reads
reviews from a session, and the mini runs the module through its callers.)

**Python API — the only names a caller may use** (the developer, 2026-10-07, triage action 6 (declare public surfaces); the I-139 (qc-checks answers) form). Callers load `review_request.py` by path (each keeps a small `review_request()` loader) or import it with this folder on the path, and may use only:
1. **Filing:** `file_request(asset, type, reviewers, lane, requested_by, …)` → the request record filed (git commit, or `POST /api/review` with a key); `file_record(item, verdict, reviewer, notes=, …)` → one record filed; `record(item, verdict, reviewer, notes=)` → a record not yet filed; `filename(rec)` → its file name; `has_key(env=)` → whether the API door is open; `Refused` — raised for anything the grammar refuses.
2. **Reading:** `read_records(root=, item=)` → every record, oldest first; `fold(records)` → one item's state (never stored); `list_open(records=, root=, reviewer=, lane=)` → open requests, folded; `latest_verdicts(records)` → `{reviewer: verdict record}`; `is_accepted(records)` → `True` only on an `accepted` close.
3. **Validators** (RV-67 (review public validators)): `people`, `asset`, `anchors`, `capped`.
4. **Constants:** `ITEM_RE` (`RQ-<id>`), `KIND` (`"review"`), `RECORDS_REL` (`platform/data/records/review`), `VERDICTS` (`approve | reject | fix`).
5. **Command:** `python3 components/review/review_request.py --title --type --warehouse --ref --lane … [--viewport]`.
Anything else is internal and may change without notice (`_file_batch` included).

## The ruling that shapes everything here

**The manifest is FROZEN, and it IS the contract.** the email lead builds the front end
and has no ai-dev access; `platform/data/kinds/review.json` is the only thing
standing between her lane and the engine's. RV-1 (review kind manifest) wrote
it verbatim from batch 54's frozen block, the lead marks it `approved`, and no
panel card dispatches before that mark. **A manifest change after the freeze is
a ruling, never a maker's judgment** — a maker who believes a field is missing
BLOCKS and says which. RV-8 (review queue index view) is the one card licensed
to edit this file, and only to add its index declaration, after RV-1 (review kind manifest) merges.

Consequences worth stating once, because every later card inherits them:

- **Status is never stored — it is folded.** No close = open; the latest close
  wins; the latest verdict per reviewer stands. RV-2 (review request module)
  owns the ONE implementation; a second copy of the fold is a defect, and
  RV-8 (review queue index view) and RV-10 (PM review integration) import it.
- **No sub-items.** `.v` and `.close` do not exist as item ids — `request`,
  `verdict` and `close` are event labels. (The visual-run/output-review
  `.i<k>` split existed because those kinds are latest-per-reviewer; this one
  is `history`, so it does not need the trick.)
- **No merged index record, ever.** Struck by the 2026-09-08 ids-only ruling
  and by WM-24 (index truncation).
- **Media is a pointer, never bytes** (workspace rule 3). Drive is the media
  warehouse for human-authored creative and video, blob for small machine
  outputs (the developer, ruled 2026-09-08).

## Layout

The folder is its own listing (`ls components/review/`). `review_request.py` is
the module and the one fold (RV-2 (review request module)); `seed/` holds
RV-1 (review kind manifest)'s example requests; `reference/` the reference
panels; `tests/` the declared tests.

## Status

This folder's residency and status are its row in `components/CLAUDE.md` (the
register); this file does not restate them.
