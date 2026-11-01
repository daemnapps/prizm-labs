# Artifacts — email-production

One artifact per subject; republish over the same link, never a second copy.

| Artifact | URL | Subject | Mirror |
|---|---|---|---|
| The Email Machine | (team page) | The operating dashboard (board · catalogue · build cards · runs). **the owner's working copy is the LIVE page at `http://localhost:8785`** (launchd server + watcher, video-board pattern); the artifact is the shareable mirror — republish over this link when sharing matters. | `dashboard.md` |
| One Machine, Any Brand | (team page) | The brand-agnostic architecture: machine/brand split, the live wiring check, brand onboarding. Source `machine-wiring.html` (also served at localhost:8785/machine-wiring.html). | `ONBOARDING.md` |
| The Email System | (team page) | The system map: brand root, workflows, categories, types, arc, and every prompt verbatim. Rebuilt by `build_system.py`. | `email-production.md` |
| The Offer Bank | (team page) | What a brand may actually sell — per lane, per date, per surface. The catalogue, the hero offer for the paid front end, what is refused and why, and the gaps nobody has closed. Snapshot; regenerate from `offers.py` after the bank changes. | `OFFERS.md` |
| The Email Chain | (team page) | The working line for Brand B, calendar to Klaviyo draft: every station and how it's triggered, the twelve writing steps with model, inputs and prompt verbatim, next week's sends, the knobs in order. Built by `chain_page.py` (source `email-chain.html`). Distinct from The Email System, which is the strategy catalogue (types, wells, arc). | `EMAIL-CHAIN.md` |

Note 2026-08-29: a second artifact also titled "The Email System"
(87b1714b-c532-4626-96ef-4489ca639966, last updated 08-27) exists from an
earlier session. The one above matches the current generator and is the live
one; the duplicate awaits the owner's call to retire.
| The Send Plan | (team page) | The month's emails for one brand in plain words, with the calls only the owner can make — approved here before a word is written. Rebuilt by `send_plan.py <calendar run>` from the calendar's own slots.json. Republish over this link every month, never a second copy. | `SEND-PLAN.md` |
| The Drafts | (team page) | Every email of the current month as it would read, with each one's picture DIRECTION (not the picture) and what the check is holding it on. Rebuilt by `drafts_page.py <calendar run>` from the runs on disk. Republish over this link each time the drafts change, never a second copy. | `DRAFTS.md` |
| Where the Assets Live | (team page) | Where a brand's pictures and footage actually live — the one home folder, what could come into it, what is ruled out; thumbnails sampled from the real files and every card opening the real Drive folder. Rebuilt by `assets_page.py <brand>` then `assets_render.py`. | none (the page IS the record) |
