# Labelled before-after selfie — rebuild sheet

A 16.2s front-camera car selfie cut in two labelled halves — "Before moving to Miami" / "Vs moving out of Miami" — where the only thing that changes is the person's own hair, makeup and clothes. By adri_me27, 2,909,429 views, 78,918 likes.

**Why it works** — Both halves are shot the same way, in the same kind of seat, in the same daylight, so the frame gives the viewer nothing to look at except the difference in the person, and the two captions tell them exactly what that difference is supposed to mean. The switch lands on one cut in the middle, which turns a plain selfie into a comparison the viewer finishes themselves.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 1.3s | Front-facing selfie from a car's passenger seat. Chest-up, slightly off-centre, plain black top with the seatbelt across it, hair down and loose with lighter ends, one hand up near the face. Flat daylight through the side window; back seats and a headrest behind her. | Before moving to Miami |
| 3.89s | Same seat, same framing and light. She holds a small dark compact-sized case open in both hands at chest height and looks down into it. The object is too small and dark in the frame to identify — the stills don't show what it is. | Before moving to Miami |
| 6.48s | **The cut.** Tighter front-facing selfie, again inside a car but framed higher so the sun visor and an open sunroof fill the top of the frame. Same subject, now with fuller, darker, longer hair, fuller makeup and a brown knit button cardigan, facing the lens straight on in bright daylight from above and behind. | Vs moving out of Miami |
| 9.07s | Same framing, eyes down. A pale object rises into the bottom of the frame in her hands, close enough to the lens to be out of focus. No label is readable — the stills don't show what the product is. | Vs moving out of Miami |
| 11.66s | Same framing. She applies something to her lower lip with a fingertip, ring visible on the hand. | Vs moving out of Miami |
| 14.26s | Same framing. Hand up at her hair and jaw, looking back at the lens, the finished look held for the last beat. | Vs moving out of Miami |

The text sits top-centre in a small black serif face, in the same position in every frame, and changes exactly once — on the cut at 6.48s.

**What the frames don't show:** whether she is talking, whether there is music or a voiceover, whether the two halves were shot in the same car, and what either product is. A contact sheet can't answer any of those. Nothing here has been guessed at to fill them in. The caption is the whole caption: "The Miami glow up #miamiglowup".

## What carries the value

The contrast in one person's own presentation across the seam — plain top and loose hair before, full hair, makeup and knitwear after. The two captions do all the framing; the viewer's eye does the comparing. Neither product is ever explained, held up to the lens, or named. Take the caption pair away and there's no video.

This one needs a face and a real look change, so it isn't a hands-only rebuild — but it needs no performance, no script and no crew.

## Shoot it

- **Camera:** front camera, arm's length, chest-up, subject roughly centred. Handheld — small natural drift is right, don't stabilise it. No zoom, no cuts inside a half.
- **Location:** a parked car, both halves. Shoot the "before" from the seat with the seatbelt visible and the back seats behind; shoot the "after" holding the phone a little higher so the visor and sunroof edge come into the top of the frame. That framing lift is what makes the second half read as a different chapter, not a different video.
- **Light:** daylight through the glass only. Bright and flat in the first half, brighter and from above/behind in the second.
- **Wardrobe rule:** the halves have to be legibly a step apart on the same axis. Before — plain, single colour, nothing styled, hair as it falls. After — texture and a warmer colour (the source uses a brown knit cardigan), fuller hair, fuller makeup. Same person, same seat, so the clothes and hair are the only variables.
- **Structure:** two beats in the first half, four in the second. Give the second half the extra time — that's where the payoff sits.
- **Text:** top-centre, small serif, black. One line for the whole of half one, a second line for the whole of half two, switching on the cut. Don't animate it, don't add a third line.

## Or generate it

The beat worth generating is the cut at 6.48s — the "after" reveal.

```
vertical 9:16 front-facing phone selfie taken from a car's passenger seat,
{SUBJECT} chest-up and centred, looking straight into the lens, hair full and
worn down, wearing a soft knit button cardigan, holding {PRODUCT} low in the
frame near the bottom edge, car sun visor and an open sunroof filling the top
of the frame, bright natural daylight from above and behind through the glass,
seat and door edges visible at the sides, front-camera look with slight
softness and grain, no retouching, no on-screen text
```

**Motion:** handheld front camera held at arm's length, small natural drift and breathing movement, no zoom and no cuts inside the beat — the subject moves, the frame does not.

**Text overlay:** act one, pinned top-centre — `Before {change}` · act two, switching on the cut, same position and same font — `Vs {the change undone or reversed}`

Generate both halves from the same subject seed so it reads as one person; the whole format collapses if the viewer can't tell it's the same face.

**Reference:** https://www.instagram.com/p/DUTyvv8kmXH/
