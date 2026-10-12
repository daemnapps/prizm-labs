# Swipe

## How to use it → (team dashboard)

Competitor brands, torn down. One folder per brand, identical shape every time.

Artifact: (team page)

**Words here. Media on Drive** at `Team Drive/swipe/paid/<brand>/`,
mirroring this tree, reached through `swipe_home.py`. the developer moved it there from
`the shared drive/swipe-paid/` on 2026-10-07; old stored lab paths still
resolve through `swipe_home.resolve()`. See `CLAUDE.md` for the rules.

## Block vs angle — the one thing to get right

A **block** is ads that share one paragraph of copy. It is mechanical, a
`GROUP BY`, and it is what `blocks.json` and `blocks/` hold. It says what copy
an advertiser has locked, nothing more.

An **angle** is the read on a problem — signed in the brand's
`strategy/angles.json`, where the rule is "no receipt, no entry". It lives on
`creatives.angle`, put there by a person, and one angle runs across many blocks.

They were the same word until 2026-09-02 and it hid the thing that matters. In
our own account one block held an ad that took $__ and one that took $__
same paragraph — the difference was entirely in the picture. Copy cannot carry
an angle; the frame can, which is what `scan_frames.py` reads.

## Three lanes, one corpus

This started as competitor teardowns. It now holds everything we swipe from,
described in one vocabulary so the three can be read against each other.

| lane | what a creative is | where it comes from | what we know for free |
|---|---|---|---|
| `own` | an ad we are running | the ecom_data_sync Supabase tables | real spend and ROAS |
| `paid` | a competitor's live ad | the AdPlexity advertiser sweep | nothing until judged |
| `organic` | a post the avatar's world watches | `swipe-organic/records/avatar-feeds/` | the platform |

```
python3 own/ingest.py --days 120     # our account + our live library, with spend
python3 corpus.py build              # rebuild all three lanes into swipe.db
python3 lane_profile.py              # regenerate the records for own + organic
python3 serve.py 8780                # one UI over all of it
```

Vocabulary is owned by `../naming/names.py` (`CREATIVE_FIELDS`) and never
re-declared here; `../naming/selfcheck.py` fails if the two ever drift. The
join back to a production run is `swipe:<lane>:<source>:<id>`, kept in the
manifest, never in the ad name.

## The angle is read off the frame, not the copy

Grouping ads by body copy gives **copy blocks**, not angles. In our own account
one copy block held an ad that took $__ and one that took $__ — same
paragraph, different picture:

    "If you have brown spots on your legs right now"   $__   shows the problem, demonstrates
    "If you wore a cardigan"                           $__       shows neither

```
python3 scan_frames.py <lane> <source> [--limit N]
```

reads the burned-in hook and what is actually in frame (who is present, where
the problem shows, whether the product is demonstrated, filmed vs generated)
and merges it over the corpus. Prompt: `prompts/frame-scan-v1.md`. A frame
already scanned is never paid for twice.

## What you need to run it

Nothing is committed that a run needs, so a fresh clone works once these exist:

Every key travels by NAME — the environment first, then the macOS Keychain
(`python3 ~/.daemn/daemn_keys.py` says what is stored). No machine here reads a
key out of a file, and none reaches outside this workspace for one; that was
cut on 2026-09-23.

| for | what | where it comes from |
|---|---|---|
| the `own` lane | `SUPABASE_DB_URL` | the Keychain; the data is still the ecom_data_sync Supabase tables |
| page capture | `psycopg[binary]`, `playwright` | `python3 -m venv ~/.local/venvs/ecom && ~/.local/venvs/ecom/bin/pip install "psycopg[binary]" playwright` |
| page screenshots | Google Chrome | already installed; playwright drives it with `channel="chrome"` |
| the frame scan | `GEMINI_API_KEY` | the Keychain |
| the `paid` lane | `ADPLEXITY_API_KEY` | the Keychain |
| the AdPlexity client | `capture/adplexity_client.py` | in this component, with its `market.db` and `raw/` ad cache |
| media | the team Drive mounted | swipes at `Team Drive/swipe/paid/` (through `swipe_home.py`); our own media at `the shared drive/` |

