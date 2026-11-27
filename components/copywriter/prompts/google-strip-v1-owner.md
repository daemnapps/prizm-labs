*v1 (2026-11-23: the first Google campaigns carried raw customer lines instead of ads): the same swipe → strip → fill the Meta copy runs on (copy-format-strip), for Google's text ads. Competitors' live Google ads in, formats out. Run by `components/copywriter/machine/google_copy.py strip`; the parts in {braces} are filled by that tool.*

---

You are stripping real Google search ads into FORMATS, so new Google ads can be written by filling the same structure instead of from scratch. These ads are still running; the longer an ad has run, the more it has paid for itself. `days running` is shown beside each.

A Google search ad is a set of short headlines (30 characters at most) and descriptions (90 at most). Google shows two or three headlines side by side and one or two descriptions under them, in any order, so each line must stand alone.

A format is the line's own words, kept, with only the parts that belong to this one product, offer or brand replaced by a named blank in square brackets. Like this:

    REAL:   Lumin™ Men's Premium Skin Care
    FORMAT: [BRAND] Men's Premium [CATEGORY]

    REAL:   Get your skin clean in 30 seconds with LUNA 3.
    FORMAT: Get your [BODY PART] clean in [HOW FAST] with [PRODUCT].

## The rules

1. **Keep every word that carries the structure**: the verbs, the turns, the rhythm, the punctuation, the capitals. A format may not paraphrase the line: the fixed words are the line's own, in its order.
2. **Blank only what changes from brand to brand**: brand and product names, the category, the problem, body parts, ingredients and mechanisms, numbers, counts of customers or reviews, prices, discounts and offers, guarantee lengths, places, seasons. Write each blank as a plain name of what goes there, in capitals: [BRAND], [PRODUCT], [CATEGORY], [PROBLEM], [RESULT], [HOW FAST], [NUMBER OF CUSTOMERS], [RATING], [DISCOUNT], [GUARANTEE LENGTH].
3. **Never blank the whole line.** Two or three fixed words beside a blank stay fixed. A line that is nothing but a name ("FOREO Official store") becomes "[BRAND] Official store".
4. **One format per line below, every one, in order.** Keep a line's two halves when a description runs two sentences.
5. For each line name its **slot**: the one job it does in the ad, one of {slots}.

## The ads

{ads}

## What you return

Only one fenced json block, a list, one object per line, in the order given:

```json
[
  {"n": 1, "kind": "headline", "format": "[BRAND] Men's Premium [CATEGORY]", "blanks": ["BRAND", "CATEGORY"], "slot": "who-its-for"},
  {"n": 2, "kind": "description", "format": "…", "blanks": ["…"], "slot": "how-it-works"}
]
```
