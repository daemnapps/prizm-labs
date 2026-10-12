# meta-upload — the joiner

**Owner: the owner (engine and definitions both). Component since 2026-09-29**, moved out of
`lab/meta-upload/` on the owner's word: *"this uploading thing … needs to just be in a component
now, versus the lab."* Split out of `image-production` 2026-09-10 on his call: *"image production and
uploading to meta are completely different."*

| New-resident question | Answer |
|---|---|
| Engine + owner | `build.py` (the import sheet), `prepare.py` (images into the library, ad sets into the account), `naming.py` (campaign / ad set names, the 50-cap deal), `brand.py`, `meta.py`, `review_page.py` — the owner |
| Definitions + curator | per brand, `brands/<brand>/meta/account.json` (ids, defaults, name templates) — the owner; Meta's own `template-headers.json` / `AdsManagerTemplate_v2.3.xltx` |
| Plane | none in the repo of its own — `build.py` writes only under `--out` (the caller's run folder, `runs/meta-upload/<brand>/<label>/` by convention): `import.csv`, `images/`, `summary.json`; `upload.py`'s hand-off road keeps `plan.json`, `state.json` and `live-ids.json` under `runs/meta-upload/<brand>/<hand-off name>/upload/` (SI-27 (upload state home), 2026-10-07). **The card road writes on the Drive**, under `to_check.cards_root()` (`--root`, else `$META_CARDS_ROOT`, else `Shared Assets/meta/`): `<brand>/1-check|2-approved|3-live|sent-back/<lane>/<ad name>/` (the media + `card.json`), `learnings.jsonl` + `learnings/<step>-<name>/<brand>.md`, and `live.jsonl` |
| Manifest | none — the account file is read, not executed |
| Runs by | person |

**Names** come from `components/naming/` (the short form, 2026-09-29): each batch goes in as one Meta ad
named `brand_product_brief_batch_funnel`, into the `adset_brand_avatar_angle` ad set its brief sets; the
campaign name comes from the brand's account file plus `--funnel`.

**It is brand-agnostic** (2026-09-12). No tool here names a brand; every one
takes `--brand <name>` and reads `brands/<brand>/meta/account.json`. Adding a
brand is writing that file — see RUNBOOK.md, *Adding a brand*.

**Every brand goes in by bulk import** (the owner, 2026-09-12) — one procedure,
whatever the account. Where an account's API is open it can pre-load the
images and pre-make the ad sets, which is an accelerator on that same
procedure, never a second way of working.

**It owns nothing.** the owner, same day: *"the meta uploader just needs to link
the assets together and create the import sheet properly filled out."* That is
the whole job. Pictures are made elsewhere, copy is written elsewhere, the
record is kept elsewhere. This reads all three and emits one sheet.

If you find yourself putting content in this folder, it belongs somewhere else.

## What it reads

| input | home | owned by |
|---|---|---|
| the pictures, named to the 13 fields | `../image-production/runs/<brand>/<batch>/ads/<unit>/` | image-production |
| the words | `../copy/output/<slug>/copy.json` | the copy machine |
| what each asset is | `../creative-ledger/records/creative-asset/` | the creative ledger |
| the offer, the avatars, the angles | `brands/<brand>/` | the brand |

## What it emits

`build.py`: one import sheet on Meta's own template, plus the picture files named
exactly as the sheet references them. The sheet is disposable — rebuild it any
time from the four inputs above. What `upload.py` writes is whatever it writes
(read `upload.py`; the Plane row above names its homes) — this section does not
restate it.

## The join

**The 13-field ad name.** It carries brand, product, media, source, talent,
avatar, problem, angle, concept, format, brief, ratio, batch — so a picture
finds its copy on `format` + the talent's sub-avatar, and Meta's report finds
its way back to both. Drop the last field of any filename and you have the ad
unit it belongs to.

That join is the only contract for the DATA between these folders. Code crosses only through the LIBRARY clause below (the names other components import) and the commands in the lane-feeder table; anything else that crosses is a reach, not a contract.

**A LIBRARY — the public surface** (SI-120 (library clauses drafted), 2026-10-08, triage action 6 (declare public surfaces), PROVISIONAL — the developer signs on the owner's behalf; he may strike any line). Callers put this folder on `sys.path` (today they insert it at 0) or load one file by path, and may use only these names:
1. **`to_check` — the one card writer:** `plan(brand, lane, fmt, media, words=, links=, made_by=, *, ad_name=, …)` → the card plan; `show(p)` → its printout; `cards_root(root=None)` → the `meta/` folder (`--root`, else `$META_CARDS_ROOT`, else the Drive); `Refused` (the exception every refusal raises); `SHARED` (the mount's Shared Assets). Command: `to_check.py --brand --lane …` (video-edit `line.py:121` runs it).
2. **`card_words` — the words on a card:** `empty()` → the empty shape; `from_runs(runs)` → words from copywriter stage-8 runs; `from_file(path)` → words from a `words.json` / copy file; `for_brief(brand, brief, repo=, product=)` → `(words, where)`, the approved copy set first, then the brief's copywriter runs.
3. **The feeders — one per lane:** `feed_image.feed(brand, batch, links, *, root=, dry_run=, …)`; `feed_video.file_master(brand, brief, product, batch, master, *, handoff=, run=, links=, …)` → `(plan, words_from)`; `feed_carousel.feed(folder, brand, product=, *, brief=, batch=, links=, words=, …)`, `feed_carousel.slides(folder)` → `(order, gaps)`, `feed_carousel.batch_for(root, brand, product, brief, run)`; `feed_creator.feed_root(brand, watched, since=, …)`. Each is also a command (the lane-feeder table above).
4. **The account:** `brand.Brand(name)` → `.account_id`, `.token_key` (the key's NAME); `meta.Meta(brand)` → `.get(path, **params)`, `.post(path, **params)`; `meta.token(name=)` → the key's value, read from the Keychain by name; `meta.BASE` (the Graph API base, versioned).
5. **The learnings hook**, loaded by file path (`learnings.py`): `prompt_block(tool, step, brand)` → the text a prompt hook appends, `""` while that tool's switch in `learnings-hooks.json` is off; `show(tool, step, brand)` → recent rejections printed to the run log, no prompt changed.
6. **SEAM, not public:** `feed_carousel._rel(p)` (image-teardown `carousel.py:571`); and a feeder's module handles — `feed_carousel.T` / `feed_carousel.N`, `feed_image.T`, `feed_creator.T` — which callers use today to reach `to_check` (and naming's `names`). What they reach through `T` is item 1; the handle itself is no promise, and `N` is naming's surface, not this one's. A seam renamed keeps its old name as an alias until its callers move.
Everything else — `cards`, `upload`, `build`, `prepare`, `naming`, `drop`, the desk pages — is internal and may change without notice.

## What is here

| file | what |
|---|---|
| `build.py` | **the builder.** Reads the four inputs, writes `import.csv` + an `images/` folder + `summary.json` |
| `brand.py` | **where brand context enters.** One class, one file per brand; run it to see every brand and what each is missing |
| `prepare.py` | images into the library, ad sets into the account — steps 2 and 3, resumable |
| `naming.py` | **what things are called.** Campaign, ad set, and how a drop over 50 ads is cut into ad sets. Nothing types these names by hand |
| `STRUCTURE.md` | the account's limits, where we sit against them, and why one drop = one ad set |
| `AdsManagerTemplate_v2.3.xltx` | Meta's own template, downloaded from the 1. Brand B account 2026-09-10. Kept so nobody re-downloads it |
| `template-headers.json` | its 143 column names, in order, machine-readable |
| `RUNBOOK.md` | **the procedure** — the order a drop goes in, and every trap between the steps |
| `BULK-IMPORT.md` | the column reference: the three import situations, the CBO shape, every allowed value, and what the template will not carry |

## Lane feeders (1 Oct 2026)

Every lane's last step makes the folder the owner approves from (CARD.md): `Shared Assets/meta/<brand>/1-check/<lane>/<ad name>/`
— the media copied in and renamed, plus `card.json`. One writer, `to_check.py`; one feeder per lane. Nothing here
reaches Meta. Root: `--root`, else `$META_CARDS_ROOT` (tests, proofs), else the Drive. `--dry-run` everywhere prints
the card and writes nothing. An ad already in 2-approved / 3-live / sent-back is never re-filed.

| lane | command | called from |
|---|---|---|
| image | `feed_image.py --brand --batch <drop> --links <ids>` | `variations.py --to-check --links …` (opt-in) |
| video | `feed_video.py <video-edit run or hand-off>` | `handoff_run.py` right after give_back() (live runs only) |
| carousel | `feed_carousel.py <sequence run or slide-NN.png folder> --brand --product` | `sequence.py --to-check` |
| creator | `feed_creator.py --brand` | `delivery_rule.py --apply --to-check` |

**Words** (`card_words.py`) come only from the copywriter's stage 8 render — bodies, HEADLINES, DESCRIPTIONS. The
image feeder finds the run by the drop's own copy.csv body text (that is how the lost headlines come back); the
others by the brief's number/alias in a copywriter run label, a copywriter run whose source sits in the brief's own
run folder, or a `words.json` beside the media. None found → empty lists, and the card fails its check. A brief
with no words yet gets them from `tools/copywriter/machine/brief_words.py` (the copywriter's chain, unchanged).
**Pages** (2 Oct 2026): `--links` when given, else the brief's own `landing_page` (`components/naming/page_pick.py`,
picked when the brief is written). Tests: `tests/test_to_check.py`.

## The uploader (1 Oct 2026)

`upload.py <ad-uploader hand-off>` plans a drop (talks to nothing); `--go` builds it in the account
through the Marketing API (v25, Meta's flexible format via `creative_asset_groups_spec` on the ad, all AI enhancements off; one Prizm Labs key `daemn-PRIZM_META_TOKEN` for every account) — only for a hand-off the owner approved in `approvals.json`, and nothing
at all before his first go. One flexible ad per unit per landing page, the drop's own words
(`drop.py` reads `copy.csv`), pictures or finished videos, ids written to the runs home and back to the hand-off's
`returned/live-ids.json` (its declared return) and the ledger; a hand-off half done before 2026-10-07 resumes from its old `returned/upload/state.json`. `--all-approved` runs every approved drop. What's blocking it and the owner's clicks:
`GO-LIVE.md`. `build.py --handoff <folder> --out <dir>` is the sheet fallback for the same drop.

## The approval card (1 Oct 2026) — the road every new ad takes

Four lanes (video · image · carousel · creator) end in one place:
`Shared Assets/meta/<brand>/1-check/<lane>/<ad name>/` — the media plus `card.json` (**CARD.md** is the
standard). The folder moves 1-check → 2-approved → 3-live, or sent-back; never copied, never deleted.

| file | what |
|---|---|
| `cards.py` | list / load / save / move cards; the machine checks written into `card["checks"]` (media kind and count per lane/format, 9:16, words, name, pages live + on the funnel list, product = page product, ad set, campaign, Page ad-cap headroom). The joins come from `upload.card_plan`, not a copy of them. `META_CARDS_ROOT` points it at a scratch tree |
| `approve.py` + `approve.html` | **the approval page**, http://localhost:8795 (launch config `meta-approve`, 127.0.0.1 only). To check / Approved / Live / Sent back / **Learnings**, brand and lane filters. Who is deciding: a name from `approvers.json`, picked once per browser, written on every decision. **Approve → Meta** is disabled while a check fails; it writes `card.approval`, moves the card to 2-approved and runs the uploader. **Disapprove** needs one or more reasons from `reasons.json` (each names the upstream step + tool that caused it) and a note; the card goes to sent-back carrying them and one line goes to `meta/learnings.jsonl`. `--root <tree> --fake-meta` for trials (nothing reaches Meta) |
| `learnings.py` + `reasons.json` + `learnings-hooks.json` | **the system learns from a disapprove (2 Oct 2026).** learnings.jsonl → one digest per step and brand, `meta/learnings/<step>-<name>/<brand>.md`; the Learnings tab groups by step and tool. Upstream tools read it through one marked `APPROVAL-PAGE LEARNINGS HOOK` each: prompt hooks (video-teardown, copywriter stage 8, image draft judge, video-edit cut, image-edit) add text only when their switch in `learnings-hooks.json` is on — **all off** until the owner has seen the exact text; catalog check and video-production print the rejections to the run log and change no prompt |
| `upload.py` `card_plan` / `upload_card` / `carousel_ad` | one card → one ad per page, named `<ad name>_<funnel_of(link_id)>`; flexible = `flexible_ad`, carousel = `link_data.child_attachments` in slide order (`multi_share_optimized` and end card off); ids on the card, folder to 3-live, one line per ad in `live.jsonl` (on the Drive, `meta/live.jsonl`). A Meta error stays on the card (`upload_error`) in 2-approved |
| `tests/test_cards.py`, `tests/fake_meta.py` | the card road against a fake Meta |

**The go is an approver's click, and only that.** Nothing approves a card except the page's Approve button
writing `{"by": <a name on approvers.json>, …}` (the owner only, until he adds people); the uploader refuses any
other name; no job, session or script writes `card.approval`. `approvals.json` /
`first_go` stays for the legacy hand-off road (`upload.py <hand-off> --go`) only — the card road never
reads it.

Cleared headline-audit calls live at `runs/meta-upload/<brand>/held/held.json` — written by image-production's
`static/queue/triage.py --apply`, read by `build.py` `blocked(brand)`; the component keeps none (meta-upload#14,
K2 (brands write wall)).

## Running it

    python3 components/meta-upload/build.py --brand <brand> --lane <lane> \
        --run <copy run> --out <dir>

`--funnel` names the funnel (an id from `brands/<brand>/web/funnels/funnels.json`) for a brand whose campaign name carries it; `--shipped`, `--media` and `--lane` name the drop's ad sets; `--campaign-id`
attaches the drop to an existing campaign instead of letting Meta create a new
one on every import.

Every row lands PAUSED, campaign and ad alike. The builder never talks to
Meta — it writes a sheet and the picture files, and a person imports them.

**A picture with no copy for its format + sub-avatar is left out and listed**,
never shipped with borrowed words. `--strict` turns that into a failure.

The builder holds no account facts. The Page, the pixel, the call to action
and the rest are the brand's, read off its live account rather than guessed,
and they live in `brands/<brand>/meta/account.json`. The call to action is
one of them — the owner moved a lane to `Shop now` on 2026-09-12 because it
sells straight off the page, and that is a setting on that brand, not a
default for the folder.
