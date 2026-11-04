# The Viewer Chain

Page (every run, one tab each): (private page) · built by `viewer_chain.py` into `runs/viewer-check/INDEX.html`

the owner, 2026-10-02: *"consolidate the viewer check and the ad signal tools … build a chain now for this process … I think this is literally it."*

One brief in; one folder and one page out at `runs/viewer-check/<brand>/<label>/`.

    python3 components/marketing-chain-checks/viewer_chain.py <brief> --brand <b> --avatar <core> [--sub <sub>] [--kind video|"still image"|carousel] [--frames <dir or images>] [--label <name>]

| # | Step | What it does |
|---|---|---|
| 1 | Card | The avatar as a person, built from the profile (cached; `viewer-card` prompt) |
| 2 | Cut | What a viewer actually sees and hears, second by second (`viewer-cut`) |
| 3 | Feed | 9 real posts from the avatar's feed, with ours dropped in at a random spot |
| 4 | Scroll | 5 fresh viewers (`viewer-check` v2), 2 of them with the sound off |
| 5 | Objections | Their doubts, pitch lines and comments matched to the brand's objection bank, with the bank's answer quoted (`objection-match`). The viewers never see the bank. |
| 6 | Score | Code, against the real posts: stop, beats feed, stays to offer, not an ad before stop, would act, believe, not fake, not a pitch, works muted. "Looks real" is never scored. |
| 7 | Route | A fail goes back to the writing step, carrying the viewers' words and the bank's answers. New objections are flagged for the owner, never invented. |
| 8 | Hidden by the app | Faces, product and words found on each frame (`hidden-boxes`) and measured against the Reels zone (Meta's numbers) and the TikTok and Shorts zones (approximate) |
| 7b | Fix | The failing part is rewritten (`viewer-fix` prompt) using the objection bank's own answers and the customers' words from the language bank, with every change citing its source. Structure locked, prices and guarantees kept word for word, nothing invented. One rewrite, then the chain moves on: no second panel scrolls the fix (2026-10-31). The first round already names what is wrong and the bank holds the answers. |
| 7c | Learn | A pass after a fail is written to `records/learnings/<brand>--<avatar>.md`: what failed, each change (was → now, why, source), and the numbers after. Every later fix and every writing stage of the video and statics chains reads it. |
| · | Waiting for install | Where eyes go · will they keep watching (from the real video) · the face |

The video and statics chains run steps 1–7 at their own gate (`viewer.check`), using the same code. Their send-back re-makes the real writing step, and a pass after a fail is learned there too.

## First live runs (2 Oct)
- **Silent Chair** (<brand> · glow-up, video): FAILED. Belief 0/5, and 5/5 felt the refund line was a pitch. The refund line is not in the objection bank, so it's a new worry. It goes back to the lines that sound like a sales pitch.
- **p005 marker on belly** (<brand>, static; run as fed-up-king because the brief records no avatar): FAILED. Belief 0/5, 3 said it looked fake or staged, 5 said it was a pitch. "TRY <brand> NOVA", the device and the face sit partly under Reels' bottom bar. It goes back to the shot that looks fake or staged.
