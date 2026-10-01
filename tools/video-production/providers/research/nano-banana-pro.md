# Nano Banana Pro — three doors for discrete edits (web research, 2026-09-17)

Model: **Gemini 3 Pro Image**, marketing name "Nano Banana Pro." API model id is
`gemini-3-pro-image` (Google's own model card); many third-party pages and fal
still use the preview id `gemini-3-pro-image-preview` — treat both as valid,
confirm which one your account resolves before locking it in. "Nano Banana 2"
is a **different, cheaper/faster model**: `gemini-3.1-flash-image` (a
"3.1 Flash Lite Image" tier also exists: `gemini-3.1-flash-lite-image`). Do not
conflate the two — Higgsfield's console also separates `nano_banana_pro` from
`nano_banana_2`.

## 1. Direct — Gemini API (ai.google.dev)

- **Model ids**: `gemini-3-pro-image` (Pro/"Nano Banana Pro"), `gemini-3.1-flash-image`
  ("Nano Banana 2"), `gemini-3.1-flash-lite-image`, legacy `gemini-2.5-flash-image`.
- **Multi-image input for composition/editing** — the 3 Pro model's limits are stated as:
  up to **6 object images, 5 character images**; the Flash-tier model instead
  allows up to 10 object / 4 character / 3 style-reference images. (Source:
  ai.google.dev/gemini-api/docs/image-generation.) No separate "mask" input is
  documented — edits are instruction-driven (natural-language edit on
  supplied reference images), not mask-based.
- **`imageConfig` fields**: `aspectRatio` (values: `"1:1", "3:2", "2:3", "3:4",
  "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"`) and `imageSize` (values:
  `"1K", "2K", "4K"`, plus a `0.5K`/512px tier on some models). Default with no
  config is square 1024x1024.
- **Reasoning/composition**: the model runs a "thinking" process and produces
  interim "thought images" before the final render — this is the mechanism
  that plans multi-reference composition.
- **Text rendering**: documented as "advanced text rendering... legible,
  stylized text for infographics, menus, diagrams, marketing assets" — this is
  the headline feature vs. older models.
- **SynthID**: "All generated images include a SynthID watermark" — invisible,
  non-removable, applies on every door (direct, fal, Higgsfield all inherit it
  since they all call the same underlying model).
- **Safety settings**: fully exposed and adjustable via `safety_settings` /
  `GenerateContentConfig`, per-category `HARM_CATEGORY_HARASSMENT`,
  `HARM_CATEGORY_HATE_SPEECH`, `HARM_CATEGORY_SEXUALLY_EXPLICIT`,
  `HARM_CATEGORY_DANGEROUS_CONTENT`, `HARM_CATEGORY_CIVIC_INTEGRITY`, each
  settable to `BLOCK_NONE / BLOCK_ONLY_HIGH / BLOCK_MEDIUM_AND_ABOVE /
  BLOCK_LOW_AND_ABOVE`. Google states core child-safety protections cannot be
  disabled regardless of setting.
- **Pricing** (ai.google.dev/gemini-api/docs/pricing): Gemini 3 Pro Image —
  input $2.00/M tokens (~$0.0011/image), output **$0.134 per 1K/2K image**,
  **$0.24 per 4K image** (priced as $120/M output tokens, ~1,120 tokens/image).
  Nano Banana 2 (3.1 Flash Image) — $0.045 (0.5K) / $0.067 (1K) / $0.101 (2K) /
  $0.151 (4K) per image.
- **Batch mode**: supported ("Batch API" listed as a capability on the 3 Pro
  Image model card) and carries a flat **50% discount** — 2K drops to
  $0.067/image, 4K to $0.12/image.
- **Rate limits**: Google no longer publishes a full numeric table since
  ~March 2026; quota is per-project across RPM/TPM/RPD/IPM and tier-gated
  (free tier reports being far lower than paid Tier 1, which several
  third-party trackers put around 150–300 RPM). Confirm your project's actual
  tier in the Cloud console rather than trusting any blog's number.

Sources: https://ai.google.dev/gemini-api/docs/image-generation ·
https://ai.google.dev/gemini-api/docs/models/gemini-3-pro-image ·
https://ai.google.dev/gemini-api/docs/pricing ·
https://ai.google.dev/gemini-api/docs/safety-settings ·
https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/gemini-image-responsible-ai ·
https://blog.google/technology/developers/gemini-3-pro-image-developers/

## 2. fal.ai

Confirmed live endpoints (fal.ai/models pages, schema pulled directly):

- `fal-ai/nano-banana-pro` — text-to-image generation.
- `fal-ai/nano-banana-pro/edit` — image-to-image / editing (accepts references).
- `fal-ai/gemini-3-pro-image-preview` and `fal-ai/gemini-3-pro-image-preview/edit`
  also exist as aliases (same underlying model, preview id).

**`/edit` input schema** (field names verbatim):
`prompt` (string, required), `image_urls` (list of strings, required — no
documented hard cap in the schema itself, but treat Google's 6-object/5-character
ceiling as the practical limit since fal is a thin wrapper over the same model),
`num_images` (int, default 1), `seed`, `aspect_ratio` (enum:
`auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16`, default `auto`),
`output_format` (`jpeg, png, webp`, default `png`), `resolution` (enum
`1K, 2K, 4K`, default **1K** — you must set this explicitly to get 2K),
`safety_tolerance` (enum `1`–`6`, default `4`; 1 = strictest, 6 = most
permissive — this is fal's equivalent of Google's `safety_settings`, exposed
as a single tunable knob instead of five per-category ones), `sync_mode`
(bool), `system_prompt` (string), `enable_web_search` (bool),
`limit_generations` (bool, default true).

The plain generation endpoint (`fal-ai/nano-banana-pro`) has the identical
parameter set minus `image_urls`.

**Pricing**: **$0.15/image** flat for 1K/2K generation or edit, **$0.30 for
4K**, +$0.015 if `enable_web_search` is on.

**What's missing vs. direct**: no `imageConfig`-style structured object (it's
flattened into top-level fields, functionally equivalent); no per-category
safety controls, only the single `safety_tolerance` scalar; no explicit batch
discount tier (fal's batch/queue mode is about throughput, not price); no
documented mask input either door. Functionally, fal is a faithful pass-through
of the same model — the only real gaps are per-category safety granularity and
the batch price break.

Sources: https://fal.ai/models/fal-ai/nano-banana-pro/edit/api ·
https://fal.ai/models/fal-ai/nano-banana-pro/api ·
https://fal.ai/nano-banana-pro ·
https://fal.ai/docs/model-api-reference/image-generation-api/nano-banana-pro

## 3. Higgsfield

- Models: `nano_banana_pro` and `nano_banana_2`, called through
  `generate_image` (JSON body) or the CLI/MCP wrapper.
- **Reference images travel in a `medias` array**, each entry shaped
  `{ "value": "<url>", "role": "image" }`. This is the exact, documented shape —
  and it is **not** `{"url": ..., "roles": [...]}` or a top-level
  `image_references` field. One community skill doc calls this out explicitly:
  *"The medias field requires `{value: string, role: string}`, not `{url: ...,
  roles: [...]}`"* and *"Use `value` (not `url`) for the media reference."*
  This lines up with what your runs hit — a request shaped with `url`./`roles`
  or an `image_references` key will pass whatever loose validation Higgsfield
  does and come back with the reference simply not attached (empty), because
  the field the model actually reads (`medias[].value` / `medias[].role`) was
  never populated.
- **Max references**: Higgsfield's own consumer-facing docs describe
  "multi-reference" support up to **8 images in one composition** for the
  standard flow, with mentions of extending to **up to 14** references in some
  contexts — but this is UI-level messaging, not a confirmed hard API cap; the
  API docs proper (docs.higgsfield.ai) don't publish a numeric ceiling for
  `medias` length, so probe empirically before batching.
- **Resolution**: `resolution` field takes `"1k" | "2k" | "4k"`; Higgsfield
  markets `nano_banana_2` as native 4K and `nano_banana_pro` as reasoning-first
  (precision over speed) — both are backed by the same underlying Google
  models as the other two doors, so the ceiling is the same 4K.
- **Aspect ratio**: `aspect_ratio` field accepts the same style enum
  (`1:1, 2:3, 3:4, 4:5, 9:16, 16:9, 21:9`, etc.) as fal/direct — but this is
  exactly the field your runs found being **ignored for 9:16**, which is
  consistent with Higgsfield's API being a thinner, less-mature wrapper than
  fal's: the field exists in the schema and is accepted, but downstream
  application to the actual generation call has been unreliable in practice.
  Treat any Higgsfield aspect-ratio request as needing a post-hoc crop/pad
  check, not a guarantee.
- **Pricing**: in **credits**, not USD directly — third-party trackers report
  "a single Nano Banana Pro generation consumes about 4–5 credits" on
  Higgsfield's own plans (credit-to-dollar rate depends on your plan tier);
  resellers proxying the same model (APIYI, Segmind) charge $0.05–$0.23/call,
  which is not Higgsfield's own price and not a reliable proxy for it.
- **Concurrency**: not published in any doc surfaced (docs.higgsfield.ai's
  request-lifecycle/polling pages describe the mechanics of async jobs and
  webhooks, not a concurrency number) — assume undocumented and test your own
  ceiling.

Sources: https://docs.higgsfield.ai/docs · https://docs.higgsfield.ai/docs/llms.txt ·
https://higgsfield.ai/nano-banana-intro · https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-nano-banana-pro ·
https://skills.lc/S3YED/appie-kit/s3yed-appie-kit-skills-content-higgsfield-image-skill-md ·
https://help.apiyi.com/en/higgsfield-nano-banana-pro-api-low-cost-alternative-en.html

## Verdict table

| Capability | Direct (Gemini API) | fal.ai | Higgsfield |
|---|---|---|---|
| Multi-reference (2nd image = packshot) | Yes, documented 6 object/5 character refs | Yes, same model, `image_urls` list | Yes, `medias[]`, but shape is easy to get wrong (must be `value`./`role`, not `url`./`roles`) |
| 2K output | Yes, `imageSize: "2K"` | Yes, `resolution: "2K"` | Yes on paper (`resolution: "2k"`), same backing model |
| Exact aspect ratio | Yes, `aspectRatio` enum, applied reliably (it's Google's own API) | Yes, same enum, applied reliably (thin pass-through) | Field exists but **your runs found 9:16 ignored** — unreliable |
| Identity preservation across edit | Same model everywhere — no difference | Same | Same |
| Safety threshold control | Full per-category control (5 categories × 4 levels) | One scalar (`safety_tolerance` 1–6) — coarser but usable | Not documented at all |

## Ruling

1. Nothing your edit process needs is *missing* at fal — it's the same model,
   same reference-image mechanics, explicit resolution/aspect fields, just a
   single safety scalar instead of five category knobs (still adjustable, just
   coarser).
2. Higgsfield is the odd one out: your own runs already found its aspect-ratio
   handling unreliable (9:16 ignored) and its reference-image field has a
   documented gotcha (`medias[].value`./`role`, not `url`./`roles` or
   `image_references`) that silently no-ops if you get the shape wrong.
3. Direct Gemini API is the only door with fine-grained safety control and a
   confirmed batch discount (50% off at scale) — worth it only if you're
   running high volume and can tolerate async batch latency.
4. For your discrete-edit loop (approved frame + packshot in, one change out,
   everything else preserved), **fal should be primary**: same model fidelity
   as direct, reliable aspect/resolution fields, one API call, no OAuth/GCP
   project setup — with direct-API batch mode as a cost lever once volume
   justifies it.
5. Keep Higgsfield only where you already depend on its other tooling; don't
   route new edit work through it until its aspect-ratio behavior is
   independently re-verified — the wrong `medias` shape it will still accept
   silently is a real trap for a machine-driven, unattended pipeline.
