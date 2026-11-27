---
name: video-teardown
description: Set up and run the video-teardown machine that turns a creator video into a shot-ready creator brief. Use when someone says "set me up" / "get me started" for video teardowns, asks to run a video through the chain, wants a brief made from a video, wants creator sourcing run, asks to test a prompt change, or asks why a run is not showing on the teardowns page. Runs on the person's own machine under their own logins; it gates nothing.
---

# Video teardown

> **Activates component:** `components/video-teardown` — the sixteen-stage chain.


The machine lives at `components/video-teardown/` — the owner's teardown chain,
graduated 2026-08-25. A swiped video goes in; a brief with a picture on every
scene comes out. Thirteen stages; the first (Triage) picks the lane and
everything downstream reads that call.

External dependencies (this skill is otherwise self-contained):

- `components/video-teardown/` — the machine. `README.md` is the doctrine, in
  the owner's voice, and outranks this file on how the thing works; `machine/run.py`
  is the runner; `prompts/` holds one current prompt per stage.

**Read `components/video-teardown/README.md` before doing anything here.**
This file only says how to drive.

*(Until 2026-08-27 this skill targeted `new-workflow-design/builds/
video-teardown/` and `brief.py` — that chain was RETIRED 2026-08-25. If you
find notes or muscle memory pointing there, they are stale, not a second way.)*

## Setting someone up

Triggers: "set me up", "get me started", "first run".

Do it for them, reporting as you go — do not hand over a list of commands.

1. `git pull` from the workspace root, cloned at `~/Projects/ai-workspace`
   (the machine expects that path).
2. Check what they have, and for each gap name plainly what only they can do:
   - **claude CLI** — installed and signed in (several stages run through it).
   - **`~/.gemini.env`** — one `GEMINI_API_KEY=…` line, `chmod 600`. Required:
     the video-reading stages are Gemini. Never ask anyone to paste a key into
     the chat (workspace rule 6) — point at the file or their password manager.
   - **`~/.apify.env`** — same shape, only needed for creator sourcing
     (`sourcing.py`).
   - **Google Drive for Desktop** — signed in, Shared Assets visible. This is
     how finished runs reach the team: the bundle mirrors to
     `Shared Assets/lab/the owner/video-teardown-machine/machine/runs/` and the
     platform adapter files it onto the teardowns page from there. Today a
     missing mount silently skips that mirror (the run still works locally) —
     card VT-1 (mount glob + loud failure) is making its absence loud.
3. **Any of those missing? Offer the mini route below — do not improvise.**
   A missing key is not a reason to open the video yourself or reach for
   another tool; it is the moment to say what is missing and offer the run
   that needs none of it.
4. Offer a proving run on one short video. Say first that it is thirteen
   stages of model calls, several of them Opus, and takes minutes. Run it only
   if they agree, then read the actual brief rather than trusting the exit code.

## Sourcing a creator, and picking what to run

Triggers: "pull her posts", "run this profile", "get her content", "run
<handle> through apify", a bare profile link, or any request to tear down "a
video by X" where no specific post is named.

From `components/video-teardown/machine/`:

    python3 sourcing.py --creator <handle-or-profile-url>
    python3 sourcing.py --all          every creator on the tracker
    python3 sourcing.py --list         who is on it

It indexes up to 200 posts, scores each one `views + likes + comments`, keeps
the top ten, and files them on the Drive under
`lab/the owner/swipe/creators/<handle>/posts/NN-<shortcode>/`. Needs
`~/.apify.env`. A re-pull replaces the previous ten but never deletes a post
folder that has teardown work in it.

**Then pick — and picking is not the ranking.** The score is engagement
arithmetic and nothing else: no model reads the posts, nothing opens a frame,
nothing asks whether a person is on camera. Rank 1 is the most-engaged post,
which is not the same as the best source.

Before running anything, open `thumbnail.jpg` in the post folder and look at
it. Then check it against the rule below. Skipping this is what put a quote
card through thirteen Opus stages on 2026-08-26 and produced a brief with no
person in it.

**Only video ads get torn down (the owner, 2026-08-27.)** The source has to be
the creator performing — talking to camera, doing the thing, on screen. These
are NOT sources, however well they scored:

- a quote card or text block over stock footage or scenery
- a still, a photo dump, or a carousel
- a mirror selfie or b-roll whose whole content is the caption over it

Triage will not catch these. Its `STATIC / SEQUENTIAL` lane tests the *file*,
so anything delivered as a real mp4 with motion and an audio track passes as
`ORGANIC` and the full chain runs. The check is yours, before the run starts.

Tell the operator which post you picked and why, and name the runners-up — a
post with a problem said out loud usually tears down harder than an
inspirational one, and they may want a different call.

## The mini route — a run without any local setup

Triggers: "I don't have the keys", "can the mini run it", a setup step that
fails, or anyone who wants a run without installing anything.

