# naming — the vocabularies every asset and page is named from

**naming** — takes **a brief, a page or a delivery folder**, makes **the name —
ad, file, folder, page format — and the creative record for what was
delivered**. Does not **invent a name: a name not in its bank is an error**.
Triggered by importing it (`names`, `classify_pages`, `page_pick`, `record`)
or `python3 components/naming/delivery_rule.py --brand <brand>`.

**Owner:** the owner (definition and engine both).

Runs by: person

**A LIBRARY** (the developer, 2026-10-07, triage action 3 (definition lines and registry rows), provisionally on the owner's
behalf — he is told and may object): callers import `names.py`,
`classify_pages.py`, `page_pick.py` and `record.py`; `deliver.py` and
`delivery_rule.py` run as commands. The contract below says what each one is.
**Graduated from `lab/the owner/naming/` on 2026-09-11**, when live pages started
depending on it. the owner: *"for the formats we're still pulling from lab."* Lab
is for work still being figured out; a standard production leans on cannot
live there (workspace rule 9).

## What this is

The single place a name is *looked up* rather than chosen. Three vocabularies,
each with exactly one home:

| Field | Decided by | Home |
|---|---|---|
| `format` | `classify_pages.py:page_type()` — reads the page | here |
| `angle` / `concept` | the brand's own signed angle bank | `brands/<brand>/strategy/angles.json` |
| `avatar` | the brand's own avatar folders | `brands/<brand>/core-avatars/` |

**Nothing here invents a name.** Coining one silently forks the vocabulary and
every report built on it; a name that is not in its bank is an error, not a new
entry. Only the owner signs an angle active.

## Four things, and the test that tells them apart

Ruled 2026-09-11, after the angle bank turned out to be half formats and one
duplicate. The four get confused because they all feel like "an idea for an
ad", so each one gets a test that settles it without taste:

What avatar, sub-avatar, demographic, angle, moment, idea, hook and format mean, and the test for each: **`components/marketing-doctrine/slices/words.md`**,
the one home. This section only says how the names relate.

