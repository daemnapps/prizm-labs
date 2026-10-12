# marketing-chain-checks (folder: quality-checks)

Renamed from **quality-checks** on 2026-10-02 (the owner: *"call it marketing chain
checks"*). The code is `marketing_chain_checks`; `import quality_checks` still
works and forwards to it.

The checks every marketing chain runs, and the checks on the chains themselves.
It takes a finished piece of work and the facts it must agree with, makes a list
of problems and a `check.json`, and **holds** failing work. It fixes nothing and
approves nothing — a person reviews.

    import marketing_chain_checks as Q
    problems  = Q.price_check(text, Q.offer_block(bank_text, offer), offer)
    problems += Q.unfilled_check(text)
    problems += Q.read_check_block(check_step_output)
    Q.hold("copy", problems, run_dir)        # writes check.json; raises Q.Held if anything failed

| Word | What it is | Stops anything? |
|---|---|---|
| **Check** | one question of one piece of work | no |
| **Gate** | a fixed point in a chain where checks run | **yes** — `hold()` raises `Held` |
| **Review** | a person's verdict | yes — the final say |

The five gates, the same in every chain: inputs · elements · copy · media · delivery.

## Two layers of checks (the owner, 2026-10-02)

*"There are internal checks as it goes through its actual loop, and then there's
also the higher-level check to make sure the loop itself is actually working and
updated."*

1. **In-loop** — on every piece of work: the hold and the five gates · price,
   unfilled and copy checks · the creative review after every stage
   (`review.py`) · the viewer check after the writing (`viewer.py`).
2. **On the loop** — on the chain itself: the QC log (`qc_log.py`) files every
   round beside the run, and a cause that would recur is written back as a chain
   change (`qc_log.py fix`). Not built yet: the same viewer complaint across
   several briefs turning into a prompt change on its own · the viewer's calls
   measured against live Meta results.

## The creative QC loop — every tool, every stage

1. **Machine checks** — the tool's own gates (`hold()`, `check.json` …).
2. **The review** — `marketing_chain_checks/review.py`: a model reads the stage's
   output against what it was given and the stage's hard bars, and returns
   findings per item (`ok`, `severity` BLOCKER/FIX/NOTE, `problems`, `fix_at`,
   `prompt_change`). What each stage is compared against, and its bars:
   `definitions/stages.json` (12 tools; the picture stage carries a 14-line
   inventory). The reviewer's words: `prompts/creative-review-v1-damon.md`.
3. **The log** — `marketing_chain_checks/qc_log.py`: every round filed at
   `<run>/qc-log/QC-LOG.md` + raw findings. Nobody writes a row by hand.
4. **The fix** — at the stage that caused it.
5. **Re-make** — only what failed, then QC again.

    from marketing_chain_checks import review
    review.after_stage("copywriter", "stage6-hooks", run_dir, output=…, sources=[…])

A review never crashes its caller: one that cannot run is filed UNCHECKED. A
tool's own tests never spend on a review. Off: `QC_REVIEW=0`. Needs
`GEMINI_API_KEY`.

## The viewer check and the viewer chain

The last check after the writing: the finished brief is dropped into its
avatar's real feed and scrolled by 5 fresh viewers built from the avatar profile.
The viewers only react; code scores. See **VIEWER-CHECK.md** (the check) and
**VIEWER-CHAIN.md** (the standalone run: check → rewrite → re-check → learn).

    python3 viewer_chain.py <brief> --brand <b> --avatar <core> [--sub <sub>] [--kind video|"still image"|carousel] [--frames <dir>]

It reads from your brand folder: `core-avatars/<avatar>/profile.md` (and
`sub-avatars/`), the objection banks (`core-avatars/objection-bank.md`,
`customer-experience/objection-bank.md`, `offers/objection-answers.md`), the
language bank (through `tools/language-layer`), and each avatar's real feed
(`VIEWER_FEEDS`). What it learns is kept in `records/` (yours; not shipped).

## Tests

    python3 test_marketing_chain_checks.py     # the checks, the hold, the review, the log
    python3 test_viewer.py                     # the viewer check's scoring, routing, rewrite rules

29 tests, no network, no model.
