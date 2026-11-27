# How the first world skit's script got good

The first world skit went through about a dozen rounds before it worked. Each row is what was wrong, what changed, and where the rule now lives.

| # | What was wrong | What changed | Now enforced by |
|---|---|---|---|
| 1 | The audit held lines for sounding like a brand, and the close kept failing | Taste checks stopped holding the offer and the ask | Audit v10 |
| 2 | The voice didn't match the characters | Voices are cast to the character and checked by label and by ear | World file `voices`, memory of the rule |
| 3 | It was a voiceover over pictures | Two brothers actually talking, in the market's slang | Build v9 rules 1, 3 |
| 4 | Lines felt robotic and could sit anywhere | Each line answers the last; they interrupt and circle back | Build v9 rule 2, audit v11 check 13 |
| 5 | Two people talking, no scenes | One picture per joke, new scene when the joke moves | Build v9 rule 5, `script_check.py` |
| 6 | Razor bumps on the neck were never named | The problem and its place are said out loud early | Build v9 rule 4, `script_check.py` |
| 7 | Razors rained into the frame for no reason | The absurd image has to be what the words say | Build v9 rule 6, audit v11 check 13 |
| 8 | Failed fixes were listed, not shown | Each fix on his neck, bumps climbing, a counter on screen | Build v9 rule 7 |
| 9 | The ad stopped being an ad after the product arrived | Product, mechanism, demo, proof, after, objection, offer, ask, in order | Build v9 rule 8, `script_check.py` |
| 10 | Proof floated free | A character doubts first, then real reviews and real before and afters | Build v9 rule 9 |
| 11 | Top text read like an ad | Comment-style roast from the language bank | Build v9 rule 10, copy fill v7, `script_check.py` |
| 12 | Disclaimers on screen | None on these videos | `script_check.py`, world file |
| 13 | First frames flashed black and old bodies; openings were short | Render waits for the characters; openings run 1.5 s or more | Engine, `check.py` |
| 14 | Effects spilled into the next section; captions drifted | Effects stop at their section; captions use the heard words | Engine |

Lessons from the Razor Bump, Text Thread and Christmas ads: match the swipe's sound and tone first (build v9 rule 11, `check.py listen`), and make scenes line up with the voice (engine: words timed from the real voice; `script_check.py` requires a picture per joke).
