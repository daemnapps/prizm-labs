#!/usr/bin/env python3
"""What on a landing page is NOT the argument — found in code, for free, before
and after the model reads it.

    furniture.py scan <saved page file> [--brand <brand>]    print what the code finds
    furniture.py lines <saved page file>                     print the page as the model is handed it

Four jobs, none of which spends anything:

  load()            a saved page as readable lines. An `.html` file is reduced
                    in code: scripts, styles, inline pictures and tracking
                    noise are dropped; text, headings (`#`), pictures
                    (`[IMAGE alt=…]`), links and buttons are kept in page
                    order, and every line remembers whether it sat inside the
                    site's menu, footer, cookie bar or a pop-up. A `.txt`/`.md`
                    capture is read as it stands.
  scan()            which lines are page furniture (menu, footer, cookie bar,
                    legal lines, pop-ups) and which carry damage (a template
                    tag showing as code, filler text, a hidden character).
                    Handed to the read step as a starting list — the read step
                    decides, this only points.
  strip_block()     the read step's own STRIP block: furniture words, defect
                    quotes, the source's names and its figures — data the gate
                    checks the construct against.
  sections_only()   the record with its PAGE FURNITURE section taken out — the
                    later steps are never shown furniture words, so they
                    cannot carry them.

This tool does not fetch. A page is saved first; this reads the saved file.
No brand's words are typed here: a brand's own names are read from its folder
at run time (`brands/<brand>/products/store.json`, when it is there).
"""
import html.parser
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402
import slots as S                                             # noqa: E402

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
DROP = {"script", "style", "noscript", "svg", "template", "iframe", "object", "canvas", "select", "datalist"}
BLOCK = {"p", "div", "section", "article", "main", "aside", "header", "footer", "nav", "ul", "ol", "li", "table",
         "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "form", "blockquote", "figure",
         "figcaption", "details", "summary", "dl", "dt", "dd", "pre", "address", "fieldset", "legend", "label",
         "body", "html", "head", "title", "picture", "video"}
# Where on the page a line sat — read off the markup, never off a brand's words.
ZONE_TAGS = {"nav": "site menu", "footer": "footer"}
ZONE_ROLES = {"navigation": "site menu", "contentinfo": "footer", "dialog": "pop-up", "alertdialog": "pop-up",
              "banner": "site header"}
ZONE_WORDS = [
    (re.compile(r"cookie|consent|gdpr|onetrust|privacy-banner"), "cookie or consent bar"),
    (re.compile(r"breadcrumb"), "breadcrumb trail"),
    (re.compile(r"cart-drawer|mini-cart|minicart|cart-notification|drawer-cart|side-cart"), "cart drawer"),
    (re.compile(r"newsletter|popup|pop-up|modal|klaviyo|email-signup|exit-intent"), "pop-up or sign-up form"),
    (re.compile(r"skip-to|skip-link|skiplink|visually-hidden|sr-only"), "screen-reader or skip link"),
    (re.compile(r"announcement|promo-bar|top-bar|topbar|utility-bar"), "announcement bar — site-wide on most stores; confirm"),
    (re.compile(r"(?<![a-z])(?:site-)?footer(?![a-z])"), "footer"),
    (re.compile(r"(?<![a-z])(?:site-nav|main-nav|navbar|nav-menu|mega-menu|menu-drawer|mobile-nav)"), "site menu"),
]
LEGAL = re.compile(r"©|\(c\)\s*\d{4}|all rights reserved|privacy policy|terms (?:of|and|&) (?:service|use|conditions)|"
                   r"refund policy|shipping policy|return policy|cookie (?:policy|settings|preferences)|"
                   r"do not sell (?:or share )?my|powered by |skip to (?:main )?content|"
                   r"statements? (?:have|has) not been evaluated|not intended to diagnose|"
                   r"results may vary|this site is not (?:a )?part of", re.I)
MERGE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\*\|[A-Z_:]+\|\*|\[\[\s*[a-z_.]+\s*\]\]")
FILLER = re.compile(r"lorem ipsum|dolor sit amet|^\s*(?:undefined|NaN|null|\[object Object\])\s*$", re.I)
HIDDEN = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
NO_TARGET = re.compile(r"\[(?:LINK|BUTTON) [^\]]*-> \(no target\)\]")
MONEY = re.compile(r"(?:[$£€]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP|dollars|bucks)\b)", re.I)
# What a construct may never name: the frame every page on the site arrives in.
FRAME_NOUNS = ("navigation bar", "navigation menu", "nav bar", "site menu", "site header", "site footer", "footer",
               "cookie bar", "cookie banner", "consent banner", "announcement bar", "breadcrumb", "privacy policy",
               "terms of service", "skip to content", "cart drawer")


