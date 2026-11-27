"""Fill the real-video reference bank from footage we already own (2026-10-30).

Every shot a clip might need (talking, a product in use, an action) is defined in `movement-shots.json`. This finds each
one in the footage index, reads only the seconds it needs off Drive with the key, and cuts them to
runs/ai-elements/movement/. Nothing joins the bank here: `add` files the pieces a person or a check has passed.

    python3 movement_fill.py cut [--per 3] [--only <shot>]    cut the best pieces and write candidates.json + a contact sheet
    python3 movement_fill.py add <candidate id> ...           file passed pieces in movement-bank.json as draft
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHOTS = HERE.parent / "movement-shots.json"
OUT = ROOT / "runs/ai-elements/movement"
CANDIDATES = OUT / "candidates.json"
BRANDS = ("brand_b", "brand_a")
LONG = 10.0               # best reference length is 5 to 10 s
SHORT = 4.0               # a scene shorter than this shows too little movement


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def shots():
    return [s for s in json.loads(SHOTS.read_text())["entries"] if s.get("status") != "deprecated"]


def creator_scene(hit):
    """Real people's footage only: a brief's delivered ad may itself be AI-made."""
    where = str(hit.get("shared_path") or hit.get("collection"))
    return "creator" in str(hit.get("collection")) and "brief" not in where and hit.get("drive_id")


def find(shot, per, search):
    rows, seen = [], set()
    for brand in BRANDS:
        rows += [dict(h, brand=brand) for h in search.search(shot["find"], "", brand=brand, core=shot["core"], per=80)]
    rows.sort(key=lambda h: -h["score"])
    out = []
    for hit in rows:
        secs = float(hit.get("out") or 0) - float(hit.get("in") or 0)
        talks_right = bool(hit.get("talking_head")) == (shot["kind"] == "talking")
        if hit["drive_id"] in seen or secs < SHORT or not creator_scene(hit) or not talks_right:
            continue
        seen.add(hit["drive_id"])
        out.append({"shot": shot["id"], "kind": shot["kind"], "brand": hit["brand"], "drive_id": hit["drive_id"],
                    "label": hit.get("shared_path"), "from": float(hit["in"]), "seconds": min(secs, LONG), "shows": hit.get("shows"),
                    "score": hit["score"]})
        if len(out) >= per:
            break
    return out


def cut(row, paths):
    dest = OUT / (row["id"] + ".mp4")
    if not dest.is_file():
        src, header = paths._media_request(row["drive_id"])
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-headers", header, "-ss", str(row["from"]), "-i", src, "-t", str(row["seconds"]),
                        "-an", "-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "24", str(dest)], check=True, timeout=240)
    return dest


def sheet(rows):
    """One strip of four frames per piece, labelled, so the pieces can be judged at a glance."""
    done = [r for r in rows if (OUT / (r["id"] + ".mp4")).is_file()]
    for r in done:
        strip = OUT / "strips" / (r["id"] + ".jpg")
        strip.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(OUT / (r["id"] + ".mp4")), "-vf",
                        "fps=4/%s,scale=-2:220,tile=4x1" % r["seconds"],
                        "-frames:v", "1", str(strip)], check=False)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["cut", "add"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--per", type=int, default=3)
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    have = json.loads(CANDIDATES.read_text()) if CANDIDATES.is_file() else []
    if a.what == "cut":
        index = ROOT / "components/asset-index/machine"
        paths = load("shared_paths", index / "shared_paths.py")
        search = load("asset_index_search", index / "search.py")
        for shot in shots():
            if a.only and shot["id"] != a.only:
                continue
            for i, row in enumerate(find(shot, a.per, search)):
                row["id"] = "%s-%d" % (shot["id"], i + 1)
                try:
                    cut(row, paths)
                except (subprocess.SubprocessError, OSError) as e:
                    print("skip", row["id"], type(e).__name__)
                    continue
                have = [h for h in have if h["id"] != row["id"]] + [row]
                CANDIDATES.write_text(json.dumps(have, indent=1, ensure_ascii=False))
                print(row["id"], row["brand"], row["from"], row["seconds"], str(row["shows"])[:70], flush=True)
        print(len(sheet(have)), "pieces with strips")
        return 0
    bank_path = HERE.parent / "movement-bank.json"
    bank = json.loads(bank_path.read_text())
    types = {s["id"]: s for s in shots()}
    for row in [h for h in have if h["id"] in a.ids]:
        shot = types[row["shot"]]
        bank["entries"] = [e for e in bank["entries"] if e["id"] != row["id"]] + [{
            "id": row["id"], "file": "runs/ai-elements/movement/%s.mp4" % row["id"], "seconds": row["seconds"], "from": 0,
            "kind": row["kind"], "talks": row["kind"] == "talking", "framing": row["shows"], "does": shot["does"], "real": True,
            "source": {"label": row["label"], "drive_id": row["drive_id"], "cut": "%s s from %s s, no sound" % (row["seconds"], row["from"])},
            "status": "draft"}]
    bank_path.write_text(json.dumps(bank, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
