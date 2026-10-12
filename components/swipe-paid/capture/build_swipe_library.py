#!/usr/bin/env python3
"""Turn an AdPlexity advertiser sweep into a by-angle swipe library.

The step between `adplexity_client.py advertiser <domain>` and a teardown:
dedupe the sweep, group creatives by the copy block they deliver, rank the
blocks by volume, and file every creative under its block split by media type.

    python3 build_swipe_library.py <brand-slug> [--no-media]

Reads   raw/advertiser_<domain-slug>_*_off*.json  (every page of the sweep)
Writes  raw/<brand>_uniq.json          deduped corpus, one row per creative
        assets/<brand>/by-angle/NN_<angle-slug>/_ANGLE.md
        assets/<brand>/by-angle/NN_<angle-slug>/video/<id>.mp4 + _poster.jpg
        assets/<brand>/by-angle/NN_<angle-slug>/image/<id>.jpg
        assets/<brand>/by-angle/README.md

assets/ is gitignored — media never enters the repo (10MB rule).

Meta appends the advertiser's page id to `description` in the API payload;
it is stripped before grouping or two identical copy blocks look distinct.
Landing pages come from `raw/ad_<id>.json` detail pulls (1 credit each) —
whatever reps have been pulled, mapped onto their block.
"""
import json, os, re, sys, glob, collections, urllib.request, concurrent.futures

HERE = os.path.dirname(os.path.abspath(__file__))

def slugify(s, n=52):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:n].strip("-") or "no-copy"

def norm_copy(s):
    """Strip the trailing page-id Meta glues onto the body text."""
    return re.sub(r"\d{10,}$", "", (s or "").strip()).strip()

def load_sweep(domain_slug):
    items = {}
    pat = os.path.join(HERE, "raw", f"advertiser_{domain_slug}_*_off*.json")
    files = sorted(glob.glob(pat))
    if not files:
        sys.exit(f"No sweep pages matching {pat}")
    for f in files:
        for a in json.load(open(f))["items"]:
            items[a["id"]] = a
    return list(items.values()), files

def landing_pages():
    """{ad_id: [urls]} for every ad detail pulled so far."""
    out = {}
    for f in glob.glob(os.path.join(HERE, "raw", "ad_*.json")):
        a = json.load(open(f))
        urls = [lp["url"] for lp in (a.get("landing_pages") or []) if lp.get("url")]
        if urls:
            out[a["id"]] = urls
    return out

def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return "skip"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as fh:
            fh.write(r.read())
        return "ok"
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        return f"FAIL {url} -> {e}"

def main(brand, domain, media=True):
    domain_slug = re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-")
    items, files = load_sweep(domain_slug)
    print(f"{len(items)} unique creatives from {len(files)} sweep pages")

    json.dump({"domain": domain, "count": len(items), "items": items},
              open(os.path.join(HERE, "raw", f"{brand}_uniq.json"), "w"), indent=1)

    lp_map = landing_pages()
    blocks = collections.defaultdict(list)
    for a in items:
        blocks[(a.get("title") or "", norm_copy(a.get("description")))].append(a)
    ranked = sorted(blocks.items(), key=lambda kv: (-len(kv[1]), kv[0][0]))

    root = os.path.join(HERE, "assets", brand, "by-angle")
    os.makedirs(root, exist_ok=True)
    jobs, rows = [], []
    for i, ((title, body), ads) in enumerate(ranked, 1):
        vids = [a for a in ads if a.get("video_url")]
        imgs = [a for a in ads if not a.get("video_url") and a.get("image_url")]
        lps = sorted({u for a in ads for u in lp_map.get(a["id"], [])})
        d = os.path.join(root, f"{i:02d}_{slugify(title)}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "_ANGLE.md"), "w") as fh:
            fh.write(f"# {i:02d} — {title or '*no copy*'}\n\n"
                     f"`{len(ads)} creatives` · `{len(vids)} video / {len(imgs)} static`\n\n"
                     f"## Headline\n\n{title or '*(none)*'}\n\n## Primary text\n\n{body or '*(none)*'}\n\n"
                     f"## Landing pages (from pulled ad details)\n\n"
                     + ("".join(f"- {u}\n" for u in lps) or "- *not resolved*\n")
                     + f"\n## Creative ids\n\n`{', '.join(str(a['id']) for a in ads)}`\n")
        if media:
            if vids:
                os.makedirs(os.path.join(d, "video"), exist_ok=True)
            if imgs:
                os.makedirs(os.path.join(d, "image"), exist_ok=True)
            for a in vids:
                jobs.append((a["video_url"], os.path.join(d, "video", f"{a['id']}.mp4")))
                if a.get("image_url"):
                    jobs.append((a["image_url"], os.path.join(d, "video", f"{a['id']}_poster.jpg")))
            for a in imgs:
                jobs.append((a["image_url"], os.path.join(d, "image", f"{a['id']}.jpg")))
        rows.append((i, title, len(ads), len(vids), len(imgs), lps))

    if jobs:
        print(f"downloading {len(jobs)} files ...")
        done = fails = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for r in ex.map(lambda j: fetch(*j), jobs):
                done += 1
                if isinstance(r, str) and r.startswith("FAIL"):
                    fails += 1
                    print(r)
                if done % 100 == 0:
                    print(f"  {done}/{len(jobs)}")
        print(f"media done: {done} files, {fails} failed")

    with open(os.path.join(root, "README.md"), "w") as fh:
        fh.write(f"# {brand.title()} swipe library — by angle\n\n"
                 f"Every live {brand.title()} creative from the AdPlexity advertiser sweep of "
                 f"`{domain}`, filed under the copy block it delivers, then split by media type.\n\n"
                 "```\nby-angle/\n  NN_<angle-slug>/\n    _ANGLE.md     headline + primary text verbatim,"
                 " counts, landing page\n    video/        <ad_id>.mp4  +  <ad_id>_poster.jpg\n"
                 "    image/        <ad_id>.jpg\n```\n\n"
                 "`NN` is rank by creative volume — `01` is the block carrying the most footage.\n\n"
                 f"## The {len(ranked)} angles\n\n"
                 "| # | Angle | Creatives | Video | Static | Landing page |\n|---:|---|---:|---:|---:|---|\n")
        for i, title, n, v, im, lps in rows:
            fh.write(f"| {i:02d} | {(title or '*no copy*')[:58]} | {n} | {v} | {im} | "
                     f"{', '.join('`'+u.split('?')[0]+'`' for u in lps) or '—'} |\n")
        tv = sum(r[3] for r in rows); ti = sum(r[4] for r in rows)
        fh.write(f"\n**Totals:** {sum(r[2] for r in rows)} creatives · {tv} video · {ti} static\n\n"
                 f"Filenames are AdPlexity ad ids — look any of them up in `raw/{brand}_uniq.json`.\n"
                 "Video posters are AdPlexity's thumbnail for that ad, not an extracted frame.\n"
                 "This folder is gitignored: media never goes in the repo.\n")
    print(f"library at {root}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], media="--no-media" not in sys.argv)
