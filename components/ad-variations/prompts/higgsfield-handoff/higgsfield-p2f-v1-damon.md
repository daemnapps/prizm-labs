# Make a proven-ad → new-format video from its brief (Higgsfield) — v1

Paste this into a Claude session that has Higgsfield and Google Drive connected. Then paste one brief link from the list at the bottom (or say "all ready ones").

```text
You are making ONE finished AI video ad from a written brief. The brief is the whole job — follow it exactly, add nothing.

THE BRIEF: {brief_link}
Open it from Google Drive and read every section before generating anything.

WHAT THIS AD IS
A proven <brand> winner re-told in a new format. Product: Brilliance Face Scrub. Avatar: spot-hider (women 45+ with dark spots). Lane: AI. The ONLY offer is "buy 2, get 1 free" — never write, say or show any other price, discount or bundle.

HOW TO BUILD IT — in this order, and stop for my OK at each ★
1. Read THE PIECE (aspect, resolution, style), THE CAST, THE WORLD, THE PRODUCT, PRODUCT LOCK and COMPOSITION. Every person, room and product shot must match these descriptions.
2. ★ Voice first. Generate the spoken lines from A-ROLL ("Say:" lines, word for word) with ElevenLabs, using each cast member's Voice line. Send me the audio before any picture is made.
3. ★ Cast stills. Any cast member marked "Bank: <name>" starts from that banked cast master as the reference image — never a text-only face, never a new face. Anyone marked NEW gets one reference still built from their description and its "Real reference" moment. Product shots use the real tube per PRODUCT LOCK. Pictures: GPT Image. Send me the stills.
4. ★ Openings. Under WHAT TO GENERATE → "The openings", generate EVERY hook in the set (Control and each V), one clip each, exactly as each "Shot:" line says. Clips: Seedance, image-to-video from the approved stills.
5. ★ A-roll then B-roll. Generate each shot in order, exactly as written, image-to-video from approved stills. B-roll is only what the brief lists.
6. LAYERS AND SOUND: carry exactly what the brief lists (captions, music, effects) — never invent one.

RULES THAT NEVER BEND
- Spots are never lightened, blurred, smoothed or retouched in any frame unless the brief's shot says the change happens there. No instant before/after.
- Never invent a claim, number, testimonial, price or person. If the brief leaves a slot empty or says TO MAKE, stop and tell me — don't fill it.
- If the brief's top "Core message" line talks about anything other than dark spots and the face scrub, ignore that line and tell me.
- Edits are image-to-image: change one thing on the approved frame, never re-roll from scratch.
- Save everything to Google Drive: Shared Assets/runs/ad-variations/<brand>/higgsfield/<the brief's square name>/ (audio/, stills/, clips/), and send me the folder link.

When every ★ is approved, give me one list: each clip in order with its link, ready for the editor.
```

## The briefs (Google Drive)

| Square | Status | Brief |
|---|---|---|
| Scrub Task 5 (Hook 2) × TV-shopping live demo | **Ready** — passed every check | https://drive.google.com/file/d/1QdRxtQ_HiugXkPIXf7B_ABtx_Cwgkdzj/view |
| <brand>'s Grandma × Captioned steps (Hua Jin) | Brief written · 5 production fields to fill | https://drive.google.com/file/d/11xASIPn6OmkCshYOl4Rrkc1Lnb1LeDE6/view |
| Scrub Task 4 (Hook 1) × TV-shopping live demo | Brief written · 2 production fields to fill | https://drive.google.com/file/d/1X6qK9uWuf9dnYF6mCPwqroH_xlI1xmtU/view |
| Scrub Task 5 (Hook 2) × Captioned steps (Hua Jin) | Brief written · 1 production field to fill | https://drive.google.com/file/d/1QAs2ZY4OGynCCMXNM3Rs7IkSF0ivieUt/view |
| Scrub Task 43 (Hook 3) × TV-shopping live demo | Brief written · waiting at the Viewer Check | https://drive.google.com/file/d/1v5kJUXFxpKSxPdKTeaOxLx-u1FYrJZj5/view |

All briefs folder: https://drive.google.com/drive/folders/FOLDER_ID

"Production fields to fill" are items the chain's production check found empty in the brief (marked TO MAKE or blank). The prompt above stops and asks when it meets one.
