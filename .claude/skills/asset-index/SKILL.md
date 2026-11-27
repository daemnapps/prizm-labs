---
name: asset-index
description: Find a shot in the footage we own, index new footage, or organize a brand's whole footage library into one vocabulary (beat, product, tier, polish, text marks, handles, people) so storyboard blanks fill themselves — a brand plus a description of the shot goes in; clips with a time range, the Shared Assets path, tier and text marks come out. Use whenever someone says "organize <brand>'s assets", "index <brand>'s library", "run the asset library for <brand>", "set up the asset index for a new brand", "keep the library current", "what footage do we have for <beat> with <product>", or "find a shot of <what is in it> for <brand>", "do we have footage of a man patting his face with a towel", "search the <brand> footage for <words>", "what footage do we have of <thing>", "index this footage folder for <brand>", "prepare these clips so they can be searched", "describe these clips for <brand>", or hands over a footage folder and a brand.
---

# Asset index

> **Activates component:** `components/asset-index` — `machine/search.py` finds a shot; `machine/extract.py` prepares a footage folder for free; `machine/describe.py` describes clips (paid, with a budget); `library/` sorts a brand's footage into one vocabulary, checks it, snaps editor times to the real cut and keeps it current.

External dependencies: `components/asset-index/` (the engine; `CLAUDE.md` is its rules), `components/video-production/machine/footage.py` (the first caller of the search), the footage on the Shared Assets drive under `brands/<brand>/`.

Asset index answers "what is IN this clip", not "what is the file called". Two jobs, and the first is the one used most.

## Find a shot (free, no network)

```
python3 components/asset-index/machine/search.py --brand <brand> "man runs fingers along his jaw, razor bumps"
python3 components/asset-index/machine/search.py --brand <brand> --said "the words spoken" "what it shows"
```

- It scores every scene of every indexed clip against the description. The same records and the same words give the same answer every time.
- It returns only clips that resolve to the Shared Assets drive, so every hit is footage a person can open. Each hit has the clip, the time range inside it, the Shared Assets path, the nearest frame and a score from 0 to 1.
- Show the person the top hits with their paths. Do not pick one for them.

## Prepare new footage (free) and describe it (paid)

```
python3 components/asset-index/machine/extract.py "<footage folder>" --brand <brand> [--label <name>] [--limit N]
python3 components/asset-index/machine/describe.py --brand <brand> --folder "<Shared Assets/brands/<brand>/… label prefix>" --budget <USD> --reason "<why now>" --dry-run
```

- `extract.py` makes frames, a transcript and measurements on this Mac. It never calls a model and costs nothing, so a whole drive can be prepared first. A clip already done is skipped, so a run can be stopped and resumed.
- `describe.py` is the model step (about $0.002 a clip). It needs `--budget` and `--reason`, checks the budget before each clip, and has `--dry-run`. Always dry-run first and tell the person the clip count and cost before the real run.
- Footage is never copied or moved. Only records are written.

## Organize a brand's library (any brand)

The library sorts every described scene of a brand into one vocabulary keyed to the doctrine's sections, so a
storyboard scene leaves a blank and the library fills it: an owned cut first, then AI made from a clean real
frame, then `[UNFILLED: …]`. The video chain's footage step reads it, so every brief's b-roll picks arrive with
file, exact in/out, tier and text marks. Editors work from the brief; they never need this machinery. Their one
surface is the **board** (below), where they sift footage and pick shots.

What each scene carries: beat (doctrine section it fills), product, setting, shot, **tier** (A direct b-roll =
high-quality creator or studio-staged footage, short side 720 px+, no quality problem, 2 s+; B montage or proof
only; P talking to camera, never b-roll), **polish**, **text marks** with size and the words, **handles as
written**, the Drive's **filed** creator gender / ethnic appearance / age band, apparent people on screen, source,
and the **editor's in/out snapped to the real shot change** (`cut_in`, `cut_out`, `cut_source`). The brand's
tagged before-and-after pictures join as `proof` rows.

### A new brand, start to finish

1. **Brand file.** Write `runs/asset-index/<brand>/library/brand-vocabulary.json`: product ids with match words
   and how each looks, `partners` (handles cleared to show), `brand_handles`, `exclude_words` (a Drive folder
   whose path holds one of these is left out). Copy the shape from an existing brand; fill in this brand's values.
   Without it every product reads `none`.
