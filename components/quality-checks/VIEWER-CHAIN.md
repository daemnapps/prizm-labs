# The Viewer Chain

the owner, 2026-10-02: *"consolidate the viewer check and the ad signal tools … build
a chain now for this process … I think this is literally it."*

One brief in; one folder and one page out at `runs/viewer-check/<brand>/<label>/`,
plus `runs/viewer-check/INDEX.html` with every run, one tab each.

    python3 components/quality-checks/viewer_chain.py <brief> --brand <b> --avatar <core> [--sub <sub>] [--kind video|"still image"|carousel] [--frames <dir or images>] [--label <name>]

| # | Step | What it does |
|---|---|---|
| 1 | Card | The avatar as a person, built from the profile (cached; `viewer-card`) |
| 2 | Cut | What a viewer actually sees and hears, second by second (`viewer-cut`) |
| 3 | Feed | 9 real posts from the avatar's feed, with ours dropped in at a random spot |
| 4 | Scroll | 5 fresh viewers (`viewer-check` v2), 2 of them with the sound off |
| 5 | Objections | Their doubts, pitch lines and comments matched to the brand's objection bank, the bank's answer quoted (`objection-match`). The viewers never see the bank. |
| 6 | Score | Code, against the real posts: stop, beats feed, stays to offer, not an ad before stop, would act, not fake, not a pitch, works muted, belief (`belief-drivers`). "Looks real" is never scored. |
| 7 | Route | A fail goes back to the writing step, carrying the viewers' words and the bank's answers. New objections are flagged for a person, never invented. |
| 7a | Answers from real data | Worries the bank can't answer are answered only with real lines from the brand's language bank, by row id, checked word for word (`answer-find`). None found means the proof doesn't exist yet. |
| 7b | Fix | The failing part is rewritten (`viewer-fix`) using the bank's answers and the customers' own words, each change citing its source. Structure locked; prices and guarantees kept word for word (a rewrite that changes one is refused); any quoted line must exist in the real data. A fresh 5 scroll it again, up to 3 rewrites, never building on a worse version. |
| 7c | Learn | A pass after a fail is written to `records/learnings/<brand>--<avatar>.md`: what failed, each change (was → now, why, source), and the numbers after. Every later fix and writing stage reads it. |
| 8 | Hidden by the app | Faces, product and words found on each frame (`hidden-boxes`) and measured against the Reels zone (Meta's numbers) and the TikTok and Shorts zones (approximate). |
| · | Waiting for install | Where eyes go · will they keep watching (from the real video) · the face |

The video and statics chains run steps 1–7 at their own gate (`viewer.check`),
using the same code; `viewer.run_loop` is the whole loop for any caller.
