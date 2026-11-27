---
name: system-ready
description: Prepare one piece of work so others can use it — "get this ready for the email lead", "prep the story builder for integration", "/system-ready <folder>", "is this ready for someone else to run", "make the handoff pack", "what would the designer need to set this up", "is this ready to graduate", "can the mini run this", "run the mini check", "/system-ready <folder> mini", "what grant would this need", "get the copywriter onto the mini". Reads the target's `Runs by:` intent (absent = person) and reports a verdict PER LEVEL — L1 here, L2 another person, L3 the mini — with the mini checks mechanical: root, keys against env.template and the grant, the 3.9.6 interpreter, machine-bound literals, where output goes. Writes a readiness report that never blocks on cleanliness (only on a wall: a secret, a key by path, a write into a brand folder, oversize media), then the packet: plan, handoffs for the designer, the email lead and the owner, a twelve-line "how it works", an SOP draft, and the task block the email lead files. Writes only under its run folder; files nothing, rules nothing — except that on the lab owner's own "yes" it makes the move itself (git mv, readers, test, commit, push) and files its /system-review through components/system-integration/move.py.
---

# system-ready — so others can use it

> **Activates component:** `components/system-integration` — readiness packet for one folder.


Stage 2 of the three: `/system-fit` (the owner's own check) → `/system-ready`
(this) → `/system-review` (what already sits in the workspace). the developer,
2026-09-21: "the ultimate goal is to build things, and then set them up so
that they actually work as intended, including for others to use."

```
/system-ready <folder>      the readiness report, then the packet — always both
/system-ready <folder> --mini         file it for the mini's `system` lane; run nothing here
```

## Atlas, compiled fresh (ATL-53 (atlas daily), 2026-10-30)

The committed `platform/data/atlas/data.json` now refreshes once a day (the worker's refresh switch). Before this skill reads the atlas, compile it fresh for this run, and read that copy wherever this file names `platform/data/atlas/data.json`:

```
ATLAS_FRESH=$(mktemp -d)/data.json && python3 components/atlas/compile.py --out "$ATLAS_FRESH" --no-stamp
```

It takes about 30 s. The report says "atlas compiled fresh at <git rev-parse --short HEAD>". If the compile fails, say so and fall back to the committed copy, naming its age (`stat -f %Sm platform/data/atlas/data.json`).

## `--mini` — queue it on the mini's `system` lane instead (SI-15 (mini flag), 2026-09-30)

`/system-ready <folder> --mini` runs NOTHING here. It files ONE `system-check`
request and answers with its id and where the memo will land; the mini's
`system` lane (WM-114 (reserved lanes)) runs this skill headless on
origin/main and publishes the memo under `runs/system-integration/<slug>/` on
main — your laptop does none of it.

```
python3 components/system-integration/queue_check.py ready <folder>
git commit -m "system-check: /system-ready <folder> --mini, queued" -- <the ONE path it printed>
git push
```
- The script checks the request with the worker's own `system_check_plan` and
  writes it with `platform/tools/dispatch_card.py`'s writer — it refuses
  exactly what the lane would refuse, by name, and writes nothing on a refusal.
- **Refused:** a folder not on origin/main (the mini sees main and nothing
  else — push first, or run without `--mini`), the `mini` mode word (that is the L3 check of whether the MINI CAN RUN the target — a different question from WHERE this skill runs; run it here), and anything that reaches step 15 — the move is the owner's act, never a queued job. Commit ONLY the
  printed path, by pathspec, and push in the same turn — an unpushed request is
  one the mini never sees.
- Answer with: the request id, `platform/data/records/workflow-requests/`
  for its status (`running` → `done` with the memo's commit, or `failed` with
  the reason), and the memo folder. Then stop — no Step 0, no memo, no Step last.
- `--mini` never changes a local run: without it, every step below runs as written.

## JOB MODE — only when the `system` lane runs you (never on a person's session)

The lane's prompt says JOB MODE; each line below overrides this skill where they
differ. A person's session never enters it, whatever it is asked.
- Step 0's pull is SKIPPED — the worktree IS origin/main.
- Step 0b reports `local = main, clean`.
- **Step last is SKIPPED** — leave the memo files where you wrote them; the
  worker publishes them. No git write of any kind (git is read-only here).
- Write `<run folder>/system-run.json` beside the memo — the seven fields of
  `platform/data/kinds/system-runs.json` (target, skill, verdict, label,
  base_sha, issue_ids, memo_path); `verdict` is the memo's headline verdict
  COPIED WORD FOR WORD (the filer refuses a paraphrase or a summary). The worker files the record from it
  (SI-17 (system runs filed)); you run no python3.
- Write `<run folder>/flow.json` too (Step flow, SI-19 (ready drafts flow)) — it
  ships with the memo; you run no flowcheck here, the compiler checks it.
- Step README (components rule 10, amended 2026-10-01): write the component's
  README as it should land at `<run folder>/README.md` — never into
  `components/` (the fence); omit it when the README needs no change.
- Write ONLY under `runs/system-integration/<slug>/` — one file anywhere else
  fails the whole job and nothing is published.
- **`/system-ready` stops at the readiness report and the packet** — NEVER
  step 15, never `components/system-integration/move.py`, whatever the
  report says.

External dependencies (rules file: pointers outside this folder are listed here):
- `.claude/skills/system-fit/SKILL.md` — steps 0–9 and the levels table; run
  it first when no FIT.md is newer than the folder's last commit.
- `components/system-integration/conventions.md` — THE LIST; O-ids
  cited here are its.
- `components/system-integration/move.py` — step 15's mechanics (SI-8 (skill-executed move)): stage / land / revert, exit codes 0,2–12 (10: HEAD is not origin/main after a fetch — stage and land refuse rather than publish a stray local commit; 11: revert refuses because a rewritten line no longer matches, or matches more than once — SI-13 (move lands only the move), SI-13b (revert unstages readers); 12: land refuses because a reader changed after stage — SI-13b (revert unstages readers)).
- `components/system-integration/readers.py` — THE readers count (SI-9 (one readers count)); `--patterns readers.txt --json`.
- `platform/data/kinds/tasks.json` — the task block's field authority.
- `team/id-tags.json` — tags for every id in prose.
- `team/dispatch-grants.json`, `platform/workers/mini-worker/env.template` —
  level 3 facts.

## Step 0 · freshness — before reading anything (the developer, 2026-09-21: "these skills should auto git pull when run to avoid repo drift")

```
git fetch origin --quiet && git status -sb | head -1
```
- `behind` → `git pull --ff-only origin main` BEFORE any read. A fast-forward
  only: this clone is shared with worker ticks and other seats, and a merge
  or rebase minted by a skill is a human-shaped problem, never the skill's.
- pull refused (diverged, or the tree has another seat's uncommitted edits)
  → do NOT stash, do NOT reset; say so in the memo header —
  `read at HEAD <sha>, UNPULLED: <reason>` — and proceed. Every finding then
  carries that caveat once, in the header, not per line.
- fetch fails (offline) → proceed, header says `(unfetched)`.
- `ahead` → say so; unpushed local commits mean another seat parked early.
The memo's HEAD stamp is taken AFTER this step, never before.

## Step 0b · the local machine, and its drift from main (the developer, 2026-09-21: "all skills need to also read the local machine it's on … used before significant merges to gut check prior to integration … each skill also then considers the relevant main repo and any drifts on local as one consideration")

The checks run against THE TREE AS IT IS ON THIS MACHINE — that is what is
about to merge — while reuse, conventions and "what's new" are read from
`origin/main`. So after the pull, read the local state, once, and carry it
as its own section of the memo:

```
git rev-parse --abbrev-ref HEAD                      # branch, or a detached worktree
git merge-base HEAD origin/main                       # the base this work forked from
git log --oneline origin/main..HEAD -- .              # LOCAL AHEAD: commits main does not have
git status --porcelain -- <folder> <paths it reads>   # uncommitted and untracked, target + inputs
git stash list                                        # parked work that a merge would not carry
git diff --name-only <merge-base> origin/main -- <paths the target reads or imports>
                                                      # MAIN AHEAD: inputs that moved under it
git diff --name-only <merge-base> HEAD | sort > /tmp/l; git diff --name-only <merge-base> origin/main | sort > /tmp/m; comm -12 /tmp/l /tmp/m
                                                      # COLLISIONS: both sides touched
```
Memo section **Local vs main**, always present, four lines minimum:
- `local: <branch|detached> at <sha>, <n> commits ahead of origin/main, <k> files uncommitted under the target, <s> stashes` — or `local = main, clean`.
- `main ahead on inputs: <files the target reads that changed on main since the base>` — each one is a pre-merge re-check (a contract line, a brand file, a rule).
- `collisions: <files both sides changed>` — a merge of this work touches them; name the other side's commit and author.
- `unpushed memo risk: <yes/no>` — whether this run's own output would reach origin (see the last step).
The verdict lines (levels, readiness, disposition) are stamped `at local <sha> (<n> ahead of main <sha>)` — the Step-0 sha, the one the checks read; a later `(HEAD at write: <sha>)` in the header is information, never the verdict's base — never at main alone, so a reader knows the judgment was on what is about to merge, not on what has merged. A worktree on an `impl/*` branch is named as such with its card id and tag.

## The integration process this skill prepares (the developer, 2026-09-21)

```
 1 EXPERIMENT        owner builds in lab/<person>/ · runs /fit whenever they want to
                     know what changed, what to reuse, what conflicts
 2 FIT CHECK         /fit <folder> — the owner's own act, repeatable, writes nothing
                     but FIT.md
 3 READY GATE        /fit ready <folder> — pass/fail on the list; if pass: plan,
                     handoffs, task block
 4 INTEGRATION       THE OWNER BY DEFAULT (the developer, 2026-09-30; amends 09-21's
    (if needed)      "the designer + the email lead, WITH the owner"): the owner gives the
                     walkthrough and finishes the SOP from understanding.md and
                     sop-draft.md. the designer joins ONLY for a key grant, a
                     template change, a contract line or mini setup. the email lead joins
                     ONLY when someone other than the owner will run it: she
                     verifies on one real input and finishes the end-user SOP.
                     Owner the only user (`Runs by:` the owner, nothing on the
                     mini) → step 4 drops out. Never a gate before the move.
 5 MOVE              the OWNER's act (ruled 2026-09-21: graduation is not a gate);
                     the move FILES /system-review on the system lane itself
                     (SI-20 (move triggers review), 2026-09-30) — the owner does
                     nothing more; the email lead may re-run it by hand; its
                     disposition replaces the word
 6 IN USE            end users run it from the SOP; output under runs/; records
                     on the plane; the email lead tracks it
```

the developer supports the whole process (heavily this week); the target is that it
runs with minimal oversight. Steps 4 and 5 are not sequential with L2/L3:
a machine may go to the mini before a second person runs it, or after.


## Where a run lives (the developer, 2026-09-21: "Go move to runs")

`runs/system-integration/<target-slug>/<YYYYMMDD-HHMMZ>-<skill>/` — the machine
is `system-integration`, the brand slot is the TARGET's path slug (slashes →
hyphens: `components-copywriter`, `lab-owner-intake`, `brands`), the label is
the UTC stamp from Step 0 plus the skill name. Never beside the target,
never under a person's folder: output location must not depend on code
location or on who ran it (runs/README.md). One run = one folder, never
overwritten; history is the list of labels.

## Step 0c · prior runs — build on them, never regenerate what did not move

`ls runs/system-integration/<target-slug>/` — every earlier run, any skill,
any invoker. List them in the memo's first section (label, skill, read-at
sha, verdict). Then: if the newest run of THIS skill was read at a commit
since which nothing changed under the target or its inputs (`git log
<that sha>..HEAD -- <target> <inputs>` empty) and the conventions list did
not move, write nothing — answer "current as of <label>" and stop, unless
invoked with `--fresh`. Otherwise run, and CARRY FORWARD: issues keep their
ids across runs (W1, U3 …), an unchanged issue keeps its provenance verbatim
marked `unchanged since <label>` and only its impact line is re-checked; a
closed issue is listed CLOSED with the closing commit; new issues get new
ids; ids are PER SKILL — a fit's findings carry the list's O-ids (O2, O9…)
and a review keeps them as they are; a review's own kinds (W/U/C, D, R,
REG, M, N…) are minted by the review and never renumbered; WHEN A MERGED
REVIEW.md EXISTS its ids are the base and a part cites its own older
numbering once as a cross-reference — parts mint review kinds too, never
bare `#n` or `I-n` (the org's I-series collides); a prior memo from an
older skill shape is matched by content, path and kind, never by
position. The predecessor's read-at sha is taken from the PART's own
header, not the merged file's (they can differ by minutes and a commit
can land between). "Nothing moved" means: the target, its INPUTS (for a
tool: what it imports and reads; for a content tree: its READERS, taken
from the predecessor's saved reader list), and the conventions list —
a change to the LIST or the SKILL is a run, limited to the checks that
changed; readers that moved are a run of the impact lines only. Grep
`platform/data/records/` for the predecessor's issue ids: a lead's inbox
item or task citing one is the usual reason an issue CHANGED. Save the
reader-grep pattern list as `readers.txt` in the run folder so the next
run reuses the same set and a count that moves is the tree, not the
method. **COUNT IT WITH `components/system-integration/readers.py`, never
by hand-grepping** (SI-9 (one readers count), 2026-09-25 — ONE implementation,
also what `moved-readers.sh` calls): `python3
components/system-integration/readers.py --patterns <run folder>/readers.txt
--json` gives this skill's count, method `pattern-list`. The hook prints the
SAME script's `needle-tail` count (the old path's last two segments) after a
`git mv`. Same code, two NAMED methods: when the pattern file holds only that
needle the numbers are equal; when it holds more, the memo quotes BOTH with
their method names, and **the `pattern-list` count is the authoritative one for
a memo**. `readers.txt` lines are REGEX (SI-9b (regex pattern mode), merged
2026-09-25); the hook's needle stays fixed-string, because a path's `.` must not
match anything. A line that does not compile is reported under `bad_patterns`. Word-cap relief on a repeated run: an `unchanged since` issue is
ONE line (id · title · decider) and its verbatim provenance is exempt
from the count. Re-run `git status -sb` just before writing the header;
a shared clone moves mid-run. Hooks are checked by `git config
core.hooksPath`, never by listing `.git/hooks`., and a prior memo whose header names a path
that has since moved is history only, never a base. A repeated run LEADS
with "Since <label>": closed · new · changed · how the verdict moved.

