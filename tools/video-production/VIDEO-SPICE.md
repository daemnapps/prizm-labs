# Video spice: what makes a video feel real

the owner, 20 Oct 2026, after the first Remedy Reel that landed:

> "What makes content feel real is emotional connection … through our senses: the eyes, the ears,
> the mouth, the nose … the whole body, body language, subtle movements, imperfections in the skin …
> like the little head bobble an Indian avatar does when agreeing or listening … Grandma Yai's
> fingers slightly yellow from the turmeric she has ground up over the decades … the little subtle
> things are what really make this stuff work."

This does for video what spice does for copy. The script, the pictures and the clips all carry it.
Every format uses it; Remedy Reel was the first.

## The seven layers

| # | Layer | What it means on screen | Where it lives |
|---|---|---|---|
| 1 | **Emotion travels** | Her face and eyes follow the words and the action: grim at the problem, focused on her hands while she works, a slow smile at the result, warm into the lens at the end. Never one expression held throughout. | per shot: `emotion`, `face`, `delivery` (the teardown's Emotion / Face / Delivery slots) |
| 2 | **Body language** | Small, real movements that belong to this person and her culture: a nod while listening, a hand to the chest, a head tilt. Each character has their own. | the character's `gestures` |
| 3 | **Lived-in marks** | Imperfections that tell a life story: skin texture, age spots, worn tools, and marks of what she does (turmeric-stained fingertips, a chipped clay bowl she has used for years). | the character's `life_marks`, in every picture prompt |
| 4 | **The senses** | Show a sense being used: she smells the lime, feels the paste between her fingers, listens. | a `sense` beat in the script where it fits |
| 5 | **Rhythm** | Fewer, longer shots (the swipe's own count). Cuts land between shots, never mid-breath. No mechanical punch-ins. | the writer's shot count; the editor's `breathing` pace |
| 6 | **Continuity** | One object, one look for the whole piece. Every step that is said is shown. Nothing enters the frame from nowhere: what she uses is in her hand or on the counter in the first frame. | the carry-over pictures; the writer's "show every step" rule; the clip check |
| 7 | **Camera and cutting** (TV and film cutting, adapted to a phone) | The camera moves the way a phone does: handheld push-ins, pull-backs, pans, tilts, a slow arc, a follow. The angle changes inside a scene (front, three-quarter, down at the counter, close on the hands). Shots hand off cleanly, so the piece reads as one continuous take that keeps the eye moving: an invisible join (the clip ends on the next shot's first frame), a cut on the person's action, a match cut on an object, or a phone whip between beats. the owner, 2026-10-20: "angle changes and camera movement changes mid scene and into clean transitions is what keeps the eye engaged. That's how TV and movies are cut … just adapted to mobile." | written into the **production brief** as part of spice (per shot `angle`, `camera`, `hands_off`, `ends_on`), used where it serves the scene and adds creativity, never forced on every shot |

Plus **phone-native finish**: captions, motion and transitions match the app the piece pretends to be
made in (Instagram, TikTok), down to the font and how each word comes in. Never "edited off the phone."
The looks live in `tools/video-edit/looks/bank.json` (e.g. `edits-glow`).

## The realism index

Every small human behaviour these layers call for is an entry in `spice/realism-index.json` (people read
`spice/REALISM-INDEX.md`), by family (the hand holding the phone, body, face, voice, skin, senses, place,
finish), by format (selfie-talk, counter-demo, walk-and-talk, street-interview …), by level, by culture where it
belongs to one (a South Asian head bobble, a Thai polite nod), and by **stage**: **writing** (the brief decides
where it happens), **production** (the picture or clip carries its words) or **editing** (the editor adds it).
the owner, 2026-10-20: *"some things will be editing and some things will be production … some things might be even
at the writing stage."* A run never coins an entry; it adds one here.

Editing entries the editor does not draw yet: `phone-grain`, `crooked-hold`, `digital-micro-shake`,
`reframe-nudge`, `exposure-shift`, `imperfect-zoom`. `app-native-captions` is drawn (`edits-glow`).

## Levels (like copy spice)

| Level | What it adds |
|---|---|
| 1 · clean | Layers 1, 5 and 6: emotion travels, natural rhythm, continuity |
| 2 · lived-in | + layer 3: the character's life marks in every picture |
| 3 · fully lived | + layers 2, 4 and 7: the character's own gestures, the senses, and the camera and cutting, shot by shot |

Remedy Reel runs at level 3.

## Next

Imagery gets the same treatment, all the way to "one of one, indistinguishable from reality, and
it still lands": full frame control.
