#!/usr/bin/python3
"""The mini's door into the Ad Desk READ — a lab-run turns a request into these two calls.

    lab-run → lab_entry.py --label L [--asof YYYY-MM-DD]
            → analyze.py $BRAND [--asof D]                  (writes runs/media-buying/<brand>/<asof>/)
            → desk_page.py $BRAND --out $OUT/<label>/desk.html
            → report.json + REPORT.md copied into $OUT/<label>/

Why it is hand-written (LD-7 (four more doors)): analyze.py takes the brand
POSITIONALLY (analyze.py:246), which a lab_door.json manifest cannot express;
the argument pairs and their refusals are run-kit's shared door
(run_kit/lab_door.py), reused here rather than copied.

THE READ ONLY: this door never runs decide.py (it records owner's calls) or
act.py (it changes ads in Meta). Either word anywhere in an argument — a name
or a value, `decide.py`, `--act`, `act-1` — is refused before anything runs.

Refuses (exit 2, named, before anything runs): a missing $BRAND or $OUT; any
argument but --asof and --label; an --asof that is not a real YYYY-MM-DD date;
a missing or malformed --label; an existing $OUT/<label>/. analyze.py failing
stops the run before desk_page.py, so no stale page is made.
"""
import os
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                   # components/media-buying/machine → repo root (analyze.py ROOT)
sys.path.append(str(REPO / "components" / "run-kit"))
from run_kit import lab_door as D        # noqa: E402  pairs, Refused, NAME

NEVER = ("decide", "act")                # decide.py records calls (:66-67); act.py acts in Meta (:37)
ACCEPTS = ("asof", "label")
ASOF = re.compile(r"\d{4}-\d{2}-\d{2}")
REPORT = ("report.json", "REPORT.md")


def never_hit(argv):
    """(word, argument) when decide or act is a word of any argument, else None."""
    for tok in argv:
        ws = [w for w in re.split(r"[^a-z0-9]+", str(tok).lower()) if w]
        for bad in NEVER:
            if bad in ws:
                return bad, tok
    return None


def asof_of(value):
    """The run's date folder. Not given: yesterday, analyze.py's own default (:166)."""
    if not value:
        return str(date.today() - timedelta(days=1))
    if not ASOF.fullmatch(value):
        raise D.Refused(f"--asof {value!r}: a date, YYYY-MM-DD")
    try:
        date(*map(int, value.split("-")))
    except ValueError:
        raise D.Refused(f"--asof {value!r} is not a real date")
    return value


def commands(brand, asof, dest):
    """analyze.py first, then desk_page.py — the brand positional in both."""
    analyze = [sys.executable, str(HERE / "analyze.py"), brand]
    if asof:
        analyze += ["--asof", asof]
    page = [sys.executable, str(HERE / "desk_page.py"), brand, "--out", str(dest / "desk.html")]
    return analyze, page


def main(argv=None, env=None, run=subprocess.call, repo=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    env = os.environ if env is None else env
    repo = Path(repo).resolve() if repo else REPO
    try:
        hit = never_hit(argv)
        if hit:
            raise D.Refused(f"{hit[1]!r} names {hit[0]} — this door reads the desk only; "
                            "decide.py and act.py are owner's, by hand")
        missing = [n for n in ("BRAND", "OUT") if not env.get(n)]
        if missing:
            raise D.Refused(f"${' and $'.join(missing)} not set — lab-run sets them; "
                            "run analyze.py and desk_page.py directly by hand")
        brand, out = env["BRAND"], Path(env["OUT"])
        if not D.NAME.fullmatch(brand):
            raise D.Refused(f"$BRAND {brand!r} is not a plain name")
        args = D.pairs(argv)
        unknown = sorted(set(args) - set(ACCEPTS))
        if unknown:
            why = " — $BRAND comes from lab-run" if "brand" in unknown else ""
            raise D.Refused(f"unknown argument(s) {', '.join('--' + u for u in unknown)}; "
                            f"this door takes only --asof and --label{why}")
        label = args.get("label", "")
        if not D.NAME.fullmatch(label):
            raise D.Refused(f"--label {label!r}: a plain name is required — the read lands in $OUT/<label>/")
        given = args.get("asof", "")
        asof = asof_of(given)
        dest = out / label
        if dest.exists():
            raise D.Refused(f"{dest} already exists — refusing to overwrite it")
    except D.Refused as e:
        print(f"lab_entry: {e}")
        return 2
    dest.mkdir(parents=True)
    analyze, page = commands(brand, given, dest)
    print("running: " + " ".join(analyze))
    rc = run(analyze, env=dict(env))
    if rc:
        print(f"lab_entry: analyze.py failed (exit {rc}) — desk_page.py not run")
        return rc
    print("running: " + " ".join(page))
    rc = run(page, env=dict(env))
    made = repo / "runs" / "media-buying" / brand / asof
    lost = []
    for name in REPORT:
        if (made / name).is_file():
            shutil.copy2(str(made / name), str(dest / name))
        else:
            lost.append(name)
    if lost:
        print(f"lab_entry: {', '.join(lost)} not found in {made}")
        return rc or 1
    print(f"lab_entry: desk read → {dest}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
