Derive the ledgers for this piece from its production document, and check
them against each other for contradictions before anything is generated.

**Every example in this prompt is illustrative only.**

The ledgers are the anti-drift backbone: written once, pasted into every
scene prompt that needs them. Their value is that they are *checkable* — a
contradiction between two ledgers is a broken piece, caught here for free
instead of in a render.

---

THE PRODUCTION DOCUMENT

{production_document}

THE FORMAT PROFILE

{format_profile}

---

Return exactly these sections.

## THE LEDGERS

Write out each ledger this format uses, as a table, complete for every
scene. Where the production document already states a ledger, reproduce it
exactly — you are not re-deciding, you are consolidating. Where it states
a fact in prose that belongs in a ledger, lift it into the table.

For a ledger this format does not use, write its name and `— not used in
this format`, so a reader knows it was considered.

**Entrances** · scene → who enters, or `closed`.
**Positions** · role × scene → first-frame position as `x≈n% y≈n%`.
**Objects** · scene → holder, state, and any handoff.
**Camera** · the axis never crossed; scene → left-to-right screen order.
**Atmosphere** · scene → the value, as a number or percentage.
**Wardrobe** · role → the block pasted verbatim into every scene.

## CONTRADICTION CHECK

Go through these checks and report each one as `OK` or a specific failure.
A failure names the scenes involved and what disagrees.

1. **Entrance count** — does any character enter more than once across the
   whole piece?
2. **Presence before entrance** — is anyone positioned inside a scene
   earlier than the scene they enter in?
3. **Position continuity** — does any character jump across the frame
   between consecutive scenes with nothing in the mechanics moving them?
4. **Screen order versus positions** — does the camera ledger's order for
   a scene match that scene's position row?
5. **Object custody** — is the product held by two people at once, or held
   by someone who is not in that scene, or does it change hands in more
   scenes than the document allows?
6. **Atmosphere direction** — does the value move backwards without the
   mechanics giving a reason?
7. **Wardrobe stability** — does any role's outfit change between scenes
   without the document scheduling the change?
8. **Distinctness** — could any two roles be confused with each other on
   their locked appearance alone?

## VERDICT

`CLEAN` if every check passed, or `CONTRADICTIONS` followed by the
numbered failures. A piece with contradictions does not go to generation —
the production document gets fixed first.

---

Write the ledgers and the check, and nothing else.
