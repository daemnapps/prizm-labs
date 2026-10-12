# The card — one finished ad, waiting for the owner's approve

Decided 1 Oct 2026 (the owner): four lanes — **video · image · carousel · creator** — each ends in one last
folder; every delivery gets the same approval card; **Approve** sends it into Meta. Nothing goes to Meta
without that click. Page: After the Edit (team page)

## Where

Google Drive, shared drive *Shared Assets* (mounted on your Mac under
`~/Library/CloudStorage/GoogleDrive-<you>@…/Shared drives/Shared Assets`, found by components/brandpath drive_index.mount()):

    meta/<brand>/1-check/<lane>/<ad name>/      finished, waiting for the owner
    meta/<brand>/2-approved/<lane>/<ad name>/   approved, going into Meta
    meta/<brand>/3-live/<lane>/<ad name>/       in Meta, ids on the card
    meta/<brand>/sent-back/<lane>/<ad name>/    disapproved, with the reasons and the note
    meta/learnings.jsonl                        one line per disapproval (learnings.py)
    meta/learnings/<step>-<name>/<brand>.md     the digest each upstream step reads

The ad folder **moves** between states; nothing is copied or deleted. `<ad name>` is the short unit name
`<brand>_<product>_<brief>_<batch>` (components/naming, names.short_unit).

## What's in an ad folder

- the media: `<ad name>_asset-01.png` … (pictures), `_asset-01.mp4` (video), `_slide-01.png` … (carousel, in order)
- `card.json`:

```json
{
  "schema": "meta-card/1",
  "brand": "brand-a",
  "lane": "image",
  "format": "flexible",
  "ad_name": "brand-a_glow-body-scrub_brief-0154_batch-2026-10-02-a",
  "old_name": null,
  "brief_id": "brief-0154",
  "product": "glow-body-scrub",
  "avatar": "avatar-four",
  "angle": "pigment-memory",
  "media": ["brand-a_glow-body-scrub_brief-0154_batch-2026-10-02-a_asset-01.png"],
  "words": {
    "primary": ["…the ad's primary text…", "…a second version…"],
    "headlines": ["It comes right back", "Not stubborn. It's remembered."],
    "descriptions": ["Turmeric body scrub", "Hands arms legs"]
  },
  "copy_checked": true,
  "pages": [{"link_id": "link_brand-a_cpk_quiz", "url": "https://recipe.brand-a.example/brand-a-scrub-cpk/quiz/"}],
  "made_by": {"tool": "image-edit", "run": "runs/image-edit/brand-a/261002a", "creator": null},
  "made_at": "2026-10-02T10:00:00",
  "checks": {},
  "approval": null,
  "meta": []
}
```

- `format`: `flexible` (several pictures or videos rotating in one ad — image, video, creator lanes) or
  `carousel` (slides in order, one swipeable ad — carousel lane).
- `copy_checked`: true when the words came from a copywriter run that passed the read-back copy check (stage 8c,
  2026-10-09). The board labels a card "Copy checked · ready" or "Copy not checked yet · don't upload".
- `words`: up to 5 of each; at least 1 primary text and 1 headline. Never invented downstream: a lane that
  has no headline leaves the list empty and the card fails its check.
- `pages`: landing pages by catalog link id (`lab/catalog/data/catalog.json`), each becomes its own
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
