# Running caption over borrowed cutaways — rebuild sheet

A 44-second post by lucamaxiim: a chopped-up narration runs one fragment at a time over borrowed Chinese-internet clips, cut against the poster's own fixed desk shot — 547,856 views, 31,264 likes, caption "Is ts tuff in China?"

**Why it works** — No single frame ever completes the sentence, so the caption is a loop the viewer can only close by staying to the end. The borrowed clips do all the spectacle for free, and the plain desk plate he keeps cutting back to makes a pile of unrelated found footage read as one person's argument.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 3.53s | Borrowed clip, full frame: a hand holds a dark-skinned baby doll in a white frilled dress over grey concrete, shot close and top-down. A 小红书 watermark sits top-left and a handle card (蔡大伯–Charisse) top-right — this footage is lifted from another platform. | like black |
| 10.58s | Borrowed clip: a bald wide-eyed baby doll on white bedding with a small Chinese-labelled milk carton propped by its head, low side angle, flat daylight. | thinking |
| 17.63s | His own shot: young man in glasses and a plain olive t-shirt at a home desk, side-on, typing, the back of his monitor to camera, desk lamp and second screen behind, bare pale wall. He does not address the lens. | trying to |
| 24.68s | Borrowed clip: outdoors on bare dirt by a corrugated-metal shack, an older man in a navy graphic tee walks holding a small child upside down by one leg, two bystanders watching. Handheld, hard daylight. | I'm not even |
| 31.73s | His own shot again — identical desk, lamp, monitor and angle as 17.63s, but he is now in a black tee printed with a red dragon and the slogan, so this plate was shot on a separate occasion, not as one take. | Sparta |
| 38.78s | Closer on the same man, leaning down over pale bedding with his face lowered and eyes closed; a red paper-cut dragon graphic and the slogan are laid over as a card. What he is leaning over is not legible in the frame. | You met me at a very Chinese time in my life. |

Not shown by the frames, so not claimed here: whether there is a spoken voice track under the fragments (the caption style reads as chopped speech, but stills cannot prove it), whether the camera moves inside any beat, what the full sentence resolves to, and where the borrowed clips came from beyond the one visible 小红书 watermark and handle.

## What carries the value

The unfinished caption chain. Each beat hands over a fragment — "like black", "thinking", "trying to" — and cuts away to a clip stranger than the last, so the sentence and the escalation pull in the same direction. Nothing is demonstrated, nothing is argued; the borrowed footage is the entertainment and the caption is the reason to stay for it.

## Shoot it

You only shoot one thing: the desk plate. Everything else is found footage.

- **Camera.** Phone on a shelf or small tripod, vertical, chest-up, side-on to the desk so the back of the monitor faces the lens. Lock it and never move it — every return to this plate must match frame for frame. No handheld, no reframe, no second angle.
- **Light.** Whatever the room has: daylight from the window plus the desk lamp already in shot. No fill, no ring light. It should look like the room, not a set.
- **Wardrobe.** Plain t-shirt, no styling. Note the source video's own two plates were shot in different shirts and it did not hurt it — matching wardrobe is not required, matching framing is.
- **Performance.** None. He is typing and looking at the screen, not talking to camera. Do not perform, do not address the lens.
- **Cutaways.** Three or four found clips that are visibly not yours and visibly unrelated to each other — leave the source watermarks on, they read as proof it is real rather than made. Only use clips you have the right to use.
- **Cutting.** Fragment lands, cut. Roughly a beat every 7 seconds in the source. Alternate: borrowed, borrowed, you, borrowed, you, close on you.

## Or generate it

The one beat worth generating is the desk plate — the borrowed clips cannot be honestly faked.

```
vertical 9:16 photograph, {SUBJECT} seated at a plain home desk in a small
bedroom-office, side-on to the lens and looking at a monitor whose back faces
camera, both hands on a keyboard, plain unbranded t-shirt, a folded angle-poise
desk lamp and a second screen behind, bare pale wall, daylight mixed with lamp
light, chest-up locked framing, phone-camera look, slight grain, unstyled,
no on-screen text, {PRODUCT} sitting on the desk beside the keyboard
```

**Motion.** Camera locked at this exact desk framing every time the video returns to it — no push, no pan, no reframe; only the hands on the keyboard move. Generate every return from the same seed so the plate matches.

**Text overlay.** One short fragment of a running narration per beat, centred mid-frame in white with a soft drop shadow, sentence case, same position every time: `{fragment 1}` → `{fragment 2}` → `{fragment 3}` → `{fragment 4}` → `{fragment 5}`, none of them a complete sentence on its own. The final beat swaps the fragment for a fixed slogan card, `{slogan}`, over the closing shot.

**Reference:** https://www.instagram.com/p/DZVKdiRxIXe/
