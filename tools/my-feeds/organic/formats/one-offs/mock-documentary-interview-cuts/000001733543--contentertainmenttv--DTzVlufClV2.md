# Mock-documentary interview cuts — rebuild sheet

A 2m33s fake documentary about a startup harvesting solar power off bald heads, shot and cut exactly like a real industry film — 1,733,543 views, 49,533 likes, by contentertainmenttv.

**Why it works** — The joke is never told; the format tells it, because every piece of documentary furniture is used at full strength on a premise that is nonsense: a leader-line spec callout on a scalp, a doorstep vox-pop, an apparatus strapped to a real head, and a suited executive at a desk saying "first offshore bald farm". Nobody in frame is playing it funny, so the viewer has to keep watching to work out how far the commitment goes — and the running subtitles mean every beat lands mid-sentence, with no clean place to leave.

## The beats

Six stills sampled evenly across the runtime, so the moments between them are not visible — the order below is what the sampled frames show, not a full shot list.

| Time | What happens | On-screen text |
|---|---|---|
| 12.27s | Extreme macro on a bald scalp, shallow focus, head filling the left of frame — shot as a product-spec close-up, not a portrait. A thin leader line runs from the scalp to a two-word technical label; a bold three-line claim card sits lower-left with the middle line in a pink highlight box. | "Solar Bounce Receptors" · "ONE UNIT CAN **CHARGE A HOUSE** IN 8 HOURS" |
| 36.81s | Handheld exterior, daylight. A woman in a fur-collared coat and red top smiles off-lens in a residential doorway; a man stands in the dark doorway behind her. Reads as a doorstep vox-pop — she is answering someone off camera. | "Oh, amazing." |
| 61.36s | A bald man in a plain grey sweatshirt sits square-on and motionless with a large transparent funnel-shaped apparatus mounted over his head. Red brick behind, an interior wall and doorway edge to the right. Camera near-locked at seated eye level. The mechanism, demonstrated on a body, deadpan. | "become less efficient over time." |
| 85.9s | Handheld and motion-blurred — an older bald man in grey moving through frame in front of brick and a sash window. Vérité coverage of the operation; the blur is camera movement, not a cut. | "Um, so we'll" |
| 110.44s | Mostly out-of-focus grey field with a partial face in profile at the right edge. **The frames do not show whether this is a whip-pan, a body crossing the lens, or a rack focus** — only that the camera is moving and someone is close to it. The line is a question, so an interviewer is likely off-lens. | "know if it's a fake?" |
| 134.98s | Interior sit-down interview: a man in a dark suit jacket over an open white shirt at a wooden table, window blinds behind him, looking down and aside as he answers. Static, chest-up — the standard executive-interview plate. | "first offshore bald farm," |

A channel watermark sits top-right in every frame. It is branding, not part of the format.

## What carries the value

The straight face of the documentary apparatus itself. Invented spec graphics, doorstep vox-pops, a mechanism strapped to a real body, and a suited executive at a desk, all treating an impossible premise as a functioning industry — and nobody in frame ever acknowledging the joke. There is no product demo and no punchline card; the commitment is the payload.

**Not replicable without talent.** This needs at least four people performing deadpan across four locations, plus a built prop. It is a shoot, not a phone grab.

## Shoot it

- **Camera** — two registers, alternating. Interviews: phone on a tripod, chest-up, seated eye level, subject looking slightly off-lens at an interviewer, absolutely static. B-roll: the same phone handheld and loose, allowed to blur and miss focus. The gap between the two is what sells it as documentary; do not stabilise the b-roll.
- **Light** — whatever is there. Flat overcast daylight outside, plain window light in. No fill, no reflectors, no grade. It has to look like a crew that turned up.
- **Wardrobe** — ordinary and specific to role. The people being interviewed about their lives wear their own clothes (sweatshirt, coat); the executive wears a dark jacket over an open shirt. **No costumes.** The moment anyone looks dressed up, it becomes a sketch and stops working.
- **Performance** — total commitment, zero winking. Interviewees hesitate, say "um", trail off. The one non-negotiable rule: nobody smiles at the camera.
- **Locations** — at least three that read as different worlds: a residential street or doorway, a working interior (brick, a doorway, real clutter), and an office or boardroom with blinds. They do not need to be far apart, only to look unrelated.
- **Graphics** — the spec layer is the cheapest and highest-leverage part. One leader-line callout naming an invented mechanism, and one bold claim card with the impossible number highlighted. Both belong on the opening beat, over the macro shot.
- **Subtitles** — burn in every spoken clause for the whole runtime, one clause at a time, centre-low. This is what keeps a 2m33s piece watchable.

## Or generate it

The single most important beat is 61.36s — the mechanism on a body. Image prompt:

```
vertical 9:16 documentary still, {SUBJECT} in an ordinary plain grey sweatshirt
seated square-on and motionless with a completely neutral expression,
{PRODUCT} mounted over and around them as a large transparent apparatus,
red brick wall directly behind, a pale interior wall and doorway edge entering
at the right of frame, flat overcast daylight from the left, handheld
documentary camera at seated eye level, slightly soft, unstyled, no retouching,
no on-screen text
```

**Motion** — camera near-locked at seated eye level with only faint handheld breathing drift, no push and no reframe; the subject holds still and never acknowledges the lens.

**Text overlay pattern** — two layers.

- All runtime: burned-in speech subtitles, one clause per beat, centre-low, white sans, cut mid-sentence — `"{clause}"`.
- Opening beat only: a thin leader line from `{PRODUCT}` to a stacked two-word callout `"{Invented technical name}"`, plus a bold three-line spec claim in the lower left — `"ONE UNIT CAN / {IMPOSSIBLE BENEFIT} / IN {NUMBER} HOURS"` with the middle line sitting in a highlighted colour box.

**Reference:** https://www.instagram.com/p/DTzVlufClV2/
