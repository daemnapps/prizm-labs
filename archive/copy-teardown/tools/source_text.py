#!/usr/bin/env python3
"""The words a teardown is handed, and what the code can do with them for free
— before the model reads them and after it answers.

    source_text.py scan <source file or "-">     print what the code finds

Five jobs, none of which spends anything:

  load()               the source as words. A plain `.md`/`.txt` file is read
                       as it stands; a saved swipe card that keeps its copy
                       under `## Headline` / `## Primary text` headings has
                       those parts lifted out and the card's own notes left
                       behind; `-` is text piped in.
  not_words_only()     why a source is NOT for this tool — a page, an email, a
                       picture, a video each have their own teardown.
  scan()               names the code can see without a model (handles,
                       hashtags, web addresses), prices, and damage (a merge
                       tag showing as code, a hidden character).
  block() / heads      the read step's answer, parsed the way a model actually
                       writes it: a tagged fence, or a `# SLOT` heading over a
                       plain or ```json fence, or a bare JSON object.
  for_later_steps()    the record with the source's own names swapped for
                       numbered markers — the construct step is never shown a
                       name, so it cannot carry one.

No brand's words are typed here. What counts as a name comes from the source
itself (the read step's list plus the scan) and from the folder names under
`brands/`, read at run time.
"""
import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402

WORDS = {".md", ".txt", ".text", ".markdown", ""}
ELSEWHERE = {
    "page teardown": {".html", ".htm", ".mhtml", ".pdf"},
    "image teardown": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic"},
    "video teardown": {".mp4", ".mov", ".webm", ".m4v", ".mkv"},
}
PART_HEAD = re.compile(r"^##\s+(headline|primary text|description|caption|body|post|hook|headlines)\b.*$", re.I | re.M)
ANY_H2 = re.compile(r"^##\s+", re.M)

HANDLE = re.compile(r"(?<![\w@])@[A-Za-z0-9_.]{2,}")
HASHTAG = re.compile(r"(?<![\w#&])#[A-Za-z][\w]+")
WEB = re.compile(r"(?:https?://|www\.)[^\s)>\]\"']+|\b(?:[a-z0-9][a-z0-9-]*\.)+(?:com|co|net|org|io|shop|store|us|uk|ca|au|de)\b(?:/[^\s)>\]\"']*)?", re.I)
MERGE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\*\|[A-Z_:]+\|\*|%%[A-Za-z_]+%%")
HIDDEN = re.compile("[​‌‍⁠﻿]")
MARKER = re.compile(r"\[SOURCE NAME \d+\]")


# ------------------------------------------------------------------ the source

def load(source, piped=None):
    """(the words, how they were taken). `source` is a path, or "-" with the
    piped text handed in."""
    if source == "-":
        return (piped or "").strip() + "\n", "text piped in"
    text = Path(source).read_text(errors="replace")
    heads = list(PART_HEAD.finditer(text))
    if not heads:
        return text.strip() + "\n", "the file as it stands"
    parts = []
    for m in heads:
        nxt = ANY_H2.search(text, m.end())
        body = text[m.end():nxt.start() if nxt else len(text)]
        lines = [re.sub(r"^\s*>\s?", "", l).rstrip() for l in body.strip().splitlines()]
        words = "\n".join(lines).strip()
        if words:
            parts.append(f"{m.group(1).upper()}:\n{words}")
    if not parts:
        return text.strip() + "\n", "the file as it stands"
    return "\n\n".join(parts) + "\n", ("the copy parts of a saved swipe card ("
                                         + ", ".join(m.group(1).lower() for m in heads) + ") — the card's own notes left out")


def not_words_only(source, text):
    """Why this source belongs to another teardown. Empty when it is words."""
    out = []
    if source != "-":
        suffix = Path(source).suffix.lower()
        for where, suffixes in ELSEWHERE.items():
            if suffix in suffixes:
                out.append(f"`{suffix}` is not words only — that source goes to {where}")
        if suffix not in WORDS and not out:
            out.append(f"`{suffix}` is not a words file — hand this tool a .md or .txt file, or pipe the text in with `-`")
    if re.search(r"\[IMAGE alt=", text or ""):
        out.append("the source carries pictures (`[IMAGE alt=…]` lines) — an email goes to email teardown")
    if re.search(r"<(?:html|body|img|table|div)\b", text or "", re.I):
        out.append("the source is page markup, not words — a page goes to page teardown, an email to email teardown")
    return out


