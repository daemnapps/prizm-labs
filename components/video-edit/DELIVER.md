# Deliver: hand it over, get it back done (2026-11-21)

Rule: every video edit is handed to Video Edit and comes back as a finished delivery. Format does not matter: the
edit puts together what production made (the swipe's order, the writing, the shots and scenes, the voice, the music,
the AI clips, the pictures) and brings it to life in the detail. It adds no decisions of its own. The Video Studio
(`components/video-studio`) is the view of that work; it does no editing itself.

    python3 machine/run.py deliver <what> --dry-run    # the road and the stage due; writes nothing
    python3 machine/run.py deliver <what>              # straight through to the approval card
    python3 machine/run.py deliver <what> --no-file    # everything but the card

| `<what>` | road | code |
|---|---|---|
| a Studio production (`idea-36`, `0332`, its brief number or key) | cut → check → render → edit moves → covers | `machine/studio/` (moved from the Studio 2026-11-21), run on the Studio's own job file so the Studio screen shows each step |
| a video-production run folder | the edit-map line | `machine/line.py` |
| a video-editor hand-off folder | the kit road, every version | `machine/run.py handoff --versions` |
| a kit folder | the kit road, every version | `machine/run.py start --versions` |

`machine/deliver_any.py` picks the road. Every run writes `DELIVERY.md` + `delivery.json` beside the work: the road,
each stage's steps, the versions, the card, and what held and why.

**Holds, never guesses.** When production is not finished (shots, voice, AI shots, the maker's clips, a song), the
delivery is held and names what production owes. A stage that stops holds the delivery with the stage's own words.

**Used everything** (`machine/studio/used_everything.py`), run before any card is filed: every scene in the brief's
order is in the edit as production cut it (same file), nothing plays that production did not make, every caption
word production timed is drawn, the song and the bed are in when production made them, every version (control,
hooks, footage variations) is rendered after the latest cut, and each sits at -14 LUFS (±0.5). Any miss holds.

**The card.** A Studio production's versions go on one flexible card in `meta/<brand>/1-check/video/` through
meta-upload's own filer (`feed_video.file_master`, `production=` so the cover stage's hand-off is read). The brief
key must be `<brand>_<product>_<brief>`; a production without one is held ("number the brief first"). Nothing goes
to Meta; Approve is the owner's click.

## What moved (2026-11-21)

From `components/video-studio/` to `machine/studio/`, by `git mv`, each old name left as a forward (module and
command) so every reader works unchanged: `swipe_cut.py`, `swipe_check.py`, `to_studio.py`, `edit_stage.py`
(+ `edit-stage.json`), `edit_moves.py`, `layers.py`, `reply_card.py`, `covers_stage.py` (+ `cover-stage.json`).
Out of `video_studio.py`: the scene cut and its caption lines (`scene_cut.py`; the take print, `gen.take`, stays in
the Studio as production) and the render of every version with its -14 LUFS levelling (`studio_render.py`).
Proof: the edit project of three productions built byte-identical before and after; three scene cuts identical
(video, captions, still); the Studio's own tests unchanged (the two failing files failed before the move).

## Seams still open

The moved stages still read the Studio's production side (`settings.py`, `video_studio.py` helpers: where a
production lives, footage lookup, takes, voices) through `STUDIO_HOME`. Each is cut by giving Video Edit the data it
needs as a contract instead of an import. Studio's own `music_bed.py` and `song_captions.py` are copies with no
caller; they go when the forwards go.
