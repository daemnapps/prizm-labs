#!/usr/bin/env python3
"""The month's two gates, and the copy of the month that goes to the repo's
one home for run records (rollout, 2026-09-20).

THE GATES — recorded, never raised. `components/quality-checks` stops failing
work by raising `Held`; the calendar's own rule is *"adoption stays a human
act"*, so a month that fails a gate is still written, still drawn on the board,
and says HELD in `check.json` for the person reviewing it. The review board is
the Review.

    inputs    before any model runs: can this brand run the chain? A blocked
              layer is HELD (and the run stops, as it always has); a degraded
              one passes with a note saying what the month loses
    elements  after layer 6 and again on the finished slots: every send's
              `type` is an email format — it must be in the element library
              (components/elements, `format/email`) OR in the brand's own
              `email-sms/email-types.json`. In neither is a BREAK in checks.md

THE FILING — `runs/marketing-calendar/<brand>/<month>/` at the repo root
(`runs/README.md`: a machine's record must not live beside its code) is now
THE home of the working month (SI-22 (calendar months home), 2026-10-07):
calendar.py writes there, and the review board and email production read it
there. One home, no second copy — so a month that is already home is never
filed again. `file_month` still copies a month held anywhere else (an old
`calendar-<month>[-<brand>]` folder, a hand-made one) onto its shelf: text
only, never over 1 MB, never the board's HTML. It never deletes and never
fails a month: the caller wraps it, so a problem prints SKIP and the month is
whole.

Switch the filing off: `MC_NO_REPO_FILING=1`.

    python3 gates.py                 list every month on the shelf (already home)
    python3 gates.py <run-folder>    file one held somewhere else
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import paths as P

TOOL = "marketing-calendar"
OFF_ENV = "MC_NO_REPO_FILING"
MAX_BYTES = 1_000_000
TOP_FILES = ("run.json", "slots.json", "checks.md", "check.json")
TEXT_SUFFIXES = (".md", ".json")
ELEMENT, ASSET = "format", "email"


# ------------------------------------------------------------- elements ---

def _library():
    """components/elements/machine/elements.py, found under the workspace."""
    d = P.WORKSPACE / "components" / "elements" / "machine"
    if not (d / "elements.py").is_file():
        return None
    if str(d) not in sys.path:
        sys.path.append(str(d))
    try:
        import elements as E
        return E
    except Exception:
        return None


def library_ids():
    """Every email format the element library knows. Empty when it cannot be
    read — which the caller says out loud rather than treating as 'all wrong'."""
    E = _library()
    if not E:
        return set()
    try:
        return {r["id"] for r in E.rows(ELEMENT, ASSET)}
    except Exception:
        return set()


def brand_type_ids(brand_root):
    """The brand's OWN catalogue — it may carry a format nobody else has."""
    try:
        cat = json.loads((Path(brand_root) / "email-sms" / "email-types.json").read_text())
        return {t["key"] for t in cat.get("types") or [] if t.get("key")}
    except (OSError, ValueError, AttributeError):
        return set()


def _nearest(bad, ids, n=5):
    parts = set(str(bad).lower().split("-"))
    return sorted(ids, key=lambda k: (-len(parts & set(k.split("-"))), k))[:n]


def type_problems(types_seen, brand_root, dropped=()):
    """-> (breaks, warnings, picked).

    `types_seen`  the type of every slot in the finished month
    `dropped`     what layer 6 dropped for not being in the brand's catalogue
    `picked`      {type: {"from": library|brand|both|unknown, "sends": n}} —
                  what goes into run.json"""
    lib, own = library_ids(), brand_type_ids(brand_root)
    known = lib | own
    breaks, warns, picked = [], [], {}
    if not lib:
        warns.append("the element library (components/elements, format/email) could not "
                     "be read, so types were checked against the brand's catalogue alone")
    for t in types_seen:
        row = picked.setdefault(t, {"from": ("both" if t in lib and t in own else
                                             "library" if t in lib else
                                             "brand" if t in own else "unknown"), "sends": 0})
        row["sends"] += 1
    for t in sorted({str(x) for x in list(types_seen) + list(dropped)}):
        if t in known:
            if t in dropped:
                warns.append(f"`{t}` is an email format the element library knows, and this "
                             f"brand's catalogue does not carry it — the send was dropped. "
                             f"Add it to the brand's email/email-types.json to plan with it.")
            continue
        where = "was dropped at layer 6" if t in dropped else "is on a send in this month"
        breaks.append(
            f"`{t}` is not an email format — it {where}. It is in neither the element "
            f"library (format/email) nor this brand's email/email-types.json. Nearest real "
            f"ids: {', '.join(f'`{k}`' for k in _nearest(t, known)) or 'none'}. "
            f"All {len(known)}: {', '.join(sorted(known))}.")
    return breaks, warns, picked


# ---------------------------------------------------------------- gates ---

def _quality():
    d = P.WORKSPACE / "components" / "quality-checks"
    if str(d) not in sys.path:
        sys.path.append(str(d))
    try:
        import marketing_chain_checks as Q
        return Q
    except Exception:
        return None


