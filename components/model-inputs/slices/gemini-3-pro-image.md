# Nano Banana Pro (Gemini 3 Pro Image) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/gemini-3-pro-image.json` (read 2026-10-26, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- max images: 14
- max images note: Google's tips: blend up to 6 to 14 unconnected images depending on the surface; the API page lists up to 6 object images, 5 character images and 3 style images in its comparison table (flattened in the fetch: verify)
- image sizes: 1K (default), 2K, 4K; the K must be uppercase, lowercase is rejected
- aspect ratios: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 (the list Higgsfield shows for this model; Google's page list for Pro was not readable)
- thinking: on by default and cannot be switched off in the API; up to two interim images, the last is the final
- watermark: every generated image carries a SynthID watermark
- grounding: Google Search grounding is available
- multi turn: multi-turn conversation is the recommended way to iterate

## The prompt structure that works

- **Core elements: subject, composition, action, location, style, and the editing instruction; add aspect ratio, camera and lighting, text placement, factual constraints and reference roles for professional results.**
- **Describe the scene in full sentences, not keywords.**
- **Define the role of each uploaded image: 'Use Image A for the pose, Image B for the art style, Image C for the background.' State how the references relate.**
- **For an edit be direct and specific about the change and state what stays the same.**
- **Define the canvas with an aspect ratio in the prompt too ('a 9:16 vertical poster').**
- **Direct it like a cinematographer: angle, depth of field, lighting, colour grading.**
- **State exactly what text appears and how: the words in quotes, the font style, the placement.**
- **For diagrams or factual pictures request accuracy explicitly and supply factual inputs.**
- **Iterate by conversation: one change at a time, restating what must hold.**

## Avoid

- Expecting perfect small text, fine detail or spelling.
- Trusting data-driven or factual visuals without checking them.
- Assuming text in other languages is free of grammar errors.
- Expecting complex edits, blends or lighting changes to be free of artifacts.
- Assuming character consistency stays perfect across edits.
- Lowercase image sizes: '2k' is rejected, send '2K'.
- Studio, cinematic or staged wording when you want a real photo.
- A person's name, a date or a quote from our own rulings inside the prompt: the model draws it as picture content.

## Through Higgsfield (differs from the maker's own door)

- resolutions: 1k, 2k, 4k
- aspect ratios: 1:1, 3:2, 2:3, 4:3, 3:4, 4:5, 5:4, 9:16, 16:9, 21:9
- references: role image_references; at most 14 (Higgsfield's own rule); a non-empty prompt or at least one reference is required
- differs: Reachable through the Higgsfield command line only: the keyed API answers model_disabled.
- default resolution: 2k
