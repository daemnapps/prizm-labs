# Trending Sounds — the recent TikTok sounds pool

Built 2026-09-23 for the owner. Markdown mirror of the artifact
"Trending Sounds" (link in `context/artifacts.md`).

> "I wouldn't want to use existing meme sounds, I would only really want to
> use sounds that are more recent." — the owner, 2026-09-23

Organic posts only. He is not running TikTok ads, so paid-ad licensing is not
a filter. The sounds make the content feel culturally current, not AI-made.

## Where it lives

- **The page:** My Feeds → **Trending sounds** button (`/sounds` on port 8820).
  It lists every sound with a player, its chart position, how fast it is
  climbing, mood/energy/genre, tempo, and **Keep / Skip** buttons.
- **The pull:** `sounds.py`, run by the **Pull this week's sounds** button on the
  page. The button shows the cost and asks for a second click to confirm.
  **Nothing is scheduled** (the owner, 2026-09-23: no automated check).
- **The data:** `records/sounds/pool.json` (every sound),
  `records/sounds/index.json` (his kept sounds = the shortlist),
  `records/sounds/pulls.jsonl` (every pull), `records/sounds/raw/` (the chart as it came in).
- **The audio:** on the Drive at `Shared Assets/lab/swipe-organic/sounds/<id>.mp3`.
  Never in git.

## How one pull runs

1. **Source (switched 2026-09-23):** the sounds on TikTok's Explore page right now (US),
   read by the Apify actor `automation-lab/tiktok-trends-scraper`. Each sound also shows
   **when TikTok created it**, so a brand-new sound and an old song resurfacing are easy to tell apart.
   *Why switched:* TikTok's Creative Center song chart now returns nothing to every
   scraper tried (`burbn/tiktok-trending-sounds`, `datapeak/tiktok-creative-center`). Those
   runs still report "succeeded", with 0 sounds.
2. **Tag:** Claude Haiku labels each sound: kind, mood, energy, genre, what posts
   it's being used on, and whether it's an old meme sound. The prompt is below,
   word for word, and on the page.
3. **Audio:** saved to the Drive from TikTok's own link (free). The tempo is
   measured from the file.
4. **the owner:** plays them on the page and presses Keep or Skip.
5. **Shortlist:** every kept sound goes into `index.json`, the list production uses.

## Recent only: the rules

- Both lists are this week's movers by definition.
- A sound the chart hasn't shown for **14 days** leaves the pool (logged in `aged.jsonl`).
- A sound he **kept** stays, marked "off the chart".
- Old meme sounds (vine boom, bruh, sad violin, metal pipe…) are flagged by the
  tagger and **never shown**.

## Cost

