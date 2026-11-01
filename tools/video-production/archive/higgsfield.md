# Higgsfield — the house rules

> Provider page. Written from the song ad's 2026-09-04 run (the worked example) and the 2026-09-16 session's misfires (PROVIDER NOTES at the end); everything here applies to every format on Higgsfield, through the MCP connector or the web app. The switch: `machine/platform.py --provider higgsfield-mcp | higgsfield-ui`; the models per station: `machine/providers.json`.

# The same song ad, built on Higgsfield — the exact run

**2026-09-04.** Same format, same song, same six beats as `fal.md`; a
different house. Where `fal.md` builds the person from reference crops on
fal, this route builds her from a **trained Soul identity** and gets the
visual format from a **restyle pass**. Proven end to end: 30.27s, six shots,
cut to the same lyric timings.

Character used: **June (wife)**, Soul id `<id>`.
Format: **Pixar-style 3D animation**.

---

## THE FINDING THIS RUN BOUGHT

**Soul makes the person. It does not make the style.**

Asked for "Pixar-style 3D animated film still" with June's Soul id, Soul
returned a documentary photograph. It is an identity model and will not be
talked out of realism — the style words are simply ignored.

So the shot is built in **two passes, not one**:

    Soul (identity, photoreal)  →  restyle (format)  →  motion

And the restyle only works if you hand it the picture. Asked for Pixar with
no image attached, the restyle model invented a completely different woman —
young, Indian, in a sari. Attach the frame and it is June.

Same rule as everywhere else: **a reference beats a description.**

The payoff is that the person is decided once and the look is a cheap swap
after. Photoreal, Pixar, claymation, anime — one Soul, any number of formats.
That is the variation lever, with Higgsfield doing the creative half.

---

## THE CALLS

Every parameter except `medias` goes **inside `params`**. `medias` is a
top-level argument on the tool.

### Pass 1 — the person (Soul)

    model:      soul_2
    soul_id:    <the Soul id>          ← inside params
    quality:    2k
    aspect_ratio: 9:16

Prompt: the same fixed blocks as `fal.md` — PLACE, FEELING, framing — plus
this shot's ACTION clause. Drop the phone-camera block: grain and blown
highlights fight the 3D pass that follows.

### Pass 2 — the format (restyle)

    model:        nano_banana_pro
    resolution:   2k
    count:        1
    aspect_ratio: 9:16
    medias:       [{"value": "<media_id>", "role": "image_references"}]

The frame reaches the model only as a `media_id`. Get one with
`media_import_url` on the Soul output's `rawUrl`, then pass it in the shape
above — any other shape validates fine and arrives **empty**, and the model
silently invents a stranger. Check `input_images` on the job before trusting
the result.

Prompt shape, and it is a delta not a description:

> Restyle this exact photograph as a Pixar-style 3D animated film still.
> Keep the same woman — same face, same identity, same hair, same age — and
> the same pose, the same clothing, the same setting, the same framing and
> the same light. Change only the rendering: stylized 3D animation, smooth
> matte subsurface-scattering skin, softly rounded and slightly exaggerated
> features, large expressive eyes, simplified clean geometry, detailed hair
> strands and cloth simulation, soft global illumination with a gentle rim
> light. High-end 3D animation studio quality. No text, no watermark, no
> logos.

### Pass 3 — the product

**The real product is already saved on the account as a prop reference.**
`<brand>-tube`, media `<id>`, and
its own description says: *always use this as the product reference — never
invent tube colors.* The first cut of shot 4 had a generic brown jar in it
because nobody looked.

Swap it in as a **second reference on the finished frame** — the scene first,
the product second:

    medias: [{"value": "<scene frame>",  "role": "image_references"},
             {"value": "<product prop>", "role": "image_references"}]

> Using the first image as the scene: replace the small brown jar with the
> exact product tube shown in the second image … Reproduce that tube's
> shape, colour and label exactly … Change nothing else.

It came back correct but hero-sized and centred. The format's rule — *the
product arrives late and small* — took one more pass to restore.

**Check the prop library before generating any product.** Same lesson as
checking the character's own folder.

