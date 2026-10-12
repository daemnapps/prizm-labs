# The Cinema line

> **Superseded on the talking beat, 2026-09-17 (the owner's ruling).** The 16
> Sep route — `seedance_2_5`, the approved still as `start_image`, the
> ElevenLabs line attached as a media with role `audio`, `mode:
> omni_reference` (mode confirmed by the course write-up, the owner 09-14) —
> replaces `cinematic_studio_3_0` as the primary talking route below.
> Cinema Studio is now the talking FALLBACK if sync drifts, not the whole
> architecture. Element injection and the receipts, everywhere else in this
> page, still stand. Details: `providers/README.md`, `machine/providers.json`.

How a Brand B video ad gets made. Settled 2026-09-12 after a full day of
getting it wrong, and it is the system to print from.

**Everything happens in Higgsfield. Nothing else touches a frame.**

---

## The one thing to understand first

**Do not marry an audio file to a video. Ever.**

That is the hard problem, and it is the wrong problem. A whole day went into
it: seedance with `audio_references`, wan with `audio_references`, fal's
`sync-lipsync`, padding audio to whole seconds, nudging synthesis speed to
land on the second, measuring mouth openness against voice envelopes. All of
it was solving a problem that does not exist in the tool we already own.

**Cinema Studio generates the speech and the picture together.** The dialogue
goes in the prompt as words. There is no audio input. There is nothing to
line up, so nothing can drift.

> the owner, 2026-09-12: *"I literally had the elder presenter on TV doing a podcast
> interview. I had these fake people, realistic, word for word, feeling
> emotion and how they were delivering things through Higgsfield cinematic.
> This is not complicated."*

It is not complicated. It is two calls.

---

## The two calls

### 1 · Generate

    model            cinematic_studio_3_0
    prompt           the room, the character as <<<element>>>, the action,
                     and THE LINE SHE SAYS, in quotes
    generate_audio   true
    duration         4-15s
    aspect_ratio     9:16      resolution  1080p
    genre            drama
    medias           none — no audio file, no start image

The character and the room come in as `<<<element-uuid>>>` references inside
the prompt text. The model builds the shot around them and performs the line.

### 2 · Revoice

    tool        voice_change
    video_id    the job id from step 1
    voice_id    the cast member's voice element
    voice_type  element

`voice_change` **keeps the original timing and visuals** and swaps only the
voice. So the lip sync stays exactly as the model made it — native, frame
accurate — and the voice becomes ours. Measured: envelope match 0.945 before
against after, which is the timing holding while the voice changes.

That is the whole production step. Generate, revoice, done.

---

## Which model, and why it is not the cheap one

Tested 2026-09-14 against the AvatarHype model table, which routes talking
beats to Omni. We do not, and the reason is not picture quality.

| model | 8s · 720p | duration cap | takes `<<<element>>>` |
|---|---|---|---|
| `gemini_omni_flash_1_1` (Omni) | **24 cr** | 10s | **NO** |
| `cinematic_studio_3_0` | 40 cr | 15s | yes |
| `seedance_2_5` | 52 cr | 30s | yes |

**Omni cannot read the bank.** Element injection — `<<<uuid>>>` in the prompt,
which is how the cast, the room and the product reach a shot — works on Nano
Banana Pro/2, GPT Image 2, Seedream 4.5/5 lite, Cinema Studio Image 2.5,
Cinema Studio Video 2/3.0, Seedance 2.0 and Kling 3.0. Not Omni. Measured, not
assumed: the placeholders went through as literal text and the backend replied
that it had received zero references.

You can hand Omni an element's underlying **media id** as `image_references`
and it holds identity well — Beto came back as Beto. But then:

- the prompt must name references by POSITION ("the man from the first
  reference"), not by identity, so the one fixed prompt shape per stage stops
  being fixed — reference order becomes part of the sentence;
- b-roll loses the product element, which is the only reason the real wordmark
  renders. Ask a generator to letter a bottle and it returns "bloodmark" and
  "BUMP PATROL". It has, twice;
- every extra model is another payload builder — Omni has `mode` and no
  `genre` and no `generate_audio`, Cinema has the reverse.

16 credits a clip is not worth paying for with the mechanism that makes this
printable at volume. **The bank is the scaling unit, not the model.**

**Where Omni does belong:** shots with no cast and no product in them —
ambience, texture, a street, a sky. There the bank has nothing to contribute
and the cheaper, faster, exactly-sized file wins.

**`voice_change` is model-agnostic.** Measured envelope correlation, original
against revoiced: 0.945 on Cinema Studio, 0.939 on Omni. So step 2 never has
to change, whatever step 1 ran on.

---

## Ivy — the locked settings

Everything below is banked in Higgsfield. Attach all three elements to every
talking clip; the voice goes on afterwards.

| What | Element | ID |
|---|---|---|
| Her face and wardrobe | `ivy-esthetician` | `<id>` |
| Her hands and wrist | `ivy-hands` | `<id>` |
| Her voice | `ivy-a1-speed-120` | `<id>` |
| The room she stands in | `set-shop-wall` | `<id>` |

The room comes from **the standing set**, not from her — any cast member uses
the same four positions. See `brands/<brand>/set/barbershop/SET.md`:

| Position | Element | For |
|---|---|---|
| the presenter wall | `set-shop-wall` `f4c2e30e` | **every A-roll talking beat** |
| the chair | `set-shop-chair` `71bc1cef` | the man in the chair |
| the counter | `set-shop-counter` `e5020f42` | hand-holding-product inserts |
| the mirror station | `set-shop-mirror` `553d89da` | self-inspection, before-and-after |

The shelf in every position carries Brand B in matte black and gold and a partner brand
in white-over-cobalt-blue (`mane-house-look` `19adbc3b`). a partner brand already retails
Brand B's device, so that shelf is a real retail relationship — keep it true:
only products they actually sell, in their actual colours, from their own
photography.

**The room must be attached to every clip in an ad.** Cinema Studio rebuilds
the world from the prompt each time, so without it every clip invents its own
shop and the cut does not match. That is what the environment element is for.

**The voice element is why the voice is consistent.** The model performs the
line in a voice it invents, and it invents a different one each time. Revoicing
every clip to the same element makes the delivery identical across a whole ad
and across every ad she ever fronts.

Her voice element was cloned from the approved ElevenLabs take
(`a1-speed-120` — the esthetician's print refined toward the core avatar). The
ElevenLabs recipe stays in `brands/<brand>/ai-cast/nina/character.md` as the
source of truth; the Higgsfield element is the copy that Cinema Studio work
revoices to.

---

## The structure: A-roll is the spine

**A scene is one continuous run of voiceover.** She starts talking, she
finishes the thought. 12 to 25 seconds; Cinema Studio's ceiling is 15 per
clip, so a longer run splits at a sentence break, not at a cutaway.

**B-roll is not a scene.** When the source cuts to a bottle in a hand or a
diagram, her voice does not stop — the picture changes *over* a take that
keeps running. Inserts are notated under the A-roll scene they cover, with the
second they land on, and they are made **after** the A-roll exists:

    Cutaways:
      @4s  — hand holds the Tend Skin bottle, label to camera — generate
      @11s — skin cross-section, hair curling back under      — footage library

> the owner: *"B-roll just sits on top of A-roll. If A-roll is the foundation, we
> focus on creating A-roll, then we notate B-roll and generate that
> afterwards, or we source it afterwards."*

**How many scenes.** The teardown's own timestamped record already found the
structure — that source came out as 15 rows of 8 to 17 seconds. The brief
should land near that number. When stage 5 defined a talking beat as "~4s"
and made every cutaway its own scene, a 15-row source became **33 scenes**,
eighteen of them the same woman at the same crop saying consecutive
sentences. That is where the cost, the repetition and the drift came from.

---

## Writing the prompt

One shape, every time:

```
<the room, one sentence>. IVY <<<id>>>, <who she is in a clause>,
stands facing camera at chest height and speaks directly to the viewer.

<the gesture — and it must RESOLVE: "then her hand comes down out of the
bottom of frame and stays down">

She says, <the delivery in a few words>:

"<the whole continuous run of speech, every sentence of it>"

Her eyes stay on the lens. Her eyebrows work with the meaning. Locked frame,
no camera movement, no cuts. No filming equipment in shot.
```

**Three rules inside that, each of which cost a re-run:**

**A gesture is a beat, not a pose.** Write "holds up three fingers" and she
holds three fingers aloft for the entire clip like a statue, long after the
word has passed. Say where the hand goes afterwards.

**Never name the camera.** A generator has no concept of a camera it looks
*through* — everything named is an object it can put *in* the frame. "Shot on
a phone on a tripod" renders a phone on a tripod standing in the barbershop.
Say the result instead: framing, height, how flat the light is.

**Never ask for lettering to be rendered.** A named product comes in as its
prop element. Asking the model to write a brand name on a bottle gets
"bloodmark" and "BUMP PATROL".

---

## Writing the line she says

**Figures and marks belong on screen, never in her mouth.** The voice model
reads what is written, literally:

| Written | Spoken |
|---|---|
| `4x deeper` | "four **x** deeper" ✗ |
| `four times deeper` | ✓ |
| `69.99` | write "[the price]" |
| `12,000` | write "twelve thousand" |
| `the device™` | drop the ™ — it is a character like any other |

**No ellipses.** Every `…` becomes a literal gap and reads as choppy.

**Direction is attitude only.** `[confident, easy, like she's
mid-conversation]`, `[a flick of amusement]`. Never pace words — pace belongs
to the voice recipe, emotion belongs to the direction, and writing "speaks
slowly" into both puts two brakes on.

---

## Check before showing anyone

| Check | How | Pass |
|---|---|---|
| Is it her voice? | RMS-envelope correlation, revoiced track vs the element's source | ~1.0 |
| Did the timing hold? | same correlation, before revoice vs after | >0.9 |
| Is the picture alive? | frame-to-frame scene score across the clip | moving, not a held frame |
| Does the gesture resolve? | eight frames tiled across the clip | up at the start, down after |
| Do the clips match? | first frame of each, side by side | one room, one wardrobe, one light |

**A mouth-openness measurement against the voice envelope does not work.** A
fixed crop lands on the nose whenever the framing shifts, and it scored
badly on clips that were fine and well on clips that were not. Cinema Studio's
sync is native; it does not need proving frame by frame. The ear decides.

---

## What is retired, and why it must stay retired

**fal, entirely.** `sequence.py` and `sound.py` ran on it and are marked
retired in place. Their clips came off `kling3_0` with `sound: "off"` and no
audio attached at all — a model this repo had already written down as retired
— and because nothing recorded which model made a clip it went unnoticed
through a whole finished ad.

**Record the model on every clip.** A wrong model that leaves no trace is a
wrong model that gets used twice.

**seedance with `audio_references`** takes the audio as a *style* reference
and returns a silent clip. **wan2_7** consumes it and returns a track, but the
mouth drifts. Both are the wrong shape for a talking beat. They are fine for
B-roll, where nothing is said.

---

## Printing at volume

The reason this scales: **nothing about a clip is re-decided.**

- The cast, the room and the voice are elements. They do not get described,
  so they cannot drift.
- The prompt is a fill-in-the-blanks shape, not a piece of writing.
- The line comes straight from the brief, with figures written out.
- Two calls per clip, no chaining, no plates to build first, no audio to
  upload, no durations to match.

Which means a new ad is: swipe → teardown → brief (A-roll scenes with cutaways
noted) → generate → revoice → notate B-roll → cut. Headline and scroll-stopper
swaps replace only scene one, so a tested body can carry a dozen fronts.

---

## B-roll: ask the library, and disqualify before you pick

A-roll is generated. **B-roll is found.** On the first print run the library
carried nine of nine cutaways and nothing had to be generated at all — the
brand owns 1,342 indexed clips with scene-level vision breakdowns, and the
whole insert track came out of them for nothing.

**Match on what the footage SHOWS, not on what is said.** The recommender
scores transcripts, and B-roll is silent — asking it for "a hand holding a
bottle" returns almost nothing. Every clip has a `breakdown.json` with
`visuals`, `subject`, `setting`, `products_visible` and `talking_head`. Score
against those and the same query returns the shot.

**Four disqualifiers, checked by eye on the actual frame before a clip is
used.** Each one of these got through a text match and would have shipped:

| Disqualifier | What it looked like |
|---|---|
| **Broadcast footage** | "Close-up of a player's neck" scored top for the bumps beat. It was an NBA game. Not ours, not licensable, and it nearly went in a paid ad. |
| **Third-party watermark** | Every one of the esthetician's 28 delivered clips carries a `RECORDED ON BIGVU` badge, bottom right — the teleprompter app she filmed with. Crop it out (normalise to 9:16, crop 1005×1788 at x=38, rescale); never blur it, a delogo smears across a moving sleeve. |
| **Someone else's caption** | A real device box in real hands — inside a screen-recorded repost with "Being honest be like… 😅" burnt in and the platform UI around it. |
| **A speaking mouth** | A cutaway of a person mid-word, laid under a voiceover, reads as a muted talking head. Skip any scene whose `visuals` mention talking, speaking, to camera, selfie or smiling — and look at the frame anyway. |

**Never fake a competitor's label.** Three cutaways wanted a named rival
product in a hand. The library does not own them, and a generator writes
"bloodmark" and "BUMP PATROL" on anything it is asked to letter. Both roads
are wrong, so the beat is dropped: her delivery carries the line, and the
picture stays on her face. A brand name belongs in her mouth, never in the
frame.

**Where product must be legible, use the real photography.** The answer to
"I still don't see our logos on the bottles" was never a better prompt — it
was the brand's own pack shots, already filmed, with the real wordmark on the
real bottle. Generate shapes; composite or cut to type. A generator cannot
render a six-letter wordmark, and it does not have to.

**Two cutaways back to back beat a one-second flash of her face.** When a
mechanism takes two inserts to explain, run them together. Anything under
about a second and a half of A-roll between two cutaways reads as a hiccup,
not a beat.

**Keep the ratio near a third.** The first run landed at 27s of insert over
91s — 30% B-roll, her face on screen for the other 70%. The voice never stops.

---

## The print run, recorded

Every clip records the model that made it. The first finished pair:

| Cut | Length | How |
|---|---|---|
| `IVY-device-90s` | 91.2s | 7 generated A-roll takes, revoiced, with 9 owned cutaways over them |
| `ESTHETICIAN-device-85s` | 84.5s | 9 segments of real delivered footage from one contracted esthetician, cut to the DR structure, watermark cropped |

The the esthetician cut cost nothing and cannot drift, invent a wordmark, or put a tripod
in the shop — she is real. **Ask the roster before casting a generated
presenter.** Four contracted estheticians have delivered footage; between them
they have already said most of a direct-response script on camera.

---

## Generating B-roll

Cinema Studio makes the cutaways too, and at 4 seconds it is **cheaper than
seedance** (20 credits against 26 at 720p) while matching the A-roll's grade
exactly — the same world, the same light, no regrade in the edit. Set
`generate_audio` **false**: a cutaway sits under her voice, which never stops,
and a cutaway carrying its own dialogue fights the take it covers.

The B-roll prompt is a different shape from a talking beat — four blocks, in
`prompt.py` as `BROLL_SHAPE`:

    place     where it is, with the set element
    subject   what is in frame, with the prop element
    action    ONE action, with a beginning and an end
    look      how close, how shallow, how lit

**A named product comes in as its prop element, never as a description.** The
elements were built from the brand's own photography, so the label is real.
That is what finally answered "I still don't see our logos on the bottles" —
not a better prompt.

**Say out loud that there is no text.** Every B-roll prompt ends with *nothing
in frame carries any text, label copy, price tag or writing*. Without it the
model invents a price tag or a wordmark unprompted.

### What the first generated set got wrong

Five of seven landed. The two failures were both the prompt's fault, and both
are general:

**An unstated quantity comes back maximal.** "Two fingertips glossy with a
warm amber oil" produced what looked like honey being smeared on a jaw — a
thick golden pour with foam. Oil on skin is a *sheen*. The fix names the
amount and forbids the failure: *only the faintest trace, already worked in,
nothing pooled*, plus *no liquid pooled, running, dripping or beading
anywhere, nothing amber, golden, syrupy or foamy*. Drop the colour word that
is driving it.

**Motion needs something to shake.** "The bristles break into a fast tight
shimmer" on a product filling frame came back a hero render on a seamless
black background under neon strips, perfectly still. Two causes: *filling
frame* and *a single hard highlight* invited a lighting studio, and a
vibration with nothing on it cannot be seen. The fix put the product in a
hand on the counter under the shop's own light and put **beads of water on the
bristles** — now the movement has a witness, and the bristles visibly blur and
resolve. Also worth saying: *no coloured lighting, no studio backdrop, no
seamless black background*.

**The API may answer with a preset instead of a job.** Three of the seven came
back `submission_failed` with a recommended preset ("IN THE DARK") rather than
a render. Retry those with `declined_preset_id` set to the preset it offered;
they then submit normally. It is not a rejection of the prompt.

### Placing them

`(retired — editing is the editor's)` resolves every cutaway against the durations **on disk**, not
the ones the brief asked for — Cinema Studio picks its own length, so the two
are never equal and using the asked-for number slides every cut late. It also
enforces the two edit rules: a cutaway must finish at least 0.4s before its
take ends, and two cutaways less than 1.5s apart get run together, because a
one-second flash of her face between two inserts is a hiccup, not a beat.

Near a third is the ratio. The first full cut: 28s of insert over 94s, her
face on screen for the other 70%.

### Cast the B-roll. Do not let the model choose who it is.

A cutaway of "a man's jaw at the beard line" comes back as whoever the model
reaches for, and what it reached for was a white man — four times in one set,
in an ad for a brand whose customer base reads otherwise. Nobody wrote
that; nobody checked it either, which is worse.

**The core avatar is Theo** — `Brand B core-avatar face`
`<id>`. Twenty-nine, Black, deep brown skin,
short taper fade, razor bumps and ingrown hairs down the neck and jawline,
the core avatar lane. `brands/<brand>/core-avatars/casting/roster.json` calls him
"the face we have over-used", which is another way of saying he is the
default. **Every shot of a customer's skin attaches him as an element**, the
same way every talking beat attaches Ivy.

The roster holds thirteen men, balanced against the real base, so a batch has
somewhere to go when it needs a second face — but a face is *cast*, from that
file, and never left to the prompt.

### Two rules about the device that the object itself dictates

**It cannot stand up.** Its base is a fully rounded glossy dome with no flat
foot and no standing rim. Told only "resting on its dome", the model stood it
upright on its narrow end anyway. State it as a fact about the object and
forbid the alternative: *it is physically incapable of standing upright and is
never upright at any point.*

**The bristles are on the FRONT only.** The back is smooth matte black with a
sculpted wave. A rotation that is not told this grows bristles on both faces.
And when it is working on skin, the bristle face is **down, against the
skin** — say that the smooth back is what faces camera, or it comes back lying
face-up with the bristles pointing at the lens.

### A set element will dress the shot with invented product

`set-shop-counter` put white shampoo bottles with an invented crossed-shears
badge on the counter beside the device — not one real Brand B bottle in frame.
The set element carries its own shelf dressing, and that dressing is made up.

When a cutaway must show real product, **drop the set element**, describe the
surface plainly, and attach the real product elements by name, saying that
nothing else is in frame: *the only products anywhere on the counter are a
two Brand B serum bottles, both with their brushed gold pump
caps and gold base collars; there are no other bottles, tubs, tubes or jars.*

And then the no-text line has to change, because the point of a product
element is that its label renders. `prompt.py` carries both forms and picks by
whether the row is marked `products`:

| row | line sent |
|---|---|
| no product in shot | nothing in frame carries any text, label copy, price tag or writing |
| real product in shot | the only writing is the real label each product actually carries; no invented lettering |

Sending the first one over a product shot fights the element that finally put
the real wordmark on the bottle.
