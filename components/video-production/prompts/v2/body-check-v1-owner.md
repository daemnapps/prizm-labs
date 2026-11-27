# Body check — v2 (count the limbs, size the hands; nothing else)

v2, 2026-10-28 (a take the clip judge passed had a third arm and an oversized hand). The judge scores a whole take and
misses a body that is wrong; this check looks at ONLY the bodies, frame by frame, and any failure stops the picture or
the take.

You get one or more frames of the same picture or video. For EACH person in the frames:

1. **Arms.** Count every arm you can see that belongs to that person, including a forearm or wrist alone (a bangle on a
   wrist is a wrist). Group connected segments into complete arms, allowing normal elbows and occlusion. A person has
   at most 2. A wrist, hand or forearm that cannot be
   connected to a plausible bent arm is suspicious, but occlusion alone is NOT an extra arm. Elbows bend: a horizontal
   forearm at waist height can connect to a vertical upper arm. Do not count upper arm and forearm as separate arms.
   Sleeves, torsos and foreground props can hide the elbow or upper arm. A forearm need not point directly at a shoulder.
2. **Hands.** Count every hand. At most 2 per person. Fingers: 5 per hand where the hand is clearly visible.
   A rounded or pointed bent elbow is NOT another hand: identify a palm or fingers before calling it a hand.
   Realistic anatomical teaching props and mannequin parts are objects, not additional limbs of the presenter.
3. **Hand size.** Compare each hand to the same person's face. A real adult hand, wrist to fingertip, is about as long
   as the face from chin to hairline. A hand clearly bigger than that (half again or more) is oversized. Perspective is normal: a hand nearer the camera than the face (reaching toward the lens, working at a counter close to the camera, a close-up of the hands) looks bigger and is NOT oversized. Only a hand at the same distance as the face that is far too big is oversized.
4. **Fused or melted.** A hand whose fingers have NO edge where they meet something: they melt into an object, the clothing or the other hand, or turn into a shapeless blob. Holding, gripping, pinching, pressing or touching an object is NORMAL and never fused, even when fingers overlap or hide behind it.

Ignore everything else: the room, the props, the light, the acting.

First trace, then count. For every hand, identify the wrist, forearm, possible bent elbow and upper arm. A robe or
large foreground prop can hide part of that chain. Assign plausible left/right arms through that occlusion. A hand
resting near the waist does not originate from the waist merely because its forearm is horizontal. Count an EXTRA
arm only with positive visual evidence: three distinct arms/hands present simultaneously, two incompatible complete
limb chains from one shoulder, or a clearly detached/duplicated limb that cannot be explained by the two normal arms.
In each problem identify the concrete visible duplicate and frame; do not turn "I cannot see the hidden elbow" into
a third arm. Assess actual finger boundaries, allowing normal grip contact and overlap with an object.
For a claimed third arm, describe all THREE separate limb chains and their visible endpoints. Naming only
"an extra arm at the edge" without distinguishing it from the bent elbow of an already counted arm is insufficient.

Reply with JSON only:

{"hands": [{"frame": n, "where": "plain words", "traced_to": "left | right | neither"}],
 "ok": true or false, "people": [{"arms": n, "hands": n, "oversized_hand": true or false, "fused": true or false}],
 "problems": [{"frame": n, "what": "plain words: what is wrong and where"}]}

`ok` is false when any person has more than 2 arms or 2 hands, any hand is oversized, or anything is fused or melted.
