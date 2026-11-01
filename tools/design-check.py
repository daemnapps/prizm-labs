#!/usr/bin/env python3
"""Refuse a page that is not on the design system.

    python3 tools/design-check.py                 every page under docs/
    python3 tools/design-check.py --staged        only what a commit would send
    python3 tools/design-check.py docs/x.html     named files

This is the reason "it follows the system" stops being something to remember.
The pre-commit hook runs `--staged`; a page that breaks a rule is printed with
the line and the reason, and nothing is committed.

THE RULES, and why each one exists:

  1  LOADS THE SYSTEM — every page links /studio.css with the version query.
     A page that styles itself is how three visual worlds appeared on one
     site in the first place.
  2  NO RAW COLOUR — no hex, rgb() or hsl() outside studio.css. Colour comes
     from a token, so the spectrum's meaning holds everywhere.
  3  NO RAW TYPE — no font-family outside the three tokens, and no font host
     but the system's own Google Fonts line. A fourth face breaks the voice.
  4  NO RAW RADIUS OR SHADOW — radii and the one shadow are tokens; a
     hand-typed 12px is how a page starts to drift.
  5  A PAGE'S OWN CSS STAYS SMALL — layout only, under the line budget. Past
     that it is a second system and belongs in studio.css.
  6  THE SHELL IS SHARED — nav.bar and footer.bot, same markup everywhere.

Generated pages are checked too: the builder that writes them is what gets
fixed, never the output.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SYSTEM = "docs/studio.css"
LINK = re.compile(r'href="/studio\.css\?v=[\w.-]+"')
FONT_HOST = re.compile(r'fonts\.googleapis\.com/css2\?family=([^"]*)')
ALLOWED_FONTS = {"Unbounded", "Plus+Jakarta+Sans", "DM+Mono"}
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}\"']+)")
OK_FAMILY = re.compile(r"var\(--(display|body|mono)\)")
RADIUS = re.compile(r"border-radius\s*:\s*(?!var\()[^;}]+")
SHADOW = re.compile(r"box-shadow\s*:\s*(?!var\(|inset|none)[^;}]+")
CSS_BUDGET = 60          # lines of page-specific CSS
# A page may name a colour outside a token only where the platform gives no
# choice: a meta theme colour, and #fff on a coloured button where the token
# set has no "on-accent" ink. Both are listed rather than guessed at.
EXEMPT_LINE = re.compile(r'name="theme-color"|color:#fff\b|#fff"|background:#000\b')


def pages(args):
    if args.files:
        return [Path(f) for f in args.files if f.endswith((".html", ".md"))]
    if args.staged:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                             capture_output=True, text=True, cwd=ROOT).stdout.split()
        return [ROOT / f for f in out if f.startswith("docs/") and f.endswith(".html")]
    return sorted(DOCS.rglob("*.html"))


def style_blocks(text):
    """Every <style> block with the line it starts on."""
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", text, re.S):
        yield text[:m.start()].count("\n") + 1, m.group(1)


def check(path):
    rel = path.relative_to(ROOT) if path.is_absolute() else path
    if str(rel) == SYSTEM:
        return []
    if not path.is_file():
        return []
    text = path.read_text(errors="replace")
    bad = []

    if not LINK.search(text):
        bad.append((1, 'does not load the system: needs <link rel="stylesheet" '
                       'href="/studio.css?v=…">'))

    for fam in FONT_HOST.findall(text):
        names = {p.split(":")[0] for p in fam.split("&") if p and not p.startswith("display=")}
        names = {n.replace("family=", "") for n in names}
        extra = names - ALLOWED_FONTS
        if extra:
            line = text[:text.index(fam)].count("\n") + 1
            bad.append((line, f"loads a face outside the system: {', '.join(sorted(extra))}"))

    for host in re.findall(r'href="(https?://[^"]+\.css[^"]*)"', text):
        if "fonts.googleapis.com" not in host:
            line = text[:text.index(host)].count("\n") + 1
            bad.append((line, f"loads a stylesheet that is not the system: {host}"))

    total_css = 0
    for start, css in style_blocks(text):
        total_css += css.count("\n")
        for i, line in enumerate(css.split("\n")):
            n = start + i
            if EXEMPT_LINE.search(line) or line.strip().startswith(("/*", "*", "//")):
                continue
            if COLOUR.search(line):
                bad.append((n, f"raw colour — use a spectrum or paper token: {line.strip()[:60]}"))
            m = FONT_FAMILY.search(line)
            if m and not OK_FAMILY.search(m.group(1)):
                bad.append((n, f"raw font-family — use var(--display/--body/--mono): {m.group(1).strip()[:40]}"))
            if RADIUS.search(line):
                bad.append((n, f"raw radius — use var(--r1/--r2/--r3/--r4): {line.strip()[:50]}"))
            if SHADOW.search(line):
                bad.append((n, f"raw shadow — only a floating object gets one, via var(--float): {line.strip()[:50]}"))
    if total_css > CSS_BUDGET:
        bad.append((1, f"{total_css} lines of page CSS (budget {CSS_BUDGET}) — "
                       "anything shared belongs in studio.css"))

    # colours in markup are as off-system as colours in CSS
    for m in re.finditer(r'style="([^"]*)"', text):
        if COLOUR.search(m.group(1)) and not EXEMPT_LINE.search(m.group(0)):
            line = text[:m.start()].count("\n") + 1
            bad.append((line, f"raw colour in a style attribute: {m.group(1)[:50]}"))

    if 'class="bar"' not in text and "nav class=\"bar\"" not in text:
        bad.append((1, "no shared nav — every page carries <nav class=\"bar\">"))
    if 'class="bot"' not in text:
        bad.append((1, "no shared footer — every page carries <footer class=\"bot\">"))
    return [(rel, n, why) for n, why in bad]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--staged", action="store_true")
    a = ap.parse_args()

    found = []
    checked = 0
    for p in pages(a):
        checked += 1
        found += check(p)

    if not found:
        print(f"design-check: {checked} page(s) on system")
        return 0

    print("\n  \033[1;31mOFF-SYSTEM\033[0m — daemn.co has one design system and these break it:\n")
    for rel, n, why in found:
        print(f"  {rel}:{n}\n      → {why}")
    print("\n  The system is docs/studio.css. The rules are docs/DESIGN.md.")
    print("  Fix it, or if the rule itself is wrong, change the system — not the page.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
