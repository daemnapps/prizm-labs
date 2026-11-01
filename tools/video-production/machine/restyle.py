#!/usr/bin/env python3
"""Restyle an approved scene set into a new visual format — mechanically.

    python3 restyle.py --run <run> --style <style-slug> --formula formula.md

THE WHOLE POINT: a variation is the SAME film with a new rendering. The
screenplay, blocking, dialogue, mechanics and edit are frozen. Only the
look changes.

So this step is DELIBERATELY NOT A MODEL. Handing approved prompts to a
model and asking it to restyle them is exactly what produced the slop run:
it re-planned the film — new shot structure, new framing, paraphrased
dialogue — and the result read as a different film. A model cannot resist
improving what it is handed.

This does three mechanical things to each approved prompt and nothing else:

  1. prepend the STYLE LOCK block (the formula, verbatim, at the very top)
  2. swap the reference media for their converted versions
  3. strip the photoreal descriptors named in the formula's strip table,
     replacing each with the style's own vocabulary

Every word the user approved survives. Nothing is rewritten, nothing is
paraphrased, nothing is re-planned. The diff is auditable, and the tool
prints it.

Brand- and style-agnostic: the formula supplies the lock and the strip
table; nothing here names a style.
"""

import argparse
import json
import re
import sys
from pathlib import Path

STYLE_LOCK = """STYLE LOCK (absolute — overrides everything below): {formula}
{motion}
The reference images are the characters, world and product IN THIS STYLE.
{nots}

"""


def parse_formula(md):
    """Pull the locked formula, the motion language, the strip table and the
    must-nots out of the stage-v1 output."""
    formula = ""
    m = re.search(r"FORMULA LOCKED\s*—\s*(.+?)(?:\n\s*\n|\Z)", md, re.S)
    if m:
        formula = " ".join(m.group(1).split())
    motion = ""
    m = re.search(r"##\s*THE MOTION LANGUAGE\s*\n(.+?)(?=\n##|\Z)", md, re.S | re.I)
    if m:
        motion = " ".join(m.group(1).split())
    nots = ""
    m = re.search(r"##\s*WHAT THIS STYLE MUST NOT LOOK LIKE\s*\n(.+?)(?=\n##|\Z)",
                  md, re.S | re.I)
    if m:
        # strip the bullet or list number ONLY — "3D rendering" must keep
        # its 3, which a greedy \d class eats (caught 2026-09-02)
        items = [re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", l).strip()
                 for l in m.group(1).splitlines() if l.strip()]
        items = [i for i in items if i]
        if items:
            nots = "NOT: " + "; ".join(items) + "."
    # the strip table: | original | replacement |
    strip = []
    m = re.search(r"##\s*THE PHOTOREAL DESCRIPTORS TO STRIP\s*\n(.+?)(?=\n##|\Z)",
                  md, re.S | re.I)
    if m:
        for line in m.group(1).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 2 and cells[0] and not set(cells[0]) <= set("-: "):
                if cells[0].lower().startswith("in the original"):
                    continue
                strip.append((cells[0].strip('"“”'), cells[1].strip('"“”')))
    return formula, motion, nots, strip


def restyle_prompt(text, formula, motion, nots, strip, media_map):
    """The three mechanical operations. Returns (new_text, changes)."""
    changes = []
    out = text

    # 2. media swap — reference paths only, never prose
    for old, new in media_map.items():
        if old in out:
            out = out.replace(old, new)
            changes.append(f"media: {Path(old).name} → {Path(new).name}")

    # 3. strip photoreal descriptors, longest first so phrases beat words
    for old, new in sorted(strip, key=lambda p: -len(p[0])):
        if not old:
            continue
        pat = re.compile(re.escape(old), re.I)
        if pat.search(out):
            out = pat.sub(new, out)
            changes.append(f'strip: "{old[:44]}" → "{new[:44]}"')

    # 1. style lock LAST so it sits at the very top, untouched by the above
    lock = STYLE_LOCK.format(formula=formula, motion=motion, nots=nots)
    out = lock + out
    changes.insert(0, "style lock prepended")
    return out, changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True,
                    help="folder of the APPROVED scene prompts (.txt/.md)")
    ap.add_argument("--formula", required=True,
                    help="the stage-v1 style formula output")
    ap.add_argument("--media-map", default=None,
                    help="JSON {old_reference: converted_reference}")
    ap.add_argument("--out", required=True, help="where restyled prompts land")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    formula, motion, nots, strip = parse_formula(Path(a.formula).read_text())
    if not formula:
        sys.exit("no 'FORMULA LOCKED —' line in the formula file; stage v1 "
                 "must emit one, because that isolated copy is what gets pasted")
    media_map = json.loads(Path(a.media_map).read_text()) if a.media_map else {}

    src = Path(a.prompts)
    dst = Path(a.out)
    files = sorted(p for p in src.iterdir()
                   if p.suffix.lower() in (".txt", ".md"))
    if not files:
        sys.exit(f"no prompt files in {src}")
    print(f"formula: {formula[:90]}…")
    print(f"strip table: {len(strip)} descriptor(s) · media swaps: {len(media_map)}")
    print(f"{len(files)} approved prompt(s)\n")

    if not a.dry_run:
        dst.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in files:
        text = f.read_text()
        new, changes = restyle_prompt(text, formula, motion, nots, strip, media_map)
        total += len(changes)
        print(f"  {f.name}")
        for c in changes:
            print(f"      {c}")
        if not a.dry_run:
            (dst / f.name).write_text(new)
    print(f"\n{total} mechanical change(s) across {len(files)} prompt(s)")
    print("Nothing was rewritten, paraphrased or re-planned — every other word "
          "is the approved prompt, unchanged.")
    if a.dry_run:
        print("(dry run — nothing written)")


if __name__ == "__main__":
    main()
