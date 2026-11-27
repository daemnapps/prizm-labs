# Manga & Comics (/manga)

Turns an idea, script or photos into a lettered manga, comic or webtoon chapter with consistent characters (sheets, poster, pages), then exports PDF, CBZ or a video; a sandbox engine writes every picture prompt.

Source files: `commands/manga.md`, `manga-engine/SKILL.md`, `manga-engine/scripts/steps/concept.md`, `manga-engine/scripts/steps/designs.md`, `manga-engine/scripts/steps/plan.md`, `manga-engine/scripts/steps/script.md`, `manga-engine/scripts/data/prompts.json.md`, `manga-engine/scripts/data/layouts.json.md`, `manga-engine/scripts/data/rules.json.md`, `manga-engine/scripts/manga.py.md`, `commands/manga-references-styles.md`, `commands/manga-references-engine.md`, `commands/manga-references-runtime.md`, `commands/manga-references-webtoon.md`, `commands/manga-references-review-and-export.md`, `commands/manga-references-video.md`

## Inputs it needs

- A story source: an idea, a script (adapted faithfully, line for line), photos of people or places, or a short video clip.
- Style: black-and-white manga, colour manga, comic or webtoon; length 15-40 pages (default 20); page shape 2:3 default (9:16 or 3:4 on request); lettering language; title kept exactly as typed.
- For real people from photos: each person's age (without a stated 18+ they are drawn and treated as under 18); at most 6 people from photos per series.

## Steps in order

1. **Intake** - Take or ask for story, style, length, shape, language, early price if asked; research the web first if real events or places are involved.
2. **Story steps (free)** - concept -> designs -> plan -> script; each submitted to the engine, which lists issues until accepted.
3. **Script approval** - Shows the chapter page by page and stops until the user's own words approve it.
4. **Price and approval** - Prices every parameter set with the cost tool, shows the total with a 2-redraw ceiling, stops for the OK.
5. **Reference sheets** - Characters, places and props at 16:9, then a full-colour poster; shown once; user asked 'sheets look right?'
6. **Pages** - The engine's exact params in order, never edited; all job ids recorded.
7. **Check every page** - Looks at each page against `review`; one redraw within the 2-redraw ceiling for a sure fault.
8. **Export (free)** - PDF or CBZ (or a video, silent free, voiced priced) built in the sandbox; hosted URL delivered.

## Prompt blocks, word for word

**Intro, B/W story page** (`manga-engine/scripts/data/prompts.json.md`)

```text
You are drawing an interior page of a Japanese manga printed in black and white: black ink line art on white paper, the look of a page from a printed manga magazine or collected volume. It is NOT a grey illustration, NOT a painting, NOT an American comic and NOT a webtoon.
```

**Style, B/W story page** (`manga-engine/scripts/data/prompts.json.md`)

```text
STYLE — MANGA, BLACK INK ON WHITE PAPER:
- Economical line art: few, confident G-pen lines with clear thick-thin weight — bolder outer contours, thin inner lines; no line is spent on surface texture.
- Simple character shapes: an oval face, simple eyes with one small catchlight, a short tick for the nose, a simple mouth, no shading on skin; hair as a few large clumps — one solid black mass, or a white shape outlined with a few strokes — never fine strands; clothes as flat white, flat black or one flat tone with only two to four fold lines.
- Backgrounds only where they are needed: the place is drawn in at most one or two panels of the page, in clean open line art with white surfaces and very little texture; in close-ups, reactions, dialogue and action panels the figures stand on plain white paper, speed lines, focus lines or a single floor line.
- Solid flat black for dark hair, dark clothing, cast shadows and night skies; a few small hard-edged areas of flat dot screentone or parallel hatching only where a shadow or a mood needs it.
- No surface texture anywhere: no fur strands, no leaf-by-leaf foliage, no brick-by-brick walls, stone, wood grain or fabric weave, no stitch-by-stitch knit or plaid (a pattern is a few lines), no rendered clouds, smoke, fog or water (simple outlines with white inside), no glow, no soft shadows, no grain.
- Manga devices where the beat calls for them: speed lines behind a moving figure, radial focus lines behind a reaction, a black flash for a realisation, sweat drops and simple comic faces in a comic beat.
```

