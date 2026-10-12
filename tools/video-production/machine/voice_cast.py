"""VOICE CASTING FROM THE CLIP MODEL — the clip model's own voices sounded better than the
cast voices (the owner 2026-10-03: "even the doctor's voice sounded better with omni"), but it
invents a new voice every clip. So: make N takes of a character saying their real lines, the
owner picks the best one by ear, and that take is cloned (ElevenLabs instant voice clone) as
the character's ONE voice for every line, on camera and off — consistent across the ad.
("we need to use the best voice then clone it for everything so it stays consistent")

    python3 voice_cast.py takes <name> --still <casting master> --line "<their real words>" --out <dir> [--n 3]
    python3 voice_cast.py clone <name> <take.mp3> [--more take2.mp3 ...] --out <dir>
"""
from __future__ import annotations

import argparse, json, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import omni, omni_bench, lineparity  # noqa: E402

TAKE_NOTES = ("Close-up, talking straight to the lens in a quiet room, a natural, clear speaking voice close to the "
              "microphone, no music, no background noise, no echo. No captions or on-screen text.")


def takes(name: str, still: Path, line: str, out: Path, n: int = 3, resolution: str = "360p") -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    case = {"kind": "talk", "picture": str(still), "prompt": omni.omni_prompt(line, TAKE_NOTES),
            "seconds": 10, "resolution": resolution}

    def one(i):
        clip = out / f"{name}-take-{i}.mp4"
        r = omni_bench.fal(case, clip)
        mp3 = clip.with_suffix(".mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vn", "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)
        return {"take": i, "clip": str(clip), "audio": str(mp3), "usd": r["usd"], "took_s": r["took_s"]}
    with ThreadPoolExecutor(n) as ex:
        return list(ex.map(one, range(1, n + 1)))


def clone(name: str, samples: list[Path], description: str = "") -> str:
    """ElevenLabs instant voice clone from the picked take(s). -> the new voice_id."""
    k = lineparity.key_of(); b = lineparity._boundary()
    body = lineparity._multipart_body({"name": f"{name} (cloned from the clip model, picked by ear)",
                                       "description": description or "picked by ear from the clip model's takes",
                                       "remove_background_noise": "false"},
                                      [("files", Path(s)) for s in samples], b)
    st, _h, raw = lineparity.http_transport("POST", "https://api.elevenlabs.io/v1/voices/add",
                                            {"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={b}"}, body)
    d = json.loads(raw.decode())
    if st is None or st >= 400 or "voice_id" not in d:
        raise SystemExit(f"clone failed {st}: {raw[:300]!r}")
    return d["voice_id"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("takes"); t.add_argument("name"); t.add_argument("--still", required=True); t.add_argument("--line", required=True)
    t.add_argument("--out", required=True); t.add_argument("--n", type=int, default=3)
    c = sub.add_parser("clone"); c.add_argument("name"); c.add_argument("take"); c.add_argument("--more", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "takes":
        print(json.dumps(takes(a.name, Path(a.still), a.line, Path(a.out), a.n), indent=1))
    else:
        print(clone(a.name, [Path(a.take)] + [Path(m) for m in a.more]))
