#!/usr/bin/env python3
"""Every re-cut of a winner → a production brief that actually reads.

the owner, 2026-10-08: "read through the new setups and identify if it actually reads
well … think through what the format is actually calling for … create new
production briefs … pull from our asset index … be resourceful."

    python3 components/distinct-six/variation_brief.py brand-a brand-a-grandma-winner --product glow-face-scrub [--only order-pas]

For each cut in runs/distinct-six/<brand>/<winner>/recipes.json: Claude (the owner's
plan, `claude -p`) reads the cut like a viewer with prompts/variation-brief-v1-damon.md,
the winner's beats (Creative Index), the doctrine framework the cut follows, the
clip library (runs/distinct-six/<brand>/clip-library/*.json), the brand's
position (its NEVER list), the product's offer and the core message. Writes
briefs/<cut>.json. Never calls Meta.
"""
import argparse
import json
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.argv_saved, sys.argv = sys.argv, ["x"]
sys.path.insert(0, str(HERE))
import run as R  # claude(), the Creative Index path  # noqa: E402
sys.argv = sys.argv_saved
PROMPT = HERE / "prompts" / "variation-brief-v1-damon.md"
FORMULAS = json.loads((HERE / "formulas.json").read_text())
FW = json.loads((ROOT / "components" / "marketing-doctrine" / "ad-frameworks.json").read_text())
FW = {f["id"]: f for f in (FW.get("frameworks") or [v for v in FW.values() if isinstance(v, list)][0])}


def offer_text(brand, product):
    t = (ROOT / "brands" / brand / "products" / "offer-bank.md").read_text()
    m = re.search(rf"^## {re.escape(product)}.*?(?=^## )", t, re.S | re.M)
    return (m.group(0) if m else "")[:6000]


def inputs(brand, winner, product):
    db = sqlite3.connect(R.LEDGER)
    beats = db.execute("SELECT n, section, start_s, seconds, says FROM beat WHERE creative_id=? ORDER BY n",
                       (f"creative_winner_{brand}_{winner}",)).fetchall()
    win = "\n".join(f"{n}. `{s}` {a:.0f}–{a + d:.0f}s ({d:.0f}s): \"{w}\"" for n, s, a, d, w in beats)
    clips = []
    for f in sorted((ROOT / "runs" / "distinct-six" / brand / "clip-library").glob("*.json")):
        lib = json.loads(f.read_text())
        clips += [f"- `{c['clip']}` · {', '.join(c['sections']) or c['kind']} · \"{c['vo_line']}\" · {c['note']}"
                  for c in lib["clips"]]
    return {"BRAND": brand.title(), "WINNER": win, "CLIPS": "\n".join(clips) or "(no clip library yet)",
            "POSITION": (ROOT / "brands" / brand / "brand-identity" / "position.md").read_text()[:12000],
            "PRODUCT": product, "OFFER": offer_text(brand, product),
            "CORE": json.loads((ROOT / "brands" / brand / "brand-identity/core-message/core-message.json").read_text())["core"]}, beats


def framework_text(cut):
    if cut.get("framework"):
        f = FW[cut["framework"]]
        aw = f.get("awareness") or {}
        return (f"This cut runs the **{f['name']}** framework (enters {aw.get('entry')}, exits {aw.get('exit')}). Its sections, in order, "
                "and what each must do:\n" + "\n".join(f"- `{s['id']}`: {s['shape']}" for s in f["sections"]))
    fm = next(x for t in FORMULAS["tiers"] for x in t["formulas"] if x["id"] == cut["formula"])
    return f"This cut is a **{fm['name']}**: {fm['how']} It tests {fm['tests']}. Keep the winner's own argument; make the new order read."


def one(brand, winner, base, beats, cut, out):
    text = PROMPT.read_text()
    by_n = {b[0]: b for b in beats}
    plan = "\n".join(f"{i}. winner beat {n} · `{by_n[n][1]}` · \"{by_n[n][4][:160]}\"" for i, n in enumerate(cut["beats"], 1))
    vals = dict(base, CUT_NAME=cut["name"], FORMULA=cut["formula"], FRAMEWORK=framework_text(cut),
                CUT=f"{cut['name']} — {cut['length_s']:.0f}s as planned\n{plan}")
    for k, v in vals.items():
        text = text.replace("{" + k + "}", str(v))
    (out / f"{cut['id']}.sent.md").write_text(text)
    got = R.claude(text)
    got.update({"cut": cut["id"], "name": cut["name"], "formula": cut["formula"], "framework": cut.get("framework"),
                "prompt": PROMPT.name})
    (out / f"{cut['id']}.json").write_text(json.dumps(got, indent=1, ensure_ascii=False))
    return cut["id"], got.get("verdict"), len(got.get("new_pieces") or []), len(got.get("breaks") or [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("winner")
    ap.add_argument("--product", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    run = ROOT / "runs" / "distinct-six" / a.brand / a.winner
    cuts = json.loads((run / "recipes.json").read_text())["cuts"]
    if a.only:
        cuts = [c for c in cuts if c["id"] in a.only]
    out = run / "briefs"
    out.mkdir(exist_ok=True)
    base, beats = inputs(a.brand, a.winner, a.product)
    with ThreadPoolExecutor(3) as ex:
        for cid, verdict, new, breaks in ex.map(lambda c: one(a.brand, a.winner, base, beats, c, out), cuts):
            print(f"{cid:<26} {verdict:<18} {new} new piece(s) · {breaks} break(s)")


if __name__ == "__main__":
    main()