**Output, B/W story page** (`manga-engine/scripts/data/prompts.json.md`)

```text
OUTPUT: a single manga interior page, {{FRAME}}, BLACK INK ON WHITE PAPER ONLY — the look of a printed black-and-white manga page: clean pen line art and large areas of untouched white paper; a background in at most one or two panels, every other panel shows the figures against plain white, speed lines or a single floor or horizon line; wherever the place is drawn it is flat and clean — big simple shapes in clean lines, white or one flat grey, a few key objects drawn simply, never texture; solid flat black for dark hair, clothes, shadows and night; grey only as small hard-edged areas of flat dot screentone or hatching. Never a grey wash, gradient, airbrush, soft shading or painted texture. A white page margin around the panels and clean white gutters. {{READING_ORDER}}
```

**Final, B/W story page** (`manga-engine/scripts/data/prompts.json.md`)

```text
DO NOT use colour of any kind — no sepia, cream or warm tint, no coloured light. DO NOT shade with grey — no grey wash, gradients, airbrush, soft shadows or rendered light; grey only as flat dot screentone or hatching. DO NOT draw surface texture (fur strands, single leaves, stone, wood grain, fabric) or a detailed background in every panel. DO NOT texture a background: no rows of individual book spines, no brick, tile, plank or paving patterns, no rain streaks over every surface, no hatching fields, no wet or glossy reflections. DO NOT draw semi-realistic shaded faces, strand-by-strand hair or many clothing folds. DO NOT render a page number. DO NOT letter the @ handles, reference image numbers, panel numbers or any instruction text from this prompt.
```

**Negative (default)** (`manga-engine/scripts/data/prompts.json.md`)

```text
NEGATIVE PROMPT — under no circumstance render any of the following on this page:
{{NEGATIVE_PROMPT_BLOCK}}
```

**Reference sheet style, B/W** (`manga-engine/scripts/data/prompts.json.md`)

```text
Black-and-white manga art in black ink on white paper: clean, economical G-pen line art with clear thick-thin weight. Characters in simple manga shapes — an oval face, simple eyes with one small catchlight, a short tick for the nose, a simple mouth, no shading on skin; hair as a few large clumps (one solid black mass, or a white shape outlined with a few strokes), never fine strands; clothes as flat white or flat solid black areas with two to four fold lines. Places and objects in clean open line art — their main shapes and a few perspective lines, white surfaces, flat solid black only for dark openings and dark materials, no surface texture. A small flat dot-tone area only where two parts must read apart. No grey shading, no gradients, no colour anywhere. Hand-drawn 2D line art on white paper — never photographic, never a 3D render, never a grey painting.
```

**Reference sheet layout** (`manga-engine/scripts/data/prompts.json.md`)

```text
SHEET LAYOUT — follow exactly.
One landscape image split into three equal-width vertical panels of identical height, separated by two solid pure-black vertical dividers about 0.6% of the image width. Nothing crosses a divider. No outer border, no frame, no drop shadow.
Panel 1, left — full body, front view, square to camera, head to feet, eyes to the lens.
Panel 2, centre — full body, back view of the same subject at the SAME scale and camera distance as panel 1: head, shoulders, hips and feet at the same heights. Back fully to camera, head not turned.
Panel 3, right — three-quarter close-up portrait: head, shoulders and upper chest, cropped at mid-chest, body turned about thirty-five degrees off axis, face back to the lens.
Framing: in panels 1 and 2 the subject fills about ninety percent of the panel height, centred, with thin headroom and the ground visible below the feet. In panel 3 the head fills about forty-five percent.
```

**Page rules for the script step** (`manga-engine/scripts/steps/script.md`)

