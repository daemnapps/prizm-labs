# World Skit Format

Cost per variation, writing left out: voice about $0.05 to $0.40, pictures $0, generated video $0, Higgsfield credits $0, rendering $0 on this Mac.

Page: see artifacts.md.

A new variation is one mission file. Date at Eight proved it: 5 new lines, about $0.05, stop price $1.00, 0 script faults on its first draft.

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

## Changed prompts

## THE SKIT RULES — when two or more people carry the script

Apply these whenever the swipe's format is people talking to each other. A single presenter skips rules 1 to 3.

1. **Real back and forth.** No speaker holds more than two sentences in a row before the other cuts in. Most lines are under ten words.
2. **Every line answers the one before it.** Read each line alone with the line above it. If it could sit anywhere in the script, rewrite it. People interrupt, deny, drift and circle back.
3. **Their words, not ours.** Use the market's own slang and roast language from the language bank. Say the insult the comments already say.
4. **Name the problem and where it lives, out loud, in the first ten seconds,** in the viewer's own words. A joke about the problem does not replace naming it.
5. **One picture per joke.** Every joke names the shot that makes it land, and the shot is the joke made literal. If a line is only two people talking, cut it or give it a picture. Every location change earns a new scene.
6. **The absurd image must be what the words are saying.** Spectacle with no link to the line is cut, however big it is.
7. **Failed solutions are shown happening,** each on the problem itself, each making it visibly worse.
8. **From the moment the product appears, run direct response in order:** what it is, how it works, the demonstration, the proof, the after, the objection, the offer, the ask. The jokes keep going inside each section; no section is skipped.
9. **The doubt comes first, then the proof.** A character says what the viewer is thinking, then real customer words and real pictures land.
10. **The top text reads like a comment, not an ad.** Lower case, the market's roast language. No claim, no benefit, no product.
11. **Match the swipe's sound and tone before anything else.** If the swipe is laughing, this is laughing.

<!-- writing v2 (2026-11-02, V56): stage4v2b-build-v7 = v6 + THE CONTROLLING IDEA, EVERY SECTION IS A MOMENT, the creative moves bank and the owner's notes. -->

### 13 · THE SKIT TEST

Only when the swipe's format is people talking to each other. Fail, and quote the line or beat, if any of these is true:

- A speaker holds three or more sentences in a row.
- A line does not answer the line before it.
- The problem and where it lives are not said out loud in the first ten seconds.
- A joke has no picture named for it, or a stretch of four lines is only people talking in one place.
- An absurd image has nothing to do with the words over it.
- A failed solution is told and not shown.
- After the product appears, any of these is missing or out of order: what it is, how it works, demonstration, proof, the after, objection, offer, ask.
- Proof arrives before anyone doubts it.
- The top text states a claim, a benefit or the product.

The offer may stay plain, and bold or crude lines are never a failure here.

When the ad is an organic-style skit, write the headline and the first line like a comment under the video: lower case, the market's own roast language from the bank, no claim and no benefit up front.
