#!/usr/bin/env python3
"""SI-157 (names parse) — names parse as documented.

    python3 components/naming/test_aw17_names_documented.py

Offline, stdlib only. Writes only into a temp dir (record.HOME is pointed
there); reads CONVENTION.md, the creative-asset kind and the brands tree.
"""
import re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N
import record as R

fails = []


def check(label, cond, detail=""):
    print(f"  [{' ok ' if cond else 'FAIL'}] {label}" + ("" if cond else f"  {detail}"))
    if not cond:
        fails.append(label)


def convention_example(header):
    """The line under `header` inside CONVENTION.md's example block."""
    lines = (HERE / "CONVENTION.md").read_text().splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.startswith(header))
    return lines[i + 1].strip()


# 1. the CONVENTION example parses, field for field
unit = convention_example("AD UNIT (this is what goes in Meta's Ad name field)")
asset = convention_example("ASSET (this is the filename")
u = N.parse(unit)
check("the CONVENTION ad-unit example parses", u is not None, unit)
check("it carries every AD_FIELD", bool(u) and all(u.get(k) for k in N.AD_FIELDS), u)
check("its field count is len(AD_FIELDS)", len(unit.split(N.SEP)) == len(N.AD_FIELDS))
a = N.parse(asset)
check("the CONVENTION filename example parses", a is not None, asset)
check("the filename is the ad unit plus its asset",
      bool(a) and a["ad_name"] == unit and a["asset_n"] == 1, a)
check("round trip: the example rebuilds to itself",
      bool(u) and N.ad_name(*[u[k] for k in N.AD_FIELDS]) == unit)
doc = (HERE / "CONVENTION.md").read_text()
check("CONVENTION says thirteen fields, fourteen in a filename",
      "Thirteen fields in an ad name, fourteen in a filename" in doc)
check("the field table lists every AD_FIELD",
      all(re.search(rf"^\| `{k}` \|", doc, re.M) for k in N.FIELDS))

# 2. a page swipe ref parses; an ad tool's number stays an int
check("swipe:<brand>:pages-acne parses",
      N.parse_swipe_id("swipe:acme:pages-acne") == ("acme", "pages-acne"))
check("an all-digit id still comes back an int",
      N.parse_swipe_id(N.swipe_id("acme", 162098799)) == ("acme", 162098799))
check("a ref with no id is refused", N.parse_swipe_id("swipe:acme:") is None)
check("an upper-case id is refused", N.parse_swipe_id("swipe:acme:Pages") is None)

# 3 + 4. status words and same-second writes, into a temp HOME
with tempfile.TemporaryDirectory() as td:
    R.HOME = Path(td) / "creative-asset"
    try:
        R.human("batch-2026-10-08-a.x.a01", "status", "tester", to="banana", evidence="x")
        refused = False
    except SystemExit:
        refused = True
    check("human(status, to='banana') refuses", refused)
    check("a refused status writes nothing", not R.HOME.exists() or not any(R.HOME.iterdir()))
    p = R.human("batch-2026-10-08-a.x.a01", "status", "tester", to="testing", evidence="x")
    check("a word from the kind's `to` vocabulary is written", p.is_file(), p)

    real_now = R.now
    R.now = lambda: "2026-10-08T09:00:00Z"
    try:
        v = {"event": "note", "text": "same second"}
        p1 = R.write("batch-2026-10-08-a.x.a02", "tester", v)
        p2 = R.write("batch-2026-10-08-a.x.a02", "tester", v)
    finally:
        R.now = real_now
    notes = sorted(R.HOME.glob("*a02--note.json"))
    check("two same-second writes give two files", p1 != p2 and len(notes) == 2, notes)
    check("the first record is still there", p1.is_file() and p2.is_file())

# 5. selfcheck reaches its subs block
src = (HERE / "selfcheck.py").read_text()
subs_at = src.index("# ---------------------------------------------------------------- subs ---")
exit_at = src.rindex("sys.exit(1 if fail else 0)")
check("selfcheck's exit sits after the subs block", exit_at > subs_at)
check("selfcheck exits once", src.count("sys.exit(1 if fail else 0)") == 1)
out = subprocess.run([sys.executable, str(HERE / "selfcheck.py")], capture_output=True,
                     text=True, cwd=str(HERE)).stdout
lines = out.splitlines()
summary = [n for n, ln in enumerate(lines) if re.search(r"\d+ ok · \d+ failing", ln)]
last_pre = max((n for n, ln in enumerate(lines) if "every evidence entry stays unaddressable" in ln), default=-1)
check("selfcheck runs to its summary", bool(summary), out[-500:])
check("the summary prints after the last pre-subs check", bool(summary) and summary[-1] > last_pre >= 0)
subs = [n for n, ln in enumerate(lines)
        if "carries an id equal to its bare slug" in ln or "resolves to a card or a core" in ln]
cards = list((N.WS / "brands").glob("*/core-avatars/*/sub-avatars/sub-*.md"))
if cards:
    check("the subs block printed its checks", bool(subs), f"{len(cards)} sub cards on disk")
    check("the subs checks sit between the last pre-subs check and the summary",
          bool(subs) and bool(summary) and last_pre < min(subs) and max(subs) < summary[-1])
else:
    print("  [GAP ] no sub-avatar cards on this disk — subs labels not checkable; ordering checked in source")

print(f"\n{len(fails)} failing")
sys.exit(1 if fails else 0)
