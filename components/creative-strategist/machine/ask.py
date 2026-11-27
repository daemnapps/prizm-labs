#!/usr/bin/env python3
"""ask — write or check a creative strategist ask record (link 00 of the ad workflow).

    ask.py new   --brand B --ask LABEL --product P --avatar A --said "..." --funnel "..."
                 [--sub-avatar S] [--moment KEY] [--window "YYYY-MM-DD to YYYY-MM-DD ..."] [--offer-section KEY] [--offer-line L]...
                 [--never N]... [--moment-line L]... [--count NAME=N]... [--maker ROLE=NAME]...
                 [--asked YYYY-MM-DD] [--out DIR] [--force]
    ask.py check PATH

`new` turns the person's sentence into `runs/creative-strategist/<brand>/<ask>/ask.json`: the one
record every later link reads (image-writing --ask, copywriter brief_words, video-writing --ask,
promo-calendar). Whatever the person did not say is looked up in the brand folder, never invented:
the offer lines from the offer bank's section for the moment (else the product), the moment's window
from strategy/moments.json. A fact it cannot find is left empty and reported. Brand-agnostic.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "brandpath"))
import brandpath  # noqa: E402

REQUIRED = ("brand", "product", "avatar", "asked", "ask", "said", "funnel", "offer")


def _sections(lines):
    out, cur = [], None
    for i, l in enumerate(lines, 1):
        if l.startswith("## ") or l.startswith("### "):
            if cur:
                out.append(cur)
            head = l.lstrip("#").strip()
            cur = {"key": re.split(r"\s+[—-]\s+", head)[0].strip().lower(), "start": i, "lines": []}
        elif cur is not None:
            cur["lines"].append(l)
    if cur:
        out.append(cur)
    return out


def _quoted(s):
    return [a or b for a, b in re.findall(r'"([^"]+)"|“([^”]+)”', s)]


def bank_lines(text, key, moment=None):
    """The offer bank's own lines for a section key: the "word for word" list, else the
    sentence naming the moment, else the section's bold funnel-offer line. [] when none."""
    secs = _sections(text.split("\n"))
    for sec in secs:
        if sec["key"] != key:
            continue
        body = " ".join(x.strip() for x in sec["lines"])
        m = re.search(r"word for word:[^(]*\(([^)]*)\)", body)
        if m and _quoted(m.group(1)):
            return _quoted(m.group(1))
        if moment:
            name = moment.replace("-", " ")
            for x in sec["lines"]:
                # only a sentence that names the moment AND calls the quote a line ("... use the same line: "..."")
                m = re.search(r'\bline\b[^"“]*[:\s]["“]([^"”]+)["”]', x[x.lower().index(name):]) \
                    if name in x.lower() else None
                if m:
                    return [m.group(1)]
        for x in sec["lines"]:
            m = re.search(r"Funnel offer[^:]*: \*\*([^*]+)\*\*", x)
            if m:
                return [m.group(1).strip()]
    return []


def moment_record(path, key):
    d = json.loads(Path(path).read_text())
    hit = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("key") == key and "window" in o:
                hit.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return hit[0] if hit else None


def build(root, a):
    """The ask record and the notes about what could not be found. Writes nothing."""
    root = Path(root)
    brands = root / "brands"
    notes = []
    if not (brands / a["brand"]).is_dir():
        raise SystemExit("refused: no brand folder brands/%s" % a["brand"])

    def at(key, *rest):
        return brandpath.brand_path(a["brand"], key, *rest, root=brands)
    bank = at("products", "offer-bank.md")
    try:
        bank_rel = str(bank.relative_to(root))
    except ValueError:
        bank_rel = str(bank)
    text = bank.read_text() if bank.is_file() else ""
    keys = {s["key"] for s in _sections(text.split("\n"))}
    if a["product"] not in keys:                       # the catalog id names the same product the bank files under its short key
        try:
            sys.path.append(str(Path(__file__).resolve().parents[2] / "naming"))
            import names as _N
            a = dict(a, product=next((k for k in sorted(keys) if _N.product_id(a["brand"], k) == a["product"]), a["product"]))
        except Exception:  # noqa: BLE001 -- an unreadable catalog is the refusal below
            pass
    if a["product"] not in keys:
        raise SystemExit("refused: product %r is not a section of %s" % (a["product"], bank_rel))
    avdir, avjson = at("core-avatars", a["avatar"]), at("core-avatars", "avatars.json")
    if not avdir.exists() and not (avjson.is_file() and a["avatar"] in avjson.read_text()):
        notes.append("avatar %r not found in the brand's core-avatars" % a["avatar"])
    section = a.get("offer_section")
    mom = None
    if a.get("moment") == "evergreen":
        mom = {"window": "always on"}                      # the always-on ask: no dated moment to look up
    elif a.get("moment"):
        mf = at("strategy", "moments.json")
        mom = moment_record(mf, a["moment"]) if mf.is_file() else None
        if not mom:
            raise SystemExit("refused: moment %r is not in the brand's strategy/moments.json" % a["moment"])
        if not section:
            section = a["moment"] if a["moment"] in keys else (mom.get("offer") if mom.get("offer") in keys else a["product"])
    section = section or a["product"]
    lines = list(a.get("offer_line") or []) or bank_lines(text, section, a.get("moment"))
    if not lines and section != a["product"]:
        lines = bank_lines(text, a["product"], a.get("moment"))
        section = a["product"] if lines else section
    if not lines:
        notes.append("no offer lines found in the offer bank section %r; offer.lines is empty" % section)
    flat = " ".join(text.split())
    for l in lines:
        if " ".join(l.split()) not in flat:
            notes.append("offer line not word for word in the offer bank: %r" % l)
    rec = {
        "brand": a["brand"], "product": a["product"], "avatar": a["avatar"],
        "asked": a.get("asked") or date.today().isoformat(), "ask": a["ask"], "said": a["said"],
        "funnel": a["funnel"],
        "offer": {"bank": "%s#%s" % (bank_rel, section), "lines": lines,
                  "never": list(a.get("never") or [])},
    }
    if a.get("sub_avatar"):
        rec["sub_avatar"] = a["sub_avatar"]
    if mom:
        win = a.get("window") or mom["window"]
        rec["moment"] = {"key": a["moment"], "window": win, "lines": list(a.get("moment_line") or [])}
        if not re.match(r"\d{4}-\d{2}-\d{2} to \d{4}-\d{2}-\d{2}", win):
            notes.append("moment.window is text, not a dated span; the promo calendar reads dates: pass --window")
        if not rec["moment"]["lines"]:
            notes.append("moment.lines is empty: pass --moment-line for the words the ads carry (e.g. the deadline)")
    if a.get("count"):
        try:
            rec["count"] = {k: int(v) for k, v in (c.split("=", 1) for c in a["count"])}
        except ValueError:
            raise SystemExit("refused: --count takes NAME=INTEGER, e.g. static_concepts=5")
    if a.get("maker"):
        if any("=" not in m for m in a["maker"]):
            raise SystemExit("refused: --maker takes ROLE=NAME, e.g. statics=editor")
        rec["makers"] = dict(m.split("=", 1) for m in a["maker"])
    return rec, notes


