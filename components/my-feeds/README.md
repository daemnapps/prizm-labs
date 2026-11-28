# My Feeds — what already works, organic and paid

**Keys this tool needs:** none. Put your own in `.env` at the top of the repo — see [`.env.example`](../../.env.example).

The swipe end of Prizm Labs. In production this is **My Feeds**: one board of
what people actually watch (organic) and what competitors are paying to show
them (paid). This folder is the public half of it — the structure pulled out of
those swipes, with no brand, creator or competitor named.

| | What it is | Start with |
|---|---|---|
| **Organic** | 48 formats pulled apart from 377 posts that worked, some past a hundred million views. | [`organic/START-HERE.md`](organic/START-HERE.md) |
| **Paid** | 6,269 live competitor ads across nine markets, reduced to the ten angle shapes that keep working. | [`paid/START-HERE.md`](paid/START-HERE.md) |
| **Library** | The index over both: the organic formats, the angle shapes and the counts, published as a page. *Team-only build* — it reads our private workspace; the page is for everyone. | [`library/README.md`](library/README.md) |

## The feed: Studio → Production → Swipes

[`feed.py`](feed.py) is the one swipe feed the Studio shows (`/api/desk/feed`):

- **One list, one filter:** All · Organic · Paid · Links I pasted, and a profile (who the feed was pulled for).
  Each post has one identifier (platform and the post's own id), so a post pulled by two feeds, pasted again or
  torn down twice shows once. Torn down folds repeat runs of the same swipe into one row.
- **Paste a link:** the post downloads and goes to [`../video-teardown/`](../video-teardown/) in code
  (`run.py … --to 2`, the teardown stages only). The same happens from any card's **Tear down**. A post already
  torn down is never torn down twice.
- **Paid** is the shop videos picked from the product finds (TrendTrack, Kalodata) plus ad-library sweeps of the
  advertisers still in those finds. The paid brands tracked now are the shops in the newest finds.
- **Clear out:** old posts (over a year, never torn down), last season's posts, profile feeds and advertisers
  nobody pulls any more. They are kept off the feed and listed for the owner's yes; a yes is recorded in
  `runs/my-feeds/decisions.json`. Nothing is deleted from the folders the feed reads.

Where the feeds live is set per computer in `runs/my-feeds/sources.json` (`{"organic": [...], "paid": [...]}`);
with none, this repo's own `components/swipe-organic/records/avatar-feeds` and `components/swipe-paid`.
`python3 feed.py show|dead|torn --brand <brand>` prints the same from the command line.

**How to use it:** pick a format or an angle shape, find a real example, then
hand that example to [`../video-teardown/`](../video-teardown/) — the structure
comes out, your brand goes in.

The packs were built 2026-09-22 from the production feeds.

## The page: daemn.co/feeds/

**[daemn.co/feeds/](https://daemn.co/feeds/)** is My Feeds itself, read-only:
good posts to copy, organic and paid, picked by who it is for. Tap a post and
make your own in three steps:

1. Press **Open in Claude** or **Copy the prompt**.
2. Open your Higgsfield Supercomputer, or Claude Code with this repo.
3. Paste and press Enter. It takes the post apart
   ([`../video-teardown/`](../video-teardown/), or
   [`../image-teardown/`](../image-teardown/) for a picture) and writes the
   brief for that person.

**How the page gets its posts.** Nothing on it is live and nothing on it can
spend. It reads a static export in `docs/feeds/data/`, written by
[`components/swipe-organic/feedsexport.py`](../../components/swipe-organic/feedsexport.py) (in this repo since 12 Oct 2026):

| File | What it holds |
|---|---|
| `index.json` | the people (a plain label and one line each), grouped by product world, with counts and the build date |
| `organic/<who>.json` | that person's top 120 posts by views — link, handle, date, views, likes, one line on why it works |
| `paid/<who>.json` | the longest-running competitor ads in that person's product world — headline, 200 characters of copy, days running, copies, the public Ad Library link |
| `sheets/<post>.json` | the rebuild sheet, for posts already taken apart |
| `thumbs/` | 360px covers, and the six-frame strip where there is one |

The export copies an allow-list of fields and nothing else, re-keys every feed
by person (no brand name anywhere), and refuses to write unless a no-secrets
scan and a size check pass (pictures under 40 MB; one run changes under 3 MB).
It reads what is already pulled — it never pulls, so it never spends. It runs
after each Pull on the board; [`components/swipe-organic/feeds-publish.sh`](../../components/swipe-organic/feeds-publish.sh)
exports, commits and pushes in one go.

**Full breakdowns of one brand's ads** — every live ad, the words they keep,
the pages behind them — live at [daemn.co/feeds/examples/](https://daemn.co/feeds/examples/)
(`docs/feeds/examples/`). The old `/swipes/` addresses forward there.
