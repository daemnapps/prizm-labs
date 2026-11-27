#!/usr/bin/env python3
"""Capture any web page as text the teardown can read: headings, paragraphs, list items, buttons and links, pictures,
with the page's navigation, header and footer marked as such (they are the source's own furniture, never ours).

    python3 capture.py <url> <out_dir>        -> out_dir/page.html, out_dir/page.txt, out_dir/capture.json

Plain HTTP first; if the page comes back empty or blocked, the Apify website content crawler (APIFY_TOKEN, then
APIFY_TOKEN_PERSONAL through components/keys) renders it. Agnostic: works on any page.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
SKIP = {"script", "style", "noscript", "svg", "template", "iframe", "form"}
FURNITURE = {"nav": "NAV", "header": "HEADER", "footer": "FOOTER", "aside": "ASIDE"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="ignore")


def fetch_apify(url):
    sys.path.append(str(Path(__file__).resolve().parents[2] / "keys"))
    tokens = []
    try:
        import loader  # components/keys/loader.py: the one way code reads keys
        for name in ("APIFY_TOKEN", "APIFY_TOKEN_PERSONAL"):   # company first, then the personal key (account-agnostic)
            t = loader.key(name, required=False)
            if t and t not in tokens:
                tokens.append(t)
    except Exception as e:  # noqa: BLE001
        print(f"  ! keys: {e}")
    for tok in tokens:
        try:
            api = ("https://api.apify.com/v2/acts/apify~website-content-crawler/run-sync-get-dataset-items"
                   f"?token={tok}")
            body = json.dumps({"startUrls": [{"url": url}], "maxCrawlPages": 1, "saveHtml": True,
                               "crawlerType": "playwright:chrome"}).encode()
            req = urllib.request.Request(api, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                items = json.loads(r.read())
            if items and items[0].get("html"):
                return items[0]["html"]
        except Exception as e:  # noqa: BLE001
            print(f"  ! apify: {e}")
    return ""


def text_of(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def walk(el, out, region=None):
    for ch in el.children:
        if isinstance(ch, NavigableString) or not isinstance(ch, Tag):
            continue
        name = ch.name.lower()
        if name in SKIP:
            continue
        cls = " ".join(ch.get("class") or []).lower() + " " + (ch.get("id") or "").lower()
        reg = region
        if name in FURNITURE:
            reg = FURNITURE[name]
        elif reg is None and re.search(r"\b(site-?header|site-?footer|navbar|breadcrumb|cookie|newsletter|related)\b", cls):
            reg = "FURNITURE"
        tag = f"[{reg}] " if reg else ""
        if re.fullmatch(r"h[1-6]", name):
            t = text_of(ch)
            if t:
                out.append(f"{tag}{'#' * int(name[1])} {t}")
            continue
        if name == "img":
            alt = (ch.get("alt") or "").strip()
            src = ch.get("src") or ch.get("data-src") or ""
            out.append(f"{tag}[IMAGE alt={alt} · {src.split('/')[-1][:60]}]")
            continue
        if name in ("button",) or (name == "a" and re.search(r"\b(btn|button|cta)\b", cls)):
            t = text_of(ch)
            if t:
                out.append(f"{tag}[BUTTON: {t}" + (f" -> {ch.get('href')}" if ch.get("href") else "") + "]")
            continue
        if name in ("p", "li", "blockquote", "figcaption", "td", "th", "dt", "dd", "summary"):
            t = text_of(ch)
            if t:
                pre = "- " if name == "li" else "> " if name == "blockquote" else ""
                out.append(f"{tag}{pre}{t}")
            for a in ch.find_all("a", href=True):
                at = text_of(a)
                if at and len(at) < 80 and at.lower() not in t.lower()[: len(at) + 2]:
                    pass
            continue
        if name == "a" and ch.get("href"):
            t = text_of(ch)
            if t and not ch.find(re.compile("^(p|h[1-6]|li|div)$")):
                out.append(f"{tag}[LINK: {t} -> {ch['href'][:120]}]")
                continue
        walk(ch, out, reg)


def capture(url, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    html, how = "", "http"
    try:
        html = fetch(url)
    except Exception as e:  # noqa: BLE001
        print(f"  ! plain fetch failed: {e}")
    lines = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        walk(soup.body or soup, lines)
    if len(" ".join(lines).split()) < 150:
        html2 = fetch_apify(url)
        if html2:
            html, how, lines = html2, "apify", []
            s2 = BeautifulSoup(html, "html.parser"); walk(s2.body or s2, lines)
    # drop exact repeats that are furniture noise (menus repeated for mobile)
    seen, clean = set(), []
    for ln in lines:
        k = ln.lower()
        if k in seen and (ln.startswith("[") or len(ln) < 60):
            continue
        seen.add(k)
        clean.append(ln)
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
    (out / "page.html").write_text(html or "")
    body = "\n".join(clean)
    (out / "page.txt").write_text(f"URL: {url}\nTITLE: {title}\n\n{body}\n")
    rec = {"url": url, "title": title, "via": how, "lines": len(clean), "words": len(body.split())}
    (out / "capture.json").write_text(json.dumps(rec, indent=1))
    print(f"captured {url} via {how}: {rec['lines']} lines, {rec['words']} words")
    return rec


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    capture(sys.argv[1], sys.argv[2])
