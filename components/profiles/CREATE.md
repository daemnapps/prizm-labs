# When a profile exists, and how it is made (2026-11-27)

One rule above all: **a profile is a different argument to a different person, proven by customer lines.** Not a different face, product, moment, format or angle. Layer tests are the doctrine's (`marketing-doctrine/slices/people.md`, `words.md`); this file adds the gates a candidate must clear before ads are made for it. A gate that is a number is code (`profiles.py gate`); a gate that is a judgement is recorded as one line with its receipt.

## What never makes a profile

A product · a moment or holiday · a format · an angle (it belongs to the brand) · a demographic alone (age, gender, race, language are a layer, chosen per piece) · a person's role or relationship to the buyer without a different argument.

## The six gates, in order

| # | Gate | Passes when | Kind |
|---|---|---|---|
| 1 | **Layer** | The doctrine's test names which layer it is. New **avatar**: the desire or the problem changes. New **sub-avatar**: one factor (tried, when, where, since, feels, has) changes the argument; swap it and the ad breaks. New **demographic**: swap race, age or language and the ad still works, so it is never a new profile. One line states the factor and the swap. | judgement, one line |
| 2 | **Name** | `people.py check` accepts it: lowercase, kind-first sub name from the closed list, no character, age, race or gender in an avatar or sub name. A new name is signed by the owner. | code, then owner |
| 3 | **Evidence** | At least `MIN_OWN` (25) own customer lines stand under it, each with its receipt. Fewer: it stays a candidate and says what research would fill it; no ad is made for it. | code (`gate`) |
| 4 | **Distinct** | No more than `SAME_PERSON` (50%) of its lines also sit under any one sibling of the same avatar. More: it is a HOLD, and the owner merges it into that sibling (the narrower factor becomes a lens, not a profile) or keeps it with the reason in one line. | code (`gate`), owner decides |
| 5 | **Filled** | `profiles.py check` has no FAIL: card and slots exist, all four doubts with their lines, awareness, stage, name equals the profile's id, every cited line resolves. A lower level is allowed and says `open`; nothing is filled by guess. | code (`check`) |
| 6 | **Filed** | The owner's yes copies the draft card and the slots into the brand folder. Until then it is a draft and every tool reads it as one. | owner |

Order matters: a profile that fails gate 3 or 4 is not built further. Gates 3 and 4 are re-run whenever lines are added (the data moves), so a profile can lose its place and go back to a hold.

## A merge

A hold the owner answers "merge" becomes one entry in the brand's `people-aliases.json` under `merges` (profile id → `into`, `lens`, `why`, `decided`; `demographic` when the lens had its own). From then on: the merged profile is not listed or audited as a profile; asking a tool for it (`--profile <merged>`) resolves to the profile it was merged into (`people.folders`); the keeper shows it as a lens. Nothing is deleted: the merged card and slots stay as drafts, and removing the entry undoes it. The merged profile's own lines are not yet folded into the keeper's slots; that is a refill of the keeper (`who.py fill`).

## How one is made

1. A candidate is named from the lines (a cluster of customer lines that share a factor), never from a persona idea. State the factor and the swap (gate 1).
2. `people.py check sub <name>`. The owner signs the name (gate 2).
3. `who.py build` for the card, `who.py fill` for the slots (the skill `avatar-profile`, steps in order).
4. `profiles.py gate` and `profiles.py check`. A hold or FAIL goes to the owner before anything else.
5. The owner's yes files it. Nothing is written to `brands/` by a tool.

## What the thresholds are

`MIN_OWN` and `SAME_PERSON` are the owner's numbers. They were set from the data on 2026-11-27: across the first brand's 17 profiles own lines run from 5 to 263, and the closest real pair shares 61% of its lines. They are defaults: a brand sets its own in `brands/<brand>/core-avatars/criteria.json` (`min_own`, `same_person`) when its data is smaller or larger. Change the defaults in `profiles.py` and say why here.

## Any brand

Nothing here names a brand. A brand supplies only its own folders:

| Brand file | Holds | Without it |
|---|---|---|
| `brands/<brand>/core-avatars/<avatar>/` | the avatar's `profile.md`, its sub-avatar cards, its language bank | no profiles |
| `brands/<brand>/core-avatars/people.json` | the signed names: `avatars`, `subs`, `demographics`, `merges` | falls back to the brand's entry in `components/naming/people-aliases.json` |
| `brands/<brand>/core-avatars/criteria.json` | optional `min_own`, `same_person` | the defaults above |

A new brand: `profiles.py init --brand <b>` lists every profile and what stands between it and ads (sign a name, build the card, fill the slots, clear a hold). The owner files anything under `brands/`.
