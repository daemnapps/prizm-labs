# Ad Variations

## How to use it → (team dashboard)

**One ad that already worked goes in. A variation plan comes out.** Every
element of the ad marked a proven LOCK or a LEVER to test, with evidence from
the brand's whole teardown corpus; N variations that each move one lever,
highest estimated impact first; new formats recombined from parts the corpus
already proves; the merge recipe for each (which seconds of the original are
reused, what AI makes, on which route, at what cost); the QC gates each must
pass; and the static and landing-page section each one feeds.

It plans. It generates nothing. Production is NOT built yet: no component reads
`variation-plan.json` today (2026-10-08) — no reader yet.

Page: **Ad Variations** — (team page) (register: `context/artifacts.md`). Markdown
mirror of the page: `AD-VARIATIONS-damon.md`.

## Inputs

| Input | Where it comes from |
|---|---|
| The proven ad's teardown | `runs/video-teardown/<brand>/<slug>/` — triage, the record with its verbatim transcript, the doctrine read, the audience read, the replication spec, `doctrine.json`, `transcript.json`, `sound-sheet.json`, and `run.json` (for the source video on Drive) |
| Its metrics | any `runs/swipe-*/<brand>/*/manifest.json` row whose `teardown_run` names the run (views, likes, saves, comments, shares, duration, caption) |
| The brand's corpus | every other teardown run of that brand with metrics — counted into the Variable Index |
| Brand context | `brands/<brand>/`: position.md, story.md, identity-anchors.md, compliance.json, products/heroes.json + the hero product files, the run's core avatar (profile, sub-avatars, language bank), the casting roster, funnels/README.md |
| Optional campaign plan | `--plan <file>` — a plan whose page sections the congruence stage may name |

## Outputs

