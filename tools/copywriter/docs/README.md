# docs/ — the Markdown mirror

Damon reviews this work as a board. This folder is the record that survives
when a board is regenerated, in the form GitHub renders.

**Both are kept in step.** If one changes and the other doesn't, the Markdown
is the one to trust — it is the version under version control.

| File | What's in it |
|---|---|
| [`the-chain.md`](the-chain.md) | The ten stages, what each does, and why the chain has this shape |
| [`archive-v1-chain/`](archive-v1-chain/) | The first chain's docs, kept as the record of how the tool got here. Retired 2026-08-25 — nothing in there describes what the machine does now. |

The prompts are in [`../prompts/`](../prompts/), one file per stage,
versioned. `../prompts/superseded/` holds the retired chain's prompts and
nothing there runs.

Runs land in `../results/<label>/`; `../results/archive-v1-chain/` holds the
five made under the first chain.
