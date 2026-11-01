# ElevenLabs Eleven v3 (speech) — what it takes, and what works

*Rendered from `components/model-inputs/inputs/eleven-v3.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- max prompt chars: 5000
- max prompt chars note: 5,000 comes from a third-party review only; ElevenLabs' own prompting page gives no number. Confirm before relying on it.
- min prompt chars advised: 250
- output formats: mp3 and pcm tiers (set by output_format)
- languages: 70+ (third-party review)
- House: reads each line is its own read with that shot's delivery as an audio tag; never one long take for the whole piece; voice one custom voice per character (V4)

## The prompt structure that works

- **Each line is its own read with that shot's delivery as a tag; never one long take for the whole piece.**
- **Choose the voice first; a tag only works if the delivery already exists in the voice. A whisper tag fails on a loud voice.**
- **Match tags to the voice's character: a serious voice does not respond well to playful tags.**
- **Keep tags short, clear and about emotion, tone, pace or action; describe voice quality so it cannot be read as a sound cue.**
- **Give it enough text; very short inputs are inconsistent.**
- **Use ellipses for weight, capitals for emphasis and normal punctuation for rhythm instead of break tags.**
- **For the most expressive read use Creative or Natural stability.**
- **Write brand words and figures the way they are spoken; the text is the only lever.**

## Avoid

- SSML break tags: v3 ignores them.
- Playful tags on a serious voice.
- A Professional Voice Clone on v3 when clone quality matters: not fully optimised.
- One long take for the whole piece.
- A one-word or very short prompt.
- Tags the voice reads aloud because they read like speech.
