# Skills library — damon

**Front door:** say the job; the `make` skill (in ~/.claude/skills/make) reads it,
goes **Higgsfield first** (`HIGGSFIELD.md`), opens the recipe in `recipes/`, pulls
skills from the library (`catalog.json`, search with `tools/find.py`), and runs
every stage — stopping only for his picks and for anything that spends, goes live
or sends.

**Home:** Prizm Labs (private, 28 Oct 2026). The team workspace's established
skills are indexed and read in place; nothing is written to or copied into it.

- Recipes: ad-from-a-swipe, premium-landing-page, brand-from-zero,
  game-feel-mobile-app, ship-a-web-app, motion-piece, icon-set.
- Tool map (ready / sign in once / add later): `recipes/tool-map.md`.
- Research behind it: `RESEARCH-2026-10-28.md`.
- Plugins added 28 Oct: playwright, chrome-devtools-mcp, context7, expo (ready);
  canva, figma, stripe, supabase, vercel, resend, posthog, firecrawl (ask him to
  sign in the first time each is used).
- Library repos in `references/` (on this Mac, not committed): anthropics/skills,
  claude-plugins-official, knowledge-work-plugins, greensock/gsap-skills,
  expo/skills, remotion-dev/skills, coreyhaines31/marketingskills,
  rampstackco/claude-skills, jgerton/brand-toolkit,
  nextlevelbuilder/ui-ux-pro-max-skill, obra/superpowers, wshobson/agents,
  NextCommerceCo (skills, page kit, starter templates, spark).
  Rebuild the catalog after adding one: `python3 tools/catalog.py`.


What's loaded on this Mac, grouped by the job it does. Say the job; the session
picks the skill. Nothing here is built from scratch — every entry is an existing
skill or repo, adapted to how we work.

Page: see `context/artifacts.md` → "Skills Library".

## How a design job runs now

1. **Pull the reference first.** The store's WAR Face Wash routine box, the CPK
   starter templates, or a page he points at. No UI is drawn from a blank page.
2. **Load `frontend-design`** before any page, upsell, landing page or board.
3. **Build from the reference's tokens** (colour, radius, type) — match, don't invent.
4. **Screenshot it at phone width and show him before anything goes live.**

## 1. Pages, UI and boards

| Skill | What it does for you |
|---|---|
| frontend-design | Gives a page a deliberate look — type, colour, layout — so it doesn't read as a template |
| theme-factory | 10 ready colour/font themes, or a new one on the spot, applied to any page or deck |
| web-artifacts-builder | Bigger interactive pages (tabs, state, components) as one shareable link |
| artifact-design | House rules for every page we publish (built in) |
| dataviz | Charts, KPI tiles, dashboards that read cleanly in light and dark (built in) |

Plugins to switch on: **Design** (Anthropic), **ui-consistency**.

## 2. Funnels, upsells and landing pages (Next / CPK)

| Skill | What it does for you |
|---|---|
| next-campaigns-setup | Starts a new funnel from a starter template |
| next-campaigns-create | Builds the campaign, packages and offers in Next |
| next-campaigns-build | Assembles the funnel pages from a brief |
| next-campaigns-polish | Visual pass before QA |
| next-campaigns-qa | Test order through the whole funnel |
| next-campaigns-os / -os-setup | Runs the full funnel lifecycle end to end |
| quiz-funnel-page | Quiz / product-finder page from one config |
| next-theme-design | Captures a live page (desktop, tablet, phone) as a design to rebuild |
| next-theme-dev / next-theme-figma | Storefront theme build; Figma designs in |

Reference repos (on this Mac, `skills-library/references/`, not committed):

- **campaign-cart-starter-templates** — 9 funnels: Apollo (recommended one-page),
  Olympus, Apollo/Olympus multi-variant, Olympus two-step, Demeter, Shop single
  and three-step, and the **Landing** section library (niche example pages).
- **campaign-page-kit** — the CPK itself.
- **spark** — Next's storefront theme, with its DESIGN.md.
- **NextCommerceCo/skills** — source of the next-* skills.
- **anthropics/skills** — source of the design skills.

## 3. Icons, game art, posters (the team's game icons go here)

| Skill / tool | What it does for you |
|---|---|
| Higgsfield image generation | Icon sets and game art from a style reference (personal Higgsfield workspace) |
| canvas-design | Finished posters and static art as PNG / PDF |
| algorithmic-art | Generative patterns, textures, backgrounds |
| objects | 3D props and objects with a spinnable web copy |

Plugins to switch on: **Icons8**, **Streamline Icons** (ready-made icon libraries).

Route for a game icon set: the team's references → he picks → one style sheet →
Higgsfield generates the set on that sheet → background removed → icon grid page.

## 4. Games and gamified pages

| Skill | What it does for you |
|---|---|
| web-artifacts-builder | Interactive game-like pages, scored, stateful |
| quiz-funnel-page | Quiz mechanics with results |
| slideshow | Live, clickable presentations (talks are games, not slides) |
| algorithmic-art | Motion and visual play |

## 5. Mobile apps

Plugins to switch on: **Mobile Design System**, **Mobile App Design (iOS)**.
The desktop app runs and screenshots iOS apps in the simulator.

## 6. Video

hyperframes (start here) · general-video · motion-graphics · music-to-video ·
product-launch-video · faceless-explainer · talking-head-recut ·
embedded-captions · slideshow · media-use · figma · remotion-to-hyperframes ·
hyperframes-animation / -audio / -core / -creative / -keyframes / -registry /
-studio / -cli · video-remake-benchmark

## 7. Store operations (Next)

next-ops-scan (daily risk scan) · next-bulk-subscription · next-bulk-fulfill ·
next-bulk-move

## 8. the owner's own

handoffs · tella-pull · book-a-flight · objects · video-remake-benchmark
