---
name: atlas-view
description: Draw one curated atlas page for one subject — a component, a pair of components, or a workflow — rendered only from the compiled atlas. Use when someone says "atlas view of video-teardown", "show me the dashboard workflow on the atlas", "curated atlas page for qc-checks and quality-checks", "/atlas-view <subject>", or wants one component's or workflow's place in the org as a page. Never hand-fills a fact; where the atlas does not know something, the page says so and names the proposal that would fill it.
---

# /atlas-view <subject>

> **Reads, runs nothing:** platform/data/atlas/data.json (compiled by `components/atlas`) — draws one page from the compiled atlas; runs no component command.


External dependencies (read only): `platform/data/atlas/data.json` and
`platform/data/atlas/last-refresh.json` (the compiled atlas, refreshed by the worker's
`atlas_refresh_tick`), and `components/atlas/CLAUDE.md` for the conventions the page follows.

Ruled 2026-09-30 (the developer, "go with view mode as proposed"; "1" = follow the design copy's
component layout, data only, gaps shown openly). Status: PILOT — three subjects.

## Run it

Compile the atlas fresh first (ATL-53 (atlas daily): the committed copy refreshes once a day); `render.py` and `flowcheck.py` read `ATLAS_DATA` when it is set, else the committed copy. The page header's compile time is the committed stamp's; say "atlas compiled fresh at <git rev-parse --short HEAD>" beside it.

```
ATLAS_FRESH=$(mktemp -d)/data.json && python3 components/atlas/compile.py --out "$ATLAS_FRESH" --no-stamp
ATLAS_DATA="$ATLAS_FRESH" python3 .claude/skills/atlas-view/render.py <subject> --out <file.html>
```

`<subject>` is one of:
- a workflow trace id: `dashboard`
- a component: `component:video-teardown` (a bare name also works when no trace has that id)
- several components joined by `+`: `qc-checks+quality-checks`

An unknown subject is refused (exit 2) with the list of subjects the atlas knows. The
renderer never guesses.

**Component pages to the standard** (ruled by the developer element by element, 2026-09-30, pages approved the same day):
pass `--flows <folder>` (today `new-workflow-design/builds/atlas/flows`) and a component with a flow file on the standard
renders as: open issues · how it works (the picture) · how to use it · who owns it · the core table · refusals · what the
atlas flags · reference. The standard: `new-workflow-design/builds/atlas/COMPONENT-PAGE-STANDARD.md`; the flow format and
how to draft one: `flows/SCHEMA.md`, `flows/DRAFTING.md`. `flowcheck.py <flows> <name>` checks every claim against the code.
Without `--flows` the renderer draws from the compiled atlas only, which is what the atlas lane (WM-115 (atlas view
handler)) runs; flows reach the lane when ATL-11 (compiler reads flows) lands. The page uses the dashboard's own UI
elements (pills, key-value lists, tiles, panels); its stylesheet is the dashboard's base plus only what it has no element for.

## What the page holds

- **A component:** its place on the eight-column chain; the design copy's header facts
  (since · owner · takes · makes · does not · run · runs by · contract · system path ·
  workflows through it); the flow feeds → keys and machines → engine → published · read by,
  drawn from the traces that cross it; drift the atlas raises about it; and **what the atlas
  does not know yet**, one proposal per gap.
- **A workflow:** the chain, each step's `does`, the end-to-end stages (H/A/T, with
  uncertain ones dashed), what it feeds and consumes, its cards, and its drift.

## Rules

1. **Data only.** Every fact comes from `data.json`. Nothing is typed in by hand. A missing
   fact renders as a gap with the proposal that would fill it, where the compiler already
   reads.
2. **Refresh, then render.** The page is only as current as the last compile; the stamp
   says when that was.
3. **Where the page goes** is still open (the pilot writes locally, and the fence is proposed
   after the pilot). Publishing as an artifact happens only on request.
