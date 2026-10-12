# components/keys — context

A proposed component for managing keys and env files. It holds the **names**
of every key and never a value. Status: **proposal**. The folder was created
on the developer's word on 2026-09-29. The lead filed its CLAUDE.md as PROPOSED from
the `HANDOFF.md` draft (6c3048c14). The first piece is the shared psql
helper, `pg_argv.py`, being built under WM-108b (other argv sites). Written by
◆ PLAN · dev-developer, read from `a170788df`. The plan-file record is batches
504–519 of `team/plans/dev-developer.md`.

## Review these first

Open each file in a browser. Each is a copy of a published page, with
placeholders only.

| # | File | What it shows | Published page |
|---|------|---------------|----------------|
| 1 | `plans/1-impact-on-damon.html` | What changes for the people using keys, told through the owner's real tasks and key names | the owner's Key Map |
| 2 | `plans/2-component-view.html` | The component in the atlas's shapes: its place on the chain, its contract, one trace | Keys on the Atlas |
| 3 | `plans/3-implementation-plan.html` | Every kind of key, how files move, the rotation list, the rollout phases, decisions | Team Key Ring |

## The model, in six lines

1. **Company accounts, personal keys.** Each paid service has one company
   account and one bill. Each holder (a person or the Mac mini) gets their
   own key under it, so usage shows per holder.
2. **One layout everywhere.** A names-only template in git sets which
   variables exist. Every machine's file follows it; only the values differ.
3. **A managed file beside each person's own setup.** The managed file is
   built and sent by the ops lead or Operator B, replaced whole, and never edited.
   Everything else is the person's own setup: a personal file, the Keychain,
   several files, anything. It is **not checked** (the developer, 2026-09-29). Checks
   start only when work enters the system path. The mini loads only its
   managed file.
4. **Admins run it.** the ops lead and Operator B are admins on every company
   account, with two-factor sign-in. They create keys, build each file and
   send it securely. the developer owns the accounts and billing.
5. **Brand keys go by job.** Sync keys stay in the sync pipeline's secrets.
   Reading brand data uses a read-only database login per person. Acting on
   a brand system (send, upload) uses a per-brand key on the mini, or a
   narrow key for someone who does it often.
6. **Supabase first.** Data a dashboard, a teammate or an agent would use
   again routes through Supabase. That also bounds what Claude reads: a few
   prepared tables, with `public.orders` (MET-C11 (orders chain)) as the
   model, not each vendor's whole API.

## Decisions

| | Decision | Status |
|---|---|---|
| D1 | How files are sent securely, and whether admins keep a copy | **Open.** Decide before the first files go out. Without a kept copy, changing one key means collecting every other key in that file again. |
| D2 | A managed file beside each person's own setup | Answered yes by the developer, 2026-09-29, reconfirmed 2026-09-30. **FILED in the decision log 2026-09-30** (the developer, typed to the lead ~01:00Z). |
| D5 | Personal setups are not checked. `/system-fit`, `/system-ready` and `/system-review` check and migrate keys when work enters the system path. Always on: the walls, the mini on its managed file only, and announced revocation dates | Answered yes by the developer, 2026-09-29 ("update the three documents accordingly"). **FILED in the decision log 2026-09-30** (the developer, typed to the lead ~01:00Z). |
| D3 | **Generalized, the developer 2026-09-30:** a key is personal only when it matters who used it (spend, accountability, reach, or it acts as the person) AND that is worth more than it costs (seats or accounts, plus create/rotate/revoke per person). Otherwise it is shared at the account's natural edge: per brand, per machine or service, or one for all of the team, with a named owner and a spend cap. Personal today: Higgsfield, fal, OpenAI, Gemini, OpenRouter, Apify, the read-only database login. Shared: ElevenLabs (with a quota), brand systems, sync, Drive, the Slack bot, the full database login. Vercel and Figma: one token with a named owner. Spend line: deferred by the developer, 2026-09-30 ("ignore this for now"); decide per service meanwhile | Answered by the developer, 2026-09-30. **FILED in the decision log 2026-09-30** (the developer, typed to the lead ~01:00Z). |
| D4 | the ops lead and Operator B as admins, the developer as owner, two-factor on all three | Answered yes. **FILED in the decision log 2026-09-30** (the developer, typed to the lead ~01:00Z). |
| — | A component for key management | Proposed by PLAN; the developer asked for this folder. Not yet carded. |

D2–D5 are in the decision log (2026-09-30, the developer typed to the lead). D1 is
still open.

These answers changed earlier rulings (superseded in the same entry):
- **2026-08-24:** "the mini holds the only key copy" (D3).
- **I-101 (secrets stack), open since 2026-09-05:** "no password manager on
  the mini". Settled by the file model.
- **R1 of 2026-09-27:** "Keychain later". Dropped, because Keychain fails on
  the mini after a reboot.

## Component scope

