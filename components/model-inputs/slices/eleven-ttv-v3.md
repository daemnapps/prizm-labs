# ElevenLabs Voice Design (eleven_ttv_v3) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/eleven-ttv-v3.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- voice description: required; the maker states no maximum
- text chars: 100 to 1000
- reference audio: base64, eleven_ttv_v3 only; size limit not stated
- previews: returned as a list; maximum not stated
- House: rule one custom voice per character, designed from the cast member's description and a real reference recording

## The prompt structure that works

- **Design from a real reference recording on v3 so the voice has a human base.**
- **Prefer a longer, more detailed description at a low guidance scale over a short one at a high scale.**
- **Design the voice once and bank it; every later read uses that voice id.**
- **Pin the seed once a preview is chosen so the voice can be rebuilt.**
- **Keep the sample text between 100 and 1000 characters.**
- **Listen to every preview and pick by ear; a 409 means a preview is still generating, retry.**

## Avoid

- A high guidance scale: the voice turns artificial or robotic.
- A reference recording on the v2 design model: only v3 takes it.
- Sample text under 100 or over 1000 characters.
- Designing a new voice each run: the character changes.
