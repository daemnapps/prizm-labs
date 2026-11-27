# asset-index (the owner)

**asset-index** — takes **a folder of footage, for any brand**, makes **one
searchable record per clip: what is IN it, not what the file is called**. Does
not **choose, cut or ship anything**. Triggered by
`python3 machine/extract.py <footage folder> --brand <brand> [--label <name>]`.

`IMG_5476.MOV` becomes *"man patting his face with a grey towel in a bathroom,
profile reveal, usable as demo"* — so the edit can ask for a shot instead of
someone scrubbing through files.

Moved out of the owner's own repo 2026-09-20 on his word: *"that should definitely
be a real thing because we need to run that on any brand."* The folder already
existed here with its data and no code at all; this is the code.

## Two halves, deliberately split

| Half | What it does | Cost |
|---|---|---|
| `machine/extract.py` | frames + transcript + measurements, on this Mac | free |
| `prompts/index1-clip-v1-owner.md` | frames + transcript → one JSON record | about $0.002 a clip |

The free half never calls a model, so a whole drive of footage can be prepared
before a penny is spent.

## Rules

- **Any brand.** `--brand` is required and nothing in the code names one
  (workspace rule 7). Records land at `runs/asset-index/<brand>/<label>/`,
  per `runs/README.md`; media stays where it is and is never copied.
- A clip already done is skipped, so a run can be stopped and resumed.
- `projects/` and `work/` hold what was already here — the owner's own pulls.

## Where each clip lives now, and finding a shot (2026-10-05)

the owner moved the footage to the company Shared Assets drive
(`Shared drives/Shared Assets/brands/<brand>/…`, creators under
`content-creators/<gender>/<look>/<age>/<person>/raw/`). The records still carry
the old personal-drive path, so:

- `machine/shared_paths.py --brand <brand>` walks the drive ONCE (cached at
  `work/_maps/walk-<brand>.json`, `--rewalk` to refresh) and maps every clip to
  its Shared Assets copy by filename — confirmed by size whenever more than one
  file could be it (Drive's `(1)` suffixes and the move's folder-slug prefixes
  are understood). The map is `work/_maps/<collection>.json` (gitignored). It
  never returns a personal-drive path; a clip it cannot confirm is left
  unresolved and named.
- `machine/search.py` finds a shot in the records directly — no service, no
  network, the same answer every time — and returns only clips that resolve,
  each with its time range, Shared Assets path, frame and score. The video
  machine's footage step (`components/video-production/machine/footage.py`)
  is its first caller.
- Tests: `machine/test_index.py`, `machine/test_readers.py`.
- **LIBRARY (read surface, SI-99 (asset-index readers), 2026-10-08):** `machine/shared_paths.py`, loaded by file (as `components/video-production/machine/footage.py` does) — `collections(brand)` is the ONE reader of clip records: `runs/asset-index/<brand>/*`, then `work/<brand>-*`, then the read-only lab leftover `lab/the owner/asset-index/work` (folders whose name contains the brand); `record_frames(record_dir)` gives a record's frame files. image-production (`assets.py`) and casting (`search.py`) read through it. `extract.py` writes no `clip.json` for a failed step and exits non-zero.

## Creator usage rights in the search (2026-10-30, the email lead)

`machine/rights.py` reads the brand's register, `brands/<brand>/content-creators/usage-rights.json`
(people curate it; one row per creator, matched to footage by `drive_folder`, any case). `search()` takes
`use="ads"` (default) or `"website"`: creator footage whose row refuses that use, or whose `until` has
passed, is never returned; `use=None` filters nothing. Every hit carries `rights`
(`allowed` / `refused` / `expired` / `unknown` / `n/a`). Why: NO-ADS footage (two creators who never agreed
to ads, one of whose videos already ran as an ad) sat in the index, and `map_all.py` re-adds anything
removed, so the search is where it has to be stopped. A creator with no row comes back `unknown`, never
refused: most older creators have no row yet. Tests: `machine/test_rights.py`.
`use="email"` (LD-101 (Brand B house look), the email lead 2026-10-30) is stricter: only `allowed` comes back, which needs
`email: true` on the row, or no row and the folder on a register list that clears email. Tests:
`machine/test_ld101_email_rights.py`. **Folder lists (the email lead, 2026-11-10):** any top-level block of the register with a
`drive_folders` list (e.g. `pre_registry`, an era block) clears exactly the uses it marks `true` — `paid_ads`,
`website`, `social`, `email` — for folders with no row; a use no list marks stays `unknown`, and a row always wins.
`use="social"` is a fourth use. Tests: `machine/test_rights_folder_lists.py`. Every hit also carries `products` (the clip record's
`products_visible`), which the email line reads to offer only stills of the email's own product (the email lead, 2026-10-30).

