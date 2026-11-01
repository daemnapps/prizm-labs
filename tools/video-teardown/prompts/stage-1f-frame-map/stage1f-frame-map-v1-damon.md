# Frame map — one shot of the source, moment by moment (v1, 2026-10-01)

> the owner, 2026-10-01: "in the source video, actually map out every single frame so
> when we describe what happens in our version it's as close as possible to the
> swipe so it becomes indistinguishable. the movement of the characters and
> everything needs to be mimiced." Then: "there are layers to this entire
> experience … frame control and layering the timeline."
>
> Every example below is illustrative — the shape of an answer, never its
> content. Nothing here names a brand, product, category or person; you describe
> only what is in this clip.

You are watching ONE SHOT of a short vertical video — the stretch between two
cuts. It runs {seconds} seconds and sits at {start}–{end} s of the whole video.
Where the people are named in the full record, use these names: {people}.

Describe exactly what is on screen and in the sound, as it happens, so that a
person who never sees this clip could stage the same shot and an AI model could
copy the same movement. Facts only: what you see and hear. Where you are
unsure, say so in the field rather than guess.

Answer as JSON, nothing else:

{
 "who": ["⟨every person or body part in frame, by the names above — e.g. \"PERSON A (face, shoulders)\", \"PERSON B (right hand and forearm only)\"⟩"],
 "start_frame": "⟨the first frame as one still picture: who is where (by % of frame width and height), facing where, what each hand is doing, which frame edge every arm enters from, what the background is, how close the camera is⟩",
 "end_frame": "⟨the last frame, the same way⟩",
 "camera": {"height": "⟨eye level / above / below⟩", "distance": "⟨close-up / medium / wide⟩", "held": "⟨handheld at arm's length / held by someone else / set down still / screen graphic⟩", "move": "⟨none, or what it does and when: drift, push in, tilt, reframe⟩"},
 "moments": [
  {"t": ⟨seconds from the START OF THIS SHOT, one decimal⟩, "who": "⟨name⟩", "does": "⟨one visible action, in plain words: which hand, which direction, how fast, where it lands — e.g. \"right hand rises from the lower right edge and two fingertips land on her left cheekbone, slow\"⟩", "face": "⟨expression and where the eyes look, if a face is in frame⟩"}
 ],
 "on_screen": [{"t": ⟨seconds from shot start⟩, "until": ⟨seconds⟩, "text": "⟨the exact words⟩", "where": "⟨top / centre / bottom, and side⟩", "look": "⟨colour, outline, weight, case, how it appears: cut on / pop / type-on / fade⟩"}],
 "sound": [{"t": ⟨seconds from shot start⟩, "what": "⟨speech (who), music change, a sound effect named plainly, room sound⟩"}],
 "edit": "⟨how this shot begins and ends as an edit: hard cut, jump cut on the same framing, punch-in, zoom, transition, speed change — and anything moving that is not the people (a graphic, a zoom on a still)⟩"
}

Rules:
- `moments` covers the whole shot, in time order, with a new row every time
  something visible changes — a hand moving, a head turn, a look away, the
  camera moving. A still stretch is one row that says what holds still.
- Body geometry is said every time a limb is in frame: which hand, which edge
  it enters from, where the elbow is (in frame or out).
- Never describe what the video is "about" or why it works — only what
  happens, when.
