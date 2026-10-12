#!/usr/bin/env python3
"""Safety check for this public repo. Looks only at lines a change ADDS and blocks:

  1. key-like text (API keys, tokens, private keys)
  2. personal email addresses (placeholders like name@example.com are fine)
  3. paths off someone's own computer (/Users/<name>/, /home/<name>/, C:\\Users\\)
  4. private brand and people names (the list in BLOCKED_NAMES)

A line that legitimately needs one of these goes in .github/safety-allow.txt
("path-prefix|text"), which is itself reviewed like any other change.

    python3 tools/safety_check.py <base> <head>     # e.g. origin/main HEAD
Standard library only.
"""
import os
import re
import subprocess
import sys

KEYS = re.compile(r"sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}"
                  r"|apify_api_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|glpat-[A-Za-z0-9_-]{20,}"
                  r"|figd_[A-Za-z0-9_-]{20,}|whsec_[A-Za-z0-9]{20,}|shp(at|ss|ca)_[A-Za-z0-9]{20,}")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@(example\.(com|org|net)|users\.noreply\.github\.com|anthropic\.com)$|^(you|name|your-email|someone|admin)@", re.I)
SUPPORT = {"admin@gradientmediallc.com"}          # the published support address
PATHS = re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[Cc]:\\Users\\")
BLOCKED_NAMES = re.compile(r"\b(douxds|pasnida|upright\s*commerce|valentina|steph(anie)?\b|ecommops|ledger\s*labs)\b", re.I)


def allowed():
    rules = []
    p = os.path.join(os.path.dirname(__file__), "..", ".github", "safety-allow.txt")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                prefix, text = line.split("|", 1)
                rules.append((prefix.strip(), text.strip()))
    return rules


def added_lines(base, head):
    diff = subprocess.run(["git", "diff", "-U0", "--no-color", f"{base}...{head}"],
                          capture_output=True, text=True, check=True).stdout
    path, n = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            n = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            yield path, n, raw[1:]
            n += 1


def main():
    base, head = (sys.argv[1:3] + ["origin/main", "HEAD"])[:2]
    rules, problems = allowed(), []
    for path, n, line in added_lines(base, head):
        if path.startswith("tools/safety_check.py") or path.startswith(".githooks/"):
            continue                                   # the rules themselves
        ok = lambda text: any(path.startswith(p) and t.lower() in text.lower() for p, t in rules)
        for m in KEYS.finditer(line):
            problems.append((path, n, "key-like text", m.group(0)[:6] + "…"))
        for m in EMAIL.finditer(line):
            e = m.group(0)
            if e.lower() not in SUPPORT and not EMAIL_OK.search(e) and not ok(e):
                problems.append((path, n, "personal email", e))
        for m in PATHS.finditer(line):
            if not ok(m.group(0)):
                problems.append((path, n, "path off someone's computer", m.group(0)))
        for m in BLOCKED_NAMES.finditer(line):
            if not ok(m.group(0)):
                problems.append((path, n, "private name", m.group(0)))
    if not problems:
        print("safety-check: OK — nothing private in the added lines.")
        return 0
    print("safety-check: BLOCKED. These added lines can't go public:\n")
    for path, n, kind, what in problems:
        print(f"  {path}:{n}  {kind}: {what}")
    print("\nRemove them, or if one truly belongs, add 'path-prefix|text' to .github/safety-allow.txt in this same change.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
