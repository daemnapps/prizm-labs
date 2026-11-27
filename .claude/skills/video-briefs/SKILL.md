---
name: video-briefs
description: The video editor's two commands. List the video editing briefs waiting for a brand, and open one, ready to edit, in HyperFrames or Premiere. Use when the editor says "pull up my video editing briefs for <brand>", "what briefs do I have", "my editing briefs", "open brief <number> in premiere", "open brief <number> in hyperframes", "load brief <number>", or names a brief number and an editor.
---

> **Activates component:** `components/video-edit/open_brief.py` (Mac and Windows).

The editor says two things; everything else is yours to do without asking.

## "Pull up my video editing briefs for <brand>"

Run `python components/video-edit/open_brief.py list <brand>` (Windows: `py`). Show the editor the table it prints:
brief number, what it is, which editors it opens in, open or back. Nothing else.

## "Open brief <number> in <hyperframes | premiere>"

Run `python components/video-edit/open_brief.py open <number> <hyperframes|premiere>`. It copies the brief from the
shared drive to `~/VideoBriefs/<brief key>/` (their own working copy), then:

- **hyperframes**: opens the edit in the HyperFrames app.
- **premiere**: sets up the Premiere bridge the first time (`prpr`; if it says to restart Premiere, tell the editor
  that one line, then run the same command again), builds the project with the rough cut assembled (every scene,
  product, word card, caption and sound its own clip) and opens it. Nothing is left for the editor to set up.

If HyperFrames is missing, it installs it (needs Node; install Node first if `npm` is missing). If Python is missing on
Windows, install it from python.org, then run the command again.

Tell the editor in one or two lines what opened and where the finished master goes (`returned/` in their copy). Then
the edit is theirs: help them with whatever they ask, in that editor. `EDITING.md` inside the brief lists how to drive
each editor (Premiere through `prpr`).

## When they're done

Read `VIDEO-DELIVERY.md` in the handoff (source: `components/briefs/video-delivery.md`). Follow its checklist for every requested opening/variation and one distinct thumbnail per finished version, including the cover production steps, provenance records and approval-card pairing. Read the actual `BRIEF.md` even when a pack index lists no separate hook files. Raw creator/founder takes keep their filming-manifest return; the final editor owns the video-and-cover delivery.

The completed videos, covers, records and checklist go in `returned/` of their copy; copy them into the same brief's `returned/` on the shared drive
(`Shared Assets/runs/handoffs/video-editor/<brand>/<brief key>/returned/`) and say it's in.

## Complete delivery and revisions

Read `components/briefs/delivery-completeness.md`. Every design/editor handoff must issue its full deliverable checklist with `delivery_contract.py pack`. Creative changes are allowed; incomplete scope or unchecked returns stay with the maker. Submit only the current revision through `delivery_contract.py submit`; never reduce the issued checklist to fit returned files.
