# Product Photoshoot
Finished product stills in 10 modes: packshots, lifestyle scenes, product-with-person closeups, Pinterest pins, hero banners, social carousels, static ad packs, virtual try-ons, conceptual CGI-style images, restyles.
Source: `product-photoshoot/SKILL.md`, `product-photoshoot/_files.md`, `product-photoshoot/ui.yaml.md`, `product-photoshoot/references/ (10 mode files, typography, photography-vocabulary, photographer-references, negative-prompts, refinement-pass)`

## Inputs it needs
- A product: confirmed image (upload or HTTPS import) or a text description detailed enough (category, form, packaging, material, colour, label).
- A mode / use case (10 modes); restyle, virtual-model-tryout and closeup-with-person REQUIRE a source product image.
- Optional: variant or slide count (default 3), visual direction, aspect ratio (default 1:1), exact on-image text, brand palette, hands-off intent.

## Steps in order
1. Parse the brief before asking. On 'full auto / just do it' use the silent defaults (3 variants, clean-studio, 1:1, product colours) and state the recipe in one sentence.
2. Ask only for a user-owned gap (product, preset, variant count, ratio, vague-rejection triage), bundled up to three questions.
3. Bring in the product image once (`media_upload_widget` or `media_import_url`) or reuse a completed job id.
4. Choose the mode by deliverable intent (platform/format beats environment) and load its reference plus the five shared references.
5. Verify `nano_banana_pro` supports image references and 2K via `models_explore`; stop on a mismatch rather than switching model.
6. Assemble each variant's prompt from the mode template, append the negative blocks, apply the typography three-case rule, strip every photographer/retailer name.
7. Text-only product with several views: make index 0 first, wait, reuse its job id as the reference for the rest.
8. Submit with `generate_image_batch` (submission groups of 6, wait groups of 8), poll `jobs_wait` 15 s; retry only failed indices.
9. Refine only an observed defect or a specific user correction, at the same index and ratio, single reference = latest job for that index.
10. Call `show_generation_by_ids` once with the final job per index; one sentence naming mode, preset, ratio, correction; disclose unverified QA.

## Prompt blocks, word for word
Mode templates all use the same named-section skeleton; the product-shot template is quoted in full, the ad-creative-pack variant template shows how a pack differs. Photographer names in the library files are internal craft anchors and never go into a generation prompt.

**Modes** (`product-photoshoot/SKILL.md`)
`````
| Mode | Intent | Reference |
|---|---|---|
| `product-shot` | Neutral or styled studio packshot, catalog, Shopify | `references/product-shot.md` |
| `lifestyle-scene` | Product in a real environment or in use | `references/lifestyle-scene.md` |
| `closeup-product-with-person` | Tight product + hands or partial face | `references/closeup-product-with-person.md` |
| `pinterest-pin` | Pinterest-native vertical still | `references/pinterest-pin.md` |
| `hero-banner` | Wide web, email, or campaign header | `references/hero-banner.md` |
| `social-carousel` | 3–10 connected product slides | `references/social-carousel.md` |
| `ad-creative-pack` | Coordinated static paid-social variants | `references/ad-creative-pack.md` |
| `virtual-model-tryout` | Product worn or used by a generated adult model | `references/virtual-model-tryout.md` |
| `conceptual-product` | Surreal, floating, splash, sculptural, CGI-style still | `references/conceptual-product.md` |
| `restyle` | Change an existing image's aesthetic while preserving subject | `references/restyle.md` |
`````

**Preflight model check** (`product-photoshoot/SKILL.md`)
`````
Before the first submission, call
`models_explore({action:"get",model_id:"nano_banana_pro"})` once to verify
image-reference and 2K support. If either is unsupported, stop and report the
mismatch; do not switch model or drop the product reference.
`````

