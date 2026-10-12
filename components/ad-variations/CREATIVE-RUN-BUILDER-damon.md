# Creative Run Builder (the owner's copy)

Page: (team page) · 5 Oct 2026. One page for the whole variation cycle: Build a run · Runs (your calls, spec, prompt, what was sent) · Formats (was the Format Bank) · Prompts. Page source `page/creative-run-builder.html`; how a session runs the queue: `RUN-QUEUE.md`.

**The workflow (5 Oct 2026): `PROVEN-TO-FORMAT-damon.md`** — proven ad → new format, batch by batch. The page now builds from a batch file (`definitions/proven-to-format/<batch>.json`) via `machine/proven_to_format.py page <batch>`.

**Rules (5 Oct):** video → video only; face scrub offer is buy 2, get 1 free and nothing else. The three image-winner runs (MOFU hands, Grandma static, hands photostrip) are off the page — image ads for the MOFU hands concept are a later job.

## The seven swaps (prompt: `prompts/stage-format-swap/stage-format-swap-v1-damon.md`)

| Concept | Format | Spec |
|---|---|---|
| MOFU showing hands (static) | Public reaction, repeat demo · Dbmik5RNWQV | `runs/ad-variations/<brand>/<run>` |
| Grandma House (top 1% video) | Body scan → kitchen fix · DavXLyHKZSB | `runs/ad-variations/<brand>/<run>` |
| Melanin overproduction VSL (top 1%) | Body scan → kitchen fix · DavXLyHKZSB | `runs/ad-variations/<brand>/<run>` |
| Grandma static | Public reaction, repeat demo · Dbmik5RNWQV | `runs/ad-variations/<brand>/<run>` |
| Hands photostrip p140 (static) | Public reaction, repeat demo · Dbmik5RNWQV | `runs/ad-variations/<brand>/<run>` |
| Grandma House | the herbalist signs → remedy → book · Ddh2x27iLY0 | `runs/ad-variations/<brand>/<run>` |
| Grandma House | the herbalist real-vs-fake tests → book · Dd12vX6inUo | `runs/ad-variations/<brand>/<run>` |

Each folder also holds `sent.md` (the prompt exactly as filled) and `run.json`.

## What every spec had to change (from the specs' own section F)

- The concepts sold the body scrub; these re-aim at the face scrub — legs/hands → face, "brown spots" → "dark spots", face-scrub usage (once or twice a week).
- Offer is the face funnel's: buy 2 get 1 free, $__ a tube. That page was logged built-but-not-live on 24 Sep — confirm it's live before any of these run.
- Cut where the brand files don't back them: Coco's age, the husband story, "five clean ingredients", "25% off", instant before/after reveals, the word "melanin" (brand rule).
- the herbalist's "comment BOOK" close becomes the tube held to the lens + "Tap below".

## the herbalist (@creator_a123) top 10 × our Grandma House winner

Pool: `components/swipe-organic/<creator>/` · format reads in `components/swipe-organic/records/swipe-videos/<code>/format.json`.

| # | Post | Views | Secs | Format | Match |
|---|---|---|---|---|---|
| 01 | Dd12vX6inUo — food purity tests → book | 418k | 51 | captioned-steps-comment-gate | strong · **swapped** |
| 02 | DeBPt79DllY — throat-odour gross-out → mouthwash recipe | 380k | 40 | subtitled-monologue-evidence-cutaways | medium |
| 03 | DdzrUsBCVsP — gut parasites, medical animations, supplement | 255k | 140 | subtitled-monologue-evidence-cutaways | weak (melanin-VSL territory) |
| 04 | DdNDb37y2Ds — neck vinegar tip → book | 194k | 33 | captioned-steps-comment-gate | medium |
| 05 | Dd5HtikDoO6 — knee foam reaction → book | 182k | 35 | captioned-steps-comment-gate | weak (instant result) |
| 06 | Dc_3JDZDnKa — leg swelling → 4-ingredient drink → book | 178k | 33 | captioned-steps-comment-gate | strong · next in line |
| 07 | DdfEJsmiMxZ — sagging, anatomy models, supplement | 169k | 140 | subtitled-monologue-evidence-cutaways | weak |
| 08 | Ddh2x27iLY0 — grandma points at signs → recipe → book | 157k | 35 | captioned-steps-comment-gate | strong · **swapped** |
| 09 | DdC6mkplOjS — presenters over medical animations | 146k | 116 | running-caption-borrowed-cutaways | weak |
| 10 | DdKbAPNDg2n — 87-year-old, three secrets → book | 133k | 58 | captioned-steps-comment-gate | strong |

Her main format: captioned steps → "comment for the book" (6 of 10).

The Formats tab also carries the full 43-format library and the format-read prompt verbatim (`components/swipe-organic/<creator>/format-read-prompt.md`).

## Formats added
- 2026-10-05 · TV-shopping live demo · Dd7GVDvprzl (@frankyshaw repost of an AI-made mascara ad, 2:20) · pool `components/swipe-organic/tv-shop-demo/` · format read only
- 2026-10-05 · the owner: one grandma video only, the most popular — the herbalist's Dd12vX6inUo (418k) as the grandma format, Grandma House (#1 winner, 959 sales) as the grandma winner. The other nine the herbalist posts, the Grandma House hook-1 cut and the signs→remedy run are off the page (files kept).
- 2026-10-05 · the owner: one cut per winner — Melanin VSL = #2 (878 sales), Today-years = #5 (426). The #4/#9 melanin cuts and the #8 today-years cut are off the grid. Grid now 7 winners × 5 formats = 35.
- 2026-10-05 · the owner: bald-head grooming format (DUe1HtWjI3p) removed — not for this avatar. Grid 7 × 4 = 28.

## The chain: proven ad → new format (drafted with the owner, 2026-10-05)

- Winner (already a proven ad): 1 Teardown ✓ → 1b Doctrine ✓ (done for all 7) — the content carried over.
- Format (the fresh swipe): 0 Triage → 1 Teardown → 2 Spec — the baseline.
- Then: 3 Injection (winner's content + face scrub + buy 2, get 1 free into the format's Spec) → 4 loop (4a Reading · 4b Hooks · 4c Placement · 4d Expansion · 4e Close · 4f Audit · 4g Spice — the owner picks which) → 5 Brief, AI lane → Viewer Check (Marketing Chain Checks; fails go back: opening → 4b, middle → 4c, close → 4e; 2 fails → held) → 6 Frames → 7 Final brief.
- Format status: body scan → kitchen fix ✓ 2 Spec · public reaction ✓ 2 Spec · TV-shopping live demo and captioned steps (the herbalist): 1 Teardown done, stopped at 1b (chain's Claude login expired).
- The 3 earlier swap specs skipped this chain (one-step shortcut) and get redone through it.
