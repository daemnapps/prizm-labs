# Avatar-Template workbook v2 — exact cell map

One workbook = one brand, named **`<Brand>-Avatar.xlsx`**, stored beside that brand's
calendar and hub workbooks. Downstream skills locate it by this name:
`marketing-calendar-system` stage 3 reads the Cultural Relevance cells from it, and every
concept brief's `avatar` field names a core defined in it. Without the convention the
workbook exists but nothing can find it, and the avatar field silently degrades into a
label somebody typed.

Labels in column A, **answers in column B**, hints in column C
(never overwrite C). Prefer `scripts/avatar_sheet.py` over manual cell writes.

Tabs: `Instructions` · `Brand Resonance` · `Core Avatar` · `Sub-Avatar TEMPLATE` ·
`Sub-Avatar 1/2/3` · `Emotions Bank` · `Demographics` · `Rules & Stages` · `Resources`

## Tab: `Brand Resonance` (fill FIRST — before any avatar)

| Cell | Field |
|------|-------|
| B5 | Reason for existing (beyond the product) — the "Red Bull gives you wings" level |
| B6 | Big branded angle / transformation promise — e.g. "Transform to a New Man" |
| B7 | Tagline expression(s) |
| B8 | Brand personality formula — the distinctive combination of tone, values and customer perspective |
| B9 | Cultural territory owned — e.g. NBA × skincare humor |
| B10 | Enemy / status quo replaced |
| B11 | Proof of resonance — which assets/angles crushed and why |
| B27 | Notes |

**Angle Hierarchy** — header row 14 (`A #` · `B Sub-angle` · `C What it assumes they already know or do` ·
`D Proof it works`), entries in **rows 15–19**. Example relationship: "Transform to a New Man"
(brand angle) → "Make Your Face Wash Actually Work" (sub-angle; assumes he's already washing).

Row 22 holds the sourcing rule (merged, read-only): angles come from reading comments; work
backwards angle → positioning → structure → framework/format; channel requirements belong to
the execution layer.

## Tab: `Core Avatar`

### BRAND
B5 Brand · B6 Product · B7 Revenue stage ("Stage 1 — $0-100K/mo" etc.) · B8 Date created · B9 Last updated

### CORE AVATAR PROFILE
B11 Avatar name/label · B12 Seed category (Desire preferred) · B13 Specificity

### 1. DESIRE
B15 Desire ("I want ___") · B16 Underlying core desire (optional; Health/Status/Control-Comfort/Sex/Belonging)

### 2. EXPERIENCES
B18 Situational experience · B19 Active or Past? · B20 Product experience (tried → outcome) · B21 Direct or Indirect?

### 3. EMOTIONS
B23 Emotion · B24 Primary or Secondary? · B25 Why / trigger

### 4. BEHAVIORS & HABITS
B27 Behavior ("So now I ___") · B28 Frequency

### 5. CULTURAL RELEVANCE (their world)
| Cell | Field |
|------|-------|
| B30 | Lifestyle / day-to-day world |
| B31 | Media diet (platforms + formats) |
| B32 | Creators / shows / sports / niches followed |
| B33 | Cultural moments & references that land |
| B34 | Cultural language / slang (their words — verbatim from comments/reviews) |
| B35 | Humor style (what makes them laugh & share) |
| B36 | How they buy |
| B37 | When they buy |
| B38 | Identity — who they want to become / be seen as |

### 6. DEMOGRAPHICS (rows 40–51, fill only what matters)
B40 Gender · B41 Age/Generation · B42 Location · B43 Income · B44 Marital status ·
B45 Employment · B46 Education · B47 Race/Ethnicity · B48 Religion · B49 Language ·
B50 Health conditions · B51 Other

### VISUAL IDENTITY
B53 Casting brief / image prompt · face image embedded anchored at **B55**
(`avatar_sheet.py embed-image <file> "Core Avatar" <img>`; rows 55–63 reserved for the image)

### SUB-AVATAR INDEX
Header row 64, columns row 65 (`A #` · `B name` · `C one-liner` · `D narrowed by` · `E tab`).
Entries in **rows 66–70**.

### NOTES
B72.

## Tabs: `Sub-Avatar 1/2/3` and `Sub-Avatar TEMPLATE`

| Cell | Field |
|------|-------|
| B5 | Sub-Avatar name / # ("1 — The Magnesium Skeptic") |
| B6 | Parent core avatar |
| B7 | Narrowed by (category added) |
| B8 | One-liner: "core avatar + [new element]" |
| B9 | Specificity |
| B11 | 1. Desire (inherited) |
| B12 | 2a. Situational experience |
| B13 | 2b. Product experience |
| B14 | 3. Emotion + why |
| B15 | 4. Behavior + frequency |
| B16 | 5. Cultural relevance (inherited + sharpened) |
| B17 | 6. Demographics (as relevant) |
| B19 | Relatable angle / hook direction |
| B21 | Casting brief / image prompt |
| — | Face image anchored at **B23** (rows 23–30 reserved) |
| B31 | Notes |

## Tab: `Resources`

Table header row 4 (`A Resource` · `B What it gives you` · `C Where to find it`), rows **5–14**.
Rows 5–10 come prefilled generically (customer language skill, customer intelligence database,
ad comment mining, winning creative breakdowns, brand/founder voice skills, retention/email
learnings) — **replace the generic "where" values with the brand's actual skills/links** when
onboarding. Rows 11–14 are open (`add-resource`).

## Reference tabs (read-only pick-lists)

**Emotions Bank** — Primary 6: fear, anger, joy, sadness, surprise, disgust. Secondary
examples: Anxious, Frustrated, Overwhelmed, Confident, Excited, Stressed, Motivated, Worried,
Disappointed, Insecure. Frequency tiers T1–T6 (Stress & Overwhelm … Competence & Capability).

**Demographics** — the full static-trait list.

**Rules & Stages** — category checkers (all 6, including Cultural), rules of thumb, stage
guidance (summarized in SKILL.md).

## Script CLI

```bash
python scripts/avatar_sheet.py new <dest.xlsx>
python scripts/avatar_sheet.py read <file.xlsx>                    # JSON incl. brand resonance + resources
python scripts/avatar_sheet.py fill-brand <file.xlsx> <brand.json>
python scripts/avatar_sheet.py fill-core <file.xlsx> <core.json>
python scripts/avatar_sheet.py add-sub <file.xlsx> <sub.json>
python scripts/avatar_sheet.py embed-image <file.xlsx> "<sheet name>" <image.png>
python scripts/avatar_sheet.py add-resource <file.xlsx> <resource.json>
```

`brand.json` keys: reason_for_existing, big_branded_angle, taglines, personality_formula,
cultural_territory, enemy, proof_of_resonance, notes, angle_hierarchy: [{num, sub_angle,
assumes, proof}].

`core.json` keys: brand, product, revenue_stage, date_created, last_updated, avatar_name,
seed_category, specificity, desire, underlying_desire, situational_experience, active_or_past,
product_experience, direct_or_indirect, emotion, primary_or_secondary, why_trigger, behavior,
frequency, lifestyle, media_diet, creators_followed, cultural_moments, cultural_language,
humor_style, how_they_buy, when_they_buy, identity, casting_brief, notes, demographics: {gender,
age, location, income, marital_status, employment, education, race_ethnicity, religion,
language, health_conditions, other}.

`sub.json` keys: name (nickname only; script prefixes the number), parent, narrowed_by,
one_liner, specificity, desire, situational_experience, product_experience, emotion_why,
behavior_frequency, cultural_relevance, demographics, relatable_angle, casting_brief, notes.

`resource.json` keys: resource, gives, where.
