# Culture tags — v1 (the owner)

Used by `research_gatherer/retag.py` (`gather.py retag --culture`). It re-reads
rows ALREADY in a language bank — comments, community posts, creator
comments — and says which culture tags each one also carries. It only ever
ADDS tags: a tag a row already has is never questioned or removed. One call
per batch of rows. The engine fills the `{{…}}` slots at run time; nothing
brand-specific is written here. The examples below are shapes, not words to
look for.

These tags are what the avatar's culture map is built from (what they
watch, who they trust, their slang, what they laugh at, what is off-limits),
so a wrong tag puts a false line on that map. When unsure, leave it off.

---

You are reading real words people wrote in the comment sections and
communities where one audience gathers. For each row, say which of these
seven culture tags the words carry. Most rows carry none — that is the
normal answer, and an empty list is a good answer.

The audience these rows are filed under:

{{AVATAR}}

## The seven tags

- `taste` — the row names something this room enjoys, rates or holds up as
  good: a creator, a show, a song, a game, a format, a look, a brand of
  thing, a style. Shape: "<a name> is the best at this", "this sound again",
  "the <style> on him is crazy". Praise of the person in the post alone
  ("you look great") is not taste unless it names what is good.
- `cringe` — the row mocks or recoils from something: an ad register, a
  phrase, a look, a type of person, something that reads as trying too hard.
  Shape: "nobody talks like this", "the <thing> made me cringe", "why do
  they always <do that>".
- `subculture` — the row reads as belonging to one specific community, not
  to language in general: its own register, rituals, ranks, gear, places.
  Shape: a routine or rule only members would know, spoken as if everyone
  reading knows it too.
- `in-word` — the row uses one specific slang term, abbreviation, nickname
  or reference point that marks membership. Shape: a word an outsider
  would have to look up.
- `community-voice` — the row speaks for the group or to the group, not
  just for the speaker: "we", "us", "all of us who…", a shared complaint,
  a call-and-response line the room repeats.
- `role-claimed` — the speaker claims a role or identity for themselves:
  "as a <role>…", "I'm a <role> and…", "my <family role> does this".
- `laugh` — the row is a joke, or reacts to one: a roast, a punchline, a
  bit, playing along with the post's joke, or laughter itself in words
  ("I'm crying", "this got me", "not the <detail>"). Laughter in emoji
  only counts when the row also has words.

A row can carry several. Tag the WORDS, not the post they sit under.

## Return

A JSON array, one object per row that carries at least one tag, and
nothing else — no prose, no code fence. Rows that carry none are left out.

```
[{"i": <the row's number>, "add": ["<tags from the seven above>"]}]
```

Rows:

{{ROWS}}
