# Aspect Ratio Resize

Page: (team page)

Any picture in, whatever its shape; a 9:16 asset out. The picture is never
cropped, stretched or redrawn, and it always sits inside the middle 4:5 window
that feed placements keep (`the team notes/SAFE-ZONE.md`). Only the space around it
is painted, continuing the background. Ruled by the owner 2026-09-22 (every asset
9:16, content in the 4:5 zone) and 2026-09-29 (any ratio in; a core step of
image production, always done).

## How it works

1. The picture as it came in. Nothing about it changes from here on.
2. Placed inside the safe zone: set into a 9:16 frame, as big as it fits
   inside the centred 4:5 window (`providers.zone_box`).
3. The model paints only the empty space: it gets the picture and a mask that
   lets it touch the empty space and nothing else (GPT Image edit door).
4. The original pasted back on top at the exact box, so the picture is
   provably the one that came in. Delivered at 1080x1920.

## Where each shape lands

| In | Result |
|---|---|
| 4:5 | fills the zone; top and bottom painted |
| 1:1 | full width; more painted above and below |
| 16:9 | full width; most of the frame painted |
| 2:3 | zone-tall; sides painted too |
| 9:16 | left alone |

## The instruction the model gets (verbatim)

Top and bottom only:

> Extend this picture upward and downward. The visible picture is finished and must not change in any way. Paint only the transparent areas: continue the same backdrop — the same surface, the same light, the same colour and grain — seamlessly, with no edge, no band and no change of tone where it meets the picture. Put nothing new there: no object, no word, no logo, no shape, no person. Background only.

Every side (new 2026-09-29, used when the picture is taller than 4:5):

> Extend this picture outward on every side where it is transparent. The visible picture is finished and must not change in any way. Paint only the transparent areas: continue the same backdrop — the same surface, the same light, the same colour and grain — seamlessly, with no edge, no band and no change of tone where it meets the picture. Put nothing new there: no object, no word, no logo, no shape, no person. Background only.

## How to trigger it

Say "these aren't 9:16", "resize to 9:16", "make this 9:16" or "aspect ratio
resize" and point at the picture or folder (skill `resize-9x16`). Inside
image production it happens on its own: every `ad` and `video-still` leaves at
9:16. The Higgsfield-side copy of the skill is `tools/image-edit/skills/resize-9x16.md`.

## Runs

| Date | What | Pictures | Where |
|---|---|---|---|
| 2026-09-29 | Face Scrub statics that came in at 4:5: P167, P169, P174 (Final), P176 (Final), P177, P178, P179, P180 | 27 | Team Drive / Higgsfield Outputs / Face Scrub Static Ads / P### / 9x16 / |

## Inside Higgsfield (tested 2026-09-29 on P178)

| Tool | Result |
|---|---|
| Plain Outpaint (`outpaint_image`) | FAILS: zooms out and redraws the scene smaller; headline lands on the edge of the zone. Never used for statics. |
| FLUX.2 Pro Outpaint (`flux_2_pro_outpaint`) | WORKS: exact pixels per side, picture lands in the zone, not redrawn. 4:5 and 2:3 both right. About 5 credits a picture. Refuses large files, so the picture goes in at 1080 wide. |

The Higgsfield copy of the skill: `tools/image-edit/skills/resize-9x16.md`.
What a designer pastes into Higgsfield once:

> Pull this skill from our GitHub and save it as one of my skills, named resize-9x16:
> https://github.com/brand-d-team/workspace/blob/main/tools/image-edit/skills/resize-9x16.md
>
> Follow it exactly whenever I say "these aren't 9:16", "resize to 9:16", "make this 9:16" or "aspect ratio resize". Use FLUX.2 Pro Outpaint with the numbers the skill gives. Never the plain Outpaint tool, never crop, never add bars. Then show me it working on the image I attach.
