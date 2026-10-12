"""THE MIX — how the whole thing sits, measured.

    LOUDNESS   integrated loudness (LUFS), loudness range and true peak of the
               full soundtrack (ffmpeg's EBU R128 meter — the broadcast standard)
    BALANCE    the voices' loudness against the music's, in dB
    DUCKING    how far the music drops while someone speaks (measure.py duck)
    SILENCES   every drop to silence ≥ 0.35 s, and the line that comes after it —
               a pause before the reveal is part of the swipe's structure
    FORM       spoken / music share of the runtime, from the lines and the music read
"""
import json
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = Path(os.environ.get("AUDIO_PYTHON") or "/nonexistent/audio-python")


def loudness(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    def grab(pat):
        m = re.search(pat, tail)
        return float(m.group(1)) if m else None
    return {"lufs": grab(r"I:\s+(-?[\d.]+) LUFS"), "range_lu": grab(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak_dbfs": grab(r"Peak:\s+(-?[\d.]+) dBFS")}


def silences(path, lines, noise="-35dB", least=0.35):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", f"silencedetect=noise={noise}:d={least}",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    out = []
    for a, b in zip(starts, ends):
        nxt = next((l for l in lines if l["start"] >= b - 0.2), None)
        out.append({"from": round(max(a, 0), 2), "to": round(b, 2), "seconds": round(b - max(a, 0), 2),
                    "before": f"{nxt['id']}: {nxt['text'][:60]}" if nxt else "the end"})
    return out


def read(video, tracks, lines, music_section):
    total = float(music_section.get("measured", {}).get("seconds") or 0) or None
    mix = loudness(video)
    out = {"loudness": mix}
    if tracks.get("how") == "demucs":
        v, m = loudness(tracks["voices"]), loudness(tracks["music"])
        out["voices_lufs"], out["music_lufs"] = v.get("lufs"), m.get("lufs")
        if v.get("lufs") is not None and m.get("lufs") is not None:
            out["voice_over_music_db"] = round(v["lufs"] - m["lufs"], 1)
        if lines and music_section.get("present"):
            r = subprocess.run([str(PY), str(HERE / "measure.py"), "duck", str(tracks["music"]),
                                json.dumps([[l["start"], l["end"]] for l in lines])], capture_output=True, text=True)
            try:
                d = json.loads(r.stdout.strip().splitlines()[-1])
                out.update(d)
                if d.get("music_db_while_speaking") is not None and d.get("music_db_otherwise") is not None:
                    out["music_ducks_by_db"] = round(d["music_db_otherwise"] - d["music_db_while_speaking"], 1)
            except Exception:
                pass
    out["silences"] = silences(video, lines)
    speech = 0.0
    last = 0.0
    for l in sorted(lines, key=lambda x: x["start"]):          # union of speaking time
        a, b = max(l["start"], last), l["end"]
        if b > a:
            speech += b - a
        last = max(last, b)
    if total:
        vocals = (music_section.get("heard") or {}).get("vocals")
        out["form"] = {"spoken_percent": round(100 * speech / total),
                       "music_percent": music_section.get("measured", {}).get("music_share_percent", 0),
                       "sung_or_rapped": vocals in ("sung", "rapped", "chant")}
    return out


def render(mx):
    L, f = mx.get("loudness", {}), mx.get("form", {})
    md = ["### MIX", "",
          f"- **Loudness:** {L.get('lufs', '—')} LUFS · range {L.get('range_lu', '—')} LU · peak {L.get('true_peak_dbfs', '—')} dBFS",
          f"- **Voice over music:** {mx.get('voice_over_music_db', '—')} dB"
          + ((f" · music drops {mx['music_ducks_by_db']} dB while someone speaks" if mx["music_ducks_by_db"] >= 1
              else " · music does not drop under the voice") if mx.get("music_ducks_by_db") is not None else ""),
          f"- **Form:** spoken {f.get('spoken_percent', '—')}% of the runtime · music under {f.get('music_percent', '—')}%"
          + (" · the music has sung or rapped words" if f.get("sung_or_rapped") else "")]
    sil = mx.get("silences") or []
    md.append("- **Silences:** " + ("; ".join(f"{s['from']}–{s['to']}s ({s['seconds']}s) before {s['before']}" for s in sil)
                                   if sil else "none — sound all the way through"))
    return "\n".join(md + [""])
