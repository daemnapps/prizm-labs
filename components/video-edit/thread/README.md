# thread — a phone text thread ad, drawn entirely in code

No video model runs. The only paid step is the voice. Sister of `../stick/`. Study the swipe frame by frame first; every picture comes through the image process as a clone of the swipe's frame, and the sound is the swipe's own, split out by `audio-teardown`.

The look: a screen recording of one chat. One message held down at a time, the rest blurred behind it, the reaction bar above and the menu below. Voice notes play through a phone speaker with their words on screen.

- In: `runs/video-edit/<brand>/<label>/` holding `lines.json`, `vo/<id>.mp3` (from `components/video-production/machine/voice.py`), `ad.json` and the pictures in `page/assets/`.
- Out: `final.mp4` in the same folder, 1080x1920, plus `beats.json` and the HyperFrames page in `page/`.

Run: `python3 thread.py all <run>`. `python3 thread.py look <run> [step ...]` also writes one still per step to `<run>/look/`.

`ad.json`:

- `steps`: in order. Every step has `kind`, and `from` (`me` or `them`), `time` (the time on the bubble) and `clock` (the phone's clock).
- `kind`: `photo`, `editor` and `paper` (the opening, with `src` and `pov`), `image` (`src`, a file in assets, made by the image process), `text` (`text`), `voice` (`sid`, `caption`), `missed`.
- `news`: one made-up page. `style` is `paper`, `report` or `breaking`, with `kicker`, `head`, `photo`, `body`, `quotes`.
- `narrate`: a teller's line id, laid clean over any step, and the step holds for it.
- `hold`: seconds on screen. Left out, a text holds by its length and a voice note by its sound. `after`: seconds after a voice note.
- `small_print`: `{step, text}`, from the brand's compliance file.
- `blur_pic`: a picture sits in the blur behind this step. `seed`: the blurred chat.

No brand, app name or logo is drawn. Real product pictures only; nothing that makes a claim the product file does not.

Plane: `runs/video-edit/<brand>/<label>/`, video mirrored to the same path on the Drive. Runs by: person.
