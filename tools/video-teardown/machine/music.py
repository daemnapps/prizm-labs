"""THE MUSIC, IDENTIFIED — not guessed (2026-09-25).

Three reads of the same swipe described its music three ways ("upbeat pop",
"pizzicato", "dark synthwave"): quiet music under speech is beyond a model's
ear. the owner: "L would be cool if possible … let's find it."

    1. SPLIT   Demucs (Meta's open separation model, on this Mac, in its own
               venv named by DEMUCS_PYTHON) pulls the music out from under the
               talking: <run>/music/no_vocals.wav.
    2. NAME    Shazam names the track and artist from the isolated music — free,
               no account (shazamio, in its own venv named by SHAZAM_PYTHON).
               AudD is a backup only if a key is ever put in the Keychain
               (daemn-AUDD_API_TOKEN); the owner chose Shazam over signing up.
    3. DESCRIBE When no song is named (an original or unreleased sound), the
               ISOLATED music is described by the model, which can actually hear
               it on its own.

Writes <run>/music/music.json and returns {"song": …, "described": …}.
Brand-agnostic; reads only the run's video.

    python3 music.py <run dir>
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMUCS = Path(os.environ.get("DEMUCS_PYTHON") or "/nonexistent/demucs-python")
AUDD = "https://api.audd.io/"
SHAZAM = Path(os.environ.get("SHAZAM_PYTHON") or "/nonexistent/shazam-python")


def _key(name):
    sys.path.insert(0, str(Path.home() / ".daemn"))
    try:
        import daemn_keys
        v = daemn_keys.key(name)
        return v if v and "PASTE" not in v else None
    except Exception:
        return None


def split(video, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    # The audio teardown (transcript.py) has already lifted the music off this
    # video with the same Demucs split — reuse it rather than split twice.
    try:
        spec = importlib.util.spec_from_file_location("transcript", HERE / "transcript.py")
        tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)
        cached = tr.AUDIO_CACHE / tr._fingerprint(video) / "audio" / "music.mp3"
        if cached.exists():
            mp3 = out_dir / "music-only.mp3"
            shutil.copy(cached, mp3)
            return mp3
    except Exception:
        pass
    wav = out_dir / "mix.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "2", "-ar", "44100",
                    str(wav)], check=True)
    if not DEMUCS.exists():
        raise RuntimeError("Demucs is not installed (set DEMUCS_PYTHON to its venv's python)")
    r = subprocess.run([str(DEMUCS), "-m", "demucs", "--two-stems", "vocals", "-o", str(out_dir / "sep"), str(wav)],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"Demucs failed: {r.stderr[-300:]}")
    nv = next((out_dir / "sep").rglob("no_vocals.wav"), None)
    if not nv:
        raise RuntimeError("Demucs wrote no music track")
    target = out_dir / "no_vocals.wav"
    nv.replace(target)
    mp3 = out_dir / "music-only.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(target), "-b:a", "128k", str(mp3)], check=True)
    return mp3


def loudness(path):
    """Mean volume in dB — near-silence means there is no music to name."""
    r = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "mean_volume" in line:
            return float(line.split(":")[1].replace("dB", "").strip())
    return -99.0


SHAZAM_CALL = """
import asyncio, json, sys
from shazamio import Shazam
t = (asyncio.run(Shazam().recognize(sys.argv[1])).get("track") or {})
meta = {m.get("title"): m.get("text") for s in t.get("sections") or [] for m in s.get("metadata") or []}
print(json.dumps({"artist": t.get("subtitle"), "title": t.get("title"), "album": meta.get("Album"),
                  "release_date": meta.get("Released"), "link": t.get("url")} if t else {}))
"""


def shazam(mp3):
    if not SHAZAM.exists():
        return None, "Shazam is not installed (set SHAZAM_PYTHON to its venv's python)"
    r = subprocess.run([str(SHAZAM), "-c", SHAZAM_CALL, str(mp3)], capture_output=True, text=True, timeout=180)
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None, f"Shazam answered oddly: {(r.stderr or r.stdout)[-160:]}"
    return (d, "named by Shazam") if d.get("title") else (None, "Shazam: not a known recording (an original or unreleased sound)")


def name_song(mp3):
    song, how = shazam(mp3)
    if song:
        return song, how
    tok = _key("AUDD_API_TOKEN")
    if not tok:
        return None, how
    r = subprocess.run(["curl", "-sS", "--max-time", "120", "-F", f"api_token={tok}", "-F", "return=spotify,apple_music",
                        "-F", f"file=@{mp3}", AUDD], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None, f"AudD answered oddly: {r.stdout[:160]}"
    res = d.get("result")
    if d.get("status") != "success":
        return None, f"AudD: {json.dumps(d.get('error'))[:160]}"
    if not res:
        return None, "AudD: not a known recording (an original or unreleased sound)"
    return {"artist": res.get("artist"), "title": res.get("title"), "album": res.get("album"),
            "release_date": res.get("release_date"), "link": res.get("song_link")}, "named by AudD"


def describe(mp3):
    sp = importlib.util.spec_from_file_location("deepen", HERE / "deepen.py")
    dp = importlib.util.module_from_spec(sp); sp.loader.exec_module(dp)
    return dp.ask(mp3, """This is ONLY the music track of a short video — the speech has been removed. Describe it as
someone briefing a composer: genre and sub-genre; the instruments you hear; vocals or none; the feel; tempo in bpm
(approximate); the era or reference; how it is built (intro, loop, drop) and where it changes. Name two real tracks
it sounds like, marked (sounds like). One paragraph, no heading. If there is no music at all, say so.""")


def identify(run_dir):
    d = Path(run_dir)
    out = d / "music"
    # THE AUDIO TEARDOWN READ IT ALREADY (2026-09-30): named by Shazam and AudD,
    # tempo, key and energy measured, heard from the music alone. Use that
    # rather than splitting, naming and describing a second time.
    ss = d / "sound-sheet.json"
    if ss.exists():
        mu = (json.loads(ss.read_text()) or {}).get("music") or {}
        if mu:
            out.mkdir(exist_ok=True)
            m, h = mu.get("measured") or {}, mu.get("heard") or {}
            if not mu.get("present"):
                res = {"song": None, "how": "no music (audio teardown)", "described": "No music."}
            else:
                song = mu.get("song")
                res = {"song": song, "how": f"named by {mu.get('named_by')}" if song else "not a known recording (Shazam and AudD)",
                       "described": f"Measured: {m.get('tempo_bpm')} bpm, key {m.get('key')}, ends {m.get('ending')}. "
                                    + str(h.get("composer_brief") or "")}
            res["from"] = "sound-sheet.json (audio teardown)"
            (out / "music.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
            return res
    mp3 = split(d / "source.mp4", out)
    vol = loudness(mp3)
    res = {"music_only": str(mp3.relative_to(d)), "mean_volume_db": vol}
    if vol < -55:
        res.update(song=None, how="no music under the speech (the isolated track is near silent)", described="No music.")
    else:
        song, how = name_song(mp3)
        res.update(song=song, how=how)
        res["described"] = describe(mp3)
    (out / "music.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    return res


if __name__ == "__main__":
    print(json.dumps(identify(sys.argv[1]), indent=1, ensure_ascii=False))