**How they relate.** An angle belongs to the BRAND, not to an avatar
(the owner, 28 Oct 2026: "angles are just ways to start the conversation and each conversation varies by language of the avatar but the approach is the same"). An angle is a way to start the conversation, and any angle can be
aimed at any avatar. The avatar's language and the swipe being mined or briefed
decide how it is said, never whether it may be used. An angle's `avatar` field
records where it was found, and is a hint only. Where an angle meets an avatar
is the ad set (`adset_<brand>_<avatar>_<angle>`) and the brief. Sub-avatars it
serves are declared per page or per asset (`page_subs`), never as another angle.
Format is orthogonal to both: any angle, for any avatar, can be told in any
format.

    avatar ──┐
             ├──> brief / ad set (avatar × angle) ──> told in any format
    angle ───┘    (the avatar's language says the angle; sub-avatars declared per asset)

**The two rules that stop the bank filling with things that are not angles:**

1. **Same claim, narrower person → a sub-avatar, not a new angle.**
   `forty-year-shaver` was `razor-not-problem` aimed at a sub-avatar. As a
   separate row it split the reporting on one claim across two lines, which is
   the exact thing the naming scheme exists to prevent.
2. **Same claim, different container → a format, not a new angle.**
   `slideshow-native` was "carry the proven three-line-hook into the slideshow
   container". `barbershop-canon` said outright it was `transform-new-man`
   inside a room's shape. Neither is a claim; both are construction.

The same two rules apply one level down, inside the format library: a format
with the same mechanic and different footage under it is a **variant of that
format**, not a new format. Thirteen of the fifty were variants.

**Nothing enters a bank because it is interesting.** An angle needs a claim and
a receipt that resolves; a format needs a mechanic and the posts behind it
counted. `unreviewed` is the honest default and only the owner moves anything to
active.

## The contract

```
CONVENTION.md      how an ad is named          brand-media-avatar-format-concept-ratio-batch
PAGES.md           how a page is named         page ID <brand>_<place>_<page>; address format-angle[-sub]
page_list.py       the one page list (pages.json): IDs, steps, versions, tests, the daily check
WHERE-THINGS-GO.md where words and media live  words in git, media on the drive

classify_pages.py  page_type(row) -> one of ten formats. The only decider.
names.py           build, parse and check an ad name; read a brand's signed angles
deliver.py         the delivery step — renames a finished run and writes its manifest
delivery_rule.py   names every delivery an editor or designer drops on Drive, from its brief;
                   `--to-check` also files each named delivery as a card in meta/<brand>/1-check/creator/ (meta-upload)
record.py          appends the creative record for what was delivered
repo_paths.py      stored paths made portable (rule 4): to_portable / to_local, `scan|fix [roots] [--apply]`
products.py        one product record for every brand (2026-11-16): any name -> id, name, bank page, kit, Drive packshots, gaps; `record|check`
selfcheck.py       exercises every claim the conventions make against the real code
```

Consumers read the documents and call `names.py` / `classify_pages.py`. Nothing
outside this folder reproduces a vocabulary or re-implements a rule — the
duplicate is what drifts.

**Public names — the only ones a caller may use** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line):
1. **`names`** — building and reading: `slug`, `SLUG`, `parse`, `parse_any`, `parse_short`, `ad_name`, `asset_name`, `asset_n`, `short_unit`, `short_file`, `short_meta`, `audit`; batches: `batch_id`, `norm_batch`, `next_batch`; briefs: `brief_id`, `brief_code`, `brief_forms`, `brief_number`, `brief_key`, `parse_brief_key`, `is_brief_id`, `next_brief_number`, `find_brief`, `brief_header`, `brief_record`, `brief_angle`, `brief_aliases`, `brand_briefs`, `register_rows`, `AmbiguousBrief`, `PER_PRODUCT`, `BRIEF_NEW`, `BRIEF_OLD`, `brief_key_forms`, `catalog_key` (the catalog form a new folder is named with); products (2026-10-28, one product id — the catalog id; store handles are aliases): `product_id(brand, any_name)`, `product_aliases(brand, catalog_id)`, `product_ids(brand)`; vocabularies: `AD_FIELDS`, `CREATIVE_FIELDS`, `MEDIA`, `SOURCE`, `UNCLASSIFIED`, `signed_angles(brand)`, `swipe_id(brand, ad_id)`. Each returns what its name says — a name, a parsed dict, an id or `None`; a value not in its bank raises or is `None`, never invented.
2. **`classify_pages.page_type(row)`** → one of the ten formats (also run as a command). **`page_pick`**: `pick(brand, brief, …)` → the landing page (`page_ids` beside `link_ids`); `landing_ids(brand, brief, product)`; `landing_page_ids(brand, brief, product)`; `page_ids_of(refs)`; `meta_page(page ID or link id)`. **`page_list`** (2026-11-14, the one page list): `load`, `save`, `is_page_id`, `parse_page_id`, `page_id`, `long_name`, `run_label`, `find(any ref)`, `meta`, `control`, `funnel`, `next_version`, `reserve_version`, `file_build`, `set_control`, `add_test`, `test_problems`, `end_test`, `check`, `write_check`, `backfill`, `STEPS`, `JOBS`, `RESULTS`, and the command. **`angle_pick`**: `pick(brand, brief, product)`, `record(brand, result)`, `auto(brand, brief, product)` (the hook at brief registration), and the command.
3. **`record`**: `write`, `item_id`, `made_from_manifest`, `prompt_for`, `human`. **`deliver`**: `deliver(folder, fields, extra=, batch=, dry=)`, `from_brief(brief)`, and the command. **`delivery_rule`**: `load`, `resolve`, `is_work`, `ratio_of`, `to_check`, `launch_sheet`, and the command.
4. **`repo_paths`** (2026-10-28, builder card rule 4 (stored data references)): `to_portable(s)` (a clone of the workspace → repo-relative, a Drive mount of Shared Assets → "Shared Assets/…", anything else unchanged), `to_local(obj, labels=)` (the reader's half), `kind(path)`, `hits(text)`, `scan(paths)`, `fix(paths, apply=False)`, and the command. Callers inside a chain use run-kit's `paths.portable` / `paths.local`, which load it. Tests: `tests/test_repo_paths.py`.
5. **`products`** (2026-11-16, one product record, the same way for every brand): `record(brand, any_name)` → the catalog id, `name`, `bank` page, `kit` (what, kind, size, `refs`), `drive` packshots (id + "Shared Assets/…" label), `words`, `missing`; `check(brand=None)` → every product and what it is missing; and the command (`record <brand> <name>`, `check [<brand>]`). Every tool that names, shows or makes a product reads it here, so a product is identified one way in every brand. Tests: `test_products.py`.
6. **SEAMS, not public:** `names._ALIASES` (image-teardown's `briefs.py` resets it to `None` after writing `brief-aliases.json`), `names._PRODUCTS` (the product table cache; `None` re-reads the kits, the Drive index and `product-aliases.json`) and `names._workspace_root(start)` (video-edit's `deliver.py`). A seam renamed keeps its old name as an alias until its callers move.
Everything else in these files is internal and may change without notice.

## The four new-resident questions

- **Engine + owner:** the code above — `classify_pages.py`, `names.py`,
  `deliver.py`, `delivery_rule.py`, `record.py`, `page_pick.py`,
  `selfcheck.py`. **the owner.**
- **Definitions + curator:** `CONVENTION.md`, `PAGES.md`, `WHERE-THINGS-GO.md`
  and `registry.json`. **the owner.**
- **The plane it emits:** creative-asset records, filed by `record.py` under
  `lab/the owner/creative-ledger/records/creative-asset/` until the developer rules on
  them landing on `platform/data/records/` (its docstring says so); and,
  with `--apply`, `delivery_rule.py` writes `naming.json` into each delivery
  folder and rebuilds `READY-TO-LAUNCH.md` at the top of the watched folder.
- **Manifest per entry:** a creative-asset record follows
  `platform/data/kinds/creative-asset.json`.

## Brand-agnostic, and checked (workspace rule 7)

the owner, 2026-09-11: *"how can we make this all brand agnostic in the system?"*
The rule already existed; what was missing was anything that made it true.

**Brand is a parameter and a path segment, never a literal.** Three things
enforce it now, and `selfcheck.py` fails if any is violated:

1. **Brands are discovered, never named.** The checks list `brands/*/` and run
   against every brand found. A second brand is not a special case — it is
   another row.
2. **Every per-brand bank is tested for every brand.** This found a real hole
   in its first run: Brand B has no `guarantees.json` while Brand A does, and
   the wording lives in prose nobody had lifted. A genuine gap is recorded in
   the registry's `brands_missing` with its reason and printed as `[GAP ]` on
   every run — visible forever, without turning the board permanently red. A
   gap that is NOT recorded fails.
3. **No brand name in a path, an id, an asset token, or this component's
   code.** It may appear only as *data about a brand* — a recorded gap, a
   recorded conflict. This caught two usage examples in our own files that
   named a brand, which is precisely where someone copies from.

**The one place the rule and reality disagree** is recorded rather than
papered over: the 82 page section blocks are true of any brand's page and
physically live inside one brand's funnel repo. The second funnel will either
copy them or reach into another brand's repo, and both are wrong. It is in the
registry as `location_conflict`, needing a ruling before a second funnel is
built, not after.

## Running the check

    python3 components/naming/selfcheck.py

Run it after any change to a convention. A naming standard that is only a
document drifts the first time a field is added.

## The page list (14 Nov 2026)

`page_list.py` + `pages.json`: every page of every brand — funnels and the store — with its ID
(`<brand>_<place>_<page>`), its step (landing → cart → checkout → post-purchase), its versions (one holds the
control mark) and its tests (control vs variant, PostHog's field names). It replaces the page entries in the
funnel lists, the catalog's link ids, the per-funnel `pages.md` registries and the ICON `pages.json`, which now
point here. Ad briefs record `landing_page.page_ids`; a page brief (type `page`, `briefs.py page`) is opened at
the START of a page chain run and reserves its version; the page chain files the build as that version.
`page_list.py check` is the daily check. Rules: `PAGES.md`. Tests: `test_page_list.py`; `selfcheck.py` checks the
real list.

## The concept and the openings, on the brief's record (18 Nov 2026)

`concept.py` reads the concept a brief names off the brief itself (its piece block; no model) and writes it onto
the brief's register entry when the brief is registered (`briefs.py open`, every lane), and writes which opening
each filed asset carries under the ad's name when the card is filed. The short name is unchanged. `concept.py show
<brand> <brief>` prints both. Tests: `test_concept.py`.

## The landing page, at the brief (2 Oct 2026)

`page_pick.py` chooses a brief's landing page when the brief is written — sells the
brief's product, carries its offer, same page type as the swipe's page (advertorial ·
quiz · offer page · store page, read from the swipe library), answers 200 — and writes it
onto the brief as `landing_page` with its why. `briefs.py open` (every lane) runs it; the
hand-off, the card writer and the feeders read it by default. `page_pick.meta_page(link id)`
is the one place a Meta ad name's page part is made: `<funnel id>-<page>`
(`body-scrub-cpk-quiz`, `body-scrub-cpk-offer`). Tests: `test_page_pick.py`.

## The angle, at the brief (12 Oct 2026)

the owner: *"The angle should be derived from the brief itself … The angle should be in the notes of
the brief."* `angle_pick.py` reads the brief once, when it gets its number (`briefs.py open`, every
lane; `NAMING_ANGLE_PICK=off` skips it), and names ONE angle from the brand's active bank with a
one-line reason quoting the brief — or `no-fit`. Kept on the brief register entry (`angle`,
`angle_why`, `angle_state`, `angle_by`) and as a Notes line in the brief file; every stage reads it
through `names.brief_record` / `brief_angle`. Prompt `prompts/angle-pick-v1.md`; runs at
`runs/naming/<brand>/angle-<brief>/`. The map: `ANGLE.md`. Tests: `test_angle_pick.py`.