# ------------------------------------------------------------------ the page as lines

class _Reduce(html.parser.HTMLParser):
    """A saved HTML page as plain lines, in page order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []                 # [(text, zone)]
        self.buf, self.buf_zone, self.prefix = [], None, ""
        self.stack = []                 # [(tag, zone, dropped)]
        self.title, self.site_name, self.in_title = "", "", False
        self.links = []                 # [(href, is_button, start index in buf)]

    # -- state
    def _zone(self):
        for _, z, _ in reversed(self.stack):
            if z:
                return z
        return None

    def _dropped(self):
        return any(d for _, _, d in self.stack)

    def _flush(self):
        text = re.sub(r"\s+", " ", " ".join(self.buf)).strip()
        if text:
            self.lines.append(((self.prefix + text) if self.prefix else text, self.buf_zone))
        self.buf, self.buf_zone, self.prefix = [], None, ""

    def _add(self, piece):
        if not self.buf:
            self.buf_zone = self._zone()
        self.buf.append(piece)

    @staticmethod
    def _zone_of(tag, a):
        if tag in ZONE_TAGS:
            return ZONE_TAGS[tag]
        role = (a.get("role") or "").lower()
        if role in ZONE_ROLES:
            return ZONE_ROLES[role]
        marks = " ".join(str(a.get(k) or "") for k in ("class", "id", "aria-label", "data-section-type")).lower()
        if marks.strip():
            for rx, zone in ZONE_WORDS:
                if rx.search(marks):
                    return zone
        return None

    @staticmethod
    def _file(src):
        src = (src or "").strip()
        if not src:
            return ""
        if src.startswith("data:"):
            return "inline picture"
        return (urlparse(src).path.rsplit("/", 1)[-1] or src)[:60]

    @staticmethod
    def _target(href):
        href = (href or "").strip()
        if not href or href == "#" or href.lower().startswith("javascript:"):
            return "(no target)"
        return href.split("?")[0][:160]

    # -- parser events
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            if (a.get("property") or a.get("name") or "").lower() == "og:site_name":
                self.site_name = (a.get("content") or "").strip()
            return
        was_dropped = self._dropped()
        if tag in BLOCK and not was_dropped:
            self._flush()
        if tag not in VOID:
            self.stack.append((tag, self._zone_of(tag, a), tag in DROP))
        if was_dropped:
            return
        if tag == "title":
            self.in_title = True
        elif tag == "iframe":
            if re.search(r"youtube|youtu\.be|vimeo|wistia|vidalytics|loom|vturb", a.get("src") or "", re.I):
                self._add("[VIDEO embedded]")
        elif tag == "select":
            self._add("[CHOICE LIST]")
        elif tag in DROP:
            return
        elif tag == "img":
            self._add(f"[IMAGE alt={(a.get('alt') or '').strip()} · {self._file(a.get('src') or a.get('data-src'))}]")
        elif tag == "video":
            self._add("[VIDEO]")
        elif tag == "input":
            kind = (a.get("type") or "text").lower()
            if kind in ("submit", "button") and a.get("value"):
                self._add(f"[BUTTON {a['value'].strip()}]")
            elif kind not in ("hidden", "checkbox", "radio"):
                self._add(f"[FIELD {(a.get('placeholder') or a.get('name') or kind).strip()}]")
        elif tag == "a":
            marks = " ".join(str(a.get(k) or "") for k in ("class", "role")).lower()
            self.links.append((self._target(a.get("href")), bool(re.search(r"btn|button|cta", marks)), len(self.buf)))
        elif tag == "button":
            self.links.append((None, True, len(self.buf)))
        elif re.fullmatch(r"h[1-6]", tag):
            self.prefix = "#" * int(tag[1]) + " "
        elif tag == "li":
            self.prefix = "- "

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self.in_title = False
        if tag in ("a", "button") and self.links and not self._dropped():
            href, is_button, at = self.links.pop()
            words = re.sub(r"\s+", " ", " ".join(self.buf[at:])).strip()
            kind = "BUTTON" if is_button else "LINK"
            token = f"[{kind} {words}" + (f" -> {href}]" if href else "]")
            if words or href:
                self.buf[at:] = [token]
        if any(t == tag for t, _, _ in self.stack):
            while self.stack:
                t, _, _ = self.stack.pop()
                if t == tag:
                    break
        if tag in BLOCK and not self._dropped():
            self._flush()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return
        if self._dropped() or not data.strip():
            return
        self._add(data.strip())

    def close(self):
        super().close()
        self._flush()


def load(source):
    """{"text", "zones": {line number: where it sat}, "title", "site_name",
    "kind", "raw_chars"} — the saved page as the lines a model is handed."""
    f = Path(source)
    raw = f.read_text(errors="replace")
    if f.suffix.lower() not in (".html", ".htm"):
        kept, second = _drop_second_copy([(t, None) for t in raw.strip().splitlines()])
        return {"text": "\n".join(t for t, _ in kept) + "\n", "zones": {}, "title": "", "site_name": "",
                "kind": "text capture", "raw_chars": len(raw), "second_copy_lines_dropped": second}
    r = _Reduce()
    r.feed(raw)
    r.close()
    lines, last = [], None
    for text, zone in r.lines:
        if text == last:                                   # a desktop copy and a mobile copy of one line
            continue
        lines.append((text, zone))
        last = text
    lines, second = _drop_second_copy(lines)
    zones = {n: z for n, (_, z) in enumerate(lines, 1) if z}
    return {"text": "\n".join(t for t, _ in lines) + "\n", "zones": zones, "title": re.sub(r"\s+", " ", r.title).strip(),
            "site_name": r.site_name, "kind": "saved html, reduced in code", "raw_chars": len(raw),
            "second_copy_lines_dropped": second}


def _drop_second_copy(lines):
    """Many saved pages hold the whole page twice — one render for wide
    screens, one for phones. When the main headline comes round again and what
    follows it has been read already, the second copy is dropped. Repetition
    INSIDE a page (an ask made twice) is structure and is left alone."""
    texts = [t for t, _ in lines]
    heads = [i for i, t in enumerate(texts) if t.startswith("# ")]
    if len(heads) >= 2 and texts[heads[0]] == texts[heads[1]]:
        a, b = heads[0], heads[1]
    else:                                                  # a text capture has no headline marks: the first long line that comes round again
        a = next((i for i, t in enumerate(texts[:40]) if len(t) >= 30 and t in texts[i + 1:]), None)
        if a is None:
            return lines, 0
        b = texts.index(texts[a], a + 1)
    cut = max(a + 1, b - a)
    first = set(texts[:cut])
    while cut > a + 1 and texts[cut - 1] in set(texts[:a + 1]):
        cut -= 1
    rest = [t for t in texts[cut:] if len(t) >= 30]
    if len(rest) < 5 or sum(t in first for t in rest) / len(rest) < 0.7:
        return lines, 0
    return lines[:cut], len(lines) - cut


def numbered(text):
    """The page with its line numbers, as the read step is handed it."""
    return "\n".join(f"{n:>4}  {line}" for n, line in enumerate(text.splitlines(), 1)) + "\n"


# ------------------------------------------------------------------ the free scan

def _ranges(items):
    """[{line, why, text}] → the same, with a run of neighbours on one `why` folded into one row."""
    out = []
    for it in items:
        if out and out[-1]["why"] == it["why"] and it["line"] - out[-1]["to"] <= 1:
            out[-1]["to"] = it["line"]
            out[-1]["count"] += 1
        else:
            out.append({"line": it["line"], "to": it["line"], "count": 1, "why": it["why"], "text": it["text"]})
    return out


def scan(page):
    """{furniture: [{line, to, count, why, text}], defects: [{line, kind, quote}]} —
    what the code can see without a model. Line numbers are the reduced page's own."""
    furn, defects, dead = [], [], 0
    for n, line in enumerate(page["text"].splitlines(), 1):
        s = line.strip()
        if not s or not HIDDEN.sub("", s).strip():
            continue
        why = page["zones"].get(n)
        if why:
            why = f"sat inside the page's {why}" if not why.startswith("announcement") else f"sat inside an {why}"
        elif LEGAL.search(s) and len(s) < 400:
            why = "legal, policy or copyright line"
        if why:
            furn.append({"line": n, "why": why, "text": s[:120]})
        for tag in MERGE.findall(s):
            defects.append({"line": n, "kind": "template tag showing as code", "quote": tag[:80]})
        if FILLER.search(s):
            defects.append({"line": n, "kind": "filler or a broken value showing as text", "quote": s[:80]})
        if HIDDEN.search(s):
            defects.append({"line": n, "kind": "hidden character inside a line", "quote": HIDDEN.sub("", s)[:80]})
        if not why and NO_TARGET.search(s) and "[BUTTON" in s:
            dead += 1
            if dead <= 8:
                defects.append({"line": n, "kind": "button that goes nowhere in the saved copy (may be script-driven — confirm)",
                                "quote": NO_TARGET.search(s).group(0)[:80]})
    return {"furniture": _ranges(furn), "defects": defects}


