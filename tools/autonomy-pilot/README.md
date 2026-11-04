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
`.env`, preserving other entries and setting file mode 0600. It makes no API
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
test exercises the actual run-kit with its offline model seam. Real-generation handlers are deliberately not registered by this pilot.
The synthetic server registers only local fixture writers.

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
