#!/usr/bin/env python3
"""learn.py — the edit's declared last step, run by the machine (the logic layer, 2026-11-18).

    python3 machine/learn.py <edit run folder> [--dry-run]     # learn from this run's changes since its last lesson
    python3 machine/learn.py --rebuild [--runs-root <dir>]     # write the hand-over file again from the bank (no model)

`steps.json` has always declared `learn` ("every change made at a stop, with the why, becomes a rule the next cut
reads") and `prompts/stage-9-learn/` holds its prompt, but no road of the edit ran it: only the timeline page did, on
its own Render button. A change made any other way (`run.py change`, the Brief Editing Board, a hand-off) taught
nothing, the rules file was otherwise kept by hand, and nothing the cut learned reached production or writing.

Now `run.py start` and `line.py` run it as their last step.

Reads   <run>/changes.jsonl (every stop: timeline, captions, board) and <run>/feedback.jsonl, both only past this
        run's own mark (<run>/.learned-upto, the mark the timeline page already keeps, so nothing is learned twice);
        the rules on file.
Asks    the highest `stage9-learn` prompt, on the `checks` tier (run-kit model). No new change = no call at all.
Writes  runs/video-edit/_lessons/lessons.jsonl   the bank: every lesson, with the stage of the line it teaches
        runs/video-edit/_lessons/learned.json    THE HAND-OVER, written by machine: the same lessons by stage (edit,
                                                 captions, production-picture, production-clip, voice, brief,
                                                 teardown), rules and observations apart, for every stage to bind.
                                                 Rebuilt whole from the bank each time.
Nothing is written inside the component: `components/video-edit/learned.json` stays the rules kept by hand, and the
cut reads both (`for_cut()`: the hand-kept rules, then the machine's edit and caption rules).

What is written here carries the rule, the scope and how often it was seen: direction only. The words a person typed
stay in the run's own change log, where they were typed.

A lesson step that cannot run (no login, a reply that will not parse) is said on the run's record and never fails or
stops the edit: `safe()` returns what happened as a row.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
STAGES = ("edit", "captions", "production-picture", "production-clip", "voice", "brief", "teardown")
CUT_STAGES = ("edit", "captions")              # what the cut itself obeys (learned.json)
SEEN_FOR_RULE = 2
STATED = re.compile(r"\b(always|never|from now on|every time|every edit|each time)\b", re.I)


def repo_root() -> Path:
    for p in [TOOL, *TOOL.parents]:
        if (p / "runs" / "README.md").exists() or (p / ".git").exists():
            return p
    return TOOL.parents[1]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _jl(p: Path) -> list:
    rows = []
    if Path(p).is_file():
        for line in Path(p).read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                rows.append(r)
    return rows


def _read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def lessons_dir(runs_root: Path | None = None) -> Path:
    return (Path(runs_root) if runs_root else repo_root() / "runs" / "video-edit") / "_lessons"


def runs_root_of(run: Path) -> Path:
    """<runs root>/<brand>/<label> -> the runs root this run lives in (a test's own root included)."""
    return Path(run).resolve().parent.parent


def _ts(s):
    """A written time as a moment (UTC when it names no zone), or None when it will not read."""
    try:
        d = dt.datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def after(at, upto) -> bool:
    """Was this row written after the mark? By the moment itself, so two tools that write the time differently (UTC,
    a local offset) are still read in order; by the text only when one of them will not read as a time."""
    if not upto:
        return True
    a, u = _ts(at), _ts(upto)
    return a > u if (a and u) else str(at or "") > str(upto)


def pending(run: Path) -> tuple:
    """(change rows, feedback rows, the mark) this run has not been learned from yet."""
    run = Path(run)
    mark = run / ".learned-upto"
    upto = mark.read_text().strip() if mark.is_file() else ""
    changes = [r for r in _jl(run / "changes.jsonl") if after(r.get("at"), upto)]
    fbs = [{"at": r.get("at"), "asked": r.get("asked"), "scope": r.get("scope"),
            "answer": (r.get("answer") or {}).get("summary") if isinstance(r.get("answer"), dict) else r.get("answer")}
           for r in _jl(run / "feedback.jsonl") if after(r.get("at"), upto)]
    return changes, fbs, upto


def mark_for(rows: list, at: str) -> str:
    """How far a run has been learned: this moment, or its latest row's own time when a clock that wrote it runs
    ahead of this one, so a row just read is never read again."""
    seen = [x for x in (_ts(r.get("at")) for r in rows) if x]
    last = max(seen + [_ts(at)]) if seen else _ts(at)
    return last.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def ad_of(run: Path) -> dict:
    run = Path(run)
    st = _read(run / "run.json", {}) or {}
    sheets = sorted(run.glob("cutsheet-v*.json"), key=lambda p: int(re.search(r"-v(\d+)", p.name).group(1)))
    meta = ((_read(sheets[-1], {}) or {}).get("meta") or {}) if sheets else {}
    return {"edit": run.name, "brief": st.get("brief"), "brand": st.get("brand") or run.parent.name,
            "format": meta.get("format") or st.get("format")}


def prompt_file() -> Path:
    sys.path.insert(0, str(repo_root() / "components" / "run-kit"))
    from run_kit import prompts as P
    return Path(P.latest(TOOL / "prompts" / "stage-9-learn", "stage9-learn"))


def ask(sent: str, runner=None) -> tuple:
    """(the reply, the model). `runner` is the seam a test fakes: runner(prompt, model) -> (code, stdout, stderr)."""
    sys.path.insert(0, str(repo_root() / "components" / "run-kit"))
    from run_kit import model as M
    mdl, _why = M.pick("checks", len(sent))
    return M.call(sent, mdl, label="edit learn", tries=2, timeout=900, runner=runner), mdl


def _parse(reply: str) -> dict:
    out = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
    if not isinstance(out, dict) or not isinstance(out.get("rows"), list):
        raise ValueError("the reply has no rows")
    return out


def standing(row: dict, promote: set, seen_before: int) -> str:
    """rule | observation. A rule when the prompt promoted it, or it has now been seen twice, or it was stated as one."""
    seen = max(int(row.get("seen") or 1), seen_before + 1)
    if row.get("id") in promote or seen >= SEEN_FOR_RULE or STATED.search(str(row.get("his_words") or "")):
        return "rule"
    return "observation"


def bank_row(row: dict, ad: dict, at: str, model: str, prompt: str, stand: str, seen: int) -> dict:
    """What the bank keeps of one lesson: direction only (the typed words stay in the run's change log)."""
    stage = row.get("stage") if row.get("stage") in STAGES else "edit"
    return {"at": at, "id": row.get("id"), "stage": stage, "rule": row.get("rule"), "what_changed": row.get("what_changed"),
            "scope": row.get("scope") or "this ad only", "seen": seen, "standing": stand,
            "stated": bool(STATED.search(str(row.get("his_words") or ""))),
            "conflicts_with": row.get("conflicts_with") or "", "edit": ad.get("edit"), "brief": ad.get("brief"),
            "brand": ad.get("brand"), "format": ad.get("format"), "model": model, "prompt": prompt}


def rebuild(runs_root: Path | None = None) -> dict:
    """THE HAND-OVER FILE from the bank, whole, no model: every lesson by the stage it teaches, rules and observations
    apart, the newest wording of each kept. -> the document written to <lessons>/learned.json."""
    d = lessons_dir(runs_root)
    rows = [r for r in _jl(d / "lessons.jsonl") if r.get("id") and r.get("rule")]
    by = {}
    for r in rows:
        stage = r.get("stage") if r.get("stage") in STAGES else "edit"
        k = (stage, r["id"])
        e = by.setdefault(k, {"id": r["id"], "rule": r["rule"], "scope": r.get("scope"), "seen": 0, "standing": "observation",
                              "first": r.get("at"), "last": r.get("at"), "formats": [], "edits": []})
        e["seen"] += 1
        e["rule"], e["scope"], e["last"] = r["rule"], r.get("scope") or e["scope"], r.get("at") or e["last"]
        if r.get("standing") == "rule" or r.get("stated") or e["seen"] >= SEEN_FOR_RULE:
            e["standing"] = "rule"
        for key, val in (("formats", r.get("format")), ("edits", r.get("edit"))):
            if val and val not in e[key]:
                e[key].append(val)
        if r.get("conflicts_with"):
            e["conflicts_with"] = r["conflicts_with"]
    stages = {s: {"rules": [], "observations": []} for s in STAGES}
    for (stage, _id), e in sorted(by.items(), key=lambda kv: (kv[0][0], str(kv[1]["first"]))):
        stages[stage]["rules" if e["standing"] == "rule" else "observations"].append(
            {k: v for k, v in e.items() if k != "standing"})
    doc = {"_what": ("What the edit has learned, by the stage of the video line it teaches. Written by machine "
                     "(components/video-edit/machine/learn.py) from the lessons bank beside it; never edited by hand. "
                     "A rule was stated as one or has been seen twice; an observation was seen once and binds nothing. "
                     "Each stage upstream binds its own block; the cut's own rules are also in "
                     "components/video-edit/learned.json."),
           "status": "draft", "built": now(), "from": "lessons.jsonl", "lessons": len(rows), "stages": stages}
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / ".learned.json.tmp"
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, d / "learned.json")
    return doc


