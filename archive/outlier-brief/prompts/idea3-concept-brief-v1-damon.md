**No example in this prompt is an answer.** Any id, name, phrase, scene or
sentence shown below as an illustration of the SHAPE of a reply is a
placeholder — never copy it into your answer because it appeared here. Every
fact, claim, price, product detail, proof and customer quote in your answer
comes from the files you are handed below, and from nowhere else. If the files
do not carry it, the brief does not say it — it lists it under WHAT IS MISSING
instead. An invented proof is worse than a named gap.

You are writing ONE concept brief from one person's own idea for an ad. There
is no swipe and no reference ad. The owner will read this brief and approve it,
edit it or send it back before anything is made — so it has to read like a
person wrote it to another person.

**How it must read.** Plain, whole sentences, in the order a person would say
them. No chopped fragments. No headline-speak. No stacks of three adjectives.
No sentence that is only a noun phrase with a full stop after it. No em-dash
pile-ups. No marketing voice, no "imagine", no "picture this", no hype words.
If a sentence would sound strange said out loud across a table, rewrite it
until it would not. Short is fine; broken is not.

**The brief does not know its format.** It does not say video, image, email or
page, it names no shot, no layout, no length and no channel. A format is picked
only after the owner approves this brief, from a library this step never sees.

**The idea, exactly as it was given — it stays the owner's idea:**

{idea}

**Answers the owner has given:**

{answers}

**The round-out:**

{roundout}

**The awareness read:**

{awareness_read}

**What is settled for this brief** (looked up, never coined — write for exactly
this reader at exactly this awareness entry):

{chosen}

**What came back last time** (when the brief was sent back or held, fix exactly
these things and change nothing else without a reason):

{send_back}

---

**What the brand has on file.** Anything marked "(not on file …)" does not
exist for this run.

The brand's position:

{position}

The brand's stories:

{story}

The offers it sells today — the only prices that exist:

{offers}

The objections on file:

{objections}

The reader's card:

{avatar_card}

The angles on file — the only angles that exist:

{angles}

The customer's own words — quote them exactly or not at all:

{customer_language}

---

**The doctrine.** Read it; never restate it in your own words as if it were a
rule of yours. Where the brief leans on it, name the level, stage or framework
by its id.

{desire_dimensions}

{awareness_levels}

{sophistication_stages}

{ad_frameworks}

The only framework ids that exist: {framework_ids}

---

Your answer has exactly these labelled parts, under exactly these headings, in
this order. Every part is written in whole sentences unless it says "a list".

# THE BIG IDEA

First, the idea in the owner's own words — one or two sentences lifted from
what they gave, quoted. Then the same idea sharpened: two to four sentences
that say it more exactly without turning it into a different idea. If you
changed anything about it, say what and why in one sentence.

# THE ARGUMENT

One paragraph. The desire this idea walks into, in the reader's terms. The
mechanism — why the thing works, only as far as the brand's own files explain
it. The one belief the reader holds when they arrive and the belief they hold
when they leave.

# THE AWARENESS ENTRY

One paragraph. The awareness level this brief is written for, by its id, where
the reader is when they meet it, what has to be true for the idea to land
there, and what it must not assume. Then the sophistication stage, by its id,
and what that means the idea leads with.

# THE PROOF WE HAVE

A list. Each item is one whole sentence naming one piece of proof the brand's
files actually carry for this idea, and the file it comes from. Nothing that is
not shown above.

# WHAT IS MISSING

A list. Each item is one whole sentence naming a proof, a fact, a permission or
a story the idea wants and the files do not hold. If a question was asked of
the owner and not answered, it belongs here.

# HOOK DIRECTIONS

Three to five directions, a list. Each is one or two whole sentences describing
an OPENING the idea allows and what it does to the reader at this awareness
entry. These are directions, not finished lines — do not write the hook itself,
and never write a customer quote that is not in the files.

# THE WORLD

One paragraph. Where this idea lives: the place, the people in it, what they
are doing, what it feels like to be there — drawn from the reader's card and
their own words, not from a stock picture. No camera, no layout, no format.

# THE FRAMEWORKS IT FITS

One to three frameworks, each by its id from the list above, each with one or
two sentences on why this idea fits that plan and which of its sections carries
the weight. If the idea bends a framework's order, say how.

# WHAT IT MUST NEVER CLAIM

A list. Each item is one whole sentence naming a claim this idea will tempt a
writer to make and must not: anything the files do not carry, anything the
brand's position rules out, any result, number, time frame or price that is not
on file, and the awareness level's own must-nots as they apply here.

# CONCEPT

End with ONE fenced block, tagged `CONCEPT`, holding valid JSON with exactly
these keys:

```CONCEPT
{
 "frameworks": ["<each framework id named under THE FRAMEWORKS IT FITS>"],
 "angle": null,
 "offer": null
}
```

`angle` is an angle id from the angles on file when this idea truly is one of
them, otherwise `null` — never bend an angle to fit and never invent one.
`offer` is an offer key from the offer bank when the brief leans on one offer,
otherwise `null`. Name a price anywhere in the brief only if it is that offer's
own price, written exactly as the bank writes it.

If a part cannot be written from the files, say so in one plain sentence under
its heading. Never leave a placeholder or a note to fill in later.
