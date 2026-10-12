# swipe-organic — what the avatars actually watch

Auto-loads for work nested here. Written 2026-09-23, when the folder moved out
of `lab/` and owed the four new-resident questions
(`components/CLAUDE.md`). **Nothing here is new doctrine** — every line is
assembled from the five documents that were already in this folder, and where
this file and one of them disagree, say so rather than guessing:

`README.md` (what the board is and what runs it) · `METHOD.md` (why it works
from people rather than seed lists) · `FEEDS.md` (the per-avatar feeds) ·
`SAVES.md` (the owner's saves as intake) · `HOSTING.md` (the hosted-board plan:
route A, a static read-only public export, live since 1 Oct 2026; the
22 Sep "NOT NOW" ruling is kept there as history) ·
`SYSTEM.md` (how the whole research system fits together). Written since:
`THE-SWIPE-LINE.md` (2026-10-03 — every post has a lane, and which lanes a
feed keeps).

Runs by: person

## The four questions

- **Engine + owner:** `desk.py` is My Feeds, the front — port 8820, launch
  entry `my-feeds`, kept up by `com.daemn.feeds-serve` on the owner's Mac. It is
  a one-Mac service: anyone else runs `python3 desk.py` on their own clone.
  Behind it:
  `dig.py` (ask → plan → pull → sift → follow winners), `sift.py` (keep or
  drop against the ask), `daily.py` (every feed in one run, $__ cap, $__
  floor — SWITCHED OFF: `com.daemn.feeds-daily` is disabled, rule 0; every
  pull is the owner's **Pull now**), `subfeeds.py` (one feed per
  sub-avatar), `saves.py` (his saves), `formats.py` and `bundle.py` (the
  format library and the kit built from it), `packs.py` / `paidpack.py` /
  `paiddata.py` (the public download kits), `sounds.py` (trending TikTok
  sounds, recent only — `/sounds` on the desk, pulled only on his button, no
  schedule; see `SOUNDS.md`). `desklib.py` is the shared layer.
  Apify calls go through `apify.py`, a re-export of `components/apify/`.
  **the owner.**
- **Definitions + curator:** the prompts in `prompts/feed-*.md`, shown
  verbatim on the page so they can be corrected where they are read;
  `formats.json`; each feed's source list in
  `records/avatar-feeds/<feed>/sources.json`, where **a source enters only with a
  receipt line saying where it came from**. **the owner** — the standing content
  rule ("pure entertainment only", 2026-09-19) sits at the top of both prompts,
  above any ask.
