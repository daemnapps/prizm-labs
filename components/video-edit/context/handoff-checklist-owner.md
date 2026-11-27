# Video Hand-off Checklist (team copy)

Page: https://claude.ai/artifact/3oBcATgzNZJDUjUUSpdkFH · source `handoff-checklist-owner.html` · 2026-11-25

## What was wrong (0333)
1. The product's casting sheet was in the hand-off folder and on none of the 17 clips. Cast sheets were named, not attached. Only song ads attached files.
2. The brief wrote the product out of the shot (V58 photoreal: laid on at the edit), so start pictures said "grip left open for" / "space left clear", and the model drew an empty hand.
3. Clip recipes carried the swipe person's action on the swipe's own product.

## What changed (VIDEO-RULINGS V59)
- `video-edit/maker/scene_packet.py`: one packet per clip, every format; from the brief's per-shot `subjects` and `start_picture`. People, product sheet, place, props, look as files; one start-picture prompt, one clip prompt, files by number. The product's sheet is sent with the clip too (Seedance reference-to-video). Texture-only shots carry no pack. No box sheet: the product itself is held.
- `handoff_check.py`: two new checks; a clip with a person, product or words missing holds the pack.
- Writing: photoreal and unknown styles bind `in-scene` (product in the made shot, from its sheet); `in-look` unchanged.

## Not done
- Live hand-offs are unchanged until the owner says refresh. No clip has been generated with the new packets yet.
- Places and props with no banked picture are still built from the brief's words or the swipe's frame.
- 0377 S16 (two clips) and 0378 S6 are held; 0377's words reserve a spot for texture and 0378 S6 is held on purpose: its place text still says an area "remains clear for the later product".
