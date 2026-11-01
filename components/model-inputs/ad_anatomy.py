"""Ad anatomy scoreboard: what the winning swipes do, dial by dial.

Joins every swipe the image teardown has already broken down (its dials, its
element labels, its swap list) with how well that swipe performed, and writes
one scoreboard a picture-ad tool can read next to each control.

Read only. It re-runs nothing, calls no model and spends nothing.

    python3 components/model-inputs/ad_anatomy.py            # every brand
    python3 components/model-inputs/ad_anatomy.py brand-a     # one brand

Writes runs/ad-anatomy/scoreboard.json (only when run as a script).
"""
from __future__ import print_function

import datetime
import glob
import json
import math
import os
import re
import statistics
import sys
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEARDOWN_RUNS = os.path.join(ROOT, "tools", "image-teardown", "runs")   # the old working home, read for one release
LANE_RUNS = os.path.join(ROOT, "runs", "image-teardown")
ORGANIC_ROOT = os.path.join(ROOT, "runs", "swipe-organic")
PAID_ROOT = os.path.join(ROOT, "components", "swipe-paid")
OUT_PATH = os.path.join(ROOT, "runs", "ad-anatomy", "scoreboard.json")

LABEL_LISTS = ("format/image", "style/image", "framework/all", "doctrine/awareness")
TIERS = {"top": 3, "middle": 2, "bottom": 1}

SCORE_RULE = (
    "Each swipe gets its real number (organic: views, or likes when the post only "
    "shows likes; paid: days the ad ran, else how many times the advertiser rebuilt it, "
    "else its top/middle/bottom tier), then is "
    "ranked against the other swipes of the same brand, same kind and same number "
    "type, and its score is that percentile from 0 (lowest) to 1 (highest), "
    "ties sharing the average rank and a lone swipe getting 0.5."
)


# ---------------------------------------------------------------- reading

def _load(path):
    # type: (str) -> Optional[object]
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def _num(v):
    # type: (object) -> Optional[float]
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _walk(obj):
    """Every dict inside a loaded JSON value."""
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            yield o
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)


_PREFIX = re.compile(r"^(tt|ig|igp)-", re.I)


def organic_index(root=ORGANIC_ROOT):
    # type: (str) -> Dict[str, Dict[str, float]]
    """post id -> {"views": n, "likes": n} from every research record."""
    idx = {}  # type: Dict[str, Dict[str, float]]
    for path in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        data = _load(path)
        if data is None:
            continue
        for d in _walk(data):
            pid = None
            for key in ("videoId", "aweme_id", "video_id", "code", "shortcode", "id"):
                v = d.get(key)
                if isinstance(v, (str, int)) and not isinstance(v, bool) and str(v):
                    pid = _PREFIX.sub("", str(v))
                    break
            if not pid:
                continue
            stats = d.get("stats") if isinstance(d.get("stats"), dict) else {}
            views = None
            for src in (d, stats):
                for key in ("viewCount", "playCount", "views", "play_count", "view_count"):
                    views = views if views is not None else _num(src.get(key))
            likes = None
            for src in (d, stats):
                for key in ("likeCount", "likes", "diggCount", "like_count"):
                    likes = likes if likes is not None else _num(src.get(key))
            if views is None and likes is None:
                continue
            rec = idx.setdefault(pid, {})
            if views is not None:
                rec["views"] = max(rec.get("views", 0.0), views)
            if likes is not None:
                rec["likes"] = max(rec.get("likes", 0.0), likes)
    return idx


def paid_index(root=PAID_ROOT):
    # type: (str) -> Tuple[Dict[str, float], Dict[str, List[str]]]
    """(ad id -> days the ad ran, block file name -> its ad ids) from the paid pulls."""
    days = {}  # type: Dict[str, float]
    blocks = {}  # type: Dict[str, List[str]]
    for path in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        if "__pycache__" in path:
            continue
        data = _load(path)
        if data is None:
            continue
        for d in _walk(data):
            if "id" in d and _num(d.get("days_total")) is not None:
                key = str(d["id"])
                days[key] = max(days.get(key, 0.0), float(d["days_total"]))
            if isinstance(d.get("slug"), str) and isinstance(d.get("ad_ids"), list):
                blocks[d["slug"]] = [str(a) for a in d["ad_ids"]]
    return days, blocks


def _lane_source(run):
    # type: (str) -> Tuple[Optional[str], dict]
    for path in sorted(glob.glob(os.path.join(LANE_RUNS, "*", run, "source.json"))):
        brand = path.split(os.sep)[-3]
        if brand.startswith("_"):
            continue
        return brand, _load(path) or {}
    return None, {}


def _brand_from_name(run):
    # type: (str) -> Optional[str]
    head = run.split("-", 1)[0]
    if head and os.path.isdir(os.path.join(LANE_RUNS, head)) and not head.startswith("_"):
        return head
    return None


# ---------------------------------------------------------------- numbers

