You check one finished clip of a short vertical video ad against what was written for it. The clip is attached. Watch
all of it, at its real speed, before you answer.

What was written, beat by beat, in order (each beat: who does it, the action, the prop in hand, who or what it lands
on, where, and any words said):
{beats}

The cast, by name, as each one looks:
{cast}

The line-up ("fixed": true means exactly these people stand in the line, in this order, and nobody else joins it;
anyone else in the cast moves around it; "fixed": false means no line is fixed and "order" is just the cast):
{lineup}

The staging as written:
{staging}

Give back JSON only, in exactly this shape:
{"beats": [{"beat": 1, "seen": true, "at": "0.0-2.5 s", "shows": "what the clip actually shows in this beat's place, in plain words"}],
 "cast": {"ok": true, "why": "who is on screen that should not be, or who is missing; empty when it matches"},
 "lineup": {"ok": true, "why": "where the order or the count breaks, at what second; empty when it holds or no line-up is fixed"}}

Rules:
1. `seen` is true only when the clip shows that beat's action done by that beat's person, with that prop when one is
   written, landing on that target when one is written. A different action in its place is false, and `shows`
   says what was done instead.
2. Judge the action, the person, the prop and the target. Do not judge acting quality, light, faces' likeness or the
   camera: other checks do that.
3. Beats happen in order. A beat that happens but out of order is false; say so in `shows`.
4. `cast.ok` is false when someone on screen is not in the cast (an extra person, a stranger in the line), or a cast
   member the beats need never appears. Background people far behind, out of focus, do not count.
5. `lineup.ok` is false, when the line-up is fixed, if at any moment the count changes, someone swaps places, joins or
   leaves. Name the second.
6. Every beat in the list gets one row, in order, with its own number.
