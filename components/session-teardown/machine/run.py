#!/usr/bin/env python3
"""session-teardown — find the leak, pull the recordings, read the page, tear them down, write the hypothesis.

    python3 machine/run.py --brand <brand> --sample basic --dry-run       every prompt filled, no model call
    python3 machine/run.py --brand <brand> --sample basic                 the full run on recorded sample data
    python3 machine/run.py --brand <brand>                                live: PostHog (needs the read key)
    python3 machine/run.py --brand <brand> --page-id <ID>                 a chosen page instead of the top leak
    python3 machine/run.py --brand <brand> --label <L> --rerun-from teardown   rerun from a step, the rest kept
    python3 machine/run.py pick <run folder> <N>                          the owner's pick: swing N is the hypothesis

Runs on the shared chain pieces (machine/shared.py names each one): run-kit's Chain runs every model step (tier,
depends, dry run, reuse, prompt as sent, run.json), marketing-chain-checks' gates hold failing work, page-teardown's
own structure prompt reads the page under test into sections, and every recording is read in video-teardown's
frame-map shape (shots and moments, timeline.py).

Writes only runs/session-teardown/<brand>/<label>/: leak.json, picked.json, timelines/, moments/, the page
structure, every prompt as sent (<step>--sent.md) and output (<step>--<label>.md), teardown.json (every finding,
priced), fixes.json (the team's fix list), swings/swing-N/hypothesis.json (up to three big swings, the most money
first), hypothesis.json (swing 1 until the owner picks; the contract, see record.py), deliverable/, check.json,
run.json, page.html. The hypothesis goes to the page system's page brief (`briefs.py page --hypothesis <file>`) and
the fix list to its page-change intake; nothing here builds a page or starts a test.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import shared                         # noqa: E402  (puts run-kit and marketing-chain-checks on the path)
from run_kit import claude_flags, filing, prompts   # noqa: E402
from run_kit import model as M        # noqa: E402
from run_kit.stage import Chain, DRY  # noqa: E402
import marketing_chain_checks as Q    # noqa: E402
import friction                       # noqa: E402
import leak as leak_mod               # noqa: E402
import money                          # noqa: E402
import pages as pages_mod             # noqa: E402
import page as page_mod               # noqa: E402
import record                         # noqa: E402
import sections as S                  # noqa: E402
import source as source_mod           # noqa: E402
import timeline                       # noqa: E402

TOOL = "session-teardown"
# The chain, declared once. `code` steps run here with no model; the rest run through run-kit's Chain, whose
# `depends` says what reruns when an earlier step does. `prompts` names a step whose prompt lives in another
# component (read there, never copied).
STEPS = [
    {"key": "leak", "name": "Find the leak", "code": True},
    {"key": "pull", "name": "Pull recordings", "code": True},
    {"key": "structure", "name": "Read the page (page-teardown)", "tier": "designs", "label": "structure",
     "prompts": shared.PAGE_TEARDOWN_PROMPTS},
    {"key": "teardown", "name": "Tear down the recordings", "tier": "designs", "label": "patterns",
     "depends": ["structure"]},
    {"key": "hypothesis", "name": "Write the hypothesis", "tier": "designs", "label": "hypothesis",
     "depends": ["teardown"]},
]
MIN_LEFT = 5


class RunError(Exception):
    pass


def definitions():
    return json.loads((ROOT / "definitions" / "stop.json").read_text())


def tiers():
    """This chain's three tiers, from the one model table (run-kit tiers.json, entry "session-teardown"), pinned
    2026-11-26 to what it ran before: Haiku 5.5, Sonnet 5.5, and designs on the registry's chain model (claude_flags,
    LD-100 (chain model explicit)). Every step of this chain is a designs step today."""
    from run_kit import tiers as T
    return T.for_chain("session-teardown")


def parse_json(text):
    try:
        return shared.chain_io().pull_json(text or "")
    except ValueError:
        m = re.search(r"\{.*\}", text or "", re.S)
        if not m:
            raise RunError("the model's reply had no JSON in it")
        return json.loads(m.group(0))


def run_step(chain, key, **fields):
    """chain.run for one step, its prompt read from the folder the step names (default: this component's)."""
    home = chain.steps[key].get("prompts")
    if not home:
        return chain.run(key, **fields)
    own, chain.prompts_dir = chain.prompts_dir, Path(home)
    try:
        return chain.run(key, **fields)
    finally:
        chain.prompts_dir = own


def pick(page_leak, recs, n_left, n_conv, min_active):
    def usable(s):
        r = recs.get(s)
        return r is not None and (r.get("active_s") or 0) >= min_active
    newest = lambda ss: sorted(ss, key=lambda s: recs.get(s, {}).get("start", ""), reverse=True)  # noqa: E731
    left = [s for s in newest(page_leak["left_sessions"]) if usable(s)][:n_left]
    conv = [s for s in newest(page_leak["converted_sessions"]) if usable(s)][:n_conv]
    return {"left": left, "converted": conv}


def _rel(d):
    return str(d.relative_to(shared.WS)) if str(d).startswith(str(shared.WS)) else str(d)


def read_page(chain, out, page, src, brand, runs_root, today, use_page_list=True):
    """The page under test as sections, and what it was built to do. First hit wins: the page-chain run that BUILT
    the control (its page.json and brief), a page-chain teardown of the control, else page-teardown's structure
    prompt run here as the `structure` step. -> (structure | None, where it came from, plan | None)."""
    built, plan, d = S.from_context(shared.page_context(page["page_id"]) if use_page_list else None, shared.WS)
    if not built:
        built, plan, d = S.from_build(page["page_id"], page["control"]["version"], brand, runs_root)
    if built:
        (out / "structure.json").write_text(json.dumps(built, indent=1, ensure_ascii=False))
        plan["run"] = _rel(d)
        chain.record.stage("structure", status="reused", why="the page's own build record", source=_rel(d) + "/page.json")
        chain.echo("  == structure  (the page's build record: %s)" % _rel(d))
        return built, "the page's build record (%s)" % _rel(d), plan
    found, d = S.from_page_chain(page["control"]["url"], brand, runs_root)
    if found:
        (out / "structure.json").write_text(json.dumps(found, indent=1, ensure_ascii=False))
        rel = _rel(d)
        chain.record.stage("structure", status="reused", why="page-teardown run on file", source=rel + "/structure.json")
        chain.echo("  == structure  (page-teardown's run on file: %s)" % rel)
        return found, rel, None
    text = src.page_text(page["page_id"]) if hasattr(src, "page_text") else None
    if text is None and not chain.dry:
        try:
            shared.capture()(page["control"]["url"], out / "source")
            text = (out / "source" / "page.txt").read_text()
        except Exception as e:                       # noqa: BLE001 — the run goes on with scroll % only
            chain.skip("structure", "the page could not be captured (%s); depth stays in scroll %%" % type(e).__name__)
            return None, None, None
    if text is None:
        chain.skip("structure", "no page text on file and a dry run captures nothing; depth stays in scroll %")
        return None, None, None
    (out / "source").mkdir(exist_ok=True)
    (out / "source" / "page.txt").write_text(text)
    reply = run_step(chain, "structure", source=text, source_url=page["control"]["url"], today=today)
    if reply == DRY:
        return None, "dry run", None
    structure = parse_json(reply)
    (out / "structure.json").write_text(json.dumps(structure, indent=1, ensure_ascii=False))
    return structure, "this run (page-teardown's structure prompt)", None


def run(brand, src, label=None, page_id=None, days=None, dry_run=False, ask=None, model=None, out=None, now=None,
        rerun_from=None, runs_root=None, echo=print):
    """`ask(prompt, model) -> text` and `model` are the test seam (run-kit's runner and forced model)."""
    d = definitions()
    cfg = d["pick"]
    days = days or cfg["days"]
    now = now or dt.datetime.now(dt.timezone.utc)
    page_list = getattr(src, "page_list", lambda: None)() or pages_mod.load()
    stamp = now.strftime("%Y%m%d-%H%M")

    # 1 find the leak (code)
    found = leak_mod.find(src.page_views(brand, days), src.outcomes(brand, days), cfg["min_visitors"])
    ranked = [p for p in found["pages"] if p["ranked"]]
    if page_id:
        chosen = next((p for p in found["pages"] if p["page_id"] == page_id), None)
        if chosen is None:
            raise RunError("no visits to %s in the last %d days" % (page_id, days))
    else:
        open_pages = [p for p in ranked if p["page_id"] in page_list.get("pages", {})
                      and not pages_mod.page(p["page_id"], page_list)["running_test"]]
        if not open_pages:
            raise RunError("no page has enough visits to read (floor %d) and no test running" % cfg["min_visitors"])
        chosen = open_pages[0]
    page = pages_mod.page(chosen["page_id"], page_list)
    label = label or "%s_hyp-%s" % (chosen["page_id"].split("_", 1)[1].replace("_", "-"), stamp)
    out = Path(out) if out else filing.run_dir(TOOL, brand, label)
    runner = (lambda p, m: (0, ask(p, m), "")) if ask else None
    chain = Chain(TOOL, brand, label, out, ROOT / "prompts", [s for s in STEPS if not s.get("code")],
                  assignment={"brand": brand, "source": src.__class__.__name__, "page_id": page_id, "days": days},
                  dry=dry_run, rerun_from=rerun_from, force_model=model, tiers=tiers(), runner=runner, echo=echo)
    st = chain.record.state
    leaks = [{k: v for k, v in p.items() if not k.endswith("_sessions")} for p in found["pages"]]
    st.update(at=now.isoformat(timespec="seconds"), source=src.__class__.__name__, steps=STEPS_SHOWN, page_id=chosen["page_id"],
              state="started")
    (out / "leak.json").write_text(json.dumps({"value_per_reacher": found["value_per_reacher"], "chosen": chosen["page_id"],
                                               "pages": leaks}, indent=1))
    chain.record.stage("leak", status="done", out="leak.json", chosen=chosen["page_id"], pages=len(leaks))

    # 2 pull recordings (code) — the inputs gate holds a run with too little to read
    recs = src.recordings(chosen["left_sessions"] + chosen["converted_sessions"])
    picked = pick(chosen, recs, cfg["left"], cfg["converted"], cfg["min_active_seconds"])
    st.update(n_left=len(picked["left"]), n_converted=len(picked["converted"]))
    try:
        Q.hold("inputs", ["only %d recordings of visitors who left %s; need %d or more"
                          % (len(picked["left"]), chosen["page_id"], MIN_LEFT)] if len(picked["left"]) < MIN_LEFT else [], out)
    except Q.Held as e:
        _finish(out, chain, "held at the inputs gate: " + "; ".join(e.problems), leaks)
        raise
    events = src.session_events(picked["left"] + picked["converted"])
    (out / "picked.json").write_text(json.dumps({"picked": picked, "recordings": {s: recs[s] for s in picked["left"] + picked["converted"]}}, indent=1))
    chain.record.stage("pull", status="done", out="picked.json", left=len(picked["left"]), converted=len(picked["converted"]))

    # 3a read the page under test into sections (page-teardown)
    structure, structure_from, plan = read_page(chain, out, page, src, brand, runs_root or shared.PAGE_CHAIN_RUNS,
                                                now.date().isoformat(), use_page_list=runs_root is None)
    pmap = S.page_map(structure)
    st.update(structure_from=structure_from, page_map=pmap, plan=plan)

    # 3b every recording read as shots and moments (video-teardown's frame-map shape)
    tdir, mdir = out / "timelines", out / "moments"
    tdir.mkdir(exist_ok=True)
    mdir.mkdir(exist_ok=True)
    texts, furthest, mm = {}, {}, {"page_id": page["page_id"], "page_map": pmap, "recordings": []}
    for group in ("left", "converted"):
        parts, furthest[group] = [], []
        for s in picked[group]:
            tl = timeline.build(s, events.get(s, []), recs.get(s), page_path=page["control"]["path"], page_map=pmap)
            (tdir / ("%s.txt" % re.sub(r"[^A-Za-z0-9_-]", "-", s))).write_text("\n".join(tl["lines"]) + "\n")
            parts.append(timeline.as_text(tl, group.upper()))
            furthest[group].append(tl["furthest"])
            mm["recordings"].append(dict({k: tl[k] for k in ("session", "ended", "seconds", "shots", "furthest", "depth")},
                                         group=group))
        texts[group] = "\n".join(parts)
    (mdir / "moments.json").write_text(json.dumps(mm, indent=1))
    (mdir / "MOMENT-MAP.md").write_text(timeline.markdown(mm))
    n = {"left": len(picked["left"]), "converted": len(picked["converted"])}
    reach = S.reach_counts(pmap, furthest)
    rub = friction.count(events, picked)
    st.update(reach=reach, friction=rub)

    # 3c tear down
    base = {"page_id": page["page_id"], "step": page["step"], "kind": page["kind"], "product": page["product"],
            "url": page["url"], "n_left": n["left"], "n_converted": n["converted"], "page_map": S.as_text(pmap),
            "plan": S.plan_text(plan)}
    td_text = run_step(chain, "teardown", reach=S.reach_text(pmap, reach, n), friction=friction.as_text(rub, n),
                       left_timelines=texts["left"], converted_timelines=texts["converted"], **base)
    lost = chosen["visitors"] - chosen["reached_next"]
    findings = []
    if td_text != DRY:
        td = parse_json(td_text)
        for f in td.get("findings") or td.get("patterns") or []:
            if not isinstance(f, dict) or not (f.get("finding") or f.get("pattern")):
                continue
            f = dict(f, finding=f.get("finding") or f.get("pattern"))
            f.update(money.price(f.get("left"), f.get("converted"), n["left"], n["converted"], lost,
                                 found["value_per_reacher"], days))
            findings.append(f)
        (out / "teardown.json").write_text(json.dumps(dict(td, findings=findings), indent=1))
    patterns = [{"pattern": f["finding"], "left": int(f.get("left") or 0), "converted": int(f.get("converted") or 0)}
                for f in findings]
    st.update(findings=findings, patterns=patterns)
    window = "%s..%s" % ((now - dt.timedelta(days=days)).date().isoformat(), now.date().isoformat())
    by = {"tool": "components/" + TOOL, "at": st["at"]}

    # the team's half: every fix, the most money first
    known = set(picked["left"] + picked["converted"])
    jobs = {str(sec["n"]): sec["job"] for sec in pmap or []}

    def job_of(section):              # "§4", "§4 items" or "§3–§4": the first section named
        m = re.search(r"§\s*(\d+)", section or "")
        return jobs.get(m.group(1), "") if m else ""
    tstep = chain.record.state["stages"].get("teardown") or {}
    fixes = sorted([f for f in findings if f.get("kind") == "fix"], key=lambda f: -f["at_stake_month"])
    fix_list = record.build_fixes(
        fix_list_id(out, page["page_id"], now), page,
        record.evidence(chosen, picked, [p for p, f in zip(patterns, findings) if f.get("kind") == "fix"] or patterns,
                        [], window),
        [{"what": f.get("fix", ""), "section": f.get("section") or "", "section_job": job_of(f.get("section")),
          "selector": f.get("element") or "", "pattern": f["finding"], "left": f.get("left"),
          "converted": f.get("converted"),
          "clips": record.clips_of([m for m in f.get("moments") or [] if m.get("recording_id") in known]),
          "value_usd_month": f["at_stake_month"], "basis": f["basis"], "type": f.get("type") or "",
          "effort": f.get("effort") or ""} for f in fixes],
        dict(by, prompt=Path(tstep.get("prompt_name") or "teardown").stem, model=tstep.get("model") or model))
    fix_state = ("queued: a test is running on this page; page-change takes the list once it ends"
                 if page["running_test"] else "ready for page-change")

    # 4 the hypothesis
    def line(i, f):
        return "%d. [%s] %s — %d of %d who left, %d of %d who reached checkout · $%s a month at stake. Moments: %s" % (
            i, f.get("kind") or "?", f["finding"], int(f.get("left") or 0), n["left"], int(f.get("converted") or 0),
            n["converted"], format(int(f["at_stake_month"]), ","),
            "; ".join("%s at %ss (%s)" % (m.get("recording_id"), m.get("at_s"), m.get("note", "")) for m in f.get("moments", [])))
    numbered = list(enumerate(findings, 1))
    hyp_text = run_step(chain, "hypothesis", control_version=page["control"]["version"],
                        control_offer=page["control"]["offer"], days=days, visitors=chosen["visitors"],
                        reached_next=chosen["reached_next"], reach_rate="%.0f%%" % (100 * chosen["reach_rate"]),
                        revenue_per_visitor="$%.2f" % chosen["revenue_per_visitor"],
                        swings="\n".join(line(i, f) for i, f in numbered if f.get("kind") != "fix")
                        or "(dry run: the teardown's big-swing findings go here)",
                        patterns="\n".join(line(i, f) for i, f in numbered)
                        or "(dry run: the teardown's findings go here)", **base)
    if dry_run:
        _finish(out, chain, "dry run: every prompt filled, no model call", leaks)
        return out

    # the owner's half: up to three big swings, each a full hypothesis record, the most money first
    reply = parse_json(hyp_text)
    swings = reply.get("swings") if isinstance(reply.get("swings"), list) else [reply]
    hstep = chain.record.state["stages"].get("hypothesis") or {}
    hby = dict(by, prompt=Path(hstep.get("prompt_name") or prompts.latest(ROOT / "prompts", "hypothesis").name).stem,
               model=hstep.get("model") or model or claude_flags.model())
    priced = []
    for w in [x for x in swings if isinstance(x, dict) and x.get("hypothesis")][:3]:
        w["clips"] = [c for c in (w.get("clips") or []) if c.get("recording_id") in known]
        backing = [(findings[i - 1]["at_stake_month"], i) for i in (w.get("from") or [])
                   if isinstance(i, int) and 0 < i <= len(findings)]
        worth, top = max(backing) if backing else (0.0, None)
        basis = ("finding %d: %s" % (top, findings[top - 1]["basis"])) if top else \
            "no finding named as its evidence: $0 until one is"
        priced.append((worth, basis, w))
    priced.sort(key=lambda r: -r[0])
    recs_out = []
    for i, (worth, basis, w) in enumerate(priced, 1):
        links = {(c["recording_id"], int(c.get("at_s") or 0)): src.replay_link(c["recording_id"], c.get("at_s"))
                 for c in w["clips"]}
        recs_out.append((worth, record.build("%s-s%d" % (label, i), page, chosen, picked, patterns, w, d["stop"], hby,
                                             links=links, window=window, rank=i, value_usd_month=worth, basis=basis)))
    sdir = out / "swings"
    shown = []
    for i, (worth, rec) in enumerate(recs_out, 1):
        (sdir / ("swing-%d" % i)).mkdir(parents=True, exist_ok=True)
        (sdir / ("swing-%d" % i) / "hypothesis.json").write_text(json.dumps(rec, indent=1))
        shown.append({"n": i, "at_stake_month": worth, "file": "swings/swing-%d/hypothesis.json" % i,
                      "type": rec["type"], "hypothesis": rec["hypothesis"], "change": rec["change"]})
    st.update(swings=shown, fixes=fix_list["fixes"], fix_state=fix_state)
    (out / "fixes.json").write_text(json.dumps(fix_list, indent=1))

    # the delivery gate: both contracts, and no hole the writer left
    bad = record.check_fixes(fix_list)
    for _, rec in recs_out:
        bad += ["%s: %s" % (rec["id"], b) for b in record.check(rec)]
        bad += Q.unfilled_check(rec.get("hypothesis", "") + " " + rec.get("change", ""))
    bad += Q.unfilled_check(" ".join(f["what"] for f in fix_list["fixes"]))
    if recs_out:
        (out / "hypothesis.json").write_text(json.dumps(recs_out[0][1], indent=1))   # swing 1 until the owner picks
        st["hypothesis"] = recs_out[0][1]
        st["picked"] = None
    try:
        Q.hold("delivery", bad, out)
    except Q.Held:
        _finish(out, chain, "refused: " + "; ".join(bad), leaks)
        raise
    chain.deliver(*[out / f for f in ("hypothesis.json", "fixes.json") if (out / f).is_file()])
    _finish(out, chain, "%d big swing(s) and %d fix(es) written" % (len(recs_out), len(fix_list["fixes"])), leaks)
    return out


def fix_list_id(out, page_id, now):
    """<page_id>_fix-<YYYYMMDD>-<n>: n counts this page's fix lists already written that day (in any run)."""
    prefix = "%s_fix-%s-" % (page_id, now.strftime("%Y%m%d"))
    taken = 0
    for f in Path(out).parent.glob("*/fixes.json"):
        if f.parent == Path(out):
            continue
        try:
            if str(json.loads(f.read_text()).get("id", "")).startswith(prefix):
                taken += 1
        except ValueError:
            pass
    return prefix + str(taken + 1)


def pick_swing(run_dir, n):
    """The owner's pick: swing N becomes the run's hypothesis.json (and its deliverable), which the page system's
    page brief takes."""
    run_dir = Path(run_dir)
    src = run_dir / "swings" / ("swing-%d" % n) / "hypothesis.json"
    if not src.is_file():
        raise RunError("this run has no swing %d" % n)
    rec = json.loads(src.read_text())
    bad = record.check(rec)
    if bad:
        raise RunError("swing %d breaks the contract: %s" % (n, "; ".join(bad)))
    for f in (run_dir / "hypothesis.json", run_dir / "deliverable" / "hypothesis.json"):
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(rec, indent=1))
    rj = run_dir / "run.json"
    st = json.loads(rj.read_text())
    st.update(hypothesis=rec, picked=n, state="swing %d picked" % n)
    rj.write_text(json.dumps(st, indent=2, ensure_ascii=False) + "\n")
    page_mod.render(run_dir, st, STEPS, json.loads((run_dir / "leak.json").read_text())["pages"])
    return run_dir / "hypothesis.json"


