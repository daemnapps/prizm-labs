# Culture map — bottom-up (v1)

Used by `research_gatherer/culture_map.py` (CLI: `components/research-gatherer/culture_map.py`).
One call per avatar. The engine fills the `{{…}}` slots at run time: the
evidence pack (bank rows, My Feeds posts / authors / hashtags, culture digs,
culture reads from teardowns, each with its id) and the unbacked candidates
(the hand-built map, the profile, the voice rules). Nothing brand-specific is
written here. Every example below is a SHAPE, not content to reuse.

After the model answers, the engine checks every line: a line that does not
end with evidence ids, or cites an id that is not in the pack, is dropped and
counted. The To test section is not checked; nothing in it is used as fact.

---

You are writing the culture map for one kind of person, so the people writing
{{BRAND}}'s ads know what this person watches, trusts, quotes, cares about and
laughs at. The ads are written from this map, so a wrong line becomes a wrong ad.

Avatar: `{{AVATAR}}` · its sub-avatars: {{SUBS}}

## The one rule

You may only say what the EVIDENCE below shows. Every line you write ends with
the ids of the evidence it rests on, in square brackets, copied exactly as
they appear in the pack:

    - <the claim, in plain words, with the number that proves it> [id, id]

A line with no brackets, or with an id that is not in the pack, is deleted
before anyone reads it. Do not invent ids. Do not shorten them. A post id is
the whole `post:<url>`.

## What counts as evidence

- **Bank rows** (`language_…`): real words real people wrote. Quote them
  verbatim, short. `likes` and `said Nx` say how loud they were.
- **Feed posts** (`post:<url>`): what wins in the feeds built for this person,
  with the latest view count. Say the views. `(sift: junk)` means the post was
  judged off-topic; never build on it, but you may list it under Off-limits if
  it shows a line not to cross.
- **Feed authors and hashtags** (`feed:<feed>@<author>`, `feed:<feed>#<tag>`):
  how many posts and how many summed views. A pattern across many posts is
  stronger than one big post. Say both numbers.
- **Culture digs** (`dig:<path>`): what the most engaged commenters in a room
  carry on their own posts. A signal under 3 people is thin; say "thin".
- **Culture reads** (`run:<slug>#R<n>`): a reference a teardown found in a
  real post, with its receipts and confidence. Prefer CONFIRMED.

The feeds were seeded from a plan written before the data, so a feed shows
what wins inside the world we guessed. Say "in his feed", never "he follows".
When a line holds for one sub-avatar only, start it with the sub id in bold
(`**sub-id:**`).

## Unbacked candidates

Below the pack are the hand-built map, the profile and the voice rules. They
are NOT evidence. For each claim in them that matters to culture (a show, a
creator, a phrase, a value, a joke, a line not to cross):

- if pack evidence backs it, write it in the body with the pack ids;
- otherwise put it under **To test**, one line each, saying what it claims,
  where it came from (hand map / profile / rules), and what evidence would
  settle it. No brackets needed there.

Never move a candidate into the body because it sounds right. A famous name,
a slogan, a creator list, a "research says": if the pack does not show it,
it goes to To test. Off-limits lines from the rules or profile also go to To
test unless the pack shows the risk; the body's Off-limits is only what the
evidence shows.

## Write these sections, in this order, as `## ` headings

1. `## What they watch and listen to` — worlds, formats, creators, sounds, with
   counts and views.
2. `## Who they trust` — who they listen to, from their own words.
3. `## References and slang` — the words and references they actually use,
   quoted.
4. `## What they care about`
5. `## What they laugh at` — what the comedy in the evidence is about, and how
   it is built (format, who is the butt).
6. `## What moves them that isn't a joke` — pride, nostalgia, family, relief:
   the straight emotional ground.
7. `## Off-limits` — what the evidence shows would turn them off or hurt them.
8. `## Culture uses` — a table:

   | Reference / format | What it does | Receipt |
   |---|---|---|
   | <shape: a reference> | <laugh · belonging · nostalgia · trust · aspiration · relief> | [id, id] |

   The receipt cell holds only the bracketed ids.
9. `## To test` — the candidates the evidence does not back yet.

Bullets, short, plain words. One claim per line. No em dashes. Group lines
under `### ` subheadings inside a section when it helps (one per world or per
sub-avatar). If a section has no evidence, write nothing under its heading;
the engine marks it empty. Return the sections only: no title, no preamble,
no closing note, no code fence.

## EVIDENCE PACK

{{PACK}}

## UNBACKED CANDIDATES (not evidence)

{{CANDIDATES}}
