# lowpoly — a blocky early-2000s console game world, drawn entirely in code

No video model runs. The only paid step is the voice. Sister of `../stick/` and `../cartoon/`, whose word timing it uses. three.js draws the world (`world.js`), a HyperFrames page steps it frame by frame, and the game screen (money, health, map, shop menu, subtitles) sits on top.

No real game art, name, logo, font or music. The look alone carries the nod.

- In: `runs/video-edit/<brand>/<label>/` holding `lines.json`, `plan.json` (each scene's `speaker`), `voice/` (one read per line from `components/video-production/machine/voice.py`) and `ad.json`.
- Out: `final.mp4` in the same folder, 1080x1920, plus `beats.json` and the HyperFrames page in `page/`.

Run: `python3 lowpoly.py track <run>`, then `python3 lowpoly.py all <run>`. A 56-second ad renders in about 2 minutes.

`ad.json`:

- `timeline`: the order of the ad. `{id}` for a spoken line, `{id, hold}` for a silent beat of that many seconds. `lead` and `pad` trim the air around a line.
- `beats`: one per timeline id. `scene` is a name in `SC` in world.js: walk, neck, chair, talk, cross, flexcross, pickup, use, clock, reveal, selfie, store, shower, end. `bumps` is how many sit on the neck and `from` where they start. `swing` wipes in with the barber's body. `menu` is the row picked, `spent` the rows struck out. `money`, `pop`, `slot`, `red`, `cards`, `quote`, `lab`, `chime`.
- `menu`, `menu_title`, `cards`, `quote`, `quote_by`, `end`: the words on the game screen.
- `product_turn`: real product cut-outs in turn order, from the current casting sheet.
- `small_print`: `{at, until, text}` by beat id, from the brand's compliance file.
- `drop_at`, `stop_at`: beat ids where the music drops and stops dead. Without them the slow funk loop plays. A timeline row's `max` trims a read.
- `of` and `part` on a beat, as `[i, n]`, place it inside another line's read. `headline` and `headline_until` set the top line. `bleeps`, `mask` and `no_subs` handle bleeped words, masked subtitles and beats with no subtitles.
- `lead_glb`: a rigged character file in the run folder. It stands in for the drawn lead; its bones follow the same pose joints, and bumps are painted into its skin texture. `solo` hides the second person.
- `voice_chain`: an ffmpeg filter per speaker. `subtitle_colour`: subtitle colour per beat id. `music`: music level.

The music and effects are written by the code, so they cost nothing. A new subject needs a new `ad.json`, and a new scene function only if nothing on the list fits.

Plane: `runs/video-edit/<brand>/<label>/`, video mirrored to the same path on the Drive. Runs by: person.