def check(rec):
    """Problems with an ask record, by what the readers need. [] when it is readable."""
    bad = []
    for k in REQUIRED:
        if k not in rec:
            bad.append("missing %s" % k)
    off = rec.get("offer")
    if not isinstance(off, dict):
        bad.append("offer is not an object")
    else:
        for k in ("lines", "never"):
            if not isinstance(off.get(k), list):
                bad.append("offer.%s is not a list" % k)
    if "moment" in rec:
        m = rec["moment"]
        if not isinstance(m, dict) or not m.get("key"):
            bad.append("moment has no key")
        elif not isinstance(m.get("lines", []), list):
            bad.append("moment.lines is not a list")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--brand", required=True)
    n.add_argument("--ask", required=True)
    n.add_argument("--product", required=True)
    n.add_argument("--profile", help="the person it is for: <avatar>[_<sub>][_<demographic>] (naming/PEOPLE.md); replaces --avatar/--sub-avatar")
    n.add_argument("--avatar")
    n.add_argument("--sub-avatar", dest="sub_avatar")
    n.add_argument("--said", required=True)
    n.add_argument("--funnel", required=True)
    n.add_argument("--moment")
    n.add_argument("--window", help="the dated window the ads run in; default is the moment's own window text")
    n.add_argument("--offer-section", dest="offer_section")
    n.add_argument("--offer-line", dest="offer_line", action="append")
    n.add_argument("--never", action="append")
    n.add_argument("--moment-line", dest="moment_line", action="append")
    n.add_argument("--count", action="append")
    n.add_argument("--maker", action="append")
    n.add_argument("--asked")
    n.add_argument("--out")
    n.add_argument("--force", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("path")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        bad = check(json.loads(Path(a.path).read_text()))
        print("\n".join(bad) or "ok")
        return 1 if bad else 0
    root = brandpath.repo()
    pid = ""
    if a.profile:                                            # a person is a profile (naming/PEOPLE.md); the folders keep their own names
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "naming"))
        import people
        a.avatar, sub, demo = people.folders(a.brand, a.profile)
        a.sub_avatar = sub or a.sub_avatar
        pid = people.profile(a.brand, a.avatar, a.sub_avatar or "", demo)["id"]
    if not a.avatar:
        raise SystemExit("refused: --profile (or --avatar) says who it is for")
    rec, notes = build(root, vars(a))
    if pid:
        rec["profile"] = pid
    bad = check(rec)
    if bad:
        raise SystemExit("refused: " + "; ".join(bad))
    build_rec = rec
    d = Path(a.out) if a.out else root / "runs" / "creative-strategist" / a.brand / a.ask
    f = d / "ask.json"
    if f.exists() and not a.force:
        raise SystemExit("refused: %s exists; pass --force to replace it" % f)
    d.mkdir(parents=True, exist_ok=True)
    indent = 1
    if f.exists():
        # a replaced ask keeps what later links wrote into it (gates, swipes, evidence, page, ...),
        # its key order and its indent, so only the values that changed show in a diff
        raw = f.read_text()
        old = json.loads(raw)
        second = raw.split("\n")[1] if raw.count("\n") > 1 else ""
        indent = len(second) - len(second.lstrip()) or 1
        rec = dict((k, rec.get(k, old.get(k))) for k in old if k in rec or k in old)
        rec.update((k, v) for k, v in build_rec.items() if k not in rec)
    f.write_text(json.dumps(rec, indent=indent, ensure_ascii=False) + "\n")
    print("ask written: %s" % f)
    for x in notes:
        print("note: %s" % x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
