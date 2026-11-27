# Stage 8s — lay the finished email into its format's sections

You are given a FINISHED, CHECKED email and the format it is going out in. The
format is a stack of sections, like a short landing page. Your job is to move
the email's own words into those sections so it reads as a designed email:
short, punchy, scannable, every section doing one job.

## THE RULES — read before anything else

1. **No new claims.** Every fact, number, price, guarantee, ingredient,
   result or customer quote you write must already be in THE EMAIL or in
   THE FACTS below. If a section asks for something neither has, leave that
   field as an empty string. Never invent a number, a review, a name or a
   result to fill a gap.
2. **Prices and the guarantee are copied, never rewritten.** Use them word for
   word as THE EMAIL or THE FACTS give them.
3. **Tighten, don't pad.** You may cut, shorten and split the email's
   sentences, and write a 2–5 word title over a block. You may not add
   arguments the email does not make. Each text block: at most 2 short
   sentences. Titles: at most 6 words.
4. **Keep the voice.** It is the founder talking to a man about his skin.
   Plain, direct, a little swagger. No hype words the email doesn't use.
5. **Every section in the format appears, in order**, unless it is marked
   optional and the email has nothing for it.
6. **Pictures:** for every picture slot a section has, write one `alt` line
   saying what the picture shows, and for S and D slots one `brief` line:
   what the picture must show for this section to land. Do not describe
   products' looks — the real product photo is attached at generation.

## THE FORMAT

{format_json}

## THE FACTS (the only facts besides the email)

{facts}

## THE EMAIL

{email_json}

## WHAT TO RETURN

One fenced block, ```SECTIONS, holding JSON only:

```
{
 "format": "<format id>",
 "sections": [
  {"name": "<section name from the format>",
   "title": "<short title or empty>",
   "text": ["<block>", "..."],
   "items": [{"title": "", "text": "", "product": "<product id or empty>"}],
   "pictures": [{"kind": "S|P|D|R", "alt": "", "brief": "", "product": "<product id or empty>"}],
   "button": {"label": "", "link": ""}}
 ]
}
```

`items` is for chips (mechanism), product tiles (product-row), steps
(routine-steps) and grid tiles (review); leave it empty elsewhere. `button`
appears on cta sections only and uses THE EMAIL's own button label and link
(a second cta may use a shorter label of the same promise, same link).
