#!/usr/bin/env python3
"""Full-page mobile screenshots of captured pages, for the teardown deliverable.

    python3 shoot_pages.py <brand-slug> [urls.txt]

Headless Chrome at 390pt wide into a very tall window, then trimmed to the
real page height with ImageMagick — Chrome's old headless shoots the viewport,
so height is bought rather than measured. Writes page.png beside the page.html
and page.txt already filed under assets/<brand>/pages/by-type/<type>/<slug>/.

Without a url file it shoots one page per template family, picked from
_classified.json — the set a teardown actually shows.
"""
import concurrent.futures, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH, TALL, WORKERS = 390, 7000, 2

def slugify(u):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://", "", u.split("?")[0]).lower()).strip("-")[:80]

def shoot(url, out_png, profile):
    tmp = out_png + ".raw.png"
    p = subprocess.Popen([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                          "--hide-scrollbars", f"--user-data-dir={profile}",
                          f"--window-size={WIDTH},{TALL}", f"--screenshot={tmp}", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p.wait(timeout=240)
    except subprocess.TimeoutExpired:
        p.kill()
    if not os.path.exists(tmp):
        return None
    # trim the dead white below the fold, keep full width
    subprocess.run(["magick", tmp, "-background", "white", "-flatten",
                    "-fuzz", "1%", "-trim", "+repage", out_png],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(tmp)
    if not os.path.exists(out_png):
        return None
    h = subprocess.run(["identify", "-format", "%h", out_png],
                       capture_output=True, text=True).stdout.strip()
    return int(h) if h.isdigit() else None

def default_set(rows):
    """One page per template family: first of each type, plus every ad-facing PDP."""
    seen, picks = set(), []
    for r in rows:
        key = r["type"]
        if key not in seen:
            seen.add(key); picks.append(r["url"])
    return picks

def main(brand, urlfile=None):
    d = os.path.join(HERE, "assets", brand, "pages")
    rows = json.load(open(os.path.join(d, "_classified.json")))
    by_url = {r["url"]: r for r in rows}
    urls = ([l.strip() for l in open(urlfile) if l.strip() and not l.startswith("#")]
            if urlfile else default_set(rows))
    def one(job):
        i, u = job
        r = by_url.get(u)
        slug = r["slug"] if r else slugify(u)
        dest = (os.path.join(d, "by-type", r["type"], slug) if r
                else os.path.join(d, "by-type", "other", slug))
        os.makedirs(dest, exist_ok=True)
        # one Chrome profile per worker slot — they cannot share a user-data-dir
        profile = os.path.join(HERE, ".build", f"chrome-profile-{i % WORKERS}")
        os.makedirs(profile, exist_ok=True)
        out = os.path.join(dest, "page.png")
        if os.path.exists(out) and os.path.getsize(out) > 20000:
            print(f"skip        {u}", flush=True)
            return True
        h = shoot(u, out, profile)
        print(f"{'ok ' if h else 'FAIL'} {str(h or '-'):>6}px  {u}", flush=True)
        return bool(h)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        done = sum(ex.map(one, enumerate(urls)))
    print(f"\n{done}/{len(urls)} shot")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
