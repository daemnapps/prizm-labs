#!/usr/bin/env python3
"""action-log: every change that touches the business, one entry, every brand (owner, 28 Nov 2026).

One door to write (`append`), append-only and chained (each entry carries the hash of the one before it, so an edit or
a deletion anywhere breaks `verify`). Every tool can read it. The logs kept before it are brought in, not replaced
(`ingest`), so nothing starts over. Each entry carries what it needs to be scored on its return later: brand id,
object ids, time, before and after (`score`).

    action_log.py add --brand <b> --kind <kind> --by <who> --object <type>:<id>[:<name>] --before X --after Y
                      --why "..." [--said "the owner's words"] [--result '{"success": true}']
    action_log.py ingest                  bring in every source log (safe to run again: nothing is added twice)
    action_log.py list [--brand b] [--kind k] [--days N]
    action_log.py score <entry id>        its return at 3 / 7 / 14 days
    action_log.py verify                  the chain is whole: no entry edited or removed

Where it lives: <runs>/action-log/log.jsonl (all brands; the brand is a field). Sources and their places are in
SOURCES below, each relative to the runs folder; a source outside it (a Drive mirror) is named in a local file,
~/.prizm/action-log.json {"sources": {"<name>": "<path>"}}, never in the repo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get("ACTION_LOG_WS") or HERE.parents[1])
RUNS = WS / "runs"
LOG = Path(os.environ.get("ACTION_LOG_FILE") or RUNS / "action-log" / "log.jsonl")
KINDS = ("budget", "bid", "status", "created", "paused", "rule", "approved", "live", "scheduled", "price", "offer",
         "handoff", "call", "queue", "other")
REQUIRED = ("at", "by", "brand", "kind", "object", "why")
WINDOWS = (3, 7, 14)


# ---------- the one door ----------

def _canon(e):
    return json.dumps({k: v for k, v in e.items() if k not in ("hash",)}, sort_keys=True, ensure_ascii=False)


def _tail():
    """The last entry's sequence number and hash (the chain's head)."""
    if not LOG.is_file():
        return 0, ""
    last = None
    with open(LOG, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 65536))
        lines = f.read().splitlines()
    for line in reversed(lines):
        try:
            last = json.loads(line)
            break
        except ValueError:
            continue
    return (last or {}).get("seq", 0), (last or {}).get("hash", "")


def append(entry):
    """Write one entry. The only way in: it checks the fields, stamps the sequence and the chain, and appends."""
    e = dict(entry)
    e.setdefault("at", dt.datetime.now().isoformat(timespec="seconds"))
    missing = [k for k in REQUIRED if not e.get(k)]
    if missing:
        raise ValueError("an entry needs " + ", ".join(missing))
    if e["kind"] not in KINDS:
        raise ValueError("kind is one of: " + ", ".join(KINDS))
    o = e["object"]
    if not isinstance(o, dict) or not o.get("type"):
        raise ValueError("object needs a type (campaign, ad, brief, rule, card, email, offer …) and an id")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", str(e["brand"])):
        raise ValueError("brand is the brand id")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            seq, prev = _tail()
            e["seq"], e["prev"] = seq + 1, prev
            e["id"] = e.get("id") or "a%06d" % e["seq"]
            e["hash"] = hashlib.sha256((prev + _canon(e)).encode()).hexdigest()
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return e


def read(brand=None, kind=None, days=None):
    out = []
    if not LOG.is_file():
        return out
    since = (dt.datetime.now() - dt.timedelta(days=days)).isoformat() if days else None
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if brand and e.get("brand") != brand:
            continue
        if kind and e.get("kind") != kind:
            continue
        if since and str(e.get("at") or "") < since:
            continue
        out.append(e)
    return out


def verify():
    """Walk the chain: every entry's hash matches its content and the one before it."""
    prev, n = "", 0
    if not LOG.is_file():
        return {"ok": True, "entries": 0}
    for i, line in enumerate(LOG.read_text(encoding="utf-8").splitlines(), 1):
        e = json.loads(line)
        if e.get("prev") != prev or hashlib.sha256((prev + _canon(e)).encode()).hexdigest() != e.get("hash"):
            return {"ok": False, "entries": n, "broken_at_line": i, "id": e.get("id")}
        prev, n = e["hash"], n + 1
    return {"ok": True, "entries": n}


