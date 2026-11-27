"""The winner line: a brand's proven ads, kept apart from swipes.

Winners are the best ads from the brand's own ad account (the bank's Core rows). Swipes come from anywhere else.
A winner does not go through swipe teardown or a fresh brief: it goes straight into variations (components/ad-variations)
and is the base new swipes are built on.

    python3 components/winners/line.py --brand brand_a        writes runs/winners/<brand>/line.json
    python3 components/winners/line.py --brand brand_a --ok <winner id>      records the OK on its variation plan

Each row: the bank row (name, ad ids, spend, purchases, ROAS from the widest window), the teardown run that took it
apart if one exists, its variation plan if one exists, and its step on the line:

    banked              the default: kept in the bank and reused, pulled up beside new-format swipes; not on the queue
    variations          raw variations were asked for by name (--raw); no plan yet
    approve-variations  a plan exists and waits for the OK
    making              the plan has its OK; variations go to production

Winners are reused over and over (owner, 6 Nov), so a winner only becomes a queue piece when raw variations of it
are asked for.

Reads only. The one write besides line.json is line-calls.json, the OKs.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIN = REPO / "runs" / "winners"
TEAR = REPO / "runs" / "video-teardown" / "_work"
VAR = REPO / "runs" / "ad-variations"
STOP = {"the", "a", "an", "of", "with", "w", "lp", "ads", "ad", "and", "in", "to", "for", "new", "copy", "version"}


def _words(s):
    return {w for w in re.findall(r"[a-z0-9]+", str(s).lower()) if w not in STOP and len(w) > 1}


def _widest(row):
    snaps = [s for s in row.get("snapshots") or [] if s.get("since") and s.get("until")]
    return max(snaps, key=lambda s: (s["until"] >= s["since"], s["until"], -int(s["since"].replace("-", "")[:8] or 0)),
               default={}) if snaps else {}


def _core_runs(brand):
    """Teardown runs made from this brand's Core winners (core<N>-NN-… with the brand on run.json, <brand>-core<N>-NN…)."""
    out = []
    if TEAR.is_dir():
        for d in sorted(TEAR.iterdir()):
            n = d.name
            if not d.is_dir():
                continue
            bare, own = re.match(r"core\d+-", n), n.startswith(f"{brand}-core")
            if bare or own:
                try:
                    rj = json.loads((d / "run.json").read_text())
                except (OSError, ValueError):
                    rj = {}
                if rj.get("brand") == brand or (own and rj.get("brand") is None):
                    out.append(d)
    return out


