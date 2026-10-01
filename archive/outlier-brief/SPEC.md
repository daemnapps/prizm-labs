# The Outlier Brief

**Status:** SPEC, for Damon to mark up. Nothing new is built yet. 2026-09-20.

Damon, 2026-09-20: *"It's so easy to just look at a swipe and say, 'we're just
going to remake this.' It's another thing to round out your research, actually
get creative and think without AI for a second… 'Let's execute this ad in this
way. This is my idea.' …flesh out a truly unique brief. At the end of that, we
can then select what format we want to put it into."* And: *"let's call it the
outlier creative flow… we'll literally be able to make any ad in any format
with high confidence and consistency and quality."* Renamed **Outlier
Creation** the same day (*"this shouldn't be in the video teardown because
it's not actually a teardown"*), then **the Outlier Brief** (*"instead of
outlier creation, let's call it the outlier brief because that's literally
what it is"*).

---

## 1. Two doors into the same machine

| | The first door — the swipe | **the Outlier Brief** |
|---|---|---|
| Starts from | somebody else's ad that already works | **your idea** |
| The thinking | read it, strip it to a template, inject ours | round the idea out with everything we know, then write the brief the idea implies |
| What it's for | proven structures, fast, at volume | the ads nobody else can make — the outliers |
| Ends in | the same chains, the same briefs, the same QC | the same chains, the same briefs, the same QC |

The Outlier Brief is the second door, made into a workflow. Today's
second door (`components/video-teardown/machine/compose.py`, 2026-09-18) takes
four picks — avatar, awareness level, format, framework — and writes an ad
from them. It has **no slot for the idea** and it only goes into video. This
flow adds both.

---

## 2. The flow, step by step

### Step 1 — The idea (you)

You write or say it rough. A line, a paragraph, a scene you're seeing, a
feeling, a reference. Plus anything you want pinned:

- brand · product or offer
- who it's for (avatar, sub-avatar) — or "you tell me"
- the awareness stage(s) to aim at — or "run it across all five"

Nothing else is asked of you here. The idea is the input; the machine does not
improve it before it has understood it.

### Step 2 — Round it out (the system)

The flow pulls everything we have that touches the idea — the same information
every chain reads, from the same places:

- the brand's **position** (`brands/<brand>/position.md` — line, mechanism, market stage)
- the avatar and sub-avatar cards, and the **customer's own words** (the language layer)
- the **research gatherer** — the rooms the avatar talks in, what they're saying now
- offers (the bank), objections, proof and stories on file
- the **marketing doctrine** — mass desire, awareness, sophistication, the
  techniques, the frameworks (`components/marketing-doctrine`)

Where the idea needs something the files don't have, it **asks you**, as a
short list of questions. It does not fill the gap itself.

### Step 3 — The foundation: awareness first

Every outlier ad is built on one awareness stage, stated up front: where the
reader is when they meet it, what has to be true for the ad to land there, and
what it must not assume. An idea can be run across several stages at once —
the same idea, written for the unaware and for the product-aware, are
different ads.

### Step 4 — The concept brief (format-free)

Your idea, fleshed out into one brief that does not yet know its format:

- **the big idea** — in your words first, then sharpened
- **the argument** — the desire it enters, the mechanism, the belief it moves
- **the awareness entry** and the sophistication stage it's written for
- **the proof** we actually have for it, and what's missing
- **hook directions** — the openings the idea allows
- **the world** — the scenes, the people, the setting it lives in
- **the frameworks it fits** (PAS, story, mechanism-led…) and why
- **what it must never claim**

**You approve or edit the concept brief before anything is produced.** This is
the one gate the flow cannot skip — it is the point of the flow.

### Step 5 — Pick the formats

From **one format catalogue across every medium**, you pick one or several.
Each row in the catalogue says four things:

| Field | Example |
|---|---|
| **Format** — the ad's structure and who carries it | storytelling ad · holistic healer authority · expert consult · testimonial montage · meme · demonstration |
| **Style** — the look | claymation · native Facebook image · UGC phone footage · studio · illustrated |
| **Medium** | video · static image · carousel · email · pre-sell page |
| **How it's made** — which chain, which route | video (creator / AI) · image (designer / AI) · email · page |

Format and style are separate on purpose: a storytelling ad can be shot on a
phone or made in claymation. You pick the pair.

Today the catalogue is scattered: 7 video formats in
`ai-video-production/formats/bank.json`, 8 frameworks in
`components/marketing-doctrine/ad-frameworks.json`, image templates in
`image-production/templates/`, 16 surfaces in
`components/copywriter/bank/format-bank.json`. **Storytelling, holistic healer
authority, claymation and native Facebook image are not catalogued anywhere
yet.** The catalogue becomes one file with all of them.

### Step 6 — Into the chains

The approved brief enters each chosen format's chain at its WRITING step —
past the steps that read a swipe, because there is no swipe:

| Medium | Enters | Status today |
|---|---|---|
| **Video** | the video teardown at stage 3, the way `compose.py` already enters it — the concept brief becomes the construct | **exists** for framework picks; needs the brief as its input |
| **Static image** | the image chain's writing, with the chosen template's slots as the zone table (no swipe to read one from) | **to build** — the image chain only knows swipes today |
| **Email** | email production's writer, with the brief as the argument | **to build** — close: email already takes an argument from the calendar |
| **Page** | the pages machine, with the framework's sections as the page's order | **to build** |

Each chain produces its normal deliverable — a creator brief, an AI scene
list, a static brief, an email, a page — every piece tagged with the concept
it came from, so one idea's pieces sit together.

### Step 7 — Every idea, every format (the grid)

One approved concept × the formats you picked × the awareness stages you
picked = a set of briefs in one run. `compose.py grid` already does this for
framework picks in video; the flow extends it to the concept brief and every
medium.

---

## 3. It is its own tool, not part of the video teardown

A teardown takes an existing ad apart. The Outlier Brief takes nothing apart —
it starts from an idea. So it lives on its own (`outlier-brief/`
for now), and the second door's code that sits inside the video teardown today
(`compose.py`, `ad-frameworks.json` reads) moves here as it is built out. The
teardown keeps what is a teardown; this tool feeds every chain, video only
being the first.

**The outlier brief — a brief any tool can use.** No such thing exists today:
every chain has its own brief shape. The concept brief in step 4 is the first
draft of one — a single brief that video, image, email and pages can all take
in. Getting it right is the long-term work; the first version only has to
carry one idea into video well.

## 4. What exists, what's new

**Reused as-is:** the research gatherer, the language layer, the marketing
doctrine, the position slot, the offer bank, the video chain from stage 3 on,
`compose.py`'s plan/run/grid machinery, every chain's QC.

**New:**
1. **Idea intake** — where you drop the idea (a Control Room box, a page, or a message).
2. **The round-out step** — gathers the context and writes your questions.
3. **The concept brief step** — one prompt, Opus, with your approval gate after it.
4. **The format catalogue** — one file across media, format × style × medium × route, with the four new formats added.
5. **Hand-offs** from the concept brief into video, then image, email, page.

---

## 5. What is proven and what isn't

Honest status, so nothing is assumed:

- **Proven:** writing an ad from chosen parts and running it through the video
  chain (`compose.py`, since 2026-09-18).
- **Not proven:** that a concept brief written from an idea carries through
  the video chain as well as a framework does — first test.
- **Not proven:** the image chain writing from a template instead of a swipe.
- **Not proven:** that the video production side can make every style — a
  claymation ad needs a production route that has not been tried.

Each is proven the same way: one real idea of yours, run to a finished brief,
read by you, before the next piece is built.

---

## 6. Build order

1. **The concept brief** — idea intake, round-out, the brief, your approval.
   Proven on one of your ideas, read on its own.
2. **Into video** — the approved brief enters the video chain through
   `compose.py`. Proven: one idea → one video brief.
3. **The format catalogue** — one file, the four new formats added, video's
   seven and the image templates brought in.
4. **Into static image** — the template-slot entry.
5. **Into email, then pages.**
6. **The grid** — one idea across formats and awareness stages in one run.
7. **The trigger** — a Control Room recipe or an idea box, so you drop an idea
   and get briefs back.

---

## 7. Settled by Damon, 2026-09-20

1. **Where the idea comes in:** Damon, speaking into his phone, to a Claude
   Code session that has the whole system — *"you're actually my agent… you
   have all my systems and my processes."* No box, no page: the session is the
   intake.
2. **Who approves the concept brief:** Damon, for now. It is a tool in the repo
   so anyone can run it later.
3. **How it's proven:** first run the system end to end and make sure it is
   clean; then set up the environment so it runs without his computer on.
