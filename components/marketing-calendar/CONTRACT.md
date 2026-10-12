# Contract — marketing-calendar

What a run emits, and what anything downstream may depend on. This is the
**only** dependable surface: nothing outside this folder may read `machine/`
internals beyond the names in "The library surface" below. It is written to the components contract standard (marketing-calendar#11).

## The run

    python3 machine/calendar.py <YYYY-MM> --brand <brand> [--out DIR]

Every write lands under `--out` (default: the repo-root
`runs/marketing-calendar/`), in one folder `<brand>/<YYYY-MM>/` — the month's
one home (SI-22 (calendar months home), 2026-10-07). The front page covering
every brand is `runs/marketing-calendar/_system/calendar.html`.

Exit is non-zero on failure; a failed run writes no `slots.json`.

`--dry-run` (or `--dry`) spends nothing and writes nothing — not even the
month's folder. It checks the brand, runs layers 1–2 in memory, resolves both
prompts (highest `-vN-`, numeric) and reports every field each would be handed
as OK / EMPTY / WAITS / MISSING. Exit 0 ready · 1 a prompt or a field is
missing · 2 the brand is blocked.

`--model <name>` forces one model onto both thinking layers. Without it each
layer takes its tier from `components/run-kit` (`designs` for both), and the row
in `run.json` carries `model` and `model_why`.

**One home, no second copy:** the folder above is where the board and downstream
tools read the month; it is never filed again (`gates.file_after_run` returns
nothing for a month already home). `moments_apply.py --write` files a PROPOSAL
under `runs/marketing-calendar/<brand>/moments-<YYYY-MM-DD>/` and writes nothing
under `brands/`. `run.json` additionally carries `gates` (`{"inputs", "elements", "out": "check.json"}`) and
`elements` (`{"format/email": {<type>: {"from": library|brand|both|unknown,
"sends": n}}}`); both are additive.

## What the folder holds

| Path | Who writes it | What it is |
|---|---|---|
| `slots.json` | the engine | **the deliverable** — an array of sends. The stable surface. |
| `run.json` | the engine | the run's own state — see **The run record** below |
| `checks.md` | the engine | every rule tested, with `## Breaks` and `## Warnings` lists and the per-person math |
| `check.json` | the engine (`gates.py`) | the quality gates, in `components/quality-checks` `hold()` shape: `{"inputs": {result, problems, notes}, "elements": {result, problems}}`, `result` is `pass` or `HELD`. **Recorded, never raised** — a `HELD` month is still written; the board is the review. Added 2026-09-20; a reader must tolerate its absence on older months |
| `review.json` | a **human**, via the board | status, rewrites and notes per slot — see below |
| `board.html` | `board.py` | generated, rebuilt on every load; never hand-edited |
| `1-holidays/` … `9-order/` | the engine | one folder per layer, and for the two AI layers the prompt **as actually sent** beside its full output |

## The run record

`run.json` carries three things, kept apart on purpose.

**`stages`** always holds all nine layers, keyed by the chain's own keys
(`holidays · moments · cells · anchors · concepts · catalogue · offers ·
affiliate · order` — declared in `machine/chain.py`). Every layer records the
same shape, so a reader can ask any of them the same question:

```json
"order": {
  "n": 9, "name": "The order", "by": "code", "status": "done",
  "produced": 26, "unit": "slot", "out": "9-order/order.md",
  "seconds": null, "at": "2026-09-13T23:25:24", "dropped": 1
}
```

A thinking layer (`by: "ai"`) adds `prompt_name`, `prompt_sha256_12`, `model`,
`chars_out`, and paths to `sent` (the prompt **as actually sent**) and
`reasoning` (its full output). The prompt is the product: a month that cannot
name the prompt version behind it is not reproducible.

`status` is one of:

- `done` — it ran in this run.
- `carried` (with `carried: true`) — a replay reused this layer's output from
  disk and carried its record forward unchanged.
- `unrecorded` — a replay reused the output, but no prior record exists, so
  the prompt version behind it cannot be named. **A named hole, never a
  silent one.**

**`events`** holds what happened to the run rather than what a layer decided —
a replay, a resume. These are not stages and never appear among them.

**`checks`** holds the checker's result (`errors`, `warnings`, `out`). The
board is not a layer: it tests the chain's result and draws the review page.

## A slot

Every send carries at least these. Consumers should tolerate extra keys
being added; none of these are removed without a version bump here.

```json
{
  "id": "sep-01",                   // stable within the run; the review key
  "date": "2026-09-14",             // ISO, always inside the month
  "hour": 17,
  "segment": "Core | VIP Customer", // the brand's own vocabulary
  "segments": ["Core | VIP Customer"],
  "avatar": "avatar-one",
  "variants": [                     // one per avatar in the slot
    {"avatar": "avatar-one", "angle": "…", "angle_dropped": "…"}
  ],
  "category": "Community",          // Promotional · Educational · Cultural
                                    // Community · Brand · Affiliate
  "type": "spotlight",              // from the brand's type catalogue
  "role": "earns",                  // earns · sets-up · recovers · closes
  "occasion": "…",                  // what the send is about
  "product": "the-king-skin-set",
  "offer": "none",                  // a key in the brand's offer bank, or "none"
  "follows": null, "then": null,    // the arc, by slot id
  "source": "…",                    // the FORMAT this send is written off —
  "source_brand": null,             //   a real email whose shape it borrows.
                                    //   `source_brand` is null for the brand's
                                    //   own; a brand with no library of its own
                                    //   may declare a borrow in
                                    //   email/format-sources.json, and then this
                                    //   names the brand the email came from.
                                    //   The SEND is still this brand's.
  "spent": "…",
  "why": "…",                       // the planner's reasoning, with citations
  "anchored": false,                // pinned to a real date
  "arc_generated": false,
  "affiliate": null
}
```

**Anything resolving a source must read `source_brand`**, not just `source` —
`brands/<source_brand or brand>/email-sms/sends/<source>` (resolved through
brandpath's `email-sms` key, month.py `send_path`). Reading `source` alone
resolves a borrowed format against the wrong brand and silently finds nothing.

`offer: "none"` is a **decision**, not an absence — it means this send
carries no offer, and a consumer must not go shopping in the bank for one.

## The human layer

`review.json` is written only by a person, through the board. The planner
never touches it, so re-planning a month leaves every judgement intact.

```json
{
  "slots": {
    "sep-01": {
      "status": "pending | approved | needs-work | cut",
      "note": "free text for the writer",
      "edits": {"angle": "the rewritten line", "…": "…"},
      "by": "…", "at": "2026-09-13T20:37:28"
    }
  },
  "copy": {"sep-01": {"state": "queued|running|done|failed", "at": "…"}}
}
```

Editable fields: `date · hour · segment · category · type · role · offer ·
product · occasion · angle`. Everything else is the machine's reasoning and
is readable but not editable — an edited `why` would forge the record of why
the send exists.

**Anything that produces work from a month must read the merged view**, not
raw `slots.json`:

```python
import review as R
sends = R.applied(slots, R.load(run_dir))     # edits laid over the plan
```

A consumer that reads `slots.json` alone will write the send the planner
first proposed rather than the one the human approved.

## The library surface (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line)

Besides the run and its folder, a caller may append `machine/` to `sys.path` and use exactly these:
1. **`review`** — `load(run_dir)` → the human layer (`review.json`, or empty); `applied(slots, data)` → the sends with the human's edits laid over the plan (the recipe above).
2. **`brandrecord`** — the brand-record readers, each a pure read of `brands/<brand>/`: `brand_segments`, `offerless_avatars`, `render_types`, `render_offers`, `render_products`, `findings`, `responsiveness`, `cadence_history`, `coldness`, `per_person`; plus `parse_slots(output)` → the slots in a model reply, and `check(slots, month, …)` → the month checker's problems.
3. **`brandrecord.L`** — the language-layer engine handle, re-exported for convenience; new code imports `language_layer` itself.
Everything else in `machine/` is internal and may change without notice.

## The hand-off

The board's "write the copy" button runs whatever `handoff.json` names for
that run, with `{run}`, `{run_name}` and `{slots}` substituted. The planner
plans; something else writes. Changing what writes copy is an edit to that
file, never to this engine.

## The record

`machine/records.py <run_dir>` files one `calendar-run` record to
`platform/data/records/calendar-run/`. Pointers and counts only — no slot,
no angle, no copy. The kind's manifest is
`platform/data/kinds/calendar-run.json`.

## What this does NOT do

It writes no copy, no subject line, no layout, and no image. It plans what
exists and when, and says why.
