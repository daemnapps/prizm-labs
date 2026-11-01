# Triage: the core engine and its themes (contract, draft)

2026-10-02, ≈ STREAM · atlas [6941d8], on the team's word: "We want the component to work so it is theme agnostic as well. Considering the atlas first. It has its own set of owners and prioritization logic and flow. But each theme will have its own as well but routed through the same core engine" — then "Go".

**Status: a draft for the team (engine owner, ruled 2026-10-02) to read, not ruled.** This round's two themes (the team, 2026-10-02) are `themes/atlas.json` (components / atlas) and `themes/operations.json` (operations). `themes/red-tests.json` is paused, with its lessons kept.

## Who owns what (the team, 2026-10-02)

the team: "I will remain component owner of the triage component for now. And the team is owner of components / atlas (both triage owner and the theme itsemf), and the team for operations. FOr both of them there is a next step for each of them to evaluate their own use case and consolidate their feedback to refine the overall component / theme design over the following two weeks."

| Role | Holds | Decides |
|---|---|---|
| Engine owner | the team, "for now" | The core: passes, item shape, shared page and log, ref resolvers. Any change every theme feels. |
| Theme owner | the team (components / atlas), the team (operations) | The pack and its adapter: item word, cause classes, priority rules, refs it carries, what the triage owner may do alone. |
| Triage owner | the team (components / atlas), the team (operations) | Works the list first (pass 7), closes with evidence. |

Theme owner and triage owner are one person in both themes today. They are kept as two pack fields (`theme_owner`, `triage_owner`) so a list can later be owned by one person and worked by another.

**Evaluation, 2026-10-02 → 2026-10-16.** Each theme owner works their own list as the real job and hands in one consolidated set of findings. Each finding is tagged **theme** (a pack change, the theme owner's) or **engine** (a core change, the team's ruling). Proposed homes: `themes/atlas-FEEDBACK.md`, `themes/operations-FEEDBACK.md`. Both lists are re-run on fresh data for 10-09 and 10-16. The theme/engine split of the findings is itself the test of this contract: mostly theme findings means the split holds; mostly engine findings means it is redrawn before a third theme joins.

## Words

- **Theme**: one list that gets triaged, with its own owners, priorities and flow: the atlas's component issues, red tests, and later parked cards or the inbox.
- **Category**: a grouping of items *inside* a theme, such as "README and how-to link" in the atlas. `tools/triage_dryrun.py` calls these `theme`; they are renamed `category` when that logic moves into the atlas pack.
- **Theme pack**: the one file that tells the core everything about a theme. It is curated by the theme owner.
- **Core engine**: the one program every theme runs through. It is owned by the team.

## The rule

**The core never names a person, a path, a cause class or a priority rule.** Everything theme-specific comes from the pack. This mirrors the brand-agnostic rule (root CLAUDE.md rule 7): theme context enters only from the pack, never from the engine. A change to how a theme is triaged is an edit to its pack, which is its theme owner's act. A change to how every theme is triaged is an edit to the core, which is the team's.

**The walls are not per theme.** They bind every theme, come from root CLAUDE.md and the decision log, and no pack may relax one.

## What the core does, and what it needs from each pack

| Pass | The core does | The pack must give |
|---|---|---|
| 1 Intake | Calls the pack's adapter and turns each item into the common shape below | `item` (noun, id scheme, record slug), `adapter.read` |
| 2 Still true? | Drops or marks items the adapter says are already fixed, with evidence | `adapter.still_true` |
| 3 Summary | Anything the engine creates (an item, an action group, an issue it files) is created with all eight parts (SCHEMA §5); an item read from a source without them is listed as a gap | `summary` (standard, required fields, labels, where they live, `at_creation`) |
| 4 Cause | Gives each item one cause class and a `blocked_by` (a card, a decision, or nothing) | `cause_classes`, `categories` |
| 5 Group | Applies the pack's grouping rules in order, first match wins; counts "clears N" | `grouping` (ordered rules: when an item matches, what it is grouped by) |
| 6 Priority | Weights each action by the items it clears and raises old items | `priority` (tier rules, live-use evidence, weights, age days and cap, severity source) |
| 7 Three whos | Decides first, then can do it (the triage owner considered first), then affected; tags each item now / after / draft / owner | `triage_owner`, `owners`, `deciders`, `lane_conditions`, `doer_tags` |
| 8 Outputs | Writes one queue model, one page, explain and do prompts for every action and item, decision-log records and context files. The item's word on the page and in prompts is the pack's `item.noun`; how an item closes comes from `adapter.still_true` | `people`, `sidecars`, `outputs`, `context_hook`, `routes`, `item.noun` |
| 9 Write-back | Records each act as a `triage` record naming its theme; passes closes and reopens to the adapter | `adapter.write_back`, `adapter.reopen` |

