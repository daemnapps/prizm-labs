# Swipe

## How to use it → https://dashboard.the company.com/atlas#c-components-swipe-paid

Competitor brands, torn down. One folder per brand, identical shape every time.

Artifact: (private page)

**Words here. Media on Drive** at `Shared Assets/swipe/paid/<brand>/`,
mirroring this tree, reached through `swipe_home.py`. the team moved it there from
`Shared Assets/lab/damon/swipe-paid/` on 2026-10-07; old stored lab paths still
resolve through `swipe_home.resolve()`. See `CLAUDE.md` for the rules.

## Block vs angle — the one thing to get right

A **block** is ads that share one paragraph of copy. It is mechanical, a
`GROUP BY`, and it is what `blocks.json` and `blocks/` hold. It says what copy
an advertiser has locked, nothing more.

An **angle** is the read on a problem — signed in the brand's
`strategy/angles.json`, where the rule is "no receipt, no entry". It lives on
`creatives.angle`, put there by a person, and one angle runs across many blocks.

They were the same word until 2026-09-02 and it hid the thing that matters. In
our own account one block held an ad that took $41,870 and one that took $99,
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
one copy block held an ad that took $41,870 and one that took $99 — same
paragraph, different picture:

    "If you have brown spots on your legs right now"   $41,870   shows the problem, demonstrates
    "If you wore a cardigan"                           $99       shows neither

```
python3 scan_frames.py <lane> <source> [--limit N]
```

reads the burned-in hook and what is actually in frame (who is present, where
the problem shows, whether the product is demonstrated, filmed vs generated)
and merges it over the corpus. Prompt: `prompts/frame-scan-v1.md`. A frame
already scanned is never paid for twice.

## What you need to run it

Nothing is committed that a run needs, so a fresh clone works once these exist:

Every key travels by NAME through the one key loader (`components/keys/loader.py`)
— the environment first, then the one key file, this repo's `.env` (add
`NAME=value` there). No machine here reads a key out of any other file.

| for | what | where it comes from |
|---|---|---|
| the `own` lane | `SUPABASE_DB_URL` | this repo's `.env`; the data is still the ecom_data_sync Supabase tables |
| page capture | `psycopg[binary]`, `playwright` | `python3 -m venv ~/.local/venvs/ecom && ~/.local/venvs/ecom/bin/pip install "psycopg[binary]" playwright` |
| page screenshots | Google Chrome | already installed; playwright drives it with `channel="chrome"` |
| the frame scan | `GEMINI_API_KEY` | the Keychain |
| the `paid` lane | `ADPLEXITY_API_KEY` | the Keychain |
| the AdPlexity client | `capture/adplexity_client.py` | in this component, with its `market.db` and `raw/` ad cache |
| media | the team Drive mounted | swipes at `Shared Assets/swipe/paid/` (through `swipe_home.py`); our own media at `Shared Assets/lab/damon/` |

Derived files are gitignored and rebuilt, never migrated: `swipe.db`,
`own/*/ads.json`, `own/*/pages.json`, `.build/`. Everything else is the record.

## Brands

| Brand | Domain | Swept | Creatives | Copy blocks | Page | Write-up |
|---|---|---|---:|---:|---|---|
| **competitor-a** | `competitor-a.com` | 2026-08-19, refreshed 2026-09-21 | 1,830 | 30 | [teardown.html](competitor-a/teardown.html) · [artifact]((private page)) | [teardown.md](competitor-a/teardown.md) |
| **resilia** | `resilia.shop` | 2026-08-31 | 496 | 8 | [teardown.html](resilia/teardown.html) | [teardown.md](resilia/teardown.md) |
| **competitor_blab** | `quiz.competitor_blab.com` | 2026-08-20 | 463 | 35 | [teardown.html](competitor_blab/teardown.html) · [artifact]((private page)) | [teardown.md](competitor_blab/teardown.md) |
| **competitor-c** | `competitor-c.co` | 2026-08-20 | 837 | 162 | [teardown.html](competitor-c/teardown.html) · [artifact]((private page)) | [teardown.md](competitor-c/teardown.md) |
| **marsmen** | `mengotomars.com` | 2026-09-11 | 395 | 109 | [teardown.html](marsmen/teardown.html) · [artifact]((private page)) | [teardown.md](marsmen/teardown.md) |
| **froya** | `froyaorganics.com` | — | 153 | 71 | [teardown.html](froya/teardown.html) · [artifact]((private page)) | [teardown.md](froya/teardown.md) |
| **consciousbar** | `theconsciousbar.co` | 2026-09-19 | 44 | 40 | [teardown.html](consciousbar/teardown.html) · [artifact]((private page)) | [teardown.md](consciousbar/teardown.md) |
| **nuora** | `mynuora.com` | 2026-09-19 | 150 | 106 | [teardown.html](nuora/teardown.html) · [artifact]((private page)) | [teardown.md](nuora/teardown.md) |
| **sprtn** | `shop.try-sprtn.com` | 2026-09-20 | 1,901 | 39 | [teardown.html](sprtn/teardown.html) · [artifact]((private page)) | [teardown.md](sprtn/teardown.md) |
| **lasta** | `lasta-fit.com` | 2026-09-23 (US, live 14+ days) | 177 | 14 | [teardown.html](lasta/teardown.html) · [artifact]((private page)) | [teardown.md](lasta/teardown.md) |

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
