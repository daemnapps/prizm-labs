# Product behaviour — how the real product sits, moves and works (v1)

the owner, 2026-10-07: "Every time that we pull in a product, we need to apply that
product's physics as well. Just like we create its dimensions and its weight …
we also need to do the same for the way that the product actually functions."
A picture that shows the product doing something it physically cannot do (the device
stood upright on a table — it has a domed base and rolls over) is a wasted
generation. This record is read by every picture the product appears in.

You read the brand's own files about ONE product and the list of its real
pictures, and write down how it physically behaves. Only what the files or the
picture names say. Never infer from what products "usually" do; when the files
are silent on a point, leave that field empty.

## The product

{product}

## The brand's own files that mention it (verbatim)

{files}

## Its real pictures on the company drive (paths only)

{pictures}

## What to write

1. `cannot` — what it physically cannot do (stand on its own, float, bend, open…), each one line.
2. `rests` — every way it sits when nobody is holding it, best first. For each: `how` (one line), `on` (the thing it sits in or on, by the brand's name for it, or "" for a bare surface), and `pictures` — the paths from the list above that SHOW that rest, up to two, empty when none does.
3. `held` — how a person holds it, one line.
4. `in_use` — what it does while it works (vibrates, foams, lights up, needs water…), one line.
5. `never_show` — the wrong pictures this product keeps getting, one line each, from the files.
6. `receipts` — for every line above, the file and the words that say it.

## What you return

JSON only, no prose around it:

```
{"cannot": ["..."],
 "rests": [{"how": "...", "on": "...", "pictures": ["<path from the list>"]}],
 "held": "...",
 "in_use": "...",
 "never_show": ["..."],
 "receipts": [{"for": "<which line>", "file": "<file name>", "says": "<the file's own words, under 25 words>"}]}
```
