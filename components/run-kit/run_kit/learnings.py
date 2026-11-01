"""The chain's learnings: every correction so it never happens again, every win so it happens again. Any chain, any brand.

the owner, 2026-10-17: "every time a shift is made on the copy level, on the image level, whatever the case may be, with
the feedback, that all needs to be stored and put into learnings back up and through the chain … it needs to
compound", and the same day: "this learning stuff should definitely be agnostic … this is for the overall chain."

Two stores, both under the repo's runs/ (a machine never writes brands/):

    runs/learnings/_all.jsonl       holds for every brand and every chain (no brand is ever named in it)
    runs/learnings/<brand>.jsonl    facts about one brand only (its product, its colours, its people)

Each line: {"at", "by", "chain", "stage", "kind", "rule", "why", "from"}
    chain   email | ads | video | page | all       (which line it came from; `all` reaches every line)
    stage   calendar | copy | design | picture | edit | build | all
    kind    do | never     (a later {"kind": "retire", "n": i} line retires rule i of that store)

Read by every stage that writes or makes something: `block(brand, stages, chain)` is the text a prompt carries.
The image engine (tools/image-production) reads the `picture` rules on every picture it makes, so ads, emails
and video frames all learn from one another.

    python3 -m run_kit.learnings add  --stage picture --kind never --rule "…" --why "…" --by the team [--brand b] [--chain email]
    python3 -m run_kit.learnings list [--brand b] [--stage picture]
    python3 -m run_kit.learnings retire --n 4 --why "…" [--brand b]
"""
import argparse
import datetime
import json
from pathlib import Path

from . import paths

STAGES = ("calendar", "copy", "design", "picture", "edit", "build", "all")


def _store(brand):
    return Path(paths.repo()) / "runs" / "learnings" / ("%s.jsonl" % (brand or "_all"))


def load(brand=None):
    f = _store(brand)
    if not f.exists():
        return []
    rows = []
    for x in f.read_text().splitlines():
        try:
            rows.append(json.loads(x))
        except ValueError:
            continue
    retired = {r.get("n") for r in rows if r.get("kind") == "retire"}
    return [dict(r, n=i) for i, r in enumerate(rows) if r.get("kind") in ("do", "never") and i not in retired]


def add(brand, stage, kind, rule, why="", by="", src="", chain="all"):
    f = _store(brand)
    f.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": datetime.date.today().isoformat(), "by": by, "chain": chain or "all", "stage": stage, "kind": kind,
           "rule": rule.strip(), "why": (why or "").strip(), "from": src}
    with f.open("a") as h:
        h.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def retire(brand, n, why):
    f = _store(brand)
    with f.open("a") as h:
        h.write(json.dumps({"at": datetime.date.today().isoformat(), "kind": "retire", "n": n, "why": why}) + "\n")


def rules(brand, stages, chain=None):
    """Every rule that reaches these stages for this brand and chain: the shared ones, then the brand's, newest first."""
    want = set(stages) | {"all"}
    rows = [r for b in (None, brand) for r in load(b)
            if r.get("stage") in want and (chain is None or r.get("chain", "all") in (chain, "all"))]
    rows.sort(key=lambda r: r.get("at", ""), reverse=True)
    return rows


def block(brand, stages, chain=None, extra=()):
    """The learnings as the text a prompt carries; `extra` are lines a caller adds (e.g. its own send-backs)."""
    out = list(extra) + ["- %s %s%s" % ("DO:" if r["kind"] == "do" else "NEVER:", r["rule"],
                                        (" (why: %s)" % r["why"]) if r.get("why") else "") for r in rules(brand, stages, chain)]
    return "\n".join(out) if out else "(none yet)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--brand")
    a.add_argument("--chain", default="all")
    a.add_argument("--stage", choices=STAGES, required=True)
    a.add_argument("--kind", choices=("do", "never"), required=True)
    a.add_argument("--rule", required=True)
    a.add_argument("--why", default="")
    a.add_argument("--by", default="")
    a.add_argument("--from", dest="src", default="")
    li = sub.add_parser("list")
    li.add_argument("--brand")
    li.add_argument("--stage")
    r = sub.add_parser("retire")
    r.add_argument("--brand")
    r.add_argument("--n", type=int, required=True)
    r.add_argument("--why", required=True)
    x = ap.parse_args()
    if x.cmd == "add":
        print(json.dumps(add(x.brand, x.stage, x.kind, x.rule, x.why, x.by, x.src, x.chain), ensure_ascii=False))
    elif x.cmd == "list":
        for row in load(x.brand):
            if not x.stage or row["stage"] == x.stage:
                print("%3d  %-6s %-8s %-5s %s" % (row["n"], row.get("chain", "all"), row["stage"], row["kind"], row["rule"]))
    else:
        retire(x.brand, x.n, x.why)
        print("retired %d" % x.n)


if __name__ == "__main__":
    main()
