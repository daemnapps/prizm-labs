# briefs — ask for a brief by what it is


Video handoffs carry [video-delivery.md](video-delivery.md): the requested versions, one thumbnail per version, the cover workflow and the return checklist. Public surface: `video_delivery.pack(folder, standalone=True)` preserves creative text and refreshes marked delivery appendices in `BRIEF.md`, legacy `briefs/*/brief.md` and `handoff.md` when present. It also writes `VIDEO-DELIVERY.md` unless `standalone=False`. The run-sheet, production, editor and re-edit packers and open-video pack index call it; no media is generated.

Delivery gate public surface: `delivery_contract.pack`, `validate`, `gate`, `request_revision`, `publish` and `submit`; CLI `pack|check|submit|revise <folder>`. Requirements, revision requests and submission templates live in the handoff. See [delivery-completeness.md](delivery-completeness.md). The approval filer validates before writing; card checks revalidate before approval. A missing/unresolved checklist holds maker work. `DELIVERY_WORKSPACE_ROOT` selects the source workspace for a separately installed approval service.

A brief is a **projection of a record**. The record is the expensive half; the
brief is what you print from it. A teardown run costs ~25 minutes, the brief off
the end of it 21 seconds — so a new brief style is one file that prints against
every record you already have.

```
python3 tools/briefs.py list                  every style, by status and state
python3 tools/briefs.py find --asset video    everything that makes a video
python3 tools/briefs.py find --asset video --actor creator
python3 tools/briefs.py path video--creator   where that prompt lives today
python3 tools/briefs.py records               what each style reads FROM
python3 tools/briefs.py check                 do the declared paths still exist
python3 tools/briefs.py retire                the kill list, with its evidence
```

Free — no model, no credential, no network.

## It registers; it does not move

Every style stays where its machine keeps it. Establishing this folder moved,
renamed and rewired **nothing** — the 8 lanes that produced 412 briefs in a
fortnight keep running untouched. Styles migrate in one at a time, on the owner's
word. Same precedent as `components/intake`, which reads every swipe as one
list while the swipe folders stay the tools they always were.

## The naming rule

    brief--<asset>--<actor>.md

The stage number leaves the filename. A brief is named for what it is and who
acts on it — not for where in some chain it sat. `copywriter` and
`email-production` both write `stage9--brief.md` today; that is the fault this
rule closes.

## What is in the register

20 styles: 18 approved and live, 2 draft and parked. Every `live` carries a run count and a date — a style that
has produced nothing in 30 days is `parked`, whatever its config claims.

`retire` lists superseded prompts still sitting in live folders. **the owner rules
that list.** Archive into the folder's own `archive/`, never delete — and note
the one marked ⚠: a byte-identical copy of it is pinned by
`components/chain-runner/chains/video-teardown/chain.json`.

Research is deliberately not here — it becomes its own component.

Ledger public surface: `ledger.refresh_delivery_states(root=None)` refreshes the existing brief ledger from handoff revision state. Both send-back and successful filing call it; R01/R02 appears in the ledger without changing the brief ID.


## Shared workflow records

Users, role ownership, assignments and delivery state belong in this workspace.
Personal interfaces consume these records; they do not own a second roster or
assignment database. JSON is authoritative; Markdown ledgers are readable exports.

| Record | Source |
|---|---|
| Canonical users | `team/people/<person>/identity.json` |
| Maker role ownership | `components/image-edit/delivery.json` → `roles` |
| Assignment, priority, queue history | `runs/queue/<brand>/<type>/<stage>/<brief-key>.json` |
| Current delivery and revision | `runs/handoffs/<role>/<brand>/<brief-key>/delivery-state.json` |
| Generated indexes | `runs/queue/index.json`, `brief-index.json`, `brief-ledger.json` |

Public surface: `workload.enrich(queue_view, root=None, legacy_offset_minutes=0)`
joins the existing queue view with safe user labels, roles, assignments, current
revision and elapsed hours. It reads identity org facts only, never profile
preferences or private contact details. A role default is not an assignment.
The caller supplies the timezone offset for legacy timestamps; explicit offsets
are preserved. Missing timestamps and unconnected usage remain null. Maker
elapsed time starts at the first recorded `making` event, and stops only at a
current `ready-for-review` delivery state. It is not active work time or an ETA.

