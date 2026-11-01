# Make a proven-ad → new-format video from its brief (Higgsfield) — v3, the template

> Which model does what: `components/generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). v3 changes only steps 2, 4 and 5 and the edits rule from v2: clips follow that rule (Omni today, not Seedance), the voice is the approved ElevenLabs v3 read fitted to Omni's lips (no speech-to-speech), and edits are GPT Image.

| Slot | Fill with |
|---|---|
| {brand} | the brand's spoken name |
| {brand_folder} | its folder under brands/ |
| {product} | the product's full name |
| {avatar} | the avatar line |
| {offer} | the one offer |
| {look_rule} | the product's never-retouch rule |
| {core_topic} | what the core message must be about |

A filled copy for a brand lives in `runs/ad-variations/<brand>/higgsfield/`; fill every slot from the brand's own files before pasting. `{brief_link}` is not a fill slot: it stays literal, as in v1.

Paste this into a Claude session that has Higgsfield, fal (for Omni) and Google Drive connected. Then paste one brief link from the list at the bottom (or say "all ready ones").

```text
You are making ONE finished AI video ad from a written brief. The brief is the whole job — follow it exactly, add nothing.

THE BRIEF: {brief_link}
Open it from Google Drive and read every section before generating anything.

WHAT THIS AD IS
A proven {brand} winner re-told in a new format. Product: {product}. Avatar: {avatar}. Lane: AI. The ONLY offer is "{offer}" — never write, say or show any other price, discount or bundle.

HOW TO BUILD IT — in this order, and stop for my OK at each ★
1. Read THE PIECE (aspect, resolution, style), THE CAST, THE WORLD, THE PRODUCT, PRODUCT LOCK and COMPOSITION. Every person, room and product shot must match these descriptions.
2. ★ Voice first. Generate the spoken lines from A-ROLL ("Say:" lines, word for word) with ElevenLabs v3, using each cast member's Voice line. Send me the audio before any picture is made. The read I approve is the voice the ad has — never change it with speech-to-speech.
3. ★ Cast stills. Any cast member marked "Bank: <name>" starts from that banked cast master as the reference image — never a text-only face, never a new face. Anyone marked NEW gets one reference still built from their description and its "Real reference" moment. Product shots use the real tube per PRODUCT LOCK. Pictures: GPT Image. Send me the stills.
4. ★ Openings. Under WHAT TO GENERATE → "The openings", generate EVERY hook in the set (Control and each V), one clip each, exactly as each "Shot:" line says. Clips, image-to-video from the approved stills: Omni (Google Gemini Omni Flash 1.1, on fal) for talking heads, the same face clip after clip, and anything meant to look shot on a phone. Omni says the line itself, so write the line word for word into its prompt, say nobody else speaks, and keep my approved ElevenLabs read: it is fitted to Omni's lips afterwards (align_take), never swapped in by speech-to-speech. Seedance 2.5 (Higgsfield) only for a shot that needs the strongest physical motion and may look cinematic. MiniMax H3 (Higgsfield) only for cheap B-roll where nobody talks. A shot taken from the swipe's own footage: Genjutsu object swap with the full cast sheet; if the swap kept the original face, Genjutsu motion transfer with our cast master.
5. ★ A-roll then B-roll. Generate each shot in order, exactly as written, image-to-video from approved stills, on the same clip models as step 4. B-roll is only what the brief lists.
6. LAYERS AND SOUND: carry exactly what the brief lists (captions, music, effects) — never invent one.

RULES THAT NEVER BEND
- {look_rule}
- Never invent a claim, number, testimonial, price or person. If the brief leaves a slot empty or says TO MAKE, stop and tell me — don't fill it.
- If the brief's top "Core message" line talks about anything other than {core_topic}, ignore that line and tell me.
- Edits are image-to-image on GPT Image: change one thing on the approved frame, never re-roll from scratch.
- Save everything to Google Drive: Shared Assets/runs/ad-variations/{brand_folder}/higgsfield/<the brief's square name>/ (audio/, stills/, clips/), and send me the folder link.

When every ★ is approved, give me one list: each clip in order with its link, ready for the editor.
```

## The briefs

Each brand's brief list sits in its filled copy: `runs/ad-variations/<brand>/higgsfield/higgsfield-p2f-v1-damon.md`.

"Production fields to fill" are items the chain's production check found empty in the brief (marked TO MAKE or blank). The prompt above stops and asks when it meets one.