### The common item shape (what pass 1 produces)

`{theme, id, title, tier, status, areas[], owner_hints[], evidence[], summary{...pack fields}, open_since?, raw}`.

`areas` are typed keys: `path:` (a component folder, a build folder, a file), `brand:`, `product:` or `sku:`. They decide which context files (path areas only) an item reaches and where its decision-log records show up, and they are how the core links items across themes. *(Amended 2026-10-02 after the metrics-insights test: a signal belongs to a brand or a product, not a folder.)*

## Born with the eight parts (the team, 2026-10-02, a standing rule)

the team, 2026-10-02, received 06:43Z by date -u: "also starting from now make it a rule that anything issues that come from this triage process should geneate with the 8 step summary from the start".

Anything the triage process creates carries the eight-part summary (SCHEMA §5: why, impacts, evidence, response (a fix, or a follow-up on a positive signal), what the response changes, if ignored, lane, severity) from the moment it exists: every signal a detector emits, every action group, every issue triage files (including the triage component's own open issues), every card it proposes. Nothing is created now and summarised later; the engine refuses to emit one without (`no-summary-at-birth`). Items a theme *reads* from elsewhere (component issues from system runs) are the source's to summarise; triage lists the gap and does not invent one. State on 2026-10-02: both themes meet it. Operations: 13 signals and 5 actions. Components: all 83 actions and all 656 open issues (the 29 that look fixed close instead), after ATL-31 (remaining issue briefs) and `tools/triage_fill.py` built the 60 missing action summaries from their issues' summaries.

## Grouping is the theme's, never the engine's (the team, 2026-10-02)

the team: "the group by logic should be custom to each theme as well". The pack's `grouping` holds ordered rules; the engine applies them, first match wins, and counts what each action clears. Components (2026-10-02): close-out (looks fixed) → shared fix across components (by cause class, 24) → decision group (waits on one ruling, 11) → local batch per component for its owner (47). Operations: one action per detector per brand, data health first (5).

## Priority is the theme's, never the engine's (the team, 2026-10-02)

the team: "how we actually prioritize is not hard coded in, each theme has its own priotization list". The pack's `priority` holds the ordered tier list (what makes an item P0 to P3), the proof a P0 needs, the weights, the age rule and its cap. The engine only applies it: each action ranks by the summed weight of what it clears. Components rank by risk to running work; operations by money at stake a month. The weights match today (8 · 4 · 2 · 1) by choice, not by rule.

## More themes later

the team: "even though we are focusing on two themes, the point is that this will be gernealized for more themes in the future (so just note that but we dont need to design those yet)". Noted; not designed. "Adding a theme" below is the whole procedure.

## What sharing one core buys

1. **One queue format and one page renderer.** Every theme's page looks and works the same: decides first, can do it, affected, prompts, briefs, drafts, options.
2. **One log** (the `triage` record kind, extended with the five proposed acts) with a `theme` field. Nothing about the log differs by theme.
3. **One decision log across themes.** Every act on every theme's items is one `triage` record naming its theme. "What changed in my areas, and how do I undo it" is a question to the log; no separate digest (the team, 2026-10-02: "Remove weekly digest, lets start with the decision log").
4. **Cross-theme links.** Items from two themes that share an area and a cause are one problem. Example: a red test in a build folder and an atlas issue on the component it tests. The core shows the link so the fix is done once.
5. **One context file per area.** The context hook draws every theme's acts for that area.

## Adding a theme

1. Name its triage owner (a ruling, as for atlas and red tests on 2026-10-02).
2. Name its theme owner (who curates the pack; usually the triage owner).
3. Write its pack: copy a sibling pack and fill every key. A key that does not apply is set to `null` with a reason, never left out.
4. Write its adapter: read, still-true, write-back. Only the adapter knows where the list lives.
5. Run the core once by hand, and the triage owner checks the page before anything reaches an owner.

**The third-theme test:** the parked cards (127, the lead's list) are a "still wanted?" list, not a "something is broken" list. If they run through the core with only a new pack and adapter, the core is general. If the core itself needs changing, the contract is missing something, most likely a second item shape for decisions. Record which.

## What has to move out of today's code into the packs

- `tools/triage_page.py`:
  - the list of people;
  - the brief field labels;
  - the paths of the issue briefs, drafts and decisions;
  - the weights and the age cap;
  - the word "issue" in the explain prompts.
- `tools/triage_dryrun.py`: the whole atlas pass (keyword categories, P0–P3 rules, the moved-path resolver). This becomes the atlas adapter plus `themes/atlas.json`.
- The red-test definitions (`red-tests/DEFINITIONS-red-tests.md`) become `themes/red-tests.json`; the prose stays as its explanation.

Rough size: about a day in the atlas stream's own area once this contract is agreed (inferred).

## Cross-references: by design, specific to each theme (the team, 2026-10-02)

the team: "The theme should also allow cross referencing from multiple areas by general design, but the cross reference is specific to the theme", with examples: components relate to the atlas and brand folders; operations relate metrics and the P&L systems the team will build; both relate to the general PM lists and Slack channels "(to be determined next)".

**The core owns the mechanism; the pack owns which references a theme carries.**

1. **Typed refs on every item.** An item carries `refs`: typed keys such as `component:email-production`, `brand:<brand>`, `product:war face wash`, `metric:<brand>-performance`, `pnl:pnl_brand_a_orders`, `card:HE-3`, `task:TSK-…`, `inbox:I-…`, `slack:<channel>`. The pack's `refs.emits` lists the types its adapter writes.
2. **One resolver per ref type, in the core.** A resolver says where a ref points and how to find what else touches it:
   - `component:` resolves to the folder and the atlas page;
   - `brand:` resolves to `brands/<brand>/`;
   - `card:` resolves to its deck;
   - `metric:` resolves to the data plane;
   - `pnl:` resolves to the warehouse table or view.

   Resolvers are shared, so a brand ref means the same thing in every theme.
3. **Reference sources are not themes.** The PM lists (tasks, cards, inbox) and Slack channels are indexed for links. They are not triaged here (they can become themes later). The pack's `refs.related_sources` names which ones a theme looks at.
4. **Declared beats inferred.** The 2026-10-02 trial matched refs to cards by text. For email-production#1 it found 8 "related" cards, of which 3 are real (HE-3 (shared brand facts), EP-1 (email writer mini door), SI-3 (offer-bank move)). So a reference source should carry declared refs: a card's or task's `refs:` line, written at filing. Text matching is a fallback and is labelled as such.

**On the triage list**, every item and action shows **Related elsewhere**: other themes' items on the same refs, open cards or tasks already handling it, and later Slack threads. That does three things:

- stops re-filing what is already in flight (it becomes `blocked_by` or "already carded");
- shows a fix that clears items in two themes at once;
- tells the triage owner whom to ask.

**In the component design**, refs add one core index, built each run from every theme's items plus the reference sources. It feeds the decision log's area view, the context files (path refs only) and cross-theme links.

## Third theme, run 2026-10-02

Metrics insights (the team) ran through the core with only a new pack and adapter. Two core assumptions surfaced and are amended above (typed areas; the item word and close semantics from the pack). See `themes/metrics-insights-FINDINGS.md`. The parked cards remain the test for a decision-shaped list.

## Kill-condition

The parked cards need a core change beyond a new adapter and pack. Then this split is wrong for decision-type lists: either the core gains a second item shape, or decision lists get their own engine.
