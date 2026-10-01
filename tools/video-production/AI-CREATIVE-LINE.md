# The AI Creative Line

**How a competitor's ad becomes one of ours, with nobody on set.**

Written 2026-09-11, from the first run that went end to end — a competitor
angle 01 → a hero product. Every number here is measured on that run, not
estimated. Where something broke, it says so and says what it cost.

This is the **AI route**. A creator brief is a different document for a
different job — see the split at the bottom, because getting it wrong is the
single most expensive mistake in the line.

---

## The line

```
SWIPE ─► TEARDOWN ─► INJECT ─► THE DR LOOP ─► AI BRIEF ─► CAST+VOICE ─► SCENES ─► MOTION
 pick a    what it     our      hooks, entry,   scenes by   who says it   clips     the edit
 winner    actually is  brand   close, audit    shot type   and how
```

Two machines, joined today. `components/video-teardown/` carries swipe through
brief. `this folder` carries scenes through clips. The AI brief
is the seam, and it is the thing that had to change.

---

## 1 · Pick the swipe

Not "a competitor video" — **the creative they are spending behind.**

a competitor: 407 ads pulled, clustered into 35 copy blocks. Block 01 carried
**248 of their 388 videos**. Inside that block, the creative duplicated most
times is the one the account is betting on. That is the swipe.

Duplication count is the signal. An ad cloned nine times is one they are
paying to keep alive.

> Records: `swipe-paid/<brand>/angles/`. Media mirrors to Drive,
> never the repo.

## 2 · Teardown — stages 0–2

| | | |
|---|---|---|
| **0 Triage** | 33s | Calls the lane. `ALREADY AN AD` skips expansion — the source has hook, proof and offer, so structure is inherited, not rebuilt. |
| **1 Teardown** | 35s | The source shot by shot: timestamp, visuals, on-screen text, transcript. |
| **1b Audience** | 15s | Reads the avatar off the source. Came back `fed-up-king` — which is FLEX's own lane, arrived at independently. |
| **2 Spec** | 15s | Brand and product stripped out. What remains is the reusable machine: phases, durations, what flexes and what is fixed. |

## 3 · Inject — stage 3

The brand goes in. The pharmacist's *"three face creams I'd never recommend"*
becomes *"three things I'd never recommend to a man struggling with razor
bumps"* — Tend Skin, switching razors, drugstore benzoyl peroxide. Their
retinyl palmitate becomes **10 sonic vibrations at 12,000 RPM**.

**It refuses to invent.** A fact not in the brand files comes back as
`[SLOT: customer count]` rather than a competitor's fabricated "73,000 Italian men".

## 4 · The DR loop — stages 4a–4f

Read → hooks → product entry → close → audit. The hook bank came back at
22.4k with **five variations, each carrying a receipt** to the avatar profile
or a customer verbatim.

The one that proves the system closed: **"Run your hand up your neck right
now. If it feels like braille, none of this is working."** Sourced twice —
the avatar profile and a customer's own words. Then the footage index returned
**three owned clips of men saying it**. A customer said it, the avatar recorded
it, the hook used it, the footage exists.

## 5 · The AI brief — stage 5

**This is where the AI route stops looking like the creator route.**

The brief emits **scenes, not frames**, and every scene declares a shot type
before anything else. The type decides what gets written:

| Type | What it is | What the scene carries |
|---|---|---|
| **A · TALKING** | Cast member says a line to camera. One banked still + the voice take, lip-synced. ~4s. | **The line and its delivery. Nothing else.** |
| **B · CINEMATIC** | Demonstration, insert, reaction, establisher. Written direction, 0–2 refs, 8–15s. | Action across the clip, camera, sound with negatives. |
| **C · PRODUCT** | Product alone. Photo + motion. Silent, slow, label-first. 8–9s. | Which product, how the camera moves. |

First run: **17 scenes — 6 A, 9 B, 2 C.**

### Why this changed (Damon, 2026-09-11)

