# Viewer cut — what someone scrolling would actually see (v1)

Below is a production brief for one {kind} ad. Turn it into exactly what a
person scrolling past it would see and hear, and nothing else.

Rules:
- Only what reaches the viewer: what's in the picture, what's heard (voice
  word for word, sounds, music), and on-screen text word for word.
- Strip every instruction to the maker: camera, lens, lighting, wardrobe
  notes, "film this", "if you don't have this", reasons, sources, frame ids.
- Write the picture the way a viewer would notice it, in a few plain words
  ("a woman holds a jar up to the bathroom mirror"), never the way a director would.
- Keep every detail the brief says will be visible: skin, marks, faces,
  the product and what it looks like, a reaction. Those are what a viewer
  stops for. Call the product what the brief calls it.
- Ignore any "Source:" line or reference to the original video — that
  describes the ad we copied, not this one.
- If the brief offers several openings, use the FIRST one, then the body.
- Keep the brief's own timing. A video is one line per beat, `0:00–0:02`.
  A still image or carousel slide is one line per image/slide, `[1]`, `[2]`.
- Copy every spoken line and every on-screen line exactly. Don't improve,
  shorten or explain anything.
- Add nothing the brief doesn't have.

Return JSON only:
{"length_s": <total seconds, 0 for a still>,
 "offer_at": <second the price, offer or ask first appears; for a still, the image number; null if none>,
 "caption": "<the post caption if the brief gives one, else \"\">",
 "lines": ["0:00–0:02  ...", "..."]}

--- BRIEF ---
{brief}
