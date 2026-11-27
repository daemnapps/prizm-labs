#!/usr/bin/env python3
"""act.py — carry out a recorded call in Meta, only on owner's go in that same conversation.

    python3 act.py brand_b F2            # shows exactly what would change, changes nothing
    python3 act.py brand_b F2 --go       # does it: pause the ad, or move the campaign budget by the desk's step

Reads the call from decisions.jsonl (decide.py writes it first — no call, no action). Only three moves:
pause an ad (call off), and a campaign's daily budget up or down by the step in desk.json. Everything
else (double down, keep, watch, hold) is not a Meta change. Each action is written back beside the call.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "meta-upload"))
import analyze as A


def plan(brand, flag):
    p = A.desk_dir(brand) / "decisions.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
    call = next((r for r in reversed(rows) if r["flag"].lower() == flag.lower()), None)
    if not call:
        raise SystemExit(f"no call recorded for {flag} — record it with decide.py first")
    desk = A.load_desk(brand)
    if call["call"] == "off" and call["kind"] == "ad":
        return call, {"what": f"pause ad {call['name']}", "id": call["id"], "post": {"status": "PAUSED"}}
    if call["call"] in ("budget_up", "budget_down") and call["kind"] == "campaign":
        return call, {"what": f"campaign budget {'up' if call['call'] == 'budget_up' else 'down'} {desk['lines']['budget_step_pct']}%",
                      "id": call["id"], "step": desk["lines"]["budget_step_pct"] * (1 if call["call"] == "budget_up" else -1)}
    return call, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("brand"); ap.add_argument("flag"); ap.add_argument("--go", action="store_true")
    a = ap.parse_args(argv)
    call, move = plan(a.brand, a.flag)
    if not move:
        print(f"{a.flag}: '{call['call']}' is not a Meta change — nothing to do"); return
    if not a.go:
        print(json.dumps({"would": move["what"], "flag": a.flag}, indent=1)); return
    import meta
    m = meta.Meta(a.brand)
    if "post" in move:
        res = m.post(move["id"], **move["post"])
    else:
        cur = int(m.get(move["id"], fields="daily_budget").get("daily_budget") or 0)
        if not cur:
            raise SystemExit("this campaign has no daily budget on the campaign (ad-set budgets?) — change it by hand")
        new = int(round(cur * (1 + move["step"] / 100)))
        res = m.post(move["id"], daily_budget=new)
        move["what"] += f" (${cur / 100:,.2f} → ${new / 100:,.2f} a day)"
    done = {"at": __import__("datetime").datetime.now().isoformat(timespec="seconds"), "flag": a.flag, "id": move["id"],
            "did": move["what"], "meta": res}
    with open(A.desk_dir(a.brand) / "actions.jsonl", "a") as fh:
        fh.write(json.dumps(done) + "\n")
    print(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
