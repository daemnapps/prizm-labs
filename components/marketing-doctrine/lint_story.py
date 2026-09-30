#!/usr/bin/env python3
"""The story gate: every brand's story.md has the template's shape.

    python3 components/marketing-doctrine/lint_story.py            # every brand
    python3 components/marketing-doctrine/lint_story.py <file> ... # named files

Mirrors lint_position.py. The shape is the one <brand>'s hand-built file set and
Damon approved on 2026-09-19 ("story looks good"); brands/_TEMPLATE/brand-identity/story.md
carries it with no brand in it.

What it checks, per file:
  * a `## The story block` section holding ONE fenced block
  * the fifteen slots, in the template's order, each exactly once, one per
    line, `LABEL: value` — a slot may say `open`, never be missing or empty;
    the last one is `confirmed by:`
  * the standard `##` sections, in the template's order; a second-lane block
    (`## The <name> lane …`) is allowed between `## The tellers` and
    `## How a run uses this`, and extra sections only under `## Also on file`
  * a lane block's fence, when it has one, uses the block's labels, in the
    block's order, and ends with `confirmed by:`
  * every `###` under `## The stories` is `<kebab-id> — <line>` and carries
    **Beats:**, **Teller:**, **Fits:** and **Receipt:**/**Receipts:**
  * every id in STORIES has its `###`, and every `###` is in STORIES
  * no `<placeholder>` left from the template (inline code is ignored)
  * brand-agnostic template: brands/_TEMPLATE/brand-identity/story.md names no brand
Exit 0 = clean. Exit 1 = findings. Exit 2 = nothing to check.
Stdlib only.
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent
# v6 layout: story and position live in brand-identity/; the old top-level spot is still read
TEMPLATE = next((t for t in (WS / "brands" / "_TEMPLATE" / "brand-identity" / "story.md",
                             WS / "brands" / "_TEMPLATE" / "story.md") if t.is_file()),
                WS / "brands" / "_TEMPLATE" / "brand-identity" / "story.md")

SLOTS = ["SPINE", "BEFORE", "TURN", "AFTER", "TELLERS", "ENTRY", "STORIES", "ARC",
         "REASON TO SWITCH", "OPENS IN", "PRODUCT ENTERS", "PROOF", "VOICE", "NEVER",
         "confirmed by"]
SECTIONS = ["The story block", "The lesson this file comes from", "The stories",
            "The tellers", "How a run uses this", "Where it lives in the chains",
            "Receipts", "Open"]
LANE = re.compile(r"^The .+ lane\b")
OPTIONAL_TAIL = ["Also on file"]
# The template has the writer mark an unfinished story "(open)" — it may land in the heading too.
STORY_HEAD = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)(?: \(open\))? — \S")
STORY_FIELDS = [("Beats", r"\*\*Beats:\*\*"), ("Teller", r"\*\*Teller:\*\*"),
                ("Fits", r"\*\*Fits:\*\*"), ("Receipt", r"\*\*Receipts?:\*\*")]


def brand_names():
    b = WS / "brands"
    return [p.name for p in b.iterdir() if p.is_dir() and not p.name.startswith("_")] if b.is_dir() else []


def section_body(text, head):
    m = re.search(rf"^## {re.escape(head)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def parse_block(fence):
    """-> (labels, values, findings) for one fenced block's lines."""
    f, labels, values = [], [], {}
    lines = fence.splitlines()
    if any(not l.strip() for l in lines):
        f.append("blank line inside the block")
    for l in lines:
        if not l.strip():
            continue
        mm = re.match(r"^([A-Za-z][A-Za-z ]*?): ?(.*)$", l)
        if not mm:
            f.append(f"not `LABEL: value`: {l[:60]!r}")
            continue
        labels.append(mm.group(1)); values[mm.group(1)] = mm.group(2).strip()
    return labels, values, f


def story_ids(value):
    """STORIES: a · b (open) · c  ->  ['a', 'b', 'c']"""
    if value.strip().lower() in ("", "open"):
        return []
    return [p.strip().split()[0] for p in value.split("·") if p.strip()]