The current queue scanner and mutation adapter still run in the personal
interface service; they write the shared entries above. This read surface does
not migrate that engine or enable the separate creative-queue shadow switch.
Per-brief collection uses project hooks for Claude Code and Codex. Each account
must load/trust this checkout’s hooks. Historical or uninstrumented usage remains unknown.


## Measure a brief session

Start Claude Code or Codex in this AI Workspace checkout. At the start of work say:

```text
Pick up brief <full-key> --stage <stage>
```

The default stage is `production`; use explicit stages such as `storyboard`,
`editing` or `revision` when those are the work being picked up. The leading
`/brief-pickup <full-key>` command is equivalent. Mere mentions of a brief do not
change attribution. Ambiguous numbers refuse and require the full key. A natural
request that does not match the leading command routes through
`python3 components/briefs/make.py pickup <full-key> --stage <stage>` using the
hook-provided session context; never supply or guess a session ID.

Pickup resolves the current issued revision, records the actual harness session
ID and excludes responses already present before pickup. Repeat pickup is
idempotent. Picking another brief/stage/revision closes the previous binding;
`/brief-release` closes it before unrelated work. A resumed session retains its
binding; a new session must pick up explicitly. Any contributor may pick up.
Use `--continued-from <recorded-session-id>` to link a new session to prior work
on this brief; this does not grant access to another account’s conversation.
Each independent or delegated session must pick up separately; detached subagent
usage is outside the parent-session collector’s coverage.

Hooks are committed in `.claude/settings.json` and `.codex/hooks.json`, preserving
existing hooks. Restart existing sessions after updating the checkout. Codex
requires review/trust of the exact hook definitions in `/hooks` on each client;
new or changed definitions are skipped until trusted. Do not bypass that review
in routine work. Claude managed settings can also restrict hooks. If pickup
cannot find its runtime context or transcript, it refuses rather than guessing.
The hook’s “Brief tracking active” message and a session record confirm binding;
a subsequent request receipt confirms token collection.

`pickup.py` is the hook/CLI adapter. `usage.summarize(brief_key, root)` is the
shared read surface, also exposed by `usage.py show <full-key>` and the ledger.
Session records: `runs/brief-usage/sessions/<id>.json`. Request receipts:
`runs/brief-usage/requests/<hash>.json`. Private transcript pointers and binding
cursors are ignored under `runs/brief-usage/local/`; no chat text or credentials
are copied into receipts. Hooks serialize writes. Replayed events deduplicate;
Claude content-block updates may only increase the same response’s counts.
Conflicting attribution or a changed/unrecognized usage format is a visible
collection error. Supported transcript versions: Claude Code 2.1.x and Codex
0.166/0.167; validate fixtures and a live smoke run before extending that range.

Input, output, cache reads and cache writes stay separate. Codex input is split
into uncached and cached portions; reasoning is already included in output and
is not added twice. Actual model and reported effort stay per request. Claude
transcripts may omit effort and identity; those remain null. A session ending
never completes a brief or bypasses its checklist. The ledger shows tracking
state and collection errors even before token receipts exist.

Receipts are visible immediately in this checkout. Other machines still need
the normal repo sync to publish `runs/brief-usage/`; hooks do not silently push
unrelated work or install global account configuration. This is local per-brief
measurement, not a weekly subscription monitor.

Rates come from the existing `platform/data/model-prices.json`. Unknown models,
missing rates and unknown/nonstandard speed remain unpriced; a priced portion is
not a total. API-equivalent cost is a comparison, not an additional subscription
charge. Codex’s transcript does not report a pricing tier, so these receipts
remain unpriced pending a supported tier/rate source.

The optional `usage.py run --brief-key <key> --stage <stage> --revision-id <revision> -- claude`
OTLP launcher remains available for dedicated sessions needing provider-reported
identity/effort. It disables transcript hooks in that process to prevent double
counting. It covers the whole launched process, so do not resume unrelated work
through it. Its event identity uses the existing exact team map, never assignment.

