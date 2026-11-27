#!/usr/bin/env python3
"""Copy library — the words an approver picks from on the approval page, and the log of every change made there.

    python3 copy_library.py <brand>           # print the library's counts and the newest edits
    python3 copy_library.py <brand> --digest  # rebuild the copywriter's digest of approval-page copy edits

Three lists per brand (primary texts, headlines, descriptions), each option with where it came from:
  - winner: the brand's banked winners (runs/winners/<brand>/bank.json), with purchases and cost per purchase
  - live:   the words on cards already approved or live (meta/<brand>/2-approved, 3-live), with how many ads use them
  - edit:   words an approver wrote or kept on the approval page (meta/copy-edits.jsonl), newest first

Every save of a card's words on the approval page writes one line to `Shared Assets/meta/copy-edits.jsonl`:
who, when, which ad, the words before and after, and which library options were picked. Those lines feed the
next batch two ways: the words come back as `edit` options in the library at once, and a digest for the
copywriter is rebuilt at `Shared Assets/meta/learnings/4-brief/<brand>-copy-edits.md` (newest first). The
copywriter's prompt hook (learnings-hooks.json "copywriter") stays OFF until the owner has seen its text.

Never writes into the repo. Reads that fail return empty lists.
"""
import importlib.util, json, os, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KINDS = ("primary", "headlines", "descriptions")
KEEP = 40
_s = importlib.util.spec_from_file_location("meta_learnings_cl", HERE / "learnings.py")
L = importlib.util.module_from_spec(_s)
_s.loader.exec_module(L)


def norm(t):
    return " ".join(str(t or "").split())


def log_path():
    return L.root() / "copy-edits.jsonl"


def read_edits(brand=None):
    try:
        lines = log_path().read_text().splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if not brand or r.get("brand") == brand:
            out.append(r)
    return sorted(out, key=lambda r: r.get("at") or "", reverse=True)


def _winners(brand):
    try:
        bank = json.loads((REPO / "runs" / "winners" / brand / "bank.json").read_text())
    except (OSError, ValueError):
        return []
    rows = bank.get("rows") if isinstance(bank, dict) else bank
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        snaps = r.get("snapshots") or [{}]
        best = max(snaps, key=lambda x: x.get("purchases") or 0)
        out.append({"name": r.get("name"), "primary": r.get("body"), "headline": r.get("headline"),
                    "description": r.get("description"),
                    "purchases": best.get("purchases") or 0, "cpa": best.get("cpa"), "roas": best.get("roas")})
    return sorted(out, key=lambda x: -x["purchases"])


def _card_words(brand):
    """(words, ad name) for every card approved or live."""
    base = L.root() / brand
    for state in ("2-approved", "3-live"):
        d = base / state
        for f in sorted(d.glob("*/*/card.json")) if d.is_dir() else []:
            try:
                c = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            yield c.get("words") or {}, c.get("ad_name")


def library(brand, n=12):
    """{"primary": [...], "headlines": [...], "descriptions": [...]}; each option
    {"id", "text", "from": winner|live|edit, "note", "purchases", "cpa", "uses", "at"}."""
    lib = {k: {} for k in KINDS}

    def add(kind, text, **kw):
        t = str(text or "").strip()
        if not t:
            return
        key = norm(t).lower()
        o = lib[kind].get(key)
        if o is None:
            o = lib[kind][key] = {"text": t, "from": kw.get("src"), "purchases": 0, "cpa": None, "uses": 0, "at": None}
        if kw.get("purchases", 0) > o["purchases"]:
            o.update(purchases=kw["purchases"], cpa=kw.get("cpa"), **{"from": "winner"})
        if kw.get("use"):
            o["uses"] += 1
        if kw.get("at") and (o["at"] or "") < kw["at"]:
            o["at"] = kw["at"]
            if o["from"] != "winner":
                o["from"] = kw.get("src") or o["from"]

    for w in _winners(brand):
        add("primary", w["primary"], src="winner", purchases=w["purchases"], cpa=w["cpa"])
        add("headlines", w["headline"], src="winner", purchases=w["purchases"], cpa=w["cpa"])
        add("descriptions", w.get("description"), src="winner", purchases=w["purchases"], cpa=w["cpa"])
    for words, _ in _card_words(brand):
        for k in KINDS:
            for t in words.get(k) or []:
                add(k, t, src="live", use=True)
    for e in read_edits(brand):
        for k in KINDS:
            for t in (e.get("after") or {}).get(k) or []:
                add(k, t, src="edit", at=e.get("at"))
    out = {}
    for k in KINDS:
        opts = list(lib[k].values())
        for o in opts:
            o["note"] = (f"{o['purchases']:,} sales" + (f" · ${round(o['cpa'])} each" if o.get("cpa") else "")
                         if o["purchases"] else
                         f"your edit · {o['at'][:10]}" if o["from"] == "edit" and o.get("at") else
                         f"on {o['uses']} live ad{'s' if o['uses'] != 1 else ''}")
        winners = sorted([o for o in opts if o["from"] == "winner"], key=lambda o: -o["purchases"])[:n]
        edits = sorted([o for o in opts if o["from"] == "edit"], key=lambda o: o["at"] or "", reverse=True)[:n]
        live = sorted([o for o in opts if o["from"] == "live"], key=lambda o: -o["uses"])[:n]
        out[k] = [dict(o, id=f"{k}-{i}") for i, o in enumerate(winners + edits + live)]
    return out