## Step 0d · the INTENT — what this move is FOR (SI-6 (intent line) / SI-7 (level verdicts), 2026-09-22)

Read it BEFORE the report, because it decides which questions are even asked.

```
Runs by: person | mini | both        in the target's own CLAUDE.md
```

- **ABSENT MEANS `person`.** That is exactly today's behaviour, so nothing
  already written changes meaning and nothing needs backfilling. An absent line
  is an answer, not a gap — never report it as one.
- A word in the invocation overrides it for THIS run only —
  `/system-ready <folder> mini` — and **never writes itself into the record**.
  Someone asking "what would it take to put this on the mini?" is asking a
  question, not declaring an intent.
- Say in the header which one you used and where it came from, so a reader can
  tell a declared intent from a one-off question:
  `intent: mini (from <folder>/CLAUDE.md:<line>)` or `intent: mini (this run only; record says person)`.
- The wording of the convention line itself is the email lead'S to curate. If you find a
  variant spelling in the wild, report it — do not silently normalise it.

WHY IT EXISTS (the developer, 2026-09-22): "the system ready should check for what the
move was intended (L2 or L3 or both)". A report that asks every question every
time buries the three that matter for the machine actually being prepared.

## Steps

10. **The readiness report, as its own step — never a refusal.** Read the
    FIT.md (run `/system-fit` first if none is newer than the folder's last
    commit). Verdict is one of:
    - **BLOCKED** — only by a WALL: a secret-shaped literal in the folder; a
      key read by path or literal (O6); a machine write into `brands/` (O5);
      a tracked file over 10 MB or media (O8). Walls are about harm, not
      cleanliness (the developer, 2026-09-21). BLOCKED still writes the packet, with
      the wall item first.
      **TWO OF THESE FOUR NOW REFUSE MECHANICALLY AND THIS REPORT ONLY REPORTS
      THEM** (2026-09-22): `wall-guard.sh` refuses a >10 MB write or a
      secret-shaped literal at Edit/Write, and `wall-staged-guard.sh` refuses
      the same over the STAGED set at `git commit` — person-agnostic, worker
      included. So a secret or an oversize file is stopped by a hook whether or
      not anyone runs this skill; never write the memo as though the prose is
      what refuses (never-flex 1). The other two — a key by path (O6) and a
      machine write into `brands/` (O5) — have NO mechanical guard yet and this
      report is still the only thing that catches them. Say which kind each
      wall finding is, because it tells the owner whether they are about to be
      refused or merely warned.
    - **READY WITH GAPS** — anything else on the list is open: L1 findings,
      the four new-resident questions unanswered (O11), NO GENERATED "HOW TO
      USE IT" in the folder's README at a commit no older than the folder's
      last change, or one whose confirm-with list is unanswered (the
      how-to standard, the developer 2026-09-21), no adapter line
      (O12; accepted forms: an adapter exists · "none — the manifest is the
      product" · "none — <reason>, it files the CALLER's run" · a named
      card), owner not in writing, a decision someone else must make.
      Each gap is one line: what, who closes it, rough size.
    - **READY** — no gap.

    **A VERDICT PER LEVEL, IN ONE `ready.md` (SI-7 (level verdicts), 2026-09-22).**
    A wall is LEVEL-INDEPENDENT and refuses regardless; a gap is PER LEVEL and
    never blocks. Report only the levels the intent asks for, plus L1 always.

    - **L1 · runs here** — always reported. Today's L1 findings, unchanged.
    - **L2 · another person** — today's checks plus the packet, unchanged. Report
      it when intent is `person` or `both`.
    - **L3 · the mini** — report it when intent is `mini` or `both`. These are
      MECHANICAL, not judgment: run them, do not reason about them.
      1. **Root.** Is the runnable script under `components/` or under the
         invoker's OWN `lab/<person>/`? Either needs NO grant row
         (WM-80 (component roots)). Anything else: name the exact
         `team/dispatch-grants.json` row it would need. **Live for fit-run today
         (`platform/workers/mini-worker/worker.py:9439`); lab-run is
         WM-80 (component roots) itself, so say which of the two this target
         would run under rather than assuming both behave alike.**
      2. **Keys.** For a COMPONENT run (`components/<name>/`, WM-121 (component
         keys from code), merged 988b3605d): every env name the code READS,
         intersected with `env.template` — NO grant; the worker hands the run
         exactly those keys that the `lab-run` ceiling holds, and a component
         row carrying `keys` is refused. For a LAB script or a person-scoped
         key, the three-way intersection stands: every env name the code READS,
         intersected with `env.template`, intersected with that person's grant
         `runs.keys`. Name each missing one INDIVIDUALLY — "some keys missing"
         is not a finding. The effective set is the grant ∩ `JOB_ENV` ceiling
         (`platform/workers/mini-worker/job_env.py:72`, the `lab-run` row at
         `:154`). **the designer commits a grant row; this skill never does.**
      3. **The interpreter, and it is a FACT not a preference.** Every file must
         compile under `/usr/bin/python3` (3.9.6 on the mini) AND the declared
         test must run under THAT binary. `python3` is 3.14.7 here and they are
         different fact worlds. **If `/usr/bin/python3` refuses to execute for
         you — it is permission-blocked inside worker worktrees — say so as the
         finding; do NOT substitute the other interpreter and report a pass.**
      4. **Machine-bound literals.** Home-path literals (`/Users/<name>`, `~/…`),
         fixed ports, Drive MOUNT paths, and any file read by path. Each one is
         a line with its `file:line`.
         Also stored data: `python3 components/system-integration/data_paths.py --under runs/<the target's machine>` — each *reference* finding is machine-bound (a TARGET, never a wall); old records are listed, not rewritten (LD-80 (stored path check)).
      5. **Where output goes.** Writes only under `runs/`; media to the Drive
         mirror path, never into git; a records adapter named, or the words
         "none yet".
      6. **If it shells to `claude -p`:** say plainly that the fenced lane has
         NEVER been proven to run it — the CLI writes state under `$HOME` and
         the fence denies that — and that **the first `--dry-run` IS the test**.
         Do not report this as a pass or a fail; report it as unproven.
      Reuse a measurement that already exists rather than re-deriving it: if a
      fit-run has measured L2/L3 for this target, cite its numbers and say where
      they came from.

    **WHEN THE INTENT IS `mini` OR `both`, END WITH TWO DRAFTS AND A LINE TO
    PASTE — AND FILE NEITHER.** This skill's contract is that it writes only
    under the run folder and files nothing, and that contract is NOT changed
    here (changing it is SI-8 (skill-executed move)'s job, deliberately and in
    the same commit as the behaviour). So:
    1. `grant-row.draft.json` in the run folder — the exact
       `team/dispatch-grants.json` row this target would need, or the words
       "no new row needed" with the reason. **the designer commits it. A grant is
       a human's own act and this skill never performs one** — it writes the
       draft so that act takes one paste instead of an hour.
    2. `dry-run-request.draft.json` in the run folder — the `lab-run` request
       with `--dry-run`, ready to file.
    3. Print, in the answer and as the last line of `ready.md`, the ONE command
       that files it and WHERE THE RESULT WILL LAND, so nobody has to go
       looking: the request path under `platform/data/records/workflow-requests/`
       and the run folder under `runs/`.
    A later invocation READS that result and moves L3 from READY to PROVEN.
    Until a dry run has actually executed, **L3 is never reported as PROVEN** —
    the strongest L3 verdict a static check can earn is READY.

    **`mini`-only still gets the twelve-line "how it works".** The 2 a.m.
    operator is a person. An unattended machine is not a reason to skip the
    page a human reads when it stops.

    Write the verdict to `ready.md` in this run's folder
    `runs/system-integration/<target-slug>/<label>-ready/` (overwritten whole;
    header
    `# READY — <machine> — HEAD <sha> — <date -u> — intent <person|mini|both> — L1 <verdict> · L2 <verdict|n/a> · L3 <verdict|n/a>`, then
    the gaps, then "re-run when: <items>"). THEN ALWAYS CONTINUE to the
    packet — the email lead and the designer decide with the gaps in front of them;
    the report informs, it does not gate. (Changed from a gate on the developer's
    ruling of 2026-09-21: build fast, get others using it, clean up after;
    conventions are targets, walls are the exception.)
