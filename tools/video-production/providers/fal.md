# fal — the house rules

> Provider page. Written from the song ad's 2026-09-03 run, which stays here as the worked example; the calls, shapes and traps apply to every format on fal. The switch: `machine/platform.py --provider fal`; the models per station: `machine/providers.json`.

# Building a song ad — the exact run

**2026-09-03, worked end to end with Damon.** Not a summary: the actual
calls, the actual parameters, the actual strings that produced a 30-second
sung ad for a body scrub. Anyone should be able to rebuild it from this
page alone.

Total generation cost ≈ **$4.00**.

---

## THE RULE UNDERNEATH EVERYTHING

**A reference beats a description.** Every failure in this run was something
written in words that should have been pointed at with a picture.

| Layer | Stop describing | Point at |
|---|---|---|
| Person | "a woman of 52 with grey hair…" | her master in the AI cast |
| Skin | "irregular brown patches…" | her own `details` board |
| Scene | "a grocery aisle, shelves five high…" | the source frame |
| Style | "3D animated, stylised proportions…" | a frame already in that style |

---

## STEP 1 — Write the lyrics

**File:** `song-v2.txt`. The song IS the script; nothing generates before it
exists.

The first draft failed. Four long lines per verse ("I stopped wearing short
sleeves in the summer of nineteen") came back unintelligible — too many
syllables for the seconds available. **The fix was cutting every line by
roughly half**, not changing model:

    [verse]
    Long sleeves in August
    Nobody asks what you hide
    Twenty years of my hands
    Kept out of the light

    [verse]
    I tried every cream
    Three hundred a jar
    Twelve weeks, be patient
    My hands never changed

    [chorus]
    Then a little brown jar
    Turmeric and moringa
    I scrubbed and I rinsed
    And I didn't say a word

    [verse]
    Week six, a tank top
    Out on the porch
    Nobody made a fuss
    I just left the cardigan

Four to six words a line. Structure markers `[verse]` / `[chorus]` are read
by the model. No product claim beyond what the brand can say; the win is
deliberately small ("nobody made a fuss").

## STEP 2 — Record it, and keep the timing sheet

**Model:** `lyria-3-clip-preview`, on the Gemini key (not fal).
**Call:** `generateContent`, one text part.

The prompt carries the mix direction, which must be explicit — left alone
the vocal gets buried:

    A warm acoustic folk-pop song, 40 seconds, mid-tempo, gentle guitar.
    A clear female lead vocal SINGING these exact lyrics, every word
    intelligible, unhurried, one line at a time with space between lines:

    <lyrics>

**It returns two parts: audio AND a timed lyric sheet.** The sheet is a
production asset, not a curiosity:

    [0.0:5.3]   Long sleeves in August
    [5.3:10.7]  Nobody asks what you hide
    [10.7:16.0] Twenty years of my hands
    [16.0:21.3] Kept out of the light

One line every ~5.3s. Clips are 5.04s. **One shot per line, and the cut
syncs with no trimming.** Song came out 30.72s; six clips = 30.27s.

An earlier attempt on `fal-ai/ace-step` (60s, tags-based) produced a muddier
vocal with heavy auto-tune. Lyria won on intelligibility and on returning
the timings.

## STEP 3 — Take the character from the AI cast

    brands/<brand>/ai-cast/yai/
      master-sheet-sm.jpg     ← the face reference
      boards/details.png      ← the skin reference (4096×2304, 6 panels)

**This is the step that cost the most when skipped.** Four separate
generations were spent inventing age spots for her arms and legs. Her
`details` board already had them — correct, subtle, and hers.

The crops taken out of `boards/details.png` with ImageMagick:

    magick details.png -crop 1340x1150+0+0     +repage yai-arms.jpg
    magick details.png -crop 1340x1120+0+1184  +repage yai-legs.jpg
    magick details.png -crop 1370x1150+2726+1154 +repage yai-hands.jpg

**Check the character's own folder before generating anything about the
character.**

## STEP 4 — Generate the shots

**Model:** `fal-ai/ideogram/character`
**Parameters, exactly:**

    reference_image_urls: [face, arms, legs]     ← all three, every shot
    image_size:           "portrait_16_9"        ← 736×1312, non-negotiable
    style:                "REALISTIC"
    rendering_speed:      "QUALITY"
    negative_prompt:      "large dark blotches, raised bumps, skin disease,
                           smooth young skin, studio lighting, posed smile,
                           landscape"

Run 3 at a time with a thread pool. ~40s each.

**The prompt is assembled from five fixed blocks plus one variable clause.**
The blocks are byte-identical in every shot; only the last line changes.

    IDENTITY  This exact woman — her face, her age, her thin white hair in
              a small bun from the first reference.

    SKIN      Her forearms, hands and lower legs match the skin in the
              reference images exactly — the same weathered skin and the
              same age spots, in the same places, at the same subtle
              density.

    CAMERA    Shot on an older iPhone by a family member: slightly soft,
              handheld and tilted, harsh sun blowing out highlights, sensor
              grain, careless framing. No grading, no retouching.

    PLACE     Rural Isan, north-east Thailand — rice fields, dry-season
              dust, a corrugated-roof house, plastic stools, a concrete
              washing area. Nothing arranged for a camera.

    FEELING   She is not smiling for anyone; tired and private.

    ACTION    She is <the one thing this shot shows>. No text anywhere.

**CAMERA, PLACE and FEELING are what earn the realism.** Without them every
model returns a polished studio portrait. They did more than the choice of
model did.

The six ACTION clauses, in the song's order:

| # | key | action |
|---|---|---|
| 1 | `01-sleeves` | standing at the edge of a rice field in full sun in a long-sleeved shirt buttoned to the wrist in the heat, sweat on her face and neck, squinting against the light |
| 2 | `02-hands` | sitting on a plastic stool in the shade, looking down at the backs of her own hands, sleeves pushed up, close on the hands |
| 3 | `03-shelf` | at a concrete washing area outside, a row of old half-used jars on the ledge, looking at them without hope |
| 4 | `04-jar` | at a low table inside the house, one small brown jar among the everyday clutter, looking at it warily |
| 5 | `05-wrist` | in the doorway holding one wrist up into the daylight, studying the skin closely |
| 6 | `06-sleeveless` | outside in a sleeveless top and a skirt above the ankle, arms and lower legs bare in the sun, standing easy among drying laundry, a small private smile |

Shots 5 and 6 add one extra sentence, and it is load-bearing for the story:

    Her spots are visibly lighter than before but not gone — the same
    spots, faded.

The spots must be the **same** spots or the before/after is a lie.

## STEP 5 — Animate the approved stills

**Model:** `fal-ai/bytedance/seedance/v1/pro/image-to-video`
**Parameters:** `duration: "5"`, `resolution: "1080p"`, `image_url: <still>`
**Timing:** ~60s per clip; six in 218s at 3 concurrent.

One short motion line each, describing movement only:

    01  She tugs the cardigan sleeve down over her hand. Slow gentle push in.
    02  She turns her hands over slowly on the table, studying them.
    03  She looks along the row of jars and glances away. Slow drift.
    04  She reaches toward the small brown jar and pauses. Slow push in.
    05  She turns her wrist toward the light and her expression softens.
    06  She laughs and turns slightly, arms relaxed and bare.

Each ends with `Natural subtle motion, no cuts.`

**Never animate before the stills are approved.** A still is ~$0.04, a clip
~$0.62 — motion is 94% of the budget.

## STEP 6 — Cut and mix

Local, instant, free.

    # concat, discarding the clips' own audio
    for c in 01 02 03 04 05 06; do echo "file 'clips/$c.mp4'" >> list.txt; done
    ffmpeg -f concat -safe 0 -i list.txt -an \
           -c:v libx264 -pix_fmt yuv420p -r 30 cut-silent.mp4

    # lay the song over
    ffmpeg -i cut-silent.mp4 -i song.mp3 -map 0:v -map 1:a \
           -c:v copy -c:a aac -b:a 192k -shortest \
           -movflags +faststart final.mp4

`-an` on the concat matters: the clips carry their own generated audio and
it must be dropped, not mixed.

---

## THE MODEL HOUSE, DECIDED BY BAKE-OFF

Same reference, same prompt, four models, judged side by side.

| Job | Model | Price |
|---|---|---|
| People — default | `fal-ai/ideogram/character` | ~$0.04 |
| People — peer | `fal-ai/bytedance/seedream/v4/edit` | — |
| Change one thing in a finished frame | `fal-ai/nano-banana/edit` | $0.039 |
| Motion | `fal-ai/bytedance/seedance/v1/pro/image-to-video` | ~$0.62 |
| Song | `lyria-3-clip-preview` (Gemini key) | pennies |

Nano Banana preserves what it is handed — the right **editor**, the wrong
generator of people. Note it **does not honour an aspect request**: it
returned landscape from a 9:16 source. Check output dimensions.

## COSTS

| | each | ×  | total |
|---|---|---|---|
| Stills | $0.04 | 6 | $0.23 |
| Clips | $0.62 | 6 | $3.72 |
| Song | ~$0.02 | 2 | $0.05 |
| Cut/mix | $0 | — | $0 |
| | | | **≈ $4.00** |

---

## THE SIX FAILURES AND THE RULE EACH ONE BOUGHT

1. **4,262-character prompt describing a scene the source frame already
   contained** — two different women, five outfits, another character's
   wardrobe. The model blended them and put the mistress's denim jacket on
   the lead. → *Never describe what the picture already shows.*
2. **The lead's identity and wardrobe applied to a shot she was not in** —
   the line read "Michelle's point of view down the aisle", so she was
   behind the camera and the instruction turned the woman she was looking at
   into her. → *A name in the scene line does not mean she is in frame.*
3. **Four attempts at age spots** — "irregular patches" gave four dark
   blotches; "freckle-size, soft edges" was too small and too vague;
   "slightly rough, thickened surface" (lifted from a dermatology page
   without understanding it described a different condition) produced raised
   pale lesions. → *Look it up, then point at a real photograph.*
4. **Inventing skin for a character who already had it** — see step 3. →
   *Check the character's own folder first.*
5. **A trained LoRA fighting a style conversion.** Parked behind
   `--use-identities`. A LoRA trained on photoreal images encodes photoreal;
   asking it for an animated look fights its own training. → *Edit-first
   carries the person from the source frame; the LoRA was solving a problem
   that no longer existed.*
6. **Opening frames all seeded from 0:00** — three "different" hook frames
   were three edits of one picture. → *Seed every frame from its own
   timestamp.*

---

## STILL OPEN

- **Lip sync.** `fal-ai/sync-lipsync`, `latentsync`, `sync-lipsync/v2` and
  `creatify/lipsync` are all live on the account; none tested here. Intent:
  two singing moments in six shots. Lip-syncing all six makes a music video,
  not an ad.
- **Type as a layer.** Generate clean plates, compose the words on top
  (`image-teardown/tools/compose.py` already does this). Text can then never
  garble and copy stays editable without regenerating pictures.
- **Who the singer is.** The cast member used here is the brand's authority
  figure — the source of the recipe — and the song is a first-person
  customer story. That is a casting decision, not a technical one.
