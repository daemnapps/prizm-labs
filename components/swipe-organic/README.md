# swipe-organic — what the avatars actually watch

## How to use it → (team dashboard)

> ## MY FEEDS IS THE FRONT (2026-09-19) — `desk.py`, port 8820, launch entry `my-feeds`
>
> the owner, that day: Swipe Studio "doesn't automatically update itself… there are
> no trigger actions… it's just a dashboard from stuff I already did." My Feeds
> is the answer: **type what you want to see → a dig runs → it becomes a standing
> feed → the owner's Pull now refills it.** (The nightly run that kept it filling,
> `com.daemn.feeds-daily`, is switched off — see SWITCHED OFF below.) Search
> runs across every post in every feed.
>
> **One Mac.** The board is served only from the owner's Mac, where launchd
> `com.daemn.feeds-serve` keeps `desk.py` up on 8820. Anyone else runs
> `python3 desk.py` on their own clone.
>
> `dig.py` (ask → plan → pull → sift → follow winners) · `sift.py` (keep/drop
> against the ask) · `daily.py` (every feed, every morning, with a money floor) ·
> `desklib.py` (shared) · prompts in `prompts/feed-*.md`, shown verbatim on the
> page. Asked feeds land beside the avatar feeds as `damon--<name>/` — same four
> files.
>
> **Ruled by the owner the same day: "This is what we're going with, and we don't
> use the old one."** My Feeds is THE board. Swipe Studio and the per-feed
> pages (feedapp.py) are not opened any more. (This block said his saves
> "already show here as the `damon · saves` feed" — they did not: that feed is
> DUG from the creators he saves twice or more. His actual saves arrived on
> 2026-09-22 as `damon · my saves`; see the block above.) New layers get added
> to My Feeds, never as another board.
>
> **The standing content rule (the owner, same day): pure entertainment only.**
> "Stuff that has nothing to do with selling anything or even learning about
> anything… brain rot… things people watch because they're truly entertained."
> It sits at the top of both prompts, above any ask. An ask names WHOSE scroll
> it is; it never turns the feed into content about their problem.
>
> **One feed per sub-avatar (the owner, 2026-09-20).** `subfeeds.py` walks every
> brand's sub-avatar cards and digs a feed for each one that has none —
> `<brand>--<sub-id>/`. The card's PERSON half is the ask; the plan prompt is
> told to ignore what we sell him. New card → run `subfeeds.py` → new feed.
>
> **Lanes, not keep/drop (the owner, same day).** Entertainment comes first — it is
> what people open the app for, before they are aware of any problem (the
> unaware end of the awareness scale). Educational is kept too, as its own
> filter on the page. Selling and junk never show. The sift fills a LANE slot;
> code decides what stays.
>
> **Money.** A dig is ~$__ of scraping. `daily.py` — switched off, see below —
> stops starting new feeds once one run has spent $__ (`--cap`, default 40),
> stalest feeds first, three at a time, so a run can pass $__ by the feeds
> already in flight; and it pulls nothing when the Apify account has less than
> $__ left this month (`--floor`, default 3). If the spend cannot be read,
> neither guard applies. **Pull now** runs one feed and has no dollar cap or
> floor of its own.
>
> **HIS SAVES ARE A FEED HERE NOW (2026-09-22).** He asked the right question —
> "we have My Feeds, why are we still using Swipe Studio?" — and the honest
> answer was that his actual saves only ever lived on the old board. They are
> projected into the feed store by `saves_feed.py` and show as **damon · my
> saves**, with covers, search, and Tear down. The feed already called
> `damon--saves` is a different thing and was retitled **damon · creators I
> save**: it is DUG from the accounts he saves twice or more, not the saves.
> Tear down on a feed with no avatar of its own now asks which brand and runs
> the machine on that brand — the pick-a-brand flow Swipe Studio had, which was
> the last reason to open 8765. **Pull now** on the saves feed re-reads the
> catalog; a fresh sweep of the saved folder still needs his own Chrome.

