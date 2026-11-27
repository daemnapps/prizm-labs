<!-- storyboard-ask-v4-the owner (2026-11-27, AI-1 acting intent) = storyboard-ask-v3 + an Intent paragraph, an `intent` object on every pitch and check 11 (the face has a reason). Every other word is v3's. -->
---

# THIS RUN: THE STORYBOARD (this replaces the reply format above)

The script is already written, checked and locked. Every spoken line, every
scene's job and the order of scenes stay exactly as they are. You are not
pitching a new ad this time. You are directing the pictures of the ad that
exists: for each scene below, pitch **{per_scene} different visual ideas**,
one per rung named above, that make the scene's moment impossible to scroll
past.

We use the swipe's picture to generate our version, and we extract its motion
pattern to generate our own. Each scene below gives the swipe's shot — its
composition, its camera and its motion pattern (what moves, in what order) —
and, read beside it, what the swipe does there and why it works. That shot is
the BASE your idea is built on: keep its composition and its motion pattern,
and make everything on it ours — our people, our place, our product, our idea —
pushed as far as the dial target in the rulings asks (intensity,
dramatisation, stopping power, motion, specificity, absurdity, realism).
Never a literal re-enactment; never a picture that throws the base away.

**What one idea is.** One premise you can say in a handful of words, turned
into what is seen. The kinds of move that clear the bar:
- a format the feed already knows, dropped onto the moment (found footage, a
  nature documentary, a heist, a sports replay, a cooking show, an evidence
  board);
- a scale flip on the problem (the problem becomes weather, a landscape, a
  monument, a crowd);
- a genre move borrowed onto a body part or an object (a safecracker's
  fingers, a bomb-disposal hand, a surgeon's count);
- an everyday object doing an impossible job (a letter that flies itself in,
  a bill stamped paid in full on its own, a bath mat that keeps score).

**What every idea holds — these are checks, not suggestions:**
1. **It says the line.** The picture plays the scene's spoken words; a viewer
   with the sound off still gets them. Never a picture about something else.
2. **One impossible or hyper-specific thing, read in a second**, and it IS the
   problem or the benefit (the controls target in the rulings sets how far).
3. **Inside our world, on the swipe's base.** The brief's people and look, in
   one of the brief's places (the scene card lists them), framed and moving
   the way the swipe's shot is. The surreal thing is treated as normal; nothing turns into a
   different film.
4. **Nonstop movement.** Something moves in every beat: hands, body, camera,
   the impossible thing. Never a held pose, never a slow push in.
5. **The problem stays visible** on every scene before the payoff, big enough
   to read on a phone. A clean result appears only at the payoff.
6. **The product is clear** on every scene whose section is about the product,
   the mechanism, the solution, the offer or the result: the real product,
   recognisable, doing its real job.
7. **Nothing enters from nowhere**; every prop is one already in the brief's
   props or world, or one the idea itself needs and names.
8. **No words on screen** inside the picture (captions are added at the edit).
9. **Facts stay facts.** The picture claims nothing the brief does not say.
10. **Hard rules hold:** {hard_rules}
11. **The face has a reason.** Every shot's `face` and `gestures` follow from the pitch's `intent`: the first tactic before the turn word, something visible on it, the second tactic after. A shot that is a held expression, or whose face ignores the intent, does not clear the bar.

**Beats.** Each scene lists its beats with ids. Your idea restages every beat:
keep the same beat ids, the same count and the same order (each beat plays
under the words it already sits under). For each beat say who does it, the
action as two things — `do`, the ONE visible action in one verb (the clip model's limit: a second joined action
drifts), and `action`, the whole picture of the beat with the impossible thing in it — the prop, and where. A beat keeps the swipe's
motion pattern for that moment (each shot says what the swipe shows there): the
same movement, done by our people, in our place, with our idea in it. When the
words say another person did something, that person is the one doing it on
screen.

**Intent.** Before you give any shot its face, decide what the person in the scene is trying to get from the person or thing in front of them: one verb aimed at someone or something, never a feeling (talk him out of it, make her admit it, stall until the timer ends). Say what is in the way and the first thing they try. Then find the word in the scene's line where that first try fails and a second one takes over: that word is the turn. Every shot's `face` and `gestures` come from this. Before the turn the eyes and hands pursue the want with the first tactic. On the turn word something visible changes: a breath, a look away or onto the other person, a hand that stops or starts. After it they play the second tactic. The eyes reach what they look at before the head follows, and the quietest line is played the quietest. A shot that is only a held expression is not directed. `face` and `gestures` stay visible actions only: no feeling words in them, as before. A scene with nobody acting (an insert) gets `"intent": null`.

**Shots.** Give every shot listed its face and its gestures for your idea, in
the same words a director gives an actor: what the eyes, brows and mouth do,
and what the hands and body do. And its camera, starting from the swipe's
camera for that shot: `angle` (where the lens is, its height and how close),
`camera_move` (exactly one of `push-in` · `pan` · `tilt` · `arc` · `handheld` ·
`hold`) and `camera_why` (what our idea changes in the swipe's camera, or
"the swipe's camera" when it stays).

**The scenes to direct:**

{scenes}

---

Reply with ONE fenced block tagged `STORYBOARD`, holding valid JSON and
nothing outside it except a single heading line `# STORYBOARD`:

```STORYBOARD
{"scenes": [
  {"id": "<scene id exactly as given>",
   "pitches": [
     {"title": "<working title, a few words>",
      "rung": "L2|L3|L5",
      "premise": "<the idea in a handful of words>",
      "intent": {"want": "<one verb phrase aimed at someone or something, no feeling words>", "blocked_by": "<what is in the way>", "tactic": "<the first thing they try>", "turn_on": "<the word of the scene's line where it changes>", "then": "<the second thing they try>"},
      "picture": "<one sentence: what the viewer sees>",
      "happens": "<the scene's new staging line: lower-case, present tense, starts with the verb, one clause, the same register as the scene's current line>",
      "setting_id": "<one place id from the scene card's list>",
      "first_frame_action": "<what is happening in the scene's opening picture, one sentence>",
      "beats": [{"id": "<beat id as given>", "who": "<cast id>", "do": "<ONE visible action: one verb, present tense, a few words, no 'and', 'as', 'while' or comma; never opening on says, stops, slows or settles>", "action": "<the whole picture of the beat: what is seen, the impossible thing included>", "prop": "<prop or empty>", "where": "<setting id>"}],
      "shots": [{"id": "<shot id as given>", "face": "<the face in this shot for your idea: eyes, brows, mouth, one clause>", "gestures": ["<what the hands and body do, one short clause each>"], "angle": "<where the lens is: side, height, distance>", "camera_move": "push-in|pan|tilt|arc|handheld|hold", "camera_why": "<what our idea changes in the swipe's camera, or 'the swipe's camera'>"}],
      "problem_visible": "<how the problem reads on screen, or 'payoff scene'>",
      "product": "<how the product reads on screen, or 'not this scene'>",
      "movement": "<what moves, beat by beat>",
      "keeps_from_swipe": "<the composition and motion pattern this scene keeps from the swipe>",
      "risk": "<the one way it fails>"}
   ]}
]}
```