11. **The plan.** `fit/plan.md` beside FIT.md, stamped with the
    CURRENT HEAD and naming the HEAD its FIT.md was read at: steps in order, each with
    who (owner / lead / the email lead / a lead for the review disposition),
    what it produces, and the decision it waits on if any. Points at FIT.md
    §Reuse rather than copying it. Ends with `Reuses / could be reused by:`.
12. **Handoffs — the integration step's inputs**, in `fit/` beside FIT.md:
    **WHO A DECISION ADDRESSES** (the developer, 2026-09-21): a decision the lab owner
    cannot make alone — a key grant, a template change, a Residents contract
    line — addresses **the designer**, never the developer. She can grant today with no
    code change: `team/dispatch-grants.json`'s `_rules` makes a grant "the
    granting human's own act" and is not the developer-specific. If a packet says
    otherwise it is repeating the record's history, not this rule.
    - `handoff-the designer.md` (technical finish): what to set up for L2/L3 and
      why each item is blocked today (from the levels section), the run
      command, keys by NAME, where output lands, the adapter question.
    - `handoff-the email lead.md` (integration + PM): the task block (step 13), who the
      end user is — THE ONE HOME for that question (ask the owner if unknown,
      never guess; plan.md and sop-draft.md point here rather than repeat
      it), what "working as intended" means in one testable sentence, and
      the SOP skeleton.
    - `handoff-<owner>.md`: the owner's own step 4 (owner by default,
      2026-09-30) — the walkthrough on one real input, the command, what to
      look at in the output, finishing the SOP from sop-draft.md — and the
      decisions still theirs.
    - `understanding.md` — THE GENERATED "HOW TO USE IT", in the six parts
      `/system-review` produces (what it does · before you start, each line
      tagged (ran)/(read)/(docs) · the command as the docs name it · what you
      get and where · when to stop and ask whom · confirm with <owner>) plus
      the steps in order and what breaks it. It is read out of the folder AS
      IT IS, never written from the owner's description first — that order
      is the standard (the developer, 2026-09-21: a creator often cannot explain
      precisely, or the tool differs from what was intended; the code-derived
      reading finds that, the confirm-with list is where the creator
      corrects it). It goes into the flow's `howto` (Step flow) and shows on the component's atlas page, fresh on every run. The README carries ONE line, `## How to use it → <atlas page link>` (components rule 10, amended 2026-09-30); nobody pastes the block. The skill writes the README itself (Step README, rule 10 amended 2026-10-01); a README it could not write is a GAP naming the owner, never a wall.
    - `sop-draft.md` — the end-user SOP SKELETON: purpose · before you start ·
      the command · what you get and where · when to stop and ask whom. Marked
      DRAFT — the email lead and the designer own the finished SOP; the skill never claims
      to.
    Each file: what you are being asked, what to read first (paths), what is
    already true at HEAD (sha), what is yours to decide, what happens if you
    do nothing. Claude-optimised: paths and shas, no narrative.
