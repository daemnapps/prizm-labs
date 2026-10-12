#!/usr/bin/env python3
"""The wiring doctor: is this brand connected and pulling, row by row?

    python3 doctor.py --brand brand-b

Walks the ONBOARDING.md contract — every brand fact the system reads — and
reports OK / MISSING per row with size and freshness. Then runs the two
zero-cost dry-run probes (composer inputs, chain variables) so 'connected'
means resolved, not merely present. Read-only, spends nothing.
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

from paths import HERE, WORKSPACE, component
sys.path.append(str(component("brandpath")))   # appended, never ahead of this machine
import brandpath as BP                                # noqa: E402

CONTRACT = [
    ("Avatars + language index", "core-avatars/language-index.json"),
    ("Products", "products"),
    ("Offer bank (sectioned per avatar)", "products/offer-bank.md"),
    ("Objection bank", "core-avatars/objection-bank.md"),
    ("Cultural moments", "calendar/moments.json"),
    ("Sender identity", "email-sms/identity/sender.md"),
    ("Variable map (this surface)", "variables/email.md"),
    ("Type catalogue (brand-owned)", "email-sms/email-types.json"),
    ("Audience matrix (segments)", "email-sms/audience-matrix.json"),
    ("Segment audit", "email-sms/segments.md"),
    ("Subject ledger", "email-sms/ledger.json"),
    ("Sent emails, whole", "email-sms/sends"),
    ("Sends classified", "email-sms/classified.json"),
    ("Performance", "email-sms/performance.json"),
    ("Learnings", "email-sms/learnings.md"),
    ("Design skin (+photo_register)", "email-sms/design-formats/components.json"),
    ("Design formats", "email-sms/design-formats/formats.md"),
    ("Design census", "email-sms/design-formats/census.json"),
    ("Adopted calendar(s)", "email-sms/calendar-*.json"),
]


def age(p):
    d = datetime.date.today() - datetime.date.fromtimestamp(p.stat().st_mtime)
    return "today" if d.days == 0 else f"{d.days}d old"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    root = WORKSPACE / "brands" / a.brand
    if not root.is_dir():
        sys.exit(f"no brand folder at {root}")
    print(f"THE WIRING — {a.brand}  ({root})\n")
    ok = miss = 0
    for name, rel in CONTRACT:
        if "*" in rel:
            hits = sorted(root.glob(rel))
            if hits:
                ok += 1
                print(f"  OK      {name:34} {len(hits)} file(s) · newest {age(hits[-1])}")
            else:
                miss += 1
                print(f"  MISSING {name:34} {rel}")
            continue
        p = BP.resolve_rel(root.name, rel, root=root.parent)
        if p.is_dir():
            n = len([x for x in p.iterdir() if x.name != "README.md"])
            if n:
                ok += 1
                print(f"  OK      {name:34} {n} file(s) · {age(p)}")
            else:
                miss += 1
                print(f"  MISSING {name:34} {rel} (empty)")
        elif p.is_file():
            extra = ""
            if name.startswith("Design skin"):
                extra = (" · photo_register ok"
                         if json.loads(p.read_text()).get("photo_register")
                         else " · NO photo_register")
            ok += 1
            print(f"  OK      {name:34} {p.stat().st_size:>9,} B · {age(p)}{extra}")
        else:
            miss += 1
            print(f"  MISSING {name:34} {rel}")
    print(f"\n  contract: {ok} OK · {miss} missing\n")

    print("PROBE 1 — composer inputs (dry run, spends nothing)")
    r = subprocess.run([sys.executable, "compose.py",
                        f"{datetime.date.today():%Y-%m}", "--brand", a.brand,
                        "--dry-run"], capture_output=True, text=True, cwd=HERE)
    tail = [ln for ln in (r.stdout + r.stderr).splitlines()
            if "OK " in ln or "MISSING" in ln or "roster" in ln]
    print("\n".join("  " + ln.strip() for ln in tail[-13:]) or "  FAILED:\n" + r.stderr[-300:])

    print("\nPROBE 2 — chain variables (dry run on the newest sent email)")
    sends = sorted((root / "email-sms/sends").glob("*.md"))
    if sends:
        idx = json.loads(BP.brand_path(root.name, "core-avatars", "language-index.json", root=root.parent).read_text())
        avatar = max(idx["per_avatar"],
                     key=lambda k: sum(f["rows"] for f in idx["per_avatar"][k].values()))
        r = subprocess.run([sys.executable, "email.py", str(sends[-1]),
                            "--brand", a.brand, "--avatar", avatar,
                            "--label", "_doctor", "--dry-run"],
                           capture_output=True, text=True, cwd=HERE)
        got = [ln for ln in r.stdout.splitlines() if "variables resolved" in ln]
        print(f"  avatar probed: {avatar}")
        print("  " + (got[-1].strip() if got else "FAILED: " + r.stderr[-200:]))
        # Nothing to clean up: a dry run writes nothing under runs/ (2026-09-20).
        # This used to delete a folder after every check — and deleted the
        # wrong one, results/_doctor, while the dry run wrote to runs/.
    else:
        print("  no sent emails to probe with")


if __name__ == "__main__":
    main()
