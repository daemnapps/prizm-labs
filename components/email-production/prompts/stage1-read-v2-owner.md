**Everything named in this prompt as an example is an example of a SHAPE, not
of content.** No brand, product, person, price or phrase in this file belongs in
your answer. Your answer's content comes only from the inputs below.

Today is: {today}
Here is what triage decided: {triage}
Here is the source: {source}

An objective record of this email. **Observation only.** You are not saying
what would work better, what is weak, or what we should do — a later stage
does that and it needs a clean record to do it from.

If the source is a teardown record from another lane rather than an email,
read it as it stands. Do not redo it, do not contradict it, and do not
translate it into email terms — stage 2 does that. Note what it does not
cover and move on.

## TWO THINGS ARE KEPT APART FROM THE MESSAGE — AND THIS IS NEW IN v2

RULED 2026-09-20, after it was seen live: a new email came out with the source
email's navigation and footer words written into its body as though they were
part of the argument, and with a typing mistake from the source's preview line
carried into the new preview line. Both happened because this record listed
everything in the source in one run, top to bottom, with nothing to say which
parts were the sender talking and which were the frame the sender's emails all
come in — and quoted a broken line faithfully without saying it was broken.

So this record has three parts, under their own headings, and nothing may sit
in more than one:

1. **THE MESSAGE** — what this one email says to its reader: the envelope, the
   blocks that argue, the buttons that ask, the offer, the proof, the voice.
2. **PAGE FURNITURE** — the frame every email from this sender arrives in,
   whatever the email is about: the logo row, a navigation row, category or
   shop-by links, a standing brand strip or slogan panel, a social-icon row,
   the footer, the unsubscribe line, the postal address, legal lines, "view in
   browser". The test: **would this part be identical in the sender's next
   email, on a different subject?** If yes, it is furniture.
3. **SOURCE DEFECTS** — places where the source is broken rather than chosen:
   a dropped or doubled character, a word cut off at the start or end of a
   line, a merge tag that shows as code or came out empty, a link with no
   target, a typo, a sentence that stops mid-thought because of the export
   rather than the writer.

Furniture is recorded so nobody downstream mistakes it for a move. Defects are
recorded so nobody downstream copies them. Neither is part of what the email
argues.

Give me:

# THE MESSAGE

**THE ENVELOPE**

- From-name and the shape of the address
- **Subject line, quoted exactly.** Character count.
- **Preview text, quoted exactly.** If there is none, say `no preview text` —
  that is a finding, not a blank.
- What the pair does together: whether the preview completes the subject,
  repeats it, or changes the subject entirely

**THE BLOCKS, IN ORDER**

**Message blocks only.** A logo row, a navigation row, category links, a
standing brand strip, a social row, the footer and the legal lines are NOT
listed here — they go under PAGE FURNITURE below, and only there. Where a
furniture block sits in the middle of the message, leave a one-line marker in
its place (`(furniture — see F2)`) so the order still reads true, and quote it
under its own heading.

Numbered, in the order they appear down the scroll. For each: the type
(copy / image / button / review / product / divider / PS), and its
content **quoted, never paraphrased**. Copy blocks quoted in full. Image
blocks described by what is in the frame and what it is doing.

The opening line of body copy gets quoted in full and called out — it is the
line the preview text was buying.

**THE CTA CENSUS**

Message buttons and links only — a navigation link, a category tile, a social
icon or a footer link is furniture and is not counted here.

Every button and every inline link: what it says, where it falls in the scroll,
and where it goes. Then the count, and whether the first one comes before or
after the argument has been made.

**THE WEIGHT**

Roughly how much of the email is image and how much is text. How many phone
screens it runs. Where the fold falls — what a reader sees before scrolling at
all.

**THE OFFER**

Where it appears, in what words, exactly. Where it conspicuously does not
appear. If there is no offer, say so.

**THE PROOF**

Every specific: a number, a duration, a named person, a review, a study, a
before-and-after. Quoted. Unspecific claims are not proof and do not go here.

**VOICE MARKERS**

Sentence length and rhythm. Punctuation habits. Vocabulary — the words this
speaker reaches for and the register they sit in. Contractions or not. What
this speaker **never** does.

Where the lane is organic this is the most load-bearing section in the
document; everything downstream depends on it being precise rather than
flattering.

**WHAT IT NEVER DOES**

The things this email conspicuously avoids — a claim it could have made and
didn't, a beat it skipped, a word it stayed away from. Absences are structure
too, and they are the part a replication most often loses.

# PAGE FURNITURE

Everything in the source that is the sender's standing frame rather than this
email's message. Numbered `F1`, `F2`, … in the order they appear. For each:

- **what it is** — logo row / navigation row / category links / standing brand
  strip / social row / footer / unsubscribe and address / legal / other
- **where it sits** — above the message, inside it (between which message
  blocks), or below it
- **its words and alt texts, quoted exactly**

Then one line: **`FURNITURE WORDS:`** every word or phrase that appears ONLY in
furniture, comma-separated, quoted exactly as written. This line is what later
stages check their own words against, so be complete rather than tidy.

If the source has no furniture at all (a plain-text email, a teardown record
from another lane), say `no page furniture` — that is a finding, not a blank.

When you cannot tell whether a part is message or furniture, put it under
furniture and say why in one line. A message block wrongly called furniture
costs one move; furniture wrongly called message gets written into our email.

# SOURCE DEFECTS

Every place the source is broken rather than chosen. Numbered `D1`, `D2`, ….
For each:

- **the defect, quoted exactly as it appears** — broken, not corrected
- **where it is** — subject line, preview text, which block, which furniture item
- **what kind** — dropped character / cut-off word / broken or empty merge tag /
  dead link / typo / export damage
- **what it was evidently meant to say**, only when that is plain from the
  source itself; otherwise `unclear`

Everywhere ELSE in this record the source is still quoted exactly, defects
included — but each defective quote carries its marker (`[D1]`) right after
it, so no reader of this record can take the broken form for the sender's
choice.

If you find none, say `no source defects found`.
