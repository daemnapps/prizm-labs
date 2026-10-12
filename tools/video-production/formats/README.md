# The format bank — AI video production

Every format the video machine runs is a row in **`bank.json`** and a
profile file beside it. A run names one (`format` in its `run.json`); a
run naming a format that is not here is refused at preflight. That is the
whole mechanism by which the bank grows on purpose: **a new format is a row
and a profile, never a code change.**

**Scope — what this bank is NOT.** These are *production* profiles: how the
machine builds a piece of a given shape. They are not the fifty organic
video structures (`swipe-organic/formats.json` — what a swiped
post's structure is), not copy styles, not image build templates, not email
design formats. Each of those is its own vocabulary; the map is
`components/naming/FORMATS.md`. Address, in the repo's own grammar:
`format:video:format-profile:<id>`.

## The bank

<!-- bank:start -->
Rendered from `bank.json` — edit that file, then `python3 formats/render_bank.py`.

| `format` (run.json) | Name | Status | What a scene contains | Proven on | Profile |
|---|---|---|---|---|---|
| `song-ad` | Song ad | draft | one lyric line, illustrated; shot length = line spacing; the product late and small | 2026-09-03 (fal) and 2026-09-04 (Higgsfield) — the calls are the provider pages; 2026-09-16 again on Higgsfield, record not in the repo; filed: runs/video-production/<brand>/<run> (2026-09-16, Higgsfield) | [`song-ad.md`](song-ad.md) |
| `single-presenter` | Single presenter | draft | one person to camera, one line, one of several locations | 2026-09-16 on Higgsfield with a demonstration beat inside it — runs/video-production/<brand>/<run> | [`single-presenter.md`](single-presenter.md) |
| `meme` | Meme | draft | one swiped meme beat — the source's decisive action kept unchanged; the caption added at the edit | 2026-09-16 on Higgsfield — record not in the repo (chat sandbox); profile drafted from the session's reports, for the owner to correct | [`meme.md`](meme.md) |
| `expert-consult` | Expert consultation | draft | one presenter takes the same problem to several experts in turn; the price of each answer is the argument, the product is the last expert | 2026-09-16 on Higgsfield — runs/video-production/<brand>/<run> | [`expert-consult.md`](expert-consult.md) |
| `demonstration` | Demonstration | draft | the product doing the work — hands, surfaces, before and after; an action is one beat | not yet run end to end | [`demonstration.md`](demonstration.md) |
| `micro-drama` | Micro-drama | draft | several characters in one continuous set — a confrontation, a turn, an offer | not yet run end to end | [`micro-drama.md`](micro-drama.md) |
| `testimonial-montage` | Testimonial montage | draft | one person, one line, one room, many times over — the accumulation is the argument | not yet run end to end | [`testimonial-montage.md`](testimonial-montage.md) |
<!-- bank:end -->

`status` is the repo's ruled set: **draft** (written; may run — the run is
the evidence) · **approved** (the owner signed it) · **deprecated** (kept for
the record; a run may not name it). Nothing is approved until it is signed.
`proven_on` is separate from status: a profile can be approved and unrun, or
run and unsigned.

## Adding a format

1. Copy `TEMPLATE.md` to `<id>.md` and fill every field. A field that does
   not apply says so — never delete it.
2. Add the row to `bank.json` as `draft` (the template carries the row
   shape). `python3 formats/render_bank.py` re-renders the table above.
3. Run it under `RUN-PROTOCOL.md`. The first run filed at
   `runs/video-production/<brand>/<label>/` goes into `proven_on`, and what
   it taught goes into the profile's *What still fails*.
4. the owner signs it, or does not.

A format is one file, always. What a run taught about a *provider* — the
call shapes, the traps — goes to `../providers/<provider>.md`, not under
the format; what it taught about the *format* goes into the profile's
*What still fails*.

## What a profile is, and is not

A profile says what a piece of this shape **contains**: the cast, the
places, the scenes and what drives their length, the sound, the beat shape,
the stations it uses, the references it depends on, which prompt sections
and ledgers carry weight, what the editor builds in post, the failure it
invites first. The template holds the fields in that order.

**A profile never carries a gate.** What has to be true before anything
generates, moves or ships is `RUN-PROTOCOL.md`, the same for every format.
A profile that adds its own gate will drift from the protocol; the gate
belongs there and the profile points at it.

**A profile never builds a character.** Building the avatar is its own
process, done once per person in `brands/<brand>/ai-cast/<name>/`
(`../building-the-cast.md`); a format *consumes* a character — its master
and its skin references — and generates nothing about her. The same cast
serves a song ad, a micro-drama and a demonstration without rework. The
moment character-building leaks into a format, every format starts
reinventing the same people.

**A profile never changes the method.** The production document, the
trained identities, the eleven-section scene prompt, the ledgers and the
QC gate are the same for every format. What changes is how many people, how
many places, who talks to whom, and how long a scene runs.

## Playbooks — the layer that DOES carry per-format settings (the owner, 2026-10-10)

the owner, 2026-10-10: *"it's about optimizing workflows for specific types of ads, as
opposed to just having a general workflow for all ads … at certain points being
more specific on the type of video requires specialized knowledge … we cannot have
AI slop."* That reverses, for one explicit layer, the old rulings above that "a
profile never carries a gate" and "never changes the method": **profiles still
don't — a PLAYBOOK does.** `playbooks/<id>.json` (readable twin `<id>.md`) sits on
top of the shared chain and carries, for one family of ad: the stage order, audio
first (song / voice / none), the picture door's quality, size and fix calls, the
clip model, resolution, seconds and clips per picture, the cast reuse policy, the
hook shape, the caption look, which gates apply or skip, the edit method, the known
failure → fix list (each with the run it came from), a cost target per ad and the
format's own "not slop" checks. Runners read it through `machine/playbook.py`
(`playbook_for(id)`, `setting(id, "stages.x.y")`); a format with no playbook gets
`playbooks/default.json`, which is today's general chain unchanged.

**Families, not one playbook per swipe** (the owner, same day: *"we first need to
identify whether or not it's similar enough to another type of format that's
already worked … so we're not doing double work"*). Every playbook has a
STRUCTURAL SIGNATURE — audio driver, speakers on screen and who they address,
settings, the product's role, pacing, capture, story shape — and a family. A new
swipe is matched first (`machine/playbook_builder.py`): close enough → it is
recorded as a **variant** of that family (only its differences and overrides);
nothing close → a new family is drafted. Every decision is logged under
`runs/playbook-learn/`. After a run, `machine/playbook_learn.py <run>` adds new
known failures automatically and applies setting changes to drafts — to an
approved playbook only when they lower cost or fix a refusal without changing
the look. Status is the ruled set: a builder-made playbook is always `draft`;
`approved` needs the owner's ruling cited in `signed`.

| playbook | family | status | variants |
|---|---|---|---|
| [`song-ad`](playbooks/song-ad.md) | sung story (animated) | approved | — |
| [`multi-speaker-scene`](playbooks/multi-speaker-scene.md) | people talking around a patient / a product | draft | expert-consult (three doctors) · tv-shopping · grandma-explainer · body-scan-recipe · public-reaction (the last two matched by the builder) |
| [`short-movie`](playbooks/short-movie.md) | animated doll short movie (wordless) | draft | micro-drama (the passport swipe, matched by the builder) |
| [`sports-interview`](playbooks/sports-interview.md) | one locked press-conference take | draft | — |
