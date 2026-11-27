# Pull briefs — v3

*Paste this at the start of every working session in Higgsfield
Supercomputer (or a Claude Code session on the cloned repo). Replace
`{BRAND}` and `{ROLE}`. Optionally name a brief in `{BRIEF}`; leave it as
"newest open" and the newest hand-off with an empty `returned/` is picked.*

*v3 (2026-10-01): the hand-off folder is the only door. Work is read from
`Shared Assets/handoffs/<role>/<brand>/<name>/` and its `handoff.md`, and goes
back into that hand-off's `returned/`, each file named `<brief id>_asset-NN`;
the team runs the take-back. The edit is the video-edit tool's AI cut, with
two review stops (timeline, captions), not Premiere or CapCut.*

*v2 (2026-09-22): FORMATS — one ratio. Nothing at 4:5 or 1:1; every frame
keeps faces, product and words inside the centred 4:5 crop; the ask is the
15-second cutdown map plus that check. v1 (2026-09-22): first version. The
review checklist and the default asks menu are inline so the prompt works on
its own; the ASKS menu is the one in `tools/video-production/ASKS-SPEC.md`.*

---

```prompt
Working session on {BRAND}. Brief: {BRIEF} (or "newest open"). Do these in order; stop and show me at every ⏸.

## 1. SYNC — always first, never skipped
- Pull https://github.com/daemnapps/prizm-labs for updates and say in one line whether anything changed under tools/editor-onboarding/, tools/video-production/ or tools/video-edit/. If tools/editor-onboarding/SOP.md changed, re-read it.
- Open my hand-off folder on Google Drive: `Shared Assets/handoffs/{ROLE}/{BRAND}/<my name>/`. Read it live — not a copy from an earlier chat.
- Show me every hand-off in it, newest first: what it is · the brief ids · whether `returned/` is empty.

## 2. PICK
- If I named a brief, use the hand-off that holds it. Otherwise take the newest hand-off whose `returned/` folder is empty.

## 3. READ THE HAND-OFF
- Read `handoff.md` in full — every section; do not skim. It says what this is, who it is for, what is inside by id, what to do, what must not change, the links, the checks, and how to send it back.
- Open `briefs/`, `assets/` and `references/` as `handoff.md` lists them.
- Lay out the brief for me:
  · WHAT THIS IS — two lines.
  · THE SCENES — the scene table exactly as the brief has it, and for each row the clip file, the voice file, and a thumbnail or first frame so I can see it.
  · If it is a static brief — every image draft, largest first, with its prompt beside it.
  · WHAT MUST NOT CHANGE, the known issues and the loop — verbatim.
  · THE ASKS if the brief has that section; if not, say "no asks section — using the default menu".
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

## 6. THE EDIT
Everything is cut at 9:16 with the subjects inside the 4:5 window — one master serves every placement.
- If the brief is a video: put the approved clips, the voice, the music and the approved asks into one kit folder, then run the video edit from tools/video-edit on it, exactly as its README describes. It makes the cut on its own and stops twice:
  · STOP 1 — THE TIMELINE. Show me the cut. I approve it, or give one change in plain words and why; it recuts and shows me again.
  · STOP 2 — THE CAPTIONS. Show me the captioned cut. I approve it or name the change.
  ⏸ Nothing moves past a stop until I approve it.
- If the brief is static: the approved drafts and asks, at 9:16, in one folder.

## 7. SEND IT BACK
- Put the finished files in the hand-off's `returned/` folder, each named `<brief id>_asset-NN.<ext>` (for example `brief-0142_asset-01.mp4`), numbered in the order `handoff.md` lists the assets. Nothing anywhere else.
- Walk the checks in `handoff.md` ("Checks before you're done") and tell me each one passed.
- Confirm to me with the Drive path. The team runs the take-back from `returned/` — you do not edit or move anything else.

Rules, always:
- Nothing invented. If the brief does not say it, say "not in the brief" and ask.
- Every identity visible in a frame carries its reference. A person or product generated without their reference is a reroll, not a delivery.
- When Drive or GitHub cannot be reached, say which door failed, in one line, and wait.
```