def findings_text(found):
    """The scan, as the read step is handed it."""
    out = ["Lines the code already flagged as page furniture (lines · why · first text):"]
    out += [f"- {f['line']}" + (f"–{f['to']}" if f["to"] != f["line"] else "") + f" · {f['why']} · {f['text']}"
            for f in found["furniture"]] or ["- none found by the code"]
    out += ["", "Damage the code already found (line · kind · quoted):"]
    out += [f"- {d['line']} · {d['kind']} · {d['quote']}" for d in found["defects"]] or ["- none found by the code"]
    return "\n".join(out)


# ------------------------------------------------------------------ names the construct may not carry

def _host_label(url):
    host = (urlparse(url if "//" in (url or "") else "//" + (url or "")).hostname or "").lower()
    parts = [p for p in host.split(".") if p and p != "www"]
    return parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")


def brand_names(brand):
    """The names the brand this run files under goes by, read from its own
    folder at run time: the folder name, and — when the brand keeps a store
    file — its name, its site and its product titles."""
    names = {brand}
    try:
        store = json.loads((P.BRANDS / brand / "products" / "store.json").read_text())
    except (OSError, ValueError):
        store = {}
    if store.get("brand"):
        names.add(str(store["brand"]))
    if store.get("site"):
        names.add(_host_label(store["site"]))
    for p in store.get("products") or []:
        title = re.sub(r"[™®©]", "", str(p.get("title") or "")).strip()
        if len(title.split()) >= 2:
            names.add(title)
    return sorted(n for n in names if n and len(n) >= 3)


