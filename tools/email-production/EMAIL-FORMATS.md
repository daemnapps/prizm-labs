# Email formats — every email is a short landing page

the owner, 2026-10-08: *"We need to have formats of emails very clearly defined so
that we know how many images need to be generated. We need to think about email
design just like we think about landing page design, because they're basically
just many landing pages."* For now the emails are built from **sections** and
uploaded to Klaviyo directly — nobody builds one by hand. More design elements
are added over time; the target is designed, generated emails by Black Friday.

This file fixes three things: **which format a send gets, which sections it is
made of, and exactly how many pictures it needs and of what kind.** It builds
on what is already ruled — it invents no names:

- the **section names** are the 17 fixed ones in `SECTIONS.md`;
- the **formats** are the brand's own, read off its design file —
  for Brand B, `brands/brand-b/email-sms/design-formats/formats.md` (8 formats,
  2026-08-31), plus `simple` from the element library (`template.email`);
- the **picture rule** is `IMAGERY.md` (2026-09-09) — never a product or a
  person from a text description — made concrete per slot below.

## The four kinds of picture slot

Every picture in every format is one of four kinds. The kind decides where it
comes from and whether anything is generated at all.

| kind | what it is | where it comes from | generated? |
|---|---|---|---|
| **SCENE** | a person or a place doing the thing the section argues | a **real-life reference first** — a frame from footage we own (`tools/asset-index/machine/search.py`), a customer photo, a before-after, the archive — then our own version made on top of it with the banked person and the real product as references | yes, from references — never from words alone |
| **PRODUCT** | the product itself | the refined product kit render (`runs/ai-elements/<brand>/products/<slug>/model/`, once signed off) or the live-store photo | no |
| **PROOF** | a result, a review, a before-after | the real thing, as it is (`core-avatars/before-afters.md`, reviews, customer posts) | no |
| **DETAIL** | a texture or close-up — lather, bristles, a label, skin | a real macro reference (store photo, studio render, footage frame), then made on top of it | yes, from references |

**Real customers and before-afters are usable** (the owner, 2026-10-08: *"You can
use all of my before-and-afters. All this content in the archives is 100%
usable."*) — as references for a SCENE and as-is in a PROOF slot.

## The formats, as stacks of sections

Picture count = what the email needs made or placed. `S` scene · `P` product ·
`R` proof · `D` detail.

| format | for | sections, top to bottom | pictures |
|---|---|---|---|
| `simple` | letters, notes, one-thought sends | header · hero (1S) · [offer (1P)] · cta · footer | **1–2** (1S + optional 1P) |
| `hero-product` | one product carries it | header · hero (1P) · mechanism (3D chips) · cta · cards (1S lifestyle) · cta · footer | **5** (1P · 3D · 1S) |
| `proof-grid` | evidence carries it | header · hero · review (6R grid) · mechanism · b4a (1R) · stat-proof · cta · cards (2S) · footer | **9** (7R real · 2S) |
| `system-education` | several products as one routine | header · symptoms · product-row (1P per product) · routine-steps · cta · footer | **1P per product** (+ optional 1S) |
| `winback` | coming back without shame | header · hero · mechanism (what changed) · cards (1S or 1P) · cta · footer | **1** |
| `objection-crusher` | the doubt, faced | header · hero · cards (1 real person: R or S) · mechanism · review · product-row (2–3P) · guarantee · cta · footer | **3–4** (1 person · 2–3P) |
| `offer-urgency` | the ask | header · hero · cards (3S/P) · pricing · social · cta · footer | **3** |
| `launch-window` | a drop with a deadline | header · hero (1P) · offer · cta · footer | **1–2** |
| `brand-manifesto` | a position, out loud | header · hero · cards (1S portrait) · mechanism · product-row (2P) · cta · footer | **3** (1S · 2P) |

## Which format each send type gets (the default)

The calendar names a send's `type` (element library `format.email`). Its format
defaults from this map; a send may override it in its run when the email argues
something else. A type not listed is `simple`.

| format | send types |
|---|---|
| `hero-product` | product-spotlight · mechanism · launch (single product) |
| `proof-grid` | proof-drop · spotlight · someone-like-you · room-answered · peer-advice |
| `system-education` | bundle · stack · routine · mistake-audit |
| `winback` | sunset · availability · restock · what-went-wrong |
| `objection-crusher` | guarantee · objection-shot · switch · myth-correction |
| `offer-urgency` | sale-window · last-chance · early-access · gift-guide |
| `launch-window` | launch (a drop with a deadline) · anticipation |
| `brand-manifesto` | mission · opinion · founder-note · milestone |
| `simple` | everything else — moment · holiday · content-request · product-finder · subscription-invite · reader-question · problem-explainer · affiliate · channel-invite … |

## The picture step, in the chain

After the copy is written (step 8) and before layout:

1. **Format.** From the map above (or the send's override). It fixes the
   sections and the picture slots.
2. **Real reference per slot.** SCENE and DETAIL slots get a real-life
   reference found first — `search.py --brand <b> "<what the slot shows>"`
   over footage we own, then customer photos, before-afters, the archive.
   PRODUCT and PROOF slots are filled from the real thing directly.
3. **Picture brief per generated slot.** The slot's one job, the shot, the
   real reference, who (a banked casting sheet or a real customer), where,
   which real product. Filed at
   `runs/email-production/<brand>/week-<date>/picture-briefs.json`.
4. **Sign-off.** the owner approves the briefs on the weekly picture page before
   anything is spent.
5. **Generate.** `tools/image-production` (`make.py --purpose email-hero`)
   with the real reference, the person's casting sheet and the product
   reference all attached. Never words alone.
6. **Check.** Product against its kit (`product_check.py`), face against its
   casting sheet; one fix if off.
7. **File.** Drive, `Shared Assets/runs/email-production/<brand>/<label>/`,
   named by slot (`hero.png`, `product-1.png`, `scene-2.png` …); an earlier
   picture is kept as a version, never deleted.
8. **Sections to Klaviyo.** The email is laid out as its format's sections
   and uploaded as a draft to the send's engaged segment. A person schedules.

## What is built and what is not (2026-10-08)

- Built: the copy chain; the `simple` layout and its Klaviyo draft
  (`simple_email.py`); image-production with references; the footage search.
- **Not built yet:** the section renderer for the eight designed formats, and
  the picture step's steps 1–3 in code (today the hero is still made from the
  writer's words alone — the gap that made the October heroes generic). Until
  the renderer lands, a designed format is laid out by hand in the brief and
  its pictures are made through this step; `simple` ships as it does today.
