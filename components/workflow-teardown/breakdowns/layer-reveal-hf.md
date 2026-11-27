# Layer Reveal (/miami-hf and four sister styles)

Paints a user's hero into a styled game-loading-screen scene with Seedream 5.5, splits it into layers and renders a video where the layers fade in one by one under a LOADING bar.

Source files: `layer-reveal-hf/SKILL.md`, `commands/miami-hf.md`, `layer-reveal-hf/scripts/reveal.py.md`

## Inputs it needs

- A hero: a name after the command and/or one photo; none means the style's default hero (Miami: `a red 1980s sports coupe seen from behind at a three-quarter angle, driving away`).
- Optional notes: 16:9 or horizontal (default 9:16), length 5-20 s (default 10), 'no bar', a label of their own.
- Style command: /miami-hf, /nightclub-hf, /supercar-hf, /helicopter-hf, /mansion-hf (only Miami's prompts are saved in this library).

## Steps in order

1. **Describe the hero** - Put a short visual description into `<HERO>`; with a photo, attach it and say 'with its exact shape, colours and details'.
2. **Cost line** - One picture and five edits, say the number of images.
3. **FULL picture** - `generate_image` 2k, 9:16 (or 16:9); regenerate once if the hero is missing, tiny, or the picture has text.
4. **Cut-out and BACKGROUND** - `remove_background` on FULL (hero as transparent PNG) and the BACKGROUND edit run together.
5. **STAGES 3, 2, 1 and PLATE** - One `generate_image_batch` for the three stages from BACKGROUND, then the PLATE from STAGE 1.
6. **Check layers** - Stack small copies with ffmpeg hstack and look; redo a bad edit once.
7. **Render** - reveal.py draws every frame itself (60 fps, eased fades, push-in, LOADING bar).
8. **Deliver** - Video and FULL picture, one line.

## Prompt blocks, word for word

**SCENE (Miami; replace <HERO>)** (`commands/miami-hf.md`)

```text
Vertical painted illustration in the style of a classic open-world video game loading screen set in 1980s
Miami: bold crisp dark outlines around every shape, sharp clean edges and cel-shaded colour areas in
hand-painted digital art, a saturated sunset palette and slightly stylised realism. HERO: <HERO>. STYLING,
when the hero is a person: they pose like the star of a game poster, chin up and a confident look straight at
the viewer, hair blowing in the sea breeze, a low camera angle and a glowing sunset rim light. The outfit
follows the person's gender: a woman wears a cropped pastel jacket, high-waisted shorts, gold jewellery and
heels, with bold lipstick and a hand on the hip; a man wears an open pastel linen suit jacket over a loose
floral shirt, light trousers, loafers and a gold chain, with a hand in the pocket. Glasses only if the person
wears them in the photo; otherwise the face and eyes stay uncovered. The hero dominates the frame and holds
all the attention: close to the camera, about two thirds of the frame height from head to feet, centred, with
the scene kept smaller behind, on a wide sunlit beachfront boulevard, seen at a three-quarter angle. The
scene, back to front: a purple-pink sunset sky with streaked glowing clouds, a low golden sun near the horizon
and a small plane; pastel art-deco hotels decorated with neon tube outlines (shapes only, no lettering) and a
distant city skyline along the beach; a turquoise sea on one side; street lamps, flowering hedges and a low
seawall railing along the road; tall palm trees leaning in from the edge of the foreground, casting long
shadows across the asphalt. The road fills the bottom third. No text, letters, signs with words, logos or UI
anywhere.
```

**BACKGROUND edit (from FULL)** (`commands/miami-hf.md`)

```text
Edit the reference image. Remove ONLY the hero (the person, animal or vehicle in the middle of the frame),
together with its shadow; fill the area with the ground and scenery that would be behind it. Everything else
stays pixel-identical: same framing, painting style, every other object, buildings, sky, road, light and
colours. No text.
```

**STAGE 3 edit (from BACKGROUND)** (`commands/miami-hf.md`)

```text
Edit the reference image. Remove ONLY the palm trees in the foreground and anything flying in the sky (planes,
birds), with their shadows and reflections on the ground; fill those areas with what would be behind them.
Everything else stays pixel-identical: same framing, painting style, buildings, sky, road, light and colours.
No text.
```

**STAGE 2 edit (from BACKGROUND)** (`commands/miami-hf.md`)

```text
Edit the reference image. Remove the palm trees and anything flying with their shadows and reflections, and
ALL hotels, towers and the whole city skyline; behind them show only the open sky down to the horizon. Keep
the road, the street lamps, hedges, railing and the sea, and the clouds and the sun exactly as they are: same
framing, painting style, light and colours. No text.
```

**STAGE 1 edit (from BACKGROUND)** (`commands/miami-hf.md`)

```text
Edit the reference image. Remove the palm trees and anything flying, all hotels, towers and the whole city
skyline, and the street lamps, hedges, railing and the sea. What remains: the road with its edges and
markings, the sky with the clouds and the sun, and a flat empty horizon. Same framing, painting style, light
and colours. No text.
```

**PLATE edit (from STAGE 1)** (`commands/miami-hf.md`)

```text
Edit the reference image. Remove ONLY the clouds and the sun, moon or stars from the sky, and replace the
whole sky with a plain smooth gradient in the picture's own sky colours, down to the same horizon. The ground
and everything on it stay pixel-identical: same shape, position, framing, art style, light and colours. No
text.
```

**FULL picture request** (`layer-reveal-hf/SKILL.md`)

```text
{
  "params": {
    "model": "seedream_5_5",
    "prompt": "<SCENE with the hero>",
    "aspect_ratio": "9:16",
    "resolution": "2k"
  }
}
```

**Render command** (`layer-reveal-hf/SKILL.md`)

```text
mkdir -p ~/reveal && cd ~/reveal \
  && curl -sfL '<PLATE_URL>' -o 0.png && curl -sfL '<STAGE_1_URL>' -o 1.png \
  && curl -sfL '<STAGE_2_URL>' -o 2.png && curl -sfL '<STAGE_3_URL>' -o 3.png \
  && curl -sfL '<BACKGROUND_URL>' -o 4.png && curl -sfL '<CUTOUT_URL>' -o hero.png \
  && python3 "$HF_WORKFLOWS/layer-reveal-hf/scripts/reveal.py" 0.png 1.png 2.png 3.png 4.png --hero hero.png -o reveal.mp4 \
  && curl -f -X PUT -H 'Content-Type: video/mp4' -H 'If-None-Match: *' --upload-file reveal.mp4 '<VIDEO_UPLOAD_URL>'
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| FULL picture and every edit (BACKGROUND, 3 STAGES, PLATE) | `seedream_5_5` | 2k, 9:16 or 16:9, edits take one image reference |
| Hero cut-out | `remove_background` | media_type image on the FULL job (free per the command) |
| Reveal video | none | reveal.py in the sandbox; never a video model |

## Checks and gates

- Prompts are sent exactly as the command gives them, only putting the hero in; never writes a style, reorders or merges stages, or animates with a video model.
- A man never gets a dress, skirt, heels or lipstick and a woman never the man's suit and chain; glasses only from the photo; a real person keeps face and identity.
- Regenerates FULL once when the hero is missing, tiny, hidden, or the picture has text or logos.
- Layer check: scene images must keep FULL's framing, show only their layers and no hero; redo a bad edit once with the same request.
- Label stays `LOADING...` unless the user's language uses Latin or Cyrillic; other alphabets keep English (sandbox font).
- Library note: only /miami-hf is saved; nightclub, supercar, helicopter and mansion prompts are not.

## Price pattern

Quotes before running: six images (1 picture + 5 edits) plus a free cut-out and a free render. `seedream_5_5` is not in `_prices.md`; its siblings quote `seedream_v5_pro` 2k at 2.5 and `seedream_5_0_flash` 2k at 0.5, so six images are roughly 15 credits at the Pro rate (estimate, re-quote).

## Cheap swap

- Swap the six images to `seedream_5_0_flash` 2k: 0.5 credits a picture quoted, against 1.75-2.5 for 2k pictures: 6 x 0.5 = about 3 credits against about 15 (a fifth), if the edits keep the framing.
- Or `gpt_image_2_6_flare` 1k low: 0.75 credits a picture quoted: 6 x 0.75 = 4.5 credits.
- Cut-out: local BiRefNet (free). The reveal render is already free (reveal.py on this Mac also works). The hero description is written by Claude on the plan.