STEPS_SHOWN = [s["key"] for s in STEPS]


def _finish(out, chain, state, leaks):
    chain.record.state["state"] = state
    chain.record.save()
    page_mod.render(out, chain.record.state, STEPS, leaks)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["pick"]:
        if len(argv) != 3 or not argv[2].isdigit():
            print("usage: run.py pick <run folder> <swing number>", file=sys.stderr)
            return 2
        try:
            print(pick_swing(argv[1], int(argv[2])))
        except RunError as e:
            print("stopped: %s" % e, file=sys.stderr)
            return 1
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--sample", help="a recorded sample under samples/ (or a folder) instead of live PostHog")
    ap.add_argument("--page-id")
    ap.add_argument("--label")
    ap.add_argument("--days", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rerun-from", choices=[s["key"] for s in STEPS if not s.get("code")])
    a = ap.parse_args(argv)
    if a.sample:
        folder = Path(a.sample) if Path(a.sample).is_dir() else ROOT / "samples" / a.sample
        src = source_mod.Sample(folder)
    else:
        src = source_mod.PostHog()
    try:
        out = run(a.brand, src, label=a.label, page_id=a.page_id, days=a.days, dry_run=a.dry_run,
                  rerun_from=a.rerun_from)
    except (RunError, KeyError, ValueError, prompts.PromptError, Q.Held, M.UsageLimit, M.StageFailed) as e:
        print("stopped: %s" % e, file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
