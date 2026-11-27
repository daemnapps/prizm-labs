# Brand Asset Creation
A consistent set of branded graphics from supplied or newly approved brand elements: logos, palettes, type systems, brandbooks, decks, social graphics, posters, banners, packaging, signage, merchandise and mockups.
Source: `brand-asset-creation/SKILL.md`, `brand-asset-creation/_files.md`, `brand-asset-creation/references/ (24 files)`, `brand-asset-creation/scripts/brandkit.py.md`, `brand-asset-creation/scripts/build_brandbook.py.md`, `brand-asset-creation/scripts/render_brandbook_pdf.py.md`

## Inputs it needs
- The deliverables named in the first message (logo, brandbook, deck, social graphic, poster, packaging, signage, merchandise, mockup).
- Supplied brand materials treated as authoritative: logo, palette, fonts, copy, graphic references, brand homepage URL (captured in the sandbox), PDF/DOCX/XLSX/CSV.
- For graphics: platform, aspect ratio, count, exact text ('no text' is valid), visual mode, supplied photography.
- A new logo or identity only when explicitly requested; strategy, mission, values, tone and messaging are never invented.

## Steps in order
1. Classify the request and persist its deliverables and constraints; never re-ask scope.
2. Read approvals (`brandkit.py state --action get_status`) after restoring this conversation's latest confirmed snapshot; never adopt leftover sandbox state.
3. Load intake; ask one compact set of only blocking questions.
4. Inventory and analyze every supplied asset; immediately lock user-declared official logo, palette and typography through the `lock_authoritative_*` actions; save visual axes.
5. Compute the minimum approved slots the requested output needs (logo-only needs logo; text-bearing social, packaging, poster, signage need logo + palette + typography; brandbook/deck need all three).
6. Build only missing slots: palette options first and wait for a pick, then three distinct logo candidates (Design Brain mechanism each, enhanced once, `recraft_v4_1` vector); user selects; persist with the matching approve_* action.
7. Show review boards (HTML to PNG, uploaded) and STOP for the user's chat reply in interactive mode; auto/no-question mode records its own authorization.
8. Produce the requested outputs from one Brand Lock copied verbatim into prompts; reuse the same approved logo media everywhere; exact SVG, never redrawn; color-only revisions via `logo-export`.
9. QA every output, fix only the failing asset, save approval with the exact required_slots; deliver the Brand Lock summary, a manifest of requested files and any font or fidelity limits.

## Prompt blocks, word for word
Logo prompts are written by Claude under the enhancer contract (no server-side enhancer). Fixed text below: the logo enhancer's input/output contract, the Brand Lock shape, the mockup prompt contract, the social-graphic prompt must-state list, and the routing rules.

**Classify and core workflow** (`brand-asset-creation/SKILL.md`)
`````
1. **Classify the request.**
   - `apply-existing`: make new graphics from supplied brand assets.
   - `extend-partial`: fill only missing visual-system decisions.
   - `create-identity`: allowed only when the user explicitly requests a new logo or identity.
   - Persist the deliverables and constraints named in the first message; never discard them or ask the user to choose scope again later.
2. **Read approvals.** Load [handoff routing](references/handoff.md), then run `${HF_WORKFLOWS}/brand-asset-creation/scripts/brandkit.py state --action get_status` through `sandbox_exec` (restoring this conversation's state first, per that reference). Load only the needed state module later; never read unrelated state modules or infer approval from the newest generation.
3. **Load [intake](references/intake.md).** Parse the first message and attachments first. Ask one compact question set containing only genuine gaps that block the requested output; never repeat answered questions or force a full identity questionnaire for a partial task.
4. **Inventory, analyze, and lock supplied assets.** Load [asset analysis](references/asset-analysis.md). Inspect every relevant asset/page, separate official assets from inspiration, and immediately lock each user-declared official logo, palette, and typography slot through its independent `lock_authoritative_*` state action. Persist normalized visual axes with `set_visual_axes`.
5. **Determine the minimum approved slots for the requested output.** Never require a complete Essential Kit by default:
   - logo-only → logo
   - palette-only → palette
   - typography-only → typography
   - symbol mockup, merchandise, or copy-free packaging → logo; add palette when color/application decisions need it
   - text-bearing social, packaging, poster, or signage → logo + palette + typography
   - Brandbook or presentation deck → logo + palette + typography
6. **Build only missing required slots.** Load [Brandkit Design Brain](references/brandkit-design-brain.md), [concept boards](references/concept-boards.md), [inline widgets](references/inline-widgets.md), and only the missing [palette](references/palette.md), [logo](references/logo.md), or [typography](references/typography.md) module. When the user selects a generated element, immediately save only that element with `approve_palette`, `approve_logo`, or `approve_typography`; do not wait for a combined approval.
7. **Use combined review only when useful.** For a requested full identity/Brandkit, or when the user asks to see the approved elements together, render one combined HTML board from the separately approved slots. It is a presentation view, not another approval gate.
8. **Continue the original request.** As soon as its required slots are approved, proceed with the deliverables named in the first message. Do not ask the user to choose production scope again unless the original scope was genuinely ambiguous.
9. **Load only the requested output modules:**
   - Logo or logo guide → [logo](references/logo.md)
   - Color palette → [palette](references/palette.md)
   - Font recommendations or type system → [typography](references/typography.md)
   - Brandbook → [brandbook](references/brandbook.md)
   - Deck → [presentation deck](references/presentation-deck.md)
   - Carousel or social graphic → [social media graphics](references/social-templates.md)
   - Poster or banner → [posters and banners](references/posters-banners.md)
   - Packaging artwork → [packaging](references/packaging.md)
   - Signage → [signage](references/signage.md)
   - Merchandise artwork → [merchandise](references/merchandise.md)
   - Packaging, device, signage, merch, or lifestyle visualization → [mockups](references/mockups.md)
10. **Audit and approve downstream elements.** Load [QA and iteration](references/qa-and-iteration.md). Fix only the failing asset. Save a final page/template/mockup through the state script's `approve_brandbook_element` action only after explicit user approval, passing the exact `required_slots` that output actually used.
`````

