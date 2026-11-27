# PAGE WRITING — FILL THE STRUCTURE WITH OUR BRAND (v2)

<!-- v2 (2026-11-13) = v1 + a quote is only ever a row from the list below, never a review quoted in the product or brand files. -->

You are writing a complete web page for OUR brand. You get a page's STRUCTURE (its sections in order and the
persuasion job of each, already stripped of everything that belonged to the page it came from) and everything you
need about our brand, our product, our offer and our customers. You write every word of the page.

You never saw the source page and you must not try to reconstruct it. The structure tells you WHAT each section must
do for the reader; our files tell you WHAT TO SAY.

## The structure, and how far you may adapt it

Keep the order of the jobs and the arc of the page (where the reader arrives, where they leave). Inside that:

- **Headline, subhead, every section heading and every button are written new, for us.** Nothing is "kept".
- **The form may change to fit our format.** The target below says what format this page is. A roundup of other
  companies' products becomes a roundup we can own (for example the things to look for, the mistakes, the reasons,
  the steps), never a list of other brands. Item counts may change. A section whose job our files cannot honestly
  fill is dropped, and you say so in `adapted`.
- **Sections the structure marked as the source business's own** (its location, team, booking, related posts) are
  not in the structure and are not written. Our page has our own ask instead: the button to our next page.
- Every change from the structure (a form changed, a section merged, dropped or added) is one line in `adapted`.

## Where every word comes from

1. **Customer language — the language bank, raw rows only.** The rows below are real things our customers said, each
   with its row ID. Build the page's lines out of their words and phrasings: the reader's problem, what they tried,
   what they feel, what changed. Every block lists in `rows` the IDs whose words it uses. A block that quotes a
   customer (`quote`) carries one row's text word for word, unchanged, with that row's ID (a shorter quote is one
   unbroken stretch of the row's words, cut only at a sentence end). Quotes come ONLY from the rows listed under
   CUSTOMER LANGUAGE below: a review or testimonial printed in the product file, the brand files or anywhere else is
   not a bank row and is never quoted. Never invent a customer, a quote, a name or a number.
2. **The offer and the guarantee — the offer file, word for word.** Prices, bundles, gifts and the guarantee are
   written exactly as the offer file says, `source: "offer-file"`. If the offer file names no guarantee, the page has
   none. Never a guarantee, price or promise the file does not state.
3. **Product facts — the product file.** What it is, what it does, how it is used, what it is made of:
   `source: "product-file"`. Nothing the file does not say.
4. **Our position and story — the brand files.** They set the angle, the enemy, the mechanism and the voice.
5. **Not used:** past winning ads, ad headlines, any other brand's words. The page is built from the raw bank rows and
   our files only.

Claims stay as bold as our files allow, and inside the brand's compliance file.

## The target

This page is for: {target}

Format to write: {target_format}

The page's buttons all go to: {next_url}

## Pictures

Every picture slot the structure calls for (and any our format needs) is a `picture` block saying exactly what the
picture shows: who or what, doing what, where, how close, the light — concretely enough that a 3D set can be built
from it. People shown are our customer avatar (below). The product, when shown, is our product as the product file
describes it. No words, logos or badges in a picture.

## Output

Return ONE json block and nothing else:

```json
{
  "title": "the page's title tag",
  "meta_description": "up to 155 characters",
  "format": "the format written",
  "adapted": ["one line per change from the structure, and why"],
  "sections": [
    {
      "n": 1,
      "job": "the structure's job this section does (or 'added: <job>')",
      "blocks": [
        {"type": "eyebrow | headline | subhead | paragraph | bullets | steps | items | quote | faq | offer | guarantee | button | picture | note",
         "text": "the words (headline, subhead, paragraph, quote, button label, offer, guarantee, note)",
         "list": ["bullet or step lines (bullets, steps)"],
         "items": [{"title": "", "text": "", "rows": ["row ids"]}],
         "faq": [{"q": "", "a": "", "rows": ["row ids"]}],
         "shows": "picture blocks only: exactly what the picture shows",
         "aspect": "picture blocks only: 4:5 | 1:1 | 16:9",
         "rows": ["the bank row IDs whose words this block uses"],
         "source": "bank | offer-file | product-file | brand-file"}
      ]
    }
  ]
}
```

---

## THE STRUCTURE (from the teardown — jobs, not words)

```json
{structure}
```

## OUR BRAND

Brand: {brand}

### Position
{position}

### Story
{story}

### Voice
{voice}

### Compliance
{compliance}

## OUR PRODUCT — the product file
{product}

## OUR OFFER AND GUARANTEE — the offer file
{offer}

## OUR CUSTOMER — the avatar
{avatar}

## CUSTOMER LANGUAGE — raw language-bank rows (cite by ID)
{language}
