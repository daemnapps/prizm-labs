"""THE QC LOG — every QC round on a run, filed in the repo beside the run
(the owner, 2026-10-02: "each qc log needs to be filed in the repo … so improvements
to the chain can be made").

    <run>/qc-log/QC-LOG.md                      one row per round, newest last
    <run>/qc-log/<step>-r<N>-<by>.json          the raw findings of that round

Nobody writes a row by hand: `qc.py` files its own round every time it runs, and
the reviewer's findings are filed with `add`. A row says what was checked, by
what, how many passed and were sent back, the causes, and the CHAIN-FIXES row
that fixed them (filled in by `fix` once the chain is changed).

    python3 qc_log.py add <run> --step pictures --by reviewer --findings f.json [--method "..."] [--causes "..."]
    python3 qc_log.py fix <run> --round N --fix "CHAIN-FIXES 55 — ..."
    python3 qc_log.py show <run>

Findings may be a list of {station, finding, fix_at} (qc.py) or a dict of
{id: {ok, severity, problems, ...}} (the picture reviewer). Brand-agnostic.
"""
from __future__ import annotations

import argparse, json, re, sys, time
from pathlib import Path

HEAD = """# QC log

Every QC round on this run, filed automatically (`machine/qc_log.py`). One row per
round; the raw findings sit beside this file. A cause that would recur becomes a
chain change, named in the last column (components/video-teardown/CHAIN-FIXES.md).

| Round | When | Step | Checked by | Method | Passed | Sent back | Causes | Chain fix | Findings |
|---|---|---|---|---|---|---|---|---|---|
"""


def _cell(s) -> str:
    return " ".join(str(s or "—").split()).replace("|", "/")


def tally(findings) -> tuple[int | None, int, list[str]]:
    """(passed, sent back, short causes) from either findings shape."""
    if isinstance(findings, dict):
        ids = {k: v for k, v in findings.items() if not str(k).startswith("_") and isinstance(v, dict)}
        bad = {k: v for k, v in ids.items() if not v.get("ok")}
        causes = [f"{k}: {(v.get('problems') or [''])[0]}" for k, v in bad.items()]
        return len(ids) - len(bad), len(bad), causes
    rows = list(findings or [])
    return None, len(rows), [f"[{r.get('station')}] {r.get('finding')}" for r in rows]


def rounds(run: Path) -> list[str]:
    f = Path(run) / "qc-log" / "QC-LOG.md"
    return [l for l in f.read_text().splitlines() if re.match(r"^\| \d+ \|", l)] if f.exists() else []


def add(run, step: str, by: str, findings, method: str = "", causes: str = "", fix: str = "") -> int:
    run = Path(run)
    d = run / "qc-log"
    d.mkdir(parents=True, exist_ok=True)
    log = d / "QC-LOG.md"
    if not log.exists():
        log.write_text(HEAD)
    n = len(rounds(run)) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", step.lower()).strip("-")
    raw = d / f"{slug}-r{n}-{re.sub(r'[^a-z0-9]+', '-', by.lower()).strip('-')}.json"
    raw.write_text(json.dumps(findings, indent=1, ensure_ascii=False) + "\n")
    passed, back, auto = tally(findings)
    why = causes or ("; ".join(auto[:6]) + (f"; +{len(auto) - 6} more" if len(auto) > 6 else "") if auto else "clean")
    row = (f"| {n} | {time.strftime('%Y-%m-%d %H:%M')} | {_cell(step)} | {_cell(by)} | {_cell(method)} | "
           f"{'—' if passed is None else passed} | {back} | {_cell(why)} | {_cell(fix)} | `{raw.name}` |")
    with log.open("a") as fh:
        fh.write(row + "\n")
    return n


def fix(run, n: int, text: str) -> bool:
    log = Path(run) / "qc-log" / "QC-LOG.md"
    lines = log.read_text().splitlines()
    for i, l in enumerate(lines):
        if l.startswith(f"| {n} |"):
            cells = l.split(" | ")
            cells[-2] = _cell(text)
            lines[i] = " | ".join(cells)
            log.write_text("\n".join(lines) + "\n")
            return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("run"); a.add_argument("--step", required=True)
    a.add_argument("--by", required=True); a.add_argument("--findings", required=True)
    a.add_argument("--method", default=""); a.add_argument("--causes", default=""); a.add_argument("--fix", default="")
    f = sub.add_parser("fix"); f.add_argument("run"); f.add_argument("--round", type=int, required=True); f.add_argument("--fix", required=True)
    s = sub.add_parser("show"); s.add_argument("run")
    x = ap.parse_args(argv)
    if x.cmd == "add":
        n = add(x.run, x.step, x.by, json.loads(Path(x.findings).read_text()), x.method, x.causes, x.fix)
        print(f"filed round {n} → {Path(x.run) / 'qc-log' / 'QC-LOG.md'}")
    elif x.cmd == "fix":
        print("ok" if fix(x.run, x.round, x.fix) else "no such round"); 
    else:
        print((Path(x.run) / "qc-log" / "QC-LOG.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
