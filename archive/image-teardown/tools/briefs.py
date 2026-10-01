#!/usr/bin/env python3
"""The brief register — the bank brief ids are looked up in, never coined.

    briefs.py list                          every brief, newest first
    briefs.py open <run> --brand <brand>    give a finished run its id
    briefs.py show <id>                     one brief's record

A brief id has been sitting in the ad name since the naming convention was
written — the `brief` field, `p003` in
`<brand>-flex-static-ai-ray-…-razornotproblem-faceoff-p003-9x16-260907b`. It is
in the name rather than the manifest because a Meta report is often read by
someone with no repo access, and "which briefs produce winners" is worth
ranking.

**Nothing defined those ids.** p001–p004 and p140–p142 are live in ad names
and in the creative ledger with no file behind them, so a new run either
guessed a number or wrote something off-convention (`braille`, 2026-09-13).
This is that file: one record per brief, so the id resolves to the swipe it
came from, the run that produced it, and the ads that carry it.

Ids are per brand and sequential in the brand's own block, because that is
how the live ones already read; the seeds live in briefs.json.
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REGISTER = HERE / "briefs.json"
RUNS = HERE / "runs"

# Each brand gets its own hundred. The first two blocks are read off ids
# already live in ad names — <brand> at p001, <brand> at p140 — and every brand
# after them is allocated the next free hundred the first time it opens a
# brief. It used to be a hand-written map, so standing up a new brand exited
# and told somebody to edit this file, which is a person in the loop for no
# reason (2026-09-14).
BLOCK_SIZE = 100


def block_for(reg, brand):
    """This brand's hundred, allocated and remembered on first use."""
    # The first blocks were read off ids already live in ad names and live in
    # briefs.json as data. No brand is named in this file — a brand name in
    # code is how the next brand's run quietly aims at the last brand.
    blocks = reg.setdefault("blocks", {})
    if brand not in blocks:
        taken = set(blocks.values())
        n = 1
        while n in taken:
            n += BLOCK_SIZE
        blocks[brand] = n
    return blocks[brand]


def load():
    return json.loads(REGISTER.read_text()) if REGISTER.is_file() else {"briefs": {}}


def save(reg):
    REGISTER.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")


def next_id(reg, brand):
    """The next free id in this brand's block. Never reuses one."""
    lo = block_for(reg, brand)
    # Retired ids stay taken. A brief pulled off the board is not a free
    # number: the id travels into ad names and creative records, and
    # reissuing it would point two different ads at one row.
    # (Damon, 2026-09-15: "remove those" — p011-p014.)
    taken = {int(k[1:]) for k in list(reg["briefs"]) + list(reg.get("retired", {}))
             if re.fullmatch(r"p\d{3}", k)}
    n = lo
    while n in taken:
        n += 1
    if n >= lo + BLOCK_SIZE:
        # Spill into the next free hundred rather than stopping. A full block
        # is a counting problem, not a decision anybody needs to make.
        return next_id({"briefs": reg["briefs"],
                        "blocks": {**reg.get("blocks", {}),
                                   brand: max(reg.get("blocks", {}).values() or [0])
                                   + BLOCK_SIZE}}, brand)
    return f"p{n:03d}"


def read_run(run: Path):
    """What the run itself says it is. Nothing here is invented."""
    src = json.loads((run / "assets/source.json").read_text()) \
        if (run / "assets/source.json").is_file() else {}
    out = run / "out"
    stages = {p.name: p for p in sorted(out.glob("0*.md"))} if out.is_dir() else {}
    brief = out / "06-brief.md"
    fields = {}
    if brief.is_file():
        # stage 6 declares problem / angle / concept in a json block
        m = re.search(r'\{[^{}]*"problem"[^{}]*\}', brief.read_text(), re.S)
        if m:
            try:
                fields = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return src, stages, fields


def open_brief(run_name, brand, reg=None, product=None, avatar=None):
    run = RUNS / run_name
    if not run.is_dir():
        sys.exit(f"no run at {run}")
    reg = reg or load()
    for bid, rec in reg["briefs"].items():
        if rec["run"] == run_name:
            return bid, rec           # a run gets one id, for ever

    src, stages, fields = read_run(run)
    if "06-brief.md" not in stages:
        sys.exit(f"{run_name} has no 06-brief.md — a brief id is for a "
                 f"finished brief, not a run in progress")

    bid = next_id(reg, brand)
    reg["briefs"][bid] = {
        "brand": brand,
        "product": product,
        "avatar": avatar,
        "run": run_name,
        "opened": date.today().isoformat(),
        "swipe": {"brand": src.get("swipe"), "block": src.get("block"),
                  "block_file": src.get("block_file"),
                  "clone": src.get("clone"), "variants": src.get("variants"),
                  "drive": src.get("drive"), "why": src.get("why")},
        "declares": fields,           # problem / angle / concept, as stage 6 wrote them
        "stages": sorted(stages),
        "status": "for-review",       # for-review -> approved -> in-production
        "ads": [],                    # ad names that carry this brief id
    }
    save(reg)
    return bid, reg["briefs"][bid]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    o = sub.add_parser("open"); o.add_argument("run"); o.add_argument("--brand", required=True)
    o.add_argument("--product"); o.add_argument("--avatar")
    s = sub.add_parser("show"); s.add_argument("id")
    a = ap.parse_args()
    reg = load()

    if a.cmd == "list":
        for bid, r in sorted(reg["briefs"].items(), reverse=True):
            d = r.get("declares", {})
            # A reserved id has no run — it predates the register.
            run = r["run"] or "(before the register)"
            print(f"{bid}  {r['opened']:<20} {r['brand']:<8} {r['status']:<13} "
                  f"{run:<34} angle={d.get('angle') or '—'}")
    elif a.cmd == "open":
        bid, rec = open_brief(a.run, a.brand, reg, a.product, a.avatar)
        print(f"{bid}  {rec['run']}  ({rec['status']})")
    elif a.cmd == "show":
        print(json.dumps(reg["briefs"].get(a.id) or f"no brief {a.id}", indent=1))


if __name__ == "__main__":
    main()
