#!/usr/bin/env python3
"""Winner match: the brand's banked winners ranked against a swipe on a matrix of traits, both read from their own
teardowns, and the switch that writes the swipe on the winner the owner picks.

Every swipe is matched with a winner before writing: the winner gives what we say (its argument, proof and offer),
the swipe gives the form. The closer the two are in awareness and shape, the less the script has to bend either.

    python3 winner_match.py rank   <swipe run> [--brand B] [--top 8] [--json]
    python3 winner_match.py switch <swipe run> <winner run> --why "..." [--dry-run]
    python3 winner_match.py match  <run>                     stage 2w by hand (the writing chain runs it itself)
    python3 winner_match.py pick   <run> <winner run> --why "..."   the owner's pick (the Studio's Pick button)

rank    reads only finished teardown files (no model call, no spend). The swipe and every winner get the same trait
        sheet (`winner_index.traits`), and each trait is marked same / close / different:
          awareness in · awareness out · format · cast · framework · sections in order · sophistication ·
          length · pace · tone · hook · sound
        The score out of 100 weighs those marks (WEIGHTS); a trait unknown on either side is left out and the rest
        re-weighed. Each winner carries a plain reason, its proof (sales, cost per sale, return, last ran) and its
        index call (keep / watch). Copies of a winner are folded under it and a retired run is left out. Nothing is picked: the owner
        picks, and a top score under FIT_WEAK says so in words (no banked winner carries this shape).
switch  opens a new run folder beside the swipe's (`<swipe run>--w-<winner>`), carrying the swipe's teardown
        (stages 0-2, its files) and nothing written after it, sets the writing lane to the chosen winner, records
        `winner-pick.json` (winner, why, the ranking at the time) and runs the normal writing chain on it
        (writing_v2.py). The swipe's first run is left as it was. Spends model money: run on the owner's go.

Banked winners of a brand: the brand default (`brands/<brand>/winner.json`), the runs listed in
`brands/<brand>/winners.json` when that file exists, and every teardown run of that brand whose name carries
`winner` or `core`. The index (`winner_index.py build`) adds each one's proof and call.
"""
import argparse
import difflib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load_index():
    """winner_index, loaded fresh beside this module so both read the same workspace (tests point it elsewhere)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("winner_index_for_match", HERE / "winner_index.py")
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


WI = _load_index()

WS = WI.WS
RUNS = WI.RUNS
WRITING = Path(os.environ.get("VIDEO_WRITING_V2") or WS / "components" / "video-writing" / "machine" / "writing_v2.py")

# what a switch carries from the swipe's run: its teardown and its source, never anything written after stage 2
WRITTEN_STAGE = re.compile(r"^(3|4|5)")
WRITTEN_FILES = {"writing-result.json", "hook-matrix.json", "winner-pick.json", "usage.jsonl", "AUDIT-HOLD.md"}
WRITTEN_DIRS = {"revalidation", "section-fit", "hand"}
WRITTEN_KEYS = {"state", "stopped_at", "writing", "writing_retry_budget", "writing_v2_calls", "viewer_redo",
                "slot_fill", "claims_fixed", "section_fit", "cast_match", "production_contract",
                "writing_revalidation", "writing_error", "waiting_for"}

# the matrix: trait -> weight (sums to 100). Awareness and the shape of the scene lead: a winner that meets the
# viewer where the swipe meets him and moves him as far, in the same kind of scene, needs the least bending.
WEIGHTS = {"aware_in": 16, "aware_out": 6, "format": 14, "cast": 8, "framework": 10, "sections": 12,
           "sophistication": 6, "length": 10, "pace": 4, "tone": 8, "hook": 4, "sound": 2}
TRAIT_NAMES = {"aware_in": "awareness in", "aware_out": "awareness out", "format": "format", "cast": "cast",
               "framework": "framework", "sections": "sections", "sophistication": "sophistication",
               "length": "length", "pace": "pace", "tone": "tone", "hook": "hook", "sound": "sound"}
FIT_STRONG, FIT_WEAK = 70, 55


def _read(p):
    return WI._read(p)


def _json(p, default=None):
    return WI._json(p, default)


_mmss = WI.mmss


def profile(run):
    """The trait sheet of one teardown run (kept under its old name for readers of this module)."""
    return WI.traits(run)


def bank(brand):
    """The brand's banked winners: [(run, label)], the default first."""
    return [(r, WI.label(r)) for r in WI.banked_runs(brand)]


