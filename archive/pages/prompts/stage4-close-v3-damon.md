Today is: {today}
Here is the injected page: {injection}
Here is the source page, complete: {source}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here are the avatar's voice rules: {language_bank}
This page is `{page_name}`; every ask hands off to `{page_next}`.
For checks 6-7 below — verification (where proof should land) and the
offer-close rules (the anchor, the guarantee): {verification} {offer_close}

**This is a clean injection; the page is already written.** This stage does not write a close and does not touch the words. It checks the injected page against the source, once, hard, and hands on the page with the check attached.

Check, in this order:

1. **Completeness.** Walk the source top to bottom. Every source line is on the injected page, in the same place. Anything missing is restored from the source, verbatim, and listed.
2. **Over-reach.** Any line on the injected page that differs from the source at something other than a product fact is put back to the source's wording, and listed. A product fact is: the product's name, exfoliant or texture, the places it is used, how long and how often, what it feels like in use, its label, its numbers, its price, its size.
3. **Facts.** Every swapped fact matches the product file or the offer file word for word. A fact that matches neither is flagged `FACT NOT ON FILE` and left as the source had it.
4. **Bans.** Every line — kept or swapped — is checked against the ban list and the never-pair rules (no dated result promise, no subscription language, the ruled guarantee wording where the offer file makes it verbatim). A kept line that breaks one is flagged `SOURCE BREAKS BAN`, not edited. A swapped line that breaks one is fixed at the fact only.
5. **Asks.** Every button and ask reads exactly as the source's did and hands off to `{page_next}`.
6. **Proof placement.** Read against the verification rules above: does the
   page's existing proof (as kept or swapped) land at the beat where doubt
   would peak, or did the swap move it out of that place? Report only — this
   check never moves a block or rewrites a word.
7. **The anchor and the guarantee.** Read against the offer-close rules
   above: does the swapped price still sit against a bigger anchor rather
   than standing bare, and does the swapped guarantee still restate every
   promise the page makes (the final intensification), the way the source's
   did? Flag `ANCHOR LOST` or `GUARANTEE THIN` where a swap weakened either —
   report only, do not rewrite.

Give me:

**THE PAGE** — the injected page, complete, with the corrections from 1–5 applied. Nothing else changed.

**THE CHECK** — what 1–7 found, each as a line: the section, the source line, what was done. If nothing was found under a step, say `clean`.

**FOR A HUMAN** — every `FACT NOT ON FILE`, `SOURCE BREAKS BAN`, `ANCHOR LOST` and `GUARANTEE THIN`, one line each, with the source line quoted.