2. **Dry-run the pass** and tell the person the counts and the cost before spending anything:
   `python3 components/asset-index/library/index_new.py --brand <brand> --budget <USD> --dry-run`
3. **Run it** inside a cap the person names: same command without `--dry-run`. It maps new Drive files (free),
   describes new videos in the footage folders (paid), checks them (paid, ~$0.003 a clip), finds shot changes
   (free) and rebuilds the library (free). A key out of credit pauses the paid steps; the free ones still run.
4. **Before-and-after pictures** come from the proof index: `machine/proof.py index --brand <brand>` then
   `machine/tag.py --brand <brand> --label proof`; the next build picks them up.
5. **Daily (not scheduled anywhere yet):** when it is set up, schedule `components/asset-index/library/run-daily.sh`
   on a machine that stays on, against a clean checkout nobody edits (see its header). It commits and pushes only
   `runs/asset-index/<brand>/`. Until then, run step 3 by hand when new footage lands.

### Everyday use

```
python3 components/asset-index/library/library.py query --brand <brand> '{"beat":"mechanism","product":"<id>","min_tier":"A"}'
python3 components/asset-index/library/library.py build --brand <brand>        # after any vocabulary or brand-file change
python3 components/asset-index/library/check.py --brand <brand> --dry-run      # what the check pass would still send
python3 components/asset-index/library/cuts.py --brand <brand>                 # shot changes for clips with a local proxy
```

- A blank takes any of: beat, product, action_words, setting, person, shot, min_tier, stream, `text`
  (`any` default, `clean`, or a list of allowed marks), creator_gender, creator_ethnicity, creator_age. Every
  answer has a ranked band and a different band and names what it dropped.
- **Captions and handles mark a clip, they never remove it.** Show the marks with every pick. Only an AI
  reference frame asks for `text: clean`.
- **Clearing a handle:** add it to `partners` in the brand file (`match: "handle"` for one read on screen,
  `creator_folder` for a creator whose every clip carries it), then build.
- **People:** the filing is carried as filed. Never read ethnicity from a picture.
- **No slicing.** The library hands out times; the editor cuts. Nothing is cut or copied by these tools.
- Shared words change in `components/asset-index/library/vocabulary.json`, brand words in the brand file; then build.

### The board (sifting footage for an edit)

A page on the machine, never a published page: `components/asset-index/library/board/serve.py`, at
http://localhost:8915 (launch entry `footage-library`; open it with the preview tool, never a terminal for the
person). Each brand with a built library has its own board at `/<brand>/`, never mixed. Filter buttons over a
picture grid of every scene; **+** on a picture adds it to Picks; **Copy shot list** copies, per shot, the beat,
product, exact in/out ("on the cut" when it sits on a shot change), what is burned in, the Drive path and link.
**Put in brief** sends the picks to one brief, each for a scene of
it or for its pool: they land in `runs/video-writing/<brand>/<brief>/deliverable/picks.json` (schema
editor-picks/v1, written by `components/video-production/machine/footage.py` `write_picks`), and a pick for a
scene makes it that scene's cut in the brief's `footage.json` / `footage.md`. It reads `library.json` live, so a rebuild shows on reload. Pictures: the scene's own frame where the footage is
on the machine, else the file's Drive thumbnail (shows when signed in to Drive). The brand's page words (name,
colours, what each beat holds) are `runs/asset-index/<brand>/library/board.json`; a new brand copies one.
`--pull` keeps a checkout nobody edits current with origin and commits and pushes the picks it puts into a brief; never pass it on a working tree.

## Rules the component enforces

1. **Any brand.** `--brand` is required; nothing in the code names one.
2. **Media stays where it is.** Records and frames are written; the original clips are never copied or deleted.
3. **A clip is described when something needs it or, in a brand's footage folders, when it arrives** (the daily
   pass, inside its cap); the reason and the spend are kept in the ledger either way.
4. **A clip the search cannot confirm on the Shared Assets drive is left out and named,** never returned with a personal-drive path.
5. Never delete on the Drive mount.

## What comes back, and where it lands

- A search prints hits and writes nothing.
- `extract.py` writes `runs/asset-index/<brand>/<label>/<clip-id>/` (frames and `clip.json`).
- `describe.py` writes the description beside the clip's record and the spend into the ledger.
- `library/` writes `runs/asset-index/<brand>/library/` (library.json, coverage.json, cuts.json, check/, index-new.json).

Reply with the result and the folder it landed in (repo path or Drive folder name).
