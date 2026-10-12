---
name: handoff
description: Hand work to a role — creator-manager, creator, clipper, graphic-designer, video-editor, ad-uploader or klaviyo-uploader — as one checked folder (handoff.md + manifest.json), or refuse and say which id is unknown. Use whenever the owner says hand this off, hand off <briefs> to the <role>, send the batch to the uploader, package this for the editor, the clipper kit, or names a role and a brief or batch. LAB — in development under components/handoff-standard/skill; not registered in .claude/skills until it graduates.
---

External dependencies: the brief register (`tools/image-teardown/briefs.json`),
the catalog (`lab/catalog/data/catalog.json` today; the folder of records the
catalog tool writes tomorrow — `--catalog`), `components/naming` (ids in both
spellings, the name parser), `components/brandpath` (the brand's folders),
`components/ad-handoff` (a drop's landing pages), the drops at
`runs/image-edit/<brand>/<batch>/deliverable/`.

**One command. It writes one folder, or it refuses.**

```
python3 components/handoff-standard/skill/handoff.py <role> <brand> <brief ids | batch id> [--offline] [--ids ids.json] [--no-drive]
python3 components/handoff-standard/skill/handoff.py take-back <role> <brand> <hand-off name>
```

Roles: `creator-manager` · `creator` · `clipper` · `graphic-designer` · `video-editor`
(`--kit <folder>`) · `ad-uploader` · `klaviyo-uploader` (`--email-run <folder>`).
Brief ids in either spelling (`brief-0140`, `p140`); a batch in either
(`batch-2026-09-23-a`, `260923a`) takes every ad in that drop.

## What it does, in the standard's order

1. **Gather by id** — the brief from the register, its brief.md from its run
   folder (or the brand's briefs folder), its ads from the brand's drops with
   their copy rows, and the product / offer / link / part ids it declares.
2. **Check** — every product, offer, link and part id against the catalog; the
   role's inputs present (the brief itself, the ads, a copy row per ad, a link
   by id, an edit kit, an email run); every ad name parses; links answer 200
   unless `--offline`. A publish role (clipper, ad-uploader, klaviyo-uploader)
   also needs the offer live.
3. **Write** — `<staging>/<role>/<brand>/<role>-handoff_<brand>_<date>/` (no
   other level; `--staging` defaults to `runs/handoffs/`) with `handoff.md` (the
   same 8 sections every time), `manifest.json` (every id, every check, every
   file in assets/), `briefs/`, `assets/`, `references/`, `returned/`.
   **assets/ holds the actual files**, copied in: the ad pictures, the edit kit
   (`--kit`), the email run's `deliverable/` and `media/` (`--email-run`). A
   file is looked for in this checkout, then the main checkout (a worktree has
   no media), then the Drive mirror; one that is found nowhere refuses.
   **Ads carry the 29 Sep short form** (`components/naming`: `short_unit`,
   `short_file`, `short_meta`): pictures sit in `assets/ads/<brand_product_brief_batch>/`
   as `…_asset-NN`, and each ad is listed with one Meta ad name per landing
   page (`brand_product_brief_batch_<funnel>`, the funnel being the link id's
   page part) and its old 13-part name beside it — live ads keep their old
   names on Meta.
4. **Drive** — the finished folder is **copied** to
   `Shared Assets/handoffs/<role>/<brand>/<name>/` through the Drive mount
   (`handoffs/` is created once), and that path is recorded in
   `manifest.json` (`drive.written`, `drive.path`). Copy only: sharing is
   never changed, nothing is deleted, a folder already on Drive is never
   overwritten (the next name is `-2`). No mount refuses before anything is
   written. `--no-drive` skips the copy; called from code (`run()`), the copy
   is off unless `drive=True`.
5. **Ledger** — one line per event (`sent` · `refused` · `returned`) in
   `<staging>/ledger.jsonl`, or `--ledger`.
6. **Take back** — `take-back` reads `returned/`, joins every file to its brief
   and asset id, records the live ids from `returned/live-ids.json` as
   `live_meta_<id>` / `live_klaviyo_<id>`, and writes the ledger record.
   Nothing in `returned/` is published by that step.

## The creator manager's command

`creators.py` sits on top of this tool for creator briefs: `pick --brand <b> --brief <id>`
ranks the brand's talent cards against what the brief asks (avatar, sub-avatar,
gender, age, look, language, lane) with the reason for every point; `handoff
--brand <b> --brief <id> --creator <card id>` writes the folder through this tool
(role `creator`) plus the card and a DRAFT message — nothing is sent; `track`
lists waiting / footage back across every creator hand-off and runs `take-back`
where footage has landed. See `../agents/creator-manager.md`.

## A refusal is the answer

An id the catalog does not know, a brief the register does not know, a landing
page with no link id, a missing role input, an ad name that does not parse —
each is named with its reason and **no folder is written**. Do not work around
it. What the brief record does not carry yet (today: the offer and the link
ids) goes in a sidecar, `--ids ids.json`:

```json
{"brief-0140": {"offers": ["offer_<brand>_..."], "links": [{"id": "link_<brand>_...", "url": "https://..."}]},
 "*": {"links": [{"id": "link_<brand>_...", "url": "https://..."}]}}
```

`"*"` applies to every brief in the hand-off. A drop's own `links.json` labels
are matched to declared links by URL; a URL nobody named by id refuses.

## Rule 6

Every role stops before anything goes live: sending a brief to a creator,
posting a clip, uploading to Meta, scheduling or sending in Klaviyo. The
package says so in section 7; the role agents (`../agents/<role>.md`) stop
there too. Nothing goes live without the owner's go.

## What to send back to the owner

One line: READY with the folder name and the ids counted, or REFUSED with each
missing thing on its own line. No paths, no commands.

## Tests

`python3 -m unittest discover -s components/handoff-standard/skill/tests` — offline,
no network, no key, no brand name in the code (the brand comes from the
register). The Drive step is tested against a temporary folder standing in for
the mount; the real Drive is never touched by a test.
