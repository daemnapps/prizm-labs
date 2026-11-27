# Where the cast lives, and where the avatars live

**Ruled by the owner, 2026-09-22.** *"We need to keep the ai cast separate from the
avatars technically. Avatars should just be information about people / market…
they live in brand designated ai-cast folders and can be referenced back to
core-avatars if it makes sense, or if they're authority figures for our core
avatars."*

## The two ends

| | `core-avatars/` | `ai-cast/` |
|---|---|---|
| **What it is** | INFORMATION — who the market is, how they talk, what they object to | PEOPLE — generated characters the brand owns, and their pictures |
| **Holds** | profiles, sub-avatars, language banks, objection banks | one folder per character: `character.md`, the banked masters, and `casting/` |
| **Never holds** | a face, a picture, a cast member | a market insight, a language bank |

## The link points ONE WAY

A cast row names the core avatar it serves, in its `lane` field. The avatar
files name nobody. The cast points back at the avatars; the avatars never point
forward at the cast.

Why: an avatar is a fact about the market and outlives any character. A
character is a thing the brand made and may replace. If the avatar file named
the character, replacing the character would mean editing a market record —
which is how a market record stops being true.

- `lane` — the core avatar this person serves. One.
- `sub` — the sub-avatar, where the person is that specific.
- `also_plays` — other avatars they can cover.
- On an authority row, `fronts` says which slot they front FOR that avatar.

## Two kinds, one folder

- `casting/roster.json` — people who play the CUSTOMER, or supporting figures.
- `casting/authority.json` — people the customer BELIEVES: the source, the
  explainer, the professional. An authority figure exists for an avatar; that
  is the whole point of the `lane` on their row.

Both are read by `components/casting`, which answers two questions:

    who plays this role?          cast.py who    --brand <b> --role "<role>"
    who do we have for this one?  cast.py avatar --brand <b> [--name <avatar>]

An avatar with people to play it but **no authority figure** is a real gap —
nobody to be believed by that market — and the second command prints it.
