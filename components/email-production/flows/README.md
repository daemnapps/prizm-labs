# flows: email flows and page copy (RMBC skills, v1)

Nine prompts that write automated email flows and page copy, every customer-facing line built from the
brand's language-bank rows and files and cited by row id. Status 2026-11-07: **installed, with a fill-only
runner.** `email_line.py` reads `../prompts/` only (`latest_prompt`, not recursive), so nothing here changes a
live stage. `run_flow.py` fills one flow's prompt from the files and the bank and writes it out; it calls no
model, writes no exposure record and sends nothing:

    python3 flows/run_flow.py --brand Brand A --flow welcome --avatar fed-up-king --offer flex --offer popup --set length=6 --out FILE

A slot the files cannot fill (a link, a length, an unfiled story) is set with `--set name=value` or comes out
as `[UNFILLED] name`.

**Drafts only.** Every output carries `status: draft`. Nothing here schedules, sends or builds a flow in
Klaviyo or Postscript, or publishes a page. Flows are assembled in the platform by a person (`../PARKED.md`);
pages change in their own repo.

## The prompts

| File | Makes | Source skill (RMBC) |
|---|---|---|
| `prompts/welcome-v1-owner.md` | 5–7 email welcome flow | `skills/welcome-sequence/SKILL.md` |
| `prompts/soap-opera-v1-owner.md` | 5–7 email story flow | `skills/soap-opera-sequence/SKILL.md` |
| `prompts/cart-abandonment-v1-owner.md` | 3–4 email abandoned-cart (or abandoned-checkout) flow | `skills/cart-abandonment-flow/SKILL.md` |
| `prompts/checkout-abandonment-v1-owner.md` | Checkout page audit with exact fixes | `skills/checkout-abandonment/SKILL.md` |
| `prompts/post-purchase-v1-owner.md` | 4–5 email post-purchase flow | `skills/post-purchase-sequence/SKILL.md` |
| `prompts/upsell-sequence-v1-owner.md` | 3–5 email upsell flow | `skills/upsell-sequence-writer/SKILL.md` |
| `prompts/upsell-page-v1-owner.md` | One-time offer page after checkout | `skills/upsell-script/SKILL.md` |
| `prompts/lander-v1-owner.md` | Landing page copy | `skills/lander-copy/SKILL.md` |
| `prompts/product-page-v1-owner.md` | Product page copy | `skills/pdp-ecomm-template/SKILL.md` |

`WORDS.md` is the one rule for where words come from; it fills `{words_rule}` in every prompt.

## What fills each input

The same sources the email lane already reads (`../email_line.py`, `../offers.py`):

| Placeholder | Filled by |
|---|---|
| `{customer_language}` | `language.for_stage(brand, "injection", avatar, funnel, …, used="fresh")` from `components/copywriter/machine/language.py`, funnel = the flow's reader (below); rows render as `- [row id] "text"`; the avatar's lived moments are added once, picked without a record |
| `{proof_language}` | the same call with stage `"proof"`, funnel `customer` (buyers) on every flow |
| `{objection_language}` | the same call with stage `"close"`, funnel = the flow's reader |
| `{language_bank}` | `brands/<brand>/core-avatars/<avatar>/language/rules.md` |
| `{offer_rule}` | `offers.writer_rules(brand, offer, deadline=…)`: guarantee lines word for word, the only deadline, no code, `NO_INVENTION` |
| `{offer}`, `{upsell_offer}`, `{pairs_with}` | each `--offer` id's own section of `brands/<brand>/products/offer-bank.md` (`##` or `###` heading), plus its Proof section |
| `{story}` | `brands/<brand>/brand-identity/story.md` |
| `{product_file}`, `{upsell_product}` | `brands/<brand>/products/<product>.md` |
| `{mechanism}` | the brand's filed position line (`brands/<brand>/brand-identity/position.md`) |
| `{shipping}` | `brands/<brand>/operations/shipping.md`, "Claims these numbers support" |
| `{offer_box}` | `brands/<brand>/offers/standard-offer-box.md` |
| `{sender_identity}` | as `email_line.py` resolves it |
| `{words_rule}` | `WORDS.md` |

The flow's reader, by funnel (`run_flow.FLOW_FUNNELS`): the bank's rows carry `prospect` (social comments,
not opted in), `lead` (opted in, commented on an ad, or abandoned), `customer` and `churned`. The prospect query
returns social comments only, so no flow reads it.

| Flows | Reader rows (customer, objection) | Proof rows |
|---|---|---|
| welcome, soap opera, cart, checkout audit, lander, product page | `lead` | `customer` |
| post-purchase, upsell emails, upsell page | `customer` | `customer` |

`brands/` is read only from here.

## What changed from the source

Our rules replace the RMBC defaults wherever they differ:
1. Its specificity gate stays, but every number, name and timeframe comes from a file. Where none exists the line stays general or is marked `[UNFILLED]`.
2. Urgency is the plan's deadline or a filed line, or none. Its stock warnings, countdowns and "price increase" closes are dropped.
3. Discounts, bonuses, value stacks and anchor prices come only from the offer bank. Its "anchor 5–10×", "add bonuses" and "Not $297… just $97" moves are dropped.
4. Its default guarantee (60 days) is dropped; the guarantee is word for word from `{offer_rule}`.
5. Its unsourced figures (checkout abandonment rates, recovery rates, phone traffic shares) are dropped; a cost is measured or written "not measured".
6. A story, founder or customer, holds only what is filed.
7. A brand's fixed offer box wins over its product-page value stack and pricing sections.

## Test

`python3 test_flows.py`: the runner covers every prompt, fills the file and bank slots, and writes nothing; every prompt has its sections in order (role, inputs, task, real examples, output,
banned), binds `{words_rule}`, `{offer_rule}` and a language slot, writes `status: draft`; no file name can
be picked up by `latest_prompt`; and every row id cited in an example exists in the brand's bank, with every
quote next to it inside that row's text.

## License

The prompts adapt files from https://github.com/coleschaffer/copywritingskills-rmbc (commit `8327d49b`),
MIT License, Copyright (c) 2026 Stefan Georgi. The full notice is `LICENSE-rmbc.md`.
