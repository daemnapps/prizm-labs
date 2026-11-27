---
name: brief-handoff
description: Hand a written brief to its designer, editor or production agent, bring finished files back, and check delivery completeness. Use for "hand this brief off", "make brief", "pick up a brief", "work on brief", "check what came back", "did the editor deliver", or "bring the deliveries in".
---

> **Activates component:** `components/image-edit` (`handoff.py` packs the folder, `delivery.py` brings the work back) with `components/briefs` (`runsheet.py`, the tool-agnostic run sheet inside every folder).

Resolve the maker and reviewer from the current brief and `components/promo-calendar/definitions/roster.json`. Names in examples are not assignments. Use `components/WORKFLOWS.md` to distinguish AI production packages, human creator filming briefs and static-image handoffs.

External dependencies: `components/image-edit/handoff.py`, `components/image-edit/delivery.py`, `components/briefs/make.py`,
`components/briefs/runsheet.py`, `components/briefs/briefs_index.py`, `components/briefs/backfill_brief_key.py`,
`runs/BRIEFS.md`, `runs/handoffs/START-HERE.md` (what the maker reads),
`components/naming/WHERE-EVERYTHING-GOES-owner.md` (the map), `components/model-inputs/lessons.json` (where a fix
from a returned file is written).

**One brief in, one folder out, finished files back in that folder's `returned/`.** The folder is the same on the repo
and the Drive: `runs/handoffs/<role>/<brand>/<brief key>/` = `Shared Assets/runs/handoffs/<role>/<brand>/<brief key>/`.
Roles: `graphic-designer` (pictures) and `video-editor` (video). Proven 2026-10-28 on brief 0232 (6 pictures, 14 min)
and brief 0075 (video).

Read the component rules in `components/image-edit/CLAUDE.md` and `components/video-edit/CLAUDE.md` before choosing a door.
The writing run and register determine `production_route`; conflicting claims refuse and must be fixed upstream.
`creator` and `founder` use the existing `video-editor` folder with `packet_kind: filming-assignment`: verbatim filming
instructions, stable asset IDs, expected takes and `RETURN-MANIFEST.template.json`. They do not enter Higgsfield.
`state: draft` / `execution_ready: false` means planning only; `make.py plan` refuses generation for that packet.
For human returns, copy the template to `returned/return-manifest.json`, preserve IDs, provide file SHA-256,
explicit reviewer acceptance, A/B-roll and timed speech words; run
`python3 components/image-edit/delivery.py --brand <brand> --ingest-filming <handoff-folder> [--dry-run]`.
A valid return creates `edit-kit.json` for `video-edit/machine/run.py start`; repeated identical intake is a no-op.
Raw takes cannot go through `delivery.py --send`; the finished edit owns final delivery.

## 1 · Pack the folder (free, spends nothing)

```
python3 components/image-edit/handoff.py <brief id or key> --brand <brand>                 # the lane picks the role
python3 components/image-edit/handoff.py <brief key> --brand <brand> --role video-editor    # name the role outright
```

The folder gets BRIEF.md, RUN.md + run.json (the run sheet: model, exact prompt, references, settings, asset names,
return place, written three ways: A for a person in the Higgsfield web app, B for an agent with the Higgsfield tools,
C for Codex or any other agent), refs/ with every reference picture, voice read and start frame, and an empty
`returned/`. A video brief also gets RUN.md's "The format" section and `format/` with the format's `FORMAT.md` and
`LEARNINGS.md` when the format has a home (`components/video-production/formats/README.md`, One home per format). The whole folder is mirrored to the Drive. A video folder takes a few minutes to upload.
A brief that is not finished in its chain is refused by name. Fix it upstream; never hand over a half brief.
A video brief's RUN.md ends in **the cut**: every clip in step order, cut into one 9:16 video named
`<brief key>-control.mp4`.

**An older brief is brought up to the standard, never skipped** (2026-10-28). Before packing it:
- The folder name uses the catalog product name (`Brand A_flex-face-brush_brief-0075`, not `Brand A_flex_brief-0075`).
  Move an old-spelling folder to the new name on the repo and the Drive. Move it, never copy it, never delete it.
- The run records carry the right number: `python3 components/briefs/backfill_brief_key.py --fix-briefs --apply`
  corrects the clear cases. `runs/BRIEFS.md` lists the rest under collisions; those are the owner's calls.
- Check the brief with `python3 components/briefs/briefs_index.py find <brief>`. Every station should show up.

## Per-brief usage

Before making or revising a brief in Claude Code or Codex, follow
`components/briefs/README.md#measure-a-brief-session`. If the pickup hook has not
already confirmed this brief/stage/revision, run `python3 components/briefs/make.py
pickup <full-key> --stage <stage>`. It uses runtime session context; never guess
IDs or claim tracking is active after a refusal. Each independent session picks
up separately. Keep unknown identity/model/effort fields unknown. Release the
binding with `/brief-release` before unrelated work.