def block(stage: str, runs_root: Path | None = None) -> str:
    """The rules one stage binds, as labelled text for a prompt ("NONE" when the edit has taught it nothing yet).
    A reader for the stages upstream: nothing in this component calls it."""
    doc = _read(lessons_dir(runs_root) / "learned.json", {}) or {}
    rules = ((doc.get("stages") or {}).get(stage) or {}).get("rules") or []
    if not rules:
        return "NONE"
    return "\n".join(f"- {r['rule']} (scope: {r.get('scope') or 'this ad only'}; seen {r.get('seen')})" for r in rules)


def kept_by_hand() -> dict:
    """components/video-edit/learned.json: the rules and observations kept by hand (definitions; never written here)."""
    return _read(TOOL / "learned.json", {}) or {}


def for_cut(runs_root: Path | None = None) -> list:
    """The rules the cut obeys: the ones kept by hand, then the machine's own edit and caption rules (the hand-over
    file), each once by id. What `{learned}` carries into the cut prompt."""
    rules = [r for r in kept_by_hand().get("rules") or [] if isinstance(r, dict)]
    have = {r.get("id") for r in rules}
    doc = _read(lessons_dir(runs_root) / "learned.json", {}) or {}
    for stage in CUT_STAGES:
        for r in ((doc.get("stages") or {}).get(stage) or {}).get("rules") or []:
            if r.get("id") not in have:
                have.add(r.get("id"))
                rules.append({"id": r.get("id"), "rule": r.get("rule"), "scope": r.get("scope"), "seen": r.get("seen"),
                              "at": str(r.get("last") or "")[:10], "from": "the edit's learn step"})
    return rules


