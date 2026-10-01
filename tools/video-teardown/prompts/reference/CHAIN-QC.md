# Chain QC — the line-item check run against every stage output

One pass per stage, run after the stage completes, before its output feeds
the next stage. Every item is checkable by looking — no judgment calls. An
item that fails is a defect in the output or the prompt, never something QC
fixes silently. Record PASS / FAIL / N/A per line, per run.

**Stage 1 — teardown**
- [ ] All four sections present: Objective Record, Scene Mechanics, Psychology, Index
- [ ] Character & Setting profile covers who / wardrobe / setting / props
- [ ] Table has all six columns (Timestamp · Roll · Visuals · On-Screen Text · Transcript · Sound), no merged rows, one row per frame
- [ ] Every row carries one Roll label (A · B-over · B-vo · B-silent · C); every non-A row opens Visuals with its `[shows: …]` tag
- [ ] The record closes with a Roll sheet — the counts and the make-list of every shot that is not the speaker
- [ ] Transcript and on-screen text kept separate
- [ ] `Breaks if cut:` present per phase; `Belief shift:` present per play
- [ ] Accuracy markers used where footage is unclear — or their absence plausible
- [ ] `[ARTIFACT: …]` used for watermarks/editor junk if any exist
- [ ] Observation only — no evaluation of brand or product
- [ ] AI tells recorded if present (synthetic voice, avatar drift, generated b-roll)

**Stage 2 — replication spec**
- [ ] Format named in one sentence
- [ ] Structural skeleton: every phase with duration, fixed-position, fixed-or-flexes
- [ ] Element inventory: each element has MANDATE / SOURCE INSTANCE / INJECTION SLOT
- [ ] Script architecture: each line-slot has its job and source line
- [ ] Load-bearing list present; swappable list present
- [ ] Brand-free — no source brand leaks into mandates as a requirement

**Stage 3 — injection**
- [ ] One output line per source line, same order — no beats merged or dropped
- [ ] Lines with no brand content copied verbatim
- [ ] Only brand-specific words swapped; register and length held
- [ ] Every missing fact is a `[SLOT: …]`, never an invented number
- [ ] Rule collisions written as the structure demands AND reported in CONFLICTS
- [ ] Characters and scenes sections present; production instructions per scene

**Stage 4a — placement**
- [ ] Lane is exactly one of the four labels, spelled exactly
- [ ] Placement beat quoted from the teardown record
- [ ] Opening beat named by timestamp
- [ ] Awareness entry and exit rungs stated
- [ ] Runtime budget is a ledger covering body + objection + close + ceiling (v2)
- [ ] Device check read against the objection bank; collisions named
- [ ] One named risk, specific to this asset

**Stage 4b — hooks**
- [ ] Foundational hook cited from the spec (phase bounds, element mandates, premise) — not derived
- [ ] Control is a straight swipe — only brand/category words changed
- [ ] Exactly five variations; no two share their first four words
- [ ] Every variation: line + scroll stopper + verbatim-in-full-sentence + source + axis + speaker assumption
- [ ] Scroll stopper is an event (something happening), not a camera setup
- [ ] Every hook names this brief's one discrete problem, in the avatar's dominant word
- [ ] No verbatim already spent in the ledger (unless validated, returning as itself)
- [ ] No banned template openers
- [ ] BRIEF VARIATION OPPORTUNITIES section present (or "none")
- [ ] LEDGER ROWS append-ready; no status beyond control-ran/offered
- [ ] No recommendation anywhere

**Stage 4c — expansion**
- [ ] Every `[SOURCE]` row is character-identical to its baseline line (diff them)
- [ ] Opening is the control head, tagged as the hook cell
- [ ] Each of the four moves: named baseline line proving not-needed, OR reason + spec element served
- [ ] Every `[ADDED]` beat names its spec phase and mandate
- [ ] Hook compatibility table: one verdict per hook in the set
- [ ] Runtime ledger is arithmetic on the page; over-budget flagged with the uncut beat named
- [ ] SLOTS entries contain no digit, no quote, no "e.g."
- [ ] Spine intact phase-by-phase against the spec skeleton

**Stage 4d — close**
- [ ] Every carried beat character-identical to the expanded script (diff them)
- [ ] Objection line: flinch quoted, bank objection named, placed immediately after the beat that raises it
- [ ] Ending device kept if the spec marks it fixed/load-bearing; close is a continuation
- [ ] Guarantee quoted exactly as the offer file records it
- [ ] Prices only from the offer file, channel named if two exist
- [ ] Three runtime numbers on one line; overshoot flagged with breakdown
- [ ] Upstream slots carried unfilled, never generalised
- [ ] Variation section: used with full rule compliance, or "not used" with reason

**Stage 5 — brief**
- [ ] Zero `[SLOT: …]` anywhere in the maker's document
- [ ] Every cut slot listed in the internal document
- [ ] Claim trace: one row per claim, each naming its file, or REMOVED
- [ ] Every approved hook variation present — none dropped, none ranked, control marked
- [ ] Scroll stopper rides with each opening
- [ ] Route respected: directions for a creator, script for the brand
- [ ] No process jargon in the maker's document
- [ ] Guarantee wording exact; price channels explained
- [ ] Test matrix in the internal document
- [ ] Concept provenance and Rejected sections present
