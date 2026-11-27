---
name: pull-briefs
description: Start an editing session on a brand's next brief — reads the live brief queue on Google Drive, claims a brief, downloads and lays out its package, reviews every scene, makes the asks, and hands it to the edit. Trigger when the editor says "pull briefs", "pull briefs for Brand A", "pull briefs for Brand B", "next brief", or names a brief to start.
---

# Pull briefs

*Made 1 Oct 2026 from the Pull-briefs prompt v2 (tools/21-editor-onboarding/prompts/02-pull-briefs-v2-owner.md) — the same steps, now a skill so the editor only triggers it. Brand = Brand A or Brand B, from what the editor said; if they didn't say, ask which one. Brief = the one they named, else the newest open.*

## The two brand folders (Google Drive, shared drive "Shared Assets")

| Brand | Briefs folder (the queue, the packages, `claims/`) | Deliver into |
|---|---|---|
| Brand A | https://drive.google.com/drive/folders/1-WlAVOrbhwCdroRk02LrWWxToHQyCuY9 | https://drive.google.com/drive/folders/142iy3AZe0AedKHbq55Mr0biJ9GFplzbR |
| Brand B | https://drive.google.com/drive/folders/1LEXFnXIL3Z2cXW7YSZzEZojhIJky4y0M | https://drive.google.com/drive/folders/1bLLYR3OMbXP6zo3U-9IiWlprqe3tCnAj |

## Video briefs: the hand-off folders (from 17 Nov 2026; this overrides the queue and the zips for video)

| Brand | Video hand-offs (one folder per numbered brief) |
|---|---|
| Brand A | https://drive.google.com/drive/folders/1nkOhgco7bSBb86MMz175FnoPnl1sPDTf |
| Brand B | https://drive.google.com/drive/folders/1JIkj3RRHBoFMVAsdPXIv0Pb9FaV_zltL |

- Every video brief is a folder `Shared Assets/runs/handoffs/video-editor/<brand>/<brief key>/`, e.g. `Brand A_flex-face-brush_brief-0333`. Only folders named `…_brief-NNNN` are briefs; a folder starting with `_` is set aside.
- A brief is **open** while its `returned/` folder is empty, **back** once it holds a file.
- In the folder: `BRIEF.md` (the ad), `RUN.md` (how to make each piece, step by step), `CLIPS.md` (every clip to make, its recipe and the exact file name to return), `ELEMENTS.md` (cast, sets and props to build first), `TIMELINE.html` (the ad on its clock), `edit/<key>.premiere.xml` (the Premiere timeline), `hyperframes/` (the same timeline in HyperFrames), `voice/` or `song/`, `refs/<clip>/`, `made/`.
- **Deliver into that folder's `returned/`**: each clip as named in `CLIPS.md`, then the cut as `<brief key>-control.mp4` (hooks `<brief key>-v1.mp4` …). Nothing goes to `briefs/delivered/` for video.
- On a machine with this repo, `python components/video-edit/open_brief.py list <brand>` lists them and `open <number> premiere|hyperframes` opens one.

`briefs/QUEUE.md` in the brand's briefs folder is the work queue — every brief, who it is for (the `For` column) and its state; the brief packages sit beside it (`ai-video-production/<brief>.zip` for video, `image/<brief>.zip` for pictures, `carousel/<brief>.zip` for carousels). Deliveries go to `briefs/delivered/<brief>/` — one folder per brief.

Working session on {BRAND}. Brief: {BRIEF} (or "newest open"). Do these in order; stop and show me at every ⏸.

## 1. SYNC — always first, never skipped
- Pull https://github.com/the owner/prizm-labs for updates and say in one line whether anything changed under tools/21-editor-onboarding/ or tools/05-ai-video-production/. If tools/21-editor-onboarding/SOP.md changed, re-read it.
- Open `briefs/QUEUE.md` in the {BRAND} folder on Google Drive. Read it live — not a copy from an earlier chat.
- Show me the rows that are mine, by the queue's `For` column — a video editor takes the `Video editor` rows, a graphic designer the `Graphic designer` and `Carousel` rows; if you do not know which I am, ask once: brief · old code · state · who · bounty · due.

## 2. PICK
- If I named a brief, use it. Otherwise take a row `Sent back` to me first (its note is what to fix), else the newest of mine whose state is `Open`.
- Claim it: create a file in `briefs/claims/` named `<brief> — <my name>` (empty is fine). If you cannot create files in Drive, tell me and I will make it.

