# components/research-gatherer — querying the open internet for a chain

Extracted 2026-09-18 (RG-1), the day it was built, on the owner's ruling: *"the
OS pulls COMPONENTS into workflows, so the research gatherer must be a
resident component, not code inside one machine."* Same shape as the LL-1
precedent (`components/language-layer/`) — an engine with no stage map, a
chain's shim binding its own definitions on top.

What it is: three things behind one engine. (1) `find_rooms(...)` — ROOM
DISCOVERY: one unrestricted search in the avatar's own desire words that
finds which communities that avatar actually talks in. (2) `inputs(st,
chain_profile)` — a Schwartz-shaped research packet for one run: forums
pulled for those rooms, comments on the swiped post, and (when the caller
hands in a chain profile) the language bank's own tagged rows. (3) the C2
deep-research trigger — pulls for one sub-avatar using that file's rooms +
desire words + the Schwartz research questions, and files verbatim rows,
with permalinks, into that sub-avatar's own language bank. What it is not:
anybody's chain. It holds no stage map, no brand and no opinion about which
STAGE_USE keys a chain cares about.

## Rooms are FOUND, not written down (the owner, 2026-09-18)

> *"He should never have to write down rooms - the system finds where the avatar talks on its own."*

Before this ruling, an avatar with no `### rooms` block got
`[UNFILLED: no rooms recorded for this avatar]` and the forums pull simply
did not happen, which made a hand-typed list of subreddits the price of
entry for every new avatar. Now:

1. **A block a PERSON confirmed wins outright.** The lock is one line inside
   the block — `confirmed by: <your name>` — and nothing else. Not the
   heading's wording, not who last touched the file. A confirmed block is
   read as written and discovery never runs.
2. **Anything else — a seeded block, an agent's guess, no block at all —
   means the gatherer goes and looks.** ONE search, in the avatar's own
   desire words (the words `desire_words()` already reads off the file), no
   subreddit named, **posts only**, sort and window from `research.json`'s
   `discovery` block (`relevance` / `year` today), cap ~40 items (~$__).
   The posts that come back are tallied by the room they came from,
   **weighted by score** — the loudest room, not merely the busiest — and
   the top 5 are the rooms.

   **Two things the first live pulls taught, both now settled in config.**

   *Posts only.* The very first live discovery (2026-09-18, a
   body-pigmentation sub-avatar) came back with exactly ONE room, and it was
   a cave-diving video: the reddit door's default `maxComments: 25` let a
   single viral thread's comment tail eat the whole 25-item budget — 1 post,
   24 comments, one room. Discovery is a question about ROOMS, and a comment
   thread is one room repeated, so it passes the door's `--no-comments`.

   *Relevance, not top.* With posts-only fixed, sort `top` still came back
   with `r/interesting`, `r/mildlyinteresting` and `r/shittymoviedetails` —
   because sorting an UNRESTRICTED search by score ranks the loudest posts
   on Reddit that happen to share a word, not the posts about the topic.
   Sort `relevance` on the same query, same cap, returned `r/skincare_ph`,
   `r/40PlusSkinCare`, `r/Blackskincare`, `r/SkincareAddicts` and
   `r/indianbeautyyappers` for $__. Relevance finds the topical rooms;
   the score weighting then picks the loudest of THOSE, which is what the
   weighting was always for. Both knobs live in `research.json` rather than
   in code, so the next correction is a config change; the cache key carries
   them, so no answer from before a change is ever served.
3. **Every discovery is recorded twice.** Into the run (`rooms-found.json`
   and a "Rooms" section in `research.md`: room · posts · score · a sample
   title each), and back into the avatar's own file as

   ```
   ### rooms — found <date> by the gatherer (edit freely; add "confirmed by: <your name>" to lock)
   - r/<room> — <n> post(s), <score> total score in the discovery pull
   ```

   replacing any earlier gatherer- or agent-seeded block and leaving every
   other byte of the file exactly as it was. The `curated … Builder C`
   blocks of 2026-09-18 count as seeded and were replaced by the first real
   discovery.
