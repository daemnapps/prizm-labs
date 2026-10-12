# What's left to fix in the other prompts

**For the owner and the dev.** Stage 5 v7 was made agnostic and given proper slot
handling in this session. These are the same problems everywhere else, found by
reading the current heads on 2026-08-19. **Nothing here has been changed** —
this is the list to work from.

Note: 4a, 4b and 4c advanced mid-session (v1 → v3/v4/v4, with the v1s moved to
`superseded/`). This audit is against the new heads.

---

## 1. Baked gender — 5 prompts

Workspace rule 7 says no prompt assumes a brand. The same argument applies to
assuming the customer or the speaker is a woman: it silently breaks the moment
this chain points at a product sold to men, or to both.

| Prompt | Hits | Who the "she" is | Severity |
|---|---:|---|---|
| `stage4b-hook-v4-damon.md` | **17** | the viewer | **Worst.** The whole hook philosophy is written about a female viewer |
| `stage4c-expansion-v4-damon.md` | 5 | the viewer | Moderate |
| `stage4e-audit-v1-damon.md` | 3 | the speaker | Low |
| `stage4a-placement-v3-damon.md` | 2 | the viewer | Low |
| `stage4d-close-v3-damon.md` | 2 | the speaker | Low |

Clean already: stage 1, stage 2, stage 3, stage 5 v7.

**Worth knowing before the fix:** the "she" is not the same person in every
prompt. In 4a/4b/4c it is the **viewer**; in 4d/4e it is the **speaker**.
Whoever fixes this should use the role name — *the viewer*, *the speaker*, *the
maker* — rather than swapping in "they" everywhere, because naming the role is
what actually removes the assumption.

4b is the real job. Lines like *"finish a sentence she has already started"* and
*"a private moment she thought nobody saw"* are not decoration — they carry the
method. They need rewriting, not find-and-replace.

---

## 2. Baked category — 1 prompt

`stage3-injection-v3-damon.md`, lines 23–24. The worked example is skincare:

> "...because it's loaded with X to do Y to **skin that looks like this**" ...
> "...to **skin** that..."

Everything else is clean. One example to re-cut generically.

---

## 3. Slot handling — the part that will actually bite

### 3a. A category-specific fact is hardcoded in a generic stage

`stage4c-expansion-v4-damon.md` still contains the literal string
`[SLOT: substantiated customer count]`.

That is one product's missing fact written into a stage that is supposed to work
for any product. It is also the non-canonical spelling — the registry carries it
as an *alias*, not a name. **If T-33 rules option (a) — remove the count claim —
this line has to go with it.**

### 3b. No stage emits canonical slot names

The registry (`slots/registry.json`) expects `[SLOT: fact_id]`, lowercase
snake_case, because the safety greps only match `[a-z_]+` — a capital letter
makes a slot invisible to every check in the build.

What the stages actually emit today:

| Prompt | Emits | Canonical? |
|---|---|---|
| stage 3 | `[SLOT: identity_anchors — role]` | yes |
| stage 3 | `[SLOT: what's needed]` | **no** — free text |
| stage 4a | `[SLOT: …]` | **no** — shape only, no naming rule |
| stage 4c | `[SLOT: substantiated customer count]` | **no** — spaces |
| stage 4d | `[SLOT: …]` | **no** — shape only |

This is exactly how the chain ended up with **17 spellings for 6 facts**.
**No prompt anywhere points at the registry.** The fix is one sentence in each
stage naming the canonical form, plus a pointer to the registry as the list.

### 3c. "Slot" means two different things

`stage2-replication-v2-damon.md` defines **INJECTION SLOT** — which brand
material fills a structural element. That is not the same as `[SLOT: …]`, a fact
nobody has. Two concepts, one word, in adjacent stages. Rename one.

### 3d. Cut-vs-rewrite is now inconsistent across the chain

Stage 5 v7 was just given an order of preference: **fill → rewrite the beat →
cut**, and never invent the fact. Upstream stages have no equivalent:

- 4d: *"Carry the slot forward unfilled."*
- 4a: *"do not describe the fact... slotted out"*

That is defensible — stage 5 is the resolver, upstream just carries. But it
means **every rewrite burden lands on stage 5**, and nothing upstream is
thinking about whether a beat can survive its fact going missing. Worth a
deliberate ruling rather than leaving it as an accident.

### 3e. The audit stage contradicts the new rule

`stage4e-audit-v1-damon.md` SHIP condition: *"all seven checks pass, slots are
flagged not filled"* — i.e. a script full of slots can SHIP.

Under stage 5 v7 that is survivable, because stage 5 now rewrites rather than
cuts. But 4e is the gate, and a gate that passes unresolved facts is not gating
that. **4e has also never run — zero outputs — so none of this is enforced
anywhere today.**

---

## Suggested order

1. **4c's hardcoded customer-count slot** — it is a live wrong thing, and it is
   tied to T-33 which is already on the owner's list.
2. **Canonical slot naming, one sentence per stage** — cheap, and it is what
   makes the checker work across the whole chain instead of just stage 5.
3. **4b's gender rewrite** — the biggest single job, and the one that most
   limits which brands this chain can serve.
4. **4a / 4c / 4d / 4e gender** — small, mechanical once the role names are
   agreed.
5. **stage 3's skincare example** — one paragraph.
6. **The 4e SHIP criterion** — but that stage needs its hold-only recut anyway
   (audit finding 1), so fold it into that.
