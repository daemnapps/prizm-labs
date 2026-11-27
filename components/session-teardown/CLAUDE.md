# session-teardown — recordings in, one testable hypothesis out

**session-teardown** — takes **a brand's visits and session recordings** (PostHog, or a recorded sample), makes
**two lists, every item priced in dollars a month**: the page that loses the most money before checkout, what the
recordings show people doing there (counted), a **fix list** for the team (one element each: friction, words, size,
broken, layout) and **up to three big swings** for the owner (offer, positioning, order, angle — each a full
hypothesis for its own 50/50 test). Does not **build a page, start a test, or write to
PostHog** — the page system does steps 5–7 (page brief → variant → compliance → approval card). Triggered by
`python3 machine/run.py --brand <brand>`.

**Owner:** the owner. **Group:** teardowns.
**Runs by:** person

Direction (the owner, 2026-11-14): the tool downloads the recordings, tears them down and writes the hypothesis, so
the owner only reviews the hypothesis and the variant at approval. Recordings come from PostHog because PostHog
recordings can be downloaded as data; Clarity's cannot (its export gives links and totals only).

Direction (the owner, 2026-11-14, second): the teardown is the recordings plus the page — and a page we built already
carries its brief and section plan, so read that. The goal is how people really move through the page and how to
make more money from it. Small fixes (friction, confusing words, buttons too small or large) are the team's; he
only takes the big swings. Team fixes keep the page system's go-live rule (compliance check + the owner's click,
one click per page batch); a shipped fix is a new version marked control; nothing lands while a test runs.

## Built on the shared teardown pieces (2026-11-14)
the owner: "we have 2 components we should've leveraged to at least source the build of the new component. page
teardown and video teardown leverage similar combined technology here." So this machine owns only what is new to it
(the leak, the PostHog read, the hypothesis contract) and runs on the rest. `machine/shared.py` loads each piece
from its own component:

| Piece | From | Used for |
|---|---|---|
| `run_kit.stage.Chain` | run-kit | every model step: tier, `depends`, free dry run, reuse, `--rerun-from`, prompt as sent (`<step>--sent.md`), output (`<step>--<label>.md`), `run.json`, `deliver()` into `deliverable/`, the creative QC loop after each step |
| `run_kit.prompts`, `filing`, `claude_flags` | run-kit | highest `-vN-` wins, `runs/<tool>/<brand>/<label>/`, the registry's chain model |
| `hold()` gates, `unfilled_check` | marketing-chain-checks | the **inputs** gate (fewer than 5 recordings of visitors who left) and the **delivery** gate (the hypothesis contract, no UNFILLED note); both write `check.json` |
| `structure` prompt, `capture.py`, `chain_io.pull_json` | page-teardown | the page under test read into sections, with page-teardown's own prompt (never copied); a page-chain teardown of this control already on file is used instead, no model call |
| the frame map's shape | video-teardown (`machine/framemap.py`) | each recording read as shots (one page each) and moments (`{t, does}` rows), `moments/moments.json` + `MOMENT-MAP.md` |
| `chain_page.CSS` | page-production | the run page looks like the page chain's run page |

Still its own: `leak.py` (where the money leaks), `source.py` (PostHog and the sample), `record.py` (the hypothesis
contract and the fix list), `sections.py` (build record or structure → depth bands), `timeline.py` (events →
moments), `friction.py` (rage, dead and repeated taps counted per element), `money.py` (each finding's dollars a
month), `page.py` (the run page).

## Steps
Declared once in `machine/run.py` `STEPS`:
1. **leak** (code) — `machine/leak.py`: per landing/cart page, visitors and who left there (their last page before
   leaving without reaching checkout), priced as lost visitors × revenue per visitor who reached checkout. Pages under
   the `min_visitors` floor are listed, not ranked. The top page with no running test is chosen (or `--page-id`).
2. **pull** (code) — `machine/source.py`: the newest 30 recordings of visitors who left and 10 who reached checkout,
   each with at least 5 active seconds. The inputs gate holds a run with fewer than 5 who left.
3. **structure** — the page under test as sections, first hit wins: the page's own **build record** (the page-chain
   run that built the control version: its `page.json`, every section's job and our words, and its brief, job and
   hypothesis), a page-chain teardown of the control, else page-teardown's structure prompt run here.
   `machine/sections.py` turns them into depth bands (each section's share of the page from its words, pictures and
   button: an estimate, and the page says so), so a scroll % reads as "furthest §6 offer box".
4. **teardown** — `machine/timeline.py` reads every recording as shots and moments, naming the deepest section
   reached; code counts how far each group got and what fought back (`friction.py`); prompt `teardown` names the
   findings and sorts each into **fix** or **swing**; `money.py` prices each (gap between leavers and buyers × lost
   visitors × value of a checkout, a month; an upper bound for ranking, never a forecast). → `fixes.json`.
5. **hypothesis** — prompt `hypothesis` writes up to three big swings from the swing findings; each is a full
   hypothesis record, ranked by money → `swings/swing-N/hypothesis.json`. `hypothesis.json` is swing 1 until the owner
   picks: `python3 machine/run.py pick <run folder> <N>`. The delivery gate checks every record.

## The four questions
- **Engine + owner:** `machine/`, the owner.
- **Definitions + curator:** `prompts/` (one file per step, `-vN-`, highest wins) and `definitions/stop.json`
  (the stop point every test carries, and how many recordings a teardown reads), the owner. The structure prompt is
  page-teardown's, curated there.