Per plan, in `runs/ad-variations/<brand>/<label>/` (label = the teardown run's name unless given):

- `variation-plan.json` — **the contract** (schema below and in `definitions/variations.schema.json`)
- `VARIATIONS.md` — the Markdown record
- `deliverable/` — both, where the runs standard says a deliverable lives
- `measure.json` / `measure.md` — stage 0, the file's own clock
- `evidence.md` — the corpus table stage 2 quotes from
- `stageN--sent.md` / `stageN--<label>.md` — every prompt exactly as sent, beside what came back
- `run.json` — the assignment, the model and prompt hash per stage, the brand files read

Per brand, in `runs/ad-variations/<brand>/variable-index/`: `variable-index.json`, `VARIABLE-INDEX.md` (the index's Markdown mirror), `coded/<run>.json`.

## The stages

| # | Stage | Model | Reads | Writes |
|---|---|---|---|---|
| index | Variable Index | rules + Claude Sonnet coder per post (cached) | every teardown run of the brand + metrics | the index |
| 0 | Measure | none — ffmpeg | the source video: the run.json path, else this machine's Drive mount, else Drive by file id (video_url) | hard cuts, soft changes, loudness every 0.5 s, fps |
| 1 | Anatomy → elements | Claude Opus | teardown, spec, doctrine, audience, measurement, this ad's index values | beats on the file's clock; the 19 fixed elements with index ids; record-vs-file differences |
| 2 | Locks vs levers | Claude Opus | elements + the evidence table (computed) + brand rules | LOCK / LEVER per element, evidence quoted, levers ranked (ESTIMATE), rulings needed |
| 3 | Variation matrix | Claude Opus | calls, audience, avatars, language bank, cast, products, rules | V00 control + N variations, each change as `variable: from → to` |
| 4 | New formats | Claude Opus | the index by family, combinations already run | K untested formats, each part a proven index value with its evidence |
| 5 | Merge recipe | Claude Opus | beats, variations, formats, routes, cast, rules | per variation: seconds reused, what is made, route + units, TEST alternative, shared pieces |
| 6 | QC gates | Claude Opus | variations + recipes, gates, forced gates | the gates per variation with a variation-specific pass line |
| 7 | Congruence | Claude Opus | variations, the element library's static and page formats, funnels, plan | the static format and page section each variation feeds |

After stage 7 the machine assembles `variation-plan.json`: it prices every recipe
(units × `definitions/routes.json`, rolls and overshoot applied, shared pieces
costed once), adds any gate a route forces, checks every change names a real
index id, and writes what its checks found into `problems`.

## The Variable Index

Every adjustable variable the teardown records — 90 today, in eleven
families (hook, structure, audience, proof, product, talent, look, sound, edit
rhythm, text, offer and ask). Definitions live in `definitions/variables.json`:
id (`V-hook.04`), name, the teardown field(s) it is read from, type
(categorical, numeric, multi, text), how it is read (`rule:` = straight from
the record; `coder:` = one Sonnet call per post against a fixed vocabulary),
which production routes can change it, and a cost class.

The build counts every value across the brand's posts: count, share of views,
share of saves, save rate, like rate, and share of the top-quartile posts'
views. A variable is **lock-leaning** when one value holds ≥ 60% of the
top-quartile posts' views, **lever** otherwise (text is always a lever). A
value the coder cannot place is kept as `other: <label>` and listed as a new
value — never dropped. Rebuilding is cheap: only new or changed teardowns are
coded again, so adding posts or a brand grows the index and every value lists
the runs it came from.

Stages 2–4 and `variation-plan.json` name every change by these ids —
"V-hook.08: reacts-to-another-video → …".

## The contract — `variation-plan.json` (`ad-variations/1`)

```
schema, brand, built
source        teardown_run, post_id, url, metrics{rank, views, likes, saves, …}, video (Drive path)
index         path, built, runs
measurement   duration, fps, shots[{n,start,end,len}], soft_changes, loudest, quiet_windows_s,
              music_present_s (from the music stem, when Demucs is on the machine)
beats         [{n, start, end, section, picture, words, sound, attention, why}]
elements      [{key, name, what, seconds, variables{V-id: value}, source, call LOCK|LEVER,
                evidence, impact_rank, impact, impact_basis (ESTIMATE), needs_ruling,
                calls[{part, cut both|organic|paid, call, variables, evidence, impact_rank}]}]
record_vs_file, lever_order
variations    [{id (V00 = control), title, kind, changes[{variable, variable_name, element, from, to, bank_ids}],
                locked[], hypothesis, confirms_if, kills_if, audience{avatar, sub_avatar, cut}, order_reason, needs_ruling,
                recipe{reuse[{seconds, what}], make[{what, route, units, usd, hours, shared, chain_order, start_frame}],
                       cheaper_test{replaces_route, route, units, usd}, seam_repair, blocked_by},
                cost{usd_own, usd_standalone, usd_with_test, hours, shared_pieces},
                gates[{gate, name, pass_line, check, auto_check, forced}], congruence{static, page}}]
formats       [{id, name, what_the_viewer_sees, parts[{variable, value, evidence}], status "NEW — untested",
                closest_existing, why, seed_footage, to_make, audience, recipe, cost, gates}]
shared        [{key, piece, route, units, usd, used_by[], why}]
totals        variations, formats, usd, usd_with_tests, hours, not_included
damon_decides [], problems []
run           stages{prompt, sha, model, seconds, chars}, llm_cost, brand_files_read
```

Route ids resolve in `definitions/routes.json`, gate ids in `definitions/gates.json`, variable ids in `definitions/variables.json`.

## Routes and rates

The locked choices: GPT Image direct via OpenAI ($__ per still, 3 rolls
costed); Seedance 2.5 on Higgsfield, 720p ($__ per second, +30%
overshoot); Genjutsu motion transfer on Higgsfield ($__ per ~4 s clip);
the local studio on the owner's Mac for cut-outs, tracking, interpolation, stems,
captions ($0). Wan 2.2 Animate Replace and Kling 3.0 Motion Control on fal
are listed as **TEST** — a recipe may offer them as a cheaper alternative,
never as the default. Rates are from the Model Map v1 (27 Sep 2026); a price
change is one edit to `routes.json`.

## Cost per run

Planning: seven Claude Opus calls through `claude -p` (the teardown's text
route, via run-kit). Measured on the two test runs: ≈150k tokens in and ≈60k
out — **≈ $__ per ad** at list price (#1 $__, #2 $__), plus an
occasional Sonnet call when a stage's JSON needs its punctuation repaired.
About 20–25 minutes per ad. The Variable Index cost **$__ once** for the 60
Brand B posts on Sonnet; after that only new posts are coded. Stage 0 is free
(ffmpeg and the local Demucs). No production money is spent here.

The machine cost of the plans themselves (what production would spend):
#1 — 11 variations + 5 new formats, $__ on the locked routes, $__ if
the TEST motion routes pass; #2 — $__, $__ with TEST routes.

## Tests

`python3 machine/test_ad_variations.py` — no network, no model: the rule
extractors on a synthetic teardown, every rule in the definitions exists, the
element list points at real ids, cost arithmetic, shared pieces costed once,
TEST-route arithmetic, forced gates (including seams on chained clips), every
prompt field supplied, no prompt names a brand.

## Running it (for a session or operator)

the owner says "run ad variations on <brand> post <id>". The session: checks the
post has a finished video teardown (runs one first if not); refreshes the
index (`python3 machine/run.py index --brand <brand>` — cached posts cost
nothing); dry-runs (`python3 machine/run.py plan <id> --brand <brand> --dry-run`);
runs it without `--dry-run`, adding `--plan <campaign plan file>` when a plan
names the page sections; rebuilds the page (`python3 machine/run.py page`) and
republishes it over the same link. `--rerun-from stageN` reruns one stage and
everything after it; a changed prompt reruns itself and what depends on it.

## Calibration against the hand-made spec (27 Sep 2026)

Post #1 (TikTok 7167399325910289706) was planned automatically and compared
with the hand-made Asset 01 spec (`the team notes`).
The full side-by-side is `notes/calibration.json`, rendered on the page.

What was weaker, and what changed:

| Gap in the first run | Change |
|---|---|
| Read the sound from the mix only and concluded there was no music; the hand spec found a bed at 7.0–10.8 s and a hit on the reveal at 14.5–15.5 s | Stage 0 separates the music stem (local Demucs) and measures it; stage 1 v2 reads the stem before the record's Music line. Now finds both. |
| Did not see that post #3 is the same template with a different reactor — the brand's own half-run test of the reactor | A computed closest-posts table (what a viewer sees and hears; the same first line or sticker wording weighted ×4) goes to stages 2 and 3. #3 now tops it. |
| Locked too much on corpus counts (the whole hook layout, who reacts, captions, SKU, talent, end frame) | Stage 2 v2: call the parts separately, call organic and paid separately, a value everyone shares is not proof. v3: rank the top ten levers, the rest "later"; the nineteen keys only. |
| Variations changed three variables at once; two were new formats | Stage 3 v2/v3: at most two variables, no format changes, check the paid cut's needs (sound-off, 4:5, one offer), cast person-levers from the roster by name, test a second hero SKU. The machine flags any non-control variation with more than two changes. |
| Stage JSON sometimes did not parse (a straight quote inside a value) | Every stage prompt now says how to write quotes; a failed parse is repaired by a small model and the repair is kept beside the run. |
| (the owner's production rule, 27 Sep) chained generated clips popped at the joins | Stage 5 v3 makes chained clips in order, each starting from the real last frame of the one before; stage 6 v3 and gates.json add a seams gate (≤ ~2× the median frame step at every join); an optical-flow bridge over ~10 frames each side is the fallback only. |

Where it still falls short: it cannot see the video. The picture on each beat
comes from the teardown record, so it cannot spot reused footage (the hand
spec saw that #1's background is post #6's clip) or correct a record that
puts a picture on the wrong side of a cut. After calibration the plan covers
seven of the hand spec's ten levers; it did not plan the problem line, the
faceless demo inserts or the motion-transfer pitch swap.

Prompt versions now live: stage 0c v1, stage 1 v3, stage 2 v3, stage 3 v3,
stage 4 v2, stage 5 v3, stage 6 v3, stage 7 v2. Earlier versions are in each
stage's `archive/`.

`machine/format_swap.py` (the one-step concept+format → spec shortcut) is superseded by the proven ad → new format chain: `PROVEN-TO-FORMAT-damon.md`, `machine/proven_to_format.py`.
