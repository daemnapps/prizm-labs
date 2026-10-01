#!/usr/bin/env python3
"""The research gatherer, for THIS chain — the `~research` var, and the
deep-research trigger's CLI, over the shared component.

    python3 research.py run --run runs/<slug>
    python3 research.py deep --brand <brand> --avatar fed-up-king --sub bald-bumps-guy
    python3 research.py deep --brand <brand> --all
    python3 research.py deep --pick-thinnest --cap 150
    python3 research.py deep --brand <brand> --avatar fed-up-king --sub bald-bumps-guy --dry-run

SHIM (RG-1, 2026-09-18). The engine moved to `components/research-gatherer/`
so the query-the-open-internet logic has ONE home — the LL-1 precedent
(`language.py` below is that same shim shape for the language bank). This
file is the same command it always was: it re-exports the component's
`inputs`/`deep_for`/`pick_thinnest` and hands them THIS chain's own
settings — its `depth`/`spice` STAGE_USE keys, its own `for_stage`, and
where a run's `research/` folder lives. run.py's `~research` binding is
unchanged: it still calls a plain `research.inputs(st)`.

`chain_profile` below stays HERE because it is this chain's definition, not
the engine's: which STAGE_USE keys feed the language section, and which
`for_stage` answers them, differ legitimately between chains (the copy
chain would hand in its own `language.py`'s `for_stage`), and the engine
that shipped one chain's map would be that chain's engine.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C          # noqa: E402  WS, MACHINE, runs_root()
import language as L       # noqa: E402  this chain's STAGE_USE (depth, spice)

_COMPONENT = Path(__file__).resolve().parents[2] / "research-gatherer"
if not _COMPONENT.is_dir():                     # a workspace mounted elsewhere
    _COMPONENT = Path(C.WS) / "components" / "research-gatherer"
sys.path.append(str(_COMPONENT))                # appended, never ahead of this machine
from research_gatherer import engine as _engine  # noqa: E402

_engine.configure(workspace=C.WS)


def _run_dir(st):
    """Where THIS chain keeps a run's own folder — `<run>/research/` lands
    beside `<run>/stages/` the way every other stage output does."""
    slug = st.get("slug")
    return (C.runs_root() / slug) if slug else None


# The per-chain definition (components/research-gatherer/README.md,
# "chain_profile — the definition a caller hands inputs()"). `depth` leads
# with mechanism/accepted-belief/role-claimed once the market is stage-3+
# sophisticated; `spice` is the 4g creative pass's subculture register —
# both keys live in THIS FILE's `language.py`, STAGE_USE, not the engine.
CHAIN_PROFILE = {
    "language_stages": ["depth", "spice"],
    "language_for_stage": L.for_stage,
    "run_dir": _run_dir,
}

# The public surface this file has always had: a plain `inputs(st)` that
# run.py binds as `~research`, unchanged by the move underneath it.
FALLBACK_QUESTIONS = _engine.FALLBACK_QUESTIONS
parse_rooms = _engine.parse_rooms
desire_words = _engine.desire_words
rooms_and_words = _engine.rooms_and_words
schwartz_questions = _engine.schwartz_questions
platform_of = _engine.platform_of
build_queries_per_question = _engine.build_queries_per_question
all_sub_avatars = _engine.all_sub_avatars
row_count = _engine.row_count
pick_thinnest = _engine.pick_thinnest
build_bank_rows = _engine.build_bank_rows
demographics = _engine.demographics
room_fit = _engine.room_fit
split_by_fit = _engine.split_by_fit
markers_table = _engine.markers_table
deep_for = _engine.deep_for
reddit_door = _engine.reddit_door
apify_layer = _engine.apify_layer


def inputs(st):
    """The `~research` var — run.py calls this exactly like
    `creator_profile.inputs(st)`. Never raises (the engine's own guarantee)."""
    return _engine.inputs(st, chain_profile=CHAIN_PROFILE)


# ---------------------------------------------------------------- CLI

def main():
    import argparse, json
    ap = argparse.ArgumentParser(description="The research gatherer, for the video-teardown chain.")
    subs = ap.add_subparsers(dest="cmd", required=True)

    r = subs.add_parser("run", help="the ~research var, over a run folder already on disk")
    r.add_argument("--run", required=True)

    d = subs.add_parser("deep", help="file rows into one (or every) sub-avatar's own bank")
    d.add_argument("--brand")
    d.add_argument("--avatar")
    d.add_argument("--sub")
    d.add_argument("--all", action="store_true", help="every sub-avatar of --brand")
    d.add_argument("--pick-thinnest", action="store_true",
                   help="across ALL brands, the sub-avatar with the fewest language rows")
    d.add_argument("--cap", type=int, default=_engine.default_cap("forums_per_deep", 150))
    d.add_argument("--dry-run", action="store_true", help="print the queries; spend nothing")

    a = ap.parse_args()

    if a.cmd == "run":
        run_dir = Path(a.run).resolve()
        rj = run_dir / "run.json"
        if not rj.is_file():
            sys.exit(f"no run.json at {run_dir}")
        st = json.loads(rj.read_text())
        out = _engine.run_over(st, chain_profile=CHAIN_PROFILE, out_dir=run_dir / "research")
        print(out["research"][:4000])
        return

    if a.pick_thinnest:
        picked, ranked = pick_thinnest()
        if not picked:
            sys.exit("no sub-avatars found anywhere in brands/")
        print(f"pick-thinnest: {picked['brand']}/{picked['avatar']}/{picked['sub']} "
             f"({picked['rows']} language rows on file — thinnest of {len(ranked)})")
        targets = [picked]
    elif a.all:
        if not a.brand:
            sys.exit("--all needs --brand")
        targets = [c for c in all_sub_avatars() if c["brand"] == a.brand]
        if not targets:
            sys.exit(f"{a.brand} has no sub-avatars on file")
    else:
        if not (a.brand and a.avatar and a.sub):
            sys.exit("name --brand --avatar --sub, or pass --all / --pick-thinnest")
        targets = [dict(brand=a.brand, avatar=a.avatar, sub=a.sub)]

    for t in targets:
        print(f"\n== {t['brand']} / {t['avatar']} / {t['sub']} ==")
        res = deep_for(t["brand"], t["avatar"], t["sub"], a.cap, dry_run=a.dry_run)
        if res.get("dry_run"):
            print(f"  rooms: {res['rooms'] or '(none — nothing would be pulled)'}")
            print(f"  words: {res['words']}")
            if res.get("fallback_questions"):
                print("  (fallback question bank — components/marketing-doctrine/frameworks.json not found)")
            for q in res["queries"]:
                print(f"    {q['question']:<20} {q['tags']}: \"{q['query']}\"")
            continue
        if not res.get("ok"):
            print(f"  [UNFILLED] {res.get('why')}")
            continue
        print(f"  rows written: {res['rows_written']}  spend: ${res['spend']:.3f}")
        for s in res.get("sample", [])[:5]:
            print(f"    - {s['text'][:100]!r} — {s['source']['ref']}")


if __name__ == "__main__":
    main()
