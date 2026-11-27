# components/language-layer — the customer-language query engine

**Owner: engine the developer; content (tools, prompts, the standard) the owner** — split
confirmed 2026-10-08 (the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:32:36Z: "go on B1, 2, 3"; decision log 2026-10-08 B1 (owner names); the owner may object). Extracted under LL-1 (language layer) on 2026-09-01, name ruled by the developer
("language layer is fine"; module `language_layer`, never `language` — a
top-level module by that name is one more thing on everybody's sys.path, and
`copy` was rejected for the same reason).

**language-layer** — takes **a brand and what one stage needs — an avatar, a
funnel, topics, an awareness level or a business area, and the calling chain's
own stage map (`--profile`)**, makes **the customer-language rows that stage
should see, filtered and ranked, provenance on every row; its bank tools write
proposals under `runs/language-layer/<brand>/`**. Does not **hold a stage map,
know a brand, or write the bank — the research gatherer applies every
proposal**. Triggered by
`python3 components/language-layer/query_language.py --brand <b> --stage <stage> --profile <chain-profile>.json`.

What it is: the query over the ~14.6k-row customer-language banks — rows in,
filtered and ranked rows out, per stage, provenance travelling on every row.
What it is not: anybody's chain. It holds no stage map, no brand and no
opinion about what a stage is for.

**Why it exists as one home.** It was two files, 103 diff lines apart, and one
of them lived inside `components/video-teardown/machine/` — component
internals nothing else may depend on (components rule 2). The render fix of
2026-08-31 lived only in the copy lab's copy. The video machine's own header
named the drift as the signal to give it one home rather than patch both.

**Both machines keep working, and that was the hard constraint of the move.**
`components/video-teardown/machine/language.py` and
`lab/the owner/copy/machine/language.py` are now thin shims over this engine: same
command, same flags, same output, same roots, same stage maps. Nothing was
asked of the owner and nothing changed on either side. Each shim is the ONLY file
LL-1 (language layer) touched in its folder.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

| question | answer |
|---|---|
| **engine + owner** | this folder's `language_layer/` — **the developer** |
| **definitions + curator** | **two kinds, neither of them here.** (1) The **stage maps** — which evidence types a stage is looking for — are per-chain definitions living in each chain's shim or profile file; **the chain's owner curates his own** (the owner, for both chains that exist today). The copy chain's map has a `render` entry because that chain has a render stage; the video chain's does not. (2) The **banks** themselves are brand content, curated brand-side under `brands/<brand>/core-avatars/*/language/` — rule-9 (brand home) |
| **the plane it emits** | **the query library: none** — a call returns rows or a rendered block to its caller; the CALLER emits. **The tools in `tools/`** write under `runs/language-layer/`; each tool's docstring says what it writes |
| **what the manifest declares per entry** | **n/a** — no manifest, because there are no entries. The definitions it executes are declared per chain, by the chain |

## Lived moments rotate, positioning stays (2026-11-02)

