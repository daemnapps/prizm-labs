# elements

The one library of every element the system uses — formats, placements,
structures, frameworks, styles, delivery values, templates, doctrine — in one
shape, and the lookup that refuses a value that isn't on its list.

    python3 machine/elements.py build          # refresh from every source list
    python3 machine/elements.py get format video song-ad
    python3 machine/elements.py check format:image=stickynote style:image=candid-ugc
    python3 machine/page.py                    # the library page

In a tool: `import elements as E; E.get(element, asset, id)` — the row, or
`Unknown` with the real options named. Definitions, fields and the four
questions are in machine/elements.py; every source list is mapped in sources.json.

An id is lowercase with "-" between words. Old spellings live on as `aliases`
on their row, so `get()` and `check()` still resolve them. the owner's rulings over
a source list — a rename, an alias, a dropped id, a status — live in
`decisions.json` and are applied at build; the source list is never touched.
Rows the owner has named that no list holds yet live in `additions.json`. A source
list this checkout does not carry keeps the rows last built from it.

`python3 machine/test_elements.py` — 11 tests.
