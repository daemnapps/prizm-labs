# Day-count self-test — rebuild sheet

A 12.34s bathroom selfie series by `hairyorg`: the same man, the same angle, the same gesture of opening his hairline to camera, stamped Day 1 → Day 14 → Day 30 → Day 120 while he applies an oil to his own scalp — 12,655,519 views, 128,828 likes.

## Why it works

Nothing in the frame changes except the thing being sold on — same room, same arm's-length angle, same head-down gesture — so the day stamp does all the arguing and the viewer's eye is forced onto the one area that is actually different. The wardrobe changing at every stamp is the quiet proof that time really passed, and the face never comes up until Day 120, which turns the payoff into a reveal rather than a claim.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 0.99s | Selfie in a home bathroom — mirror wall, blinds, sink and dark cabinets. Grey t-shirt, head tilted down, hand pushing hair off the temple to show a thin, receded hairline. A small golden shape clips the left edge (a drop, or the dropper tip — too cropped to be sure). | `Day 1` + `"I wasn't ready to lose my hair..."` |
| 2.96s | Same room, same angle, black hoodie. Head down, glass dropper held against the front hairline mid-application, other hand parting the hair. | `Day 14` |
| 4.94s | Same room and angle, still the hoodie, framed tighter — crown and hand fill the frame, hand parts the front hairline. | none at this instant — this frame sits between two stamps |
| 6.91s | Same room and angle, white t-shirt. Dropper held high with a golden drop hanging off it, head still down. Hairline reads denser, the bare patch smaller. | `Day 30` |
| 8.88s | First face-forward shot. Black zip jacket, full hairline, faint smile, product held up beside the face — amber glass, green label, black dropper cap, label square to the lens and readable. | `Day 120` |
| 10.86s | Same hero held, smile a little wider, bottle still up beside the face. | `Day 120` |

Gaps, stated plainly: the contact sheet stops at 10.86s of a 12.34s runtime, so the last ~1.5s is unsampled and I don't know how it ends. Stills also can't tell you whether the camera moves *within* a beat, whether there is a voiceover or only music, or how many cuts sit between the six sampled moments. The caption carries a disclaimer verbatim — *"Disclaimer: individual results may vary"* — which is part of what shipped.

## What carries the value

The day counter climbing over an unchanged shot. Because the room, the angle and the gesture are identical every time, the hairline is the only variable left, and the outfit change at each stamp is what stops it reading as one afternoon's filming. No claim overlay, no voiceover argument, no before/after split screen — just the same frame, four dates apart.

## Shoot it

- **Camera:** phone front camera, held at arm's length, vertical. Same spot, same distance, same height every single time — mark the floor and note where the mirror edge and the window sit in frame, because matching framing across months is the whole format.
- **The gesture:** head tilted *down* toward the lens so the treated area faces camera, one hand opening it up, the other applying. Face stays out of it until the payoff.
- **Light:** daylight from the window only, no lamps, no grade. Shoot at roughly the same time of day so the light matches across the intervals.
- **Wardrobe:** a different plain top at every date, and no logos. That change is the evidence, so don't let it be accidental.
- **The payoff beat:** the only face-forward shot. Product up beside the face, label square to the lens and readable, held for the last ~3 seconds.
- **What this actually costs:** no acting, no lines, no charisma — but it needs a real person with a real result over a real four months. You cannot shoot this in a day, and faking the intervals is the one thing that breaks it. Start filming Day 1 before you know whether it works.
- **Text:** `Day {n}` underlined, top third, same position every beat, held for the whole beat. One extra quoted line under the first stamp only.

## Or generate it

The beat that has to be right is the repeated interval frame — it appears four times and everything depends on it matching itself.

```
vertical 9:16 selfie photograph at arm's length, {SUBJECT} in a home bathroom — large wall
mirror filling the background, a window with white blinds at the upper right, sink and dark
wood cabinets low in frame — head tilted down toward the lens so the top of the head faces
camera, one hand holding {PRODUCT} against the scalp mid-application, the other hand pushing
the hair open at the side of the head, plain unbranded top, bright soft daylight from the
window bouncing off the mirror, no lamps and no colour grade, phone front-camera look with
slight grain, no retouching, no on-screen text
```

**Motion:** handheld at arm's length and almost static — small breathing drift only, no zoom and no push; the head stays tilted down for the whole beat so the treated area never leaves frame.

**Text overlay:** `Day {n}` centred in the top third, white with a dark outline, underlined, held for the whole beat — one stamp per interval, ascending (`1` → `14` → `30` → `120`), the last interval repeated across the closing beats. On the first beat only, a smaller quoted line directly under it: `"{the fear, first person, past tense}..."`

Generate every interval from the same seed frame, or the room will drift and the format dies.

**Reference:** https://www.instagram.com/p/Dap3DXdgfa6/