def code_names(page, source_url):
    """Names the code can see for itself: the site's own declared name and the
    address the page was saved from."""
    names = set()
    if page.get("site_name"):
        names.add(page["site_name"])
    label = _host_label(source_url) if source_url else ""
    if len(label) >= 4:
        names.add(label)
    return sorted(names)


# ------------------------------------------------------------------ the record

HEADS = ("SECTIONS AS READ", "PAGE FURNITURE", "SOURCE DEFECTS")
STRIP_NAMES = ("STRIP",)
STRIP_KEYS = ("furniture_words", "defects", "names", "figures")


def strip_block(record):
    """The STRIP block → {"furniture_words", "defects": [{id, quote, meant}],
    "names", "figures"}. Read tolerantly (slots.json_slot)."""
    got = S.json_slot(record, STRIP_NAMES, STRIP_KEYS)

    def words(k):
        return [str(w).strip() for w in got.get(k) or [] if str(w).strip()]
    defects = [d for d in got.get("defects") or [] if isinstance(d, dict) and d.get("quote")]
    return {"furniture_words": words("furniture_words"), "defects": defects,
            "names": words("names"), "figures": words("figures")}


def _part(record, name, stop=HEADS + ("STRIP",)):
    m = S.heading(name).search(record or "")
    if not m:
        return None
    end = len(record)
    for other in stop:
        if other == name:
            continue
        for n in S.heading(other).finditer(record, m.end()):
            end = min(end, n.start())
            break
    return m.start(), m.end(), end


def section_ids(record):
    """S1, S2, … as the record numbered them, in order."""
    span = _part(record, "SECTIONS AS READ")
    body = record[span[1]:span[2]] if span else (record or "")
    ids = re.findall(r"^[ \t>#*\-]*\**\[?(S\d+)\b", body, re.M) or re.findall(r"\b(S\d+)\b", body)
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def record_problems(record):
    """The read step's answer must arrive in its labelled parts."""
    out = [f"the record has no `# {h}` heading" for h in HEADS if not S.heading(h).search(record or "")]
    try:
        strip_block(record)
    except ValueError as e:
        out.append(str(e))
    if not out and not section_ids(record):
        out.append("the record numbers no sections (`S1`, `S2`, …) under SECTIONS AS READ — nothing can be labelled")
    return out


