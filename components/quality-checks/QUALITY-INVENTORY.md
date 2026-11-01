# Quality Check Inventory (2 Oct 2026)

Page: `quality-inventory.html`

This lists everything in the workspace whose name says quality, QC, check, review, judge, gate or audit. Each entry says what it actually does and who owns it.

## The four components

| Folder | Owner | What it does | Judged by |
|---|---|---|---|
| `components/marketing-chain-checks/` (was `quality-checks/` until 2 Oct) | the owner | Checks the ads and briefs our chains make and holds bad work. It has the shared hold (5 gates), the price/unfilled/copy checks, the creative review after every stage, the QC log, and the viewer check. | A machine plus code |
| `components/qc-checks/` | Engine the developer · definitions curator | Checks finished text and pages for defects. `text_check` is live, `voice_check` and `avatar_walk` are pending. Findings are filed to `review`. | Code plus a dictionary, then a person |
| `components/review/` | Engine the developer · definitions curator | Not a checker. It records a person's verdict: request → verdict → close (RQ-… records). | A person |
| `components/page-picture-review/` | the developer | Numbers the picture slots on a built page and records the decisions. | People |

qc-checks files its findings into review. marketing-chain-checks calls neither. Its notes used to say it called qc-checks, but no code ever did, and that line is removed.

## Two layers (marketing-chain-checks, from 2 Oct)
| Layer | Checks | Built | Not built yet |
|---|---|---|---|
| 1 · Inside the loop | each ad or brief as it moves through a chain | the hold and 5 gates · price / unfilled / copy checks · creative review after every stage · viewer check | — |
| 2 · On the loop | the chain itself: working and current? | QC log: every round filed, recurring causes written up as chain changes | same viewer complaint across briefs → prompt change · viewer calls vs live Meta results · prompts and avatar files current |

Other checks on the system, owned by others: /system-review and the control room's machine check.

## Name clashes
- **quality-checks vs qc-checks**: resolved 2 Oct. the owner's is renamed **marketing-chain-checks**. the developer ruled on 30 Sep that the two stay separate (SD-2). A stub at `components/quality-checks/` forwards old imports.
- **review** means five different things:
  - quality-checks `review.py`: a machine reviews each stage.
  - `review/`: a person's verdict.
  - `page-picture-review/`: decisions on page pictures.
  - `/system-review`: does a folder follow the rules.
  - `review_page.py` in meta-upload and language-layer, and `build_review.py` in email: a look-over page for a person.
- **QC** means:
  - `qc-checks/`: the developer's defect checks.
  - `/qc-check`: runs the developer's text check.
  - video-production `qc.py`: every check on one video ad.
  - email `sweep/qc.py`: rebuilt emails checked against their sources.
  - `qc_log`: there is one log. Video-production's copy points to it.
- **As the avatar** means two things:
  - The viewer check in quality-checks (live) scrolls a brief inside the avatar's feed.
  - `avatar_walk` in qc-checks (pending) clicks through a built funnel.
- `/component-check` asks whether a tool already exists. `/gut-check` is a blind review of decision documents. Neither one checks ads.

## Checks built inside each tool
Every `gates.py` holds work through marketing-chain-checks' shared hold.
- **video-teardown:** swipe match, cast match, spoken check, elements check, hole fill and claims check, 4f audit, viewer gate
- **copywriter:** 4f audit prompt
- **video-production:** qc.py, voice QC, audio check, elements and library checks, stage-5 / motion / variation QC prompts, plate check
- **video-edit:** sync check, frames vs cut sheet
- **image-production:** judge, gates, headline audit
- **image-teardown (lab):** judge, draft judge, gates (elements, copy, viewer), check
- **image-edit:** compare judge
- **casting:** judge, gates
- **email-production:** sweep/qc.py, check_month, stage 8c check, review page
- **marketing-calendar:** gates, review, brand check
- **ad-variations:** stage 6 gates
- **audio-teardown:** effects check
- **intake, research-gatherer:** gates
- **lab teardowns (copy, email, page), outlier brief, pages:** gates
- **meta-upload, language-layer:** review page
- **naming, metrics, brandpath:** data self-checks (not ads)
- **system-integration, control-room:** checks on the machine itself (not ads)
