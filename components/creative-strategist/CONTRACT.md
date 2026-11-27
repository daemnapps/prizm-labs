# Contract — creative-strategist

What a run emits and what anything downstream may depend on. Nothing outside this folder reads `machine/` internals.

## The runs

    python3 machine/ask.py new   --brand B --ask LABEL --product P --avatar A --said "..." --funnel "..." [options]
    python3 machine/ask.py check PATH
    python3 machine/keywords.py --brand B --avatar A [--sub S] [--top N] [--json]

`new` writes `runs/creative-strategist/<brand>/<ask>/ask.json` (or `--out DIR`; also `--sub-avatar`, `--offer-section`, `--asked`, `--force`) and prints `note:` lines for anything it could not find. It refuses an existing file without `--force` (with it, keys later links wrote into the ask are kept), a malformed `--count` (NAME=INTEGER) or `--maker` (ROLE=NAME), an unknown brand, a product that is not a section of the brand's offer bank, and a moment that is not in the brand's `strategy/moments.json`. Exit 0 on success, non-zero with a line starting `refused:` otherwise. `keywords.py` is read-only.

## ask.json (the shape the readers already use; unchanged)

Required: `brand`, `product` (an offer-bank section key), `avatar`, `asked` (YYYY-MM-DD), `ask` (the label, also the folder name), `said` (the person's words), `funnel` (text), `offer` {`bank` (repo-relative path, optionally `#section`), `lines` (list: what the ads may say, word for word), `never` (list)}.

Optional: `moment` (an always-on ask has key `evergreen`, window `always on`, or omits `moment`) {`key`, `window` (text; a `YYYY-MM-DD to YYYY-MM-DD ...` span is what promo-calendar reads as dates), `lines` (list: the words every ad carries, e.g. the deadline)}, `sub_avatar`, `count` (object of integers, e.g. `static_concepts`, `pictures_per_concept`, `video_edits`), `makers` (role → name), `swipes` {`paid`, `organic`}, `gates` (step → text), `evidence`, `page`, and any other key a later link adds (readers ignore keys they do not know).

Optional, from the research route: `strategy` {`route` "research", `record` (the idea's file), `who`, `awareness`, `insight`, `idea`, `line`, `see`, `truths` [{`true`, `receipt`}], `no_price` (bool), `not_cleared` (list), `form` {`no`, `what`, `lends`, `job`, `swipe`}}. A reader prints it with `machine/idea.py` `block(ask)`, which is "" for an ask without it.

## The research route

    python3 machine/strategy.py evidence --brand B --avatar A --sub S --product P --label L
    python3 machine/strategy.py think|check|forms|choose|ask|hand|show <run> ...

`think` exits 1 when anything is held. `choose` refuses a held idea. `hand` prints the next command and runs nothing.

## Who it is for: the one read every writing chain makes

    import who   # components/creative-strategist/machine/who.py (public: block, stamp, resolve, MARK, END, avatars, subs)
    who.block(brand, avatar, sub=None, demographic=None, what=None)   # text, put on every step that writes or judges words
    who.stamp(...)                                                     # the same decisions, kept on the run as `aim`
    python3 machine/who.py show|profile|fill|status --brand B [--avatar A] [--sub S] [--demographic D]   # profile: the one page a whole asset is made from, runs/creative-strategist/<brand>/profiles/<name>.md
    python3 machine/wiring.py                                          # one green or RED line per workflow, from its own proof

The block also carries their world on every piece (the avatar's culture map: the shared part plus the named sub-avatar's and demographic's own; owner, 2026-11-25, replacing the 2026-11-09 withholding). `what` carries what the chain decided: `desire`, `awareness`, `stage`, `leads_with`, `doubt`, `claim`. What it did not decide comes from the filled slots. `sub` is an id or the card's file name; a named sub that does not exist stops. `aim` = {avatar, sub, demographic, desire, awareness, stage, doubt, claim}; `components/briefs/aim.py` reads it back by brief, `components/winners` `winners.py who` joins it to sales. `fill` writes proposals to `runs/creative-strategist/<brand>/who/<avatar>/`; the owner's signed slots live in the brand's `core-avatars/<avatar>/slots/` and win. Definitions live in `components/marketing-doctrine` (people, desire, awareness, sophistication, belief, mechanics) and nowhere else. Only the measured mechanics are handed to writers; lab-only and unproven ones run as tests. A new chain that writes adds the block and one line in `wiring.py`.

### Selecting a profile for video (2026-11-26)

`who.catalog(brand)` returns the available strategist profiles with `name`, `avatar`, `sub`,
`source` (repo-relative JSON path), `sha256`, `state` (`filed` or `draft`) and `profile`.
It reads the filed person first, else `runs/creative-strategist/<brand>/profiles/`; it never
rebuilds the index or writes brand files. `who.catalog_block(brand)` supplies the complete
profiles and receipts to audience selection. `who.selection(brand, avatar, sub)` returns
the chosen source receipt without the profile payload. If profiles exist, a missing or
unavailable person stops the chain; broad avatar summaries cannot replace these profiles.
A brand with none returns `None` and retains its legacy path. Selection does not approve a draft.

### A person, start to finish (skill `avatar-profile`)

A person (avatar + sub-avatar) is stored once, in the brand: `core-avatars/<avatar>/sub-avatars/<card>/profile.json`. A look (demographic) is joined per piece, never stored with the person.

1. `who.py build`: writes the person from the lines on file (sorted, written in the method's order, checked, read cold), lists what is missing, writes the searches and the price, and stops. With `--cap` and the owner's `--go` it pulls Reddit, YouTube and TikTok (`gather.py person`) and writes the person again. A draft until the owner's yes files it in the brand folder.
2. `who.full(brand, avatar, sub, demographic, what)`: person + look + message, joined now. `who.attach(folder, ...)` saves it with the piece (`profile.json`, `profile.md`); video, image, copy, email, page and statics runs call it, and `runsheet.pack` copies it into the hand-off as `PROFILE.md`.
3. `who.py index` is the database (state, own lines, unknowns, stale); `who.py refresh` rewrites the stale ones as drafts.

## Who reads it

| Reader | Reads |
|---|---|
| image-writing `--ask` (`tools/writing.py` `offer_input`, `idea_block`) | `offer.lines`, `offer.never`, `funnel`, `makers`, `moment.key/window/lines`, `strategy` (through `idea.block`, on every step) |
| copywriter `machine/brief_words.py` | `moment` (is it a sale ad), `offer.lines`, `moment.key` |
| video-writing `--ask` (`machine/writing_v2.py`) | `offer`, `moment`, `funnel`, `ask`, `strategy` (through `idea.block`, on every pass) |
| image-teardown `pick_run.py` / `run.py --ask` | the file path |
| promo-calendar `machine/homes.py` | `moment.key/window`, `product`, `avatar`, `asked`, `funnel`, `offer.lines/bank`, `makers` |

## Other files this component owns

`definitions/search.json` (swipe search settings), `prompts/avatar-profile-v1-owner.md`, `CREATIVE-STRATEGIST.md`.

### Where on the body

`components/naming/anatomy.json` is the one list of body parts (51, in 10 groups), each with how customers say it and what is true of it (coarse hair, shaved, can be seen unaided, covered). A product names its parts as yes or no in `brands/<brand>/products/body-parts.json` once signed (draft: `runs/creative-strategist/<brand>/products/body-parts.json`); a part not listed is not ruled and not claimed. `components/naming/body.py` is the one door that reads it. Every tool goes through it:
- writers: `who.block(..., what={"product": ...})` hands them the place this person is about, the places close by that may be mentioned with it (anatomy.json `regions`), and only the product in the piece; a product ruled out there stops the run (`who.must_fit`).
- research: the searches are told the place and how people say it (`who.unknowns`, `person.plan`).
- finished words: copy, email, pages and image briefs are held on a line that puts the product on a ruled-out part (`body.problems`: exact, low false holds); the video claim judge is handed the rule (`claimfix.claim_rules`).
- pictures: the prompt and the judge are handed the rule (`brand_facts`). clips: the checklist row "where on the body".
- hand-off: `profile.json` and `PROFILE.md` carry the place, how people say it and which products may go there.
- sales: `winners.py who` has a "Body part" row. Proof: `components/naming/tests/test_body.py`, in `machine/wiring.py`. A sub-avatar named `where-<part>` must name a part or group from this list.
