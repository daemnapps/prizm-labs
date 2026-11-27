---
name: naming
description: Name deliveries and ads to the convention. Use whenever someone says "name the deliveries", "run the naming", "a creator / the editor / a creator delivered", "check the delivery folders", "what's ready to launch", "name this batch", "is this name right", "what does this name mean", or hands over finished pictures or clips on their way to Drive or Meta.
---

# Rename

> **Activates component:** `components/naming` — `delivery_rule.py` names a delivery; `names.py` checks a name.


External dependencies: `components/naming/` (`CONVENTION.md` top section is the rule; `delivery_rule.py` names deliveries; `names.py` builds and parses names), `brands/<brand>/briefs/briefs.json` (every brief's header), `brands/<brand>/briefs/delivery.json` (the folders people drop work into), `brands/<brand>/funnels/funnels.json` (funnel ids).

## Name every delivery (the one most people need)

Editors, designers and creators drop finished work into a folder named with the brief number, any file names. This names them from the brief:

```
python3 components/naming/delivery_rule.py --brand <brand>            # report only: what it would name, what it holds
python3 components/naming/delivery_rule.py --brand <brand> --apply    # rename, write naming.json, rebuild READY-TO-LAUNCH.md
```

- Names are short (ruled 2026-09-29): folder `brand_product_brief_batch`, file `…_asset-NN`, Meta ad `…_funnel` (one per batch). Everything else is in the brief.
- **Held, never guessed:** no brief matches the folder; the brief has no product; a file's frame isn't the brief's ratio. Fix the brief (or the file) and run again.
- A brief with no angle is named but listed with no ad set in `READY-TO-LAUNCH.md` until its angle is set in `briefs.json`.
- Swipe references (`*control*`, `*reference*`) and unchosen picks (`*candidate*`) ride along untouched.
- Show the person the report, run `--apply` when they say so, then show `READY-TO-LAUNCH.md` from the delivery folder.

## The older 13-part tools

Still here for old batches and live ads that carry the 13-part name:
**Two commands: check a name, or deliver a folder.**

```
python3 components/naming/names.py next-batch <brand>                 # the next free batch id for today
python3 components/naming/names.py check <name> [<name> …]            # does it parse
python3 components/naming/names.py parse <name>                       # show its fields

python3 components/naming/deliver.py <folder> --brand <brand> --product <product> --media static|video|carousel --source ai|ugc|studio|mixed --talent <talent or none> --avatar <avatar> --format <format> --brief <brief id> --ratio 9x16|4x5|1x1 [--problem …] [--angle …] [--concept …] [--brief-file <brief.md>] --dry-run
python3 components/naming/deliver.py <folder> … 
```

- `deliver.py` renames every finished asset in the folder to the
  convention, writes `manifest.json` beside them, and prints the ad unit
  name to paste into Meta. `--brief-file` reads problem, angle and concept
  off the brief instead of the flags.
- **`--dry-run` spends nothing** — shows the names it would give and writes
  nothing.
- Every value is looked up: an angle must be in the brand's angle bank, an
  avatar one of the brand's core folders, `media` and `source` on their
  lists. An unknown one is an error, not a new entry.

## The rules the command enforces — do not work around any of them

1. **Nothing here invents a name.** A name that is not in its bank is an
   error. Only the owner signs an angle active.
2. **Lowercase `[a-z0-9]` inside a field; hyphen only between fields.**
   `spot-hider` becomes `spothider`.
3. **All the fields, always.** A missing field shifts every field after it
   into the wrong column.
4. **The name is a key, not a description.** The headline, the offer, the
   plate, the prompt, the swipe — all of that lives in the manifest and is
   recovered by joining on the name. Never a headline in a name.
5. **A name is never reused or re-pointed.** A changed creative is a new
   asset in a new batch. `names.py` refuses a rename onto an existing name.
6. **What each word means, and its test**: `components/marketing-doctrine/slices/words.md`, the one home. Same claim, narrower
   person → a sub-avatar, not a new angle; same claim, different container →
   a format, not a new angle.
7. **Naming is a step in production, not a tidy-up afterwards.** An asset
   that reaches Drive as `ad-control.png` is already lost.

## What comes back

The renamed files in the folder, `manifest.json` beside them (the ad unit
name once, one row per asset carrying what the name leaves out), and the ad
unit name. The batch is then read by its filenames (the Production Board
and spend reports join on them) — a badly named asset is lost to both. The standard's shared
page is "Ad Name Spec" (`lab/the owner/context/artifacts.md`).

Report: the ad unit name, how many assets were named, and anything refused
and why.

Reply with the result and the folder it landed in (repo path or Drive folder name).
