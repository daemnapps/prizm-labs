# Autonomy pilot

Local, brand-agnostic workflow experiment. It preserves review of scripts,
storyboards, image drafts, email drafts and finished assets while code handles
state, local handoff packages and operator returns. No publisher is connected.

## Run

From the repo root, with Python 3.9+:

```sh
python3 -m unittest discover -s tools/autonomy-pilot/tests -v
python3 tools/autonomy-pilot/pilot.py --root runs/autonomy-pilot serve --synthetic
```

Open http://127.0.0.1:8917. Load synthetic examples. Approve or send back each
stage. Preparing the next draft and packaging a handoff run automatically while
the server is running. This is a local trial screen, not a replacement for an
existing production approval page. The machine must stay awake.

The connection form writes only `TYPESAFE_API_KEY` into this checkout's ignored
`.env`, preserving other entries and setting file mode 0600. If this checkout’s `.env`
is a symlink to a canonical local Prizm `.env`, the form updates its target
and preserves the link. It makes no API
call. Never put the key in a command argument, a tracked file or chat.

## Levels

| Mode | Automatic work | Review |
| --- | --- | --- |
| observe (default CLI) | None; record state | Every required artifact |
| prepare | Call registered draft adapters | Every required artifact |
| handoff | Also package approved drafts and ingest matching returns | Every draft and finished artifact |

Video: script → storyboard → image draft → operator production → finished asset.
Image: image draft → operator production → finished asset.
Email: email draft → image draft → operator production → finished asset.
The image draft stage in the synthetic demo is a text placeholder, not a generated image.

Approvals bind to artifact bytes and workflow revision. Revising an earlier
stage removes its approval and every downstream artifact/approval. In-flight
handoffs become superseded. Model output is never an approval event.

## Operator contract

`outbox/<handoff-id>/manifest.json` and `artifacts/` are local packages. No message,
Drive upload, access grant or external assignment is sent. A transport adapter
must deliver only a pending package with an idempotency key and delivery receipt.
Copying a folder is not evidence that an operator received it.

An operator places the completed file in `returns/<handoff-id>/` with:

```json
{"handoff":"<handoff-id>","file":"finished.html"}
```

Use `.html` or `.eml` for email, `.png/.jpg/.jpeg/.webp` for an image, `.mp4/.mov`
for video. The server checks the matching active handoff, nonempty bytes and
file extension, stores an immutable snapshot and stops at final review. These
are transport checks, not codec validation or visual quality judgment. An
existing lane's media checks must pass before any production cutover.

`tick` ingests matching returns without a web server. Duplicate event IDs have
no repeated effect; reuse with changed input is refused. SQLite transactions
serialize state changes. Run one worker/server per output directory; this pilot
does not yet provide distributed job leases or paid-execution crash recovery.

## Jev comparison

```sh
python3 tools/autonomy-pilot/pilot.py --root runs/autonomy-pilot evaluate
python3 tools/autonomy-pilot/pilot.py --root runs/autonomy-pilot evaluate --live --max-usd 1
```

The first command is free. The second calls Jev on **15 bundled synthetic
feedback examples only**, with the caller's Typesafe key through the existing
`components/keys/loader.py`. Pinned model: `jev-1.14.0`. No screenshots, media,
private source files or brand records leave the machine.

Each attempt reserves the maximum standard 64k-context input charge ($0.002688
at the documented $0.042/M rate) before sending, even on failure. All reservations
remain charged against the chosen output store's cumulative cap. Fifteen attempts
reserve at most $0.04032. No retries or auto-top-up; limit must be at most $1.
Reusing this output directory preserves the allowance across restarts. A new
output directory is a new budget; operators must not use that to evade a limit.
Recheck price/context limits before changing the model or enabling extended context.

Results in `jev-results.json` include correct/answered/routed counts, every
probability distribution, observed call times, known estimated usage and worst-case
reserved charges. Failure messages omit provider bodies and credentials. The
baseline always routes to review. This smoke test does not claim superiority over
the current generative classifier or establish production accuracy. That comparison
requires labeled representative examples, development/holdout splits and actual
operator correction effort. The example 0.85 confidence cutoff is not calibrated.

## Integrating existing tools

`Store.tick(handlers)` takes a registry keyed by `(lane, stage)`. A handler receives
the job and returns a file path; it cannot approve the result. Use `adapters.run_kit_handler(chain_factory, step_key, fields)` to wrap existing
`run_kit.stage.Chain.run` stages, or supply a lane-specific callable. The integration
test exercises the actual run-kit with its offline model seam. The opt-in creator adapter below registers one existing writing stage. Other generation handlers remain disconnected.
The synthetic flag registers local fixture writers only for demo jobs; connected creator jobs cannot fall through to them.

Existing seams reviewed:

