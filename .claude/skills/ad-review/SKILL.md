---
name: ad-review
description: Review finished static pictures or a finished video cut before they are named and filed for Meta — a person looks, says what to change, and each change is made one at a time until they approve. Use whenever someone says "review the <brand> statics", "I want to review the drafts", "review this cut", "send this batch for review", "here is what to change on this one", "approve the drafts for <brand>", "this one needs fixing", or hands over a picture batch or a video run and asks for a look.
---

# Ad review

> **Activates component:** `components/review` — files the review request and the verdict (`review_request.py`); the changes themselves are made by `image-edit` (statics) and `video-edit` recut (video).

External dependencies: `components/review/review_request.py` (the request and verdict records, written to `platform/data/records/review/`), `components/image-edit/` and `components/video-edit/` (the fixes).

This is the review stage the email chain already has (`email-review`), for static and video. It sits **after the pictures or the cut are made and before `stage-check` and `naming`**. It is not the final go: that stays the owner's, on `Shared Assets/meta/<brand>/1-check/`.

## What the reviewer opens

- **Statics:** the draft or variation folder, `components/image-teardown/drafts/<brand>/vN/` (and the batch's `deliverable/` for variations).
- **Video:** `runs/video-edit/<brand>/<label>/deliverable/` after both edit stops (timeline, captions) are approved.

## The steps

1. **File the request** (dry run first, it prints the record and writes nothing):
   ```
   python3 components/review/review_request.py --title "<what is being reviewed>" --type image|video --warehouse repo --ref <the folder above> --lane static-ads|video-ads --reviewer <person> --by <person> --dry-run
   ```
   Then run it without `--dry-run`. The lane is `static-ads` or `video-ads`, never `ad-runs`.
2. **Take the changes in the person's own words.** Each change becomes **one** edit: a static change is one `image-edit` change on the picture; a video change is one `video-edit` recut (`run.py change … timeline|captions "words"`). Never batch three changes into one edit, and never regenerate a picture or scene to fix one thing.
3. **Show the result** and ask again. Repeat 2 until they are happy.
4. **Record the verdict.** Say it in words ("approve", "fix: …", "reject: …"); the session files it:
   ```
   python3 -c "import importlib.util as u;s=u.spec_from_file_location('rr','components/review/review_request.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.file_record('<RQ item id>',{'event':'verdict','verdict':'approve'},'<person>',notes='<their words>')['filename'])"
   ```
   The verdict is `approve`, `reject` or `fix`. A `fix` or `reject` carries the reasons: add `'reasons':['<their words>']` to the verdict. Read the state back with the `review-status` skill.

## Rules

1. **Never writes a card approval, never moves a card out of `1-check`, never uploads.** Final approval and going live are the owner's.
2. **Do not reuse `video-edit approve`** for this. Those two stops review one cut mid-edit; this reviews the finished deliverable.
3. One change per edit. The original is never overwritten; every edit is a new version.
4. The record is the proof. A review with no filed verdict is not done, and `stage-check` should not treat it as approved.
5. The reviewer's words are the instruction. Do not improve on them.

## What comes back, and where it lands

The request and verdict records in `platform/data/records/review/` (one file per event), and the new versions in the same folders the reviewer opened.

Reply with the result and the folder it landed in (repo path or Drive folder name).
