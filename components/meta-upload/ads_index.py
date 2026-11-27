#!/usr/bin/env python3
"""THE FINISHED ADS INDEX — one row per brief that reached an approval card: brief → card → live ad.

The same front door as the product index (components/video-production/machine/product_index.py), for finished ads.
The audit that asked for it: components/naming/WHERE-EVERYTHING-GOES-owner.md ("Finished ad → ADS-INDEX.json (brief →
card → live ad)"; a brief with two names in meta/).

Built from, READ ONLY (nothing on the Drive is written, moved or touched):

  Shared Assets/meta/<brand>/<state>/<lane>/<ad name>/card.json   every card, in 1-check · 2-approved · 3-live · sent-back
                                                                  (and a brand's _duplicates/, listed as `duplicate`)
  Shared Assets/meta/live.jsonl                                   every ad the uploader made live
  components/image-teardown/briefs.json                           the brief register (its key, and product_id when it has one)
  components/briefs/aim.py                                        who each brief is for: sub, demographic, desire, awareness, doubt

It writes:

  runs/meta-upload/<brand>/ADS-INDEX.json    every brief, for machines
  runs/meta-upload/<brand>/ADS.md            the front page, for people

A brief filed under two names (a store handle and a catalog name for one product) is ONE row, with both names listed. Every path is a
"Shared Assets/..." label — never a machine path.

Read it, never re-scan:  import ads_index as AI;  AI.find_ad("<brand>", "<brief key>")   (a bare number answers only
when one product of the brand has it)

    python3 components/meta-upload/ads_index.py [--brand <brand>]   (every card move and every new card rebuilds it)
"""
import argparse
import collections
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STATES = ("1-check", "2-approved", "3-live", "sent-back")
RANK = {"3-live": 5, "2-approved": 4, "1-check": 3, "sent-back": 2, "duplicate": 1}
LABEL = "Shared Assets/meta"
INDEX, FRONT = "ADS-INDEX.json", "ADS.md"


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def root():
    """The meta/ tree the cards live in: META_CARDS_ROOT (tests, trials), else the cards' own root (the Drive)."""
    if os.environ.get("META_CARDS_ROOT"):
        return Path(os.environ["META_CARDS_ROOT"])
    sys.path.insert(0, str(HERE))
    import cards as C
    return Path(C.root())


def out_dir(brand, out=None):
    return Path(out or os.environ.get("ADS_INDEX_OUT") or REPO / "runs" / "meta-upload") / brand


def _register():
    """(brand, brief number) -> [register entries]."""
    reg = _json(REPO / "components" / "image-teardown" / "briefs.json") or {}
    out = collections.defaultdict(list)
    for shelf in ("briefs", "retired"):
        for k, b in (reg.get(shelf) or {}).items():
            m = re.search(r"(\d{3,4})$", str(b.get("brief") or ""))
            if m and b.get("brand"):
                out[(b["brand"], m.group(1).zfill(4))].append(dict(b, key=k))
    return out


def _full_key(name):
    """The catalog full brief key a name starts with (names.full_brief_key), or None; None for every name while the
    rollback switch is thrown (naming brief-labels.json "on": false / BRIEF_IDS_OFF=1), so rows go back to brand + number."""
    try:
        sys.path.insert(0, str(HERE.parent / "naming"))
        import names as N
        return N.full_brief_key(name) if N.brief_ids_on() else None
    except Exception:  # noqa: BLE001
        return None


def _live(r):
    out = collections.defaultdict(list)
    f = Path(r) / "live.jsonl"
    try:
        lines = f.read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if x.get("ad_name"):
            out[x["ad_name"]].append({k: x.get(k) for k in ("ad_id", "meta_ad_name", "at")})
    return out


def _cards(r, brand):
    base = Path(r) / brand
    places = [(s, base / s) for s in STATES] + [("duplicate", base / "_duplicates")]
    for state, d in places:
        if not d.is_dir():
            continue
        for lane in sorted(x for x in d.iterdir() if x.is_dir() and not x.name.startswith(".")):
            for c in sorted(x for x in lane.iterdir() if x.is_dir() and not x.name.startswith(".")):
                card = _json(c / "card.json")
                files = sorted(f.name for f in c.iterdir() if f.is_file() and not f.name.startswith(".")
                               and f.name not in ("card.json", "upload-state.json"))
                yield state, lane.name, c, card, files


def stem(ad_name):
    return str(ad_name or "").split("_batch-")[0]


AIM = ("sub", "demographic", "desire", "awareness", "doubt")


def _aims(brand):
    """The brand's aims (components/briefs/aim.py), or None when they cannot be read: the index is built without them."""
    try:
        sys.path.append(str(HERE.parent / "briefs"))
        import aim
        return aim.Aims(brand, REPO)
    except Exception:  # noqa: BLE001
        return None


