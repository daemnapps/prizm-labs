# Subtitled monologue, evidence cutaways — rebuild sheet

A 60-second piece by @heystevetan: he tells you a tool exists, and every claim he makes cuts away to a full-frame screen showing that exact thing — 331,441 views, 7,687 likes.

**Why it works**
The speech subtitles are chopped one clause to a beat and keep getting cut off mid-sentence, so there is never a clean place to stop watching. And the persuasion isn't in what he says — it's that the second he names a risk or a chore, the screen showing that risk or that chore fills the frame, so the viewer watches the claim instead of being asked to accept it.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 4.81s | Presenter chest-up in his own room — white t-shirt, dark glasses, podcast mic on a boom in the bottom-right foreground, shelves and a plant soft behind him. Talking straight to the lens. | "so Meta just dropped their official AI connector" |
| 14.42s | He's gone. Black frame, one small screenshot card floating centre: a Facebook "Your account has been disabled" notice. | "you don't have to worry about your account getting" |
| 24.04s | Same black frame, new card: an ads-manager ad-sets table, budget and cost columns, one column highlighted. | "you manually review every ad set" |
| 33.65s | Same black frame, new card: a dark AI chat window, "Good afternoon", empty prompt box. | "and simply tell it what you want" |
| 43.26s | Cut back to him. Same room, same wardrobe, framed slightly wider, standing more upright, hand raised mid-gesture. | "and it just does it in seconds" |
| 52.88s | Gone again — and the screen evidence now fills the frame edge to edge instead of floating: a campaign-build screen, ad creative at the top, settings filled in down the panel. | "pick the audience and runs the whole campaign for you" |

Two things worth naming. The presenter is **completely absent** during the cutaways — there is no little talking-head panel pinned in the corner, which is what separates this from the borrowed-cutaway formats. And the evidence **grows**: it floats small on black for three beats, then goes full-bleed at the end.

The screenshots carry their own text (the Facebook notice, the table headers, the greeting). That's the source material's text, not text this creator authored — the only authored overlay is the subtitle track in the table above.

**What carries the value**
The screen evidence, timed to the sentence. The ban notice lands under the risk line, the manual table lands under the drudgery line, the empty prompt box lands under "tell it what you want." The mid-sentence subtitles are the retention device; the screens are the argument. Note the ask is deferred entirely to the post caption — a comment gate, "Comment 'meta' and I'll send it to you" — nothing on screen ever asks for anything.

**Shoot it**

- **Camera:** phone on a small tripod at your seated eye level, vertical, chest-up framing set slightly off-centre so there's room on one side. Fixed — no push, no reframe. Shoot the two presenter beats in one sitting so the room matches; the sheet shows the second presenter beat framed a little wider than the first, so a small reset between takes is fine and reads as natural rather than sloppy.
- **Light:** soft even daylight from the front, roughly window-height. Nothing dramatic, no key-and-fill setup — the room behind should read as somewhere someone actually works.
- **Wardrobe:** plain solid t-shirt, no logo, no pattern. One accessory at most. The point is that nothing competes with the screens.
- **Room:** a real lived-in background with depth — shelving, a plant, ornaments — sat far enough back to go soft. Not a blank wall, not a styled set.
- **The mic is deliberate.** A podcast mic in the bottom of the foreground, out of focus, is doing credibility work in the first frame before he says a word. Put it in shot.
- **The cutaways:** record your own screens. Screenshot or screen-record the actual surfaces — the failure state, the tedious version, the thing that replaces it — then place each one small and centred on a pure black frame, and make the last one full-bleed.
- **The subtitles:** transcribe your own audio and break it one clause per beat, deliberately cutting each card mid-phrase. Never let a card end on a complete thought.

I cannot tell from six stills whether the cutaways are still screenshots or live screen recordings, whether there are additional cuts between the sampled beats, or whether the two presenter beats are one continuous take — build it either way; nothing in the structure depends on the answer.

**Or generate it**

The presenter beat is the one to generate — the screens are captured from your own product, never generated.

```
vertical 9:16 photograph, {SUBJECT} framed chest-up and set slightly left of
centre, plain white cotton t-shirt, dark-framed glasses, talking straight to
the lens with a relaxed open expression; a black podcast microphone on a boom
arm entering the bottom-right of frame in the foreground, close and out of
focus; behind them a real lived-in room thrown soft — open shelving with small
ornaments and books, a plant, a dark cabinet, a wall in warm neutral tone;
even soft daylight from the front, phone or mirrorless camera look, slight
grain, no retouching, no on-screen text; no product in this beat — {PRODUCT}
never appears in the presenter frames, it exists only in the full-frame screen
cutaways
```

**Motion:** camera fixed at the presenter's eye level with only the faintest handheld drift, no push and no reframe — the subject talks and gestures inside a frame that does not move, and the cut away to the screen is hard with no transition. Generate both presenter beats from the same seed so the room matches.

**Text overlay:** two centred lines low in frame, white sans-serif with a soft dark backing, replaced every beat by the next clause of one continuous spoken sentence and almost always cut off mid-phrase —

`so {SOURCE} just dropped {THING}` → `you don't have to worry about {RISK}` → `you manually {OLD MANUAL LABOUR}` → `and simply tell it {WHAT YOU WANT}` → `and it just does it {IN SECONDS}` → `{DOES THE WHOLE JOB} for you`

**Reference:** https://www.instagram.com/p/DXzGgl_zOg1/
