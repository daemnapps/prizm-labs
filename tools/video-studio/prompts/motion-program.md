You are the blocking director for one continuous scene of a short vertical video ad. Before any video model is paid
for, the scene's motion is programmed as stand-in figures in 3D, so the paid take only has to dress what is already
right. Turn the take below into a blocking: where every person stands, what every body does on every line, and what the
phone camera does.

The floor is in metres. x runs across the frame (negative is left, positive is right, as the camera sees it at the
start); y runs away from the camera. The camera starts on the near side (y about -3) looking toward +y. A person is
1.7 m tall. Degrees for `face` and `turn`: 0 faces the camera, 90 faces right (+x), 180 faces away, 270 faces left.
People square up to whoever they reach for on their own. People standing side by side are 0.7 to 0.9 m apart; two people talking stand 0.5 to 0.8 m apart, facing
each other.

The take:
{take}

Each line's time window, in seconds (the line is spoken inside it):
{timeline}

The scene runs {seconds} seconds.

Give back JSON only, in exactly this shape:
{"people": [{"name": "HOST", "at": [x, y], "face": "<a name> or degrees", "color": [r, g, b], "legs": [r, g, b], "skin": [r, g, b]}],
 "beats": [{"from": 0.0, "to": 1.0, "who": "<name>", "<one action>": "..."}],
 "camera": {"at": [x, y, z], "look": [x, y, z], "lens": 26, "handheld": 0.02,
            "follow": [{"from": 0.0, "who": "<name>", "offset": [dx, dy, height]}]},
 "notes": ["one line for each move you could not say with the actions below"]}

Colours are 0 to 1, read from what each person wears and looks like in the take, so the stand-ins can be told apart.

Actions, one per beat:
- "walk": [x, y] walks to that spot.
- "walk_to": "<name>" walks to stand in front of that person, facing them.
- "reach": "<name>.<part>" with "hands": "both", "left" or "right": the hands go to that part of that person (cheeks,
  face, mouth, shoulder, chest). "reach": null lets go.
- "mic": "<name>" holds a microphone in the right hand out to that person's mouth. "mic": null lowers it.
- "turn": "<name>" or degrees turns to face someone.
- "lean": degrees leans forward (up to 30) or back (negative); 0 stands straight.
- "nod": count or "shake": count nods or shakes the head.
- "tilt": degrees tilts the head (up to 20); 0 straightens it.
- "laugh": true throws the head back with the shoulders bouncing.

Rules:
1. Every person the take mentions gets a name and a place, including people who never speak (name them by what they
   are: MAN1, MAN2, and so on, in the order the take meets them).
2. Every line gets the moves its `do` and `moves` describe, inside that line's window. A beat lasts 0.4 to 2 seconds.
   Walking 1 m takes about 1 second.
3. Keep the take's order: nobody reaches someone before walking to them; a hand lets go of one person before it reaches
   the next.
4. People with nothing to do still stand where the staging puts them and turn toward whoever is speaking or acting.
5. The camera is a phone held by a person: give it handheld drift, and follow whoever the action moves with
   (`follow`: the phone stays at that offset across the floor from them, at `height` metres off the floor, about 1.5
   at eye level), keeping the people who matter inside a 9:16 frame; 2 to 3 m away keeps a group of three in frame.
   The phone stands where the faces that matter are seen: for a line-up, out in front of the line looking along it or at
   it, never straight behind someone's back. Read the take's camera words for each line.
6. Faces are not yours (they are made later): only bodies, places and the camera.
7. If a move cannot be said with these actions, write it in `notes` and use the nearest action.
