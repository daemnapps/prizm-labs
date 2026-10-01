#!/usr/bin/env python3
"""The research gatherer, for THIS chain — the `{research}` var that stages 6
and 7 read, and the deep-research trigger's CLI, over the shared component.

    python3 research.py run --run results/<label>
    python3 research.py deep --brand <brand> --avatar spot-hider --sub sun-damage-reckoner
    python3 research.py rooms --brand <brand> --avatar spot-hider --sub sun-damage-reckoner
    python3 research.py deep --brand <brand> --all
    python3 research.py deep --pick-thinnest --cap 150
    python3 research.py deep --brand <brand> --avatar spot-hider --sub sun-damage-reckoner --dry-run

SHIM (2026-09-18, Damon's ruling: *"the live research gatherer runs in the
copy machine too"*). Exactly the shape of
`components/video-teardown/machine/research.py` — the LL-1 precedent, the
same one `language.py` and `paths.py` in this folder already follow. The
engine lives once, in `components/research-gatherer/`; this file is only
THIS chain's definitions on top of it:

  * which language STAGE_USE keys the research packet's language section
    should query — `depth` and `spice`, both defined in THIS folder's
    `language.py`, never in the engine;
  * which `for_stage` callable answers them — this machine's own;
  * where a run's `research/` folder lives — beside the run's own stage
    outputs, in `results/<label>/`.

Nothing brand-specific lives here (workspace rule 7). Rooms and desire words
arrive at run time from `brands/<brand>/core-avatars/**`, and since
2026-09-18 the gatherer FINDS the rooms itself when nobody has confirmed a
`### rooms` block — Damon should never have to write down where an avatar
talks.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from paths import HERE as PACKAGE, WORKSPACE   # noqa: E402  the copy package root
import language as L                           # noqa: E402  this chain's STAGE_USE (depth, spice)

_COMPONENT = next((d for d in Path(__file__).resolve().parents if (d / "components" / "research-gatherer").is_dir()), Path(__file__).resolve().parents[2].parent) / "components" / "research-gatherer"
if not _COMPONENT.is_dir():                     # a workspace mounted elsewhere
    _COMPONENT = Path(WORKSPACE) / "components" / "research-gatherer"
sys.path.append(str(_COMPONENT))                # appended, never ahead of this machine
from research_gatherer import engine as _engine  # noqa: E402

_engine.configure(workspace=WORKSPACE)


def _run_dir(st):
    """Where THIS chain keeps a run's own folder — `<run>/research/` lands
    beside `<run>/stage6--expansion.md` the way every other stage output
    does. `out_dir` wins when the runner hands one in (it already knows the
    folder it made); otherwise it is rebuilt from the run's label."""
    out = st.get("out_dir")
    if out:
        return Path(out)
    slug = st.get("slug") or st.get("label")
    if not slug:
        return None
    # Both homes (2026-09-20): a run that exists is found where it is —
    # runs/copy-machine/<brand>/<label> first, then results/<label>. One that
    # does not exist yet is a new run, and new runs file under runs/.
    # Another tool that imports this shim (email production) has ITS OWN
    # module called `paths` loaded, which knows neither function — it always
    # hands out_dir in, and if it ever does not, the old answer still stands.
    import paths as _P
    if not hasattr(_P, "find_run"):
        return PACKAGE / "results" / slug
    found = _P.find_run(slug, st.get("brand"))
    if found:
        return found
    return _P.run_dir(st["brand"], slug) if st.get("brand") else (PACKAGE / "results" / slug)


# The per-chain definition (components/research-gatherer/README.md,
# "chain_profile — the definition a caller hands inputs()"). `depth` is the
# expansion stage's Schwartz pass — mechanism, accepted-belief, role-claimed
# once the market is stage-3+ sophisticated; `spice` is the subculture
# register the close needs to sound like the room rather than like a brand.
# Both keys live in THIS FOLDER's `language.py`, STAGE_USE, not the engine.
CHAIN_PROFILE = {
    "language_stages": ["depth", "spice"],
    "language_for_stage": L.for_stage,
    "run_dir": _run_dir,
}

