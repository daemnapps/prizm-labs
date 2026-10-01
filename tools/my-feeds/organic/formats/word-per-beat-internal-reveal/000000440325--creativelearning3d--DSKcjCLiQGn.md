# Word-per-beat internal reveal — rebuild sheet

A 35.71s all-3D explainer of how an exfoliating body wash works, by creativelearning3d — 440,325 views, 5,555 likes. No face, no room, no hands: every frame is a render.

**Why it works**
The caption feeds you one word at a time and is still mid-sentence at every single beat, so there is never a clean place to leave. And instead of claiming the acid works, the camera cuts the skin open and shows you the acid running down inside a pore — a mechanism you can watch reads as fact, not marketing.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 2.86s | Rendered lower leg covered in raised red bumps, flat blue backdrop | `on` |
| 8.57s | Closer on the same limb; an orange bottle tips in from the top and pale gel spills onto the bumps | `because` |
| 14.28s | Inside the skin — a cross-section with one pore cut open; a dark applicator tip drops translucent blue gel that fills the shaft | `salicylic acid` (top) · `goes` (low) |
| 20.0s | Macro of the surface as tan interlocking plates, the top layer cracking and lifting off the intact layer beneath | `lactic acid` (top) · `surface.` (low) |
| 25.71s | Back out to the rendered limb on the blue backdrop, bumps still there | `skin.` |
| 31.42s | Frame splits: darker mottled arm on top, lighter smooth arm below | `Before` · `After` · `smoother,` |

The six words in order read `on / because / goes / surface. / skin. / smoother,` — fragments of a continuous voiceover. **What we can't tell from six stills:** what the words between the sampled beats are, what happens in the first 2.86 seconds, and whether there is a spoken track at all. Don't guess at the full script — write your own line and cut it to one word per beat.

**What carries the value**
The cut-open pore. Everything before it is setup and everything after it is result; the persuasion happens in the two beats where you see the named acid go down the shaft and the dead surface layer break apart. The unfinished one-word caption is the retention device that keeps people there for it.

**Shoot it**
You can't, honestly — not with a phone. This one is 100% CGI: a rendered limb and a rendered skin cross-section, both on a flat blue backdrop with even, shadowless light. There is no camera, no set and no talent anywhere in it. The closest phone version would be a locked macro on real skin plus a bought or licensed cross-section animation for the middle two beats — but that is a different format, not this one. Treat this as a generate-it or animate-it build.

The rules that do transfer if you rebuild it: flat single-colour backdrop the whole way through, so the only thing the eye can track is the skin; the same word placement, centre-low, every beat; ingredient names in a fixed top-centre slot and nowhere else; and the closing Before/After as a stacked two-panel split on that same backdrop.

**Or generate it**

The single most important beat is the pore cross-section at 14.28s.

```
vertical 9:16 photoreal 3D render, cross-section of human skin cut open to show
one pore shaft, upper layer rendered as tight pale-pink cell blocks over deeper
pink tissue, a dark applicator tip entering from the top of frame releasing
translucent blue {PRODUCT} gel that fills the pore shaft from the surface down,
flat blue backdrop above the cross-section, clean even studio-render light,
no camera perspective distortion, no on-screen text
```

*Motion:* camera starts on the surface of {SUBJECT}'s skin and travels down through it into the cross-section, following the gel into the pore shaft; nothing else in frame moves.

*Text overlay:* one word of the voiceover per beat, bold serif, centre-low, white with a dark outline, building a narration that is unfinished at every beat (`on` → `because` → `goes` → `surface.` → `skin.` → `smoother,`). On any beat showing a named ingredient, put `{INGREDIENT}` in the same top-centre position in the same face. On the closing split panel, `Before` over the top half and `After` over the bottom half.

**Reference:** https://www.instagram.com/p/DSKcjCLiQGn/
