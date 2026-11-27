---
name: ask-first
description: Answer a question from the workspace before anyone asks the owner. Use whenever a teammate asks how something works or what was decided — "how does X work", "what's the rule for", "which audience should this SMS go to", "is $49 on the storefront or funnel only", "which model do we use for", "should I…", "did the owner decide…", "is this ruled", "check before I ask the owner", or the state of a piece: "is brief 0320 ready", "is this ad live", "does the owner still want these", "why is this still on the queue" — about a brand, an offer, a price, an audience, a send, a process, a tool or a model. Answers with the rule and its source, or says plainly it isn't ruled and writes the one question for the owner.
---

# Ask first

> **Standalone skill:** activates no component. It reads the workspace and answers; it
> changes nothing unless the person asking approves filing a ruling.

External dependencies (greppable):
- `brands/<brand>/rulings.md` — the owner's standing rulings for that brand, by area,
  with an Open list at the bottom;
- `brands/<brand>/` — `CLAUDE.md`, `products/offer-bank.md`, `offers/`, `email-sms/`,
  `products/`, `web/funnels/`, `core-avatars/`, `operations/`;
- `team/owner-rulings.md` — the owner's working rules that hold on every brand;
- `components/WORKFLOWS.md`, `components/GLOSSARY.md`, and the owning component's
  `CLAUDE.md` / `CONTRACT.md` / `README.md`;
- `the-org/decision-log.md` — decisions the team itself filed;
- `components/image-teardown/briefs.json` (the brief register), `runs/meta-upload/<brand>/ADS-INDEX.json` (what went to
  Meta) and `runs/handoffs/` (what is out and back) — the state of a piece.

## The run

1. **Name the brand and the area** from the question (or the folder the person is
   working in). Areas: offers and prices, email and SMS, paid media, video, images,
   copy, creators, products, web, research, operations.
2. **Search the rulings before anything else, in this order, and stop at the first clear
   answer.** Run records and past work show what happened, not what is ruled: read them
   only after the rulings, and never let them outrank a ruling.
   1. `brands/<brand>/rulings.md`, the area's section, and `team/owner-rulings.md`
      (who may do what, how every brand works);
   2. the brand's own file for the area (prices and offers: `products/offer-bank.md`;
      audiences and sends: `email-sms/`; pages and funnels: `web/funnels/`);
   3. `components/WORKFLOWS.md`, then the owning component's `CLAUDE.md` and `CONTRACT.md`;
   4. `the-org/decision-log.md`.
   Grep the question's key nouns and their everyday synonyms (price, offer, $49;
   audience, segment, list; storefront, store, product page; funnel, landing page).
3. **Answer in this shape:**
   - the answer in one line;
   - the rule it comes from, with its date, quoted exactly;
   - the source as `path:line`, so the person can open it.
   When two sources disagree, show both: the newer dated ruling wins, a HARD RULE line
   always wins, and the disagreement is named so it gets fixed.
4. **Something live** (today's price on the store, a segment's size, what an ad is
   spending) is checked only through the workspace's existing read-only doors. If none
   is open, say what the files rule and that the live state needs a look.
   **The state of a brief or an ad** is looked up before anyone is asked: its `state` in the register (`shipped` = it
   went to Meta, done; `superseded` or `killed` = never work), its row in `ADS-INDEX.json`, then its hand-off folder's
   `delivery-state.json`. A folder with no pictures, no voice read or an empty `returned/` is not "not ready" when the
   register says `shipped`: the ad was made another way. Answer with the state and take it off the list; ask the owner
   only what is left (keep it, drop it, change it). "Went to Meta" is not "spending today": say which one was checked.
5. **Not ruled anywhere:** say "Not ruled in the workspace", give the closest rules
   with their sources, and write **the one question for the owner**: short, the options
   side by side, and a recommended pick that follows from the closest rules. Then offer
   to put it on the brand's Open list in `rulings.md` so it is asked once.
6. **Filing the owner's answer.** An Open question is the owner's call: it is filed
   only on the owner's own answer, never on the asker's preference or a recommendation
   (a recommendation goes to the owner with the question). When the owner answers, the answer goes into the
   area's section of `brands/<brand>/rulings.md` (or `team/owner-rulings.md` for every
   brand) as one dated line, and leaves the Open list. `brands/` is read-only to
   machines: show the exact edit to the person in this session and write it only after
   they approve. Direction only — the rule in neutral words, never a quote, a name's
   opinion or a key.

## Never

- Message anyone, or post the question for the person. They send it.
- Change a store, ad account, email platform, page or drive.
- Guess an answer the files don't give. "Not ruled" beats a confident guess.

## Tested

2026-11-16, two real teammate questions on Brand A: whether the $49 FLEX price reaches
the storefront for Black Friday (answered from the offer bank: funnel only, never email,
SMS or storefront) and which Postscript audience an SMS goes to (answered from the
brand's rulings: the engaged segments, never a mass send to dormant lists).

2026-11-25, on a real question: three Brand A video briefs read as "not ready for the editor". The register and the Meta
index answered it: two had shipped on 8 and 9 November, the third was an idea with no brief number, not yet a brief, so not
the editor's. Nothing to ask.
