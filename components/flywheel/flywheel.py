#!/usr/bin/env python3
"""flywheel — the read joined to the plan: each morning, what the numbers say becomes brief proposals.

    python3 components/flywheel/flywheel.py run  --brand <brand> [--date YYYY-MM-DD] [--lead-days 21]
    python3 components/flywheel/flywheel.py show --brand <brand>            the newest proposals, as a table

One step, any brand. It reads only what is already on file (never Meta):
  - the warehouse copy        runs/funnel-tracking/<brand>/<date>/warehouse.json   (through the desk's live_ads)
  - the desk report           runs/media-buying/<brand>/<date>/report.json        (its 3 / 7 / 14-day windows)
  - the winner rule           ~/.prizm/targets.json via the desk (spend winner, KPI winner)
  - the creative matrix       brands/<brand>/briefs/briefs.json moves, the plan ledger, the tagged library
  - the brief register        variation_of, ad-variations runs and Studio jobs already asked
  - the promo-calendar        brands/<brand>/products/offer-bank.md, runs/promo-pack/<brand>/
  - the winners bank          runs/winners/<brand>/bank.json

and writes runs/flywheel/<brand>/<date>/proposals.json: one row per proposal, four kinds:

  variations  a KPI winner showing creative fatigue      -> variations of it (ad-variations plan, dry run)
  matrix      a spend winner not yet varied              -> the matrix column to test next, from what it holds
  promo       a promo window coming up                   -> the promo pack's hand-offs (dry run)
  re-make     an old winner, not spending now            -> a baseline re-make

Each row carries the numbers behind it and nothing else. It makes no money decision and nothing it proposes spends:
a row's job stops at the quote, as the chain does. The owner starts a row from Studio -> Today (one button).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Meta's own thresholds (components/creative-diversity/META.md, "Fatigue"): cost per result above the ad's past is
# creative limited; 2x or more is creative fatigue. Our window (draft): the ad's last 7 days (and 3) against its own
# best longer window (14 or 30 days) — the desk keeps no single best 7 days yet.
FATIGUE_AT = 2.0
SEEN = ("format", "face", "setting", "look")
COLS = ("who", "awareness", "argument") + SEEN
NAMES = {"who": "person", "awareness": "awareness", "argument": "angle", "format": "format", "face": "face",
         "setting": "setting", "look": "look"}
REMAKES = 3


def root():
    return Path(os.environ.get("FLYWHEEL_ROOT") or ROOT).resolve()


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _mod(name, path):
    key = "flywheel_" + name
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, str(path))
        m = importlib.util.module_from_spec(spec)
        sys.modules[key] = m
        spec.loader.exec_module(m)
    return sys.modules[key]


def desk(base):
    """The Studio desk: its live_ads is the one home of the winner rule. Pointed at `base`."""
    p = str(ROOT / "components" / "video-studio")
    if p not in sys.path:
        sys.path.insert(0, p)
    import workflow_desk as WD
    WD.WS = base
    return WD


def out_dir(brand, day, base=None):
    return (base or root()) / "runs" / "flywheel" / brand / day


def _newest(base, pattern):
    hits = sorted(glob.glob(str(base / pattern)))
    return Path(hits[-1]) if hits else None


def _rel(base, p):
    try:
        return str(Path(p).relative_to(base)) if p else None
    except ValueError:
        return None


def _r(v, n=2):
    return round(float(v), n) if v is not None else None


# ------------------------------------------------------------------------------------------------- the matrix --
def moves_index(brand, base):
    """{"brief": {"0323": moves}, "ad": {"<ad id>": moves}} from the brief register, the plan ledger and the newest
    tagged library (ad -> asset -> moves). Only what is on file; nothing is inferred."""
    by_brief, by_ad = {}, {}
    reg = _read(base / "brands" / brand / "briefs" / "briefs.json") or {}
    for r in reg.get("briefs") or []:
        m = re.search(r"(\d{4})", str(r.get("brief") or ""))
        if m and isinstance(r.get("moves"), dict):
            by_brief[m.group(1)] = r["moves"]
    led = _read(base / "runs" / "creative-diversity" / brand / "planned.json") or {}
    for row in (led.get("ads") or {}).values() if isinstance(led, dict) else []:
        if isinstance(row, dict) and isinstance(row.get("moves"), dict):
            m = re.search(r"(\d{4})", str(row.get("brief") or ""))
            if m:
                by_brief.setdefault(m.group(1), row.get("made") or row["moves"])
    lib = sorted(glob.glob(str(base / "runs" / "creative-diversity" / brand / "2*" / "matrix.json")))
    running = []
    if lib:
        day = Path(lib[-1]).parent
        items = {i.get("asset"): i.get("moves") or {} for i in (_read(lib[-1]) or {}).get("items") or []}
        running = [m for m in items.values() if m]
        ads = _read(day / "ads.json") or {}
        for a in ads.get("ads") or [] if isinstance(ads, dict) else []:
            for asset in a.get("assets") or []:
                if items.get(asset):
                    by_ad[str(a.get("ad_id"))] = items[asset]
                    break
    return {"brief": by_brief, "ad": by_ad, "running": running,
            "library": Path(lib[-1]).parent.name if lib else None}


def known(m):
    return {k: v for k, v in (m or {}).items() if k in COLS and v not in (None, "", "unclear", "?")}


def next_column(moves, running):
    """The seen column to move next, from what the winner already holds: the one whose value is shared by the most
    running ads (Meta groups ads that look alike; the matrix asks for 2 seen columns apart). Returns the column, the
    winner's value, how many running ads share it, and the least-used values already on the running list."""
    m = known(moves)
    if len([k for k in SEEN if k in m]) < 2:
        return None
    use = {k: Counter(r.get(k) for r in running if r.get(k) not in (None, "", "unclear")) for k in SEEN}
    best = None
    for k in SEEN:
        if k not in m:
            continue
        n = use[k].get(m[k], 0)
        if best is None or n > best[1]:
            best = (k, n)
    k, n = best
    total = sum(use[k].values())
    open_ = [v for v, _ in sorted(use[k].items(), key=lambda x: (x[1], str(x[0]))) if v != m[k] and not str(v).startswith("new:")][:3]
    return {"column": k, "name": NAMES[k], "holds": m[k], "shared_by": n, "of_running": total,
            "share": round(n / total, 2) if total else None, "least_used": open_,
            "keeps": {c: m[c] for c in ("who", "awareness", "argument") if c in m}}


