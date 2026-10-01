# editor-onboarding

The front door for the people who make our ads — clippers, creators, video
editors and graphic designers. They work from their own **Higgsfield
Supercomputer** or **Claude Code** account, with these tools from GitHub. Work
arrives in their own hand-off folder on Drive
(`Shared Assets/handoffs/<role>/<brand>/<name>/`): they read `handoff.md`, put
finished work in `returned/`, and the team runs the take-back.

**The page:** [daemn.co/onboarding.html](https://daemn.co/onboarding.html) —
the walkthrough video, the SOP and the prompts, in one place.

| | |
|---|---|
| `DESK.md` | the other side — what the person onboarding an editor does: folders by link once per brand, one message per editor, what to check. Team-only; it is not a page on the site. |
| `SOP.md` | the way we work — once to set up, then the loop every session. What the page says, in Markdown. |
| `prompts/01-day-one-v3-damon.md` | pasted once: connects, clones the tools, opens your hand-off folder, reads each `handoff.md` |
| `prompts/02-pull-briefs-v3-damon.md` | pasted every session: sync → pick → read `handoff.md` → review → the asks → the edit (two review stops) → back into `returned/` |
| `machine/queue.py` | the work queue per brand — every role (video editor, graphic designer, creator, carousel), every state from Open to Live or Sent back — written to `briefs/QUEUE.md` on Drive from the folders and approval cards. Runs hourly. Tests: `machine/test_queue.py`. |
| `walkthrough/cut-list.json` + `cut.py` | the edited walkthrough video — a cut list over the recorded call, rendered with ffmpeg. The recording is not in the repo. |
| `context/artifacts.md` | the pages that show this work |

## What the brief now carries

The handoff every editor receives ends with **`## THE ASKS`** — scroll
stoppers, headlines, variations, extra scenes, formats, styles — each specified
or refused with a reason. The list and its defaults:
[`../video-production/ASKS-SPEC.md`](../video-production/ASKS-SPEC.md).
The Pull-briefs prompt reads it; when a handoff predates it, the prompt applies
the default menu.

## Two homes, on purpose

The **tools** live here, in the public repo. The **briefs** — runs, packs, brand
material — never do: they live in the private workspace (`AI_WORKSPACE`,
default `~/Projects/ai-workspace`) and on Google Drive, which is where editors
read them. Nothing in this folder reads a brief from the repo.

## Keeping Drive and the tools in step

Three directions, all automatic:

- **Workspace → Drive.** `queue.py ship --auto` (hourly) finds every run in
  the private workspace whose pack cleared its gates (`deliverable/EDITOR-PACK.md`
  exists), zips it into the brand's `briefs/ai-video-production/` on Drive —
  once; a brief already on the queue is never duplicated or overwritten. Image
  and carousel briefs marked approved in the workspace's brief register (ready
  to make) are packaged the same way into `briefs/image/` and `briefs/carousel/`.

- **Tools → editors.** The Pull-briefs prompt pulls the repo before anything
  else, every session. A change committed here reaches every editor the next
  time they sit down.
- **Drive → queue.** `queue.py build --all` runs hourly on the owner's Mac
  and rewrites each brand's `briefs/QUEUE.md` from the folders: a package (or a
  creator hand-off folder) makes a brief **Open**, a claim file (a hand-off
  marked sent) makes it **Claimed**, files in `delivered/` (or the hand-off's
  `returned/`) make it **Delivered**, and its approval card in
  `meta/<brand>/1-check|2-approved|3-live|sent-back/` makes it **In check**,
  **Approved**, **Live** or **Sent back** (with the owner's note). Each row
  shows `<product> brief-NNNN` with its old code, looked up in the private
  workspace at run time. Renamed deliveries are matched back to their package.
  Bounty, due and who are the owner's, set with `queue.py set`, and survive
  every rebuild. The hourly job runs from a clean copy of this repo
  (`~/Projects/prizm-labs-queue`, on origin/main), never a working checkout.
- **One queue.** When the private workspace carries its Asset Ledger, the
  ledger is the single source: the hourly job rebuilds it from the Drive and
  `queue.py build` hands QUEUE.md to its renderer, so the table also sees the
  older delivery folders, the cards and the live ads. Same columns, same
  hand-set fields. The folder reading above is the fallback without a ledger
  (or with `QUEUE_FROM_FOLDERS=1`).

## Run it

    python3 machine/queue.py build --all                                  # every brand
    python3 machine/queue.py ship --auto                                  # finished runs → Drive
    python3 machine/queue.py ship runs/video-machine/<brand>/<run> --brand <brand>
    python3 machine/queue.py set --brand <brand> <brief> bounty="$150" due=2026-09-30
    python3 walkthrough/cut.py walkthrough/cut-list.json <recording.mp4>  # re-cut the video

`DRIVE_ACCOUNT=<google account>` picks the Drive mount; unset, the first one
found is used.
