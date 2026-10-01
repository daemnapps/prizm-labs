**Everything named in this prompt as an example is an example of a SHAPE, not
of content.** No brand, product, person, price or phrase in this file belongs in
your answer. Your answer's content comes only from the inputs below.

Here is where the page was saved from (an address only — you cannot open it and
must not try): {source_url}

What the code already found before you, line by line: {code_findings}

Here is the saved landing page, top to bottom, every line numbered: {source}

Write an objective record of this page. **Observation only.** You are not
saying what would work better or what is weak, and you are not abstracting
anything. A later step turns this record into the page's construct, and it
needs a clean record to do it from. Every later step argues against this record
instead of re-reading the page and quietly seeing something different.

**How to read the lines.** The page was reduced to lines by code. A line
starting `#`, `##`, `###` is a headline of that size. `[IMAGE alt=… · file]` is
a picture — its alt text is what the page says the picture shows, and on many
pages a headline or a whole claim lives inside a picture. `[BUTTON words]` and
`[BUTTON words -> address]` are buttons; `[LINK words -> address]` is a link and
where it goes. `[VIDEO]`, `[FIELD …]` and `[CHOICE LIST]` mark a video, a form
field and a drop-down. `- ` starts a list item. The line numbers are yours to
cite.

**The code's list is a starting point, not a verdict.** It points at lines that
sat inside the site's menu, footer, cookie bar or a pop-up, and at lines that
look like damage. Confirm each one or overrule it, and find what it missed. A
strip across the top of the page that carries THIS page's offer is part of the
argument even when the code flagged it; a strip that would say the same thing
on every page of the site is furniture.

Your answer has FOUR labelled parts, under exactly these headings, in this
order. Nothing may sit in more than one of the first three.

# SECTIONS AS READ

What this one page argues, to its reader, in the order she meets it.

**THE PAGE AT A GLANCE** — one line each, read off the page, never guessed:

- PAGE JOB: `hands off` (it warms the reader and sends her to another page) or
  `takes the order` (prices, packs, a cart or a checkout button on this page)
- WHO IS SPEAKING: a named writer, an unnamed writer, a customer, an expert,
  the seller — and whether a real named person or a byline persona stands
  behind it
- WHO IT IS WRITTEN TO: what the page explains, what it takes for granted, and
  so how much the reader already knows when she arrives
- LENGTH: roughly how long the argument runs, in words

**THE SECTIONS, IN ORDER** — one entry per move the page makes, top to bottom,
numbered `S1`, `S2`, `S3`, … Each entry starts on its own line with its number.
For each:

- **its job, in three or four words**
- **the lines it covers** (`lines 12–31`)
- **the actual words that do the job, quoted exactly.** Quote — never
  paraphrase. A paraphrase here is a mistranslation every later step inherits.
  A picture that carries part of the argument: what its alt text says and what
  it is doing there.
- **every button or link that asks for the click**, quoted, and where it goes

A new section starts where the page starts doing a different job on the
reader, not where the markup starts a new box. Where a section comes round
again (the same ask block appearing twice), record it each time — repetition is
structure. Where a furniture item sits in the middle of the argument, leave a
one-line marker in its place — `(furniture — see F2)` — so the order still
reads true.

**THE HEADLINE, IN FULL** — quoted exactly, with its subline if there is one,
and separately what it does to make someone keep reading: names a person,
counts something, contradicts a belief, states a number, promises an outcome in
a time.

**THE TURN** — the one place the page pivots: a reveal, a reversal, a
confession, the moment the product is named. Quote it, give its section number,
and say plainly what changes at that moment. If the page has no turn, write
`no turn` rather than electing one.

**THE PROOF** — every specific thing the page leans on: a number, a named
person's words, a credential, a duration, a guarantee, a count of buyers.
Quote each, give its section number, and say what kind of proof it is. Where
the page is vague, record it as vague — a claim about volume is not a number.

**THE OFFER AND THE ASK** — what the page asks the reader to do, quoted, each
time it asks, with the section number. What it says about price, discount,
guarantee, shipping, scarcity — quoted exactly, figures and all. Where the ask
goes (another page, a cart). If the page carries no offer, write `no offer`.

**VOICE MARKERS** — six to ten features of HOW this writer writes, each with a
quoted example: sentence length, punctuation habits, capitalisation,
first-person habits, where it breaks into a list.

**WHAT IT NEVER DOES** — two or three things conspicuously absent: a claim it
could have made and did not, a beat it skipped, a kind of proof it never
shows. Absences are structure too.

# PAGE FURNITURE

The frame every page on this site arrives in, whatever the page is about: the
site's menu, its logo row, a site-wide announcement strip, a cookie or consent
bar, a pop-up or sign-up form, a cart drawer, a breadcrumb trail, the footer,
policy links, the company's address, payment-method icons, copyright and legal
lines, skip links.

The test: **would this part be identical on a different page of the same site,
about something else?** If yes, it is furniture.

Numbered `F1`, `F2`, … in the order they appear. For each:

- **what it is** — site menu / logo row / announcement strip / cookie bar /
  pop-up / cart drawer / breadcrumb / footer / policy links / address / legal /
  other
- **where it sits** — above the argument, inside it (between which sections),
  or below it, with its line numbers
- **its words and alt texts, quoted exactly**

If the page has no furniture at all, write `no page furniture`.

When you cannot tell whether a part is argument or furniture, put it under
furniture and say why in one line.

# SOURCE DEFECTS

Every place the saved page is broken rather than chosen: a template tag
showing as code, filler text left in, a word cut off, a doubled or dropped
character, a button that goes nowhere, a typo, a sentence that stops
mid-thought, a block that the save caught half-loaded.

Numbered `D1`, `D2`, …. For each:

- **the defect, quoted exactly as it appears** — broken, not corrected
- **where it is** — the line number, and which section or furniture item
- **what kind** — template tag as code / filler text / cut-off word / dropped
  or doubled character / dead button / typo / save damage
- **what it was evidently meant to say**, only when that is plain from the page
  itself; otherwise `unclear`

Everywhere else in this record the page is still quoted exactly, but each
defective quote carries its marker (`[D1]`) right after it.

If you find none, write `no source defects found`.

# STRIP

The same findings again, as data the code checks later steps against. One
fenced block, exactly this shape, valid JSON, nothing else under this heading:

```STRIP
{
 "furniture_words": ["every word or phrase that appears ONLY in furniture, quoted exactly as written"],
 "defects": [
  {"id": "D1", "quote": "the broken form, exactly as it appears", "meant": "what it was meant to say, or unclear"}
 ],
 "names": ["every proper name on the page, exactly as written: the seller, each product or range, each named person, each publication, each named mechanism or trademarked term"],
 "figures": ["every price, saving, percentage-off and money-value figure on the page, exactly as written"]
}
```

Use empty lists (`[]`) where there is nothing. Be complete rather than tidy: a
name or a figure left off these lists is one a later step is free to carry.
