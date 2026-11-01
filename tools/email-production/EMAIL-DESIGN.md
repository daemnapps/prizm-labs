# How we design emails

Markdown copy of the **How We Design Emails** page (artifact link in
`tools/email-production/context/artifacts.md`). What we actually did for
the <brand> designed emails on 9–10 Oct 2026, written down so the design step can
run inside the chain every week (the owner, 17 Oct 2026). The process itself is
`EMAIL-LINE.md`; this file is the record of how it ran and what it needs to run
on its own.

Where it sits: **Calendar → Copy → Design (6 steps) → Approval page → Klaviyo draft → a person schedules.**

> "Think about this like we are actually designing many landing pages." — the owner, 9 Oct 2026

## The line: six steps, in order

A step starts only when the one before it has its OK.

| Step | What it makes | Checked by | Ran last week by |
|---|---|---|---|
| 1 Think | A job card per email: who reads it, its one job, the one belief, what proves it, the one action, how we'll know, what was cut and why, the product facts | the owner, with step 2 | `runs/email-production/<brand>/week-2026-10-12/layouts.py`, `halloween_layouts.py` |
| 1b Concept | One concept per email from the reader's culture map (a borrowed format, never a person); `concept` + `culture` on the card; a season gets its own colours | the machine holds any email without both | `brands/<brand>/core-avatars/<avatar>/culture-map.md`; `THEMES` in `design_system.py` |
| 2 Layout | Phone-scale wireframe, first screen marked; every box says its words and its picture source (type · pull from what we own · real product cut-out · make from a real reference · ornament). No pictures | **the owner's OK** | `layouts.py` `wireframe()` |
| 3 Pictures | Real product → proof we own → made from a real reference. Every label on a made picture read; fixed by edit pass, never a re-roll | **the owner's OK** | `tools/asset-index/machine/proof.py` (535 indexed), `social_pull.py`; scenes and ornaments made on Higgsfield |
| 4 Product check | Pictures vs the real product, prices vs the offer bank, claims vs the product file and position.md's NEVER list, in-the-box vs the product file | the machine, problems shown to the owner | inside `klaviyo_build.py` cards |
| 5 Build + approve | Designed sections cut to pictures in the brand's fonts (headless Chrome); letters, buttons, GIFs, footer live; tracked links; `card.json`; final check; card on the approval page | **the owner's click** makes a DRAFT; a person schedules | `klaviyo_build.py`, `final_check.py`, `tools/email-production/approve_klaviyo.py` (localhost:8798) |

Final check (step 5): every link answers 200 · subject and preview set ·
unsubscribe and preferences tags present · alt text on every picture · no
picture over 1MB, whole email under 2.5MB · no name on the never-use list ·
product check passed · send day still ahead · across the week, no customer
photo or made scene used twice.

## Two kinds of email. Never both.

| | Design | Letter |
|---|---|---|
| For | product spotlights, offers, objections, the guarantee | VIP thank-yous, the mission, asking for his story |
| Pictures | 5 to 8 | 1 photo hero, maybe a customer quote |
| Words | no block over 30, about 90 in all | 3 or 4 short paragraphs, about 120 in all |
| Opens on | big type + product, or a photo hero | a photo hero |
| Ends on | the product card or the guarantee | one button, one ask |

## The section library

| Section | Job | Picture from | Words |
|---|---|---|---|
| Big type + product | opens a design email | real product, cut out | ≤ 7 |
| Photo hero | opens a letter or a design email | brand photo we own | ≤ 8 |
| Studio-set hero | product on the gold set, emeralds below | brand photo we own | ≤ 7 |
| Spec strip | the real numbers, four across | none | 4 numbers |
| Three tiles | how it works, one picture each | real product / photo | ≤ 10 a tile |
| Photo + card | the argument on a glass card over a photo | brand photo we own | ≤ 30 |
| Customer words | one real line, as written | none | the quote |
| Arrow list | what he tried, one line each, then the turn | none | ≤ 8 a line |
| Every side | front, side, back from the store's 360° video | real product, cut out | ≤ 4 |
| Proof grid | six real men who use it | real customer proof | ≤ 10 |
| Before and after | one real result, never made | real customer proof | ≤ 20 |
| Product card | product, one job, price, button | real product, cut out | ≤ 20 |
| Guarantee | the risk taken away, word for word | none | the guarantee |
| Letter block | short paragraphs from a person | none | ≤ 45 each |
| Button | one ask, the only sage thing in the email | none | ≤ 4 |

Format stacks and picture counts per send type: `EMAIL-FORMATS.md`, `formats.json`.

## Pictures, in this order

1. **Real product, cut out** — store 360° frames for FLEX, real packshots for bottles. Not the 3D models in emails yet.
2. **Brand photo we own** — studio lifestyle shots.
3. **Real customer proof** — before/afters, photo reviews, UGC, own social posts; as they are, never made.
4. **Made, from a real reference** — only what nothing we own shows; real product photo as the reference; every label read.

