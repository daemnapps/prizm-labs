# Personified mechanism explainer — rebuild sheet

A 37.2s skin video by **lossweght** — a cartoon mascot points at inflamed skin, a 3D cross-section shows what is happening under the surface, the mascot cheers at clear skin. **816,500 views · 11,851 likes**, caption in full: "Did you know ?"

## Why it works

The middle of the video is a cutaway you cannot argue with: you watch the trapped hair, the blade, the cream and the liquid act on the follicle *below* the skin, so the claim is something seen rather than said. The mascot bookends turn that render into a one-second before/after — it points at the problem in the first frame and celebrates in the last, so a viewer who understood none of the mechanism still leaves with the verdict.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 2.98s | Locked extreme macro on real skin — raised red inflamed bumps, pink garment edge top right, a bare fingertip entering bottom left. A small glossy blue cartoon blob with big white eyes stands on the skin and points down at the bumps. | INFLAMED |
| 8.93s | Hard cut to a locked 3D cross-section of skin: a dark coiled ingrown hair trapped under the surface, red inflamed tissue around it, white foam sitting on top of the skin with smoke rising off it. | SKIN |
| 14.88s | Same cross-section, identical framing. Straight hairs now stand above the surface, a metal blade tip comes down from the top of frame, a clear glossy film covers the skin. The coiled hair is still trapped below. | SHAVING |
| 20.83s | Same cross-section. The hair is now straight and clear of the follicle; a white dollop of cream sits at the follicle mouth. Pale green granules along the bottom of the cutaway. | CREAM |
| 26.78s | Same cross-section. Amber liquid drips in from the top of frame and pools over the follicle mouth; the surrounding tissue reads less red than earlier. | 4 |
| 32.74s | Cut back to real macro skin in the opening look — surface now smooth and clear, same pink garment edge. The mascot stands in the same part of frame with both arms raised, celebrating. | BYE |

**On the text, honestly:** the six words do not form a sentence. "4" is plainly a fragment caught mid-word or mid-number. That pattern — a different single word in the same position at each sample — is what a rolling speech-caption track looks like when it is sampled every six seconds. So treat the text as **spoken subtitles, one word at a time**, not as an authored word-per-beat build. The actual spoken track is not readable from stills.

**What the frames do not show:** no product, package or label appears in any of the six frames. The amber liquid in the fifth beat may or may not be the product — nothing on screen names it. There is no face and no voice-over source visible. Whether the mascot appears during the four cross-section beats is unknown; it is absent from every sampled cross-section frame. The four render beats are the same locked framing, so whether there are cuts between them or one continuous animation cannot be told from stills.

## What carries the value

The cross-section. Everything persuasive happens below the skin line, in a frame that never moves, so the eye has nothing to track but the mechanism. The mascot carries none of the argument — it carries the *verdict*, and it is what makes the first frame stoppable.

## Shoot it

Only two of the six beats are shootable. Be clear about that before scheduling anything.

- **Beats 1 and 6 (phone):** macro lens or macro mode, camera on a stand, absolutely locked — the closing frame must match the opening frame in distance, angle and light, because the whole before/after depends on the two matching. Plain even indoor light, no ring-light hotspot, no beauty filter, no retouching. Wardrobe rule: one soft plain-coloured garment edge in the corner of frame for scale (here a pink strap), nothing patterned, nothing branded. Skin is not styled — the bumps are the asset.
- **Beats 2–5 (not shootable):** these are a 3D render of a skin cross-section. They need an animator or a generator, not a camera. Same framing for all four, no camera move at any point.
- **The mascot:** composited animation over the real footage in beats 1 and 6 only. It must be the same character in both, same size, same part of frame — pointing down at the problem in the first, arms up in the last.
- **Text:** burn one word at a time, centre-low, white all-caps with a hard black outline, in the exact same position on every beat.

## Or generate it

The hook beat — beat 1, the mascot on the real inflamed skin. This is the frame that stops the scroll and it is the one worth generating first.

```
vertical 9:16 extreme macro photograph of {SUBJECT}'s skin, raised red inflamed
bumps clustered across the surface, a soft pink garment edge crossing the top
right corner, a bare fingertip entering from the bottom left and resting on the
skin beside the bumps, and a small glossy blue cartoon blob character with two
large white eyes and short stubby arms and legs standing on the skin at mid-right
pointing down at the bumps, shallow depth of field, plain even indoor light,
phone-macro look, slight grain, no retouching, no on-screen text, no product in
frame at this beat ({PRODUCT} does not appear in any sampled frame and enters, if
at all, inside the cross-section beats)
```

**Motion:** camera absolutely locked — no push, no pan, no reframe; only the fingertip and the cartoon character move, the character stepping in and raising an arm to point at the bumps.

**Text overlay pattern:** one word at a time, centre-low, white all-caps with a hard black outline, identical position every beat, changing on every beat as a rolling speech caption —
`{PROBLEM}` → `{SURFACE}` → `{OLD METHOD}` → `{STEP}` → `{FRAGMENT}` → `{SIGN-OFF}`

**Reference:** https://www.instagram.com/p/DbHENoIxD4f/
