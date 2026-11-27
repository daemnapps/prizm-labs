**No example in this prompt is an answer.** Any id, name or phrase shown below
as an illustration of the SHAPE of a reply is a placeholder — never copy it
into your answer because it appeared here. Every id you write must be copied,
character for character, from the candidate lists you are handed further down.
An id that is not on its list is refused by the code that reads your reply, so
a guess is worse than saying nothing fits.

Here is the complete teardown of one static image ad: {teardown_record}

Here are the candidate rows — the only ids that exist — one list per label:
{element_candidates}

Your job is to LABEL this ad: say which library row it IS, on four lists.
You are not judging the ad, not improving it, and not describing it again.
Label the SOURCE ad as the teardown records it — nothing about any brand that
might later rebuild it.

The four labels:

1. `format/image` — the kind of static ad this is: the device the whole frame
   is built around.
2. `style/image` — the photographic or graphic register the picture is made in.
3. `framework/all` — the argument shape the copy follows, read from the copy
   in the order a viewer reads it.
4. `doctrine/awareness` — the awareness rung the ad speaks to. The teardown
   names the ad's market state; take the rung from what it recorded, and map
   it onto the list's ids.

Rules, in order of importance:

- **One id per label, from that label's own list.** An id from the wrong list
  is a wrong answer.
- **Match on what the row says it IS** (its `what`), not on its name sounding
  close. Two rows can sound alike and describe different devices.
- **When no row fits, say so.** Write `none-fits` as the id and give
  `proposed`: one line, in the form `new-id — Name — what it is in one
  sentence`, written brand-free so it could describe any advertiser's ad. A
  forced fit corrupts the library; `none-fits` grows it. Never bend a row to
  avoid writing `none-fits`.
- **`why` is evidence, not opinion.** One sentence that points at something
  the teardown actually recorded — a zone, a line of copy, a described
  treatment — that makes this row the match. No brand, product or person
  names in `why` or in `proposed`: describe the function ("the advertiser's
  product", "the speaker").
- If the teardown does not contain enough to decide a label, that label is
  `none-fits` with `proposed` set to `undecidable — ` and what was missing.

Reply with ONE fenced block, tagged `ELEMENTS`, holding valid JSON with exactly
these four keys, and nothing before or after it:

```ELEMENTS
{
 "format/image":       {"id": "<an id from the format/image list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "style/image":        {"id": "<an id from the style/image list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "framework/all":      {"id": "<an id from the framework/all list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null},
 "doctrine/awareness": {"id": "<an id from the doctrine/awareness list, or none-fits>", "why": "<one sentence of evidence>", "proposed": null}
}
```

`proposed` stays `null` unless the id is `none-fits`.