| What | Cost |
|---|---|
| One pull (30 sounds) | **≈ $__** ($__ start + $__ a sound) |
| Saving the audio | free (TikTok's own link) |
| Looking up audio the chart didn't link (optional, `--fallback`) | ≈ $__ per sound |
| Tagging | Claude on this Mac, no extra bill |

**Blocked right now:** the main Apify account is at **$__ of its $__**
monthly limit and the spare is at **$__ of $__**. The pull button stays locked
until the limit is raised (in Apify's billing settings, the owner's account) or the
cycle resets (main: Oct 14, 7am the owner time; spare: Oct 10, 7am). No pull has run yet. The first one waits for the owner's OK.

**Nightly Apify jobs are off** (the owner, 2026-09-23): the My Feeds nightly pull
(`com.daemn.feeds-daily`, 1:00am) and the research gatherer's nightly pull
(`com.daemn.research-nightly`, 2:30am) are disabled. Every Apify pull is now a
button press.

## The tagging prompt: `prompts/sounds-tag-v1.md`, verbatim

```
# Sounds — tag v1

You are tagging TikTok sounds that are trending RIGHT NOW, so an editor can
pick one for an organic post by feel. These are organic posts, not ads.

The rule from the owner (2026-09-23): only sounds that are recent. Classic meme
sounds — vine boom, bruh, oh no no no, sad violin, metal pipe, emotional
damage, the Wii theme, Curb Your Enthusiasm, "directed by Robert B. Weide",
Among Us, any sound that has been a meme for a year or more — are OUT, even
if they show up on a chart. Mark them `classic_meme: true`.

For each sound below, give back:

- `kind`: `song` (a released track), `original` (someone's own audio: a voice,
  a skit line, a remix a creator made), or `meme` (a sound that is used as a
  joke punchline rather than a bed)
- `classic_meme`: true only for the old, worn-out meme sounds described above
- `mood`: ONE word — pick from: hype, happy, warm, calm, sad, moody, tense,
  funny, romantic, nostalgic, confident, eerie
- `energy`: `low`, `mid` or `high`
- `category`: ONE of: pop, hip-hop, r&b, edm, latin, country, rock, afro,
  k-pop, lo-fi, cinematic, speech, remix, other
- `use`: one short line (under 14 words) — what kind of post this sound gets
  put under on TikTok right now
- `why`: one short line — what you based the tags on (the title, the artist,
  what you know of the track). If you do not know the sound, say so and tag
  from the title only; do not invent facts about it.

Answer with JSON only, a list in the same order as the input:
`[{"id": "...", "kind": "...", "classic_meme": false, "mood": "...", "energy": "...", "category": "...", "use": "...", "why": "..."}]`

The sounds:

{sounds}
```

## Hand-off to production: a proposal only, video-production not edited

Kept sounds are written in the **same row shape as the music and SFX banks**
(`tools/video-production/banks/*/index.json`, ELEMENTS.md §3):

```json
{
 "id": "snd-7550000000000000001",
 "tags": ["confident", "high", "pop", "song", "trending"],
 "energy": "high", "tempo_bpm": 120, "mood": "confident", "seconds": 30,
 "file": "Shared Assets/lab/swipe-organic/sounds/snd-7550000000000000001.mp3",
 "source": "tiktok trending sound — <title> · <artist>",
 "licence": "organic posts only — added from TikTok's sound library at post time; not cleared for paid ads",
 "status": "made",
 "title": "…", "artist": "…", "tiktok_url": "…",
 "first_seen": "…", "last_seen": "…", "off_chart_since": null, "use": "…"
}
```

Proposed for the video-production session to adopt:

1. **Brief:** an organic brief may carry `sound: "snd-<id>"`. It names one row,
   the same way `music` and `sfx` name bank rows.
2. **Production:** `banks.py` gains a third bank, `trending-sounds`, whose index
   is `components/swipe-organic/records/sounds/index.json`. The same rules apply:
   only a `made` row with a `file` is picked, and a missing row stops the run
   and names the row.
3. **plan.json:** `plan.sound = {bank_id, file, tiktok_url}`. When present it
   replaces the music bed.
4. **Posting:** the `tiktok_url` goes on the post sheet, so whoever posts adds
   the sound from TikTok's own library in the app. The post then counts
   toward the trend.
5. **Staleness:** a row with `off_chart_since` older than 14 days gets a warning
   at the gate, not a stop.

## What was checked (2026-09-23)

- Dry run of the pull: 2 actor calls, ≤ $__. ✔
- Tempo reader on a 120 BPM click track read **120**. ✔
- Tagging prompt on three real titles: Espresso → pop / confident / high;
  Vine Boom → **flagged as an old meme, hidden**; an unknown creator
  original → tagged from its title and said so. ✔
- The page, served by My Feeds: sample rows showed with player and tags;
  Keep wrote the row into the shortlist with its tags and tempo. The sample
  data was removed afterwards. ✔
- The live My Feeds was restarted and serves `/sounds`. ✔

## Checked and set aside

- **TikTok Creative Center** trending-songs page: now redirects to a
  "TikTok One" login (confirmed 2026-09-23). The Apify actor still reads the
  chart: 525 of 525 runs succeeded in the 30 days before.
- **Higgsfield `tiktok_music_trending`:** lists only TikTok's licensed business
  music (the Commercial Music Library), not what's actually trending, and
  needs a connected TikTok account (none is). Not used.
- **Usage counts** ("how many videos use this sound"): the chart gives rank and
  a daily popularity curve, not a video count. The page shows growth from that
  curve. A video count would need a second paid lookup per sound. Not built.
- **Field names** from the chart actor aren't published. The reader tries the
  known names and keeps the raw chart in `records/sounds/raw/`, so the first
  real pull will confirm or correct them.

## First live pull — 2026-09-23 ✔
Cap raised $__ → $__ on the owner's word to test. 10 sounds pulled from Explore, tagged, all 10
saved to the Drive and playable on the page. Two fixes found on the way: creators' own audio
needs a tiktok.com referer to download; the page plays from a local, gitignored copy
(`records/sounds/audio/`) because macOS won't let the background My Feeds server read the Drive.
Test spend ≈ $__ across four sources.
