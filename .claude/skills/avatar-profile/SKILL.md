---
name: avatar-profile
description: Create, check, audit or clean up profiles. Build or refresh the full profile of one person a brand sells to (avatar, sub-avatar, demographic) from real customer lines and outside research on Reddit, YouTube and TikTok, so every ad, email and page is made from it. Use whenever someone says "build the profile for <avatar>", "fill the avatar profile", "profile <sub-avatar> for <brand>", "create a profile", "is this profile built properly", "check the profile", "audit the profiles", "clean up the profiles", "fill every profile the same way", "which tools still use avatar flags", "run the avatar profiles for <brand>", "enrich our avatars", "research this person", "refresh the profiles", "which profiles are out of date", "what do we know about <person>", or names an avatar, a sub-avatar and a demographic.
---

# Avatar profile

> **Activates component:** `components/profiles` (the standard, `check`, `audit`, the one door) — builds through `components/creative-strategist` `machine/who.py` (build, profile, fill, index, refresh), with `components/research-gatherer` (`gather.py person`) for the outside research.

External dependencies: `components/profiles/` (SPEC.md, profiles.py), `components/naming/people.py` (names), `components/marketing-doctrine/slices/` (definitions), `components/apify/` (the scrapers), `brands/<brand>/core-avatars/` (read only), `runs/research/<brand>/` (what was pulled).

A person is an avatar (a whole person led by one desire) plus a sub-avatar (one thing), stored ONCE in the brand: `brands/<brand>/core-avatars/<avatar>/sub-avatars/<card>/profile.json`, beside that sub-avatar's own words. A look (the demographic) is joined to the person for each piece: `who.py full ... --demographic <d>`. The joined profile is saved with the piece (`profile.json`, `profile.md`) and travels with its brief to the editor and designer. Names: `components/naming/PEOPLE.md`.

## Make a profile properly (every time, in this order)

0. **Should it exist?** Read `components/profiles/CREATE.md`. State the one factor and the swap (gate 1). It is never a product, moment, format, angle or a demographic alone.
1. **Name** (`people.py check avatar|sub|demographic <name>`). A new name is the owner's to sign; stop there until they have.
2. **Build** with the one step below (card from the lines on file, price shown first).
3. **Fill the slots**: `who.py fill --brand <b> --avatar <a> --sub <s>` (the deep desires, roles, beliefs, experiences, behaviors, emotions, the four doubts, awareness, stage).
4. **Gate and check**: `python3 components/profiles/profiles.py gate --brand <b> --profile <name>` (evidence ≥ 25 own lines; no more than half its lines under any one sibling; a HOLD goes to the owner, never fixed by hand), then `python3 components/profiles/profiles.py check --brand <b> --profile <name>`. A FAIL is fixed before anyone sees it (`SPEC.md`). Notes (open or thin parts, unsigned slots) are shown, never hidden. Levels may be lower; structure may not.
5. **Show the page**, then file on the owner's yes (below).
6. **Audit** any time: `python3 components/profiles/profiles.py audit --brand <b>`; and `profiles.py doors` lists tools still taking a person around the door.

A tool names a person with `--profile` and no other way. Nothing is written or edited by hand.

## One step

```
python3 components/creative-strategist/machine/who.py build --brand <brand> --avatar <avatar> [--sub <sub>]
```

No `--sub` builds every sub-avatar of that avatar. It writes the person from the lines on file, names what is missing, writes the searches and prints the price. **It spends nothing.** Show the person asking: how many lines are the person's own, the open questions, the searches, the price per person and in total.

Only on the owner's yes to that price:

```
python3 components/creative-strategist/machine/who.py build --brand <brand> --avatar <avatar> --sub <sub> --cap <dollars> --go "<the owner's words>"
```

It pulls Reddit, YouTube and TikTok (the platforms stop it at the cap), files every line with its link, and writes the person again.

## Filing it in the brand folder

A build writes a draft under `runs/creative-strategist/<brand>/profiles/`. Show the owner the page. On their yes, and only then, copy the draft's `.json` to the home above, put the person's new lines (`his` in the research rows) in that folder's `language/`, remove the draft, and run `who.py index`. A tool never writes the brand folder.

## Keeping them current

- `who.py index --brand <brand>`: every profile, its own lines, open questions, cast, and whether a source has changed since it was written.
- `who.py refresh --brand <brand>`: rewrites the ones whose sources changed. Free.

## Rules

1. Never write a profile by hand or paste from the avatar. An entry with no line behind it does not exist; it is an open question.
2. Never spend without the owner's words for that price. Report what was spent from `run.json`.
3. A new sub-avatar or avatar name is the owner's. `people.py check` refuses a name that breaks the rule.
4. Read the finished page before showing it: every want, feeling and habit is about this person's one thing, in their sex, at their place on the body.

## What comes back

The draft page and data, then the filed profile in the brand folder; `index.json` lists every person and where each stands. Report: own lines before and after, open questions left, dollars spent, and the page.
