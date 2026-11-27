Today is: {today}
Here is what triage decided: {triage}
Here is the placement plan: {placement}
Here is the email, end to end: {close}
Here is the subject set: {subject_set}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here are this avatar's voice rules: {language_bank}
Here is the brand context chosen for this source: {brand_context}
Here is the moment this send was scheduled for: {occasion}
Here is the day it goes out: {send_date}
Here is what this send may sell: {offer_rule}

**Everything named in this prompt as an example is an example of a SHAPE, not
of content.** No brand, product, person or price in this file belongs in the
email. The email's content comes only from the inputs above.

Put the finished email into its shape. The email is already written — the
argument, the lines, the close. This stage does not rewrite it. It lays it
into one fixed, simple layout that every email uses, and writes the two or
three things only this stage writes: the headline, and the direction for each
picture.

**THE SHAPE — always this, in this order**

1. The brand's logo — supplied by the brand, not by you.
2. **Headline** — the email's promise in one line.
3. **Hero picture** — one image that shows what the headline says.
4. **The copy** — the email's words.
5. **Offer** — only if this send may sell something: a short line, optionally
   one more picture of what is being sold.
6. **One button.**
7. The sign-off and the footer — supplied by the brand, not by you.

Nothing else. No product cards, no grids, no dividers, no quotes blocks, no
second button. If the written email leans on something the shape does not
have, carry it in the copy as words.

**HEADLINE.** One line, nine words at most. The promise the copy then earns —
said the way this avatar would say it, not as a slogan. It may be the control
subject line if that line is already the promise; it must not repeat the first
line of the copy.

**HERO PICTURE.** A direction a picture model can build from, written as a
plain description of one photograph:
- It shows the headline's idea in this avatar's own world — a real place, a
  real moment, the kind of thing they would recognise from their own week.
- Photographic, natural light, unstaged. Not an advert, not a studio set.
- **No words, letters, numbers or logos anywhere in the frame.**
- No before-and-after, no close-up of skin or a body presented as a result,
  no medical setting. A picture that implies a result is a claim.
- If a person is in it, say who in plain terms (age range, how they look,
  what they are doing) drawn from the avatar — never a named person.
- One sentence of `alt`: what the picture shows, for someone with images off.

**THE COPY.** The written email's body and close, carried over. You may cut
to fit — a line that only served a block this shape does not have — but you
may not add a claim, a number, a feature or a beat that is not already there,
and you may not smooth the voice. Paragraphs short, two to four lines each on
a phone. Do not open with a greeting and do not close with a sign-off — the
brand adds both.

**OFFER.** Obey what this send may sell, exactly:
- If it may sell nothing: `"offer": null`. The copy and the button must not
  name a price, a discount, a deadline or a bundle.
- If it carries an offer: one line stating it, with the price **verbatim from
  the offer bank** — never rounded, never invented. `image` is optional; when
  present it shows the thing being sold, plainly, and names the product key so
  the real product photo can be used as its reference.

**BUTTON.** One. The label says what happens when it is tapped, in this
avatar's words — not "Learn more", not "Click here". The link is the offer's
`Link:` from the offer bank when there is an offer, otherwise the product's
own link from the product file. If neither names one, write
`[UNFILLED: destination]` — never invent a URL.

**SUBJECT AND PREVIEW.** Carry the control pair from the subject set, and the
other pairs after it, unchanged.

Give me, in this order:

**THE EMAIL** — the email as a person reads it, top to bottom, in the shape.

**NOTES** — anything cut from the written email and why, anything left
`[UNFILLED: …]`. If nothing, say "nothing unresolved".

**THE EMAIL, AS DATA** — the same email in a code fence tagged exactly
`EMAIL`. It must agree with the readable version word for word.

```EMAIL
{
  "subjects": [{"subject": "…", "preview": "…"}],
  "headline": "…",
  "hero": {"prompt": "…", "alt": "…"},
  "body": ["paragraph", "paragraph"],
  "offer": {"line": "…", "image": {"prompt": "…", "alt": "…", "product": "product-key"}},
  "button": {"label": "…", "link": "…"}
}
```

`offer` is `null` when the send sells nothing; `offer.image` is `null` when no
second picture is needed. The first `subjects` entry is the control.
