# Pull briefs — v1

*Paste this at the start of every working session in Higgsfield Supercomputer.
Replace `{BRAND}`. Optionally name a brief in `{BRIEF}`; leave it as "newest
open" and the newest open brief is picked.*

*v1 (2026-09-22): first version. The review checklist and the default asks
menu are inline so the prompt works on its own; the ASKS menu is the one in
`tools/05-ai-video-production/ASKS-SPEC.md`.*

---

```prompt
Working session on {BRAND}. Brief: {BRIEF} (or "newest open"). Do these in order; stop and show me at every ⏸.

## 1. SYNC — always first, never skipped
- Pull https://github.com/daemnapps/prizm-labs for updates and say in one line whether anything changed under tools/21-editor-onboarding/ or tools/05-ai-video-production/. If tools/21-editor-onboarding/SOP.md changed, re-read it.
- Open `briefs/QUEUE.md` in the {BRAND} folder on Google Drive. Read it live — not a copy from an earlier chat.
- Show me the open and claimed briefs, newest first: brief · type · status · who · bounty · due.

## 2. PICK
- If I named a brief, use it. Otherwise take the newest brief whose status is `open`.
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
- FORMATS — the base cut planned at 9:16 plus a 4:5 and a 1:1 reframe note (what to crop, what to protect), and a 15-second cutdown map (which scenes survive).
- STYLES — only if the handoff names a style variation. Otherwise skip and say so.
Name every file `<brief>--<ask>--<n>` (for example `kzn03--stopper--2`). Show me each one as it lands, with the prompt used.
⏸ Stop. I approve or reroll.

## 6. HAND IT TO THE EDIT
If the brief is a video: put everything into one folder named `<brief>--edit` — the base clips numbered as in the scene table, the voice files, the approved asks, and a `CUT-SHEET.md` written from THE INTENDED SHAPE: scene order, target seconds per segment, where it breathes, the cards and overlays to compose from POST, the captions to burn. I take that folder into Premiere or CapCut.
If the brief is static: the approved drafts and asks, padded to the formats named, in one folder `<brief>--finals`.

## 7. DELIVER
- Upload the finished files to `briefs/delivered/<brief>/` in the {BRAND} folder on Google Drive, named `<brief>--<what>--v1.<ext>`. Never into the source package.
- Write `briefs/delivered/<brief>/DELIVERED.md`: what was delivered, what was rerolled and why, what is still open for the owner to rule on, in that order, plain lines.
- Confirm to me with the Drive path. The queue picks it up from the folder — you do not edit QUEUE.md.

Rules, always:
- Nothing invented. If the brief does not say it, say "not in the brief" and ask.
- Every identity visible in a frame carries its reference. A person or product generated without their reference is a reroll, not a delivery.
- When Drive or GitHub cannot be reached, say which door failed, in one line, and wait.
```
