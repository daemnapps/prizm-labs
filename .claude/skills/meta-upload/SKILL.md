---
name: meta-upload
description: Get a finished ad drop ready for Meta without touching the ad account — build the drop kit (the import sheet plus the picture files) and file finished ads into the approval folder `Shared Assets/meta/<brand>/1-check/` (the approval page). A brief's videos (the control and every hook) go in as ONE flexible ad. Finished ads and their copy go in; a kit folder or filed ad folders come out. Approval and going live are the owner's click, never this skill's. Use whenever someone says "build the drop kit for <brand>", "make the import sheet for <brand>", "file the <brand> image batch for check", "put this <brand> video in the check folder", "send the <brand> carousel to 1-check", "file the creator delivery for <brand>", "show me what the card would say, don't write it", "what is waiting in 1-check for <brand>", "send this to the approval page", "get it on the Meta approval page", "load it into the account".
---

# Meta upload — drop kit and the check folder

> **Activates component:** `components/meta-upload` — `build.py` builds the drop kit; `feed_image.py`, `feed_video.py`, `feed_carousel.py` and `feed_creator.py` (each through `to_check.py`) file a finished ad into `1-check`.

External dependencies: `components/meta-upload/` (the engine; `CLAUDE.md`, `CARD.md`, `RUNBOOK.md`, `BULK-IMPORT.md` are its rules), `components/naming/` (ad and ad set names), `components/copywriter/` (the words on every card), `brands/<brand>/meta/account.json` (the brand's account facts — read, never written), `brands/<brand>/briefs/` (each brief's header), the finished ads from `runs/image-teardown/<brand>/`, `runs/image-edit/<brand>/` or a video-edit run, and the Drive folder `Shared Assets/meta/`.

## The walls — read first

- **Approval and going live are the owner's click.** The approval page is his; nothing a teammate or a session does approves a card, makes an ad live, spends, pauses, or changes a budget. This skill stops at `1-check`.
- Never run `upload.py`, never run `approve.py`, never write `card.approval`, never import a sheet into Ads Manager. Those reach Meta; they are not this skill's job.
- Never move a card out of `1-check`. An ad already in `2-approved`, `3-live` or `sent-back` is never re-filed.
- Never write a key, a token or an account id anywhere. Keys come from the environment by name only.

## Two jobs a teammate may do

### 1. File a finished ad into the check folder (the usual one)

One command per lane. Always run the `--dry-run` form first: it prints the card and writes nothing. Show the person the card, then run it for real when they say so.

```
python3 components/meta-upload/feed_image.py --brand <brand> --batch <drop> [--links <link ids>] [--briefs <brief ids>] --dry-run
python3 components/meta-upload/feed_video.py <video-edit run or hand-off folder> [--links <link ids>] [--batch <batch>] --dry-run
#   a brief with several versions: feed_video.file_master(brand, brief, product, batch, [control, hook1, hook2, …]) — one card
python3 components/meta-upload/feed_carousel.py <sequence run or slide-NN.png folder> --brand <brand> [--product <product>] [--brief <brief>] [--batch <batch>] [--words <words.json or copywriter run>] --dry-run
python3 components/meta-upload/feed_creator.py --brand <brand> [--folder <watched folder>] --dry-run
```

Drop `--dry-run` to file it. `--replace` re-files an ad that is still waiting in `1-check`. `--root <meta folder>` points at a scratch tree instead of the Drive (leave it off unless you are testing).

If the finished ad does not fit those four, the one door underneath is `to_check.py --brand <brand> --lane video|image|carousel|creator --media <files in order> [--words …] [--links …] --dry-run`.

### 2. Build the drop kit (the import sheet)

The sheet is the fallback way of getting a drop into an account; building it touches nothing in Meta.

