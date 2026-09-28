# Frame control — the editor's guide (v2, 2026-09-28)

> For the video editor: every move behind the music-video edit,
> what it fixes, how much control you have over it, and
> where to do it — locally with `framectl.py`, or in Higgsfield.
> Damon, 2026-09-28: "my editor understands the level of control that he
> actually has … save a lot of time if he can do a lot of this stuff locally
> as well and use Higgsfield as needed."

**Split of work:** Damon — research, creative strategy, briefs, funnels.
Editor — execution: the cut, the finish, the fixes below.

## The rule that saves the most time — chained clips

**Generate in order. Each next clip's start image is the ACTUAL last frame of
the clip before it** (`framectl.py lastframe`), never the still it was aimed
at. Start/end-frame video models (Seedance, Kling) do not land exactly on the
images they are given, so a join built from the stills jumps (tens of times a
normal frame step). Check every join with `framectl.py seams`:
**pass = the jump is ≤ 2× the clips' own median step.** A join that fails is
re-made from the real last frame. The flow bridge is the fallback only.

## The moves

| Move | What it fixes | Your control | Local | In Higgsfield |
|---|---|---|---|---|
| **Clean** (dedupe + interpolate) | stutter: AI clips at 24 fps padded to 30 repeat every 5th frame | target fps | `framectl.py clean in out --fps 30` | upscale/interpolate tools where offered; else run locally |
| **Chain from the real last frame** | jumps between generated clips | which frame, which clip order | `framectl.py lastframe clip.mp4 last.png` → use as start image | Seedance `start_image` = that frame; end_image = the next still |
| **Seam check** | invisible bad joins | the pass line (2×) | `framectl.py seams a.mp4 b.mp4 …` | — (local) |
| **Flow bridge** | a join that still jumps and can't be re-made | k frames each side (default 10) | `framectl.py bridge a b out --k 10` | — (local) |
| **Continuous clock** (slow-mo dips, never freezes) | "gets stuck": frozen holds read as broken | where, how wide, how deep (≤0.8) | `framectl.py retime in out --slow 3.2:0.3:0.6 --push 0.05` | speed ramps in the editor |
| **Push-in** | a static frame dies | how far (0.05 = 5% over the clip) | `--push` on retime | camera move in the prompt |
| **Kick surge** | flat, syncless energy | per beat, width, depth | `framectl.py surge in out --beat 1.4 --beat 2.6` | no equivalent — bake into the prompt or run after |
| **Outfit blend** (the look swap) | a hard cut between two takes of the same motion | when, how wide | `framectl.py blend a b out --at 1.5 --width 0.4` | Genjutsu makes the second take; this blends the two |
| **360° spin** with radial + motion blur | a whip-pan/turn shot at one shutter speed | when it locks, how long, the bounce | `framectl.py spin in out --lock 1.4 --dur 0.9` | motion presets give the turn, not the blur — run this after |
| **Eased flick-scroll** | a scroll timed by the clock, not by distance moved | the span, the hold | `framectl.py flick in out --from 4.0 --to 6.0` | no equivalent — screen-recording move, always local |
| **Pull-back into the screen** (run in reverse: push into it) | a push into a frame-within-frame that doesn't land exactly | the tracked rectangle, the landing frame | `framectl.py pushinto in out --corners … --land next.png` | a real 3D camera move is the production route; this is the 2D, locked-off version |
| **Seamless loop** | a loop that visibly jumps at the repeat | how many frames blend at the wrap | `framectl.py loopcheck in` then `loopclose in out --k 8` | no equivalent — runs on the finished render |

## What the music video used

- **The music video (Carousel):** a fractional source clock (every output frame
  sampled between source frames and flow-tweened), kick-drum surges, outfit
  blends, a 360° spin with radial and motion blur locking onto the snare, an
  eased scroll whose timing follows distance, a pull-back into the screen with
  smootherstep easing, and a seamless loop (the last frame is the first).

The original production scripts are private. Every move above is `framectl.py`'s own
brand-free rewrite of the underlying technique — same math, no copied code,
proven on real music-video clips.

## The breakdowns (for the call)

- `MOTION-VOCABULARY.md` — the visual dictionary: 57 editing and motion
  terms, 39 shown on real moments of the finished video.
- `breakdowns/` — three AI reels reverse-engineered frame by frame (how the
  humans were made to move, the tools, inputs and outputs, what reads fake vs
  real) plus the findings.
  - Reel A `DdrtGPgIzXA` · Reel B `DdpRowAM42r` · Reel C `DdntUJEOUL6`

## Setup (the editor's machine)

`ffmpeg`, and Python 3.12 with `numpy` and `opencv-python` (opencv has no
wheels yet for Python 3.14 — give the kit its own Python 3.12 environment).

    python3 framectl.py <command> …
