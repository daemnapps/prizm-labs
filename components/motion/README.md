# motion

The motion chain: how every AI clip gets its movement. Real footage of the same action is found, tracked, read as
body mechanics and rehearsed in 3D by the real skeletons, on stand-ins shaped to the cast's own bodies, with the real camera; the chain then passes or holds that
motion on its own checks before any paid take (nobody approves it), and the finished take is checked against the
reference beat by beat.

Owner: the owner


```
python3 components/motion/motion_chain.py run <scene dir> --brand <brand> --framemap <framemap.json> --source <swipe.mp4> --span 0-15
python3 components/motion/motion_chain.py decide <scene dir>
python3 components/motion/motion_chain.py ours <scene dir>                 # our beats on the reference's timing and camera
python3 components/video-studio/take.py scene <scene dir> [--dry-run]     # inject, motion, start picture, review, take, checks
python3 components/motion/motion_chain.py check <scene dir> [<take.mp4>]
python3 components/motion/motion_chain.py status <scene dir>
```

A reference is used for its timing and its camera. When it does not show what our beats do (the read's `missing`),
its skeletons are not used: the rehearsal is programmed from our beats on its timing and filmed by its camera (`ours`),
and an override cannot pass the reference's own moves in place of ours (2026-11-15). A scene injected by production
(`components/video-studio/production_inject.py`) carries our own movement and camera instructions; `direct` renders
them as the rehearsal and no reference skeleton is used at all.

Details, the stages and the files each writes: `CLAUDE.md`.