```
python3 components/meta-upload/build.py --brand <brand> --lane <lane> --run <copy run> --out <dir> [--shipped YYMMDD] [--funnel <funnel id>] [--strict]
python3 components/meta-upload/build.py --handoff <ad-uploader hand-off folder> --out <dir>
python3 components/meta-upload/review_page.py --kit <dir> --out <dir>/upload-kit.html
```

`build.py` has no `--dry-run`; it writes only under `--out`, so give it a run folder (`runs/meta-upload/<brand>/<label>/` by convention). `--strict` fails if any picture has no copy; `--campaign-id`, `--adset-ids`, `--hashes` attach to things already in the account and are the owner's to supply. Importing the sheet into Ads Manager is a person in a browser touching the account: that is the owner's, not this skill's.

What a person can check before the kit leaves: `python3 components/meta-upload/brand.py` lists every brand and what its account file is missing (reads only).

## What it reads

- The finished pictures or video, named to the convention (`components/naming`).
- The words: only from the copywriter's finished render (bodies, HEADLINES, DESCRIPTIONS). The image feeder finds the run by the drop's own `copy.csv`; the others by the brief's number in a copywriter run, or a `words.json` beside the media.
- `brands/<brand>/briefs/` for the product, avatar, angle and landing page; `brands/<brand>/meta/account.json` for the account.

## The rules it enforces — do not work around any of them

0. **One brief is one flexible ad.** Every finished version of a brief (the control and each hook) goes into the same card as `asset-01`, `asset-02` … — one filing with all the masters, control first. Never a card per version. A second waiting video card for a brief is refused; add versions by re-filing that card with every master (`--replace`).
0b. **Words: the brand's proven copy.** When the brief has no copywriter run, the card carries the primary text and headline of the brand's banked winner on the same product (`runs/winners/<brand>/bank.json`), passed in as the card's words, `copy_checked` true. No copywriter run is made for a video brief.

1. **Words are never invented.** None found means empty lists, and the card fails its check. A picture with no copy for its format and sub-avatar is left out of the kit and listed.
2. **Every ad has a name** built from `<brand>_<product>_<brief>_<batch>`; a name that does not parse is refused.
3. **Pages:** `--links` when given, else the brief's own landing page. Each page becomes its own ad.
3b. **Campaign and ad set: the Ad Directory.** Where an ad goes is read from `runs/meta-upload/<brand>/DIRECTORY.md` (built from the data warehouse by `components/meta-upload/directory.py --brand <brand>`): its page's funnel → the live campaign, its brief's avatar × angle → the ad set. Read it before filing; if a page shows no live campaign there, say so and stop rather than pick another campaign.
4. **Nothing reaches Meta from these commands.** Every kit row lands PAUSED; the feeders only copy media and write `card.json`.
5. **An ad folder is moved between states, never copied or deleted** — and this skill never deletes on the Drive.
6. **A refusal is the answer.** The commands raise a refusal naming what is missing (no brief, no product, wrong ratio, no words). Fix what it names upstream or say who owes it; do not edit `card.json` by hand.

## What comes back, and where it lands

- **Filed ads:** the Drive folder `Shared Assets/meta/<brand>/1-check/<lane>/<ad name>/` where `<lane>` is `video`, `image`, `carousel` or `creator`. It holds the media renamed `<ad name>_asset-01.png` (or `.mp4`, or `_slide-01.png` for a carousel) and `card.json`. The card's machine checks (media, 9:16, words, name, pages, ad set) are written into it.
- **Drop kit:** the `--out` folder (by convention `runs/meta-upload/<brand>/<label>/`) holding `import.csv`, `images/` and `summary.json`; the optional `upload-kit.html` review page lands beside them.
- the owner approves from `1-check` and the ad then moves to `2-approved` and `3-live` by his click. Tell the person plainly: it is waiting for the owner.

Report: how many ads were filed, any the card check failed and why (one clause each), and what is held back. If the Drive is not mounted or a key is missing, say so in one line and stop.

Reply with the result and the folder it landed in (repo path or Drive folder name).
