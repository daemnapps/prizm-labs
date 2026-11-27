---
name: review-request
description: File a review request from this session in one call — "ask the email lead to review this", "put this up for review", "file a review request", "who still owes me a verdict on this", "is that review accepted yet". Writes the record into the repo and commits it; posts to the review API instead when a review key is in the environment. Never handles a secret from a file.
---

<!--
LEAD, INSTALL THIS AS `.claude/skills/review-request/SKILL.md`.

This is the SKILL half of RV-2 (review request module), shipped here because
`.claude/**` is maker-forbidden by every ai-workspace dispatch — the same split
PV-1 (personal-view skill) was carded with, and the same reason the vt-multiuser
skill card is lead-executed (maker builds the engine, lead writes the skill).
Install it byte-for-byte:

    mkdir -p .claude/skills/review-request
    cp new-workflow-design/builds/review-component/skill-review-request.SKILL.md \
       .claude/skills/review-request/SKILL.md

RV-2 (review request module)'s declared test asserts the installed copy is
identical to this draft and that its documented call matches the module's real
signature, so the two can never drift silently. Per `.claude/skills/CLAUDE.md`,
run it once on a real example and note it in the commit message
(`tested: <example>`). Delete this comment block on install if you prefer;
the test compares the two files only when both exist.
-->

# /review-request — put something in front of a named reviewer

> **Activates component:** `components/review (through components/run-kit)` — files a review request.


External dependencies (greppable): `components/review/review_request.py`
(the module, RV-2 (review request module)), `platform/data/kinds/review.json`
(the frozen grammar, RV-1 (review kind manifest)),
`platform/data/records/review/` (the plane it writes to).

A REVIEW REQUEST is one record on the `review` kind pointing at an asset by
warehouse pointer, naming who is asked. Status is never stored — it is FOLDED
from the records every time it is read, so there is nothing to keep in step.

## Steps

1. **Know who is asking.** The requester is the person in this session:
   the team/people/<id>/ whose identity.json lists `git config user.email`
   (`python3 components/run-kit/run_kit/people.py whoami`; never the address's local
   part, LD-77 (one person resolver)). If it refuses, ask — never guess a name
   onto a record.
2. **Name the asset by pointer, not by paste.** `warehouse` is one of
   `repo` (a path in this checkout), `drive`, `blob`, `supabase`, `url`; `ref`
   is the path / file id / url; `title` is what the reviewer is being asked to
   judge, in their words. Media bytes never travel on the plane (workspace
   rule 3).

   **A LINK IS `url`, NEVER `blob`** (the developer, ruled 2026-09-10, card RV-34).
   `blob` means *a capture WE MADE and hold*; `url` means it lives somewhere
   the platform does not own — a Figma file, a Netlify preview, any link — and
   `ref` is the url itself, **tracking params stripped**. Filing a Figma link
   as `blob` is a lie about provenance that nothing catches, which is exactly
   why the word was ruled.

   **A url has no `at`.** The ref pair is repo-only and stays repo-only: a
   deploy preview redeploys on every push and a Figma file changes under you,
   so version binding for a link is the CAPTURE (RV-35 (page capture)), never
   a commit. An `at` beside a `url` is refused by name.

   **`viewport` is optional and absent means UNSTATED.** Add
   `"viewport": "mobile"` or `"desktop"` to the asset when the width matters —
   it is what the thing was meant to be read at. Omit it and nothing is
   assumed; it is never defaulted to `desktop`, and a third word is a ruling,
   not a filer's move.

   ```python
   asset={"warehouse": "url",
          "ref": "https://deploy-preview-42--Brand B.netlify.app/",
          "title": "Brand B PDP — preview 42",
          "viewport": "mobile"}      # optional; omit to leave it UNSTATED
   ```
