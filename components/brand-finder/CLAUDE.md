# components/brand-finder — where `brands/` is, answered once

**Owner: the developer** — confirmed 2026-10-08 (the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:32:36Z: "go on B1, 2, 3"; decision log 2026-10-08 B1 (owner names); the owner may object). Built under BH-1 on 2026-09-02. Name
RULED by the developer (PLAN batch 23) — `brand-finder`; `brand-home` is only the build
folder's name and the placeholder never shipped. Module `brand_finder`, never
a top-level `paths` or `brandhome`, for the reason LL-1 gave: this component
exists because files with the same job drifted, and a generic name on
everybody's `sys.path` is how the next one starts.

What it is: rule-9 (brand home)'s LOCATOR — "where is `brands/` from here" —
as ~50 lines of stdlib. What it is not: a finder of brand CONTENT, a reader of
anything, or anybody's policy about which tree to prefer.

**Why it exists as one home.** The same question had three implementations,
converging by copy-paste: `lab/copy/machine/paths.py`,
`lab/email-production/paths.py` (which copied copy.py's probing at
7345d2c63 — and the copy is DEAD there, its first candidate can never exist)
and `components/chain-runner/runner/brandhome.py`. Same drift class the
language layer just cured.

## THE DIVERGENCE THIS COMPONENT REFUSED TO FLATTEN

The two lab machines name **different default trees**, and BH-1's kill says a
shared locator must never pick a winner:

| machine | default when `AI_WORKSPACE` is unset |
|---|---|
| `lab/copy/machine/paths.py` | `$AI_WORKSPACE` (the repo root) |
| `lab/email-production/paths.py` | `$AI_WORKSPACE/lab` |

So **this module has no default of its own, structurally**: `workspace()`
takes the caller's default positionally and there is nowhere a fallback could
live. Each machine's default stayed on its own line, exactly where it already
was; the declared test pins both and goes red if a later session unifies them
silently. The judgement behind proceeding rather than stopping — drift, not
policy, but drift with a live behavioural consequence — and the decision
the owner owns are written up in
`new-workflow-design/builds/brand-home/DIVERGENCE.md`.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

| question | answer |
|---|---|
| **engine + owner** | this folder's `brand_finder/` — **the developer** |
| **definitions + curator** | **none here, and that is the point.** The only definition in sight is each caller's DEFAULT TREE, which is the caller's, curated by whoever owns that machine (the owner, for both lab machines). chain-runner declares no default at all — it is handed paths |
| **the plane it emits** | **none — it is a locator library.** A call returns a path string; the CALLER reads, writes and emits. Nothing here opens a file it was not asked about, and `--out` would be meaningless |
| **what the manifest declares per entry** | **n/a** — no manifest, no entries |

## Contract (components/CLAUDE.md rule 2)

The Python API is the whole dependable surface. Four names:

```python
from brand_finder import HOME, workspace, checkout_of, home_of

HOME                       # "brands" — a directory name, never a brand
workspace(default, env="AI_WORKSPACE")   # env override, else the CALLER'S default
checkout_of(path)          # the working tree `path` sits in, or None
home_of(path)              # that checkout's brands/, or None
```

- **`default` is required.** See above. There is no module-level fallback and
  adding one is the change this component was built to prevent.
- **`workspace()` hands `default` back unchanged**, so a caller that has always
  received a `Path` still does. The env value goes through `expanduser` and
  nothing else — not resolved, not made absolute, not checked for a `brands/`
  inside it, because each of those is a decision the caller already made. An
  **empty** `AI_WORKSPACE` falls through to the default; that is the original
  `if env:` behaviour and it is pinned in the test.
- **`checkout_of` probes upward for `.git` and the path NEED NOT EXIST** — a
  root naming a directory nobody created yet is still a declaration, and it is
  the declaration rule-9 reads. A `.git` that is a FILE counts: a linked
  worktree is a checkout.
- **A caller needing both the checkout and its home calls `checkout_of` and
  joins `HOME`** (chain-runner does, because it reads a path's segments
  relative to the checkout). `home_of` is the one-call form for everyone else.

## The three consumers

| consumer | what it takes | what stayed its own |
|---|---|---|
| `lab/copy/machine/paths.py` | `workspace()` | `HERE`, and its default tree |
| `lab/email-production/paths.py` | `workspace()` | `HERE`, and its default tree |
| `components/chain-runner/runner/brandhome.py` | `HOME`, `checkout_of` | **all of the FINDING logic** — which declared roots take brand content from outside the home, the CR-7 table, the messages |

The two lab files are thin shims with their public names unchanged
(`HERE`, `workspace`, `WORKSPACE`) — the only two files BH-1 wrote under
`lab/`, per the LL-1 shim-placement ruling. Nothing about a run on either
machine changes.

**The fourth copy is folded — into run-kit, not here** (2026-10-07):
`components/chain-runner/runner/run.py`'s `repo_root()` now delegates to
run-kit's `paths.repo()`, the one workspace locator (triage page 12; SI-64
(runner repo root)), and returns None when that root does not contain the
start folder. brand-finder's own walk stays the no-policy primitive.

## Rules

- **Brand-blind** (workspace rule 7): no brand name appears here and none can.
  `HOME` is a directory name; the brands that exist are read out of the tree
  by the caller, at check time.
- **No policy.** No default, no preference between trees, no "probe this one
  first". Where two callers disagree, they disagree in their own files.
- **Reads nothing.** It answers with paths. It never opens a brand file, and
  `os.path.exists` on a `.git` is the only filesystem question it asks.
- **Machine-agnostic** (components rule 8): no credential is read, at import
  time or ever; no network module is in the import graph; nothing is written.
- **Stdlib only, one module: `os`.** No dependency, ever — this thing has to
  run wherever a chain or a machine runs.

## The declared test

`python3 new-workflow-design/builds/brand-home/test_brand_home.py` — no
pytest, no network, nothing written outside a temp directory, green on **both
rails** (3.9 `/usr/bin/python3` and the default python3), so no 3.10+ syntax
anywhere in this component.

It proves the move rather than describing it. The pre-BH-1 behaviour is
**pinned in the test as source** and not fetched from git — once this card is
committed `git show HEAD` returns the SHIM, so a git-sourced baseline would
quietly compare the new code with itself. Against that pin: each shim's
`workspace()`, `WORKSPACE` and `HERE` are byte-identical before and after
across unset / absolute / `~` / EMPTY / relative `AI_WORKSPACE`; each still
exposes every public name it did; and the two defaults are pinned EQUAL (the owner, 2026-09-09).
The locator is byte-identical to the old probe over the quirks that matter —
a nested checkout, a `.git` file, a path that does not exist, a path under no
checkout, the filesystem root. chain-runner's CR-7 table is re-run against a
**miniature checkout the test builds** — its own `.git`, its own home holding
two INVENTED brand names, content trees outside it — and the brand-named-copy
finding still fires on a name this code has never seen, which is the proof the
names come from the tree. Plus: `workspace()` refuses to be called without a
default (BH-1's kill, asserted); a fresh interpreter importing the component
pulls in no network module; and a sentinel fingerprint over the trees around
the three touched files is byte-unchanged across the whole run.

The chain-runner suite (`test_chain_runner.py`) is the other half of the
acceptance surface and must stay green — this component changed one file in it.

## Kill-condition

**Fewer than 2 real callers → fold it back.** It stands at three. And the
sharper one, carried from the card: **the day a caller needs this module to
carry a default, or to prefer one tree over another, the flattening BH-1
refused has arrived by the back door** — that is a convergence decision for
the machines' owner, made in the open, never a parameter added here.