def _ladder(a, b):
    if not a or not b:
        return None
    ia, ib = WI.LADDER.index(a), WI.LADDER.index(b)
    return {0: 1.0, 1: 0.5}.get(abs(ia - ib), 0.0)


def _mark(v):
    return "same" if v >= 0.85 else ("close" if v >= 0.4 else "different")


def compare(sw, wn):
    """(score 0-100, matrix, facts) for one winner against the swipe. The matrix holds, per trait, the swipe's value,
    the winner's value, the match 0-1 and its mark; facts are the same in plain words."""
    m = {}

    def put(k, v, a, b):
        if v is not None:
            m[k] = {"swipe": a, "winner": b, "match": round(v, 2), "mark": _mark(v)}

    put("aware_in", _ladder(sw["aware_in"], wn["aware_in"]), sw["aware_in"], wn["aware_in"])
    put("aware_out", _ladder(sw["aware_out"], wn["aware_out"]), sw["aware_out"], wn["aware_out"])
    if sw["format"] and wn["format"]:
        v = 1.0 if sw["format"] == wn["format"] else (0.6 if sw["family"] and sw["family"] == wn["family"] else 0.0)
        put("format", v, sw["format"], wn["format"])
    put("cast", 1.0 if sw["cast"] == wn["cast"] else 0.0, sw["cast"], wn["cast"])
    if sw["framework"] and wn["framework"]:
        put("framework", 1.0 if sw["framework"] == wn["framework"] else 0.0, sw["framework"], wn["framework"])
    elif sw["framework"] or wn["framework"]:
        put("framework", 0.0, sw["framework"] or "none named", wn["framework"] or "none named")
    if sw["sections"] and wn["sections"]:
        v = difflib.SequenceMatcher(None, sw["sections"], wn["sections"]).ratio()
        put("sections", v, " → ".join(sw["sections"]), " → ".join(wn["sections"]))
    if sw["sophistication"] and wn["sophistication"]:
        put("sophistication", 1.0 if sw["sophistication"] == wn["sophistication"] else 0.0,
            sw["sophistication"], wn["sophistication"])
    if sw["runtime"] and wn["runtime"]:
        r = abs(math.log(wn["runtime"] / sw["runtime"]))
        put("length", max(0.0, 1 - r / math.log(4)), _mmss(sw["runtime"]), _mmss(wn["runtime"]))
    if sw["pace"] and wn["pace"]:
        put("pace", max(0.0, 1 - abs(wn["pace"] - sw["pace"]) / 2.0), f"{sw['pace']}/s", f"{wn['pace']}/s")
    st, wt = set(sw["tones"]), set(wn["tones"])
    if st and wt:
        put("tone", len(st & wt) / len(st | wt), ", ".join(sorted(st)), ", ".join(sorted(wt)))
    if sw["hook"] and wn["hook"]:
        put("hook", 1.0 if sw["hook"] == wn["hook"] else 0.0, sw["hook"], wn["hook"])
    if sw["sound"] and wn["sound"]:
        put("sound", 1.0 if sw["sound"] == wn["sound"] else 0.0, sw["sound"].lower(), wn["sound"].lower())
    if not m:
        return 0, m, ["no traits to compare"]
    w = sum(WEIGHTS[k] for k in m)
    score = round(100 * sum(WEIGHTS[k] * c["match"] for k, c in m.items()) / w)
    facts = []
    for k in WEIGHTS:
        if k in m:
            c = m[k]
            facts.append(f"{TRAIT_NAMES[k]}: both {c['swipe']}" if c["mark"] == "same" else
                         f"{TRAIT_NAMES[k]}: swipe {c['swipe']} · winner {c['winner']} ({c['mark']})")
    missing = [TRAIT_NAMES[k] for k in WEIGHTS if k not in m]
    if missing:
        facts.append("not compared (unknown on one side): " + ", ".join(missing))
    return score, m, facts


