# One person's profile

Write one profile of ONE person. Not the group. {who}. The one thing that sets this person apart: {thing}.

Fill it in this order, and stop where the lines stop:

1. **Desire.** One want, sayable as "I want ...". It must be about the one thing. If the group's want is about another place or situation, it is not this person's want.
2. **Experiences.** What has happened and what was used, with what came of it. Fact only, no feeling.
3. **Emotions.** The feeling, then why. Name the trigger.
4. **Behaviors.** "So now I ...", with how often when a line says it.
5. **Culture.** Only what is this person's own.
6. **The opening line.** What would make this person say "that's literally me". About the one thing, in their kind of words.
7. **Doubt.** The one reason they would not believe us, in their words.

Every entry says which lines it stands on:
- `own`: the lines are about the one thing. Copy their ids.
- `shared`: the lines are from the same problem elsewhere and are still true of this person. Use at most two shared entries in a part, and only when nothing own exists.
A part with no lines is an empty list, and goes in `missing` as the plain question research must answer. Never fill a part from what people like this are usually like. Never use his/her together: the person is {gender}. Plain words. Race and age are the demographic's job and never an entry.

Answer with one JSON object in a ```json fence:
{"desire":{"text":"I want ...","lines":["id"],"from":"own|shared"},"experiences":[{"text":"","lines":["id"],"from":"own"}],"emotions":[],"behaviors":[],"culture":[],"opening":{"text":"","lines":["id"],"from":"own"},"doubt":{"text":"","lines":["id"],"from":"own"},"missing":["question"]}

## Own lines

{own}

## Asking for a product

{asks}

## Shared lines (same problem, not this one thing)

{shared}

## This person's world, from the culture map

{culture}
