# Variables — the whole chain

**Rule: no prompt names a brand, product, category, avatar or customer.** Brand context
enters only through these variables. **Where each variable resolves for a
given brand is stated in exactly one place — the brand's chain-variables
map.** Production home: `brands/<brand>/chain-variables.md`. While a brand's
chain work is pre-production it lives in the owner's lab folder instead —
**`<brand>/chain-variables.md`** (with the hook
ledger beside it), per Damon's 2026-08-18 ruling that nothing from these
runs enters the brand folder before graduation. A run pulling from a path not in that
map is a defect. Zero variance: a variable name in a prompt must appear in
one of the tables below, spelled identically, or the prompt does not run.

Audited 2026-08-18 against every current prompt (Damon's zero-variance
ruling). The audit's own lesson is encoded in the check at the bottom: the
old grep pattern missed digits, which is how `{stage4_outputs}` went
undocumented.

## Produced by the chain — nothing to create

| Variable | Made by | Consumed by |
|---|---|---|
| `{teardown_record}` | stage 1 | 2, 3, 4a, 4b, 4c (scenes/rhythm only — never structure, never lines) |
| `{replication_spec}` | stage 2 — **the construct**; structure is read from it, never re-derived | 3, 4a, 4b, 4c, 4d |
| `{specs_with_metrics}` `{teardown_records}` `{n}` | the ten specs + records fed to stage 2b (parked) | 2b |
| `{baseline_injection}` | stage 3 — the only source of script lines downstream; its CHARACTERS and SCENES sections are the ai brief's casting and per-scene instructions | 4a, 4b, 4c, 4d, 5·ai |
| `{placement_plan}` | stage 4a — includes the whole-asset runtime budget (v2) | 4b, 4c, 4d |
| `{hook_set}` | stage 4b — control + variations, each a line + scroll stopper; **all ship to test** (DECIDED 2026-08-18), the human gate is QA. Replaces `{chosen_hook}`, retired with the pick itself. | 4c, and rides into `{stage4_outputs}` for 5 |
| `{expanded_script}` | stage 4c — one body, built to carry any hook in the set | 4d |
| `{full_script}` | stage 4d | 4e (parked); rides into `{stage4_outputs}` for 5 |
| `{stage4_outputs}` | assembled per brief run: **for each source format, the 4d full script + the 4b hook set that heads it** | 5·creator, 5·ai |
| `{general_brief}` | the general lane's output | match |

## Supplied per brand — resolved by the brand's chain-variables map

| Variable | Canonical role | Used by |
|---|---|---|
| `{avatar}` | the core avatar file | 3, 4b |
| `{language_bank}` | the customer language bank | 3, 4b, 4c, 5·all |
| `{objection_bank}` | the objection bank | 4a, 4d |
| `{product_file}` | the product spec for the product being sold | 3, 4a, 4c, 4d, 5·all |
| `{offer_file}` | prices, guarantee wording, never-pair rules | 3, 4c, 4d, 5·all |
| `{hook_ledger}` | every hook already generated; human-owned statuses | 4b |
| `{identity_anchors}` | who may appear on camera | 3 |
| `{position}` | the brand's `position.md` — its LINE, SPINE, MECHANISM, MARKET STAGE and what the stage LEADS WITH, as labelled slots (added 2026-09-19). The audience stage checks the swipe's market read against it; injection carries the mechanism in its named words; hooks are tested against LEADS WITH; placement budgets a beat for the line; compose makes the mechanism section mandatory when the stage leads with one | 1b, 2f, 3, 4a (placement), 4b |
| `{story}` | the brand's `story.md` — its storytelling framework beside the position: SPINE, TELLERS, ENTRY, STORIES with their beats, tellers and the avatars each fits, REASON TO SWITCH, OPENS IN, PRODUCT ENTERS, PROOF, VOICE, NEVER (added 2026-09-19). Filled by the run (`~story`): `[UNFILLED]` for a brand with no file; after 1b, the run's pick (`THIS RUN'S STORY: STORY · TELLER`) is appended. The audience stage picks the story and teller; injection tells that story in that teller's mouth; compose gives every beat a phase; hooks open the story; expansion carries its middle; spice speaks it in the teller's voice | 1b, 2f, 3, 4b, 4d (expansion), 4g |
| `{brand_name}` | literal value, not a file | 3 |

