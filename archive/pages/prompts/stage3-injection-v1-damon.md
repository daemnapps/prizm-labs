Today is: {today}
Here is what triage decided: {triage}
Here is the brand-free construct: {spec}
Here is the record of the source page, for reference: {record}
Here is our customer avatar: {avatar}
Here are this avatar's voice rules: {language_bank}
Here is real language selected for this stage: {language}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here is the brand context chosen for this page: {brand_context}
Brand: {brand_name}
This page is `{page_name}`. It is a pre-sell: it hands off to `{page_next}` and never takes the money itself.

**The language above is queried, not dumped.** These rows were chosen because of what they ARE — the kind of thing this stage needs — and ranked by how loud they were and how well sourced. They are real sentences real people said, each carrying who said it and where it came from.

Use their words. A row marked `ATTRIBUTION ASSUMED` is weaker evidence and a row from a paid panel is not a customer speaking; weigh them accordingly and never present either as something a customer said. If nothing in the rows fits, say so — an empty result is a fact about the bank, not a licence to write the sentence yourself.

Fill the construct's slots with our brand. **Substitution, never rewriting.**

The construct's moves, their order, their proportions and its voice rules are the template. You are answering the questions its slots ask — you are not writing a new page that resembles the old one. If you find yourself improving a move, stop: the move is not yours to improve, and a construct that gets improved one slot at a time arrives as generic brand copy with the source's outline faintly visible underneath.

**This is not the finished page.** It will read stiff in places and that is correct — the close comes later, the per-avatar variations after that. Getting a slot honestly filled matters more than getting a line to sing.

**The bank is evidence, not a script. Interpret it; do not transplant it.** Everything in these files was true of a particular person, in a particular body, at a particular moment. Re-judge every piece against what is actually being made: does it fit what this page is about, when it runs, who is speaking, the format, and is it what it appears to be — a customer verbatim, a marketer's angle line, a paid panelist. **Keep the truth, drop the frame.**

Work slot by slot:

- **Fill it from the supplied files.** Every figure, claim, price and guarantee comes from the product or offer file as written there. Never round a price, never firm up a hedge, never state a result the files state cautiously. Ingredients are said the way the product file's "how to say it" says them.
- **The narrator is a cast persona, never a real customer.** Real customers are quoted with their attribution; the first-person "I" of the page is the persona triage bound. Never give the persona a real customer's biography.
- **Reviews are reused, never written.** A slot that wants a review is filled from a review the brand already runs on its own pages or from a verified interview line, attributed as the file attributes it. If none fits, the slot is `[UNFILLED]`.
- **Search the supplied context before declaring a slot unfillable.** A slot wanting a customer's own words is answered by the evidence, the objection bank or the brand context — read them for an actual sentence someone said before concluding there isn't one.
- **If a slot genuinely has no honest filler, say so.** Write `[UNFILLED: <what is missing>]`, name where you looked, and leave the move standing. A missing beat plays worse than a beat that survived; a later stage can rewrite around a marked hole and cannot recover a deleted one.
- **Never add a move the construct does not have.** No extra proof point because we happen to have one, no price where the source showed none, no second ask where the source asked once.
- **A page-bound device the brand cannot honestly use** (a countdown, "sells out everywhere", a credential the narrator does not hold) is not copied. Name what it was doing and fill that job with what is on file, or leave the slot `[UNFILLED]`.

**The voice rules are binding.** {brand_name}'s house style does not override them, and the avatar's voice rules bind over both. Where a language-bank phrasing collides with a voice rule, the voice rule wins, and you note the collision in one line at the end. **The ban list is absolute** — a banned word does not appear even inside a quoted review unless the review is reproduced verbatim from a brand-owned page, in which case say so.

Give me:

**THE INJECTED PAGE** — the construct's moves in order, each now carrying real content, written out as continuous copy under a one-line label per move (`[1 · what the move is]`). Any unfilled slot stays visible.

**SUBSTITUTION LOG** — one line per slot: what the construct asked for, what filled it, and which file that came from. A slot filled from nothing on file is the one thing this stage must never do quietly, so this log is where it would show.

**COLLISIONS** — anything where the construct and our brand genuinely fight: a move that needs a claim we cannot make, a voice rule that contradicts the language bank, a load-bearing element with no honest filler, a page-bound device we cannot use. Name each and say which way you resolved it. Do not resolve a collision by weakening a claim — flag it and let a person rule.