def _aim_columns(row, aims):
    """Who the brief is for, beside the card's own sub_avatar and face: those stay as the card says. The card's word is
    used where the brief has none; an aim of another avatar than the card's is not carried."""
    try:
        a = aims.of(row["brief"]) if aims and row.get("number") else {}
    except Exception:  # noqa: BLE001
        a = {}
    if row.get("avatar") and a.get("avatar") not in (None, row["avatar"]):
        a = {}
    out = {k: a.get(k) for k in AIM}
    out["sub"] = out["sub"] or row.get("sub_avatar")
    out["demographic"] = out["demographic"] or row.get("face")
    return out


def collect(brand, r):
    reg, live, aims = _register(), _live(r), _aims(brand)
    rows = {}
    for state, lane, folder, card, files in _cards(r, brand):
        card = card or {}
        name = card.get("ad_name") or folder.name
        m = re.search(r"brief-(\d{3,4})", str(card.get("brief_id") or "")) or re.search(r"_brief-(\d{3,4})", name)
        num = m.group(1).zfill(4) if m else None
        key = (brand, num) if num else (brand, name)
        entries = reg.get((brand, num)) or [] if num else []
        fk = _full_key(name)
        if fk:
            # one row per brief: brand + product + number (2026-11-11: two products' 0324 became one row, marked live
            # because one of them was). Register entries of another product with this number are not this brief's.
            key = (brand, fk)
            entries = [e for e in entries if _full_key(e["key"]) in (None, fk)]
        meta = [{k: x.get(k) for k in ("ad_id", "meta_ad_name", "campaign", "ad_set", "status", "at")}
                for x in card.get("meta") or []]
        known = {x["ad_id"] for x in meta}
        meta += [dict(x, from_live_log=True) for x in live.get(name, []) if x.get("ad_id") not in known]
        appr = card.get("approval") or {}
        media = card.get("media") or []
        c = {"state": state, "lane": lane, "ad_name": name, "folder": f"{LABEL}/{brand}/{folder.parent.parent.name}/{lane}/{folder.name}/",
             "format": card.get("format"),
             "files": [{"asset": f, "on_drive": f in files} for f in media] + [{"asset": f, "on_drive": True, "not_on_card": True}
                                                                                for f in files if f not in media],
             "meta_ads": meta, "made": card.get("made_at"), "checked": card.get("checked_at"),
             "approved": appr.get("at") if appr.get("decision") == "approve" else None,
             "decision": appr.get("decision"), "live": min((x.get("at") or "" for x in meta), default=None) or None,
             "withdrawn": (card.get("withdrawn") or {}).get("why"), "superseded_by": card.get("superseded_by"),
             "unreadable": card == {} or None}
        c = {k: v for k, v in c.items() if v not in (None, [], "")}
        row = rows.setdefault(key, {"brief": None, "number": num, "brand": brand, "names": [], "product": None,
                                    "product_id": None, "avatar": None, "sub_avatar": None, "face": None, "angle": None, "lanes": [], "state": None, "cards": []})
        row["cards"].append(c)
        if stem(name) not in row["names"]:
            row["names"].append(stem(name))
        if lane not in row["lanes"]:
            row["lanes"].append(lane)
        for f in ("product", "avatar", "sub_avatar", "face", "angle"):
            if card.get(f) and (not row[f] or state != "sent-back"):
                row[f] = card[f]
        if entries:
            row["brief"] = row["brief"] or next((e["key"] for e in entries if e.get("product") == card.get("product")),
                                                entries[0]["key"])
            row["register"] = sorted({e["key"] for e in entries})
            row["product_id"] = next((e.get("product_id") for e in entries if e.get("product_id")), None)
    out = []
    for row in rows.values():
        row["brief"] = row["brief"] or row["names"][0]
        row["cards"].sort(key=lambda c: (-RANK.get(c["state"], 0), c.get("made") or ""))
        live_cards = [c for c in row["cards"] if not c.get("withdrawn")] or row["cards"]
        row["state"] = max(live_cards, key=lambda c: RANK.get(c["state"], 0))["state"]
        dates = [d for c in row["cards"] for d in (c.get("made"), c.get("checked"), c.get("approved"), c.get("live")) if d]
        row["first_made"] = min((c.get("made") for c in row["cards"] if c.get("made")), default=None)
        row["last_change"] = max(dates, default=None)
        row["meta_ad_ids"] = sorted({m["ad_id"] for c in row["cards"] for m in c.get("meta_ads") or [] if m.get("ad_id")})
        row.update(_aim_columns(row, aims))
        out.append({k: v for k, v in row.items() if v not in (None, [])})
    return sorted(out, key=lambda r: (r.get("number") or "9999", r["brief"]))


def _cell(v):
    v = str(v or "—").replace("|", "/")
    return v if len(v) <= 60 else v[:57] + "..."


