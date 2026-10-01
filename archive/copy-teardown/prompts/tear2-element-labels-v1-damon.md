**No example in this prompt is an answer.** Any id, name or phrase shown below
as an illustration of the SHAPE of a reply is a placeholder — never copy it
into your answer because it appeared here. Every id you write must be copied,
character for character, from the candidate lists you are handed further down.
An id that is not on its list is refused by the code that reads your reply, so
a guess is worse than saying nothing fits.

Here is the record of one piece of copy — words only. The source's own names
(its brand, products, people, handles) were taken out by the code before you,
on purpose; each shows only as a numbered marker, `[SOURCE NAME n]`: {record}

Here are the candidate rows — the only ids that exist — one list per label:
{candidates}

Your job is to LABEL this copy: say which library row it IS, on six lists. You
are not judging the copy, not improving it, and not describing it again. Label
the SOURCE as the record has it — nothing about any brand that might later
rebuild it.

The six labels:

1. `format/copy` — what kind of piece this is: its shape and its job, read from
   THE PARTS, THE BEATS and its length. If two rows fit, name the one whose
   JOB matches — a piece built mostly out of other people's quoted words is
   doing a different job from one person's own account.
2. `placement/all` — where these words ran: which slot of which channel the
   source's MAIN body was written for, read from THE PARTS and WHAT IT WAS
   BUILT TO DO. A source with a headline and a body is labelled by its body; a
   source that is only a set of headlines is labelled as headlines.
3. `framework/all` — the argument's plan, read from THE BEATS in the order a
   reader meets them, THE TURN and THE CLOSE.
4. `doctrine/awareness` — the level the OPENING assumes its reader already
   stands on: the record's AWARENESS entry level. Not the exit level.
5. `delivery/register` — how the sentences sound, read from VOICE MARKERS.
6. `delivery/humor` — whether, and how, it is funny, read from the quoted
   lines. A piece with no joke anywhere has a row of its own; that is not
   `none-fits`.

Rules, in order of importance:

- **One id per label, from that label's own list.** An id from the wrong list
  is a wrong answer.
- **Match on what the row says it IS** (its `what`), not on its name sounding
  close. Two rows can sound alike and describe different things. Some rows
  were written with a spoken piece in mind; match on what the row says about
  the WORDS, and ignore what it says about a face, a voice or a camera.
- **When no row fits, say so.** Write `none-fits` as the id and give
  `proposed`: one line, in the form `new-id — Name — what it is in one
  sentence`, written brand-free and subject-free so it could describe anyone's
  copy. A forced fit corrupts the library; `none-fits` grows it. Never bend a
  row to avoid writing `none-fits`.
- **`why` is evidence, not opinion.** One sentence that points at something
  the record actually holds — a beat number, a quoted line, a voice marker —
  that makes this row the match. No brand, product or person names, and no
  `[SOURCE NAME n]` markers, in `why` or in `proposed`: describe the function
  ("the sender's product", "the speaker").
- **A source defect is never evidence.** Do not match a row on a broken line.
- If the record does not contain enough to decide a label, that label is
  `none-fits` with `proposed` set to `undecidable — ` and what was missing.

# ELEMENT LABELS

Reply with ONE fenced block, tagged `ELEMENTS`, holding valid JSON with exactly
these six keys, and nothing before or after it:

```ELEMENTS
{
 "format/copy":        {"id": "<an id from the format/copy list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "placement/all":      {"id": "<an id from the placement/all list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "framework/all":      {"id": "<an id from the framework/all list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "doctrine/awareness": {"id": "<an id from the doctrine/awareness list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "delivery/register":  {"id": "<an id from the delivery/register list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "delivery/humor":     {"id": "<an id from the delivery/humor list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null}
}
```

`proposed` stays `null` unless the id is `none-fits`.