**Picture references (the email lead, 2026-11-10):** `components/image-production/image_production/assets.py` reads
`shared_paths.collections()` directly, so it applies `rights.verdict` itself (`assets.cleared`): a creator reference
is kept only when the verdict is `allowed` for the picture's use (email purposes "email", `page-section` "website",
the rest "ads"); refused, expired and unknown are left out. Tests: `components/image-production/tests/test_reference_rights.py`.

## Proof: before-afters, reviews, UGC, social posts (2026-10-09)

the owner, 2026-10-09: *"index all the possible before and afters and social media
posts … ensure we have a clean path to extract … use these elements for further
email generations."* `machine/proof.py` indexes the brand's real proof (folders
named before-after, reviews, organic/social, creators-curated/ugc,
content-starter-pack; raw creator footage stays with `extract.py`):

    proof.py index   --brand <b>              # Drive's own metadata + thumbnails via gdrive-creator, nothing downloaded (~3 min for 535)
    proof.py list    --brand <b> [--kind before-after] [--problem acne]
    proof.py fetch   --brand <b> <id> …       # originals into runs/asset-index/<b>/proof/src/ through Drive
    proof.py extract --brand <b> <id> --part pair|before|after|full --ratio 1:1 --w 600 --out <file>

Writes `runs/asset-index/<brand>/proof/proof.json` (one entry per item: kind,
person, problem, side-by-side/stacked/single, Drive id and link, status draft)
plus `thumbs/` and `proof.html`. Needs `GDRIVE_SA_KEY` in the environment and an
interpreter with google-api-python-client (the Mac's /usr/bin/python3 has it).
`--from-mount` reads every file through the mounted Drive instead: it works,
but streams each file in full (25 items in 30 minutes on 2026-10-09).

**The brand's own live posts:** `machine/social_pull.py --brand <b> --ig <h> --tt <h1,h2> --fb <page>`
(Apify, `APIFY_TOKEN` by name) writes each post's media and details into
`brands/<b>/intake/organic/live-<date>/<platform>/` on the Shared Assets drive, named so
`proof.py index` reads them as social posts; raw results at `runs/asset-index/<b>/social/<label>/`.
First run 2026-10-09 was refused: every Apify account at its monthly cap (company resets 14 Oct).

## What is IN each picture: tags (2026-10-17, product photos 2026-10-28)

`machine/tag.py --brand <b> [--label proof|products] [--ids …]` looks at every picture once (Gemini, sheets of
12, the image engine's judge entry) and writes `tags.json` beside the records: the shot, the person, the
products shown, quality, baked-in words and `one_line`, what a person sees. `--label products` reads the
picture records `map_all.py` wrote and fetches each picture by its Drive id. The email design line
(`components/email-production/design/line.py`) offers only tagged proof and product photos and writes a real
picture's alt from its `one_line`: before, it picked product photos by file name and described what it
guessed (the email lead, 2026-10-28). Tests: `machine/test_tag.py`.

## The footage library: one vocabulary, a blank to fill (2026-11-06)

`library/` sorts every described scene of a brand into one fixed vocabulary keyed to the marketing doctrine's
section ids (`components/marketing-doctrine/ad-frameworks.json`), so a storyboard scene can leave a blank and
the library fills it: an owned cut first, then AI from a clean real frame, then `[UNFILLED: …]`.

- `library/vocabulary.json` — the shared words: beat (doctrine sections it fills), setting, shot, tier
  (A direct b-roll: polish hucg or studio-staged / B montage or proof / P talking to camera), polish,
  text marks (clean, caption, offer-text, handle, partner-handle, brand-handle, platform-mark, app-screen,
  editor-logo) with text size, people, stream, source. No brand appears in it.
- `runs/asset-index/<brand>/library/brand-vocabulary.json` — the brand's words: product ids, their match words
  and looks, handles cleared to show, the brand's own handles, and words that leave a Drive folder out.
- **Captions and handles mark a clip, they never remove it** (owner ruling 2026-11-06): every pick carries its
  marks so whoever selects knows. Only an AI reference frame asks for `text: clean`.
- **People:** the Drive's own filing `content-creators/<gender>/<ethnic-appearance>/<age-band>/<person>/` is
  carried as creator_gender / creator_ethnicity / creator_age; apparent on-screen gender and age come from the
  check pass. Ethnicity is never read from a picture.
- `library/library.py build --brand <b>` (free) writes `library.json` + `coverage.json` beside the brand file,
  including the proof index's tagged before-and-after pictures as `proof` rows. `query` answers a blank with a
  ranked band and a different band and says what it dropped. Past 9 MB the rows go into `library-01.json`,
  `library-02.json`, … and `library.json` names the parts (the 10 MB repo rule); read a library only through
  `library.read_rows` / `rows_of`, never by loading `library.json` directly.
- `library/check.py --brand <b> [--dry-run] --budget <USD>` (paid, ~$0.003 a clip) asks
  `prompts/check-pass-v1-owner.md` of each described clip: polish, handles as written, platform marks, people,
  products, quality, and per scene the beat, burned-in text, its size and words. Answers and the prompt as sent
  land in `library/check/results.jsonl`, then `results-02.jsonl`, … once a file nears 9 MB (read them through
  `library.check_lines`).
- `library/index_new.py --brand <b> --budget <USD> [--dry-run]` keeps it current: map new Drive files (free),
  describe new videos in footage folders, check them, find their shot changes (free), rebuild. One cap for the whole pass. For this
  component's own footage folders the owner moved new footage from describe-on-use (LD-63 (describe on use))
  to describe-on-arrival, capped per pass (2026-11-06).
- **The video chain reads it:** `components/video-production/machine/footage.py` passes every candidate
  through `library.enrich()` — one file once, talking-to-camera scenes kept out of b-roll, tier A first when
  its score is within a quarter of the best — and the brief's footage ledger shows tier and text marks.
  A brand with no built library is unchanged.
- **Editor times on the cut:** `library/cuts.py --brand <b>` (free) finds every real shot change on the local
  proxies (`cuts.json`); the build snaps each scene's in and out to a shot change within 1 s (`cut_in`,
  `cut_out`, `cut_source`), and `enrich()` hands those times to the footage step, whose ledger marks them
  "(on the cut)". Nothing is cut or copied; slicing is for the editor (owner ruling 2026-11-06).
- **Footage from an ad is marked as such** (owner ruling 2026-11-06): a file filed under `intake/ads/<product>/<project>/` or `briefs/delivered/<brief>/` is source `ad`, and its row's `used_in` names the ad project or brief. Ad folders hold finished ads and the b-roll gathered for them, much of it sourced rather than shot by a creator, so every pick from one says which ad it came from; the footage step's brief ledger shows "from ad <name>". Other origins by filing: `brand-footage` (brand-assets), `internal` (operations, core-avatars, brand-identity), `ai` (ai-elements or an archive folder named ai-…).
- **Creator on every row** (2026-11-20): `creator_of` takes the person from `content-creators/…/<person>/`; else
  the person folder under a `<n>. Creators/` folder in the record's own path (`1. Founder - Jo Bloggs` → `jo`);
  else the handle in a social download's file name (`IG_reel_<h>_<date>`), mapped to a creator folder when
  `partners` lists that handle. Only a file with none of these keeps its bucket (`intake/organic`).
- **Left out:** a Drive folder whose path holds a brand file `exclude_words` entry (the owner's own folder).
  Clips elsewhere that show or name the owner stay in (owner ruling 2026-11-06).
- **Before-and-after pictures:** proof-index items of kind before-after, media image, tagged by `tag.py`; tier A
  when the tag's quality is 4 or more, text marks from `baked_text`, problem from the item or its one-line tag.
- **Daily:** `library/run-daily.sh` runs `index_new.py` per brand from a clean checkout on a scheduler and pushes
  only `runs/asset-index/<brand>/`. Keys by name only (shared loader, or `ASSET_LIBRARY_KEY_ENV`).
  **Not scheduled on any machine yet** (owner, 2026-11-06): it is set up later, in its own session. Until then
  new footage enters the library when someone runs `index_new.py` by hand.
- **Editors see results, not the machinery:** the library reaches production only through the footage step's
  picks in the brief (owner ruling 2026-11-06).
- Tests: `library/test_library.py`.

### The board: where editors sift (2026-11-06)

- The producer-facing surface of the library is the board, `library/board/serve.py` (port 8915), a page on the
  machine and never a published page. One board per brand. It reads the built library live, shows each scene's
  frame, filters by every library field, and copies a shot list of picked scenes (file, Drive link, exact in/out,
  text marks). Picks stay in the viewer's browser until "Put in brief" writes them beside a brief
  (`deliverable/picks.json`, editor-picks/v1, via the video chain's `footage.write_picks`); a pick for a scene is that scene's cut.
- Producers get no guide to the machinery; the board and their briefs are what they see.
- The video edit's Brief Editing Board (`components/video-edit/machine/brief_board.py`, port 8916) reads this board's
  rows and frames (`serve.rows`, `serve.frame`) and `library.query` for a brief's scenes; it keeps no copy of the library.
  Its swaps and trims are cut-sheet versions in the video edit, and each is written back as the scene's pick through
  `footage.write_picks`, so picks.json stays one file.

### Pulling the library into the edit: where it is, how it reaches Drive (2026-11-07)

| What | Where |
|---|---|
| A brand's built library (rows) | `runs/asset-index/<brand>/library/library.json` (names its parts `library-01.json`, …) |
| The brand's words, board words, coverage, shot changes | `brand-vocabulary.json`, `board.json`, `coverage.json`, `cuts.json` beside it |
| Check answers | `runs/asset-index/<brand>/library/check/results*.jsonl` |
| One clip's description and frames list | `runs/asset-index/<brand>/<collection>/<drive file id>/clip.json`, `breakdown.json` |
| Proxies and scene stills | on the machine that described them only (`proxy.mp4` beside the record, gitignored; stills in `~/Library/Caches/asset-library-frames/<clip>_<scene>.jpg`) |
| The original footage | Google Drive, Shared drives → Shared Assets → `brands/<brand>/…` |

Every row is one scene and carries its way back to Drive:

- `clip` is the Drive file id. `library.drive_link(row)` gives `https://drive.google.com/file/d/<id>/view`.
- `label` is the file's path under the Shared drives (`Shared Assets/brands/<brand>/…`).
  `library.source_file(row)` returns that file on the Drive folder synced to this machine (Drive for desktop,
  found by `components/brandpath/drive_index.mount()`), or None.
- `cut_in` / `cut_out` are the editor's in and out, on a real shot change where one is within 1 s (`cut_source`).
- `used_in` names the ad or brief a scene came from; `source`, `tier`, `text_marks`, `handles` say what it is.

Fast path for the edit: read rows with `library.rows_of(brand)` (or a blank with `library.query`), open each
pick with `source_file(row)` at `cut_in`–`cut_out`, and fall back to a Drive API download by `clip` only when it
returns None. The synced folder costs no API quota: on 2026-11-06 the API answered `downloadQuotaExceeded` after
about 100 files in a day, and the synced folder carried the remaining 2,500 described clips. A file read through
the synced folder is downloaded on first open and then stays in Drive for desktop's cache.

## Not done yet

The paid half is still run by hand from the prompt — there is no `run.py` that
does both halves and files the record. That is the next piece.

## The four questions

Answered 2026-09-23, when this folder owed them as a resident
(`components/CLAUDE.md`).

**Before you start (asset-index#9, 2026-10-08):** `ffmpeg` and `ffprobe` on PATH (`machine/extract.py` calls both); `faster-whisper` installed in this component's local `.venv`; the `base.en` model downloads on the first transcript (needs network once). Where it runs (its Runs by line) is the owner's call and is not set here.

- **Engine + owner:** `machine/extract.py` (frames, transcript and
  measurements, free, on this Mac) and `prompts/index1-clip-v1-owner.md`
  (frames + transcript → one JSON record, about $0.002 a clip). The split is
  deliberate: a whole drive of footage is prepared before a penny is spent.
  **the owner.**
- **Definitions + curator:** the record shape the prompt writes — what is IN a
  clip, never what the file is called. **the owner.** Nothing here names a brand
  (workspace rule 7).
- **The plane it emits:** `runs/asset-index/<brand>/<label>/`, per
  `runs/README.md`. **Media is never copied** — a record points at the
  footage where it already sits.
- **Manifest per entry:** one JSON record per clip, keyed by the clip. A clip
  already done is skipped, so a run stops and resumes.

## Where the footage actually lives — the honest answer

**Nowhere shared, today.** `work/` (1.3 GB) and `projects/` (110 MB) hold
the owner's own pulls and scene cuts. Both are gitignored, and **neither is mirrored
to Drive** — there is no `Shared Assets/lab/the owner/asset-index/` folder. So this
footage exists on one Mac and nowhere else, which means a second person cannot
run this tool against it and a disk failure loses it.

That is stated here rather than left implicit because the component's Residents
row promises a contract over "the index it builds", and an index over footage
only one machine can see is a narrower promise than it reads as. Giving it a
Drive mirror is a card, not a thing to do inside a doc.

`.venv/` (218 MB) is a local build artifact and is not the work.

## Two things that are open, not settled

- **The Drive carve-out (O9).** The media stayed on Drive at its lab path when
  the code moved into `components/`, so the mirror above still reads as a lab
  path. The standing ruling is that Drive is reached by fileId through the API,
  not by the mounted folder. Migrating is its own card; until it lands, the lab
  path is deliberate, and this file says so rather than leaving it to look like
  an oversight. The Shared Assets root is `SHARED_ASSETS_ROOT`, else the mount
  found through `components/brandpath/drive_index.py` mount() (SI-45 (footage
  mount helper)).
- **A records adapter (O12): none yet.** The convention allows "an adapter or
  'none yet' stated"; this states it. Worth knowing for whoever builds one:
  `chain_records.py` is cheap because it did not mint a kind — it files onto an
  existing one and distinguishes itself with a single constant. One shared kind
  behind one adapter is 50–100 lines per component; a kind of its own is
  450–650 plus a manifest plus worker wiring.

## Swipes: viral covers (2026-11-11)

`swipes/covers.py` pulls the covers the platforms' discovery surfaces are pushing (Instagram Explore, TikTok Explore
and For You, YouTube Trending, YouTube Shorts), keeps only rows over a views/likes floor with their URL and post date,
measures each cover on this Mac (text read, faces, colour), carries a by-eye breakdown in one vocabulary, and indexes
every cover as a swipe in `runs/asset-index/swipes/covers/` (`covers.json`, `patterns.json`, `covers/<id>.jpg`),
for paid and organic work. Swipes are brand-agnostic and sit beside the brand libraries, never inside them: the
footage step never picks a swipe as footage. The cover step's per-platform styles
(`components/video-edit/machine/cover_styles.json`) quote these sums as their evidence; a style changes through a new
pull and its numbers. Commands and rules: `swipes/README.md`.

## What the AI tools have made: the register (2026-11-25)

`machine/made.py build|pull|find|count` keeps one register of everything AI-made, so nothing is paid for twice:
`runs/asset-index/_made/<brand>.jsonl`, one row a file (kind person, place, prop, picture, clip or sound; what it shows; where it
is; the job that made it; `reuse` any, or "this ad" when a line is spoken in it). It reads the element bank, the production runs,
the picture runs and the account's own job list (`pull`, free, read-only). Retired and unfinished people are left out, in sheets
and in clips. Kept apart from the real footage records on purpose: an AI face is never offered as a real customer.
Before anything is paid a door calls `close(brand, kind, words)` and shows what fits; nothing is swapped in by itself. Read by
`video-studio/higgsfield/hf_route.py` (every brief's list of pictures to make) and `clip_tools.py`. Tests: `machine/test_made.py`.
