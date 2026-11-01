"""Pinterest inspiration for the pictures an email makes.

the owner, 2026-10-18: "the team likes to use Pinterest for inspiration on images, so outside of our regular brand assets
and customer stuff, we should also pull in relevant images from Pinterest to create unique images from all of our
references for image emails."

For each picture the layout asks to make (a key visual, a gift picture, a story picture), this searches Pinterest
for the look it describes and keeps the best few pins as INSPIRATION references: light, composition, styling,
props and mood. They sit beside the brand's real product photos and the real people the index already supplies;
they never stand in for the product or a person, and nothing from a pin is copied (no faces, no logos, no text).

    pins.for_picture(run_dir, slot_n, query, n=4) -> [paths]   # cached per run: a slot is searched once

Pins land in <run>/media/pins/p<NN>/ with a pins.json beside them (the pin page, the image link, the query), so a
person can see exactly what inspired a picture. Through the shared Apify door (components/apify/apify.py), the
actor fetch_cat/pinterest-search-scraper, about $0.06 a search (start + 10 results). easyapi's search returned
nothing on 2026-10-18 and devcake's refuses fewer than 24 results. PINS_OFF=1 in the environment
skips the step.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTOR = "fetch_cat~pinterest-search-scraper"        # the API spells owner/name with a tilde
PER_SEARCH = 10


def _apify():
    p = str(HERE.parent.parent / "apify")
    if p not in sys.path:
        sys.path.append(p)
    import apify
    return apify


def _image_url(item):
    for k in ("imageUrl", "image", "image_url", "images", "media", "thumbnail"):
        v = item.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, dict):
            for kk in ("orig", "original", "736x", "url", "large"):
                vv = v.get(kk)
                if isinstance(vv, str) and vv.startswith("http"):
                    return vv
                if isinstance(vv, dict) and str(vv.get("url", "")).startswith("http"):
                    return vv["url"]
        if isinstance(v, list) and v:
            x = v[0]
            if isinstance(x, str) and x.startswith("http"):
                return x
            if isinstance(x, dict) and str(x.get("url", "")).startswith("http"):
                return x["url"]
    return None


def query_for(todo, brief="", use="story"):
    """A short Pinterest search from what the picture shows: the scene words, never brand or product names."""
    import re
    text = (todo or "").lower()
    text = re.sub(r"\b(the|a|an|her|his|their|our|real|brilliance|radiance|body|scrub|cream|tube|brand-b|brand-a|flex)\b", " ", text)
    words = [w for w in re.findall(r"[a-z][a-z\-]+", text) if len(w) > 2][:4]   # long searches come back empty
    tail = {"key-visual": "editorial", "gift": "gift styling", "story": "aesthetic"}.get(use, "")
    return " ".join(words + [tail]).strip()


def for_picture(run_dir, n, query, keep=4):
    """Up to `keep` pin images for picture slot n, downloaded into the run; [] when off, failed or nothing found."""
    if os.environ.get("PINS_OFF") or not query:
        return []
    d = Path(run_dir) / "media" / "pins" / ("p%02d" % n if isinstance(n, int) else "p%s" % n)   # n: the picture's own key
    meta = d / "pins.json"
    if meta.exists():                                      # searched once per slot, never paid for twice
        return [str(d / x["file"]) for x in json.loads(meta.read_text()).get("pins", []) if (d / x["file"]).exists()]
    try:
        items = _apify().run(ACTOR, {"queries": [query], "maxResultsPerQuery": PER_SEARCH}, timeout=300) or []
    except BaseException as e:                            # a spent allowance or a dead actor never stops the email
        print("   pins: none (%s)" % str(e)[:120])
        return []
    d.mkdir(parents=True, exist_ok=True)
    kept = []
    for i, it in enumerate(items):
        url = _image_url(it)
        if not url:
            continue
        f = d / ("pin-%02d.jpg" % i)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                f.write_bytes(r.read())
        except Exception:
            continue
        kept.append({"file": f.name, "image": url, "pin": it.get("pinUrl") or it.get("url"),
                     "title": (it.get("title") or it.get("description") or "")[:160]})
        if len(kept) >= keep:
            break
    if kept:                                              # an empty search is tried again next run, never cached
        meta.write_text(json.dumps({"query": query, "actor": ACTOR, "pins": kept}, indent=1, ensure_ascii=False))
    return [str(d / x["file"]) for x in kept]
