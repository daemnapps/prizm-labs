# stick — a stick-figure explainer ad, drawn entirely in code

No video model runs. The only paid step is the voice.

Run `stick.py tighten <run>` after the voice so no pause runs over 0.2 s.

Script check before voicing: the costly fix in the setup must be the same kind of thing as the "No X on earth" line and the closing line. Prices match the offer file exactly.

- In: `runs/video-edit/<brand>/<label>/` holding `lines.json`, `vo/` (from `components/video-production/machine/voice.py`) and `ad.json`.
- Out: `final.mp4` in the same folder, 1080x1920, plus `beats.json` and the HyperFrames page in `page/`.

Run: `python3 stick.py all <run>`. A 67-second ad renders in about 30 seconds.

`ad.json`:

- `accent`: the one colour.
- `pictures`: name to Drive file id. Fetched by key through gdrive-creator.
- `highlight`: words coloured in the captions.
- `small_print`: `{at, text}`, from the brand's compliance file.
- `beats`: in spoken order, each `{at, pose, show}`. `at` is the words the beat lands on. `pose` is a name in `POSES`. `show` is one or two of `pic:<name>`, a drawing (`lotion|LABEL`, `dry`, `question`, `phone`, `jar`, `x`, `earth`, `shelf`, `clock`, `badge`, `price|TEXT`), or the skin picture (`skin:sit`, `skin:scrub`, `skin:through`).

The music bed and pops are written by the code, so they cost nothing. A new subject needs a new script and beat list, and a new drawing only if nothing on the list fits.

Plane: `runs/video-edit/<brand>/<label>/`, video mirrored to the same path on the Drive. Runs by: person.
