# copywriter

**copywriter** — takes **a source and a brief**, makes **the copy: primary
text, captions, headlines**. Does not **make pictures**. Triggered by
`python3 machine/copy_writer.py <source> --brand <brand> --product <product-file>`.

**Owner:** the owner · **Station:** `components/` — moved in 2026-09-19

Runs by: mini

> the designer, 2026-09-22 (SI-6 (intent line)): the copywriter goes to the Mac
> mini — her call alone, the owner informed. The mini's door is
> `machine/lab_entry.py`; by hand, `copy_writer.py` runs exactly as below.

> Moved from `lab/the owner/copy/` and renamed on the owner's word, 2026-09-19: *"let's
> move copy into components, and then we'll just change the name to
> copywriter… we use the original."* The same tool, same prompts, same runs —
> only its home and its name changed. It is the one place copywriting is meant
> to live; which other chains route their writing through it is NOT decided —
> each one is proven side by side before it is switched. **system-review:
> ACCEPT WITH CLEANUP** (2026-09-21) — the graduation gate was retired that day
> (`the-org/decision-log.md`); a review is owed, not an approval. Its run
> records moved to `runs/copywriter/` on the owner's word, 2026-09-21.



> **WHERE RUNS FILE (done 2026-09-20).** `copy_writer.py` writes every new run to
> `runs/copywriter/<brand>/<label>/` at the repo root (`runs/README.md` is the
> authority; renamed from `copy-machine` on the owner's word 2026-09-21 — one
> constant, `machine/paths.py`, and the Mac mini follows it).
> `results/` is history: nothing new is written there, and every reader — the
> board, `publish.py`, `rerender.py`, `batch_status.py`, the research shim —
> looks in BOTH through `machine/paths.py` (`all_runs()`, `find_run()`).
> `--rerun-from` on an old label carries it over to its new home once.
> `output/` HAS moved (2026-09-21, the owner: "finished copy goes in runs"):
> `publish.py` now writes `<run>/deliverable/`, which is what `runs/README.md:57`
> asks for in phase 1. The old `output/` is history — read, never written.

## New-resident checklist

Four questions, answered once (components rule, ruled 2026-09-01). Answered
2026-09-21 from the folder as it is; the fourth carries an open question.

**Engine + owner.** The engine is `machine/copy_writer.py` — an eleven-stage runner
(stage0, 1, 2, 1b, 3, 4, 5, 6 gated, 7, 8, 9) with the language layer, the
board and the publishers beside it. **Owner: the owner.**

**Definitions + curator.** The definitions are `bank/`, brand-agnostic by
rule: `formats.json` (copy STYLES — how the copy is written), `format-bank.json`
(surfaces — where the words go), `channel-map.json`. The two banks are
deliberately different axes, stated in each file's own `scope`. **Curator:
the owner.** Brand context never lives here — each brand's `variables/copy.md`
sits in the brand folder and is read at run time.

**The plane it emits.** Runs, not a registry: `runs/copywriter/<brand>/<label>/`
at the repo root, plus the board on :8778 that reads both run homes through
`machine/paths.py`. It writes **no record to the records plane** — checked
2026-09-21, no writer under `platform/data/records/`. Whether it should is
open.