def check(path, is_template=False):
    f = []
    try:
        text = Path(path).read_text()
    except Exception as e:
        return [f"cannot read: {e}"]
    # --- sections
    heads = re.findall(r"^## (.+?)\s*$", text, re.M)
    got_std = [h for h in heads if h in SECTIONS]
    missing = [s for s in SECTIONS if s not in heads]
    if missing:
        f.append("missing section(s): " + " · ".join(f"## {m}" for m in missing))
    elif got_std != SECTIONS:
        f.append("sections out of the template's order: " + " → ".join(got_std))
    lanes = [h for h in heads if h not in SECTIONS and LANE.match(h)]
    extra = [h for h in heads if h not in SECTIONS + OPTIONAL_TAIL and h not in lanes]
    if extra:
        f.append("section(s) the template does not name (put them under `## Also on file`): "
                 + " · ".join(f"## {h}" for h in extra))
    if not missing:
        lo, hi = heads.index("The tellers"), heads.index("How a run uses this")
        for ln in lanes:
            if not lo < heads.index(ln) < hi:
                f.append(f"`## {ln}` must sit between `## The tellers` and `## How a run uses this`")
    # --- the block
    body = section_body(text, "The story block")
    if body is None:
        f.append("no `## The story block` section")
        return f
    fences = re.findall(r"^```[^\n]*\n(.*?)^```", body, re.M | re.S)
    if len(fences) != 1:
        f.append(f"`## The story block` must hold exactly one fenced block, found {len(fences)}")
        return f
    labels, values, bf = parse_block(fences[0])
    f += bf
    if labels != SLOTS:
        miss = [s for s in SLOTS if s not in labels]
        unknown = [s for s in labels if s not in SLOTS]
        dupes = sorted({s for s in labels if labels.count(s) > 1})
        if miss: f.append("missing slot(s): " + " · ".join(miss))
        if unknown: f.append("slot(s) the template does not name: " + " · ".join(unknown))
        if dupes: f.append("slot(s) repeated: " + " · ".join(dupes))
        if not (miss or unknown or dupes): f.append("slots out of the template's order")
    for s, v in values.items():
        if not v:
            f.append(f"{s}: empty — write `open` if it is not settled")
    # --- lane blocks: a subset of the labels, same order, confirmed by last
    for ln in lanes:
        for fence in re.findall(r"^```[^\n]*\n(.*?)^```", section_body(text, ln) or "", re.M | re.S):
            ll, lv, lf = parse_block(fence)
            f += [f"`## {ln}`: {x}" for x in lf]
            bad = [x for x in ll if x not in SLOTS]
            if bad:
                f.append(f"`## {ln}`: label(s) the block does not use: " + " · ".join(bad))
            elif ll != sorted(ll, key=SLOTS.index) or len(set(ll)) != len(ll):
                f.append(f"`## {ln}`: labels out of the block's order, or repeated")
            if not ll or ll[-1] != "confirmed by":
                f.append(f"`## {ln}`: the block must end with `confirmed by:`")
    # --- the stories
    sb = section_body(text, "The stories") or ""
    parts = re.split(r"^### (.+?)\s*$", sb, flags=re.M)
    stories = list(zip(parts[1::2], parts[2::2]))
    if not stories:
        f.append("`## The stories` holds no `###` story")
    ids = []
    for head, sbody in stories:
        if not is_template:
            m = STORY_HEAD.match(head)
            if not m:
                f.append(f"story heading is not `<kebab-id> — <line>`: {head[:60]!r}")
                continue
            ids.append(m.group(1))
        lacking = [n for n, rx in STORY_FIELDS if not re.search(rx, sbody)]
        if lacking:
            f.append(f"story {head.split(' — ')[0]!r} lacks: " + " · ".join(lacking))
    if not is_template:
        listed = story_ids(values.get("STORIES", ""))
        if values.get("STORIES", "").strip().lower() != "open":
            nohead = [s for s in listed if s not in ids]
            unlisted = [s for s in ids if s not in listed]
            if nohead: f.append("STORIES names a story with no `###`: " + " · ".join(nohead))
            if unlisted: f.append("`###` story not listed in STORIES: " + " · ".join(unlisted))
        # placeholders, ignoring inline code (`confirmed by: <name>` is an instruction)
        bare = re.sub(r"`[^`\n]*`", "", text)
        ph = re.findall(r"<[a-z][^<>\n]{2,60}>", bare)
        if ph:
            f.append(f"{len(ph)} template placeholder(s) left, e.g. {ph[0]!r}")
    else:
        for b in brand_names():
            if re.search(rf"\b{re.escape(b)}\b", text, re.I):
                f.append(f"template names a brand: {b}")
    return f


def main(argv):
    files = [Path(a) for a in argv] or sorted(
        p for p in [*(WS / "brands").glob("*/story.md"), *(WS / "brands").glob("*/brand-identity/story.md")]
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
