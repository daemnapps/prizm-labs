# Product layer: the real product on skin, in a video

A product that is applied to the face or body is never drawn by a video model. The take shows the person and the
hand; the product comes from its own 3D kit and is laid into that hand by `product_layer.py`.

## In the finished chain

Step 8 of 9 (write the take → cast sheets → first frame → voices → motion → print → voices on → **product on skin** →
check): whenever the product touches skin, it runs on the printed take, after our voices are laid on and before the
check.

```
python3 product_layer.py step take.mp4 --kit runs/ai-elements/<brand>/products/<product> --beat 1.8,5.0 \
    --stand-in green --side left --out take-product.mp4
```

In: the printed take with our voices on, and the beat (seconds) where the product is used. Out: the same take with
the real product on the skin through the beat and the take's own sound kept; the stages' files (`track.json`,
`path.json`, `check.mp4`, `step.json`) sit beside it in `<out>-product-layer/`. `step.json` says how many beat
frames carry the product; any beat frame without it (no stand-in, no hand) is a miss for the check. Outside the
beat the picture is the take's own, except where a keyed stand-in still shows: it is always covered. Without
`--plan`, the path is circles along the jaw for three quarters of the beat, then up the cheek.

## How it is held (owner, 9 Nov)

- **Locked to the hand.** Once the hand grips the device it is one rigid object with the hand: it moves and turns
  only with the hand. No sliding, no re-orienting mid-hold, no shake from frame to frame. A hold is a run of frames
  in one grip (loose in the open palm, or held to the skin).
- **The grip pose is fixed once,** at the start of each hold, from the stand-in's own axis in its first clearly read
  frames: how the device sits, its lean toward the lens, and where it sits against the stand-in. The stand-in's
  narrow end is the tip, so where the stand-in lies on its side in an open palm the device lies on its side there
  too. Which end is the tip is voted once for the clip.
- **Carried on the hand.** Through the hold the device turns with the hand's turn in the picture (wrist to middle
  knuckle) plus that fixed offset, and moves with the stand-in the hand holds, steadied over a few frames. The
  tracker's depth for each knuckle is too unsteady to turn a device by, so its lean toward the lens stays as it was
  at the grip. The offset may drift only slowly, over about two seconds, where the take's hand and the thing it
  holds part ways (a generated hand is not a rigid body); never frame by frame.
- **Re-grip.** Where the take moves the stand-in from one grip to another (open palm into the fingers), the device
  turns from the first grip to the second over a third of a second.
- **Flush on the skin, where the stand-in is held.** On the skin the device sits where the stand-in sits in the
  fingers, its body a little toward the palm so its tip shows above them, its bristle face flat on the skin: it faces
  the way the skin faces round the contact (the face mesh, over a wide patch), so on a jaw or a cheek turned from the
  lens it is seen near side-on, as in the brand's own footage of it in use. It is not laid flat with its back square
  to the camera.
- **Lit by the room.** Besides the key read off the skin, the room round the person (the frame's upper part, its
  brighter half) lights it from all round and from behind, so its satin shell catches a thin edge highlight the way
  the real one does; its edges are softened to the footage's own focus (read from the frame's fine detail).
- **Fingers on top.** The fingers in front of it are the take's own pixels, fingertips and nails included: the hand
  is cut out by a body-skin segmenter (MediaPipe's selfie multiclass model, which tells hand skin from face skin),
  kept to the area round the tracked hand. No shadow or grade lands on the fingers.
- **Steadiness check.** `jitter.json` beside every run gives, for every held frame, how far the device turned and
  moved since the last frame, how far the hand did, and its shake (how far it sits off the line through the frames
  either side). While held, shake reads close to zero and the device turns about as much as the hand. On the 5 s
  test (120 held frames): turn 0.3° a frame at the median against the hand's 0.13° (2.2° before the lock); shake
  0.45 px and 0.05° at the median, worst 2.7 px (1.15 px, 0.65°, worst 16.4 px before).
- **The bar:** executed with finesse. A device that slides, re-orients or shakes in a still hand, a finger dimmed or
  covered, the device standing when the stand-in lies, or its back laid flat to the lens is a miss at the check.

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
5. **Composite.** `product_layer.py comp`: the hand stays in front (its own pixels, cut out by the body-skin
   segmenter inside the area round the tracked hand; without the segmenter, a shape drawn from the hand's 21
   points; wherever the stand-in shows, the hand is not in front), any stand-in left uncovered filled from round it and its colour cast taken off the fingers, a soft
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
- The segmenter works at 256×256 and is scaled up, so a finger's edge can be a pixel or two soft at 720p.
- The light is one key and one fill read off the skin; a hard coloured light or a strong reflection on the product
  is not matched.
