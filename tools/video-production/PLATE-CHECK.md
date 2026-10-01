# The plate check

**Step 10 of the generation method, written out for video.** Every plate is
judged before anyone sees it, by measurement, and the numbers are written down
before the verdict. A hedge is a fail. A flagged plate is not shown.

This exists because on 2026-09-11 it was skipped: seventeen plates went to
Damon unjudged and he found the faults — a sterile room, blank bottles, a
tripod standing in the shop, the presenter in profile talking to a wall, and a
device with a competitor's wordmark rendered on it. Every one of those is
catchable by looking, and none of them should have reached him.

## The checks

Run every one on every plate. Write the observed value, not a pass mark.

| # | Check | What to write down |
|---|---|---|
| 1 | **Subject orientation** | front-on / three-quarter / profile / away. A presenter plate that is not front-on with eyes on the lens is a FAIL. |
| 2 | **Subject size** | roughly what fraction of frame height the subject occupies. A presenter under a third is a FAIL — the room has taken over. |
| 3 | **Filming equipment** | count cameras, phones, tripods, lights, mics visible. Anything above zero is a FAIL. |
| 4 | **Rendered text** | quote every word legible in frame. Any wordmark or brand name on our product is a FAIL — those are composited. |
| 5 | **Third-party brands** | name any competitor brand visible on our product or in a hero position. Any is a FAIL. |
| 6 | **Product geometry** | against the reference: silhouette, handle or none, bristle face, base. Any mismatch is a FAIL. |
| 7 | **Anatomy** | count hands, fingers on each visible hand, limbs. Anything impossible is a FAIL. |
| 8 | **Continuity** | does the scene's `Hold:` line still hold against the plate it follows? |
| 9 | **Physical sense** | say out loud what the object is doing, then check the picture agrees. A device working on skin shows the side that is NOT touching it. Anything the picture could not actually do is a FAIL. |

## The rules behind them

- **The reference carries the material; words carry subject, action, framing.**
  A product described rather than attached comes back as a different product.
  This is rule 1 of the generation method and it is the one most often broken.
- **Never ask for a legible label.** Ask for a plain surface. The wordmark is
  composited from the real asset at build. A generated wordmark is either
  wrong or it is a competitor's.
- **Never name camera equipment.** It becomes an object in the room.
- **A working object is seen from its other side.** If the bristles are on his
  cheek, the camera sees the smooth back and the wordmark — not the bristle
  face. The 360 reference has every angle; name the one the action implies
  rather than defaulting to the hero view. Damon caught this one after the
  geometry was already right: correct object, impossible orientation.
- **The presenter is the subject; the room is behind her.** A long world block
  in a prompt makes the room the subject and puts the person in the corner of
  it, in profile.

## What happens to a failure

Fix the prompt, not the picture. Re-roll. A plate that fails twice on the same
check means the prompt is wrong in a way re-rolling will not fix — change one
thing, and only one, so the next result says which change did it.
