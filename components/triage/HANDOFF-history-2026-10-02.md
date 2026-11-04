# Triage handoff history, moved from new-workflow-design/builds/atlas/HANDOFF.md on 2026-10-02

Kept verbatim as the record of how the design got here. The current state is HANDOFF.md in this folder. Paths in these blocks were written before the move: `triage/component/…` is now this folder; `triage/proposals/…` is `proposals/`; `triage/red-tests/…` is `history/red-tests/`.

# ★ TRIAGE — STATE 2026-10-02 06:03Z (≈ STREAM · atlas [6941d8]) — READ THIS FIRST; the 01:39Z block below is history

## UPDATE 2026-10-02 06:22Z: ownership and the two-week evaluation (the team, this session)
- the team, verbatim: "I will review the overall component approach, the two lists in a meeting soon. ANd we will decide on the option 3 question. I will remain component owner of the triage component for now. And the team is owner of components / atlas (both triage owner and the theme itsemf), and the team for operations. FOr both of them there is a next step for each of them to evaluate their own use case and consolidate their feedback to refine the overall component / theme design over the following two weeks. Consider this first and update artifacts accordingly"
- Roles now in the contract and packs: engine owner the team ("for now"); theme owner + triage owner the team (components / atlas) and the team (operations). Packs carry `theme_owner` and `evaluation`.
- Evaluation 10-02 → 10-16: both lists re-run for 10-09 (this stream) and 10-16; one consolidated findings file per theme (proposed `themes/<theme>-FEEDBACK.md`), each finding tagged theme or engine. The split of findings tests the contract.
- Approach page republished as the meeting document: who owns what, the agenda, the Option 3 box (recommend 3, ask the owner first), the two weeks.
- Filed by the lead at 0d119a6c5: decision log (ownership; Option 3 not filed, decided at the meeting); tasks TSK-20261002062419-evaluate-components-atlas-triage-theme (the team evaluates components) and TSK-20261002062420-evaluate-operations-triage-theme (the team evaluates operations), due 10-16, each naming its FEEDBACK file, the 10-09 re-run and the meeting page. The 10-09 re-run is this stream's, no card.
- 06:35Z, the team: "combine the themes artifiacte into the approach, and remove red tests from themes for now. Also layer in how the component is proposed to work in the same artifact per our atlas conventions". Done: the approach page (4BsAyTeRYP7Z1UWBgcpx6s) is now Part 1 (meeting: owners, agenda, Option 3, themes, cross-refs, patterns, lessons, the two weeks) + Part 2 (the triage component to the atlas component-page standard, rendered by /atlas-view from flow-triage.json, CSS scoped under .ap). flow-triage.json redrawn: themes not domains, nine passes, packs as Inputs, the team engine owner, red tests out; issues #10–#14 added (snapshots, theme code in tools, guessed refs, ops targets/ads owner, log extension). flowcheck: 49 agree · 8 draft-error (all "components/triage not built") · 1 stated. Themes view (MyiJcUuxeYxQ6BHdtnWibW) marked merged; standalone component page (QXsWLWkkujn2MU8abPniay) re-rendered from the same flow. Header "Owner: not in the atlas" is the data-only rule (triage is not an atlas resident yet).
- Batch received between 06:35Z and 06:37Z (date -u before and after), the team verbatim: "1. even though we are focusing on two themes, the point is that this will be gernealized for more themes in the future (so just note that but we dont need to design those yet) 2. then the overall component and theme approach should be more focuxed on specific it woudl generally work, but use both current themes are real examples 2.1 One notable point is - how we actually prioritize is not hard coded in, each theme has its own priotization list 2.2 Remove weekly digest, lets start with the decision log, but then we want thed etails of the decision log itself". Done: Part 1 now leads with how it generally works (nine steps, engine column + components and operations columns), "Prioritising: each theme brings its own list" (both tier lists from the packs), "The decision log" (eight acts with status, record fields, one illustrative record per theme, where it lives, who reads it, vs the org decision log), a "More themes later" note. Weekly digest removed everywhere (page, flow, contract, packs; Option 3 limit now "every change in the decision log with a one-line undo"). Contract gains "Priority is the theme's" and "More themes later". The owner-digest page (AWGmifrnHKUR1Z8LiRpYMr) is superseded; not deleted.
- 06:41Z, the team: "the group by logic should be custom to each theme as well". Done: packs carry `grouping` (ordered rules, first match wins): components close-out (1) → shared fix (24) → decision group (11) → local batch (47); operations detector per brand (5). Contract pass 5, page ("Grouping and prioritising"), flow table and engine label updated; cites re-pinned to 76eb340b8 (flowcheck 47 agree · 8 draft-error · 1 stated). The engine code itself still hard-codes both groupings (metrics_insights.py, the components dry run): part of the refactor, open issue triage #11.
- Still to do: queue pages carry no theme-owner or evaluation line yet; add at the ATL-31 (remaining issue briefs) re-render (components) and the 10-09 re-run (operations).

