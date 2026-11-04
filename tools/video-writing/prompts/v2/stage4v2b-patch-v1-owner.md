<!-- writing v2 (2026-10-21): pass B PATCH v1 — the audit's RE-RUN BUILD answered by a patch, not a rebuild (video-system sync W32). The same full audit reads the patched script afterwards; nothing here judges. -->

# Writing v2 · pass B — the patch the audit asked for

The audit read the script below and sent it back with numbered fixes. Make **exactly those fixes and
nothing else**. Every line the audit did not name stays byte for byte as it is — the words, the order,
the markers, the tables, the part headers. You are not rewriting the script; you are correcting the
lines the audit pointed at. The same full audit reads the result again afterwards.

Here is the script as it stands — the build pass's whole answer, its three parts marked
`=== PART n: NAME ===`:

{build_output}

Here is the audit's verdict and its numbered fixes, in its own words:

{audit_fixes}

Here is THE LANE this piece runs on — it changes only the ask:

{ask_lane}

## How to answer

For each fix, print one block, in the order the audit numbered them:

```
=== FIX <the audit's number or label> ===
PART: <PLACEMENT · EXPANSION · CLOSE — the part the lines are in>
FIND:
<the exact lines to change, copied character for character from the script above — enough whole lines
that they appear ONCE in the script>
REPLACE:
<the corrected lines>
=== END ===
```

Rules:

1. **FIND is a copy, never a paraphrase.** Copy whole lines out of the script exactly, spacing and
   punctuation included. A FIND that does not appear in the script, or appears more than once, makes the
   machine throw the whole patch away and rebuild the pass instead.
2. **REPLACE changes only what the fix names.** Keep everything else in those lines as it was.
3. **One fix may need several blocks** (the same mistake in two places): give each its own block, with the
   same number.
4. **A fix that needs a fact the files do not hold** is written as a `[RESEARCH: what is needed]` marker in
   REPLACE, exactly as the build pass would write it — never an invented number, name or price.
5. **Every rule of the build pass still holds** for the lines you change: the swipe's structure, the
   lane's last ask, every rung carries the product, claims only from the brand files.
6. Print the blocks and nothing else — no commentary before or after them.
