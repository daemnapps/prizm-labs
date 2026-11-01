# The model — four axes, multiplied

Ruled 2026-09-11. the owner: *"angles should be able to be used for any channel and
format. So LETS GET REALLY CLEAR — channels, angles, formats all of that."*

Everything that gets made is one point in a four-axis space. The axes are
independent: fixing one never fixes another, and nothing may be a value on two
axes at once.

```
   AVATAR        ×      ANGLE       ×     CHANNEL      ×     FORMAT      =  an asset
   who it is           what we           where it            how it is
    for                 claim             runs                built

   4 core,            15 in the          4: paid-social,     25 banks, one
   each with          bank, only         organic-social,     per asset type
   sub-avatars        the owner signs        email, owned-pages
```

## Why this exact shape

It is not invented here. Two places in the repo had already worked it out, and
this file only writes down what they agree on:

> **`lab/damon/copy/bank/channel-map.json`** — *"Copywriting is one brain…
> A channel decides the reading context; a format is a data row inside it;
> **the words always come from the same place.**"*

> **`brands/<brand>/email/email-types.json`** — *"A TYPE is what the email IS…
> Types are multiplied by a FORM (how it is built), a TREATMENT (how it is
> played) and an AWARENESS level."*

Both say: separate axes, each a closed set, multiplied. Not one list.

## The test for each axis

| Axis | The question it answers | The test |
|---|---|---|
| **Avatar** | who is this for? | Is it a description of a person? |
| **Angle** | what are we claiming? | Can you say it as one sentence a customer could agree or disagree with? |
| **Channel** | where does it run? | Does it change the reader's *state* — interrupted, chosen, permitted, arrived? |
| **Format** | how is it built? | Is it camera, layout, beat order, text behaviour, slot? |

## The rules that follow

1. **An angle is channel-free and format-free.** The same claim runs as a Meta
   static, a TikTok video, an email and a landing page. If a thing only works
   in one container, it is a **format**, not an angle.
2. **An angle belongs to the brand, not to an avatar** (the owner, 28 Oct 2026: "angles are just ways to start the conversation and each conversation varies by language of the avatar but the approach is the same"). Any angle
   can be aimed at any avatar; the avatar's language and the swipe say it. The
   avatar and the angle meet in the brief and the ad set. Sub-avatars are
   declared per asset, never as a second angle.
3. **A channel does not own words.** It sets the reading context and it owns
   surfaces (a headline is a paid-social surface). It never owns a claim.
4. **A format is scoped to one asset type.** The 50 organic-video structures
   are organic video only; they are not page formats or email templates. Every
   bank names its lane and says what it is NOT.
5. **Nothing is a value on two axes.** `slideshow-native` was an angle that was
   really a container. `Angle` is a row in the copy-surface bank, which is a
   claim filed as a format. Both are the same error in opposite directions.

## Still wrong, and known

**Eleven entries in the <brand> angle bank are formats** — `three-line-hook` is
a text template, `arrow-methods-grid` a slide layout, `product-as-method` a
placement rule. Seven of them are signed. Every one is a glow-up entry, which
is why the bank looks channel-coupled: those rows only work in one container,
which is the definition of a format.

They have not moved, and the reason is honest: **there is no bank for what they
are.** They are argument structures for static and slideshow creative. The
organic-video library is video only. The image-ad templates are render
templates — canvas, slots, typography — not argument structures. Opening a bank
for them is a naming decision, and naming decisions are the owner's.

**`lane` meant three different things and the addressing scheme used one of
them** — the asset lane (`organic-video`), the source lane (`paid | own |
organic`, `swipe-paid/corpus.py`), and the brand positioning lane (Brotherhood
/ 2.0). **Fixed 2026-09-11 by taking the ambiguous word out of the addressing
path**: the axis is `asset`, which the registry already called it and which
means exactly one thing. `corpus.py` keeps `lane` for the source axis, where it
is unambiguous, and the brand map keeps it for positioning. Three axes, three
contexts, and the one that names files no longer shares a word with the other
two.

The rule, now in the registry: *an address built on a word with three meanings
is the collision this registry exists to prevent.*
