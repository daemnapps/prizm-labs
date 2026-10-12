# video-edit

**Keys this tool needs:** ELEVENLABS_API_KEY. Put your own in `.env` at the top of the repo — see [`.env.example`](../../.env.example).

## How to use it → (team dashboard)

Turns an approved kit — voice, A-roll, B-roll, music, sound effects — into the
finished captioned video, with two stops for the owner: the timeline, then the
captions. No timeline software, no editor.

    python3 machine/run.py start <kit-folder> --brand <brand> --label <label> --dry-run   # check, spend nothing
    python3 machine/run.py start <kit-folder> --brand <brand> --label <label>             # runs to the next stop
    python3 machine/run.py change  <run> timeline "bring the cutaway in later" --why "it covered her face"
    python3 machine/run.py approve <run> timeline
    python3 machine/run.py status  <run>
    python3 machine/run.py render  <run>                                                  # one video per hook + the 15/30/60 cutdowns + covers, named — 9:16 only

It assembles every element production made (ELEMENTS.md): cards, screens,
splits, greenscreen, end card, lower thirds, annotations, platform UI,
disclaimers, transitions, one grade, music ducked and cut on the bar, sound
effects, room tone, and a −14 LUFS master. It decides nothing.

Words sit in named zones clear of every feed's buttons and off the face, in fonts
from a named library, one space apart; comment bubbles, posts, threads, counters,
icons, stickers and drawn arrows/rings/bursts are picked by id from `looks/`.

    python3 machine/fonts.py            # which fonts it would fetch (nothing downloads without `install`)
    python3 machine/icons.py            # which icons and emoji it would fetch

Rules, files and what is not built yet: CLAUDE.md. The page: context/artifacts.md.

Retention (warnings and a score, never a block), the helpers and the new packs:

    python3 machine/retention.py <run>                 # the retention report for a run
    python3 machine/registry.py find confetti          # look up a HyperFrames registry block
    python3 machine/registry.py install <id>           # install one so a sheet may use it
    python3 machine/cutout.py <clip> --seconds 2 --out <dir>   # BiRefNet cut-out: alpha PNGs + WebM

