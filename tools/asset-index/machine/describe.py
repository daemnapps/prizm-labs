#!/usr/bin/python3
"""describe.py — describe a clip only when something needs it, and keep the description (LD-63 (describe on use);
the team, 2026-10-21: "Describing it can still be based on actual use need").

    python3 machine/describe.py --brand <brand> --folder "Shared Assets/brands/<brand>/…" --budget 1.00 --reason "…" [--dry-run]
    python3 machine/describe.py --brand <brand> --ids <drive id>,<drive id> --budget 0.20 --reason "…"

Library: describe_on_use(record_dirs, budget_usd, reason, brand=…) — the footage gate calls it for its top
mapping-only candidates; a person calls the CLI. For each mapping record (described false) that is a VIDEO, it runs
index_run.one() into the record folder (breakdown.json + usage.json there; meta and frames merged into clip.json;
described true). One clip at a time, so the budget is checked before each clip starts and the worst overshoot is
one clip. Every call's spend is one entry in runs/asset-index/<brand>/describe-on-use-<YYYY-MM>/ledger.json
(index_run.ledger). A described file is never read again. The Drive's daily download limit stops the batch and
nothing more is described that day (a quota marker beside the ledger). Pictures are a later card.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))       # appended: a folder at position 0 can shadow a caller's own modules
import index_run as IR  # noqa: E402
import shared_paths as SP  # noqa: E402

PROXY_TOKENS_PER_S = 194        # measured on the 2026-10-20 sample: prompt tokens per second of the 360p proxy
OUT_TOKENS = 2200               # median output + thinking tokens per clip on the 147 clips described 2026-10-20


def month_collection(now=None) -> str:
    return "describe-on-use-" + time.strftime("%Y-%m", time.gmtime(now or time.time()))


def _quota_marker(brand: str, runs: Path, now=None) -> Path:
    return runs / brand / month_collection(now) / ("quota-%s.json" % time.strftime("%Y-%m-%d", time.gmtime(now or time.time())))


def estimate(clip: dict) -> float:
    """~USD for one clip, from its duration and the registry price (rate()); 0 when unpriced."""
    r, _why = IR.rate()
    if r is None:
        return 0.0
    secs = min(float((clip.get("meta") or {}).get("duration_s") or 30.0), 90.0)
    return round((PROXY_TOKENS_PER_S * secs * r[0] + OUT_TOKENS * r[1]) / 1e6, 4)


def _todo(record_dirs):
    out, skipped = [], []
    for d in record_dirs:
        d = Path(d)
        try:
            clip = json.loads((d / "clip.json").read_text())
        except (OSError, ValueError):
            skipped.append((str(d), "no record"))
            continue
        if (d / "breakdown.json").is_file():
            skipped.append((d.name, "already described"))
        elif clip.get("kind") == "image" or not (clip.get("kind") == "video" or (clip.get("meta") or {}).get("duration_s")):
            skipped.append((d.name, "a picture: describing pictures is a later card"))
        elif not (clip.get("drive_id") or (d.parent / "map.json").is_file()):
            skipped.append((d.name, "no Drive id"))
        else:
            out.append((d, clip))
    return out, skipped


def describe_on_use(record_dirs, budget_usd: float, reason: str, *, brand: str, dry_run: bool = False,
                    runs: Path | None = None, one=None, now=None) -> dict:
    """Describe the undescribed video records given, cheapest-first never — in the order given (callers pass
    their best candidates first), stopping before a clip would start once `budget_usd` is spent.
    -> {described, kept, failed, skipped, spent_usd, stopped, would_describe, est_usd, ledger}."""
    runs = Path(runs or SP.runs_root())
    todo, skipped = _todo(record_dirs)
    res = {"reason": reason, "described": [], "failed": [], "skipped": skipped, "spent_usd": 0.0,
           "stopped": None, "would_describe": len(todo), "est_usd": round(sum(estimate(c) for _d, c in todo), 4),
           "ledger": None}
    if dry_run or not todo:
        return res
    if _quota_marker(brand, runs, now).is_file():
        res["stopped"] = "Drive download quota (already hit today) — nothing described"
        return res
    one = one or IR.one
    k, tok, av = IR.gb.key(), IR.DriveToken(), IR.avatars(brand)
    r, _why = IR.rate()
    rows, counts, t0 = [], {"recorded": 0, "kept": 0, "failed": 0, "not footage": 0}, time.time()
    try:
        for d, clip in todo:
            if res["spent_usd"] >= budget_usd:
                res["stopped"] = "budget $%.2f reached" % budget_usd
                break
            fid = clip.get("drive_id") or d.name
            label = clip.get("label") or ("Shared Assets/" + str(clip.get("path") or d.name))
            try:
                IR.drive_check(fid, tok)
                _cid, how, use = one(label, d.parent, brand, k, av, fid, tok, record_dir=d)
            except IR.QuotaExceeded as e:
                m = _quota_marker(brand, runs, now)
                m.parent.mkdir(parents=True, exist_ok=True)
                m.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "why": str(e)}) + "\n")
                res["stopped"] = "Drive download quota"
                counts["failed"] += 1
                res["failed"].append((d.name, "Drive download quota"))
                break
            except Exception as e:  # noqa: BLE001 — one clip never stops the rest
                counts["failed"] += 1
                res["failed"].append((d.name, "%s: %s" % (type(e).__name__, str(e)[:160])))
                continue
            counts[how] += 1
            if how == "recorded":
                res["described"].append(d.name)
            if use:
                rows.append(use)
                if r:
                    res["spent_usd"] = round(res["spent_usd"] + (use["prompt"] * r[0] + (use["candidates"] + use["thoughts"]) * r[1]) / 1e6, 6)
    finally:
        if rows or counts["failed"]:
            entry = IR.ledger(rows, dict(counts, reason=reason), time.time() - t0, brand, month_collection(now), runs=runs)
            res["ledger"] = entry
    return res


def records_under(brand: str, folder: str = "", ids=(), runs: Path | None = None) -> list:
    """Record folders whose label starts with `folder` (a "Shared Assets/…" label), or whose Drive id is in `ids`."""
    runs = Path(runs or SP.runs_root())
    want = set(ids or ())
    out = []
    for m in sorted((runs / brand).glob("*/map.json")):
        try:
            mp = json.loads(m.read_text())
        except ValueError:
            continue
        for fid, e in mp.items():
            if (want and fid in want) or (folder and str(e.get("label") or "").startswith(folder.rstrip("/") + "/")):
                out.append(m.parent / fid)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--folder", default="", help='a "Shared Assets/brands/<brand>/…" label prefix')
    ap.add_argument("--ids", default="", help="Drive ids, comma-separated")
    ap.add_argument("--budget", type=float, required=True, help="USD; checked before each clip starts")
    ap.add_argument("--reason", required=True, help="why these are described now (kept in the ledger)")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args(argv)
    recs = records_under(a.brand, a.folder, [i for i in a.ids.split(",") if i])
    res = describe_on_use(recs, a.budget, a.reason, brand=a.brand, dry_run=a.dry)
    print(json.dumps({k: v for k, v in res.items() if k != "skipped"} | {"skipped": len(res["skipped"])}
                     if sys.version_info >= (3, 9) else res, indent=1, default=str))
    return 0 if not res["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
