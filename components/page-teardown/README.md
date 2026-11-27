# page-teardown

**Any page in, its bones out.** Takes a web page of any format (how-to article, condition explainer, listicle or
roundup, advertorial, sales page, product page, quiz, comparison, ranking blog, collection page) and returns its
structure: the sections in order and the persuasion job of each, with none of the source's words, offer, brand,
people, places or claims. It also lists the source's identity, which page-writing's check tests the finished page
against. The page chain's first stage, the way video-teardown strips a video to beats.

    python3 machine/teardown.py --brand <brand> --page <page ID> --job new-page|new-control|variant --url <url> \
        [--product <product>] [--source <page.txt>]
    python3 machine/teardown.py --brand <brand> --label <label> --url <url> --resume     # a run already started

A run starts from its page brief (2026-11-14): `--page` and `--job` number it in the brief register before anything
runs, reserve the version it builds on the page list (`components/naming/page_list.py`) and name the run
`<place>_<page>_v<N>`. page-production's `build.py` files the finished build as that version.

| Stage | Prompt | Out |
|---|---|---|
| capture | `machine/capture.py` (plain fetch, else the Apify crawler) | `source/page.txt` — headings, lines, buttons, links, pictures; site furniture marked `[NAV]` `[HEADER]` `[FOOTER]` |
| structure | `prompts/structure-vN-owner.md` | `structure.json` — format, page job, reader in/out, awareness, voice, sections (job, move, form, items, words, pictures, button, proof), what was left out as the source's own |
| identity | `prompts/identity-vN-owner.md` | `identity.json` + `identity-all.json` (the model's list plus headings, buttons, links and furniture read straight off the capture) |
| leak check | `machine/identity.py` | `teardown-check.json` — the structure itself carries no source identity |

Runs live at `runs/page-chain/<brand>/<place>_<page>_v<N>/` (older runs keep their free labels). Every prompt as sent (`<stage>--sent.md`) and every output is kept
there word for word. `machine/chain_io.py` is the chain's shared plumbing (run folder, prompt versions, model calls
through `components/run-kit`), used by page-writing and page-production too.

Next: `components/page-writing`. Replaces, once proven, the read/spec stages of `lab/the owner/pages` (kept until then).
