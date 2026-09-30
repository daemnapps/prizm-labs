# Creator profile spec — the avatar workflow, run on a real person

**AGNOSTIC ON EVERY AXIS** (Damon's standing rule): brand, product,
avatar, creator, gender. Nothing in this template assumes who the
creator is — a profile speaks about the actual person in the actual
person's pronouns, taken from their own bio/content, never assumed.

Damon's ruling (2026-08-30): a retained creator gets the SAME
distillation as an avatar — we already tore down their posts; we should
know who this person actually is. Built on the customer-avatar-framework
(v2): desire-first, six categories, demographics LAST, language pulled
VERBATIM from the creator's own posts, nothing invented, unknowns marked
OPEN.

Sources per creator (in authority order): their teardown runs
(the teardown machine's records — brief.md + stage outputs, esp. the
stage-1 psychology/audience reads) · their record (creator.md, posts.md,
copy/*.md) · the live page only to confirm what records claim.

## The template (profile.md, exactly these sections)

```
# <Real first + last name if findable — else handle> — creator profile

<one line: who this person actually is, in plain words>

## Basics
- Real name: <from bio/watermarks/post copy — else OPEN>
- Pronouns/presentation: <as their own content states it>
- Handle · page · platform · followers (dated)
- Teardowns on record: <n> (ids)

## Who they are (the avatar distillation — observed, verbatim-sourced)
- Desire: what they want, "I want ___" — as their content states it
- Experiences: what they've lived/tried (procedures, products, outcomes)
- Emotions: how they feel and WHY (secondary emotions need the why)
- Behaviors: what they DO in their LIFE and in the life their content
  shows — "So now I ___" + how often. Their rituals, what they use,
  what they do about the problem this brand solves, what they buy, how
  they spend their days. NOT posting mechanics — how they film/edit/
  post belongs in "The content machine", never here.
- Cultural relevance: their world — what they reference, their humor,
  their slang QUOTED from posts, how their audience talks back
- Demographics: last, only what sharpens (age band, region if visible)

## The content machine (the creator layer)
- Formats they run + which ones outperform (from post scores)
- Their delivery: pace, register, on-camera habits
- What their audience is FOR — which of this brand's avatars the
  following maps to

## Avatar fit
- Core / sub-avatar they embody or attract — THIS BRAND'S avatar names
  come from the brand's core-avatars folder, never hardcoded — + why,
  sourced

## On camera (for briefs and the AI twin)
- What they look like, recurring settings, wardrobe register — specific
  enough to cast their twin

## Links
- ALL links CLICKABLE — relative markdown links from the profile's
  location, never bare paths. Records folder + one link per run brief.
```

## Rules

- The profile's pronouns are the CREATOR'S, from their own content;
  the machinery never assumes a gender.
- Verbatim beats paraphrase; every claim traceable to a post/run;
  invented color = defect.
- No terms/rates/status — operational, churns; the roster owns it.
- Everything clickable: a reference that can't be clicked is a defect.
- Refresh is the teardown machine's stage 8: the brand declares spec +
  home in `brands/<brand>/content-creators/profile-home.json`; the
  spec wins over the prompt.