**If a local prerequisite is missing, offer this instead of improvising.** Do
not open the video yourself, do not download it, do not substitute a different
tool. Improvising is how the first attempt at this failed on 2026-08-27: a
session met a missing key, opened the link in a browser, and nothing ever
reached the mini.

File a `workflow-requests` record and push. The mini's 60s tick picks it up and
runs the WHOLE chain on company keys:

```
{"schema":1,"kind":"workflow-requests","reviewer":"<person>",
 "item":"teardown-run-<slug>",
 "verdict":{"action":"teardown-run","source":"<path>","brand":"<brand>",
            "requested_by":"<person>"},
 "created":"<UTC>","via":"<person>-session"}
```

Write it into `platform/data/records/workflow-requests/`, named
`<UTC-stamp>--<person>--teardown-run-<slug>.json`, then commit and push — the
push IS the trigger. The run comes back on the teardowns viewer carrying
**their** name: `ran_by` is the requester from the record, `venue` is `mini`.

**`source` IS A PATH, NOT A LINK — and this is the current ceiling.** The
request takes a folder of videos the mini can already reach (a Drive path
under Shared Assets, typically). A bare Instagram URL is **not** servable by
the mini today: URL ingestion lives in `sourcing.py`, which is a local tool
needing `~/.apify.env`, and `run.py` itself only ever takes paths. So:

- video already on the Drive → mini route works now.
- only a link, and no local setup → say so plainly. Either someone with the
  local setup runs `sourcing.py` first (which puts the posts on the Drive,
  and then the mini route works), or they wait. **Do not pretend the link
  will work, and do not fetch it yourself to fill the gap.**

## Running a video

From `components/video-teardown/machine/`:

- One video: `python3 run.py <file> --brand <brand> --route <creator|ai|founder>`
  — **ask the owner which route before running.** Without `--route` the swipe is
  only torn down and writing waits (the route lock, 2026-09-30). Records file
  to `runs/video-teardown/<brand>/<slug>/` (what was read) and
  `runs/video-writing/<brand>/<slug>/` (what was written; the brief is in its
  `deliverable/`).
- A folder: `python3 run.py --source <folder> --brand <brand>` (skips what's
  done; `--again` reruns)
- Her own post: add `--creator <handle>` — without it the run is treated as
  swipe research (brief unassigned, no frames)
- Pictures: none any more (2026-09-30) — every brief carries the swipe file link
- See the chain: `python3 run.py --brand <brand> --stages` (the parser wants
  `--brand` even here; it reads nothing from it for this)

`--brand` is named every time, deliberately — a default would quietly hand one
brand's files to another. Never hard-code a brand name into anything you write
(workspace rule 7).

Instagram sourcing is its own tool: `python3 sourcing.py --creator <handle>`
indexes her page, keeps the ten best posts, and lays them out on the Drive.
It needs `~/.apify.env`.

Say what a run will cost before starting one you proposed.

## Testing a prompt change

1. The new version is a **new file** in that stage's `prompts/` folder —
   version number bumped, never an edit in place. Retired versions go to the
   folder's `archive/`.
2. The machine resolves to the highest version automatically; nothing to point
   anywhere.
3. Run a video, read the version line per stage, and tell the operator what
   actually ran — that is the whole evidence the change was tested.

## Where runs show up

1. **The run folder**: `runs/video-teardown/<brand>/<id>/`. Every stage's prompt
   and output is in it.
2. **The Drive bundle**: a run whose bundle reached Shared Assets has its poster,
   clip and pictures there. A bundle that is missing means it never reached the
   Drive — check the mount, then check the run's own `run.json` for a mirror error.
3. **A Google Doc**, made by the run itself (stage 9, `drive.py`), in that
   run's own Drive folder beside the source video. That is the copy the owner and
   the team edit before it goes to the creator, so it is the deliverable to
   hand over — its link is on the run as `gdoc_url`. Re-running the same brief
   updates that same Doc rather than leaving a second copy, so a link already
   sent stays correct. It needs `GDRIVE_SA_KEY` in `~/.daemn/keys.env`; if the
   Drive is unreachable the step says it skipped and the run still finishes.

## Never

- Commit media. Not one byte — bundles live on the Drive; the platform
  streams them (workspace rule 3).
- Edit `components/video-teardown/machine/` casually — the owner owns the folder
  (its CLAUDE.md carries the rules; an owner-of-record escalation is in force
  while he is away, scoped to the VT-* cards, and he reviews on return).
- Point any config at an absolute path under one person's home or Drive
  mount — that is what made the retired chain un-runnable for anyone but its
  author.
- Gate a run on brand fit. No stage checks it; flag a poor fit and keep going.
- Pick a source off the sourcing rank without looking at it. The rank is
  engagement, not judgement, and nothing downstream re-checks it.
- Hand-build a page, doc or deliverable the machine already produces. If the
  output shape is wrong, fix the stage that makes it — a one-off crafted in a
  session exists exactly once and never again.
