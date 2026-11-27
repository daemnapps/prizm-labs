#!/usr/bin/env python3
"""Seeds the board with the proven cloud run.

Reads ../archive/evidence-run.json (every generation from the Thai grandma
production, verbatim params) and writes runs/thai-grandma/run.json in the
board's shape: four stations, each a list of assets with prompt, settings,
references, and output URL. Run once; safe to re-run (overwrites).

    python3 machine/seed_evidence.py --brand <brand>

--brand is required and is written into the run record as its brand.
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / "archive" / "evidence-run.json"
OUT = HERE / "runs" / "thai-grandma" / "run.json"

STATION = {
    "character-still": ("cast", None),
    "voiceover": ("voices", None),
    "scene-still": ("scenes", None),
    "scene-video-lipsync": ("motion", "talking"),
    "scene-video-silent": ("motion", "b-roll"),
    "scene-video-prompted": ("motion", "cinematic"),
    "product-video": ("motion", "product"),
}


def settings_for(item):
    p = item.get("params") or {}
    t = item.get("type")
    if t == "image":
        return " · ".join(x for x in [p.get("aspect_ratio"), str(p.get("resolution") or "").upper()] if x)
    if t == "audio":
        bits = []
        if p.get("speech_rate") is not None:
            bits.append(f"rate {p['speech_rate']:+d}" if isinstance(p["speech_rate"], int) else f"rate {p['speech_rate']}")
        if p.get("medias"):
            bits.append(f"cloned from {len(p['medias'])} ref" + ("s" if len(p["medias"]) > 1 else ""))
        return " · ".join(bits)
    if t == "video":
        bits = [f"{p.get('duration')}s", p.get("resolution") or ""]
        if p.get("generate_audio"):
            bits.append("gen audio")
        return " · ".join(b for b in bits if b)
    return ""


def refs_for(item):
    out = []
    for m in (item.get("params") or {}).get("medias") or []:
        d = m.get("data") or {}
        out.append({"role": m.get("role"), "type": d.get("type"), "url": d.get("url")})
    return out


def poster_for(item, refs):
    r = item.get("results") or {}
    if r.get("thumbnailUrl"):
        return r["thumbnailUrl"]
    if item.get("type") == "video":
        for ref in refs:
            if ref.get("role") == "image" and ref.get("url"):
                return ref["url"]
    if item.get("type") == "image":
        return r.get("minUrl") or r.get("rawUrl")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seed_evidence.py",
                                 description="Seed the board with the proven cloud run.")
    ap.add_argument("--brand", required=True, metavar="<brand>",
                    help="the brand written into the seeded run record")
    brand = ap.parse_args(argv).brand
    items = json.loads(SRC.read_text())
    stations = {"cast": [], "voices": [], "scenes": [], "motion": []}
    for it in items:
        m = STATION.get(it.get("stage"))
        if not m:
            continue
        station, mode = m
        r = it.get("results") or {}
        refs = refs_for(it)
        asset = {
            "id": (it.get("id") or "")[:8],
            "date": (it.get("iso_date") or "")[:10],
            "kind": it.get("type"),
            "mode": mode,
            "model": it.get("model"),
            "prompt": ((it.get("params") or {}).get("prompt") or "").strip(),
            "settings": settings_for(it),
            "refs": refs,
            "out": r.get("rawUrl"),
            "poster": poster_for(it, refs),
            "dur": r.get("durationSec"),
        }
        stations[station].append(asset)
    for k in stations:
        stations[k].sort(key=lambda a: a["date"])
    run = {
        "slug": "thai-grandma",
        "label": "Thai grandma — the proven cloud run",
        "brand": brand,
        "opened": "2026-07-28",
        "closed": "2026-08-18",
        "note": ("The production this machine was reverse-engineered from: "
                 "three sessions, every asset kept. Outputs stream from the "
                 "cloud host; nothing here regenerates."),
        "stations": stations,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(run, indent=1))
    counts = {k: len(v) for k, v in stations.items()}
    print(f"wrote {OUT} — " + ", ".join(f"{k} {n}" for k, n in counts.items()))


if __name__ == "__main__":
    main()
