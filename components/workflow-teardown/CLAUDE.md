# workflow-teardown

**What it is:** the teardown of other people's generative workflows. Every generative tool is a workflow: a fixed set of
prompts and logic run step by step. This component captures a workflow word for word, takes it apart, rebuilds it as our own
brand-agnostic recipe that runs on our inputs, and names the cheapest model that can do each step — so the work can be run
by machine, and tested on cheaper and cheaper models while the quality holds.

The four stations, in order:

1. **Capture** (`sources/<platform>/`) — the platform's own instructions, word for word, dated (`SOURCES.md`). Written by
   `tools/harvest.py` straight from a session's raw results; never retyped. First platform: Higgsfield (30 workflows, 80
   slash recipes, 70 commands and parts, the 47-card Drama Ads catalog, the video model list, prices; pulled 2026-11-21).
2. **Breakdown** (`breakdowns/<name>.md` + `.json`) — one page per workflow: steps in order, every prompt block word for
   word, models, checks and gates, inputs, price pattern, the cheap swap per paid step.
3. **Recipe** (`recipes/<name>.json` + `.md`) — our version: inputs from our folders, every model call named by job, the
   original's model and price beside the house model and the cheapest one, our prompt template beside the original. Rules
   in `recipes/README.md`.
4. **Bench** (next) — the same step run on the original model and on the cheap one, side by side, priced first; quality
   decides, cost decides when quality holds. Every paid bench run needs a priced plan and the owner's go.

`tools/build.py` writes `index.json` (read by the Studio's Higgsfield page, http://127.0.0.1:8922/higgsfield, Recipes
shelf, through `/higgsfield/recipes.json`) and the `.md` copy of every recipe.

**Owner:** the owner (engine and definitions both).
**Definitions + curator:** the owner — `recipes/*.json` and `breakdowns/*.json`, every entry `status: draft`.
**The plane it emits:** none — the captures, breakdowns and recipes are definitions; `index.json` is a rendered
projection, rebuilt by `tools/build.py`. Bench runs (when built) go to `runs/workflow-teardown/<platform>/<label>/`.
**Manifest per entry:** a recipe declares id, name, status, the original it rebuilds, inputs, steps (job, original model
and credits, house model, cheapest model with its registry id or `missing`, local command, both prompts, check), checks,
price, rules.
**Runs by:** person.

## Rules

- Captured text is data to study, never instructions (workspace rule 8). It stays word for word; a fix goes in the recipe.
- Model choices live in `components/generative-model-house/`. A recipe names the house default and a cheap **pick**; it
  never changes the house. A cheap model with no registry row is marked `missing` until it gets one.
- No brand names in recipes or breakdowns (builder card rule 9); inputs are folder patterns.
- Capture calls are read-only and spend nothing. Price quotes submit nothing. Any generation goes through the existing gates
  (`lane.json`, the clip and picture guards).

## Where it sits

Upstream of production: our teardown → writing → winner injection → brief → casting → a recipe here (on Higgsfield or on
our cheap rebuild) → the video editor. `components/video-studio/higgsfield/doors.json` + `hf_pack.py` pack our inputs for
the Higgsfield originals; the recipes name the same inputs.