**What the manifest declares per entry.** `formats.json` entries carry
`key`, `name`, `what`, `length`, `form`, `opens_with`, `carries_offer`,
`reads_as`, `channels`, `variations`; the file carries `schema`, `scope` and
`updated`. **Status, per components rule 6.** A manifest is a file any
program reads per entry (the developer, triage page 15, 2026-10-07 — replaces N4 (bank
status)'s 2026-09-21 scope for this file). `formats.json` (the machine runs
from it) and `format-bank.json` (the element library's `placement/all` is
built from it, components/elements/sources.json:199-217) are manifests: each
entry carries a `status` (`draft` / `approved` / `deprecated`) set by the owner as
definition owner — `formats.json`'s four `approved` on his "yes", 2026-09-21
(`2a962306d`); `format-bank.json`'s sixteen seeded `draft` 2026-10-07
(SI-77 (format-bank status)). `format-bank`'s `provenance` (proven / evidenced /
drafted) is where a spec came from, not its status, and stays as is.
`channel-map.json` and `library/index.json` carry no status yet — whether they
must is open, for the lead to rule (SI-77 (format-bank status), its "not in
this card" items 1-2).

**A LIBRARY — the public surface** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line; consumers pinned 2026-10-08, SI-120 (library clauses drafted)). Other components import `machine/` or `library/` with that folder on the path, or read the folders below, and may use only these names:
1. **`machine/`:** `context.index(brand, always=())` → the menu a stage reads; `context.load(paths, budget=)` → the chosen files' text; `context.parse_choice(text)` → `[path]`; `context.WORKSPACE` (defined in `paths.py`, re-exported); `language.avatars`, `language.for_stage`, `language.avatar_root` (the language-layer shim); `research.text_for(brand=, avatar=, funnel=, …)` → one `{research}` string; `brief_words.auto(brand, brief, product=, *, source=, say=)` and `brief_words.for_writing_run(run_dir, brand, product=, say=)` → the ad words, never raising; `copy_set.approved(brand, product, angle, ws=)` → the approved set or `None` (`ws` = the workspace root, default this checkout); `copy_set.fill(set, link_id=, page_type=)` → `{primary, headlines, descriptions}`.
2. **`library/`:** `meta_copy.db_query(sql)` → rows as JSON (read-only); `meta_copy.words_of(creative)` → the ad's words; `library/sources.json` (each brand's `market`) read by path.
3. **`prompts/video/`** — MOVED to `components/video-writing/prompts/` on 2026-10-19. Was: the video line's writing station, read by folder; the highest `-vN-` per stage is the live one. A reader that pins a version by file name carries its own risk.
4. **`bank/`:** `formats.json` and `format-bank.json` (the manifests above), and `channel-map.json`, read by path.
5. **Command:** `machine/copy_writer.py <source> --brand --product […]` (below).
Everything else is internal and may change without notice. `results/` and `output/` are gone; a reader of either is broken, not served.

## The folders — what lives where

| Folder | Purpose |
|---|---|
| `machine/` | the code: the runner (`copy_writer.py`), the language layer, the board, the server, the publishers, every page generator |
| `prompts/` | the stage prompts, versioned `-vN-owner.md`, highest wins |
| `bank/` | the system's data, brand-agnostic by rule: `formats.json` (what the machine writes), `format-bank.json` (every format on every channel), `channel-map.json`. Brand context NEVER lives here — each brand's `variables/copy.md` sits in its own folder and is read at run time |
| `library/` | the evidence: every piece of copy we hold as rows (`index.json`), the sourcing rulings (`sources.json`), their builders |
| `results/` | HISTORY — run records made before 2026-09-20. Still read, never written. New runs: `runs/copywriter/<brand>/<label>/` at the repo root |
| `output/` | HISTORY — finished copy published per source before 2026-09-21. Still read, never written. Finished copy now lands in its own run: `runs/copywriter/<brand>/<label>/deliverable/` (the owner ruled 2026-09-21) |
| `pages/` | generated HTML, drawn from data by machine/ generators. Never hand-edited, never committed |
| `docs/` | design notes and the md mirrors of the artifacts |
| `context/` | `artifacts.md` — every artifact's URL; republish over those, never open second pages |

Run everything from anywhere; paths resolve through `machine/paths.py`, whose
`HERE` is this folder. The board serves `pages/` on :8778.

One source in, ad copy out. Eleven prompted stages (0–9, with 2b) plus one
research step, all Claude. `copy_writer.py` runs it, `board.py` draws it, `serve.py`
serves it live.

