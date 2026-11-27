"""Every picture an email asks a mail app to load, and whether each one will load (email_lead, 2026-11-13).

brand_b-nov-10a went out on 2026-11-12 with an empty hero: its hero is a background picture with a live
button on top, and the upload swapped only `src="assets/…"` for Klaviyo's hosted address, leaving
`background="assets/s02.jpg"` and `background-image:url(assets/s02.jpg)` pointing at a file only this Mac has.
Outlook's copy (VML `<v:fill src=…>`) was hosted; every other mail app drew the grey fill colour.

A picture is any of: <img src>, a `background` attribute, a CSS `url(...)` (inline or in <style>), a VML
`<v:fill src>` / `<v:image src>`. `problems()` lists every one that is not an absolute https address, and,
with `fetch`, every one that does not answer as an image. `missing_from()` lists the pictures of the local
build that the hosted copy dropped or left relative. Reads only; never writes to Klaviyo.

    python3 picture_refs.py <file.html> [...]       # print each picture and its problems
"""
import os
import re
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_kept = list(sys.path)
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != _here]   # this folder's email.py shadows the stdlib
import urllib.request  # noqa: E402
sys.path[:] = _kept

_PATTERNS = (
    ("img", re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)),
    ("background attribute", re.compile(r"<(?!v:)[a-z][a-z0-9]*\b[^>]*?\sbackground\s*=\s*[\"']([^\"']+)[\"']", re.I)),
    ("css url()", re.compile(r"url\(\s*[\"']?([^\"')]+?)[\"']?\s*\)", re.I)),
    ("outlook picture", re.compile(r"<v:(?:fill|image)\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)),
)


def refs(html):
    """[(kind, url)] in document order, one row per occurrence; data: and Klaviyo merge tags left out."""
    out = []
    for kind, rx in _PATTERNS:
        for m in rx.finditer(html or ""):
            u = m.group(1).strip()
            if u.startswith("data:") or "{{" in u or "{%" in u:
                continue
            out.append((m.start(), kind, u))
    return [(k, u) for _, k, u in sorted(out)]


def _answers_as_image(url, timeout=15):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "email-picture-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = r.headers.get("Content-Type") or ""
            body = r.read(64)
            if r.status != 200:
                return "answered %s" % r.status
            if not ctype.startswith("image/"):
                return "answered %s, not a picture" % (ctype or "no content type")
            if not body:
                return "answered an empty file"
    except Exception as e:  # noqa: BLE001 — any failure to load is the finding
        return "did not load (%s)" % e
    return None


def problems(html, fetch=True, _seen=None):
    """Every picture that a mail app could not load: relative, not https, or (fetch) not answering as an image."""
    out, seen = [], {} if _seen is None else _seen
    for kind, u in refs(html):
        if not u.lower().startswith("https://"):
            out.append("%s %s is not a hosted https address: mail apps show nothing there" % (kind, u))
            continue
        if fetch:
            if u not in seen:
                seen[u] = _answers_as_image(u)
            if seen[u]:
                out.append("%s %s %s" % (kind, u, seen[u]))
    return list(dict.fromkeys(out))


def missing_from(local_html, hosted_html):
    """Picture slots the local build has that the hosted copy lost: counts per kind must match."""
    have, want = {}, {}
    for k, _ in refs(hosted_html):
        have[k] = have.get(k, 0) + 1
    for k, _ in refs(local_html):
        want[k] = want.get(k, 0) + 1
    return ["the build has %d %s picture(s), the hosted email %d" % (n, k, have.get(k, 0))
            for k, n in want.items() if have.get(k, 0) != n]


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        h = open(f).read()
        print(f)
        for k, u in refs(h):
            print("  %-20s %s" % (k, u))
        for p in problems(h):
            bad += 1
            print("  PROBLEM", p)
    sys.exit(1 if bad else 0)
