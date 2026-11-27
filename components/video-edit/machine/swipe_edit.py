"""swipe_edit.py — a swipe's edit, rebuilt on our own footage. Ours, on this machine: no credits for anything we own.

    swipe_edit.py read <swipe.mp4> [--framemap F]                  its shots, lengths and measured energy (free)
    swipe_edit.py plan <swipe.mp4> --brand B [--framemap F] [--shots our.json]
                                                                   every shot filled from our footage, or named as a gap
    swipe_edit.py cut  <plan.json> --out X.mp4 [--audio A]          the picture cut to the swipe's lengths (needs no gap)

The swipe lends its edit only: the order, the lengths and the energy. Its people, product, words and sound never come
across. `--shots` is our own list {shot id: what our shot shows}; without it each shot is looked for by what it shows.
A gap is one shot we do not own: it goes to the brief's own clip route for exactly its seconds, and nothing else is paid
for. Words and captions are the edit line's (compose.py). Checked after the cut: the same number of shots, no piece of
footage twice, and energy at least 0.6 of the swipe's. Output under runs/video-edit/<brand>/<label>/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot_engine as SE  # noqa: E402

CREDITS_S, MIN_CLIP, FLOOR = 3, 4, 0.6


def read(video, framemap=None):
    ss = SE.shots(video, framemap)
    return {"swipe": Path(video).name, "seconds": round(SE.length(video), 2), "shots": ss, "energy": SE.energy(video)}


def plan(video, brand, framemap=None, ours=None, find=None, where=None):
    r = read(video, framemap)
    find, used, rows = find or SE.find, set(), []
    for s in r["shots"]:
        seen = (ours or {}).get(s["id"]) or s["what"]
        hit = find(brand, seen, s["seconds"], used, where=where, does="" if (ours or {}).get(s["id"]) else s.get("does") or "") if seen and not (ours is None and s.get("talks")) else None
        rows.append(dict({"id": s["id"], "seconds": s["seconds"], "shows": seen}, **({"ours": hit} if hit else {"gap": "a person talking: the brief's own clip" if s.get("talks") and not ours else "not in our footage"})))
    gaps = [x for x in rows if "gap" in x]
    return {"brand": brand, "swipe": r["swipe"], "seconds": r["seconds"], "energy": r["energy"], "rows": rows, "owned": len(rows) - len(gaps), "gaps": len(gaps),
            "credits": sum(max(MIN_CLIP, round(x["seconds"])) * CREDITS_S for x in gaps), "ready": not gaps,
            "check_before_use": sorted({"%s: usage rights %s" % (x["id"], x["ours"]["rights"]) for x in rows if "ours" in x and x["ours"].get("rights") not in (None, "allowed")} |
                                       {"%s: preview copy, not the full file" % x["id"] for x in rows if "ours" in x and x["ours"].get("copy") == "preview"})}


def cut(p, out, audio=None):
    if not p["ready"]:
        raise SystemExit("NOT READY: %d shot(s) not in our footage: %s" % (p["gaps"], ", ".join(x["id"] for x in p["rows"] if "gap" in x)))
    items = [dict(x["ours"], id=x["id"]) for x in p["rows"]]
    res = SE.build(items, out, audio=audio)
    SE.sheet([(x["file"], float(x["in"]), x["seconds"]) for x in items], Path(out).with_name(Path(out).stem + "-look-first.png"))
    e = SE.energy(out)
    seen = [(x["file"], round(float(x["in"]), 1)) for x in items]
    res["checks"] = {"same shots": len(items) == len(p["rows"]), "no footage twice": len(seen) == len(set(seen)),
                     "energy": e["motion"] >= FLOOR * p["energy"]["motion"], "length": abs(res["seconds"] - sum(x["seconds"] for x in items)) < 0.15}
    res["energy"] = {"ours": e, "swipe": p["energy"]}
    return res


def main(argv):
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None               # noqa: E731
    if len(argv) < 2:
        print(__doc__)
        return 2
    if argv[0] == "read":
        r = read(argv[1], opt("--framemap"))
    elif argv[0] == "plan" and opt("--brand"):
        r = plan(argv[1], opt("--brand"), opt("--framemap"), json.loads(Path(opt("--shots")).read_text()) if opt("--shots") else None)
    elif argv[0] == "cut" and opt("--out"):
        r = cut(json.loads(Path(argv[1]).read_text()), opt("--out"), opt("--audio"))
    else:
        print(__doc__)
        return 2
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
