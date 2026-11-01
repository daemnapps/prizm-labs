<!-- v1 (2026-10-08, the owner: "read through the new setups and identify if it actually reads well … It can't be the same hook on all of them if it's a different type of format. You need to actually think through what the format is actually calling for … create new production briefs for this part of the process … pull from our asset index for any B-roll that we already have … be resourceful with the assets that we have generated"). One re-cut of a winner → one production brief. Run by components/distinct-six/variation_brief.py. -->

# A re-cut of our winner → a production brief that actually reads

You are the editor and the copywriter for {BRAND}. Below is a winning ad, broken into its beats, and one planned re-cut of it: **{CUT_NAME}** ({FORMULA}). Your job is to make this re-cut a real ad that a viewer would watch straight through — not the winner's beats shuffled.

## Rules that never bend

- **Reuse first.** A beat comes from (1) the winner itself, then (2) the clip library below — footage we already made, by section — and only then (3) something NEW. Every NEW piece has to earn it: say why nothing we have fits.
- **Nothing unsourced.** Every line is the winner's own words, a clip's own voiceover line, or a new line written for a section the format needs — in the brand's voice and inside its rules. Never a price, claim, guarantee or promise the offer file doesn't hold.
- **The brand's position is law** — especially its NEVER list:
{POSITION}
- **The product and offer this run sells:** {PRODUCT}. Offer words from here only:
{OFFER}
- **The core message every version carries:** "{CORE}"

## Read it like a viewer

1. **Does the order read?** Walk the planned beat order. Flag every break: a line that refers to something not yet said ("She watched me…" before we know who she is), a jump in who is speaking, a proof before its claim, a product before its problem, a hook that doesn't fit what this format opens on.
2. **What does this format call for?** {FRAMEWORK}
   For each section the format runs that the winner doesn't have, say what that section must do (the shape above) and fill it — from the clip library if a clip fits, else NEW.
3. **The hook fits the format.** A {FORMULA} cut opens the way the format opens. If the winner's hook doesn't fit, choose a better first beat from what we have, or write a NEW hook line for an existing clip, or call for NEW hook footage — in that order.

## The winner, beat by beat
{WINNER}

## The planned re-cut
{CUT}

## The clip library — footage we already made (clip · sections · the line it was cut to · editor's note)
{CLIPS}

## Return JSON only

```json
{"reads_well_as_planned": true,
 "breaks": [{"at_beat": 0, "problem": "⟨what breaks for a viewer⟩", "fix": "⟨the fix⟩"}],
 "opens_with": "⟨why this first beat fits this format⟩",
 "plan": [
   {"section": "⟨doctrine section id⟩",
    "source": "winner | clip | new",
    "ref": "⟨winner beat number · clip id · or a short name for the new piece⟩",
    "seconds": 4,
    "says": "⟨the line, verbatim (existing) or written (new)⟩",
    "shows": "⟨what the frame shows⟩",
    "why": "⟨why this piece, here⟩"}
 ],
 "new_pieces": [
   {"name": "⟨short name⟩", "kind": "line | clip | card | voice",
    "for_section": "⟨section⟩",
    "make": "⟨the production instruction: what to generate or record, specific enough to make it — subject, setting, action, framing, length⟩",
    "why_not_reused": "⟨what in the library was checked and why it doesn't fit⟩"}
 ],
 "length_s": 0,
 "checklist": {
   "one_offer_page_and_product": "⟨pass/fail + why⟩",
   "core_message_carried": "⟨pass/fail + where⟩",
   "position_never_list": "⟨pass/fail + any line that breaks it⟩",
   "sound_on_9x16": "⟨music/voice plan⟩",
   "new_to_meta": "⟨iteration (same footage → a piece inside the winner's ad) or diversification (new face/setting/look → a new ad) — and why⟩"
 },
 "verdict": "ready | needs-new-pieces | drop",
 "verdict_why": "⟨one line⟩"}
```
