#!/usr/bin/env python3
"""music_bed.py — the music bed for an edit, made to cover the WHOLE edit (the owner, 4 Oct 2026: "we need the
music for the whole edit"). ElevenLabs Music (his ruled music model), never a named commercial track.

    python3 music_bed.py <video-production-run> [--out <edit run dir>] [--reveal <seconds>]

Reads the edit map's length and the brief's music line (plan.json `music`: energy, bpm, mood), and asks for one
bed in two parts: the brief's energy up to the product reveal, a lift after it, running to the last frame plus a
second of tail — the bed never stops before the edit does. Writes <out>/music/bed.mp3 + music.json (the request,
the cost estimate) and points decisions.json `music` at it; edit_map.py then lays it from 0 to the end.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ve_keys  # noqa: E402  (every key through components/keys/loader.py — SI-194 (readers use loader))

URL = "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192"
USD_PER_MIN = 0.15            # music_v2_5, as billed on the 3 Oct bed (0.30 for ~2 min)

BASE = ["instrumental", "sits under a voice", "continuous loop feel, no big changes"]
NEG = ["vocals", "singing", "lyrics", "choir", "spoken word", "drops", "build-ups", "EDM drop", "aggressive",
       "distorted", "orchestral", "cinematic trailer"]


def plan_for(total: float, reveal: float | None, brief: dict, style: list[str] | None = None) -> dict:
    """The request: the brief's tempo, energy and mood, plus the style words the AD names (decisions.json
    music.style, else the brief's music `style`/`genre`/`instruments`) — no genre is assumed here."""
    bpm = int(brief.get("tempo_bpm") or 100)
    mood = brief.get("mood") or "neutral"
    energy = brief.get("energy") or "low"
    words = list(style or brief.get("style") or [])
    for k in ("genre", "instruments"):
        v = brief.get(k)
        words += v if isinstance(v, list) else ([v] if v else [])
    style = [f"{bpm} BPM", f"{energy} energy", mood, *(words or ["soft modern instrumental bed"])]
    end = total + 1.0                                   # a second of tail past the last frame: never runs out early
    cut = reveal if reveal and 10 < reveal < end - 10 else None
    chunks = []
    if cut:
        chunks.append({"text": "", "duration_ms": int(cut * 1000), "positive_styles": BASE + style,
                       "negative_styles": NEG})
        chunks.append({"text": "", "duration_ms": int((end - cut) * 1000),
                       "positive_styles": BASE + [s for s in style if "energy" not in s] +
                       ["mid energy", "a touch brighter lift", "ends with a soft fade out"],
                       "negative_styles": NEG})
    else:
        chunks.append({"text": "", "duration_ms": int(end * 1000), "positive_styles": BASE + style + ["ends with a soft fade out"],
                       "negative_styles": NEG})
    return {"model_id": "music_v2_5", "seed": 1,
            "composition_plan": {"positive_global_styles": [], "negative_global_styles": [], "chunks": chunks}}


def make(req: dict, dest: Path) -> None:
    k = ve_keys.key("ELEVENLABS_API_KEY")
    if not k:
        raise SystemExit(f"music: {ve_keys.missing('ELEVENLABS_API_KEY')}")
    body = dest.with_suffix(".req.json"); body.write_text(json.dumps(req))
    # the key rides on stdin (-H @-), never on the command line (video-edit#22)
    r = subprocess.run(["curl", "-s", "-o", str(dest), "-w", "%{http_code}", "-X", "POST", URL, "-H", "@-",
                        "-H", "Content-Type: application/json", "--data-binary", f"@{body}"],
                       input=f"xi-api-key: {k}\n", capture_output=True, text=True, timeout=900)
    body.unlink(missing_ok=True)
    if r.stdout.strip() != "200":
        msg = dest.read_text(errors="ignore")[:400] if dest.exists() else ""
        dest.unlink(missing_ok=True)
        raise SystemExit(f"music: ElevenLabs said {r.stdout.strip()}: {msg}")


def dur(f) -> float:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True).stdout.strip()
    return float(o or 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--reveal", type=float)
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    total = max(json.loads(f.read_text())["total"] for f in [out / "edit-map.json", *out.glob("edit-map-*.json")])
    brief = (json.loads((vm / "plan.json").read_text()).get("music") or {}) if (vm / "plan.json").exists() else {}
    d = out / "music"; d.mkdir(parents=True, exist_ok=True)
    old = d / "music.json"
    reveal = a.reveal or (json.loads(old.read_text()).get("reveal_s") if old.exists() else None)
    dec_f = out / "decisions.json"
    dec = json.loads(dec_f.read_text()) if dec_f.exists() else {}
    req = plan_for(total, reveal, brief, (dec.get("music") or {}).get("style"))
    mp3 = d / "bed.mp3"
    make(req, mp3)
    got = dur(mp3)
    if got < total:
        raise SystemExit(f"music: the bed is {got:.1f}s but the edit runs {total:.1f}s — it must cover the whole edit")
    secs = sum(c["duration_ms"] for c in req["composition_plan"]["chunks"]) / 1000
    old.write_text(json.dumps({"request": req, "why": "covers the whole edit (the owner, 4 Oct 2026); lift at the product reveal",
                               "reveal_s": reveal, "out_s": None, "seconds": round(got, 2),
                               "usd_est": round(secs / 60 * USD_PER_MIN, 2)}, indent=1))
    mu = dec.get("music") or {}
    mu.update(file="music/bed.mp3", why="the owner, 4 Oct 2026: \"we need the music for the whole edit\" — one bed from the "
              "first frame to the last, the brief's energy, a lift at the product reveal; ElevenLabs Music v2.5")
    mix = json.loads((HERE.parent / "looks" / "edit-looks.json").read_text())["mix"]
    mu.setdefault("under_voice_db", mix["music_under_voice_db"]); mu.setdefault("in_pauses_db", mix["music_in_pauses_db"])
    dec["music"] = mu
    dec_f.write_text(json.dumps(dec, indent=1, ensure_ascii=False))
    print(f"music: {mp3} · {got:.1f}s for a {total:.1f}s edit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
