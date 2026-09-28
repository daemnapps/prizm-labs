# PRIZM LABS — the tools

The generative marketing machine. This is Damon's brain for the business: the
strategy, the brands and the calls stay with him. What's here are the tools our
creative marketers use to turn those calls into finished work.

Take a video that already worked — a competitor's ad, an organic post,
anything — keep its structure, and rebuild it for one of our brands. You get a
script, a shot list, and a prompt for every frame.

**One way to use it:** clone this repo into Higgsfield Supercomputer (or Claude
Code) and tell it what you want. No kits, no copies.

**→ [daemn.co](https://daemn.co)** — see it working, with the same ad rebuilt
three different ways. **→ [How it works](https://daemn.co/how-it-works.html)**
— the whole line on one page: swipe, teardown, brief, make, hand-off, live,
performance, and the seven roles that carry it.

---

## Start here

Sixteen tools, one brand folder. Everything is plain text. Clone it and it is
all there; say "pull for updates" and it stays current. The numbers are the
folder names, kept stable so a link never breaks; two tools are marked
**team-only** where the part that builds them reads our private workspace —
what they publish is here for everyone.

| | What it is | Read it |
|---|---|---|
| **01** | **The brand folder** — every tool reads it, so a brand is set up once and never explained again. | [`brands/_TEMPLATE/`](brands/_TEMPLATE/) |

### Take something apart

Something already worked. These pull it down to the structure underneath, then
put our brand where theirs was.

| | What it is | Read it |
|---|---|---|
| **02** | **Video teardown** — any video in, your brief out. Written for someone who has never done this. | [`tools/02-video-teardown/`](tools/02-video-teardown/) |
| **03** | **Organic swipe pack** — 48 formats pulled apart from 377 posts that worked, some past a hundred million views. Rebuilt 2026-09-22. | [`tools/03-organic-swipe-pack/`](tools/03-organic-swipe-pack/) |
| **04** | **Paid ad swipe pack** — 6,269 live competitor ads across nine markets, reduced to the ten angle shapes that keep working. Rebuilt 2026-09-22. | [`tools/04-paid-ad-swipe-pack/`](tools/04-paid-ad-swipe-pack/) |
| **06** | **Image teardown** — the same chain pointed at a single frame. | [`tools/06-image-teardown/`](tools/06-image-teardown/) |
| **07** | **Copy teardown** — for a piece of writing rather than a video. | [`tools/07-copy-teardown/`](tools/07-copy-teardown/) |
| **09** | **Page teardown** — a landing page, same treatment. | [`tools/09-page-teardown/`](tools/09-page-teardown/) |

### Make something

| | What it is | Read it |
|---|---|---|
| **05** | **AI video production** — the brief becomes scenes, motion and finished shots. The chain that builds a brief from scratch. | [`tools/05-ai-video-production/`](tools/05-ai-video-production/) |
| **10** | **Image production** — stage two for statics, the twin of the video line. | [`tools/10-image-production/`](tools/10-image-production/) |
| **13** | **Pages** — swipe, construct, inject, base, then one variation per sub-avatar. No page gets written freehand. | [`tools/13-pages/`](tools/13-pages/) |
| **14** | **Copywriter** — the copy chain. | [`tools/14-copywriter/`](tools/14-copywriter/) |
| **—** | **Customer language** — every word the tools use comes from what the market said; this is the query over a brand's language, with the receipt on every row. | [`tools/language-layer/`](tools/language-layer/) |

### Plan it and finish it

| | What it is | Read it |
|---|---|---|
| **15** | **Outlier brief** — the second door. Start from an idea instead of someone else's video. | [`tools/15-outlier-brief/`](tools/15-outlier-brief/) |
| **16** | **Video edit** — cut sheets, in plain words rather than a timeline. | [`tools/16-video-edit/`](tools/16-video-edit/) |
| **20** | **Asset index** — a folder of footage becomes records you can search. | [`tools/20-asset-index/`](tools/20-asset-index/) |
| **21** | **Editor onboarding** — the front door for creative marketers: the walkthrough, the SOP, the two prompts they paste into Higgsfield, and the brief queue. *Team-only:* the queue reads our private workspace; the page, SOP and prompts are for everyone. | [`tools/21-editor-onboarding/`](tools/21-editor-onboarding/) · [the page](https://daemn.co/onboarding.html) |
| **22** | **Swipe library** — one front door to everything swiped: the formats, the torn-down videos, one feed per customer type, every competitor's live ads. Public half on the site, the rest on Drive. *Team-only:* the build reads our private workspace; the page is for everyone. | [`tools/22-swipe-library/`](tools/22-swipe-library/) · [the page](https://daemn.co/swipes/) |

### The shared parts

The tools import these. You do not run them yourself, but nothing runs without
them: the chain runner, the element system, the marketing doctrine, the run
layout, the name maps, the research gatherer and the quality checks.
[`components/`](components/)

**Do 01 first.** Nothing else works well on an empty brand folder — the tools
are built to say *"I don't know this"* rather than invent an answer, so an
empty file shows up as a question instead of a fake.

Then read
[`tools/02-video-teardown/HOW-TO-RUN-IT.md`](tools/02-video-teardown/HOW-TO-RUN-IT.md)
— the whole process in seven numbered steps.

---

## What you need

1. **Higgsfield Supercomputer** with this repo cloned into it — where the
   video gets watched, the chain runs and your scenes get made.
   ([affiliate link](https://higgsfield.ai?fpr=damon61) — costs you nothing
   extra.) Claude Code with the repo cloned works the same way.
2. **Google Drive** — where finished briefs and delivered work live, so the
   people who make the ads can reach them. `tools/21-editor-onboarding`.

Nothing gets installed. Nothing runs on your computer.

The exact models and settings are in
[`WHICH-MODELS.md`](tools/02-video-teardown/WHICH-MODELS.md) — don't leave it
on Auto.

---

## The two rules

**Copy the structure, not the content.** The shape is what earned the views;
the product is what changes. A scalp treatment and a countertop demo can be
the same format — that's the whole point.

**Nothing invented.** If the brand folder doesn't say what the product looks
like or how the customer talks, the tools say they don't know rather than
guessing. That's them working correctly. Ask Damon for that part.

---

## What it won't do

Publish anything. Spend anything on ads. Invent a customer quote. Make a
medical claim. Write in a voice it hasn't been given evidence for.

Those are hard stops in the prompts, not guidelines.

---

## Also in here

| | |
|---|---|
| [`docs/`](docs/) | The site itself — daemn.co is served straight from this folder. |
| [`SECURITY.md`](SECURITY.md) | What's exposed, what isn't, and the commit guard that keeps keys out. |
| [`receiver/`](receiver/) | The small workers behind the site's Ask box and forms. |

License: MIT (see [`LICENSE`](LICENSE)).
