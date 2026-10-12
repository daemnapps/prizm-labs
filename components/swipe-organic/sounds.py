#!/usr/bin/env python3
"""Trending sounds — the pool of TikTok sounds that are trending RIGHT NOW.

    python3 sounds.py pull  [--dry-run] [--country US] [--max 20] [--days 14]
    python3 sounds.py audio [--dry-run] [--fallback]   # save the audio to the Drive
    python3 sounds.py tag                              # mood / energy / kind, by Haiku
    python3 sounds.py status

the owner, 2026-09-23: "I wouldn't want to use existing meme sounds, I would only
really want to use sounds that are more recent." Organic posts only — he is
not running TikTok ads, so commercial licensing is not a filter here.

Where the sounds come from: TikTok's own trending-sounds chart, read through
the Apify actor burbn/tiktok-trending-sounds (the public Creative Center page
went behind a TikTok One login in September 2026; this actor still reads it —
525 of 525 runs succeeded in the 30 days to 2026-09-23). Two lanes per pull:

- `surging` — the sounds climbing fastest this week
- `new`     — the sounds new to the Top 100 this week

Both are recent by construction. On top of that a row ages out when the chart
has not shown it for --days days, and the tag step marks the old meme sounds
so the page never shows them.

The pool is records/sounds/pool.json, one row per sound, keyed `snd-<tiktok id>`.
His keep/skip lives on the row. The kept rows are written out as
records/sounds/index.json in the same row shape as the video-production banks,
which is the hand-off: a brief names a sound by its id.

Audio lives on the Drive (the organic swipe home's sounds/, via swipe_home),
never in git. Money: the pull (~$__) and the audio fallback are the only
spends. Nothing is scheduled (the owner, 2026-09-23: no automated check) — a pull
runs when he presses the button on the page, which shows the cost first.
"""
import argparse, json, re, subprocess, sys, tempfile, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import desklib as D

ROOT = D.HERE / "records" / "sounds"
POOL = ROOT / "pool.json"
PULLS = ROOT / "pulls.jsonl"
INDEX = ROOT / "index.json"
RAW = ROOT / "raw"
AGED = ROOT / "aged.jsonl"
SENT = ROOT / "prompts-as-sent"
for _r in Path(__file__).resolve().parents:   # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
DRIVE = swipe_home.path("organic", "sounds")
DRIVE_LABEL = swipe_home.label("organic", "sounds")

# The source (switched 2026-09-23): TikTok's Explore page, read by
# automation-lab/tiktok-trends-scraper. The Creative Center song chart that
# burbn/tiktok-trending-sounds and datapeak/tiktok-creative-center read came
# back EMPTY on 2026-09-23 (the actor logs "Request failed" and still reports
# SUCCEEDED), so a run "succeeding" proves nothing about the chart.
CHART = "automation-lab~tiktok-trends-scraper"
AUDIO_FALLBACK = "clockworks~tiktok-sound-scraper"
# Prices read 2026-09-23 from the Apify store (the main account is BRONZE,
# the spare is FREE). Used only to state a cost before anything runs.
PRICE = {"BRONZE": {"start": 0.05, "result": 0.015, "fallback": 0.004},
         "FREE": {"start": 0.05, "result": 0.015, "fallback": 0.005}}
LANES = {"explore": {"trendType": "sound"}}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128 Safari/537.36"}


# ------------------------------------------------------------------ the store
def load():
    return json.loads(POOL.read_text()) if POOL.exists() else {"rows": {}}


def save(pool):
    ROOT.mkdir(parents=True, exist_ok=True)
    POOL.write_text(json.dumps(pool, indent=1, ensure_ascii=False))
    write_index(pool)


def first(d, *keys):
    for k in keys:
        v = d.get(k) if isinstance(d, dict) else None
        if v not in (None, "", [], {}):
            return v
    return None


