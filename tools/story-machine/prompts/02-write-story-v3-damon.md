# Stage 2 — Write the Story (v3)

Turns one seed into the narration for a vertical story video. Shape copied
from the format's biggest videos (8.4M, 8.3M, 6.6M, 3.6M views).

**v2 (6 Oct 2026): no length limit.** v1 capped the script at 690–970 words
and the cap was cutting the work. The story runs as long as the story needs.
When the seed came from a swipe, the swipe's own beats set the shape.

**v3:** the story-ad lane. It is a dramatized story in the customer's own
words, with the product at the turn.

---

You are writing the narration for a vertical story video. It is read by a
voice over B-roll with one word on screen at a time. Nobody sees a face.
The words carry everything.

## What you are given

- `{seed}` — one seed from Stage 1 (door, title, first line, pressure, turn,
  payoff, last line, receipt)
- `{lane}` — `organic`, `ad` or `story-ad`
- `{pack}` — **story-ad lane.** The language pack; her voice is built from it.
- `{brand_rules}` — **story-ad and ad lanes.** Banned words, required words, claim limits.
- `{voice}` — whose mouth this is in (first person, age, register). From the
  brand folder in the ad lane; invented in the organic lane.
- `{product_line}` — **ad lane only.** One product, one sentence of what it
  does, exactly as the brand states it. Never embellish.

## The beats, in order

| Beat | | What has to happen |
|---|---|---|
| 1 | **Title read aloud** | The title IS the first line. Question or reversal. |
| 2 | **Drop in** | Straight into the situation. No "so this happened". Who, where, what's wrong. |
| 3 | **The setup that hurts** | Specific details that make us side with them. Small, concrete, real (a birthday crown, a $5,000 monthly transfer, tape over a mouth). |
| 4 | **Pressure** | Three escalations. Each one costs more than the last. *But… so… but…* |
| 5 | **The turn** | The reveal, the snap, the stranger. One sentence that flips it. |
| 6 | **Payoff** | The score is settled or the kindness lands. Let it breathe — show reactions. |
| 7 | **Sting** | One short line. A feeling or a twist. Then stop. No moral, no outro. |

## Writing rules

1. **Spoken, not written.** Short sentences. Contractions. The way a person
   tells it to a friend at 1 a.m.
2. **Dialogue in quotes, said out loud.** Real people speak in the story —
   at least four short lines of dialogue. Dialogue is where the anger and
   the tears happen.
3. **One concrete detail per beat.** Numbers, objects, places. "$180,000",
   "his little birthday crown", "the bouncy house stood empty".
4. **No and-then.** Every sentence either causes the next or interrupts it.
5. **Never explain the feeling — show the reaction.** Not "I was sad".
   "I felt my own tears coming and knew I couldn't let him see me."
6. **Open a question early that you don't answer until the turn.** Why didn't anyone come? What is the boyfriend actually doing?
7. **No filler words the voice would stumble on**, no emojis, no stage
   directions, no headings in the narration itself.

## Lane rules

**organic** — fiction, no brand, no product, no advice, no claims. Nothing
graphic involving children; no sexual content involving minors in any form.

**ad**
- Every fact about the person must trace to `{seed}.RECEIPT`. If the
  receipt doesn't say it, the script doesn't say it.
- The product enters **at the turn only**, as the thing they found, in
  `{product_line}`'s words. One product, one mention, maybe two.
- The payoff is **shown** — someone noticing, a reaction, their own words —
  never a claim ("works in 3 days", "clinically proven") unless that exact
  claim is in `{product_line}`.
- Last line is still a story sting, not a call to action. The CTA lives on
  the end card, not in the voice.

**story-ad**
- Fiction: an invented narrator and invented events, told as a real person
  would tell them. Requested Reads' own disclaimer works the same way, and
  the video carries "Dramatized story" on screen.
- **Citations never go inside the narration.** The narration is only what the voice says: no [ids], no brackets, no quote marks around whole paragraphs. Ids go under WORDS USED.
- **Her voice is the pack.** Wherever she describes her skin, her doubts, her
  age or her family, use the pack's words (verbatim or near-verbatim) instead
  of writing new ones. List every [id] you used under WORDS USED (never inline).
- Never put a pack quote in another character's mouth as a review or a
  testimonial (no "a woman in a video said…").
- **The product enters at the turn, the way she'd say it.** A woman telling a
  friend, not a label read aloud. Name it once, maybe twice.
- Claims: only what `{product_line}` allows. No number of weeks, no
  "erase/remove/cure", nothing clinical, nothing in `{brand_rules}`' banned list.
- Proof is shown: someone noticing, or her doing the thing she'd stopped
  doing. The drama's own payoff and the skin payoff land together.
- The last line is a story sting, not a call to action.

## Return

```
TITLE: <title>
OPEN QUESTION: <the question planted early and held until the turn>

NARRATION:
<the full narration, one paragraph per beat, nothing else>

BEAT MARKS:
drop in — "<first 6 words>"
pressure 1 — "<first 6 words>"
pressure 2 — ...
pressure 3 — ...
turn — ...
payoff — ...
sting — ...

RECEIPT CHECK (ad lane): every fact in the script → the receipt words it came from. Any fact without a receipt: say so here.
WORDS USED (story-ad lane): every [id] from the pack that the script borrowed, with the line it shaped.
CLAIM CHECK (story-ad and ad lanes): every claim about the product → the product_line words that allow it.
```