def scan(text):
    """{names: [{kind, quote}], prices: [...], defects: [{line, kind, quote}]}"""
    names, seen, defects = [], set(), []
    for kind, rx in (("handle", HANDLE), ("hashtag", HASHTAG), ("web address", WEB)):
        for q in rx.findall(text or ""):
            q = q.rstrip(".,;:!?")
            if q.lower() not in seen:
                seen.add(q.lower())
                names.append({"kind": kind, "quote": q})
    for n, line in enumerate((text or "").splitlines(), 1):
        for tag in MERGE.findall(line):
            defects.append({"line": n, "kind": "merge tag showing as code", "quote": tag})
        if HIDDEN.search(line) and HIDDEN.sub("", line).strip():
            defects.append({"line": n, "kind": "hidden character inside a line", "quote": HIDDEN.sub("", line).strip()[:80]})
    return {"names": names, "prices": sorted(_quality().prices_in(text)), "defects": defects}


def findings_text(found):
    """The scan, as the read step is handed it."""
    out = ["Names the code already found (kind · quoted):"]
    out += [f"- {n['kind']} · {n['quote']}" for n in found["names"]] or ["- none found by the code"]
    out += ["", "Prices the code already found: " + (", ".join("$" + p for p in found["prices"]) or "none")]
    out += ["", "Damage the code already found (line · kind · quoted):"]
    out += [f"- {d['line']} · {d['kind']} · {d['quote']}" for d in found["defects"]] or ["- none found by the code"]
    return "\n".join(out)


def _quality():
    if str(P.QUALITY) not in sys.path:
        sys.path.append(str(P.QUALITY))
    import quality_checks as Q
    return Q


# ------------------------------------------------------------------ reading an answer

def _head(name):
    """A slot heading the way a model writes one: `# NAME`, `### NAME:`,
    `**NAME**`, `## **NAME**` — on its own line."""
    n = re.escape(name)
    return re.compile(rf"^[ \t]*(?:#{{1,4}}[ \t]*\**|\*\*)[ \t]*{n}[ \t]*:?[ \t]*\**[ \t]*:?[ \t]*$", re.M | re.I)


def _json_object(s):
    try:
        got = json.loads(s)
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


def block(text, tag, aliases=(), keys=()):
    """The JSON object a slot carries, however the model fenced it:
      1. a fence tagged with the slot's name        ```STRIP
      2. the slot's heading over a plain/json fence  # STRIP … ``` or ```json
      3. any fence, or a bare {…}, holding one of `keys`
    Raises ValueError saying what is wrong."""
    text = text or ""
    m = re.search(rf"```[ \t]*{re.escape(tag)}[ \t]*\n(.*?)```", text, re.S | re.I)
    body = m.group(1) if m else None
    if body is None:
        for name in (tag, *aliases):
            h = _head(name).search(text)
            if h:
                f = re.search(r"```[ \t]*\w*[ \t]*\n(.*?)```", text[h.end():], re.S)
                if f:
                    body = f.group(1)
                    break
    if body is None and keys:
        tries = [f.group(1) for f in re.finditer(r"```[ \t]*\w*[ \t]*\n(.*?)```", text, re.S)]
        a, b = text.find("{"), text.rfind("}")
        if 0 <= a < b:
            tries.append(text[a:b + 1])
        for t in tries:
            got = _json_object(t)
            if got is not None and set(got) & set(keys):
                return got
    if body is None:
        raise ValueError(f"the answer carries no {tag} block")
    got = _json_object(body.strip())
    if got is None:
        raise ValueError(f"the {tag} block is not a valid JSON object")
    return got


HEADS = ("THE COPY AS READ", "SOURCE NAMES", "SOURCE DEFECTS")


def strip_block(record):
    """→ {"names": [...], "defects": [{id, quote, meant}]}"""
    got = block(record, "STRIP", keys=("names", "defects"))
    names = [str(w).strip() for w in got.get("names") or [] if str(w).strip()]
    defects = [d for d in got.get("defects") or [] if isinstance(d, dict) and d.get("quote")]
    return {"names": names, "defects": defects}


def record_problems(record):
    """The read step's answer must arrive in its labelled parts."""
    out = [f"the record has no `# {h}` heading" for h in HEADS if not _head(h).search(record or "")]
    try:
        strip_block(record)
    except ValueError as e:
        out.append(str(e))
    return out


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')).lower()


def not_in_source(names, source):
    """Names the record lists that the source does not hold — a note, not a hold."""
    src = _norm(source)
    return [n for n in names if _norm(n) not in src]


