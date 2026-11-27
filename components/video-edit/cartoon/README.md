# cartoon — a flat 1960s Saturday morning cartoon, drawn entirely in code

No video model runs. The only paid step is the voice. Sister of `../stick/`, whose word timing, captions and pause tightening it uses.

The look: inked line that boils eight times a second, flat paint, mid-century colour, limited animation. Lookalikes of nobody: no real character, show name or logo is drawn or typed.

- In: `runs/video-edit/<brand>/<label>/` holding `lines.json`, `vo/` (from `components/video-production/machine/voice.py`) and `ad.json`.
- Out: `final.mp4` in the same folder, 1080x1920, plus `beats.json` and the HyperFrames page in `page/`.

Run: `python3 cartoon.py all <run>`. Free look test before any voice: `python3 cartoon.py look <run> [scene ...]` writes one still per scene to `<run>/look/`.

`ad.json`:

- `beats`: in spoken order, each `{at, scene, num}`. `at` is the words the beat lands on, `scene` a name in `SCENES`, `num` the list number shown in the corner (optional).
- `tune`: the music box, a list of `[note, beats]`; the note is a name in `NOTE`, or null for a rest. Public-domain carols only.
- `tube`: `body` or `face`, which tube the drawn product is. `packshot`: repo path to the real packshot laid over the `pack` scene, with `offer_line` under it. `small_print`: `{at, text}` from the brand's compliance file.
- `brand_card`: the words on the `end` scene, fading in over the last seconds.
- `music`: music level under the voice (default 0.32). `tail`: seconds held after the last word (default 3).

Scenes: title, catalog, tv, stocking, tinsel, aluminum, bubble, drive, window, gift, slinky, cards, lot, lot_empty, angel, canes, tablet, portrait, covered, spots, dry, shelf, layers, scrub, glad, pack, end. A new memory needs a new scene function, added to `SCENES`.

Plane: `runs/video-edit/<brand>/<label>/`, video mirrored to the same path on the Drive. Runs by: person.
