# How the swipe decides

What the machine measures, what it infers, and what it cannot know. Read this
before briefing production off it — several of the labels are heuristics you
can correct, and one of the central numbers is a proxy, not a result.

---

## 0. What the data actually is

An AdPlexity advertiser sweep returns **eight fields per ad**:

```
id · type · title · description · image_url · video_url
meta_ad_type · meta_group_ads_count
```

A per-ad detail call (1 credit) adds one more: `landing_pages[].url`.

That is the whole input. **There is no spend, no impressions, no clicks, no
conversions, no start date, and no run duration.** Meta does not publish those
for commerce ads and no scraper has them. Anyone selling you "winning ads"
from this source is inferring, and so are we — the difference is that we say
which inference.

---

## 1. Angles — how a copy block is formed

Ads are grouped into **copy blocks** by exact match on
`(headline, normalized primary text)`.

**Normalisation:** AdPlexity appends the Meta ad id to the end of every primary
text. Without stripping it every ad is unique — the competitor's 407 ads came back as
407 blocks before the fix and 34 after. The strip is `\d{9,}$`.

**Validation:** run against the Competitor A sweep, which had a hand-built answer
already: 830 creatives collapse to exactly 18 blocks, 614 video / 216 image,
in the same rank order the human teardown produced. That is the only
ground-truth check in the system.

**Known limit — exact match is brittle.** A block re-run with one word changed
becomes a second block. the competitor shows this directly: `01`, `03` and `04` are
all "Stress showing on your face?" with different bodies. Treat near-identical
headlines as one family when briefing.

---

## 2. The two counts, and which one means what

| | what it counts | what it tells you |
|---|---|---|
| `creatives` | distinct ads sharing that copy block | how much they **made** |
| `variants` | `meta_group_ads_count` summed over the block | how much they **believe** |
| `max_variants` | the most-cloned single creative in the block | their single best bet |

`meta_group_ads_count` is how many near-identical ad variants run one creative.
**Ranking is on variants, not creatives.** The reasoning is the dropship
playbook's heat signal #1 — nobody clones a loser. Production of a creative is
cheap; duplicating one across ad sets is a decision to spend behind it.

**Why it matters concretely:** Competitor C's `31 · Stop Acne or Money Back` runs 5
creatives — rank 31 of 162, deep in the tail — but 80 variants with its top
creative cloned 23 times. Ranked by volume it is invisible. Ranked by
replication it is a top-ten block in the sweep.

**This is a proxy, not a result.** High replication means they are betting.
It does not mean the bet is working. A brand can clone a loser for a week
before killing it, and this sweep cannot see the kill.

---

## 3. Stage — where the block sits in the funnel

Three labels, assigned by pattern match:

- **top** — education, mechanism, problem callout
- **mid** — proof, story, result, comparison
- **bottom** — offer, scarcity, guarantee, discount

Rules live in `STAGE_RULES` / `STAGE_RULES_INTL` in `build.py` as plain regex.
They are recomputed on every `cluster` run, so editing a rule re-labels the
whole sweep for free.

**Two decisions that materially changed the output:**

1. **The headline is authoritative, the body is a fallback.** Classifying on
   headline + body filed almost everything as bottom, because nearly every
   direct-response body mentions a guarantee somewhere — "Understand your acne
   type" read as a scarcity ad. The hook carries the awareness level.
2. **Non-English rules are a separate pass.** the competitor came back 78%
   unclassified because its library is largely Italian, and the question-mark
   rule was anchored to end-of-string so "Sagging Neck? Not anymore..." missed.

**Coverage:** 210 of 214 blocks. **Not validated against ground truth** —
unlike clustering, nobody has hand-labelled a library to check this against.
It is a reading aid, not a measurement.

---

## 4. Seasonal — the hold-out

A block is flagged `seasonal` if it names a dated event (Back To School, Black
Friday, …) or carries an explicit date range.

This exists because Competitor C's single biggest block by variant weight —
`LOW STOCK WARNING`, 461 variants — is a Back To School sale running
"August 14–23 only". A 10-day promotion inside a 30-day sweep, and **20% of
the brand's entire variant weight.** Ranked raw it outranks everything they
believe year-round.

`top` holds these out of the evergreen ranking and reports them separately.
They are real and they make money; they are just not a strategy you can
reverse-engineer into an evergreen angle.

---

## 5. Pages — resolution and typing

**Resolution is one credit per block, not per ad.** The sweep returns copy but
no landing page. Clustering first and pulling detail for one representative ad
per block cost 196 credits across two brands instead of 1,244.

**Known limit:** we take the *first* landing page from *one* ad in the block.
If a block routes to several pages, we see one of them. Competitor A's hand-built
teardown lists two LPs for some angles; the machine records one.

**Type is decided structurally**, not by appearance, in this order:

1. `quiz` — step markers or a quiz host
2. `listicle` — five or more numbered list items
3. `product-page` — cart language
4. `advertorial` — over 4,000 characters of prose with none of the above

**Capture** is headless Chrome at 390×844 @2×, full-page, after a forced
lazy-load scroll. Two things this taught us:

- Entry modals are **on a timer, not on load** — absent at 2.5s, present at 9s.
  Probing once on arrival reports a clean capture that is half covered. Capture
  polls 14s and saves the modal separately as `popup.png`.
