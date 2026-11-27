# Our recipes — Higgsfield's workflows, rebuilt on our inputs and cheaper models

Higgsfield's presets do production; our research is what goes into them. Each recipe here is one Higgsfield workflow taken
apart step by step (its own words are in `../sources/higgsfield/`) and rebuilt so it:

- takes **our** inputs, by the folders `components/video-studio/higgsfield/doors.json` names, never a brand name;
- names every model call by **job**, and puts the Higgsfield original beside the cheapest model that can do that job;
- keeps every Higgsfield prompt block word for word (`prompt_hf`) next to our brand-agnostic template (`prompt_ours`,
  `{slots}` filled from the inputs).

`<name>.json` is the manifest the Studio's Higgsfield page reads (Recipes shelf); `<name>.md` is the same recipe for people.

## The model rule

`components/generative-model-house/MODEL-HOUSE.md` is the only place that says which model does which job. A recipe never
changes that. Each step names:

- `house` — what the house default does today (a tool calls `model(job)` and gets this);
- `cheap` — the cheapest model that can do the job, as a **person's pick** (`pick(job, model)`), with its price. A cheap
  model that has no registry row yet (`components/models/models.json`) is marked `registry: missing`: it needs a row
  before any tool can pick it.

To make a cheap swap the default, change the house, not the recipe.

## Prices

Every credit figure comes from `../sources/higgsfield/_prices.md` (quoted 2026-11-21, quotes submit nothing). Re-quote before a run.
The gates stay: no paid step without a priced plan and the owner's go (`lane.json`), and the clip and picture guards in
`~/.claude/hooks/` are never bypassed.

## Manifest shape (`<name>.json`)

```
id, name, status (draft), higgsfield {command|workflow, library: [files]}, makes, inputs [{name, from, required}],
steps [{n, name, job, what, hf {model, settings, credits}, house {model, credits}, cheap {model, registry, credits, note},
        local, prompt_hf, prompt_ours, check}],
checks [..], price {higgsfield, house, cheap, basis}, rules [..]
```