Derived files are gitignored and rebuilt, never migrated: `swipe.db`,
`own/*/ads.json`, `own/*/pages.json`, `.build/`. Everything else is the record.

## Brands

| Brand | Domain | Swept | Creatives | Copy blocks | Page | Write-up |
|---|---|---|---:|---:|---|---|
| **competitor-a** | `competitor-a.example` | 2026-08-19, refreshed 2026-09-21 | 1,830 | 30 | [teardown.html](competitor-a/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-a/teardown.md) |
| **brand-c** | `brand-c.shop` | 2026-08-31 | 496 | 8 | [teardown.html](brand-c/teardown.html) | [teardown.md](brand-c/teardown.md) |
| **competitor-b** | `competitor-b.example` | 2026-08-20 | 463 | 35 | [teardown.html](competitor-b/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-b/teardown.md) |
| **competitor-c** | `competitor-c.example` | 2026-08-20 | 837 | 162 | [teardown.html](competitor-c/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-c/teardown.md) |
| **competitor-d** | `competitor-d.example` | 2026-09-11 | 395 | 109 | [teardown.html](competitor-d/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-d/teardown.md) |
| **competitor-e** | `competitor-e.example` | — | 153 | 71 | [teardown.html](competitor-e/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-e/teardown.md) |
| **competitor-f** | `competitor-f.example` | 2026-09-19 | 44 | 40 | [teardown.html](competitor-f/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-f/teardown.md) |
| **competitor-g** | `competitor-g.example` | 2026-09-19 | 150 | 106 | [teardown.html](competitor-g/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-g/teardown.md) |
| **competitor-h** | `competitor-h.example` | 2026-09-20 | 1,901 | 39 | [teardown.html](competitor-h/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-h/teardown.md) |
| **competitor-i** | `competitor-i.example` | 2026-09-23 (US, live 14+ days) | 177 | 14 | [teardown.html](competitor-i/teardown.html) · [artifact]((team page)) | [teardown.md](competitor-i/teardown.md) |

## Repo — the words, and Drive — the media

The folder layout on both sides is declared once, in this folder's `CLAUDE.md`
(the repo side) and `swipe_home.py` (where the Drive side resolves); the schemas
every brand fills are the files in `_TEMPLATE/`. This README does not restate
either tree.

Every `.md` on the repo side carries a `**Drive:**` line naming its mirrored
folder, so the words always point at their media.

## The rules

**One angle = one copy block.** Ads are clustered by identical headline + primary
text. `NN` is rank by creative volume — `01` is the block carrying the most
footage, the angle they are betting on.

**Cluster before you resolve.** The sweep returns copy but no landing page; the
LP only comes from `/ads/<id>` at 1 credit each. Cluster into angles first, then
pull detail for one representative ad per angle — 18 credits instead of 830.

**Pages are captured once.** A page can serve several angles (on competitor-a, four
pages carried eleven). It lives once under `_pages/` on both sides; the angle
file names it.

**No page means no folder.** If an angle has no capturable landing page (broken
merge tag, dead LP), its angle file records why and no Drive `page/` folder is
created.

**Media never enters git.** `.gitignore` blocks the extensions outright. Every
file re-downloads from the ad IDs recorded in the angle file.

## The record schemas

Every brand's files follow `_TEMPLATE/` exactly, so any two brands read the same
and diff against each other:

| File | Template |
|---|---|
| `<brand>/_BRAND.md` | `_TEMPLATE/_BRAND.md` |
| `<brand>/teardown.md` | `_TEMPLATE/teardown.md` |
| `<brand>/blocks/NN_*.md` | `_TEMPLATE/_BLOCK.md` |
| `<brand>/_pages/*.md` | `_TEMPLATE/_PAGE.md` |

`teardown.md` carries two **judgment slots** — *Structural findings* and *What to
take, and what to beat*. Those are never machine-written; `build.py brief` refuses
while `teardown.md` exists, `--replace` overwrites (SI-84 (paid pool bugs)). Everything else in the
file is countable and comes straight from the data.
