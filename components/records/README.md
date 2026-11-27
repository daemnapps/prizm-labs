# Records

**Keys this tool needs:** none.

Every record the system keeps, one name each, linked by id. Any result traces back to the brief, the offer and the
brand that made it. That trace is what lets the system learn from its own numbers: winners ranks ads by their
results, and each session's learnings name the part of the system they should change.

You don't run it by hand. Tools write their records as they run; ask Claude "trace this ad" or "check the records".

## The records

```
brand → offer → funnel ← page (presell · offer · checkout · post-purchase)
                  ↓
research → ad-brief → organic · dr · creator → ad → email → text
                                                ↑
                                             results

session: every working session, by anyone, in any tool → what it made + what it learned
```

| Record | Means | Links to |
|---|---|---|
| brand | A business the system works for | |
| offer | What the brand sells in one deal | brand |
| page, presell-page, offer-page, checkout-page, post-purchase-page | One page a buyer sees | brand, offer |
| funnel | The pages an ad sends a buyer through, in order | brand, offer, pages |
| research | What buyers say and want, every quote sourced | brand |
| ad-brief | What one ad must say and do | brand, offer, research |
| organic · dr · creator | The brief written as a native post, a direct-response ad, or a creator's film list | ad-brief |
| ad | One finished ad and its results | brand, offer, funnel, ad-brief |
| email · text | One send and what it earned | brand, offer, ad / email |
| session | One working session: what it made and learned | brand |

The full definition, every field and its type, is `records.json`. A record is one file at
`brands/<brand>/records/<record>/<id>.json`, so it stays in the brand's own folder and never in this repo.

## Commands

| Command | What it does |
|---|---|
| `records.py list` | every record, what it means, what it links to |
| `records.py new <record> --brand <id>` | a blank record to fill |
| `records.py check <file> ...` | each file against its record's shape |
| `records.py trace <id> --root <folder>` | one record back through everything it came from |

Tests: `python3 components/records/test_records.py`.

Neighbours: [system](../system/) (the words), [naming](../naming/) (the ad name results join on),
[brand folder](../../brands/_TEMPLATE/) (where records live).
