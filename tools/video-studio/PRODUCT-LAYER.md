# Product layer: the real product on skin, in a video

A product that is applied to the face or body is never drawn by a video model. The take shows the person and the
hand; the product comes from its own 3D kit and is laid into that hand by `product_layer.py`.

## The method

1. **Make the take with a stand-in.** The take is written so the hand holds a plain stand-in of the product's shape
   and true size in one flat keyable colour (for an egg-shaped device: "a plain smooth matte bright green egg-shaped
   pod, as big as his palm (about 11 cm tall), narrow end up … one flat bright green colour with no marks, like a
   green-screen prop", the grip written out). The stand-in gives the grip, the fingers wrapped over it and the
   contact with the skin; its colour lets the tool find it exactly and remove it. Run with `--stand-in green`
   (or `blue`, `magenta` when the shot holds green).
2. **Track.** `product_layer.py track`: the face mesh (MediaPipe Face Landmarker, 478 points, with the head pose),
   both hands (Hand Landmarker, 21 points) and the keyed stand-in (centre, long axis, length) on every frame. Named regions: `jaw_right`, `jaw_left`, `chin`,
   `cheek_right`, `cheek_left` (the subject's own sides).
3. **Plan the path.** `plan.json` says what the product does on the beat (circles along a region, a sweep from one
   region to another, a hold). Every path point is a mix of mesh points, so it rides the face as the head moves.
   With `"follow": "hand"` (the default) the product rides the stand-in (or, with none keyed, the holding hand):
   pressed to the skin when it is on the face, carried in the palm when it is not, one hand for the whole clip. Its
   roll is read from the stand-in's long axis only when that is clearly egg-shaped and whole in the picture. The plan is then the motion written
   into the take and the yardstick: each frame records how far the hand strayed from it (`drift`, in face widths).
   `"follow": "path"` keeps to the plan exactly; it is only right when the take itself was driven by the plan.
4. **Render.** `product_layer.py render --kit <product kit>`: the kit's own model (`model/render3d.json`), at its
   true size against the face's width, pressed flat on the skin (the face's local surface, leaned toward the way the
   face looks), the fingers' direction setting its roll. The light is read off the clip: the side the key comes
   from (fitted from the skin's brightness against which way it faces), the key's colour from the skin's brightest
   part, the fill from the frame. Blender EEVEE, transparent frames, motion blur. About 0.3 s a frame on this Mac.
5. **Composite.** `product_layer.py comp`: the hand stays in front (palm and the four fingers as one shape, the
   thumb on its own so the product shows between thumb and fingers; wherever the stand-in shows, the hand is not in
   front), any stand-in left uncovered filled from round it and its colour cast taken off the fingers, a soft
   contact shadow, the product's body
   brought to the level of the clip's own blacks, the clip's white balance and grain. Writes `layered.mp4`,
   `side.mp4` (take | layered) and `check.mp4` (mesh regions, the planned path, the hand, where the product sits).

`product_layer.py run <take.mp4> --kit <kit> --plan plan.json --stand-in green` does all five steps. The kit is a product folder of image production (`runs/ai-elements/<brand>/products/<product>`, with `kit.json` and `model/render3d.json`). Runs on any Python with mediapipe, opencv and numpy (the video-edit venv has them) and Blender.

## What holds and what breaks

Measured 9 Nov 2026 on Wan 3.0 takes (Higgsfield, 720p, 5 s, from a cast member's start frame) and on real clips.

| Case | Result |
|---|---|
| Green stand-in, one hand, close-up | Holds. Stand-in found in 134 of 150 frames (the rest: before the hand comes in). No green left after the composite. Fingers sit in front, the product's back (wave ridges, base light line) faces the camera, at true size. |
| Moving 3× faster (the same take sped up) | Holds. Face mesh 52 of 52 frames, frame-to-frame jump at most 0.06 face widths; the hand tracker lost 11 of 52 frames, which does not matter while the stand-in is keyed. |
| Head turned past about 50° | Breaks. The face mesh is lost on 1 frame in 3 past ~50° of turn; those frames hold the last face, so the product sticks in place while the head moves. Keep the turn under ~45° while the product is on the face. |
| Both hands crossing the face | Breaks. The mesh is lost on 1 frame in 4 and jumps up to 0.57 face widths when it comes back. One hand on the face holds; two hands over it do not. |
| Empty hand, motion written | Breaks. The model opens the hand flat, swaps hands mid-take, and does not do the written circles; a flat hand leaves the product nowhere to sit. |
| Stand-in the product's own colour (black) | Breaks on a dark beard or dark clothes: the stand-in cannot be told from them, and the hand alone does not say where the product sits (the fingertips hold it, not the palm). |
| Written path vs the take | The model follows the written beats only roughly: on the green take the hand was a median 0.16 face widths (about 2 cm) from the planned circles, at most 0.49. The product follows the hand, never the plan, so it always stays in the hand; the plan is the motion written into the take and the yardstick. A take that has to hit the path exactly needs the path driving the take (tracked motion), not words. |
| A stand-in seen round (a ball in an open palm) | Its roll cannot be read; the product stands upright in the palm until the stand-in is clearly egg-shaped again. |

## Cost and time

- The take: 8.75 Higgsfield credits for 5 s at 720p on Wan 3.0 (about $0.40 at the house rate of 20 credits for $0.90).
- The layer: local and free. A 5 s clip at 720×1280 runs in about 75 s on this Mac (tracking ~20 s, rendering 150
  frames ~20 s, compositing ~30 s).

## Worked example

`plan.json` for a 5 s take, the product on the subject's left jaw and cheek:

```json
{"beat": {"seconds": [1.8, 5.0]}, "follow": "hand", "side": "left",
 "moves": [{"do": "circles", "region": "jaw", "beats": 3, "circles": 3, "radius": 0.06},
           {"do": "sweep", "from": "jaw", "to": "cheek", "beats": 1}]}
```

```
python3 product_layer.py run take.mp4 --kit runs/ai-elements/<brand>/products/<product> --plan plan.json --stand-in green --out work/
```

## Known limits

- The camera is orthographic: the product keeps one size across the frame. Right for a selfie close-up; a product
  that travels toward or away from the lens needs a perspective camera.
- The hand mask is drawn from 21 points, so finger edges are approximate (soft, a few pixels wide). A segmentation
  model would cut them exactly.
- The light is one key and one fill read off the skin; a hard coloured light or a strong reflection on the product
  is not matched.
