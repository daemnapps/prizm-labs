*v1 (2026-09-30): the effects, named and given their job. A tool found WHEN every sharp sound happens; each moment was then checked on its own one-second clip (prompts/effects-check). This read hears the whole track with the confirmed moments listed, says what job each does in the edit and which industry category it files under, and adds any the check missed.*

This is the soundtrack of a short social video with the voices removed: music plus every added sound effect and real sound. These moments were confirmed as sound effects, each on its own clip:
{events}

For every moment listed, say what job it does in the edit, which UCS category it files under, and whether it was added in the edit or made by the room or the product. Keep the name unless you are sure it is wrong. Then add any added sound effect the list missed. Ignore the music itself and ignore speech.

Only what you can hear. Every label field takes values ONLY from these lists; if nothing fits, write "other: <your word>":
{lists}

Return JSON only:
{
 "effects": [{"at": <seconds>, "name": "<plain cue name, one or two lower-case words>", "ucs_category": "<ucs_category value>", "job": "<effect_job value>", "added": <true if put there in the edit, false if the room or the product made it>, "missed_by_list": <true only for one you added>}],
 "room": "<the real sound of the place under everything: room tone, echo, street, water, silence>"
}
