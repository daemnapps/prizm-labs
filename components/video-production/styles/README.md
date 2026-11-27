# styles — the video style bank and its board

`bank.json` is the bank: one row per style (a style lock: `formula` + `motion`).
It is `style:video` in `components/elements`; the video machine's preflight
refuses a `style_id` that is not a row.

    python3 styles/make_swatches.py --base <approved-frame.png>   # one picture per style, skips what exists
    python3 styles/render_board.py                                # -> runs/video-production/_system/style-board.html + STYLE-BOARD.md
    python3 ../../../components/elements/machine/elements.py build

The board publishes over ONE artifact — The Format Frontier,
https://claude.ai/artifact/RUBXajrAH5uyiVH6eyJM5h — never a second one.
`board-content.json` holds the written tabs; the show-format candidates are in
`../formats/show-formats.json`; the edit tab describes `components/video-edit`.

**`board-template.html` is source, not a generated page.** The repo ignores
`lab/the owner/**/board-*.html` to keep built boards out; this one is the template
the generator fills, so it is force-added. `style-board.html` IS generated
(5 MB of inlined pictures): `render_board.py` writes it to
`runs/video-production/_system/style-board.html`, ignored there — rebuild it
and republish over the artifact from that path.

**Pictures are not in git** (workspace rule 3). `swatches/`, `board-media/` and
`../formats/show-frames/` live on the Drive at
`Shared Assets/components/video-production/<same path>/`. Copy them back beside
this file before printing the board. `style-board.html` carries them inline, so
it opens from disk at `runs/video-production/_system/style-board.html` after a
render; everyone else opens it through the one artifact above.


## The ad's style runs the whole chain (`style_chain.py`, owner ruling 12 Nov 2026)

The swipe's style is ONE setting, read by every step: the teardown writes `style_id` on its run, the writing run
carries it, the Video Studio production brief holds it as `style` (seeded from the run; `style_chain.py set-style`
changes it). Casting (`cast.py who|build --style`, `cast.py variant`), the 3D print queue, `make_character`, the
Studio's cast check and the library footage fill all read it.

Every element (person, product, set, world, prop) is used in the ad's style. A banked element in another style is a
variant to make, never a gap and never a reason to change the ad's look: `style_chain.py ensure-one` files a 3D print
of the element's master (identity) with the swatch or a face-free swipe frame (look only), then adopts the kept print
(a person gets their full sheets from `make_character` in the style). Variants live in the element's own folder,
`styles/<style-id>/`, and are reused after. `style_chain.py needs --production <idea>` lists what a production has and
what is still to make. A non-photoreal ad takes no real library footage.
