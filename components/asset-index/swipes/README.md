# Swipes: viral covers

Real covers, each one an indexed swipe next to the footage library, for paid and organic work. Two kinds of pull
land in one index: what the platforms' discovery surfaces are pushing, and what one avatar's own feed carries. A cover
step picks the cover it follows from here by avatar and by move (`find`), and names the swipe id on its record.

| Step | Command (`covers.py`) | Cost |
|---|---|---|
| Pull the discovery surfaces | `pull <dir> [--key-name APIFY_TOKEN]` | Apify, about $1.50 a full pull |
| Pull one avatar's feed | `pull <dir> --avatar <avatar file> [--key-name APIFY_TOKEN]` | Apify, not yet measured |
| One row shape, floor applied | `rows <dir>` | free |
| Download every cover | `fetch <dir>` | free |
| Measure (text, faces, colour) | `measure <dir>` | free, on this Mac (macOS Vision) |
| Contact sheets for the eye read | `sheets <dir>` | free |
| Index as swipes + sums | `index <dir> runs/asset-index/swipes/covers` | free |
| Bring in a pull made elsewhere | `import <pull dir> runs/asset-index/swipes/covers --avatar <avatar file or name>` | free |
| Fill the move on rows that lack it | `moves runs/asset-index/swipes/covers` | free, no model call |
| Find swipes | `find runs/asset-index/swipes/covers --avatar <name> --move wrong-scale` | free |

## The avatar file

One small JSON file per avatar (shape: `avatar.example.json`). The caller keeps it where the avatar belongs; nothing
in this folder names a brand.

| Field | What it is |
|---|---|
| `avatar` | The name every indexed cover carries: lower-case letters, digits, dashes. Any spelling is read as that name (`Home Baker`, `home_baker` → `home-baker`); it must match the name the briefs use |
| `who` | One line: who they are |
| `platforms` | Where to pull: `instagram` (default), `tiktok`, `youtube-shorts` |
| `hashtags`, `accounts`, `topics` | What their feed carries. Hashtags and accounts are pulled on Instagram and TikTok; topics are searched on TikTok and YouTube Shorts |
| `on_topic` | Optional words. When set, a row is kept only if its caption or carrying hashtag has one of them |
| `floor` | Optional, per platform, e.g. `{"instagram": {"likes": 5000}}`. Default: `AVATAR_FLOOR` in `covers.py` |
| `max_age_days` | Optional. Default: no age limit |
| `per_source` | Optional. Results asked per hashtag, account or topic. Default 40 |

`pull --avatar` asks only for what the file lists and keeps the file as `<dir>/avatar.json`; `rows` and `index` read
it there. Run `rows`, `fetch`, `measure`, `sheets`, `index` after it as for a discovery pull.

## Import

