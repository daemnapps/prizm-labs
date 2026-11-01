<!-- v1 (2026-10-08, the owner: "every concept … six unique versions of that same concept, same brief" · "variations of the full hook-through-lead" · "define the different sections of a video ad … mix and match" · "keep those sections that we have"). Built off to the side of the video chain (the developer is working in it); run by components/distinct-six/run.py on a finished chain run. -->

# Stage 4v · The Distinct Six

You are writing ONE concept as {N} genuinely different ads. Not {N} hooks on one ad: {N} ads.

**Why.** Meta's ad system "groups together ads that share key visual and thematic attributes. When multiple ads look or feel alike, these are seen as variations of the same creative" — they share one place in delivery. A new creative is "truly different in look, feel, storyline, and message", made for a different persona or use case (Meta, *Demystifying Creative Diversification*, 16 Dec 2025). Meta's ranking model then matches each person to the creative that fits them, and fatigue is counted by the image or video itself. So {N} versions that look alike are one ticket; {N} that differ are {N} tickets, each able to find a different woman inside the same avatar, each wearing out on its own clock.

## What stays the same in every version

- **The ad set:** avatar `{AVATAR}`, angle `{ANGLE}`. Every version is for this avatar and argues this angle.
- **The product and the offer**, word for word from the offer file. Never a new price, claim or guarantee.
- **The core message:** "{CORE}"
- **The words people say** come from the concept's own script and the language bank's register — sharpened, never invented claims.

## What changes — the five moves an ad set leaves free

Every version takes its own value for each, and any two versions differ on **at least 3** of them:

| Field | Values from |
|---|---|
| `awareness` | unaware · problem-aware · solution-aware · product-aware · most-aware |
| `format` | the format list below |
| `lead` | a `bank_id` from the cast list below, `NEW (<one-line description>)`, or `none` |
| `setting` | the settings list below |
| `style_id` | the style list below |

Also write `face` — the lead person's `gender/age-band/ethnic-appearance` (e.g. `female/55-64/white`), or `none`. The machine compares faces this way.

**And stay clear of what's already running.** These cells are crowded in the live library — a version should not land on them: {CROWDED}
These are open — prefer them: {OPEN}

## The sections

Every version is a full ad from the first frame to the last, built beat by beat from the doctrine's own sections — the same ids the swipe's section map uses:

{SECTIONS}

- The **opening sections are new in every version** (the hook and whatever carries the first seconds) — that is where most of the difference lives.
- The concept's own proof and mechanism come back, re-staged for this version's place, person and look. Pick the sections the awareness level needs: an unaware version earns the problem before the product; a most-aware version goes almost straight to the offer.
- The `offer` and `call-to-action` keep the offer file's words; only how they are staged changes.
- Give each beat its length in seconds. A Reel version runs 20–60 seconds unless the format says otherwise.

## The concept

**The script so far (the close stage, full script):**
{SCRIPT}

**The swipe's section map (where each section sits in the winning ad):**
{SECTION_MAP}

**The hooks already written for this concept** (lines to reuse or re-fit; each version may keep up to two as its own iteration tests):
{HOOKS}

**The culture read:**
{CULTURE}

## The lists

**Formats:** {FORMATS}

**Styles:** {STYLES}

**Settings:** {SETTINGS}

**Cast (bank_id — who):**
{CAST}

## Return JSON only

```json
{"versions": [
  {"title": "⟨three or four words, what this version is⟩",
   "why_different": "⟨one sentence: who inside the avatar this one finds, and why it is not the others⟩",
   "piece": {"avatar": "{AVATAR}", "sub": "⟨sub-avatar id or none⟩", "angle": "{ANGLE}",
             "awareness": "⟨…⟩", "format": "⟨…⟩", "lead": "⟨…⟩", "face": "⟨gender/age-band/ethnic-appearance or none⟩",
             "setting": "⟨…⟩", "style_id": "⟨…⟩"},
   "beats": [
     {"section": "⟨one id from the sections list⟩", "seconds": 4,
      "says": "⟨the spoken line or on-screen words, verbatim⟩", "shows": "⟨what the frame shows, one line⟩"}
   ],
   "hooks": ["⟨up to two alternate first lines for this version — iteration only⟩"]}
]}
```

Exactly {N} versions.
