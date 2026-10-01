# Prizm Labs — the tools

The generative marketing machine, as the tools our creative marketers use to
turn a proven ad into finished work for our brands. **Prizm Labs is our
internal system — not for sale.** It is public so the people who work with us
can read every prompt; it is hosted at [daemn.co](https://daemn.co).

Take a video that already worked — a competitor's ad, an organic post,
anything — keep its structure, and rebuild it for one of our brands. You get a
script, a shot list, and a prompt for every frame.

**→ [daemn.co](https://daemn.co)** — see it working, with the same ad rebuilt
three different ways. **→ [How it works](https://daemn.co/how-it-works.html)**
— the whole line on one page: swipe, teardown, brief, make, hand-off, live,
performance, and the seven roles that carry it.

---

## How to use it — Higgsfield Supercomputer or Claude Code

The same three steps in either one:

1. **Clone this repo** into Higgsfield Supercomputer, or open it in Claude
   Code (`git clone https://github.com/daemnapps/prizm-labs`).
2. **Point it at a brand folder** — say which brand you are working on. The
   folder follows [`brands/_TEMPLATE/`](brands/_TEMPLATE/); every tool reads
   it, so a brand is set up once and never explained again.
3. **Run the tool** by saying what you want in plain words — "tear this video
   down for <brand>", "make the scenes for this brief", "edit this kit". Each
   tool's front page says what it takes and what comes out.

Say "pull for updates" and it stays current. Everything is plain text.

---

## The tools

Nine tools, one brand folder. Each tool carries the name it has in
production. Two are marked **team-only** where the part that builds them
reads our private workspace — what they publish is here for everyone.

| | What it is | Read it |
|---|---|---|
| **Brand folder** | Every tool reads it, so a brand is set up once and never explained again. Do this first. | [`brands/_TEMPLATE/`](brands/_TEMPLATE/) |

### Swipe and take it apart

| Tool | What it is | Read it |
|---|---|---|
| **My Feeds** | What already works, organic and paid: 48 organic formats pulled apart from 377 posts, and 6,269 live competitor ads reduced to ten angle shapes — plus the library that indexes both. *Team-only:* the library build reads our private workspace; the page is for everyone. | [`tools/my-feeds/`](tools/my-feeds/) · [the page](https://daemn.co/swipes/) |
| **Video teardown** | Any video in, your brief out. Written for someone who has never done this. | [`tools/video-teardown/`](tools/video-teardown/) |

### Write and make

| Tool | What it is | Read it |
|---|---|---|
| **Copywriter** | The copy: primary text, captions, headlines, from a source and a brief. | [`tools/copywriter/`](tools/copywriter/) |
| **Language layer** | Every word the tools use comes from what the market said; this is the query over a brand's customer language, with the receipt on every row. | [`tools/language-layer/`](tools/language-layer/) |
| **Video production** | An AI video brief in; the voice, the stills and the clips out. | [`tools/video-production/`](tools/video-production/) |
| **Image production** | Brief to finished static ad — the twin of video production. | [`tools/image-production/`](tools/image-production/) |

### Edit and hand off

| Tool | What it is | Read it |
|---|---|---|
| **Video edit** | An approved kit — voice, clips, music, sound — becomes the finished, captioned video, with two stops for review: the timeline, then the captions. | [`tools/video-edit/`](tools/video-edit/) |
| **Asset index** | A folder of footage becomes records you can search by what is in each clip. | [`tools/asset-index/`](tools/asset-index/) |
| **Editor onboarding** | The front door for creative marketers: the walkthrough, the SOP, the prompts they paste into Higgsfield, and the brief queue. *Team-only:* the queue reads our private workspace; the page, SOP and prompts are for everyone. | [`tools/editor-onboarding/`](tools/editor-onboarding/) · [the page](https://daemn.co/onboarding.html) |

### The shared parts

The tools import these. You do not run them yourself, but nothing runs without
them: the chain runner, the element system, the marketing doctrine, the run
layout, the name maps, the research gatherer and the quality checks.
[`components/`](components/)

Tools retired from the public kit are kept, unchanged, in
[`archive/`](archive/).

**Do the brand folder first.** Nothing else works well on an empty one — the
tools are built to say *"I don't know this"* rather than invent an answer, so
an empty file shows up as a question instead of a fake.

Then read
[`tools/video-teardown/HOW-TO-RUN-IT.md`](tools/video-teardown/HOW-TO-RUN-IT.md)
— the whole process in seven numbered steps.

---

## What you need

1. **Higgsfield Supercomputer** with this repo cloned into it — where the
   video gets watched, the chain runs and your scenes get made
   ([higgsfield.ai](https://higgsfield.ai?fpr=damon61)). **Claude Code** with
   the repo cloned works the same way.
2. **Google Drive** — where your hand-off folder lives: you read
   `handoff.md` there and put finished work in its `returned/` folder.
   `tools/editor-onboarding`.

In Higgsfield nothing gets installed and nothing runs on your computer. In
Claude Code the repo sits on your machine and the tools run there.

The exact models and settings are in
[`WHICH-MODELS.md`](tools/video-teardown/WHICH-MODELS.md) — don't leave it
on Auto.

---

## The two rules

**Copy the structure, not the content.** The shape is what earned the views;
the product is what changes. A scalp treatment and a countertop demo can be
the same format — that's the whole point.

**Nothing invented.** If the brand folder doesn't say what the product looks
like or how the customer talks, the tools say they don't know rather than
guessing. That's them working correctly. Get that part added to the brand
folder first.

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
