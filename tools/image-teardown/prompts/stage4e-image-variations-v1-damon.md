Here is the format we are building on: {replication_spec}

Our brand put through it: {baseline_injection}

The headline set: {hook_set}

Our product: {product_file}. Our customer language bank: {language_bank}.

Write the **picture variations** — the different photographs this format can
be built on, each one shot on the same layout.

**The headlines are already written and they are not your business.** Six of
them exist, each moving on its own axis. You are not adding a seventh, not
rewording one, and not pairing pictures to headlines. This pass answers a
different question: **given this layout, what are the genuinely different
pictures that could sit in it?**

## Why this stage is cheap and the picture is not

On a static, a headline swap costs a recomposite — the same photograph, the
words reset over it, seconds and no generation. **A picture swap costs a
generation.** So the two are not the same kind of variation and must not be
priced as though they were: six headlines over one plate is nearly free, and
six plates is six times the spend.

That asymmetry is the whole reason this pass exists separately. Give the
smallest set of pictures that covers genuinely different ground, and say what
each one is *for* — so whoever runs the generation can stop after one, or
after two, and know exactly what they gave up.

## What makes a variation

**One variable moves.** Each picture changes exactly one thing against the
control, and names which. A picture that changes the body part *and* the
setting *and* the framing tells you nothing when it wins — you will not know
which half did it.

**It has to be a different picture, not a different rendering.** A new subject,
a new part of the body, a different moment of the same action, a different
setting, a different state of the product. Not: a warmer grade, a tighter crop,
a different lens. Those are the same picture and belong in generation as
retries, never here as variations.

**The format does not move.** Every variation obeys the layout skeleton, the
image mandate and the load-bearing elements exactly as the spec records them.
The spec's *swappable* list is where your freedom is, and it is the only place
it is. If a variation would break something the spec marks load-bearing, it is
not a variation of this format.

**It has to be defensible.** Every variation traces to something in the
supplied files — a concern the customer language bank ranks, a body part the
avatar actually names, a use the product file supports. A picture nobody's
words justify is a guess wearing a lab coat. Where the files do not support
one, write fewer variations and say so.

## What to give me

**The control first.** The picture the injection already specified, restated in
one line, labelled as the control. It is the baseline every variation is a bet
against. Never improve it.

**Then up to four variations**, and fewer where the files do not support more.
Four is a ceiling, not a target — the ceiling exists because each one costs a
generation and an untested picture nobody can justify is worse than an honest
short set.

**Use these exact labels, spelled and punctuated exactly as written below,
including the heading.** A person downstream turns each Picture into a prompt
by machine, and the label is how it is found. Measured cause, 2026-09-14: six
runs wrote the same six fields six different ways — `**VARIATION 1 — X**`,
`### Variation 1 — X`, `**VARIATION 1: X**`, `**Variable moved:**`,
`**Variable that moved:**`, `**Variable:**`, `**Picture:**`, `**The
picture:**` — and every variation but one was invisible to the tool that
builds the designer's prompts. Do not improve these labels.

```
**Variation 1: The name**

**Variable moved:** …

**Picture:** …

**What it is for:** …

**What it gives up:** …

**Cheaper first:** …
```

What goes in each:

- **The name** — three or four words, what it is, no cleverness.
- **Variable moved** — named plainly against the control: the body
  part, the subject, the setting, the moment, the product state.
- **Picture** — a shot list in the shared vocabulary, in the order subject
  → action → environment → composition → camera → light → grade → style →
  texture. Everything the spec fixes is carried through unchanged; only the
  moved variable and what it forces are different. Write it so it still
  reads correctly with the control's own picture placed immediately above
  it, because that is where it will be read.
- **What it is for** — the reason this ground is worth covering, in one
  sentence, naming the file that supports it.
- **What it gives up** — what the control has that this does not. Every
  variation loses something; a variation that appears to lose nothing has not
  been thought about.
- **Cheaper first** — say whether this variation can be reached by
  recompositing over an existing plate rather than generating a new one. Most
  cannot. The ones that can are free and should be run first.

**Close with the order to run them in**, cheapest and most-defensible first,
and the honest note of what is lost by stopping after the first, the second and
the third. Whoever runs generation will stop somewhere; tell them where.

Nothing else in your output. No headlines, no copy, no offer, no production
notes, no opinion about which will win.
