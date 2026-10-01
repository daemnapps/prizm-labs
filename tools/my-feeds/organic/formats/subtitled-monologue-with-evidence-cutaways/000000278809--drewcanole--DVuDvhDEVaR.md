# Subtitled monologue with evidence cutaways — rebuild sheet

A 59.9s studio monologue that turns a single ingredient into a numbered ladder of body systems, each rung paid off by an anatomical render — 278,809 views, 15,834 likes (~5.7% like rate) from drewcanole.

**Why it works** — The presenter never demonstrates anything, so the argument has to be carried by pictures: every claim he makes cuts to a labelled organ render, which reads as observed rather than asserted. The rising number in the corner turns the middle of the video into a countdown the viewer has to stay for, and the speech subtitles are always cut off mid-sentence so there is no clean place to leave.

## The beats

| Time | What happens | On-screen text |
| --- | --- | --- |
| 4.79s | Full-frame close on two hands pressing a cling-film-wrapped pad of yellow-orange pulp onto a bare abdomen — daylight, a different room and camera from the studio. The presenter sits as a small cut-out at the lower-left edge so he never fully leaves the frame. | "You're Missing Out on Ginger Compresses… Here's What They Do for Cramps, Bloating & Fertility!" |
| 14.37s | Presenter full-frame, chest-up, seated against pure black with no set dressing, podcast mic on a boom entering from the lower left, warm front-left key. Camera locked, talking to the lens. | "This is what happens," |
| 23.94s | No presenter at all — a full-frame red graphic card with two rounded panels: a 3D render of the reproductive organs above, digestive organs over a torso below, each named in rotated vertical type. | "Reproductive System" / "Digestive System" |
| 33.52s | Back in the identical locked studio frame. A huge red numeral and a white benefit line across the upper half; a rounded inset panel in the lower half holds a glowing orange render of the digestive organs. | "2 Improves Digestion" |
| 43.1s | Same frame, same light. The numeral advances and the inset swaps to a red-and-blue muscle-and-joint render. Nothing else changes. | "3 Heals Inflammation" |
| 52.68s | Presenter reframed — shifted right of centre, looking down and away from the lens, mic in shot. No number, no inset; the speech subtitle is back on its own. | "haven't even begun to" |

**What the frames do not show, stated plainly:** only six stills across 59.86s were sampled, so anything between beats is unknown. Rung "1" of the numbered list is not in any sampled frame — the counter reads 2 at 33.52s and 3 at 43.1s, so item 1 landed somewhere between 23.94s and 33.52s. There is no audio, so the spoken script beyond the two subtitle fragments is unknown. Nothing in the frames says whether the opening compress clip was shot by the presenter or borrowed. No CTA, end card or product shot appears in any sampled frame.

## What carries the value

The numbered ladder of body systems, each rung paid off by a full-colour anatomical render. Breadth is proved by pictures of organs, not by the sentence being spoken — and the rising count is what makes leaving feel like leaving early. The presenter's job is only to be a continuous, credible voice between the graphics.

## Shoot it

- **Camera** — one locked frame, chest-up, subject slightly left of centre, and it never moves for the whole runtime. A phone on a tripod at seated eye height does this. Do not reframe between beats; the only late reframe in the source is at 52.68s and it reads as the piece winding down.
- **Background** — pure black. A dark wall far enough behind the subject that the key light does not reach it, or black fabric. No shelves, no plants, no set dressing — the black is what lets the graphics pop when they cut in.
- **Light** — one warm key from the front left, nothing on the background. A single softbox or a window with everything else killed.
- **Prop** — a large podcast microphone on a boom, deliberately allowed to intrude into the lower-left corner of frame. It is doing credential work; do not tidy it out.
- **Wardrobe** — one saturated block-colour top (the source is a mustard tie-dye knit) and tinted round glasses. One strong colour against black, no patterns competing with the overlays.
- **Graphics** — you need renders or licensed diagrams of each body system before you shoot, because they are the proof. Two treatments, both used: full-frame graphic cards with the systems labelled, and rounded-corner insets sitting in the lower third under the number.
- **Talent** — required. A person on camera carries four of the six beats; this is not a hands-only build.

## Or generate it

The single most important beat is the numbered rung (33.52s / 43.1s) — it is the unit that repeats.

```
vertical 9:16 studio photograph, {SUBJECT} chest-up and seated slightly left of
centre against a pure black seamless background with no set dressing, wearing
tinted round glasses and one saturated block-colour knit sweater, a
large-diaphragm podcast microphone on a boom arm intruding from the lower-left
edge of frame, warm key light from the front left with the background falling
to true black, sharp modern camera look, mouth open mid-sentence toward the
lens, a rounded-corner inset panel occupying the lower third holding a glowing
photoreal 3D render of the body system {PRODUCT} acts on, no on-screen text
```

**Motion** — camera absolutely locked at the same distance and angle for every studio beat; only the presenter's face and hands move while the number card and the inset render swap between beats. Generate every beat from the same seed frame so the studio matches exactly.

**Text overlay pattern**

- Numbered rungs: a huge numeral in a hot accent colour beside a two-word benefit in white bold, identical position each rung — `{n} {Benefit}` ("2 Improves Digestion" → "3 Heals Inflammation").
- Between rungs: running speech subtitles in one lower-centre box, a single mid-sentence fragment per beat with one word in a contrast colour — `{fragment with one {word} highlighted}`.
- Opening beat only: a two-line hook banner — `You're Missing Out on {THING}… Here's What {it does} for {problem 1}, {problem 2} & {problem 3}!`

**Reference:** https://www.instagram.com/p/DVuDvhDEVaR/
