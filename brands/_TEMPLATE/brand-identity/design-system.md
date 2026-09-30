# <Brand> — the design system

**This folder is the design system: colour, type, marks, and the tokens a web
surface renders with.** It is not the position — what the brand argues lives in
`position.md` (same folder) and never carries a hex value. A machine that needs a colour,
a face or a mark reads here and nowhere else.

_Created <date> by <name>. Shape: `brands/_TEMPLATE/brand-identity/`. Every value is
**measured, not chosen** — sampled off the brand's own product photography, its
live CSS, its real font files and its real marks. A slot the material cannot
settle says `open`._

## The four files, and what each is sampled from

| File | Holds | Sampled from | Read by |
|---|---|---|---|
| `palette.md` | the photography palette — what the product actually is | the packshots in `../products/**/images/` | image and video production, the frame stage, the cast |
| `web-tokens.md` | colour, type, radius, spacing as CSS tokens | the brand's live CSS | pages, email, the checkout, anything in a browser |
| `fonts.md` | what is licensed, what each licence allows, where the files live | the purchase records and the font files | pages, email, statics |
| the marks | the real wordmark and logo files, listed below | the live site | every surface that shows the brand name |

**Photography colours and web colours are kept apart.** They agree in character
and differ in exact value; a print of the product is not a button. Creative reads
`palette.md`, anything rendered in a browser reads `web-tokens.md`.

## The marks

**Never typeset the brand name** — a wordmark is either right or it is wrong,
and there is no close. Files live in this folder; the font files live on the
company drive under brands/<brand>/brand-identity/fonts/ (workspace rule 3: no
binaries over 10 MB in git).

| File | What it is | Ground |
|---|---|---|
| `<brand>-logo.svg` | the primary mark, as the site's header shows it | light |
| `<brand>-logo-white.png` | the primary mark knocked to white | dark or photographic |
| `<brand>-logo-dark.png` | the primary mark in the brand's near-black | light |
| open | <any other lockup the site actually uses> | |

## Why this folder exists

An undocumented colour is not a neutral absence. It gets filled by whoever we
swiped: a brief once cut a whole zone from an ad with the reason "brand accent
color hex undocumented", and a headline shipped in a competitor's pink because
nothing of ours was on file to replace it.

## How to create one for a brand that has nothing yet

The tool is `brand-identity/measure.py`; every step is one command,
and every step writes `open` where the material is missing rather than guessing.

1. **Scaffold** — copies these four template files into `brands/<brand>/brand-identity/`,
   never overwriting one that exists.
2. **Palette** — samples the dominant colours off every image under
   `brands/<brand>/products/**/images/` and writes the table in `palette.md`,
   dated, with the file each colour came from. A person then names each row
   (what it IS on the product) — the tool never coins a name.
3. **Tokens** — fetches the brand's live CSS and writes `web-tokens.md`: every
   colour by how often it is declared, every font-family, the radii. Measured
   off the surface the customer sees.
4. **Fonts** — a person fills `fonts.md` from the purchase records; there is no
   material a machine can measure a licence from.
5. **Marks** — a person drops the real files in and lists them above.
6. **Check** — reports which files and slots are still `open`, for every brand
   or one.

Lanes: a brand that runs two visual lanes that are never blended keeps one
`palette.md` per lane (`palette.md`, `palette-<lane>.md`) and says so at the top
of each.
