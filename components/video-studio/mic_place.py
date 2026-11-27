#!/usr/bin/env python3
"""A clean read placed on a real mic in a real place: the read sounds recorded where the scene is shot.

A designed voice comes back studio-clean (close mic, no room, no air). A scene shot outdoors on a handheld
interview mic never sounds like that. This step takes any read and gives it:
  - the MIC's sound (`kind`): its low cut, its top roll-off, its presence bump and how hard it squeezes,
  - the PLACE's air (`place`): the setting's room-tone bed from the SFX bank (`room-tone-<place>`, looped,
    levelled, then set `bed_db` under the voice), plus wind on the mic when the place is outdoors,
and NO room echo outdoors (nothing is added that a field recording would not have).
The speaker is on a CLEAN mic: the voice stays clear and forward, the mic only lightly coloured, and the place
sits SUBTLY underneath (bed 26 dB under the voice, wind 46 dB under) — a hint of where they are, never a
competing sound. That holds for every place, not only the beach (owner, 2026-11-10).
The read keeps its exact length, so its timing in a take never moves.

    python3 mic_place.py <clean.mp3> <out.mp3> [--place beach] [--kind handheld] [--bed bed.mp3] [--bed-db -26]

In a take (take.py): `"mic": {"place": "beach", "kind": "handheld"}` on the take (or on one cast member) and
every re-read line is made clean, then placed. The clean read is kept beside it in reads/clean/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

# Each mic, as filters on the voice. handheld = a dynamic interview mic held at the mouth (street interviews).
KINDS = {
    "handheld": "highpass=f=100,lowpass=f=13000,equalizer=f=300:t=q:w=1.1:g=-1.5,equalizer=f=3000:t=q:w=1.3:g=2,"
                "acompressor=threshold=-20dB:ratio=2.5:attack=6:release=100:makeup=1",
    "phone": "highpass=f=200,lowpass=f=7000,equalizer=f=1800:t=q:w=1.4:g=3,"
             "acompressor=threshold=-22dB:ratio=5:attack=3:release=70:makeup=2",
    "lav": "highpass=f=90,lowpass=f=12000,equalizer=f=4500:t=q:w=1.5:g=2,"
           "acompressor=threshold=-18dB:ratio=3:attack=6:release=120:makeup=1",
}
OUTDOOR = {"beach", "street", "park", "outdoor", "pool", "rooftop", "field"}


def bed_of(place: str) -> Path:
    """The setting's room tone from the SFX bank (components/video-production/banks/sfx, `room-tone-<place>`)."""
    banks = ST.part("video-production") / "banks" / "sfx" / "index.json"
    row = next((r for r in json.loads(banks.read_text())["rows"]
                if isinstance(r, dict) and r.get("id") == f"room-tone-{place}"), None)
    if not row or row.get("status") != "made" or not row.get("file"):
        raise SystemExit(f"no made room tone for {place!r}: add a `room-tone-{place}` row to {banks} and make it "
                         "(video-production/machine/make_bank.py)")
    sys.path.append(str(ST.part("brandpath")))
    import drive_index as DI                                       # the Drive's Shared Assets
    m = DI.mount()
    if not m:
        raise SystemExit("the Drive's Shared Assets is not mounted — pass --bed")
    f = m / row["file"].split("Shared Assets/", 1)[-1]
    if not f.is_file():
        raise SystemExit(f"room tone file missing: {f}")
    return f


def seconds(f) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True, check=True).stdout.strip())


def place(clean, out, place="beach", kind="handheld", bed=None, bed_db=-26.0, wind_db=-46.0):
    """`clean` read → `out`, on the `kind` mic in `place`. Same length as the clean read."""
    clean, out = Path(clean), Path(out)
    if kind not in KINDS:
        raise SystemExit(f"mic kind {kind!r}: one of {', '.join(KINDS)}")
    bed = Path(bed) if bed else bed_of(place)
    secs = seconds(clean)
    # each read starts the bed somewhere else (fixed per read), so lines cut together never repeat the same waves
    off = int(hashlib.sha1(clean.name.encode()).hexdigest()[:6], 16) % max(1, int(seconds(bed) * 10) - 10) / 10
    graph = (f"[0:a]aresample=44100,aformat=channel_layouts=mono,{KINDS[kind]},loudnorm=I=-16:TP=-1.5:LRA=11[v];"
             f"[1:a]aresample=44100,aformat=channel_layouts=mono,atrim=start={off:.1f},asetpts=PTS-STARTPTS,"
             f"aloop=loop=-1:size=2147483647,atrim=0:{secs:.3f},loudnorm=I=-16:TP=-1.5,volume={bed_db}dB[b];")
    mix = "[v][b]"
    n = 2
    if place in OUTDOOR:      # wind on the mic: low rumble that comes and goes
        graph += (f"anoisesrc=color=brown:sample_rate=44100:amplitude=0.6:seed=7,atrim=0:{secs:.3f},lowpass=f=180,"
                  f"tremolo=f=0.35:d=0.85,volume={wind_db}dB[w];")
        mix += "[w]"
        n = 3
    graph += f"{mix}amix=inputs={n}:duration=first:normalize=0,alimiter=limit=0.95[o]"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(clean), "-stream_loop", "-1", "-i", str(bed),
                    "-filter_complex", graph, "-map", "[o]", "-t", f"{secs:.3f}", "-c:a", "libmp3lame", "-b:a", "192k",
                    str(out)], check=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clean"); ap.add_argument("out")
    ap.add_argument("--place", default="beach"); ap.add_argument("--kind", default="handheld")
    ap.add_argument("--bed"); ap.add_argument("--bed-db", type=float, default=-26.0)
    a = ap.parse_args()
    print(place(a.clean, a.out, a.place, a.kind, a.bed, a.bed_db))
