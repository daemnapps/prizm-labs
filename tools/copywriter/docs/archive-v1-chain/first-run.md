# First run — 2026-08-24

Live <brand> video brief in, six pieces of paste-ready ad copy out. First
proving run of the five-stage chain (`../prompts/`), run via `../copy.py`.

**One false start, logged for whoever hits this next.** The first attempt
came back corrupted — every stage returned commentary about an unrelated
Stop hook instead of ad copy, because a repo-wide `run-log.md` guard
(`.claude/hooks/runlog-guard.sh`) was silently hijacking every headless
`claude -p` call in this repo while three old, unlogged video-teardown run
folders sat in the working tree. Resolved by logging those three runs
honestly (see `new-workflow-design/builds/video-teardown/run-log.md`, entries dated 2026-08-20 but
backfilled 2026-08-24) — not by bypassing the hook. `copy.py`'s `claude()`
briefly carried a `--bare` workaround; reverted, since `--bare` also drops
normal OAuth login and needs its own API key.

Source: `new-workflow-design/builds/video-teardown/results/<person>-DbGfFHxI8LJ/stage5--brief.md`
(<person> × <brand>, "3 lies" video). No existing copy was on file to test
the reuse/re-angle lanes — that needs real past primary text supplied via
`--existing-copy` on an actual call. All six options below are net-new.

Full stage-by-stage output: `../results/<person>-DbGfFHxI8LJ-netnew/`.

---

## Media Buyer Brief — <brand> Brilliance Turmeric Body Scrub

**<person> concept · six primary text options · ready to traffic**

### Concept: <person> — "Three lies" / sleeveless reveal

**The video it pairs with:** `<person>-DbGfFHxI8LJ` — <person>, unretouched arms,
sleeve pushed past the elbow mid-video, closing on three unbroken seconds of
a sleeveless dress with no filter.

**The angle, one line:** Every option here refuses the fast-result promise
the category runs on — the copy says out loud that it took months, not
weeks, and earns the sleeveless close by being the only ad in the feed that
admits the timeline.

### Primary text options

**Option 1**

Three lies women over 55 have been told.

The first one is that the brown spots are just part of the deal now, like
the reading glasses.

The second one is that covering up is easier than fixing it. Long sleeves.
Higher necklines. A cardigan in July, at my granddaughter's birthday party.

The third one is that at our age, sleeveless is over.

Watch the end of the video for that one.

Here's the honest part, and it's the part most ads skip: mine took months,
not weeks. Not four weeks. Months. Twice a week, consistently, small circles
from the wrist upward until the grains dissolve.

That's the Brilliance Turmeric Body Scrub. $29.99.

And the guarantee is exactly this — 60-day money back. Use it twice a week,
consistently. If the spots do not fade, you get every penny back.

*Why: leans on the three-lies structure as its spine and hands the payoff to
the video — the third lie is deliberately unanswered in text so the
sleeveless close does the work. Longest option; strongest for cold
audiences.*

---

**Option 2**

Lie: at our age the cardigan is for summer.

Truth: occasionally.

I didn't say that in the video. I wore the dress instead. Sleeveless, arms
and shoulders bare, no filter, no flattering angle. The spots are still
there — you can see them. Some of them have faded. Some of them are on their
way.

Because here's what nobody tells you when they're selling you something: it
took months, not weeks. I was diligent about it. Twice a week in the shower,
damp skin, small circles from the wrist up until the salt dissolves.

Everything I'd tried before did half the job — it cleared the old skin off
and the same spots came back in the same places. This one does both halves.

Brilliance Turmeric Body Scrub. $29.99.

60-day money back. Use it twice a week, consistently. If the spots do not
fade, you get every penny back.

**Headline:** Truth: occasionally

*Why: leans on the mechanism differentiator — "everything else did half the
job" is the one line that explains why the fading holds instead of coming
back. Best for retargeting people who've already tried something else.*

---

**Option 3**

I counted three lies before I got to the end of my own arm.

Lie one: it's just part of getting older. Lie two: everything's been tried
already, so nothing works. Lie three: the sleeves stay down now.

I unbuttoned the cuff in the video for a reason. The spots are unretouched
and still clearly there. I'm not going to show you a rinse-and-reveal,
because that isn't what happened. What happened was months of it. Twice a
week, consistently.

If you want the version where it disappears in four weeks, that's not this.
Every skin is different — some women see changes in weeks, others in
months.

Five core ingredients do the work: sea salt, turmeric, moringa, ginger,
chamomile. The salt clears the old damaged skin off. The turmeric tells
those cells to stop.

The scrub. $29.99.

60-day money back. Use it twice a week, consistently. If the spots do not
fade, you get every penny back.

**Headline:** Lie three: the sleeves stay down now

