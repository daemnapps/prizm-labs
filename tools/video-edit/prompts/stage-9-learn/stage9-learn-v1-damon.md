# Stage 9 — learn from his changes (v1)

Damon reviewed an edit and changed things. Your job is to turn what he changed
into rules the next cut can follow, without over-reading one instance.

**Never invent an example.** Work only from the change log and the two cut
sheets you are given.

## What you are given

- `{changes}` — each change: what he asked for in his words, his reason if he gave one, which stop it was at
- `{before}` / `{after}` — the cut sheet before and after each change
- `{learned}` — the rules already on file

## What to do

For each change, write one row:

- `what_changed` — the measurable difference between the two sheets (a clip moved 0.5s later; caption look switched; a pause removed)
- `his_words` — quoted exactly
- `rule` — the general rule this points to, in one plain sentence a cutter could follow. If his reason is given, the rule comes from the reason, not from the numbers.
- `scope` — `this ad only` · `this format` · `this brand` · `every edit`. **Default to the narrowest scope the evidence supports.** One change is never `every edit` unless he said so.
- `seen` — how many times a change pointing to this same rule is now on file (count `{learned}` too)
- `conflicts_with` — any rule already on file that this contradicts. Do not resolve it; name it. The ruling is his.

A rule is only PROMOTED into `{learned}` for the cut prompt when `seen` is 2 or
more, or when he stated it as a rule himself. Until then it is filed as an
observation.

Return JSON: `{"rows": [...], "promote": [rule ids], "observations": [rule ids]}`.