**First-pass request shape** (`product-photoshoot/SKILL.md`)
`````
Each first-pass request is:

```json
{
  "index": 0,
  "params": {
    "model": "nano_banana_pro",
    "prompt": "<assembled mode prompt>\n\nresolution: 2k",
    "aspect_ratio": "<mode ratio>",
    "resolution": "2k",
    "count": 1,
    "medias": [{"value": "<confirmed media_id when present>", "role": "image_references"}]
  }
}
```
`````

**Product-shot prompt template** (`product-photoshoot/references/product-shot.md`)
`````
```
[SUBJECT]
Hero shot of {{exact product description from reference or user input}}, {{material/finish details}}, {{label/branding visible if applicable}}.

[COMPOSITION]
{{Camera angle}}, {{framing}}, {{rule-of-thirds placement}}, {{negative space directive}}.

[LIGHTING]
{{Lighting setup with direction and quality from photography-vocabulary.md}}. {{Color temperature in Kelvin}}. {{Shadow behavior}}.

[LENS & CAMERA]
Shot on {{focal length}} lens, aperture {{f-stop}}, {{depth of field directive}}, sharp focus on {{specific area}}.

[MATERIALS & TEXTURE]
{{Surface treatments}}, {{reflections}}, {{micro-details}}.

[COLOR PALETTE]
Dominant tones: {{2-3 colors aligned with known brand context}}. {{Contrast directive}}.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 matching entries in photographer-references.md}}. Commercial product photography, magazine editorial quality. Never include the source names.

[BRAND INTEGRATION]
{{Known brand colors}}, {{brand mood — clean / warm / edgy / refined}}.

[QUALITY MARKERS]
Tack-sharp, hyper-detailed, photorealistic, commercial-grade.

[AVOID]
{{universal + anti-text-warp from negative-prompts.md}}

resolution: 2k
```
`````

**Product-shot style presets** (`product-photoshoot/references/product-shot.md`)
`````
| Preset | Use for | Visual signature |
|---|---|---|
| `clean-studio` | Universal e-commerce, Shopify, catalog | Seamless white-to-light-grey gradient, soft frontal key, minimal shadow |
| `dramatic-studio` | Premium brands, hero shots, fragrance, electronics | Hard rim light, deep shadows, single light source, moody backdrop |
| `minimal-design` | Modern DTC, clean aesthetic brands | Pastel or single-color seamless, geometric simplicity, high negative space |
| `etsy-handmade` | Handcrafted goods, artisan products, small batch | Warm natural light, linen / wood / stone surfaces, organic shadow |
| `luxury-editorial` | High-end fashion, jewelry, perfume | Polished surface reflections, marble or velvet, jewel-tone backdrop |
| `vibrant-color` | Beauty, food packaging, lifestyle DTC | Saturated solid background, bold color blocking, modern flat composition |
| `floating-product` | Hero shots, dramatic display, suspended product | Product appears suspended mid-air, motion blur on accents, surreal staging |
| `ingredient-flatlay` | Beauty, food, supplements showing what's inside | Top-down composition with raw ingredients arranged around product |
`````

**Ad-creative-pack per-variant template** (`product-photoshoot/references/ad-creative-pack.md`)
`````
## Per-variant Prompt Template

```
[VISUAL SYSTEM]
{{Locked specifications copied verbatim}}

[VARIANT {{N}}: {{Hook Angle}} — {{Aspect Ratio}}]

[HOOK VISUAL]
{{Specific visual that delivers the chosen hook angle}}.

[COMPOSITION]
{{Variant-specific framing}}, {{focal anchor placement using rule of thirds}}, strong eye-leading hierarchy.

[LIGHTING]
{{Lighting tuned to deliver the hook — dramatic for problem-solution, warm aspirational for lifestyle, clean clinical for feature-zoom}}.

[CONTRAST & SATURATION]
Higher saturation and contrast than organic content — must fight the feed. Bold tonal range, deep shadows, bright highlights.

[STYLE REFERENCE]
{{Locked style references from visual system}}.

[QUALITY MARKERS]
Scroll-stopping, magazine-quality, hyper-detailed, performance-ad ready.

