"""multiply.py — our Ad Multiplier: many versions of one ad that already sells, paying only for seconds that truly change.

    multiply.py plan <ad.mp4> --brand B [--framemap F] [--versions N] [--changes C.json]   the versions and what each costs
    multiply.py make <plan.json> --out DIR                                                 every version that costs nothing

One version changes one thing. The ad's sound and timing stay exactly as they are, so a change is only ever a picture:
    shot        a shot swapped for a piece of our own footage           free
    opening     the first shot swapped                                  free
    end         the last shot swapped                                   free
    file        a shot swapped for a file you name (a finished clip)    free
    person, product, background   the shot sent to the swap, that shot only, its own seconds     paid, listed, never sent here
Words on screen are not touched here: a new headline or card is the edit line's (compose.py). A shot with words burned
into it loses them when it is swapped: such a version says so (`words_to_reset`), and a clean master avoids it.

The bought tool re-renders the whole ad for every version. This cuts the ad into its shots, changes one, and lays the
rest back untouched. `--changes` is a list of {"name", "do", "shot", "show" | "file" | "with"}; without it the versions
are found from our footage, the opening first (it decides the stop), then the shots nobody talks in.
Output under runs/ad-variations/<brand>/<label>/. Nothing here spends.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "video-edit" / "machine"))
import shot_engine as SE  # noqa: E402

PAID = ("person", "product", "background")
CREDITS_S, MIN_CLIP, OPENING = 3, 4, 0.5


def _version(name, do, s, hit=None, gap=None, **kw):
    v = dict({"name": name, "do": do, "shot": s["id"], "at": [s["start"], s["end"]], "seconds": s["seconds"]}, **{k: x for k, x in kw.items() if x})
    if s.get("text"):
        v["words_to_reset"] = s["text"]
    if do in PAID:
        v.update(ready=False, credits=max(MIN_CLIP, round(s["seconds"])) * CREDITS_S, send="this shot only: %s, %.2f s" % (s["id"], s["seconds"]))
    elif hit:
        v.update(ready=True, credits=0, use=hit)
    else:
        v.update(ready=False, credits=0, gap=gap or "not in our footage")
    return v


def plan(ad, brand, framemap=None, versions=5, changes=None, find=None):
    find, ss = find or SE.find, SE.shots(ad, framemap)
    by, out, used = {s["id"]: s for s in ss}, [], set()
    first = next((s for s in ss if s["seconds"] >= OPENING), ss[0])          # a flash frame is not the opening
    if changes:
        for c in changes:
            s = first if c["do"] == "opening" else ss[-1] if c["do"] == "end" else by.get(c.get("shot"))
            if s is None:
                raise SystemExit("no shot %s in this ad (it has %s)" % (c.get("shot"), ", ".join(by)))
            hit = None
            if c["do"] == "file":
                hit = {"file": c["file"], "in": float(c.get("in") or 0), "seconds": s["seconds"]}
            elif c["do"] not in PAID:
                hit = find(brand, c.get("show") or s["what"], s["seconds"], used, does="" if c.get("show") else s.get("does") or "")
            out.append(_version(c.get("name") or "%s-%s" % (c["do"], s["id"]), c["do"], s, hit, with_=c.get("with")))
    else:
        order = [("opening", first)] + [("shot", s) for s in ss if s is not first and s["seconds"] >= OPENING and not s.get("talks")]
        tries = 0
        while len(out) < versions and tries < 3:
            tries += 1
            for do, s in order:
                if len(out) >= versions:
                    break
                hit = find(brand, s["what"], s["seconds"], used, does=s.get("does") or "") if s["what"] else None
                if hit:
                    out.append(_version("%s-%s-%d" % (do, s["id"].lower(), tries), do, s, hit))
    whole = round(SE.length(ad)) * CREDITS_S
    return {"ad": str(ad), "brand": brand, "seconds": round(SE.length(ad), 2), "shots": len(ss), "timeline": ss, "versions": out, "credits": sum(v["credits"] for v in out),
            "bought_tool_credits": whole * len(out), "ready": sum(v["ready"] for v in out),
            "check_before_use": sorted({"%s: usage rights %s" % (v["name"], v["use"]["rights"]) for v in out if (v.get("use") or {}).get("rights") not in (None, "allowed")} |
                                       {"%s: preview copy, not the full file" % v["name"] for v in out if (v.get("use") or {}).get("copy") == "preview"})}


def make(p, out):
    out, made, ad = Path(out), [], p["ad"]
    sound = ad if SE.has_audio(ad) else None
    for v in p["versions"]:
        if not v["ready"]:
            continue
        items = [dict(v["use"], id=s["id"], seconds=s["seconds"]) if s["id"] == v["shot"] else {"id": s["id"], "file": ad, "in": s["start"], "seconds": s["seconds"]} for s in p["timeline"]]
        r = SE.build(items, out / (v["name"] + ".mp4"), audio=sound)
        r.update(name=v["name"], changed=v["shot"], checks={"length": abs(r["seconds"] - sum(s["seconds"] for s in p["timeline"])) < 0.15, "sound kept": bool(sound) == SE.has_audio(r["file"])})
        made.append(r)
    out.mkdir(parents=True, exist_ok=True)
    rows = [(v["use"]["file"], float(v["use"].get("in") or 0), v["seconds"]) for v in p["versions"] if v["ready"]]
    if rows:
        SE.sheet(rows, out / "look-first.png")                            # the swapped pieces, to look at before any is used
    (out / "made.json").write_text(json.dumps(made, indent=1))
    return made


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d          # noqa: E731
    if len(argv) >= 2 and argv[0] == "plan" and opt("--brand"):
        r = plan(argv[1], opt("--brand"), opt("--framemap"), int(opt("--versions", 5)), json.loads(Path(opt("--changes")).read_text()) if opt("--changes") else None)
    elif len(argv) >= 2 and argv[0] == "make" and opt("--out"):
        r = make(json.loads(Path(argv[1]).read_text()), opt("--out"))
    else:
        print(__doc__)
        return 2
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
