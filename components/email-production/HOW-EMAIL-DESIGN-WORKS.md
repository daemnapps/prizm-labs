# How an email is made and designed

Written 2026-10-26 from a read of `tools/email-production`, `components/marketing-calendar` and the brand files. `<brand>` is <brand> or <brand>. Nothing here was run against Klaviyo.

## 1. The stages, in order

| Stage | Component or skill | What happens | Lands in |
|---|---|---|---|
| Plan | marketing-calendar | The month's slots: date, audience, email type, product, offer, occasion. Layer 9 also sets the design: letter or design, and the format. | runs/marketing-calendar/<brand>/<YYYY-MM>/slots.json |
| Write | email-production (stages 0 to 9) | Triage, read, spec, context, live read, injection, placement, subject lines and preview, expansion (organic only), close, build the blocks, facts check, brief. | runs/email-production/<brand>/<label>/stage0 … stage9 files, then deliverable/email.json |
| Design | email-design (design/ line) | Job card, section layout, pictures, prices and words, then the Klaviyo build and the final check. | runs/email-production/<brand>/<label>/design/ and klaviyo/ |
| Review | email-review | A person looks and asks for changes. Each change edits design/email.json. | the same run folder |
| Check | stage-check | Is it done? Copy, built email, delivery check, brief number. | runs/stage-check/<brand>/ |
| Upload | email-upload | Checks the email, makes a Klaviyo draft and its approval card. Never sends. | klaviyo-status.json, email-card.json, the draft in Klaviyo |
| Approve | (a person) | Approves and schedules the draft. No component sends. | Klaviyo |

## 2. How one email gets its design

1. **The calendar writes the slot.** type, segments, product, offer, occasion. `components/marketing-calendar/machine/calendar.py → slots.json`
2. **The type decides: letter or design, and which format.** only the email type decides. Occasion and avatar do not. `components/marketing-calendar/machine/kinds.py, components/marketing-calendar/definitions/email-kinds.json, tools/email-production/formats.json`
3. **The copy is written first.** 13 stages, using the offer bank, language bank, objection bank and product file. `tools/email-production/email_line.py, prompts/stage*`
4. **Moment research and the concept.** what is happening in the culture this week for this avatar. `prompts/design0-moment, brands/<brand>/core-avatars/<avatar>/culture-map.md`
5. **The job card.** what this email must do. `prompts/design1-jobcard → design/job.json`
6. **The layout.** the model picks 8 to 11 sections from the engine's list, in the brand's look. `design/line.py, prompts/design2-layout, brands/<brand>/email-sms/design-system.json → design/email.json`
7. **Checks and gaps.** promises check, missing prices and words filled from the offer bank. `design/promises.py, design/gaps.py`
8. **Pictures.** real product first, then real proof or a brand photo, and only then a made picture. `design/line.py --pictures, tools/image-production (email-hero, email-offer and others)`
9. **The Klaviyo build.** sections cut into pictures and live text, tracked links, the approval card. `design/build.py, design/engine.py → klaviyo/`
10. **Final check.** last check before a person sees it. `design/check.py → klaviyo/card.json`

## 3. Which email type gets which design

Only the email type decides. Occasion changes the look through a theme, never the format.

| Email types | Kind | Format |
|---|---|---|
| sale-window, last-chance, early-access, gift-guide | design | offer-urgency |
| launch, anticipation | design | launch-window |
| restock, availability | design | winback |
| bundle, stack, routine, mistake-audit | design | system-education |
| myth-correction, switch, objection-shot, guarantee | design | objection-crusher |
| opinion, milestone | design | brand-manifesto |
| spotlight, someone-like-you, proof-drop, room-answered, peer-advice | design | proof-grid |
| product-spotlight, mechanism, moment, holiday, ritual, subculture, regional, trend, problem-explainer, seasonal-skin, pharmacist-dad, roll-call, behind-the-scenes, subscription-invite, channel-invite, product-finder, affiliate-roundup | design | hero-product (the fallback for any designed type with no stack) |
| content-request, mission, founder-note, what-went-wrong, sunset, reader-question, affiliate-feature | letter | simple (plain letter) |

The rule is `decide()` in `components/marketing-calendar/machine/kinds.py`. A person's call on the calendar board is never overwritten.

## 4. The sections

- **The engine's sections (current).** About 35 section types in tools/email-production/design/engine.py (band, hero, headline, letter, quote, specs, tiles, offer, guarantee, cta, ticker, foot and more). The model is shown a guide of them and may use only those.
- **The 17 older names.** tools/email-production/SECTIONS.md and formats.json. Older design path. Only the calendar's format label still reads formats.json.
- **The 15-section human library.** tools/email-production/EMAIL-DESIGN.md. A table of each section's job, picture source and word limit. For people, not read by the engine.

## 5. Who changes what

| To change | Edit |
|---|---|
| Which types are plain letters | components/marketing-calendar/definitions/email-kinds.json (a brand's own exceptions: brands/<brand>/email-sms/email-kinds.json) |
| Which format a type gets | tools/email-production/formats.json |
| A brand's look (colours, fonts, logo, themes) | brands/<brand>/email-sms/design-system.json and design-formats/visual-dna.md |
| A prompt | add a new -vN- file in tools/email-production/prompts/. The highest number wins. Never edit an old one. |
| A new section type | engine code: an s_ function in design/engine.py and a line in the guide in design/line.py. Not a data edit. |
| Never by hand | run outputs, slots.json, learnings, the html and md mirrors scripts rebuild, made pictures, kind_set_by on a slot |

## 6. Where stages step on each other

| What happens | Why it matters | Where |
|---|---|---|
| Re-running design overwrites design/email.json and job.json | A person's edits from review are lost. A copy re-run followed by a design re-run loses them again. | `design/line.py:409` |
| Re-running copy overwrites every stage file | Without --rerun-from, every stage is rewritten and run.json is rebuilt. | `email_line.py:312, 825` |
| The simple layout rebuilds deliverable/email.json every run | A hand edit there is lost. Edit stage8 instead. | `simple_email.py:705` |
| The Klaviyo build empties klaviyo/assets/ | It keeps the approval fields on card.json. | `design/build.py:344` |
| Two Klaviyo paths | The simple layout's push and the design card both make a draft, so one slot can end with two different drafts, through two approve pages. | `simple_email.py push; approve_klaviyo.py` |
| One shared run.json | email_line, simple_email and design all write it. | `run.json` |

## 7. Proposed split (parked until after Q4: see SPLIT-PLAN-AFTER-Q4.md)

- Keep one component. The state is one run folder, and splitting the component would cut run.json and the stage files apart.
- Give each group its own entry point, folder and skill. Plan, review, check and approve are already clean. Design already has its own line. Upload is already one command.
- Needs code, not yet done: a copy-only entry point (`write_copy.py` with `--only-stage`); `run_month.py --stages plan,write,design,check,upload` so it stops chaining silently; design refusing to overwrite `design/email.json` when a person has edited it; and retiring the older simple-layout push so there is one Klaviyo path.

## 8. Hard to explain today

- Three section lists exist and do not match. The format name is only a label the model sees: nothing in data fixes which sections an email gets.
- Some engine sections are never shown to the model (hero_blink, hero_overlay, photo_row, callout, timeline, link).
- Rules like '8 to 11 sections', 'ends on foot' and 'a letter needs a letter block' live in the prompt and the validator, not in a data file.
- EMAIL-FORMATS.md still says the section renderer is 'not built yet'. The design line is the current process. Treat that doc as stale.
- <brand> has no design_rules in its design-system.json, so almost none reach the prompt for that brand.