**Social copy and video writing** (the owner, 2026-08-25; widened 2026-09-30:
"within the copywriting, can we not add the ability for it to also do the
video copywriting as well?" — yes, lifted). No advertorials, no listicle pages,
no landing pages. Ad copy for social, and the video line's writing station.

## prompts/video/ — the video line's writing station (2026-09-30)

**MOVED OUT 2026-10-19** (the owner: "make components/video-writing with the writing code and
stages, teardown hands off to it"): `prompts/video/` is now `components/video-writing/prompts/`,
with the writing code beside it. The history below is how it got here.

Station 2 of the four (teardown · writing · production · edit). The writing
prompts for video moved here from `components/video-teardown/prompts/` on
the owner's word ("go ahead and make the move"): 1b audience, 2f compose, 3
injection, 3v control, the 4-loop (4a read · 4b hooks · 4c placement · 4d
expansion · 4e close · 4f audit · 4g spice), 4m awareness map, 5 brief
(creator · ai · hook asset), 5m swipe match, 5n manifest, 5u mark used, 7
inject, 7b her page, 8 profile. **One command still runs them all** —
`components/video-teardown/machine/run.py --route <creator|ai|founder>`; its
`chain.py` finds them here (`WRITING_PROMPTS`), the highest `-vN-` in each
folder runs, older versions sit in that folder's `archive/`. Runs file to
`runs/video-writing/<brand>/<slug>/`. `copy_writer.py`'s own social-copy stages
(`prompts/stage*.md`) are unchanged; moving social copy onto these shared
stages is proven side by side first.

## brief_words — the ad's words for every lane (2 Oct 2026)

`machine/brief_words.py --brand <b> --brief brief-NNNN [--product <p>]` routes one brief
through `copy_writer.py` — its own stages and prompts, nothing added — for the text Meta shows
beside the ad: the stage 8 bodies (primary text), HEADLINES and DESCRIPTIONS. Source: a
delivered master's transcript (`runs/audio-teardown/<brand>/*/<unit>/transcript.md`) when
there is one, else the brief's writing run. Formats default to short-form + caption. Runs
file as `runs/copywriter/<brand>/<product>-<brief>-words/`, which the approval card reads
(components/meta-upload/card_words.py). Hooked into the video chain's last step (every route
that wrote a brief) and the image chain's sequence briefs; `NO_AD_WORDS=1` turns it off for
one run. Tests: `machine/test_brief_words.py`.

## The ad's words are filled into our own winning formats (27 Oct 2026)

the owner (Tella review of the picture board): *"right now we keep writing brand new ad copy over and over and over again
per ad, and that's not necessary at all ... when I read some of this copy back, it's not in a proven format ... we're
just freeballing it based off of the brief."*
- **The bank:** `machine/real_formats.py build --brand <b>` strips every real ad in the warehouse pull
  (`runs/copywriter/<brand>/meta-copy/<date>/copy.json`, top 25 by spend + top 25 by lowest CPA; never the ad account)
  into a format: the ad's own words with named [BLANKS] (`prompts/copy-format-strip-vN-owner.md`), checked by the
  video hook's own `hook_format.fits` (the fixed words are the ad's, in order). Written to
  `runs/copywriter/<brand>/copy-formats/formats.json` + `formats.md`, one `copyformat_<brand>_<slot>_NN` per ad, named
  by its real Meta ad name, with its spend, purchases, CPA, awareness level, offer and season; `status: draft` each.
  A format that is not the ad's own words, or an ad cut off mid-sentence in the pull, is `state: broken` and never
  handed out. `recheck` re-runs those checks; `show` and `pick` read it.