# ---------- bringing the earlier logs in ----------

def _local_sources():
    p = Path(os.environ.get("ACTION_LOG_CONF") or Path.home() / ".prizm/action-log.json")
    try:
        return (json.loads(p.read_text()) or {}).get("sources") or {}
    except (OSError, ValueError):
        return {}


def _jsonl(path):
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                yield json.loads(line)
            except ValueError:
                continue
    except OSError:
        return


def _brief_of(text):
    m = re.search(r"brief-(\d{3,5})", str(text or ""))
    return m.group(1) if m else None


def _media_actions():
    for f in glob.glob(str(RUNS / "media-buying/*/actions.jsonl")):
        brand = Path(f).parent.name
        for i, r in enumerate(_jsonl(f)):
            did = str(r.get("did") or "")
            m = re.search(r"\$([\d,]+(?:\.\d+)?)\s*->\s*\$([\d,]+(?:\.\d+)?)", did)
            kind = ("budget" if "budget" in did.lower() and m else "rule" if "rule" in did.lower() else
                    "paused" if "pause" in did.lower() else "bid" if "bid" in did.lower() else
                    "created" if re.search(r"\b(new|built|created)\b", did.lower()) else "other")
            otype = "rule" if kind == "rule" else "ad" if r.get("ad") else "campaign"
            yield ("media-buying:%s:%d" % (brand, i), {
                "at": r.get("at"), "by": r.get("by") or "media-buying session", "brand": brand, "kind": kind,
                "object": {"type": otype, "id": str(r.get("id") or ""), "name": r.get("ad") or did[:80],
                           "brief": _brief_of(r.get("ad"))},
                "before": m.group(1).replace(",", "") if m else None, "after": m.group(2).replace(",", "") if m else None,
                "what": did, "why": r.get("why") or did, "said": _said(r.get("why") or r.get("by")),
                "result": r.get("meta"), "source": "runs/media-buying/%s/actions.jsonl" % brand})


def _said(text):
    m = re.search(r'"([^"]{2,200})"', str(text or ""))
    return m.group(1) if m else None


def _desk_calls():
    for f in glob.glob(str(RUNS / "media-buying/*/decisions.jsonl")):
        brand = Path(f).parent.name
        for i, r in enumerate(_jsonl(f)):
            yield ("desk:%s:%d" % (brand, i), {
                "at": r.get("at"), "by": r.get("by") or "owner", "brand": brand, "kind": "call",
                "object": {"type": r.get("kind") or "ad", "id": str(r.get("id") or ""), "name": r.get("name"),
                           "brief": _brief_of(r.get("name"))},
                "before": r.get("suggested"), "after": r.get("call"), "why": r.get("why") or r.get("said") or "desk call",
                "said": r.get("said"), "numbers": r.get("numbers"), "source": "runs/media-buying/%s/decisions.jsonl" % brand})


def _live_cards():
    p = _local_sources().get("live_cards")
    if not p:
        return
    for i, r in enumerate(_jsonl(os.path.expanduser(p))):
        if not r.get("brand"):
            continue
        yield ("live:%s:%s" % (r.get("ad_id") or i, r.get("at")), {
            "at": r.get("at"), "by": r.get("by") or "approval page", "brand": r["brand"], "kind": "live",
            "object": {"type": "ad", "id": str(r.get("ad_id") or ""), "name": r.get("meta_ad_name") or r.get("ad_name"),
                       "brief": _brief_of(r.get("ad_name"))},
            "before": "approved", "after": "live", "why": "card went live from the approval page",
            "lane": r.get("lane"), "source": "meta/live.jsonl"})


def _approvals():
    d = {}
    try:
        d = json.loads((RUNS / "briefs/approved.json").read_text()).get("approved") or {}
    except (OSError, ValueError):
        pass
    for key, r in d.items():
        brand = key.split("_", 1)[0].split("-", 1)[0]
        yield ("approved:%s" % key, {
            "at": r.get("at"), "by": r.get("by") or "owner", "brand": brand, "kind": "approved",
            "object": {"type": "brief", "id": key, "brief": _brief_of(key)}, "before": None, "after": "approved",
            "why": r.get("how") or "brief approved", "said": _said(r.get("how")), "source": "runs/briefs/approved.json"})


