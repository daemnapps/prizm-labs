#!/usr/bin/env python3
"""Check an ad-series ledger against the checks in format.json (FORMAT.md, "The ledger"), L1 to L8.

    python3 components/video-production/formats/ad-series/series_check.py <ledger.json> [--json]

Prints one line per finding, `FAIL Lx ...`, and exits 1 when any FAIL is found. No model, no network, stdlib only;
runs on Python 3.9.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
# the creator brief's header line (components/briefs/creator-brief/creator-brief-v1-owner.md, OUTPUT): its last field
ASK_LINE = re.compile(r"^\*\*Format:\*\*.*\*\*Ask:\*\*\s*(.*?)\s*$", re.M)
HOME = HERE / ("format.json" if (HERE / "format.json").is_file() else "format.draft.json")
KINDS = ("arc", "carried", "cast", "setups", "rules", "proof")


def spec():
    return json.loads(HOME.read_text())["series"]


def _same(a, b):
    def n(s):
        return " ".join(str(s or "").replace("\u2019", "'").split())
    return n(a) == n(b)


def _creator_ask(path, base):
    """The Ask a creator brief's header names; None when the file or the field is missing."""
    p = Path(path)
    for f in ([p] if p.is_absolute() else [Path(base or ".") / p, ROOT / p]):
        if f.is_file():
            m = ASK_LINE.search(f.read_text()[:600])
            return m.group(1) if m else None
    return None


def _brief_text(path, base):
    """A filed brief's text (an arc row's `brief_file`), or None when the file is not there."""
    p = Path(str(path)).expanduser()
    for f in ([p] if p.is_absolute() else [Path(base or ".") / p, ROOT / p]):
        if f.is_file():
            return f.read_text()
    return None


def _said(line):
    """A setup's own words, without a bracketed note, for matching against a brief: lower case, one space."""
    s = re.sub(r"\([^)]*\)", " ", str(line or "")).replace("\u2019", "'").lower()
    return " ".join(re.findall(r"[a-z0-9']+", s))


def check(ledger, base=None):
    """[(code, message)] for every failed check; an empty list is a pass. `base` is the ledger's folder, against
    which an arc row's `creator_brief` path is read (else the repo root)."""
    s = spec()
    out = []
    missing = [k for k in KINDS if not isinstance(ledger.get(k), list)]
    if missing:
        return [("L0", "ledger lacks list(s): %s" % ", ".join(missing))]
    arc = {a.get("ad"): a for a in ledger["arc"]}
    ads = sorted(a for a in arc if isinstance(a, int))
    # the last ad written; planned ads past it are not due yet
    last = ledger["current"] if isinstance(ledger.get("current"), int) else (max(ads) if ads else 0)
    # L5 the arc card's first three ads, each with its task
    for n in range(1, s["ads_min"] + 1):
        if n not in arc or not str(arc[n].get("task") or "").strip():
            out.append(("L5", "arc has no task for ad %d" % n))
    # L6 every ad carries an ask
    for n in ads:
        if not str(arc[n].get("ask") or "").strip():
            out.append(("L6", "ad %d has no ask" % n))
    # L7 a creator brief written for an ad asks the ledger's ask for that ad, word for word
    for n in ads:
        cb = arc[n].get("creator_brief")
        if not cb:
            continue
        said = _creator_ask(cb, base)
        if said is None:
            out.append(("L7", "ad %d names creator brief %s, which is missing or has no Ask in its header" % (n, cb)))
        elif not _same(said, arc[n].get("ask")):
            out.append(("L7", "ad %d: the creator brief asks %r, the ledger asks %r" % (n, said, arc[n].get("ask"))))
    # L8 a setup the filed brief of an ad already says is planted no later than that ad (round 3, 2026-11-07)
    for n in ads:
        bf = arc[n].get("brief_file")
        if not bf:
            continue
        text = _brief_text(bf, base)
        if text is None:
            out.append(("L8", "ad %d names brief file %s, which is missing" % (n, bf)))
            continue
        said = " ".join(re.findall(r"[a-z0-9']+", text.replace("\u2019", "'").lower()))
        for f in ledger["setups"]:
            words = _said(f.get("setup"))
            if words and words in said and isinstance(f.get("planted"), int) and f["planted"] > n:
                out.append(("L8", "setup %s is said in ad %d's brief but is planted in ad %d" % (f.get("id"), n, f["planted"])))
    # L1 a setup still planted one ad past its due ad (only once the series has reached that ad)
    statuses = s["ledger"]["kinds"]["setups"]["statuses"]
    for f in ledger["setups"]:
        st = f.get("status")
        if st not in statuses:
            out.append(("L1", "setup %s has status %r; use one of %s" % (f.get("id"), st, ", ".join(statuses))))
        elif st == "planted" and isinstance(f.get("due"), int) and last > f["due"]:
            out.append(("L1", "setup %s was due by ad %d and is still planted" % (f.get("id"), f["due"])))
        elif st == "paid" and not isinstance(f.get("paid"), int):
            out.append(("L1", "setup %s is paid but names no ad" % f.get("id")))
    # L2 a cast member marked out appears in a later ad
    for p in ledger["cast"]:
        if p.get("state") == "out":
            gone = p.get("out_after")
            if not isinstance(gone, int):
                out.append(("L2", "cast %s is out but names no out_after ad" % p.get("id")))
            elif any(a > gone for a in p.get("ads") or []):
                out.append(("L2", "cast %s is out after ad %d but appears in ad %d"
                            % (p.get("id"), gone, max(p.get("ads")))))
    # L3 every carried item, person and rule names a source
    for kind in ("carried", "cast", "rules"):
        for row in ledger[kind]:
            if not str(row.get("source") or "").strip():
                out.append(("L3", "%s %s names no source" % (kind, row.get("id"))))
    # L4 the same main proof type in two adjacent ads
    types = s["ledger"]["kinds"]["proof"]["types"]
    by_ad = {}
    for p in ledger["proof"]:
        if p.get("type") not in types:
            out.append(("L4", "ad %s proof type %r is not one of %s" % (p.get("ad"), p.get("type"), ", ".join(types))))
        by_ad[p.get("ad")] = p.get("type")
    for n in ads:
        if n not in by_ad:
            out.append(("L4", "ad %d has no main proof" % n))
        elif by_ad.get(n + 1) == by_ad[n]:
            out.append(("L4", "ads %d and %d both lean on %s" % (n, n + 1, by_ad[n])))
    return out


def hot(ledger, ad):
    """The rows the writer reads before ad `ad`: open setups and everything active in the last hot_window ads."""
    w = spec()["ledger"]["hot_window"]
    near = set(range(max(1, ad - w), ad))

    def live(row):
        return bool(near & set(row.get("ads") or [])) and row.get("state") != "out"
    return {
        "carried": [r for r in ledger["carried"] if live(r)],
        "cast": [r for r in ledger["cast"] if live(r)],
        "rules": ledger["rules"],
        "setups": [f for f in ledger["setups"] if f.get("status") == "planted"],
        "proof": [p for p in ledger["proof"] if p.get("ad") in near],
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__.strip())
        return 2
    ledger = json.loads(Path(args[0]).read_text())
    found = check(ledger, Path(args[0]).resolve().parent)
    if "--json" in args:
        print(json.dumps([{"check": c, "message": m} for c, m in found], indent=1))
    else:
        for c, m in found:
            print("FAIL %s %s" % (c, m))
        if not found:
            print("pass: %d ads, %d setups, %d carried, %d cast" % (
                len(ledger["arc"]), len(ledger["setups"]), len(ledger["carried"]), len(ledger["cast"])))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