def reason(m, score):
    """One plain line: what lines up, then the biggest gap."""
    same = [TRAIT_NAMES[k] for k in WEIGHTS if k in m and m[k]["mark"] == "same"]
    gaps = sorted((k for k in m if m[k]["mark"] == "different"), key=lambda k: -WEIGHTS[k])
    parts = []
    if same:
        parts.append("same " + ", ".join(same[:4]))
    if gaps:
        g = gaps[0]
        parts.append(f"but {TRAIT_NAMES[g]} differs ({m[g]['swipe']} vs {m[g]['winner']})")
    elif not same:
        parts.append("close on most traits, the same on none")
    return "; ".join(parts) or "nothing to compare"


def fit_word(score):
    return "strong" if score >= FIT_STRONG else ("workable" if score >= FIT_WEAK else "weak")


def current_winner(run):
    return ((_json(RUNS / run / "run.json", {}) or {}).get("writing_lane") or {}).get("winner")


def source_run(run):
    """The swipe's first run behind a switched run (`<run>--w-<winner>`), else the run itself."""
    pick = _json(RUNS / run / "winner-pick.json", {}) or {}
    return pick.get("swipe_run") or run


def label(run, given=""):
    if given and given != run:
        return given
    return WI.label(run)


def _index(brand):
    idx = _json(WS / "runs" / "winners" / brand / "winner-index.json", {}) or {}
    return {r["run"]: r for r in idx.get("winners") or []}


def rank(run, brand=None, top=8, current=None):
    """The brand's winners ranked on the trait matrix against the swipe. Nothing is picked: `pick` is None until
    the owner picks with `switch`."""
    base = source_run(run)
    sw = WI.traits(base)
    if not sw:
        raise SystemExit(f"{base}: the swipe's teardown is not finished, so there is nothing to match on.")
    brand = brand or sw["brand"]
    cur = current_winner(run) or current
    idx = _index(brand)
    out, folded = [], {}
    for w, lab in bank(brand):
        if w == base:
            continue
        rec = idx.get(w) or {}
        if rec.get("copy_of"):
            folded.setdefault(rec["copy_of"], []).append(w)
            continue
        if (rec.get("retire") or {}).get("call") == "retire":     # not a winner: never offered as one
            continue
        wn = WI.traits(w)
        if not wn:
            continue
        if not wn["has_read"] and rec.get("traits"):          # the index borrowed a read for it
            wn = dict(rec["traits"])
        score, m, facts = compare(sw, wn)
        out.append({"winner": w, "label": label(w, lab), "score": score, "fit": fit_word(score),
                    "reason": reason(m, score), "matrix": m, "facts": facts, "current": w == cur,
                    "runtime": wn["runtime"], "tones": wn["tones"], "format": wn["format"],
                    "one_line": wn["one_line"], "argument": rec.get("argument"), "proof": rec.get("proof") or {},
                    "call": (rec.get("retire") or {}).get("call"), "call_why": (rec.get("retire") or {}).get("why"),
                    "run": _switched(base, w)})
    for x in out:
        x["copies"] = folded.get(x["winner"], [])
    out.sort(key=lambda x: (-x["score"], x["winner"]))
    for i, x in enumerate(out, 1):
        x["rank"] = i
    shown = out[:top] + [x for x in out[top:] if x["current"]]
    best = out[0]["score"] if out else 0
    verdict = (f"no banked winner carries this shape: the best fit is {best}/100" if best < FIT_WEAK else
               f"best fit {best}/100 ({fit_word(best)})")
    return {"swipe_run": base, "run": run, "brand": brand, "current": cur, "pick": None,
            "picked_by": "owner", "verdict": verdict,
            "swipe": {k: sw[k] for k in ("runtime", "pace", "tones", "format", "family", "cast", "framework",
                                         "sections", "aware_in", "aware_out", "sophistication", "hook", "sound",
                                         "one_line", "first_line")},
            "winners": shown, "banked": len(out), "folded": sum(len(v) for v in folded.values()),
            "weights": WEIGHTS, "thresholds": {"strong": FIT_STRONG, "weak_below": FIT_WEAK}}