- **The plane it emits:** `runs/session-teardown/<brand>/<label>/` — leak.json, picked.json, source/page.txt,
  structure.json, timelines/, moments/, every prompt as sent (`<step>--sent.md`) and output (`<step>--<label>.md`),
  teardown.json, **hypothesis.json** (and `deliverable/hypothesis.json`), check.json, run.json, page.html (prompts
  and outputs readable). Records adapter: none yet; the shared runs filer reads the standard shape.
- **Manifest per entry:** `run.json` (run-kit's record: tool, brand, label, assignment, every step's status,
  prompt, prompt hash and model; plus page_id, page map, reach counts, patterns, state) and `hypothesis.json`.

## The contract: hypothesis.json
Agreed with the page system 2026-11-14 (its intake: `briefs.py page --hypothesis <file>`). Shape and checks in
`machine/record.py`: id, kind "hypothesis", page_id, type design|offer, control {version, path, offer},
variant_offer, hypothesis, change, primary_metric checkout_reached, confirm_metric purchase, stop, evidence {leak
{step, visitors, reached_next, revenue_per_visitor, window, source, device}, recordings {left, converted},
patterns [{pattern, left, converted}], clips ≤3 [{recording_id, at_s, note, replay?}], clarity|null}, by {tool,
prompt, model, at}, status "draft"; and for a big swing rank 1–3, value_usd_month, basis. A record that breaks the contract is written, held at the delivery gate
(check.json), marked refused in run.json, never copied to deliverable/, and the run exits non-zero.

## The fix list: fixes.json
Shape agreed with the page-system session 2026-11-14 (its page-change intake: a page brief with job "new-control"
builds vN against the control named here; it goes live on a compliance pass and the owner's dated click — the owner,
2026-11-14: the team's approver is not a separate person — then becomes the control; refused while the page has a
test draft or live, once the control has moved, or for an archived page). id `<page_id>_fix-<YYYYMMDD>-<n>`, kind
"fix-list", page_id, control {version}, fixes [{id f1…, what, where {section_job, section, selector?}, why {pattern,
left, converted, clips}, value_usd_month, basis, type copy|design|bug|speed, effort s|m|l}], evidence (the same
block as the hypothesis), by, status "draft". Checks in `record.check_fixes`. run.json `fix_state` says "queued" while
a live test is on the page.

Each big swing is the hypothesis contract plus rank 1–3, value_usd_month and basis (agreed the same day).

## Keys and models
- PostHog, by name through `components/keys/loader.py`: `POSTHOG_PERSONAL_API_KEY` (read-only: query +
  recordings), `POSTHOG_PROJECT_ID`; `POSTHOG_HOST` optional (default US). Only reads are sent.
- Models by tier, each a `components/models/models.json` id (`run.py tiers()`); every step is a designs step, the
  registry's chain model (`run_kit.claude_flags.model()`), called through run-kit (`claude_door`).

## Samples
`samples/basic/` is a RECORDED SAMPLE, made up (fictional brand "sample"), rebuilt by `samples/make_sample.py`. It
carries its own `pages.json` and the offer page as captured text (`pages/<page_id>.txt`) so it needs no real page.
Its "See reviews" link leads nowhere, so some taps on it do nothing (a fix the run should find). Use it until live
recordings exist: `--sample basic`. `runs/session-teardown/sample/sample-chain-3/` is the sample run with fixes and
swings in the agreed shapes; `sample-chain-2/` (fixes before the shapes were agreed), `sample-chain-1/` (one hypothesis on the shared chain) and `sample-full-2/` (the first build) are kept as
they were.

## Tests
`/usr/bin/python3 tests/test_session_teardown.py` — no network, no model (a fake model answers).

## Proposed to the shared components (not changed from here)
- **run-kit:** a step may name its own prompts folder (`"prompts": <dir>` in STEPS), so a chain can run another
  component's prompt without the swap in `run.py run_step()`; reuse keyed on the prompt AS SENT (page-teardown's
  `chain_io` does this with `sent_sha`) as well as the prompt file, so a rerun under the same label never keeps an
  output whose inputs changed; `model.TIERS["reads"]` is `claude-haiku-4-5-20251001`, which is not a registry id
  (the registry has `claude-haiku-4-5`).
- **page-teardown:** declare `chain_io.pull_json`, `capture.capture` and the `structure` prompt as its public
  surface (callers today: page-writing, page-production, this); a teardown run of a page we own carries the page id
  and `job: control-read` without opening a page brief, so other machines can find it.
- **page-production:** split `chain_page.py`'s stage block out as `stages_html(run_dir, stages)` that reads both
  `chain_io` and run-kit `run.json` shapes, so every chain's run page shares one block, not just the CSS.
- **video-teardown:** lift the frame map's shot/moment document and its `markdown()` into a shape any time-based
  reader can fill (video by pixels, recordings by events), so this machine fills it instead of matching it.

## Not yet
- Button sizes measured on the page (the design-audit skill measures tap sizes; not wired in). Size findings come
  only from what visitors did (taps that miss, repeated taps).
- `--source` / `--device` slices (the record carries "all" today).
- Clarity totals in `evidence.clarity` (null today).
- A records adapter for the platform.
