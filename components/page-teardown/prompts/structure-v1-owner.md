# PAGE TEARDOWN — STRUCTURE (v1)

You are tearing a web page down to its bones, the way a video teardown strips a video to its beats. What comes out is
the page's STRUCTURE and the PERSUASION JOB of each section — never its words, never what it sells, never who it is.

The next stage writes a brand-new page into this structure for a different brand, product and offer. Anything of the
source that leaks into your output leaks onto that page. So:

## What you never write

- No words, phrases or sentences from the page. Not its headline, its headings, its buttons, its list items, its
  quotes. Describe; never quote.
- No brand, company, product, person, doctor, editor, tester or author name. No town, city, region or address.
- No offer, price, discount, guarantee, shipping promise, appointment, booking, phone number or date.
- No claim, statistic, ingredient or method the source makes. Say what KIND of proof or method it is
  ("a list of practical steps the reader can do today", "a named expert's credentials"), never which.
- No category words of the source's topic in the job descriptions. Write the job so it fits any product in any
  category: "names the problem in the reader's words and says it is common", not "explains razor bumps".

## What you read

- `[NAV]`, `[HEADER]`, `[FOOTER]`, `[ASIDE]`, `[FURNITURE]` lines are the site's furniture. They are NOT sections of
  the page. List them only under `furniture` as kinds ("site menu", "booking button in the header", "related posts").
- Sections that only serve the source business (its location, its team, "about us", booking its service, related
  posts, its newsletter) are listed under `source_only` as kinds, and are not part of the structure — UNLESS the
  section does a persuasion job any page needs (for example "an expert is behind this advice" is a job: authority).
  Then it stays in the structure as that job, described generically.

## What you write

Return ONE json block and nothing else:

```json
{
  "format": "one of: how-to article | condition explainer | listicle / roundup | advertorial | sales page | product page | quiz | comparison | ranking blog | collection page | other: <say>",
  "page_job": "what the whole page does for the reader, in one generic sentence",
  "reader_arrives": "what the reader wants or believes when they land (generic, from the page's own framing)",
  "reader_leaves": "what the page wants the reader to do or believe at the end (generic)",
  "awareness": "unaware | problem-aware | solution-aware | product-aware | most-aware",
  "voice": "how it talks: person, register, sentence length, warmth, humour — no quoted words",
  "length_words": 0,
  "sections": [
    {
      "n": 1,
      "job": "the persuasion job of this section, generic, one sentence",
      "move": "the move it uses to do the job (e.g. 'names the reader's symptoms back to them', 'gives numbered steps', 'one ranked item with pros and cons')",
      "form": "headline | headline + subhead | paragraphs | bulleted list | numbered steps | repeated item cards | pros / cons | table | FAQ | quote / testimonial | expert box | offer box | button | picture | other",
      "items": 0,
      "item_shape": "for repeated items: what each item carries, generic (e.g. 'a name, a one-line verdict, three pros, one con, a spec line, a reviewer quote')",
      "words": 0,
      "pictures": [{"does": "what the picture does for the reader, generic (e.g. 'shows the problem close up', 'shows the product in use')"}],
      "button": "none | what the button asks the reader to do, generic",
      "proof": "none | the kind of proof, generic"
    }
  ],
  "proof_kinds": ["generic kinds of proof the page leans on"],
  "ask_pattern": "where and how often the page asks the reader to act, generic",
  "furniture": ["kinds of site furniture seen"],
  "source_only": ["kinds of sections that only serve the source business, left out of the structure"]
}
```

Today is {today}.

The page, as captured from {source_url}:

```
{source}
```
