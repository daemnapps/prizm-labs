Today is: {today}
Here is the teardown record: {teardown_record}
Here are this brand's avatars, and where their language sits: {avatars}

The video has been broken down. Decide **who our version speaks to**.

This pass exists because the answer was previously never given: every stage
that writes drew its words from whichever rows happened to be first in a file,
across every avatar the brand has. A brand with three avatars is three
different people, and blending their language produces copy that is precise
about a person who does not exist.

Everything downstream binds to what you decide here. A wrong answer draws
every later stage's words from the wrong person's mouth, and it will not look
wrong — it will look like copy that is slightly off for reasons nobody can
trace.

**Read the teardown, not the brand.** You are deciding who the source
actually speaks to and who the product serves in that context. Not who the
brand wishes it were talking to, and never whichever bank holds the most
rows — the biggest bank is the most tempting wrong answer available here.

---

**1 · AVATAR**

Name one, by its exact key from the list.

If none genuinely fit, answer `AVATAR: none fit` and say why in a line. That
is a real finding, not a failure: a source about a subject no avatar owns is
worth knowing about before a brief is written on top of it. Forcing a source
onto the nearest avatar is the most expensive mistake available at this
stage, because everything after it inherits the error silently.

**2 · FUNNEL**

`prospect` — has never heard of us. Nothing is assumed known: not the
product, not the category's mechanics, not why anything failed before.
`lead` — engaged, gave contact, has not bought. Knows roughly what this is
and has not been convinced.
`customer` — has bought. Never re-sell them the first purchase.
`churned` — bought, then refunded, cancelled or went quiet. Something went
wrong, and writing as though it did not reads as not knowing them.

Then one line: **what this reader already knows, and what would insult them
to be told.**

The list shows which funnels this avatar has language for. If the one you
pick is thin or empty, say so — the copy will have less real speech to draw
on, and that is worth knowing before it is written rather than after.

**3 · SUB-AVATAR**

Narrow only when the record proves it. A sub-avatar is a claim about which
version of this person the source speaks to, and the brand's own schema rule
holds here: **a wrong tag is worse than none.** If the teardown does not
demonstrate it, answer `SUB-AVATAR: none` and lose nothing.

**4 · TOPICS**

**A topic is a subject the source actually raises** — the thing being talked
about, not the kind of thing being said. It answers *what is this about*, where
the row's `use` tag answers *what is this line doing*.

Take them from the vocabulary the roster lists for this brand, using its exact
keys. That list is the whole of what exists; a topic you invent matches no rows
and silently narrows every later stage to nothing.

Name as many as the source genuinely raises and no more. There is no target
count — a single-subject video has one topic and that is a complete answer.

These filter the rows every later stage sees. Without them a stage asking for
objections gets objections about the wrong subject entirely — the right *kind*
of row about the wrong *thing*. A topic added speculatively pulls rows that
will read as off-subject.

---

**Cite the teardown for every answer** — a timestamp, a line, a described
scene. An answer you cannot point at is a guess, and a guess here is
inherited by nine stages.

**Decide nothing about our version.** Not its structure, not its opening, not
where the product goes, not how long it runs. Those are later passes and they
are better made after the hooks exist. This pass answers one question: whose
language should the rest of this run be written in.

Answer in exactly this shape, nothing else:

```
AVATAR: <key, or "none fit">
AVATAR WHY: <one line, citing the teardown>
FUNNEL: prospect | lead | customer | churned
FUNNEL MEANS: <one line: what this reader knows, and what not to tell them>
SUB-AVATAR: <key, or "none">
TOPICS: <comma-separated, roster keys only — as many as the source raises>
TOPICS WHY: <one line, citing the teardown>
```
