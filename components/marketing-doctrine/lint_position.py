#!/usr/bin/env python3
"""The position gate: every brand's position.md has the template's shape.

    python3 components/marketing-doctrine/lint_position.py            # every brand
    python3 components/marketing-doctrine/lint_position.py <file> ... # named files

What it checks, per file:
  * a `## The line` section holding ONE fenced block
  * the fourteen slots, in the template's order, each exactly once, one per
    line, `LABEL: value` — a slot may say `open`, never be missing or empty
  * MARKET STAGE names one of the doctrine's five stages, spelled as
    frameworks.json spells it (case-insensitive; a leading "3." is fine)
  * the standard `##` sections, in the template's order (extra sections are
    allowed only under `## Also on file`)
  * no `<placeholder>` left from the template
  * no hex colour — colour is the design system (identity/), never the position
  * brand-agnostic template: brands/_TEMPLATE/brand-identity/position.md names no brand
Exit 0 = clean. Exit 1 = findings. Exit 2 = nothing to check.
Stdlib only.
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent
# v6 layout: story and position live in brand-identity/; the old top-level spot is still read
TEMPLATE = next((t for t in (WS / "brands" / "_TEMPLATE" / "brand-identity" / "position.md",
                             WS / "brands" / "_TEMPLATE" / "position.md") if t.is_file()),
                WS / "brands" / "_TEMPLATE" / "brand-identity" / "position.md")

SLOTS = ["LINE", "SPINE", "PROBLEM WORD", "MECHANISM", "MECHANISM NAME", "DISPLACES",
         "MARKET STAGE", "STAGE WHY", "LEADS WITH", "TRUST MOVE", "AUTHORITY",
         "SIGNATURE ASSET", "NEVER", "confirmed by"]
SECTIONS = ["The line", "The goal, in one counterintuitive sentence", "The position",
            "The thing nobody in the category will say", "The competition, by mechanism",
            "The territory", "The words", "The binding rules", "Receipts", "Open"]
OPTIONAL_TAIL = ["Also on file", "The method, for the next brand"]


def stage_names():
    try:
        d = json.loads((HERE / "frameworks.json").read_text())
        return [s["name"] for s in d["sophistication"]["stages"]]
    except Exception:
        return ["First in the market", "The claim is in the market", "Claims exhausted",
                "The mechanism is in the market", "Exhausted field"]


def brand_names():
    b = WS / "brands"
    return [p.name for p in b.iterdir() if p.is_dir() and not p.name.startswith("_")] if b.is_dir() else []


def check(path, is_template=False):
    f = []
    try:
        text = Path(path).read_text()
    except Exception as e:
        return [f"cannot read: {e}"]
    # sections
    heads = re.findall(r"^## (.+?)\s*$", text, re.M)
    want = SECTIONS[:]
    got_std = [h for h in heads if h in SECTIONS]
    if got_std != want:
        missing = [s for s in want if s not in heads]
        if missing:
            f.append("missing section(s): " + " · ".join(f"## {m}" for m in missing))
        elif got_std != want:
            f.append("sections out of the template's order: " + " → ".join(got_std))
    extra = [h for h in heads if h not in SECTIONS + OPTIONAL_TAIL]
    if extra:
        f.append("section(s) the template does not name (put them under `## Also on file`): "
                 + " · ".join(f"## {h}" for h in extra))
    # the block
    m = re.search(r"^## The line\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        f.append("no `## The line` section")
        return f
    fences = re.findall(r"^```[^\n]*\n(.*?)^```", m.group(1), re.M | re.S)
    if len(fences) != 1:
        f.append(f"`## The line` must hold exactly one fenced block, found {len(fences)}")
        return f
    lines = [l for l in fences[0].splitlines()]
    if any(not l.strip() for l in lines):
        f.append("blank line inside the block")
    labels, values = [], {}
    for l in lines:
        if not l.strip():
            continue
        mm = re.match(r"^([A-Za-z][A-Za-z ]*?): ?(.*)$", l)
        if not mm:
            f.append(f"not `LABEL: value`: {l[:60]!r}")
            continue
        labels.append(mm.group(1)); values[mm.group(1)] = mm.group(2).strip()
    if labels != SLOTS:
        missing = [s for s in SLOTS if s not in labels]
        unknown = [s for s in labels if s not in SLOTS]
        dupes = sorted({s for s in labels if labels.count(s) > 1})
        if missing: f.append("missing slot(s): " + " · ".join(missing))
        if unknown: f.append("slot(s) the template does not name: " + " · ".join(unknown))
        if dupes: f.append("slot(s) repeated: " + " · ".join(dupes))
        if not (missing or unknown or dupes): f.append("slots out of the template's order")
    for s, v in values.items():
        if not v:
            f.append(f"{s}: empty — write `open` if it is not settled")
    # Colour is the design system, not the position (Damon, 2026-09-19) — a hex
    # value here belongs in brands/<brand>/identity/.
    hexes = re.findall(r"#[0-9A-Fa-f]{6}\b", text)
    if hexes:
        f.append(f"{len(hexes)} hex colour(s) e.g. {hexes[0]} — colour belongs in identity/, not the position")
    if not is_template:
        st = values.get("MARKET STAGE", "")
        if st.lower() != "open" and not any(n.lower() in st.lower() for n in stage_names()):
            f.append("MARKET STAGE does not name one of the five stages: " + " · ".join(stage_names()))
        ph = re.findall(r"<[a-z][^<>\n]{2,60}>", text)
        if ph:
            f.append(f"{len(ph)} template placeholder(s) left, e.g. {ph[0]!r}")
    else:
        for b in brand_names():
            if re.search(rf"\b{re.escape(b)}\b", text, re.I):
                f.append(f"template names a brand: {b}")
    return f


def main(argv):
    files = [Path(a) for a in argv] or sorted(
        p for p in [*(WS / "brands").glob("*/position.md"), *(WS / "brands").glob("*/brand-identity/position.md")]
        if not p.relative_to(WS / "brands").parts[0].startswith("_"))
    if TEMPLATE.is_file() and not argv:
        files.append(TEMPLATE)
    if not files:
        print("nothing to check"); return 2
    bad = 0
    for p in files:
        fs = check(p, is_template=(p.resolve() == TEMPLATE.resolve()))
        rel = p.resolve().relative_to(WS) if str(p.resolve()).startswith(str(WS)) else p
        if fs:
            bad += 1
            for x in fs: print(f"{rel}: {x}")
        else:
            print(f"clean: {rel}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
