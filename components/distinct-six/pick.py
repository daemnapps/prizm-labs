#!/usr/bin/env python3
"""The swipe picker — the Distinct Six chosen from REAL swipes, never written from lists.

the owner, 2026-10-08: "Where did you get those formats … everything needs to be tied
together. We do not just assume or make up anything. We need a swipe."

Every version = the winner's message poured into one real swipe from the library.
This picks the N swipes, by evidence, from the Creative Index (asset-ledger/db
ledger.db: swipe_card, element_score, variation):

  earned  — what that swipe's format has earned in this brand's own ads (Meta, via the warehouse)
  proven  — how many creators' swipes share the shape, and the swipe's views where known
  new     — never already used for this winner, and a format none of its versions use yet
  distinct— one format per pick

    python3 components/distinct-six/pick.py brand-a brand-a-grandma-winner [--n 6]

Writes runs/distinct-six/<brand>/<winner>/picks.json — each pick in the same shape
as the proven-to-format batch files (components/ad-variations/definitions/proven-to-format/),
so the format run that writes the version is the one the system already has.
Never calls Meta or a model.
"""
import argparse
import json
import os
import math
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = Path(os.environ.get("CREATIVE_INDEX_DB") or ROOT / "records" / "asset-ledger" / "ledger.db")


def pick(brand, winner, n=6):
    db = sqlite3.connect(LEDGER)
    db.row_factory = sqlite3.Row
    wid = f"creative_winner_{brand}_{winner}"
    # what this winner already has: its format versions (by swipe) — any winner run of the same ad counts
    used = db.execute("""SELECT v.swipe_code, s.format FROM variation v LEFT JOIN swipe_card s ON lower(s.code)=lower(v.swipe_code)
                         WHERE v.relation='format-swap'""").fetchall()
    used_codes = {r["swipe_code"].lower() for r in used if r["swipe_code"]}
    used_formats = {r["format"] for r in used if r["format"]}
    earned = {r["value"]: (r["purchases"] or 0, r["cpa"], r["spend"] or 0) for r in db.execute(
        "SELECT value, purchases, cpa, spend FROM element_score WHERE brand_id=? AND move='format'", (brand,))}
    shared = {r["format"]: r["n"] for r in db.execute("SELECT format, COUNT(*) n FROM swipe_card GROUP BY format")}
    cands = []
    for s in db.execute("SELECT * FROM swipe_card WHERE has_video=1 AND format IS NOT NULL"):
        if s["code"].lower() in used_codes or s["format"] in used_formats:
            continue
        buys, cpa, spend = earned.get(s["format"], (0, None, 0))
        score = 3.0 * math.log10(1 + buys) + 1.0 * math.log2(1 + shared.get(s["format"], 1)) \
            + 0.5 * math.log10(1 + (s["views"] or 0)) - (0.5 if s["format_confidence"] not in ("high",) else 0)
        why = []
        if buys:
            why.append(f"its format earned {buys:g} purchases in {brand}'s own ads (${spend:,.0f} spent" + (f", ${cpa:,.0f} each)" if cpa else ")"))
        why.append(f"{shared.get(s['format'], 1)} swipes in the library share this shape")
        if s["views"]:
            why.append(f"{s['views']:,} views")
        cands.append({"code": s["code"], "format_id": s["format"], "score": round(score, 2), "why": why,
                      "post_url": s["url"], "handle": s["author"], "views": s["views"], "what_happens": s["what_happens"],
                      "carries_value": s["carries_value"], "no_talent": bool(s["no_talent"]), "sheet": s["sheet"],
                      "record": s["record"], "video": f"{s['record']}/video.mp4", "confidence": s["format_confidence"]})
    cands.sort(key=lambda c: (-c["score"], -(c["views"] or 0)))
    picks, seen = [], set()
    for c in cands:
        if c["format_id"] in seen:
            continue
        picks.append(c)
        seen.add(c["format_id"])
        if len(picks) == n:
            break
    out = ROOT / "runs" / "distinct-six" / brand / winner
    out.mkdir(parents=True, exist_ok=True)
    doc = {"_what": "The Distinct Six as REAL swipes: each pick is a swipe from the library the winner's message is poured into "
                    "(the proven-to-format run). Chosen by evidence from the Creative Index; nothing written from lists.",
           "brand": brand, "winner": winner, "picked": date.today().isoformat(),
           "already": sorted(used_codes), "already_formats": sorted(used_formats),
           "formats": picks, "candidates_considered": len(cands)}
    (out / "picks.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return doc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("winner")
    ap.add_argument("--n", type=int, default=6)
    a = ap.parse_args()
    d = pick(a.brand, a.winner, a.n)
    print(f"{d['candidates_considered']} real swipes considered · already used: {', '.join(d['already'])}")
    for i, p in enumerate(d["formats"], 1):
        print(f"{i}. {p['code']} · @{p['handle']} · {p['format_id']} ({p['confidence']}) · score {p['score']}\n"
              f"   {(p['what_happens'] or '')[:140]}\n   why: {'; '.join(p['why'])}\n   {p['post_url']}")