def on_file(runs_root: Path | None = None) -> dict:
    """Everything already learned about the cut, for the learn prompt's `{learned}`: rules and observations, by hand
    and by machine, so `seen` is counted against all of it."""
    hand = kept_by_hand()
    doc = _read(lessons_dir(runs_root) / "learned.json", {}) or {}
    obs = [o for o in hand.get("observations") or [] if isinstance(o, dict)]
    have = {o.get("id") for o in obs}
    for stage in CUT_STAGES:
        for r in ((doc.get("stages") or {}).get(stage) or {}).get("observations") or []:
            if r.get("id") not in have:
                obs.append({"id": r.get("id"), "points_to": r.get("rule"), "scope": r.get("scope"), "seen": r.get("seen")})
    return {"rules": for_cut(runs_root), "observations": obs}


def learn(run: Path, runner=None, dry_run: bool = False) -> dict | None:
    """Learn from one edit run's changes since its last lesson. None when there is nothing new (no model is called).
    -> {"rows", "rules", "observations", "to_cut", "upstream", "model"}."""
    run = Path(run).resolve()
    changes, fbs, _upto = pending(run)
    if not changes and not fbs:
        return None
    root = runs_root_of(run)
    ad = ad_of(run)
    pf = prompt_file()
    sent = (pf.read_text().replace("{changes}", json.dumps(changes, ensure_ascii=False, indent=1)[:60000])
            .replace("{feedback}", json.dumps(fbs, ensure_ascii=False, indent=1)[:20000])
            .replace("{learned}", json.dumps(on_file(root), ensure_ascii=False, indent=1)[:40000])
            .replace("{ad}", json.dumps(ad, ensure_ascii=False)))
    if dry_run:
        return {"rows": 0, "rules": [], "observations": [], "to_cut": [], "upstream": [], "model": None,
                "would_read": {"changes": len(changes), "feedback": len(fbs), "prompt": pf.name}}
    reply, mdl = ask(sent, runner)
    out = _parse(reply)
    at = now()
    d = lessons_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    before = {}
    for r in _jl(d / "lessons.jsonl"):
        before[r.get("id")] = before.get(r.get("id"), 0) + 1
    by_hand = {x.get("id") for x in (kept_by_hand().get("rules") or []) + (kept_by_hand().get("observations") or [])}
    promote = set(out.get("promote") or [])
    kept = []
    with (d / "lessons.jsonl").open("a") as fh:
        for r in out["rows"]:
            if not isinstance(r, dict) or not r.get("id") or not r.get("rule"):
                continue
            seen_before = before.get(r["id"], 0) + (1 if r["id"] in by_hand else 0)   # a lesson already kept by hand counts
            stand = standing(r, promote, seen_before)
            row = bank_row(r, ad, at, mdl, pf.name, stand, seen_before + 1)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            kept.append(row)
    rebuild(root)
    (run / ".learned-upto").write_text(mark_for(changes + fbs, at))
    rules = [r["id"] for r in kept if r["standing"] == "rule"]
    return {"rows": len(kept), "rules": rules,
            "observations": [r["id"] for r in kept if r["standing"] == "observation"],
            "to_cut": [r["id"] for r in kept if r["standing"] == "rule" and r["stage"] in CUT_STAGES], "model": mdl,
            "upstream": sorted({r["stage"] for r in kept if r["stage"] not in CUT_STAGES})}