def log_edit(card, before, after, picked=None, by=None, at=None):
    """One save of a card's words -> one line in copy-edits.jsonl, then the copywriter's digest rebuilt.
    Nothing is written when the words did not change. Returns the line, or None."""
    b = {k: [str(x).strip() for x in (before or {}).get(k) or []] for k in KINDS}
    a = {k: [str(x).strip() for x in (after or {}).get(k) or []] for k in KINDS}
    if all([norm(x) for x in b[k]] == [norm(x) for x in a[k]] for k in KINDS):
        return None
    if L._no_root():
        return None
    row = {"at": at or datetime.now().isoformat(timespec="seconds"), "by": by or "owner", "brand": card.get("brand"),
           "lane": card.get("lane"), "unit": card.get("ad_name"), "brief_id": card.get("brief_id"),
           "product": card.get("product"), "before": b, "after": a, "picked": list(picked or [])}
    p = log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    L.SD.save(p)
    digest(card.get("brand"))
    return row


def change_lines(r):
    """What changed, in words: kept, swapped, added, removed — per kind."""
    out = []
    names = {"primary": "Primary text", "headlines": "Headline", "descriptions": "Description"}
    for k in KINDS:
        bb = [norm(x) for x in r["before"].get(k) or []]
        aa = [norm(x) for x in r["after"].get(k) or []]
        for t in aa:
            if t not in bb:
                out.append(f"  - {names[k]} now: \"{t[:300]}\"")
        for t in bb:
            if t not in aa:
                out.append(f"  - {names[k]} removed: \"{t[:300]}\"")
    return out


def digest(brand):
    """learnings/4-brief/<brand>-copy-edits.md: every approval-page change to an ad's words, newest first."""
    rows = read_edits(brand)[:KEEP]
    if not rows or L._no_root():
        return None
    d = L.root() / "learnings" / L.step_dir(4)
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{brand}-copy-edits.md"
    body = [f"# Copy changes made on the approval page — {brand}", "",
            "Written by components/meta-upload/copy_library.py from every save of an ad's words. "
            f"Newest first, last {KEEP}. What the approver kept, swapped, added or removed before approving.", ""]
    for r in rows:
        body.append(f"- {r['at'][:16].replace('T', ' ')} · {r.get('unit')} · by {r.get('by')}"
                    + (f" · picked {len(r['picked'])} from the library" if r.get("picked") else ""))
        body += change_lines(r)
    tmp = f.with_name("." + f.name + ".tmp")
    tmp.write_text("\n".join(body) + "\n")
    os.replace(tmp, f)
    L.SD.save(f)
    return f


def main(argv):
    if not argv:
        sys.exit(__doc__)
    brand = argv[0]
    if "--digest" in argv:
        print(digest(brand) or "nothing to write")
        return
    lib = library(brand)
    for k in KINDS:
        print(f"{k}: {len(lib[k])} option(s) — " + ", ".join(f"{o['from']}" for o in lib[k][:6]))
    for r in read_edits(brand)[:5]:
        print(r["at"], r.get("unit"))
        print("\n".join(change_lines(r)))


if __name__ == "__main__":
    main(sys.argv[1:])