- `components/run-kit/run_kit/stage.py`: retains generation, prompt caching and receipts.
- `components/naming/stages.json`: overall vocabulary; pilot review stages are finer-grained local steps.
- `components/ad-handoff/take_back.py`: existing return ingestion; a future adapter must honor its manifest and ledger instead of duplicating its production state.
- `components/meta-upload/to_check.py`: existing final review-card writer; never write `card.approval` from a worker.
- `tools/email-production/adapter/adapter.py`: existing email observation/revision entry points; keep production identities and deployment separate.

This component writes no existing production approval records. The next integration
is one reviewed generation adapter plus one local-to-existing-card adapter, tested
against fixtures before connecting external delivery. Human reviews should remain
in the existing production UI once those adapters are proven.

## Local trust and limitations

Loopback bind, Host/Origin checks and a per-process request token prevent ordinary
cross-site requests. They do not isolate hostile local processes. Roles are
library arguments on a trusted single-user machine, not authenticated identities.
Do not expose this server through a tunnel or share the output root with workers
that must not be able to approve. Multi-user deployment requires authentication,
role enforcement outside the worker, job leases and verified delivery adapters.
Uploaded HTML is previewed as text, never executed beside approval controls.
The browser does not render binary media yet; use existing lane review surfaces
for real visual approvals. All persistent run data belongs under an ignored root.

## Sources

API/model documentation checked 4 November 2026:
[typed API](https://docs.typesafe.ai/api/system-one),
[model and pricing](https://docs.typesafe.ai/models),
[confidence](https://docs.typesafe.ai/confidence).

## Historical feedback comparison

`compare --cases <local.json>` validates a frozen labeled dataset without calling a model.
Add `--live --max-usd 1` to evaluate it on the unchanged decision policy and cutoff.
Each case contains `id`, `feedback`, `context`, `expected`, `source` and `label_basis`.
The dataset declares `label_status` and `limitations`. Only feedback and context go to
Typesafe; labels and recorded fixes do not. The report preserves the dataset hash.
Run data and source excerpts remain in the ignored output directory.

The existing email `redo()` function stores every note as a standing rule. The baseline
is a policy replay of that behavior, checked against its AST and source hash. It is
not a current generative classifier, and applying it to creator feedback is a
cross-workflow comparison. `send_back()` is a separate append-only note path.
The pilot never invokes either production function or writes to their stores.
A historical convenience sample and analyst labels cannot establish production accuracy.
A completed or interrupted comparison is not overwritten or silently retried.

## Connected creator-brief chain

```
python3 tools/autonomy-pilot/pilot.py --root runs/autonomy-pilot connect-creator --inputs <local-inputs.json> --run
python3 tools/autonomy-pilot/pilot.py --root runs/autonomy-pilot serve --creator --creator-provider codex --synthetic
```

The input JSON has `fields` for the variables requested by the existing
`tools/video-writing/prompts/stage-7b-page` prompt, `script` containing the already
written spoken lines, and `provenance` explaining where they came from. It pins and
hashes both the inputs and the resolved prompt. Missing inputs stop before spending.
No new writing prompt is introduced. This connects stage7b, not the full upstream
teardown, injection and script-writing pipeline.

Creator lane: brief plus supplied script → human script review → local creator
handoff package → returned video → final human review. It follows the creator
brief's words-only format. The AI-video lane still requires storyboard and image reviews.
The first live exercise uses a documented historical brief; it is not a new campaign.

Send back regenerates the concept for that revision with the correction, without
promoting it into a standing rule. The supplied script remains unchanged. To change
spoken lines, supply revised script inputs as a new job. Jev stays advisory until
representative evidence supports routing; it does not block a reviewer-requested edit.

Generation uses the personal machine's Claude CLI in safe mode, with no model tools,
MCP servers, session persistence, repository context, API-key loader or account
fallback. A failed or interrupted attempt is held without an automatic retry.
A durable claim and input hash prevent repeat refreshes from buying another draft.
A prompt or input change requires a new job. Each attempt reserves $0.10 in the same
cumulative $1 ledger as Jev, with the CLI's own $0.10 limit. Reported Claude usage cost
may be covered by a subscription; it is not a verified cash charge. Budget exhaustion
holds preparation while completed drafts remain reviewable.

The adapter uses the existing run-kit prompt resolver, not the production runner
that also touches shared systems. Automatic creative QC is not invoked through that
runner. This is a local generation/review integration, not production readiness.
Human review, lane media checks, authenticated operator delivery and distribution
remain separate. Neither approval nor handoff sends a Google Doc or message.


### Explicit Codex plan fallback

Use `connect-creator --provider codex` or `serve --creator --creator-provider codex`
after the owner chooses the existing Codex login. This selection is explicit;
Claude failures never switch accounts on their own. The CLI forces ChatGPT login,
removes API-key environment variables, ignores user configuration, uses a temporary
read-only working directory, disables shell/apps/browser/multi-agent tools and hooks,
and accepts only a completed text turn. No new account or API key is created.
Five Codex plan attempts are allowed per pilot store, including interrupted calls;
each revision still has one durable attempt. Plan usage is recorded separately
from the cumulative $1 API reserve and is not reported as a zero cash bill.

Reference: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
