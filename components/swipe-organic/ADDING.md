# Adding a swipe — the save door

*the owner, 2026-09-25: "there will be multiple sources for me to pull swipes in
and they all need to be organized and indexed through proper lanes."*

## A swipe is three things

| | | |
|---|---|---|
| 1 | the media | `records/swipe-videos/<id>/` |
| 2 | the Drive | `Shared Assets/lab/swipe-organic/records/swipe-videos/<id>/` |
| 3 | **the row** | a line in `<pool>/posts.json` |

**`components/intake` builds the index from the ROWS. It never walks the
media.** So doing 1 and 2 without 3 stores a swipe and hides it — no brand
tool, no teardown and no board can see it. On 2026-09-24 thirteen swipes
the owner handed over were stored this way; twelve of the thirteen were invisible
to the index the next morning.

The same day showed the other half of it: the Drive mirror had been broken
since this library graduated out of `lab/` (the mirror still pointed at the
old path), so **135 swipes, 1.1 GB, existed on one laptop only**. Nothing
said so, because nothing asked.

## The door

```
python3 add.py --pool tiktok-shop --brand brand-a ~/Downloads/*.mp4
python3 add.py --pool competitor-pool --brand brand-a --url <post link>
python3 add.py --check                    what is filed but not on the Drive
python3 add.py --pool tiktok-shop --list  what a pool holds
```

It does all three, every time, or none of them. It also resolves a TikTok
id's author, caption and view count through the site's own oembed and
yt-dlp — **no Apify allowance spent**, which mattered the week the cap was
gone and a whole source looked unreachable.

## The lane is four fields, not a folder

| field | values | what it decides |
|---|---|---|
| `source` | organic · paid · own | which half of the library it belongs to |
| `owner` | creator · competitor · own | whose asset it is |
| `kind` | video · image · carousel · copy · page · email | read off the asset |
| `brand` | a real folder under `brands/`, or shared | who it was swiped for |

`kind` picks the teardown: video → video-teardown, image and carousel →
image-teardown, and so on. **`--pool` is not a lane** — it is just what you
call one batch from one place (`tiktok-shop`, `competitor-pool`, `reddit-finds`), so
a swipe can always say where it came from. Both go into the row.

## After adding

```
python3 components/intake/tools/run.py --brand <brand>
```

That is the index every brand tool reads. `add.py` prints the line.

## The guard

`add.py --check` answers the question nobody was asking: how many swipes are
filed here but not on the Drive. Run it after a big add, and whenever the
library has moved.