def _switched(base, winner):
    """The run a switch to this winner made (or would make), and whether its writing is finished."""
    slug = switched_slug(base, winner)
    d = RUNS / slug
    return {"slug": slug, "exists": d.is_dir(), "brief": (d / "stages" / "5-brief.md").is_file()}


def switched_slug(base, winner):
    short = re.sub(r"^core\d*-", "", winner)[:24].strip("-")      # existing switched runs keep their names
    return f"{base}--w-{short}"


def _carry(src, dst):
    """Copy the swipe's run up to its teardown: hard links where the disk allows (source video), nothing written."""
    dst.mkdir(parents=True)
    for p in src.iterdir():
        if p.name in WRITTEN_FILES or p.name in WRITTEN_DIRS or p.name == "run.json":
            continue
        if p.is_dir():
            if p.name == "stages":
                (dst / "stages").mkdir()
                for f in p.iterdir():
                    if f.is_file() and not WRITTEN_STAGE.match(f.name):
                        shutil.copy2(f, dst / "stages" / f.name)
            elif p.name == "prompts":
                (dst / "prompts").mkdir()
                for f in p.iterdir():
                    if f.is_file() and not WRITTEN_STAGE.match(f.name) and not f.name.startswith(("stage3", "stage4", "stage5")):
                        shutil.copy2(f, dst / "prompts" / f.name)
            else:
                shutil.copytree(p, dst / p.name, copy_function=_link_or_copy)
        else:
            _link_or_copy(p, dst / p.name)


def _link_or_copy(a, b):
    try:
        os.link(a, b)
    except OSError:
        shutil.copy2(a, b)
    return b