4. **Discovery is cached like every other pull** (14 days, per brand /
   avatar / sub / words / cap / sort / window), so a repeat run on the same
   avatar, from any chain, re-spends nothing — and changing how the search is
   shaped invalidates the cache rather than serving a stale answer.
5. **It is never worse than before.** No key, a 403, a strange actor, or an
   avatar with no desire words all come back as an empty list, and the
   caller falls back to whatever the file already said. `--dry-run`
   discovers nothing and spends nothing.

**Both machines keep working, and that was the hard constraint of the
move.** `components/video-teardown/machine/research.py` is now a thin shim
over this engine: same CLI (`run --run <dir>`, `deep --brand … --avatar …
--sub …`, `--all`, `--pick-thinnest`, `--dry-run`), same output, same cache.
Nothing was asked of the owner and nothing changed on the video-teardown side.
Any sibling chain adopts the same door by writing its own equally-thin shim
— **`copy/machine/research.py` is the second one** (2026-09-18,
the owner's ruling *"the live research gatherer runs in the copy machine too"*),
binding the copy chain's own `depth`/`spice` keys, its own `for_stage`, and
its own `results/<label>/` run folder; the copy chain's stages 6 (expansion)
and 7 (close) read the packet as `{research}`.

## Research is reconciled against the avatar's demographics (the owner, 2026-09-18)

> Discovery for a sun-damage sub-avatar came back with `r/Blackskincare`,
> `r/skincare_ph` and `r/indianbeautyyappers`. That brand's customers are none
> of those people. **Research has to be reconciled against the avatar's
> demographics or it is irrelevant for that avatar.**

Three parts, and a deliberate asymmetry running through all of them.

1. **The avatar says who it is, in slots.** `profile.md` carries a
   `### demographics` block — `age` · `gender` · `skin tone / ethnicity` ·
   `region` · `language`, plain words, `unknown` allowed, never inferred from a
   name. A sub-avatar inherits it and may override it line for line.
   `demographics(brand, avatar, sub)` is that read. The block's spec lives with
   the avatars, in `brands/_TEMPLATE/core-avatars/README.md`.
2. **The room name is read for markers.** `room_fit(room_name, demo)` returns
   `yes` / `no` / `unknown` with the reason, judged against a marker table in
   `research.json` (`demographic_fit`) — room-name signal → demographic signal.
   Markers are matched by segment, not by substring: a marker of three
   characters or fewer must equal a whole segment (`ph` finds `skincare_ph` and
   never `phimosis`), a longer one must start a segment (`black` finds
   `blackskincare`, and `men` never fires inside `women`). Age is compared as a
   band, where `30plus` is open upward. No room of ours is named in the table —
   these are generic community-naming conventions (rule 7).
3. **`no` rooms are dropped before anything is pulled from them.** Discovery
   keeps `yes` and `unknown` and drops `no`, recording each drop and its reason
   in `rooms-found.json` and under "Rooms dropped — demographic mismatch" in
   the run's `research.md`. The block written back into the avatar's file lists
   only the kept rooms plus one line naming the dropped ones, so a dropped room
   never sits there looking like a room to pull from. Every filed bank row
   gains `"fit": {"room", "verdict", "why"}`, and a row from a `no` room is
   never filed at all — `deep_for` keeps those in
   `rows-dropped-demographic-mismatch.json` in the run record instead. The
   run's `research.md` header prints a `demographics` line so a reader can see
   what the check ran against.

**The asymmetry is the whole safety property.** The table can say a room is
plainly for SOMEONE ELSE; it can never say a room is plainly for us. A name
with no marker is `general` and is kept. A slot the profile leaves `unknown`
rules nothing out — **an avatar with no block at all drops nothing, ever**, so
this is never worse than the behaviour it replaced. And a `### rooms` block a
person confirmed still wins outright: the check runs and records which rooms it
would have questioned, and drops none of them.

The fit verdict is NOT cached. The rooms a search found are; they are re-judged
on the way out, so correcting a demographics block takes effect on the next run
without re-spending on the search.

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

| question | answer |
|---|---|
| **engine + owner** | this folder's `research_gatherer/engine.py` — **the owner** (built as part of the Schwartz-backbone build, 2026-09-18; corrects to the developer if the engine-ownership convention from LL-1/IDT-1 applies here instead) |
| **definitions + curator** | **three kinds, none of them here.** (1) **Chain profiles** — which language STAGE_USE keys a chain wants queried (`language_stages`), the callable that runs that query (`language_for_stage`), and where a run's own output folder lives (`run_dir`) — are per-chain, curated by that chain's owner (the owner, for video-teardown) and live in the chain's shim, never here. (2) **Desire words** are avatar content, curated brand-side under `brands/<brand>/core-avatars/**/sub-avatars/*.md` — rule-9 (brand home). **Rooms are FOUND by this engine**, written back into that same file, and a person locks a block by adding `confirmed by: <name>` to it (see `brands/_TEMPLATE/core-avatars/README.md`); a person curates rooms only when they choose to. (3) **The Schwartz research questions** are the marketing-doctrine component's (`components/marketing-doctrine/frameworks.json`, `research_questions`), curated by the owner there; this engine falls back to a small built-in list, marked as a fallback, only when that file is missing or empty |
| **the plane it emits** | **none, directly.** `inputs()` writes into the CALLING chain's own run folder (`<run>/research/{language,forums,comments,research}.md`), at the path that chain's `chain_profile["run_dir"]` names. `deep_for()` writes into the avatar's own bank (the sub-avatar's OWN folder beside its card — `brands/<brand>/core-avatars/<avatar>/sub-avatars/<card stem>/language/deep-research-<date>.json` (rows carry `sub`; the language layer reads every sub-avatar folder as part of the avatar's bank) plus the clean readable report at `…/<card stem>/research/<date>/` (research.md, rooms-found.json, rows.json — only what passed the gates) — the owner's 2026-09-18 exception, in this shape only, to "a person moves it") and a run record at the repo-root `runs/research/<brand>/<sub>-<date>/` (rows, receipts, two bands, spend) — **never inside this component**: run records don't live in a component (CLAUDE.md §1, `runs/README.md`), even though this engine is what writes them |
| **what the manifest declares per entry** | n/a — no manifest. `research.json` at the component root is config (actor ids, spend caps, cache days, and the `discovery` block's sort / window / posts-only / keep), not a definitions registry |

## Contract

Two dependable surfaces, same as the engine's own docstring:

### 1. The API

```python
from research_gatherer import engine

engine.configure(workspace=None)                 # this host's workspace root

engine.find_rooms(brand, avatar, sub, cap=40)
# -> [{"room", "posts", "score", "sample_title", "sample_url"}], loudest
#    first. ONE unrestricted, posts-only search, shaped by research.json's
#    `discovery` block (relevance / year today). NEVER RAISES: no key / 403 /
#    no desire words -> [].

engine.resolve_rooms(brand, avatar, sub=None, topics=None, root=None,
                     discover=True)
# -> (rooms, words, discovery_record_or_None). A `confirmed by:` block wins;
#    otherwise discovery runs and is written back into the avatar's file.

engine.demographics(brand, avatar, sub=None, root=None, sub_path=None)
# -> {"age", "gender", "skin tone / ethnicity", "region", "language"} off the
#    `### demographics` block — the CORE avatar's, overridden line for line by
#    the sub-avatar's own block. {} when nobody has written one. NEVER RAISES.

engine.room_fit(room_name, demo)
# -> {"room", "fit": "yes"|"no"|"unknown", "marker", "markers", "why"}. Pure:
#    no network, no file read, so the whole table is testable on strings alone.

engine.split_by_fit(rooms, demo)   # -> (kept, dropped), each row carrying `fit`
engine.markers_table()             # -> research.json's marker rows
engine.demographics_line(demo)     # -> the one line a run's research.md prints

engine.rooms_block_state(text)     # -> ("confirmed" | "seeded" | "none", match)
engine.tally_rooms(posts, top=5)   # -> the weighting, pure and testable
engine.write_rooms_block(path, found)   # -> True when the file changed;
#    never overwrites a block a person confirmed

engine.inputs(st, chain_profile=None)
# -> {"research": <markdown, the _METHOD standard: receipt on every claim,
#     two bands, counts with denominators, [UNFILLED] where nothing came
#     back>}. NEVER RAISES.

engine.deep_for(brand, avatar, sub, cap, dry_run=False)
# -> {"ok", "rows_written", "spend", "sample", "bank_file", ...} or
#    {"ok": False, "why": ...}. Never invents a room; a row with no
#    permalink is dropped before it's ever written.

engine.pick_thinnest(root=None)                  # -> (picked, ranked) across ALL brands
engine.all_sub_avatars(root=None)                # -> every sub-avatar anywhere, with its file
engine.row_count(brand, avatar, sub, root=None)  # -> language rows tagged to that sub
```

### 2. `chain_profile` — the definition a caller hands `inputs()`

```python
chain_profile = {
    "language_stages": ["depth", "spice"],          # this chain's STAGE_USE keys to query
    "language_for_stage": my_language_module.for_stage,   # that chain's own callable
    "run_dir": lambda st: Path(...) or None,        # where <run>/research/ goes
}
```

Any key may be omitted — the section it feeds records `[UNFILLED: why]`
rather than guessing or falling back to someone else's chain. `inputs(st)`
with no `chain_profile` at all still runs (forums + comments still pull);
only the language-bank section goes `[UNFILLED: no chain profile given]`.

### The CLI

```
python3 components/research-gatherer/gather.py [deep|rooms] \
    [--brand B --avatar A --sub S | --brand B --all | --pick-thinnest] \
    [--cap N] [--dry-run]

# the voiceprint mode — the spoken profile of a brand's creators, off their own audio
python3 components/research-gatherer/gather.py voiceprint --brand B --creator H
python3 components/research-gatherer/gather.py voiceprint --brand B --all [--dry-run]
```

**`voiceprint`** (2026-09-19, the owner: "analyze our actual content creators
that we've worked with… analyze the audio specifically and create voice
prints"): `research_gatherer/voiceprint.py`. For every ready post in the
brand drive's newest `SELECTED-<date>.json` it pulls the audio with ffmpeg
(mono 16 kHz), transcribes it ONCE on ElevenLabs Scribe with word
timestamps (kept at `runs/research/<brand>/creators/<handle>/transcripts/<post>.json`,
so a second run spends nothing), and measures the SPOKEN PROFILE — words per
minute, sentence length, fragment rate, contraction rate, marker inventory,
openers, sign-offs, questions, pauses, energy off the wav, in-words and
phrases with one receipt each — into `voiceprint.{json,md}` beside the
creator's profile and the brand roll-up `VOICEPRINTS.md`, pooled by
denominator per avatar (a creator under 100 measured words is listed as
thin and left out of the band). A post with no audio track or no speech is
named and left out. The teardown chain binds the roll-up as `{voiceprint}`
(`~voiceprint` in extra-stages) and the spoken pass matches its rhythm.

Two modes, chain-agnostic. `deep` (the default when no mode word is given,
so every older call still works verbatim) matches `deep_for`/`pick_thinnest`
above one-to-one, and runs discovery first when the rooms block is not
confirmed. `rooms` runs **discovery alone** and prints what it found — room,
posts, score, a sample title — writing the block back unless a person has
confirmed it; `--dry-run` prints the search it would fire and spends
nothing. A chain's shim exposes `run --run <dir>` on top of this same engine
for its own research var.

### `apply` — the bank tools' changes, written through the gatherer (2026-09-29)

```
python3 components/research-gatherer/gather.py apply --proposal runs/language-layer/<b>/<run>/proposal.json [--dry-run] [--root <tree>]
```

`brands/` is read-only to machines (decision-log 2026-09-17) and this
component is the one machine ruled to write the bank (the owner 2026-09-18, the
O5 carve-out: only what passed its gates). The language layer's bank tools
(`tools/language-layer/tools/` — the labeller's backfill, the id
renamer, the source mapper, the `keyword-cta` tagger, the origin rule) no
longer write bank files: each writes a PROPOSAL under
`runs/language-layer/<brand>/<run>/` and hands it here.
`research_gatherer/bank_apply.py` checks it, then writes it with the same
file writer new rows are filed with (`annotate._dump`: each file keeps its
indent, escaping and newline).

Its gates — REFUSED whole, nothing written: not a language-bank proposal or
another brand's; a path outside `brands/<brand>/core-avatars/` or not a bank
file (rows only in `language/`, used-lane marks only in `language/used/`,
one whole file only: `core-avatars/language-sources.json`); a field the bank
tools do not own (rows may set awareness, sophistication, lane_words,
origin, voice, use, id, source — never the words); an id off the Naming
Standard or two rows on one id; a source change that drops the row's link.
SKIPPED row by row and listed: a row no longer there, words changed since
the proposal read them, a label a person wrote. A proposal never adds or
removes a row. It writes `applied.json` + `applied.md` beside the proposal.
Test: `python3 components/research-gatherer/test_bank_apply.py`.

## Rules

- **Brand-agnostic** (workspace rule 7): no brand, avatar or room name in
  this code or in `research.json`. Desire words arrive at run time from
  `brands/<brand>/core-avatars/**`, and rooms are discovered from those
  words — a room name never enters the code, the config, or a prompt.
- **Ships no stage map**, same reasoning as `language-layer/`: what a
  chain's language section is looking for is that chain's call, not this
  engine's.
- **Reuses rather than re-implements**: `control-room/tools/
  reddit.py` (the Reddit door — actor, flags, cap, 403 handling) and
  `components/apify/apify.py` (the shared token + spare-account
  layer, the per-platform comment actors), both loaded as modules and
  driven through their own existing contracts, never copied.
- **Never raises.** No Apify key, a 403, or a missing actor never stops a
  chain — the section says `[UNFILLED: why]` and the caller moves on.
  `deep_for` is the one exception that's allowed to come back empty
  (`rows_written: 0`) rather than silent, since a deep pull is itself the
  point of running it.
- **Spend is capped and printed** on every pull (`research.json`); forum
  pulls cache 14 days per (brand, avatar, sub, words, rooms), comment pulls
  per source_url, under the repo-root `runs/research-cache/_system/` (never inside
  this component — same reasoning as run records) — so repeat runs on the
  same avatar, from any chain, don't re-spend.
- **A row with no permalink is never written.** The bank schema
  (`brands/language-schema.md`) requires a source; `deep_for` enforces it
  twice (once while accumulating pulled rows, once again in
  `build_bank_rows`).

## The declared test

`python3 components/research-gatherer/test_research_gatherer.py` — no
pytest, no network, no dependency, every Apify-touching call monkeypatched.
Proves: a missing key never raises (`inputs`, `deep_for`, both pull
functions); the bank row schema is the schema's; a row without a permalink
is dropped; a cache hit skips the pull; `--dry-run` never spends; and
`pick_thinnest` actually picks the thinnest, on an isolated temp tree. On
room discovery it proves: the tally ranks by TOTAL SCORE and never invents a
room from a row that names none; a `confirmed by:` line is the only lock and
an agent-curated heading is not; the write-back replaces the seeded block
and leaves every other byte of the file identical, and never touches a
confirmed one; discovery fires exactly ONE search with no subreddit named,
sort `top`, window `year`; a repeat discovery is a cache hit; and both
`deep --dry-run` and `rooms --dry-run` discover nothing and spend nothing.
On demographic fit it proves: the marker table names no room of ours; the five
slots parse and an `unknown` slot reads as unknown even when it explains
itself; the three rooms that started the ruling are `no` for that avatar and
kept for one whose profile says nothing; a sub-avatar's own block overrides the
core's line for line; `men` never fires inside `women` and `ph` never inside
`phimosis`; an age band that overlaps keeps and one that cannot drops; the
write-back lists only kept rooms while naming the dropped ones; and every filed
row carries a `fit` while a row from a `no` room is never filed.

## Gates (2026-09-20) — a hold is written down

A deep pull now leaves `check.json` in its run folder
(`runs/research/<brand>/<sub>-<date>/`), keyed by gate, written through the
shared `components/quality-checks` `hold()`: **inputs** (the sub-avatar file
exists, there are rooms), **elements** (every doctrine technique or delivery
dial a research question names is a real one in `components/elements`),
**delivery** (every row carries a permalink, none from a mismatched room,
something to file). What passes and fails is what passed and failed before; a
pull that files nothing now reads `HELD`, and `deep_for` adds `held` /
`problems` to the dict it already returned. The one new refusal is the
elements gate — `research.json` › `gates` › `elements: "record"` puts the old
behaviour back. Code: `research_gatherer/gates.py`; test:
`python3 components/research-gatherer/test_gates.py`; the table is in
`CLAUDE.md`.

The engine's workspace is now found — `AI_WORKSPACE`, else the checkout the
file sits in, else `~/Projects/workspace` — so a worktree no longer reads
and writes the main checkout. A shim's `configure(workspace=...)` still wins.

## Kill-condition

Fewer than 2 real chains calling `inputs()` post-adoption → fold this back
into `components/video-teardown/machine/` the way it started (same LL-1
reasoning: a component earns its wall by being shared, not by being tidy).


## Nightly (2026-09-19) — the bank grows on its own

`~/.local/bin/daemn-research-nightly.sh`, scheduled by
`~/Library/LaunchAgents/com.daemn.research-nightly.plist` at 02:30 on the owner's
Mac. Per brand that has sub-avatars: `gather.py deep --brand <b> --pick-thinnest
--cap 150` (per-brand `--pick-thinnest` landed the same day — with `--brand` the
pick is narrowed to that brand's own sub-avatars, so a brand with a thick bank
never starves a thin one), then `git commit -- <only the paths the pull
produced>` and push. Nothing else in the tree is staged. `DRY=1` prints the
queries and spends nothing. Log: `~/Library/Logs/daemn/research-nightly.log`.
The script is machine setup, not a component: it lives on the Mac that runs it,
like the hourly workspace pull, and this section is its record.

## Daily language pull (2026-09-29) — the free sources, on a trigger

the owner's ruling, 2026-09-29: automate only the sources that cost nothing. The
2026-09-23 "no automatic Apify spend" stands — organic comment scraping, the
top-ad scrape and Reddit deep pulls stay on request. `daily.py` runs every
free source for every brand that has `brands/<brand>/operations/language-pulls.json`,
files the rows through the same read as `ownvoice` (intake read + the
language layer's labeller, `research_gatherer/voicepull.py`), then refreshes
the source registry (`tools/language-layer/tools/map_sources.py`,
proposal → `gather.py apply`) and rebuilds the bank page
(`tools/bank_page.py` → `runs/language-layer/_system/bank.html` + `BANK.md`).

| Source | Mode | What it reads | Schedule | Cursor (state file) |
|---|---|---|---|---|
| Ad comments (warehouse) | `ownvoice --no-scrape` | `meta_ad_comments` for the brand's Meta ad account | daily 05:30 | `runs/research/<b>/ownvoice-state.json` |
| Support tickets (Gorgias) | `ownvoice --no-scrape` | warehouse `gorgias_ticket_*`, customer messages, only when `brand.json` › `accounts.helpdesk == "gorgias"` | daily 05:30 | `runs/research/<b>/ownvoice-state.json` |
| Surveys (Google Forms) | `surveys` | each response sheet in `language-pulls.json` › `surveys`, first tab exported as CSV through the Drive API as the `GDRIVE_SA_KEY` service account | daily 05:30 | `runs/research/<b>/surveys-state.json` (newest response per survey) |
| Store reviews | `reviews` | `language-pulls.json` › `reviews`: Junip public API (store key by name) or Judge.me API (shop domain + token by name) | daily 05:30 | `runs/research/<b>/reviews-state.json` (newest `created_at`) |
| Interviews / panels | `interviews` | new `.md` / `.vtt` / `.txt` transcripts in `language-pulls.json` › `interviews.inbox`; customer turns only | daily 05:30 | `runs/research/<b>/interviews-state.json` (files ingested) |
| Top-ad comments, organic comments, Reddit | `ownvoice` (scrape), `comments`, `deep` | Apify | **on request only** | — |

```
python3 components/research-gatherer/gather.py surveys    --brand B [--dry-run] [--since D] [--avatar A]
python3 components/research-gatherer/gather.py reviews    --brand B [--dry-run] [--since D] [--avatar A]
python3 components/research-gatherer/gather.py interviews --brand B [--dry-run] [--avatar A]
python3 components/research-gatherer/daily.py [--brand B] [--dry-run] [--no-push]
```

Every row: source id by the Naming Standard (`survey_<b>_<survey>` with
`question` `q-<nn>_<slug>` — the bank's own number when the question is
already there — and `item` = a response id hashed from values never stored;
`review_<platform>_<b>` with `item` = the review id and `signal.rating`;
`interview_<b>_<date>` / `panel_<b>_<date>` with `item` = the turn), `origin`
internal, de-duped against the avatar bank by `ref`. Lane: a verified buyer,
a customer-survey answer or a customer interview is a customer by
relationship; a refund-survey answer is churned (`"lane": "churned"`); the
rest are read from the words. Emails, names and phone numbers are never read
into a row. Every mode takes `--dry-run` (pull and count, read and file
nothing) and writes the usual run record `runs/research/<b>/<mode>-<run>/`.
A cursor moves only when nothing was held. Tests: `test_voicepull.py`.

**Where it runs:** a launchd job on the owner's Mac, `com.daemn.language-daily`
at 05:30 local, running `~/.local/bin/daemn-language-daily.sh` (copies of
both in `schedule/`). The script reads `daily.py` from origin/main so the
newest code always runs; `daily.py` makes a throwaway checkout off
origin/main under `~/Library/Caches/daemn/language-daily/`, runs the pulls
there, stages ONLY what the run produced (bank `language/` files, the source
registry, `runs/research/**`, `runs/language-layer/**`), commits and pushes
with rebase-retry, never force. A conflict leaves the checkout in place and
names it in the log; the cursors did not move on origin, so the next run
pulls the same rows again. The Mac, not the mini: the run needs `claude -p`
on the owner's subscription, the warehouse URL, the Drive service account and
the Junip key, and the mini's lab-run grant (`team/dispatch-grants.json`)
reaches none of them without a gated edit. Summary per run:
`runs/research/_system/daily/<run>.md`. Log: `~/Library/Logs/daemn/language-daily.log`.

**Apify is fenced off, fail closed.** Inside the run every Apify host fails
to resolve and the engine's Apify layer raises; one attempt and the run
exits 3 with nothing committed.

## The culture map — built bottom-up from real data (the owner, 2026-10-06)

*"Our systems need to be fully dynamic and based on the real language only."*
Each avatar's `core-avatars/<avatar>/culture-map.md` (what they watch, who they
trust, their references and slang, what they care about, what they laugh at,
what is off-limits) is written from evidence, not from the profile and a hunch:

    python3 components/research-gatherer/culture_map.py --brand B --avatar A [--dry-run] [--pack-only]

1. **Evidence pack** (no model): the bank's culture-tagged rows, loudest first
   (through the language layer); the avatar's feeds (`VIEWER_FEEDS`: top posts,
   authors, hashtags); any culture digs; the video teardown's culture reads
   (`stages/1k-culture.json`). The profile is not evidence — it only seeds "To test".
2. **Write** — `prompts/culture-map-v1-damon.md`, one Claude call; every line
   ends in its evidence ids.
3. **Verify** — a line that cites nothing, or an id not in the pack, is dropped
   and counted in the footer. A hand-written map is kept once beside it.

The marketing doctrine's humor and culture rules read this map as the RQ-17
receipt. Tests: `python3 test_culture_map.py`.
