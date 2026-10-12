Today is: {today}
Here is what triage decided: {triage}
Here is the record of the source: {record}
Here is the brand-free construct: {spec}
Here is the placement plan: {placement}
Here is the email, end to end: {close}
Here is the subject set: {subject_set}
Here is the product: {product_file}
Here is our offer: {offer_file}
Here are this avatar's voice rules: {language_bank}
Here is the brand context chosen for this source: {brand_context}
Here is the moment this send was scheduled for: {occasion}
Here is the day it goes out: {send_date}
Here is the week this email lands in: {live_read}
Here is what this send may sell: {offer_rule}

Turn the argument into the email as it will actually be built.

Everything before this stage was content. This stage is where it becomes an
object with blocks in it — and **only** that. You are not rewriting the
argument, not improving lines, not adding a beat. If a line has to change to
fit a block, the block is wrong, not the line.

**The placement plan is binding.** It already decided the scroll budget, how
many buttons and where, how many images and what each is for. This stage
executes that plan. A block count that does not match the plan is a defect —
if the plan genuinely cannot be executed, say so with a number rather than
quietly building something else.

**THE BLOCK VOCABULARY**

These are the only types. **Never invent one.** If this email needs something
not on the list, build it from what is here and say in a note what was missing.

| Type | What it carries |
|---|---|
| `preheader` | the preview text — always first, exactly once |
| `headline` | the largest line on the screen |
| `subhead` | a smaller line supporting a headline |
| `copy` | body copy; one paragraph or a tight run of them |
| `image` | a picture, with the direction to make it and its alt text |
| `quote` | a review or a customer's words, with who said it |
| `bullets` | a short list, when the argument is genuinely a list |
| `button` | a CTA, with what it says and where it goes |
| `product` | a product card: picture, name, price, its own button |
| `divider` | a rule, when the argument genuinely turns |
| `ps` | the PS, if stage 7 wrote one |
| `signoff` | who it is from, in their own words |
| `footer` | unsubscribe and address — required, exactly once, last |

**IMAGE BLOCKS ARE JOBS FOR THE IMAGE LANE**

For every `image` and every `product`, write:

- `image_brief` — what has to be true in the frame for this to do the job the
  placement plan gave it. Written so it can be handed to the image lane's
  injection stage and built. Not a description of a nice picture.
- `alt` — real alt text. Written as a sentence a person with images off should
  be able to read and lose nothing structural. `alt` is not a filename and it
  is not a caption for the sighted.

An image whose alt text carries a claim that appears nowhere else in the email
is a claim hidden from most readers. Move it into copy.

**BUTTONS**

`label` is what it says — in the bound voice, not house CTA language. `href` is
where it goes; use the destination the placement plan or the product file
names, and where none is named write `[UNFILLED: destination]` rather than
inventing a URL.

**Every price, pack size and guarantee comes verbatim from the offer file.**
Not rounded, not softened, not paraphrased. A guarantee's conditions travel
with it.

Give me, in this order:

**THE EMAIL, BLOCK BY BLOCK** — human-readable. Each block numbered, typed,
with its content in full. This is the version a person reads to check it.

**NOTES** — anything the plan asked for that could not be built, anything left
`[UNFILLED: …]`, any block type that was missing from the vocabulary. Plainly.
If there is nothing, say "nothing unresolved".

**THE BLOCKS** — the same email as a fenced JSON array, in a code fence tagged
exactly `BLOCKS`. This is the version that renders, so it must agree with the
human-readable one exactly.

```BLOCKS
[
  {"type": "preheader", "text": "…"},
  {"type": "image", "image_brief": "…", "alt": "…"},
  {"type": "headline", "text": "…"},
  {"type": "copy", "text": "…"},
  {"type": "quote", "text": "…", "attribution": "…"},
  {"type": "bullets", "items": ["…", "…"]},
  {"type": "button", "label": "…", "href": "…"},
  {"type": "product", "name": "…", "price": "…", "image_brief": "…", "alt": "…", "label": "…", "href": "…"},
  {"type": "divider"},
  {"type": "ps", "text": "…"},
  {"type": "signoff", "text": "…"},
  {"type": "footer", "text": "…"}
]
```

The example above shows the fields each type takes. It is not a template for
this email — build the array the placement plan calls for, in the order the
argument runs, using only the types it actually needs.
