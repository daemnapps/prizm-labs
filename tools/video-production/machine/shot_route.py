"""shot_route — label every shot REAL, SWAP or AI with its reason and cost (SHOT-ROUTES.md, 2026-10-20).

the owner, 2026-10-20: one rule for which way a shot is made, so the piece is inventoried and costed
before anything runs and the edit knows what every clip is. The rule itself lives in
SHOT-ROUTES.md; this file applies it. Brand-agnostic: a shot is described by its facts only.

    python3 shot_route.py label <shots.json> [--out routes.json]

shots.json is a list of shots (or {"shots": [...]}), each with:
  id, seconds, what, owned_footage, motion_is_the_point, swipe_shot, clean_single_shot,
  talks_to_camera, needs_product, product_slot_in_swipe
"""
import argparse
import json
import sys
from pathlib import Path

CREDIT_USD = 0.0435
SWAP_CR_PER_S = 35 / 4.2          # measured 2026-10-20, Genjutsu 1080p
SEEDANCE_CR_PER_S = 7            # every AI clip is Seedance 2.5; MiniMax is out (the owner, 2026-09-22, restated 2026-10-20)
PICTURE_USD = 0.12
PICTURES_PER_AI_SHOT = 2
PICTURE_TRIES = 2
RETRY = 1.5
MIN_SWAP_S = 2.0


def route(shot):
    """The route for one shot, in the order SHOT-ROUTES.md rules: REAL, then SWAP, then AI."""
    secs = float(shot.get("seconds") or 0)
    if shot.get("owned_footage"):
        return "REAL", "we own real footage of this", 0.0
    if shot.get("talks_to_camera"):
        return "AI", "talks to camera with our voice: needs real lip-sync", ai_cost(secs)
    if shot.get("motion_is_the_point"):
        problems = []
        if not shot.get("swipe_shot"):
            problems.append("the swipe has no shot for it")
        if not shot.get("clean_single_shot"):
            problems.append("the swipe shot has a cut inside")
        if secs < MIN_SWAP_S:
            problems.append(f"under {MIN_SWAP_S:g} s")
        if shot.get("needs_product") and not shot.get("product_slot_in_swipe"):
            problems.append("the product must appear and nothing is in hand to replace")
        if not problems:
            return "SWAP", f"the motion is the point: swipe shot {shot['swipe_shot']}", swap_cost(secs)
        return "AI", "motion matters but no swap: " + "; ".join(problems), ai_cost(secs)
    return "AI", "a simple setup or a shot the swipe does not have", ai_cost(secs)


def swap_cost(secs):
    return round(max(secs, 4.0) * SWAP_CR_PER_S * CREDIT_USD * RETRY, 2)


def ai_cost(secs):
    pics = PICTURES_PER_AI_SHOT * PICTURE_TRIES * PICTURE_USD
    clip = max(secs, 4.0) * SEEDANCE_CR_PER_S * CREDIT_USD * RETRY
    return round(pics + clip, 2)


def label(shots):
    rows, totals = [], {"REAL": [0, 0.0, 0.0], "SWAP": [0, 0.0, 0.0], "AI": [0, 0.0, 0.0]}
    for s in shots:
        r, why, cost = route(s)
        rows.append({"id": s.get("id"), "what": s.get("what", ""), "seconds": s.get("seconds"),
                     "route": r, "why": why, "cost_usd": cost})
        t = totals[r]
        t[0] += 1
        t[1] += float(s.get("seconds") or 0)
        t[2] += cost
    summary = {k: {"shots": v[0], "seconds": round(v[1], 1), "cost_usd": round(v[2], 2)} for k, v in totals.items()}
    summary["total_usd"] = round(sum(v[2] for v in totals.values()), 2)
    return {"shots": rows, "summary": summary}


def main(argv=None):
    p = argparse.ArgumentParser(description="Label every shot REAL, SWAP or AI with its cost.")
    sub = p.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("label")
    lp.add_argument("shots")
    lp.add_argument("--out")
    a = p.parse_args(argv)
    data = json.loads(Path(a.shots).read_text())
    shots = data.get("shots", data) if isinstance(data, dict) else data
    res = label(shots)
    for r in res["shots"]:
        print(f"{str(r['id']):<6} {r['route']:<5} ${r['cost_usd']:>6.2f}  {r['what'][:48]:<48} {r['why']}")
    s = res["summary"]
    print(f"\nREAL {s['REAL']['shots']} · SWAP {s['SWAP']['shots']} (${s['SWAP']['cost_usd']}) · "
          f"AI {s['AI']['shots']} (${s['AI']['cost_usd']}) · total ${s['total_usd']}")
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
