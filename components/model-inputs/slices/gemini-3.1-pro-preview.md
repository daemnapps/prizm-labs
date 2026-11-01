# Gemini 3.1 Pro (the judge) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/gemini-3.1-pro-preview.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- file api gb paid: 20
- file api gb free: 2
- inline mb: 100
- request total mb inline: 20
- videos per request: 10
- default fps: 1
- tokens per second: {'low_media_resolution': 100, 'high_media_resolution': 300}
- context video hours: {'low': 3, 'high': 1}
- formats: mp4 to mpeg to mov to avi to x-flv to mpg to webm to wmv to 3gpp
- House: busy_fallback ['gemini-3.5-flash', 'gemini-3-flash-preview']; fallback_rule when the judge answers 'high demand' (V17), never a cost choice

## The prompt structure that works

- **Put the video part first and the text prompt after it.**
- **Refer to moments with MM:SS so the answer points at a place.**
- **One check per read (face, product, leftover person, slop); a verdict that names the timestamp.**
- **Use the File API above 100 MB or for reuse.**
- **On 'high demand' fall back in order to the next model that can read video.**
- **Raise fps or clip the span for fast action; 1 fps misses it.**

## Avoid

- Putting the prompt before the video.
- Judging fast hands at the default 1 fps.
- Accepting a pass with no timestamp.
- Letting the judge approve: the owner approves status, the judge only checks.
- Custom fps or clipping in agentic mode: not supported.
