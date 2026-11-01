# marketing-chain-checks (folder: quality-checks) — the checks every marketing chain runs, and the checks on the chains themselves

**marketing-chain-checks** — takes a finished piece of work and the facts it must agree
with, makes a list of problems and a `check.json`, and **holds** failing work.
Does not fix anything and does not approve anything — a person reviews. Triggered
by importing it (`import marketing_chain_checks as Q`).

**Renamed 2026-10-02** from `components/quality-checks` (the owner: *"we need to
name this thing something else … call it marketing chain checks"*). The old name
sat beside the developer's `components/qc-checks`, a different component. A tombstone at
the old path forwards `import quality_checks` until every caller has moved.

**Owner:** the owner (engine and definitions). Built 2026-09-20, rollout Step 0c,
lifted from `tools/email-production/simple_email.py`. **Not the developer's
`components/qc-checks`** — a separate component, kept separate by SD-2 (qc
shared truth); no code here calls it.

| Word | What it is | Stops anything? |
|---|---|---|
| **Check** | one question of one piece of work; reports what's wrong and where | no |
| **Gate** | a fixed point in a chain where checks run | **yes** — `hold()` raises `Held` |
| **Review** | a person's verdict | yes — the final say |

**The five gates, the same in every chain** (`GATES`): inputs · elements · copy ·
media · delivery.

**Checks today:** `price_check` · `unfilled_check` · `read_check_block` (the
copy-check step: product facts, chopped thoughts, typos — prompt in
`prompts/copy-check-v1-damon.md`) · `elements_check` (against `components/elements`) ·
`draft_product_check` · `money_path_check` · `subject_check` · `partner_check`.

**The four questions:** engine + owner — `marketing_chain_checks/`, the owner · definitions —
the checks and `prompts/`, the owner · plane — `check.json` inside the CALLER's run
folder · manifest — `{gate: {result, problems[]}}`.

Tests: `python3 test_marketing_chain_checks.py` · `python3 test_viewer.py`.

## Two layers of checks (the owner, 2026-10-02)

*"We're doing a lot of checking over our system so that the system learns.
There are internal checks as it goes through its actual loop, and then there's
also the higher-level check to make sure the loop itself is actually working
and updated."*

**1. In-loop checks — on every piece of work, as it moves through a chain.**
The hold and the five gates · price, unfilled and copy checks · the creative
review after every stage (`review.py`) · the viewer check after the writing
(`viewer.py`). They stop or send back one ad.

**2. Loop checks — on the chain itself: is it working, and is it current?**
Built: the QC log (`qc_log.py`) files every round beside the run, and a cause
that would recur is written back as a chain change (`qc_log.py fix`, `tally`).
Not built yet: the same viewer complaint across several briefs turning into a
prompt change on its own · the viewer check's calls measured against live Meta
results · a check that a chain's prompts and avatar files are the current ones.
Checks on the system that live elsewhere, other owners: `/system-review`
(does a folder follow the workspace rules), the control room's machine check.

## The creative QC loop — every tool, every stage (2026-10-02)

the owner: *"i want this kind of creative QC process installed for each of my
production tools because this is going to actually make it work … not just the
production folder but this should exist for all stages in the creation process."*

The same five steps everywhere:

1. **Machine checks** — the tool's own gates (`hold()`, `check.json`, `qc.py` …).
2. **The review** — `marketing_chain_checks/review.py`: a model reads the stage's output
   against what it was given and the stage's hard bars, and returns findings per
   item (`ok`, `severity` BLOCKER/FIX/NOTE, `problems`, `fix_at`, `prompt_change`).
   What each stage is compared against and its bars: `definitions/stages.json`
   (12 tools). The reviewer's words: `prompts/creative-review-v1-damon.md`.
3. **The log** — `marketing_chain_checks/qc_log.py`: every round filed beside the run,
   `<run>/qc-log/QC-LOG.md` + raw findings. Nobody writes a row by hand.
4. **The fix** — at the stage that caused it; a cause that would recur becomes a
   chain change, written back into the row (`qc_log.py fix`).
5. **Re-make** — only what failed, then QC again.

**Where it is called (one line each, after the stage writes its output):**
video-teardown `run_stage` (every teardown and writing stage) · copywriter
`run_stage` · email-production `run_stage` · run-kit `Chain.run` (so every chain
built on run-kit — ad-variations and the lab chains) · video-production
`run.py` (the picture review after every batch, plus `qc.py`) · image-edit
(its compare judge's verdicts filed as the round) · video-edit (six frames of the
finished cut against the cut sheet) · marketing-calendar `run_ai` · meta-upload
(the sheet) · intake (the record).

A review never stops a run on its own and never hides: one that cannot run is
filed UNCHECKED. A tool's own tests never spend on a review. Off: `QC_REVIEW=0`.

## The viewer check — the last step after writing (2026-10-02)

the owner: *"slide this into the chains and lets ride it."* From Andrei Lunev's
"Toilet Mike". `marketing_chain_checks/viewer.py`: the finished brief is translated into
what a viewer sees (`prompts/viewer-cut-v1-damon.md`), dropped among 9 real posts
from its avatar's feed (`VIEWER_FEEDS`; default `components/swipe-organic/records/avatar-feeds/`), and
scrolled by 5 fresh viewers built from the avatar profile
(`prompts/viewer-card-v1-damon.md`, cached in `records/viewer-cards/`; reads
`prompts/viewer-check-v1-damon.md`). **The viewers only react; code scores**
against the real posts, so "looks real" is never a score. A fail returns a role
(openings · middle · giveaway · close · audience) that each chain maps to its
own step. Called from video-teardown `run.py` (`viewer_gate`, last stage-5 gate,
and `_agent_stage.py done`) and image-teardown `tools/run.py` (`viewer_step`).
Not yet on landing pages. Gemini first, OpenAI when Gemini refuses. Off:
`QC_VIEWER=0`. Page: VIEWER-CHECK.md · `viewer-check.html`

## The viewer chain (2026-10-02) — the viewer check and the phone checks as one run

`viewer_chain.py <brief> --brand --avatar [--sub] [--kind] [--frames] [--label]` runs
card → cut → feed → 5 viewers (v2) → objections (matched to the brand's
objection bank, bank answer quoted; the viewers never see the bank) → score →
route → hidden by the app (frames) into `runs/viewer-check/<brand>/<label>/` and
rebuilds `runs/viewer-check/INDEX.html`.
Where eyes go, keep watching and the face wait for install. See VIEWER-CHAIN.md.

## Claude only (the owner, 2026-10-03: "we can just use claude for this")

The viewer chain uses Claude and nothing else by default (`QC_VIEWER_ENGINE=claude`).
It tries headless Claude on your own plan first. When that isn't signed in, every
question is written as a numbered `*.prompt.md` in `<run>/viewer-chain/hand/` (or
`VIEWER_HAND_DIR`), and the run waits for `*.answer.md` beside it. **A session running
briefs answers them:** run the chain or chain stage in the background, then hand each
pending prompt to a fresh subagent ("read this file, do exactly what it asks, write
only your answer to the .answer.md"). The 5 viewer prompts go to 5 separate
subagents at once. Never answer two prompts from one context: a viewer must not see
another viewer, the brief or the bank. Gemini/OpenAI run only with
`QC_VIEWER_ENGINE=gemini`.
