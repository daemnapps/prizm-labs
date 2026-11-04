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
import hashlib
import os
import re
import subprocess
import sys

KEYS = re.compile(r"sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}"
                  r"|apify_api_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|glpat-[A-Za-z0-9_-]{20,}"
                  r"|figd_[A-Za-z0-9_-]{20,}|whsec_[A-Za-z0-9]{20,}|shp(at|ss|ca)_[A-Za-z0-9]{20,}")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@(company(llc)?\.com|elsewhere\.com|example\.(com|org|net)|users\.noreply\.github\.com|anthropic\.com)$|^(you|name|your-email|someone|admin)@", re.I)
SUPPORT = set()
PATHS = re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[Cc]:\\Users\\")
# Private names, stored as hashes so this public file does not spell them.
OUR_NAMES = {"ad630d1b84507ba3", "e2a357c15620693e", "0fc1793d6129e594", "66a898a08b12ec51", "861b7be1b5c417f4", "30381a3d96190154", "91d872a4839bf873"}
OTHER_BRANDS = {"8d4d7f4398aa17da", "a727a45a69043a6a", "844b50f3d1799eab"}
PEOPLE = {"9af2921d3fd57fe8", "f0fd52e74857e4e8", "1f9489f5feb46a3d", "1c3058782188323d", "3e90307d36e5ae56", "bc5534e9c0cbad11", "2bfa5bf7003b922e", "0ec5f7c0abe435d2", "a1df6dffb5e4869e", "ba2d0830e65eadb3"}
WORD = re.compile(r"[a-z0-9]+")


def _hash(word):
    return hashlib.sha256(word.encode()).hexdigest()[:16]


def private_names(text, hashes=None):
    """The private names in text: single words, and two words run together."""
    hashes = (OUR_NAMES | OTHER_BRANDS | PEOPLE) if hashes is None else hashes
    words, found = WORD.findall(text.lower()), []
    for i, w in enumerate(words):
        if _hash(w) in hashes:
            found.append(w)
        elif i + 1 < len(words) and _hash(w + words[i + 1]) in hashes:
            found.append(w + " " + words[i + 1])
    return found


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


def check_file(path):
    """For the commit hook: 0 if the file holds no brand name. Competitors are allowed under docs/swipes."""
    hashes = OUR_NAMES if path.startswith("docs/swipes/") else OUR_NAMES | OTHER_BRANDS
    with open(path, encoding="utf-8", errors="ignore") as f:
        found = sorted(set(private_names(f.read(), hashes)))
    if found:
        print(" ".join(found[:3]))
    return 1 if found else 0


def main():
    if sys.argv[1:2] == ["--file"]:
        return check_file(sys.argv[2])
    base, head = (sys.argv[1:3] + ["origin/main", "HEAD"])[:2]
    rules, problems = allowed(), []
    for path, n, line in added_lines(base, head):
        if path in ("tools/safety_check.py", ".github/safety-allow.txt") or path.startswith(".githooks/"):
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
        for name in private_names(line):
            if not ok(name):
                problems.append((path, n, "private name", name))
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