def prepare(run, winner, why="", ranking=None):
    """Open the switched run folder; returns its slug. Writes nothing in the swipe's own run."""
    base = source_run(run)
    src = RUNS / base
    if not (RUNS / winner / "stages" / "1-teardown.md").is_file():
        raise SystemExit(f"No finished teardown for winner {winner}.")
    slug = switched_slug(base, winner)
    dst = RUNS / slug
    if dst.exists():
        return slug, False
    rec = _json(src / "run.json", {}) or {}
    _carry(src, dst)
    rec = {k: v for k, v in rec.items() if k not in WRITTEN_KEYS}
    rec["stages"] = {k: v for k, v in (rec.get("stages") or {}).items() if not re.match(r"stage[345]", k)}
    rec["slug"] = rec["label"] = slug
    rec["opened"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec["writing_lane"] = {"lane": "winner", "winner": winner, "set": rec["opened"], "switched_from": base}
    (dst / "run.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    ranking = ranking or rank(base, rec.get("brand"), top=50)
    row = next((x for x in ranking["winners"] if x["winner"] == winner), {})
    pick = {"swipe_run": base, "winner": winner, "label": row.get("label") or winner, "why": why,
            "rank": row.get("rank"), "score": row.get("score"), "facts": row.get("facts") or [],
            "previous_winner": current_winner(base), "at": rec["opened"],
            "ranking": [{k: x[k] for k in ("winner", "rank", "score", "facts")} for x in ranking["winners"]]}
    (dst / "winner-pick.json").write_text(json.dumps(pick, indent=1, ensure_ascii=False))
    return slug, True


def write(slug, log=None):
    """Run the normal writing chain (stages 3-5) on a switched run. True when its brief is written."""
    env = dict(os.environ)
    env.setdefault("DAEMN_STRUCTURE_APPROVALS", "all")     # the swipe's structure was approved on its first run
    out = open(log, "a") if log else None
    subprocess.run([sys.executable, str(WRITING), str(RUNS / slug)], cwd=str(WRITING.parent), env=env,
                   stdout=out, stderr=subprocess.STDOUT if out else None)
    return (RUNS / slug / "stages" / "5-brief.md").is_file()


# ------------------------------------------------------------------------------------------------- on the chain

MATCH_FILE = "winner-match.json"
WRITTEN_MARK = ("3-injection.md", "5-brief.md")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _brand_default(brand):
    return (_json(WS / "brands" / (brand or "") / "winner.json", {}) or {}).get("winner") or ""


def picked(st):
    """The winner the run is written on, when a person picked it: the owner on the board (`picked_by: owner`), or a
    winner named on the command that is not just the brand's default. None while the pick is open."""
    wl = st.get("writing_lane") or {}
    if wl.get("lane") != "winner" or not wl.get("winner"):
        return None
    if wl.get("picked_by"):
        return wl["winner"]
    return None if wl["winner"] == _brand_default(st.get("brand")) else wl["winner"]


def on_chain(d, st):
    """Stage 2w, Winner match: runs on every swipe before its writing. Builds the brand's index, ranks its winners
    against this swipe, writes `winner-match.json` in the run and the stage record. Picks nothing.

    Returns (go, why): go False when the run is on the winner lane and no person has picked yet, so the writing waits
    for the pick on the Studio board. A run whose writing already started, or a swipe-only run (no swipe to match,
    a from-scratch piece), is never held here."""
    d = Path(d)
    wl = st.get("writing_lane") or {}
    stages = st.setdefault("stages", {})
    if wl.get("lane") == "swipe" and (wl.get("why") or "").startswith("from scratch"):
        stages["stage2w"] = dict(status="skipped", name="Winner match", why="from scratch: no swipe to match",
                                 finished=_now())
        return True, ""
    base = source_run(d.name)
    try:
        if not WI.traits(base):
            stages["stage2w"] = dict(status="skipped", name="Winner match", why="the swipe's teardown is not finished",
                                     finished=_now())
            return True, ""
        WI.build(st.get("brand") or WI.traits(base)["brand"])
        res = rank(d.name, st.get("brand"), top=8)
    except (Exception, SystemExit) as e:  # noqa: BLE001  (a match that cannot run never stops the writing)
        stages["stage2w"] = dict(status="error", name="Winner match", error=str(e)[:300], finished=_now())
        return True, ""
    pick = picked(st)
    res["pick"] = pick
    res["picked_by"] = wl.get("picked_by") or ("command" if pick else None)
    res["at"] = _now()
    (d / MATCH_FILE).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    top = res["winners"][0] if res["winners"] else {}
    stages["stage2w"] = dict(status="done", name="Winner match", finished=res["at"], out=MATCH_FILE,
                             best=top.get("winner"), best_score=top.get("score"), verdict=res["verdict"],
                             picked=pick, banked=res["banked"])
    written = any((d / "stages" / f).is_file() for f in WRITTEN_MARK)
    if wl.get("lane") == "winner" and not pick and not written:
        st["waiting_for"] = "winner pick"
        return False, (f"waiting for the winner pick: {res['verdict']}; top: " +
                       "; ".join(f"{x['label']} {x['score']}" for x in res["winners"][:3]) +
                       ". Pick on the Studio board (Orders), or winner_match.py pick <run> <winner> --why ...")
    return True, ""


def pick_winner(run, winner, why, by="owner"):
    """The owner's pick. Nothing written on the run yet: the run itself takes the winner (lane winner, picked_by) and
    `winner-pick.json`. Already written: a new run is opened beside it (`switch`) so the first stays as it was.
    Returns {"run": <the run to write>, "new": bool}. Spends nothing; the caller starts the writing."""
    d = RUNS / run
    st = _json(d / "run.json", {}) or {}
    if not st:
        raise SystemExit(f"no run called {run}")
    if not (RUNS / winner / "stages" / "0-triage.md").is_file():
        raise SystemExit(f"no banked winner called {winner}")
    if not why.strip():
        raise SystemExit("a pick needs its reason")
    written = any((d / "stages" / f).is_file() for f in WRITTEN_MARK)
    if written:
        slug, new = prepare(run, winner, why)
        rec = _json(RUNS / slug / "run.json", {}) or {}
        rec["writing_lane"]["picked_by"] = by
        (RUNS / slug / "run.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        return {"run": slug, "new": new}
    match = _json(d / MATCH_FILE, {}) or {}
    row = next((x for x in match.get("winners") or [] if x["winner"] == winner), {})
    st["writing_lane"] = {"lane": "winner", "winner": winner, "picked_by": by, "why": why, "set": _now()}
    st.pop("waiting_for", None)
    s3 = (st.get("stages") or {}).get("stage3") or {}
    if s3.get("status") == "held" and "winner" in str(s3.get("error", "")):
        st["stages"].pop("stage3")
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    (d / "winner-pick.json").write_text(json.dumps({
        "swipe_run": source_run(run), "winner": winner, "label": row.get("label") or label(winner), "why": why,
        "by": by, "rank": row.get("rank"), "score": row.get("score"), "reason": row.get("reason"), "at": _now(),
        "ranking": [{k: x.get(k) for k in ("winner", "rank", "score", "reason")} for x in match.get("winners") or []]},
        indent=1, ensure_ascii=False))
    return {"run": run, "new": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick", help="the owner's pick: the run takes the winner (no writing started)")
    p.add_argument("run"); p.add_argument("winner"); p.add_argument("--why", required=True)
    m = sub.add_parser("match", help="stage 2w by hand: write winner-match.json into the run (no pick)")
    m.add_argument("run")
    r = sub.add_parser("rank"); r.add_argument("run"); r.add_argument("--brand"); r.add_argument("--top", type=int, default=8)
    r.add_argument("--json", action="store_true")
    s = sub.add_parser("switch"); s.add_argument("run"); s.add_argument("winner")
    s.add_argument("--why", required=True, help="the owner's reason for this pick; a switch is never automatic")
    s.add_argument("--dry-run", action="store_true", help="open the run folder only; no writing call")
    s.add_argument("--log")
    a = ap.parse_args()
    if a.cmd == "pick":
        print(json.dumps(pick_winner(a.run, a.winner, a.why)))
        return 0
    if a.cmd == "match":
        st = _json(RUNS / a.run / "run.json", {}) or {}
        go, why = on_chain(RUNS / a.run, st)
        (RUNS / a.run / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
        print("writing may go" if go else why)
        return 0
    if a.cmd == "rank":
        res = rank(a.run, a.brand, a.top)
        if a.json:
            print(json.dumps(res, indent=1, ensure_ascii=False))
            return 0
        sw = res["swipe"]
        print(f"swipe {res['swipe_run']}: {sw['format']}, {sw['cast']}, {_mmss(sw['runtime'])}, "
              f"{sw['aware_in'] or '?'} -> {sw['aware_out'] or '?'}, {sw['framework'] or 'no framework named'} · "
              f"{res['banked']} banked winners for {res['brand']} ({res['folded']} copies folded)")
        print(f"  {res['verdict']} · nothing picked: the owner picks, then `switch`")
        for x in res["winners"]:
            p = x["proof"]
            print(f"  {'*' if x['current'] else ' '} #{x['rank']} {x['score']:>3} {x['fit']:<8} {x['label']}"
                  f"  [{x['call'] or '?'}; {p.get('purchases') or '-'} sales, last ran {p.get('last_ran') or '?'}]")
            print("          " + x["reason"])
            for f in x["facts"]:
                print("            " + f)
        return 0
    slug, new = prepare(a.run, a.winner, a.why)
    print(("opened " if new else "already open: ") + slug, flush=True)
    if a.dry_run:
        return 0
    ok = write(slug, a.log)
    print(("brief written: " if ok else "writing stopped before the brief: ") + slug)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