## 2 · Make an execution-ready AI packet in Higgsfield

**the editor or a creator in Claude Code, with the Higgsfield tools (the standard way, 2026-10-28).** What they say, and what you do:
- **"What's waiting for me?"**: `python3 components/briefs/make.py waiting --role <graphic-designer|video-editor>`
  (reads the Drive; a hand-off whose `returned/` is empty).
  Both makers' lists show only briefs the owner approved (`components/briefs/approved.py`, 2026-11-25). The approved
  hand-off goes straight to the maker's queue: no message is drafted or sent. When the owner
  says yes to a brief in their own words, record it: `approved.py add <brief key> --how "<where they said it>"`. Never
  record one they did not say.
- Brief numbers repeat across products (0310 can be FLEX, face scrub and body scrub), so use the full brief key from the waiting list and `--brand`.
- **"Make brief 0341"**: for each step in turn:
  1. `python3 components/briefs/make.py plan 0341 <step>`. It fetches the step's files and prints the files to
     upload, in order, plus the exact call.
  2. `media_upload` each file in that order (PUT the bytes, `media_confirm`), put each media id where the plan says,
     then call the tool with the plan's params. Never retype or edit the prompt.
  3. Show the person what is about to be made and wait for their OK before each call: it spends credits.
  4. When it has finished, save the `show_generation_by_ids` reply unchanged to a file, then
     `python3 components/briefs/make.py save 0341 <step> --record <file>`. It downloads, names, saves to `returned/`
     here and on the Drive, and checks it.
  5. Show the person the picture or clip. If it is wrong, say what is wrong and remake it with the same plan.
  - Video: after the last clip, cut every clip in step order (RUN.md's cut step), then
    `make.py save <brief> cut --file <the cut>`.
- **"Bring it in"**: step 3 below. "It came out wrong: <what>" is a lesson (step 3's last paragraph).
The walkthrough they read: https://claude.ai/artifact/X6anK5J2qPT2BSwuPg1GQ7.

**Higgsfield Supercomputer projects** (Brand A Production, Brand B Production) also work. One line in the brand's
project, "Make brief <brief key> (<role>)", and the project's instructions do the rest. It is slower: about 6 minutes
just to list the briefs.

**A person in Higgsfield alone:** open the folder on the Drive and follow RUN.md section A.

**An agent (Supercomputer, or us testing):** open https://higgsfield.ai/supercomputer, start a **new chat**, and paste
`references/supercomputer-message.md` with the folder's Drive link filled in. Then:
- It asks before every generation and every Drive save. Read what it is about to send. The prompt must be the run
  sheet's, word for word, and the pictures must be in the order the sheet gives. Then press **Approve**. Never press
  "Always allow".
- If it reports that a take came out wrong and asks to remake it, approve the remake. If it changes the prompt,
  stop it.
- Its final message lists every file saved and everything in RUN.md it could not follow. Keep that list.

## 3 · Bring it back and check it

```
python3 components/image-edit/delivery.py --brand <brand> --role <role> --dry-run   # what is new
python3 components/image-edit/delivery.py --brand <brand> --role <role>             # bring it in
```

The files land in the repo's `returned/` and the brief's `delivery.json` records each one ({drive_id, label}).
- Read the folder's `REFERENCE-CHECK.md` (the check runs on every bring-in; alone:
  `python3 components/image-edit/reference_check.py <hand-off folder>`): per file, receipt · prompt · inputs · looks.
  A ✗ is fixed in the chain or the file is re-made; a – with "no receipt" means ask the maker for the receipt.
Look at every file next to the swipe (a contact sheet for pictures; the first frame and the voice for clips).
Anything wrong is fixed in the chain, never by hand: one row in `components/model-inputs/lessons.json` plus the line
that makes the chain obey it, then pack the folder again.

## 4 · Onto the approval page (only on the owner's word)

```
python3 components/image-edit/delivery.py --brand <brand> --send <role>/<brief key>
```

Files one card in `meta/<brand>/1-check/`. Nothing goes live until the owner presses Approve.

## Report

One line per brief: how many files came back, which held and why. Then the finished ads as a picture
(a contact sheet, or the video link). No paths, no commands.

## Never

- Never send or draft a message to a maker. The queue is how an approved brief reaches them (2026-11-25).
- Never delete anything on the Drive. `returned/` only ever gains files.
- Never let the maker change a prompt. A better prompt goes into the chain and the folder is packed again.

## Complete delivery and revisions

Read `components/briefs/delivery-completeness.md`. Every design/editor handoff must issue its full deliverable checklist with `delivery_contract.py pack`. Creative changes are allowed; incomplete scope or unchecked returns stay with the maker. Submit only the current revision through `delivery_contract.py submit`; never reduce the issued checklist to fit returned files.
