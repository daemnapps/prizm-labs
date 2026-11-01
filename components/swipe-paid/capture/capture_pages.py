#!/usr/bin/env python3
"""Capture a competitor's funnel pages: HTML, readable text, stack, redirects.

    python3 capture_pages.py <brand-slug> urls.txt

One row per URL in assets/<brand>/pages/_capture.json, and per page:
    assets/<brand>/pages/<slug>.html    raw HTML as served
    assets/<brand>/pages/<slug>.txt     readable text, scripts/styles stripped

Mobile UA — these funnels serve a different page to a desktop browser.
"""
import json, os, re, sys, html, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

def slugify(u):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://", "", u.split("?")[0]).lower()).strip("-")[:80]

class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self): self.chain = []
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append(f"{code} {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def text_of(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", h)
    h = re.sub(r"(?is)<!--.*?-->", " ", h)
    h = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    h = html.unescape(h)
    h = re.sub(r"[ \t\r\f\v]+", " ", h)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", h).strip()

def stack_of(h):
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', h)
    return {"shopify": "cdn.shopify.com" in h or "Shopify.theme" in h,
            "fbq": "connect.facebook.net" in h or "fbq(" in h,
            "gtag": "googletagmanager.com" in h or "gtag(" in h,
            "tiktok": "analytics.tiktok.com" in h,
            "klaviyo": "klaviyo" in h.lower(),
            "clarity": "clarity.ms" in h,
            "triplewhale": "triplewhale" in h.lower(),
            "northbeam": "northbeam" in h.lower(),
            "scripts": scripts[:40]}

def capture(url, outdir):
    rh = Redirects()
    op = urllib.request.build_opener(rh)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "en-US,en;q=0.9"})
    row = {"url": url, "slug": slugify(url), "redirects": rh.chain}
    try:
        with op.open(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
            row["status"], row["final_url"] = r.status, r.url
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        row["status"], row["final_url"] = e.code, url
    except Exception as e:
        row["status"], row["error"] = None, str(e)
        return row
    t = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    row["title"] = html.unescape(t.group(1).strip()) if t else None
    txt = text_of(body)
    row["text_chars"], row["stack"] = len(txt), stack_of(body)
    row["text"] = txt
    open(os.path.join(outdir, row["slug"] + ".html"), "w").write(body)
    open(os.path.join(outdir, row["slug"] + ".txt"), "w").write(txt)
    return row

def main(brand, urlfile):
    outdir = os.path.join(HERE, "assets", brand, "pages")
    os.makedirs(outdir, exist_ok=True)
    urls = [l.strip() for l in open(urlfile) if l.strip() and not l.startswith("#")]
    rows = []
    for u in urls:
        r = capture(u, outdir)
        rows.append(r)
        print(f"{r.get('status')}  {r.get('text_chars','-'):>7}ch  {u}")
    json.dump(rows, open(os.path.join(outdir, "_capture.json"), "w"), indent=1)
    print(f"\n{len(rows)} pages -> {outdir}")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