def record(gate, problems, out_dir, notes=()):
    """Write one gate's result into <month>/check.json — `hold()`'s file, in
    `hold()`'s shape — and NEVER stop the month. -> "pass" | "HELD"."""
    problems = [p for p in problems if p]
    out_dir = Path(out_dir)
    Q = _quality()
    if Q:
        try:
            Q.hold(gate, problems, out_dir)
        except Q.Held:
            pass                       # recorded; adoption stays a human act
    f = out_dir / "check.json"
    state = json.loads(f.read_text()) if f.is_file() else {}
    if not Q:                          # no shared checks in this checkout — same shape, by hand
        state[gate] = {"result": "pass" if not problems else "HELD", "problems": problems}
    if notes:
        state[gate]["notes"] = list(notes)
    f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    return state[gate]["result"]


def inputs_gate(ready, out_dir):
    """`ready` is `chain.readiness(brand_root)`."""
    problems, notes = [], []
    for L in ready:
        if L["verdict"] == "blocked":
            miss = ", ".join(r["path"] for r in L["needs"] if r["required"] and not r["have"])
            problems.append(f"layer {L['n']} {L['name']} cannot run — it needs {miss}")
        elif L["verdict"] == "degraded":
            notes.append(f"layer {L['n']} {L['name']} runs with less: " + " · ".join(L["losing"]))
    return record("inputs", problems, out_dir, notes)


# --------------------------------------------------------------- filing ---

def _safe(s):
    return re.sub(r"[^a-z0-9-]+", "-", str(s or "").lower()).strip("-")


def repo_root():
    """The workspace this tool reads and files into — paths' one locator."""
    return P.WORKSPACE


def repo_home(brand, month, repo=None):
    return Path(repo or repo_root()) / "runs" / TOOL / _safe(brand) / _safe(month)


def _wanted(run_dir):
    run_dir = Path(run_dir)
    for name in TOP_FILES:
        if (run_dir / name).is_file():
            yield run_dir / name, Path(name)
    for d in sorted(p for p in run_dir.iterdir() if p.is_dir() and re.match(r"\d-", p.name)):
        for f in sorted(d.rglob("*")):
            if f.is_file() and f.suffix in TEXT_SUFFIXES:
                yield f, f.relative_to(run_dir)


def file_month(run_dir, repo=None):
    """Copy one month's text to the repo-root home. -> (dest, copied, left_out).
    Raises on a month with no brand or no month — those ARE the filing key."""
    run_dir = Path(run_dir)
    st = json.loads((run_dir / "run.json").read_text())
    brand, month = _safe(st.get("brand")), _safe(st.get("month"))
    if not brand or not month:
        raise ValueError(f"{run_dir.name}: run.json names no brand or no month, "
                         "so there is no shelf to file it on")
    dest = repo_home(brand, month, repo)
    copied, left_out = [], []
    for src, relp in _wanted(run_dir):
        if src.stat().st_size > MAX_BYTES:
            left_out.append(f"{relp} (over 1 MB)")
            continue
        try:
            src.read_text(encoding="utf-8")            # text, or it does not go
        except (UnicodeDecodeError, OSError):
            left_out.append(f"{relp} (not text)")
            continue
        out = dest / relp
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.is_file() or out.read_bytes() != src.read_bytes():
            shutil.copyfile(src, out)
        copied.append(str(relp))
    return dest, copied, left_out


def _is_home(run_dir, repo=None):
    """True when the month is already on its shelf — under paths.RUNS, or at
    repo_home(brand, month) for the repo given."""
    run_dir = Path(run_dir).resolve()
    if repo is None and P.RUNS.resolve() in run_dir.parents:
        return True
    try:
        st = json.loads((run_dir / "run.json").read_text())
    except (OSError, ValueError):
        return False
    return run_dir == repo_home(st.get("brand"), st.get("month"), repo).resolve()


def file_after_run(run_dir, repo=None):
    """The end-of-run call. -> a one-line note, or None when it does not apply.

    A month calendar.py wrote is already home (runs/marketing-calendar/<brand>/
    <month>/), so this files nothing — one home, no second copy. A test or a
    scratch run points `--out` somewhere else, and must never be able to write
    into runs/marketing-calendar/ either. Only an explicit `repo` files."""
    if os.environ.get(OFF_ENV):
        return None
    if _is_home(run_dir, repo):
        return None
    if repo is None:
        return None
    dest, copied, left_out = file_month(run_dir, repo)
    return (f"{len(copied)} text file(s) -> {P.rel(dest)}"
            + (f" · left out: {', '.join(left_out)}" if left_out else ""))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        found = P.months()
        for d in found:
            print(f"  {P.rel(d)}: already home")
        print(f"{len(found)} month(s) already home under runs/{TOOL}/")
        return 0
    n = 0
    for a in argv:
        d = Path(a) if Path(a).is_dir() else P.RUNS / a
        try:
            if _is_home(d):
                print(f"  {P.rel(d)}: already home")
                continue
            dest, copied, left_out = file_month(d)
            print(f"  {d.name}: {len(copied)} file(s) -> {P.rel(dest)}"
                  + (f" · left out: {', '.join(left_out)}" if left_out else ""))
            n += 1
        except Exception as e:
            print(f"  {d.name}: SKIP — {e}")
    print(f"{n} month(s) filed under runs/{TOOL}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
