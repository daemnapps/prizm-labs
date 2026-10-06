# Stage 2 — Write the Story (v2)

Turns one seed into the narration for a vertical story video. Shape copied
from the format's biggest videos (8.4M, 8.3M, 6.6M, 3.6M views).

**v2 (6 Oct 2026): no length limit.** v1 capped the script at 690–970 words
and the cap was cutting the work. The story runs as long as the story needs.
When the seed came from a swipe, the swipe's own beats set the shape.

---

You are writing the narration for a vertical story video. It is read by a
voice over B-roll with one word on screen at a time. Nobody sees a face.
The words carry everything.

## What you are given

- `{seed}` — one seed from Stage 1 (door, title, first line, pressure, turn,
  payoff, last line, receipt)
- `{lane}` — `organic` or `ad`
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
```
