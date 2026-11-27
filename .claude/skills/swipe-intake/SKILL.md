---
name: swipe-intake
description: Save and index swipes. TWO doors — `add.py` SAVES a swipe you found by hand (files or links from any source) into a pool with its lane; `intake` READS every saved swipe (paid, organic, ours, a competitor's) and files one record per swipe with its source, its kind and which teardown it goes to. Use whenever someone hands over swipe files or links, or says "here are the swipes", "add these swipes", "save this swipe", "file this swipe, paid, from <competitor>", "run intake for <brand>", "index the swipes", "are these swipes saved and indexed", "what's new in the swipe pools for <brand>", "which teardown does this go to", "route the swipes", or asks to see every swipe for a brand as one list.
---

# Swipe intake

> **Activates component:** `components/intake and components/swipe-organic` — `intake/tools/run.py` reads and routes every swipe; `swipe-organic/add.py` saves a swipe by hand.


## Handed some swipes? Use the save door FIRST

**A swipe is three things, and doing two of them looks like doing all three:**
the media in the library, the media on the Drive, and a ROW in a pool's
`posts.json`. Intake builds its index from the ROWS — it never walks the media.
So a file dropped into the library is stored and invisible: no brand tool, no
teardown, no board can see it. That is exactly what happened to thirteen swipes
on 2026-09-24.

```
python3 components/swipe-organic/add.py --pool <name> --brand <brand> <files…>
python3 components/swipe-organic/add.py --check          # filed but not on the Drive
python3 components/swipe-organic/add.py --pool <name> --list
```

It does all three at once, resolves a TikTok id's author/caption/views through
the site's own doors (no Apify allowance spent), cuts the contact strip, and
writes a readable record behind every row. Then run intake below.

**The lane is four fields, not a folder** — `--source organic|paid|own`,
`--owner creator|competitor|own`, `--kind` (read off the asset), `--brand`.
`--pool` is just what you call the batch (`tiktok-shop`, `medicube`). Both go
in the row, so a swipe always says where it came from and which teardown it
goes to.

External dependencies: `components/intake/` (the tool), `components/swipe-paid/` (a pool — intake reads it, never writes it), `components/swipe-organic/` (a pool — intake reads it, never writes it; the save door's `add.py` above is swipe-organic's own script and writes rows into `<pool>/posts.json` there), `brands/<brand>/` (must be a real folder), `components/elements` (formats and structures are checked against it).

**One command. Free — no model, no network.**

```
python3 components/intake/tools/run.py --brand <brand>
python3 components/intake/tools/run.py --brand <brand> --source paid|organic|own|competitor --kind video|image|carousel|copy|page|email
python3 components/intake/tools/run.py --brand <brand> --dry-run
```

- `--brand` is required — a real folder under `brands/`.
- `--source` and `--kind` narrow the index; `--label` names the run (default:
  today's date); `--limit N` takes the first N.
- **`--dry-run` spends nothing** — prints the counts and where it would file,
  writes nothing.

## What it actually does

A swipe is **saved** by the swipe tools (the paid library, My Feeds, Swipe
Studio) in the folders they always used. Intake does not save, fetch or
scrape a swipe — "file this swipe" means: the swipe is already in its pool,
and intake reads both pools as one and writes one record per swipe:
`source` (paid · organic · own), `owner`, `kind` (read off the asset),
`route` (which teardown it goes to), `swiped_for` (the brand, discovered from
the folders), the asset's location, and its format if its pool knows one.

## The rules the command enforces — do not work around any of them

1. **Read-only on both pools.** No write, move, rename or reshape — ever.
2. **No format is ever filled in here.** An empty format stays empty and is
   counted. Labelling is a separate pass that needs a model and the owner's sign-off.
3. **Format and structure are different elements.** A paid ad's format is
   checked against `format/<kind>`; an organic post's "format" is a
   *structure*, checked against `structure/video`.
4. **Two gates:** inputs (both pools readable, every pool file readable, the
   brand real; `--source own` needs the own-ads cache on this machine, and a
   default run without it says the own lane was skipped) always holds;
   elements defaults to `warn` — the index still files, each swipe whose
   label the library has never seen is marked `unknown-format` /
   `unknown-structure` with the real ids beside it, and `check.json` says
   HELD. Never silently passed, never invented. `--gates hold` once the pools
   are clean.
5. **No brand in code. No model, no network. Every run is free.**

## What comes back

`runs/intake/<brand>/<label>/` — the index (one record per swipe), `run.json`,
`check.json`.

Report: how many swipes, split by source and kind, how many routed to each
teardown, how many unrouted or unknown-format, how many point at no asset,
and whether the own lane was skipped.

Reply with the result and the folder it landed in (repo path or Drive folder name).
