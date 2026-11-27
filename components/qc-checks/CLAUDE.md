# qc-checks/ — portable quality checks

A resident for check engines that read an asset plus declared truth and emit the
portable two-file findings bundle. Status vocabulary is `live | pending |
retired`; a check is `live` only when its declared test holds.

**Which checks component:** this one checks a FINISHED asset (text, a built
page, a review request) against declared truth and files findings to review.
`components/marketing-chain-checks/` (the owner's) gates a marketing chain's stages
by import. Neither calls the other (SD-2 (qc shared truth); B2 (triage design
calls), 2026-10-08).

## Definition

**qc-checks** — takes an asset (a local text or built-HTML file, a URL, or a review request `RQ-…`) plus declared truth (the `CHECKS` tables and a brand's `qc-dictionary.json`, passed by `--brand`); makes the portable two-file findings bundle (`findings.json` + a self-contained `findings.html`) and, only when filing is asked for, the same records on the review plane. Does not edit the asset, write under `brands/`, or file anything it was not asked to. Triggered by `python3 components/qc-checks/text_check.py --item RQ-… --text-file <file> [--html] --brand <brand> --out <dir>` (`--out` requires `--item`; to look without an item, `--text-file <file> --brand <brand> --dry-run` prints and writes nothing).

**Python API — the only names a caller may use** (the developer, 2026-09-30, I-139 (qc-checks answers); settles the review's INV-1 (callers use internals)): `text_check.check_request(item, records, …)`, `text_check.file_findings(bundle, …)`, `text_check.text_from_url(url)`, `text_check.TAGS`, and `text_check.Refused` (re-exported as `voice_check.Refused` and `avatar_walk.Refused`). Anything else is internal and may change without notice.

**Declared dependency — the mini worker's modules** (the developer, 2026-09-30, I-140 (qc worker dependency), "1"; closes the review's O2-a (worker modules)): the members import six modules from `platform/workers/mini-worker/` — `prereview_adapter`, `infer_run`, `clone_root`, `job_env` (text_check.py:122, :208, :214, :946), `shadow_judge` (voice_check.py:454) and `page_capture` (avatar_walk.py:430) — with that folder appended to the path at text_check.py:127-131. Sanctioned as it stands; REVISIT if a worker change ever breaks a check. O2-b (review private calls) CLOSED by RV-67 (review public validators), merged 8ab3c7f66 (2026-09-30): the members call only review's public `people`, `asset`, `anchors`, `capped`.

## New-resident checklist — CONFIRMED by the developer 2026-09-30 (I-139 (qc-checks answers), "1" — confirm as written)

1. **Engine + owner — the designer, permanent from 2026-10-01** (relayed by ◆ PLAN [a1b3f2], verbatim, ~06:39Z, the developer: "QC checks permanent", answering "qc-checks engine: hers for this work only, or permanently? … I'd make it permanent", batch 551). The engine is the code in each member;
   the designer owns its implementation and contract compliance (the developer until 2026-10-01).
2. **Definitions + curator — the email lead.** Definitions are the `CHECKS`
   tables and the QC dictionary schema. the email lead, as human QC lead, curates what
   deserves to be called a defect; brand content remains under
   `brands/<brand>/` and enters only by argument.
3. **Plane — no plane of its own.** A checker emits a findings bundle.
   When filing is requested, its unchanged `records[]` go to the review plane
   through `components/review/review_request.py`.
4. **Manifest — none of its own.** The declared output is
   `new-workflow-design/builds/upright-qc/findings-bundle-contract.md`; each
   record obeys the frozen review manifest at
   `platform/data/kinds/review.json`.

## Members

| Member | Status | Contract |
|---|---|---|
| `text_check.py` | `live` | `--out <dir>` writes `findings.json` and self-contained `findings.html`; a clean run writes `clean: true` and no records |
| `voice_check.py` | `parked` (the developer 2026-10-08, I-141 (voice and walk): never run; un-park with one real campaign run) | reads the brand map's `language_bank` checklist at run time; `--dry-run` prints only, while `--out <dir>` requires `--item RQ-…` and writes the shared two-file bundle; becomes `live` after the declared real campaign run |
| `avatar_walk.py` | `parked` (the developer 2026-10-08, I-141 (voice and walk): never run; un-park with one real run against a preview; its slow browser test is skipped in the hourly sweep while parked) | `--brand --avatar --pages <ordered urls>`; ONE run over the whole funnel, so the bundle's `asset` is the ORDERED LIST of page pointers (contract §3a) and `--out <dir>` also writes `pages/<n>-<name>.png`, one capture per page; one record per page plus one closing record, every objection cited to a bank heading or marked `NEW`; becomes `live` after one real run against a preview |

## What the walk needs from the machine

It drives QG-6 (screenshot baselines)' `qc_probe.js` — so `node` and Chrome must
be on the machine — and spends ONE metered call per walk through WM-34 (infer
action). A run with no `OPENROUTER_API_KEY` in its `infer` grant refuses BEFORE
a page is opened, so nothing is loaded and nothing is spent. A walk is per funnel
VERSION, never per edit.