### Pass 4 — motion

    model:        seedance_2_5
    mode:         omni_reference
    duration:     5              → 5.04s per clip, six clips = 30.27s
    resolution:   1080p
    generate_audio: false        ← the song goes on in the cut
    aspect_ratio: 9:16
    medias:       [{"value": "<pixar frame>", "role": "start_image"}]

Same one-line motion notes as `fal.md`, prefixed `Pixar-style 3D animation.`

### Pass 5 — cut and mix

Unchanged from `fal.md`. Local, instant, free.

---

## WHAT WENT WRONG, AND THE RULE EACH ONE BOUGHT

1. **Soul ignored the style instruction** and returned a photograph. →
   *Soul is an identity model. The format comes from a second pass.*
2. **The restyle with no reference attached invented a different person.** →
   *A reference beats a description — and verify it actually attached.*
3. **`medias` in the wrong shape validated and arrived empty.** Four
   different shapes passed validation; only
   `[{"value": id, "role": "image_references"}]` reached the model. →
   *Read `input_images` on the job, not the submission.*
4. **A clip was rejected by the safety filter** because the restyle had
   quietly changed her blouse into a thin camisole. The restyle changes
   wardrobe when the prompt does not pin it. → *Pin the clothing, or a
   $__ clip fails on a wardrobe you never asked for.*
5. **A generic jar stood in for a real product that was already on the
   account.** → *Check the prop library first.*

---

## STILL WRONG IN THIS CUT

Named honestly rather than quietly shipped:

- **No age spots.** The whole premise of the song is skin she hides, and
  nothing visible changes between shot 1 and shot 6. The before/after does
  not read. Soul rendered her skin clean and the restyle smoothed what
  little was there. Fix: put spots in as a **reference image**, not a
  sentence — the same lesson `fal.md` records for Yai.
- **The lyric says "jar", the product is a tube.** Either re-record that
  line or accept the mismatch.
- **Wardrobe continuity drifts.** Shot 3 has her in a camisole while the
  song is still on the hiding verses.

---

## COST

Roughly **$__** on credits — six Soul stills, seven restyles, seven clips
(one refused, one redone). Motion is still the whole budget; stills are
noise. The account held __ credits going in.

---

## PROVIDER NOTES (2026-09-17)

Learned on this house across the 2026-09-16 runs (three formats, six
pieces). They apply to every format run here, not just this one; the gates
they feed are in `../RUN-PROTOCOL.md`.

- **Keyframe routing.** A stylized-animation scene with a human lead
  defaults to `nano_banana_2` for its keyframes. `gpt_image_2`'s moderation
  misfires on that scene class — six blocks on clean content in one day,
  none of them about the content. Fall back to `gpt_image_2` only for a
  concrete need the default cannot meet.
- **`start_image` is a media UUID.** Upload the still first and pass the
  id; a URL string is rejected with a 422 (`uuid_parsing`). A whole batch
  failed validation on this once. Preflight checks it.
- **Prove the reference attached.** Read `input_images` on the job, not
  the submission. Several `medias` shapes validate and arrive empty, and
  an empty reference is a stranger in the frame.
- **Read the model's `duration_range` BEFORE slicing audio.** Audio is cut
  to the motion model, never before it is chosen — a song sliced to twelve
  pieces was re-cut to twenty-one after the cap was read late.
- **Sweep every ledger page before quoting spend.** Cursor to the end; one
  page is a guess. Record the `job_set_type` slug as the model name — the
  ledger said `nano_banana_2` where the records said the marketing name.
  Blocked and stuck jobs (`nsfw`, `ip_detected`) are billing-ambiguous and
  are listed separately, never folded into billed.
- **Voice anchors are first-class.** Voice element registration is
  rate-limited (`voice_clone_limit_reached`). Attaching the anchor audio id
  directly as `role: audio` is the locked-voice rule holding, not a
  workaround: the voice record carries anchor id, element id and status,
  and motion reads the anchor id regardless of whether the element ever
  registered.
- **Blocked jobs leave a tile.** The gallery keeps a gray tile per job,
  including refused ones. A gray tile is a job with no output, not a frame
  that went missing.
