# triage

One engine that turns any long list into ranked actions. Each action comes with:
- who decides first, who can do it (the triage owner considered first), and who is affected;
- a summary for every item and every action;
- links to related work elsewhere;
- a record of every act in the decision log.

Each list is a **theme** with its own rules. Today there are two, and more will follow later; those aren't designed yet.

| Theme | Owner (theme and triage) | The list | Its queue |
|---|---|---|---|
| components / atlas | the team | open issues on the component pages | (private page) |
| operations | the team | signals from the metrics dashboards; P&L next | (private page) |

## Open it in Claude (no shared link needed)

In Claude Code, from your clone of the workspace:
- `/triage operations` or "show me the operations triage list" builds the list on today's data and opens it;
- `/triage components` opens the components list;
- "explain action 2 on the operations list" or "why is this signal P0?" answers from the list's data and its theme file;
- "note that: …" adds a finding to your theme's FEEDBACK file.

The skill lives in `.claude/skills/triage/`. Each run lands in `runs/triage/<theme>/<stamp>/`.

## Start here

1. `approach-two-themes.html`: how it works, step by step, with both themes as real examples. Published at (private page) (private; ask the team to share it).
2. `CONTRACT-themes.md`: what the engine does and what each theme file must give it.
3. `themes/atlas.json`, `themes/operations.json`: each theme's own rules, including its grouping and priority lists.
4. `HANDOFF.md`: where things stand, what's open, what's next.

**Ask your Claude:** "Read components/triage/README.md and HANDOFF.md, then explain how the <components | operations> theme groups and ranks its items, and what I'd change in its theme file to rank differently."

## Evaluation, 2026-10-02 → 2026-10-16

the team and the team each work their own list and hand in one findings file, `themes/<theme>-FEEDBACK.md`. Each finding gives the item, what's wrong, the change wanted, and whether it is a **theme** change or an **engine** change.

## How to use it → https://dashboard.the company.com/atlas#c-components-triage
