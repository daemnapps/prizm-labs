# Stage 0e — hold every line to the brand's own claim rules (v1)

the owner, 2026-09-23: "I really need to get this moving … clean up anything else so I
can just get to printing." Every spoken and on-screen line must stay inside what
the brand is allowed to claim. The rules are the brand's own product files below:
the Claims section (allowed and forbidden) and any known-issues note. You fix only
the words that break a rule, with the brand's allowed wording. Nothing else changes.

## The brand's claim rules

{claim_rules}

## The lines

{lines}

## For each line

- If it breaks a rule (a forbidden word, a claim beyond the allowed phrasing, a dated
  result promise, a clinical term, a phrase the known-issues note flags), rewrite
  ONLY the breaking words using the allowed wording. Keep the line's voice, rhythm
  and meaning as close as you can.
- If it's fine, leave it out of your answer.

## What you return

JSON only:

```
{"fixes": [{"id": "<line id>", "was": "<the breaking words>", "now": "<the whole line, fixed>", "rule": "<the rule it broke, quoted from the files>"}]}
```
