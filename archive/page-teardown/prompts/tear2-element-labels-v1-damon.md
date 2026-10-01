**No example in this prompt is an answer.** Any id, name or phrase shown below
as an illustration of the SHAPE of a reply is a placeholder — never copy it
into your answer because it appeared here. Every id you write must be copied,
character for character, from the candidate lists you are handed further down.
An id that is not on its list is refused by the code that reads your reply, so
a guess is worse than saying nothing fits.

Here is the record of one landing page — its sections as read, and its
defects. The site's page furniture was taken out before you, on purpose:
{record}

Here are the candidate rows — the only ids that exist — one list per label:
{candidates}

What a rule-based classifier read the page's format as, from its address and a
few surface markers (a second opinion, often wrong on unusual pages — the
record outranks it): {code_format}

Your job is to LABEL this page: say which library rows it IS. You are not
judging the page, not improving it, and not describing it again. Label the
SOURCE page as the record has it — nothing about any brand that might later
rebuild it.

The labels:

1. `format/page` — ONE id. What kind of page this is: its shape and who carries
   it, read from THE PAGE AT A GLANCE and the run of the sections.
2. The framework list, when the candidates include one (`framework/…`) — ONE
   id. The plan the argument follows, read from the sections in the order a
   reader meets them. If the candidates hold no framework list, leave this
   label out entirely.
3. `doctrine/section` — ONE id FOR EACH section the record numbers (`S1`, `S2`,
   …): the job that section does in the argument. Label every numbered section,
   once, under its own number. Two sections may carry the same id — a page may
   prove twice or ask three times.

Rules, in order of importance:

- **One id per label, from that label's own list.** An id from the wrong list
  is a wrong answer.
- **Match on what the row says it IS** (its `what`), not on its name sounding
  close. Two rows can sound alike and describe different things. Several rows
  were written about another kind of asset; read them for the JOB they name,
  which is the same job on a page.
- **When no row fits, say so.** Write `none-fits` as the id and give
  `proposed`: one line, in the form `new-id — Name — what it is in one
  sentence`, written brand-free and subject-free so it could describe any
  seller's page. A forced fit corrupts the library; `none-fits` grows it. Never
  bend a row to avoid writing `none-fits`.
- **`why` is evidence, not opinion.** One sentence that points at something the
  record actually holds — a section number, a quoted line — that makes this row
  the match. No brand, product or person names in `why` or in `proposed`:
  describe the function ("the seller's product", "the speaker").
- **A source defect is never evidence.** Do not match a row on a broken line.
- If the record does not contain enough to decide a label, that label is
  `none-fits` with `proposed` set to `undecidable — ` and what was missing.

# ELEMENT LABELS

Reply with ONE fenced block, tagged `ELEMENTS`, holding valid JSON in exactly
this shape, and nothing before or after it. The framework key is spelled
exactly as its candidate list's heading spells it:

```ELEMENTS
{
 "format/page": {"id": "<an id from the format/page list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "<the framework list's heading>": {"id": "<an id from that list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "doctrine/section": [
  {"section": "S1", "id": "<an id from the doctrine/section list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
  {"section": "S2", "id": "<…>", "why": "<…>", "proposed": null}
 ]
}
```

`proposed` stays `null` unless the id is `none-fits`. One row in
`doctrine/section` for every section the record numbers — no section skipped,
none invented.
