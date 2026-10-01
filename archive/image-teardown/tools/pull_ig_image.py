#!/usr/bin/env python3
"""Pull one image post from an Instagram handle, for the clone test.

    python3 pull_ig_image.py <handle> --out DIR [--limit 24]

Deliberately narrow: the full creator-ingest component builds a dossier with
transcripts and comments. This wants one still image and its permalink, and
nothing else. Reads APIFY_TOKEN from ~/.apify.env.

Media never enters a git repo — point --out at an ignored folder.
"""
import argparse, json, sys, urllib.request
from pathlib import Path

BASE = "https://api.apify.com/v2"


def token():
    for line in (Path.home() / ".apify.env").read_text().splitlines():
        if line.startswith("APIFY_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("APIFY_TOKEN not found in ~/.apify.env")


def run_actor(tok, actor, payload, timeout=300):
    req = urllib.request.Request(
        f"{BASE}/acts/{actor}/run-sync-get-dataset-items?timeout={timeout}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout + 30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("handle")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=24)
    a = ap.parse_args()
    tok = token()
    handle = a.handle.lstrip("@")

    print(f"scraping @{handle} — newest {a.limit} posts")
    posts = run_actor(tok, "apify~instagram-scraper", {
        "directUrls": [f"https://www.instagram.com/{handle}/"],
        "resultsType": "posts", "resultsLimit": a.limit,
        "addParentData": False})

    # A carousel's first frame is a still too — creators who shoot video
    # almost always still post the occasional graphic in a carousel.
    stills = [p for p in posts
              if p.get("type") in ("Image", "Sidecar") and p.get("displayUrl")]
    from collections import Counter
    print(f"  {len(posts)} posts — types: "
          f"{dict(Counter(p.get('type') for p in posts))}; "
          f"{len(stills)} usable stills")
    if not stills:
        sys.exit("no single-image posts in that window — try --limit higher "
                 "or another handle")

    stills.sort(key=lambda p: (p.get("likesCount") or 0), reverse=True)
    top = stills[0]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{handle}--{top.get('shortCode', 'post')}.jpg"
    urllib.request.urlretrieve(top["displayUrl"], dest)

    meta = {"handle": handle, "url": top.get("url"),
            "shortcode": top.get("shortCode"), "taken": top.get("timestamp"),
            "likes": top.get("likesCount"), "caption": top.get("caption"),
            "dimensions": {"w": top.get("dimensionsWidth"),
                           "h": top.get("dimensionsHeight")},
            "file": str(dest)}
    (out / "source.json").write_text(json.dumps(meta, indent=2))
    print(f"  saved {dest} ({dest.stat().st_size // 1024} KB)")
    print(f"  {top.get('url')}")


if __name__ == "__main__":
    main()
