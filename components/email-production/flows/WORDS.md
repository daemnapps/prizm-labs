# Where every customer-facing word comes from (bound into each flow prompt as `{words_rule}`)

One home for this rule across the nine prompts in `prompts/`. It applies the email lane's own bank rules
(`../prompts/stage3-injection-v3-owner.md`, "THE CUSTOMER'S OWN WORDS") and `offers.NO_INVENTION`
(`../offers.py`) to flows and pages.

## The rule

1. **A line about the reader comes from a row.** Every sentence that names a pain, a want, a feeling, a doubt,
   a result, a comparison or what they tried before is built on a row from `{customer_language}`,
   `{proof_language}` or `{objection_language}`. Each row arrives as `- [row id] "text"` with its source.
2. **Cite it.** The SOURCES table under each email or page section lists every such line with the row id it
   came from. A line with no row id and no file is not written.
3. **A quote is word for word.** Words inside quotation marks are the row's text exactly (spelling, emoji and
   all, trimmed only at a sentence end) and are credited as the row's source credits them: a survey or review
   row is "a customer"; a forum, video or ad comment row is never a customer or a verified buyer.
4. **The brand's own sentence may be built on a row** (the row's words carried into the brand's voice) and is
   still cited. It never changes what the row says.
5. **Facts come from files, not rows.** A number, spec, price, count, guarantee, warranty, press line or stock
   claim comes from `{product_file}`, `{offer}` or `{offer_rule}`, word for word as filed, and the SOURCES table
   names the file. A row's own number ("over $100") is the speaker's, never the brand's claim.
6. **Weak rows stay weak.** A row marked `ATTRIBUTION ASSUMED`, or from a paid panel, is never quoted as
   something a customer said.
7. **No row fits: say so.** Write `NO ROW` in NOTES for that beat and either drop the beat or write
   `[UNFILLED: what is missing]`. An empty query is a fact about the bank, never a licence to write the line.
8. **The voice rules win.** `{language_bank}` sets how the brand talks. Where a row's phrasing loses to a voice
   rule, keep the voice rule and list the clash under NOTES.

## Check (a reviewer can mark each pass or fail)

- Every quoted string in the draft appears inside the text of the row its SOURCES line names.
- Every number in the draft appears in `{product_file}`, `{offer}` or `{offer_rule}`.
- No line credits a comment row to a customer.
- Every `[UNFILLED: …]` and `NO ROW` is listed under NOTES.
