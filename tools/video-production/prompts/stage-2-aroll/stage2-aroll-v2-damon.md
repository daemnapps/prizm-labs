**Everything named in this prompt as an example is an example of a SHAPE, not
of content.** No brand, product, person, price or phrase in this file belongs in
a clip. Who speaks, what they say and what they hold come only from THIS run's
cast block and THIS run's brief.

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
this file — so the same shape runs one brand's expert and another brand's
customer without an edit. The prompt used to open with one named presenter
and her job title written into the shape itself, and that one line was the
whole reason this stage could only ever make one brand's ads.

| from the cast | shape |
|---|---|
| `presenter` | `<THE PRESENTER'S NAME, IN CAPITALS>` |
| `who` | `<what they are and what they wear, from the cast block>` |
| `says` | `<She says / He says / They say>` — written out so the cast carries its own pronoun |

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
| a multiplier written `<N>x` | read aloud as the letter "x" ✗ |
| the same, written `<N> times` | ✓ |
| a price in digits | write it the way it is said, in words |
| a figure with a comma in it | write it out in words |
| a product name carrying `™` or `®` | drop the mark — it is a character like any other |

No ellipses: every `…` becomes a literal gap and reads as choppy.

## Writing `{delivery}`

Attitude only. `[confident, easy, like she's mid-conversation]`, `[a flick of
amusement]`. Never pace the words — pace belongs to the voice recipe, emotion
belongs here, and writing "speaks slowly" into both puts two brakes on.
