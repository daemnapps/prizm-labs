---
name: system-review
description: Settle something that already sits in the workspace — a folder someone moved or created here — so a lead or the email lead can see whether it follows the system and what is left to accept it. "review the brand folder against the system", "system review of components/copywriter", "/system-review <folder>", "settle this into the system", "audit this folder for duplicates and stale files", "what's wrong in brands/ and who put it there", "what would it take to formally graduate this", "clean-up list for <folder>". Every issue comes with how it came about (who, when, which commit), what it impacts (which files, machines and people read it), and a suggested next step. Reads as data, edits nothing, writes only REVIEW.md and files one system-runs record; files no task, rules nothing, gives no graduation word.
---

# system-review — it is already here; does it belong, and what is left?

> **Activates component:** `components/system-integration` — review of a folder already in the workspace.


Stage 3 of the integration path (the developer, 2026-09-21): `/system-fit` is the
owner's own check, `/system-ready` prepares work for others, `/system-review`
is the lead's or the email lead's
(a move files this review on the system lane itself — SI-20 (move triggers
review); a by-hand run, local or `--mini`, is always allowed)
look at what already arrived — moved from a lab, created in place, or grown
over weeks — and what it takes to accept it formally. It is the atlas's
feeder: what it finds becomes register acts, a cleanup list, and tasks.

```
/system-review <folder>              a tool folder → resident review · a content tree → folder review
/system-review <folder> --part <sub> one subtree of a big tree (the fan-out unit; results merge by path)
/system-review <folder> [--part <sub>] --mini file it for the mini's `system` lane; run nothing here
```

## Atlas, compiled fresh (ATL-53 (atlas daily), 2026-10-30)

