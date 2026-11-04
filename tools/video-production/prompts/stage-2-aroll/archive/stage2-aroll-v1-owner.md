# Stage 2 · A-roll — the talking spine

One continuous run of voiceover per beat. She starts a thought and finishes
it. 10–15s; Cinema Studio's ceiling is 15, so a longer run splits at a
sentence break, never at a cutaway.

**No audio file is ever attached.** Cinema Studio performs the speech and the
picture together, so there is nothing to line up and nothing can drift. A clip
whose duration equals a voiceover file sample-for-sample was built the old way,
whatever it looks like — `pull.py` checks for exactly that.

```shape
{room}

{presenter} <<<{face}>>>, {who}, stands facing camera at chest height and \
speaks directly to the viewer.

{gesture}

{says}, {delivery}:

"{line}"

The eyes stay on the lens. The eyebrows work with the meaning. Locked frame, \
no camera movement, no cuts. No filming equipment in shot.
```

## The shape names nobody

`{presenter}`, `{who}` and `{says}` come from the run's **cast block**, not from
this file — so the same shape runs a licensed esthetician for one brand and a
retired nurse for another without an edit. The prompt used to open
`IVY <<<...>>>, a licensed esthetician in white medical scrubs` and that one
line was the whole reason this stage could only ever make Brand B ads.

| from the cast | example |
|---|---|
| `presenter` | `IVY` |
| `who` | `a licensed esthetician in white medical scrubs` |
| `says` | `She says` — written out so the cast carries its own pronoun |

## The three rules inside it, each of which cost a re-run

**A gesture is a beat, not a pose.** Write "holds up three fingers" and she
holds three fingers aloft for the entire clip like a statue, long after the
word has passed. The `{gesture}` field must say where the hand goes
afterwards — *"then her hand comes down out of the bottom of frame and stays
down."* Eighteen clips were built off one plate before this was written down,
and she counted to three in every single one.

**Never name the camera.** A generator has no concept of a camera it looks
*through*; everything named is an object it can put *in* the frame. "Shot on a
phone on a tripod" renders a phone on a tripod standing in the barbershop. Say
the result instead — framing, height, how flat the light is.

**Never ask for lettering.** A named product arrives as its prop element. Ask
the model to write a brand name on a bottle and it returns "bloodmark" and
"BUMP PATROL".

## Writing `{line}`

Figures and marks belong on screen, never in her mouth — the voice reads what
is written, literally.

| written | spoken |
|---|---|
| `4x deeper` | "four **x** deeper" ✗ |
| `four times deeper` | ✓ |
| `69.99` | write "[the price]" |
| `12,000` | write "twelve thousand" |
| `the device™` | drop the ™ — it is a character like any other |

No ellipses: every `…` becomes a literal gap and reads as choppy.

## Writing `{delivery}`

Attitude only. `[confident, easy, like she's mid-conversation]`, `[a flick of
amusement]`. Never pace the words — pace belongs to the voice recipe, emotion
belongs here, and writing "speaks slowly" into both puts two brakes on.
