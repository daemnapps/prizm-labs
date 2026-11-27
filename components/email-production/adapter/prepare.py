"""Make a brand's designed emails whole on this Mac before the emails page shows them (the team's lab, 2026-10-21).

    prepare.py [--brand <brand>]          rebuild every email whose built pictures are missing or older than its layout
    prepare.py --brand <brand> --dry-run  only say which ones

Why: an email's built pictures (`klaviyo/assets/*.jpg`) are media, so git never carries them. On a Mac that did not
build the email (the team's, or the team's after the team changed one), the email shows only its alt text and its Go cannot
upload the pictures. Rebuilding with email-production's own `design/build.py` makes them again, reading the source
pictures from the Drive with this person's GDRIVE_SA_KEY (about a minute per email).

The rebuild keeps the card as it was: build.py rewrites `klaviyo/card.json` and does not carry `sections_ok` (the
parts marked right), so this puts those fields back afterwards (keep_card). Proposed to the owner as a one-line change
in build.py's kept keys; until then the guard lives here and in ask.py.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(d for d in HERE.parents if (d / "components" / "run-kit").is_dir()) / "components" / "run-kit"))
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
EM = REPO / "tools" / "email-production"
RUNS = REPO / "runs" / "email-production"
KEEP = ("sections_ok", "eve_done")   # card fields build.py drops on a rebuild (sections_ok is kept by build.py since b7a55cac52)
STAMPS = Path.home() / ".upright" / "cache" / "emails-built.json"   # this Mac's record: which layout each email's pictures were built from


def _sha(run):
    return hashlib.sha256((run / "design" / "email.json").read_bytes()).hexdigest()[:16]


def _stamps():
    try:
        return json.loads(STAMPS.read_text())
    except (OSError, ValueError):
        return {}


def stamp(run):
    d = _stamps()
    d["%s/%s" % (run.parent.name, run.name)] = _sha(run)
    STAMPS.parent.mkdir(parents=True, exist_ok=True)
    STAMPS.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def stale(run):
    """Why this email needs a rebuild here, or None."""
    k = run / "klaviyo"
    if not (k / "email.html").is_file():
        return None
    want = set(__import__("re").findall(r'src="assets/([^"]+)"', (k / "email.html").read_text()))
    have = {p.name for p in (k / "assets").glob("*")} if (k / "assets").is_dir() else set()
    if want - have:
        return "%d of %d built pictures missing" % (len(want - have), len(want))
    built = _stamps().get("%s/%s" % (run.parent.name, run.name))
    if built is None:
        newest = max([p.stat().st_mtime for p in (k / "assets").glob("*")] or [0])
        if (run / "design" / "email.json").stat().st_mtime > newest + 1:
            return "no record of what its pictures were built from, and the layout file is newer"
        return None
    if built != _sha(run):
        return "the layout changed after the pictures were built"
    return None


def keep_card(run, fn):
    """Run fn(); then put back the card fields a rebuild drops."""
    f = run / "klaviyo" / "card.json"
    before = json.loads(f.read_text()) if f.is_file() else {}
    out = fn()
    if f.is_file():
        after = json.loads(f.read_text())
        changed = False
        for k in KEEP:
            if k in before and after.get(k) != before[k]:
                after[k] = before[k]
                changed = True
        if changed:
            f.write_text(json.dumps(after, indent=1, ensure_ascii=False) + "\n")
    return out


def rebuild(run):
    p = subprocess.run([sys.executable, "design/build.py", str(run)], cwd=str(EM), capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]


def page_step():
    """Say, every session, which shared-page changes this person's own page still lacks (page_sync.py), so their Claude
    brings them in (README, "Start my email session" step 1). Never blocks the emails."""
    try:
        from run_kit import people
        person = people.try_person_of(REPO, people.git_email(REPO))
        if person and (REPO / ("platform/views/viewers/%s/emails.html" % person)).is_file():
            import page_sync
            print("PAGE · keep your own emails page in step with the shared one (README step 1):")
            page_sync.status(person)
    except Exception as e:  # noqa: BLE001 — said, never hidden, never in the emails' way
        print("PAGE · could not check the shared page's changes: %s" % str(e)[:200])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", help="one brand; leave out for every brand")
    ap.add_argument("--dry-run", action="store_true")
    x = ap.parse_args(argv)
    runs = [c.parent.parent for c in sorted(RUNS.glob("%s/*/klaviyo/card.json" % (x.brand or "*")))
            if (c.parent.parent / "design" / "email.json").is_file()]
    todo = [(r, why) for r, why in ((r, stale(r)) for r in runs) if why]
    if not x.dry_run:
        page_step()
    if not x.dry_run:          # whole and never recorded: record what they were built from, so later checks read content
        known = _stamps()
        for r in runs:
            if (r, None) not in [(t, None) for t, _ in todo] and "%s/%s" % (r.parent.name, r.name) not in known \
                    and (r / "klaviyo" / "email.html").is_file():
                stamp(r)
    if not todo:
        print("all %s emails are whole on this Mac" % (x.brand or "designed"))
        return 0
    bad = 0
    for run, why in todo:
        if x.dry_run:
            print("would rebuild %s: %s" % (run.name, why))
            continue
        ok, last = keep_card(run, lambda: rebuild(run))
        if ok:
            stamp(run)
        bad += not ok
        print("%s %s (%s)%s" % ("✓" if ok else "✗", run.name, why, "" if ok else " — " + last[0][-200:]))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
