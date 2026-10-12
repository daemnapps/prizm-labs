#!/usr/bin/env python3
"""Read the angle off the frame, because the copy does not carry it.

    python3 scan_frames.py <lane> <source> [--limit N] [--force]
    python3 scan_frames.py own live

Grouping ads by their body copy says two creatives are the same thing. In our
own account the top copy block held one ad that took $__ and another that
took $__ — same paragraph, different picture, different hook burned into the
frame:

    "If you have brown spots on your legs right now"   $__
    "If you wore a cardigan"                           $__

Everything that separated them is in the content. So the angle is read off the
frame — the on-screen hook and what is actually shown — not off the copy.

Every creative in the corpus already has a frame: a poster we hold for swiped
video, or the advertiser's own image for ours. This sends that frame to Gemini
with `prompts/frame-scan-v1.md` and records what came back.

Results land in `frames.json` keyed by swipe_id, merged over the corpus on
every rebuild the same way judgements are. A frame already scanned is never
paid for twice unless --force.
"""
import argparse, base64, hashlib, json, os, re, sqlite3, sys, time
import urllib.parse, urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
DB = os.path.join(HERE, "swipe.db")
OUT = os.path.join(HERE, "frames.json")
PROMPT = os.path.join(HERE, "prompts", "frame-scan-v1.md")
# The lab root on the Drive, for OUR OWN media only; swipe media goes
# through swipe_home.resolve().
DRIVE = str(swipe_home.shared_assets() / "lab" / "damon")
CACHE = os.path.join(HERE, ".build", "thumbs")
BASE = "https://generativelanguage.googleapis.com"
MODEL = "gemini-3-flash-preview"


def key():
    # By NAME: the variable first, then the Keychain. Never a path to a key
    # file — every key moved into the Keychain on 2026-09-11 and ~/.gemini.env
    # is history.
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        import daemn_keys
        k = (daemn_keys.key("GEMINI_API_KEY") or "").strip()
    except Exception as e:
        sys.exit(f"No GEMINI_API_KEY: {e}")
    if not k:
        sys.exit("No GEMINI_API_KEY in the environment or the Keychain.")
    return k


def q(sql, args=()):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def frame_bytes(row):
    """The frame itself: the poster we hold, or the advertiser's hosted image.

    Remote frames go through the same on-disk cache the browser uses, so a
    scan and a look at the page never fetch the same picture twice.
    """
    f = row.get("file")
    if f:
        hit = swipe_home.resolve(f)       # swipe media by its stored path, first
        cands = [str(hit)] if hit else []
        cands += [os.path.join(base, f) for base in (DRIVE, str(swipe_home.root("paid")))]
        for c in cands:
            p = os.path.normpath(c)
            if p.endswith((".mp4", ".mov")):
                p = re.sub(r"\.(mp4|mov)$", "_poster.jpg", p)
            if os.path.isfile(p):
                return open(p, "rb").read()
    u = row.get("thumb")
    if not u or not u.startswith("http"):
        return None
    os.makedirs(CACHE, exist_ok=True)
    c = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest() + ".jpg")
    if not os.path.exists(c):
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": "Mozilla/5.0", "Referer": "https://www.facebook.com/"})
            open(c, "wb").write(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            return None
    return open(c, "rb").read()


def scan(img, prompt):
    body = json.dumps({
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg",
                             "data": base64.b64encode(img).decode()}}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }).encode()
    url = f"{BASE}/v1beta/models/{MODEL}:generateContent?key={key()}"
    for attempt in range(4):
        try:
            r = urllib.request.Request(url, data=body,
                                       headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=180) as resp:
                d = json.loads(resp.read())
            txt = d["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(txt)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(8 * (attempt + 1)); continue
            return {"error": f"HTTP {e.code}"}
        except Exception as e:
            return {"error": str(e)[:120]}
    return {"error": "gave up"}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("lane"); a.add_argument("source")
    a.add_argument("--limit", type=int, default=0)
    a.add_argument("--force", action="store_true")
    o = a.parse_args()

    prompt = open(PROMPT).read()
    have = json.load(open(OUT)) if os.path.exists(OUT) else {}
    rows = q("SELECT swipe_id, file, thumb, title FROM creatives "
             "WHERE lane=? AND source=? ORDER BY COALESCE(spend,0) DESC, ref DESC",
             (o.lane, o.source))
    todo = [r for r in rows if o.force or r["swipe_id"] not in have]
    if o.limit:
        todo = todo[:o.limit]
    print(f"{len(rows)} creatives · {len(todo)} to scan")

    done = miss = 0
    for i, r in enumerate(todo, 1):
        img = frame_bytes(r)
        if not img:
            miss += 1
            continue
        res = scan(img, prompt)
        res["scanned"] = time.strftime("%Y-%m-%d")
        have[r["swipe_id"]] = res
        done += 1
        hook = (res.get("hook") or "")[:58]
        print(f"  {i:>4}/{len(todo)}  {hook or '(no on-screen text)'}")
        if done % 10 == 0:
            json.dump(have, open(OUT, "w"), indent=1, sort_keys=True)
    json.dump(have, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"\n{done} scanned · {miss} had no frame · {len(have)} in the record")


if __name__ == "__main__":
    main()
