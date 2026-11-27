"""Keep a person's own emails page and the shared one in step, both ways (the team, 2026-10-22).

the team has her own live page (platform/views/viewers/designer/emails.html, cut by the team on 2026-10-22); the team keeps the shared
one (platform/views/viewers/_templates/emails.html and its preview page). Changes do not flow on their own, so each
side records how far it has brought the other's in, in the person's sync record
(platform/views/viewers/<person>/emails.sync.json), and this lists what is still to bring, from git:

    page_sync.py status --person designer      what the shared page has that the team's page doesn't yet, and the reverse
    page_sync.py mark --person designer --into own      after bringing the shared page's changes into the team's page
    page_sync.py mark --person designer --into shared   after bringing the team's changes into the shared page

`mark` records the newest commit on the other side as brought in; run it only after every listed change is in (or
left out on purpose and said so). Nothing here edits a page: the person's Claude makes the change (/page-change).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(d for d in HERE.parents if (d / "components" / "run-kit").is_dir()) / "components" / "run-kit"))
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
VIEWERS = "platform/views/viewers"
SHARED = [VIEWERS + "/_templates/emails.html", VIEWERS + "/_templates/emails-preview.html"]


def own(person):
    return [VIEWERS + "/%s/emails.html" % person, VIEWERS + "/%s/preview.html" % person]


def record_path(person):
    return REPO / VIEWERS / person / "emails.sync.json"


def _git(*a):
    p = subprocess.run(["git"] + list(a), cwd=str(REPO), capture_output=True, text=True)
    if p.returncode:
        raise SystemExit("git %s: %s" % (" ".join(a), p.stderr.strip()[-300:]))
    return p.stdout.strip()


def commits(since, files):
    """[(sha, subject)] touching files after `since` (oldest first); every commit when since is empty."""
    rng = ["%s..HEAD" % since] if since else []
    out = _git("log", "--reverse", "--format=%h\t%s", *rng, "--", *files)
    return [tuple(line.split("\t", 1)) for line in out.splitlines() if line]


def load(person):
    try:
        return json.loads(record_path(person).read_text())
    except (OSError, ValueError):
        return {}


def status(person):
    r = load(person)
    if not (REPO / own(person)[0]).is_file():
        print("%s has no page of their own: nothing to keep in step" % person)
        return 0
    to_own = commits(r.get("shared_brought_in", ""), SHARED)
    to_shared = commits(r.get("own_brought_to_shared", ""), own(person))
    print("shared page changes not yet in %s's page: %s" % (person, len(to_own) or "none"))
    for h, s in to_own:
        print("  %s %s" % (h, s))
    print("%s's page changes not yet in the shared page: %s" % (person, len(to_shared) or "none"))
    for h, s in to_shared:
        print("  %s %s" % (h, s))
    return 0


def mark(person, into):
    r = load(person)
    files, key = (SHARED, "shared_brought_in") if into == "own" else (own(person), "own_brought_to_shared")
    last = _git("log", "-1", "--format=%h", "--", *files)
    r[key] = last
    r.setdefault("_about", "How far each side has brought the other's page changes in (page_sync.py). Commit with the page.")
    record_path(person).write_text(json.dumps(r, indent=1) + "\n")
    print("%s: %s = %s" % (record_path(person).relative_to(REPO), key, last))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--person", required=True)
    m = sub.add_parser("mark")
    m.add_argument("--person", required=True)
    m.add_argument("--into", choices=("own", "shared"), required=True)
    x = ap.parse_args(argv)
    return status(x.person) if x.cmd == "status" else mark(x.person, x.into)


if __name__ == "__main__":
    sys.exit(main())
