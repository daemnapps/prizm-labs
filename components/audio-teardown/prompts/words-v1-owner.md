*v1 (2026-09-25): the words of the swipe, in every language, exactly as said. Written after the Scribe test: speech-to-text turned a Korean mother's lines into "[laughs]", and on a second run translated her into English without saying so. the owner: "we need the ability to transcribe ALL language." This prompt writes the WORDS; who spoke when comes from a separate listener and the two are merged by code.*

Transcribe this audio word for word.

**Every word exactly as it was spoken, in the language it was spoken in.**
- Never translate. Korean stays in Hangul, Spanish stays Spanish, Chinese stays in Chinese characters, Russian stays in Cyrillic.
- When a speaker switches language mid-sentence, write each word in the language it was said in: "Every night 엄마 이거 쓰지."
- An English word said inside another language stays in English; a borrowed word said with a foreign accent is written as the word they meant ("nothing", not "낫띵").
- Keep fillers, false starts, repeats, stutters and cut-off words ("I- I was", "um", "like").
- Do not tidy grammar, finish sentences, or summarise.
- Mark non-speech only in square brackets, and only when it is clearly there: [laughs], [sighs], [music], [crosstalk]. Never write a bracket in place of speech you could not understand. Write [inaudible] instead.

**One entry per speaker turn.** A new entry whenever the speaker changes, or when one speaker pauses for more than about a second. Label speakers Speaker 1, Speaker 2, … in order of first appearance, by voice.

**For every entry give its language** as an ISO 639-1 code. If one entry mixes languages, give the main one and list the others.

Return JSON only, no commentary:

[{"speaker": "Speaker 1", "start": <seconds from the start, one decimal>, "end": <seconds>, "text": "<exactly what was said>", "language": "<code>", "also": ["<other language codes in this entry, if any>"]}]

If there is no speech at all, return [].