**Minimum slots** (`brand-asset-creation/SKILL.md`)
`````
5. **Determine the minimum approved slots for the requested output.** Never require a complete Essential Kit by default:
   - logo-only → logo
   - palette-only → palette
   - typography-only → typography
   - symbol mockup, merchandise, or copy-free packaging → logo; add palette when color/application decisions need it
   - text-bearing social, packaging, poster, or signage → logo + palette + typography
   - Brandbook or presentation deck → logo + palette + typography
`````

**Logo prompt enhancer: input and output contract** (`brand-asset-creation/references/logo-prompt-enhancer.md`)
`````
## Input contract

Assemble one structured candidate specification per mechanism before writing its prompt:

```json
{
  "brand_context": {
    "name": "context only; never render it",
    "offering": "...",
    "industry": "...",
    "positioning": "...",
    "audience": "...",
    "values": ["..."]
  },
  "visual_axes": {
    "restrained_expressive": 50,
    "geometric_organic": 50,
    "familiar_experimental": 50
  },
  "candidate": {
    "mark_type": "lettermark_monogram | pictorial | abstract | mascot | emblem",
    "central_idea": "...",
    "visual_mechanism": "...",
    "distinctive_element": "specific silhouette, negative-space device, motif treatment, or unexpected locked color pairing",
    "shape_logic": "...",
    "treatment": "flat_vector | monoline | vector_gradient | hand_drawn_vector",
    "style_register": "...",
    "user_style_directive": "explicit user-requested style, or null",
    "composition": "..."
  },
  "palette": {
    "count": "1, 2, or 3 as required by the locked concept; greater only when user_requested_more_than_three is true",
    "user_requested_more_than_three": false,
    "roles": ["primary", "accent", "background"]
  },
  "reference_signals": ["formal qualities only"],
  "forbidden_elements": ["..."]
}
```

Treat supplied creative decisions as authoritative. If a nonessential detail is missing, infer the smallest sensible default without changing the central idea.

## Output contract

The result of this step is exactly one continuous enhanced Recraft prompt string per candidate — no bullet points inside the prompt, no explanation, no debug text.

The prompt must follow this order:

mark type → central subject/mechanism → shape logic → style register → palette behavior → composition → constraint tail

Every clause must materially affect the drawing.

The central subject/mechanism portion must state exactly one visual idea in one clause. Do not add a second metaphor, alternative, “and/or” construction, or hybrid concept.

## Stage boundary — symbol only

This flow creates a symbol/mark before typography selection.

Never include:

- brand name
- wordmark
- tagline
- descriptor
- invented letters
- any other readable words

The only exception is a lettermark/monogram candidate: the explicitly supplied initials inside `candidate.visual_mechanism` are permitted. For lettermarks and monograms, “no text” means no additional words, taglines, descriptors, or unrelated lettering.

Every candidate constraint tail must include the exact phrase “no text.” It does not need to be the final phrase.
`````