References: [Claude hooks](https://code.claude.com/docs/en/hooks),
[Codex hooks](https://learn.chatgpt.com/docs/hooks).

`team/work-allocation.json` holds workflow policy and optional explicit capability
records. Its people map is empty until facts are established. Role ownership remains in `delivery.json`; identities
remain in `team/people/`. No capability is inferred from token counts or title.
Separate creative owner, stage executor and quality reviewer when allocating
work. Capability declarations are currently empty pending owner assignments.

Provider event reference: https://code.claude.com/docs/en/monitoring-usage#api-request-event


The usage breakdown retains exact provider, session ID, model ID and reported
reasoning/effort for each stage and revision. Different effort settings remain
separate even within one model/session. The request trace retains request ID,
prompt ID when provided, time and token classes, so model/effort switches can be
inspected in order. Missing effort is `null` (not reported), never inferred from
a global default. Link outcome to the brief's actual checklist/review evidence;
process exit and larger token usage do not prove a better result. Skill testing
and capability assessments are deferred; these traces measure execution only.


## Weekly operating target

`team/work-allocation.json` → `operating_model` defines the weekly paid-capacity
target and the division between human oversight and system coordination. Use
that policy when planning workload or training: the overview carries session
state, dependencies, blockers and review requests; people judge outputs and
correct what needs judgment. Maintain useful, execution-ready backlog so an
available worker can take the next independent stage. Acceptance checks still
apply. The target is not permission to generate filler or bypass approvals.

The automatic dispatcher is not implemented. Employee telemetry is not connected.
Per-brief tokens and provider-reported subscription utilization are separate
measures; never fabricate a percentage from an unknown allowance denominator.


## Bind variables when work happens

The brief, stage and revision identify the work. A recorded assignment or role
default is not an exclusive lock on who may contribute. Each provider-reported
session/model/effort stays on its own request record; a later contributor adds
history to the same brief without rewriting previous contributors.

Person and account are optional at pickup. The optional OTLP collector resolves the provider's
reported email through run-kit's existing exact identity map, and stores a stable
hash of a reported provider account ID. It never stores the email or raw account
ID. If identity cannot be resolved, the work still records with null identity.
No account plan, capacity, model access or human skill is inferred. Optional
`--person`/`--account-ref` values are declared context only; they do not become
observed identity. No pre-filled account roster is required.

For the optional OTLP launcher, continuation uses `--continued-from-session-id <recorded-session-id>` (the pickup hook uses `--continued-from`).
It must refer to an existing receipt on this brief. The new event retains its
actual current session ID and contributor. This records lineage; it neither
copies a session nor grants access to another account's session. Provider access
and session-resume capabilities must be verified independently.

## Resource queues

`resources.project(queue, development_view, now=None)` projects open creative
assignments and the existing development board into one read-only queue per
canonical team identity, including people with no recorded work. It includes
non-brief creative items, backlog, explicit development assignments, pending
review responsibilities, and open issues/follow-ups. Unassigned or unresolved
work stays visible in a separate group. A builder/owner is not inferred to be
the current assignee. Private development cards stay off this shared view.

The personal ledger calls `resources.development(root)`, a 120-second in-memory
cache of the existing public `components/page-features/dev_queue.py --root ...`
read command, then passes that payload to `workload.enrich(..., development_view=...)`.
`resource_queues` reports each source's refresh/error state. A failed refresh
retains the last result with an error; an unloaded source is not treated as an
empty workload. No assignments, review marks, archive records or dispatch states
are changed. The output is a projection, not a second task database.

Display order is urgent first, then revision, active, review, queued, held and
backlog, oldest first within each group. This is a viewing order, not an approved
execution schedule. Empty queues do not establish capacity; elapsed age is not
working time or a completion estimate. The development board has its own cutoff
and source coverage; this view does not claim to inventory every person's work.

Role workflow tasks also enter this view through `resources.role_handoffs(root)`,
using `role_tasks.local_fetch` and `mytasks.load_tasks` from the existing PM
tool. The folded task state/assignees are authoritative; a handoff manifest or
an old queue receipt is not a current-status source. Done/dropped tasks are
excluded; due dates, recorded priority, role and validated session-card text
are preserved. Source failure is visible. The personal ledger's Role handoffs
view (`/ledger?source=role-handoffs`) opens these jobs directly, including their
full instructions, without older creative/development work obscuring them.

## Shared ledger page

The canonical visual page is `platform/views/brief-ledger.html`, committed with
its shared readers. The personal Nucleus service serves this page at `/ledger`
and supplies the existing `/api/queue` and `/api/ledger/pics` read endpoints.
`/ledger?source=role-handoffs` opens the role-task slice; the All recorded work
button includes the same jobs in each person's full queue. Full session handoffs
expand in the page. The file is not a standalone data snapshot: it requires
those endpoints and reads current JSON records on load. The existing personal
service and its legacy creative queue mutation engine remain separate; the
private review proxy permits reads only.
