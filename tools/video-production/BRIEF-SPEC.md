# The video brief — one shape, every brand, every ad

> **2026-09-18:** the brief shape below stands. `machine/run.py start` also reads it (`plan_from_brief.py`), for both spines, alongside the board tools named below.

**Ruled 2026-09-14, Damon:** *"I want to standardize this brief template for all
video production. This is going to be a brand-agnostic process and interface
that is built for every single brief that we get out, and that needs to be
established in the chain."*

Brand-agnostic by construction: nothing in this spec names a brand, a person or
a product. Those are arguments.

---

## Why this exists — what it cost not to have it

One brief went through the chain on 14 September. Three machines read it and
**all three disagreed about what a brief is**:

| machine | what it expects |
|---|---|
| teardown stage 5 (writes it) | `### Scene 1 · 0:00 – 0:01.8 · 1.8 s` · `**On screen.**` · `**You say.**` · `**How.**` · a `> **Prompt**` block |
| `scenes.py` (storyboard reads it) | `**Scene 1 · … · TYPE B**` · `**Happens:**` · `> **Say:**` · `**Delivery:**` |
| `board.py` (cinema board reads it) | `out/plan.json` — `cast.elements[]` with `slot·name·id·role·desc·thumb`, `cutaways[]` with `id·over·at·seconds·why·place·subject·action·look·generate` |

None of it was written down. Fitting the brief to the cinema board meant
discovering one required field at a time from a stack trace — `over`, then
`desc`, then `role`, then `generate` is a dict not a bool, then `overrides` is a
map not a list. That is not a schema, that is an excavation.

## The two ad shapes, and which board each gets

There are **two**, and conflating them is what broke the day.

| shape | what it is | the board |
|---|---|---|
| **TALKING SPINE** | someone speaks on camera; inserts cover the take | `board.py` — the cinema board, `BOARD_PORT`, default 8456 |
| **VOICE-OVER** | nobody speaks on camera; every scene is an insert under one continuous VO | `storyboard.py` — port 8455 |

The cinema board is built around A-roll: a cutaway declares the beat it sits
`over`. An ad with **zero** A-roll has nothing to sit over, and the board cannot
render it — correctly, because its whole model is "inserts cover a take."

**So: a brief declares its shape, and the shape picks the board.** Do not force
a voice-over ad onto the cinema board. The source a VO ad is torn from never
shows the speaker; that is the format, not a gap.

## The scene header — one line, both shapes

```
**Scene <n> · <start> – <end> · <seconds>s · TYPE <A|B|C>**
```

| type | means | needs |
|---|---|---|
| **A** | someone speaks on camera | a still of the speaker, then the voice |
| **B** | a generated clip, or footage we already own | a clip |
| **C** | a product packshot, moved | the real packshot |

An ad with no TYPE A rows is a voice-over ad and says so in `overrides.aroll`.

## The scene body

```
**Happens:**  what is in frame and what moves. One action with a beginning and an end.
> **Say:**    the words, verbatim. Omitted entirely when nobody speaks.
**Delivery:** how it is said, or how the beat plays.
**Refs:**     every element id whose subject is VISIBLE in this frame.
**Still:**    the generation prompt, verbatim, minus the refs.
```

## The anchor rule — the one that is not optional

**Every identity visible in a frame carries its element on that frame — not only
the identity the scene is about.**

Measured, not argued. On the Braille set the brief attached her face element to
**1 scene of 19** because only one scene was *about* her face. She was visible in
most of them. Nineteen frames came back with several different women, several
different brushes and several different bottles.

> An identity that is not attached is an identity the model invents, every time.

`frames.py` enforces it: it scans each scene's prose for each identity's own
words and attaches the element whether the brief listed it or not, **printing
every addition** — a silent fix is a fix nobody can check. `--no-anchor`
reproduces the old behaviour, so the drift stays demonstrable.

## The tail

One block, appended to **every** generation prompt without exception: wardrobe
stated completely for every person in the ad, the light, the skin rule, and the
do-not-include list. Never left to inference — a setting that invites undress
with clothing unstated produces an undressed subject, which has reached a
published brief.

## The chain

```
brief.md
   │
   ├─ plan_from_brief.py --brand <b>   → out/plan.json   (the boards' input)
   ├─ adapt_brief.py                   → stages/5-brief.md (scenes.py's dialect)
   │
   ├─ TALKING SPINE → board.py       BOARD_PORT=<p>  → cinema board
   └─ VOICE-OVER    → storyboard.py                  → storyboard
```

`plan_from_brief.py` reads either header dialect and both field dialects, pulls
the cast from `brands/<brand>/elements/index.json`, and emits the plan in the
shape the boards actually read. It is the only file that knows all three
dialects, so a fourth machine never has to.


## The asks — what the editor makes beyond the base cut (2026-09-22)

The handoff (`prompts/stage-6-handoff/`, v5) ends with **`## THE ASKS`**: six
lines — scroll stoppers, headlines, variations, extra scenes, formats, styles —
each specified or refused with a reason. That section is what the editor or
designer produces after the base cut, in Higgsfield, from the same cast and
product references. The list, its defaults and its rules: `ASKS-SPEC.md`.

## Still open

- **The cinema board cannot render a zero-A-roll ad.** Today that is correct
  behaviour and the VO ad goes to the storyboard. If one surface should serve
  both, the cinema board needs a spine that is the voice-over rather than a
  talking beat — a real change, not a field.
- **`board.py` has no schema of its own.** The table above was reverse-
  engineered from its source and from the one run that works. It should validate
  its input and say what is missing, instead of raising `KeyError` inside a
  request thread and returning an empty reply.
