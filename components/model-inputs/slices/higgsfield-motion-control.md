# Genjutsu motion control — what it takes, and what works

*Rendered from `components/model-inputs/inputs/higgsfield-motion-control.json` (read 2026-10-27, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 3 to 30
- max images: 1
- max videos: 1
- image formats: jpg to jpeg to png to webp
- max image mb: 10
- min image edge px: 340 (Kling guide, video: short edge at least 340, long edge up to 3850); 720 on the ComfyUI door; 300 short edge on Kling's own character-image rule
- video formats: mp4 to mov to webm to m4v
- max video mb: 100
- reference video seconds: 3 to 30 (Kling); 30 only when the character follows the VIDEO, 10 when it follows the IMAGE (ComfyUI, Runway)
- output length: equals the reference video's length; if the motion is fast or complex it can come back shorter, never under 3 s of continuous motion extracted, and the credits are not refunded (Kling)
- resolutions: 480p to 720p to 1080p
- kling motion control: {'mode': ['std', 'pro'], 'background_source': ['input_image', 'input_video'], 'character_orientation': ['video', 'image']}
- output shape: comes back at the stills' own shape (834x1112, 3:4, from a 4:5 still): scale it back, never crop (a crop left the original caption peeking out) (ours, 18 Oct)
- price credits per second: Kling 3.0 Standard 9, Professional 12; Kling 2.6 Standard 5, Professional 8 (Kling's own door; Higgsfield bills in its credits)
- never send stems: master
- video seconds range: 3 to 30
- House: resolution 480p, upscaled locally; aspect 9:16 from the jump (the scene still is made 9:16, the swipe is 9:16); person the cast member's BASELINE built into a scene still (headshot, look, details, expressions); never the master (the owner, 2026-10-27); orientation video (follow the swipe's movement and camera)

## The prompt structure that works

- **Make the whole scene as ONE still first: the person, her room and the product in the frame. The motion model only moves what the still shows.**
- **The person in the still is built from the cast BASELINE (headshot, look, details, expressions), never the master.**
- **The swipe video drives only the movement: timing, gesture, expression and camera. The person, the room and the product do not come from it.**
- **Build the person inside the shot's own look (same pose, light, contact shadows, depth of field, grain); a studio sheet laid in reads as pasted on. The photo look is the swipe's, never cleaner.**
- **Match the still's framing to the video's: whole body with whole body, half body with half body, close-up with close-up. Same aspect on both.**
- **The still must show every limb the motion needs, arms and hands included, with clear space around the body for large movement.**
- **One continuous shot, one person, no cuts, camera movement or obstructions in the reference; if two people are present the larger is used. Cut the swipe at its cuts and run one shot at a time.**
- **Steady, moderate movement works best. Fast gestures smear in the source and again in the model: blur the source first and check fast hands in QC; use pro for a fast-hands shot.**
- **A prop is carried only if it is in the scene still, and the maker says face binding drops props, so check the product in every clip: whole, same size, not melted. If it did not survive, the product is laid in from the real photo at the edit.**
- **The result comes back at the still's own shape; scale it back to 9:16, never crop it.**
- **Check the face against the baseline before a clip is kept; motion control exists because object swaps kept the original face (9 of 9 swaps kept it, 9 of 9 transfers carried ours).**
- **Plan the blocking before the start frame: where the hands and the held props will move in the swipe. Product props sit on the side away from that path, and the motion words say for every prop the hands pass whether it stays in front of them or behind them, so nothing passes through a prop.**

## Avoid

- Building the still from the master instead of the baseline.
- A person built on a grey studio backdrop: it reads pasted on.
- Cropping the stretched output: the original caption shows at the edge.
- A reference video with cuts, shot changes or camera moves: it can be truncated.
- Overly fast motion or a subject whose body or head is blocked.
- More than one person in the reference: the largest in frame is used, not the one you meant.
- Expecting our spoken line from motion control: it copies the swipe's mouth and carries no audio of ours.
- Assuming a prop in the still survives the motion: the maker says face binding drops props; the product is checked in every clip and never drawn.
- Under 3 s of continuous motion in the reference: the run fails and the credits are not refunded.
- A close-up still with a full-body video (or the reverse), or mismatched aspect ratios.