[AVOID]
{{universal + anti-stock-feel}}
no inconsistent palette across variants, no flat lighting, no synthetic stock look.

resolution: 2k
```
`````

**Universal negative block** (`product-photoshoot/references/negative-prompts.md`)
`````
```
[AVOID]
no AI artifacts, no warped or smeared text, no fake words baked into the image,
no plastic look, no waxy surface, no cartoonish rendering,
no extra fingers, no extra limbs, no melted geometry, no doubled subjects,
no oversaturated HDR, no HDR halos, no oversharpened look,
no flat fluorescent lighting, no harsh on-camera flash,
no generic stock photography poses, no cliché compositions,
no random unrelated brand logos, no watermarks, no signatures,
no AI sheen on hair or skin, no doll-like rendering, no airbrush look,
no flat solid color bands, no empty rectangular areas, no dull gradient zones
that look out of place from the rest of the scene.
```
`````

**Anti-uncanny, anti-text-warp and the rest** (`product-photoshoot/references/negative-prompts.md`)
`````
## Anti-uncanny (include when humans are in frame)

Append for any generation with people, hands, or faces:

```
no AI uncanny faces, no warped facial geometry, no asymmetric eyes,
no extra teeth, no melted facial features, no warped fingers or hands,
no plastic skin, no orange-tan skin, no over-smoothed retouching,
no doll eyes, no misaligned facial features, no rubber-like skin texture,
no warped jewelry or glasses, no stiff unnatural posture.
```

## Anti-text-warp (include when product has labels or branding)

```
no warped product label text, no garbled letters, no fake brand names,
no melted typography, no doubled labels, no fictional logos.
```

## Anti-stock-feel (include for ad, hero, lifestyle modes)

```
no stale stock photography aesthetic, no synthetic stock-photo look,
no over-staged feeling, no unrealistically clean environments,
no perfect symmetry where natural asymmetry should be,
no clipart elements, no flat illustration mixed with photo,
no obviously composited backgrounds.
```
`````

**Typography three-case rule** (`product-photoshoot/references/typography.md`)
`````
## Case 1 — User specified concrete text to include in the image

If the user wrote exact words they want on the image (`"the headline should say 'New Drop'"`, `"add 'Sale ends Friday'"`, `"with the text 'Made with love'"`), include the text DIRECTLY in the prompt as part of the composition. nano_banana_pro will render it as integrated typography inside the scene.

In the prompt, write something like:
```
[TYPOGRAPHY]
Integrated typography in the scene reads "New Drop" — set in {{font style: bold sans-serif / elegant serif / hand-lettered / clean modern}}, positioned {{naturally within the composition}}, color {{contrasting with background for legibility}}.
```

## Case 2 — User wants to overlay text themselves (in Figma, Canva, Photoshop)

If the user explicitly says they will add text afterward (`"I'll add the headline in Figma"`, `"leaving space for typography"`, `"need clear area for overlay"`), THEN — and only then — instruct the composition to leave a tonally uniform area:

```
[COMPOSITION FOR TEXT OVERLAY]
Leave one area of the frame visually calm and tonally uniform — natural soft gradient, atmospheric blur, or smooth surface — so the user can overlay typography in post-production. This area must still feel like part of the scene (sky, blurred background, surface), NOT a hard-edged empty rectangle.
```

The key word: **tonally uniform area within the natural scene**. Never `clean negative space` or `reserved white space` — those phrases trigger the model to draw a flat band.

## Case 3 — User said nothing about text (default)

Don't mention text or overlay zones at all. Let the model compose freely for maximum visual quality.
`````

