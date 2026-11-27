# Design step 4 · fill the gaps, change nothing else

Every brand, product, offer and avatar name below comes from THIS email's own inputs. Never bring in an example, a
product or an offer from anywhere else.

The email below is finished and approved in everything except the gaps listed. People have already ruled on its
concept, its pictures, its prices and its words. Your job is to close each gap with the **smallest change that makes
the email whole**, and to leave every other section exactly as it is: same words, same pictures, same order, same
prices. A redesign is a failure of this step even if it is better.

## How to close a gap

- **A missing member of a sequence** (STEP TWO after STEP ONE, the third of "three reasons"): add one section right
  after the last member, **in the same section type and the same form** as the members already there (same title
  pattern, same length of words, a picture of the same kind). Its words come from the job card's proof and the copy.
  Its picture shows the real product that does that step, exactly as PRODUCT TRUTH describes it.
- **A promise stated but not explained** (a box that says only "60 DAYS"): add the missing words to that section, in
  the words the copy, the job card or the rulings already use. Never invent terms.
- **Half a claim** (the job card's proof has two halves and the email shows one): add the missing half where the
  first half already is, as one more line or one more card in the same form.
- **A section that contradicts a ruling**: change only the words or price in that section to match the ruling.
- If a gap can only be closed by a fact nobody has given (a price, a term, a person), do not invent it: leave it and
  say so in "cannot_fill".

## Pictures

A new picture is a slot to make, written as {"todo": "what it shows", "brief": "how it looks, in the same style as
the email's other made pictures", "use": "story", "product": "<product key, when a product is in frame>"}. Prefer a
real photo the email's inputs already name. Never move or change an existing picture, and **never rewrite an existing
picture's description (its alt) to claim something is in it**: the words describe what people see, so a gap that
needs something in a picture is closed by changing the WORDS that point at it, or by a new picture slot.

## The rules that win

RULINGS (newest decisions; they win over everything):
{rulings}

PRODUCT TRUTH (how each product physically looks and is held):
{product_truth}

THE SECTION TYPES this brand's emails are built from:
{sections}

## The email

THE JOB CARD:
{job}

THE COPY:
{copy}

THE GAPS TO CLOSE (each with what is missing and a suggested fix):
{gaps}

THE EMAIL AS IT IS NOW, as JSON (sections numbered from 0):
{spec}

## Answer

Return only JSON, no prose:

{"ops": [
  {"op": "insert_after", "index": 6, "section": {...one complete section in this brand's section format...}},
  {"op": "set", "index": 9, "field": "lines", "value": [...]},
  ...
 ],
 "closed": ["which gap each op closes, in one line each"],
 "cannot_fill": ["any gap that needs a fact nobody gave, and the fact it needs"]}

`index` always refers to the email as it is now (before any op). Use as few ops as close the gaps.