# The component's surface, re-exported — one home, no second implementation.
FALLBACK_QUESTIONS = _engine.FALLBACK_QUESTIONS
parse_rooms = _engine.parse_rooms
desire_words = _engine.desire_words
rooms_and_words = _engine.rooms_and_words
resolve_rooms = _engine.resolve_rooms
rooms_block_state = _engine.rooms_block_state
rooms_are_confirmed = _engine.rooms_are_confirmed
find_rooms = _engine.find_rooms
tally_rooms = _engine.tally_rooms
write_rooms_block = _engine.write_rooms_block
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

UNAVAILABLE = "[UNFILLED: research gatherer not available]"


def inputs(st):
    """The `{research}` var. Never raises — the engine's own guarantee, and
    this wrapper on top of it, because a research gap must never be why a
    copy run stops."""
    try:
        return _engine.inputs(st, chain_profile=CHAIN_PROFILE)
    except Exception as e:                       # belt and braces
        return {"research": f"# Research\n\n[UNFILLED: the research gatherer failed — {e}]\n"}


def text_for(brand=None, avatar=None, funnel=None, source_url=None, out_dir=None,
             slug=None, topics=None, sub=None):
    """One call, one string, for a runner that just wants `{research}`.

    Everything it needs is named, so `copy.py` builds no state dict of its
    own and nothing here reaches into the runner. Returns the UNAVAILABLE
    line rather than raising, whatever goes wrong."""
    try:
        st = {
            "brand": brand,
            "slug": slug,
            "out_dir": str(out_dir) if out_dir else None,
            "source_url": source_url,
            "audience": {"_avatar": avatar, "_funnel": funnel,
                        "_sub_avatar": sub, "_topics": list(topics or [])},
        }
        out = inputs(st)
        return (out or {}).get("research") or UNAVAILABLE
    except Exception:
        return UNAVAILABLE


# ---------------------------------------------------------------- CLI

def main():
    import argparse, json
    ap = argparse.ArgumentParser(description="The research gatherer, for the copy chain.")
    subs = ap.add_subparsers(dest="cmd", required=True)

    r = subs.add_parser("run", help="the {research} var, over a run folder already on disk")
    r.add_argument("--run", required=True)

    for name, helptext in (("deep", "file rows into one (or every) sub-avatar's own bank"),
                           ("rooms", "find where an avatar actually talks, and write it back")):
        d = subs.add_parser(name, help=helptext)
        d.add_argument("--brand")
        d.add_argument("--avatar")
        d.add_argument("--sub")
        d.add_argument("--all", action="store_true", help="every sub-avatar of --brand")
        d.add_argument("--pick-thinnest", action="store_true",
                       help="across ALL brands, the sub-avatar with the fewest language rows")
        d.add_argument("--cap", type=int, default=None)
        d.add_argument("--dry-run", action="store_true", help="print the queries; spend nothing")

    a = ap.parse_args()

    if a.cmd == "run":
        run_dir = Path(a.run).resolve()
        rj = run_dir / "run.json"
        if not rj.is_file():
            sys.exit(f"no run.json at {run_dir}")
        st = json.loads(rj.read_text())
        st.setdefault("audience", {})
        st["audience"].setdefault("_avatar", st.get("avatar"))
        st["audience"].setdefault("_funnel", st.get("funnel"))
        out = _engine.run_over(st, chain_profile=CHAIN_PROFILE, out_dir=run_dir / "research")
        print(out["research"][:4000])
        return

    # deep / rooms are the component's own chain-agnostic CLI, verbatim.
    argv = [a.cmd]
    for flag, val in (("--brand", a.brand), ("--avatar", a.avatar), ("--sub", a.sub)):
        if val:
            argv += [flag, val]
    if a.all:
        argv.append("--all")
    if a.pick_thinnest:
        argv.append("--pick-thinnest")
    if a.cap:
        argv += ["--cap", str(a.cap)]
    if a.dry_run:
        argv.append("--dry-run")
    sys.exit(_engine.main(argv))


if __name__ == "__main__":
    main()
