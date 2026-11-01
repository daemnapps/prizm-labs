# The hand-off folder and the queue

*the owner, 28 Oct 2026: "clearly define the hand-off folder location and its connection to the queue so we have clear
automation for those database entries and adjustments." the owner, earlier the same day: "that's the place and only that
place."*

One folder per brief is the **only** thing that means "ready for the maker". The queue reads those folders. Nobody
files a card by hand to say a brief is ready.

## Where it lives

```
runs/handoffs/<role>/<brand>/<brand>_<product>_<brief id>/        in the repo
Shared Assets/runs/handoffs/<role>/<brand>/<same folder name>/    on the Drive (the same folder, mirrored)
```

| Role folder | Maker | Makes |
|---|---|---|
| `graphic-designer` | the team | pictures |
| `video-editor` | the team | video |

The folder name is the brief's register key with the catalog product name, e.g. `brand_a_flex-face-brush_brief-0296`.
`handoff.py` (`tools/image-edit/`) writes it; nobody builds one by hand.

## What makes a hand-off ready

| Part | Mark |
|---|---|
| `BRIEF.md`, `RUN.md`, `run.json` and `refs/` all present | **complete** |
| `returned/` has no files in it yet | **waiting** |
| `returned/` has files | **returned**, the maker has delivered |

A folder missing any of the four parts is **incomplete**. It is never shown as ready. Pack it again with `handoff.py`;
if the packer refuses, the brief is not finished upstream, so fix it there. A brief is never handed over half-made.

## What the queue does with it (automatic, every minute)

The sync (`queue_sync.py`, in Outlier) reads every hand-off folder and does this for each, with no one doing anything:

| The folder is… | The queue card… |
|---|---|
| **complete + waiting** | is in **Production** (making), reads "Ready for the team" (or the team), and has the maker's name on it |
| **incomplete + waiting** | stays where its own machines put it, reads "Hand-off incomplete", and carries **no** maker name |
| **returned** | keeps its stage from its own machines; the card shows the hand-off and how many files came back |
| not on the queue yet | gets a card, named by the brief's register title |

Every card with a hand-off carries a `pack` block: maker, role, `waiting`/`returned`, `complete`, what is missing, the
repo folder and the Drive folder. That is how a page, the team or a check finds the hand-off from the card.

**A person's call always wins.** If the team puts someone else's name on a card, or clears it, the sync does not put the
maker back. The same goes for priority, note, removed and backlog. The sync only fills `who` while it is empty.

## The check

```
python3 outlier/suite/queue_check.py            # plain-words report
python3 outlier/suite/queue_check.py --drive    # also looks inside each waiting hand-off's Drive copy
```

The sync writes the same result to `runs/queue/check.json` every minute. It asks three things:

1. Is every waiting hand-off complete, on the queue, and under its maker?
2. Does every hand-off made in the last 7 days have a card that shows it?
3. Does every finished brief on the register (`tools/image-teardown/briefs.json`, not shipped, with a run) have a
   card on the queue? The ones without one are listed by name.

A ✗ is a connection that is broken. The fix is always upstream (pack the folder, finish the brief), never a hand-edit of
the queue.

## What the team and the team do

They open Claude Code in this workspace (the skill is `brief-handoff`) and say:

| They say | What happens |
|---|---|
| "What's waiting for me?" | lists their waiting hand-offs, the same ones the queue shows under their name |
| "Make brief 0296" | goes step by step: fetches that step's files, shows what it is about to make, waits for their OK, makes it, saves it into `returned/` |
| "Bring it in" | checks what came back against the brief and moves the card on |

They spend their time on refinement and taste: the OK before each generation, and judging what comes back. the team
reads the queue to see who has what and to send the Drive link to the right person.

## What does not change

- Nothing is sent to the team or the team by the queue. the owner sends the Drive link himself.
- Nothing is deleted. `returned/` only gains files.
- Finished files come back with `delivery.py`; the card then moves on with its own machines.

Related: `.claude/skills/brief-handoff/SKILL.md` (packing and bringing back), `runs/handoffs/START-HERE.md` (what the
maker reads), `runs/queue/` (the ledger).