> *"We don't need frames. What we need are the scenes clearly described. I
> experienced this creating AI video ads for the brand and that was one of the
> biggest issues. It was also eating up a lot of credits."*

The brief was writing a full description for every beat, including talking
beats. A single-presenter script is mostly talking beats, and a talking beat
needs **one still and a voice take — no prompt at all.** Every one was being
generated from scratch instead of reusing a picture we already had. That is
the credit burn, and it is also where drift comes from.

**The governing rule, from `frames-by-edit.md`:** never describe anything the
reference already shows. The picture carries the composition; the words carry
only the change. Re-describing the room or the wardrobe tells the model to
rebuild them — which on a brand run put the mistress's denim jacket on the
lead, and produced 144 flagged deviations that were really one failure counted
144 times.

So the cast block and the world block are written **once**, and a scene names
a character rather than re-describing her.

## 5b · ASK THE LIBRARY — before a single credit is spent

**This is a gate, not a suggestion.**

```
python3 machine/footage.py <run>
```

Every scene goes to the footage index before anything is generated. The answer
is written into the storyboard as `source_plan`: **cut** or **generate**.

**Measured on the first run, 2026-09-11.** The whole ad was generated —
thirty-three clips, about 330 credits — without the index being asked once.
**Twenty-five of the thirty-three had owned footage in it.** The right number
to generate was eight.

The tool existed. Every card on the storyboard had a "Find footage" button.
Nothing in the chain required pressing it, so it was never pressed.

**Owned footage wins even when both would work.** It is real — a real man's
real neck, filmed. It costs nothing. It cannot drift from the product, invent
a wordmark, or stand a tripod in the shop. And it is the brand's own proof,
which is the one thing a competitor cannot copy.

Generate what the library cannot carry. That list is short, and it is the list
worth spending on.

## 6 · Cast and voice — the bank

Nobody is invented at brief time if the brand has already built them.

**Footage first.** The brand owns 1,342 indexed clips. Casting delivered footage
is the first thing to try; the synthetic cast exists for the beats the footage
does not contain.

**Then the bank.** `core-avatars/casting/` holds the handles, `ai-cast/` holds
the bible, `CAST.md` is generated from the records and is what the brief reads.

Each character carries two handles, because no single one works everywhere:

- **Element** — instant, multiple people in one shot, works across Nano Banana,
  Seedream, Kling, Cinema Studio. **The ad machine uses this.**
- **Soul** — trained on 6 refs, ~10 min. Higher fidelity, soul_2 / cinematic
  only, one person per generation. For video where the face has to hold.

### The voice

Base layer is the brand's own delivered footage, not a description. Mia's 24
minutes → five 90-second samples → clone → designed on top with the clone as a
0.35-weight anchor, so her timbre stays underneath.

**Two rules learned the hard way:**

**Pace belongs to the voice. Emotion belongs to the direction.** Writing
"speaks slowly" into the voice description AND slowing it at synthesis puts
two brakes on and reads as a drag.

**Ellipses are not punctuation.** Every `...` becomes a literal gap. That is
what reads as choppy.

Direction is attitude only — `[confident, easy, like she's mid-conversation]`,
`[a flick of amusement]`, `[certain, landing it]` — and it ships **inside the
brief**, on every type-A scene.

> Damon, on why the real shoot was unusable despite being right on every other
> axis: *"she was just reading it as she was saying it, and she couldn't really
> read and say it with emotion."* A clone inherits the read. Direction is the
> fix, and it belongs in the brief rather than in an editor's lap.

## 7 · Scenes → Motion

Hands off to `./` stations 3 and 4. Re-rolling is the
iteration: keep the same (still, voice) pair and re-roll until the motion
lands. **The pair is the asset.**

---

## Two lines, not one chain with a flag

**Ruled 2026-09-11.** This is the AI line. The creator line is a different
document for a different hand, and they are separate entry points now:

```
python3 machine/line.py teardown <video> --brand <brand>    swipe in, spec out
python3 machine/line.py creator  --label <run> --brand <b>  a person films it
python3 machine/line.py ai       --label <run> --brand <b>  nobody is on set
```

