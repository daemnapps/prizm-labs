# Objection match — {brand} · {avatar} (v1)

Real people from this avatar just watched an ad and told us, in their own words,
what they doubted, what felt like a sales pitch, and what they would comment.
Below that is the brand's objection bank: the objections real customers have
raised before, with the answers the brand has on file.

Your job: match each thing a viewer said to the objection in the bank it is the
same worry as, and copy the bank's own answer for it.

Rules:
- Quote the bank exactly. Copy the objection and the answer word for word,
  with the heading or line they sit under. Never write a new answer.
- If nothing in the bank is the same worry, say "not in the bank". That is a
  finding, not a failure, and it means a new objection we have no answer for.
- If the bank holds an objection but no answer to it, say "no answer on file".
- One match per thing said. Don't stretch: a worry about price is not a worry
  about results.
- Then predict the 3 comments most likely to show up under this ad, each tied
  to a matched objection (or to "not in the bank").

Return JSON only:
{"matches": [{"viewer": 1, "said": "<their words>", "kind": "doubt|pitch|comment",
  "objection": "<bank objection, verbatim, or 'not in the bank'>",
  "where": "<heading or line it sits under>",
  "answer": "<bank answer, verbatim, or 'no answer on file'>"}],
 "likely_comments": [{"comment": "<as a viewer would type it>", "objection": "<bank objection or 'not in the bank'>"}],
 "new_objections": ["<worries the bank doesn't hold, in the viewers' words>"]}

--- WHAT THE VIEWERS SAID ---
{said}

--- THE OBJECTION BANK ---
{bank}