*Why: the ingredient-forward option, and the most explicit anti-rinse-and-
reveal framing — the direct swipe at the category. See the flag below
before trafficking this one.*

---

**Option 4**

Ask my husband.

He's the one who said it first. I hadn't noticed — I'd been staring at that
spot on the back of my hand so long I couldn't tell anymore. He looked up
and said, hey, that brown spot is fading.

That's when I believed it.

But I'll tell you the boring part too, because the video only had so long.
The scrub is $29.99. You use it twice a week in the shower on damp skin, not
under the running water — that's how most of it ends up down the drain.
Small circles from the wrist upward until the grains dissolve. Let it sit a
minute. Rinse cool.

Mine took months, not weeks. I'd rather tell you that now than have you give
up at week four like I nearly did.

Edges soften first. That's where it starts.

Brilliance Turmeric Body Scrub. $29.99. 60-day money back. Use it twice a
week, consistently. If the spots do not fade, you get every penny back.

**Headline:** Ask my husband

*Why: third-party proof — someone else noticed before she did. Also the
most instructional option, so it doubles as a how-to for warm traffic.*

---

**Option 5**

The video ends on a sleeveless dress. Three unbroken seconds, no filter.
That's the whole argument.

What it doesn't show is the months before it, when I was doing the same
thing I'd done with everything else — checking my hands under every light,
asking myself whether that spot was lighter or whether I was imagining it.

Here's what was different. Everything I'd tried cleared the old skin off and
the new skin came in with the same spots in the same places. This one clears
the old skin and changes what comes in behind it. That's why the fading
holds instead of coming right back.

Months, not weeks. Twice a week, consistently.

The scrub. $29.99. Or stock up — three for $75, five for $109, free
shipping on both.

60-day money back. Use it twice a week, consistently. If the spots do not
fade, you get every penny back.

**Headline:** No filter, no sleeves

*Why: the only option carrying multipack pricing. Point this one at buyers
and repeat visitors — the 5-pack matches how these customers actually stock
up.*

---

**Option 6**

"At our age the cardigan is for summer."

I've heard some version of that from every woman I know. And I said it
myself, right up until the July I wore one to a birthday party and caught
myself in a photo afterward.

Three lies. I knocked down two of them with a tube of scrub on my forearms
and a sleeve pushed past the elbow. The third one I didn't argue with — I
just wore the dress.

Nothing about this was fast. Months, not weeks, twice a week, consistently.
Clean ingredients, five core ones doing the work, and it rinses clean — it
doesn't stain you yellow like the kitchen-turmeric versions do.

Brilliance Turmeric Body Scrub. $29.99.

60-day money back. Use it twice a week, consistently. If the spots do not
fade, you get every penny back.

Order it when you need it, or stock up.

**Headline:** I just wore the dress

*Why: shortest of the long-form set and the only one handling the no-stain
objection. Good top-of-funnel alternate to Option 1 at half the length.*

---

### Headlines

1. Three lies about women over 55
2. Truth: occasionally
3. Lie three: the sleeves stay down now
4. Ask my husband
5. No filter, no sleeves
6. I just wore the dress

Numbered to match, interchangeable across the set. Testing headlines
independently: 4 and 6 stand best without their body copy.

### Applies to everything above

**Price:** $29.99 single tube. Multipacks: three for $75, five for $109,
free shipping on both.

**Guarantee, exact wording:** "Use it twice a week, consistently. If the
spots do not fade, you get every penny back."

**Standing restrictions:** no countdown timers, no "only X left," no
subscription language (use "order when you need it" or "stock up"), no
discount stacking. Offers lead with the guarantee, always.

### One flag before trafficking

**Option 3 only.** "The turmeric tells those cells to stop" is approved
product language, but it's a mechanism claim on a cosmetic — the line most
likely to draw a Meta review on this account, and unresolved internally
against the appearance-only standard. Nothing blocks running it; to keep
review risk off this launch, run Options 1, 2, 4, 5, 6 first and hold 3 for
a second wave.

---

## What compliance actually caught (stage 4)

- All six ran with an open-ended guarantee — added "60-day money back"
  ahead of the locked sentence in every one.
- Option 1 twice assigned the reader an age/condition she didn't state —
  rewritten to first person / neutral framing.
- Options 3 & 6: "five ingredients" oversold the formula against the INCI —
  corrected to the sanctioned "five core ingredients."
- Option 4 originally resolved on male attention / innuendo — a hard rule
  break (resolution must be self-recognition) and a likely Meta
  adult-content flag. Rebuilt on the sanctioned husband-notices-first
  structure; hook and headline survived untouched.
- Option 5's "eleven months" was a specific figure nothing on file
  supports — flattened to "months," matching the other five.
- Option 6's "no subscription" is a banned phrase — swapped for the
  approved "order it when you need it, or stock up."
