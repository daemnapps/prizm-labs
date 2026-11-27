# Narrator montage: what each run taught

One entry per run, newest first. Every lesson names the one home it went to. A lesson with no home is not filed.

## Where a lesson goes

| The lesson is about | Its home | Owner |
|---|---|---|
| what this format contains, its steps, its checks, its cost | this folder: `format.json` or `FORMAT.md` | the format's owner |
| a model: what it takes, what it gets wrong, its price | `components/generative-model-house/` (`models.json`, `MODEL-HOUSE.md`) | the model house curators |
| a stage prompt: teardown, writing, picture or clip wording | that stage's prompt file, through its component | the stage's owner |
| the brand: offer, claims, customer language | `brands/<brand>/` (a person commits it) | the brand's people |
| the hook | the writing station's hooks pass (`components/video-writing/`, Read Hooks and `machine/hook_matrix.py`) | the writing station's owner |

A lesson seen once is written here as an entry. A lesson seen twice becomes a rule in its home.

## Entry shape

```
### <date> · <brand> · <production label>
- Lesson: <one sentence>
- Home: <path>
- Change: <the rule or setting proposed, or "none yet">
- Status: proposed | applied (<commit>) | refused
```

## Entries

### 2026-11-08 · Brand A · Brand A_flex-face-brush_brief-0322 (edit, carried to six versions) <!-- agnostic: ok — a run log entry names its brief -->
- Lesson: the edit held together only once avatar, angle and format were locked and every pick was checked against them (creator, generated shot, supporting character, proof, music).
- Home: `FORMAT.md`, "The edit, done right"
- Change: section added (owner's yes, 2026-11-08).
- Status: applied
- Lesson: rotating many creators confused the viewer; the rule is one matching creator for the body, and only identical clip sections may not repeat.
- Home: `FORMAT.md`, "The edit, done right" → Avatar, Body
- Change: rule added.
- Status: applied
- Lesson: generated shots made from a text prompt read as AI; shots made from a real reference frame, copying its phone camera and re-encoded like a phone, sat with the footage.
- Home: `FORMAT.md` → Generated shots
- Change: rule added; the image-to-video route also belongs in `components/generative-model-house/` when seen again.
- Status: applied
- Lesson: silent picture beats (a press card, a review) stopped the ad; the narration has to run continuously, with quotes riding over it as motion.
- Home: `FORMAT.md` → Sound and graphics
- Change: rule added.
- Status: applied
- Lesson: creator clips carry their own fast cuts; a window that looks clean can open on a few frames of another moment.
- Home: `FORMAT.md` → Body (the frame-by-frame check)
- Change: rule added.
- Status: applied
- Lesson: a hook effect that slices into the interviewer's question loses the question; the question plays whole.
- Home: `FORMAT.md` → Hook; the writing station's hooks pass when seen again (`components/video-writing/`)
- Change: rule added here; the brief's V1 wording ("the cut slices the interviewer off mid-word") is overruled at the edit.
- Status: applied
- Lesson: two generated music beds were rejected; the bed has to be current chart-level music in the avatar's lane, chosen by ear.
- Home: `FORMAT.md` → Sound and graphics
- Change: rule added.
- Status: applied
- Lesson: soft takes (afro-piano, Afrobeats pop) were rejected; the take that stayed was harder (afro-trap: 808 slides, trap snare, rolling hats over afro percussion), picked by ear from four.
- Home: `FORMAT.md` → Sound and graphics
- Change: none beyond "picked by ear"; the lane is the owner's call each brief.
- Status: applied
- Lesson: a script's cultural reference follows the avatar (a Middle Eastern grandpa drinks arak, not moonshine), and the cloned voice has to be tested on the new word (plain "arak" was heard as "Iraq"; "AH-rak" was heard right).
- Home: the writing station (`components/video-writing/`) when seen again; for now the edit
- Change: none yet at the writing station (seen once).
- Status: proposed


### 2026-11-06 · Brand A · Brand A_flex-face-brush_brief-0322 (brief stage, before production)
- Lesson: a brief that leaves a scene's camera unsaid is held by the swipe match every time (three of five holds).
- Home: `components/video-writing/prompts/v2/stage5-ai-brief-v12-owner.md` (the camera field names who holds it)
- Change: rule added; the writing chain uses v12.
- Status: applied
- Lesson: our product's own action replacing the swipe product's action was read as a people change.
- Home: `components/video-writing/prompts/stage-5m-swipe-match/swipe-match-v3-owner.md`
- Change: rule added (the people are kept when only the product's action differs).
- Status: applied; its first live run waits on the judge's account (402 on 2026-11-06)
- Lesson: the brand's $100 store credit sat in the offer box but not in the guarantee file the claims check reads, so every line naming it was held.
- Home: `brands/Brand A/offers/guarantees.json` and `brands/Brand A/products/offer-bank.md`
- Change: store credit added, and FLEX stacking both guarantees recorded (owner, 2026-11-06).
- Status: applied
- Lesson: the claims reviewer read "at the bar, on a date" as a fragrance claim on one run and not on another.
- Home: the run's `RULINGS.md` for now; the claims reviewer prompt if seen again
- Change: the no-fragrance ruling now says the brief's own moments are not scent claims.
- Status: applied to this run only (seen once)
- Lesson: the swipe's written notes called a shot propped; the judge watching the video read a handheld selfie.
- Home: the teardown's shot record (video-teardown) when seen again; for now the brief follows the video
- Change: the video wins over the notes (owner rule, 2026-11-06).
- Status: applied to this brief
- Lesson: the manifest held two swipe beats the brief had dropped (the prestige anchor, the sell-out reason).
- Home: `brands/Brand A/products/flex.md` (What the live store says) and the brief
- Change: carried with two customers' own Foreo lines and the store's "sells out every month"; real words are used as said (owner rule).
- Status: applied
- Lesson: the claims reviewer passed the same S3 and S7 lines on three runs and held them on a fourth.
- Home: `components/video-writing/machine/writing_revalidate.py` claims_check
- Change: proposed: three reads and a majority, as the section check does; meanwhile `flex.md` states the store's own problem list as sayable.
- Status: proposed

- Lesson: the viewer panel held a brief whose copy was already written and reviewed.
- Home: `components/video-writing/machine/writing_revalidate.py`, `components/video-teardown/machine/run.py` (viewer_gate), `components/video-production/machine/run.py` (worth making)
- Change: the viewer panel is no longer a gate anywhere in the chain; `QC_VIEWER=1` runs it by hand (owner, 2026-11-06).
- Status: applied
- Lesson: the claims check sees each line's words but not the scene's sources, so a verbatim customer line reads as untraced.
- Home: `components/video-production/machine/claimfix.py` lines_of
- Change: proposed: pass each scene's `source` with its lines; meanwhile the run's RULINGS.md lists each customer line with its row id.
- Status: proposed

- Lesson: the owner's edits on the Storyboards board are not in the brief file until something writes them in, so production would make the version from before the review.
- Home: the Storyboards board's handoff step (owner's own repo) and this format's Brief step
- Change: proposed: the Brief step writes the board's edits into the brief before the writing checks run.
- Status: proposed