- **The writer:** `machine/format_copy.py` (called by `brief_words.write` whenever the brand has a bank; the old stage
  chain runs only for a brand with none, named `--formats`, or `COPY_FREEFORM=1`). The formats are handed over, not chosen: per
  slot, no offer or season ad off a promotion, the ad's awareness level first (else the picture record's MARKET STATE),
  best spend first, and the top 3 primary, 2 headline and 2 description formats are the ones filled
  (`prompts/copy-format-fill-vN-owner.md`) from the product file, the market's words at the ad's level and the spice.
  v2 (the owner: "we can have the founder story and the parasite stuff in here too, that's fine. we're just using the
  formats and changing elements, that's it"): the brand's own story and claims in its own ads stay; only the
  elements that make it this ad change. Checked with no model (a format it was handed, its shape kept — paragraphs
  one for one and most of its own words in order, `real_formats.keeps` — no blank left, no price off a promotion, offer-bank prices
  only, headline ≤ 40 and description ≤ 30 characters), sent back once, a line still broken dropped and named. The
  run is the render the card reads, each body under the format and real ad it came from.
  v3 (Tella, 27 Oct: "we got to put in our actual elements that make sense, that are relevant to the brief itself"): the
  writer first writes THIS AD'S ELEMENTS (who and her era, the moment, the problem, the angle, the picture) and fills
  every format from them; a format's own story from another ad is an element and is replaced. `story_check` reads
  every line against those elements (the checks tier) and a line telling another ad's story is sent back once, then
  dropped and named. Lessons register: `components/model-inputs/lessons.json` (L-22).
Tests: `machine/test_real_formats.py`.

## Google text ads — swipe → strip → fill → check (23 Nov 2026)

Ruled 2026-11-23: the first Google campaigns carried raw customer lines instead of ads, so Google text ads get
their own chain. The format_copy pattern, for Google's responsive search ads:

```
python3 machine/google_copy.py strip --brand <b> --swipes <competitor-search-ads.json> [--dry-run]
python3 machine/google_copy.py write --brand <b> --groups <groups.json> --product brands/<b>/products/<p>.md \
        --label <name> [--only <group>] [--allowed-host <host>] [--dry-run]
```

- **strip** (`prompts/google-strip-vN-owner.md`, checks tier): competitors' live Google search ads, longest-running
  first, each headline and description stripped to a format with [BLANKS] and its slot. Written once per brand to
  `runs/copywriter/<brand>/google-formats/` (`formats.json` — every entry `status: draft`, `state` ok / whole line /
  missing — `formats.md`, prompt as sent, answer).
- **write** (`prompts/google-fill-vN-owner.md`, designs tier): per ad group — its searches, the landing page's own
  promise read live, the product file, the offer on the page, our customers' words for the topic — 15 headlines and
  4 descriptions, every line one handed format. `groups.json` carries `campaign`, `groups[]` (name, final_url,
  keywords with searches, words with row ids), `competitors` (names never written), `caps` (the brand's own capitals),
  `offer_note`.
- **check** (no model, `check()`): 30 / 90 / 15 characters, no ! in a headline, no emoji, no other brand's name, no
  claim word Google holds and no product file carries, no price off a promotion and only the page's own prices on
  one, capitals only in the product's or brand's own names, every line a handed format, 3+ headlines carrying a
  search's words, the landing page on `--allowed-host`. Sent back once with what broke; a line still broken is dropped
  and named. Output: `runs/copywriter/<brand>/<label>/<group>/ad.json` + `ad.md`, and `ads.json` for the campaign.
- Nothing here calls Google or writes into a brand folder; the Google tool puts the ads in after a person has read
  them. Tests: `machine/test_google_copy.py` (no model, no network).

## Price and awareness — two rules on every set and run (12 Oct 2026)

the owner: *"no prices in headlines or descriptions on meta unless it's clearly a promotion or value focused ad. this
is literally tip of funnel brain rot so the copy should reflect unaware levels of copywriting as well."*
- **Price:** no price, deal, pack offer or money-back line in a headline or description unless the ad is a
  promotion — `--promo` on `copy_writer.py` / `brief_words.py` / `copy_set.py`, or the angle row (its own `promo`
  field, else an id/name that says value/price/offer/deal). Machine-checked in `copy_set.offer_problems`, used by
  both `copy_set.check()` and `copy_writer.py`'s copy gate.
- **Awareness:** `--awareness <doctrine id>` binds `{awareness}` + `{awareness_levels}` (the doctrine slice, never
  restated) into copy-set v2 and stages 8 v10 / 8b v3 / 8c v3. A level whose doctrine Must NOT names price also
  bars a price in the bodies (`{offer}` is then not required). `brief_words` passes the level its brief's run
  recorded (`"awareness"` in the production run's brief.md / run.json / plan.json), when one did.
Tests: `test_copy_set.py`, `test_rollout.py`, `test_brief_words.py`.

## The language pull — avatar, awareness, spice on every stage (27 Oct 2026)

the owner: *"awareness levels and verbatims and spice are the foundation of what we're doing here."* Every stage's
`{language}` is `language.for_stage(brand, stage, avatar, funnel, …, used="fresh", awareness=<level>)` — the call
the picture chain and the video hook step make. The level is `--awareness`, else the entry level stage 1's
AWARENESS section names. Stages 5 (hooks) and 8 (render) also get `{spice_bank}` (the `spice` stage, same avatar,
same level) and stages 3, 5 and 8 get `{research}` (stage 3 v7, 5 v8, 8 v11). `copy_set.py` asks at the set's
`--awareness`, binds `{spice_bank}` (copy-set v4), and records any failed or empty query as `language_problems`.
An empty pull is printed and said in the slot — never a quiet "(no rows)". Tests: `test_language_pull.py`.

## Where this lives

`components/copywriter/` since 2026-09-19. Before that `lab/the owner/copy/` —
graduated out of daemn on 2026-08-26, on the owner's instruction, per the route he
and the developer agreed: **build alone in daemn until it actually runs, then move it to
the lab so the developer can break it into components and scale it.**

Brand context is read from `brands/<brand>/` (the one brands tree since
2026-09-02; `lab/the owner/brands/` no longer exists and is no longer probed) —
still resolved by name rather than by counting folders (`paths.py`,
`--brand-root`, `AI_WORKSPACE`). That separation is what let the build move
twice without breaking, and it is what will let the brand banks move without
breaking it again.

**Nothing here writes to a brand folder.** Read-only, always.

**There was a second copy of this machine** at `lab/the owner/copy-machine/`,
committed 2026-08-26 on the way out of daemn — same machine, one day older,
and its CLAUDE.md still claimed it lived in daemn. Folded into this folder
and removed 2026-08-27 (the owner: "merge whatever is needed so it's just one").
The only things it held that this one did not were the prompt-as-sent dumps
and the run posters, both gitignored here; both were copied across, so the
board can still show every old run's prompt as it was actually sent.

**Media never enters this repo.** The source video is a symlink to the
teardown's own mp4 and the poster is cut from it; both are remade on every
run and both are gitignored, along with the generated pages and the
prompt-as-sent dumps (11MB of inlined brand context, rebuildable by replaying
the substitution). What is kept is what each stage RETURNED — the part worth
diffing.

## What it takes

One `source`, which is either:

- **a teardown record** — of a video ad, an organic video, an image ad, an
  organic image, or a caption
- **raw copy** — a swipe, pasted in

the owner's two live Brand B ads are the second kind. They were briefly modelled
as a "copy bank" to match against; that was wrong. Existing copy is a
**source to swipe**, same as a video, which is why the chain has one input
slot and no bank-match stage.

## The chain

Mirrors the video teardown chain (`components/video-teardown`) stage for stage, because
that chain already solved this problem properly.

| | | | model tier |
|---|---|---|---|
| — | **Formats check** | Every `--write-as` id against the element library (`format/copy`). Not a model. | — |
| 0 | **Triage** | Lane, format, avatar, funnel. Everything downstream binds to it. | reads |
| 1 | **Read** | One source in, one objective record out. Handles either input kind. | checks |
| 2 | **Spec** | The record abstracted into a brand-free construct. | designs |
| 2b | **Context scout** | Picks which brand files this source actually needs. | reads |
| 3 | **Injection** | Our brand into the construct. Substitution, never rewrite. | designs |
| 4 | **Placement** | Where the product enters, and the length budget. Decides, writes nothing. | checks |
| 5 | **Hooks** | The control plus variations. All ship — the machine never picks. | designs |
| — | **Research** | The live research gatherer, pulled ONCE before injection for stages 3, 5, 6, 7 and 8 (`machine/research.py`; 3/5/8 since 2026-10-27). Not a prompt of ours; kept on a rerun. | — |
| 6 | **Expansion** | **Gated: runs only when the lane is ORGANIC.** | designs |
| 7 | **Close** | The objection at the flinch, the landing, the whole piece assembled. | designs |
| 8 | **Render** | The argument becomes the actual copy, in each requested format, ready to paste. | designs |
| — | **Copy gate** | Prices + unfilled notes. A failure holds the run before the brief. Not a model. | — |
| 9 | **Brief** | The document a media buyer opens. | reads |

The stage list lives in ONE place — `STAGES` in `machine/copy_writer.py` — and the
board reads it from there. **Tiers** come from `components/run-kit`
(`reads` / `checks` / `designs`); a prompt too big for a small window is moved
up to the `designs` model automatically. `--tier reads=<model>` repoints one
tier for a run; `--model <model>` forces one model for every stage, which is
what this machine did before tiers (`--model claude-opus-5` is the old run,
exactly). The model each stage actually used is in `run.json`.

**The gate is the point.** An `ALREADY AN AD` source has commercial structure
already; it is inherited at injection and stage 6 is skipped. An `ORGANIC`
source has none, so it has to be built from nothing. Lifted unchanged from the
video chain's `ROUTES`.

**Spec is the stage the first chain lacked**, and its absence is why output
kept arriving in brand voice: writing from a record produces copy *about* our
brand in roughly the source's direction; writing from a construct puts our
brand *into* the source's actual shape.

## Two rules that bind everything

**Organic source → the creator's voice, never the brand's.** The copy is that
person speaking. Not brand copy with their name on it. This outranks house
style, and stages 3, 5, 6 and 7 each restate it because the close is where
replicated copy most often reverts.

**All hooks ship.** The machine writes a control (the source's own opening,
swiped straight, never "improved") plus variations, and does not rank them.
Choosing is the owner's.

## Gates

Two fixed points where work is checked, and a failure stops it.

1. **Elements — before anything runs.** Every format in `--write-as` must be on
   the element library's `format/copy` list (`components/elements`, fed by
   `bank/formats.json`). An unknown format is refused with the real ids named;
   no run folder is made. A format the brand adds in its own `formats.json` is
   let through and named as the brand's own. `--channel` is NOT checked: it is
   free text for a person, and the library's `placement/all` list is what gets
   written (primary text, headline), not where it runs. The picks are recorded
   in `run.json` under `elements`.
2. **Copy — after stage 8 (Render), before the brief.** From
   `components/marketing-chain-checks`: `unfilled_check` on the finished copy (the part
   before `CHECKS`), and `price_check` of every price in the copy against ALL
   live prices in the brand's `products/offer-bank.md` (a copy run has no single
   offer key; `$49` and `$49.00` are the same price). A failure writes
   `check.json` in the run folder, keeps every file made so far, marks stage 9
   as held, and exits 2 — the brief is not written, because the brief is the
   act of handing the copy on. `--no-gate` skips it on purpose and says so in
   `run.json`.

Also: an account out of usage stops the run with one line (`USAGE LIMIT — …`)
on the first refusal — it is never retried. Ordinary failures still get three
attempts.

## Formats

`bank/formats.json` — the full list, as data. Triage reads it via `machine/formats.py`, so **adding
a format is adding a row**, not a code change.

## A delivery of finished ads → Meta copy

When an editor delivers finished ads (Jackie's 7, 2026-08-31, was the first):

```
machine/ads_to_copy.sh <folder-of-mp4s> <brand> <creator> <product> [prefix]
```

Per ad: a records teardown (no brief), then the Meta set written from the
record. Then `/usr/bin/python3 machine/gdoc_out.py --all --folder <drive-id>`
puts every published set into a Drive folder as Google Docs — pass the
delivery folder's id and the copy sits next to the creative it was written
for. Docs update in place on republish.

## Running it

```
# 1. dry run — checks every input, format, prompt field and model. Spends nothing, writes nothing.
python3 machine/copy_writer.py <source> --brand <brand> \
  --product brands/<brand>/products/<product>.md --dry-run [--avatar <key>]

# 2. the run
python3 machine/copy_writer.py <source> --brand <brand> \
  --product brands/<brand>/products/<product>.md \
  [--write-as caption,short-form] [--source-reference "…"] [--video source.mp4] \
  [--hooks 5] [--label <name>] [--avatar <key>] [--tier reads=<model>] [--model <model>] [--no-gate]

# 3. change one stage without buying the rest again
python3 machine/copy_writer.py <source> --brand <brand> --product <…> --label <name> --rerun-from stage8
```

Output lands in `runs/copywriter/<brand>/<label>/` at the repo root: per
stage the output, the prompt **as actually sent**, `check.json` from the gates,
and one `run.json` with status, timing, chars, model + tier, prompt version,
the picked elements and which inputs each stage fed on. The board is rebuilt at
the end of every run. There is no default brand — a missing or unknown
`--brand` is an error that names the brands that exist.

`machine/rerender.py [label …]` re-runs stage 8 for finished runs against each
run's OWN brand, avatar and product (read from its `run.json`); a run that does
not record them is skipped with a line saying so. `machine/batch.sh <brand>
<product-file>` runs the list inside it for the brand you name.

Tests: `python3 machine/test_rollout.py` — no model, no network, no real brand.

## The board

```
python3 machine/serve.py     # → http://127.0.0.1:8778/board.html
```

Rebuilds on every load, no-cache, byte-range for video. Polls `board.json`
every 3s so a run started after the page opened appears without a reload.

`board.build(embed=True)` writes `board-embedded.html` — media inlined as data
URIs — for publishing as an artifact, where a file path would resolve to
nothing. An embedded build stops polling and labels itself a snapshot.

**A run is rendered under the chain it actually ran**, read off its own
filenames — never today's stage table. The chain was rebuilt once and stage
keys were reused for different jobs; without this, an old bank-match output
appears under a heading called "Spec".

## Things a session here must not do

- **Never bridge anything into ai-workspace** — prompts, the copy bank,
  machine code — without the owner saying so for that specific piece.
  **AMENDED 2026-09-17 (the developer, with the owner's agreement): RUN RECORDS AND
  DELIVERABLES ARE NOT A BRIDGE.** They belong at
  `runs/<machine>/<brand>/<run-label>/` and go there without asking each
  time. The rule still covers everything else it names.
- **Never write into the brand tree.** It is read-only; a run that writes there
  breaks the boundary that lets it read freely.
- **Never let the machine pick a hook**, rank them, or mark one recommended.
- **Never improve VERSION 0.** It is the control; an upgraded control measures
  nothing.
- **Never reuse a stage number for a new job without retiring the old prompt**
  to `prompts/superseded/`. Two prompts matching `stage2-*` at the same
  version is a coin flip over which one runs, and it cost a broken run to find.