def all_names(strip, found):
    """Every name to withhold: the record's list plus what the scan saw."""
    out, seen = [], set()
    for n in list(strip.get("names", [])) + [x["quote"] for x in found.get("names", [])]:
        n = n.strip()
        if len(n) >= 3 and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def _name_rx(name):
    """A several-word name is swept whatever its case. A one-word name is an
    ordinary English word half the time ("Glow", "Flex"), so it is swept as
    written and Capitalised only."""
    esc = re.escape(name)
    if len(name.split()) >= 2 or not name.isalpha():
        return re.compile(rf"(?<!\w){esc}(?!\w)", re.I)
    forms = {name, name.capitalize(), name.upper()}
    return re.compile(r"(?<!\w)(?:" + "|".join(sorted(map(re.escape, forms), key=len, reverse=True)) + r")(?!\w)")


def for_later_steps(record, names):
    """The record as the labelling and construct steps see it: no SOURCE NAMES
    section, no STRIP block, and every name swapped for `[SOURCE NAME n]`."""
    rec = record or ""
    h = _head("STRIP").search(rec)
    if h:
        rec = rec[:h.start()]
    rec = re.sub(r"```[ \t]*STRIP[ \t]*\n.*?```", "", rec, flags=re.S | re.I)
    m = _head("SOURCE NAMES").search(rec)
    if m:
        nxt = _head("SOURCE DEFECTS").search(rec, m.end())
        end = nxt.start() if nxt else len(rec)
        note = (f"# SOURCE NAMES\n\n(Taken out by the code before this step: {len(names)} name(s) particular to the "
                "source — its brand, products, people, places, handles. Each is shown below only as a numbered "
                "marker, `[SOURCE NAME n]`. The names are withheld on purpose — none of them is part of how this "
                "copy argues.)\n\n")
        rec = rec[:m.start()] + note + rec[end:]
    order = sorted(enumerate(names, 1), key=lambda p: len(p[1]), reverse=True)     # longest first
    for n, name in order:
        rec = _name_rx(name).sub(f"[SOURCE NAME {n}]", rec)
    return rec.strip() + "\n"


# ------------------------------------------------------------------ the construct

NEEDS = ("THE MOVES", "THE SEQUENCE LOGIC", "LOAD-BEARING")


def construct_problems(construct, strip, found, source):
    """What the finished construct may not carry."""
    text = construct or ""
    body = re.split(r"^[ \t]*\**[ \t]*LEFT OUT[ \t]*:?", text, flags=re.M | re.I)[0]
    low = body.lower()
    out = []
    for name in all_names(strip, found):
        if _name_rx(name).search(body):
            out.append(f"the construct carries a name from the source: “{name}”")
    for b in P.known_brands():
        if re.search(rf"(?<![a-z]){re.escape(b.lower())}(?![a-z])", low):
            out.append(f"the construct names a brand: “{b}” — a construct is for any brand")
    if MARKER.search(body):
        out.append("the construct carries a `[SOURCE NAME n]` marker — a withheld name was given a place in it")
    Q = _quality()
    carried = sorted(Q.prices_in(body) & Q.prices_in(source))
    if carried:
        out.append("the construct carries a price from the source: " + ", ".join("$" + p for p in carried))
    for rx, what in ((HANDLE, "a handle"), (WEB, "a web address"), (HASHTAG, "a hashtag")):
        m = rx.search(body)
        if m:
            out.append(f"the construct carries {what}: {m.group(0)[:60]}")
    for d in strip.get("defects", []):
        q = str(d.get("quote") or "").strip()
        if len(q) >= 6 and q.lower() in low:
            out.append(f"the construct carries a source defect ({d.get('id', 'D?')}): “{q[:80]}”")
    tag = MERGE.search(body)
    if tag:
        out.append("the construct carries a merge tag as code: " + tag.group(0)[:60])
    for need in NEEDS:
        if need not in text.upper():
            out.append(f"the construct has no `{need}` part")
    if not re.search(r"^[ \t]*\**[ \t]*LEFT OUT[ \t]*:?", text, re.M | re.I):
        out.append("the construct does not end on its `LEFT OUT:` line")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scan"])
    ap.add_argument("source")
    a = ap.parse_args()
    words, how = load(a.source, sys.stdin.read() if a.source == "-" else None)
    print(f"taken as: {how} · {len(words):,} chars")
    for p in not_words_only(a.source, words):
        print("NOT FOR THIS TOOL:", p)
    print(findings_text(scan(words)))
