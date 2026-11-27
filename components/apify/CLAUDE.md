# components/apify — the Apify layer and the doors that use it

Owner: **the owner** (engine and definitions both).
Extracted 2026-09-22 from two personal lab folders (the LL-1 precedent).

## Why it exists

`components/research-gatherer/` loaded its Apify layer from
`components/swipe-organic/apify.py` and its Reddit door from
`lab/the owner/control-room/tools/reddit.py`. Two consequences, both found the
same day:

1. A **production component depended on one person's lab folder** — the exact
   coupling components rule 2 forbids, pointed the other way.
2. The **public copy could not run at all.** Neither lab path ships to the
   open-source repo, so `research-gatherer` there resolved a path that does
   not exist. The failure surfaced as `[UNFILLED: room discovery failed]`,
   which reads like an empty result rather than a missing dependency.

Both old locations now re-export this folder, so every existing caller — a
dozen lab tools and two components — is unchanged.

## The four new-resident questions

- **Engine + owner.** `apify.py` (token, spare-account fallback, 403/408
  handling, the actor ids) and `reddit.py` (the Reddit door: search, the
  three non-optional actor settings, `reddit.md` + `reddit.json` out).
  Owner the owner.
- **Definitions + curator.** The actor ids and the settings found the hard
  way, in the files themselves. Curator the owner.
- **The plane it emits.** None. Every caller passes `--out`; the door writes
  into the CALLER's folder, never inside this component.
- **What the manifest declares.** No manifest — this is an engine, like
  `gdrive-creator/`.

## The contract

- `apify.token()` → the key, from the environment first, then
  `~/.upright-keys.env` through the one key loader (`components/keys/loader.py`). **It reads no other tool.** It used
  to import `components/video-teardown/machine/keys.py`, which broke wherever
  that tool was not checked out beside it.
- `apify.run(actor, payload, timeout=900)` → rows, retrying once on
  `APIFY_TOKEN_PERSONAL` when a 403 says the allowance is spent.
- `apify.run_async` moves to the next account the same way when one is spent.
- `status.py` prints each account's used, limit, room and cycle end. It reads only.
- `reddit.py --out <dir> --queries ... --limit N` → writes `reddit.md` and
  `reddit.json` into `<dir>`. A failed read still writes `reddit.md` carrying
  the reason, so a caller never reads a stale file and never sees an empty
  directory with no explanation.

## Two things a caller should know

- **403 means spent, not broken.** A used-up allowance answers 403 to
  everything and is indistinguishable from a bad token until you read
  `api.apify.com/v2/users/me/limits`.
- **408 means the actor was slow**, not that the token or the account is
  wrong. Check the account before changing any wiring.

## The TikTok kit — `tiktok.py` (2026-09-23)

Four actors from one maker (unseenuser), one door, on the owner's word: trends
(Trend Hunter), shop (TikTok Shop: products, sales, reviews, a creator's
showcase), creator (every video a profile posted, + transcripts), sound (a
sound's details — including `user_count`, how many videos use it — and the
videos). Every run prints its price ceiling first and is capped there with
Apify's `maxTotalChargeUsd`; `--dry-run` stops before spending; rows land in
the caller's `--out`. All four proven live 2026-09-23 (runs/tiktok/test-20260923/).
