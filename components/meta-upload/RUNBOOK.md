# Getting a drop into Meta — the whole procedure

How a creative drop gets into a Meta ad account — any brand, any account.
Every step below was walked and every trap below was hit, so the next drop
is a repeat and not a re-discovery.

**The tools name no brand.** Every one takes `--brand <name>` and reads
`brands/<brand>/meta/account.json` for the account, the Page, the pixel, the
Instagram profile and where that brand's inputs live. There is no default
brand: adding one is writing that file. See *Adding a brand* at the end.

`BULK-IMPORT.md` is the template reference — which of the 143 columns hold
what, and what values Meta accepts. **This file is the order you do things
in**, and the traps between the steps.

**Every brand goes in by bulk import** (the owner, 2026-09-12). One method, one
procedure, whatever the account — no per-brand decision about how a drop
lands. The sheet creates the campaign, the ad sets and the ads; the browser
does the three things the sheet has no column for; and nothing has to be
done one ad at a time.

| | does | cannot |
|---|---|---|
| Builder (`build.py`) | turns pictures + copy + pages into the sheet and the image folder | talk to Meta at all — it writes files |
| Bulk sheet | campaign, ad sets and every ad, in one import | Instagram identity, the pixel, the conversion event — **no columns exist** |
| Ads Manager | those three, plus anything else, as **one bulk edit each** | be trusted for current state; its table caches deleted objects |

Where an account's API is open it can pre-load the images and pre-make the
ad sets, which saves real time — but that is an accelerator on this same
procedure, not a different one. It is an appendix at the end.

---

## 0 · Before anything, know what is already in there

```
python3 components/meta-upload/brand.py         # every brand, and what it is missing
python3 components/meta-upload/meta.py <brand>  # can the token actually reach it
```

Then read the campaign back — ad sets, ad counts, status. Never work from
the Ads Manager table alone: **it caches deleted objects for several
minutes** and will happily show you 248 ads when 110 exist.

---

## 1 · Build the kit

```
build.py --brand <brand> --lane <lane> --run <copy run> \
         --out <dir> --shipped YYMMDD
```

Produces `import.csv`, an `images/` folder, and `summary.json`. Read the
summary: ads, ad sets, anything held back and why. The expired-offer gate
(`offers.json`) drops pictures whose offer bar has died — that is what took
this drop from 138 to 110.

Check the review page before the account sees it:

```
review_page.py --kit <dir> --out <dir>/upload-kit.html
```

It reads the brand off the kit's own `summary.json`, so it takes no brand flag.

That is the **RUN-01 Upload Kit** artifact. Republish over it, never a new link.

---

## 2 · Put the images in the account library

Same Import dialog as the sheet, different tab: **Import ads → Images**.
Upload the kit's `images/` folder there before importing the sheet, and the
sheet's `Image File Name` column binds each row to its picture.

Browser uploads cap at **10 MB a time**, so a 51 MB drop is six or seven
goes at that tab. That is fine — it is one dialog, and unlike chunking the
*sheet* it cannot create a second campaign.

---

## 3 · Point the sheet at the right campaign

Rebuild with `--campaign-id` so the import attaches to an existing campaign
instead of Meta creating a fresh one:

```
build.py --brand <brand> --lane <lane> --run <copy run> \
         --out <dir> --shipped YYMMDD --campaign-id <id>
```

Leave it off only for a brand-new campaign. Confirm row 2 carries the
`Campaign ID` before importing — read the CSV with `encoding='utf-8-sig'`,
because the BOM hides the first column name from a naive `DictReader` and
makes a present id look absent.

---

## 4 · Clear the account's drafts

Ads Manager → **Discard drafts** (top right).

**It discards every unpublished change in the whole ad account, not just
this campaign's.** Look at what is pending first — *Review and publish (N)*
shows you — and only discard when you know what you are throwing away. An
abandoned draft left in place will import alongside yours and you will
publish two of everything.

---

## 5 · Import

Campaign table → **More** → *Import and export ad configuration* →
**Import ads in bulk** → Choose file → Import.

Expect one warning: `Minimum ROAS · Header Label Isn't Correct`, rows 2 to
N. Harmless — an unused column in the v2.3 template. "Campaigns, ad sets or
ads with only warnings were imported" is the success message.

---

## 6 · The three things the sheet has no column for

All three are one bulk edit each, and none has to be done ad by ad.

**Instagram identity — on the ads.** Every imported ad lands without one,
and that is an error which blocks publishing. It happens every time; it is
not something going wrong.

> Ads tab → select → **Edit** → you get the column-style editor, which has
> Page but *not* Instagram → click **Cancel** → you land in the **multi-ad
> editor**, with *"Identity for N ads"* carrying both. Set it once.
>
> That Cancel is not a mistake. The column editor and the multi-ad editor
> are different surfaces and only the second carries Instagram.

**The pixel and the conversion event — on the ad sets.** Same pattern one
level up, and confirmed on a live account 2026-09-12: Ad sets tab → select
them all → **Edit** → *"Conversion for N ad sets"* carries **Dataset** (the
pixel), **Conversion event**, **Performance goal**, **Conversion value** and
**Attribution model**, all editable across every selected ad set at once.

**Call to action — on the ads.** Same multi-ad editor, `Call to action` in
the left nav. Step 8 covers it with everything else of that kind.

---

## 7 · Publish

**Review and publish** → check the three tabs (Campaign / Ad sets / Ads).

If some ads carry errors: deselect exactly those rows, tick **"Try to
publish items with errors"** — which enables the button — and publish. The
deselected ones are skipped, the rest go.