def safe(run: Path, runner=None, dry_run: bool = False) -> dict:
    """The step as a run's record keeps it: what was learned, or that there was nothing to learn, or why the step
    could not run. Never raises: the lesson step never fails or stops an edit."""
    try:
        got = learn(run, runner=runner, dry_run=dry_run)
    except BaseException as e:  # noqa: BLE001 — SystemExit and the model door's refusals included
        return {"state": "not run", "note": f"the lesson step could not run ({type(e).__name__}: {str(e)[:200]}); "
                                            "the changes stay unlearned and are read again next time"}
    if got is None:
        return {"state": "done", "lessons": 0, "note": "no change since the last lesson: nothing to learn"}
    if dry_run:
        return {"state": "dry run", **got["would_read"]}
    return {"state": "done", "lessons": got["rows"], "rules": got["rules"], "to_cut": got["to_cut"],
            "upstream": got.get("upstream") or [],
            "note": (f"{got['rows']} lesson(s) banked" + (f", {len(got['to_cut'])} now a rule the cut follows" if got["to_cut"] else "")
                     + (f"; for the stages upstream: {', '.join(got['upstream'])}" if got.get("upstream") else ""))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--runs-root", type=Path)
    a = ap.parse_args(argv)
    if a.rebuild:
        doc = rebuild(a.runs_root)
        print(f"hand-over written: {lessons_dir(a.runs_root) / 'learned.json'} · {doc['lessons']} lesson(s)")
        return 0
    if not a.run:
        ap.error("give an edit run folder, or --rebuild")
    res = safe(a.run.expanduser().resolve(), dry_run=a.dry_run)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
