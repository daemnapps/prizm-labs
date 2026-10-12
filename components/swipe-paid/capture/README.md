# capture/ — pulling competitor pages down and filing them

The scripts that capture a competitor's live pages, classify them by what
they structurally are, and build the teardown. `classify_pages.py:page_type()`
is the **assigned page-format vocabulary** — every page we name, ours
included, is classified by it rather than labelled by hand.

```
blog · product-page · quiz · utility · listicle
comparison · review-page · advertorial · salespage · prelander
```

`salespage` was added 2026-09-11 (the owner named it). Before that, an
advertorial was anything over 6,000 characters, which labelled every long
page an article. It now tests for what an advertorial actually carries —
`sponsored content`, `paid content`, `advertorial`, `N min read` — and a long
page without those is a salespage: it carries the whole argument itself and
hands off rather than taking the money.

Re-running the corrected classifier over the brand-c capture moved **97 of
126 "advertorials"** into `salespage`.

**The captures themselves are not here.** Words in git, media on Drive — the
pulled pages, screenshots and DOM dumps are large and live on Drive at
`Team Drive/swipe/paid/` (moved from `the shared drive/swipe-paid/`
on 2026-10-07; found through `../swipe_home.py`).
