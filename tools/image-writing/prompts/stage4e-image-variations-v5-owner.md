Here is the format we are building on: {replication_spec}

Our brand put through it, the picture that gets made and approved first: {baseline_injection}

That picture's swap list, as data: {swaps_record}

The headline set: {hook_set}

The words on the approved picture, zone by zone, exactly as they are set on it: {approved_words}

Our product: {product_file}. Our customer language bank: {language_bank}.

The spice for this avatar, at this awareness level (what makes her words land; every headline uses one): {spice_bank}

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
- **Defensible.** Every headline is a variation of the approved headline
  (below), built from the headline set and the language bank, and every
  picture change comes from something in the files above: a worry the language
  bank ranks, a detail the brand step already put in the picture, a use the
  product file supports. Nothing nobody's words justify.

## How to build the five

## The headlines: the approved headline's shape, problem-aware, read cold

the owner, 2026-10-27, on a batch whose five headlines did not follow the approved
one: *"some of these sentences don't follow the structure of the initial
headline"* and *"we can use a fragment of one but it still needs to read
properly. like 8 years of what??? covering up what? 12 steps of what? dark
spots? brown spots, my spots. these are clear. this is a problem aware
creative, headlines need to be problem aware."*

The five are variations of the APPROVED headline above, the words actually on
the approved picture, not of the swipe's line and not of the headline set's
control. So every variation headline:

1. **Keeps the approved headline's structure.** The same mould: the same
   number of lines, the same fixed words in the same places, the same rhythm.
   Find the slots in it (the words that can change without breaking the
   mould) and change one slot, or two at most. If the approved headline is
   `DARK SPOTS? YOU AND ME / ARE NOT A PACKAGE DEAL`, its mould is
   `<the problem>? YOU AND ME / ARE NOT A <a pair that belongs together>`, and
   a variation fills those slots, it never writes a different sentence.
2. **Names the problem, every time.** This ad is problem-aware: the reader
   knows the problem and the headline says it in her own word for it, the way
   the language bank and the avatar say it (`DARK SPOTS`, `BROWN SPOTS`,
   `MY SPOTS`). A slot that does not name the problem never stands where the
   problem goes: `8 YEARS?` fails, `8 YEARS OF DARK SPOTS?` passes; `12 STEPS?`
   fails, `12 STEPS FOR 3 SPOTS?` passes; `COVERED UP?` fails.
3. **Reads properly, cold.** Material comes from the headline set and the
   language bank, and a customer's words may be cut to a fragment, but the
   whole headline reads as one sentence a person would say, and a stranger who
   has never seen the ad knows what it is about on one read. A fragment that
   only makes sense to someone who read the original post (`DOING JULY
   AGAIN`) fails. Never keep a word from a quote you are not using.

Before you write each row, check its headline against those three and fix it
until it passes all three. Then each one is a row:

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