# ------------------------------------------------------------------------------------------------ the register --
def varied(brand, base):
    """Brief numbers already varied or asked to be: variation_of in the register, an ad-variations run that names
    the brief, a Studio job (variations / make / flywheel) that names it. {"0323": "where"}"""
    out = {}
    reg = _read(base / "brands" / brand / "briefs" / "briefs.json") or {}
    for r in reg.get("briefs") or []:
        m = re.search(r"(\d{4})", str(r.get("variation_of") or ""))
        if m:
            out.setdefault(m.group(1), "brief register: %s is a variation of it" % r.get("brief"))
    for f in glob.glob(str(base / "runs" / "ad-variations" / brand / "*" / "run.json")):
        for n in set(re.findall(r"brief-(\d{4})", Path(f).read_text(errors="ignore")[:20000])):
            out.setdefault(n, "ad-variations run %s" % Path(f).parent.name)
    for f in glob.glob(str(base / "runs" / "studio-asks" / brand / "*" / "ask.json")):
        a = _read(f) or {}
        if a.get("kind") in ("variations", "make", "flywheel"):
            for n in set(re.findall(r"(?:brief[ -])(\d{4})", str(a.get("input") or ""))):
                out.setdefault(n, "Studio job %s (%s)" % (a.get("id"), a.get("state")))
    return out


# --------------------------------------------------------------------------------------------- the proposals --
def windows(report):
    """{"<ad id>": {"3": {spend, sales, cpa}, "7": …, "14": …}} from the desk report."""
    return {str(f.get("id")): f.get("windows") or {} for f in (report or {}).get("flags") or [] if f.get("kind", "ad") == "ad"}


def fatigue(ad, win):
    """The ad's recent cost per result against its own past (Meta's 2x line). None when there is no past to read."""
    w = lambda d, k: (win.get(d) or {}).get(k)                                                       # noqa: E731
    past = [c for c in (w("14", "cpa"), ad.get("cpa30")) if c]
    if not past:
        return None
    best = min(past)
    reads = {}
    for d, spend, sales in (("3", w("3", "spend"), w("3", "sales")), ("7", w("7", "spend") if win.get("7") else ad["spend7"],
                                                                          w("7", "sales") if win.get("7") else ad["buys7"])):
        if not spend:
            continue
        cpa = spend / sales if sales else None
        ratio = (cpa if cpa else spend) / best     # no sale yet: the spend so far already counts against the past
        reads[d] = {"spend": _r(spend), "sales": sales or 0, "cpa": _r(cpa), "x_past": _r(ratio)}
    if not reads:
        return None
    top = max(reads.values(), key=lambda r: r["x_past"])
    state = "creative fatigue" if top["x_past"] >= FATIGUE_AT else "creative limited" if top["x_past"] > 1 else "holding"
    return {"past_cpa": _r(best), "past_from": "14 days" if w("14", "cpa") == best else "30 days", "reads": reads,
            "worst": top["x_past"], "state": state}


