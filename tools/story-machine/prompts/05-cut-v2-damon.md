# Stage 5 — The Cut (v2)

Shortens a finished narration: trims an over-long Stage 2 script into its
band, and makes the 90 / 60 / 45-second paid cuts of an ad-lane story.

**Why v2 exists.** v1 asked the model to rewrite to a length. It can't count:
on the first run it claimed 431 words and wrote 607, and four rounds of
"counted in code, it's still too long" never got it into range. So the job is
split. **The model judges, the code counts.** The model labels and ranks every
sentence; code keeps the best sentence of every beat, then fills the word
budget in rank order. It lands in the band every time, and because the model
only picks lines, a cut can never contain a word the full script didn't.

Bands (~290 words a minute): Short 690–970 · 90s 400–460 · 60s 270–320 ·
45s 200–235. In the ad lane a cut that loses the product line is refused and
rerun.

---

This is a story narration split into {count} numbered sentences. {why}
1. Label every sentence with its beat: hook, setup, pressure, turn, payoff, sting.
2. Rank EVERY sentence from most essential to least essential. The hook, the product line (if any), the turn, the payoff and the last line rank highest. Within a beat, rank the sentence that carries the beat on its own first — one a listener understands without the sentence before it.
Return only JSON: {"beat": {"0": "hook", ...}, "rank": [every number, most essential first]}

{listing}
