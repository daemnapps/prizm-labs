# The card — one finished ad, waiting for the owner's approve

Decided 1 Oct 2026 (the owner): four lanes — **video · image · carousel · creator** — each ends in one last
folder; every delivery gets the same approval card; **Approve** sends it into Meta. Nothing goes to Meta
without that click. Page: After the Edit https://claude.ai/artifact/CHKL5G75iJBT6DQzzg9Y6U

## Where

Google Drive, shared drive *Shared Assets* (mounted on your Mac under
`~/Library/CloudStorage/GoogleDrive-<you>@…/Shared drives/Shared Assets`, found by components/brandpath drive_index.mount()):

    meta/<brand>/1-check/<lane>/<ad name>/      finished, waiting for the owner
    meta/<brand>/2-approved/<lane>/<ad name>/   approved, going into Meta
    meta/<brand>/3-live/<lane>/<ad name>/       in Meta, ids on the card
    meta/<brand>/sent-back/<lane>/<ad name>/    disapproved, with the reasons and the note
    meta/learnings.jsonl                        one line per disapproval (learnings.py)
    meta/copy-edits.jsonl                       one line per change to an ad's words on the approval page (copy_library.py)
    meta/learnings/<step>-<name>/<brand>.md     the digest each upstream step reads
    meta/learnings/4-brief/<brand>-copy-edits.md   the approver's copy changes, newest first, for the copywriter

The ad folder **moves** between states; nothing is copied or deleted. `<ad name>` is the short unit name
`<brand>_<product>_<brief>_<batch>` (components/naming, names.short_unit).

## Concept and openings (2026-11-18)

The short ad name stays as it is: brand, product, brief, batch. Two things it can't say ride on the card instead,
and on the brief's own record (`components/naming/concept.py`), so a result can be read back to the part that
earned it:

- `concept`: the concept the brief names. Present only when the brief names one.
- `openings`: a video card only. One row per asset, in the card's media order:
  `{"asset": "asset-01", "file": "<ad name>_asset-01.mp4", "version": "control", "opening": "Opening 1 · Control",
  "text": "the opening's words", "from": "caller | edit record | file name"}`. The caller's own label wins
  (`--openings`, `file_master(openings=…)`); else the edit's own record beside the render says which hook a version
  was cut for; an opening that can't be read is left null, never guessed (`openings.py`).

A real filing also writes the rows onto the brief's register entry under the ad's name; a trial root never does.

## What's in an ad folder

- the media: `<ad name>_asset-01.png` … (pictures), `_asset-01.mp4` (video), `_slide-01.png` … (carousel, in order)
- `card.json`:

```json
{
  "schema": "meta-card/1",
  "brand": "Brand B",
  "lane": "image",
  "format": "flexible",
  "ad_name": "Brand B_brilliance-body-scrub_brief-0154_batch-2026-10-02-a",
  "old_name": null,
  "brief_id": "brief-0154",
  "product": "brilliance-body-scrub",
  "avatar": "spot-hider",
  "sub_avatar": null,
  "face": null,
  "angle": "pigment-memory",
  "media": ["Brand B_brilliance-body-scrub_brief-0154_batch-2026-10-02-a_asset-01.png"],
  "words": {
    "primary": ["…the ad's primary text…", "…a second version…"],
    "headlines": ["It comes right back", "Not stubborn. It's remembered."],
    "descriptions": ["Turmeric body scrub", "Hands arms legs"]
  },
  "copy_checked": true,
  "pages": [{"link_id": "link_Brand B_cpk_quiz", "url": "https://recipe.Brand B.com/Brand B-scrub-cpk/quiz/"}],
  "made_by": {"tool": "image-edit", "run": "runs/image-edit/Brand B/261002a", "creator": null},
  "made_at": "2026-10-02T10:00:00",
  "checks": {},
  "approval": null,
  "meta": []
}
```

