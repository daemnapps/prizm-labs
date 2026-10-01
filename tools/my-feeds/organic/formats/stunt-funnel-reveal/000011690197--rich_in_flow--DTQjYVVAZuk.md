# Stunt funnel reveal — rebuild sheet

A guy reports the results of DMing a million girls on Instagram, told as a funnel chart that narrows from 1,000,000 to 0 — 46s, 11,690,197 views, 609,128 likes, by rich_in_flow.

**Why it works**

The absurd number is stated in the first second and then *proved* — the real inbox scrolls behind him, the real sent message is shown with the keyboard still up — so by the time the chart starts counting down, the viewer has already accepted the premise as true. The chart is the retention device: it opens at 1,000,000 and every beat subtracts, so you stay to find out what the last number is, and the last number is zero.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 3.7s | Instagram DM inbox screen recording fills the frame, names stacked down it all reading "Sent just now" / "Sent 2m ago". Presenter cut out and composited large in the lower-left, gesturing. | `POV: you DMed 1 million girls on Instagram💀🥀` · caption `find a girlfriend` |
| 11.1s | Plain white frame, the funnel chart starts — one thick grey-and-pink bar at lower left. Presenter shrinks to a small cut-out up top. | caption `that I put up` · chart `1,000,000 DMS` |
| 18.49s | Screenshot of the actual DM thread — sent bubble, "Seen just now", keyboard raised. Presenter large in the centre, both fingers pointing down at the message. | caption `how did this shot` · message `matcha🍵 + missionary 🍑 ??` · `7:25 PM` |
| 25.89s | The chart fully built and branching on white. Presenter mid-right, hand over his eyes, laughing. | `167 Responses` · `51,131 Rejected` · `948,702 Airballed` · `3 Dat…` — no speech caption visible in this still |
| 33.29s | Back to the opening bar, same framing as 11.1s. Presenter small up top, mid-word. | caption `Finally` · chart `1,000,000 DMS` |
| 40.68s | Near-white frame, the chart down to one thin line climbing to the right and ending on a single number. Presenter small upper-left, deflated. | caption `I know 2026 just started` · chart `0 Girlfriend` |

Two honest gaps: the `3 Dat…` label is cut off by the edge of the contact sheet — almost certainly "3 Dates", but the frames don't show the whole word. And the 25.89s beat is the one frame with no speech caption in it; whether he's silent there or the caption simply fell between stills, the sheet can't say.

**What carries the value**

The numbers, and the receipts underneath them. The inbox and the sent message make 1,000,000 believable; the chart then spends the entire runtime taking it apart — 1,000,000 → 167 → 3 → 0. The presenter is a reaction track, not the argument. Swap the topic and the structure survives intact as long as the dataset is real and the last number is a punchline.

**Shoot it**

- **Camera.** Phone front camera, vertical, one continuous piece-to-camera, chest-up. Nothing here needs a camera move — every "move" in the finished video is the cut-out being resized and repositioned on screen between beats. Film against a wall you can key out; the frames show the background removed in all six beats, so what room he actually shot in isn't evidenced and doesn't matter.
- **Light.** Flat, bright, straight on. No shadow on the face, no visible light source. A window in front of you or a ring light does it.
- **Wardrobe.** One outfit for the whole take — charcoal zip-up jacket over a plain cream tee in the reference. Since it's one continuous take cut into six placements, any wardrobe change breaks the illusion.
- **The other half is a screen, not a set.** Screen-record your real receipts (the inbox, the thread, the dashboard, whatever your version's proof is) on your phone. Build the funnel chart in any chart tool on a plain white background and animate it stage by stage. Then key the presenter out and composite him over both.
- **Casting.** This one needs a person. Every beat has a face reacting in it, and the timing of the reaction is what sells the chart. Budget for someone who can hold a piece-to-camera, or don't build this format.

**Or generate it**

The presenter is generatable; the chart is not — no image model will render legible funnel numbers. Generate the cut-out, build the chart in a graphics tool, composite.

```
vertical 9:16, a background-removed cut-out of {SUBJECT} composited over a plain
white data-chart frame, chest-up, positioned mid-right at about a third of the
frame height, one hand raised toward the face in a reaction; wardrobe is a
charcoal zip-up jacket over a plain cream t-shirt, worn identically in every
beat; lit flat and bright from the front, no shadows, no visible room — the
original room is keyed out and nothing behind the subject is evidenced by the
frames; phone front-camera look, slight grain, no retouching, no on-screen text;
the chart area and the {PRODUCT} funnel labels are left empty to be composited
in a graphics tool, not generated
```

**Motion.** The subject holds one continuous piece-to-camera with small natural upper-body movement and no camera move of its own; the stills can't confirm whether the source take pans or pushes, so treat it as a static frontal take and animate only by cutting the cut-out to a new size and screen position on each beat.

**Text overlay pattern.** Opening pinned hook: `POV: you {absurd-scale stunt} 💀🥀`. Under it for the whole runtime, running speech captions — bold white, heavy black outline, centre-low, three to five words at a time, cut on the beat. Chart labels carry the numbers: `{big number} {UNIT}` → `{n} {stage}` → `{n} {stage}` → `0 {goal}`.

**Reference:** https://www.instagram.com/p/DTQjYVVAZuk/
