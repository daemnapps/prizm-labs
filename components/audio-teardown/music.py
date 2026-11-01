"""THE MUSIC — named, measured, then heard from the music alone.

Three reads of one swipe once described its music three different ways
("upbeat pop", "pizzicato", "dark synthwave"): quiet music under speech is
beyond a model's ear. So the music is read from the voices-removed track, and
everything a tool can measure is measured first.

    NAMED     Shazam (free, no account — the venv named by SHAZAM_PYTHON), then AudD
              (AUDD_API_TOKEN) — both asked, both answers kept: in the
              2026-09-25 test each named a song the other missed
    MEASURED  tempo, beat grid, key, energy across the video, where it builds or
              drops, how it ends (librosa, in the venv named by AUDIO_PYTHON — measure.py)
    HEARD     Gemini on the music track (prompts/music-read-v<N>-damon.md):
              genre, era, instruments, vocals, mood, shape, in the scene or laid
              over, how it sits under the voice, a composer brief
    CHECKED   every label against definitions/sound.json
"""
import json
import os
import subprocess
from pathlib import Path

import gemini as G
from keys import key

HERE = Path(__file__).resolve().parent
PY = Path(os.environ.get("AUDIO_PYTHON") or "/nonexistent/audio-python")
SHAZAM = Path(os.environ.get("SHAZAM_PYTHON") or "/nonexistent/shazam-python")
LISTS = json.loads((HERE / "definitions" / "sound.json").read_text())["lists"]
MUSIC_LISTS = {k: LISTS[k] for k in ("music_source", "vocals", "energy", "valence", "arousal", "in_scene", "shape")}

SHAZAM_CALL = r"""
import asyncio, json, sys
from shazamio import Shazam
t = (asyncio.run(Shazam().recognize(sys.argv[1])).get("track") or {})
print(json.dumps({"title": t.get("title"), "artist": t.get("subtitle"), "link": t.get("url")} if t else {}))
"""


def measure(track):
    r = subprocess.run([str(PY), str(HERE / "measure.py"), "music", str(track)], capture_output=True, text=True,
                       timeout=600)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stderr or r.stdout)[-200:]}


def shazam(track):
    if not SHAZAM.exists():
        return None, "Shazam is not installed"
    try:
        r = subprocess.run([str(SHAZAM), "-c", SHAZAM_CALL, str(track)], capture_output=True, text=True, timeout=120)
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        return None, f"Shazam: {str(e)[:120]}"
    return (d, "named") if d.get("title") else (None, "not a known recording")


def audd(track):
    try:
        tok = key("AUDD_API_TOKEN")
    except Exception:
        return None, "no AudD key"
    r = subprocess.run(["curl", "-sS", "--max-time", "120", "-F", f"api_token={tok}", "-F", f"file=@{track}",
                        "https://api.audd.io/"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return None, "AudD answered oddly"
    if d.get("status") != "success":
        return None, f"AudD: {str(d.get('error'))[:120]}"
    res = d.get("result")
    if not res:
        return None, "not a known recording"
    return {"title": res.get("title"), "artist": res.get("artist"), "link": res.get("song_link")}, "named"


def check(read):
    unknown = []
    for field, allowed in MUSIC_LISTS.items():
        v = read.get(field)
        if v and str(v).replace(" (unsure)", "") not in allowed:
            unknown.append(f"{field}: {v}")
    return unknown


def read(track):
    """The music section of the Sound Sheet."""
    if not track or not Path(track).exists():
        return {"present": False, "why": "no music track (the voices could not be split off)"}
    m = measure(track)
    if m.get("present") is False:
        return {"present": False, "measured": m, "why": "no music under the video"}
    sz, sw = shazam(track)
    az, aw = audd(track)
    named = sz or az
    out = {"present": True, "measured": m,
           "song": named, "named_by": ("Shazam" if sz else "AudD") if named else None,
           "shazam": sz or sw, "audd": az or aw}
    show = {k: v for k, v in m.items() if k not in ("beats", "downbeats_guess")}
    p, text = G.prompt("music-read", HERE)
    text = (text.replace("{measured}", json.dumps(show))
            .replace("{identified}", json.dumps({"shazam": sz or sw, "audd": az or aw}))
            .replace("{lists}", json.dumps(MUSIC_LISTS)))
    try:
        heard, model, _ = G.ask(track, text)
        out["heard"] = heard if isinstance(heard, dict) else {}
        out["heard_by"], out["prompt"] = model, p.name
        out["unknown_labels"] = check(out["heard"])
    except Exception as e:
        out["heard_error"] = str(e)[:200]
    return out


def render(mu):
    md = ["### MUSIC", ""]
    if not mu.get("present"):
        return "\n".join(md + [f"No music. {mu.get('why', '')}", ""])
    m, h = mu.get("measured", {}), mu.get("heard", {})
    song = mu.get("song")
    md += [f"- **Track:** {song['title']} — {song['artist']} (named by {mu['named_by']})" if song
           else f"- **Track:** not a known recording (Shazam: {mu.get('shazam')}; AudD: {mu.get('audd')}) — "
                f"source by ear: {h.get('source', '—')}",
           f"- **Measured:** {m.get('tempo_bpm', '—')} bpm · key {m.get('key', '—')} "
           f"(confidence {m.get('key_confidence', '—')}) · music under {m.get('music_share_percent', '—')}% of the video "
           f"({m.get('starts', '—')}s–{m.get('ends', '—')}s) · ends: {m.get('ending', '—')}",
           f"- **Builds and drops:** " + (", ".join(f"{c['what']} at {c['at']}s" for c in m.get("changes", [])) or "none — steady"),
           f"- **Genre · era:** {h.get('genre', '—')} / {h.get('subgenre', '—')} · {h.get('era', '—')}",
           f"- **Instruments · vocals:** {', '.join(h.get('instruments') or []) or '—'} · {h.get('vocals', '—')}",
           f"- **Mood:** energy {h.get('energy', '—')} · {h.get('valence', '—')} · {h.get('arousal', '—')} · "
           f"{', '.join(h.get('mood_words') or [])}",
           f"- **Shape · where it sits:** {h.get('shape', '—')} · {h.get('in_scene', '—')} · {h.get('how_it_sits', '—')}",
           f"- **Sounds like:** {', '.join(h.get('sounds_like') or []) or '—'}",
           f"- **Composer brief:** {h.get('composer_brief', '—')}"]
    if mu.get("unknown_labels"):
        md.append(f"- Labels not on the lists (kept, to review): {', '.join(mu['unknown_labels'])}")
    if mu.get("heard_error"):
        md.append(f"- Not heard: {mu['heard_error']}")
    return "\n".join(md + [""])
