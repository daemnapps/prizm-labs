# The prompt boilerplate — thirteen slots, in one order

Ruled 2026-09-14, after Damon: *"whenever we do regenerations and similar
work, things don't stay in place… what I need is consistency."*

## Why things moved

A prompt written as prose has no parts. Re-roll it and the whole paragraph is
rewritten: the man's age drifts, the light changes, a lens appears in the
scene, and nothing in the system can say which of those was intended. **The
prompt was the unit, so the prompt was what varied.**

So the prompt stops being the unit. **The slots are.** A prompt is rendered
from them in a fixed order, which means a regeneration can differ only where
a slot differs — and `tools/prompt.py diff` names every slot that moved.
Change the wardrobe, and the wardrobe is the entire diff.

## The thirteen

| # | Slot | What goes in it |
|---|---|---|
| 1 | `references` | The material, by id — an Element for the cast, an Element for the product |
| 2 | `subject` | Who or what is in frame beyond the references: condition, build, state |
| 3 | `action` | What is happening. Hands, gesture, what is held and how |
| 4 | `wardrobe` | Clothing and accessories as items. `null` when nobody is in frame |
| 5 | `setting` | Where it happens, and what is behind them |
| 6 | `composition` | What occupies what, the crop, what sits at each edge |
| 7 | `shot` | Height, angle, distance, depth — **the result, never the equipment** |
| 8 | `light` | Direction, quality, and what it is there to reveal |
| 9 | `grade` | Palette, contrast, black level |
| 10 | `style` | The rendering register |
| 11 | `texture` | Surface truth — what must stay visible |
| 12 | `anchors` | Positive constraints that hold realism, not bans |
| 13 | `negatives` | The ban list: the pack's, plus anything this ad adds |

The order is the contract. The same values in a different order are a
different prompt.

## Where it came from

The shot-list order this lane already used — subject, action, environment,
composition, camera, light, grade, style, texture — plus the two things the
**AvatarHype 6C** skill had that we had never written down: a **references**
slot, and **positive anchors** rather than only a ban list.

Its six map onto these thirteen:

```
C1 Character  ->  references + subject + wardrobe
C2 Camera     ->  composition + shot        (split on purpose)
C3 Clothing   ->  wardrobe
C4 Context    ->  setting
C5 Light      ->  light + grade
C6 Anchors    ->  texture + anchors + negatives
```

**C2 is the one place we refuse to follow it.** 6C writes the camera into the
prompt — "iPhone photo", "harsh iPhone flash". A model has no concept of a
camera it looks *through*; everything named is an object it can place *in*
frame, and "shot on a phone on a tripod" once put a phone on a tripod in the
middle of a barbershop ad. So `composition` says what fills the frame and
`shot` says height, angle, distance and depth. The result, never the gear.
`GENERATION-METHOD.md`, principle 5.

## Style packs — how it stops being a UGC method

6C is written for exactly one look: phone-flash influencer UGC. Everything
distinctive about it lives in the six slots that describe *how* a frame is
rendered rather than *what* is in it.

So those six — `shot`, `light`, `grade`, `style`, `texture`, `negatives` —
come from a **style pack**, and the other seven never do. The same subject,
action and setting render as candid UGC or as flat vector by changing one
word.

The five packs in `style-packs.json` were read off the registers our own six
briefs actually used, not invented:

| pack | what it is |
|---|---|
| `candid-ugc` | a photograph a real person would have taken |
| `mirror-selfie` | through a mirror, phone in hand — the one register where a phone belongs in frame, because the mirror explains it |
| `studio-object` | the product alone on a controlled ground |
| `flat-vector` | drawn, not photographed — meme and comic register |
| `diagnostic-scan` | a glowing translucent body against a void |

A pack's negatives always hold; an ad can add to them and never remove them.

## The result budget — what a frame may CLAIM

A pack says how a frame is rendered. It says nothing about how much better a
result is allowed to look, and until 2026-09-14 neither did anything else we
had. `texture` held skin truth — pores, follicles, marks — and the claim went
unpoliced, so a plate that cleared the skin completely passed every test.

Set `"result": true` on any slot file whose frame shows an after state, a
treated area or a before/after. Two things then happen, from one entry in
`style-packs.json` under `_result_budget`:

- the credibility anchors join `anchors` — partial improvement, 3-5 surviving
  marks, freckles and texture preserved, same person, same light;
- the bans join `negatives` — no cleared result, no glow, halo or bloom, no
  airbrushed skin, no softer lens or warmer grade than the before.

`judge.py` reads the same entry and checks it off the picture that comes back,
so the plate is never asked for one thing and judged against another. A brief
can tighten the numbers with a `**Result budget**` block and the judge uses
those instead.

Taken from AvatarHype, whose own rule is the useful sentence: *if the result
looks like a brochure, FAIL.* A total fix reads as fake, so the fix is never
total.

## Using it

```
prompt.py packs                              the registers
prompt.py render --slots slots.json          the prompt string
prompt.py diff   --a before.json --b after.json    what actually moved
```

**Regeneration is a slot edit.** Copy the slots, change one value, render,
and run `diff` to prove that one value is all that changed. If the diff has
more lines than you meant, the prompt is not the problem — the edit was.

## What this does not do

It does not write the words on the ad. Type, prices, logos and the product's
label are composited at full precision by `tools/compose.py`, because a model
approximates letterforms and a generated price is a lie
(`GENERATION-METHOD.md`, principle 3). The slots describe a photograph.
