# Prizm → social distribution connector

Working local connector, Python standard library. Takes an existing Prizm
`meta-card/1` delivery and a selected named MP4; creates durable publication
jobs for explicit brand accounts; submits through GeeLark only when explicitly
executed; exports results with the original brief and asset references.

This first release is a trusted **single-operator CLI backed by SQLite**.
It is the first local slice of the proposed operations platform, not the
hosted, authenticated multi-client service or phone dashboard. Scope checks
prevent accidental mixing; anyone with direct database/CLI access is trusted.
PostgreSQL, hosted storage, authentication and always-on workers remain later
deployment work. There are no background watchers or scheduled processes.

## Try it without accounts, tokens or paid calls

From this directory:

```sh
python3 -m unittest -v test_prizm_connector.py
python3 demo_connector.py --out ../../output/social-connector-demo
```

The demo requires local `ffmpeg` and `ffprobe`. It creates a one-second video,
two synthetic brand deliveries, four **approval-pending** jobs, JSONL receipts,
and mobile-readable static HTML snapshots under the chosen private output
directory. Re-ingestion is exercised and adds no duplicate jobs. Demo accounts
are not marked ready. No content is published and no network request is made.

## The actual Prizm integration

The input is the `card.json` already emitted by video-edit's delivery station,
`to_check.py`, or a creator delivery feeder. The card contains brand, product,
brief number, named media and `made_by` references. The connector reads that
format without importing, changing or copying the upstream machines.

Select **one** listed `<unit>_asset-NN.mp4` per handoff. Every target gets one
publication job. Other formats, carousels and remote media fetching are not in
v1. The file is hashed and copied into private connector staging. No naming
value, caption, title, account or schedule is invented. `--ledger` optionally
checks the exact asset/brand/product/brief against an existing Asset Ledger in
read-only mode. Its current single-writer database is never altered here.

The delivery card's Meta approval is **not** social publishing permission.
The connector creates a separate approval for the exact media and publishing
instructions. Upstream disapprovals and explicitly failing checks block intake.
Source checks are a snapshot; upstream revocation monitoring is not connected.
Revoke an ingested handoff with `cancel` if upstream approval changes.

## Register accounts, then hand off a delivery

Use a private state location. The examples use synthetic identifiers. The
platform account ID is its stable platform identity; the GeeLark phone ID is
the corresponding cloud environment. Passwords and tokens never go in either.

```sh
python3 prizm_connector.py --db ../../output/social/state.db account \
  --workspace owner-a --brand brand-a --id instagram-main \
  --platform instagram --platform-account-id 123456789 --phone-id 987654321
```

Account bindings are immutable. Re-registering the same binding is harmless;
changing identity, brand, device or credential reference requires a new
explicit binding ID. A platform identity cannot be registered under two brands.
New accounts start paused. A local operator attests login, proxy/device mapping,
publishing eligibility and account defaults with `ready --account … --actor …`.
That is an operator assertion, not an automatic identity verification service.

The publishing instructions are a JSON list, one entry per selected account:

```json
[
  {
    "account_id": "instagram-main",
    "caption": "The exact approved caption from the existing workflow.",
    "title": "",
    "schedule_at": "2026-11-01T12:00:00+07:00",
    "ai_disclosure": true
  }
]
```

`ai_disclosure` is mandatory; the connector never silently chooses false.
Instagram maps it to `aiTag`; YouTube maps it to `isDisclosureMandatory`;
TikTok maps it to `markAI`. These request fields were checked against the
official documentation, including the browser-rendered TikTok reference.
TikTok's `maxTryTimes` is explicitly zero so provider retries do not bypass
the connector's uncertain-submission handling. Visibility and other app
defaults are not controllable through this v1 contract; validate them on the
actual account. Public visibility is never assumed or claimed in receipts.

```sh
python3 prizm_connector.py --db ../../output/social/state.db plan \
  --workspace owner-a --card /private/delivery/card.json \
  --asset brand-a_product-a_brief-0001_batch-2026-10-19-a_asset-01.mp4 \
  --targets /private/targets.json
```