Then re-import just the failures as their own sheet.

**The known failure:** an ad whose name matches an ad in a *deleted* ad set
comes back `For deleted adgroups, you can only update the adgroup name
(#1885087)`. Meta matched your new ad to the dead one by name. Seven of 110
hit this. Re-importing them after the deletes have settled works.

So: **delete the old ad sets before the import, not after**, and give the
account a few minutes.

---

## 8 · Anything the sheet cannot express, do as one bulk edit

Same multi-ad editor as step 6. The left nav carries **Call to action**,
Primary text, Headline, Description, Website URL, Media, URL parameters.
Set the value in the **"Edit all selected ads"** row at the top and it
writes to every selected ad at once.

This is how all 110 went from *Learn more* to *Shop now* in one action.

---

## 9 · Verify against the data, never the screen

The banner says "110 ads were published". Check it yourself — read it back
through the API where the account allows it, or export the CSV from Ads
Manager and diff it against the kit where it does not. Either way the
assertions are the same:

```python
for s in m.paged(f"{CAMPAIGN}/adsets", fields="id,name,targeting,promoted_object"):
    for a in m.paged(f"{s['id']}/ads",
                     fields="name,status,creative{instagram_user_id,object_story_spec}"):
        ...
```

What to assert, every time:

- ad names in the account == ad names in the sheet, **both directions**
- every ad `PAUSED`, campaign `PAUSED`
- every creative has `instagram_user_id`
- every `link_data.link` is the landing page you intended
- every `call_to_action.type` is the one you set
- every ad set has the pixel and `PURCHASE`, age 18–65

---

## What is still blocked

**The API cannot create ad creatives.** `ads_create_creative` and a direct
`act_<id>/adcreatives` POST both return:

> *Ads creative post was created by an app that is in development mode.
> It must be in public to create this ad.*

Until the app is published and through App Review, the creative half of a
drop goes through the bulk sheet. Everything else — images, ad sets,
renames, deletes, all reads — works today.

The Ads MCP is separate and also off for this account
(`is_ads_mcp_enabled: false`). `meta.py` with the Keychain token is the way in.

---

## Appendix · the API accelerator, where an account allows it

`prepare.py` does steps 2 and 3 through the Marketing API instead: it
uploads every image and returns its hash, and creates every ad set already
carrying the pixel and the conversion event.

```
prepare.py --brand <brand> --kit <dir> --campaign-id <id>
build.py   ... --hashes <kit>/hashes.json --adset-ids <kit>/adsets.json
```

The sheet is then text only — no images folder, no upload tab, and the
ad-set bulk edit in step 6 is unnecessary because they are already right.

**This is the same procedure, faster — not a second way of working.** Steps
4 to 9 are untouched, and a brand that cannot use it loses nothing but time.

Two conditions: the ad account must grant the system user
`ads_management`, and creative creation stays out of reach regardless (see
*What is still blocked*). Whether a given account has the grant is a fact
about that account, recorded in its own file — check with `brand.py`.

---

## Adding a brand

No code changes. One file:

```
cp brands/_TEMPLATE/meta/account.json brands/<brand>/meta/account.json
```

Fill it in, then check it:

```
python3 components/meta-upload/brand.py <brand>
```

That prints every field and every input, and says which are missing. Run it
until nothing says TODO.

**Read the ids off the live account, never guess them.** `account_id` is in
the Ads Manager URL (`act=…`); `page_id`, `pixel_id` and `instagram_id` come
off an existing ad in that account.

**The token has to reach the account.** Each brand's ad account must grant
the system user `ads_management`. Without it every call answers
*"(#200) Ad account owner has NOT grant ads_management or ads_read
permission"* — that is a Business Settings grant, not a code problem.

**What a new brand needs before a drop can be built:**

| input | required | shape |
|---|---|---|
| `pictures` | yes | `runs/<brand>/<batch>/ads/<unit>/manifest.json`, ads named to the 13 fields |
| `copy` | yes | `<copy root>/<run>/copy.json`, keyed by format then sub-avatar |
| `pages` | yes | sub-avatar → landing page, the shape of `funnels/icon/pages.json` |
| `roster` | no | person id → sub-avatar; without it no sub-avatar is mapped |
| `adsets` | no | per-sub-avatar notes and age bands |
| `offers` | no | the expired-offer gate; without it nothing is checked for a dead offer bar |

**Read the naming convention off the account before the first drop**, and put
it in the brand file as a template. Two live accounts, two shapes, one
renderer:

```
{market!u}{sep}{product}{sep}{funnel!u}{sep}{lane!t}   sep " | "
    -> US | WIDGET™ | ICON | Avatar One

{budget!l}{sep}{market!l}{sep}{event!l}{sep}{product!l}{sep}{lane!l}   sep "_"
    -> cbo_us_purchase_body-scrub_creators
```

`!u` upper, `!l` lower, `!t` Title Case through the brand's spelling map, no
suffix means as-written. An empty field takes its separator with it, so an
absent lane leaves no dangling joint. `campaign_sep` and `ad_set_sep`
override `sep` for one level, because an account can join campaign fields
with underscores while its ad sets read as Title Case prose.

**Read the defaults off the account too, never carry them over from another
brand.** Two accounts set up days apart disagreed on three of them: one
optimises for `OFFSITE_CONVERSIONS` and the other for `VALUE`; one runs two
publisher platforms and the other five; one uses `frequently_in`/`home`/
`recent` locations and the other only `home`/`recent`. Copying would have
been wrong every time.
