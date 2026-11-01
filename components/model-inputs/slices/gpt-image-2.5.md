# GPT Image 2.5 — what it takes, and what works

*Rendered from `components/model-inputs/inputs/gpt-image-2.5.json` (read 2026-10-26, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- Images per call: up to 16, each png, webp, jpg under 50 MB.
- Prompt: up to 32,000 characters.
- Size: WxH, both multiples of 16, each edge up to 3840, ratio up to 3:1, 655,360 to 8,294,400 pixels (above 3,686,400 is experimental).
- Quality: low, medium, high, xhigh, max, auto.
- House: quality high (video stills xhigh), frame 9:16, centre 4:5 is the safe zone, top and bottom 15% bleed.

## The prompt structure that works

- **Say what the picture is first: subject, what it is for, composition, aspect ratio, where things sit.**
- **Use labelled sections: scene, subject, details, constraints.**
- **Number every input and give it a role; say how they combine and what moves where.**
- **Name what must not change (face, skin tone, labels, proportions, background, camera angle), say 'change only X', add 'do not change anything else'.**
- **Put exact words in quotes with position and typography; ask for no extra text; say how many times it appears ('exactly once'); spell odd brand names letter by letter.**
- **Ask for a real photo in plain words: 'photorealistic', 'real photograph', real texture and wear; avoid cinematic, studio or staged wording.**
- **Describe people concretely: body framing ('full body, feet included'), gaze, scale, how hands hold things.**
- **State the aspect ratio and what must stay clear of the edges.**
- **Iterate one change at a time: feed the last picture back, change one thing, restate what to keep. Repeated edits drift.**
- **Do not rely on the prompt for pixel-exact parts: composite the approved piece into the original.**

## Avoid

- Mood words with no scale, atmosphere or colour.
- Unlisted exclusions: say 'no watermark, no extra text, no logos'.
- Studio, cinematic or staged wording when you want a real photo.
- Tiny text; use quality high for small labels.
- Assuming a higher quality setting always gives a better result.
- Copying settings from an older model unchanged.
- Trusting the text in the result without reading it.
- A person's name, a date or a quote from our own rulings inside the prompt: the model draws it as picture content.

## Through Higgsfield (differs from the maker's own door)

- variants: flare, sunburst
- qualities: low, medium, high, xhigh, max
- resolutions: 1k, 2k, 4k
- backgrounds: auto, opaque, transparent
- aspect ratios: auto, 1:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16, 21:9, 27:16, 16:27, 9:8, 8:9, 4:5, 5:4
- references: role image_references; Higgsfield publishes no maximum for this model (its rules list is empty), so OpenAI's 16 is assumed until a live call shows otherwise
- house: variant sunburst, quality high, resolution 2k, aspect_ratio 9:16
- differs from openai: A call that sends nothing gets flare at low quality and 1k, the cheapest picture. Our calls must name sunburst, high and the resolution every time.
- default variant: flare
- default quality: low
- default resolution: 1k
- Not available: mask (no region edit); n; moderation; output_format; custom WxH size (a resolution tier and an aspect ratio instead); input_fidelity.