`plan` checks the contract and prints the exact manifest and fingerprint. It
creates no jobs and makes no provider calls; opening a new database initializes
its empty schema. Replace `plan` with `intake` to stage media and create jobs.
The same source and instructions return the existing batch. Changed instructions
or media are refused under that source key. Use `--request-key revision-2` for
an intentional new version or repost; it requires its own approval.

```sh
python3 prizm_connector.py --db ../../output/social/state.db approve \
  --workspace owner-a --brand brand-a --batch batch_FROM_INTAKE \
  --fingerprint EXACT_FINGERPRINT_FROM_PLAN --actor owner
python3 prizm_connector.py --db ../../output/social/state.db ready \
  --workspace owner-a --brand brand-a --account instagram-main --actor owner
python3 prizm_connector.py --db ../../output/social/state.db dispatch \
  --workspace owner-a --brand brand-a
```

The last command is a **network-free preview**. Only `dispatch --execute`
contacts the provider and can publish/spend. Use it only for the reviewed real
asset and mapped account. Live mode validates the staged file using `ffprobe`.
The first version limits files to 100 MiB; upstream still owns creative/media QC.
The provider defaults and each account's platform eligibility need a real pilot.

Tokens are read from the named environment variable, default
`GEELARK_API_TOKEN`, or an explicitly supplied private `--env-file`. Other
connections may use distinct environment-variable names. No raw provider
messages/payloads, credentials or temporary upload URLs enter the receipt log.

Only jobs within 30 seconds of their target time are submitted. Jobs more than
15 minutes late become blocked rather than flooding accounts after an outage.
Run dispatch yourself when due; this release installs no scheduler. Paused
accounts do not dispatch. One unresolved task holds that device/credential
combination. Mutations are serialized by a local process lock; do not share
this SQLite database across hosts or network filesystems.

## Reconcile and return receipts to Prizm

```sh
python3 prizm_connector.py --db ../../output/social/state.db reconcile \
  --workspace owner-a --brand brand-a --execute
python3 prizm_connector.py --db ../../output/social/state.db export \
  --workspace owner-a --brand brand-a --out ../../output/social/results.jsonl
python3 prizm_connector.py --db ../../output/social/state.db report \
  --workspace owner-a --brand brand-a --out ../../output/social/receipt.html
```

`reconcile` also previews unless `--execute` is supplied. Export is a receipt
outbox for an upstream adapter; it does **not** silently write into the Asset
Ledger or mark a creative brief live. Each receipt has a stable event ID for
consumer deduplication, workspace, brand, product, scoped brief key, asset ID,
media hash, source tool/run, account, publication job, provider task ID and state.

Provider completion is recorded as `provider_completed`; `live_verified` stays
false. A reported sharing link is preserved only for the appropriate platform,
with query/fragment removed. Automatic post identity/visibility verification,
analytics, sales attribution and financial cost allocation are not implemented.
The provider's `cost` field is stored as **duration in seconds**, not dollars.

An interrupted or uncertain submission becomes `needs_reconciliation` and is
never automatically uploaded again. If the task ID was lost, use `attach-task --execute`
after locating the correct attempt in GeeLark: it checks the task's device and
records the operator's identity. Matching the task to the exact intended asset
is still the operator's responsibility. Provider task polling never resubmits.

`cancel` revokes approval and cancels unsent jobs. Submitted work retains its
actual state: remote cancellation is not implemented. `pause` prevents new
dispatches on an account. Blocked upload/schedule jobs remain visible for an
operator to resolve; there is no automatic retry, budget limit or spending cap
in this initial connector.

## API references checked

- [Official GeeLark documentation](https://github.com/GeeLark/geelark-openapi)
- Instagram: `/open/v1/rpa/task/instagramPubReels`
- YouTube Shorts: `/open/v1/rpa/task/youtubePubShort`
- [TikTok video task reference](https://open.geelark.com/api/task-add):
  `/open/v1/task/add`, task type 1; `markAI`, `maxTryTimes`, `planName` and
  `remark` checked in the live browser-rendered documentation.
- Upload: `/open/v1/upload/getUrl`; this connector requires HTTPS upload URLs.
- Status: `/open/v1/task/query`; execution timeout 20003 remains uncertain.

The tests exercise safety and durability with synthetic brands and stubbed
providers. They establish local behavior, not live account readiness or API
acceptance. A real asset/account pilot is still required before unattended use.
