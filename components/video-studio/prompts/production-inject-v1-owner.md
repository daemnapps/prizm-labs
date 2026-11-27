# Production injection — our scene into the source's capabilities (v1, 2026-11-15)

> The production twin of the writing side's injection: the production spec (components/video-teardown stage 2p) says
> how the source is made, as capabilities with slots; this fills every slot with our scene and then DIRECTS it: our
> own movement instructions for every body and our own camera instructions for every shot, generated here. The
> source's capabilities are the inspiration (what each moment must do on screen, its timing, the kind of framing and
> move); the movement and the camera themselves are ours, written for our people, our place and our beats.

The capabilities of the source shots this scene re-makes, in order: {capabilities}

The source's casting roles: {casting}

Our scene, as written (cast with looks, lines, beats, staging, place): {scene}

Our scene's creative dials, already set by the writing (carry them as they are; production adds no dial of its own):
{dials}

What our tools can make, by kind (a move the 3D figures cannot carry is still written; it is listed as a gap): {tools}

Fill every slot:

1. Every capability with a slot other than FIXED gets our material for it, from our scene only. When our scene does
   not say what fills a slot, fill it from what our scene is about and say so in `filled_from`.
2. FIXED capabilities stay exactly as their mandate says.
3. Our cast takes the source's roles: say which of ours plays which role. A role our scene has nobody for is a gap.
4. Our lines go where the source's speech or sounds sit; never invent a line. Our words (actions, staging, camera
   words) never carry a capability id, a source shot id or anything else of the source: they are read by the people
   and the models who make the scene.
5. Write the scene as ROWS, one row per moment, in time order, so a person who has never seen the source can read it
   top to bottom: `line` = the number of the spoken line in this moment, exactly as numbered in our scene's `lines`, or null
   for a moment with no words; `speaker` and `say` = that line's speaker and its words
   EXACTLY as written (never reworded, split, merged or moved); `who` = the one person whose body carries the moment
   (often the speaker; the listener when the listener's reaction is the moment); `action` = what `who`'s body does (one
   move or a short chain; no person, prop or place in it); `prop`, `target`, `where`; `moves` = {name: what every
   other body on screen does in this moment}; `faces` = {name: one of the faces in the tools list}; `capability` =
   the capability this moment fills ("K07.C2"); `from_script` = true when this moment's action is written in our scene
   (its script or staging), false when you chose it as the director to meet the capability. Every one of our lines
   appears in exactly one row, in the script's order. A moment the source holds without words is a row with
   `line` null.
6. Direct it. Write our own movement and camera, as a director and a camera operator would for OUR scene, so every
   capability's mandate is met by our people in our place:
   - `direction.people`: every person on screen, where they start and which way they face. The floor is in metres:
     x runs across (negative left, positive right as the first shot sees it), y runs away from the first camera;
     a person is 1.7 m tall; people side by side stand 0.7 to 0.9 m apart; `face` is a name or degrees (0 faces
     the first camera, 90 faces +x, 180 away, 270 -x); `"sit": true` for anyone seated when the scene opens.
   - `direction.beats`: every move of every body, in order, on the beats' timing, each one action from the tools
     list's motion vocabulary (`can`; reaches to the `reach_parts`): {"from", "to", "who", "<action>": value,
     "note": "what it is, in words"}. Values, exactly: lean, tilt = degrees (a number; 0 straightens); nod, shake =
     a count; squat = 0 to 1; sit, cross_legs, laugh = true or false; reach = "NAME.part" or "ME.part" or null, with
     "hands": "left", "right" or "both"; turn = a name or degrees (the whole body); look = a name or degrees (the head alone); point = a name or [x, y] or
     null; walk = [x, y];
     walk_to = a name. A move the vocabulary cannot carry gets its nearest action and is named in `routes` as PARTLY.
   - `direction.camera.shots`: every shot, in order: {"from": s, "at": [x, y, z], "look": "NAME.face" (or .chest,
     .hands, .feet, or a point [x, y, z] with its height), "lens": mm, "move": {"at", "look", "lens"} where it moves by the next shot, "words":
     the shot in plain camera words (size, angle, height, move)}. A new shot is a hard cut. Shot sizes, angles,
     heights, lenses and moves are ours, chosen so each capability lands; the source's framing is the reference for
     what kind of shot it is, never coordinates to copy. A phone camera is 1.2 to 1.7 m high; 24-35 mm reads as a
     phone; closer than 1 m only for a close-up.
7. Route every capability to the tool that makes it (from the tools list). `tool` is that tool's name; "GAP" when no
   tool can make it, or "PARTLY: <tool>" when the tool makes only some of it. `gap` says what is missing, and only then.

Answer as JSON, nothing else:

{"roles": {"⟨source role⟩": "⟨our cast name⟩"},
 "script": [{"line": 1, "speaker": "...", "say": "⟨the line, exactly⟩", "from": ⟨s⟩, "to": ⟨s⟩, "who": "...", "action": "...", "prop": "", "target": "", "where": "", "moves": {}, "faces": {}, "capability": "⟨K01.C2⟩", "from_script": true}],
 "staging": "⟨where our people stand and move, in order, in one paragraph⟩",
 "lineup": ["⟨our names in line order when the source holds a fixed line, else empty⟩"],
 "slots": [{"capability": "⟨K01.C1⟩", "slot": "...", "ours": "⟨what fills it⟩", "filled_from": "⟨the scene field it came from⟩"}],
 "direction": {"people": [{"name": "...", "at": [x, y], "face": "⟨a name or degrees⟩", "sit": false}],
               "beats": [{"from": 0.0, "to": 1.0, "who": "...", "⟨one action⟩": "⟨its value⟩"}],
               "camera": {"shots": [{"from": 0.0, "at": [x, y, z], "look": "NAME.face", "lens": 28, "move": {"at": [x, y, z]}, "words": "..."}]}},
 "routes": [{"capability": "⟨K01.C1⟩", "kind": "...", "tool": "⟨a tool from the list, or GAP⟩", "gap": "⟨what the tool cannot do, when GAP or partly⟩"}]}
