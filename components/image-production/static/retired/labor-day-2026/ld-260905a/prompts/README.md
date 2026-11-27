# ld-260905a — the prompts, verbatim

Brand A · FLEX™ · Labor Day · fed-up-king lane · run 2026-09-05.

Every prompt that produced a delivered ad is in this folder, unedited. A
summary of a prompt is not a record of it — the wording is the thing that has
to be corrected next time.

| File | Ad | Cast | Mechanic |
|---|---|---|---|
| `01-void-beto.txt` | product hero in a black void | Beto, 38 | Resilia — product in a void, authority line, urgency bar |
| `02-poster-brett.txt` | distressed sale poster | Brett, 41 | Norse — vintage poster, intrusive-thought bubbles |
| `03-apology-omar.txt` | the apology | Omar, 45 | Brand C — "we messed up", sticker badges |
| `04-faceoff-dev.txt` | price face-off | Dev, 56 | Brand C — two-panel comparison |

## Shared inputs

| | |
|---|---|
| Product reference | `<<<8fad5612-d46f-4c19-baec-c3a636f22a4e>>>` — `flex-360-true`, built from seven real turntable angles |
| Cast references | roster Element ids, `brands/Brand A/core-avatars/casting/identities.json` |
| Offer | `flex-labor-day` — $69.99 from $99.99, to Tue 8 Sept. Verified against the live Shopify variant. |
| Copy source | fed-up-king language bank, verbatim. Nothing written. |
| Model requested | `nano_banana_pro` — **note: every job returned reporting `nano_banana_2`** |
| Canvas | generated 4:5, padded to 9:16 (1856 × 3300) |

## What went wrong, and what it cost

Eleven generations to land four ads. Each of these is a rule now.

| # | Failure | Fix |
|---|---|---|
| 1 | Headline garbled to "RPMPM" — the model duplicated a word split across two lines | Put the headline on ONE line and forbid repeats explicitly |
| 2 | Pod balanced on an open flat palm like an egg | Spell out the closed-fist grip; the device has no handle |
| 3 | Device rendered as a fat rounded egg | Say slim teardrop, and give the reference more angles |
| 4 | Device stood upright on a counter — physically impossible | State the base is a rounded dome and it cannot stand |
| 5 | Device bottom cut off flat with a grey rim | Describe the dome as one unbroken curve, no rim, no foot |
| 6 | Drawn device stood on a flat base like a pin | Draw it tilted and floating, dome explicit |
| 7 | Strikethrough sliced a nine — price read **$90.99** | Drop the strike, write `WAS $99.99` |

**The one that mattered most:** every correction above was run as a fresh
text-to-image generation, so each fix also re-rolled the face, the type and the
layout. That is the whole reason this run took eleven passes.
**Corrections are image-to-image off the last approved frame** — see
`../../../../SAFE-ZONE.md`, "Edits are edits".

## Standing rules this run confirmed

- Generate at **4:5**, pad to 9:16. Asking the model to leave room does not work.
- **Put the product Element id in the prompt.** Never describe the device from
  memory; a single-still reference is not enough — the base kept coming back flat.
- **One lane per batch.** This offer is fed-up-king, so the cast came from the
  eight fed-up-king men only. Never blended with glow-up.
- **No invented claims.** Only storefront-feed facts: 12,000 RPM, IPX7,
  300 uses per charge.
- **Never the same face twice in a batch**, and weight to the ages the roster
  says have never been cast.
