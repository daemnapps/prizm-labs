You are coding one finished video teardown into fixed values, so that every
video a brand has posted can be counted the same way. You read; you do not
judge. Every example below is illustrative — none of it names a real brand.

Here is the teardown record (the objective record, the shot table, the
verbatim transcript, the voices):
{teardown_record}

Here is the replication spec written from it:
{replication_spec}

Here is the doctrine read, as filed:
{doctrine_json}

Here are the variables to code. Each line is `key — what it means — allowed
values`. For a categorical key, give one of the allowed values exactly as
written. If none fits, write `other: <two to four words>` — never force the
nearest value; a new value is how the list learns. For a numeric key, give a
number of seconds or a count, or `null` if the record does not show it. For a
text key, quote the record's own words.
{coder_vocabulary}

Rules:
- Read only what the record shows. If the record does not show a thing, the
  value is `null` and the evidence says "not in the record".
- Seconds come from the shot table's timestamps or the transcript's T-number
  times — never estimated from pacing prose.
- "Product" means the thing the video sells. A competitor's product in frame
  is not it.
- The lead is the person with the most screen time speaking; if nobody
  speaks, the person with the most screen time.

Return one fenced json block and nothing else:

```json
{
  "codes": {
    "<key>": {"value": <value>, "evidence": "<the row time or T-number and a few quoted words>"}
  }
}
```
