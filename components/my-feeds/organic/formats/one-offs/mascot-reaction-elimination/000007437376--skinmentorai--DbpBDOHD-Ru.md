# Mascot reaction elimination — rebuild sheet

A 36-second CG cross-section where the problem is a cartoon villain sitting in a pore: three products are tried on it and fail, then the real active arrives and it panics. 7,437,376 views · 78,341 likes · @skinmentorai.

**Why it works**

The problem is given a face, so the viewer gets a character to root against instead of a claim to evaluate — and the character's expression is the proof, folded arms through three failures, then terror. The labels do the rest of the work with one punctuation trick: every wrong answer ends in a question mark and the right one doesn't, so the format tells you the verdict before anything on screen has to.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 2.89s | Locked cutaway of skin. A hand works white foamy lather across the surface above the pore. The character sits in the cavity, arms folded, smirking. The lather never reaches it. | Fasewash? / Clogged Pore |
| 8.67s | Hand enters from the left, fingertips rubbing the surface above the pore. Character hasn't moved. | Scrub? / Clogged Pore |
| 14.46s | Hand fully withdrawn, surface empty. Character has risen slightly and its smirk opens into a wide grin. The label still names the thing that just gave up. | Scrub? / Clogged Pore |
| 20.24s | A fingertip spreads a thick glossy cream blob across the surface, capping the pore mouth. Character is laughing, arms out. | Moisturizer? / Clogged Pore |
| 26.02s | A cotton pad held above the pore drips clear liquid; fluid pools in the bottom of the cavity. Character's eyes go wide, mouth open, arms straight out. The flip. | Salicylic Acid / Clogged Pore |
| 31.8s | Cotton pad pressed flat on the surface. Cavity full of fluid, character lifted off the floor, floating, screaming. | Salicylic Acid / Clogged Pore |

Read honestly from the frames: the first label is spelt **"Fasewash?"** in the source — a real misspelling, not a stylisation. "Scrub?" holds across two beats, and the second of those is the hand leaving, so a failure gets its own silent beat. The stills stop at 31.8s of a 36.14s video, so roughly four seconds are unread — **the pore is never shown cleared in the frames we have**; the last thing we can prove is the character being carried up, not a clean result. There is no audio evidence here, so whether a voiceover runs under this is unknown. No product and no brand appears anywhere — only ingredient names. The caption ends mid-word on "Free skin analysi", so the call to action is only partly visible.

**What carries the value**

The character's face. The clog is a smug little villain that folds its arms through three products, and the argument is won the second its expression flips to terror. You are persuaded by watching it lose — which is exactly why the video never has to show the pore actually clearing.

**Shoot it**

You don't shoot this one with a camera — it's a 3D render, and that's the point: no talent, no location, no shoot day. What a person does have to hold constant:

- **Camera:** absolutely locked, front-on, square to the cross-section. It never moves, never pushes, never cuts to another angle. Same frame from first beat to last.
- **Layout:** plain off-white ground across the top third, the cutaway filling the lower two-thirds, one cavity dead centre. Hands only ever enter from the top of frame and only ever touch the surface — nothing above the surface may cross into the section.
- **Light:** flat even studio light, glossy clinical render, no grain, no lens character.
- **Wardrobe rule** (the only one there is): the character never changes design — same lump, same face, same colour — only its expression and pose. And nothing in the frame moves except the hand, the fluid, and the character.

If you wanted a live-action cousin of this, the transferable part isn't the render — it's the elimination with a question mark on every wrong answer and a personified problem reacting to each one.

**Or generate it**

Image prompt for the payoff beat:

```
vertical 9:16 3D medical-illustration render, locked front-on view, plain soft
off-white ground across the upper third and a cutaway cross-section of {SUBJECT}
filling the lower two-thirds — surface layer running horizontally, tissue below it
opened in section with fine branching capillaries; one open cavity centre frame
running down from the surface, its walls detailed and lined with fine pale strands;
inside the cavity a lumpy dark-brown lumpen character with a simple cartoon face —
wide white eyes, open screaming mouth, stubby arms and legs flung out — lifted off
the floor of the cavity by clear fluid that has flooded up around it, bubbles
suspended in the fluid; a photoreal human hand entering from the top of frame
pressing a round white cotton pad soaked in {PRODUCT} flat onto the surface directly
over the cavity mouth, droplets running off it; soft even studio light, glossy
clinical render, saturated interior detail, no photographic grain, no human face,
no room, no on-screen text
```

**Motion:** camera absolutely locked — the cross-section never moves; only the hand and its applicator come down onto the surface, the fluid fills the cavity, and the character's pose and expression change inside it. Generate every beat from the same seed frame and let the character do all the acting.

**Text overlay pattern:** two slots, one pinned and one cycling.

- Pinned all runtime, bottom centre, heavy white caps with a black outline: `{THE PROBLEM}`
- Cycling in the top third, dark elegant serif, one per beat: `{FAILED OPTION}?` → `{FAILED OPTION}?` → `{FAILED OPTION}?` → `{THE REAL ACTIVE}`

Every failure keeps the question mark. The answer drops it and holds for the last two beats.

**Reference:** https://www.instagram.com/p/DbpBDOHD-Ru/
