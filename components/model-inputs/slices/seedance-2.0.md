# Seedance 2.0 — what it takes, and what works

*Rendered from `components/model-inputs/inputs/seedance-2.0.json` (read 2026-10-28, status draft) by `input_rules.py render`; never hand-edited.*

## Limits

- duration seconds: 4 to 15
- aspect ratios: 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 or adaptive (a fixed list, not 2.5's free 0.4 to 2.5 range)
- max images: 9
- max videos: 3
- max video seconds total: 15
- max audio clips: 3
- max audio seconds total: 15
- max references total: 15
- best references total: 4 to 5
- stable people max: 4
- resolutions: 480p to 720p to 1080p to 4k
- resolutions fast and mini: 480p to 720p
- output format: mp4 (4k comes out 10-bit H.265)
- audio needs a picture or video: True
- real faces blocked: reference pictures or videos with a real human face are refused by the maker's moderation unless they are the account's own model outputs, the maker's preset characters or authorized portrait assets
- price: UNCONFIRMED, USD, maker's direct price: a 5 s clip with no video input 0.35 at 480p (about 0.07 per second), 0.76 at 720p, 1.87 at 1080p; fast 0.28 at 480p. Billed in tokens = (input video seconds + output seconds) x width x height x frame rate / 1024, so a reference video raises the cost. Read from a search summary of https://docs.byteplus.com/docs/ModelArk/1544106, which could not be opened directly. Higgsfield's credit price is not in the local catalogue (base_credits 0.0000).
- audio clip seconds: 2 to 15
- audio clip mb: 15
- audio formats: mp3 to wav
- image formats: png to jpg to jpeg to webp
- max image mb: 30
- unconfirmed: (1) audio_clip_seconds (2 s minimum per clip), audio_clip_mb, audio_formats, image_formats and max_image_mb come from reseller pages, not the maker's own page; (2) max_references_total: the maker lists 0-9 images, 0-3 videos and 0-3 audio, one reseller caps all files at 12 together; (3) whether Higgsfield's 2.0 reference-to-video lets a first/last-frame role sit beside audio (the 2.5 door refuses it with a 422); (4) whether a supplied voice track is lip-synced word for word: the maker says audio passes on its timbre, melody and dialogue content, and its examples type the line in the prompt with the voice taken from Audio n.
- House: resolution 480p, upscaled on this Mac (same as 2.5); aspect 9:16; duration 4 to 15 s, the model's own range; a talking take longer than 15 s must be split
- On the maker's API, a first_frame / last_frame role is its own task type (image-to-video); inside a reference task a picture called 'the first frame' in the words is followed approximately. Text + audio alone, or audio alone, is refused.

## The prompt structure that works

- **Name every file as type + number in upload order ('Image 1', 'Video 2', 'Audio 1'), counted within its own type; never by asset ID. Put the file that must be followed most precisely first.**
- **Define each subject once by 2 to 3 stable features ('the woman in the red dress in Image 1 as Subject 1') and use that same label, or 'name@Image 1', every time it appears.**
- **Order: subject + action details + scene + light and colour + camera move + style + image quality + constraints.**
- **Write a storyboard as Shot 1 / Shot 2 / Shot 3 in event order (camera, action and expression, position, sound). Do not pin seconds: 2.0's precise timing ('0-3 s') is unstable and forcing it breaks the clip. This differs from 2.5's whole-second windows.**
- **One camera move per shot, in standard terms ('slow push-in', 'fixed shot'); push, pull, pan and track together make the picture unstable.**
- **Name the body part, range, speed and force ('slowly raise a hand'); prefer slow, small, continuous movements and say how one action flows into the next.**
- **Replace an emotion word with what the body visibly does (sad: head lowered, shoulders trembling, eyes reddening).**
- **Mark sound by bracket: music in ( ), sound effects in < >, dialogue in { }, on-screen subtitles in 【 】; a language other than Chinese or English is named before the line. Keep all dialogue in one language.**
- **To use a voice: 'Character says: {line}, voice timbre references Audio n'; to place a sound: its timing + 'Audio n'. Describe the voice too ('the low, warm male voice of Audio 1') and keep the line's tone close to the reference.**
- **End with short constraints: 'keep it subtitle-free', 'do not generate a logo', 'do not generate a watermark', and, with several people, 'no duplicate characters'.**
- **Use 4 to 5 files, not the full limit: 1 to 2 character pictures + 1 scene picture + 1 camera video + 1 audio clip. Too many files blur which one matters.**
- **To edit or extend, call it 'Video n' directly ('Extend Video 1 backward', 'strictly edit Video 1'), never 'reference Video n', which turns it into a reference task; name what stays unchanged.**

## Avoid

- Exact timestamps per shot ('0-3 seconds'): 2.0 follows them unreliably and the clip breaks.
- Multi-view or three-view character sheets and mixed collages: read as several people, causing face drift and twins. Use a separate headshot and one full-body photo.
- A photo or video of a real human face that is not the account's own model output, a preset character or an authorized asset: refused at input moderation.
- Abstract emotion words ('very sad', 'extremely angry'): show the body instead.
- Sprints, big jumps, violent rolls: high-burst actions are unstable.
- Push, pull, pan and track in the same shot.
- More than 4 referenced people in one clip: wrong head count and duplicates. Group them into pictures of 4 or fewer first.
- References carrying words you do not want: they raise the chance of burnt-in subtitles. Portrait clips get subtitles more often than landscape; no prompt removes them 100%.
- Mixing languages in the dialogue (proper nouns aside).
- Text + audio only, or audio only: refused; an audio file needs a picture or video beside it.
- Pasting the whole script as the prompt: redundant words confuse subjects; keep only what this clip shows.
- Extending a model-made clip again and again: quality degrades with each pass, faces blotch. A narrated clip can also click at its end: fade the last audio out in the edit.
