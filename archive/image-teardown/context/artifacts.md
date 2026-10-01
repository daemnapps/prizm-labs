# Artifacts — the static ad machine, stage one

Every artifact this folder owns, with its subject and its URL. **Republish over
these; never open a second page for the same subject.** Damon archives chats,
so a link that lives only in a chat is a lost link.

| Subject | Title | URL |
|---|---|---|
| The briefs tool itself, shareable: the brand chooser, both brand lists and every brief page, folded into one file with the same click-through. Bundled by `tools/brief_bundle.py` from `briefs/` — the pages `brief_page.py` already writes, not a second rendering of them. | Briefs | https://claude.ai/code/artifact/4da48fca-e30d-4a36-bded-e2e698c98b87 |
| How the graphic designer works: what a brief folder holds, the Higgsfield settings, 9:16 with the 4:5 safe zone, the five-step job, the one rule (match the swipe, do not improve on it), and the feedback Damon is asking her for. Superseded 2026-09-18 by the walkthrough below (the 2026-09-14 link is not reachable from a session). | Working a Brief | https://claude.ai/code/artifact/666a5f7f-1a22-407b-b725-e6839a37a25f |
| The designer's walkthrough of the Brief Board (Damon, 2026-09-18: "a dumb simple hand off walkthrough"): what it is, each part top to bottom marked hers/ours, the swipe-vs-ours standard, settings and references per product, the five-step job, the one rule. Built by `tools/walkthrough.py --brand <brand>` off the live files; her prompts are the ones on the board, not copied here. | Working the Brief Board — <brand> | https://claude.ai/artifact/5fGdVr2euWz4zgyDQ7ftnX |
| A second cut of the briefs, designed rather than bundled: brand-filtered chips, each brief's swipe and draft side by side, its Document One and its prompts verbatim with copy buttons — and, at the top, the download pack per brand. Republished 2026-09-17 at a new link: the 2026-09-14 page (`…/code/artifact/265162a7-4230-4e5c-9b52-6ffba7d158b4`) is no longer reachable from a session, so it could not be updated in place. | The Brief Board — <brand> | https://claude.ai/artifact/Sm2UNjTNAxcpo1pHfPGFwY |
| The designer's download pack: one zip per brand — a folder per brief with the swipe, our draft, the work order, the brief and its prompts, plus a README with the batch and the settings to set once. Built by `tools/pack.py`; the zip lives on Drive at `Shared Assets/runs/image-teardown/<brand>/brief-pack-<date>/`, its README in git at `runs/image-teardown/<brand>/brief-pack-<date>/deliverable/README.md`, the link in `briefs.json` under `packs`. <brand>, 2026-09-17: 21 briefs, 82 prompts, 147 MB. | <brand> Brief Pack | https://drive.google.com/file/d/1X9fvko-qzGx38eV0rZotiF4JvDrYBvd2/view |
| The same, for <brand>, 2026-09-17: 6 briefs (p005–p010), 27 prompts, 36 MB. p015–p018 have briefs but no work order yet, so they are not in it. | <brand> Brief Pack | https://drive.google.com/file/d/1gEab2xnf-uQlDNQmEbLgysLT0LER6Lvq/view |
| <brand>'s face-scrub variants (2026-09-18): the same 21 swipes re-run for the Brilliance Face Scrub and its offer — p164–p184, each `variant_of` its body-scrub brief. Built by `chain.py variant`; packs are per product from here on. | <brand> Face Scrub Brief Pack | https://drive.google.com/file/d/17xEqJw5GW4vvgy2hHkK1v0eVKgKlXvXI/view |

**Regenerate, never hand-edit:**

```
tools/brief_bundle.py  --out briefs.html                        # Briefs
tools/designer_page.py --part instructions --out wab.html       # Working a Brief
tools/designer_page.py --part briefs --brand <brand> --out board.html   # The Brief Board — <brand> (one board per brand, Damon 2026-09-18; <brand> gets its own)
tools/pack.py --brand <brand> [--product <slug>] --upload         # a product's pack
tools/walkthrough.py --brand <brand> --out walkthrough.html      # Working the Brief Board
```

`brief_page.py` owns how a brief looks. `brief_bundle.py` reads its output
rather than re-rendering it, so the shared page and the local tool on 8792
cannot drift.
