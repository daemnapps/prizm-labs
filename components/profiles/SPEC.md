# The profile standard (2026-11-27)

A profile is ONE unit with ONE name (naming/PEOPLE.md): `<avatar>[_<sub-avatar>][_<demographic>]`. A demographic is one layer of it, never the whole thing. Every tool takes a person by that name, through one door: `profiles.load(brand, name)`.

## Every profile has every part

| Layer | Part | Built by | A part with no customer line is |
|---|---|---|---|
| Card (the person on one page; sub-avatar level) | desire · opening · doubt · experiences · emotions · behaviors · culture | `who.py profile` | `open`, with its question in `missing` |
| Slots (the deep bank) | desires · roles · beliefs · experiences · behaviors · emotions | `who.py fill` | `open`, with its gap in `gaps` |
| Slots | doubts: all four kinds (does-it-work, for-me, worth-it, trust-you), each with its line and row | `who.py fill` | a fail: the standard needs all four |
| Slots | awareness level · market stage | `who.py fill` | a fail |
| Name | the id equals `people.profile(...)["id"]`; draft and filed card carry that id | `who.name` | a fail |
| Receipts | every line a card part cites is in the card's `lines` | `who.py profile` | a fail |

A whole avatar (no sub-avatar) has slots and its own `profile.md`; the card parts read `n/a`.

## Levels may differ, structure may not

- **Fail** = structure broken: no card or no slots, a name that is not the profile's id, a cited line that is not there, a missing doubt kind, awareness or stage.
- **Note** = a level is lower: an `open` part, a thin part (below `profiles.THIN`), slots not signed, a card still a draft, no demographic yet.
- Nothing is filled by guess. An empty part says `open`.

## Rules

1. A profile is built by `who.py` (card, then slots). It is never written or edited by hand.
2. A draft lives under `runs/creative-strategist/<brand>/profiles/`; the owner's yes files it in the brand folder. Nothing here writes `brands/`.
3. A tool names a person with `--profile` and no other way. The door is `naming/people.folders` (the names) and `profiles.load` (the person). `profiles.py doors` lists every tool still around it.
4. A new avatar, sub-avatar or demographic name is the owner's to sign (`people.py check`).

5. When a profile may exist at all (layer, evidence, distinctness) is `CREATE.md`; `profiles.py gate` runs its numbers.
