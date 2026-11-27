# The cover's two pictures: the video frame is the composition, the set print is the cast and the room

The reference clause of a cover (purpose `cover`, the cover job in `image_production/covers.py`). It replaces the edit
clause ("keep the attached picture exactly as it is"), which returned a redraw of the set print for every version.

v2 (2026-11-12): v1 asked for "the same people in the same places, the same framing" as IMAGE 1, which contradicts the
word-space rule when a face in the frame sits inside the word band. v2 keeps the moment and moves faces, lips and hands
out of the band. Not yet run against v1 on real pictures.

A cover starts from the strongest frame of that version's own video. The filed 3D set print still decides who the
people are and what the room is, so no people picture is made without a filed set.

Slot: `{print_line}` is the sentence about the set print; it is left out when the set gate is rolled back for the lane
and no print rides along.

The frame keeps its moment but not a face in the word band: the band is named by the cover-word-space rule, and the job
reads the faces on the delivered plate (gate.cover.faces) and marks a cover with a headline on a face not fit to file.

---

IMAGE 1 is a frame of this ad's own video. It is the composition: the same moment, the same people and the same
camera angle. Start from it. Keep its framing, except that any face, lips or hands inside the band kept clear for the
words move out of that band: shift or reframe the people so the band holds none of them. {print_line} Any further pictures are the cast's own sheets: every
face matches its sheet. Then change what the direction above asks for, and push that one thing as far as the direction
says. It is a new picture of that moment, never a copy of IMAGE 1 and never a redraw of the set print.
