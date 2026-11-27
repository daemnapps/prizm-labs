<!-- v7 (2026-11-19): a HEADLINE FORMAT line (the words first) beside the HOOK FORMAT line (what you see first), from the locked headline formats ({video_names}), or none, or DEFINE. Length (Short/Long) is worked out from the runtime, not asked. Everything in v6 stands. -->
<!-- v6 (2026-11-19, owner: the scroll stoppers are their own list — "Yes, add those 4"): a HOOK FORMAT line from the locked hook formats ({video_names}), or none, or DEFINE. Dramatic continuation is a hook format now, not a script format. Everything in v5 stands. -->
<!-- v5 (2026-11-19, owner: "categorize the swipe / winner in this framework and when we create new briefs it needs to fall in this framework, and if it does not seem to be in this framework, then we need to clearly define it"): three name lines, SCRIPT FORMAT, PRODUCTION FORMAT and STYLE, each ONE id from the locked video names ({video_names}, components/video-production/formats/names.json) or DEFINE: <its own name> — <its own words>. A DEFINE goes to the owner as one card; writing waits for his call (run.py, video_names.settle). STYLE now picks from the locked styles. FORMAT stays as it was (the element library id, read by the format bank and the playbooks). Everything else in v4 stands. -->
Classify this video for a swipe-file triage. Answer in exactly this format, nothing else:

LANE: one of ALREADY AN AD | ORGANIC | STATIC | SEQUENTIAL — is this a paid ad (product pitch, offer, CTA to buy) or organic content?
CATEGORY: what product/service category and who the speaker appears to be (age range, gender).
RUNTIME: the video's length.
SOUND FORM: one of SPOKEN | SUNG | RAPPED | MUSIC ONLY | SILENT — how the words reach the ear. LISTEN before answering; this is not visible on screen and cannot be judged from the pictures. SUNG means a voice carries the words on a melody for most of the runtime. RAPPED means rhythmic delivery over a beat without sung pitch. MUSIC ONLY means a bed with no words. A spoken voice over music is SPOKEN, not SUNG. If the piece switches — a sung chorus between spoken verses — answer with the dominant form and add "· mixed: <what the other part is>".
FORMAT: exactly ONE `id` from the format list, then " — " and why. The format is WHO carries the message and the SHAPE of the script (a presenter talking, an expert answering, a song, a meme, a little drama).
SCRIPT FORMAT: what the ad SAYS — the shape of its argument. Exactly ONE `id` from the SCRIPT FORMAT list in THE NAMES below, then " — " and why. If none of them is what this ad says, write `DEFINE: <a short name for it> — <what it is, in plain words>`. Never stretch a name to fit.
PRODUCTION FORMAT: how the ad is MADE — who or what is on screen and what carries the sound. Exactly ONE `id` from the PRODUCTION FORMAT list in THE NAMES below, then " — " and why (read it off the sound form and who talks: sung or rapped is a song ad; music only is a short movie; one voice over shots with nobody talking on screen is a narrator montage; two or more people talking is a multi-speaker scene; one person to camera is a single presenter; a phone screen of messages is a text thread). If none fits, write `DEFINE: <a short name> — <what it is>`.
HOOK FORMAT: the scroll stopper — only when the first seconds are made differently from the body (a faked stunt, a fake billboard, watch-bait drama, a weird stunt) and end where the pitch starts. Exactly ONE `id` from the HOOK FORMAT list in THE NAMES below, then " — " and why; `none` when the opening is simply the body starting (most ads); `DEFINE: <a short name> — <what it is>` when it is a scroll stopper unlike any on the list.
HEADLINE FORMAT: the WORDS in the first seconds, spoken or on screen — not what you see (that is the hook format). Exactly ONE `id` from the HEADLINE FORMAT list in THE NAMES below, then " — " and the words themselves; `none` when there are no words up top; `DEFINE: <a short name> — <the words>` when the shape is unlike any on the list.
STYLE: what every picture LOOKS like, read off the frames, not the topic. Exactly ONE `id` from the STYLE list in THE NAMES below, then " — " and what you see that makes it that style (eyes, proportions, skin, surfaces, light, capture). The test: swap the style and the script, cast and beats would stay the same. Real people filmed on a phone is phone-ugc; never call a stylised or animated piece real footage. If none of the styles is what this looks like (claymation, a doll world, a horror look…), write `DEFINE: <a short name> — <what you see>`.
STRUCTURE: exactly ONE `id` from the structure list, then " — " the spans that make it that build (which beat happens when).
MADE: exactly ONE of the how-made `id`s, then " — " why: how OUR version of this video would get made.
AI ASSESSMENT: is any part of this video AI-generated (synthetic voice, generated avatar/likeness, AI b-roll, generated images)? Name the specific tells you observe — lip-sync drift, unnatural blinks, texture shimmer, impossible physics, TTS cadence, watermarks of gen tools — or state "no AI tells observed". Give a confidence: LIKELY AI | POSSIBLY AI | LIKELY HUMAN.
ONE LINE: what happens in the video.

HOW TO TELL STYLE FROM FORMAT — the swap test. Imagine swapping the layer for another row. If the script, the cast and the beats would all stay the same, it is STYLE. If the script changes, or who carries it changes, it is FORMAT.

WHAT IS NEVER A FORMAT. How the opening is staged (a stitch, a duet, a reaction box, a green screen, a borrowed clip) is the STRUCTURE, not the format. Ask only: who carries the message, and what shape is the script? Name a new format only for a new answer to that question.

HOW TO PICK — match the owner's calls. The owner sorted real swipes into these rows by hand; they are listed under WORKED EXAMPLES. Before you pick, find the worked example closest to this video and use its row unless this video clearly differs on the thing that row is about. A near match on the row's own test (who carries it, what it looks like, how it is built) is the row. Only when NO row fits on that test write `new:<short-kebab-name>` and say in one line what makes it unlike every row — a new name stops the run until the owner decides, so never use it for a variant of a row that exists. Use only the ids printed below; never a row that is not on the list.

THE FORMAT LIST (pick an `id`):
{layer_formats}


THE STRUCTURE LIST (pick an `id`):
{layer_structures}

HOW IT'S MADE (pick an `id`):
{how_made}

WORKED EXAMPLES — swipes the owner sorted himself, by row (each line is that swipe's own triage: category · what happens):
{teaching_examples}

THE NAMES (locked; use these ids and no others, or DEFINE):
{video_names}
