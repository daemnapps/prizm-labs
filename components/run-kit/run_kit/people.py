#!/usr/bin/env python3
"""people.py — THE one answer to "who is this" (LD-77 (one person resolver), 2026-10-22).

A person is the team/people/<id>/ whose identity.json lists the git email —
the exact address, case-insensitive — and NEVER the email's local part. The
local part is right only when it happens to equal the folder name: the team's
clone signs as stephanie@company.com (team/people/steph/), the owner's as
ddixon@companyllc.com (team/people/damon/). Eight places guessed by the
local part; they all ask here now. Unmapped or ambiguous is REFUSED with the
fix named (put the address in your team/people/<you>/identity.json), never
guessed onto a record.

    person_of(repo, email) -> str              Refused on empty, unmapped, ambiguous
    try_person_of(repo, email) -> str or None  None instead of raising (hooks, stamps)
    whoami(repo, git=None) -> str              person_of of `git config user.email`

    python3 components/run-kit/run_kit/people.py whoami [--repo R] [--email E]
        prints the id, exit 0; refused -> the reason on stderr, exit 2

An identity file's addresses are read in every shape one has used: `emails`
as a list of {"address": …} or of plain strings, or a singular `email` key.
Moved out of mini_run.person_of (mini_run.py:146-168), which already had the
rule right. Stdlib only; runs under /usr/bin/python3 3.9.6.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

PEOPLE = "team/people"
FIX = "team/people/<you>/identity.json"


class Refused(ValueError):
    """A refusal: printed, exit 2."""


def addresses(doc):
    """Every address one identity.json claims, stripped, casefolded."""
    if not isinstance(doc, dict):
        return []
    raw = doc.get("emails") or doc.get("email") or []
    if isinstance(raw, (str, dict)):
        raw = [raw]
    out = []
    for entry in raw if isinstance(raw, list) else []:
        addr = entry.get("address") if isinstance(entry, dict) else entry
        if isinstance(addr, str) and addr.strip():
            out.append(addr.strip().casefold())
    return out


def claimants(repo, email, skipped=None):
    """The ids whose identity.json lists `email` (exact, case-insensitive). An
    unreadable file is skipped — handed to skipped(path, error) when given: one
    person's broken JSON never stops the rest."""
    want = (email or "").strip().casefold()
    if not want:
        return []
    hits = []
    for f in sorted((Path(repo) / PEOPLE).glob("*/identity.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            if skipped is not None:
                skipped(f, e)
            continue
        if want in addresses(doc):
            hits.append(f.parent.name)
    return hits


def person_of(repo, email):
    """The person id (team/people/<id>/) whose identity.json lists `email`."""
    email = (email or "").strip()
    if not email:
        raise Refused("git config user.email is empty — set it to the address in "
                      "your {0}".format(FIX))
    hits = claimants(repo, email)
    if not hits:
        raise Refused("git user.email {0!r} matches no {1}/*/identity.json — refused; "
                      "the person filing must be on the team record: add the address "
                      "to your {2}".format(email, PEOPLE, FIX))
    if len(hits) > 1:
        raise Refused("git user.email {0!r} matches more than one person ({1}) — refused; "
                      "one address, one person: correct {2}".format(
                          email, ", ".join(hits),
                          " or ".join("{0}/{1}/identity.json".format(PEOPLE, h) for h in hits)))
    return hits[0]


def try_person_of(repo, email) -> Optional[str]:
    """person_of, or None where it would refuse — for hooks and stamps that must never block."""
    try:
        return person_of(repo, email)
    except Refused:
        return None


def git_email(repo):
    """`git config user.email` in repo, or "" when git is absent or has none."""
    try:
        p = subprocess.run(["git", "config", "user.email"], cwd=str(repo),
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def whoami(repo, git=None):
    """The person running this. `git` is mini_run's seam: git(args, repo) -> (code, out, err)."""
    if git is None:
        return person_of(repo, git_email(repo))
    code, out, err = git(["config", "user.email"], repo)
    return person_of(repo, out if code == 0 else "")


def find_repo(start=None):
    """The checkout: the first folder upward holding team/people/."""
    here = Path(start or __file__).resolve()
    for d in [here, *here.parents]:
        if (d / PEOPLE).is_dir():
            return d
    raise Refused("no checkout found upward of {0} (looked for {1}/)".format(here, PEOPLE))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="people.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("whoami", help="print the person id of git config user.email")
    w.add_argument("--repo", help="the checkout (default: the one holding this file)")
    w.add_argument("--email", help="resolve this address instead of git config user.email")
    a = ap.parse_args(argv)
    if a.cmd != "whoami":
        ap.print_usage(sys.stderr)
        return 2
    try:
        repo = Path(a.repo) if a.repo else find_repo()
        email = a.email if a.email is not None else git_email(repo)
        print(person_of(repo, email))
    except Refused as e:
        print("people.py: {0}".format(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
