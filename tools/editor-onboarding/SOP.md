# How creative marketers work with us — the SOP

Clippers, creators, editors and designers all use Prizm Labs from their own
account: **Higgsfield Supercomputer** (nothing to install) or **Claude Code**.
The repo is public — open it in your account, point it at a brand, run the
tool. Work comes to you in your own hand-off folder on Google Drive, and
finished work goes back into the same folder.

The walkthrough video and this page, together, are the whole onboarding:
**daemn.co/onboarding.html**.

---

## Your hand-off folder

`Shared Assets/handoffs/<role>/<brand>/<your name>/` on Google Drive. Each
hand-off in it carries a `handoff.md` — what this is, who it is for, what is
inside by id, what to do, what must not change, the links, the checks, and
how to send it back — plus `briefs/`, `assets/`, `references/` and an empty
`returned/`. You read `handoff.md`, do the job, and put the finished files in
`returned/`, each named `<brief id>_asset-NN`. The team runs the take-back
from there; you never edit anything else.

## Once — set up (ten minutes)

1. **Get your hand-off folder link.** One Google Drive link from the team.
   A Higgsfield account of your own is enough.
2. **In Higgsfield Supercomputer → Connectors → Explore**, connect **Google
   Drive** and **GitHub**. Sign in to each when asked. (In Claude Code, clone
   the repo and connect Google Drive the same way.)
3. **Put the folder in your own Drive.** Open the link, then in Google
   Drive: right-click the folder → *Organize* → *Add shortcut* → into a
   folder you make in *My Drive*. Supercomputer can only see what is in your
   own Drive.
4. **New chat in Supercomputer → the `+` button → Connectors** — check Google
   Drive and GitHub are both ticked for that chat.
5. **Paste the Day-one prompt** (`prompts/01-day-one-v3-damon.md`) with the
   brand, your role and the folder link filled in. It clones the tools, opens
   your folder and tells you what is waiting. When it ends with *"Set up for
   <brand> — N hand-offs waiting"*, you are done.

## Every session — the loop

1. **New chat → paste the Pull-briefs prompt** (`prompts/02-pull-briefs-v3-damon.md`)
   with the brand and your role. Name a brief if you have one; otherwise it
   takes the newest hand-off with an empty `returned/`.
2. **It syncs first** — pulls the tools for updates, reads your folder live.
3. **It reads `handoff.md` and lays the brief out**: the scenes with their
   clips and voices (or the image drafts), what must not change, the known
   issues, the loop. Read it. Watch every clip.
4. **Review** — it walks the checklist with you: same person, same wardrobe,
   same product, slop, sound, words, anything odd. You get a table: KEEP /
   FIX AT CUT / REROLL. Then three to five ideas. **You decide** what gets
   rerolled and which ideas to take.
5. **The asks** — the extras the brief wants: scroll stoppers, headlines,
   variations, extra scenes, formats, styles. It makes them in Higgsfield
   from the same cast and product references. You approve each one.
6. **The edit** — for video, the video-edit tool makes the cut itself and
   stops twice for you: the **timeline**, then the **captions**. You approve
   or ask for one change in plain words at each stop. For statics, the
   approved finals go in one folder.
7. **Send it back** — finished files into the hand-off's `returned/`, each
   named `<brief id>_asset-NN`. It walks the checks in `handoff.md` with you.
   The team takes it back from there.

## The rules that never move

- **Nothing invented.** Not a product detail, not a claim, not a person. If
  the brief does not say it, the answer is "not in the brief" — ask.
- **Every face and every product carries its reference.** A person or product
  generated without their reference is a reroll, not a delivery.
- **One ratio.** Everything is made and cut at 9:16, with faces, the product
  and every word inside the centred 4:5 crop — the middle 70% of the frame.
  Nothing is made at 4:5 or 1:1. A swipe that arrives 4:5 or 1:1 is rebuilt at
  9:16 the same way.
- **Never write into the hand-off's briefs, assets or references.** Finished
  work goes in `returned/` only.
- **Sync first, every session.** A brief made from yesterday's tools or a
  stale folder is the one that gets sent back.
- **When a door fails — Drive, GitHub, Higgsfield — say which one, in one
  line.** Do not work around it silently.

## When it goes wrong

| what you see | what it means | what to do |
|---|---|---|
| "Something went wrong" opening your folder | Supercomputer picked the wrong folder or cached an old one | Paste the folder's Drive link directly into the chat |
| No credits / "no chats" | Wrong Higgsfield workspace, or the free credits are used | Switch workspace (top-left) and refresh, or ask the owner |
| It found the wrong folder | Two folders share the name | Give it the path or the link; it must not guess |
| A hand-off you finished still shows as waiting | The files are not in that hand-off's `returned/` | Move them into `returned/`, named `<brief id>_asset-NN` |
| "Pull my GitHub repository" says no updates but the SOP changed | The clone is stale | Say "clone https://github.com/daemnapps/prizm-labs again, fresh" |

## Coming next (not yet — do not wait for it)

- A brief-download skill in Higgsfield, so "pull briefs" is one word.