`import` reads a folder holding a kept list (`keep.json`, else `rows.json`, or the file named with `--rows`) and
`covers/<post code or id>.jpg`. The list is either the Instagram hashtag scraper's own rows (`shortCode`,
`likesCount`, `videoPlayCount`, `timestamp`, `inputUrl`, `ownerUsername`) or this tool's rows. `measure.json` and
`breakdown.json` beside it, keyed by post code or id, are carried. A row with no picture is left out and counted.
Nothing in the pull folder is changed; rows already in the index stay, eye reads included; running it twice gives
the same index.
`--pulled YYYY-MM-DD` sets the pull date (default: the list file's date).

## The move

Each row carries `move`: what the cover does, in a few words, so a cover step copies the move and not the picture.
The vocabulary is `MOVES` in `covers.py`:

| `move` | Meaning |
|---|---|
| `impossible-object` | a thing that cannot exist |
| `impossible-scene` | a scene that cannot exist |
| `wrong-scale` | a thing at the wrong scale |
| `absurd-subject` | an absurd subject, shot straight |
| `face-at-limit` | a face pushed to its limit |
| `line-shown-literally` | the words name a thing the picture shows past real |
| `before-after` | before and after side by side |
| `pointed-at` | a circle or arrow on the target |
| `price-as-hook` | the price is the hook |
| `thing-to-lens` | a thing pushed at the lens |
| `one-odd-thing` | one odd thing in a normal frame |
| `as-shot` | no move: the frame as shot |
| `unrated` | the breakdown does not say; waits for an eye read |

- `index` and `import` write the move on every row; `moves <out>` fills it on rows indexed before the field existed.
- The move is read from the breakdown's own fields (`derive_move`): the surreal level, the expression and frame, the
  marks, and the words in `shows`. No model is called. `move_why` holds the words it was read from; `move_also` lists
  other moves the same cover makes; `move_by` is `breakdown` or `eye`.
- A cover with words on it and nothing else said stays `unrated`: whether its line is shown literally needs an eye read.
- An eye read wins and is never overwritten, also when `index` or `import` brings its row again: write `move` in the
  cover's `breakdown.json` entry before `index`, or `moves <out> --set <id>=<move> [<id>=<move> ...]`, or
  `moves <out> --from moves.json` (`{"<id>": "<move>"}`). A `move` in the pull's own `breakdown.json` is the newer eye
  read and replaces the old one. `moves <out> --redo` re-reads rule-made moves only.
- What the rules read: `impossible-object` needs surreal level 2 or 3, a photographed frame (not `graphic`,
  `text-only`, `screen`) and words for a thing that cannot exist (`made of`, `melting`, `with legs`, `shaped like`, …).
  `face-at-limit` needs a scream, wide eyes, a gaping mouth or a dropped jaw, or a shocked face filling a close frame;
  a plain open mouth counts only on a shocked or intense face in a close face frame. `thing-to-lens` needs a thing
  pushed, thrust or shoved at the lens, or held to the camera in an extreme close-up; holding a thing up is not it.
- `face-at-limit` and `thing-to-lens` read the picture only: a part of `shows` that describes the cover's words
  (quoted text, caption, headline, box, logo, …) is not read, so a cover whose text says "Screaming deals" is not a
  face at its limit. `line-shown-literally` needs a picture past real (surreal level 2 or 3) whose words name
  something it shows; a caption naming what a real frame holds up ("The humble fig's secret" over a hand holding a
  fig) is a label, not the move.

## Find: how another tool calls it

Command: `python3 components/asset-index/swipes/covers.py find <index dir> [options] --json`

| Option | Effect |
|---|---|
| `--avatar <name or avatar file>` | Only covers that avatar sees |
| `--move <move>` | A cover's main move or one it also makes; `unrated` lists the ones waiting for an eye read |
| `--rank likes` or `--rank views` | Order. Default: likes with an avatar, else views (likes where a platform gives none) |
| `--limit N` | The first N |
| `--platform ig` (`tt`, `yt`), `--frame`, `--text_style`, `--look`, `--grade`, `--absurd`, `--text none`, `--min-views N` | As before |

`--json` prints `{"scope", "avatar", "note", "covers"}`. `scope` is `avatar`, `general` (no avatar asked) or
`general-fallback`: the avatar has no covers in the index at all, so `covers` are the discovery surfaces' covers and
`note` says so. When the avatar has covers but none pass the other filters, `scope` stays `avatar`, `covers` is empty
and `note` says how many it has: a caller holds rather than follow a discovery cover. Each cover is its full index row; the picture is
`<index dir>/<frame_file>`. Without `--json` it prints one line per cover (id, platform, views, likes, posted, URL,
frame, picture, move, avatar) and the note on stderr.

From Python, load `covers.py` by path and call
`find_covers(out, avatar=None, move=None, platform=None, rank=None, limit=None, min_views=None, text=None, frame=..., ...)`;
it returns the same dict. A bad avatar name or a missing avatar file raises `AvatarError` (a `ValueError`); only the
command line stops on it.

## Rules

- **Discovery pulls are discovery surfaces only.** Instagram Explore (US, Canada, UK locales), TikTok Explore and
  For You, YouTube Trending, YouTube Shorts (most viewed in the last 14 days: YouTube has no public Shorts explore
  feed). Nothing is searched by brand.
- **An avatar pull is that avatar's feed only**: the hashtags, accounts and topics in its file. Every row carries
  `avatar` and `via` (the hashtag, account or topic that carried it). A discovery row has `avatar: null`.
- **One post is one row.** A post on a discovery surface that an avatar also sees keeps its discovery row and lists
  the avatar in `avatar_also`.
- **Viral is a number.** A discovery row is kept only over the floor in `FLOOR` (Instagram 10k likes; TikTok 500k
  views; YouTube 100k views; Shorts 250k views) and under 21 days old. An avatar row is kept over `AVATAR_FLOOR`
  (Instagram 5k likes; TikTok and Shorts as `FLOOR`) or the avatar file's own `floor`, at any age unless the file
  sets `max_age_days`. Every row keeps its views or likes, post date and URL.
- **The eye read uses one vocabulary** (`BREAKDOWN` in `covers.py`): frame, people, expression, shot, zoom, text
  style, words, case, placement, grade, marks, how raw or designed, the surreal level (0 as shot, 1 one odd
  thing, 2 impossible scale or absurd subject, 3 impossible scene) and the move. It is filled by eye from the contact
  sheets into `breakdown.json` (no model judge). Measured fields (text read, faces, saturation, colourfulness) come
  from `measure`.
- **Ids are the post's own id** (`ig-…`, `tt-…`, `yt-…`, `ys-…`), so a later pull never renumbers a row.
- **A pull replaces only the rows it brings again.** A discovery pull replaces the discovery rows of the sources its
  indexed rows carry, so `pull --only <one source>` then `index` keeps every other source's rows and their eye reads.
  A source that kept no indexed row (an empty or capped run, covers that never downloaded, a `raw/<source>.json` left
  in a reused folder) replaces nothing. A discovery row with no `source` goes with any discovery pull. A
  discovery row a pull drops stays when an avatar also sees it, as that avatar's row. An avatar's covers are only added to or updated by
  its pulls and imports: a second, narrower pull keeps the rest. Every other row in `covers.json` stays.
- **Keys by name only** (`components/keys/loader.py`). A capped account's refusal is printed, never the key.
- **Facts, not verdicts.** `patterns.json` holds counts and shares per platform for the discovery rows only;
  `components/video-edit/machine/cover_styles.json` quotes it. `avatars.json` holds one record per avatar.

## Switches

`switches.json` in this folder; row COVER-SWIPES in `team/rollbacks.md`.

| Switch | Off means |
|---|---|
| `avatar.on` | `pull --avatar` and `import` refuse; `find` ignores `--avatar` and lists discovery covers only. Avatar rows stay on disk |
| `move.on` | `moves` refuses; `index` writes no move; `find` ignores `--move` |
| `merge-keeps.on` | `index` and `import` replace the whole group they bring (the avatar, or the discovery rows): an avatar's covers a new pull lacks go, eye reads on rows brought again go, a cover an avatar also sees goes with the next discovery pull |
| `avatar-slug.on` | An avatar name must already be lower-case letters, digits and dashes; a bad name or missing file stops the caller (`SystemExit`) |
| `avatar-scope.on` | `find --avatar` falls back to discovery covers also when the avatar's covers all fail the other filters |
| `move-rules.on` | No `impossible-object` from the rules; any open mouth or shocked face is `face-at-limit`; anything held or pointed to the camera is `thing-to-lens` |
| `merge-by-pull.on` | A discovery pull replaces every discovery row (unless an avatar also sees it): a narrower pull drops the other sources' covers and their eye reads |
| `move-picture.on` | `face-at-limit` and `thing-to-lens` also match the cover's own words; `line-shown-literally` is read from any word the text shares with the picture, a caption naming what is held up included |

One machine only: `COVER_SWIPES_OFF=all`, or a comma list of switch names, in its environment.

## Where it lands

`runs/asset-index/swipes/covers/`: `covers.json` (one row per cover: platform, surface, URL, views, likes, posted,
age, `avatar`, `via`, `move`, measure, breakdown, `frame_file`), `patterns.json` (per-platform sums, discovery rows),
`avatars.json` (per avatar: who, what its feed carries, covers, median likes and views, moves), `covers/<id>.jpg`
(720 px). First discovery pull: 2026-11-11, 167 covers (Instagram 67, TikTok 47, YouTube 42, Shorts 11).

## Check

`/usr/bin/python3 components/asset-index/swipes/test_covers.py` (no network, no key; fixture in
`fixtures/avatar-pull/`). Not yet run against the live actors through this tool: the avatar sources. The Instagram
hashtag source's row shape is the one `import` and the fixture use; the account, TikTok and Shorts avatar sources are
covered by fakes only.
