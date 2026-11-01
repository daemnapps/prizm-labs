# Stage 0d — fill the holes from the brand's own files (v3)

the owner, 2026-09-23: "you already found the answer in the product file, that's what
you should use anyways … this is why all of these should be an agnostic workflow."
A brief can leave a hole in a line, like `[SLOT: how much per use]` or `[UNFILLED: …]`,
when its writer didn't find the fact. A hole left in a spoken line gets read out loud.
You fill each hole ONLY from the brand's own files below, or cut it cleanly.

**Nothing invented.** A fill is words the files already say, quoted. If the files
don't say it, you don't fill it.

## The brand's files

{brand_files}

## The holes, each with the line it sits in

{holes}

## For each hole

1. Look for the answer in the files above. Read the hole for the QUESTION behind
   it, not its exact wording. If a line in the files answers that question, use
   it, even when it isn't the exact figure the hole names. (v2, the owner on Nova's
   "how much per use": the product file's "twice a week, not daily — it lasts
   longer than she assumes" is the answer to use.) If the files only answer a
   DIFFERENT question, it doesn't count.
2. If they do:
   - `fill` is the words that replace the hole: short and spoken, in the line's own
     voice. It carries the files' fact and adds nothing.
   - `receipt` is the exact line from the files, copied character for character, and
     `file` is the file it's in.
3. On a card or screen, a hole that IS the card's figure (a price, a count) and has
   no answer in the files: `fill` is null and `cut` is null. The card is flagged
   for the owner, never left showing a blank. If a DIFFERENT figure in the files would
   make the same point, name it in `suggest` with its receipt, but never put it in
   `fill`.
4. Otherwise, if they don't answer it: `fill` is null. `cut` is the whole line rewritten without the hole
   and without whatever only made sense with it. Every other word stays exactly as
   written, in the same order.
5. The filled line has to read as one natural spoken line. If the fill now says
   something the rest of the line repeats right after it (v3, Nova's S5: "…it lasts
   longer than you'd think. That's why twice a week lasts."), return the whole line
   in `line` with the hole filled and ONLY the now-repeated words dropped. Nothing
   else is reworded.
6. Never change a line's meaning, never add a claim, and never touch a word outside
   the hole (except in a `cut`).

## What you return

JSON only:

```
{"holes": [{"id": "<hole id>", "fill": "<words>" | null, "receipt": "<exact line from a file>" | null, "file": "<file name>" | null, "cut": "<the line without the hole>" | null, "line": "<the whole line after filling, repeats dropped>" | null, "suggest": "<another figure from the files that would make the same point, with its receipt>" | null}]}
```
