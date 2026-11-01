# ByteDance video upscaler (Higgsfield) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/bytedance-upscaler-video.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- target resolutions: 1080p to 2k to 4k
- higgsfield claims up to: 8K for video (Higgsfield help page); the upstream API stops at 4K and errors above it: the two disagree, so 4K is the safe ceiling
- input resolutions: 480p to 720p to 1080p
- frame rate max: 60
- formats: mp4 to mov to webm to m4v to gif
- typical time: 1 to 5 minutes
- max duration: not stated by any source
- House: use the alternate when local Real-ESRGAN is not good enough

## The prompt structure that works

- **The local Real-ESRGAN is first; use this only as the alternate.**
- **Treat 4K as the ceiling: the upstream API errors above it.**
- **Feed 480p to 1080p sources.**
- **A video upscale takes 1 to 5 minutes; a stuck job is a retry, not a new spend.**
- **Check the result keeps the swipe's grain and the face.**

## Avoid

- Upscaling before the take is kept.
- Trusting the 8K claim without testing.
- A target above 4K on the API: it errors.
- Assuming the sound track survives the upscale.
