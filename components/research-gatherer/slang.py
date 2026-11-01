#!/usr/bin/env python3
"""Slang research for one avatar — see research_gatherer/slang.py.

    python3 components/research-gatherer/slang.py --brand B --avatar A [--dry-run] [--limit 40]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_gatherer import slang as SL   # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True); ap.add_argument("--avatar", required=True)
    ap.add_argument("--limit", type=int, default=40); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--tell", nargs=2, metavar=("TERM", "MEANING"), help="record a term a person told us, with its meaning")
    ap.add_argument("--double", help="with --tell: the two readings a writer plays on")
    ap.add_argument("--by", help="with --tell: who told us")
    ap.add_argument("--trends", help="who to search the web for, e.g. \"young men 18-34\": today's slang joins the room's")
    a = ap.parse_args()
    if a.tell:
        print(SL.tell(a.brand, a.avatar, a.tell[0], a.tell[1], a.by or "a person", a.double))
        sys.exit(0)
    r = SL.research(a.brand, a.avatar, limit=a.limit, dry_run=a.dry_run, model=a.model, trends_for=a.trends)
    if a.dry_run:
        print(r["prompt"][:3000])