**Logo candidates call** (`brand-asset-creation/references/concept-boards.md`)
`````
3. Submit the three enhanced prompts through `generate_image_batch`, one `{index, params}` request per candidate with `count: 1`, model `recraft_v4_1`, `model_type: "vector"`, the selected logo color subset in `colors`, and the selected background in `background_color`. Use the one, two, or three logo colors the concept needs; never pad to three. Exceed three only when the user explicitly requested more.
`````

**Brand Lock shape** (`brand-asset-creation/references/brand-lock.md`)
`````
```json
{
  "version": 1,
  "brand_context": {
    "name": "",
    "offering": "",
    "industry": "",
    "positioning": "",
    "audience": "",
    "tone": []
  },
  "concept": {
    "name": "",
    "visual_premise": "",
    "research_principles": [],
    "reference_preferences": [],
    "avoid": []
  },
  "visual_axes": {
    "restrained_expressive": 50,
    "geometric_organic": 50,
    "familiar_experimental": 50
  },
  "authoritative_assets": {
    "logo": {
      "origin": "user_supplied | brandkit_generated",
      "source": "",
      "upload_or_job_id": "",
      "variants": {
        "color": "",
        "black": "",
        "white": ""
      },
      "status": "fixed"
    },
    "fonts": [],
    "references": []
  },
  "palette": {
    "origin": "user_supplied | brandkit_generated",
    "primary": [],
    "accent": [],
    "neutral": [],
    "semantic_roles": {},
    "forbidden": []
  },
  "typography": {
    "origin": "user_supplied | brandkit_generated",
    "display": {},
    "body": {},
    "fallbacks": [],
    "font_links": [],
    "specimen_svg": ""
  },
  "layout": {
    "grid": "",
    "margins": "",
    "spacing_scale": [],
    "alignment": "",
    "density": ""
  },
  "shape_language": {
    "corner_radii": [],
    "borders": [],
    "shadows": [],
    "forms": []
  },
  "graphic_devices": {
    "motifs": [],
    "patterns": [],
    "textures": [],
    "rules": []
  },
  "composition": {
    "hierarchy": "",
    "logo_placement": [],
    "image_behavior": "",
    "text_behavior": ""
  },
  "applications": {},
  "unknowns": []
}
```
`````

**Mockup prompt contract (Seedream)** (`brand-asset-creation/references/mockups.md`)
`````
```text
[CREATE ONE FINISHED BRANDED MOCKUP]
<specific object/application, credible setting, camera, material, lighting,
composition, and one brand-specific art-direction idea>

[AUTHORITATIVE LOGO]
<ImageN> is the exact approved <full-color/black/white> logo. Preserve its
spelling, silhouette, geometry, proportions, internal negative space, and exact
color. Do not redraw, simplify, crop, stretch, outline, or add effects.

[PLACEMENT LOCK]
Target surface: <exact object panel/face/material>.
Position: <exact alignment and location, e.g. horizontally centered, upper
third, optical center aligned to panel>.
Scale: logo occupies <specific proportion> of the target surface while keeping
<specific clear-space margin>.
Orientation: align to <panel edge/seam/baseline>; follow surface perspective
without changing logo proportions.
Color: use the supplied <full-color/black/white> variant exactly. State why it
contrasts correctly with the material/background.

[PHYSICAL APPLICATION]
Render the logo using <credible print/emboss/foil/engraving/ink behavior>.
Respect folds, grain, perspective, occlusion, reflections, scale, and
manufacturing limits.

No extra logos, pseudo-text, invented labels, warped marks, floating print,
unrelated props, arbitrary gradients, plastic sheen, or generic luxury staging.
```
`````

**Mockup text route** (`brand-asset-creation/references/mockups.md`)
`````
## Conditional text/detail route

If the final mockup contains any readable text—wordmark, brand name, tagline, packaging label, signage, product copy, or interface text—do not ask Seedream to render it:

1. Seedream creates the same-ratio scene with the target surface blank and no logo, letters, pseudo-text, or invented graphics.
2. GPT Image 2.6 receives `Image0` as that exact Seedream/user base and `Image1` as the approved logo/artwork reference.
3. The GPT prompt preserves Image0's camera, crop, objects, lighting, material, folds, shadows, perspective, and background exactly.
4. State the exact literal text, logo variant, placement, scale, alignment, clear space, color, and physical print/application behavior.
5. Keep the ratio identical to the user-approved ratio.

Use GPT Image 2.6 only for this controlled second stage. If there is no readable text, keep the one-call Seedream route.
`````