**Refinement prompt structure** (`product-photoshoot/references/refinement-pass.md`)
`````
```
Refine the previous image. Keep composition, subject, framing, and overall scene IDENTICAL.
Only change: {{specific photographic instruction targeting the weakest area}}.
{{Mode-specific preservation directive}}.
```

### Fix-prompt language by issue type

**Lighting flat:**
> Add directional key light from camera-left at 45°, 4500K, with stronger rim separation on the opposite side. Deepen contact shadow at the base. Increase tonal range between highlight and shadow.

**Plastic surface:**
> Refine surface to show realistic micro-texture. Add tactile detail — visible weave / brushstroke / pore / grain depending on material. Remove rendered-looking sheen.

**Warped text:**
> Sharpen the product label text to fully legible commercial-print quality. Letters must be crisp and intact, not warped or merged.

**Anatomy off:**
> Correct the {{specific body part — fingers / hands / face / eye placement}}. Anatomically correct human proportions, natural realistic detail. Preserve facial likeness.

**Composition imbalance:**
> Reposition subject toward {{specific anchor — left third / right third}}. Strengthen focal hierarchy, focal anchor moved off dead-center.

**Palette drift:**
> Shift palette toward {{specific known brand colors}}. Reduce {{drifting color}} dominance. Bring {{brand accent}} forward.

**Stock feel:**
> Move away from generic staging. Add lived-in detail, intentional asymmetry, and one specific narrative cue {{name a cue}}. Photographic, not staged-stock aesthetic.

**AI sheen:**
> Remove rendered-looking sheen. Add film-grain photographic feel. Realistic skin texture with natural micro-imperfection. Hyper-realistic, not hyper-smooth.

**Aesthetic half-applied (restyle):**
> Source unchanged. Push aesthetic harder toward {{preset specifics — palette, surface, light, mood}}. Stronger {{specific element}} commitment. Source's previous aesthetic completely gone.

**Flat color band:**
> Replace the flat solid-color {{top / bottom / left / right}} area with natural scene continuation — extend the actual environment (sky, blurred background, surface texture, atmospheric gradient) into that area. The frame must read as one cohesive scene, no artificial empty rectangles.
`````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Every first pass and refinement in every mode | `nano_banana_pro` | resolution 2k, count 1, aspect per mode, medias role `image_references`, prompt ends `resolution: 2k` |
| Prompt writing, QA | none (Claude) | viewing optional |

## Checks and gates
- Model is always nano_banana_pro; never substituted.
- Sanitize: no photographer, publication, retailer, competitor or internal preset names in prompts, questions, logs or delivery notes (a user's brand only as literal text on the product).
- Never invents claims, materials, prices, brand colours or label copy.
- Typography three-case rule: exact user text goes in the prompt; overlay space only if the user says they will add text; otherwise no text mention and no reserved bands.
- Per-mode quality gates (product recognizable, lighting direction, plausible shadows, sharp unwarped label, no AI artifacts on edges, palette, prompt ends 'resolution: 2k').
- Generation budget: 1 first pass + up to 2 refinements, 3 submissions per index total; stop polling after 12 active jobs_wait calls; never regenerate a slow job.
- Without pixels it never claims a quality gate passed and never spends credits on speculative refinements.
- Does not do Amazon-compliance sets, video ads, thumbnails or creator reviews (routes those elsewhere).

## Price pattern
Not quoted (nano_banana_pro 2k absent from `_prices.md`); proxy 1.75 to 2.5 credits per 2k picture, so the default 3-variant set is about 5 to 8 credits before refinements. Quotes before paying.

## Cheap swap
- First-pass drafts: `seedream_5_0_flash` 2k at 0.5 credit (the skill locks nano_banana_pro; cheap route is for our own drafts outside the workflow) or `gpt_image_2_6_flare` 1k low at 0.75.
- Refinements: seedream_5_0_flash i2i at 0.5 instead of a second full-price pass.
- Background cut-out for a plain packshot: local BiRefNet matte (components/local-studio/README.md) free instead of regenerating.
- Prompt assembly, mode choice, QA notes, carousel outline: Claude on the plan, free.
- Upscale a 2k winner with local Real-ESRGAN (free) instead of paying for a higher tier.
