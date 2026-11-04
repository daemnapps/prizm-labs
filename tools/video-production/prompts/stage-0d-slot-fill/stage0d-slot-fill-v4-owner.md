# Stage 0d — fill every hole (v4)

the owner, 2026-09-23: "go online and do a search to find the answer … so we don't have
any holes ever … we don't need to drop stuff or overcomplicate. We improvise and infer."

A brief can leave a hole in a line, like `[SLOT: …]` or `[UNFILLED: …]`. A hole left
in a line gets read out loud or printed on screen. **Every hole gets filled.** Nothing
is dropped, and nothing waits for the owner.

## Where the answer comes from, in this order

1. **The brand's folder** (`brands/{brand}/`). Search all of it, not just the product
   file: products, offers, position, story, customer research, reviews, support
   tickets. The core files are below. Use your tools for the rest.
2. **The web.** Search when the brand folder doesn't have it: what an alternative
   usually costs, how a treatment works, a typical routine.
3. **Inference.** Nothing found? Infer the most sensible, ordinary answer from the
   brief's context and say that you did.

**One guardrail.** The brand's OWN facts, meaning its price, guarantee, dose,
results, ingredients and claims, come only from the brand's folder. If the folder
doesn't have one, fill the line so it doesn't state that fact (still no hole), and
say so.

## The fill

- Short, spoken, in the line's own voice. The line must read as one natural line.
  If the fill repeats something the line already says, smooth only that repeat.
- Return the whole line after filling, in `line`.
- Keep everything outside the hole as written.

## The brand's core files

{brand_files}

## The holes, each with the line it sits in

{holes}

## What you return

JSON only, no prose around it:

```
{"holes": [{"id": "<hole id>", "fill": "<the words>", "line": "<the whole line after filling>", "source": "brand" | "web" | "inferred", "receipt": "<the exact line from a brand file, or the URL, or 'inferred from: …'>", "brand_fact": true | false}]}
```