```text
- One page = one beat of the story. A page holds 1-{{CAP}} panels: 4 for action, 5 for mixed,
  6 for conversation; 1 only for a splash (size "splash", role impact, reveal or establishing).
- Each panel draws ONE moment: one action, one shot. Its `action` (at most 40 words, English)
  names every character drawn by @handle and says what they do, where they look and how they
  feel. Never restate a design; the sheets carry it.
- Lettering: at most 4 items a panel, 2 balloons a panel, 12 items and 210 words a page, and
  {{BALLOON_WORDS}} words a balloon. Lines are short, spoken, in the lettering language; sound
  effects (`sfx`) are written in its letters. Lettered text never holds an @handle.
- Every speaker is in the page's `cast`, or `offPanel` with `"off": true`, or an extra by label.
- Every scene starts on a new page and follows the plan's order; `scene` is the plan's scene
  number. Use the plan's key details and quotes word for word.
- The last page has role "closing", 1 or 3 panels, and ends on the chapter's cliffhanger; its
  last panel's role is "cliffhanger". `closingLines` holds the closing caption and the end
  marker, in the lettering language.
- When the series has chapter title pages, page 1 has role "cover" and one panel with no lines,
  and `cover` names who is on it.
- UNDER 18: never describe a character under 18 by body, figure, fit or skin; nothing sexual.
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Reference sheets, pages (manga-bw, manga-color) | `gpt_image_2_6` | quality medium, 2k, role image_references; sheets 16:9, poster in page shape, pages 2:3 / 9:16 / 3:4 |
| Pages (comics) | `nano_banana_2_1` | 2k, thinking_level high |
| Webtoon screens | `seedream_5_5` | 9:16, 2k (webtoon does not use the engine) |
| Webtoon character sheets, key art | `gpt_image_2_6` | 16:9, quality medium, 2k; key art 9:16 only on request |
| Chapter video (optional) | see manga-references-video.md | a silent video is free; a voiced one is priced |
| Steps, checks, export | none | manga.py in the sandbox; it never calls a generation tool or spends credits |

## Checks and gates

- Gates in order: script approved before price, price before any sheet, sheets before any page; approvals carry the user's own words; a change after approval needs approving again.
- Never writes or edits a page prompt, never uses `count` for variants; copies the engine's params exactly.
- Original work only: no existing franchise, studio, artist, character or 'in the style of'; fan works are declined with an offer of an original story.
- Under-18 rules: nothing sexual or suggestive; never describe a minor by body, figure, fit or skin; a person from a photo with no stated age of 18+ is under 18; a refusal is two plain sentences with no workaround.
- Real people: names only from the user, never identified from a face, never public figures, never humiliating, violent or sexual scenes.
- A content refusal from the image model is reported; never switches models or softens the prompt to get round it.
- Page check: wrong or missing line, balloon at the wrong speaker, off-model character, extra text, wrong panel count earn one redraw; beyond the ceiling the user decides.
- Never asks for consent ticks, logins or keys, or for the user to pick prompts, models, layouts or retries.

## Price pattern

Quotes before drawing with `estimate_image_cost` on each parameter set, times counts, plus the 2-redraw ceiling at the page price. `gpt_image_2_6` is not in `_prices.md`; its flare sibling quotes 1.75 at 2k medium. A 20-page chapter is 6 sheets, 1 poster and 20 pages = 27 images, about 47 credits at that rate. The command's own sample line reads 'about 34 (up to 36 if a page needs a redraw)'.

## Cheap swap

- Pages and sheets on `seedream_5_0_flash` 2k: 0.5 credits a picture quoted, against 1.75-2.5 for 2k pictures: 27 x 0.5 = about 13.5 credits for a whole chapter (a quarter to a third).
- Or `gpt_image_2_6_flare` 1k low: 0.75 credits a picture quoted: 27 x 0.75 = about 20 credits.
- Writing (concept, designs, plan, script, page checks) is done by Claude on the plan, free to us; the engine, PDF/CBZ export and a silent video are free local work.
- Cheaper models may draw lettering worse: run one page first and read the text before committing the chapter.
