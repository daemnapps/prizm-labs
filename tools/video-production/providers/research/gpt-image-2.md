# GPT Image 2 — three doors, exact fields

Caveat up front: OpenAI's own pricing page (openai.com/api/pricing) blocked the fetch (403); pricing below for the direct API is triangulated from third-party trackers, not OpenAI's page itself. Everything else is quoted from the vendor's own docs.

## 1. Direct — OpenAI API

- **Model id:** `gpt-image-2`, default snapshot `gpt-image-2-2026-04-21`. OpenAI's current guide is steering new integrations to the newer `gpt-image-2.5-sunburst` (precision editing) and `gpt-image-2.5-flare` (fast, everyday) — same family, same field names below, `gpt-image-2` itself still listed as a model. [Model page](https://developers.openai.com/api/docs/models/gpt-image-2) · [Images/vision guide](https://developers.openai.com/api/docs/guides/images-vision)
- **Endpoints:** `v1/images/generations` (from scratch) and `v1/images/edits` (modify existing, "either partially or entirely"). [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- **Reference images:** edit endpoint takes an `image` param as an array (`image[]` in multipart form) — code samples show multiple files at once. When multiple images are passed, **"the first image in the list preserves the finest detail."**
- **Masks:** yes, `mask` param. "The image to edit and mask must be of the same format and size (less than 50MB in size)" and the mask needs an alpha channel.
- **Sizes:** named presets `1024x1024`, `1536x1024`, `1024x1536`; also free-form `WIDTHxHEIGHT` where "width and height must be multiples of 16, the aspect ratio must be between 1:3 and 3:1, and neither edge may exceed 3840 pixels" — so a 9:16-style frame and 2K-class output are both reachable via custom dimensions, there's no named `9:16` or `"2K"` enum value.
- **`quality`:** `low`, `medium`, `high`, `xhigh`, `max`, `auto` (xhigh/max are the 2.5 sunburst/flare tier).
- **`background`:** `transparent`, `opaque`, `automatic` (transparent requires `output_format` = `png` or `webp`).
- **`output_format`:** `png` (default), `jpeg`, `webp`; `output_compression` 0–100 for jpeg/webp.
- **`moderation`:** `auto` (default, "standard filtering...age-inappropriate content") or **`low`** ("less restrictive filtering") — confirmed, this is the field your clean-frame problem needs. [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- **`input_fidelity`:** `"high"` is the documented value — "especially useful when editing images with faces, logos, or any other details that require high fidelity... faces are preserved far more accurately than in standard mode." Costs more input tokens than default. [High-fidelity cookbook](https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity)
- **Streaming:** `partial_images` param, 0–3, streams `response.image_generation_call.partial_image` events.
- **Batch/rate limits:** `v1/batch` supported for bulk; per-minute tiers are TPM/IPM — Tier 1: 100k TPM / 5 IPM, Tier 2: 250k/20, Tier 3: 800k/50, Tier 4: 3M/150, Tier 5: 8M/250.
- **Response:** base64 — `b64_json` field per image.
- **Price (third-party-tracked, not OpenAI's own page):** roughly $0.006 (low) to $0.211 (high) per 1024×1024 image; edit calls with reference images bill image-input tokens (~$8/1M) on top, so edit-heavy runs run 2–3x a bare generation.

## 2. fal.ai

Two separate model families, don't conflate them:
- `fal-ai/gpt-image-1/edit-image` — the **older** gpt-image-1, not gpt-image-2.
- **`openai/gpt-image-2`** (text-to-image) and **`openai/gpt-image-2/edit`** (image-to-image) — the current ones. [Edit API docs](https://fal.ai/models/openai/gpt-image-2/edit/api) · [Generate](https://fal.ai/models/openai/gpt-image-2)

Edit endpoint fields: `prompt` (required), `image_urls` (list, **max 16**), `mask_url`, `image_size` (presets `square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9` or custom `{width,height}` — `portrait_16_9` is your 9:16), `background` (`auto/transparent/opaque`), `quality` (`auto/low/medium/high` — **no xhigh/max**), `num_images`, `output_format`, `sync_mode`. Generate endpoint is the same minus `image_urls`./`mask_url`./`background`.

**Missing vs direct:** no `input_fidelity` field anywhere in the schema, no `moderation` field anywhere in the schema.

**Price:** edit endpoint ranges $0.011–$0.151 (1024×768) up to $0.024–$0.413 (3840×2160) across low/medium/high; generate endpoint is slightly cheaper, same shape.

## 3. Higgsfield

CLI/model id `gpt_image_2` (plus `gpt_image_2_5` with `flare`./`sunburst` variants). [MODELS.md](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md) · [product page](https://higgsfield.ai/gpt-2) · [2.5 blog](https://higgsfield.ai/blog/gpt-image-2-5-higgsfield)

- **References:** `--image-references` / `--image`, repeatable. The CLI/MODELS.md doc I could reach states the **2.5** variants take "at most 16"; a separate web summary put the base `gpt_image_2` cap at 14 — sources disagree, verify against your account before batching. I found **no documented `<<<uuid>>>` element-injection syntax or `image_references`-as-medias-role field** in the CLI README or MODELS.md — that pattern may exist only in Higgsfield's web "Elements" UI, not the CLI/API surface these docs cover; flag as unconfirmed rather than assumed present.
- **Resolution:** `1k`, `2k`, `4k` (default `2k` for base model, `1k` for 2.5). Product page separately claims "native 4K" output.
- **Quality:** base `low/medium/high`; 2.5 adds `xhigh`./`max` (labelled Low/Medium/High/Extra High/Max).
- **Aspect ratios:** long enum including `9:16`, `16:9`, `1:1`, etc.
- **`--background`:** `auto/opaque/transparent`. Inpainting via `--is_inpaint` + `--mask`.
- **No `moderation` or `input_fidelity` parameter documented anywhere** I could reach (CLI README, MODELS.md, product page, 2.5 blog).
- **Price:** only the 2.5 credit table is published — 1K/Low = 1.5 credits ($0.075) up to 4K/Max = 26.5 credits ($1.325). Base `gpt_image_2` pricing isn't broken out separately in public docs. **No rate/concurrency limits documented** anywhere I could reach.

## Verdict table

| Capability | Direct API | fal.ai | Higgsfield |
|---|---|---|---|
| Multi-reference input | ✓ `image[]`, order-sensitive (first = finest detail) | ✓ `image_urls`, max 16 | ✓ `--image-references`, cap disputed (14 vs 16) |
| High input fidelity (`input_fidelity`) | ✓ `input_fidelity: "high"` | ✗ not in schema | ✗ not documented |
| Moderation control | ✓ `moderation: "low"` | ✗ not in schema | ✗ not documented |
| 9:16 at highest res | partial — custom `WIDTHxHEIGHT`, no named alias, max edge 3840px | ✓ `portrait_16_9` preset | ✓ named `9:16` + `4k` |
| Mask/inpainting | ✓ `mask` | ✓ `mask_url` | ✓ `--mask`./`--is_inpaint` |
| Batch / high-volume | ✓ `v1/batch`, tiered rate limits | no batch endpoint found; no stated rate limits | no rate/concurrency limits documented |

## The ruling

The two things this process cannot lose — `input_fidelity: high` for faces/labels, and `moderation: low` so clean product frames don't get blocked — exist **only** on the direct OpenAI API; neither fal nor Higgsfield expose them at all, on any model variant, in any doc I could reach. fal is otherwise a clean mirror (same sizes, same masks, cheaper), so it's a fine fallback for pure exploration/drafting where a slightly-lower-fidelity frame is tolerable. Higgsfield's `gpt_image_2` gives you the resolution and aspect-ratio menu but nothing on fidelity or moderation, and its own docs disagree on the reference-image cap and never publish rate limits — treat it as the least-controlled of the three for this specific job. **Primary door: direct OpenAI API**, specifically for the two steps that must not drift (cast-sheet build, first-frame seed with packshot) — route only the exploratory/cheap-draft volume through fal or Higgsfield.

## Sources

- https://developers.openai.com/api/docs/models/gpt-image-2
- https://developers.openai.com/api/docs/guides/image-generation
- https://developers.openai.com/api/docs/guides/images-vision
- https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity
- https://fal.ai/models/openai/gpt-image-2
- https://fal.ai/models/openai/gpt-image-2/edit
- https://fal.ai/models/openai/gpt-image-2/edit/api
- https://fal.ai/models/fal-ai/gpt-image-1/edit-image/api
- https://higgsfield.ai/gpt-2
- https://higgsfield.ai/blog/gpt-image-2-5-higgsfield
- https://github.com/higgsfield-ai/cli/blob/main/MODELS.md
- https://github.com/higgsfield-ai/cli/blob/main/README.md