Positioning, mechanism, benefits, offers and rules stay fixed. A lived moment, meaning a garment, an occasion, a person, a habit, something hidden or stopped, changes every run.
`language_layer/experience.py`: `pick()` hands a run eight indexed moments across themes, ones the last five runs were handed rest, ones that fit the swipe first. `for_stage` appends them to every language query, so every chain that asks for language gets them. `clean_file()` lifts moments out of fixed brand files as they are read (position, story, language bank, avatar, and an avatar's profile, rules and culture map), using `runs/language-layer/<brand>/experience/strip.json`. The brand files themselves are untouched. No index or strip list means a brand reads as before.
Build: `tools/experience.py build --brand <b>` for a new brand or avatar, then read the new terms in `strip.json`: `overused` can pick a word that is the brand's own world, and a term removes every sentence naming it. Every quote is word for word in its source or it is refused.

## Contract (components/CLAUDE.md rule 2)

Four surfaces are dependable and they are the only four: **the Python API**,
**`configure()`**, **the chain profile**, and **the tools and seams in §4**
(added 2026-10-07, triage action 6 (declare public surfaces)). Nothing outside
this folder may depend on anything else here.

### 1. The API

```python
from language_layer import engine
engine.avatars(brand, root=None)      # -> [{key, rows, funnels, has_profile, subs}]
engine.load(brand, avatar=None, root=None)          # -> raw rows, provenance intact
engine.query(rows, use=, topics=, funnel=, speaker=,
             contains=, exclude_assumed=, limit=)   # -> filtered, RANKED rows
engine.render(rows, header="")                      # -> the block a stage reads
engine.for_stage(brand, stage, avatar=, funnel=, topics=, limit=, root=,
                 stage_use=, widen=, title=)        # -> the whole point
engine.topics_of(brand, root=None, top=40)          # -> [(topic, count)]
engine.uses(row)  # -> use tags, always a list
engine.brand_dir / engine.bank_dir / engine.avatar_root   # path resolution
```

`root` given = resolve under that tree and nowhere else. `root=None` = find
the tree by SHAPE, across `LANGUAGE_ROOT`, `<ws>/lab/the owner`, `<ws>`,
`<ws>/components` — which is what lets a caller probe candidate trees
(`avatar_root(brand, cand).is_dir()`, as the copy chain does) and get a
straight answer.

### 2. `configure()` — the host seams

```python
configure(workspace=None, stage_use=None, widen=None, title=None, roots=None)
```

Every seam is optional and unset means unchanged. `workspace` is the host's
own root (its `paths.WORKSPACE`); `stage_use`, `widen` and `title` are the
per-chain settings below.

**One process, one chain.** `configure()` sets module state, so a process that
imported BOTH shims would get whichever configured last. That is fine today —
the two chains run in separate processes, and the third caller
(`lab/the owner/email-production/`) reaches this module through the copy lane
only — but a future caller that needs two chains in one process passes
`stage_use=` / `widen=` / `title=` per call to `for_stage` instead.

### 3. The chain profile — the definitions this engine executes

A stage map is a definition, so the engine ships none: unconfigured, `--stage`
selects no evidence types and the whole bank ranks. A chain hands its own in,
as Python (`configure(stage_use=...)`, what both shims do) or as JSON:

```json
{ "stage_use": { "<stage>": ["<evidence-type>", "…"] },
  "widen": "once" | "ladder",
  "title": "<the header line a stage reads>" }
```

A bare map — no `stage_use` key — is accepted as the map alone.

| `widen` | when a stage's rows come back thin |
|---|---|
| `once` | drop the topic filter if NOTHING matched. The copy chain's |
| `ladder` | relax topics, then funnel, until a floor of `max(8, limit//4)` is met — and say so in the header, because "we widened" is a fact about the bank the reader should see. The video chain's |

**The widening policy is per-chain by the same logic the stage maps are**
(LL-1 (language layer) finding, flagged for the record): the two files had drifted here too,
and the convergence ruling named the base file but not this line. Rather than
discard one chain's behaviour — the card's hard constraint is zero behaviour
change on both sides — it moves out to the chains, where "how thin is too
thin for MY stages" actually belongs. **If the owner and the video chain later
agree on one policy, this parameter should collapse to a constant.** That is a
convergence decision, not a code decision.

### The CLI

```
python3 components/language-layer/query_language.py --brand <b> \
    [--root DIR] [--avatar A] [--funnel F] [--stage S] [--topics a,b] \
    [--limit N] [--profile chain.json] | [--avatars] | [--topic-list]
```

Same flags the two machines always had, plus `--profile`.

### The used lane (2026-09-28)

`<avatar>/language/used/` holds one file per asset a chain wrote (shape:
`brands/language-schema.md`, "The used lane"). `load()` never reads it as bank
rows. `load_used()` / `used_ids()` read it; `query(used="no"|"yes",
spent=...)` and `for_stage(..., used=...)` filter on it; `render()` prints each
row's id in [brackets] so a stage can cite what it used. Rows whose `status`
is retired or burned no longer come back from `query()`. CLI: `--used`,
`--unused`, `--used-log`. Test: `tests/test_used_lane.py`.

### 4. The tools and the seams (the developer, 2026-10-07, triage action 6 (declare public surfaces))

Besides the API, `configure()` and the chain profile, callers may use exactly these:
1. **Names the two shims re-export:** `engine.WORKSPACE` (the resolved root), `engine.TIER_RANK` (`{gold: 0, silver: 1, house: 2, community: 3}`), `engine.load_used` / `engine.used_ids` (the used lane, above), `engine.main(argv)` (the CLI).
2. **The bank tools, as commands** (research-gatherer's daily job runs both): `tools/map_sources.py --brand <b> [--dry-run | --propose-only] [--run R]` — a proposal under `runs/language-layer/<brand>/`; `tools/bank_page.py --brand <b>… [--out --md --note --mirror-of]` — the bank page.
3. **The labeller, loaded by file:** `tools/label.py` — `label(rows, brand, model, batch=20)` → `{row id: labels}`; `origin_of(row, brand="")` and `voice_of(row)` → one word each.
4. **SEAMS, not public:** `engine._uses(row)` (feedback-forms `language_pass.py`, research-gatherer `culture_map.py`, both shims) and `engine._ROOTS` (video-teardown's shim). A seam renamed keeps its old name as an alias until its callers move. `_uses` is now an alias of the public `engine.uses(row)` (language-layer#9 (public uses seam), SI-102 (public uses seam)); feedback-forms calls `uses`, the others stay on the alias.
Everything else here is internal and may change without notice.

## Rules

- **Brand-blind, not brand-aware** (workspace rule 7): no brand, product,
  avatar or category name appears in this code or in a default. A brand is a
  lookup key that arrives at run time; the word never names a behaviour
  branch. Banks resolve under `brands/<brand>/core-avatars/*/language/` —
  rule-9 (brand home).
- **Two bank layouts are accepted**, today's `brands/<b>/core-avatars/` and
  the pre-2026-08-30 `brands/<b>/avatars/core-avatars/`, today's first. Both
  machines went blind the day the folders moved, and an empty roster reads
  exactly like a brand with no banks — pinning one layout is how that happens
  again.
- **`<ws>/lab/the owner` stays in the root probe** because that is where some
  brand trees still live. It is a PATH, read-only — not a dependency on lab
  instruction content (workspace rule 9), and it leaves whether that tree
  winds down entirely to the owner, per rule-9 (brand home).
- **Machine-agnostic** (components rule 8): no credential is read, at import
  time or ever; no network module is imported; nothing is written. The root
  comes from the environment (`LANGUAGE_ROOT`) or from the host's
  `configure(workspace=...)`.
- **Stdlib only** — `argparse`, `json`, `os`, `pathlib`. No dependency, ever;
  this thing runs wherever a chain runs.
- **The stage maps are the chains'.** What a stage is looking for is the owner's
  call on his chains. Changing a map is a conversation with the chain's owner,
  not a change here.

## The declared test

`python3 new-workflow-design/builds/language-layer/test_language_layer.py`
— no pytest, no network, no dependencies, green on **both rails** (3.9
`/usr/bin/python3` and 3.14), so no 3.10+ syntax anywhere in this component.

It proves the move rather than describing it: the video shim exposes **every
public name the pre-move file exposed** (pinned list, cross-checked against
`git show HEAD` when git is available) and its `for_stage`, `query`, `load` …
**are the engine's own objects**, not copies; the same query returns
**byte-identical output** through the shim and through the component entry
point across every stage, both bank layouts, and the avatar / funnel / topic /
limit / no-match paths on a fixture workspace; the engine holds **no evidence
tag of any chain** and an empty map when unconfigured; importing either module
in a fresh interpreter reads no credential and imports no network module;
the copy lab's delivered shim parses and exposes the same public-name set as
his live file; and a sentinel fingerprint over `lab/` and
`components/video-teardown/` (minus the one shim) is byte-unchanged across the
whole run.

## Kill-condition (ruled, carried from the card)

**Fewer than 2 real callers post-convergence → fold the component back into
its caller.** It stands at three today — the video chain (`machine/chain.py`),
the copy chain (`machine/copy.py`) and the email lane
(`lab/the owner/email-production/`, which imports it through the copy lane).

## The language bank standard, its tools and its state (2026-09-29)

One home for everything about customer language — never a lab folder.

| What | Where |
|---|---|
| The rules (lanes by language, awareness, sophistication, origin, voice, row ids, source ids, the used lane, repeats) | `brands/language-schema.md` |
| Why the rules are what they are, with the evidence | `docs/STANDARD.md` · page `docs/standard.html` |
| Label rows (awareness · sophistication · lane the words point to · origin · voice) | `tools/label.py sample\|apply` · prompt `prompts/label-awareness-v*.md` |
| Row ids on the Naming Standard | `tools/rename_ids.py` |
| Source ids + the per-brand source registry | `tools/map_sources.py` (hand calls: `brands/<b>/core-avatars/language-sources-lookup.json`) |
| Check any bank against the naming | `tools/check_names.py --brand <b>` |
| The bank as a page | `tools/bank_page.py` → `runs/language-layer/_system/bank.html` + `BANK.md` |
| Per-brand run output (rename lookups, lane moves, test sets) | `runs/language-layer/<brand>/` |

A brand's own accounts (what counts as internal): `brands/<b>/channels/own-accounts.json`.