**Social graphic: what the prompt must state** (`brand-asset-creation/references/social-templates.md`)
`````
The prompt must state:

- Exact literal copy
- Display/body font family names and which text uses each
- Logo placement, scale, clear space, and color variant
- Text placement, hierarchy, alignment, line breaks, and contrast
- Exact palette roles
- Requested aspect ratio
`````

**Packaging inputs and build** (`brand-asset-creation/references/packaging.md`)
`````
## Required inputs

- package type and dimensions/dieline
- material and printing constraints
- exact product/flavor names
- required legal/regulatory copy
- barcode/nutrition/certification assets
- hierarchy and variants

Do not invent claims, ingredients, certifications, dosage, nutrition, pricing, or regulatory content.

## Build

- Create label/panel artwork deterministically in SVG or other requested editable format.
- Use exact approved logo, fonts, and palette.
- Keep copy editable.
- Preserve dieline folds, cut lines, bleed, and safe zones. Keep technical guides in an explicitly hidden group (for example `display="none"`) in artwork and clean previews; show them only in a separately labeled technical proof when requested. Custom attributes such as `data-print="false"` do not prevent SVG rendering or printing.
- Use one system across variants; vary only approved product information and designated color roles.

For presentation mockups, follow `mockups.md` after the packaging artwork is approved. The mockup is not the editable packaging source.
`````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Logo candidates (sole SVG generator) | `recraft_v4_1` | model_type vector, colors = selected hex set, background_color, count 1, 3 distinct requests via generate_image_batch |
| Concept / palette boards, mockup scenes | `seedream_5_5` (else newest Seedream tier from models_explore) | highest supported resolution (e.g. 2k), one model for the whole mockup set, ratio asked first |
| Text-bearing social graphics; second stage of text mockups | `gpt_image_2_6` | Image0.. = logo variant, typography specimen, product refs; exact copy and placement in prompt |
| Logo recolor/export, brandbook PPTX/PDF, review boards | none (sandbox scripts) | `brandkit.py logo-export | brandbook-build | preview`; deterministic |

## Checks and gates
- Supplied official assets are fixed immediately; generated options stay drafts until the user explicitly selects them.
- No downstream element (brandbook page, social template, deck, mockup) before its upstream locks exist; changing a slot invalidates dependents only.
- Interactive mode: after every visual review STOP for the user's ordinary reply; never infer approval from silence or tool success.
- Never redraw an uploaded logo that can be placed exactly; never regenerate the approved SVG; never run the logo enhancer or Recraft when an official logo exists.
- Never identify a font from pixels as certain; mark as a visual match until metadata or a font file proves it.
- Preserve exact user copy; never invent missions, values, flavours, prices, claims, statistics.
- Logo enhancer contract: symbol only (no brand name, wordmark, tagline), one central idea, constraint tail contains 'no text', no 3D treatment, one distinctive concrete element; one rewrite allowed, then stop.
- Failure policy: preview script and Recraft each retried once; logo-export geometry mismatch stops (no generative editing); brandbook build mismatch or PDF converter failure stops with no second route; social graphics never composed in the sandbox with Pillow.
- CMYK: an RGB SVG with CMYK metadata is not a validated print master; labelled provisional.
- Never says assets are approved, complete or 'beautiful' without QA and the required approval.

## Price pattern
Not quoted. Quotes before paying. Typical new-logo run = palette boards + 3 recraft_v4_1 candidates + review boards; typical supplied-brand run = scripts plus a few gpt_image_2_6 or seedream_5_5 generations.

## Cheap swap
- Everything that is not a picture is already free (brandbook, deck, logo export, review boards, packaging and poster SVG are scripts).
- Concept boards and mockup scenes: `seedream_5_0_flash` 2k at 0.5 or `gpt_image_2_6_flare` 1k low at 0.75 instead of 2 to 2.5 per 2k picture.
- Mockups onto flat targets (poster, screen, card, sign, front-facing pack): deterministic compositing of the exact logo, free, instead of a generative pass.
- Palette and typography options, Brand Lock, intake, rationale text: Claude on the plan, free.
- Vector cleanups and raster upscales: local BiRefNet matte / Real-ESRGAN (components/local-studio/README.md), free.
