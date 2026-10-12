#!/usr/bin/env python3
"""Full-page mobile screenshots, driven by Playwright.

    python3 shoot_pages_pw.py <brand> [urls.txt]

Same output as shoot_pages.py — page.png beside the capture under
assets/<brand>/pages/by-type/<type>/<slug>/ — but it drives Chrome through
Playwright instead of the old headless screenshot flag. Two reasons it exists:

  - the old flag buys height rather than measuring it, waits out a 240s
    timeout per page on a site that keeps a connection open, and trims
    afterwards. On Frøya that was minutes per page.
  - these funnels render client-side (ConvertFlow), so the page has to be
    scrolled and given time to build before it is worth shooting.

Run it with the venv that has playwright: ~/.local/venvs/ecom/bin/python3.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def slugify(u):
    return re.sub(r"[^a-z0-9]+", "-",
                  re.sub(r"^https?://", "", u.split("?")[0]).lower()).strip("-")[:80]


def main(brand, urlfile=None):
    from playwright.sync_api import sync_playwright
    d = os.path.join(HERE, "assets", brand, "pages")
    rows = json.load(open(os.path.join(d, "_classified.json")))
    by_url = {r["url"]: r for r in rows}
    urls = ([l.strip() for l in open(urlfile) if l.strip() and not l.startswith("#")]
            if urlfile else [r["url"] for r in rows])
    done = 0
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)
        for u in urls:
            r = by_url.get(u)
            slug = r["slug"] if r else slugify(u)
            dest = os.path.join(d, "by-type", r["type"] if r else "other", slug)
            os.makedirs(dest, exist_ok=True)
            out = os.path.join(dest, "page.png")
            if os.path.exists(out) and os.path.getsize(out) > 20000:
                print(f"skip  {u}", flush=True)
                done += 1
                continue
            ctx = br.new_context(viewport={"width": 390, "height": 844},
                                 device_scale_factor=2, user_agent=UA)
            pg = ctx.new_page()
            try:
                pg.goto(u, timeout=45000, wait_until="domcontentloaded")
                pg.wait_for_timeout(2000)
                pg.evaluate("""async () => { await new Promise(res => {
                    let y = 0; const t = setInterval(() => {
                      window.scrollBy(0, 1200); y += 1200;
                      if (y >= document.body.scrollHeight) { clearInterval(t); res(); }
                    }, 100);
                    setTimeout(() => { clearInterval(t); res(); }, 12000); }); }""")
                pg.wait_for_timeout(900)
                pg.evaluate("window.scrollTo(0, 0)")
                h = pg.evaluate("document.body.scrollHeight")
                if h > 26000:                      # a giant page at 2x times out
                    ctx2 = br.new_context(viewport={"width": 390, "height": 844},
                                          device_scale_factor=1, user_agent=UA)
                    p2 = ctx2.new_page()
                    p2.goto(u, timeout=45000, wait_until="domcontentloaded")
                    p2.wait_for_timeout(2500)
                    p2.screenshot(path=out, full_page=True, timeout=150000)
                    ctx2.close()
                else:
                    pg.screenshot(path=out, full_page=True, timeout=120000)
                print(f"ok  {h:>6}px  {u}", flush=True)
                done += 1
            except Exception as e:
                print(f"FAIL          {u} — {str(e)[:70]}", flush=True)
            ctx.close()
        br.close()
    print(f"\n{done}/{len(urls)} shot")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