def _short(n):
    # type: (float) -> str
    for size, tag in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= size:
            return ("%.1f" % (n / size)).rstrip("0").rstrip(".") + tag
    return str(int(n))


def _organic_number(run, source, oidx):
    # type: (str, dict, dict) -> Optional[Tuple[str, float]]
    files = " ".join(source.get("files") or [])
    cands = re.findall(r"\d{15,20}", files + " " + run)
    for f in source.get("files") or []:
        base = os.path.splitext(os.path.basename(f))[0]
        cands.append(_PREFIX.sub("", base))
    for c in cands:
        rec = oidx.get(c)
        if rec and "views" in rec:
            return "views", rec["views"]
    for c in cands:
        rec = oidx.get(c)
        if rec and "likes" in rec:
            return "likes", rec["likes"]
    return None


def _paid_number(run, source, days, blocks):
    # type: (str, dict, dict, dict) -> Optional[Tuple[str, float]]
    cands = []
    still = source.get("still")
    if still:
        cands.append(os.path.splitext(os.path.basename(str(still)))[0])
    cands += re.findall(r"(?<!\d)(\d{9})(?!\d)", run + " " + str(source.get("block", "")))
    for c in cands:
        if c in days:
            return "days", days[c]
    slug = os.path.splitext(os.path.basename(str(source.get("block_file") or "")))[0]
    ran = [days[a] for a in blocks.get(slug, []) if a in days]
    if ran:
        return "days", max(ran)
    heat = _num(source.get("heat"))
    if heat is not None:
        return "rebuilt", heat
    m = re.search(r"-(top|middle|bottom)-", run)
    if m:
        return "tier", float(TIERS[m.group(1)])
    return None


def _score_from(metric, value):
    # type: (str, float) -> str
    if metric == "tier":
        return {3: "top", 2: "middle", 1: "bottom"}[int(value)] + " tier"
    if metric == "days":
        return "ran %d days" % int(value)
    if metric == "rebuilt":
        return "rebuilt %dx" % int(value)
    return "%s %s" % (metric, _short(value))


def percentiles(values):
    # type: (Dict[str, float]) -> Dict[str, float]
    """key -> 0..1 percentile rank; ties share their average rank; one item -> 0.5."""
    n = len(values)
    if n == 0:
        return {}
    if n == 1:
        return {k: 0.5 for k in values}
    order = sorted(values, key=lambda k: values[k])
    out = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j) / 2.0
        for k in order[i:j + 1]:
            out[k] = round(rank / (n - 1), 4)
        i = j + 1
    return out


# ---------------------------------------------------------------- tallies

def _median(xs):
    # type: (List[float]) -> Optional[float]
    if not xs:
        return None
    m = statistics.median(xs)
    return int(m) if float(m).is_integer() else m


def _cell(scores):
    # type: (List[Optional[float]]) -> dict
    got = [s for s in scores if s is not None]
    return {"count": len(scores), "avg_score": round(sum(got) / len(got), 3) if got else None}


def winners(per_swipe):
    # type: (Dict[str, dict]) -> List[str]
    """Runs in the top third by score (rounded up), best first."""
    scored = sorted((r for r in per_swipe if per_swipe[r].get("score") is not None),
                    key=lambda r: (-per_swipe[r]["score"], r))
    return scored[:int(math.ceil(len(scored) / 3.0))]


def tally(per_swipe):
    # type: (Dict[str, dict]) -> dict
    top = set(winners(per_swipe))
    dial_ids = sorted({d for s in per_swipe.values() for d in s.get("dials", {})})
    dials = {}
    for d in dial_ids:
        by_level = {}  # type: Dict[int, List[Optional[float]]]
        all_lv, win_lv = [], []
        for run, s in per_swipe.items():
            if d not in s.get("dials", {}):
                continue
            lv = s["dials"][d]
            by_level.setdefault(lv, []).append(s.get("score"))
            all_lv.append(lv)
            if run in top:
                win_lv.append(lv)
        dials[d] = {
            "levels": {str(lv): _cell(by_level[lv]) for lv in sorted(by_level)},
            "winners_level": _median(win_lv),
            "all_level": _median(all_lv),
        }

    labels = {}  # type: Dict[str, Dict[str, dict]]
    for name in LABEL_LISTS:
        groups = {}  # type: Dict[str, List[Optional[float]]]
        for s in per_swipe.values():
            lab = s.get("labels", {}).get(name)
            if lab:
                groups.setdefault(lab, []).append(s.get("score"))
        labels[name] = {k: _cell(v) for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))}

    pif = {"yes": [], "no": []}  # type: Dict[str, List[Optional[float]]]
    kinds = {}  # type: Dict[str, List[Optional[float]]]
    words = {}  # type: Dict[str, List[Optional[float]]]
    for s in per_swipe.values():
        if s.get("product_in_frame") is True:
            pif["yes"].append(s.get("score"))
        elif s.get("product_in_frame") is False:
            pif["no"].append(s.get("score"))
        for k in s.get("kinds", {}):
            kinds.setdefault(k, []).append(s.get("score"))
        if s.get("words"):
            words.setdefault(s["words"], []).append(s.get("score"))
    return {
        "dials": dials,
        "labels": labels,
        "product_in_frame": {k: _cell(v) for k, v in pif.items()},
        "swap_kinds": {k: _cell(v) for k, v in sorted(kinds.items())},
        "words": {k: _cell(v) for k, v in sorted(words.items())},
        "winners": sorted(top),
    }


