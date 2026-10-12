# research-gatherer — what an audience is saying, and where

**research-gatherer** — takes **a brand and an avatar** (its desire words, its
demographics, the rooms it talks in), makes **what that audience is saying and
where — rooms, posts, language**: verbatim rows with a permalink each, filed
into the sub-avatar's own language bank, plus a run record. Does not **write
copy**, hold a stage map, or know any brand. Triggered by
`python3 components/research-gatherer/gather.py deep --brand B --avatar A --sub S`
(`rooms` for room discovery alone · `voiceprint` for a brand's creators ·
`--dry-run` on any of them spends nothing).

**Owner:** the owner (engine). Extracted 2026-09-18 (RG-1) on his ruling that the
gatherer is a resident component, not code inside one machine. The full story,
the API and the rulings behind each behaviour are in `README.md` — read it
before changing anything here.

## Who calls it — keep these working

- `tools/video-teardown/machine/research.py` — a thin shim over this
  engine (same CLI, same output, same cache).
- `tools/copywriter/machine/research.py` — the second shim.
- The nightly pull on the owner's Mac (`gather.py deep --brand <b> --pick-thinnest`).

Every existing command and flag stays as it is. New behaviour is added, never
swapped in.

## The four questions

- **Engine + owner:** `research_gatherer/engine.py` (+ `gates.py`,
  `voiceprint.py`), the owner.
- **Definitions + curator:** three kinds, none of them here. Chain profiles
  live in each chain's own shim. Desire words, demographics and rooms are
  avatar content under `brands/<brand>/core-avatars/**` (rooms are FOUND by the
  engine; a person locks a block with `confirmed by: <name>`). The research
  questions are the marketing-doctrine component's
  (`components/marketing-doctrine/frameworks.json` › `research_questions`),
  curated by the owner there.
- **The plane it emits:** none of its own. `inputs()` writes into the CALLING
  chain's run folder. `deep_for()` writes rows into the sub-avatar's own bank
  and a run record at the repo-root `runs/research/<brand>/<sub>-<date>/` —
  never inside this component.
- **Manifest per entry:** n/a — `research.json` is config (actors, spend caps,
  cache days, the discovery search's shape, the demographic marker table, the
  gate modes), not a registry.

## Own voice, comments, and what every filed row carries (added 2026-09-28)

the owner's rulings, same day: pull the brand's OWN audience into the bank from
inside this component ("build inside of there"), and give every row the
gatherer writes the bank's new fields (`brands/language-schema.md`, "Lanes by
language …" and "Row ids", both 2026-09-28).

- `gather.py ownvoice --brand B` — `research_gatherer/ownvoice.py`: support
  emails (warehouse Gorgias, customer tickets only) and ad comments (warehouse
  `meta_ad_comments`, then the top-spend ad posts scraped through
  `components/apify`), sources read from the brand's `operations/brand.json`.
  Cursor: `runs/research/<brand>/ownvoice-state.json`.
- `gather.py comments --brand B [--sub S] --url <post>` —
  `research_gatherer/comments.py`: the comment section of any TikTok,
  Instagram or Facebook post, permalink per comment. With `--sub` the rows go
  to that sub-avatar's own `language/` folder and nowhere else.
- The deep pull's rows (`deep_for`) pass through the same labeller before they
  are written; with no labeller they go out as before, with a standard id.

Every row is read twice (`research_gatherer/annotate.py`): the INTAKE read
(`prompts/annotate-row.md` — keep/drop, exit, use, topics, sub, ad use, names
and signature to strip; a definition the owner curates, shown word for word on
every run page) and the language layer's own LABELLER
(`tools/language-layer/tools/label.py` — awareness, sophistication,
lane_words), called, never restated. The lane: an order on file decides;
otherwise the labeller's `lane_words`. A row either read cannot answer is
HELD, never guessed, and the cursor does not move. Ids:
`language_<brand>_<avatar>_<lane>_<NNNN>`, numbered across the avatar bank.
Every run writes `runs/research/<brand>/<mode>-<run>/` with `report.md`
(rows per lane, per awareness level, per sub-avatar, the thin levels),
`filed/dropped/held.json` and `page.html`. The team skill `/voice-pull` is how
a person asks for it. Tests: `test_ownvoice.py` (no network, no model).

## Gates

A deep pull writes `check.json` into its run folder
(`runs/research/<brand>/<sub>-<date>/check.json`), keyed by gate, through the
shared `components/quality-checks` `hold()`. A gate that fails reads `HELD`.
The code is `research_gatherer/gates.py`.

| Gate | When | What it checks | On a fail |
|---|---|---|---|
| **inputs** | before anything is pulled | the sub-avatar file exists; there are rooms to pull from (on file, or found) | nothing is pulled, nothing is spent — as before; now recorded |
| **elements** | before anything is pulled | every doctrine technique or delivery dial a research question names is a real one in `components/elements` (`doctrine/technique`, `delivery/<dial>`) | the pull is held before a cent is spent, with the real ids named |
| **delivery** | before rows enter the bank | every row carries a permalink; no row from a room that does not match the avatar's demographics; there is something to file | nothing is filed — as before; now recorded |

What passes and fails did not change when the gates were added: a row with no
permalink was never written, a row from a mismatched room was never filed.
The gates are where that is now written down. The elements gate is the one
new refusal; `research.json` › `gates` › `elements: "record"` writes the
problem down and pulls anyway. A dry run reports what the elements gate would
say and writes nothing. If the element library or quality-checks cannot be
reached, the pull goes on and `check.json` says the check was not run — the
engine never raises.

Research questions whose `framework` names a whole doctrine block (desire,
awareness, sophistication, mood, verification, spoken.levels) have no list to
be looked up on, so nothing is claimed about them.

## Rules

- **Brand-agnostic.** No brand, avatar or room name in this code, in
  `research.json`, or in a test fixture that looks like a real one.
- **Never raises.** No key, a 403, a missing actor, a missing shared component
  — the section says `[UNFILLED: why]` and the caller moves on.
- **A row with no permalink is never written.**
- **Spend is capped and printed**; pulls cache 14 days under
  `runs/research-cache/_system/`.
- **The workspace is found, not assumed:** `AI_WORKSPACE`, else the checkout
  this file sits in, else `the workspace`. A shim's
  `engine.configure(workspace=...)` still wins.
- **`sys.path` is appended to, never inserted at 0.**

## Tests

```
python3 components/research-gatherer/test_research_gatherer.py   # the engine
python3 components/research-gatherer/test_gates.py               # the gates
```

No network, no model, no Apify, temp folders only — a test never writes into
the real `runs/` or `brands/`. In a worktree, export `AI_WORKSPACE=<worktree>`
first. The video-teardown shim's tests live in
`tools/video-teardown/machine/` (`test_rollout.py`, `test_compose.py`).
