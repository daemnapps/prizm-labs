# Brand intake

**Keys this tool needs:** `GDRIVE_SA_KEY` (the brand's own Drive service account) for a Drive folder. The website needs no key.

Most brands arrive with a Google Drive of loose folders and a website. This indexes both and says, for every
blank in the brand folder, which of their files can fill it. The `brand-intake` skill then drafts each blank from
those files, marked as a draft for the owner to confirm.

Say **here's our Drive folder**, **index our Drive**, **index our website**, or **fill the brand folder from what we have**.

| Command | Does |
|---|---|
| `python3 components/brand-intake/intake.py drive --brand <b> --folder <link or id>` | every file in the folder and its sub-folders, by Drive id and link, each matched to the blanks it can fill |
| `python3 components/brand-intake/intake.py site --brand <b> --url https://...` | home page, sitemap and product pages: store platform, review apps, outside review pages, social accounts |
| `python3 components/brand-intake/intake.py plan --brand <b>` | each blank: ✓ filled, → can fill (with the files), ? ask the owner |
| `python3 components/brand-intake/intake.py read --brand <b> --file <id>` | a Google Doc, Sheet or Slides as plain text, to draft from |

- **Nothing is downloaded.** Files stay in Drive and are kept by id and link; footage goes to the asset index by folder.
- **The folder is shared once** with the brand's Drive service account (the `client_email` in its key), as a viewer.
- **Matching** is by words in the file's whole path and by file type, in `slots.json`. Change it there.
- **Writes** only `runs/brand-intake/<b>/` (`drive-index.json`, `site-index.json`, `plan.json`, `plan.md`). The brand
  folder is written by the skill, as drafts.

| File | What it is |
|---|---|
| `slots.json` | each blank, the words and file types that fill it |
| `intake.py` | the index, the site read and the plan |
| `test_intake.py` | tests on a synthetic Drive tree and site |

Neighbours: [setup page](../onboarding/), [asset index](../asset-index/), [research fill](../research-fill/),
[Drive](../gdrive-creator/), [brand template](../../brands/_TEMPLATE/).