def _ad_numbers(a, win=None):
    n = {"spend30": _r(a["spend30"]), "buys30": a["buys30"], "cpa30": a["cpa30"], "spend7": _r(a["spend7"]),
         "buys7": a["buys7"], "cpa7": a["cpa7"], "roas7": a["roas7"], "desk_call": a.get("call")}
    if win:
        n["windows"] = {d: {k: _r(v) if k != "sales" else v for k, v in (win.get(d) or {}).items()} for d in ("3", "7", "14") if win.get(d)}
    return n


def _key(a):
    return ("brief " + a["brief"]) if a["brief"] else ("ad " + str(a["id"]))


def label(a):
    """How the owner knows the ad: its brief number, else its name up to the first separator."""
    if a["brief"]:
        return "Brief " + a["brief"]
    return re.split(r"_|\s+-\s+", str(a.get("name") or a["id"]))[0].strip()[:48]


def said(a, kpi):
    return "$%s spent in 30 days · %s buys · CPA $%s%s" % ("{:,.0f}".format(a["spend30"]), int(a["buys30"]), a["cpa30"],
                                                         " · KPI winner (target $%s)" % kpi if a["kpi_winner"] else "")


def build(brand, day=None, base=None, lead_days=21, today=None):
    base = base or root()
    today = today or dt.date.today()
    day = day or today.isoformat()
    WD = desk(base)
    la = WD.live_ads(brand)
    rf = _newest(base, "runs/media-buying/%s/2*/report.json" % brand)
    report = _read(rf) if rf else None
    win = windows(report)
    mx = moves_index(brand, base)
    done = varied(brand, base)
    rows, held = [], []

    # one row per brief (or per ad without one): the best-spending ad stands for its brief
    seen, kpi = {}, la["winrule"].get("kpi_cpa")
    for a in sorted((a for a in la["ads"] if a["spend_winner"]), key=lambda a: (not a["kpi_winner"], -a["spend30"])):
        seen.setdefault(_key(a), a)
    for key, a in seen.items():
        w = win.get(str(a["id"])) or {}
        nums = _ad_numbers(a, w)
        if a["kpi_winner"]:
            f = fatigue(a, w)
            if f and f["state"] == "creative fatigue":
                rows.append({"kind": "variations", "key": key, "label": label(a), "ad": a["name"], "brief": a["brief"],
                             "title": "Variations of %s: %s" % (label(a), f["state"]),
                             "why": "cost per result %.1fx its own past (%s CPA $%s, %s)" % (
                                 f["worst"], f["past_from"], f["past_cpa"], " · ".join(
                                     "%sd $%s on %s sales" % (d, r["spend"], r["sales"]) for d, r in sorted(f["reads"].items()))),
                             "numbers": dict(nums, fatigue=f),
                             "do": "ad-variations plan of this winner, --dry-run: every prompt filled, nothing spent",
                             "cmd": ["python3", "components/ad-variations/machine/run.py", "plan", "<teardown of %s>" % key,
                                     "--brand", brand, "--dry-run"]})
                continue
            nums["fatigue"] = f
        if a["brief"] and a["brief"] in done:
            held.append({"key": key, "why": "already varied: " + done[a["brief"]], "numbers": nums})
            continue
        moves = mx["brief"].get(a["brief"]) if a["brief"] else None
        moves = moves or mx["ad"].get(str(a["id"]))
        nc = next_column(moves, mx["running"]) if moves else None
        if not nc:
            # never tagged: the job reads its pictures, fills the 7 cells from the lists, then the same rule picks
            rows.append({"kind": "matrix", "key": key, "label": label(a), "ad": a["name"], "brief": a["brief"],
                         "title": "Tag, then test the next column: %s" % label(a),
                         "why": "%s · not yet varied · its 7 matrix cells are not on file" % said(a, kpi),
                         "numbers": dict(nums, kpi_winner=a["kpi_winner"]), "matrix": None,
                         "do": "fill its 7 cells from the lists (the ad's own pictures, free), then "
                               "`flywheel.py column` picks the seen column shared by the most running ads",
                         "cmd": ["python3", "components/flywheel/flywheel.py", "column", "--brand", brand,
                                 "who=<…>", "awareness=<…>", "argument=<…>", "format=<…>", "face=<…>", "setting=<…>", "look=<…>"]})
            continue
        rows.append({"kind": "matrix", "key": key, "label": label(a), "ad": a["name"], "brief": a["brief"],
                     "title": "Test %s next: %s" % (nc["name"], label(a)),
                     "why": "%s · %s `%s` is on %d of %d running ads (library %s); keep %s, move %s" % (
                         said(a, kpi), nc["name"], nc["holds"], nc["shared_by"], nc["of_running"], mx["library"],
                         " · ".join("%s `%s`" % (NAMES[c], v) for c, v in nc["keeps"].items()) or "what it says", nc["name"]),
                     "numbers": dict(nums, kpi_winner=a["kpi_winner"]), "matrix": dict(nc, moves=known(moves)),
                     "do": "one new row in the creative matrix: this winner's cells with %s moved; the matrix check, "
                           "then the brief (free)" % nc["name"],
                     "cmd": ["python3", "components/creative-diversity/check.py", "--brief", brand, "<new brief>"] +
                            ["%s=%s" % (c, "<new>" if c == nc["column"] else v) for c, v in known(moves).items()]})

    # promo windows coming up -> the promo pack's hand-offs
    try:
        P = _mod("pack", ROOT / "components" / "promo-pack" / "machine" / "pack.py")
        promos = P.due(brand, today, lead_days, base)
    except (Exception, SystemExit):                                                    # noqa: BLE001  no offer bank
        P, promos = None, []
    for r in promos:
        packs = [p for p in glob.glob(str(base / "runs" / "promo-pack" / brand / "*" / "pack.json"))
                 if ((_read(p) or {}).get("window") or {}).get("start") == r["start"]]
        pk = _read(packs[0]) if packs else None
        st = _read(Path(packs[0]).parent / "status.json") if packs else None
        moment = (pk or {}).get("moment")
        opens = (dt.date.fromisoformat(r["start"]) - today).days
        rows.append({"kind": "promo", "key": "promo " + (moment or r["start"]),
                     "title": "Promo pack: %s" % (moment or r["dates"]),
                     "why": "%s %s; pack %s" % (r["dates"], "opens in %d days" % opens if opens > 0 else "is open",
                                                ((st or {}).get("state") or "built, not handed") if pk else "not built"),
                     "numbers": {"start": r["start"], "end": r["end"], "opens_in_days": opens, "promo": r["promo"],
                                 "handoffs": len((pk or {}).get("handoffs") or []), "pack_state": (st or {}).get("state"), "held": (st or {}).get("held") or [],
                                 "stock_blockers": len(((pk or {}).get("stock") or {}).get("blockers") or [])},
                     "do": "the pack's hand-offs, --dry-run: what each workflow would be handed, nothing run",
                     "cmd": ["python3", "components/promo-pack/machine/pack.py", "hand", "--brand", brand, "--moment", moment, "--dry-run"]
                     if moment else ["python3", "components/promo-pack/machine/pack.py", "build", "--brand", brand, "--month", r["start"][:7]]})

    # old winners: proven in the bank, not spending in the last 30 days -> a baseline re-make
    spending = {str(a["id"]) for a in la["ads"] if a["spend30"] > 0}
    bank = (_read(base / "runs" / "winners" / brand / "bank.json") or {}).get("rows") or []
    old = []
    for b in bank:
        if not (b.get("core") or b.get("state") == "winner") or set(map(str, b.get("ad_ids") or [])) & spending:
            continue
        s = max(b.get("snapshots") or [{}], key=lambda x: x.get("purchases") or 0)
        if (s.get("purchases") or 0) >= 1:
            old.append((b, s))
    old.sort(key=lambda x: -(x[1].get("purchases") or 0))
    for b, s in old[:REMAKES]:
        rows.append({"kind": "re-make", "key": b["id"], "ad": b.get("name"),
                     "title": "Re-make: %s" % (b.get("name") or b["id"]),
                     "why": "%s purchases on $%s (CPA $%s, ROAS %s) %s to %s; no spend in the last 30 days" % (
                         s.get("purchases"), "{:,.0f}".format(s.get("spend") or 0), s.get("cpa"), s.get("roas"),
                         s.get("first") or s.get("since"), s.get("last") or s.get("until")),
                     "numbers": {k: s.get(k) for k in ("purchases", "spend", "cpa", "roas", "first", "last", "since", "until") if s.get(k) is not None},
                     "format": b.get("format"), "hook": (b.get("words") or {}).get("hook"),
                     "do": "a baseline re-make: the same ad made again from its teardown, one variation (the control), "
                           "ad-variations plan --n 1 --dry-run",
                     "cmd": ["python3", "components/ad-variations/machine/run.py", "plan", "<teardown of %s>" % b["id"],
                             "--brand", brand, "--n", "1", "--dry-run"]})

    order = {"variations": 0, "matrix": 1, "promo": 2, "re-make": 3}
    rows.sort(key=lambda r: order[r["kind"]])
    for i, r in enumerate(rows, 1):
        r["id"] = "P%d" % i
        r["start"] = {"ask": "flywheel", "input": "%s %s · %s" % (day, r["id"], r["title"])}
    wf = la.get("from")
    return {"brand": brand, "date": day, "made": dt.datetime.now().isoformat(timespec="seconds"),
            "what": "what the numbers say, as brief proposals: no money decisions; nothing here spends",
            "from": {"warehouse": wf, "desk_report": _rel(base, rf), "desk_asof": (report or {}).get("asof"),
                     "library": mx["library"], "winners_bank": "runs/winners/%s/bank.json" % brand if bank else None},
            "winrule": la["winrule"], "fatigue_rule": {"at": FATIGUE_AT, "window": "last 3 and 7 days against the ad's own "
                                                       "14 or 30 days (draft)", "source": "components/creative-diversity/META.md"},
            "counts": {"ads": len(la["ads"]), "spend_winners": sum(a["spend_winner"] for a in la["ads"]),
                       "kpi_winners": sum(a["kpi_winner"] for a in la["ads"]),
                       **{k: sum(r["kind"] == k for r in rows) for k in order}},
            "proposals": rows, "held": held}


