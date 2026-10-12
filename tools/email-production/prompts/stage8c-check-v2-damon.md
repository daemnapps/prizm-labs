Here is the finished email: {email}
Here is the product, as the brand's own file describes it: {product_file}
Here is the offer this send may carry: {offer_file}
Here is the spoken rule the copy was written to: {spoken}
Here is what this brand may sell today, and what is a draft: {offer_rule}

Do not use anything in this prompt as an example to copy. The products, names,
prices and wording above belong to one brand and one send; they are the thing
being checked, never a pattern to reach for.

Check this email before a person sees it. You are not rewriting it and you are
not judging whether it is good — four narrow questions, each answered by
quoting.

**1. PRODUCT FACTS.** Every statement the email makes about the product — its
name, what is in it, what each part is and does, sizes, prices, the guarantee,
shipping, any claim of a result. For each one, compare it with the product file
and the offer above. A statement is WRONG if the files say something different
(the email calls a serum a scrub; names a size the offer does not sell; promises
a result the files state more cautiously). A statement the files do not support
at all is UNSUPPORTED. Everything that matches, leave out.

**A PARTNER'S PRODUCT IS NOT OURS AND HAS NO FILE HERE.** If the email features
a partner's product, its facts come from the instruction the writer was given,
not from our product file, and the instruction carries the partner's own words
for it. Never mark a partner's own description UNSUPPORTED for being absent
from our files — the only thing to catch there is a claim the instruction does
not make.

**2. A DRAFT IS NOT A PRODUCT.** The block above lists what is live and what is
a draft. Quote anything the email says about a product on the never-linked
list. This outranks every other file: a brand's older notes may describe a
draft in detail, and it is still a draft.

**3. READ ALOUD.** Read the body aloud once.

A CHOP is a thought that has been cut mid-clause and left in pieces — a
fragment with no subject or no verb doing work a sentence should do, or a
dependent clause stranded as its own line. Give it joined back into the one
sentence a person would say.

Two complete short sentences in a row are NOT a chop. Short declarative
sentences are how this brand talks and how the reader talks back; they are the
voice, not a defect. Three or four of them running together are still not a
chop. Neither is a deliberate one-word line that is a whole thought.

And a join must be grammar a person would write. If the only way to join two
sentences is a comma between two things that could each stand alone, they were
never one thought — leave them. Do not hand back a comma splice. When in
doubt, leave it: this list exists to catch a thought that was broken, not to
smooth writing that is already the voice.

**4. TYPOS.** Misspellings and broken words, in the subject, the preview, the
headline, the body and the button.

Give me the four lists in plain words, then the same thing in a code fence
tagged exactly `CHECK`:

```CHECK
{
  "facts":  [{"quote": "…", "problem": "WRONG|UNSUPPORTED", "files_say": "…"}],
  "drafts": [{"quote": "…", "product": "…"}],
  "chops":  [{"quote": "…", "joined": "…"}],
  "typos":  [{"quote": "…", "fix": "…"}]
}
```

Empty lists when there is nothing. Never invent a problem to have something to
say — a clean email is a real answer, and the most common mistake this step
makes is calling the brand's own short-sentence voice a defect.
