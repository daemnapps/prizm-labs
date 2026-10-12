# The brief from her side — creator feedback, round one

*2 September 2026. Feedback from Creator A (@creator), Creator B (@creator), Creator C
(@creator) and a fourth note in the same thread, on the fifteen
Brand A briefs the machine sent them. Artifact: The Brief From Her Side (URL
in `context/artifacts.md`).*

## Diagnosis in one line

What they opened was the machine's internal shot spec — written so the picture
stage can draw every frame and so we can audit it against her old video — not
a brief. Every complaint points at a line that exists for the machine, not for
her. The fix is one split: the spec stays ours, a one-page brief goes to her.

## What went out

| Creator | Docs | Openers | Frames | Setups | Words |
|---|---|---|---|---|---|
| Creator A | 5 | 30 | 56 | 86 | 14,500 |
| Creator B | 5 | 30 | 52 | 82 | 11,600 |
| Creator C | 5 | 30 | 64 | 94 | 12,000 |
| **Total** | **15** | **90** | **172** | **262** | **38,000** |

## Complaint → the line she read → why it's there → fix

### Creator A

| She said | She read | Why it's there | Fix |
|---|---|---|---|
| "show a mask on my face, peel it, then self tanner, then the scrub" | `Source: "Subject tears open the top of the red mask pouch."` above every frame | Audit column: descriptions of her OWN old collagen-mask video, printed so we can check frame-vs-source (v24 rule 2) | **Cut.** Source lines never reach her document. |
| "I don't have rings anymore" | `Wearing: purple ribbed tank top, hair down, silver rings on both hands` ×56 | Wardrobe copied from her old videos to feed the picture generator (v24 rule 5) | **Move.** One line at top: "what you'd actually wear at home, sleeves up. Same outfit throughout." Full wardrobe stays in the spec. |
| "do I do just one of the suggested briefs? … only the scrub?" | `### The openings — shoot all six` / `### The frames`; no count, no product line anywhere | Prompt starts at the shot list: "what to point the camera at, what to wear, what to say. Nothing else." | **Add.** Cover lines: *Video 2 of 5. One video. Glow Body Scrub, one tube on camera.* Openers explained: six 3-second alternatives, we test which stops the scroll. |

### Creator B

| She said | She read | Why it's there | Fix |
|---|---|---|---|
| "five videos at this level of production detail is a significant undertaking" | JOJ-08: 19 frames for 40 s; `Say: "How"` / `"embarrassing. I wear a"` / `"cardigan. The amount of messages"` on 1-second frames | Unit is the cut: "Frame N replaces source shot N — one shot, one frame." An edit decision list, sent to the talent. | **Move.** Her page = 5–8 beats. Cut-by-cut stays in the spec for the editor and pictures. |
| "key messages in my own words, not word-for-word dialogue" | `Say:` = "the exact words she speaks"; `WHAT TO SAY — every line in order, nothing else`; CRA-03 scripts twelve "um/uh" back to her | Substitution injection keeps her transcript verbatim; the brief locks it. Her four "essential points" ARE the must-say list, never separated from the other forty lines. | **Add.** Two tiers: *Say these, however you'd say them* (4–5 locked points) + *the story, in your words*. Script stays as a labelled example. |

### Creator C

| She said | She read | Why it's there | Fix |
|---|---|---|---|
| "no window in view … not sure I have a plain wall" | `Same window, same daylight` ×14 (CRC-04), ×19 (CRC-05); `plain white wall … best camera available` ×5 (CRC-01) | "Every frame stands alone" restates place and light on every frame; one assumption becomes nineteen requirements. CRC-01 also needs a second, younger woman in a studio — nobody says who supplies her. | **Cut.** Setting once, as a need: "enough light to see the grains. Window if you have one, a lamp is fine." A format needing a second person says who provides her or isn't sent. |
| "two videos — one with still shots and one with video clips?" | Two sections + a generated still labelled `Frame N` on each of 12 frames; AI notice missing | Pictures per frame read as deliverables; the split reads as two videos. | **Move.** 3–4 pictures as a "how it might look" strip under the AI notice. One section, one video. |

### Fourth note

"Too much planned out, every step calculated… these creators can take a
simple idea and figure out how to film it." → The v24 prompt writes "the shot
list the maker films from… eight labelled lines" — which the picture stage and
the audit genuinely need. The mistake is pouring that same document into the
Doc. **One run, two documents:** spec (ours) + brief (hers).

## Broken regardless of the redesign

- **7 of 15 docs:** close reads `marketing@brand-a`, no domain (prompt says `marketing@[brand]`; the model filled the brand, not the address). CRA-02, CRA-03, JOJ-N2, CRC-01/02/03/05.
- **10 of 15 docs:** the AI notice the prompt requires word-for-word is missing from the brief body (the Doc builder still stamps it at the very top and bottom of every Doc, away from the pictures). Present in the body only in CRA-09, JOJ-01/03/08/N2.
- **CRC-01:** a cut slot left a broken caption — "How that year old influencer Is telling you to do skincare" — four times, as on-screen text.
- **14 of 15 docs:** openers need props or people she may not own (leg makeup, self-tanner, a drawer of 8–12 correctors, a candid photo from a daughter, a second person). Only two docs carry an "only if it's true for you" note.

## The shape she expected (CRA-01 "Twice a week", rebuilt from its own content)

**Twice a week** · Video 1 of 5 · Brand A Glow Body Scrub · one tube on camera · due ⟨date⟩ · upload ⟨link⟩

**The idea** — One tube, one arm, and the fifteen seconds where the grains disappear. No talking until the very end.

