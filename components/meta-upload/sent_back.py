#!/usr/bin/env python3
"""sent_back: the approval page's send-backs, counted, for the results feed.

    sent_back.py [--brand <brand>] [--repo REPO]     rebuild runs/meta-upload/<brand>/SENT-BACK.json

Each send-back on the approval page names its reasons, and each reason names the step that caused it (reasons.json,
learnings.py). This keeps one counted summary per brand in the repo, so a reader with no Drive (the winners feed)
can see which reasons come back and which step each one points at:

    runs/meta-upload/<brand>/SENT-BACK.json
        {"brand", "total", "since", "until",
         "reasons": [{"id", "label", "count", "steps": [{"step", "name", "tool"}], "last", "units": [ad names]}],
         "steps":   [{"step", "name", "count"}]}

Counts, reason labels, step names, tool names, dates and ad names only. The notes people type stay on the Drive, in
the digests learnings.py writes; nothing typed is copied here. The file is rewritten only when the counts change.
Changes no prompt and no switch: the prompt hooks in learnings-hooks.json stay as they are.
"""
import argparse, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
NAME = "SENT-BACK.json"
UNITS = 8                       # newest ad names kept per reason


def _learnings():
    mod = sys.modules.get("meta_learnings")
    if mod is None:
        spec = importlib.util.spec_from_file_location("meta_learnings", HERE / "learnings.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["meta_learnings"] = mod
        spec.loader.exec_module(mod)
    return mod


def build(brand, recs, steps=None):
    """The counted summary of one brand's send-backs. `recs` are learnings.jsonl lines, any order."""
    steps = steps or {}
    recs = sorted((r for r in recs or [] if isinstance(r, dict) and r.get("brand") == brand),
                  key=lambda r: str(r.get("at") or ""), reverse=True)
    reasons, by_step = {}, {}
    for r in recs:
        seen = set()
        for x in r.get("reasons") or []:
            rid = x.get("id")
            e = reasons.setdefault(rid, {"id": rid, "label": x.get("label"), "count": 0, "steps": [], "last": None,
                                         "units": []})
            if rid not in seen:                 # one send-back counts once per reason, however many steps it names
                seen.add(rid)
                e["count"] += 1
                e["last"] = e["last"] or str(r.get("at") or "")[:10] or None
                if r.get("unit") and r["unit"] not in e["units"] and len(e["units"]) < UNITS:
                    e["units"].append(r["unit"])
            st = {"step": x.get("step"), "name": steps.get(str(x.get("step")), "unsorted"), "tool": x.get("tool")}
            if st not in e["steps"]:
                e["steps"].append(st)
            by_step[x.get("step")] = by_step.get(x.get("step"), 0) + 1
    dates = [str(r.get("at") or "")[:10] for r in recs if r.get("at")]
    return {"brand": brand, "total": len(recs), "since": min(dates) if dates else None,
            "until": max(dates) if dates else None,
            "reasons": sorted(reasons.values(), key=lambda e: (-e["count"], str(e["id"]))),
            "steps": [{"step": s, "name": steps.get(str(s), "unsorted"), "count": n}
                      for s, n in sorted(by_step.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))]}


def path_for(brand, repo=None):
    return Path(repo or REPO) / "runs" / "meta-upload" / brand / NAME


def write(brand, repo=None, recs=None):
    """Rebuild one brand's summary. -> (path, changed). `recs` default: the send-back log, through learnings.read."""
    L = _learnings()
    recs = L.read(brand) if recs is None else recs
    doc = build(brand, recs, L.config().get("steps") or {})
    out = path_for(brand, repo)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if out.is_file() and out.read_text() == text:
        return out, False
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return out, True


def rebuild_quietly(brand, repo=None):
    """After a send-back is logged. Never raises: the send-back is recorded either way."""
    try:
        return write(brand, repo)[0]
    except Exception as e:                       # noqa: BLE001
        print(f"sent_back: summary not rebuilt ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr)
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", action="append", help="default: every brand with a send-back on the log")
    ap.add_argument("--repo", default=str(REPO))
    a = ap.parse_args(argv)
    L = _learnings()
    brands = a.brand or sorted({r.get("brand") for r in L.read() if r.get("brand")})
    if not brands:
        print("no send-backs on the log")
        return 0
    for b in brands:
        out, changed = write(b, a.repo)
        doc = json.loads(out.read_text())
        print(f"{b}: {doc['total']} send-backs, {len(doc['reasons'])} reasons -> {out.relative_to(a.repo)}"
              f"{'' if changed else ' (unchanged)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
