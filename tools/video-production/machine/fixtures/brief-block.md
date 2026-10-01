LANE: AI

# A Fixture Piece, As A Block

The same two scenes as `brief-frames.md`, written the way a current brief is
written: a short readable view for a person, and the fenced json block at the
end which is the brief. Scene 1 is to camera; **scene 2 is B-roll** — nobody
speaks in it and the paragraph plays over it at the edit. No brand, product or
person: invented throughout.

**S1 · A TABLE** — to camera. **S2 · A SHELF** — B-roll, the voice over it.

```json
{
 "lane": "ai",
 "piece": {
  "title": "A Fixture Piece, As A Block",
  "aspect_ratio": "9:16",
  "resolution": "720p",
  "format": "single-presenter",
  "brand": "_fixture",
  "avatar": "_fixture-avatar",
  "sub": "_fixture-sub",
  "awareness": "problem-aware",
  "sophistication": "stage-3",
  "framework": "_fixture-framework"
 },
 "cast": [
  {"id": "SPEAKER", "name": "THE SPEAKER",
   "identity_block": "an adult of no stated age, plain clothes, no jewellery",
   "voice": {"cast_voice_id": "00000000fixturevoice0000"}}
 ],
 "world": [
  {"id": "A TABLE", "description": "a plain wooden table by a window, morning daylight from the left"},
  {"id": "A SHELF", "description": "a shelf above head height in the same room, same daylight"}
 ],
 "product_lock": [],
 "scenes": [
  {
   "id": "S1",
   "section": "hook",
   "technique": "intensification",
   "delivery": {"humor": "dry", "style": "plain-flat", "register": "low", "pacing": "beat-and-pause"},
   "emotion": "recognition",
   "outcome": "the viewer has a name for it",
   "setting_id": "A TABLE",
   "who": "THE SPEAKER",
   "to_camera": true,
   "voice": "It comes back in the same place every time. That is not the product failing. That is the thing underneath it, doing what it does. Once you know that, you stop buying the same answer.",
   "first_frame": {
    "subject": "THE SPEAKER, seated at the table, one forearm resting on it",
    "composition": "medium-close, chest up, the forearm low in the frame",
    "action": "looking straight into the lens, hands still",
    "location": "A TABLE, the window out of frame to the left",
    "style": "flat daylight, ordinary and unstyled",
    "camera": "square on at chest height, little depth",
    "lighting": "soft directional daylight from the left, no fill",
    "refs": ["the cast sheet for THE SPEAKER", "the style frame"]
   },
   "beats": [
    {"id": "B1", "do": "holds the look into the lens", "camera": "held", "over": "It comes back in the same place every time.", "bracket": "flat, unsurprised"},
    {"id": "B2", "do": "turns the forearm up", "camera": "held", "over": "That is not the product failing.", "bracket": "matter-of-fact"},
    {"id": "B3", "do": "touches one fingertip to the forearm", "camera": "held", "over": "That is the thing underneath it, doing what it does.", "bracket": "plain"},
    {"id": "B4", "do": "lifts the eyes back to the lens", "camera": "held", "over": "Once you know that, you stop buying the same answer.", "bracket": "settled"}
   ],
   "last_frame": {
    "camera": "push-in to close",
    "change": "the camera has pushed in close, the forearm face-up filling the lower half of the frame with one fingertip resting on the mark, the face in the upper third looking straight into the lens"
   }
  },
  {
   "id": "S2",
   "section": "problem",
   "technique": "intensification",
   "delivery": {"humor": "dry", "style": "plain-flat", "register": "low", "pacing": "steady"},
   "emotion": "mild dread",
   "outcome": "the viewer sees the cost",
   "setting_id": "A SHELF",
   "who": "HANDS",
   "to_camera": false,
   "voice": "Reaching for the top shelf, and checking first who can see. That is the part nobody says out loud.",
   "first_frame": {
    "subject": "one hand and forearm, nobody's face in frame, reaching toward the shelf",
    "composition": "close, the shelf edge across the top third",
    "action": "reaching upward",
    "location": "A SHELF, the same room",
    "style": "flat daylight, ordinary and unstyled",
    "camera": "slightly below chest height, little depth",
    "lighting": "soft directional daylight from the left, no fill",
    "refs": ["the cast sheet for THE SPEAKER"]
   },
   "beats": [
    {"id": "B1", "do": "stretches toward the top shelf", "camera": "held", "over": "Reaching for the top shelf, and checking first who can see.", "bracket": "guarded"},
    {"id": "B2", "do": "holds", "camera": "held", "over": "the pause before the hand comes down", "bracket": "resigned"},
    {"id": "B3", "do": "lowers the hand out of frame", "camera": "held", "over": "That is the part nobody says out loud.", "bracket": "resigned"}
   ],
   "last_frame": {
    "camera": "same",
    "change": "the hand is gone from frame and the shelf is empty where it was"
   }
  }
 ]
}
```