def normalise(raw, lane, country):
    """One chart row in, one pool row out. The actor's field names are read
    with fallbacks because its output schema is not published; the raw row is
    kept in records/sounds/raw/ so a missed field can be recovered."""
    tid = str(first(raw, "soundId", "clip_id", "song_id", "music_id", "id", "musicId") or "")
    if not tid:
        return None
    audio = first(raw, "soundPlayUrl", "music_url", "play_url", "playUrl", "audio_url", "musicUrl", "url_music")
    link = first(raw, "link", "tiktok_url", "sound_url", "music_page") or \
        f"https://www.tiktok.com/music/-{tid}"
    trend = first(raw, "trend", "trend_data", "trends") or []
    series = []
    for t in trend if isinstance(trend, list) else []:
        if isinstance(t, dict) and "value" in t:
            series.append([t.get("time"), t.get("value")])
    return {
        "id": f"snd-{tid}", "tiktok_id": tid,
        "title": first(raw, "name", "title", "song_name", "music_name") or "untitled",
        "artist": first(raw, "soundAuthor", "author", "artist", "creator", "author_name") or "",
        "made": made(tid),
        "example": first(raw, "linkedVideoUrl"),
        "seconds": first(raw, "duration", "duration_seconds"),
        "cover": first(raw, "soundCover", "cover", "cover_url", "cover_large", "coverUrl"),
        "url": link, "audio_url": audio,
        "rank": first(raw, "rank", "position"),
        "rank_change": first(raw, "rank_diff", "rank_change"),
        "rank_change_type": first(raw, "rank_diff_type"),
        "trend": series,
        "usage": first(raw, "video_count", "videoCount", "user_count", "usage_count"),
        "commercial": first(raw, "if_cml", "commercial_music", "is_commercial"),
        "lane": lane, "country": country,
    }