def score_swipes(per_swipe, numbers):
    # type: (Dict[str, dict], Dict[str, Tuple[str, float]]) -> None
    """Fill score / score_from in place: percentile within (brand, kind, number type)."""
    pools = {}  # type: Dict[Tuple, Dict[str, float]]
    for run, (metric, value) in numbers.items():
        s = per_swipe[run]
        pools.setdefault((s.get("brand"), s.get("kind"), metric), {})[run] = value
    for pool in pools.values():
        for run, p in percentiles(pool).items():
            per_swipe[run]["score"] = p
    for run, s in per_swipe.items():
        if run in numbers:
            s["score_from"] = _score_from(*numbers[run])
        else:
            s.setdefault("score", None)
            s["score_from"] = None


# ---------------------------------------------------------------- build

def _run_homes():
    # type: () -> Dict[str, str]
    """Every picture run's working folder by name: runs/image-teardown/<brand>/<run>/ (its one home since
    2026-10-28) where it holds out/, then the old lane folder for any run a checkout has not moved yet."""
    homes = {}  # type: Dict[str, str]
    for out in sorted(glob.glob(os.path.join(LANE_RUNS, "*", "*", "out"))):
        d = os.path.dirname(out)
        homes.setdefault(os.path.basename(d), d)
    if os.path.isdir(TEARDOWN_RUNS):
        for run in sorted(os.listdir(TEARDOWN_RUNS)):
            if os.path.isdir(os.path.join(TEARDOWN_RUNS, run)):
                homes.setdefault(run, os.path.join(TEARDOWN_RUNS, run))
    return homes


def _run_home(run):
    # type: (str) -> str
    return _run_homes().get(run) or os.path.join(TEARDOWN_RUNS, run)


def _read_swipe(run):
    # type: (str) -> Optional[dict]
    out = os.path.join(_run_home(run), "out")
    controls = _load(os.path.join(out, "controls-swipe.json"))
    elements = _load(os.path.join(out, "elements.json"))
    swaps = _load(os.path.join(out, "swaps.json"))
    if controls is None and elements is None:
        return None  # no read of a swipe (e.g. our own concept runs): not a swipe
    dials = {}
    for d, v in ((controls or {}).get("dials") or {}).items():
        lv = v.get("level") if isinstance(v, dict) else v
        if isinstance(lv, int) and not isinstance(lv, bool):
            dials[d] = lv
    labels = {k: v for k, v in ((elements or {}).get("labels") or {}).items() if k in LABEL_LISTS}
    kinds = {}  # type: Dict[str, int]
    for sw in (swaps or {}).get("swaps") or []:
        k = sw.get("kind") if isinstance(sw, dict) else None
        if k:
            kinds[k] = kinds.get(k, 0) + 1
    pif = (swaps or {}).get("product_in_frame")
    return {
        "dials": dials,
        "labels": labels,
        "kinds": kinds,
        "words": (swaps or {}).get("words"),
        "product_in_frame": pif if isinstance(pif, bool) else None,
    }


def build(brand=None):
    # type: (Optional[str]) -> dict
    oidx = organic_index()
    days, blocks = paid_index()
    per_swipe = {}  # type: Dict[str, dict]
    numbers = {}  # type: Dict[str, Tuple[str, float]]
    for run in sorted(_run_homes()):
        swipe = _read_swipe(run)
        if swipe is None:
            continue
        b, source = _lane_source(run)
        b = b or _brand_from_name(run)
        if brand and b != brand:
            continue
        kind = source.get("swipe_kind")
        num = None
        if kind == "organic":
            num = _organic_number(run, source, oidx)
        elif kind == "paid":
            num = _paid_number(run, source, days, blocks)
        elif kind is None:
            num = _paid_number(run, source, days, blocks)
            kind = "paid" if num else None
        rec = {"brand": b, "kind": kind, "score": None, "score_from": None}
        rec.update(swipe)
        per_swipe[run] = rec
        if num:
            numbers[run] = num
    score_swipes(per_swipe, numbers)
    board = {
        "built": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "brand": brand,
        "swipes": len(per_swipe),
        "with_score": sum(1 for s in per_swipe.values() if s["score"] is not None),
        "score_rule": SCORE_RULE,
        "per_swipe": per_swipe,
    }
    board.update(tally(per_swipe))
    return board


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    argv = sys.argv[1:] if argv is None else argv
    board = build(brand=argv[0] if argv else None)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump(board, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print("%d swipes, %d with a score -> %s" % (board["swipes"], board["with_score"],
                                                os.path.relpath(OUT_PATH, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
