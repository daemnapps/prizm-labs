# Drive triage issues held for the keys / clean-up phase

Read from origin/main at 075dd518c2, 7 Oct 2026. Ruling (the developer, typed to ◆ PLAN · dev-developer, relayed verbatim to the lead): "address all of the google drive component updates, future structure all together as part of the keys / clean up migration phase", and "ok page 8 go".

**This phase (decided 7 Oct, triage page #8):** people may use their Drive mount. Everything the mini runs reaches Drive through the API by file id (O9 reworded for this phase). One Drive client per side (D1-A). The shared helpers become "mount if there is one, gdrive-creator by id if not". Hard-coded Damon-account paths go. The image-teardown Drive delete and the dead mirror are fixed. The swipe libraries are copied to their ruled home, Team Drive/swipe/, and the code switches at midnight BKK.

## Held issues

| Issue | What | Why held |
|---|---|---|
| gdrive-creator#3 | image-teardown re-implements upload twice (no esc(), sharing outside share()) | needs gdrive-creator's contract filled first |
| gdrive-creator#4 | research-gatherer exports a Sheet with its own (third) key parser | needs an export() in the engine; also key handling (keys migration) |
| gdrive-creator#5 | video-teardown updates a Doc by id with the raw client | needs update-by-id in the engine |
| naming#16 | naming's own Drive list and rename helpers | needs list/rename in the engine |
| asset-index#8 | Clip ids depend on the machine (they hash the full mount path) | re-hashing re-keys the owner's footage index that video-production's 'own footage first' check matches; only his Mac builds it today (page #12, 7 Oct) |
| asset-index#17 | The footage index lives only on the owner's Mac, so 'own footage first' is skipped elsewhere | a shared home (Team Drive mirror or the records plane) is clean-up; tonight it only says so out loud (page #13) |
| asset-index#6 | The footage pool is shared nowhere (work/ and projects/ on one Mac) | same shared home as #17 (page #13) |
| 7 Oct review/ready findings | runs/system-integration/components-gdrive-creator/20261007-0802Z-review (ACCEPT WITH CLEANUP), 20261007-0815Z-ready (READY WITH GAPS) | baseline for the restructure; the C3 list_folder pin may go earlier with the page #6 clause work |

## Accepted for this phase (mount reads by person-run tools; revisit in the clean-up phase)

casting#2, naming#7, research-gatherer#5, video-edit#2, video-edit#3, video-teardown#5, copywriter#7. Each works for anyone with Drive for desktop; none names the owner's account (grep, 7 Oct). In the clean-up phase they move to reading by file id.

## Future shape to design in the clean-up phase (◆ PLAN's notes, not ruled)

1. One pipe, two ways to sign in: the machine's service account, and the person's own Google login (OAuth) for scripts a person runs. That replaces copying service-account keys onto Macs, and belongs with the keys migration.
2. Sharing defaults to the company only; "anyone with the link" only when a person chooses it (creator_share for outside creators stays explicit).
3. The missing functions: update by id, export, list and rename.
4. Callers store the file ids they write in their run records; later reads go by id.
5. Merge the mini worker's built-in client onto gdrive-creator (the mini's /usr/bin/python3 3.9.6 imports googleapiclient, checked 7 Oct).
6. The long-term owner: the owner today; platform ownership (Operator B) is the open question.
7. The swipe libraries' repo-side move (components/swipe-* data → swipe/, ~3,700 tracked files, ~86 readers) and reading by id, by 2 Nov.
