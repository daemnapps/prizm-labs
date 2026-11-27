Here is the format we are building on: {replication_spec}

Our brand put through it, the picture that gets made and approved first: {baseline_injection}

That picture's swap list, as data: {swaps_record}

The headline set: {hook_set}

Our product: {product_file}. Our customer language bank: {language_bank}.

Write **the brief's five variations**, as data a machine makes them from.

## The batch is six pictures

the owner, 2026-10-27: *"It'd be 6 total images in that batch: 5 unique
variations from the initial one that we made."* The first picture is the one
the brand step above describes. It gets made and approved on its own. You
write the other five, and nothing else: exactly five, never four, never six.
The approved picture is not one of them.

## Each variation is ONE change off the approved picture

The machine that makes them sends the approved picture itself as the
reference and asks for one change to it. Everything you do not name stays
exactly as it is: the person, the pose, the crop, the light, the set, the
product, the type. So:

- **One idea per variation.** A new headline, and the one picture change that
  makes that headline true, is one idea. A new headline and an unrelated new
  setting is two, and it is not allowed.
- **Small and visible.** The change has to be something a viewer sees at a
  glance (where something sits, how many, what she holds, what she wears,
  what the light catches), not a grade, a lens or a crop. Those are the same
  picture.
- **The format does not move.** Every change sits inside the spec's
  swappable list. Nothing the spec marks load-bearing changes.
- **Defensible.** Every headline comes from the headline set and every
  picture change from something in the files above: a worry the language
  bank ranks, a detail the brand step already put in the picture, a use the
  product file supports. Nothing nobody's words justify.

## How to build the five

Take the five variation headlines from the headline set (not the control),
in their order, word for word. Each one is a row:

- **words**: every caption zone on the approved picture, in the order the
  brand step lists them, one string per zone, with ` / ` where the line
  breaks on the ad. Only the headline's zone takes the new headline; every
  other zone is copied word for word from the brand step. Written exactly as
  it will be set: the same case, no long dashes.
- **picture**: the one change to the picture that makes this headline true,
  in one plain sentence, as it will read after "THE ONE CHANGE to the
  approved picture:". Say what is different, not what stays. Leave it out
  only when the new words are true of the approved picture as it is; that row
  costs nothing, because the approved picture just gets the new words.

A row changes the person only when its headline cannot be true of the person
in the approved picture. Then it also carries:

- **people**: `made-up` (a new person, not a banked cast member) or `cast`.
- **person**: `who`, `age`, `look`, `wardrobe`, each in plain words, the way
  a casting note says it. The wardrobe stays the approved picture's unless
  the headline is about it.
- **swap**: one row, `{"from": ..., "to": ..., "kind": "drawn"}` (or `cast`
  with the cast member's name), whose `from` is copied character for
  character from the swap list above, so it replaces that row.

Use `stays_drop` only when the change undoes a line the swap list keeps
(copy that line exactly). Use no other keys.

**ids** are `v1` to `v5`. **label** is `Headline <n> · <three to five words
saying what it is>`.

## What to give me

First, for a person to read, one line per variation:

```
v1 · <label> · <the headline> · <the picture change, or "words only">
```

Then **THE VARIATIONS RECORD**: one fenced `json` block, nothing after it.
The keys, spelled exactly like this; code reads it into `out/variations.json`:

```json
{"variations": [
 {"id": "v1", "label": "Headline 1 · <what it is>",
  "words": ["<HEADLINE LINE ONE / LINE TWO>"],
  "picture": "<the one change, in one plain sentence>"},
 {"id": "v2", "label": "Headline 2 · <what it is>",
  "words": ["<HEADLINE LINE ONE / LINE TWO>", "<another zone, copied>"]},
 {"id": "v3", "label": "Headline 3 · <what it is>",
  "words": ["<HEADLINE>"],
  "picture": "<the one change>",
  "people": "made-up",
  "person": {"who": "<who she is to the ad>", "age": "<n>", "look": "<face, hair, skin>", "wardrobe": "<what she wears>"},
  "swap": [{"from": "<copied from the swap list>", "to": "<the new person, in the same pose and crop>", "kind": "drawn"}]}
]}
```

(Five rows in yours. The example shows the three shapes a row can take.)

Nothing else in your output. No new headlines, no copy, no offer, no
production notes, no opinion about which will win.
