You are checking a rehearsal before any video take is paid for. The attached clip has three panels side by side, all
showing the same instant: LEFT is real footage, MIDDLE is its tracked skeleton, RIGHT is a 3D rehearsal: plain stand-in
figures moved by that skeleton and filmed by the tracked camera. The rehearsal will be given to a video model as its
motion reference, so a fault in it is a fault in the take.

The stand-ins are deliberately plain: no faces, clothes, hair or props, a ball for a head, mitten hands, each a
different colour. Never mark those against it. Judge only where the stand-ins are, how big they read in the frame, and
how they move.

The clip runs {seconds} seconds{cuts}. Who is in our shot: {people}.
What the measured rows already say failed (do not repeat them; look for what they miss): {failed}

Watch it shot by shot and compare RIGHT with LEFT:
- People: the same number as the people who do something in the footage. A background person who only stands still and
  has no stand-in is a small fault.
- Place and size: each stand-in where its real person is (left or right, near or far), and about as big in the frame.
- The move: the one thing that happens in the shot (a lean in, a pull back, a turn of the head, a kiss, a hand going up,
  a squat) happens in the rehearsal too, the same way round, at the same moment.
- Limbs: nothing a real body cannot do. No arm or leg thrown across the frame, no limb appearing or vanishing between
  two frames, no figure floating, sunk in the floor, sliding or spinning, no limb through another body.
- Cuts: nothing jumps in the three frames either side of a cut that does not jump in the footage.

Give back JSON only, in exactly this shape:
{"shots": [{"shot": 1, "from": 0.0, "to": 2.7, "people_footage": 2, "people_rehearsal": 2, "placed": true, "sized": true,
            "move_matches": true, "limbs_plausible": true, "saw": "one line: what happens here and whether the rehearsal does it"}],
 "faults": [{"at": "1.3-2.2 s", "what": "what is wrong, in one plain sentence", "matters": "a lot | somewhat | barely"}],
 "verdict": "true to the footage | close, small faults | not yet",
 "summary": "two plain sentences: what is right, what is still off"}

How to decide the verdict:
- "not yet": a person who does something in the footage has no stand-in; or the shot's one move does not happen, or
  happens the other way round; or a fault that matters a lot lasts longer than half a second.
- "close, small faults": everyone who acts is there and every move lands, with faults that are short or small.
- "true to the footage": nothing a viewer would notice.
"matters a lot" is for a fault a video model would copy into the take as something the footage never shows.
