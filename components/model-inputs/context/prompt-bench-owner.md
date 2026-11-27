# How to make a picture ad and a video ad in four screens

Open the Prompt Bench on the Mac: http://localhost:8895/prompt

## Picture ad
1. Pick the ad you want to make.
2. See what we swap. The pictures each swap needs are ticked; untick or add one.
3. Check the list is green, then change the words, the person or the product.
4. Press Make the picture.

### Screen 2 up close: the swaps decide what goes in
The ad we copy, what stays the same, then every swap: what it becomes and the picture it needs. A cast member's photo
goes in for a cast swap. Product photos go in only when the product is in the ad. Words set on top after are not drawn.
A needed picture that is not on file shows red and nothing is made. Read from the run's swap list (`out/swaps.json`).

## Video ad
1. Tap Video ad, then pick the video.
2. Pick the clip. Its start picture and voice go in.
3. Check the list is green, then change what happens, the face, the hands or the camera.
4. Press Make the clip.

Behind it: `components/model-inputs/preview.py` (`preview`, `fill_defaults`, `fill_defaults_clip`, `validate`, `gate`, `make_picture`, `make_clip`); the sheets `picture-sheet.json` and `clip-sheet.json`.
