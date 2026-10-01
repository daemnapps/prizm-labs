**No example in this prompt is an answer.** The block at the end shows the
SHAPE of a reply only. Every quote you report must be copied, character for
character, from the brief you are handed; every "the files say" must be copied
from the brand's files you are handed. Report nothing you cannot point at.

You are checking one concept brief before its owner reads it. You are not
rewriting it, not improving it and not judging whether the idea is good. You
apply three written rules and report what breaks them.

**The brief:**

{brief}

---

**The brand's files — the only source of truth for this check.** Anything
marked "(not on file …)" does not exist.

The position:

{position}

The stories:

{story}

The offers sold today:

{offers}

The objections on file:

{objections}

The reader's card:

{avatar_card}

The customer's own words:

{customer_language}

---

**Rule 1 — nothing is claimed that the files do not carry.** A fact about the
product, how it works, what it is made of, what it does, how fast, for whom; a
result, a number, a time frame, a guarantee, a price; a story or a customer
quote presented as real. Each must be in the files above. Report each one that
is not, or that the files contradict.

Do NOT report: anything under WHAT IS MISSING or WHAT IT MUST NEVER CLAIM —
those parts exist to name what is not carried. Do not report a description of
the reader or of the idea's world as a product claim. Do not report the
doctrine's own terms (an awareness level, a sophistication stage, a framework
id). Do not report the owner's idea quoted back as the owner's idea.

**Rule 2 — no chopped thoughts.** The brief must read as whole sentences a
person would say. Report a thought that was cut into fragments: a run of two or
more sentence-pieces that are one sentence broken by full stops, a noun phrase
standing alone as a sentence, a stack of one-word sentences. Give the joined
sentence it should have been. A short whole sentence is not a chop. A list item
that is one whole sentence is not a chop. A heading is not a chop.

**Rule 3 — no typos.** A misspelled word, a doubled word, a missing word that
breaks the sentence, a broken merge of two words. Not style, not word choice,
not punctuation taste.

Reply with ONE fenced block, tagged `CHECK`, holding valid JSON with exactly
these three keys, and nothing before or after it. An empty list means the rule
found nothing — that is a normal, good answer, and you never pad a list.

```CHECK
{
 "facts": [{"problem": "NOT IN THE FILES", "quote": "<the brief's words, exactly>", "files_say": "<what the files say, exactly — or: nothing on file>"}],
 "chops": [{"quote": "<the chopped words, exactly>", "joined": "<the whole sentence they should be>"}],
 "typos": [{"quote": "<the words with the typo, exactly>", "fix": "<the corrected words>"}]
}
```

`problem` is `NOT IN THE FILES` when the files are silent and `WRONG` when the
files say something else.
