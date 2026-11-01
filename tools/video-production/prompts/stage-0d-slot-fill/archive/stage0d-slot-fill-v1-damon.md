# Stage 0d — fill the holes from the brand's own files (v1)

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

1. Look for the answer in the files above. It counts only if a line in the files
   plainly says it.
2. If they do:
   - `fill` is the words that replace the hole: short and spoken, in the line's own
     voice. It carries the files' fact and adds nothing.
   - `receipt` is the exact line from the files, copied character for character, and
     `file` is the file it's in.
3. If they don't: `fill` is null. `cut` is the whole line rewritten without the hole
   and without whatever only made sense with it. Every other word stays exactly as
   written, in the same order.
4. Never change a line's meaning, never add a claim, and never touch a word outside
   the hole (except in a `cut`).

## What you return

JSON only:

```
{"holes": [{"id": "<hole id>", "fill": "<words>" | null, "receipt": "<exact line from a file>" | null, "file": "<file name>" | null, "cut": "<the line without the hole>" | null}]}
```