def front(brand, rows, built):
    c = collections.Counter(r["state"] for r in rows)
    L = [f"# Finished ads — {brand}", "",
         "Every brief that reached an approval card: its card, its files and its Meta ads. Machines read "
         f"`{INDEX}` (`components/meta-upload/ads_index.py find_ad(brand, brief)`). Read from the cards on the Drive "
         f"(`{LABEL}/{brand}/`) and `{LABEL}/live.jsonl`; rebuilt on every card move. Never edit by hand.", "",
         f"**{len(rows)} briefs** · " + " · ".join(f"{s} {c.get(s, 0)}" for s in ("3-live", "2-approved", "1-check", "sent-back", "duplicate")
                                                 if c.get(s)) + f" · built {built}", "",
         "| Brief | Names | Lane | State | Card folder | Files | Meta ads | Made | Live | Sub-avatar | Demographic | Desire | Awareness | Doubt |",
         "|---|---|---|---|---|---:|---:|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (-RANK.get(r["state"], 0), r.get("number") or "9999")):
        top = r["cards"][0]
        names = ", ".join(f"`{n}`" for n in r["names"])
        more = f" (+{len(r['cards']) - 1} more card{'s' if len(r['cards']) > 2 else ''})" if len(r["cards"]) > 1 else ""
        L.append(f"| {r.get('number') or '—'} | {names} | {', '.join(r['lanes'])} | {r['state']} | `{top['folder']}`{more} | "
                 f"{len(top.get('files') or [])} | {len(r.get('meta_ad_ids') or [])} | {(r.get('first_made') or '—')[:10]} | "
                 f"{(top.get('live') or '—')[:10]} | " + " | ".join(_cell(r.get(k)) for k in AIM) + " |")
    two = [r for r in rows if len(r["names"]) > 1]
    if two:
        L += ["", "## Briefs filed under more than one name", ""] + \
             [f"- **{r.get('number')}**: " + " · ".join(f"`{n}`" for n in r["names"]) + " — "
              + "; ".join(f"{c['state']} `{c['ad_name']}`" + (f" (withdrawn: {c['withdrawn']})" if c.get("withdrawn") else "")
                          for c in r["cards"]) for r in two]
    return "\n".join(L) + "\n"


def build(brand=None, r=None, out=None, log=print):
    r = Path(r) if r else root()
    built = time.strftime("%Y-%m-%dT%H:%M:%S")
    brands = [brand] if brand else sorted(x.name for x in r.iterdir() if x.is_dir() and not x.name.startswith((".", "_"))
                                          and any((x / s).is_dir() for s in STATES))
    counts = {}
    for b in brands:
        rows = collect(b, r)
        d = out_dir(b, out)
        d.mkdir(parents=True, exist_ok=True)
        (d / INDEX).write_text(json.dumps({"built": built, "brand": b, "read_with": "ads_index.find_ad(brand, brief)",
                                           "from": f"{LABEL}/{b}/ (cards) + {LABEL}/live.jsonl, read only",
                                           "briefs": rows}, indent=1, ensure_ascii=False) + "\n")
        (d / FRONT).write_text(front(b, rows, built))
        counts[b] = dict(collections.Counter(x["state"] for x in rows), briefs=len(rows),
                         cards=sum(len(x["cards"]) for x in rows))
        log(f"  ads index: {b} — {len(rows)} briefs, {counts[b]['cards']} cards → runs/meta-upload/{b}/{INDEX}, {FRONT}")
    return counts


def rebuild_quietly(brand=None):
    """For the card road (cards.move, to_check): the index follows every card, and never stops one. Not on a test or
    trial tree (META_CARDS_ROOT), whose cards are not the real ones."""
    if os.environ.get("META_CARDS_ROOT") or os.environ.get("ADS_INDEX_OFF") == "1":
        return None
    try:
        return build(brand, log=lambda *_: None)
    except Exception as e:  # noqa: BLE001 — an index that cannot rebuild never stops a card
        print(f"  ads index not rebuilt: {type(e).__name__}: {e}")
        return None


def find_ad(brand, brief, out=None):
    """The brief's row — by its number (NNNN), its brief key, any of its names, or an ad name / Meta ad id."""
    f = out_dir(brand, out) / INDEX
    if not f.is_file():
        build(brand, out=out, log=lambda *_: None)
    s = str(brief)
    num = s.zfill(4) if s.isdigit() and len(s) <= 4 else None
    rows = json.loads(f.read_text())["briefs"]
    for row in rows:
        if s == row["brief"] or s in row["names"] or stem(s) in row["names"] \
                or s in (row.get("meta_ad_ids") or []) or s in (row.get("register") or []):
            return row
    # a bare number answers only when one brief of the brand has it: numbers count per brand AND product
    hits = [row for row in rows if num and row.get("number") == num]
    return hits[0] if len(hits) == 1 else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand")
    ap.add_argument("--find")
    a = ap.parse_args(argv)
    if a.find:
        print(json.dumps(find_ad(a.brand, a.find), indent=1, ensure_ascii=False))
        return 0
    build(a.brand)
    return 0


if __name__ == "__main__":
    sys.exit(main())