`{hook_ledger}` (added 2026-08-18, Damon's anti-repetition ruling): 4b
treats a ledgered verbatim as spent and appends its own rows after each
run. Measured cause: the cardigan-in-July verbatim hooked in four out of
four runs before the ledger existed.

## Supplied at run time — human-provided values

| Variable | Source | Used by |
|---|---|---|
| `{production_route}` | chosen per run — founder, creator, AI (`--route`; default creator, the original brief). The run's choice overrides the shared config's pinned "=creator" and picks the stage-5 lane; founder falls back to the creator brief until a founder brief is cut. The ai brief does not read it — its lane IS the route | 3, 5·creator |
| `{creator_profile}` | the creator's dossier — the creator lane's core input | 5·creator |
| `{creator_profiles}` | the roster's dossiers (each creator's JSON/MD profile) | match |
| `{video_count}` | the contract — never inferred | 5·creator |

**Nothing needs to be made.** Every file behind every variable exists, and
the per-brand map says where.

## Retired

| Was | Why |
|---|---|
| `{brand_material}` | Vague catch-all for four files. Split into `{product_file}` and `{offer_file}`. |
| `{proven_messaging}` | **Invented — no file behind it.** Prompts using it were silently running on whatever the brand folder held. Removed. |
| `{product_details}` | Renamed `{product_file}` so stages 3 and 4 name the same file the same way. |

## The customer count

Move 2 in stage 4c needs a **substantiated customer count**. It is not a
missing file — it comes from the **store APIs, landing in a Supabase table**
(Damon, 2026-08-15). Until that table is wired, 4c writes
`[SLOT: substantiated customer count]` rather than inventing one; once it is,
the number is read, never typed.

## Interchange axes — where this is going

**Not built yet. Recorded so the design does not drift.**

The prompts are fixed; the variables are the sockets. Three of them are meant to
be swapped, which is what turns this from a pipeline into a matrix:

| Axis | Variable | Swapping it gives you |
|---|---|---|
| **Product** | `{product_file}` | The same proven format selling a different product |
| **Avatar** | `{avatar}` | The same format and product aimed at a different customer |
| **Format** | `{replication_spec}` | A different proven structure carrying the same message |

Products × avatars × formats is the combination space. A format library is
just a folder of `{replication_spec}` outputs.

Two further axes, recorded 2026-08-18 (Damon) — context for design, not
built:

- **Awareness transforms.** A finished script or brief re-rendered for a
  different awareness entry — the same asset as an unaware ad, a
  solution-aware ad, a most-aware ad. The next layer after stage 4 settles;
  4b's foundational-hook analysis (context / structure / awareness) is the
  first piece of machinery shaped for it.
- **Market research** alongside customer research as a hook seam. No
  variable yet because no stable file exists behind it (the retired
  `{proven_messaging}` is the cautionary tale); when a per-brand
  market-research file lands, it becomes a 4b input.

The end state Damon has named: every unique element of the system defined
in a data file (MD/JSON) in this repo, so the whole thing runs dynamically
and each role gets a clean surface over it. Build accordingly — anything
minted here should be a file another pass can read, not prose trapped in a
session.

**Two constraints this puts on everything above**, worth knowing before the
swapping starts:

1. **A prompt that assumes a specific product, avatar or format cannot be
   swapped into.** This is why the brand-agnostic rule is structural rather than
   tidiness — a category example baked into prompt text silently breaks one cell
   of the matrix.
2. **`{language_bank}` does not travel with `{product_file}` automatically.**
   The bank is written against a specific product; swapping the product without
   checking whether the language still applies is how a scrub's vocabulary ends
   up selling a cream. Either the bank is scoped per product, or the swap needs
   a compatibility check.

## Checks before committing

```bash
grep -hoE '\{[a-z0-9_]+\}' stage*.md | sort -u   # every variable in use — pattern MUST include 0-9 ({stage4_outputs} hid from the old [a-z_] pattern for a week)
grep -rniE '<brand>|<category terms>' stage*.md  # brand leak check
grep -c '^## ' stage*.md                         # must be 0 — house style has no md headers
```

Every name that grep prints must appear in a table above, spelled
identically. A name it prints that the tables don't carry is the exact
defect the 2026-08-18 audit existed to remove.