Ornaments (made on Higgsfield from crops of the brand's real studio set; on the
shared Drive at `Shared Assets/brands/<brand>/email-sms/design-formats/ornaments/`):
arch crown behind the logo · emerald rule between sections · deco fan in letters ·
gold seal on the guarantee only · gold corners on quotes · gold stage for product
cut-outs · plinth under the footer. Gold and emerald for ornaments only; the button stays sage.

## Rules that came out of the owner's reviews (9 Oct)

- A headline is followed straight away by its picture; a badge or seal is never the opener.
- One price, one offer, one button; lead with the page price, one-delivery price struck through; no invented deadlines.
- One type system: serif display only inside pictures, live text in one sans; Display 34/26/21, body 16, labels 10.5 caps.
- Slim header with the brand's real logo file.
- No customer face twice in a week (once a month at most); a customer's words only with his own face.
- Every crop shows what its label names.
- Borrow a format, never a person; a homage shows no face; the villain is the problem.
- The product behaves like itself (FLEX in a hand, base or case; the case is sold separately, never shown as in the box).
- The subject names the concept, not the product; body is two or three short lines.

## The weeks it ran on

| Send | Kind | Audience | Concept / subject |
|---|---|---|---|
| Mon 12 Oct | Letter | VIP, 5+ orders | It was never about the bumps |
| Tue 13 Oct | Design | Leads + subscribers | WAR: the sting was never proof |
| Wed 14 Oct | Letter | Loyal, 4 orders | What we're against (restock WAR) |
| Fri 16 Oct | Design | Subscribers | FLEX: reaches what your hands can't |
| Sun 18 Oct | Design | Leads | "Five blade razors… makes no difference" |
| Tue 20 Oct | Design | on its card | Retire the fitted (FLEX) |
| Thu 22 Oct | Design | on its card | Now playing: Smooth (CRUSH) |
| Sat 24 Oct | Design | Subscribers | Keep it either way (the guarantee) |
| Sun 26 Oct | Design | Returning · Engaged 180d | Night of the Bumps (WAR) |
| Thu 29 Oct | Design | on its card | Barbershop at midnight (King Set as five pictures) |
| Fri 30 Oct | Letter | Customers | What are you going as? |
| Sat 31 Oct | Design | on its card | Thriller-style street (King Set deal) |

## How it runs now, both brands (17 Oct 2026)

the owner: *"the team is going to trigger the email flows, and then the team is going to do any of the design work. I'm really
not going to be involved … the design should already be there. She just needs to … make her final refinements,
and then we're done."* And: *"every time a shift is made … with the feedback, that all needs to be stored and put
into learnings back up and through the chain … it needs to compound."*

1. **the team** approves the sends on the calendar board (localhost:8790) and presses **Write the copy**. The calendar
   already holds the main, promo and cultural sends for the avatar, each marked designed or letter.
2. **The chain** (`run_month.py`, by itself): copy → on a moment send, the moment world from sourced research →
   job card and concept → layout from the brand's look and `visual-dna.md`, every person and product from the
   tagged real-picture index first (`tools/asset-index/machine/tag.py`) → the key visual and gift pictures
   through the image engine, judged → Klaviyo build with tracking → product check and final check
   (`--no-design` stops at the copy).
3. **the team** opens the approval page (localhost:8798). Each email is already designed. Per email: **Approve** (a
   Klaviyo draft), **Redo with a note** (the note becomes a rule for every later email, and this one is redone),
   or **Send back** (the reason is recorded). Final touches in the Klaviyo draft; a person presses Schedule.
4. **The learnings** (`components/run-kit/run_kit/learnings.py`): every correction and win as a DO or NEVER,
   `runs/learnings/_all.jsonl` for every brand and every line (no brand named), `runs/learnings/<brand>.jsonl`
   for a brand's own facts. Every copy step, every design prompt and every picture the image engine makes
   (emails, ads, video frames) reads them. Seeded with 12 rules from the 17 Oct review.

Every product's physical truth (`brands/<brand>/products/<p>/product.md`) is read by every design prompt; a
brief that names a product in a form it never takes is rewritten before anything is made.

## Any brand, same line (17 Oct 2026)

the owner, 17 Oct: *"we need to ensure this process becomes agnostic because we're going to run the same
process on <brand>. And when we do the marketing calendar every 2 weeks, we can also determine which
emails become design and which ones stay less design. All mapping and context and runs need to operate
on the same principles."*

What was hand-built for the <brand> week is now one shared line; a brand changes only its look file.

