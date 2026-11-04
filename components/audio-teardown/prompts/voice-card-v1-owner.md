*v1 (2026-09-25): one voice card per person, from that person's own lines cut out of the swipe. the owner: "we can make really really really powerful avatar, sub avatar, casting calls that are direct and detailed and when we generate voice, we know exactly what to generate." The numbers below were MEASURED by a tool from this clip; your job is what an ear hears.*

This clip is ONE person's lines from a short video, cut together, with the music removed. Describe the voice the way a casting director and a voice director would, so the voice can be cast or generated to match.

What was measured from this clip (use it, don't contradict it without saying why):
{measured}

What they say (their own lines, in the language said):
{lines}

Only what you can hear. Mark anything you are unsure of with "(unsure)". Never name or compare to a real, identifiable person.

Every label field takes values ONLY from these lists. If nothing on a list fits, write "other: <your word>":
{lists}

For delivery_style, choose from these (the doctrine's own delivery dial):
{delivery_styles}

Return JSON only:
{
 "languages": ["<ISO 639-1 codes spoken, main first>"],
 "accent": "<accent and region as specifically as you can hear it, per language, e.g. 'Seoul Korean; Korean-accented English'>",
 "age_band": "<list value>",
 "gender_presentation": "<list value>",
 "pitch_band": "<list value>",
 "texture": ["<one to three list values>"],
 "read_style": "<list value>",
 "delivery_style": "<doctrine value>",
 "energy": "<list value>",
 "emotion": "<the feeling in the voice, in a few plain words, and where it changes>",
 "pace": "<how the pace feels, and where it speeds up or slows>",
 "emphasis": ["<the words or phrases they punch>"],
 "tics": ["<fillers, laughs, sighs, catchphrases, verbal habits>"],
 "mic_space": "<list value>",
 "talks_to": "<list value>",
 "casting_call": "<one direct sentence a casting call could use: who, age, accent, voice, manner>",
 "voice_prompt": "<a short description a voice generator could build this voice from: gender, age, accent, pitch, texture, pace, energy, manner — no names>"
}
