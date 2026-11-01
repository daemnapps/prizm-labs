# components/review/reference/ — working reference panels, never promoted

Five plain pages over the real `review` kind, built by card RV-6 (reference
panels): one that files a request and four that show one and file a verdict.

**They are a reference, not a product, and they say so on themselves.** They
are deliberately unstyled, they are **not** in `team/promoted-surfaces.json` —
a promotion is a human act (the team's, the team's or the team's) and no session ever
writes that file — and nothing here is meant to be defended. Copy a page,
rewrite the look, keep the grammar.

## The pages

| page | what it is the reference for |
|---|---|
| `create.html` | filing one `event: request` record — the composed body, validated against the frozen manifest |
| `panel-text.html` | `type: text` — the words, from the repo mirror or public blob bytes |
| `panel-md.html` | `type: md` — the markdown **source**; which renderer to use is the panel author's call, not this page's |
| `panel-image.html` | `type: image` — the picture, through RV-5 (media renderer) |
| `panel-link.html` | `type: link`, and where an **undeclared** type degrades to |

`video` and `doc` are declared types the block keys on with no reference page of
their own — four panels is what the card names, and two more would be styling
investment somebody has to undo.

## Three files, linked — one copy of everything

    _session-bootstrap.js   the viewers' ONE credential module (CP-8) — not
                            ours; the pages load it from
                            platform/views/viewers/_templates/ by relative path
    _reference.css          the whole stylesheet, plain on purpose
    _reference.js           the fold, the two calls, and the type-keyed panel block

Each page is a banner, a paragraph, three `<script src>`/`<link>` tags and one
mount line, so the fold and the panel exist **once** and a fix is one fix.

**If you move a page into `platform/views/viewers/`, inline those files.** That
route serves exactly one html file per request and cannot fetch a sibling — the
reason every viewer template carries an inlined copy of the bootstrap, kept
honest by `new-workflow-design/builds/consumer-plane/inline_bootstrap.py`. A
reference page is never served that way, so it may link; a viewer may not.

`_reference.js` is the block **RV-10 (PM review integration) lifts** into the PM
drawer — its card says lifted from here, not rewritten. Every name in it is
prefixed `review*` / `REVIEW_*` so it can be pasted into `pm.html` without
colliding with a global that page already spends.

## The rules these pages obey (and the test proves)

1. **Status is never stored — it is folded.** `reviewFold()` is a port of
   `fold()` in `components/review/review_request.py`, which a browser cannot
   import; the declared test runs both over the same fixtures and asserts they
   agree field for field. After a write the records are re-read and re-folded,
   never patched in place.
2. **The manifest is the contract** (`platform/data/kinds/review.json`,
   `_frozen`). The vocabularies in the block are mirrored from it for
   validation only and cross-checked against the file by the test. Nothing here
   invents a field: an addition is a ruling.
3. **The pointer, never the bytes** (workspace rule 3). No warehouse is guessed
   from a url's shape and no type is sniffed — the type comes from the record.
4. **No close is filed here.** The panel *labels* which close rule a request is
   under ("auto on one reviewer + no `on_accept`; else explicit by
   requester/owner"), as the manifest requires, and leaves the write to the
   surface that owns it.
5. **No secret is read from a file.** Credentials are the shared bootstrap's:
   a session cookie when the consumer shell served the page, otherwise the key
   a `#k=…&as=…` link carries, held in this browser's `localStorage`.

## Running one

These pages talk to the real records plane, so they need a credential and an
origin the plane answers:

- **Served from the app** (any `*.vercel.app` deploy serves every tool id;
  production serves only promoted ones) — same origin, session cookie, nothing
  to paste. This is how a copy under `platform/views/viewers/<person>/` runs.
- **Opened from the repo** (`file://…/components/review/reference/create.html`,
  or any static server rooted at the repo, which is what keeps the relative
  path to the bootstrap true) — the page prompts once for a review key and your
  name, and calls `https://review-app-ecomm-ops.vercel.app`. Whether that
  cross-origin call is allowed is the API's rule, not this page's; if the
  browser blocks it the page reports the failure rather than pretending.

**What to open a panel against.** The review plane is
`platform/data/records/review/` — list it for what is filed. RV-1 (review
kind manifest)'s seeds in `components/review/seed/` are example records, not
filed ones, so a panel pointed at a seed id reports "no `request` record" —
correctly. File one with `create.html` (or
`components/review/review_request.py`) and open the id it hands back.

## The media wiring, as wired

`panel-image.html` renders through RV-5 (media renderer) —
`render(pointer, type) -> element`, routed by `pointer.warehouse`. RV-5 merged
after this folder was first built, and the seam is now closed:

    <script src="../../media-render/media-render.js"></script>   <!-- the ENGINE -->
    <script src=".../_templates/_media.js"></script>             <!-- the page SHIM -->

**The order is load-bearing** — `_media.js` throws by name at load if the
engine is not already there.

**Copy the pair, and call `pageMedia` — never `MediaRender`.** The engine's
`render` takes a third argument holding the two facts that belong to the page
and cannot live in a component: the api base, and the page's own authenticated
fetch (an `<img src>` carries neither a Bearer token nor a cross-host cookie).
`_media.js` binds exactly those and exposes `pageMedia`; that is the global
`reviewRenderer()` looks up. Reaching past it to the engine would make this
folder keep a second copy of the shim and would read a `repo` or `drive`
pointer against base `""` with no credential — so `reviewRenderer()` returns
nothing when only the engine is present, and the panel says which half is
missing.

A page under `platform/views/viewers/` cannot load two siblings — that route
serves one html file per request — and inlines the pair instead:

    python3 components/media-render/bundle.py --out <block.js>

The panel gives object urls back (`pageMedia.release`) on every re-mount, and a
verdict re-mounts it. A pointer RV-5 has no route for — `supabase` is declared
in the manifest and routed nowhere — is refused BY NAME, in RV-5's words.
