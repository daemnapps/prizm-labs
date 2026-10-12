# styles — the video style bank and its board

`bank.json` is the bank: one row per style (a style lock: `formula` + `motion`).
It is `style:video` in `components/elements`; the video machine's preflight
refuses a `style_id` that is not a row.

    python3 styles/make_swatches.py --base <approved-frame.png>   # one picture per style, skips what exists
    python3 styles/render_board.py                                # -> runs/video-production/_system/style-board.html + STYLE-BOARD.md
    python3 ../../../components/elements/machine/elements.py build

The board publishes over ONE artifact — The Format Frontier,
(team page) — never a second one.
`board-content.json` holds the written tabs; the show-format candidates are in
`../formats/show-formats.json`; the edit tab describes `video-edit`.

**`board-template.html` is source, not a generated page.** The repo ignores
`**/board-*.html` to keep built boards out; this one is the template
the generator fills, so it is force-added. `style-board.html` IS generated
(5 MB of inlined pictures): `render_board.py` writes it to
`runs/video-production/_system/style-board.html`, ignored there — rebuild it
and republish over the artifact from that path.

**Pictures are not in git** (workspace rule 3). `swatches/`, `board-media/` and
`../formats/show-frames/` live on the Drive at
`Shared Assets/<same path>/`. Copy them back beside
this file before printing the board. `style-board.html` carries them inline, so
it opens from disk at `runs/video-production/_system/style-board.html` after a
render; everyone else opens it through the one artifact above.
