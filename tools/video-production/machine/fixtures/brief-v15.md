LANE: AI

# A Fixture Piece, v15 Order

The v15 shape (2026-09-23): every scene names its `kind`, `opens`,
`section` and `priority` — the section a doctrine id, from
components/marketing-doctrine/frameworks.json, never v14's retired `module`;
the piece names its `framework` as an ad-framework id; the four new kinds
(screen, split, greenscreen, endcard) nest their fields under the kind's
name; the block carries `layers`, `music`, `sfx` and `hooks`. One scene of
every kind. No brand, product or person:
invented throughout (the `_fixture` brand lives in machine/fixtures/brands).

## A-ROLL — the talking spine

**S1 · A TABLE · to camera** — tells the lens the mark comes back. (opens · hook · 1)

**S6 · A GREEN GROUND · to camera, green-screen** — keyed over an article page.

## B-ROLL

| Scene | From the swipe | Shows | Plays over |
|---|---|---|---|
| S2 | 0:06 · B-over | a hand reaching for the top shelf | "Reaching for the top shelf, and checking first who can see. That is the part nobody says out loud." |

## CARDS

| Scene | The plate | The words | Lands on | Sound |
|---|---|---|---|---|
| S3 | a blank till receipt | FOUR TRIES / ONE ANSWER / FROM [UNFILLED] | "That is the part nobody says out loud." | a till ding |

## SCREENS

| Scene | Surface | The plate | The words | Lands on |
|---|---|---|---|---|
| S4 | review | a phone's review page, every word blank | FIVE STARS / IT STOPPED COMING BACK / [UNFILLED] REVIEWS | "Once you know that, you stop buying the same answer." |

## SPLITS

| Scene | Layout | Left | Right | Labels |
|---|---|---|---|---|
| S5 | side | the forearm with the mark | the same forearm, clear | BEFORE / AFTER |

## GREEN-SCREEN

| Scene | Layout | Background | Speaker |
|---|---|---|---|
| S6 | cutout | an article page, every word blank | THE SPEAKER, waist up, right half |

## END CARD

| Scene | The plate | Offer | CTA | Guarantee |
|---|---|---|---|---|
| S7 | the real Fixture Balm packshot, right third | Fixture Balm / Price: $24.00 / Subscribed: $18.00 every 30 days | Get yours today | 30-day money-back guarantee |

## LAYERS AND SOUND

Hook text on from frame one; captions match the swipe; a whip after S2;
music mid · 104 bpm · warm; a whoosh on S2 and a ka-ching on the CTA.

## ROLL SHEET CHECK

| Swipe row | Roll | Our scene | Or dropped, because |
|---|---|---|---|
| 0:06 · [shows: reaching for the shelf] | B-over | S2 |  |
| 0:21 · [shows: receipt] | C | S3 |  |
| 0:24 · [screen: review] · [shows: a review page] | S | S4 |  |
| 0:25 · [shows: the street outside] | B-silent |  | the street is the source creator's own town; nothing of ours stands in for it |
| 0:30 · [split: before and after] | X | S5 |  |
| 0:34 · [greenscreen: article] | G | S6 |  |
| 0:40 · [endcard: packshot and offer] | E | S7 |  |

