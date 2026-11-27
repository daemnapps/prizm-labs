# PAGE TEARDOWN — THE SOURCE'S IDENTITY (v1)

List everything on this page that belongs to the SOURCE: things that must never appear on a page we write from it.
This list is what the identity check tests our finished page against, so miss nothing.

Pull, exactly as written on the page (copy the text verbatim here — this list is the only place source words are
kept, and only so they can be checked against):

- `brand` — every brand, company, store, publication, clinic and product name (ours never appears on this page)
- `person` — every person: founders, doctors, editors, testers, reviewers, authors, celebrities
- `place` — every town, city, region, state, country, address, neighbourhood
- `offer` — every price, discount, sale, bundle, shipping promise, free gift, appointment or booking offer
- `guarantee` — every guarantee, warranty, returns or refund promise, trial
- `cta` — every button and call-to-action text
- `nav` — every menu, header, footer, breadcrumb and site-link text
- `heading` — every headline and section heading, word for word
- `claim` — every specific claim, statistic, number of products tested, credential, award
- `phrase` — distinctive phrases a reader would recognise as this page's own (6+ words)
- `contact` — phone numbers, emails, URLs, handles
- `date` — every date

Return ONE json block and nothing else:

```json
{"items": [{"text": "exact text from the page", "kind": "brand | person | place | offer | guarantee | cta | nav | heading | claim | phrase | contact | date"}]}
```

The page, as captured from {source_url}:

```
{source}
```
