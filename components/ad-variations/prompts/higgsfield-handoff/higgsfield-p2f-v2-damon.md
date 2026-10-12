# Make a proven-ad → new-format video from its brief (Higgsfield) — v2, the template

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

Paste this into a Claude session that has Higgsfield and Google Drive connected. Then paste one brief link from the list at the bottom (or say "all ready ones").

```text
You are making ONE finished AI video ad from a written brief. The brief is the whole job — follow it exactly, add nothing.

THE BRIEF: {brief_link}
Open it from Google Drive and read every section before generating anything.

WHAT THIS AD IS
A proven {brand} winner re-told in a new format. Product: {product}. Avatar: {avatar}. Lane: AI. The ONLY offer is "{offer}" — never write, say or show any other price, discount or bundle.

HOW TO BUILD IT — in this order, and stop for my OK at each ★
1. Read THE PIECE (aspect, resolution, style), THE CAST, THE WORLD, THE PRODUCT, PRODUCT LOCK and COMPOSITION. Every person, room and product shot must match these descriptions.
2. ★ Voice first. Generate the spoken lines from A-ROLL ("Say:" lines, word for word) with ElevenLabs, using each cast member's Voice line. Send me the audio before any picture is made.
3. ★ Cast stills. Any cast member marked "Bank: <name>" starts from that banked cast master as the reference image — never a text-only face, never a new face. Anyone marked NEW gets one reference still built from their description and its "Real reference" moment. Product shots use the real tube per PRODUCT LOCK. Pictures: GPT Image. Send me the stills.
4. ★ Openings. Under WHAT TO GENERATE → "The openings", generate EVERY hook in the set (Control and each V), one clip each, exactly as each "Shot:" line says. Clips: Seedance, image-to-video from the approved stills.
5. ★ A-roll then B-roll. Generate each shot in order, exactly as written, image-to-video from approved stills. B-roll is only what the brief lists.
6. LAYERS AND SOUND: carry exactly what the brief lists (captions, music, effects) — never invent one.

RULES THAT NEVER BEND
- {look_rule}
- Never invent a claim, number, testimonial, price or person. If the brief leaves a slot empty or says TO MAKE, stop and tell me — don't fill it.
- If the brief's top "Core message" line talks about anything other than {core_topic}, ignore that line and tell me.
- Edits are image-to-image: change one thing on the approved frame, never re-roll from scratch.
- Save everything to Google Drive: $SHARED_DRIVE/runs/ad-variations/{brand_folder}/higgsfield/<the brief's square name>/ (audio/, stills/, clips/), and send me the folder link.

When every ★ is approved, give me one list: each clip in order with its link, ready for the editor.
```

## The briefs

Each brand's brief list sits in its filled copy: `runs/ad-variations/<brand>/higgsfield/higgsfield-p2f-v1-damon.md`.

"Production fields to fill" are items the chain's production check found empty in the brief (marked TO MAKE or blank). The prompt above stops and asks when it meets one.
