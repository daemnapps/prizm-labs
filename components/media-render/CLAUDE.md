# components/media-render/ — one renderer, routed by warehouse

`render(pointer, type) -> element`. The fourth surface that has to show a
Drive image calls this; it does not write a fourth copy of the code. Built
under card RV-5 (media renderer) of the `review-component` build
(`new-workflow-design/builds/review-component/task-cards.md`).

**media-render** — takes **a record's media pointer (`warehouse`, `ref`, …) and
the type the record declares**, makes **the element that shows it — `render`,
`url`, `ready`, `release`**. Does not **emit a file or record, hold a
credential, or sniff a type**. Triggered by importing it (a page inlines
`media-render.js` through `python3 components/media-render/bundle.py --out <block.js>`).

**Design of record:** `the-org/decision-log.md`, 2026-09-08 — "DRIVE STAYS THE
MEDIA WAREHOUSE; THE ROUTE GENERALIZES PER-KIND AND THE RENDERER BECOMES A
COMPONENT" (the developer). That ruling also closes the `run-output-rendering`
component candidate, naming this folder.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

1. **Engine + owner — the developer** (the card says "the developer or the designer"; recorded as
   the developer because he owns every other viewer-side library this one sits beside —
   `atlas/`, `language-layer/` — and he holds the merge word
   on the platform plane the consumers live on. **the designer takes it with one
   line from either of them; nothing in the code changes.**). The engine is
   `media-render.js` plus `bundle.py`, which emits the block a template
   inlines.

   Runs by: person — it runs in the viewer's browser inside the pages that
   inline it; the mini runs only its tests (media-render#13).

2. **Definitions + curator — NONE. It is a library.** There is no curated
   content here: no stage map, no per-brand bank, no manifest of entries. The
   two vocabularies it keys on — the warehouse words and the type words — are
   the `review` kind manifest's (`platform/data/kinds/review.json`), which is
   FROZEN and whose curator is the email lead. This component reads those words off a
   record; it never authors them and holds no approval gate.
3. **The plane it emits — NONE.** No record and no run directory; `bundle.py
   --out` writes the inlined block where its caller says (see `bundle.py`). It is
   a rendering library: the CALLER emits,
   exactly as with `gdrive-creator/` and `language-layer/`. It holds no
   credential either (components rule 7) — the page hands in its own
   authenticated fetch, or the element points at a public url.
4. **What the manifest declares per entry — NOT APPLICABLE; the contract is
   the API.** `render`, `url`, `ready`, `release`, plus the pointer shape and
   the four url shapes below. Nothing outside this folder may depend on
   anything else in it.

## The contract

    MediaRender.render(pointer, type, opts) -> Element
    MediaRender.url(pointer, opts)          -> string
    MediaRender.ready(el)                   -> Promise<Element>
    MediaRender.release(el)                 -> boolean   (revokes the object url)

**Public names — beyond the four methods** (the developer, 2026-10-07, triage action 6 (declare public surfaces); option (a) of media-render#6 (names beyond four methods)). Besides `render`, `url`, `ready` and `release`, these are public and kept:
1. `MediaRender.WAREHOUSES` → the warehouse words this engine routes (a copy; mutating it changes nothing) and `MediaRender.TYPES` → the frozen type table — both re-exported by the shim as `pageMedia.WAREHOUSES` / `pageMedia.TYPES`, read-only.
2. `bundle.py`: `bundle()` → the inline block (engine, then shim — the order is load-bearing), and the command `python3 components/media-render/bundle.py --out <block.js>`; a page carries that block between its `BEGIN`/`END media-render` markers and regenerates it, never edits it.
Anything else in `media-render.js` or `bundle.py` is internal and may change without notice.

**The pointer** — the record's own words, never anything derived:

    { warehouse: "repo" | "drive" | "blob" | "url",
      ref:   string,   // repo: the repo-relative path · blob: the url itself
                       // url:  the url itself — a Figma file, a Netlify
                       //        preview, anything the platform does not own
                       // drive: the Drive file id — carried for provenance,
                       //        NEVER spent on a url (see below)
      kind:  string,   // drive only: the records kind whose manifest declares
                       //        the media inventory
      item:  string,   // drive only: the record id (`/api/media`'s `run`)
      name:  string,   // drive only: the EXACT name a row of that record's
                       //        inventory publishes
      title: string }  // optional — the human words, used as alt / link text

**The url shapes, declared:**

| warehouse | url | why |
|---|---|---|
| `repo` | `<api>/api/file?path=<ref>` | the gated read six viewers already use |
| `drive` | `<api>/api/media?kind=<kind>&run=<item>&file=<name>` | RV-4 (media route per-kind), as merged |
| `blob` | `<ref>` | a public url resolves with no credential |
| `url` | `<ref>` | RV-34 (url and viewport) — the platform does not own it, so there is no api in front of it |

`repo` and `drive` are OURS and take the page's credential; `blob` and `url`
are not, and the shim withholds it from both (`_media.js`, `OFF_PLATFORM`).
A `url` pointer is by definition a third party, so sending a Bearer token
there would hand a credential to a service that never asked for one.
`supabase` is still declared-and-unrouted, and that is not in tension with
`url` being routed: a declared word earns a route when something actually
points there, and nothing points at Supabase Storage.

**Why a drive pointer names the record and the row, not the Drive id.** The
merged `/api/media` matches `file` EXACTLY against the rows of that record's
declared media inventory and resolves the Drive id itself — the inventory
record is the allowlist, and that is the whole security model. A client
sending a Drive id would be naming a file no record published, which is
precisely what the route exists to refuse. `kind` is REQUIRED here even
though the route defaults it to `teardown-runs`: defaulting a review's media
to another kind is the kind of silent guess this component exists not to make.

**The type words** are the manifest's (`platform/data/kinds/review.json`) and
the renderer's (`media-render.js`); read the list there. `image` → `<img>`, `video` → `<video controls>`, `text` → `<pre>`,
`md` → `<div>` whose `textContent` is the raw markdown (a panel brings its own
renderer; this component ships none and builds no markup out of what it read),
`doc` and `link` → `<a>`. An unknown type **degrades to a link, never to an
empty box** — the manifest's own words for its `type` vocabulary.

**Every element carries its provenance** as data attributes:
`data-media-warehouse`, `data-media-type` (as GIVEN, including an unknown
one), `data-media-shape` (what was drawn), `data-media-url`,
`data-media-state` (`ready | loading | needs-bytes | error`) and
`data-media-error`.

## The two nevers, and how they are kept

1. **No type sniffing.** `type` is an argument, off the record. No extension is
   parsed, no magic bytes are read, no response header is consulted:
   `{ref: "notes.txt"}` with type `image` renders an `<img>`, and
   `{ref: "cat.png"}` with type `video` renders a `<video>`.
2. **No warehouse guessed from a url's shape.** `pointer.warehouse` routes, and
   a warehouse the table does not carry is REFUSED BY NAME. `supabase` is
   declared in the review manifest and has no route here — Supabase Storage was
   not added on 2026-09-08 and nothing points there — so a supabase pointer
   raises `media-render: warehouse "supabase" has no route here …` rather than
   falling through to a guess. (The one thing a url is inspected for is the
   `blob` branch refusing a non-`http(s)` scheme, which is a browser-safety
   refusal on a warehouse that was already declared, not a routing decision.)

## Bytes, and whose credential they are

`<img src>` cannot carry a Bearer token or a cross-host cookie, so a page that
reads gated bytes hands in its OWN authenticated fetch as `opts.fetch`; the
element then swaps to an object url and the caller gives it back with
`release`. With no fetch handed in, a picture points at the url — right for a
public blob, an honest visible 401 anywhere else — and a text pane reports
`data-media-state="needs-bytes"` instead of pretending to be empty. Everything
that reaches outside is injected (`document`, `fetch`, `apiBase`, `URL`),
which is also why the declared test runs the real decision layer on bare
`node` rather than a copy of it.

## Layout

    CLAUDE.md        this file
    media-render.js  THE ENGINE — the one implementation, browser <script>
                     and CommonJS (`require`) from the same file
    bundle.py        emits the block a viewer template inlines: the engine,
                     then platform/views/viewers/_templates/_media.js

The shim `platform/views/viewers/_templates/_media.js` binds the page's api
base and authenticated fetch and exposes `pageMedia`. It re-implements
nothing, and there is **no stored copy of the engine anywhere** — a second
source copy is the defect this card ends.

Declared test:
`new-workflow-design/builds/review-component/test_rv5_media_render.py`.
Needs `node` on PATH; without it the render checks SKIP rather than fail, so a
green run with no node proves nothing about the renderer (media-render#9).

## Status

Its residency is its row in `components/CLAUDE.md` (the register); its consumers
are whatever loads it (`git grep -n "media-render" -- platform components`). This
file restates neither.

**KEPT 2026-10-08** (the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:32:36Z: "go on B1, 2, 3"; decision log 2026-10-08 B2 (triage design calls)): the review surfaces (the PM review panel,
review's reference panel) count as several consumers, and the PM board runs it.
**Kill** (restated): no surface outside `components/review/` loads it → fold it
back into `components/review/`.