```json
{
 "lane": "ai",
 "piece": {
  "title": "A Fixture Piece, v15 Order",
  "aspect_ratio": "9:16",
  "resolution": "720p",
  "format": "single-presenter",
  "brand": "_fixture",
  "avatar": "_fixture-avatar",
  "sub": "_fixture-sub",
  "awareness": "problem-aware",
  "sophistication": "stage-3",
  "framework": "pas"
 },
 "cast": [
  {
   "id": "SPEAKER",
   "name": "THE SPEAKER",
   "identity_block": "an adult of no stated age, plain clothes, no jewellery",
   "voice": {
    "cast_voice_id": "00000000fixturevoice0000"
   }
  }
 ],
 "world": [
  {
   "id": "A TABLE",
   "description": "a plain wooden table by a window, morning daylight from the left"
  },
  {
   "id": "A SHELF",
   "description": "a shelf above head height in the same room, same daylight"
  },
  {
   "id": "A GREEN GROUND",
   "description": "a plain, flat, evenly lit green ground filling the frame behind the speaker, nothing else in it"
  }
 ],
 "product_lock": [
  "S7 — Fixture Balm — no garbled text, no morphing, product identical to the reference packshot."
 ],
 "scenes": [
  {
   "id": "S1",
   "kind": "talking",
   "opens": true,
   "priority": 1,
   "section": "hook",
   "technique": "intensification",
   "delivery": {
    "humor": "dry",
    "style": "plain-flat",
    "register": "low",
    "pacing": "beat-and-pause"
   },
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
    "refs": [
     "the cast sheet for THE SPEAKER",
     "the style frame"
    ]
   },
   "beats": [
    {
     "id": "B1",
     "do": "holds the look into the lens",
     "camera": "held",
     "over": "It comes back in the same place every time.",
     "bracket": "flat, unsurprised"
    },
    {
     "id": "B2",
     "do": "turns the forearm up",
     "camera": "held",
     "over": "That is not the product failing.",
     "bracket": "matter-of-fact"
    },
    {
     "id": "B3",
     "do": "touches one fingertip to the forearm",
     "camera": "held",
     "over": "That is the thing underneath it, doing what it does.",
     "bracket": "plain"
    },
    {
     "id": "B4",
     "do": "lifts the eyes back to the lens",
     "camera": "held",
     "over": "Once you know that, you stop buying the same answer.",
     "bracket": "settled"
    }
   ],
   "last_frame": {
    "camera": "push-in to close",
    "change": "the camera has pushed in close, the forearm face-up filling the lower half of the frame with one fingertip resting on the mark, the face in the upper third looking straight into the lens"
   }
  },
  {
   "id": "S2",
   "kind": "broll",
   "opens": false,
   "priority": 2,
   "section": "problem",
   "technique": "intensification",
   "delivery": {
    "humor": "dry",
    "style": "plain-flat",
    "register": "low",
    "pacing": "steady"
   },
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
    "viewpoint": "Her own point of view: the camera is where her eyes are, looking down. Both forearms enter from the bottom edge of the frame, elbows out of frame, angled slightly toward the basin. No arm enters from any other edge.",
    "lighting": "soft directional daylight from the left, no fill",
    "refs": [
     "the cast sheet for THE SPEAKER"
    ]
   },
   "beats": [
    {
     "id": "B1",
     "do": "stretches toward the top shelf",
     "camera": "held",
     "over": "Reaching for the top shelf, and checking first who can see.",
     "bracket": "guarded"
    },
    {
     "id": "B2",
     "do": "holds",
     "camera": "held",
     "over": "the pause before the hand comes down",
     "bracket": "resigned"
    },
    {
     "id": "B3",
     "do": "lowers the hand out of frame",
     "camera": "held",
     "over": "That is the part nobody says out loud.",
     "bracket": "resigned"
    }
   ],
   "last_frame": {
    "camera": "same",
    "change": "the hand is gone from frame and the shelf is empty where it was"
   }
  },
  {
   "id": "S3",
   "kind": "card",
   "opens": false,
   "priority": 2,
   "section": "proof",
   "to_camera": false,
   "plate": "a plain white till receipt, flat and square to the lens, filling the middle two thirds of the frame, blank where the lines would print, on a warm grey counter",
   "refs": [],
   "lines": [
    "FOUR TRIES",
    "ONE ANSWER",
    "FROM [UNFILLED]"
   ],
   "lands_on": "That is the part nobody says out loud.",
   "sfx": "a till ding",
   "voice": "",
   "source": "0:21 · C · [shows: receipt]"
  },
  {
   "id": "S4",
   "kind": "screen",
   "opens": false,
   "priority": 2,
   "section": "proof",
   "to_camera": false,
   "screen": {
    "plate": "a phone's review page filling the frame, square on, five empty star outlines at the top, three blank grey text lines under them, a round blank avatar top left",
    "surface": "review",
    "lines": [
     "FIVE STARS",
     "IT STOPPED COMING BACK",
     "[UNFILLED] REVIEWS"
    ],
    "lands_on": "Once you know that, you stop buying the same answer."
   },
   "refs": [
    "the style frame"
   ],
   "voice": "",
   "source": "0:24 · S · [screen: review] · [shows: a review page]"
  },
  {
   "id": "S5",
   "kind": "split",
   "opens": false,
   "priority": 2,
   "section": "unique-mechanism",
   "to_camera": false,
   "split": {
    "left": {
     "first_frame": {
      "subject": "one forearm, nobody's face in frame, the mark on the skin",
      "composition": "close, the forearm across the middle third",
      "action": "resting still",
      "location": "A SHELF, the same room",
      "style": "flat daylight, ordinary and unstyled",
      "camera": "square on at chest height, little depth",
      "viewpoint": "Her own point of view: the camera is where her eyes are, looking down. Both forearms enter from the bottom edge of the frame, elbows out of frame. No arm enters from any other edge.",
      "lighting": "soft directional daylight from the left, no fill",
      "refs": [
       "the style frame"
      ]
     },
     "beats": [
      {
       "id": "B1",
       "do": "rests",
       "camera": "held",
       "over": "Before, the mark sits right where it always sat.",
       "bracket": "flat"
      }
     ],
     "last_frame": {
      "camera": "same",
      "change": "the forearm has turned a little toward the window light"
     }
    },
    "right": {
     "first_frame": {
      "subject": "the same forearm, nobody's face in frame, the skin clear",
      "composition": "close, the forearm across the middle third, the same crop",
      "action": "resting still",
      "location": "A SHELF, the same room",
      "style": "flat daylight, ordinary and unstyled",
      "camera": "square on at chest height, little depth",
      "viewpoint": "Her own point of view: the camera is where her eyes are, looking down. Both forearms enter from the bottom edge of the frame, elbows out of frame. No arm enters from any other edge.",
      "lighting": "soft directional daylight from the left, no fill",
      "refs": [
       "the style frame"
      ]
     },
     "beats": [
      {
       "id": "B1",
       "do": "rests",
       "camera": "held",
       "over": "After, the same place is just skin.",
       "bracket": "settled"
      }
     ],
     "last_frame": {
      "camera": "same",
      "change": "the forearm has turned a little toward the window light"
     }
    },
    "layout": "side",
    "labels": [
     "BEFORE",
     "AFTER"
    ]
   },
   "voice": "Before, the mark sits right where it always sat. After, the same place is just skin.",
   "source": "0:30 · X · [split: before and after]"
  },
  {
   "id": "S6",
   "kind": "greenscreen",
   "opens": false,
   "priority": 1,
   "section": "unique-mechanism",
   "technique": "intensification",
   "delivery": {
    "humor": "dry",
    "style": "plain-flat",
    "register": "low",
    "pacing": "steady"
   },
   "emotion": "understanding",
   "outcome": "the viewer sees why it comes back",
   "setting_id": "A GREEN GROUND",
   "happens": "points back at the page behind",
   "who": "THE SPEAKER",
   "to_camera": true,
   "voice": "This is the page everybody reads first. It tells you to treat the mark. Nobody on it tells you why the mark comes back.",
   "first_frame": {
    "subject": "THE SPEAKER, standing, one hand raised toward the left of frame",
    "composition": "medium, waist up, the speaker in the right half of the frame",
    "action": "looking straight into the lens",
    "location": "A GREEN GROUND, nothing else in frame",
    "style": "flat daylight, ordinary and unstyled",
    "camera": "square on at chest height, little depth",
    "lighting": "flat even light on the speaker and on the green ground, no shadow on the ground",
    "refs": [
     "the cast sheet for THE SPEAKER",
     "the style frame"
    ]
   },
   "beats": [
    {
     "id": "B1",
     "do": "points left",
     "camera": "held",
     "over": "This is the page everybody reads first.",
     "bracket": "plain"
    },
    {
     "id": "B2",
     "do": "lowers the hand",
     "camera": "held",
     "over": "It tells you to treat the mark.",
     "bracket": "dry"
    },
    {
     "id": "B3",
     "do": "leans toward the lens",
     "camera": "held",
     "over": "Nobody on it tells you why the mark comes back.",
     "bracket": "settled"
    }
   ],
   "last_frame": {
    "camera": "push-in to medium-close",
    "change": "the camera has pushed in to medium-close, the speaker's hand down, leaning slightly toward the lens"
   },
   "greenscreen": {
    "background": "an article page on a laptop screen filling the frame, a grey header bar, a large blank image block, four blank grey text lines under it",
    "talker_scene": "S6",
    "layout": "cutout"
   },
   "on_screen": "nothing",
   "hold": "the same skin, the same light",
   "source": "0:34 · G · [greenscreen: article]"
  },
  {
   "id": "S7",
   "kind": "endcard",
   "opens": false,
   "priority": 1,
   "section": "offer",
   "to_camera": false,
   "endcard": {
    "plate": "the product standing upright in the right third of the frame on a warm grey counter, soft daylight from the left, clear empty space in the left two thirds for the offer lines",
    "offer_lines": [
     "Fixture Balm",
     "Price: $24.00",
     "Subscribed: $18.00 every 30 days"
    ],
    "cta": "Get yours today",
    "guarantee": "30-day money-back guarantee"
   },
   "refs": [
    "the Fixture Balm packshot",
    "the style frame"
   ],
   "voice": "",
   "source": "0:40 · E · [endcard: packshot and offer]"
  }
 ],
 "edit": {
  "headline": "none",
  "captions": "none in the source",
  "music": "none",
  "effects": []
 },
 "roll_sheet": [
  {
   "row": "0:06 · [shows: reaching for the shelf]",
   "roll": "B-over",
   "scene": "S2",
   "dropped": ""
  },
  {
   "row": "0:21 · [shows: receipt]",
   "roll": "C",
   "scene": "S3",
   "dropped": ""
  },
  {
   "row": "0:24 · [screen: review] · [shows: a review page]",
   "roll": "S",
   "scene": "S4",
   "dropped": ""
  },
  {
   "row": "0:25 · [shows: the street outside]",
   "roll": "B-silent",
   "scene": "",
   "dropped": "the street is the source creator's own town; nothing of ours stands in for it"
  },
  {
   "row": "0:30 · [split: before and after]",
   "roll": "X",
   "scene": "S5",
   "dropped": ""
  },
  {
   "row": "0:34 · [greenscreen: article]",
   "roll": "G",
   "scene": "S6",
   "dropped": ""
  },
  {
   "row": "0:40 · [endcard: packshot and offer]",
   "roll": "E",
   "scene": "S7",
   "dropped": ""
  }
 ],
 "layers": {
  "hook": {
   "text": "IT COMES BACK IN THE SAME PLACE",
   "look": "white bold caps, black box, top third"
  },
  "captions": {
   "look": "match-swipe"
  },
  "lower_thirds": [
   {
    "scene": "S1",
    "name": "THE SPEAKER",
    "title": ""
   }
  ],
  "annotations": [
   {
    "scene": "S4",
    "kind": "circle",
    "target": "the five star outlines",
    "at_words": "you stop buying the same answer"
   }
  ],
  "platform_ui": [
   {
    "scene": "S1",
    "kind": "comment_reply",
    "text": "does it really come back every time?",
    "handle": ""
   }
  ],
  "transitions": [
   {
    "after_scene": "S2",
    "kind": "whip"
   }
  ]
 },
 "music": {
  "energy": "mid",
  "tempo_bpm": 104,
  "mood": "warm"
 },
 "sfx": [
  {
   "cue": "whoosh",
   "at_words": "",
   "scene": "S2"
  },
  {
   "cue": "ka-ching",
   "at_words": "Get yours today",
   "scene": "S7"
  }
 ],
 "hooks": [
  {
   "id": "Opening 1 · Control",
   "text": "It comes back in the same place every time.",
   "opener_scene": "S1"
  },
  {
   "id": "Opening 2",
   "text": "The mark is not the problem."
  }
 ]
}
```