def _queue():
    for i, r in enumerate(_jsonl(RUNS / "queue/decisions.jsonl")):
        idx = str(r.get("id") or "")
        brand = idx.split("_", 1)[0].split("/", 1)[0]
        yield ("queue:%d:%s" % (i, r.get("at")), {
            "at": r.get("at"), "by": r.get("by") or "queue", "brand": brand, "kind": "queue",
            "object": {"type": "queue entry", "id": idx, "brief": _brief_of(idx)}, "before": None, "after": r.get("set"),
            "why": (r.get("set") or {}).get("note") or "queue change", "source": "runs/queue/decisions.jsonl"})


SOURCES = {"media-buying actions": _media_actions, "desk calls": _desk_calls, "cards live": _live_cards,
           "brief approvals": _approvals, "queue": _queue}


def ingest():
    """Bring every source in. Each source line has a key; a key already in the log is skipped, so running it again
    adds only what is new. Entries are written in time order."""
    have = {e.get("source_key") for e in read()}
    new = []
    counts = {}
    for name, fn in SOURCES.items():
        n = 0
        for key, e in fn() or []:
            if key in have or not e.get("at") or not e.get("brand"):
                continue
            e["source_key"] = key
            e["imported"] = True
            new.append(e)
            have.add(key)
            n += 1
        counts[name] = n
    new.sort(key=lambda e: str(e["at"]))
    brands = {p.name for p in (WS / "brands").iterdir() if p.is_dir()} if (WS / "brands").is_dir() else None
    kept = 0
    for e in new:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", str(e["brand"])) or (brands is not None and e["brand"] not in brands):
            continue                                    # a test row or an unknown brand never enters the record
        append(e)
        kept += 1
    return {"added": kept, "by_source": counts}


# ---------- the return on each entry ----------

def _snap(brand, day):
    """The warehouse copy nearest on or before a day: runs/funnel-tracking/<brand>/<date>/warehouse.json."""
    files = sorted(glob.glob(str(RUNS / "funnel-tracking" / brand / "2*/warehouse.json")))
    pick = None
    for f in files:
        if Path(f).parent.name <= day:
            pick = f
    try:
        return json.loads(Path(pick).read_text()) if pick else None, (Path(pick).parent.name if pick else None)
    except (OSError, ValueError):
        return None, None