- One brief is one flexible ad: all of a brief's finished versions (the control and each hook) are this card's media, in order. A second waiting video card for the same brief is refused (`to_check.plan`, `second_card=True` only on purpose).
- `sub_avatar`: the sub-avatar the brief declares (brief record `sub_avatar`, one of the avatar's `sub_avatars` in `brands/<brand>/core-avatars/avatars.json`), so a brief traces to its sub-avatar on the card and in the finished-ads index. A sub-avatar not filed under the card's avatar is refused. The ad set stays avatar × angle.
- `face`: the demographic on screen (gender/age-band/ethnic-appearance), the brief record's `moves.face` from `components/creative-diversity/check.py --brief`. Demographics are not part of an avatar or sub-avatar (`components/GLOSSARY.md`); they are traced per creative here.
- `format`: `flexible` (several pictures or videos rotating in one ad — image, video, creator lanes) or
  `carousel` (slides in order, one swipeable ad — carousel lane).
- `copy_checked`: true when the words came from a copywriter run that passed the read-back copy check (stage 8c,
  2026-10-09). The board labels a card "Copy checked · ready" or "Copy not checked yet · don't upload".
- `words`: up to 5 of each; at least 1 primary text, 1 headline and 1 description. Never invented downstream: a lane
  that has no headline leaves the list empty and the card fails its check. An empty description is filled at filing
  with the line most of the brand's live cards carry (the same product's first; never a price, an offer or a dated
  line); none found leaves it empty and the check names it. Switch: `description.json` (`check`, `fill`), row
  DESCRIPTION in `team/rollbacks.md`.
- `thumbs`: `{"<video file>": "<cover file>"}`, a cover per video. A waiting video card with a video that has no
  cover is not ready (`cover_rule.py`, check `cover_each`).
- `cover_records`: `{"<cover file>": {"swipe", "frame": {"video", "video_sha256"?, "t", "file", "own"?}, "version",
  "headline", "record"}}`, written by the filer from the record of each cover (`cover_rule.py` says where it is read).
  `swipe` is the id of the cover it follows in the cover index; `frame.video` is the card's own name for the video the
  frame was cut from, once the filer proved it (its sha256 or its path); `own: false` marks a frame the filer could
  not prove came from that video.
  Checks `cover_swipe`, `cover_frame` and `cover_differs` read it and the cover files.
- `made_by_tool`: `{"<picture file>": {"sha256", "record"}}`, the image-production record of each picture and
  cover filed (`made_by_tool.py`, RULE GATE-5).
- `pages`: landing pages by catalog link id (`lab/the owner/catalog/data/catalog.json`), each becomes its own
  Meta ad named `<ad name>_<funnel id>-<page>` (`…_body-scrub-cpk-quiz`, `…_body-scrub-cpk-offer` — the way the
  live ads read; made in one place, `components/naming/page_pick.meta_page`, through handoff `funnel_of`).
  A lane that names no page gets the brief's own `landing_page`, chosen when the brief was written
  (`components/naming/page_pick.py`, 2 Oct 2026).
- `checks`: written by the machine checks — `{"<check>": {"ok": true|false, "why": "…"}}`.
- `approval`: written only by the approval page on an approver's click (names in `approvers.json`) —
  `{"by": "the owner", "at": "…", "decision": "approve", "start": "PAUSED"|"ACTIVE"}` or
  `{"by": "…", "at": "…", "decision": "disapprove", "note": "…", "reasons": [{"id", "label", "step", "tool"}]}`
  (older cards carry `"send-back"` with a note only).
- `meta`: written by the uploader — `[{"link_id", "meta_ad_name", "ad_id", "at"}]`.

## The tools
`cards.py` (list, move, machine checks) · `approve.py` (the approval page, port 8795 — the only writer of
`approval`) · `learnings.py` (disapprovals → learnings.jsonl → per-step digests; `reasons.json` the reason list,
`approvers.json` who decides, `learnings-hooks.json` the prompt switches, all off) · `upload.py upload_card` (card → Meta, run by the page after the click; writes `meta`,
`upload_error` on a failed try, and `live.jsonl` on the Drive).

**Writer:** `to_check.py` (one door for all four lanes; feeders listed in CLAUDE.md, *Lane feeders*).
