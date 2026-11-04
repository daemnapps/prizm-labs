Write the style formula for this variation: ONE canonical string that every
asset and every clip prompt in this variation will carry, byte for byte.

**Every example in this prompt is illustrative only.** Cel animation, 1950s
palettes, ink outlines — none of them describe the style being asked for
here unless the request says so. Take the target from the request below.

This string is the entire visual identity of the variation. It gets pasted
verbatim into the style lock at the top of every clip prompt and into every
conversion step. If it is vague, every clip drifts differently. If it is
long, it stops fitting at the top of a prompt. It has one job: name this
look so precisely that two different generations of two different scenes
read as the same film.

---

THE TARGET STYLE

{target_style}

THE PRODUCTION THIS VARIES

{production_document}

---

Return exactly these sections.

## THE FORMULA

One paragraph, 40–70 words, no line breaks. It must name, in this order:

1. **The medium** — what this is made of (hand-drawn cel, 3D render, stop
   motion, photographed miniature, screen-printed poster art).
2. **The line and edge treatment** — outlines or none, weight, quality.
3. **The shading model** — how many values, hard or soft, where shadows sit.
4. **The palette** — named, with its temperature and saturation.
5. **The surface texture** — grain, paper, film, none.
6. **The era or reference**, if the style has one.

Write it as a description of the finished frame, never as an instruction.
"Flat three-value cel shading with tapered ink outlines" — not "use flat
shading."

Then, on its own line: `FORMULA LOCKED —` and repeat the formula exactly.
That second copy is what gets pasted; having it isolated stops a paraphrase
creeping in.

## THE MOTION LANGUAGE

Two or three sentences, separate from the formula, describing how things
MOVE in this style — frame rate feel, weight, exaggeration, camera
behaviour. This is a different axis from the look: a cel film and a 3D film
can share a palette and still move nothing alike.

If the target style has no distinct motion language, say so explicitly.

## THE PHOTOREAL DESCRIPTORS TO STRIP

Read the production document's own look and camera language, and list
every phrase in it that would fight this style. For each, give the
replacement in this style's vocabulary.

| In the original | Replace with |
|---|---|

Cover at minimum: camera and lens naming, sensor and film-stock language,
skin-texture language, lighting-physics language (bloom, volumetric,
falloff), depth-of-field language, and grain.

This table is used mechanically to rewrite the clip prompts, so be
exhaustive and be literal — quote the original's actual phrases, not
paraphrases of them.

## WHAT THIS STYLE MUST NOT LOOK LIKE

Three to six short phrases naming the specific wrong outcomes for THIS
style — the failure this style tends toward. For an animation target that
includes photoreal leakage; for a photographic target it might be
over-stylisation. Name what would actually go wrong here.

---

Write the four sections and nothing else: no preamble, no commentary.
