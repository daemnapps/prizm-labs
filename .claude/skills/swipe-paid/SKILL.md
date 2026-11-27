---
name: swipe-paid
description: Turn a competitor's AdPlexity ad sweep into that competitor's folder in the paid swipe pool — copy blocks, landing pages, the raw sweep and a teardown page. A sweep file and a competitor slug go in; a filed competitor folder comes out. It does not write our ads. Use whenever someone says "pull a sweep for <competitor> and file it", "cluster the <competitor> sweep into blocks", "build the <competitor> paid swipe for <brand>", "refresh the <competitor> swipe with the new sweep", "capture the <competitor> landing pages", "rebuild the page for <competitor>", "what paid swipes do we have", "what did <competitor> lock in as copy".
---

# Swipe — paid

> **Activates component:** `components/swipe-paid` — `build.py` takes an advertiser sweep through `cluster`, `resolve`, `harvest`, `records` and `capture` into one folder per competitor; `refresh.py` folds in a newer sweep.

External dependencies: `components/swipe-paid/` (the pool; `CLAUDE.md`, `README.md` and `METHOD.md` are its rules), `components/swipe-paid/capture/adplexity_client.py` (the AdPlexity client that pulls a sweep), `components/swipe-paid/swipe_home.py` (finds the Drive side), `components/keys/loader.py` (reads `ADPLEXITY_API_KEY` by name), and the Drive folder `Shared Assets/swipe/paid/<competitor>/` (the media).

## Spends credits — say so before you run

AdPlexity credits are limited (5,000 a month, no rollover). Two steps spend them: **pulling the sweep** (credits per ad returned) and **`resolve`** (exactly one credit per copy block). Everything else is free. Tell the person which step spends and roughly how much, get a yes, then run it. Do not run either on your own initiative. `cluster`, `records`, `capture`, `harvest` (downloads media) and the page build spend no credits.

## The steps, in order

A competitor is named by a slug (its folder name). `<ALL.json>` is the sweep file the first step writes.

```
python3 components/swipe-paid/capture/adplexity_client.py advertiser <competitor-domain> [--count 25] [--pages N] [--country US]
python3 components/swipe-paid/build.py cluster <ALL.json> <competitor-slug>
python3 components/swipe-paid/build.py resolve <competitor-slug>
python3 components/swipe-paid/build.py harvest <competitor-slug>
python3 components/swipe-paid/build.py records <competitor-slug>
python3 components/swipe-paid/build.py capture <competitor-slug>
python3 components/swipe-paid/build_page.py <competitor-slug>
```

- The sweep is saved under `components/swipe-paid/capture/raw/` as `advertiser_<slug>_<date>_ALL.json`. A person who already has a sweep file starts at `cluster`.
- **Order matters:** cluster first, then resolve one ad per block (about 18 credits instead of 830), then harvest, records, capture.
- **A competitor already in the pool** gets a newer sweep folded in, never rebuilt: `python3 components/swipe-paid/refresh.py <competitor-slug> <sweep ALL.json> <YYYY-MM-DD> [--resolve]` (`--resolve` spends one credit per new block). A refresh only ever adds.
- `python3 components/swipe-paid/md_to_content.py <competitor-slug>` lifts a hand-written `teardown.md` into the page's content before `build_page.py`.
- Read-only checks: `python3 components/swipe-paid/standardize.py check` prints the shape matrix for every competitor.

None of these commands has a `--dry-run` or a `--help`: `build.py` with no stage, or with `--help` as the slug, prints usage or fails. Do not probe it by running stages against made-up slugs.

## What it reads

The sweep (eight fields per ad: id, type, title, description, image, video, ad type, group count; no spend, impressions or dates), and a per-ad detail call that adds the landing page. Nothing about our own brands.

## The rules it enforces — do not work around any of them

1. **One block is one copy block:** ads cluster by identical headline plus primary text, ranked by how many variants they run, not by creative count.
2. **A block is not an angle.** An angle is a person's read signed into `brands/<brand>/strategy/angles.json`; this pool only holds blocks. Do not label a block an angle.
3. **Cluster before you resolve.** Never resolve every ad.
4. **Pages are captured once** and live once under `_pages/`; a block with no capturable page records why and gets no Drive page folder.
5. **Every competitor fills the same shape** (`_TEMPLATE/`).
6. **Two judgment slots are never machine-written:** "Structural findings" and "What to take, and what to beat" in `teardown.md`. `build.py brief` refuses while a `teardown.md` exists unless `--replace` is given; do not use `--replace` unless the person says to overwrite.
7. **Nothing old is ever deleted.** A refresh adds; a superseded page is kept beside the new one.
8. **Words in git, media on Drive.** Media never enters git; this skill never deletes anything on the Drive.
9. **Keys travel by name.** `ADPLEXITY_API_KEY` is read through the key loader; never print, paste or ask for it in chat. If it is missing, say so in one line.

## What comes back, and where it lands

- **Repo:** `components/swipe-paid/<competitor-slug>/` with `_BRAND.md`, `PROFILE.md`, `teardown.md`, `teardown.html`, `teardown-content.json`, `blocks.json`, `pages.json`, `blocks/NN_<slug>.md`, `_pages/<slug>.md` and `_raw/`. Each `.md` carries a `**Drive:**` line naming its media folder.
- **Drive:** `Shared Assets/swipe/paid/<competitor-slug>/blocks/<slug>/{video,photos}/` and `_pages/<slug>/page.{png,html,txt}`.
- The competitor is then readable by `swipe-intake` and both teardowns.

Report: how many ads, how many blocks, how many landing pages captured, credits spent (and which step), and anything that had no landing page.

Reply with the result and the folder it landed in (repo path or Drive folder name).
