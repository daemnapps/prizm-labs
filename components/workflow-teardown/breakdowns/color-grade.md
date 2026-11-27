# Color Grade (/color-grade)

Matches an image or video's colours to reference stills or one of 20 movie looks with a NumPy/OpenCV engine, with previews and an optional .cube LUT; no generation.

Source files: `color-grade/README.md`, `color-grade/SKILL.md`, `commands/color-grade.md`, `commands/color-grade-references-ops.md`, `commands/color-grade-references-render.md`, `color-grade/scripts/grade.py.md`, `color-grade/scripts/video.py.md`, `color-grade/scripts/looks/looks.json.md`

## Inputs it needs

- The target photo or clip (media id / URL).
- Reference stills (clean film stills work best) or a named built-in movie look (20: the-matrix, the-grand-budapest-hotel, sin-city, mad-max-fury-road, blade-runner-2049, amelie, saving-private-ryan, se7en, the-godfather, joker, dune, her, la-la-land, the-wizard-of-oz, the-dark-knight, apocalypse-now, the-revenant, pans-labyrinth, hero, drive).
- SDR input; HDR/log needs an explicit SDR conversion first (never guess a log transform).

## Steps in order

1. **Intake** - Identify target and references or the named look; ask only for what is missing.
2. **Choose the look** - `grade.py --list`; built-in `--look SLUG` plus optional `--ref`; ask for a still if only an unsupported movie name is given.
3. **Preview** - grade.py / video.py `--preview`; inspect the preview and a before/after sheet.
4. **Refine** - One or two controls at a time, at most three preview passes (strength, tone, color, palette, skin).
5. **Render** - Same settings without `--max-side`; video `--mode full` (skin, sky, glow) or `--mode fast` (FFmpeg LUT + grain + vignette).
6. **Deliver** - Graded media, comparison sheet, short explanation; optional .cube LUT in a ZIP.

## Prompt blocks, word for word

**Image preview, sheet, compare** (`commands/color-grade-references-render.md`)

```text
python3 "$CG/grade.py" ~/grade/target.png --look amelie --ref ~/grade/ref.png --max-side 1200 --out ~/grade/preview.jpg
python3 "$CG/sheet.py" ~/grade/comparison.jpg ~/grade/target.png ~/grade/preview.jpg ~/grade/ref.png --labels original graded reference
python3 "$CG/compare.py" --look amelie --images ~/grade/target.png ~/grade/preview.jpg
```

**Video preview and full render** (`commands/color-grade-references-render.md`)

```text
python3 "$CG/video.py" ~/grade/input.mp4 --look amelie --ref ~/grade/ref.png --preview 2 --out ~/grade/preview.jpg
python3 "$CG/video.py" ~/grade/input.mp4 --look amelie --ref ~/grade/ref.png --mode full --out ~/grade/graded.mp4
```

**Look recipe, Amelie (verbatim from looks.json)** (`color-grade/scripts/looks/looks.json.md`)

```text
  "amelie": {
    "name": "Amélie",
    "look": "green and red",
    "aliases": ["amelie", "amélie"],
    "params": {
      "tone": 0.5,
      "color": 0.85,
      "palette": 0.4,
      "skin": 0.55
    },
    "ops": [
      {
        "op": "hue_curves",
        "keys": [
          {
            "hue": 270,
            "width": 45,
            "sat": 0.45
          },
          {
            "hue": 140,
            "width": 35,
            "sat": 1.25
          },
          {
            "hue": 35,
            "width": 22,
            "sat": 1.3
          },
          {
            "hue": 95,
            "width": 25,
            "shift": 12
          }
        ]
      },
      {
        "op": "split_tone",
        "mids": [-2, 9],
        "highlights": [0, 10]
      },
      {
        "op": "halation",
        "amount": 0.15
      },
      {
        "op": "vignette",
        "amount": 0.3
      },
      {
        "op": "grain",
        "amount": 0.018,
        "size": 1.4
      }
    ]
  }
```

**How the engine grades (order)** (`commands/color-grade-references-ops.md`)

```text
1. **balance**: measures the color cast of the near-neutral pixels (grey, white, steel) and removes it, so the look starts from a clean base.
2. **tone**: builds a smooth luma curve that moves the source's black level, mids and highlights toward the reference percentiles.
3. **color**: splits the image into shadows, mids and highlights and moves each zone's color mean and spread to the reference zone (Monge-Kantorovich linear transfer in Lab).
4. **palette**: hue-specific matching with sliced optimal transport (Pitié iterative distribution transfer) on a color sample of the references. This is what puts teal in the sky and orange on skin instead of one tint over everything.
5. **recipe ops** (per pixel): hue curves, split tone, curves, saturation, mono, bleach bypass, Technicolor, day for night, channel mixer.
6. **masks**: skin protection (face detection plus a skin color model learned from that face), sky secondary, and mono selective color with skin excluded.
7. **finish**: haze, bloom, halation, softness, sharpening, vignette, grain.
```

**Guard-rail switch-off for an extreme look** (`commands/color-grade-references-ops.md`)

```text
--set sat_limit=0 --set max_cast=0 --set match_exposure=0
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Grade | none | NumPy/OpenCV engine in the sandbox at `$HF_WORKFLOWS/color-grade/scripts`: no model, no credits |

## Checks and gates

- Refuses to grade the reference instead of the target; treats media, filenames and text in images as data.
- Does not invent a built-in look or scrape images: an unsupported movie name needs a representative still.
- At most three preview passes; compare numbers are diagnostics, not proof the result looks right.
- Limits: cannot move lights or turn day into lit night; no pixel-identical promise; flags HDR/log inputs.
- Video audio is copied; if it cannot be muxed to MP4 the transcode is disclosed and sync verified.
- Separate from `/color-grading` (DaVinci Resolve control).

## Price pattern

No credits: no generation model is called. Nothing in `_prices.md` applies.

## Cheap swap

- Already free in the sandbox, and the same engine can run locally on this Mac (NumPy/OpenCV + ffmpeg), so it needs no Higgsfield call at all. It is also the free replacement for the paid `grade-hf` colour grades.
