# Repo and Drive — two shelves, one system

> **2026-09-18:** `THE-CINEMA-LINE.md` moved to `archive/`; the `cinema/` tools stay in `machine/`. A run's record lives at `runs/video-production/<brand>/<label>/` per `runs/README.md`, its clips in `media/` there.

Markdown mirror of **Repo and Drive**
(team page).
Read 2026-09-13.

**The repo holds every word. The Drive holds every pixel.** 767 images sit
under `brands/<brand>/` on this Mac and **zero are tracked in git** — the rule
is enforced by `.gitignore`, not by anyone remembering it.

## What sits on both shelves

| `workspace/brands/<brand>/` | `Shared Assets/brands/<brand>/` | |
|---|---|---|
| `ai-cast/` — who they are, how they speak | `ai-cast/` — their reference images | ✓ |
| `core-avatars/` — the lanes, 40 before-and-afters | `avatars/core-avatars/` | name differs |
| `ai-cast/casting/` — roster and authority | `ai-cast/casting/` — every generated ref | name differs |
| `products/` — the live catalogue from Shopify | `products/` — the brand's own photography | name differs |
| `email/` | `email/` | ✓ |
| `existing-content/` | `existing-content/` | ✓ |
| `funnels/` | `funnels/` | ✓ |
| `…/runs/<run>/cinema/` — working, gitignored | `finals/<run>/` — the delivered ad | ✓ |
| — | `kit/` — an older ad's handoff | orphan |

**The four that don't line up.** `avatars/core-avatars` is nested a level
deeper for no reason. `casting-roster-260904` carries a build date, so it
dates itself. `products` and `products` are the same subject under two words.
`kit/` predates `finals/` and belongs beside it. Nothing is broken —
`authority.json` names the casting path explicitly — but four mismatches is
four things to remember, and a mirror exists so you don't have to.

## Repo only, correctly

`calendar/` `channels/` `commerce/` `creators/` `customer/` `identity/`
`meta/` `offers/` `set/` `strategy/` `variables/`, plus `market.md`,
`position.md`, `hook-ledger.md`, `identity-anchors.md`. Read, argued with and
edited — no file to open.

## The machine

    tools/video-production/            all in git
      THE-CINEMA-LINE.md                   the written process
      element-facts.json                   what is true of each product
      prompts/stage-0-read-brief … stage-4-offer
      machine/chain.py cinema{,_board,_pull,_cut,_ship}.py

    tools/video-teardown/machine/runs/<run>/     GITIGNORED
      source.mp4 · stages/ · brief-final.md · cinema/ · _superseded/

The run folder is the same shape as an image run — the image lane calls itself
the static-ad twin of the video chain, so `stages/` is its `out/`, `source.mp4`
is its `assets/`, and both end in `finals/`.

## How a frame crosses

| step | where | what it leaves behind |
|---|---|---|
| generate | Higgsfield | a job id in `plan.json` beside the prompt that made it |
| `pull.py` | → `cinema/voiced/` | the clip, plus a provenance check |
| `(retired — editing is the editor's)` | → `cinema/CUT.mp4` | inserts over the spine, voice never cut |
| `ship.py` | → Drive `finals/<run>/` | clips in timeline order, inserts named for their beat, replaced takes with reasons |

**The ship step refuses before it copies.** A take whose length matches a
voiceover file sample-for-sample was muxed, not generated. That version sat on
Drive as the current cut for a day; it cannot cross now.
