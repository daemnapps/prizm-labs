<!-- winner-breakdown v1. HELD FOR REVIEW: not live. Nothing reads this folder; it goes live only when the owner has
seen it and it is moved to components/winners/prompts/. The record it returns is checked and filed by
components/winners/breakdown.py, which also fills the top-ads board's `breakdown`. -->
You are taking one proven ad apart, part by part, so the next brief starts from what it actually did. This is
observation first: say what the ad does and quote it, in the order below. Do not grade it and do not rewrite it.
Every example here is illustrative.

THE AD
{ad}

ITS NUMBERS (the bank's, for the window named)
{numbers}

ITS WORDS, AS SPOKEN AND AS SHOWN (the teardown and the transcript)
{words}

ITS SCENES, IN ORDER (what is on screen, with times)
{scenes}

THE BRAND'S ANGLE LIST (an angle is named from this list, or it is "none on the list")
{angles}

Work in this order, and do not skip a part. Where the ad has no such part, write "none" and move on.

1. HOOK. The first words said and the first words shown, quoted. What the viewer is promised or shown in the first
   three seconds.
2. LEAD. What carries the conversation on once the hook lands, quoted, and the tone it sets.
3. OFFER. Exactly what is offered, quoted: price, bundle, discount, bonus, deadline. No offer stated: "none".
4. MECHANISM. How the ad says the product works (how it works, not what it does), quoted.
5. OUTCOME. What the ad says the buyer gets or becomes, quoted.
6. FEATURES AGAINST BENEFITS. Each feature the ad names, and beside it the benefit the ad ties to it. A feature with
   no benefit said: write the feature and "no benefit said".
7. GUARANTEE. The guarantee as stated, quoted. None stated: "none".
8. ASK. The last thing the viewer is told to do, quoted, and when it comes.
9. THE SCENES WITH THE SOUND OFF. Go through the scenes in order as if muted. For each: what is on screen, what
   words are on screen, and whether the ad's point is still clear without sound. One line each.
10. TYPE AND ANGLE. Its type: what is on screen for most of the ad (one of the fixed on-screen types given with the
    ad). Its angle: the one claim it makes that a viewer could agree or disagree with, in one sentence, and the id
    of the angle on the brand's list it matches, or "none on the list".
11. WHAT TO CHANGE. End with a list: each item is one thing a next version would change, and what stays exactly as
    it is. One change per item. Start with new openings on the same body.

Rules:
- Quote, with the time when the source gives one. Never fill a part from what ads like this usually say.
- A part you can't find in the words or the scenes is "none", never a guess.
- Numbers are the ones given above, exactly; add none.

The json must parse. Inside any string value write quotation marks as curly quotes or escape them.

Return one fenced json block and nothing else:

```json
{
  "hook": {"said": "", "shown": "", "does": ""},
  "lead": {"quote": "", "tone": ""},
  "offer": {"quote": "", "parts": []},
  "mechanism": {"quote": ""},
  "outcome": {"quote": ""},
  "features_benefits": [{"feature": "", "benefit": ""}],
  "guarantee": {"quote": ""},
  "ask": {"quote": "", "at": ""},
  "sound_off": [{"scene": 1, "on_screen": "", "words_on_screen": "", "clear_without_sound": true}],
  "type": "",
  "angle": {"claim": "", "id": "an id from the brand's list | none on the list"},
  "what_to_change": [{"change": "", "keep": ""}]
}
```
