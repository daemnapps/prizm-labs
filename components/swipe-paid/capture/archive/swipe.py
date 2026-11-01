#!/usr/bin/env python3
"""Swipe a whole brand out of the ad tools. One command.

    python3 swipe.py <domain> [brand] [options]

    python3 swipe.py brand-c.shop
    python3 swipe.py competitor-a.example competitor-a --max 1200
    python3 swipe.py newbrand.com --from library     # resume mid-way

Runs the stages in order, stopping at the first one that fails:

    1 sweep      their whole live ad library, paged until a page comes back short
    2 resolve    ad details for a few creatives per copy block -> landing pages
    3 library    dedupe, group by copy block, rank, download every video/still
    4 sitemap    read their sitemaps for the REAL page list (not just ad targets)
    5 capture    every page: HTML + readable text + stack + redirects
    6 classify   sort pages by what they structurally are, read the slug codes
    7 shoot      full-page mobile screenshots, one per template family
    8 drive      file the media into the paid swipe home (swipe_home) /<brand>/
    9 links      print the Drive links

What it does NOT do is read the thing. Stage 10 is a person looking at the
library and writing the teardown, then `build_teardown_page.py` puts it in the
house format. That stage stays human on purpose.

Credits: roughly 1.2 per creative in their library. --max caps the sweep so a
whale can't quietly spend the month's budget; the run says when it stopped short.
"""
import os, pathlib, re, subprocess, sys, json, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STAGES = ["sweep", "resolve", "library", "sitemap", "capture", "classify",
          "shoot", "drive", "links"]
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

def _workspace_root():
    p = pathlib.Path(__file__).resolve()
    for d in p.parents:
        if (d / "brands").is_dir() and (d / "CLAUDE.md").is_file():
            return d
    raise RuntimeError("not inside the workspace")


CLASSIFIER = str(_workspace_root() / "components" / "naming" / "classify_pages.py")


def run(*args, quiet=False):
    print(f"\n$ python3 {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, *args], cwd=HERE,
                       capture_output=quiet, text=True)
    if r.returncode:
        sys.exit(f"FAILED at: {' '.join(args)}")
    return r.stdout or ""

def domain_slug(d):
    return re.sub(r"[^a-z0-9]+", "-", d.lower()).strip("-")

def sweep(domain, page, cap):
    """Page until a page comes back short or the cap is hit."""
    got, offset = 0, 0
    while got < cap:
        out = run("adplexity_client.py", "advertiser", domain,
                  "--count", str(page), "--offset", str(offset), "--pages", "4",
                  quiet=True)
        print(out[-400:], flush=True)
        m = re.search(r"^(\d+) creatives for", out, re.M)
        n = int(m.group(1)) if m else 0
        got += n
        offset += n
        if n < page * 4:
            print(f"\nlibrary exhausted at {got} creatives (last page came back short)")
            return got, True
    print(f"\nstopped at the --max cap of {cap}: their library is bigger than this sweep")
    return got, False

def resolve(brand, domain, per_block=4):
    """Pull ad details for representatives of each copy block -> landing pages."""
    import collections, glob
    items = {}
    for f in glob.glob(os.path.join(HERE, "raw", f"advertiser_{domain_slug(domain)}_*_off*.json")):
        for a in json.load(open(f))["items"]:
            items[a["id"]] = a
    g = collections.defaultdict(list)
    for a in items.values():
        g[(a.get("title") or "", re.sub(r"\d{10,}$", "", (a.get("description") or "").strip()))].append(a)
    picks = []
    for ads in sorted(g.values(), key=lambda v: -len(v)):
        n = len(ads)
        for i in sorted({0, n // 2, n - 1})[:per_block]:
            picks.append(ads[i]["id"])
    print(f"resolving landing pages for {len(picks)} representative ads "
          f"across {len(g)} copy blocks ({len(picks)} credits)")
    for pid in picks:
        if not os.path.exists(os.path.join(HERE, "raw", f"ad_{pid}.json")):
            run("adplexity_client.py", "ad", str(pid), quiet=True)
    return len(g)

LOCALE = re.compile(r"^/[a-z]{2}(-[a-z]{2})?/")

def sitemaps(domain, brand):
    """Their sitemap is the real page list — the ads only point at a handful.

    Two filters earn their keep: locale mirrors (`/fr-ca/...`) triple the page
    count and say nothing new, and the ad-detail store holds landing pages for
    every brand ever swept, so it has to be filtered back to this one.
    """
    base = f"https://{domain}"
    seen, queue = set(), [f"{base}/sitemap.xml"]
    urls = set()
    while queue:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            req = urllib.request.Request(sm, headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  skip {sm}: {e}")
            continue
        for loc in re.findall(r"<loc>(.*?)</loc>", body):
            loc = loc.replace("&amp;", "&")
            if not loc.startswith(base):
                continue
            path = loc[len(base):]
            if loc.endswith(".xml") or "sitemap" in loc.split("/")[-1]:
                if not LOCALE.match(path):
                    queue.append(loc)
            elif not LOCALE.match(path):
                urls.add(loc)
    # every landing page THIS brand's ads point at — kept even when it is a
    # locale page, because an ad target is a real destination
    import glob
    host = domain.split("/")[0]
    for f in glob.glob(os.path.join(HERE, "raw", "ad_*.json")):
        for lp in (json.load(open(f)).get("landing_pages") or []):
            u = lp.get("url", "").split("?")[0]
            if re.match(rf"https?://([a-z0-9-]+\.)?{re.escape(host)}/", u):
                urls.add(u)
    out = os.path.join(HERE, "assets", brand, "pages")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "_urls.txt")
    open(path, "w").write("\n".join(sorted(urls)) + "\n")
    print(f"{len(urls)} pages found across {len(seen)} sitemaps -> {path}")
    return path

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    domain = args[0]
    brand = args[1] if len(args) > 1 and not args[1].startswith("--") else \
        re.sub(r"\..*$", "", domain_slug(domain))

    def opt(flag, default, cast=str):
        return cast(args[args.index(flag) + 1]) if flag in args else default
    start = STAGES.index(opt("--from", "sweep"))
    cap = opt("--max", 2000, int)
    page = opt("--page", 50, int)

    print(f"=== swipe: {brand} ({domain}) · stages {' → '.join(STAGES[start:])} ===")
    urls = os.path.join(HERE, "assets", brand, "pages", "_urls.txt")

    for stage in STAGES[start:]:
        print(f"\n———— {stage.upper()} ————")
        if stage == "sweep":
            sweep(domain, page, cap)
        elif stage == "resolve":
            resolve(brand, domain)
        elif stage == "library":
            run("build_swipe_library.py", brand, domain)
        elif stage == "sitemap":
            urls = sitemaps(domain, brand)
        elif stage == "capture":
            run("capture_pages.py", brand, urls)
        elif stage == "classify":
            # The classifier graduated to components/naming/ on 2026-09-11 —
            # it decides the format every page and ad is named by, so it is a
            # shared vocabulary now, not this pipeline's private helper.
            run(CLASSIFIER, brand, os.path.join(HERE, "assets"))
        elif stage == "shoot":
            run("shoot_pages.py", brand)
        elif stage == "drive":
            run("sync_to_drive.py", brand)
        elif stage == "links":
            run("drive_links.py", brand)

    print(f"\n=== {brand} is in. Read it, then: "
          f"build_teardown_page.py {brand} {brand}-teardown-content.json "
          f"{brand}-teardown-<date>.html ===")

if __name__ == "__main__":
    main()
