# components/review/seed/ — three seed requests, one per pilot lane

Written by RV-1 (review kind manifest). Each file is a complete `review`
record body in the plane's own envelope (`schema`, `kind`, `reviewer`, `item`,
`verdict`, `notes`, `created`, `via`) — the shape
`platform/data/records/review/<ts>--<reviewer>--<item>.json` takes — so RV-2
(review request module) can file one byte-for-byte and RV-6 (reference panels)
can render one without a live plane.

**These are SEEDS, not live requests.** Nothing here has been filed to
`platform/data/records/review/`, no reviewer has been asked, and the
`on_accept` on the dev-qc seed is illustrative — RV-3 (on_accept adapter) owns
what that shape means and is the only thing that acts on one.

| File | Lane | Type | Warehouse | Close-rule half |
|---|---|---|---|---|
| `RQ-20260908050542-Brand A-flex-upgrade-copy.json` | `email-sends` | `md` | `repo` | auto (one reviewer, no `on_accept`) |
| `RQ-20260908050542-qg2-calibration-writeup.json` | `dev-qc` | `md` | `repo` | explicit (two reviewers **and** an `on_accept`) |
| `RQ-20260908050542-Brand B-nyc-r3-seedream45.json` | `static-ads` | `image` | `blob` | auto (one reviewer, no `on_accept`) |

Between them the three cover both branches of the close rule, both md and
image panels, and the `media` inventory the manifest declares in
`media_inventory`.

## Every pointer resolves, and here is where each came from

- **email-sends** — `brands/Brand A/email/sends/2026-04-11--most-upgrades-cost-hundreds-this-one-doesn-t.md`,
  filed before the v6 layout (d20151bec, 2026-09-30) renamed `email/` to
  `email-sms/`; the file is now
  `brands/Brand A/email-sms/sends/2026-04-11--most-upgrades-cost-hundreds-this-one-doesn-t.md`.
  The seed is append-only and keeps its ref; it resolves through the brandpath
  alias (`brands/<brand>/FOLDERS.json`), which is how test_rv1_manifest.py checks it.
- **dev-qc** — `new-workflow-design/builds/qc-gate-runner/2026-08-24-QG-2-calibration.md`,
  a real path in this repo.
- **static-ads** — a **blob** pointer, and the record says so. The RV-1 card
  carries a lead flag on exactly this: batch 54 asked for "a Drive image from
  an existing the editor-ai-gen round", but the the editor-ai-gen rounds on the plane store
  blob/CDN urls and **no Drive file ids**. Verified again here —
  `platform/data/records/visual-run/20260820T163222Z--mini-worker-import--Brand B-nyc-1.gen.r3.json`
  carries `images[].durable_url` on `*.public.blob.vercel-storage.com` and no
  Drive id anywhere. The ref, `bytes` and `type` on this seed are copied from
  that record's `images[0]`. The lead's flag names a blob pointer, declared as
  such, as in-rule; it is also the warehouse the developer's 2026-09-08 ruling assigns
  to a machine output, since Drive holds human-authored creative and video.

**The Drive path is documented but not seeded**, deliberately: the one
Drive-backed image inventory on the plane is `teardown-runs`
(`20260827T103328Z--mini-worker--kzn-03-three-surgeons.json`,
`verdict.media.files[]` — 74 rows, all with Drive ids), and a review request
pointing at a video-teardown frame would have to invent a fourth pilot lane
while leaving one of batch 54's three named lanes unseeded. The row shape for
that case is spelled out on the `media` field in the manifest and cited in the
static-ads seed's own note, so RV-4 (media route per-kind) has both shapes in
front of it.

**Not verified from this worktree:** the blob url and the teardown Drive id
were read out of committed records, not fetched — the maker run had no network
grant. Both are live plane records; if either has since been reaped, the seed's
ref is stale and the fix is to re-copy from the current record, not to change
the grammar.
