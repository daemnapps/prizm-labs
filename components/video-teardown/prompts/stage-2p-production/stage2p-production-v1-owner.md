# Production spec — how the source is MADE, as capabilities (v1, 2026-11-15)

> The production twin of the replication spec (stage 2). Stage 2 abstracts what the source SAYS into elements a new
> brand fills; this abstracts how the source is MADE (what the camera, the bodies, the edit, the sound, the set and the
> people on screen do) into capabilities a new brand's scenes fill. The source is inspiration: its skeleton is kept,
> everything in it that belongs to its own product and story is turned into a slot.
>
> Every example below is illustrative: the shape of an answer, never its content.

Here is the frame map of the source, shot by shot (who is in frame, the first and last frame, the camera, every
moment, on-screen text, sound, and how each shot hands off): {framemap}

Here is the source's sound sheet (music, effects, human sounds, room): {sound_sheet}

Here is the source's replication spec, its format and structural skeleton (the writing side's read of the same
video; use its phase names): {skeleton}

Its layers (format, style, structure, how it was made): {layers}

Turn how this video is made into a production spec: the discrete, reusable capabilities that make it work on screen,
abstracted from its brand, product, people and story so any brand's scenes can be produced through them.

Rules:

1. **Abstract, never copy.** A capability's `mandate` never carries the source's action, prop, person, product,
   graphic or place. Convert every specific into its function on screen: what the body does FOR the moment (an
   approach, a close inspection of another person, a recoil, a reaction to camera, a drop that reveals), how close,
   how long, how fast, in numbers. "lifts the mug to her nose and smells it" is the SOURCE INSTANCE; the mandate is "the
   actor brings the held object to within 5 cm of the face in 0.5 s and holds 0.8 s", and the action and the object
   are slots our scene fills.
   Details that only belong to the source's own action (the eyes closing while it smells, the hand cupped while it
   pours) go with the action into the slot, never into a FIXED mandate: the mandate keeps the distance, the timing
   and the shape, nothing that names how the source's own action is done.
2. **Every capability is one thing to make**, and names its `kind`: camera, motion, performance, edit, sound,
   on_screen, set, casting.
3. **Every capability names its `slot`**: what our scene puts in it. One of: OUR_ACTION, OUR_PROP, OUR_TARGET,
   OUR_CAST, OUR_PLACE, OUR_LINE, OUR_GRAPHIC, or FIXED (kept as the source does it: a camera move, a cut, a timing,
   a sound placement).
4. **Timing, camera and edit are the skeleton.** Their mandates keep the source's own seconds, framings and hand-offs.
5. **Casting is a role and its function, never a look.** "a judge who moves; a line of four who stand" with how they
   read on screen (the energy, the status between them); how the people look is our cast's, from our scene.
6. **Load-bearing**: the capabilities that carry the performance (change them and it stops working), each with why.
7. Read `moments`, not only the frames: each visible change is a candidate capability. Repeats (the same move to each
   person in a line) are one capability with a count.

Answer as JSON, nothing else:

{"format": "⟨what kind of production this is, in one line, with no product or story in it⟩",
 "shots": [
  {"id": "⟨the frame map's shot id⟩", "phase": "⟨the skeleton's phase it belongs to⟩", "from": ⟨s⟩, "to": ⟨s⟩,
   "capabilities": [
    {"id": "C1", "kind": "⟨camera · motion · performance · edit · sound · on_screen · set · casting⟩",
     "capability": "⟨its name, a few words⟩",
     "mandate": "⟨what must be true on screen, generic, numbers where numbers apply⟩",
     "source_instance": "⟨how the source does it, from the frame map, exactly⟩",
     "slot": "⟨OUR_ACTION · OUR_PROP · OUR_TARGET · OUR_CAST · OUR_PLACE · OUR_LINE · OUR_GRAPHIC · FIXED⟩",
     "who": "⟨the role it belongs to, as named in casting, or \"camera\"⟩"}]}],
 "casting": [{"role": "⟨a role name⟩", "function": "⟨what this role does for the video⟩", "count": ⟨n⟩, "reads_as": "⟨how they read on screen: energy, status, relation to the others⟩"}],
 "load_bearing": [{"id": "⟨a capability id, as K01.C2⟩", "why": "⟨what stops working without it⟩"}],
 "swappable": ["⟨what a new brand changes freely⟩"]}