> **SWITCHED OFF the same night (the owner: "We don't need to run this automatically
> now… let me get the production line really clean").** `com.daemn.feeds-daily` is
> unloaded; the plist stays in ~/Library/LaunchAgents. Until he says otherwise:
> **Pull now** refreshes a feed, **Tear down** on a card sends that one post
> through the chain. **Where it goes (2026-09-22, his one ask):** the strip at
> the top of the board shows the run while it works and links to
> `/run/<label>` — that run's stages, its brief rendered with its frames, and
> links out to the source video, the run's own folder of prompts-as-sent, and
> the machine's board. Both kinds of Tear down write a job now; the avatar-feed
> path used to spawn `briefs.py` silently and show nothing at all.
> **Rebuilt the same day** on his read ("the formatting here is clunky"): the
> brief is the page now — 18 raw stage keys collapsed to one line, the run's
> facts as a labelled grid, and each frame a 200px reference beside its scene
> that opens full size, instead of a column of posters. It also names the model
> that drew the frames, which is the other thing he asked and the page could
> not answer. A feed's video goes in DECLARED for
> its sub-avatar (`run.py --for-avatar/--for-sub`, audience prompt v9).
>
> **The nightly brief line (the owner, 2026-09-20).** "A curated creative brief
> system that is running through my chains and proactively creating briefs for
> me to review." Until 23 Sep 2026 it ran every night at 01:00: `daily.py`
> pulled every feed, then `briefs.py` sent each avatar feed's best untouched
> entertainment post through
> `tools/video-teardown/machine/run.py --no-frames` (the full chain to the
> stage-5 brief, nothing generated). Each landed on the page's **Briefs to
> review** tab with Yes / No, the verdict written only by the page
> (`records/desk/briefs/<label>.json`).
> **That tab was removed 2026-09-22 at his word.** The nightly line, the queue
> and the verdict route are all untouched and still working — nothing on the
> board shows them now. Say where briefs should surface and they get a home.
>
> **The research chain is the product.** Plan → Pull → Sift → Follow → Repeat.
> Every feed's "The research chain" button shows each stage's prompt as sent
> and what came back (searches chosen; per-source returned / let in / turned
> away; kept-and-why beside thrown-out-and-why; creators followed). That view
> is where the research process gets tightened.

> ## SWIPE STUDIO IS GONE (2026-09-22) — My Feeds is the only board
>
> the owner, that day: **"remove swipe studio, everything needs to live in my
> feeds."** Done. `app.py` no longer serves — run it and it says where to go.
> Its launch entry is removed and port 8765 is free. Nothing was deleted: the
> file stays as the LIBRARY that builds the two pages it alone had, and
> `desk.py` serves them —
>
> | What it had | Where it is now |
> |---|---|
> | the saves board | the **damon · my saves** feed (`saves_feed.py`) |
> | fit filter (Brand B / Brand A / General) | the brand chips — a feed with no avatar is filtered per CARD, on the fit he saved it for |
> | lane filter (swipes / organic) | the **Ad-shaped / Culture** chips |
> | click → tear down → inject into a brand | **Tear down** on any card; a feed with no avatar asks which brand |
> | the format library | **Format library**, in the page header |
> | the rebuild sheet per swipe | **Sheet** on every Instagram card — the written sheet where one exists, otherwise the reference video and its six beats |
>
> To bring the old board back for an hour: `python3 -c "import app; app.serve()"`.

A standing library of the **organic** posts an avatar's world lives in, the
comment sections under them, and what those two things say about the room.

Not `swipe`. That reads paid ad libraries — competitors betting money. This
reads what your people watch for free, and the unit of interest is **the
comment section**, not the creator.

## Why

An email that names an athlete these people argue about and acknowledges the
city they live in is not interrupting — it is joining a conversation already
happening. That is what made the NBA sends work, and there was no source for
it. This is the source.

`avatar-two/profile.md` is already the finished output of this process — named
accounts, five core hashtags, format ranking by saves rate, comment receipts
with like counts. `avatar-one` has categories and not one handle. The target
is to close that gap.

## The rule

**Every claim traces to a view count, a like count, or a comment receipt.**
Borrowed verbatim from avatar-two's own header, because it is the right standard.
A seed with no cited line, a cluster with no count behind it, or a named entity
with no receipt does not go in.

## How it runs

The how-to is the atlas page linked at the top of this file (**How to use it**).

## What is here

| | |
|---|---|
**The tools** (each does one job):

| | |
|---|---|
| `apify.py` | the platform layer — the actors, one post shape, every hard-won fix carried over with its reason |
| `seeds/` | where each dig starts. **Data, not code** — a seed is a row, and every row cites the profile line it came from |
| `harvest.py` | runs a culture dig: discovery by **avatar** (hashtag, search, phrase) rather than by creator handle |
| `recomment.py` | deepens a dig's comment capture, in safe chunks |
| `affinity.py` | reads a dig: who keeps showing up (the room) + the wide catch (opportunity) |
| `saves.py` | turns the owner's captured save URLs into the categorized catalog |
| `feed.py` | runs one avatar-feed sweep against the feed backend |
| `hops.py` | graph hops — seats new feed sources from winner edges, on probation |
| `personakit.py` | builds a persona account's starter pack from owned data |
| `saves_feed.py` | projects the saves catalog into the feed store as **damon · my saves**, so My Feeds carries his saves (2026-09-22) |
| `app.py` | Swipe Studio, RETIRED 2026-09-22 — no longer a server; kept as the library behind My Feeds' `/formats` and `/handoff/<code>`. Was: saves board w/ thumbnails, click → pick brand → teardown chain runs → brief served. Desktop launcher: "Swipe Studio.app" |

**The library** — everything the tools produce:

| | |
|---|---|
| `records/damon-saves/` | the owner's 429 saved IG posts, listed and categorized |
| `records/culture-digs/` | deep digs into an avatar's world — posts, comments verbatim, room + opportunity reads |
| `records/avatar-feeds/` | auto-updating organic feeds per avatar, with full history |

Each shelf has a README saying exactly what every file is. Text in git,
media on Drive, one `**Drive:**` pointer per post.

Media: `Shared Assets/swipe/organic/<brand>/<avatar>/<sub>/`, reached through
`components/swipe-paid/swipe_home.py`. the developer moved it there from
`Shared Assets/lab/swipe-organic/` on 2026-10-07; old stored lab paths
still resolve through `swipe_home.resolve()`.

## Brand-agnostic, with teeth

Brand, avatar and sub-avatar arrive as arguments and resolve out of the seed
file. A handle, hashtag, phrase or word list hardcoded in a `.py` here is a
bug, not a shortcut.

**Avatars never blend.** avatar-one and avatar-two measured zero vocabulary
overlap — they are different people, not stages of one. Separate trees; only
the shared medical/marketing bans cross.

## Known, from the first real pass

- **The tags are global.** `#freshcut` returned a 5.7M-view Berlin barber post
  and comments in four languages. The avatar is US-centric, so a locale filter
  is the next thing this needs — right now it over-collects and says so.
- **Comments come back well.** 40 of 736 captured on that post at
  `--comments 40`, ranked by likes, against the ~15 the posts actor carries.

## Still to build

`affinity.py` (the commenter hop — who showed up, what else they follow),
`formats.py` (the shape census — microdrama, storytime, reaction, and what
each earns), a weekly-delta sweep, and the written profile the bank feeds.
(`watch.py`, the old weekly-delta sweep, was never wired in and was removed
2026-10-07, SI-60 (swipe export cleanup).)

## The split, same as swipe-paid (the owner, 2026-08-31)

**Words in git, media on Drive.** Post media lives at
`Shared Assets/lab/creators/<handle>/posts/` (the creator library) and
anything non-creator at `Shared Assets/swipe/organic/` (through
`components/swipe-paid/swipe_home.py`). Profiles
live here: `creators/<handle>/PROFILE.md`, regenerated by `profile.py`, with
the organic teardown queue — a creator's biggest posts not yet torn down —
on the Swipe-Organic Profiles page (see context/artifacts.md).
