# Narrated rendered scene chain — rebuild sheet

A 32-second fully-rendered story: a woman reads something on her phone, then six unrelated cinematic locations run past under a narration that is only ever visible as one- or two-word caption cards. By lucamaxiim — 569,011 views, 39,743 likes, post caption "you got 1 notification".

**Why it works** — The caption never finishes a sentence: every card is a fragment ("because" → "profile picture" → "even" → "a volume"), so there is no clean second to leave, and the viewer keeps reading to close a loop that only closes at the end. Because every location is rendered rather than filmed, each beat can be somewhere nobody could afford to shoot — ruins, a screen-stacked bazaar, a city aerial — and the one recurring character is the only thing holding them together.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 2.58s | Warm wood-panelled study. A woman leans over a desk, both hands on a phone, looking at the screen. Bookshelves behind, warm light from the left. | because |
| 7.75s | No person. A dirt bike with a helmet on the seat, parked on sand in front of a weathered stone arch and overgrown ruins, low golden sun behind. | profile picture |
| 12.92s | A man in a red turban and dark patterned jacket crouches over sand, hands on a half-buried carved slab, jungle ruins behind. Hard daylight. | even |
| 18.08s | The same man walks toward camera down a narrow corridor of stacked screens and electronics. Black embellished jacket, gold chains, warm bulbs and screen glow either side. | a volume |
| 23.25s | No person. High aerial over a dense coastal city — skyline, a curving elevated highway, port and sea. Hazy daylight. | in Mumbai |
| 28.42s | The same man rides a red dirt bike toward camera down a dusty street with auto-rickshaws and palm trees. Blue printed t-shirt, dust in the air. | something |

What the frames do not show, and I have not filled in: the audio, so whether there is a voice-over is inferred from the caption fragments being grammatical mid-sentence pieces, not confirmed. The full narration is not recoverable from six stills — the six words above are samples from a much denser caption track, not the whole sentence. The print on the blue t-shirt in the last frame is not legible at this resolution. There is no product anywhere in the video.

## What carries the value

The unbroken narration, cut so that every card lands mid-sentence — that is the retention device. The rendered locations are the spectacle it is carried on, and the recurring character in one unchanging outfit is the only continuity between six places that share nothing else. No product, no demonstration, no talking head, no pinned line.

## Shoot it

You cannot shoot this one straight — half the beats are places and a scale a phone will not get you. If you are shooting rather than generating, the rules that carry over are:

- **Camera:** one self-contained shot per beat, no relationship between them. Cut hard on every location change; never return to a frame you have already used. No handheld wobble — each beat is stable and composed, which is what separates this from a vlog.
- **Light:** whatever the location gives, but committed — golden low sun outdoors, warm practical bulbs indoors, hazy flat daylight from above. Different in every beat on purpose.
- **Wardrobe:** one distinctive outfit on your subject that does not change between locations. It is the only thread the viewer has, so it has to be unmissable and identical every time.
- **Text:** one or two words a beat, centre frame, white with a soft shadow. Never a headline, never pinned, never a complete sentence.

## Or generate it

The hero beat is the character walking the corridor of screens — the one where the recurring subject and an unshootable location land in the same frame.

```
vertical 9:16 photoreal cinematic still, {SUBJECT} walking toward the lens down a
narrow corridor between floor-to-ceiling stacks of screens and electronics in a
cluttered shop, {PRODUCT} carried in one hand, one distinctive unchanging outfit on
{SUBJECT} that will repeat in every scene, warm hanging bulbs overhead and cold
screen glow on both walls, shallow depth, film-still grade, no phone-camera look,
no on-screen text — keep {SUBJECT}'s face and wardrobe identical across every
generation (same seed)
```

**Motion:** slow steady dolly backing away as {SUBJECT} walks toward the lens down the corridor, no handheld shake and no cut inside the beat.

**Text overlay pattern:** `{one or two words of a continuous spoken sentence}` — centre frame, white sans-serif with a soft drop shadow, lowercase except proper nouns; a new fragment every beat, never pinned, never finishing the sentence.

The `{PRODUCT}` slot is a placeholder for your rebuild — the source video has nothing in the subject's hands.

**Reference:** https://www.instagram.com/p/DVa-fWMkS0H/