- Pages over 28,000px re-capture at 1× — at 2× a 45,000px page is ~90,000px of
  raster and Chrome times out mid-render.

---

## 6. What "winning" means here — and what it doesn't

**The claim the tool can support:** *this is what the brand is spending
behind, and where in the funnel it sits.*

**The claim it cannot support:** *this ad converts.*

Signals available and used:

- ✅ variant replication (heat signal #1)
- ✅ creative volume per block
- ✅ creative weight per landing page

Signals in the playbook that this data **cannot** provide:

- ❌ active duration — no dates are returned, so "live 30+ days" is uncomputable
- ❌ disappear → reappear relaunch — needs longitudinal snapshots we don't take
- ❌ per-page active-ad-count trend — same reason
- ❌ EU reach — a separate free Meta path, not wired up

**The strongest available upgrade** is longitudinal: sweep the same advertiser
weekly and diff. That converts replication-at-a-moment into
replication-sustained-over-time, which is a far better proxy, and it is the
only way to see a kill. Nothing in the current architecture does this.

---

## 7. The pipeline, end to end

```
sweep      adplexity_client.py advertiser <domain>   bills per ad returned
  ↓
cluster    ads → copy blocks, ranked by variants     free
  ↓
resolve    one detail pull per block → landing page  1 credit per block
  ↓
harvest    every creative → Drive mirror             free
  ↓
capture    page + popup screenshots, type, height    free
  ↓
records    the .md record set per block and page     free
  ↓
brief      _BRAND.md + teardown.md with slots        free
  ↓
db         swipe.db across every brand               free
  ↓
top        per-brand shortlist, split by stage       free
```

Two sections of every teardown are **never machine-written** — *Structural
findings* and *What to take, and what to beat*. Everything else in the file is
countable and comes from the data. That line is deliberate: the moment a
machine drafts the judgment, you stop being able to tell which parts were
observed.

---

## 8. Briefing from this safely

1. **Rank on variants, then read the stage.** A bottom-funnel block at the top
   of the list is a volume play, not an angle to build from.
2. **Hold out seasonal.** Check the `dated promo` badge before you brief it.
3. **Treat near-identical headlines as one family.** Exact-match clustering
   splits them; your brief shouldn't.
4. **Verify the landing page yourself.** One block, one recorded LP, possibly
   several real ones.
5. **Remember replication ≠ conversion.** You are copying what a competitor
   *committed to*, which is a much better starting point than guessing, and
   still not proof.

## Describing a swipe in the naming convention's words

Run after every sweep, once the media is on Drive:

```
python3 swipe_fields.py apply <brand>     # write the fields
python3 swipe_fields.py report <brand>    # what is judged, what is not
python3 build.py db                       # rebuild the corpus
```

Every creative gets the eight fields the ad namer uses for our own ads —
`media · source · talent · problem · angle · concept · format · ratio` — plus
`swipe:<brand>:<ad_id>`, the reference a production manifest keeps for the ad
it was built from. The vocabulary is defined once, in `../naming/names.py`, and
imported here; it is never re-declared. See `../naming/CONVENTION.md`, "The
swipe join".

`media` and `ratio` are derived — ratio is measured off the file in the Drive
mirror. The other six are judgements, and read `unclassified` until a person
makes them. A re-run never overwrites a judgement that has been made.

Two views carry the result:

- `swipe_creatives` — every swiped creative in the columns a Meta export is
  grouped by. Group both the same way and the answers are comparable.
- `to_judge` — what still needs a human, biggest angles first. That is the
  judging queue.

## Three lanes, one corpus

Everything we swipe from lives in one table, described in one vocabulary.

| lane | what a creative is | where it comes from | what we know for free |
|---|---|---|---|
| `own` | an ad we ran | `own/ingest.py` ← the ecom_data_sync Supabase tables | **everything** where the ad is named to the convention, plus real spend and ROAS |
| `paid` | a competitor's live ad | the AdPlexity sweep | nothing until a person judges it |
| `organic` | a post the avatar's world watches | `swipe-organic/records/avatar-feeds/` | the platform |

```
python3 own/ingest.py --days 120     # pull our own ads + their spend
python3 corpus.py build              # rebuild all three lanes
python3 serve.py 8780                # one UI over all of them
```

`corpus.py` reads each lane in its own native files and never writes to them.
Judgements — the six judged fields and the swipe/pass verdict — live in one
`judgements.json` keyed by `swipe_id` and are laid over the top on every
rebuild. One write path for one idea: three would lose a judgement the first
time a lane was re-ingested.

**Our own ads are the labelled half.** Where an ad carries a convention name
its fields are parsed straight out of it, and it arrives with what it earned
attached. That is the only lane with an outcome, which is what makes the other
two worth describing in the same words.

Notes from building it:

- Meta's `thumbnail_url` is a 64px crop and useless for judging. The full
  frame is in the creative's `object_story_spec`; the ingest prefers it.
- Organic covers are hotlink-protected and time-limited, so they are fetched
  and cached server-side (`/thumb`). Instagram and YouTube covers survive;
  **TikTok signatures expire within days** — re-sweep or open the post.
