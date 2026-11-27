# Who they are, from their own words

You are reading one {which}. Below are the card, the avatar it sits in, the brand's position, the doctrine, and the customer rows. Fill the slots. Every slot is something the rows show. A slot the rows do not show stays empty and is named in `gaps`. Never fill a slot from what people like this are usually like.

Rules:
- FILL EVERYTHING THE ROWS SHOW (owner, 2026-11-26: "there's no point in limiting, we should always be filling"). There is no number of entries to aim for: give one entry for every distinct want, role, belief, experience, behavior and feeling any row shows, however many that is. Merge only two entries that say the same thing; keep two that differ in what, when, where or why as two.
- Cite rows by the id in brackets, exactly as printed. At least one row per entry; two or three when they exist.
- A want is in their words, sayable as "I want". `human` names one life force and at most one learned desire from the list of seventeen: what is this person still chasing once every product detail is gone?
- Rank desires by urgency, staying power and scope. The first one leads.
- `roles`: `character` is who they say they are, `achievement` is what they say they have done, `becoming` is who they want to be. Never a race, an age or a place.
- `beliefs` are facts they already accept before any ad, not claims we would like to make.
- `experiences`: what has happened to them and what they used, with what came of it. Fact only, the feeling stripped out.
- `behaviors`: what they now do because of it ("So now I ..."), with how often when a row says so.
- `emotions`: the feeling, then why, in one plain line.
- `doubts`: for each of the four, the words one person actually wrote, copied from the row. Leave out a doubt nobody voiced.
- `objections`: every OTHER distinct doubt or objection anyone voiced, each its own entry, its kind one of the four, its words copied from the row.
- `doubt_lead`: the doubt that stops most of them.
- `awareness_lead`: the level most of the people we have not sold to yet are at, read from the rows: unaware, problem-aware, solution-aware, product-aware or most-aware.
- `stage`: what this market has already heard and is tired of, in one line, from the position and the rows.
- For a sub-avatar: only what differs from, or is sharper than, the avatar's own slots below. Never repeat those.
- Plain words. No clever pairs, no slogans.

Answer with one JSON object in a ```json fence:

{"desires":[{"want":"I want ...","human":["attraction","beauty-style"],"urgency":"why now","staying":"why it stays","scope":"how many","rows":["id"]}],
 "roles":[{"role":"","kind":"character|achievement|becoming","rows":["id"]}],
 "beliefs":[{"belief":"","rows":["id"]}],
 "experiences":[{"fact":"","rows":["id"]}],
 "behaviors":[{"does":"So now I ...","rows":["id"]}],
 "emotions":[{"feel":"embarrassed: the barber notices first","rows":["id"]}],
 "doubts":{"does-it-work":{"said":"their words","rows":["id"]},"for-me":{"said":"","rows":[]},"worth-it":{"said":"","rows":[]},"trust-you":{"said":"","rows":[]}},
 "objections":[{"kind":"worth-it","said":"their words","rows":["id"]}],
 "doubt_lead":"for-me","awareness_lead":"problem-aware","stage":"","gaps":[""]}

## Already found from earlier rows

{found}

Everything above stays. Answer with ONLY the new entries these rows show that are not already above, plus any entry above that these rows add a row to (give it again with its exact text and the new row ids). Leave a slot out when these rows add nothing to it.

## The person

{person}

## The avatar

{avatar}

## The avatar's own slots, already filled

{core}

## The brand's position

{position}

## Doctrine: desire

{desire}

## Doctrine: belief

{belief}

## Doctrine: awareness

{awareness}

## Doctrine: market stage

{sophistication}

## The rows

{rows}
