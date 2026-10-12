# components/identity-training — the identity engine, as a component

**Owner: the developer (ruled 2026-09-01).** Extracted from
`tools/video-teardown/machine/train_identity.py` under IDT-1 on the developer's
ruling relayed through ◆ PLAN, so that trained identities are a curated,
findable asset of the org rather than a side-product of one machine.

What it is: an engine that turns a brand's certified images into a **LoRA
identity on fal** — a character (a person who must be the same person in
every scene) or a product (color, shape and logo locked). What it is not: a
video tool, a brand tool, or anybody's workflow. The training standard is
the owner's and stays his; the code that executes it is owned here.

**the owner's machine keeps working, and that is a hard constraint of the move**
(ruled). `tools/video-teardown/machine/train_identity.py` is now a thin
shim over this engine: same command, same flags, same output, same key vault,
same Drive fallback. Nothing was asked of him and nothing changed on his side.
The shim is the ONLY file IDT-1 touched in his folder.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

| question | answer |
|---|---|
| **engine + owner** | this folder's `identity_training/` — **the developer** |
| **definitions + curator** | the trained identities themselves (`lora.json` records: trigger word, weights url, training set). **Curator: the developer**, holding the registry gate; **the owner certifies the training sets** — a board set or a product set is his to bless, and an uncertified set is not trained |
| **the plane it emits** | **none beyond the filed records.** A run writes exactly one file, `lora.json`, beside the brand source; the weights live on fal (workspace rule 3 — never in git) |
| **what the manifest declares per entry** | it rides **MDL-1's trained-assets index** in `components/models/`. That component does not exist yet as of 2026-09-01, so this is **sequenced, not blocked**: until it lands, the `lora.json` records ARE the index. Per entry, this engine already writes what the index needs — `kind`, `trigger`, `lora_url`, `trained`, `steps`, `training_images`, `account` — and the index adds the status field the definition owner gates on (`draft` / `approved` / `deprecated`, rule 6) |

Runs by: person

(the developer, 2026-10-07, triage action 3 (definition lines and registry rows); SI-6 (intent line).)

## Contract (components/CLAUDE.md rule 2)

Three surfaces are dependable and they are the only three: **the command**,
**the `lora.json` record**, and **the two host seams**. Nothing outside this
folder may depend on anything else here.

### 1. A run is one command

```
python3 components/identity-training/train_identity.py --brand <brand> \
    ( --character <name> | --product <slug> ) [--steps N] [--out DIR] [--dry-run]
```

| flag | means |
|---|---|
| `--brand` | required. Resolves `brands/<brand>/` (the one brand home; `brands/` is gone since 2026-09-02, engine.py `brand_dir`) |
| `--character NAME` \| `--product SLUG` | **exactly one.** Naming both, or neither, exits non-zero |
| `--steps N` | override. Default **1000** character, **2000** product |
| `--out DIR` | where `lora.json` lands, and the only place a run may write. **Omitted = beside the brand source, exactly as before the move** |
| `--dry-run` | resolve inputs, trigger word, steps and destination; print them; **call nothing, write nothing, read no credential** |

Workspace root: `AI_WORKSPACE` when set, else `the workspace` — the
same path it always resolved, now overridable so a test or the mini can point
it somewhere else (rule 8).

### 2. `lora.json` — the record IS the asset

Written beside the brand source (`brands/<b>/ai-cast/<name>/` or
`brands/<b>/products/<slug>/`), or under `--out`:

```json
{ "kind": "character" | "product",
  "trigger": "<=24 chars, [a-z0-9] of brand+name",
  "lora_url": "<the weights, on fal>",
  "trained": "YYYY-MM-DD", "steps": 1000,
  "training_images": 25, "account": "company fal",
  "note": "<the standing caveat about label-forward frames>" }
```

Words in git, weights on fal (workspace rule 3). A run makes **one** write and
that is it.

### 3. The two host seams — `engine.configure()`

```python
configure(key_lookup=None, drive_lookup=None)
```

Both are **fallbacks, never overrides**: the environment wins on the key, the
repo wins on images. A host with neither loses nothing — it just needs
`FAL_KEY` in the environment and its images in the repo.

| seam | consulted when | video-teardown's shim passes |
|---|---|---|
| `key_lookup(name)` | `FAL_KEY` is not in the environment | `keys.get` — the owner's `~/.daemn/keys.env` vault |
| `drive_lookup(rel)` | a brand path has no images in the repo | `chain.drive_root() / rel` — his Drive mount |

The seams exist so that this engine imports **nothing** from
`tools/video-teardown/` (rule 2 both ways): `keys.py` and `chain.py` are
that machine's internals and stay there.

## Rules

- **Which `FAL_KEY`** (the developer, 2026-09-01, decision log): the MINI's — the
  company fal account the worker's image lane bills to. Trained weights live
  on that account; a personal fal key is the wrong key for a general run.
- **Credentials from the environment** (rule 8): `FAL_KEY`, read at CALL time,
  never at import time. Importing this module reads no credential and touches
  no network — the declared test asserts it in a fresh interpreter rather than
  promising it.
- **Every write under `--out`**, or — with no `--out` — the one historical
  write beside the brand source. With `--out` given, a record path escaping it
  fails the run loudly. There is no second write call site.
- **Brand-agnostic** (workspace rule 7): no brand, product, avatar or category
  name appears in this code or in a default. Brand facts arrive as `--brand`
  and resolve from the brand folder, `brands/<brand>/` only — `brands/`
  was merged into `brands/` and left the lookup on 2026-09-02.
- **the owner's standard is the owner's.** What makes a good training set — which
  boards, which crops, how many steps — is his call; changing the curriculum
  is a conversation with him, not a code change here.
- **PIL is the only non-stdlib import**, and it is imported inside the two
  set-building functions so that `--dry-run` and every import path work
  without it.

## The declared test

`python3 new-workflow-design/builds/identity-training/test_identity_training.py`
— no pytest, no network, no dependencies, and it must pass on
`/usr/bin/python3` (3.9), so no 3.10+ syntax anywhere in this component.

It proves the move rather than describing it: the shim exposes **every public
name the pre-move file exposed** (checked against a pinned list, and
cross-checked against `git show HEAD` when git is available), and its `main`,
`fal`, `character_set` … **are the engine's own objects**, not copies; a
`--dry-run` invocation is byte-identical through the shim and through the
component entry point, on a fixture workspace, with **no `FAL_KEY` and an
empty `HOME`** — which is what proves no credential is read; importing either
module in a fresh interpreter reads no credential and no network; and a
sentinel fingerprint over `tools/video-teardown/`, `platform/workers/`
and `lab/` is byte-unchanged across the whole run.

## Kill-condition

If trained identities keep being re-trained ad hoc on people's machines
instead of being looked up in the record, the curation this component exists
for is not happening — the answer is the index (MDL-1), not more engine.
