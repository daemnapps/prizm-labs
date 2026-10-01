#!/usr/bin/env python3
"""The five headline variations stage 4 wrote for a brief, as data.

    headline_sets.py --brand <brand>                 every brief
    headline_sets.py --brand <brand> --briefs p158   just these
    headline_sets.py --brand <brand> --json          for a runner

Damon, 2026-09-23: *"body scrub ads are still pumping for us right now, I
want you to bulk the variation briefs for each of these ads so I can load
them in the account."* Stage 4 already wrote five headline variations per
brief, each measured against the layout's character ceiling — that is the
fuel for a headline swap off the winning draft (`image-variation`). It was
never machine-readable, because stage 4 is a writing prompt and every run
laid its variations out slightly differently.

**Six shapes, one meaning.** Across twenty-one <brand> briefs stage 4 wrote
the same thing six ways — a fenced block, a line table, `- Line 1: "…"`,
`- Zone A: "…"`, a bold slash-separated string, `**Line:** …`, or only a
quoted title in the heading. They are read in order of how much they can be
trusted: a table of lines beats a bold string, because the table is the one
stage 4 counts characters against.

Nothing here rewrites a headline. A brief whose stage 4 wrote no variations
(a text-free ad) returns an empty list, which is an answer: that ad's
variations are pictures, not words, and they are not this tool's to invent.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import briefs as B

HEAD = re.compile(r"^[#*\s]*(?:Version|Variation)\s*(\d+)\b(.*)$", re.I | re.M)
QUOTE = "\"'“”‘’"
# Only double quotes DELIMIT a headline. An apostrophe inside one ("Don't
# try") is part of the words, and a class that includes it cuts the line at
# the apostrophe — p161 came back as "Don" (2026-09-23).
DELIM = "\"\u201c\u201d"


def _clean(s):
    return s.strip().strip(QUOTE).strip()


def _split(s):
    """A one-line headline written with its line breaks as slashes or \\n."""
    return [_clean(x) for x in re.split(r"\s*/\s*|\\n|\n", s) if _clean(x)]


def lines_from(block, tail):
    """One variation's headline lines, whichever way stage 4 wrote them."""
    m = re.search(r"```\n(.*?)\n```", block, re.S)
    if m:
        return [_clean(l) for l in m.group(1).strip().split("\n") if l.strip()]

    # the line table — stage 4 counts characters against this one, so it is
    # the most trustworthy shape. Only a table whose header names the lines.
    for tbl in re.finditer(r"^\|\s*(?:Line|#)\s*\|.*?\n(?:\|[-: |]+\|\n)((?:\|.*\n)+)",
                           block, re.M | re.I):
        rows = re.findall(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|", tbl.group(1), re.M)
        if rows:
            return [_clean(t) for t in rows]

    q = re.findall(r"^\s*[-*]\s*(?:Line \d+|Zone [A-Z]):\s*[%s](.+?)[%s]" % (DELIM, DELIM),
                   block, re.M)
    if q:
        return [_clean(x) for x in q]

    m = re.search(r"^\*\*(.+?)\*\*", block.strip(), re.M | re.S)   # bold, quoted or not
    if m and len(m.group(1)) < 200 and not m.group(1).lower().startswith(("character", "image", "line:")):
        return _split(m.group(1))

    m = re.search(r"^\*\*Line:\*\*\s*(.+)$", block, re.M)
    if m:
        return [_clean(m.group(1))]

    t = re.search(r"[%s](.+?)[%s]" % (DELIM, DELIM), tail or "")
    return [_clean(t.group(1))] if t else []


def for_brief(rec):
    """The five, in stage 4's own order. [] when the ad carries no headline."""
    f = P.RUNS / rec["run"] / "out/04-headlines.md"
    if not f.is_file():
        return []
    t = f.read_text()
    i = t.upper().find("THE FIVE VARIATION")
    seg = t[i:] if i > 0 else t            # never read the control as a variation
    heads = list(HEAD.finditer(seg))
    out = []
    for k, m in enumerate(heads):
        n = int(m.group(1))
        if n == 0 or any(v["n"] == n for v in out):
            continue
        body = seg[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(seg)]
        lines = lines_from(body, m.group(2))
        if lines:
            out.append({"n": n, "lines": lines, "headline": " / ".join(lines)})
    return out[:5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--product")
    ap.add_argument("--briefs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    reg = B.load()
    want = {x.strip() for x in a.briefs.split(",")} if a.briefs else None
    got = {}
    for bid, rec in sorted(reg["briefs"].items()):
        if rec.get("brand") != a.brand or not rec.get("run"):
            continue
        if want and bid not in want:
            continue
        if a.product and rec.get("product") != a.product:
            continue
        got[bid] = for_brief(rec)
    if a.json:
        print(json.dumps(got, indent=1, ensure_ascii=False))
        return
    for bid, vs in got.items():
        print(f"{bid}  {len(vs)}  " + (vs[0]["headline"][:64] if vs else
                                       "— no headline in this ad"))
    n = sum(1 for v in got.values() if v)
    print(f"\n{n} of {len(got)} carry headline variations · "
          f"{sum(len(v) for v in got.values())} variations in all")


if __name__ == "__main__":
    main()