3. **Write the ask in four lines.** The reviewer opens this with no prior
   context and has about ten seconds. Answer, in this order, one line each:

   ```text
   What this is: <the asset in plain language — no ids, no build words>
   Why you: <why it reached this person and not someone else>
   What I need: <the act you want — and what you are NOT asking them to judge>
   What ends your part: <the response that completes their part>
   ```

   The four lines are a **CONVENTION in the `notes` field, never a schema**.
   `notes` already exists on every record, is REVIEWER-FACING always, and the
   panel renders it `white-space: pre-wrap`, so the lines survive to the
   screen. Nothing refuses a request that skips one — a missing line is a
   worse ask, not an error — and there is no `{what, why, need, ends}` field
   to fill in: adding one would be a ruling, not a filer's move.

   Two lines are worth care. **"What I need" carries its own negative** — the
   half nobody writes and the half that saves the most time. **"What ends your
   part" must stay honest**: while no surface writes a close on either path,
   name the person who will close it, never an automatic step.

4. **File it in one call.** Run exactly:
   ```python
   import sys; sys.path.insert(0, "components/review")
   from review_request import file_request

   # step 3's four lines, composed. This example is the 2026-09-08
   # QG-2 (gate calibration) request re-authored — same asset, same
   # reviewers, same declared fields, only `notes` changed.
   ask = "\n".join([
       "What this is: the first real request on the new review tool — the "
       "document behind it records fixing an automated checker's own rules, "
       "not a page. It is testing infrastructure.",
       "Why you: you are the first person through this surface, and the panel "
       "needs one real record in front of a real reviewer.",
       "What I need: open it, use approve or fix, and tell me what was "
       "confusing about the experience. I am NOT asking you to judge the "
       "assertion logic in the document — those are the QC runner's internals.",
       "What ends your part: you leave any verdict. Nothing closes "
       "automatically; I close it by hand.",
   ])

   out = file_request(
       asset={"warehouse": "repo", "ref": "brands/Brand B/email-sms/sept-2.md",
              "title": "September send 2 — copy"},
       type="md",                     # text | md | image | video | doc | link
       reviewers=["the email lead"],           # who is ASKED
       lane="email-sends",            # a label, never a gate
       requested_by="the developer",           # who is asking — required, never defaulted
       due="2026-09-10",              # optional
       on_accept=None,                # optional {action: …} — RV-3 (on_accept adapter) files it
       notes=ask,                     # the requester's own words, four lines
   )
   print(out["item"], out["route"], out["path"])
   ```
   `route` says which door it went through: `git` (the record was written into
   `platform/data/records/review/` and committed for you) or `api` (POSTed to
   `/api/review`, because a review key was in the environment). You never
   choose, and you never handle the key.
5. **Push if it went through git.** The module commits the one record file and
   nothing else; pushing is yours: `git push origin main`. If the pre-commit
   hook blocks, do not bypass it — report the message. Nothing to push on the
   `api` route; that record is already on the plane.
6. **Read state by folding, never by looking for a status field.**
   ```python
   from review_request import read_records, list_open, latest_verdicts, is_accepted

   list_open(reviewer="the email lead")                    # what is waiting on the email lead
   recs = read_records(item=out["item"])          # one request's records
   latest_verdicts(recs)                          # {reviewer: their latest verdict}
   is_accepted(recs)                              # True only for decision: accepted
   ```
   No close = open; the latest close wins; one verdict per reviewer, their
   last. `is_accepted` is False for `rejected`, for `parked`, and for a request
   nobody has closed — those are three different states.

## Never
- Never put construction reasoning in `notes`. Why the record was built the way
  it was — why no `on_accept`, why two reviewers, what the worker does next —
  has four homes already: the session's own commit message, its
  `team/plans/dev-*.md` batch, `the-org/decision-log.md`, and the build folder.
  `notes` is the reviewer's field and holds the ask, nothing else. That
  collision is exactly how QG-2 (gate calibration) failed on 2026-09-08: a
  real reviewer opened the one live request and could answer none of the four
  questions.
- Never add a field for the ask. The four lines ride in `notes` on purpose — a
  structured `{what, why, need, ends}` field is a RULING (the kill-condition on
  this convention), never a filer's or a maker's move.
- Never read a key from a file or ask anyone to paste one. The module reads
  `REVIEWER_KEY_TEAM` from the environment and nowhere else.
- Never write a `status` onto a record — status is folded, always.
- Never re-implement the fold. Import it; RV-3 (on_accept adapter),
  RV-6 (reference panels) and RV-10 (PM review integration) all read this one.
- Never invent a field beyond the frozen grammar. A missing field is a ruling
  to ask for, not a key to add.