def _daily(brand):
    """Daily spend and sales for the brand from Outlier's warehouse feed (never Meta)."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8880/api/growth", timeout=6) as r:
            g = json.loads(r.read().decode())
        return [d for d in ((g.get("brands") or {}).get(brand) or {}).get("daily") or [] if d.get("spend")]
    except Exception:  # noqa: BLE001
        return []


def _ad_read(w, obj):
    """One object's 7-day spend and buys in a warehouse copy, and the brand's total."""
    ads = (w or {}).get("ads") or []
    num = lambda v: float(v) if v not in (None, "") else 0.0
    tot = sum(num(a.get("spend7")) for a in ads)
    oid, brief = str(obj.get("id") or ""), obj.get("brief")
    mine = [a for a in ads if (oid and str(a.get("ad_id")) == oid) or (brief and re.search(r"brief-%s(?!\d)" % brief, a.get("ad_name") or ""))]
    s, b = sum(num(a.get("spend7")) for a in mine), sum(num(a.get("buys7")) for a in mine)
    return {"found": bool(mine), "spend7": round(s, 2), "buys7": b, "cpa7": round(s / b, 2) if b else None,
            "share": round(s / tot * 100, 2) if tot else None}


def score(e, windows=WINDOWS):
    """Before → after at each window: the object's share of spend and how it moved, spend growth, CPA change, and the
    brand's blended MER over the days before and after. Only what the warehouse holds; a window not reached yet is
    marked so."""
    brand, at = e["brand"], str(e["at"])[:10]
    day0 = dt.date.fromisoformat(at)
    w0, d0 = _snap(brand, at)
    before = _ad_read(w0, e["object"]) if w0 else None
    daily = _daily(brand)
    out = {"id": e.get("id"), "at": at, "before": before, "windows": []}
    for n in windows:
        dn = (day0 + dt.timedelta(days=n)).isoformat()
        if dn > dt.date.today().isoformat():
            out["windows"].append({"days": n, "reached": False})
            continue
        wn, dd = _snap(brand, dn)
        after = _ad_read(wn, e["object"]) if wn else None
        pre = [d for d in daily if (day0 - dt.timedelta(days=n)).isoformat() <= d["d"] < at]
        post = [d for d in daily if at <= d["d"] < dn]
        mer = lambda rs: round(sum(d.get("revenue") or 0 for d in rs) / sum(d["spend"] for d in rs), 2) if rs and sum(d["spend"] for d in rs) else None
        row = {"days": n, "reached": True, "read_on": dd, "mer_before": mer(pre), "mer_after": mer(post)}
        if after and after["found"]:
            row.update(share_after=after["share"], spend7_after=after["spend7"], buys7_after=after["buys7"],
                       cpa_after=after["cpa7"])
            if before and before["found"]:          # it was already spending: the change since the entry
                row.update(share_before=before["share"], share_change=round((after["share"] or 0) - (before["share"] or 0), 2),
                           spend_growth=round((after["spend7"] / before["spend7"] - 1) * 100, 1) if before["spend7"] else None,
                           cpa_before=before["cpa7"],
                           cpa_change=round(after["cpa7"] - before["cpa7"], 2) if after["cpa7"] and before["cpa7"] else None)
            else:                                     # new since the entry (a launch): everything it has is the change
                row.update(share_before=0.0, share_change=after["share"], new=True)
        if row["mer_before"] and row["mer_after"]:
            row["mer_change"] = round(row["mer_after"] - row["mer_before"], 2)
        out["windows"].append(row)
    return out


# ---------- named views: the owner's own reads ----------

VIEWS = Path(os.environ.get("ACTION_LOG_VIEWS") or RUNS / "action-log" / "views.json")
READS = ("share_change", "spend_growth", "cpa_change", "mer_change")


def views():
    try:
        return json.loads(VIEWS.read_text())
    except (OSError, ValueError):
        return {"views": []}


def save_view(v):
    """A view: a name, a filter (brand, kind, days since), the reads shown and the window. Saving a name again
    replaces that view; views are settings, not the record, so they can change."""
    name = str(v.get("name") or "").strip()[:60]
    if not name:
        raise ValueError("a view needs a name")
    reads = [r for r in (v.get("reads") or []) if r in READS] or list(READS)
    win = int(v.get("window") or 7)
    if win not in WINDOWS:
        raise ValueError("window is one of 3, 7, 14")
    row = {"name": name, "brand": v.get("brand") or None, "kind": v.get("kind") or None,
           "days": int(v["days"]) if v.get("days") else None, "reads": reads, "window": win}
    d = views()
    d["views"] = [x for x in d.get("views") or [] if x.get("name") != name] + [row]
    VIEWS.parent.mkdir(parents=True, exist_ok=True)
    VIEWS.write_text(json.dumps(d, indent=1))
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    for k in ("brand", "kind", "by", "object", "why"):
        a.add_argument("--" + k, required=True)
    for k in ("before", "after", "said", "result"):
        a.add_argument("--" + k)
    sub.add_parser("ingest")
    l = sub.add_parser("list")
    l.add_argument("--brand")
    l.add_argument("--kind")
    l.add_argument("--days", type=int)
    s = sub.add_parser("score")
    s.add_argument("id")
    sub.add_parser("verify")
    o = ap.parse_args(argv)
    if o.cmd == "add":
        t, _, rest = o.object.partition(":")
        oid, _, name = rest.partition(":")
        res = json.loads(o.result) if o.result else None
        print(json.dumps(append({"brand": o.brand, "kind": o.kind, "by": o.by, "why": o.why, "said": o.said,
                                 "object": {"type": t, "id": oid, "name": name or None}, "before": o.before,
                                 "after": o.after, "result": res}), ensure_ascii=False))
    elif o.cmd == "ingest":
        print(json.dumps(ingest()))
    elif o.cmd == "list":
        for e in read(o.brand, o.kind, o.days):
            print(json.dumps(e, ensure_ascii=False))
    elif o.cmd == "score":
        e = next((x for x in read() if x.get("id") == o.id), None)
        if not e:
            sys.exit("no entry " + o.id)
        print(json.dumps(score(e), indent=1))
    elif o.cmd == "verify":
        v = verify()
        print(json.dumps(v))
        sys.exit(0 if v["ok"] else 1)


if __name__ == "__main__":
    main()