## Direction (the team, 2026-10-02)
- The focus today is **two themes**, components / atlas (triage owner the team) and **operations** (triage owner the team), "to design and present the overall approach and get team feedback". **Red tests are set aside** for this round; their structural lessons are kept.
- Each theme carries **cross-references by general design, specific to the theme**:
  - components: relates components, the atlas, brand folders;
  - operations: relates metrics, and the P&L systems the team will build (several pieces);
  - both: the general PM lists and Slack channels ("to be determined next").
- Operations also checks **patterns over time, positive or negative**, that should influence decisions.

## Rulings landed today (decision log, filed by the lead)
- the team owns the engine.
- Each list names its triage owner, who triages it first: the team for component issues; the team for red tests (paused); the team for operations (filed as "metrics insights", d92e9c68a; renamed operations on the team's framing).
- "Ready" means the triage owner can do it alone.
- the team may close an issue with evidence (SCHEMA §5a).
- cause and blocked_by are two fields.
- One `triage` record kind (ATL-28 (triage record kind)).
- Actions are ranked by weighted items; age escalates, never past P1; no P0 without a live path.
- Issue summaries stay on Claude: TI-24 (red-test summaries GLM) blind eval, GLM 235 vs Claude 259 and 8 vs 2 factual errors, branch closed unmerged.
- GLM is kept for test-only fixes: TI-23 (red-test fixes on GLM), 9 of 10 merged.

## Pages (custody)
- **Approach for team feedback (the deliverable):** (private page) (triage/component/approach-two-themes.html)
- **Components queue:** (private page) (v10). 685 issues, 83 actions, triage-owner-first tags (now 230 · after 297 · draft 110 · owner 48), 113 ATL-29 (drafted changes) diffs, 48 ATL-30 (decision option cards), explain prompts, Option 3 panel.
- **Operations queue:** (private page) (v2). 13 signals in 5 actions, by money at stake, with cross-references. On I-164 (metrics insights theme) for the team.
- **Engine and theme view:** (private page). Pre-operations; republish when the contract settles.
- **Triage log proposal:** (private page)
- **Owner digest example:** (private page)
- **Red-tests queue (paused):** (private page)
- **Triage component page:** (private page)
- **Proposal (historical):** (private page)
- All private; the team shares them.

## Files (all in this build)
- **Contract:** triage/component/CONTRACT-themes.md. Nine passes and pack fields; amended with typed areas, the item word and close semantics from the pack, and the cross-reference design.
- **Packs:** triage/component/themes/{atlas,operations,red-tests}.json (28 fields each, incl. `refs`).
- **Findings:** operations-FINDINGS.md.
- **Tools:**
  - tools/triage_page.py (the renderer, Python 3.9-clean);
  - tools/metrics_insights.py (operations detectors: data health, 28-day movement, sell-out before resupply, patterns: order value, Meta returns fit, floor, weekday);
  - tools/triage_refs.py (cross-reference resolver; text matching, noisy: 3 of 8 real for email-production#1).
- **Queue models:** triage/queue/model-{components,operations,red-tests}-2026-10-02.json.
- **Proposals:** triage/proposals/ (Option 3 scope, owner digest example, triage log).
- **<brand> Slack census:** themes/slack-<brand>/: 39 human messages in 30 days, too quiet; Slack waits.

## Open on the team
1. Option 3: may the triage owner apply a ruled default or a spelled-out fix with the owner told, not asked? Ask the owner first. Proposed limits: test proves it; no assertion weakened; no live-pipeline behaviour change; weekly digest with undo; logged first; quiet components first.
2. The triage owner's four conditions for working alone.
3. The ads owner for each brand (decider of the <brand> spend signals).
4. Targets for operations (none exist).
5. Summaries on every item. the team, ~06:10Z: "these lists should also include the udpated issue summaries as well". Operations is done in this stream (eight parts on all 13 signals). For components the held C card now covers 464 items (493 without a summary, minus 29 that look fixed and only need closing), on Claude. Carded as ATL-31 (remaining issue briefs): 8 parts of 56 to 59 issues each, sidecars appended. DISPATCHED e8d0eac9f on the team's typed "Go"; the lead merges part by part. When parts land, re-render the components page and republish it (the renderer reads the sidecars as is).
   **Relay rule (corrected by the lead, 10-02):** verbatim relays from this seat DO count for dispatch in dev-engineer, if they carry the line the team was answering. Always include that line.
6. The `triage` record-kind extension (five acts, plus areas, commit and test) and a SCHEMA §5a reopen sentence. To card via the lead.
7. Whether cards and PM tasks carry a declared `refs:` line.
8. <brand> the team Slack token scope is broader than its job (channel and DM history). Re-issue narrower: his call.

## Action-group summaries (the team 10-02: "If there are actions groupings there should a summary for the action group as well. Try this first on operations")
- Operations: done. Every action carries the eight parts for its group, built from its signals (a44852885, page v4).
- Components: 23 of 83 actions have a summary: the ATL-26 (action briefs) briefs, shown inline. The other 60 (1 shared without a brief, 11 small groups, 47 local batches, 1 close-out) are to be derived from their issues' summaries once ATL-31 (remaining issue briefs) lands. No extra agent work. the team 06:1xZ: "i am having lead build the rest of the briefs".

## Next for this stream
0. When ATL-31's parts merge: re-render components, derive the 60 action summaries the operations way, and republish 1Zac5idyUk2e5THqbzpGiQ.
1. Refactor triage_page.py and triage_dryrun.py to read everything theme-specific from the packs (≈ a day).
2. Wire declared refs once ruled; add PM tasks and inbox as reference sources.
3. Join the P&L systems to operations as the team lands them.
4. Republish the engine and theme view with the two-theme focus.
5. Re-run both lists for 10-09 and 10-16; collect the team's and the team's consolidated findings on 10-16 (theme vs engine).
6. Red tests resume after this round.

# ★ TRIAGE — STATE 2026-10-02 01:39Z (≈ STREAM · atlas [6941d8], swept for /focus) — READ THIS FIRST

## UPDATE 2026-10-02 02:10Z: rulings landed; queue format test published
- Ruled (decision log 981094a4a, 4b36a7a90): the team owns the engine; the team triages EVERYTHING first; the team may close an issue
  with evidence (SCHEMA §5a: `resolved` + `resolved_by: "pm"`; render.py f25c4dac3, crosscheck.py 0a414be2d); cause and
  blocked_by are two fields; one `triage` record kind (ATL-28 (triage record kind) merged 9c1367b81); actions ranked
  P0 8 · P1 4 · P2 2 · P3 1, age escalates (never past P1), no P0 without a live path. TI-22 (first failing assertion)
  merged 80d5854a5. #7 ignored, #8 deferred. Still open on the team: the team's four conditions for clearing ALONE.
- Queue format (the team 10-02: Claude-actionable prompt, click-in summaries, three whos): tools/triage_page.py draws
  triage/queue/model-*.json. Components 685 → 83 actions: (private page) (v3, replaces
  the dry-run page). Red tests 34 → 27 actions: (private page) (v2). Commit 00b5f98f8.
  Not built yet: the live-path check for P0; the team's acts written through the `triage` kind.
- Back-test (triage/red-tests/backtest-2026-10-02.json): 54 suites cleared since 09-20, engine run blind against what actually
  cleared them. Class matched how it cleared on 34/54. Engine groups: 10 of 17 pairs cleared in the same commit (59%), but
  only 10 of 40 co-cleared pairs were predicted (25%), because the lead batches unrelated re-pins into one card.

## What it is
the team wants a general TRIAGE component: any long list in; a sorted, grouped queue, action briefs and one weekly ask per
decider out. the team triages first, and nothing reaches an owner without her. This session does STRATEGY. Workers do
the building, through the lead (the team 01:08:09Z: "Targeted but can we have workers do it? I want to work with this
session on strategy").

## Rulings and directions (verbatim times; the decision log is the lead's)
- README required and generated (08:22:42Z 10-01). Ready check is the owner's call; no batch /system-ready
  (08:31:56Z, decision log ed4966da9). Retire old views (10:08:05Z): done.
- Issue brief standard: SCHEMA §5 has eight fields (why, impacts{people,components,machines}, evidence, fix,
  fix_impact, if_ignored, lane pm|owner|decision, severity P0–P3), landed by the lead in 6838d3556. My half:
  render.py shows them (217a962e2, skill:), and crosscheck.py enforces them only on issues added or reworded after
  6838d3556 (675b4a80c).
- the team triages first (the team 10-02, a direction, not yet ruled). The "pm" lane means "the team triages and answers;
  the owner still says yes" until her four conditions are ruled.

## Artifacts (custody)
- Proposal, issue format plus the team-first flow: (private page) (triage/PROPOSAL-issue-briefs.html)
- Component-issue dry run, with levers, clears-with and the output-home brief: (private page)
  Data: triage/dryrun-2026-10-02.json, clusters-2026-10-02.json, BRIEF-output-home.md (eb4121ac1); script
  tools/triage_dryrun.py.
- Red-test trial, blind engine vs ◆ PLAN's hand triage (e9995982a): (private page) (c0ce1a03f)
- Red tests as the component would sort them: (private page) (red-tests/queue-2026-10-02.html)
- Triage component design: atlas page drawn by render.py from its flow: (private page)
  (triage/component/flow-triage.json + triage-atlas-page.html, 599ef1ab9)

## Numbers (verified)
- Component issues: 685 open. 39 are already fixed (closable now; no closure path exists, see design issue #4) and 5
  are partly fixed. 402 of the 646 still open clear in 23 shared actions; the other 244 are local or one-off.
  P0 101 · P1 91 (keyword draft: in a sample of 7 P0s, 2 were false).
  Top levers: definition lines and registry rows 41 · LIBRARY clauses 41 · repoint moved paths 35 · Drive through
  gdrive-creator 30 · output-home ruling 29 (+20 follow-on moves) · records adapters 28 · keys register 27 ·
  register brandpath 11.
- Output-home brief: Option A (close the 09-17 rule's gaps, plus a hook) resolves about 34. It is the team's or the team's to
  rule (a wall). Open question: the owner's 09-18 research-gatherer carve-out.
- Red-test trial (34 suites): 26 agree · 4 same action, different label · 2 partial · 2 differ. The lesson: split the
  cause class from blocked_by. 4 shared actions clear 10 suites: d20151bec ×3, fc403711c ×3, WM-120 (system second
  slot) ×2, WM-106 (records not copies) ×2; WM-106's approval must also cover team/plans/*.md.

## Cards in flight (the lead's)
- ATL-26 (action briefs): 22 briefs into triage/briefs/. Parts A and B merged; part C round 2 is running (dfe3e05b0).
- ATL-27 (P0 P1 issue briefs): 192 issues into triage/issue-briefs/<component>.json. Part A merged (f90eb13a7) with
  10 files; B–D are running.
- **Next for me when both land:** rebuild the triage dry-run page. Link every lever to its brief, and show the eight
  parts for every P0 and P1 issue. Then it's ready for the team, with a note on what she is judging.

## Open on the team
1. Output-home Option A, which the lead is putting to him.
2. the team's four conditions, which the lead is putting to him. Send the proposal page to the team and share it first.
3. The triage component design: the engine owner (proposed: the team), plus design issues #1–#9 on its page.
4. ◆ PLAN's red-test note: "go on the batch" plus its rulings (TI-21 (last two singles), TI-20 (bench prompts
   ruled), WM-106 (records not copies), the inbox species).
5. email-production #2: owner changed to "the team (development); the owner (content)" by the 08:47Z rerun, which is unruled.
6. ATL-18b (workflow view): on hold for his approach call.
7. Strategy agenda, still open: keys convention (27 + 14 issues) · one index over runs/ vs 16 adapters (~28) ·
   public-surface policy (41) · workflows. Customer service: check the helpdesk's own AI triage before building an
   adapter.