**Say these, however you'd say them**
- Twice a week. That's it.
- "Still on the first tube" — only if that's true for you.
- Use it twice a week, consistently. If the spots don't fade, you get every penny back.
- Glow Body Scrub, link's right there.

**The one shot that can't be skipped** — Macro on one patch of forearm, skin damp, no running water; the salt grains dissolving to smooth under your fingers. No cut, no speed-up. Shoot it three or four times.

**The story, in order**
1. Tube held up still, smiling. Caption: "POV When your scrub goes real deep!"
2. Flip the cap, a teaspoon into your palm, light on the grains.
3. Small circles on forearm and lower leg, skin damp.
4. **The dissolve** (the shot above).
5. Rinse cool, pat dry, hand slowly down the arm, tube back in frame.
6. Look up and talk for the first time — the lines above, to a friend in the room.

**Six ways to start** (3 s each; alternatives — we test which stops the scroll)
1. Tube held still — "POV When your scrub goes real deep!"
2. Sleeve shoved up, arm fills frame — "POV When the brown spots are the thing you're hiding!"
3. Your phone showing a photo of your hands — "That's when I see them. Not in the mirror — in the photo."
4. Short-sleeve top back on the hanger — "Every year the sleeves get a little longer."
5. Both forearms side by side in window light — only if the difference shows.
6. Pinching the skin inside the forearm, close — "Papery. That's the word I keep landing on."

**Wear · where** — Whatever you'd wear at home, arms bare, same outfit throughout. Your bathroom, whatever light you have, enough to see the grains.

**How it might look** — *AI generation is for demonstrative purposes only…* + 3–4 frames.

Questions? marketing@brand-a.com

~350 words against 1,500; nothing new, everything from the original document.

## Where the change lands

- **Stage 5 creator brief, v24 → v25:** one run writes two documents. The spec keeps every current rule; the brief is the page above with the must-say tier and the ask at the top.
- **Stage 9 (the Doc):** pours the brief, not the spec. The spec stays in the run folder beside the frames.
- **The four bugs:** full email in the close; AI notice enforced before the Doc builds; a cut slot never leaves a broken caption; any opener needing a prop or person says so in one line.

## Done, same day (2026-09-02, on the owner's "go")

- **Stage 5 → v25** (`prompts/stage-5-brief/creator-lane/stage5-creator-brief-v25-damon.md`, v24 archived): names itself as the spec; "What she may not have" rule (one-line out under any opening/frame needing a prop, person, place or fact of her life); "a cut leaves no hole" rule for cards; contact address via `{brand_contact}`.
- **Stage 7b, the page** (`prompts/stage-7b-page/stage7b-page-v2-damon.md`, new; v2 adds the bold product line and the fixed inspiration line — the owner, same day): runs after the pictures go in; writes the one sheet she reads from the finished spec. Wired in `machine/extra-stages.json` (role `page`, order after stage 7), `chain.py` (prompt home, LOOK, display id 7b), `run.py` (`brief_count` gathered per creator), `gdoc.py` (the Doc holds `stages/7b-page.md` when present; the notice is not re-stamped when the page carries it), `records.py` (`page.md` beside `brief.md`), `board.py` key map, `prompt_page.py`.
- **Brand contact file**: `brands/<brand>/channels/creators/contact.md` = marketing@brand-a.com. Any brand without one fails the stage loudly instead of guessing.
- **All fifteen Docs re-issued in place** (finished 2026-09-03 14:05): same links in `records/INDEX.md`; each opens on the page (v2: bold product line, fixed inspiration line). Creator A's five + CRC-01 rebuilt from scratch on spec v25 (`--redo`, then resumed after a hung Hooks call, an expired sign-in and two network drops); Creator B's five + CRC-02..05 carry page v2 over their existing v21–v24 specs. Pages mirrored to `records/runs/<slug>/page.md`.
- **Two machine fixes found on the way.** (1) A rerun that renames the concept used to create a second Doc beside the first (CRA-01 → "One tube, four places"): `run.py update_doc()` now updates the Doc the run already holds, title and all. The one stray copy it made sits in Creator A's folder renamed "superseded copy — do not use" — the machine's account cannot trash in a shared drive; the owner can. (2) Model calls launched from inside a Claude desktop session inherited the session's `USER` and failed "OAuth session expired" while a plain shell was logged in: `run.py _clean_env()` now gives every `claude -p` a plain environment (bisected 2026-09-03).
- **Open:** page v2 runs 830–1,120 words against the prompt's 250–500 budget (the six openers and their outs are most of it); CRA-01's full rerun named its concept after the prompt's own example ("One tube, four places") — the example heading in v25 should become an obvious placeholder in v26.
- Artifacts: The Creator Brief (spec v25 + page v1 verbatim) — (team page). The AI Lane restored to its previous version (it is the AI brief's page, not the creator lane's).
- **Page v3 (2026-09-03, the owner reading the brief: "we should have some sort of straight script to read from as well"):** `run.py script_block()` lifts every Say line in order from the spec (or every on-screen card on a silent format) and places it as "The script, straight through" above the pictures on every page — mechanical, so it cannot drift from the frames. Prompt v3 tells the model the section is appended for it. All fifteen pages re-issued in place.
- **Titles cleaned (2026-09-03, the owner: "clean up the titles"):** CRA-01 → *Hands, arms, chest*; CRA-03 → *The receipt is her body*; CRA-09 → *Interrupted in the aisle*; CRC-01 → *Gloss vs. bathroom* — renamed in the spec, the page and the Doc (in place, same links). Spec prompt v26: the sample concept in THE SHAPE is a ⟨placeholder⟩ and the naming rule forbids borrowing it.