def _by_video(row, runs, used):
    """The run that tore down this winner's own video file (audit videos/NN-<name>.mp4)."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(row.get("name") or "").lower()).strip("-")[:24]
    if not slug:
        return None
    for d in sorted(runs, key=lambda d: ("flash" in d.name, len(d.name))):
        if d.name in used:
            continue
        try:
            vid = Path(str(json.loads((d / "run.json").read_text()).get("video") or "")).name
        except (OSError, ValueError):
            vid = ""
        if re.sub(r"^\d+-", "", vid).startswith(slug[:max(8, len(slug) - 4)]):
            return d
    return None


def _video_owned(d, core):
    """True when this run's video file is another winner's own."""
    try:
        vid = re.sub(r"^\d+-", "", Path(str(json.loads((d / "run.json").read_text()).get("video") or "")).name)
    except (OSError, ValueError):
        return False
    for r in core:
        slug = re.sub(r"[^a-z0-9]+", "-", str(r.get("name") or "").lower()).strip("-")[:24]
        if slug and vid.startswith(slug[:max(8, len(slug) - 4)]):
            return True
    return False


def _match(row, runs, used):
    """The teardown run made from this winner: by its Core number in the winners registry (…#brand_a-paid-core30-05 →
    core30-05-…, …core8-03 → <brand>-core8-03…), else the run whose name shares the most words with its names."""
    hit = _by_video(row, runs, used)
    if hit:
        return hit
    slug = ""
    if slug:
        for d in sorted(runs, key=lambda d: ("flash" in d.name, len(d.name))):
            if d.name in used:
                continue
            try:
                vid = Path(str(json.loads((d / "run.json").read_text()).get("video") or "")).name
            except (OSError, ValueError):
                vid = ""
            if re.sub(r"^\d+-", "", vid).startswith(slug[:max(8, len(slug) - 4)]):
                return d          # the run tore down this winner's own video file (audit videos/NN-<name>.mp4)
    reg = str((row.get("source") or {}).get("registry") or "")
    m = re.search(r"(core\d+)-(\d+)$", reg)
    if m:
        pre = ("%s-%s-" % (m.group(1), m.group(2)), "-%s-%s" % (m.group(1), m.group(2)))
        hit = [d for d in runs if d.name not in used and (d.name.startswith(pre[0]) or pre[1] in d.name)]
        return sorted(hit, key=lambda d: ("flash" in d.name, len(d.name)))[0] if hit else None
    names = [row.get("name") or ""] + list(row.get("ad_names") or [])
    want = set().union(*(_words(n) for n in names))
    best, score = None, 0
    for d in runs:
        if d.name in used:
            continue
        have = _words(re.sub(r"^(core30-\d+|[a-z]+-core\d+-\d+)-?", "", d.name))
        s = len(want & have)
        if s > score:
            best, score = d, s
    return best if score else None


def _plan(run_name, brand):
    p = VAR / brand / run_name / "variation-plan.json"
    return p if p.is_file() else None


def calls(brand):
    f = WIN / brand / "line-calls.json"
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return {}


def build(brand):
    bank = json.loads((WIN / brand / "bank.json").read_text())
    core = [r for r in bank.get("rows") or [] if r.get("core")]
    runs, used, ok, rows = _core_runs(brand), set(), calls(brand), []
    first = {}                       # pass 1: a run whose video file is this winner's own wins over any number
    for r in core:
        hit = _by_video(r, runs, used)
        if hit:
            first[r["id"]] = hit
            used.add(hit.name)
    for r in core:
        free = [d for d in runs if not _video_owned(d, core)]    # a run of another winner's video is never borrowed
        run = first.get(r["id"]) or _match(r, free, used)
        if run:
            used.add(run.name)
        plan = _plan(run.name, brand) if run else None
        call = ok.get(r["id"]) or {}
        if not call.get("raw") and not call.get("ok"):
            step = "banked"
        else:
            step = "making" if call.get("ok") else ("approve-variations" if plan else "variations")
        w = _widest(r)
        rows.append({
            "id": r["id"], "name": r.get("name"), "format": r.get("format"), "ad_ids": r.get("ad_ids") or [],
            "spend": w.get("spend"), "purchases": w.get("purchases"), "roas": w.get("roas"), "cpa": w.get("cpa"),
            "window": "%s to %s" % (w.get("since"), w.get("until")) if w else None,
            "teardown": str(run.relative_to(REPO)) if run else None,
            "poster": str((run / "poster.jpg").relative_to(REPO)) if run and (run / "poster.jpg").is_file() else None,
            "plan": str(plan.relative_to(REPO)) if plan else None,
            "step": step, "ok": ok.get(r["id"]),
        })
    out = {"brand": brand, "made": datetime.now().isoformat(timespec="seconds"),
           "what": "Winners: the brand's own proven ads (bank Core). They go straight to variations, never swipe teardown.",
           "rows": rows}
    (WIN / brand / "line.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


def give_ok(brand, wid, by="owner", raw=False):
    c = calls(brand)
    rec = c.setdefault(wid, {})
    rec.update({"raw": True} if raw else {"ok": True, "raw": True})
    rec.update({"by": by, "at": datetime.now().isoformat(timespec="seconds")})
    (WIN / brand / "line-calls.json").write_text(json.dumps(c, indent=1) + "\n")
    return build(brand)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--ok", help="the OK on a winner's variation plan")
    ap.add_argument("--raw", help="ask for raw variations of this winner: it joins the queue at Variations")
    a = ap.parse_args()
    d = give_ok(a.brand, a.ok) if a.ok else give_ok(a.brand, a.raw, raw=True) if a.raw else build(a.brand)
    steps = {}
    for r in d["rows"]:
        steps[r["step"]] = steps.get(r["step"], 0) + 1
    print(a.brand, len(d["rows"]), "winners", steps, "with teardown:", sum(1 for r in d["rows"] if r["teardown"]))
    sys.exit(0)