def sections_only(record):
    """The record without its PAGE FURNITURE section and without the STRIP
    block: furniture is named by number only, never by its words."""
    rec = record or ""
    strip = _part(rec, "STRIP", stop=())
    if strip:
        rec = rec[:strip[0]]
    rec = re.sub(r"```[ \t]*STRIP[ \t]*\n.*?```", "", rec, flags=re.S | re.I)
    span = _part(rec, "PAGE FURNITURE")
    if not span:
        return rec.strip() + "\n"
    ids = sorted(set(re.findall(r"\bF\d+\b", rec[span[0]:span[2]])), key=lambda x: int(x[1:]))
    note = ("# PAGE FURNITURE\n\n(Taken out by the code before this step. Items set aside: "
            + (", ".join(ids) or "none numbered") + ". Their words are withheld on purpose — "
            "nothing in them is part of what this page argues.)\n\n")
    return (rec[:span[0]] + note + rec[span[2]:]).strip() + "\n"


# ------------------------------------------------------------------ the construct

NEEDS = ("THE MOVES", "THE SEQUENCE LOGIC", "LOAD-BEARING")
LEFT_OUT = re.compile(r"^[ \t]*(?:#{1,6}[ \t]*)?\**[ \t]*LEFT OUT\b", re.M | re.I)


def _named(name, low_body, body, any_case=False):
    """A name of two or more words — or one the code itself knows is a name (the
    run's brand, the site) — is matched whatever its case. A one-word name the
    read step listed is matched as a proper noun (as written, Capitalised or in
    CAPITALS), because a product's name is often an ordinary word in lower case."""
    if any_case or len(name.split()) >= 2:
        return re.search(rf"(?<!\w){re.escape(name.lower())}(?!\w)", low_body) is not None
    forms = {name, name.upper(), name.capitalize()} - {name.lower()}
    return any(re.search(rf"(?<!\w){re.escape(f)}(?!\w)", body) for f in forms)


def construct_problems(construct, strip, names=()):
    """What the finished construct may not carry. `names` are the ones the code
    found for itself (the site's name, the address, the run's own brand)."""
    text = construct or ""
    cut = LEFT_OUT.search(text)
    body = text[:cut.start()] if cut else text
    low = body.lower()
    out = []
    for m in sorted({m.group(0).strip() for m in MONEY.finditer(body)}):
        out.append(f"the construct carries a money figure: “{m}” — a teardown's construct carries no real figure, "
                   f"only a slot for one")
    for fig in strip.get("figures", []):
        if len(fig) >= 2 and re.search(r"\d", fig) and fig.lower() in low and not MONEY.search(fig):
            out.append(f"the construct carries one of the source's own figures: “{fig}”")
    known = {re.sub(r"[™®©]", "", n).strip().lower() for n in names}
    for n in sorted({re.sub(r"[™®©]", "", n).strip() for n in list(strip.get("names", [])) + list(names)}):
        if len(n) >= 3 and _named(n, low, body, any_case=n.lower() in known):
            out.append(f"the construct names the source or a brand: “{n}”")
    for p in sorted({w.lower() for w in strip.get("furniture_words", []) if len(w.split()) >= 2}):
        if re.search(rf"(?<!\w){re.escape(p)}(?!\w)", low):
            out.append(f"the construct carries page-furniture words: “{p}”")
    for noun in FRAME_NOUNS:
        if re.search(rf"(?<!\w){re.escape(noun)}(?!\w)", low):
            out.append(f"the construct names the site's frame: “{noun}”")
    for d in strip.get("defects", []):
        q = str(d.get("quote") or "").strip()
        if len(q) >= 6 and q.lower() in low:
            out.append(f"the construct carries a source defect ({d.get('id', 'D?')}): “{q[:80]}”")
    tag = MERGE.search(body)
    if tag:
        out.append("the construct carries a template tag as code: " + tag.group(0)[:60])
    for need in NEEDS:
        if need.lower() not in text.lower():
            out.append(f"the construct has no `{need}` part")
    if not cut:
        out.append("the construct does not end on its `LEFT OUT:` line")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scan", "lines"])
    ap.add_argument("source")
    ap.add_argument("--brand", help="the brand the run would file under — there is no default")
    a = ap.parse_args()
    pg = load(a.source)
    if a.cmd == "lines":
        print(numbered(pg["text"]), end="")
    else:
        print(f"{pg['kind']}: {pg['raw_chars']:,} chars on file → {len(pg['text']):,} chars as read\n")
        print(findings_text(scan(pg)))