def made(tid):
    """When TikTok created the sound: a TikTok id carries its own timestamp in
    its top 32 bits. An old song resurfacing is fine; this just shows it."""
    try:
        return datetime.fromtimestamp(int(tid) >> 32, timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def growth(row):
    """How hard it is climbing: the last value of TikTok's own 0–1 popularity
    series against the value a week before it, in percent. None if the chart
    gave no series."""
    s = [v for _, v in row.get("trend") or [] if isinstance(v, (int, float))]
    if len(s) < 2 or not s[max(0, len(s) - 8)]:
        return None
    return round((s[-1] / s[max(0, len(s) - 8)] - 1) * 100)


def merge(pool, fresh, at):
    new = 0
    for r in fresh:
        cur = pool["rows"].get(r["id"])
        obs = {"at": at, "lane": r["lane"], "rank": r["rank"], "rank_change": r["rank_change"],
               "usage": r["usage"], "value": (r["trend"][-1][1] if r["trend"] else None)}
        if cur is None:
            new += 1
            r.update(first_seen=at, last_seen=at, lanes=[r["lane"]], seen=[obs],
                     receipt=f"TikTok Explore, sounds in use ({r['country']}) via Apify {CHART}, {at[:10]}",
                     pick=None, tags=None, bpm=None, file=None)
            pool["rows"][r["id"]] = r
        else:
            for k in ("title", "artist", "seconds", "cover", "url", "trend", "usage", "rank",
                      "rank_change", "rank_change_type", "commercial"):
                if r.get(k) not in (None, "", []):
                    cur[k] = r[k]
            cur["audio_url"] = r.get("audio_url") or cur.get("audio_url")
            cur["last_seen"] = at
            cur["lanes"] = sorted(set(cur.get("lanes", [])) | {r["lane"]})
            cur["seen"] = (cur.get("seen") or [])[-29:] + [obs]
    return new


def age_out(pool, days, at):
    """Recent only. A sound the chart has not shown in `days` days leaves the
    pool — unless he kept it, in which case it stays, marked off-chart."""
    cut = D.iso(at) - timedelta(days=days)
    gone = []
    for k, r in list(pool["rows"].items()):
        seen = D.iso(r.get("last_seen"))
        if seen and seen < cut:
            if r.get("pick") == "keep":
                r["off_chart_since"] = r.get("off_chart_since") or r["last_seen"]
                continue
            gone.append(pool["rows"].pop(k))
    if gone:
        with AGED.open("a") as f:
            for r in gone:
                f.write(json.dumps({"at": at, "id": r["id"], "title": r["title"],
                                    "artist": r["artist"], "last_seen": r["last_seen"]},
                                   ensure_ascii=False) + "\n")
    return len(gone)


# ------------------------------------------------------------------ money
def tier():
    try:
        import apify as A
        with urllib.request.urlopen(f"{A.API}/users/me?token={A.token()}", timeout=20) as r:
            return (json.load(r)["data"].get("plan") or {}).get("tier") or "FREE"
    except Exception:
        return "FREE"


def pull_cost(lanes, per_lane, t):
    p = PRICE.get(t, PRICE["FREE"])
    return round(len(lanes) * (p["start"] + per_lane * p["result"]), 2)


# ------------------------------------------------------------------ pull
def pull(a):
    lanes = list(LANES)
    t = tier()
    cost = pull_cost(lanes, a.max, t)
    payloads = {ln: {"countryCode": a.country, "period": 7, "maxResults": a.max, **LANES[ln]}
                for ln in lanes}
    if a.dry_run:
        print(f"would run {CHART} {len(lanes)} times ({a.country}, last 7 days), "
              f"up to {a.max} sounds each — at most ${cost} on the {t} tier")
        for ln, p in payloads.items():
            print(f"  {ln}: {json.dumps(p)}")
        return
    import apify as A
    at = D.now()
    fresh, errors = [], []
    RAW.mkdir(parents=True, exist_ok=True)
    for ln, p in payloads.items():
        try:
            items = A.run(CHART, p, timeout=600)
        except Exception as e:
            errors.append(f"{ln}: {str(e)[:120]}")
            continue
        (RAW / f"{at[:10]}-{ln}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
        fresh += [r for r in (normalise(i, ln, a.country) for i in items) if r]
    pool = load()
    new = merge(pool, fresh, at)
    gone = age_out(pool, a.days, at)
    save(pool)
    rec = {"at": at, "lanes": lanes, "country": a.country, "got": len(fresh), "new": new,
           "aged_out": gone, "errors": errors, "est_cost": cost}
    with PULLS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"sounds: got {len(fresh)} · new {new} · aged out {gone}"
          + (f" · errors {errors}" if errors else ""))


# ------------------------------------------------------------------ audio
def audio_path(row):
    return DRIVE / f"{row['id']}.mp3"


# The page plays from a local copy: My Feeds runs under launchd, and macOS
# will not let a background job read the Drive (found 2026-09-23). The Drive
# copy stays the file of record; the local one is gitignored, never in git.
LOCAL = ROOT / "audio"


def local_path(row):
    return LOCAL / f"{row['id']}.mp3"


def download(url, dest):
    try:
        import apify as A
        url = A.sign(url)
    except Exception:
        pass
    # creators' own audio sits on TikTok's web CDN, which answers 403 without
    # a tiktok.com referer (found on the first live pull, 2026-09-23)
    req = urllib.request.Request(url, headers={**UA, "Referer": "https://www.tiktok.com/"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 5000:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(data)
    # whatever TikTok served (m4a, mp3), the pool file is an mp3
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-vn",
                        "-codec:a", "libmp3lame", "-q:a", "2", str(dest)], capture_output=True)
    tmp.unlink(missing_ok=True)
    return r.returncode == 0 and dest.exists()


def fallback_urls(rows):
    """The chart gives a direct audio link only for some sounds. For the rest,
    one TikTok video that uses the sound carries the sound's play link."""
    import apify as A
    items = A.run(AUDIO_FALLBACK, {"musics": [r["url"] for r in rows], "resultsPerPage": 1,
                                   "shouldDownloadVideos": False}, timeout=900)
    out = {}
    for it in items:
        m = it.get("musicMeta") or {}
        mid, play = str(m.get("musicId") or ""), m.get("playUrl")
        if mid and play:
            out[f"snd-{mid}"] = play
    return out


def audio(a):
    pool = load()
    rows = [r for r in pool["rows"].values()
            if not (r.get("tags") or {}).get("classic_meme") and not (r.get("file") and audio_path(r).exists())]
    direct = [r for r in rows if r.get("audio_url")]
    missing = [r for r in rows if not r.get("audio_url")]
    t = tier()
    fb_cost = round(len(missing) * PRICE.get(t, PRICE["FREE"])["fallback"] + 0.01, 2) if missing else 0
    if a.dry_run:
        print(f"would save {len(direct)} audio files from TikTok's CDN (free) to the Drive: {DRIVE_LABEL}/")
        if missing:
            print(f"{len(missing)} have no audio link on the chart — --fallback looks them up "
                  f"via {AUDIO_FALLBACK}, about ${fb_cost}")
        return                                    # a dry run writes nothing (SI-159 (organic pool honest))
    for r in pool["rows"].values():
        if r.get("file") and audio_path(r).exists() and not local_path(r).exists():
            LOCAL.mkdir(parents=True, exist_ok=True)
            local_path(r).write_bytes(audio_path(r).read_bytes())
    if not DRIVE.parent.exists():
        sys.exit(f"the Drive folder is not mounted: {DRIVE.parent}")
    if a.fallback and missing:
        found = fallback_urls(missing)
        for r in missing:
            if found.get(r["id"]):
                r["audio_url"] = found[r["id"]]
                direct.append(r)
    saved = 0
    for r in direct:
        dest = audio_path(r)
        try:
            if download(r["audio_url"], dest):
                r["file"] = f"{DRIVE_LABEL}/{dest.name}"
                r.pop("audio_error", None)
                LOCAL.mkdir(parents=True, exist_ok=True)
                local_path(r).write_bytes(dest.read_bytes())
                r["bpm"] = r.get("bpm") or bpm(dest)
                r["seconds"] = r.get("seconds") or seconds(dest)
                saved += 1
        except Exception as e:
            r["audio_error"] = str(e)[:120]
    save(pool)
    print(f"sounds audio: saved {saved} of {len(direct)} · {len(missing)} with no link")


def seconds(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 1)
    except ValueError:
        return None


def bpm(path, sr=11025, hop=110):
    """A rough tempo, from the file itself: ffmpeg decodes 40 seconds to mono,
    an energy envelope is taken every 10 ms, and the strongest repeat between
    70 and 180 BPM wins. Good enough to sort by feel; marked approximate."""
    import array
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", "40", "-i", str(path), "-ac", "1",
                        "-ar", str(sr), "-f", "s16le", "-"], capture_output=True)
    pcm = array.array("h", r.stdout)
    if len(pcm) < sr * 5:
        return None
    env = [sum(abs(x) for x in pcm[i:i + hop]) for i in range(0, len(pcm) - hop, hop)]
    flux = [max(0, env[i] - env[i - 1]) for i in range(1, len(env))]
    m = sum(flux) / len(flux)
    flux = [f - m for f in flux]
    fps = sr / hop
    best, best_lag = 0, None
    for lag in range(int(fps * 60 / 180), int(fps * 60 / 70) + 1):
        s = sum(flux[i] * flux[i + lag] for i in range(len(flux) - lag))
        if s > best:
            best, best_lag = s, lag
    return round(60 * fps / best_lag) if best_lag else None


