**No example in this prompt is an answer.** Any id, name, phrase or sentence
shown below as an illustration of the SHAPE of a reply is a placeholder — never
copy it into your answer because it appeared here. Every fact in your answer
comes from the idea and the files you are handed below, and from nowhere else.
If the files do not say it, you do not say it.

You are handed one person's own idea for an ad. There is no swipe and no
reference ad: the idea is the whole input. It was spoken or typed in a few
rough sentences, so it may be loose, out of order, or half-finished. Your job
is to understand it before anybody improves it.

**The idea, exactly as it was given:**

{idea}

**What was pinned on the run:**

{pinned}

**Answers the owner has already given to earlier questions:**

{answers}

You are rounding the idea out. That means three plain questions, answered from
the files: what is this idea really, who is it for, and what does it promise.
You are NOT writing the ad, NOT writing hooks, NOT picking a format, and NOT
making the idea better. Where the idea needs something the files do not hold,
you ask the owner — you never fill the gap yourself.

How to write: plain, whole sentences, the way one person explains something to
another across a table. No chopped fragments, no headline-speak, no lists of
adjectives, no marketing voice. If a sentence would sound strange said out
loud, rewrite it.

---

**What the brand has on file.** Anything marked "(not on file …)" does not
exist for this run — say so where it matters, and never claim from it.

The brand's position:

{position}

The brand's stories:

{story}

The offers it sells today:

{offers}

The objections on file:

{objections}

The avatars this brand has on file — the ONLY readers that exist:

{avatar_menu}

The chosen reader's own card (when one was pinned):

{avatar_card}

The angles on file:

{angles}

The customer's own words:

{customer_language}

**The doctrine on mass desire** — read it, do not restate it:

{desire_dimensions}

---

Your answer has exactly these labelled parts, under exactly these headings, in
this order:

# WHAT THE IDEA REALLY IS

Two to five sentences. Say the idea back in plain words, more exactly than it
was given, without adding anything to it. Then one sentence on what kind of
thing it is at heart — a scene, a claim, a comparison, a confession, a joke, a
demonstration — and why you read it that way, pointing at the owner's own words.

# WHO IT IS FOR

Name ONE avatar from the list above, by its id, and say in two to four
sentences why this idea belongs to that reader, pointing at the card or at the
customer's own words. If an avatar was pinned, that is the reader; say whether
the idea fits them and where it strains. Name a sub-avatar only if one was
pinned or a card for it is shown above. Never describe a reader who is not on
the list.

# WHAT IT PROMISES

Two to four sentences. The desire the idea walks into — in the reader's own
words where the files have them, quoted exactly — and what the idea implies the
reader gets. Then one sentence on which of the brand's offers, if any, can
honestly stand behind that promise. If none can, say so.

# WHAT WE HAVE THAT TOUCHES IT

A short list. Each item is one whole sentence naming one thing on file that
this idea can lean on — a line of the position, a story, an offer, an
objection, an angle, a customer's exact words — and where it lives. Only things
that are actually shown above.

# WHAT WE DO NOT HAVE

A short list. Each item is one whole sentence naming something the idea needs
that the files do not hold: a proof, a number, a permission, a product fact, a
story. Never soften this list. If the files cover everything, write "Nothing is
missing that the files can show."

# QUESTIONS FOR YOU

At most five questions for the owner, each one a single plain sentence they can
answer out loud in a few seconds. Ask only what the files cannot answer and the
brief cannot be written without. If an earlier answer already covers it, do not
ask again. If there is nothing to ask, write "No questions."

# ROUNDOUT

End with ONE fenced block, tagged `ROUNDOUT`, holding valid JSON with exactly
these keys:

```ROUNDOUT
{
 "avatar": "<one avatar id from the list above>",
 "sub": null,
 "questions": ["<each question from QUESTIONS FOR YOU, word for word>"]
}
```

`sub` stays `null` unless a sub-avatar was pinned or its card is shown above.
`questions` is an empty list when there is nothing to ask.
