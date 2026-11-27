# Customer Avatar Framework v2 - Structure Map
### What every field, category, and rule is, and where it lives.

This file holds the METHOD: what an avatar is, the 6 categories, the checkers, the
non-negotiable rules, and the stage counts. `references/cell-map.md` holds the exact workbook
COORDINATES. Read this to decide what belongs where, read the cell map before touching a cell.

---

## 1. WHAT THIS PRODUCES, AND WHY THE METHOD MATTERS

An avatar is **a specific group of people most likely to buy the product**, described so
precisely that when they see the ad they think **"that's literally me."** That recognition is
what creates trust and conversion.

v2 adds two layers on top of that recognition:

1. **Brand Resonance**, the brand's reason for existing in culture. "Red Bull gives you wings."
   Example: a specific customer transformation, expressed in the customer’s own language.
   hanging off it and assuming he is already washing. This is the resonant message that
   transcends the algorithm. Everyone's ads look and sound the same, and this is why yours do not.
2. **A full human picture**: cultural relevance (their world, media diet, humor, language, how
   and when they buy) plus a **face image**, so a graphic designer or video editor can open the
   workbook and SEE this customer rather than read words in a spreadsheet. The finished doc is a
   handoff artifact for ANY asset: videos, statics, emails, landing pages, quizzes.

**The boundary, from the owner's notes.** This doc defines WHO the customer is and WHY the brand
resonates. Specific channel and format requirements belong to the execution layer. Do not bake
them into the avatar.

---

## 2. THE 6 CATEGORIES, IN THIS ORDER

| # | Category | What it holds | Phrasing |
|---|---|---|---|
| 1 | **Desire** | What they want | Always "I want ___ / I need ___" |
| 2 | **Experiences** | Situations they are in (situational) and products they tried plus the outcome | Fact only, emotion stripped out |
| 3 | **Emotions** | How they feel, and *why* | Name the emotion, mark Primary or Secondary, then the trigger |
| 4 | **Behaviors and habits** | What they now do, and how often | Always "So now I ___", with a frequency |
| 5 | **Cultural relevance** | Lifestyle, media diet, creators and sports followed, cultural moments, their slang, humor style, how they buy, when they buy, and the identity they want ("a new man") | Verbatim from comments, reviews, tickets |
| 6 | **Demographics** | Static traits | LAST, and only the ones that add relatability |

**Core Avatar:** built on ONE seed category, almost always a Desire.
**Sub-Avatar:** the same core person plus ONE narrowing element. Its payoff is the **relatable
angle**, the "that's exactly me" call-out line.

---

## 3. CATEGORY CHECKERS (use when unsure where something goes)

| Category | Checker |
|---|---|
| Desire | Sayable as "I want X / I need Y"? If not, it is not a desire. |
| Experience | A circumstance or event, with the emotion stripped out. |
| Emotion | A feeling in response to something. Not one of the primary 6 (fear, anger, joy, sadness, surprise, disgust) means Secondary, so dig into WHY. |
| Behavior | What they DO, and how often. More often means stronger. |
| Cultural | Their world: what they watch, reference, laugh at, and how and when they spend. |
| Demographic | A static, factual trait. |

---

## 4. THE NON-NEGOTIABLE RULES

- **Brand Resonance is filled before any avatar.** Every avatar and asset assumes it.
- **Angles come from comments, not brainstorms.** "New Man" came from reading ad comments. Mine
  comments for top-of-funnel angles, then work backwards: angle, positioning, structure,
  framework and format.
- **Always start avatars with a Desire.** Never seed with a demographic.
- **Fill top to bottom. Demographics go last**, and only where they sharpen the picture.
- **Never combine more than one Desire.** One narrowing category per sub-avatar.
- **Cultural relevance must be real, not invented.** Pull language verbatim from comments,
  reviews, and support tickets. Name actual platforms, creators, and cultural moments. The
  NBA-to-skincare emails outperformed all sales-style emails because the reference was real to
  the reader. Generic "likes sports" adds nothing.
- **Broader avatars need a stronger product, offer, and brand.** More specific converts with
  weaker marketing.

---

## 5. REVENUE STAGE SETS AVATAR COUNT

| Stage | Revenue | Avatar count |
|---|---|---|
| Stage 1 | $0 to 100K/mo | ONE desire-based core plus sub-avatars. Not working in 2 to 4 weeks means switch the desire. |
| Stage 2 | $100K to 1M | One core, slightly broader. Above roughly $500K, add cores (2 to 3). |
| Stage 3 | $1M to 10M | 3 to 10 cores. |
| Stage 4 | $10M+ | Everything, plus volume. |

If the stage is unknown, assume Stage 1.

---

## 6. THE WORKBOOK

One workbook equals one brand, named `<Brand>-Avatar.xlsx`, stored beside that brand's calendar
and hub workbooks.

Tabs: `Instructions`, `Brand Resonance`, `Core Avatar`, `Sub-Avatar TEMPLATE`,
`Sub-Avatar 1/2/3`, reference tabs (`Emotions Bank`, `Demographics`, `Rules & Stages`), and
`Resources`.

Labels in column A, **answers in column B**, hints in column C. **Never overwrite column C.**

Exact coordinates, the JSON key lists, and the reference pick-lists are in
**`references/cell-map.md`**. Read it before touching any workbook.

Pristine master: `assets/Avatar-Template-MASTER.xlsx`. Never edit it.

---

## 7. THE SCRIPT

`scripts/avatar_sheet.py`. All reads and writes go through it. Requires `openpyxl`, plus Pillow
for `embed-image`.

```bash
python scripts/avatar_sheet.py new <dest.xlsx>
python scripts/avatar_sheet.py read <file.xlsx>
python scripts/avatar_sheet.py fill-brand <file.xlsx> <brand.json>
python scripts/avatar_sheet.py fill-core <file.xlsx> <core.json>
python scripts/avatar_sheet.py add-sub <file.xlsx> <sub.json>
python scripts/avatar_sheet.py embed-image <file.xlsx> "<sheet name>" <image.png>
python scripts/avatar_sheet.py add-resource <file.xlsx> <resource.json>
```

`add-sub` fills the next open Sub-Avatar tab AND writes the index row on the Core Avatar tab, so
never write that index row by hand.

---

## 8. EXTENDING THE FRAMEWORK

This framework is expected to grow: more data points, direct customer survey questions, new
insight fields. When fields are added to the master template, update `references/cell-map.md`
and `scripts/avatar_sheet.py` to match.

The spine that survives any schema change: brand resonance before avatars, angles from comments,
desire-first ordering, one narrowing element per sub-avatar, and cultural relevance that is real
rather than invented.
