# Website Builder Flow

Builds a website, app, landing page or browser game on Higgsfield (not an ad): a phased image-grounded pipeline that ends in a deployed Cloudflare Worker with a generated cover.

Source files: `website-builder-flow/SKILL.md`, `website-builder-flow/references/website-flow.md`, `website-builder-flow/references/scroll-scrub.md`, `website-builder-flow/references/asset-system.md`, `website-builder-flow/references/reference-boards.md`, `website-builder-flow/references/app-cover.md`, `website-builder-flow/references/app-flow.md`, `website-builder-flow/references/game-flow.md`

## Inputs it needs

- The product type, the user's choice: `website` (independent brand, no AI generation), `app` (Sign in with Higgsfield, generation on credits) or `game`.
- For a website: Animated (scroll-scrub film, recommended) or Non-animated; an existing brand to honour or free rein; whether to publish to the community feed.
- A subdomain (more than 4 characters, lowercase letters, digits, single hyphens).

## Steps in order

1. **Resolve type** - Ask the type, animation, brand, and publish questions in one first call.
2. **Create site** - `create_website` with type, subdomain, template (scroll-scrub for animated, studio/preset/app-detail for apps).
3. **Concept and reference boards** - Design brief committed first, then one reference image per section.
4. **Asset system** - Brand kit, product universe, loops; everything submitted at once while the build proceeds.
5. **Film (animated sites)** - One ~15 s continuous take, 16:9, audio off, storyboard as a generic image reference (not start frame).
6. **Cover and metadata** - Two scene candidates at 3:2, judged, then composed with compose_cover.py (all type drawn by the script).
7. **Build to boards, motion, mechanical gate** - Section by section against the boards; one motion pass; mechanical gate before deploy.
8. **Deploy and optional publish** - `deploy_website`; `publish_website` only if the user said yes.

## Prompt blocks, word for word

**Cover scene prompt doctrine (six blocks)** (`website-builder-flow/references/app-cover.md`)

```text
1. Subject + action, concrete and physical ("a film editor in a bold red
   bomber jacket mid-leap, cutting a giant arc of 35mm film with oversized
   chrome scissors").
2. **World + props (story density)**: name 2–4 supporting elements that fill
   the frame around the subject. Add "no readable screens" whenever
   screens/props could sprout text.
3. **Scale + placement**: "waist-up, subject fills two thirds of the frame,
   positioned right-of-center" — and reserve the block side: "soft open
   negative space upper-left on a warm white wall". Negative space = a real
   surface (wall, sky, backdrop), NOT a black void.
4. Palette, committed and saturated: name 2–3 colors. Avoid lime/acid
   yellow-green.
5. Light + lens: "bright soft key with punchy shadows, low wide angle,
   commercial editorial grade".
6. Always end with: "no text, no letters, no logos, no captions, no UI".
```

**Rule that no model renders text** (`website-builder-flow/references/app-cover.md`)

```text
**The image model NEVER renders text. Not the title, not the wordmark, not
labels, not UI. It renders ONLY the scene.** Every glyph on the cover is drawn
by `compose_cover.py` from the Inter font — that is why the type is identical
and crisp on every cover, like the official ones. If a generated scene comes
back with lettering in it, the candidate is DEAD. Regenerate with "no text, no
letters, no logos, no captions" appended.
```

**Single-shot film rules** (`website-builder-flow/references/scroll-scrub.md`)

```text
ONE `generate_video` call. Drive the video model at its highest
quality with the approved storyboard as a **style/look reference**, and put the
continuous move in the PROMPT:

- Pass the storyboard with the model's GENERIC image/reference role — **not
  `start_image`**. As a start frame it becomes the literal first frame, so the
  page opens on a static storyboard for a second or two before motion begins.
- Ask for the longest single take the model supports (~15s), 16:9, highest
  resolution, and audio off — the page scrubs frames, not sound, and off is
  cheaper.
- Name the grade and the hexes; restate "no cuts, no camera shake, slow steady
  motion only, locked exposure, no on-screen text".
```

**Mandatory animation question rules** (`website-builder-flow/references/website-flow.md`)

```text
1. **Animation — MANDATORY, ALWAYS ask on every `type: "website"` build.** This
   question is NEVER skipped — ask it even when the request seems to imply a
   choice ("an animated site", "a plain static page"), even for a "simple" or
   "quick" site, even when you think you already know the answer. The user must
   make this call, not you. Offer exactly two options:
   - **Animated (recommended)** → sets `Animation mode: animated-website` — the
     scroll-scrub camera journey (the product default; mark it Recommended).
   - **Non-animated** → sets `Animation mode: non-animated` — a well-crafted site
     with lighter/optional motion, no mandatory camera journey.

   If the request already leans one way, still ask — just point the Recommended
   marker at the implied option. Record the picked value on the brief's
   `Animation mode` line (Phase 0). ONLY if the user is genuinely unreachable /
   never answers do you proceed on the default (**Animated**) and say so in one
   line — never as a shortcut to avoid asking.
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Reference boards and assets | `gpt_image_2_6` or `nano_banana_pro` | art-directed / photoreal and reference-driven |
| Seamless loops and the scroll film | `seedance_2_0` | single-shot film about 15 s, 16:9, highest resolution, audio off |
| Cover (photo route) | Soul (`soul_cinematic`) | 3:2, 2k, count 2 |
| Cover (graphic route) | `gpt_image_2_6` | 3:2, quality high, 2k, count 2 |
| Subject cutout, upscale | `remove_background`, `upscale_image` | cover compose needs 1500 px or more |
| Brand sting (sparingly) | `generate_audio` | model per `models_explore` |

## Checks and gates

- Type is the user's choice and the Animation question is mandatory on every website build; the answer picks the template.
- A `website` has no Higgsfield integration and no AI generation of any kind; anything that generates is an `app`; apps use Quanta and never a custom brand.
- Cover and metadata are a build step, never publish-only: an empty `og_title` or cover means the build is incomplete.
- Cover scene is judged before composing: text appeared, subject under about 50 % of frame, washed palette, missing negative space or AI tells kills a candidate.
- Mechanical gate before first deploy; the film is not vision-inspected (single-shot has no seams); multi-leg needs exact-frame handoffs.
- Cover video (`og_video_url`) and publishing are permission-gated; secrets are never asked for in chat; repo pushes confirm `status: pushed` before deploy.
- This is not an ad workflow; included for completeness.

## Price pattern

Not quoted: `gpt_image_2_6`, `nano_banana_pro`, `seedance_2_0` and Soul are not in `_prices.md`. The generation spend is boards, asset images, a ~15 s film (one long Seedance take, comparable to or above the 10 s quotes) and two cover candidates; every generation is quoted before it runs.

## Cheap swap

- Film: `wan3_0` 480p: 7.5 credits per 10 s quoted, against 30 for a `seedance_2_5` 480p draft (a quarter) (a 15 s take is about 11 credits), though quality for a scroll film may drop.
- Boards, assets and cover candidates: `seedream_5_0_flash` 2k: 0.5 credits a picture quoted, against 1.75-2.5 for 2k pictures or `gpt_image_2_6_flare` 1k low: 0.75 credits a picture quoted; subject cutout on local BiRefNet; upscale on local Real-ESRGAN.
- Writing the brief and code is Claude on the plan, free to us.