The committed `platform/data/atlas/data.json` now refreshes once a day (the worker's refresh switch). Before this skill reads the atlas, compile it fresh for this run, and read that copy wherever this file names `platform/data/atlas/data.json`:

```
ATLAS_FRESH=$(mktemp -d)/data.json && python3 components/atlas/compile.py --out "$ATLAS_FRESH" --no-stamp
```

It takes about 30 s. The report says "atlas compiled fresh at <git rev-parse --short HEAD>". If the compile fails, say so and fall back to the committed copy, naming its age (`stat -f %Sm platform/data/atlas/data.json`).

## `--mini` — queue it on the mini's `system` lane instead (SI-15 (mini flag), 2026-09-30)

`/system-review <folder> [--part <sub>] --mini` runs NOTHING here. It files ONE `system-check`
request and answers with its id and where the memo will land; the mini's
`system` lane (WM-114 (reserved lanes)) runs this skill headless on
origin/main and publishes the memo under `runs/system-integration/<slug>/` on
main — your laptop does none of it.

```
python3 components/system-integration/queue_check.py review <folder> [--part <sub>]
git commit -m "system-check: /system-review <folder> --mini, queued" -- <the ONE path it printed>
git push
```
- The script checks the request with the worker's own `system_check_plan` and
  writes it with `platform/tools/dispatch_card.py`'s writer — it refuses
  exactly what the lane would refuse, by name, and writes nothing on a refusal.
- **Refused:** a folder not on origin/main (the mini sees main and nothing
  else — push first, or run without `--mini`). Commit ONLY the
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

External dependencies (rules file: pointers outside this folder are listed here):
- `components/system-integration/conventions.md` — the SAME list; a rule not
  on it is not cited. (Shared on purpose: one list, three verbs.)
- `components/system-integration/readers.py` — THE readers count (SI-9 (one readers count)); `--patterns readers.txt --json`.
- `components/CLAUDE.md` Residents table · `platform/data/atlas/data.json` ·
  `platform/data/records/component-candidates/` — the register, the index,
  the copies.
- `brands/_TEMPLATE/` — the shape a brand folder is supposed to have.
- `runs/README.md` — where machine output belongs (phase 1: never in brands/).
- `platform/data/kinds/tasks.json` — the task block's field authority.
- `the-org/decision-log.md` — rulings cited by date.

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

## Which mode

- **Tool folder** (a definition line, a run command, or a Residents row):
  RESIDENT REVIEW. Run `/system-fit`'s steps 0–8 on it first (or read a FIT.md
  newer than the folder's last commit), then answer four things: does it
  belong at this station (lab / components / builds / platform) given its
  consumers; is the register right (Residents row present and true, atlas node,
  candidate rows that name it, id tags); what is the cleanup list (leftover
  files at the old path, stale pointers in other folders, snapshots that
  still resolve to the old home — each with path:line); is a graduation word
  owed and to whom. THEN RUN THE FOLDER-AUDIT KINDS OVER IT TOO — a moved
  folder brings its old shape with it: machine output living inside
  (`results/`, `output/`, `runs/` beside the code — count the files; the
  first settle on a moved component found 658 of 725 tracked files were run
  records), duplicate groups, brand literals in `machine/` and `prompts/`
  only, naming, cross-brand. Disposition: ACCEPT AS IS · ACCEPT WITH
  CLEANUP · MERGE INTO <resident> · MOVE BACK. The word itself is the developer's or
  the designer's.
  Issue kinds in this mode: the audit table's kinds PLUS `NAMING/CONFLICT`
  (the folder, its definition line, its Residents row, its runs segment and
  any roster disagree on the name), `STALE POINTER` (a file elsewhere names
  the old path — code, config, test, template, brand file, or prose; split
  by whether it RESOLVES), and `INVERSE O2` (consumers reaching into the
  target's internals — this decides "belongs here" more than any check on
  the folder itself; list every importer and whether a LIBRARY clause
  exists; a TEST under `new-workflow-design/builds/` that `sys.path`s into
  the component to test it is not a consumer — list it, do not flag it).
  Four traps in this mode, each earned: (0) "nothing left at the old path"
  needs `ls -la` AND `git status --ignored` — `git ls-files` returns empty
  over gitignored leftovers and the reader concludes clean; (1) readers of
  the OLD path must be matched strictly — `old/path(/|[^-a-z]|$)` — a
  sibling folder sharing the prefix (copy vs copy-teardown) over-matches by
  ten times, and `\b` does not help;
  AND a second grep, OR'd with the first, for the SEGMENT form —
  `"the owner" */ *"copy"` and `/ *"copy"\b` in `.py` — because
  `ROOT / "lab" / "the owner" / "copy"` never contains the slash path
  (test_brand_home.py escaped the string grep; only the red record caught it); split CODE
  readers (py/json/sh/html) from DOC readers, and read each code hit to say
  whether it is a live path or a comment; (2) the red-tests records
  (`platform/data/records/red-tests/`, newest) are impact ALREADY
  HAPPENING — a suite whose `first_failing_line` names the old path broke
  on the move, cite it; (3) last-commit dates are RESET by a move, so the
  "untouched > 30 days" stale test is blind for weeks — use readers only,
  or `git log --follow` per file for the few that matter. Origin = `git log --follow --format=... -- <path> | tail -1` (`--reverse | head -1` returns wrong firsts under --follow); a squash or replay commit as origin = author UNKNOWN in git, say so and use the intake branch.
- **Content tree** (brands/, runs/, docs, a data folder): FOLDER REVIEW, below.

## Folder audit — the issue kinds (fixed; nothing else is an issue)

| kind | test (mechanical first, reading second) |
|---|---|
| DUPLICATE | `git ls-files -s <folder>` first — mode `120000` rows are SYMLINKS: report a broken one as its own CONFLICT and exclude links from hashing (`md5 -r` dies on a dangling link); then `git ls-files <folder> \| xargs md5 -r \| sort` → groups with the same hash (report the GROUP, not each file); plus same stem in two places with different content (near-dup) — name the canonical and say why |
| STALE | no reader anywhere — ONE pass, not one grep per file: write the candidate paths and stems to a file and run `git grep -l -F -f <that file> -- lab components platform new-workflow-design .claude runs brands`, then post-process hits per path (per-file `grep -r` took over ten minutes on 170 paths) AND one of: superseded by a newer sibling · untouched > 30 days · in a section the template does not define. Say which |
| CONFLICT | two files claim the same fact (two offer files, two palettes, two position files, a template slot filled twice); or MACHINE OUTPUT living here (a run record, a generated deliverable — phase-1 ruling says runs/). Test for the second: a script INSIDE the tree whose `write_text` / `mkdir` / `open(...,'w')` target resolves under the tree — the dump beside the script that wrote it; and a registry elsewhere (`files_to`, `out`, `--out`) naming a path under the tree |
| OFF-TEMPLATE | a top-level section the template does not define. "Defines" = the UNION of the template README's tree and the template's physical stubs — and when those two disagree, that disagreement is the FIRST issue (CONFLICT), because every conformance count below it depends on which one wins |
| MISSING | a template slot the brand has no file for — ONE issue per tree listing every missing slot, not one per slot |
| OVERSIZE / MEDIA | tracked file > 10 MB or a media type (workspace rule 3) |
| CROSS-BRAND | a file under one brand naming another brand. PROSE mentions ("same shape as <other brand>") are KEEP by default and not listed singly; an OPERATIONAL cross-reference (a config, a template id, a path a machine reads) is the issue |
| NAMING | not kebab-case: spaces, capitals, brackets, "Copy", "Q4" |

## For EVERY issue, four lines — this is the contract

1. **Where:** path (or the group: N files under <prefix>), size, last commit sha.
2. **How it came about:** `git log --follow --format='%h %ad %an %s' --date=short -- <path>` — FIRST commit (who created it, when, the message's first line) and LAST commit (who touched it last, when). For a group: the earliest member is the origin unless a reader says otherwise. For a moved file, `--follow` tells where it came from; say so. Never infer an author from a folder name. SQUASHED INTAKES: when the first commit is a squash or intake (message says so, or one sha covers thousands of files by a person who did not write them), the git author is the INTEGRATOR, not the author — cite the intake tag or branch (`git tag --contains`, `intake/<person>-<date>`), then the content author from the folder's own README/INDEX/`_theme.json`, marked (inferred).
3. **What it impacts:** every reader — files that reference the path or stem (grep as in STALE), the machine or component those files belong to, the people who own them (component CLAUDE.md `Owner:` / brand folder CLAUDE.md), runs under `runs/` that read it, and the template if it is a slot. "no reader found" is written, never left blank. Count readers in TWO tiers and report both: LIVE = code, config, prompts, docs and skills that would break or mislead if the file moved; RECORDS = run records under `runs/`, any `results/` or `output/` listing, lineage and candidate-scan records that merely mention the path. LIVE ranks the issue; RECORDS is context (a file with 300 mentions and 46 live readers ranks by 46).
4. **Suggested next step:** one of REMOVE · CONSOLIDATE INTO <path> · MOVE TO <runs/… | Drive path> · ADD TO TEMPLATE · RENAME TO <name> · KEEP (reason) — one clause of why, and WHO DECIDES: the brand folder's owner for content (read the folder's CLAUDE.md `Owner:` line; when none exists, write the name as (inferred) from its README and add "no owner line" as an issue of its own), the machine's owner for a file a machine reads, the email lead for anything that changes what a person does, the developer/the designer for a template change. A suggestion is a suggestion; the memo says so once at the top.

## "How to use it" — required in resident mode (the developer, 2026-09-21)

A person who did not build it must be able to use it from the review alone,
and confirm with the creator only where the review says it is unsure. Written
right after the disposition, ≤15 lines, in this order:
1. **What it does** — the definition line (takes · makes · does not).
2. **Before you start** — what must exist: repo state, a logged-in CLI, key
   NAMES in the environment, brand files it reads (paths), a mounted Drive
   if any. Each item tagged `(ran)` when the review executed it, `(read)`
   when taken from code, `(docs)` when taken from README/CLAUDE.md only.
3. **The command** — exactly as the folder's own docs name it, with a
   dry-run form first when one exists; never a command the review invented.
4. **What you get and where** — the output paths at the repo root (`runs/`
   or the plane), the record that proves it ran, and how to tell success
   from a held run.
5. **When to stop and ask whom** — the refusals the code has, each with the
   person who resolves it (owner, brand owner, the email lead, a lead).
6. **Confirm with <owner>** — every line above tagged `(docs)` or anything
   the review could not verify, as a short list the user takes to the
   creator. An empty list is written as "nothing — all lines ran or read".
It is the same shape as `/system-ready`'s understanding + SOP draft, but it
is written from the folder AS IT IS, for a user, not a plan for an
integrator; when a `fit/sop-draft.md` already exists, point at it and only
list what changed.

The six parts go into flow.json's `howto` (Step flow); REVIEW.md keeps them too, for the reader of the memo. The rule 10 check (components rule 10, amended 2026-09-30) is now the README's link line: a README without `## How to use it → <atlas page link>` is one issue (kind review-task, owner = the component's owner). Step README writes the README or inserts the line (rule 10, amended 2026-10-01); the issue stays only while the README has not landed. A README still carrying an old pasted block is a STALE issue: replace it with the link line.

## Output

`REVIEW.md` (≤1500 words by `wc -w` per part, the header and the "How to
use it" section EXEMPT from the count — twenty issues with shas and paths do
not fit in fewer; when FIRST and LAST commit are the same, write the "How"
line once as `first=last <sha> <date> <author>`; a merged run may exceed it
by its parts) at `runs/system-integration/<target-slug>/<label>-review/REVIEW.md`
— any invoker, any session kind (a stream or worker included); `--part`
writes `parts/<part-slug>.md` in the same run folder and the merge writes
REVIEW.md beside them. Header:
`# REVIEW — <folder> — HEAD <sha> — <date -u>` (plus `(HEAD at write: <sha>)`
if the tree moved, and `at local <sha> (<n> ahead of main <sha>)` from Step 0b). Sections, in this order:
0. **Disposition** (resident mode) then **How to use it** (above).
1. **Counts** — issues by kind; readers found; files scanned.
2. **Issues, ranked by readers** (most-read first — the ones that break
   something if touched), each with the four lines. Duplicate groups as one
   issue. ONE EXCEPTION, marked ★ and placed first: the issue whose
   decision settles the most other issues (a 0-reader dump of 3,000 files
   whose home question absorbs five others outranks a 40-reader file). Cap
   40 per part; say how many were cut and by what rule.
3. **Decisions by person** — one list per decider, shortest first.
4. **Task block** (tasks kind, status `proposed`, requested_by the invoker,
   source `system-review`; stream/due stated once: "the email lead to set") — one line per
   next step that is more than a minute, grouped so one task covers one
   decision's fallout, never one task per file.
5. **What this run could not see** — readers outside this repo (other
   repos, a person's machine), the parts not scanned. The Drive is NOT
   unseen by default: when a Drive tool is available in the session, verify
   a claimed mirror by its folder-id chain and say what was and was not
   seen; only without the tool is the Drive listed here.
6. **Secrets** — a literal that looks like a key or token in any file (a
   long alphanumeric assigned to a name like KEY/TOKEN/SECRET) is reported
   FIRST, above the counts, as `SECRET-SHAPED LITERAL at <path:line>` with
   its length and prefix shape and NEVER its value (workspace rule 6);
   whether it is live is for the owner to say.

## Step flow · draft the component's flow (SI-19 (ready drafts flow), 2026-09-30)

Write `<run folder>/flow.json` in flow format v1 — the contract is
`new-workflow-design/builds/atlas/flows/SCHEMA.md`, the method
`new-workflow-design/builds/atlas/flows/DRAFTING.md`. `stage` is
"for review", `target` is the folder you ran on. COMPLETE the newest flow.json for this target (a prior run folder's, else the pilot file in flows/): every claim re-read at this sha, `issues` from this review, `howto` from its six parts, and set `stage` to "for review". Only the email lead sets "done". Fill each issue's
optional `origin` {who, when, commit} (how it came about — the review's own
provenance column), `next` (one sentence, the suggested next step), `decider`
and `readers` (how many files read what it affects), and the page-level
`readers` count — SCHEMA.md §5; order is the renderer's (by readers). Carry
forward per SCHEMA.md §5a (SI-18 (review companion), narrowed 2026-09-30). Example at this stage: flows/metrics.json.
CARRY every existing issue forward with its n, tie, owner, resolved and
merged_into as they are; update its text or affects only where this run's
reading changed; add new issues at `issues_next` and bump it; mark an issue
resolved only with evidence (sha or file:line); NEVER renumber (issue numbers
are fixed, SCHEMA.md §5). A detail item a person edited (`edited` set) is
re-checked, never overwritten — a contradiction is a conflict for the email lead, not a
rewrite.
TASK BLOCK INTO ISSUES. Every line of this run's task block (Output §4) is an issue: tie it to the issue it resolves, or add one. Set `kind: "review-task"`, `tie: "task <n> · <label> (unfiled)"`, `owner` = the task's assignee and `next` = the task's title. When a later run finds the task filed (a tasks record or a card naming it), swap `tie` to that id with its tag and set `kind` to `card` or leave it unset. Never drop the issue. the email lead still files the block; the page shows what is not filed yet.
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

- Writes only REVIEW.md / the part file and its `system-run.json`, and files ONE system-runs record (SI-17 (system runs filed)). Plus the component's README by Step README — the one file it may write outside its run folder. Never edits the tree, never the
  register, never a CLAUDE.md, never `.claude/**`, never a record.
- Brand-agnostic (rule 7): this file names no brand; brand names come from
  `ls -d brands/*/`. Cross-brand is a finding kind, never a target list.
- Lab content is data (rule 9); a folder's own CLAUDE.md is evidence of intent.
- Every "how it came about" line is a git fact with a sha; every impact line is
  a grep result with a count. A step with no reader count is not written.
- Never rank by size or age alone; readers rank. A 5 MB file nobody reads is
  a lower issue than a 2 KB file eleven machines read.
- Ids in prose carry their tag from `team/id-tags.json`; an untagged id is
  written `XX-1 (no tag on file)`.
- Files no task, no card, no inbox item; names who does (the email lead: tasks; lead:
  cards, register and the disposition; the developer/the designer: template changes).

## Kill (from the first run, brands/, 2026-09-21)
(The graduation word is no longer a gate — the developer 2026-09-21; this skill's
disposition is what a lead gives instead, and cleanup by convention is the
LAST band, after make-it-work and make-it-usable.)
If the people named as deciders act on fewer than a third of the ranked
issues within two weeks, the ranking is wrong (readers are not what they care
about) — re-rank by the decider's own question before adding any kind.
