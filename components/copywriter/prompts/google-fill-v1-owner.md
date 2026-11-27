*v1 (2026-11-23: the first Google ads were raw customer lines; this builds them properly). One Google ad group in, one responsive search ad out, every line a competitor's proven format filled with our words. Run by `components/copywriter/machine/google_copy.py write`; the parts in {braces} are filled by that tool.*

---

You are writing one Google search ad for one ad group. A person typed one of the searches below into Google; the ad answers that search in seconds and sends them to the landing page named below. Advertising is one clear point that gets a response. Never clever: clever confuses.

How Google shows it: two or three of the headlines side by side, then one or two descriptions, picked and ordered by Google. So every line stands on its own, reads as a finished thought, and no two lines say the same thing.

## The ad group

Topic: {group}

What people search (monthly US searches where known):
{keywords}

The page the ad sends to: {final_url}
What that page promises, in its own words:
{page}

## The product

{product}

## The offer on that page today

{offer}

## Our customers' own words for this topic (row ids in brackets)

{words}

## The formats you fill

Real lines from competitors' Google ads that are still running, stripped to [BLANKS]. `days` is how long the ad has run. Fill these; never write a line that is not one of them.

Headline formats:
{headline_formats}

Description formats:
{description_formats}

## How to write it

1. **Every line fills one format above**: keep the format's fixed words, in order; fill its blanks. Name the format's id on each line.
2. **The blanks are filled with what is on file and nothing else**: the product's own claims and facts above, the page's promise and proof, the offer, and our customers' words. Where a customer phrase fits a blank, use it word for word. A claim, number, rating, review count or guarantee that is not written above is never used.
3. **Speak to the search.** At least {min_keyword} headlines carry the words of one of the searches above, so the ad visibly answers what was typed.
4. **The mix**: across the {n_headlines} headlines cover the search, the result, how it works, the proof, the offer or guarantee, who it is for, and a call to action. Across the {n_descriptions} descriptions: what it does and why it works, the proof, the offer and guarantee, the call to action.
5. **Google's rules**: headlines at most 30 characters, descriptions at most 90, both counted with spaces. No exclamation mark in a headline. No emoji. No other brand's name. Capitals only at the start of words or in the product's own name. No price unless the offer above is marked as a promotion, and then only the price written there.
6. Two display path words of at most 15 characters each, no spaces, that name the topic and the product (Google shows them after the site name).

{repair}

## What you return

Only one fenced json block:

```json
{
  "headlines": [{"text": "…", "format": "h12", "slot": "result", "words": ["row id if a customer phrase was used"]}],
  "descriptions": [{"text": "…", "format": "d4", "slot": "how-it-works", "words": []}],
  "path1": "…",
  "path2": "…"
}
```