def write(brand, day=None, base=None, **kw):
    doc = build(brand, day, base, **kw)
    d = out_dir(brand, doc["date"], base)
    d.mkdir(parents=True, exist_ok=True)
    (d / "proposals.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return doc, d / "proposals.json"


def latest(brand, base=None):
    """The newest proposals file for a brand (the Studio's Today card reads this), or None."""
    f = _newest(base or root(), "runs/flywheel/%s/2*/proposals.json" % brand)
    doc = _read(f) if f else None
    if isinstance(doc, dict):
        doc["file"] = _rel(base or root(), f)
    return doc


def one(brand, day, pid, base=None):
    doc = _read(out_dir(brand, day, base) / "proposals.json") or {}
    return next((r for r in doc.get("proposals") or [] if r.get("id") == pid), None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--brand", required=True)
    r.add_argument("--date")
    r.add_argument("--lead-days", type=int, default=21)
    s = sub.add_parser("show")
    s.add_argument("--brand", required=True)
    c = sub.add_parser("column", help="the next column for one set of cells: who=… awareness=… … look=…")
    c.add_argument("--brand", required=True)
    c.add_argument("cells", nargs="+")
    a = ap.parse_args(argv)
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", a.brand):
        raise SystemExit("bad brand id")
    if a.cmd == "run":
        if not _newest(root(), "runs/funnel-tracking/%s/2*/warehouse.json" % a.brand):
            print("no warehouse copy for %s yet: nothing to read" % a.brand)
            return 3
        doc, f = write(a.brand, a.date, lead_days=a.lead_days)
        print("%s: %d proposals (%s) -> %s" % (a.brand, len(doc["proposals"]), ", ".join(
            "%d %s" % (v, k) for k, v in doc["counts"].items() if k not in ("ads", "spend_winners", "kpi_winners") and v),
            _rel(root(), f)))
        return 0
    if a.cmd == "column":
        cells = dict(x.split("=", 1) for x in a.cells if "=" in x)
        nc = next_column(cells, moves_index(a.brand, root())["running"])
        print(json.dumps(nc or {"column": None, "why": "fewer than 2 seen cells known"}, indent=1, ensure_ascii=False))
        return 0 if nc else 3
    doc = latest(a.brand)
    if not doc:
        print("no proposals yet for %s" % a.brand)
        return 3
    for p in doc["proposals"]:
        print("%-4s %-10s %s\n     %s" % (p["id"], p["kind"], p["title"], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
