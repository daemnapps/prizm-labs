# The Four Stations — the hand-offs (step b, 2026-09-30)

Mirror of **The Four Stations** artifact ((team page)), tab *b · Hand-offs*.
What each station must hand the next one. Written from what the machine writes today; a station may read ONLY what is listed here from the one before it.

## 1 → 2 · The Teardown Record

Everything station 1 writes into the run folder (`tools/video-teardown/machine/runs/<slug>/`, filed to `runs/video-teardown/<brand>/<slug>/`).

| Part | File | Made by |
|---|---|---|
| The source | `source.mp4`, `poster.jpg` (media stays on the Drive) | intake |
| What kind of video | `stages/0-triage.md` → `run.json` `triage_lane` | T0 |
| Every word, who said it, the voices | `sound-sheet.json`, `sound-sheet.md`, `transcript.json`, `stages/1-transcript.md`, `audio/` | T1 |
| The record | `stages/1-teardown.md` — cast, places, props, shot table, sound, section map, `### VERBATIM TRANSCRIPT`, `### VOICES` | T2 + deep passes |
| The music | `music/` (split, named) | T2 deep pass |
| The doctrine read | `stages/1c-doctrine.md`, `doctrine.json`, `elements.json` | T3 |
| How to recreate it | `stages/2-spec.md` — format, skeleton, elements E1…, script architecture, load-bearing L1…, swappable | T4 |

**Rules of the record**
1. **No brand in it.** No stage 0/1/1c/2 prompt takes a brand, product, avatar or route variable. Known exception to clean: two element lists (`format.video.json`, `structure.video.json`) carry example paths naming Brand A and Brand B into T3.
2. **One teardown, many brands.** The record is written once; each brand's writing reads it and never edits it.
3. **Complete or not handed over.** A record missing the transcript or the spec is not a Teardown Record; writing does not start on it.
4. **The audience read (old 1b) is not in it.** Who OUR version speaks to is a writing decision (W1).

## 2 → 3 · The Brief, per route

Every route's brief is one file, `stages/5-brief.md`, carrying **three stamps tied to one fingerprint** of the brief:
- line 1: `<!-- swipe-match: PASSED … · <hash> -->` (W10, shot-by-shot check against the swipe)
- `<!-- brief-read: APPROVED by the owner … · <hash> -->` (your read)
- last line: `MANIFEST: COMPLETE · <hash>` (every element E…/L… of the spec pointed at the scene that carries it; every price found in the brand's files)

Production refuses a brief without all three, or one edited after stamping. `run.json` also carries `production_route` and `route_chosen_by_hand: true` — the route lock.

| Route | What the brief holds | Also hands over | Goes to |
|---|---|---|---|
| **Creator** | per frame: Film · Say · Hear · Wearing · On screen (creator brief v26) | her page (W11, `7b-page.md`) and the Google Doc; her profile refresh (W12) on her own posts | the creator, then Production only for pictures (frames) |
| **AI** | readable view (CAST · WORLD · CAMERA · A-ROLL · B-ROLL · CARDS · GREEN-SCREEN · END CARD) + THE BLOCK. Each scene: header `Scene n · start – end · Ns · TYPE A/B/C`, then Happens · Say · Delivery · Refs · Still. `voice` = the spice pass's spoken paragraph (W9), verbatim. Every visible identity carries its element (the anchor rule). The tail: full wardrobe, light, skin rule, do-not-include | — | Production (`video-production/machine/run.py start`) |
| **Founder** | the creator brief (v26) with "founder" as the route, until a founder brief exists | her page | the founder |
| **Social copy** | primary text · headline · description per format, and a brief for the media buyer (copywriter stages 8–9) | the copy page | the ads manager |

**Rules of the brief**
1. **The route is fixed before writing starts** (the route lock). One brief per route; a second route is a second brief from the same Teardown Record.
2. **Nothing invented.** Every person, place and price comes from the record or the brand's files, or is a named `[SLOT]` production stops on.
3. **The swipe's structure is kept** unless you approved a change by number.

## 3 → 4 · The production run

`runs/video-production/<brand>/<label>/` — `run.json`, `plan.json` (scenes, music and effects rows, `subject_box`), `media/<id>.*` (stills, clips, plates), `vo/track.mp3` + `vo/timing.json` + `vo/<scene>.mp3`, `verdicts.json`, `media/<id>.parity.json`, `brief.md` (its `edit` block: headline, captions, music, effects, cards), and `deliverable/EDITOR-PACK.md`.

**Rules:** Editing reads the run folder (`video-edit/machine/run.py from-run`), not the editor pack. A music or effects row with no file goes on the edit's "unmade" list and its gate turns red. The Sound Sheet reaches editing only through the brief's `edit` block.

## 4 → out · The finished ad

`runs/video-edit/<brand>/<label>/deliverable/` — one video per hook, 15/30/60 cutdowns, covers; `cutsheet-vN.json`, `timeline.html`. Two stops on the way are yours: the timeline and the captions.
