#!/usr/bin/env python3
"""The gates this chain runs, and the record every run files.

Two of the five shared gates (`components/quality-checks`) apply to a teardown:

    elements   after stage 2b   every label is a real row in the element
                                library, or an honest `none-fits`
    copy       after stage 6    the brief carries no UNFILLED note, and every
                                price in the part that gets built is one the
                                brand's own offer bank sells today

`hold()` writes `check.json` into the run and raises `Held`. **A held run says
why**: the problems are in `check.json`, printed when it happens, and carried
into the filed record.

    gates.py <run>              print a run's check.json, plainly

Filing: every completed run's record goes to
`runs/image-teardown/<brand>/<label>/` at the repo root — stage text,
`elements.json`, `source.json`, `run.json`, `check.json`. Never media.
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

MODES = ("hold", "warn")


def quality():
    """The shared checks — components/quality-checks."""
    if str(P.QUALITY) not in sys.path:
        sys.path.insert(0, str(P.QUALITY))
    import quality_checks as Q
    return Q


def _gate(name, problems, run, mode):
    """Run one gate. `hold` raises Held; `warn` records the same check.json,
    prints why, and lets the run carry on."""
    Q = quality()
    try:
        Q.hold(name, problems, Path(run))
        return True
    except Q.Held as e:
        print(f"  ✗ {e}")
        if mode == "hold":
            raise
        print(f"  (gates are on warn — carrying on; check.json still says HELD)")
        return False


def elements_gate(run, problems, mode="hold"):
    return _gate("elements", problems, run, mode)


def built_part(brief):
    """Documents one and two — what a designer builds from. Document three is
    the internal evidence table, which quotes the SOURCE ad and the market
    (a competitor's price, what a clinic charges) and is not our copy."""
    m = re.search(r"^##\s*DOCUMENT THREE\b", brief, re.M | re.I)
    return brief[:m.start()] if m else brief


def copy_problems(brief, bank_text, product):
    Q = quality()
    problems = list(Q.unfilled_check(brief))
    block = Q.offer_block(bank_text, product) if product else ""
    label = product if block else None
    # No entry under this product's key is not "no offer": brands key their
    # bank differently, so fall back to the whole bank rather than holding
    # every brief of a brand whose keys differ from its product slugs.
    problems += Q.price_check(built_part(brief), block or bank_text, label)
    return problems


def copy_gate(run, brand, product, mode="hold"):
    run = Path(run)
    brief = (run / "out/06-brief.md").read_text(errors="replace")
    bank = P.brand(brand)["offer"]
    bank_text = bank.read_text(errors="replace") if bank.is_file() else ""
    return _gate("copy", copy_problems(brief, bank_text, product), run, mode)


def state(run):
    f = Path(run) / "check.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


def held(run, gates=None):
    """{gate: [problems]} for every gate this run is held at."""
    return {g: v.get("problems", []) for g, v in state(run).items()
            if v.get("result") == "HELD" and (gates is None or g in gates)}


# ------------------------------------------------------------------ filing

def file_record(brand, run_name):
    """Copy a run's record — stage text, labels, the swipe's index, the gates —
    to runs/image-teardown/<brand>/<label>/ at the repo root (git). Working
    files stay in the lane; pictures never travel."""
    src = P.RUNS / run_name
    dst = P.RECORDS / brand / run_name
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob("out/0*.md")):
        shutil.copy(f, dst / f.name)
    for f in ("variant.json", "check.json", "out/elements.json"):
        if (src / f).is_file():
            shutil.copy(src / f, dst / Path(f).name)
    if (src / "assets/source.json").is_file():
        shutil.copy(src / "assets/source.json", dst / "source.json")
    try:
        lane_run = str(src.relative_to(P.REPO))
    except ValueError:
        lane_run = str(src)
    h = held(src)
    (dst / "run.json").write_text(json.dumps(
        {"machine": P.TOOL, "brand": brand, "label": run_name,
         "lane_run": lane_run,
         "stages": sorted(f.name for f in dst.glob("0*.md")),
         "state": "held" if h else "filed", "held": h,
         "filed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        indent=1, ensure_ascii=False) + "\n")
    return dst


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = Path(sys.argv[1])
    r = r if r.is_absolute() else P.RUNS / r.name
    st = state(r)
    if not st:
        print(f"{r.name}: no gate has run yet")
    for g, v in st.items():
        print(f"{g}: {v.get('result')}")
        for p in v.get("problems", []):
            print(f"   - {p}")
