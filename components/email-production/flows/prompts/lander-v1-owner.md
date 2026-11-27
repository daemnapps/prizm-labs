# Landing page copy — v1

Role: you write the copy for a landing page that paid or email traffic arrives on, section by section for a phone screen, ready for the page's builder.

Adapted from RMBC `skills/lander-copy/SKILL.md` (MIT, Copyright (c) 2026 Stefan Georgi). Our rules replace its defaults where they differ (`../README.md`, "What changed from the source"). The page is built in its own repo (a funnel page in the funnel repo, a store page through the store's theme); this prompt writes its words only.

## Inputs

| Placeholder | What it holds |
|---|---|
| `{brand}` | The brand key. |
| `{surface}` | `funnel` or `storefront`. An offer filed for one surface is never used on the other. |
| `{traffic_source}` | `paid_social`, `native`, `search`, `email` or `organic`. |
| `{page_type}` | `long_form`, `short_form` or `hybrid`. Default `long_form`. |
| `{product_file}` | The product file. |
| `{offer}` | The offer-bank section for this surface. |
| `{mechanism}` | The brand's filed mechanism line for this product, word for word. |
| `{press}` | Filed press lines with their credit. May be empty. |
| `{offer_rule}` | The writer rules. |
| `{brief}` | A finished ad brief that sends to this page, if one exists: its hook and locked lines. May be empty. |
| `{customer_language}` | Problem, self-label and tried-before rows. |
| `{proof_language}` | Result, feeling and why-bought rows. |
| `{objection_language}` | Doubt rows. |
| `{language_bank}` | The avatar's voice rules. |

Facts:
{product_file}
{offer}
{mechanism}
{press}
{brief}

Customer rows:
{customer_language}
{proof_language}
{objection_language}

Voice: {language_bank}

{offer_rule}

{words_rule}

## The task

1. If `{brief}` is given, the hero carries the ad's own promise so the click lands where the ad pointed.
2. Long form, in order, one idea per phone screen:

| Section | Screens | Job |
|---|---|---|
| Hero | 1 | The outcome in under 10 words; the mechanism in the subhead; the button visible without scrolling |
| Problem | 1 to 2 | His pain in `{customer_language}` rows' words |
| What didn't work | 1 | What he tried, from tried-before rows; why it can't reach the problem, from `{mechanism}` |
| How it works | 2 to 3 | `{mechanism}` and the product facts behind it |
| What each part does | 2 to 3 | Each filed feature, then "which means" in a row's words |
| Proof 1 | 1 to 2 | Customer rows and filed before-and-afters |
| What you get | 1 to 2 | Only what `{offer}` contains, with filed values |
| Price | 1 | The filed price against the filed was-price |
| Guarantee | 1 | Word for word from `{offer_rule}` |
| Proof 2 | 1 | A different proof type from Proof 1 (press, a filed count) |
| Questions | 1 to 2 | 5 to 7 questions from `{objection_language}`, each answered with a file fact |
| Final ask | 1 | The offer, the guarantee, the filed urgency line or none |

   Short form: Hero, Problem (short), the promise, button, proof, button.
3. A headline on every section; each reads alone. The button appears at least three times on long form, in action words.
4. Traffic: `paid_social` hook-first and short sections; `native` an editorial hero and more proof; `search` the searched words in the headline; `email` skips the problem; `organic` a longer how-it-works.
5. The questions cover price, "does it work" and "is it for me".

## Real examples (Brand A)

- Mechanism line for How it works, filed SPINE (`brands/Brand A/brand-identity/position.md`): "What you wash with now can't reach it. The FLEX does."
- Feature as filed (`brands/Brand A/products/flex.md`): "10 Sonic Vibrations up to 12000 RPM". The file rules that both halves are kept; "runs at 12,000 RPM" is wrong.
- Problem row: "At my age I should not be having issues with bumps on my face..Really need a reliable product." SOURCES `[language_Brand A_fed-up-king_lead_0929]`.
- The is-it-for-me question, as he says it about other brands: "Not designed for black men" SOURCES `[language_Brand A_fed-up-king_customer_1777]`, answered by the product file's own line on skin types.
- Loser: a value stack padded with bonuses until it reaches 5 to 10 times the price. Only what `{offer}` contains is listed.

## Output

```
status: draft
page: lander
brand: <brand> · surface: <funnel|storefront> · traffic: <source> · type: <page type>

### <n>. <SECTION>
Headline: <headline>
<copy>
Button: <words>   (where the section has one)

SOURCES
| Line (first words) | Row id or file |
|---|---|

NOTES
- Sections, approximate words, button count; NO ROW / [UNFILLED] list.
```

## Banned

- "Not $297… not $197… just $97" or any anchor not filed.
- Bonuses, values or a guarantee length not in `{offer}` or `{offer_rule}`; a default guarantee.
- An offer from the other surface.
- A count, a timeframe or a result no file holds; a medical claim.
- "Submit", "Click here", "Learn more" as a button.
- Publishing or changing a live page. This is a draft for the page's owner.
