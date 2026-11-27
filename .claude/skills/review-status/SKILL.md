---
name: review-status
description: Read the state of any review without opening the PM tool — "where is RQ-…", "what reviews are waiting on me", "who still owes a verdict", "what's open in the static-ads lane", "show me the review queue", "/review-status". Answers as a table in this conversation, or as a published page with --artifact. READ-ONLY — it files nothing, closes nothing, and never writes a verdict.
---

# /review-status — the state of a review, without a dashboard

> **Activates component:** `components/review (through components/run-kit)` — reads a review's status.


External dependencies (greppable): `components/review/review_request.py`
(the module and THE FOLD, RV-2 (review request module)),
`platform/data/kinds/review.json` (the frozen grammar,
RV-1 (review kind manifest)), `platform/data/records/review/` (the records
this reads).

Companion to `/review-request`, which FILES. This one only READS. If you find
yourself wanting to write, stop and use `/review-request` — the split is the
point, and a read skill that files is how a reader becomes an actor nobody
audited.

**STATUS IS NEVER STORED. IT IS FOLDED FROM THE RECORDS EVERY TIME.** There is
no status field to read and nothing to keep in step. Every number this skill
prints is derived at the moment you ask.

## Steps

1. **Know who is asking.** The person in this session is
   the team/people/<id>/ whose identity.json lists `git config user.email`
   (`python3 components/run-kit/run_kit/people.py whoami`; never the address's local
   part, LD-77 (one person resolver)). Use it for "waiting on me" questions. If it
   refuses, ASK — never guess a name onto a
   query whose answer someone will act on.

2. **Pick the route, and say which one you used.** The module decides:

   - a `REVIEWER_KEY_TEAM` in the environment → the API, which sees records
     this clone may not have yet;
   - no key → the files in this clone, which is the record itself
     (never-flex 2: git is the write path AND the record).

   These can disagree, and the disagreement is information: a clone behind
   origin reads a stale plane. **Say which route answered.** Never read a key
   from a file and never ask anyone to paste one — the module reads
   `REVIEWER_KEY_TEAM` from the environment and nowhere else.

3. **Ask the module, never re-implement it.** Import and call; do not
   re-derive a fold in this skill or in a scratch script.

   ```python
   import sys; sys.path.insert(0, "components/review")
   import review_request as rr

   recs  = rr.read_records()                    # every record in the clone
   one   = rr.fold(rr.read_records(item="RQ-…"))  # ONE item -> its whole state
   open_ = rr.list_open(recs)                   # every open request, folded
   mine  = rr.list_open(recs, reviewer="the developer")   # open and asked of one person
   lane  = rr.list_open(recs, lane="static-ads") # open in one lane
   who   = rr.latest_verdicts(rr.read_records(item="RQ-…"))  # {reviewer: record}
   ```

   `fold()` returns: `item`, `status`, `request`, `request_notes`,
   `requested_by`, `reviewers`, `verdicts`, `seen_by`, `close`, `decision`,
   `accepted`, `created`, `records`.

4. **Answer as a table.** One row per item, these columns:

   | item | type | reviewers | verdicts standing | close rule | status |

   - **verdicts standing** — `2/3 approve, 1 pending` style, counted against
     the DECLARED reviewers only. A reviewer who voted twice has ONE vote,
     their latest; the fold already did that.

     **COUNT HUMAN REVIEWERS AND MACHINE REVIEWERS SEPARATELY, ALWAYS.**
     `verdicts` is keyed by whoever filed, and that includes the machine:
     `claude-prereview` files a verdict on items a person has not touched, and
     it is routinely the ONLY key there. A count that treats it as a vote reads
     `1/1 voted` on an item NOBODY HAS REVIEWED — wrong in the direction that
     makes unreviewed work look reviewed, which is the only direction that
     matters. Verified live 2026-09-16: all six then-open items had exactly one
     verdict each, every one of them `claude-prereview`, every one carrying
     `decision: None`, with the declared human reviewer still pending. Say
     `0/1 human, prereview filed` — never `1/1`.

     A verdict whose `decision` is `None` is NOT a decision. The prereview
     files observations; a decision comes from a reviewer who made one.
   - **close rule** — how this item ends, so a reader knows what is missing,
     not merely that something is.
   - **status** — `open`, or the closed decision. `accepted`, `rejected` and
     `parked` are THREE DIFFERENT STATES and only `accepted` starts
     RV-3 (on_accept adapter)'s next run. Never collapse them into
     "closed".
   - A `seen` record means a reviewer OPENED the request. It carries no
     judgment and closes nothing — never show it as a verdict.

5. **For one item, go deeper than the row.** Show the ask (the requester's
   four lines live in `notes`, by convention — there is no structured field
   and adding one is a ruling, not a move you make), each reviewer's latest
   verdict with its words, and what is still outstanding. Name the asset by
   its pointer (`warehouse` + `ref`), never by pasting bytes.

6. **`--artifact` publishes the same table as a page.** Same content, same
   derivation — publish the way `/personal-view --artifact` does. Use it when
   the answer is for someone else to read or keep; a table in this
   conversation is the default and usually enough.

## Never

- **Never file anything.** No verdict, no close, no `seen`, no request. This
  skill has no write path and must not grow one.
- **Never re-implement the fold.** Import it. RV-3 (on_accept adapter),
  RV-6 (reference panels) and RV-10 (PM review integration) all read the same
  one, and a second implementation is how they start to disagree.
- **Never write or infer a `status` onto a record.** Status is folded, always.
- **Never invent a field beyond the frozen grammar.** A missing field is a
  ruling to ask for, not a key to add.
- **Never hard-code a brand, a lane, or a person.** Every one of those is an
  argument (workspace rule 7). Identity comes from `git config user.email`.
- **Never report a count without its route.** "3 open" from a stale clone and
  "3 open" from the API are different claims.