## 3. GET THE PACKAGE
- Download the brief's package (a zip or a folder — the queue's Package column says which) and unpack it.
- Read the handoff document in full: `EDITOR-PACK.md`, `<brief>-editor-handoff.md`, or the brief `.md` — whichever is there. Read every section; do not skim.
- Lay out the brief for me:
  · WHAT THIS IS — two lines.
  · THE SCENES — the scene table exactly as the handoff has it, and for each row the clip file, the voice file, and a thumbnail or first frame so I can see it.
  · If it is a static brief — every image draft, largest first, with its prompt beside it.
  · THE INTENDED SHAPE, WHAT IS LOCKED, KNOWN ISSUES and THE LOOP — verbatim.
  · THE ASKS if the handoff has that section; if not, say "no asks section — using the default menu".
⏸ Show me all of this before doing anything else.

## 4. REVIEW — find what is wrong before we make anything
Go scene by scene (or draft by draft) and check every item below. Output one table: scene · verdict (KEEP / FIX AT CUT / REROLL) · what you saw.
- Same person: face, hair, skin, age, body are the same human in every scene they appear in.
- Same wardrobe: what the handoff locks is what is on screen — no swapped tops, no missing jewellery, no long sleeves where bare arms are locked.
- Same product: the real product, the right one, label readable where it plays large, nothing invented printed on it.
- Slop: extra or fused fingers, warped or gibberish text, melting objects, floating props, a hand through a surface, a mouth that does not match the line, a background that changes mid-shot.
- Sound: every spoken scene has its line; no silent stretches; the lip sync holds; no line is missing or doubled against LINE COVERAGE.
- Words: on-screen text spelled right, the offer says only what WHAT IS LOCKED allows, nothing medical, nothing about origin or guarantees that the handoff does not state.
- Odd: anything that made you look twice. Name it plainly.
Then a second short list — IDEAS — three to five ways the piece gets stronger inside its own loop and format: a tighter opener, a beat to hold longer, an insert that pays the loop off harder, a caption that lands the offer. No new claims, no new product facts, no new characters.
⏸ Stop. I decide what gets rerolled and which ideas we take.

## 5. THE ASKS — what the brief needs beyond the base cut
Use THE ASKS from the handoff. If the handoff has none, use this default menu. Make every item here in Higgsfield, from the brief's own cast references and product references (never a fresh text-described person or product), and keep the locked wardrobe, light and skin rule.
- SCROLL STOPPERS — three alternative first-three-seconds, each built from a different hook in the brief's hook set. Same scene 1 setting.
- HEADLINES — five on-screen headline lines for the opener card, each under eight words, each one a line from the brief's own language (the hooks, the loop, the offer). No new claims.
- VARIATIONS — one alternate take of the opening scene and one of the offer scene, same line, different framing.
- EXTRA SCENES — any insert the POST list or KNOWN ISSUES leaves uncovered: generate it as B-roll from the brief's setting and product.
- FORMATS — 9:16 only; we never make 4:5 or 1:1 versions. Two things: a 15-second cutdown map (which scenes survive, in order), and a check of every frame that faces, the product and every word on screen sit inside the centred 4:5 crop — the middle 70% of the frame — because feed placements cut the top and bottom 15% off. Name any scene that fails; that scene gets rerolled with the subject pulled in, not cropped later.
- STYLES — only if the handoff names a style variation. Otherwise skip and say so.
Name every file `<brief>--<ask>--<n>` (for example `kzn03--stopper--2`). Show me each one as it lands, with the prompt used.
⏸ Stop. I approve or reroll.

## 6. HAND IT TO THE EDIT
Everything is cut at 9:16 with the subjects inside the 4:5 window — one master serves every placement. If the brief is a video: put everything into one folder named `<brief>--edit` — the base clips numbered as in the scene table, the voice files, the approved asks, and a `CUT-SHEET.md` written from THE INTENDED SHAPE: scene order, target seconds per segment, where it breathes, the cards and overlays to compose from POST, the captions to burn. I take that folder into Premiere or CapCut.
If the brief is static: the approved drafts and asks, padded to the formats named, in one folder `<brief>--finals`.

When the edit is finished, the editor says "deliver" and the deliver-brief skill takes over.

Rules, always:
- Nothing invented. If the brief does not say it, say "not in the brief" and ask.
- Every identity visible in a frame carries its reference. A person or product generated without their reference is a reroll, not a delivery.
- When Drive or GitHub cannot be reached, say which door failed, in one line, and wait.