- **The plane it emits:** this is a POOL, not a run-per-invocation machine —
  the same contract as `swipe-paid/`. Its record is its folder shape under
  `records/`: `avatar-feeds/<feed>/` (every feed: `sources.json`, `items.json`,
  `observations.jsonl`, `sweeps.jsonl`; most also carry `plan.json` (the dig's
  plan), `discoveries.jsonl` (hops' adoptions), `feed.html` and
  `prompts-as-sent/`; `covers/` is gitignored and sits only on the Mac that
  pulled), `damon-saves/`,
  `culture-digs/`, `personas/`, `persona-kits/`, `swipe-videos/`, `teardowns/`,
  `desk/`. Its scripts also write, and these are pool too: handle folders
  `<handle>/` (slideshows.py); pool folders `<pool>/posts.json` (add.py
  `pool_file`); `creators/<handle>/PROFILE.md` (profile.py); `records/sounds/` —
  `pool.json`, `index.json`, `pulls.jsonl`, `raw/`, `prompts-as-sent/`
  (sounds.py); `records/format-digest.json` and `records/format-merges.json`
  (written by consolidate.py until it was removed at cda8ef9c06, 7 Oct; nothing
  rebuilds them now, so both are FROZEN at that copy — naming and elements still
  read format-digest.json). `desk.html` and `sounds.html` are the desk's own templates,
  not output. The creator-profiles page is not pool: it renders to
  `runs/swipe-organic/_system/organic-profiles.html` (swipe-organic#20). The pack builders are the exception and file like any run, at
  `runs/swipe-organic/_packs/<date>/` with a `run.json`. Media mirrors to
  `Shared Assets/swipe/organic/`, reached through
  `components/swipe-paid/swipe_home.py` (SI-47 (swipe switch)), and creator
  posts to `Shared Assets/lab/creators/<handle>/posts/`.
- **Manifest per entry:** each feed's `items.json` carries its posts, one row
  per post with its source and a receipt; `sources.json` carries its sources,
  each with a receipt. The dig writes its ask into `sources.json` and its plan
  (`plan.json`, `prompts-as-sent/plan.md`) beside them. A post with no receipt
  is not a row.

**Read surface — who may read what** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line). Besides the `records/` shelves above, these are part of the pool's contract and other components may read them by path:
1. **Handle folders** `<handle>/posts.json` and `<handle>/posts/*.md` — one pulled creator or brand (image-teardown, intake).
2. **`formats.json`** (the definition above) and **`records/format-digest.json`** — read by elements and naming.
3. **Per-shelf files:** `records/avatar-feeds/<feed>/items.json` (intake, video-production, research-gatherer, marketing-chain-checks), `records/swipe-videos/<code>/format.json` (intake), `records/damon-saves/catalog.json` (copywriter), `records/teardowns/<code>/` and `records/culture-digs/` (video-production, research-gatherer, ad-variations).
Nothing imports this folder's Python; everything else here — the scripts, `.bundle/`, `desk/` state — is internal and may change without notice. A reshape of any file above is a contract change: say so here, and move the readers in the same commit.

## Rules this component holds itself to

0. **No automatic Apify spend** (the owner, 2026-09-23: *"turn off any automatic
   feeds using Apify"*). `com.daemn.feeds-daily` is DISABLED in launchd (as is
   `com.daemn.research-nightly`, the research gatherer's nightly pull). Every
   pull runs on his button only. Do not re-enable either without his word.

1. **A seed list is a hypothesis, not research** (`METHOD.md`). Seeds are
   scaffolding; people are the data. A feed scoped to a topic harvests that
   topic and calls the guess a finding.
2. **Pure entertainment only** (the owner, 2026-09-19). An ask names whose scroll
   it is; it never turns the feed into content about their problem. What a
   feed keeps is its `keep_lanes` (`sift.py`, `sift_rules.py`): by default
   entertainment and educational. A feed whose subject is the selling (a
   shop's own posts, a remake pool), or a person's own saves, may set
   `keep_lanes` in its `sources.json` to keep selling too (the owner, 2026-10-02;
   `THE-SWIPE-LINE.md`).
3. **My Feeds is THE board** (the owner, 2026-09-19: *"this is what we're going
   with, and we don't use the old one"*). New layers get added to it, never as
   another board. `app.py` is the old surface and **no longer serves** — a
   finding in it is a finding in retired code. The other old surface,
   `feedapp.py`, was removed 2026-10-07 (SI-60 (swipe export cleanup)).
4. **Nothing here spends without a floor.** Apify was at $__ of $__ the
   month the hosted-board plan was written, which is why that plan was ruled
   NOT NOW on 2026-09-22: eleven people with live buttons can empty it in an
   afternoon. Its route A went live on 1 Oct 2026 instead — a static,
   read-only export with no keys and no buttons, which cannot spend
   (`feedsexport.py`, `HOSTING.md`).
5. **The key travels by name.** `APIFY_TOKEN` comes from the environment, then
   the Keychain, through `components/apify/`. No file path, ever.
6. **Brand-agnostic** (workspace rule 7). The public kits are checked by
   `packs.py`'s own guard, which refuses any file naming a brand, a person's
   disk or a secret.

7. **The public publish is a person's act, never a schedule** (the developer,
   2026-10-07, triage page 10; O5b (export replace is deploy)).
   `feeds-publish.sh` — the commit and push to daemn.co/feeds/ — runs only
   when a person runs it; it is never put on launchd, cron or a worker. The
   re-export `desk.py` starts after a Pull only replaces the export's own
   previous copy in the local site checkout and pushes nothing.

## Two things that are open, not settled

- **The Drive carve-out (O9 (Drive by fileId)) — closed for the pool,
  2026-10-07.** the developer moved the media by hand from
  `Shared Assets/lab/swipe-organic/` to `Shared Assets/swipe/organic/`
  (same file ids; the lab folder is gone). Every reader and writer reaches it
  through `components/swipe-paid/swipe_home.py` (SI-47 (swipe switch)). Old
  stored lab paths still resolve through `swipe_home.resolve()`. Still open:
  creator posts stay at `Shared Assets/lab/creators/`, and the repo side
  moves with the 2 Nov move. Partial copies sit at
  `Shared Assets/swipe/_partial-copy-organic`, for a person to delete.
- **Records (O12 (records adapter)): `runs/swipe-organic/` is filed by the shared
  runs filer** (PLANE-19 (runs filer), on the mini) — no adapter of its own.

## What moved here, and what did not

Moved out of `lab/swipe-organic/` on the owner's word, 2026-09-22 (*"swipe
paid, swipe organic, intake all need to move to components now"*). Both launchd
jobs were repointed and reloaded the same hour.

**Cut 2026-09-23** (the owner: *"I don't want this in that other repo or devel stuff
anymore"*): `packs.py` copied its brand template out of `another repo`,
and three builders defaulted their output into that repo's `docs/downloads`,
which does not exist. The template now comes from this workspace's own
`brands/_TEMPLATE`, and output defaults inside `runs/`. `--site` still
publishes to daemn.co when there is something to publish.
