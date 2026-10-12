<!-- v3 (2026-10-09, the owner, after a set of song ads came back photoreal from a 3D-animated swipe — "the creative format itself is supposed to look like Pixar … you need to actually analyze the format and the style … this should be in the process … something similar happened when we were doing the doll ads … so we're not wasting time on credits"): two new lines, STYLE and FORMAT, each ONE id from the element library ({styles}, {formats}), read off the pictures and the sound. run.py records them on the run (style_id, format_id) and every picture after it is made in that style. Everything in v2 stands. -->
Classify this video for a swipe-file triage. Answer in exactly this format, nothing else:

LANE: one of ALREADY AN AD | ORGANIC | STATIC | SEQUENTIAL — is this a paid ad (product pitch, offer, CTA to buy) or organic content?
CATEGORY: what product/service category and who the speaker appears to be (age range, gender).
RUNTIME: the video's length.
SOUND FORM: one of SPOKEN | SUNG | RAPPED | MUSIC ONLY | SILENT — how the words reach the ear. LISTEN before answering; this is not visible on screen and cannot be judged from the pictures. SUNG means a voice carries the words on a melody for most of the runtime. RAPPED means rhythmic delivery over a beat without sung pitch. MUSIC ONLY means a bed with no words. A spoken voice over music is SPOKEN, not SUNG. If the piece switches — a sung chorus between spoken verses — answer with the dominant form and add "· mixed: <what the other part is>".
STYLE: the visual style — what every picture LOOKS like, read off the frames, not the topic. Exactly ONE `id` from the style list below, then " — " and what you see that makes it that style (eyes, proportions, skin, surfaces, light, capture). The test: swap the style and the script, cast and beats would stay the same. Real people filmed on a phone is the phone-ugc row; a 3D-animated film, a doll or puppet world, claymation, anime and so on each have their own row — never call a stylised or animated piece real footage. If no row fits, write `new:<short-name>` and describe it.
FORMAT: the video format — the shape the piece carries its message in. Exactly ONE `id` from the format list below, then " — " and why. If no row fits, write `new:<short-name>` and describe it.
AI ASSESSMENT: is any part of this video AI-generated (synthetic voice, generated avatar/likeness, AI b-roll, generated images)? Name the specific tells you observe — lip-sync drift, unnatural blinks, texture shimmer, impossible physics, TTS cadence, watermarks of gen tools — or state "no AI tells observed". Give a confidence: LIKELY AI | POSSIBLY AI | LIKELY HUMAN.
ONE LINE: what happens in the video.

THE STYLE LIST (pick an `id`):
{styles}

THE FORMAT LIST (pick an `id`):
{formats}
