# Where a page or an ad goes — two brands, many of both

The naming conventions say what a thing is *called*
(`CONVENTION.md` for ads, `PAGES.md` for pages). This says where the
**words** and the **media** each live, because they never live together:
words in git, media on the shared drive. That split is what keeps the repo
usable at volume.

## The rule

```
words  ->  workspace/brands/<brand>/…     (git: diffable, reviewable, small)
media  ->  Shared Assets/brands/<brand>/…    (Drive: the files themselves)
```

**Brand is always a path segment.** Anything without a brand in its path
stops working the moment there are two of them — which there are.

**The drive mirrors the repo.** Below `brands/<brand>/` the two carry the same
shape — the same funnel names, the same page names — so knowing where a thing's
words are is knowing where its media is. Work still being figured out lives in
`lab/<person>/`; once it is producing for a brand, it graduates to
`brands/<brand>/` on both sides. Page media graduated 2026-09-11.

## Pages

```
WORDS   workspace/brands/<brand>/funnels/<funnel>/
            icon-build.md              the running record
            pages.md                   the registry, generated
            <name>-construct.md        what the copy was injected against

SOURCE  the funnel's own repo — for ICON: daemnapps/<brand>-icon
            src/icon/<page-name>.html  front matter carries the key
            src/icon/assets/           the media the build actually uses

DRIVE   Shared Assets/brands/<brand>/funnels/<funnel>/<format>/<page-name>/
            README.md   what the page is, its live URL, its name fields
            copy.md     every word on the page, in page order
            mechanism/  reviews/  before-after/  flex/  founder/
            video/      icons/
```

A page's Drive folder holds the **whole** page — the words and the pictures —
so it can be read, sent to a writer, or looked back at without opening
anything technical. `README.md` and `copy.md` are **mirrors**: `page-doc.py`
rewrites them from the source file on every sync, and editing them changes
nothing. The source file stays the page.

Media and words sit under the same `<brand>/funnels/<funnel>/` on both sides.
`sync-media.py` in the funnel's repo keeps the drive copy current and derives
the funnel from the folder a page is built in — nothing to pass, nothing to
keep in step by hand.

`<page-name>` is the key from `PAGES.md` — `format-avatar-angle` — so a
folder on Drive, a row in the registry, a URL and a source file all carry the
same string. No lookup table.

Live example:
`brands/<brand>/funnels/icon/salespage/salespage-fedupking-razornotproblem/`

Pages group by format on the drive — salespages together, advertorials
together — and the money pages sit under `offers/` with their plain names.
The rule and the reason: `PAGES.md`, "The folder is the format".

## Ads

Already established in `CONVENTION.md`; repeated here so the two sit together.

```
WORDS   the batch manifest beside the run
MEDIA   Shared Assets/lab/damon/<lane>/<brand>/…
            image-production · video-production · image-teardown
```

Ad name: `brand-media-avatar-format-concept-ratio-batch`, asset filename is
that plus one field.

## Swipes

```
WORDS   workspace/lab/damon/swipes/<pool>/registry.md
MEDIA   Shared Assets/lab/damon/swipe-paid/<brand>/…
CODE    workspace/components/swipe-paid/  (tool) and capture/ (pulling pages)
```

The captures themselves — ~9.3GB of DOM dumps and screenshots — live on the
Drive at the MEDIA path above.

## Why media never enters git

A page carries roughly 8MB of its own imagery. Ten pages across two brands is
80MB of binaries in a repo where every re-cut writes a new blob and nothing is
ever reclaimed. The workspace rule is already explicit — never commit media or
files over 10MB — and at the volume being planned it is the difference between
a repo that clones and one that does not.

The funnel's own source repo is the one exception: it carries the assets the
build consumes, because Netlify serves committed files and there is nowhere
else for them to be. Drive holds the masters and anything a page stopped using.