- **Holds:**
  - the loader: the person's own environment first, then gaps filled from
    the managed file, with a warning when a personal key overrides a company
    one; during the transition, a fallback to the old locations
    (`~/.gemini.env`, `~/.apify.env`, the owner's Keychain helper)
  - the template
  - the register: name, vendor, holder, kind, scope, last rotated, next due
  - checks: a file against the template (names only); no key in a command
    line; every template name hidden from the worker's jobs
  - a records adapter for check results (names only)
- **Owners (component rule 6):** Operator B owns the engine (loader and
  checks). the ops lead owns the definitions (template and register) and approves
  every change.
- **Never holds:** a key value; the per-job grants, which stay in the
  worker's `job_env.py`; the delivery method (D1).
- **Why now:**
  - there are four loaders today: the worker's `load_env_file`,
    `components/audio-teardown/keys.py`,
    `tools/video-teardown/machine/keys.py` and the owner's Keychain helper
  - about 86 scripts outside `lab/` name a key file or helper (rough grep,
    tests and docs included)
- **Kill-conditions:**
  - fewer than about five tools on the loader a month after phase 1 → fold
    it back into the worker
  - a key value ever lands in this folder or on the plane → rotate that key
    and fix the check that missed it

## Rotation list (summary; full list in plan 3)

**Now:**
- the database password: **deferred by the developer, 2026-09-29 ("too
  disruptive")**. It was exposed in the mini's process list and a session
  transcript. Kill: any sign of misuse → rotate at once. The fix that stops
  the leak is in place: WM-108 (no argv credential) merged 9ff970ffe, and
  WM-108b (other argv sites) is running.
- the Supabase access token pasted into `~/.ecom-analysis.env` on the mini
- the Slack push bot token and the mini's Drive service-account key, both in
  a world-readable stray file; the Drive key needs a brief org-policy
  override to rotate
- the Junip store key, still in git history — the developer 2026-09-30: rotate via this
  migration on an announced date (D5), overriding the owner's 09-21 no-rotation
  (decision log; the owner told, I-147 (Junip key rotation))
- the developer's Slack user token — hidden from jobs since WM-109 (person tokens held,
  5384c65657), so it can rotate on schedule (keys#7, 2026-10-07)

**With the rollout:**
- fal, Higgsfield, OpenAI (the owner's key, used by the ops lead), Gemini, Apify,
  ElevenLabs and OpenRouter
- the team review key
- the developer's Vercel token
- the dead Shopify sync token
- the owner's full database URL

**Check first:**
- Figma
- the mini's model-route token files
- 36 key-pattern lines in `PLATFORM-CONTEXT.md` (likely false positives)

## Open questions

0. **For PLAN's no-credential-on-the-command-line pass, beyond WM-108b (other
   argv sites):**
   - an 8th site, `components/research-gatherer/research_gatherer/ownvoice.py:79`
     (the owner's). It holds psql in a variable, so a literal-`psql` scan misses
     it; WM-108b's repo scan pins it by name.
   - A11, the audio-teardown key in a curl command.
   - ~~the structural fix for `SLACK_USER_TOKEN_DEVELOPER`~~ — CLOSED by WM-109
     (person tokens held), 5384c65657: a prefix holdback in `job_env.py`
     keeps person tokens out of every job (keys#7, 2026-10-07).

1. D1: the delivery method, and whether the admins keep a copy.
2. Who reimburses a trial someone pays for on their own account.
3. Whether the prepared tables in Supabase leave out customer details
   (unchecked).
4. Whether to limit each read-only login to the prepared tables, which would
   enforce "what Claude reads" in the database. Operator B's call.
5. Which of the owner's tools need the Drive service account, which would leave
   his laptop.
6. Whether BytePlus and Adplexity are Damon-only (inferred from their
   readers).
7. The sync pipeline's key names come from the sync repo's local copy (last
   change 2026-08-13, not refreshed). Operator B to confirm.

## Transition (full detail in plan 3, "Transition")

- Keep the mini's file path and today's variable names; rename only true
  duplicates. The mini's worker needs no change.
- Readers, by rough count outside `lab/`:
  - 17 read the mini's file by path (12 inside the worker)
  - 43 use the owner's Keychain helper: one change to his helper covers them
  - 12 read `~/.gemini.env` or `~/.apify.env` (7 in a retired build,
    inferred): covered by the loader's fallback
  - 4 read video production's own `.env`
- Five steps, each safe to stop at: add the loader with a fallback · issue
  personal keys, old and new overlapping · switch readers (the worker and
  the owner's helper first, the rest through the system path) · revoke old
  shared keys on announced dates after a smoke test · turn the fallback off.
- Main risk: a new key that doesn't work yet (no balance, billing not linked,
  missing access). Handled by the overlap and the smoke test.
- Effort (inferred): 2–3 build days, about a day of admin key work,
  ~10 minutes per person, no downtime on the mini.

## Rollout (within about two weeks, not urgent)

- **Phase 0, today:** the developer's hands on the mini. Delete the stray files,
  start the red rotations.
- **Phase 1:** the loader and template (this component's first job).
- **Phase 2:** admins on the accounts, and a key per holder.
- **Phase 3:** build and send the files (needs D1).
- **Phase 4:** the rotation wave.
- **Phase 5:** the standing process, run by the ops lead.

## Sources

- **Repo and mini inventory, 2026-09-29.** Key names and file paths only;
  no value was read or printed.
- **Vendor check, 2026-09-29.** Org billing, per-key usage, caps and admin
  APIs for 16 vendors. Unconfirmed facts are marked in plan 3.
- `components/atlas/CLAUDE.md` and `manual-nodes.json`, for plan 2.
- `components/metrics/refresh.py:600` and `METRICS-BLUEPRINT.md:74,188`, for
  the orders example.

Reuses / could be reused by:
- **Reuses:** `platform/workers/mini-worker/env.template` (WM-13 (venue
  file)), `job_env.py` (WM-14 (scoped job env)), `team/dispatch-grants.json`,
  `/system-ready`'s key check, and the atlas's contract anatomy.
- **Could be reused by:** every component engine, and the brand-d team's
  Sales-CS and toolkit repos when they need keys.
