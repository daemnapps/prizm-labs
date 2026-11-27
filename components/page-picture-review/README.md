# Picture review — face-scrub landing page


The review desk for the face-scrub offer page's pictures: a numbered demo of the
page, an index of every picture slot, and the decision recorded against each one.
Started 2026-09-17 by the developer. It decides nothing on its own — it is where the
decisions are written down so the next person can act on them.

## Why numbers

`pictures-map.json` names slots by filename. Filenames are hard to talk about and
several repeat, so this desk gives every picture slot on the page a number and
paints it on the page itself. Say "#12" and everyone is looking at the same picture.

**A number means the same slot on both breakpoints.** The page carries a desktop
tree and a mobile tree; `#12` is desktop `spots-demo-hands.jpg` and mobile
`m-spots-demo-hands.jpg`. Ten slots differ between the trees — **#1 and #12-#23** —
so a replacement there is two files, not one. Everywhere else both trees use the
same file and one swap covers both.

Numbers come from `slots.json`, keyed on filename, not on position in the page, so
they survive edits to `landing.html`. A picture the index does not know shows as
`D?` with a console warning — add it to `slots.json` rather than renumbering.

## The decision protocol

Each slot is one of four states, recorded in `pic-state.json`. The key is the
slot number — `"1"` decides both trees at once — or the badge id when the trees
differ, `"D1"` and `"M1"` separately. The ten split slots (#1, #12–#23) usually
need the second form, because they are different pictures.

| state | badge | means |
|---|---|---|
| *(absent)* | yellow | not discussed yet |
| `replace` | red | needs a new picture — this is the work order |
| `keep` | green | the picture on the page stays |
| `updated` | green ✓ | a new picture has been put in and is in the demo |

`replace` is a decision, not an action: red says the slot is wrong, green-updated
says it has been fixed. When the pass is finished, the red list is what goes back
to `pictures-map.json` as an amendment.

## If you pulled and saw no numbers

The demo page is **not in the CPK repo's funnel folder** — the funnel has
`landing.html`, the source page, which is Liquid and does not render on its own.
The demo is either the committed copy in `review/` at the CPK repo root, or one
you generate yourself (below).

## What the demo is

**The built page with an overlay added** — not a rebuild of it. `campaign-build`
renders the page exactly as it deploys (layout, includes, header, footer, the
kit's own CSS and JS, the cart SDK), and the generator then rewrites the built
page's absolute asset URLs so the file works from anywhere, and appends the
numbering overlay before `</body>`.

Two deliberate differences from the deployed page, neither of them visual:

- **GTM and the Meta Pixel are stripped.** A picture review should not fire
  pageviews into the live property.
- **Asset URLs are rewritten** from `/Brand B-face-scrub/…` to a relative path
  into the funnel's own `assets/`, so the page can be opened from disk.

Everything else is what deploys. Earlier versions of this kit reconstructed the
page from `landing.html` by stripping front matter and resolving Liquid by hand;
that approximated the template and quietly lost anything the layout provided —
the CTA button among them. Do not go back to it.

## Running the demo

    cd <cpk>/Brand B && npm ci          # once — the generator needs campaign-build
    python3 make_demo.py <cpk>/Brand B --out <cpk>/review
    open <cpk>/review/_preview-landing.html

`--no-build` reuses whatever is already in `_site`. `--slug` and `--page` point
it at a different campaign or page; it is not face-scrub specific.

To watch decisions update live, serve the output folder instead of opening the
file:

    python3 -m http.server 4173 --directory <cpk>
    open http://localhost:4173/review/_preview-landing.html

Root the server at the repo, **not** at `review/`. The demo reaches its pictures as
`../Brand B/src/...`, above the review folder — serve `review/` as the root and the
page loads with every picture missing, which looks like a broken build and is not one.

`http.server` caches aggressively — add `?v=2` to the URL after regenerating, or
you will be looking at the previous build.

**The decisions you see are the ones that existed when it was generated.** Pull
this folder and regenerate to catch up.

## Files

| file | what it is |
|---|---|
| `picture-index.md` | the readable index: number, desktop file, mobile file, `pictures-map.json` decision, section |
| `slots.json` | the same mapping as data, read by the overlay |
| `pic-state.json` | the decisions so far — the live record |
| `pic-index.js` | the overlay that draws the badges |
| `make_demo.py` | builds the demo page from the kit's build output |
| `placements.json` | what was put into which slot, from which source, fitted how |
| `notes.json` | review notes drawn on the page, keyed by badge id |

## Notes on the page

`notes.json` puts review comments on the picture itself, so whoever makes the
next version reads them in place instead of in a thread. Keyed by badge id:

    { "D1": [ { "kind": "fix", "rect": [0.06,0.79,0.40,0.16],
                "title": "...", "body": "..." } ] }

`kind` is `fix` (red), `ok` (green) or `spec` (blue). `rect` is
`[x, y, w, h]` as fractions of the slot's own box, so the marker lands in the
right place at any viewport; leave it out and the note pins inside the slot's
right edge as a note about the whole picture. A note only shows where its slot
shows — `M1` notes appear at mobile widths, `D1` notes at desktop.

**Turning it off.** The bar carries two toggles, `numbers` and `notes`, and
pressing **A** hides or restores everything at once — the annotations sit on top
of the very thing being judged, so being able to clear them is part of the tool.
Each viewer's choice is remembered in their own browser; it is not a property of
the file, and everyone else still opens it with annotations on.

Say what was measured, not just what you want. "Too bright" is an opinion;
"mean luminance 162 behind white type, needs under 110" is something the next
render can be checked against.

## Where the pictures come from

Replacements are picked from the funnel-assets folder on the shared drive,
mounted locally under `Shared drives/Shared Assets/` at
`brands/Brand B/products/brilliance-face-scrub/funnel-assets/` — 42 stills under
`landing/` (sectioned: hero, model-with-product, ingredients, how-to-use, claims,
texture, reviews, launch-banners) and 44 under `advertorial/`, with `index.csv` as
the manifest. Filenames are unique as pictures: 16 basenames appear in both
folders and every one is byte-identical.

Videos in that manifest are **not** copied into the folder ("not copied, open from
source"), so the three video-poster slots (#32-#34) need a frame grab, not a pick.

## Known state at handover

- Copy has been applied to `landing.html`; the pictures are still the body scrub's.
- 42 landing stills against 73 slots. The 12-tile social grid (#59-#70) and the
  eight spot-picker before/afters (#13-#23) have nothing matching on the Drive;
  the map already rules the latter MISSING.
- `pictures-map.json` covers the desktop tree only — the 13 mobile-only files have
  no row in it. That gap is why this desk numbers both trees.