# ------------------------------------------------------------------ tag
def tag(a):
    pool = load()
    todo = [r for r in pool["rows"].values() if not r.get("tags")]
    if not todo:
        print("sounds tag: nothing new")
        return
    for i in range(0, len(todo), 25):
        batch = todo[i:i + 25]
        listing = "\n".join(f"- id {r['id']}: \"{r['title']}\" by {r['artist'] or 'unknown'}"
                            f" ({r.get('seconds') or '?'}s)" for r in batch)
        p = D.prompt("sounds-tag-v1.md", sounds=listing)
        SENT.mkdir(parents=True, exist_ok=True)
        (SENT / "tag-latest.md").write_text(p)
        out = D.json_from(D.ask_model(p, model="haiku"))
        for t in out if isinstance(out, list) else []:
            r = pool["rows"].get(t.get("id"))
            if r:
                r["tags"] = {k: t.get(k) for k in
                             ("kind", "classic_meme", "mood", "energy", "category", "use", "why")}
    save(pool)
    print(f"sounds tag: tagged {len(todo)}")


# ------------------------------------------------------------------ the hand-off
def verdict(sid, pick):
    pool = load()
    r = pool["rows"].get(sid)
    if not r or pick not in ("keep", "skip", None):
        return False
    r["pick"], r["pick_at"] = pick, D.now()
    save(pool)
    return True