13. **The task block** for the email lead, in the memo and at the end of plan.md: one
    line per task in the tasks-kind shape (`platform/data/kinds/tasks.json`
    is the authority) — title · body (one paragraph) · assignees · priority
    (integer, 1 = top) · links · requested_by (the invoker) · source (`fit`)
    — with `stream` and `due` stated ONCE above the block ("the email lead to set"
    unless the owner's existing tasks carry a stream), never per line, and
    status `proposed`, which the manifest defines as "filed without
    authority to make it live; not actionable until a human with context
    confirms" — that human is the email lead. Each task line also lands in flow.json as a `review-task` issue, exactly as /system-review's Step flow says ("TASK BLOCK INTO ISSUES"), so the page shows every unfiled task. As text she pastes into the PM tool. Proposes ONLY the integration tasks that apply
    (the developer, 2026-09-30), each naming the condition that triggered it: owner's
    walkthrough + SOP (the owner — always, unless the owner is the only user) ·
    technical finish (the designer — only for a key grant, template change,
    contract line or mini setup) · verify on one real input + finish the
    end-user SOP (the email lead — only when someone other than the owner will run it). The skill NEVER
    writes a tasks record itself.
14. The visual (an artifact of the plan) is on request only — say so.


15. **THE MOVE, ON THE OWNER'S YES** (SI-8 (skill-executed move), 2026-09-25 —
    the developer: "after he resolves them then system ready should indicate it is ready
    for the move, and have him respond if he is ready, and that makes the move
    itself. Or he can decide to wait and that is his decision"). Only for a target
    under `lab/<person>/`, and only when the INVOKER is that person.
    1. **No wall open** (step 10) — otherwise stop here: "close these, then rerun".
    2. Show the two judgment calls with a proposal and its evidence: the NAME
       under `components/` (a name that already exists there is CONSOLIDATE INTO,
       a person's act — never a move), and any SHIMS for importers the reader list
       shows (the apify precedent; shims are proposed here, never written by the
       script). Then ask ONE question, verbatim shape:
       `READY WITH <n> GAPS. Move it now? (yes / not yet)`
    3. **"not yet"** → write `move.md` in this run folder (the proposal, the name,
       the reader list, the command it would run) and end. A rerun resumes from it.
    4. **"yes"** → the mechanics are NOT prose; run the script, in order:
       ```
       python3 components/system-integration/move.py stage lab/<person>/<name> --to components/<name> --run <this run folder> --rewrite
       ```
       It refuses a non-owner (exit 3) and an existing target (exit 4), PRINTS every
       old-path reader as `file:line` before touching one — show that list to the
       owner, because those files are other people's — then moves and rewrites.
       Brand files (brands/) are never rewritten: stage lists them under `brand
       readers, for the brand owner (not edited):`, stores them in move-plan.json
       `brand_readers`, and land does not wait on them — show that list to the
       brand owner (system-integration#1, K2 (brands write wall)). It
       commits nothing. THEN write, into the moved folder: its `CLAUDE.md` with
       the four new-resident answers pre-filled from `understanding.md` (plus
       `Runs by:` if the intent was declared), and the README's one line `## How to use it → <atlas page link>` (rule 10, amended; the six parts live in the run's flow.json); and add the
       Residents row to `components/CLAUDE.md`. THEN:
       ```
       python3 components/system-integration/move.py land --run <this run folder> --test <declared test> --python /usr/bin/python3
       ```
       It re-counts readers (SI-9 (one readers count)), runs the declared test,
       requires the Residents row, commits BY PATHSPEC, pushes and verifies the
       destination — and in the SAME push files ONE `/system-review` request for
       the new path on the system lane (SI-20 (move triggers review)); report the
       printed `review filed: <path> — request <item>; memo under <folder>`.
       Any refusal (5 readers remain · 6 test red · 7 row missing ·
       8 push not verified · 10 HEAD is not origin/main · 12 a reader changed after stage ·
       13 review request refused) leaves the tree changed and uncommitted and prints ONE
       revert line — report it verbatim, with the reason, and offer
       `move.py revert --run <this run folder>`. Never retry past a refusal.
    5. For intent `mini` or `both`, after a landed move: the grant-row draft and the
       dry-run request from step 10 stay DRAFTS for the designer — this step changes
       the move, not the grant rule.
    Exit 0 is the only "moved". The lab folder is removed only if it is empty;
    anything left (untracked outputs) is listed, never deleted.
    KILL (the developer heard it): a skill-executed move breaks something outside the
    owner's roster twice in a month → this step reverts to writing `move.md` only.

## Step flow · draft the component's flow (SI-19 (ready drafts flow), 2026-09-30)

Write `<run folder>/flow.json` in flow format v1 — the contract is
`new-workflow-design/builds/atlas/flows/SCHEMA.md`, the method
`new-workflow-design/builds/atlas/flows/DRAFTING.md`. `stage` is
"ready check", `target` is the folder you ran on. UPDATE the newest flow.json for this target (a prior run folder's, else the pilot file in flows/), and fill `howto` from your understanding.md, the owners, and `issues` from this run's conflicts and task block. The page this starts NEVER blocks the move — only walls do. Example at this stage: flows/email-production.json.
CARRY every existing issue forward with its n, tie, owner, resolved and
merged_into as they are; update its text or affects only where this run's
reading changed; add new issues at `issues_next` and bump it; mark an issue
resolved only with evidence (sha or file:line); NEVER renumber (issue numbers
are fixed, SCHEMA.md §5). A detail item a person edited (`edited` set) is
re-checked, never overwritten — a contradiction is a conflict for the email lead, not a
rewrite.
A file THIS run writes (the memo, readers.txt) is cited WITHOUT @sha — it did
not exist at the base (SCHEMA.md §3). `used_by.writes_back` is
`{who, events[]}`, never a sentence (SCHEMA.md §4).
Every claim cites what you read (path:line at this sha); what you could not
confirm is a gap, stated, never filled. The atlas compiler checks the claims
on its next pass; in a person's session you MAY run
`python3 .claude/skills/atlas-view/flowcheck.py <run folder> flow` first. A
draft is proposed — the email lead approves flows (decision log, 2026-09-30).

ISSUE BRIEFS (SCHEMA §5, 2026-10-02). Every issue this run adds or re-reads carries `why`, `impacts` {people, components, machines}, `evidence` (path:line@sha), `fix` (the RESPONSE: what to do — a fix, a follow-up on a positive signal, or another move; key name kept), `fix_impact` (what the response changes), `if_ignored`, `lane` (the email lead · owner · decision) and `severity` (P0–P3); `lane` and `decider` are never "none". If `new-workflow-design/builds/atlas/triage/issue-briefs/<component>.json` exists for this target, start each of its issues from that brief, re-verify every field at this sha, and carry it into the flow. Facts you could not confirm are marked (inferred)/(unchecked), never filled.

## Step README · write the component's README (components rule 10, amended 2026-10-01)

Only when the target is a `components/<name>/` folder; a lab or sandbox target
gets its README when it moves (`/system-ready` step 15). the developer, 2026-10-01
(relayed by ≈ STREAM · atlas [6941d8], verbatim, 08:22:42Z): "reauired readme,
generated." Apply `new-workflow-design/builds/atlas/tools/readme_fill.py`'s
rules to the ONE folder — same format, same marker line:
1. No README → write one: `# <name>`, the generator's `MARK` comment, what it
   is (THIS run's flow.json `character`, else the line "What it does is not
   stated yet: its next system run draws it."), `Owner: <the compiled owner in
   platform/data/atlas/data.json, verbatim, else "not stated">`, and the link
2. README without the link line → insert the link line (blank line before)
   right under its first `# ` title, else at the top. Nothing else changes.
3. README that has the line → untouched, EXCEPT one refresh (the developer, typed to the lead
   2026-10-01: "refresh the line"): when it carries the generator's `MARK` comment
   (a generated README), the "what it is" line — the first non-blank line after
   `MARK` — is replaced with THIS run's flow.json `character` when the two differ.
   Nothing else in the file changes: not the title, the owner line, the link line,
   or anything a person added. A README without `MARK` (hand-written, link line
   inserted) has no generated line and stays untouched.
4. README with an old pasted `## How to use it` block → untouched; its STALE
   issue stands.
Write it ONLY inside Step last's throwaway worktree (`$mt/components/<name>/README.md`),
never in the working clone, and add that path to Step last's list; this clone
gets it on its next pull. Your answer names which rule fired. In JOB MODE
write `<run folder>/README.md` instead (the fence) — the full file as it should
land, or no file when rule 3 or 4 fired; until the worker publishes it to the
component, the missing README or link line stays ONE issue on the page.

## Step last · leave it on origin — the memo only, never the machine's other work

The memo must reach `main` without carrying anything else this clone holds
(the developer, 2026-09-21: "the reviews need to be on main without pushing other
unintended work"). So the skill NEVER pushes the working branch. It ships
the memo from a throwaway worktree based on `origin/main`:

**First, file the record** (SI-17 (system runs filed), 2026-09-30): write
`<run folder>/system-run.json` (the seven fields of
`platform/data/kinds/system-runs.json`; `verdict` copied word for word from
the memo's headline verdict — a summary is refused), then
`python3 components/system-integration/system_runs.py <run folder>` — it
prints the ONE record path, or refuses by name and writes nothing (then the
memo ships alone and your answer says why; the memo stays the truth). In the
block below, `<memo path>` stands for the memo, `system-run.json`, `flow.json`
AND that record path — the mkdir/cp, add, commit and rm lines each take all four —
plus, when Step README fired, `components/<name>/README.md`, written in `$mt` only
(add and commit take it; no cp from the clone and no rm).

```
git fetch -q origin && mt=$(mktemp -d)/memo && git worktree add -q --detach "$mt" origin/main   # fetch FIRST: the local origin/main ref can be minutes stale
mkdir -p "$mt/$(dirname <memo path>)" && cp <memo path> "$mt/<memo path>"
git -C "$mt" add -- <memo path>
git -C "$mt" commit -q -m "note: <skill> — <folder> — read at <sha>" -m "<the attribution trailer your session requires>" -- <memo path>
git -C "$mt" push -q origin HEAD:main            # fast-forward only; refused → fetch, worktree reset to origin/main, redo once
git worktree remove --force "$mt"
rm -f <memo path>     # the LOCAL copy: identical bytes now on origin; left in place it blocks this clone's next pull ("untracked file would be overwritten") — it returns on that pull
```
Properties, each one deliberate: the working branch, its unpushed commits,
its uncommitted files and its stashes are untouched and unpushed; the
commit's only parent is `origin/main` so the push carries the memo, its draft and its record, nothing else; the
repo's hooks (id-tag lint, governance guard) still run in the worktree,
so a refused commit is reported, never bypassed — and so do the WALLS, which
fire on the Edit/Write and on the `git commit` itself whatever worktree you
are in: `wall-guard.sh` and `wall-staged-guard.sh` refuse a file over 10 MB or
a secret-shaped literal, and `moved-readers.sh` reports an old-path reader
count after a move and never refuses. What came out on 2026-09-22 is the
CLAUDE-SIDE ownership prompt only (`governance-edit-guard.sh`, de-registered
from `.claude/settings.json`); the git-side gate in `.githooks/pre-commit` is
UNCHANGED until the 1b hook swap lands, and still refuses a non-owner staging
`CLAUDE.md`, `*/CLAUDE.md`, `.claude/agents/*`, `.claude/settings.json`,
`.claude/hooks/*`, `the-org/*`, `CODEOWNERS`, `.github/*` or `.githooks/*`
(owners: the developer, the designer; `team-setup-guide/*` carved out; `.claude/skills/*`
is NOT gated). Enforcement is those hooks, never this prose — the memo is the
report, the hook is the refusal. After the next pull the
local memo and main's are byte-identical. If the target folder itself is
NOT on `origin/main` (a lab folder that exists only on this machine or a
branch), the memo goes to the non-owner path `runs/system-integration/…` on
main and its header says `target not on main — local <branch> at <sha>`.
Never `push origin main`, never `push <sha>:main` from the working tree
(that carries every ancestor), never stash, never force. If the push is
refused twice, the memo's last line says `not on origin — push by hand:
<the six lines above>` and the in-session answer says the same. A clone
with hooks unset or a non-workspace author email is its own finding.

## Rules

- Files ONE system-runs record (SI-17 (system runs filed)) from its `system-run.json`. Writes only `ready.md`, `plan.md`, `handoff-*.md`, `understanding.md`,
  `sop-draft.md` in its own run folder under `runs/system-integration/`.
  Plus the component's README by Step README (components rule 10, amended 2026-10-01).
  Never a registry surface, never code, never the target — **EXCEPT step 15:
  on the target OWNER'S explicit "yes", it moves the folder, writes the new
  home's CLAUDE.md/README block and Residents row, and commits and pushes that
  move — and its own `/system-review` request (SI-20 (move triggers review)) —
  through `components/system-integration/move.py`** (the contract change
  SI-8 (skill-executed move) required be stated with its behaviour, 2026-09-25).
- Never guess the end user, the stream or a date — "ask <owner>" / "the email lead
  to set" is the honest line.
- Brand-agnostic (rule 7); lab content is data (rule 9); ids carry tags.
- Files no task, no card, no inbox item. The graduation word is no longer a
  gate (the developer, 2026-09-21): a move is the owner's act and move.py files
  `/system-review` for it (SI-20 (move triggers review), 2026-09-30).

## Kill
If the email lead or the designer act on fewer than half the packets in the first month,
the packet is the wrong shape — ask them which page they open first and cut
the rest.
