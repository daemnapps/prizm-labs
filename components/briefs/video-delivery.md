# Video versions and thumbnails — delivery instructions

Every finished video brief includes its control, every opening/variation requested in the brief, and one distinct thumbnail (cover) for each finished version. Two revisions of the control do not replace requested variations. Creative changes to words, hooks, scenes and variations are welcome; record which required slot each alternative fulfills. Keep product and offer facts accurate. Read `DELIVERY-CHECKLIST.md` for the mandatory acceptance gate and revision process.

## 1. List the deliverables before production

Read the whole brief, including its openings/hooks and each **Thumbnail** direction. Write a checklist with one row per requested version: version name, opening, thumbnail moment, chosen thumbnail words, video filename, cover filename and cover record. Missing opening clips are work to produce through the selected video route, not permission to omit a variation. If the brief has no version list or no thumbnail direction, record that gap before production; do not silently assume control-only.

## 2. Finish every requested version

Make and review the control and each requested opening, then render each complete video. Match the checklist to the renders. A cover is made from the final render of its own version, so rerendering that version requires checking its cover again. For creator/founder filming assignments, return raw takes through the filming manifest; the video editor owns this final-video and cover checklist after editing.

## 3. Make one thumbnail per finished version

Use the brief's thumbnail direction or a documented creative alternative. Use a real frame from that version's finished video and record its timestamp; the frame is a reference, not the finished thumbnail. Select the cover swipe from the avatar's indexed covers and retain its id and rated move. Keep the ad's cast, product and filed set references.

- **Video Studio:** carry the brief's per-version headline, moment, swipe and direction into the production's `brief.json` `covers` fields. Run `python3 components/video-studio/covers_stage.py run <production>`, then `state <production>`. Resolve each held version. `file-args <production>` supplies the matched videos, thumbnails and records when the entire set is ready.
- **Other editing routes:** use the same image-production cover job, `python3 components/image-production/make.py covers --job <job.json> --dry-run`, then remove `--dry-run` after resolving its findings. One job contains all versions. Each version names `version`, `headline`, `frame`, `video`, `t`, `swipe` and the brief's visual `direction`; the job names `brand`, `ad`, `out`, the filed `set` and the required product/cast references. Follow `components/image-production/CLAUDE.md` under Covers for the complete schema and current requirements. Do not substitute a screenshot, editor export or Meta's automatic frame for the image tool's delivered cover.

**By hand (editor's choice):** the editor may instead supply their own thumbnail for any version. In `submission.json` set `"cover_manual": true` on that item and give the `cover` file and its `cover_sha256`; no swipe, frame or cover record is needed and the tool-made check is skipped for that cover. It must still be a 9:16 picture, 1080+ wide, under 10 MB, and different from the other versions' covers.

## 4. Check the whole set

Each cover must match its own video, follow its recorded swipe and brief direction, preserve the cast/product, and keep the chosen words clear of faces and interface areas. Deliver 9:16 covers at least 1080 pixels wide and under 10 MB. The image-production checks must pass; sibling covers must be visually distinct. Keep the tool's original cover and provenance files together. An unread check is unresolved, not passed.

## 5. Return videos, covers and records together

In this handoff's `returned/`, name the videos `<brief-key>-control.mp4`, `<brief-key>-v1.mp4`, etc., matching the brief's checklist. Return each matching `<brief-key>-<version>-cover.png` (or the tool's delivered JPG), its `.cover.json`/recipe records, and the tool's `run.json`/`covers.json` in that version's subfolder. Preserve provenance when copying; do not recreate or edit the cover after generation. Include the completed checklist mapping every requested opening to its video, cover and record. Name missing items explicitly; a partial return is not the completed brief.

Submit the completed current-revision checklist with `python3 components/briefs/delivery_contract.py submit <handoff-folder>`. It files all finished versions as **one** approval card, with videos, thumbnails and cover records in checklist order. The Studio supplies these through `covers/to-file.json`. Check that every video and its cover appears on that card. Filing is for review; only the owner's approval launches an ad.
