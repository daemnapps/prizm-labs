---
name: qc-check
description: Run a quality check on a file, folder, or review request from this conversation and get the findings back here — "check this copy", "qc this page", "check the face scrub copy for Brand B", "run the text check on this folder", "/qc-check <path>". Answers as a table, publishes the page only on request, and files to the review plane only when asked. Never files anything you did not ask it to.
---

# /qc-check — check something, get the answer here

> **Activates component:** `components/qc-checks` — `text_check.py` and the other checks.


External dependencies (greppable): `components/qc-checks/text_check.py` (the
engine, UQ-1 (portable bundle)), `new-workflow-design/builds/upright-qc/
findings-bundle-contract.md` (the output contract),
`components/review/review_request.py` (the filer, RV-2 (review request module)),
`platform/data/kinds/review.json` (the frozen grammar).

Companion to `/review-status`, which reads. This one RUNS a check. It runs the
SAME ENGINE the worker runs on a tick (UQ-4 (prereview text check)) — there is
one checker, and a second opinion from a different code path is not a feature.

## Steps

1. **Know who is asking.** The person whose team/people/<id>/identity.json lists
   `git config user.email` — `python3 components/run-kit/run_kit/people.py whoami`
   prints the id, never the address's local part (LD-77 (one person resolver)).
   It becomes `--by`, and lands in the bundle's `run.by`. If it refuses, ASK —
   the record says who asked and a guess there is a lie.

2. **Name the asset. There are three shapes and only three.**

   | you have | pass | note |
   |---|---|---|
   | a file in this checkout | `--text-file <path>` | add `--html` if it is built HTML rather than authored text |
   | a folder | loop the files yourself, one call each | the engine checks ONE asset per call; there is no folder flag |
   | a live page | `--item <RQ-…>` | **only through an existing review request** — see the limit below |

   **THE ENGINE WILL NOT READ OUTSIDE THE CHECKOUT.** A path it cannot express
   as a repo asset is refused as `asset-not-in-checkout`, by design. Copy the
   thing into the tree or check it where it lives; do not work around it.

   **THE URL LIMIT, STATED BECAUSE IT WILL BITE:** there is no "check this
   URL". `page_capture.capture()` takes a review RECORD, not a url, so a live
   page is checkable only when a review request already points at it. If
   someone hands you a bare link, say so and offer to file the request first
   (`/review-request`) rather than inventing a path.

3. **Run it into the scratchpad, never into the repo.**

   ```
   python3 components/qc-checks/text_check.py \
     --text-file <path> [--html] [--brand <brand>] [--no-grammar] \
     --by <who> [--item RQ-…] --out <scratchpad>/qc/<slug>
   ```

   Two files come back: `findings.json` and a self-contained `findings.html`.
   **`--out` writes nothing into the repository** — put it in the session
   scratchpad. A check is not a commit.

   **`--out` REQUIRES `--item`. VERIFIED, NOT ASSUMED** — the engine exits with
   `--out with --text-file needs --item RQ-…`. There is no such thing as a
   local-only bundle, and the reason is sound: a bundle's records are review
   records keyed by their item, so a bundle without one could never be filed as
   a copy. **To look without an item, use `--dry-run`**, which prints the
   findings and writes nothing. `--dry-run` is the "just tell me" mode;
   `--out` is the "this is filable" mode. Note the consequence: there is no
   `findings.html` without a review request.

4. **`--brand` is an argument, always.** The dictionary lives at
   `brands/<brand>/qc-dictionary.json`. Never hard-code a brand (workspace
   rule 7). If no dictionary exists for that brand the run still works — the
   dictionary-backed checks are SKIPPED and the strip names each one. Say which
   checks were skipped; a check that did not run is not a check that passed.

5. **Answer here, as a table**, one row per finding:

   | class | quote | check | proposed fix | truth |
   |---|---|---|---|---|

   - **class** is `hard-stop` or `taste`, and it is the FIRST column because it
     is the first thing the reader must know (UQ-8 (severity per finding)).
     Write `taste` findings as **advisory** — "worth your eye" — never as
     something that failed. A `taste` finding BLOCKS NOTHING: it does not make
     a page un-shippable, it does not make the run un-clean, and it is never
     counted into a "N problems" headline alongside hard-stops. Count the two
     classes separately or the advisory ones teach people to ignore the check.
   - **Where the class lives, verified:** with `--out`, it rides in the
     record's `reasons[]` as `hard-stop` or `taste`. With `--dry-run` there are
     no records, so read it off the anchor's `_classification` — **absent means
     `hard-stop`**, which is the engine's default and not a missing value.
   - **quote** is the asset's own characters, with enough neighbourhood to find
     it. Never paraphrase it.
   - **truth** is the sha of the file the judgement rests on, from `truth[]`.
     **An empty `truth[]` is a real answer and must be said out loud** — it
     means nothing but the built-in rules was consulted.
   - Lead with the strip's own summary: how many findings **of each class**,
     `clean` or not, and **which checks were skipped and why**.
   - **A CLEAN RESULT IS A RESULT.** `clean: true` with no records means the
     asset passed what ran. Say what ran.
   - **A page whose only findings are `taste` passed.** Say it passed, then
     give the advisory rows. Reporting it as a failure is the exact regression
     UQ-8 (severity per finding) exists to prevent.

6. **`--file` files the bundle's records. Only when asked, and never by
   default.**

   ```python
   import sys; sys.path.insert(0, "components/qc-checks")
   import text_check
   text_check.file_findings("<out>/findings.json")
   ```

   It COPIES the records — never transforms them — which is why the bundle is
   the single source. The reviewer is the machine identity, never a person, and
   `run.by` already names who asked. Filing needs `--item RQ-…` on the run: a
   verdict record is keyed by its item, and a bundle without one is not
   filable. If there is no item, say the findings are local-only rather than
   minting an id.

7. **`--artifact` publishes `findings.html`. Only on request.** The file is the
   truth; a page is for people without the repo — the same rule design mocks
   run on. Default is the table in this conversation plus the local path.

## Never

- **Never file without being asked**, and never mint a review request to make
  filing possible.
- **Never re-implement a check.** One engine. A finding this skill produces
  that the worker's tick would not is a bug in one of them, not a feature.
- **Never hard-code a brand, a dictionary path, or a check list.** All
  arguments; the engine reads its own tables.
- **Never write into the repository** — `--out` goes to the scratchpad.
- **Never present a skipped check as a pass**, and never report findings
  without saying which truth files were read and which were absent.
- **Never claim a model-backed judgement when none ran.** Without a key,
  `--no-grammar` deterministic checks are what you have; say so in the reply.
- **Never let a `taste` finding read as a blocker**, and never merge the two
  classes into one count. The brand's dictionary lists seven `taste` phrases —
  the fade-dark-spots verbs, `hyperpigmentation`, `melanin`, `exotic`,
  `transform` — on a deliberate angle the brand is running on purpose. A check
  that refuses a page for using them would be wrong, and a QC nobody can
  overrule gets switched off.
