# Stage 0c — does each scene do its section's job? (v1)

the owner, 2026-09-23: every part of the ad names the doctrine section it represents, so
sections can be swapped between versions. A label that doesn't match what the words DO
breaks every swap made from it. On Nova's proof run, a surgeon's pitch that the ad then
knocks down was labelled "solution" (it is failed-solutions), and a receipt for an
alternative's price was labelled "proof".

You check labels. You do not rewrite a scene, a word, or the order.

## The sections, from the marketing doctrine

{sections}

## The piece

- Framework it says it runs: {framework}
- Awareness it starts at: {awareness}

## The scenes, in play order

{scenes}

## How to judge each scene

1. Read what the scene SAYS and SHOWS, not where it sits in the ad.
2. Name the section whose "What it does" matches the scene's job in THIS ad.
   - A competing option the ad goes on to beat is `failed-solutions`, even when it is
     presented as advice.
   - The price of an alternative is part of beating it (`failed-solutions`), not `proof`.
   - `proof` is evidence FOR our product.
   - A scene with no words is judged on what it shows. An end card carrying the ask is
     `call-to-action`, and one carrying the price or guarantee is `offer`.
3. It fits when the given section is that section, or when the scene is honestly doing
   both jobs and the given one leads.
4. Check the ORDER last: an `offer` or `call-to-action` that plays before the thing it
   closes is an order problem. Name it, but don't move anything.

## What you return

JSON only, no prose around it:

```
{"scenes": [{"id": "<scene id>", "given": "<section id>", "fits": true, "should_be": "<section id>", "why": "<one plain sentence, quoting the words>"}],
 "order": ["<one line per order problem, naming the scene ids>"]}
```

`should_be` is always one of the doctrine's ids, spelled exactly. When `fits` is true it
equals `given`.
