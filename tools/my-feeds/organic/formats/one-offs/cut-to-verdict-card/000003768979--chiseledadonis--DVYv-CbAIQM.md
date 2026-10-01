# Cut-to-verdict card — rebuild sheet

A 13.5s reaction post by chiseledadonis: someone's gym clip gets a question pinned over it, and instead of an answer the whole screen is taken over by a video-game GAME OVER card that holds to the end — 3,768,979 views, 239,242 likes, caption "Shadow Realm Him IMMEDIATELY".

**Why it works** — The question on screen ("is this good form?") sets up an answer the viewer now wants, and the video refuses to give it, replacing both the clip and the person with a canned death screen. Withholding the verdict and letting a graphic say it is funnier and harsher than any spoken take, and the long hold on the card is what makes the joke land instead of passing.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 1.08s | Split frame. Top: handheld gym footage — a lifter flat on a bench under a barbell loaded with big black plates, a spotter leaning over the bar with both hands on it, two more people standing around, power rack behind, flat gym lighting. Bottom: a bearded man chest-up and centred, hood up under a black sleeveless top, mid-speech, dark room with a blue neon bar and decorated shelving behind him. Two rooms, two cameras — the top panel is sourced footage, not his own. | IS THIS GOOD FORM? / 420LB AT 14YO |
| 3.23s | Full black. Both panels gone. A neon-blue wordmark glitching in at centre-left, letters only half drawn, a vertical blue streak cutting through. | GAME OVER |
| 5.39s | Still black, the word half-assembled and reading GAME OVE, a bright blue streak sweeping across it. | GAME OVER |
| 7.54s | The card fully assembled: GAME OVER in outlined neon-blue chrome type across the middle, CONTINUE and EXIT small underneath. | GAME OVER / CONTINUE / EXIT |
| 9.7s | Identical hold. Nothing has moved since the last beat. | GAME OVER / CONTINUE / EXIT |
| 11.85s | Same card, EXIT faded out, CONTINUE alone under the wordmark. | GAME OVER / CONTINUE |

**What the frames don't show** — say this out loud rather than filling it in:

- Where exactly the cut to the card lands. Nothing was sampled between 1.08s and 3.23s, so the setup could run one second or three.
- Whether the man speaks at all, and what any audio or music does. He is mid-speech in the only frame he appears in; frames carry no sound.
- The last 1.6s after 11.85s is not sampled.
- Only one frame of the gym clip exists, so how much of the lift plays before the cut is unknown.
- No product appears anywhere in the six frames. This is an organic post; a rebuild has to decide for itself where a product goes.

**What carries the value** — The verdict card. The pinned question never gets answered out loud; it gets answered by a death screen that eats the entire frame and then just sits there. The persuasion is the refusal plus the hold — roughly two thirds of the runtime is a black screen with one graphic on it, and that is the whole joke.

**Shoot it** — Two pieces, and only one of them is a shoot.

- *The clip panel:* not shot, sourced. Someone else's footage of a thing being done badly or absurdly. Pin the question over it in white bold caps, two lines, top of frame — line one is the question, line two is the detail that disqualifies it.
- *The reaction panel:* phone on a tripod or propped, locked, framed chest-up, subject centred, facing camera. Dark room, one soft light on the face from the front, everything behind falling off to black except one coloured light source (his is a blue neon bar on the wall). No movement, no zoom. Wardrobe is whatever is already on — hood up, plain dark layers; the point is that this person is not performing, they're just registering.
- *The card:* made in an editor, not filmed. Black frame, one line of neon-outlined type, small sub-options underneath, a short glitch-in of a second or two, then dead still to the end. Do not cut back to the person — the fact that they vanish is the format.
- Length discipline: setup under 3 seconds, card for everything after. If the card is on screen for less than half the runtime, this isn't the format.

**Or generate it** — The card is a graphic, so build it in an editor. Generate only the reaction panel:

```
vertical 9:16 photograph, {SUBJECT} chest-up and centred, hood up under a black
sleeveless top, sitting in a dark room facing camera, a horizontal blue neon light
bar and decorated shelving on the wall behind them, soft front key light with the
room falling to black at the edges, {PRODUCT} sitting in frame beside them and not
held or presented, phone-camera look, slight grain, no retouching, no on-screen text
```

*Motion:* camera locked on the reacting figure, no push and no pan, only their head and shoulders moving, held for a second or two before the frame is replaced entirely.

*Text overlay pattern:* panel one, pinned top, white bold caps, two lines — `{THE QUESTION}?` / `{THE DISQUALIFYING DETAIL}` — then a hard cut to a full-screen graphic card on black: `{VERDICT}` large and centred, `{OPTION}  {OPTION}` small beneath it, held unchanged to the end.

**Reference:** https://www.instagram.com/p/DVYv-CbAIQM/
