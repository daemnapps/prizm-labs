#!/usr/bin/env python3
"""wiring — is the who-and-what block really in what every writer sends? Runs each workflow's own proof and prints
one line each. Green only when its proof passes. No model, no spend.

    python3 machine/wiring.py [--json FILE]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

C = Path(__file__).resolve().parents[2]
WORKFLOWS = [
    ("Research route", "creative-strategist/tests/test_strategy.py"),
    ("The shared reader", "creative-strategist/tests/test_who.py"),
    ("Video writing, from scratch too", "video-writing/tests/test_who_reaches_writing.py"),
    ("Director, versions, outlier brief, lab pages", "creative-strategist/tests/test_who_reaches_rest.py"),
    ("Static image writing", "image-writing/tests/test_who.py"),
    ("Statics sprint, ad variations", "ad-variations/machine/test_who.py"),
    ("Copy, copy sets, Google copy", "copywriter/machine/test_who_reaches_copy.py"),
    ("Email and SMS", "email-production/test_who_reaches_email.py"),
    ("Pages", "page-writing/tests/test_who_reaches_page.py"),
    ("Creator briefs", "briefs/creator-brief/tests"),
    ("Sales by person", "winners/tests"),
    ("Creative diversity, idea to filing", "creative-diversity/tests/test_plan.py"),
    ("The creative matrix, any brand, any format", "creative-diversity/tests/test_matrix.py"),
    ("The body map: words, pictures, clips, sales", "naming/tests/test_body.py"),
]


def by_brand():
    """One line per brand: people with a finished profile, out of every sub-avatar, and how many are out of date."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import who
    for b in sorted(p.name for p in (C.parent / "brands").iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        pairs = [(a, s) for a in who.avatars(b) for s in who.subs(b, a)]
        if pairs:
            ix = who.index(b)
            print("%-5s %-46s %d of %d people have a profile%s" % ("", "Profiles: " + b, sum(1 for a, s in pairs if who.filed(b, a, s)), len(pairs), (", %d out of date" % sum(x["stale"] for x in ix)) if ix else ""))


def proof(rel):
    p = C / rel
    fs = sorted(x for x in p.glob("test_*.py") if re.search(r"aim|\bwho\b|who\(", x.read_text(errors="replace"))) if p.is_dir() else ([p] if p.is_file() else [])
    if not fs:
        return False, "no proof on file"
    for f in fs:
        r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, cwd=str(C.parent), timeout=600)
        if r.returncode:
            return False, f.name + ": " + (r.stderr or r.stdout).strip().splitlines()[-1][:120]
    return True, "%d proof file%s pass" % (len(fs), "" if len(fs) == 1 else "s")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    out = []
    for name, rel in WORKFLOWS:
        ok, why = proof(rel)
        out.append({"workflow": name, "green": ok, "why": why})
        print("%-5s %-46s %s" % ("green" if ok else "RED", name, why))
    by_brand()
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    return 0 if all(x["green"] for x in out) else 1


if __name__ == "__main__":
    sys.exit(main())