def bank_row(r):
    """A kept sound, in the video-production bank row shape
    ({id, tags, energy, tempo_bpm, mood, seconds, file, source, licence,
    status}) plus what only a trending sound has."""
    t = r.get("tags") or {}
    return {
        "id": r["id"], "tags": [x for x in (t.get("mood"), t.get("energy"), t.get("category"),
                                           t.get("kind"), "trending") if x],
        "energy": t.get("energy"), "tempo_bpm": r.get("bpm"), "mood": t.get("mood"),
        "seconds": r.get("seconds"), "file": r.get("file") or "",
        "source": f"tiktok trending sound — {r['title']} · {r['artist']}".strip(" ·"),
        "licence": "organic posts only — added from TikTok's sound library at post time; "
                   "not cleared for paid ads",
        "status": "made" if r.get("file") else "to make",
        "title": r["title"], "artist": r["artist"], "tiktok_url": r["url"],
        "first_seen": r.get("first_seen"), "last_seen": r.get("last_seen"),
        "off_chart_since": r.get("off_chart_since"), "use": t.get("use"),
    }


def write_index(pool):
    kept = sorted((r for r in pool["rows"].values() if r.get("pick") == "keep"),
                  key=lambda r: r.get("pick_at") or "", reverse=True)
    INDEX.write_text(json.dumps({
        "_readme": [
            "THE TRENDING-SOUNDS SHORTLIST (swipe-organic, 2026-09-23). the owner's kept sounds from "
            "records/sounds/pool.json, in the same row shape as tools/video-production/banks/*/index.json. "
            "A brief names one by id (`sound: \"snd-<tiktok id>\"`); the edit reads `file` from here.",
            "Organic posts only. `status: made` means the audio is on the Drive at `file`. "
            "A row whose sound has left the chart carries `off_chart_since` — it is getting old."],
        "bank": "trending-sounds", "drive_root": DRIVE_LABEL,
        "rows": [bank_row(r) for r in kept]}, indent=1, ensure_ascii=False))


# ------------------------------------------------------------------ the page's view
def rows_for_page(days=14):
    pool = load()
    out = []
    for r in pool["rows"].values():
        t = r.get("tags") or {}
        if t.get("classic_meme"):
            continue
        first_seen = D.iso(r.get("first_seen"))
        out.append({**{k: r.get(k) for k in ("id", "title", "artist", "seconds", "url", "rank",
                                              "rank_change", "usage", "lanes", "first_seen",
                                              "last_seen", "pick", "bpm", "file", "off_chart_since",
                                              "receipt", "cover", "made", "example")},
                    "tags": t, "growth": growth(r),
                    "days_on": max(0, (datetime.now(timezone.utc) - first_seen).days) if first_seen else None,
                    "playable": local_path(r).exists(),
                    "stream": r.get("audio_url")})
    out.sort(key=lambda r: (r.get("first_seen") or ""), reverse=True)
    pulls = [json.loads(l) for l in PULLS.read_text().splitlines()][-10:] if PULLS.exists() else []
    tag_prompt = (D.PROMPTS / "sounds-tag-v1.md").read_text()
    sent = (SENT / "tag-latest.md").read_text() if (SENT / "tag-latest.md").exists() else None
    return {"rows": out, "pulls": pulls, "prompt": tag_prompt, "prompt_sent": sent,
            "kept": sum(1 for r in out if r["pick"] == "keep")}


def status(a):
    pool = load()
    rs = list(pool["rows"].values())
    print(f"{len(rs)} sounds in the pool · {sum(1 for r in rs if r.get('pick') == 'keep')} kept · "
          f"{sum(1 for r in rs if r.get('file'))} with audio on the Drive")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pull", "audio", "tag", "status"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--country", default="US")
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--fallback", action="store_true",
                    help="look up audio links the chart did not give (costs a little)")
    a = ap.parse_args()
    {"pull": pull, "audio": audio, "tag": tag, "status": status}[a.cmd](a)


if __name__ == "__main__":
    main()