| Stage | What happens | Where |
|---|---|---|
| A · Calendar | Every send gets `kind` (design / letter), `format` (section stack) and `kind_why`, at layer 9 and on a free two-week re-run. Letter types: content-request, mission, founder-note, what-went-wrong, sunset, reader-question, affiliate-feature; everything else is designed. A brand may add its own rule (`by_weekday`, `letter`, `design`). | `components/marketing-calendar/definitions/email-kinds.json`, `machine/kinds.py`, `brands/<brand>/email-sms/email-kinds.json` |
| B · Copy | The copy chain, unchanged. Design starts only on finished copy. | `email.py` / `run_month.py` |
| C · Job card + layout | Prompt 1 writes the job card and the concept from the reader's culture map; prompt 2 lays the email out as a spec (`design/email.json`). The layout is held unless every section exists, every product picture is in the brand's look, every proof id is in the proof index, and no proof repeats in the window. **the owner OKs the layouts.** | `tools/email-production/design/line.py`, `prompts/design1-jobcard-v1-damon.md`, `prompts/design2-layout-v1-damon.md` |
| D · Build | The engine renders the spec in the brand's look; `build.py` cuts it for Klaviyo (team tracking tags via `machine/email_links.py`) and writes the approval card with the product check; `check.py` runs the final check across the batch. | `design/engine.py`, `build.py`, `check.py`, `approve_klaviyo.py` |

Run it:

    python3 components/marketing-calendar/machine/kinds.py <brand> <YYYY-MM> --from <date> --days 14
    python3 tools/email-production/design/line.py <brand> <YYYY-MM> --from <date> --days 14
    python3 tools/email-production/design/build.py <run> [<run> ...]
    python3 tools/email-production/design/check.py <run> [<run> ...]

The look file, `brands/<brand>/email-sms/design-system.json`: colour tokens, the two faces and their files,
the logo, ornaments (optional), moment themes, real product pictures by name, sign-off, footer, guarantee
word for word, send hour, and the product check's prices, refused words and names. <brand>'s carries the
week of 12 Oct's values exactly; <brand>'s is built from its palette, licensed fonts and the team's email
rules (a face full width up top, card text stays live, six banned visuals, Wednesday text / Friday designed).

Proof: two <brand> emails from that week (Tue 13 WAR, Sun 26 Night of the Bumps) re-rendered from data
through the shared engine match what shipped. The week's made pictures and Halloween ornaments were copied
to `Shared Assets/brands/<brand>/email-sms/design-formats/` so any machine can build them.

Still open for <brand>: November copy is not written yet; its price list is empty (the product check holds
every price until it is filled from the pricing sheet); the plain 60-day guarantee line needs one confirm;
no ornaments yet.

## <brand>'s board, read in (17 Oct 2026)

the owner: *"the dude's email format system, the design files, the vibes … all that was derived from a
massive Figma board. I also did the same thing for [<brand>] … we have these sections, but we also have
the design system that sits with it."* On his word, <brand>'s Figma board ("Email Campaign and flows
Design", page "2026 Campaigns Designs 2/2", 13 emails, July to September 2026) was read into its design
system the way <brand>'s was:

- `brands/<brand>/email-sms/design-formats/census.json` / `census.md`: every email, its subject, headline,
  theme and sections top to bottom; pictures at `Shared Assets/brands/<brand>/email-sms/design-formats/board/`.
- `formats.md`: the look (dark band #19110E with the white wordmark, cream #FBFAF5, sand #F4EDDA, dark-brown
  panels #422F28, brown ink #422F28, dark compact buttons with 4px corners), the 16 sections counted, the six
  formats (Story, Weekend offer, Two jobs, When and how, Offer with a timeline, In their words), the July 4th
  and summer themes, and which board sections the team's banned-as-recycled list rules out.
- `components.json` v2 and `design-system.json`: the same values, read by the engine.

The engine gained what the board uses: header and footer on the brand's band, sand and dark-panel grounds,
a hero over a full-width photo, a photo row, a callout, a Week 1 / 4 / 8 timeline, a text link, and brand
layout settings (centred, compact buttons, headline size, a separate button face). Rebuilding the board's
"One Scent, On Purpose" through the engine matches the board; <brand>'s emails are unchanged.

The board was read from a native-size render (the connector cannot return this file's structure), so
exact faces and spacing are measured, not file values: a designer confirms them in one pass. Part 1 of the
page ("2/2") is not in this file.

## Putting it in the chain

Already a tool, any brand: `EMAIL-FORMATS.md` + `formats.json` · `section_email.py` ·
`asset-index/machine/proof.py` · `asset-index/machine/social_pull.py` ·
`approve_klaviyo.py` · `EMAIL-LINE.md`.

Hand-built inside `runs/email-production/<brand>/week-2026-10-12/` for that week:
`layouts.py` + `halloween_layouts.py` (job cards and layouts typed per email) ·
`design_system.py` + `.css` + `.tpl.html` (the emails, week hard-coded) ·
`klaviyo_build.py` · `final_check.py` · scenes and ornaments made one by one.

To run every week, those five pieces move from the week folder into
`tools/email-production/`, and step 1 reads the calendar's slots and the
copy chain's finished emails instead of being typed.

Landed on `main` 17 Oct 2026 (merge 197ac4553c).