Reading the swipe is shared because it is genuinely the same work — two
teardowns of one source would drift, and then the lines would disagree about
what the video was. Everything after the spec is separate.

It used to be one chain with `--route`, and the flag was a noun the stages
repeated back rather than a fork they obeyed: the AI brief called its picture
field `Film:` on a line whose own first sentence says nobody is filmed, and the
stage that writes the page a creator reads ran on a line with no creator.

## The split — what actually differs

| | AI route | Creator route |
|---|---|---|
| Who performs | banked cast | a real person |
| Stage 6 (frames) | **skipped** | runs — a person filming needs to see the shot |
| Brief shape | scenes by shot type | shot list with reference frames |
| Voice | banked recipe + per-scene direction | theirs |

> *"When it comes to content creator briefs, just some baseline frames are
> fine. When it comes to actual ad production, the brief you need to give is
> set up differently."* — Damon, 2026-09-11

The chain enforces it: `--route ai` skips stage 6.

---

## What each thing costs

| | |
|---|---|
| Full chain, swipe → brief | **~20 min**, mostly stages 4b and 4c |
| Character sheet (`soul_cast`) | 0.12 credits |
| Reference angle off an Element | ~1 credit |
| Soul training | ~10 min, 6 refs |
| Voice clone (IVC) | free, 5 samples |
| Voice design pass | ~1 cent, 3 previews |
| Stage 6 frames on the AI route | **skipped — this was the expensive mistake** |

## The mistakes, so they are not repeated

1. **Filing a role as OPEN when the brand already owns it.** The authority
   figure was marked open; the brand had contracted estheticians with delivered
   footage. The injection dutifully wrote a slot with nobody in it.
2. **Letting the brief invent a cast.** Stage 5 was never handed the casting
   files, so it wrote its own esthetician — and named her one letter from a
   real contracted creator. The bank is bound to stage 5 now.
3. **Pitch-shifting a voice down to make it warmer.** A shifted-down woman
   reads as a man, and leaning harder on the anchor made it worse.
4. **Changing two things at once.** Fixing pace by redesigning the voice
   changed the accent. One axis at a time.
5. **Generating stills for talking beats.** The whole reason this document
   exists.
6. **Letting owned footage quietly rewrite the format.** The one worth
   understanding properly — see below.

---

## The failure worth studying

Damon, looking at the first generated scenes: *"why are we using such a sterile
looking background and we're not showing the actual products guys are using
like the swipe had?"*

He was right, and tracing it stage by stage found something structural rather
than a bad prompt:

| Stage | |
|---|---|
| **1 Teardown** | Saw it — *"Pharmacy interior, white shelving filled with boxed products"*, Nivea ×4, CeraVe ×2 |
| **2 Spec** | Kept the mandate — *"physically hold and point to high-volume, **recognizable** category competitors"* |
| **3 Injection** | **Dropped both.** Wrote *"a treatment room"* and *"no label"* |
| **4f Audit** | Missed it — checked spine, register, hook, mechanics, claims. Not elements |

**Why stage 3 dropped them is the lesson.** It was casting Mia's *delivered
footage*, and her footage is shot against a plain wall. So it substituted where
our footage was shot for where the format requires her to stand. Same instinct
blanked the props rather than sourcing the real ones.

That instinct — use what we own — is correct, and it is the whole reason the
footage index exists. What is not correct is letting the limits of what we own
rewrite a mandate without saying so. The room was the authority; a white shelf
reads as stock photography. The recognition was the argument; the viewer has
that exact bottle in his own bathroom, which is why the beat lands.

**The fix is a ledger, not a rule.** Stage 3 now accounts for every numbered
ELEMENT the spec issued — Carried, Adapted, or Dropped, each with its reasoning
or its cost. Stage 4f gained an eighth check that reads the ledger and fails a
missing row. A dropped element is sometimes right. A dropped element nobody
noticed never is.
