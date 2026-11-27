---
name: brand-intake
description: Fill a brand folder from what the brand already has — a Google Drive of loose folders and its website. Indexes every file and page, matches each to the blank it can fill (logo and fonts, story, position, products and photos, offer, avatar, reviews, surveys, competitors, past ads, footage, creators), then drafts each blank from those files for the owner to confirm. Use when someone says "here's our Drive", "index our Drive folder", "our stuff is all in Google Drive", "fill the brand folder from our drive", "index our website", "find our reviews from the site", or hands over a Drive folder link during onboarding.
---

# Brand intake

> **Activates component:** `components/brand-intake` (`intake.py`), handing footage to `asset-index`, surveys and
> reviews to `brand-research` (`components/research-fill/connect.py`).

Run every command yourself; talk in plain words. The owner gives two things at most: the Drive folder link and the
website. Everything else is found.

## 1. Index

1. Website: `python3 components/brand-intake/intake.py site --brand <b> --url <site>`.
2. Drive: the folder must be shared with the brand's Drive service account. Read its email (the key's
   `client_email`, not secret) and tell them in one line: "Share the folder with <email> as Viewer." Then
   `intake.py drive --brand <b> --folder <link>`. If `GDRIVE_SA_KEY` is missing, open the setup page for it first.
3. `intake.py plan --brand <b>` and tell them in one line: "N files indexed; X blanks can be filled, Y need you."

## 2. Fill, blank by blank, in onboarding order

For each blank marked → in `runs/brand-intake/<b>/plan.json`, in the order of `brands/_TEMPLATE/onboarding.json`:

- **Text blanks** (story, position, core message, offer, avatar): read the top files with `intake.py read --file <id>`
  (and the site's pages), then write the blank's files keeping the template's shape. Use their words; invent
  nothing. Mark each file `Draft from: <file links>` at the top. Tick the item in `onboarding-progress.json` only
  when the owner confirms.
- **Look**: write `identity/drive-sources.md` with the logo, guide and font files' links; read a brand guide for
  `palette.md` and `fonts.md`.
- **Products**: one `products/<product>/` per product page on the site; its photos as Drive links in
  `products/<product>/images/drive.md`.
- **Surveys**: each Form response sheet → `connect.py surveys --brand <b> --sheet <id> ...` (brand-research).
- **Reviews**: a review app on the site → `connect.py reviews`; outside review pages (Trustpilot, Amazon) go in
  `customer/review-pages.md`; a reviews export in Drive → the language bank through the gatherer.
- **Footage**: hand the folders holding video to `asset-index` ("index this footage folder for <b>").
- **Past ads, competitors, creators**: list the files' links in `existing-content/top/drive.md`,
  `competitive/drive.md`, `creators/drive.md`.
- A blank marked **?** has nothing to draw from: ask the owner its onboarding question.

## 3. Show it

One line per blank: ✓ drafted from what (with links), ? still needs them. Then hand over to `brand-research`.

## Rules

- Nothing is downloaded or copied out of Drive; files are kept by link.
- Never overwrite a filled blank (✓). A draft says it is a draft until the owner confirms.
- Brand data stays in `brands/<b>/` and `runs/` (both ignored by git). Never commit or paste it elsewhere.
