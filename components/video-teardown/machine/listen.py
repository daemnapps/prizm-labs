"""LISTEN AGAIN (2026-11-13): the swipe's music checked by ear, and every non-word sound its people make.

Why: a swipe's music was described from the song Shazam named, not from the music itself. The match was wrong, so a
trapsoul hip-hop bed was written up as 2010s synth-pop with a singer, and the ad was scored to the wrong genre. The
same teardown never listened for the sounds the people make that are not words (a disgusted "ew", an interested
"mmm", a moan), which carried the swipe's hook.

    music_check   the isolated music (music.py split), read twice on its own by the audio model with one fixed
                  question (genre, subgenre, what decides it, felt tempo, sections). The genre family of both reads
                  must agree; then it is the music's description (`music.checked`), and a Shazam name whose own
                  description says another family is marked disputed. Two reads that disagree are kept, marked
                  `agreed: false`, and nothing is replaced.
    human_sounds  the voices alone (ElevenLabs audio isolation), where sound starts and stops measured with ffmpeg,
                  then each second that carries sound labelled on its own by the audio model (one clip, one short
                  question: the sound and its feeling). Seconds in a row with the same sound are one sound.
                  `human_sounds`: [{"at", "until", "sound", "feeling"}].

Both are written into the run's sound-sheet.json. The Video Studio's edit stage reads them: it makes the music from
`music.checked` and lays each human sound in the production's voice (edit_stage.py).

    python3 listen.py <run dir> [--only music|sounds]
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "gemini-3.1-pro-preview"
KEYS = ("GEMINI_API_KEY", "GEMINI_API_KEY_PERSONAL")
FAMILIES = (("hip-hop", ("hip-hop", "hip hop", "rap", "trap", "drill", "r&b", "rnb", "trapsoul", "phonk", "boom bap",
                         "boom-bap", "jersey club")),
            ("pop", ("pop", "synth-pop", "synthpop", "dance-pop", "indie pop")),
            ("electronic", ("edm", "house", "techno", "dubstep", "electronic", "trance", "future bass")),
            ("rock", ("rock", "punk", "metal", "grunge")),
            ("latin", ("reggaeton", "latin", "dembow")), ("afro", ("afrobeats", "amapiano", "afro")),
            ("orchestral", ("orchestral", "cinematic", "classical", "score")), ("lofi", ("lo-fi", "lofi")))

MUSIC_Q = """This is ONLY the music of a short video ad; voices are removed. Listen to the drums, the bass and the main
sound, not to any idea of a song name. Answer only JSON:
{"genre": "...", "subgenre": "...", "decided_by": "the drums, bass and sounds that decide it",
 "felt_tempo": "half-time | straight | double-time", "bpm": number, "music_vocal": "rap | sung | sample | none",
 "instruments": ["..."], "mood_words": ["..."],
 "sections": [{"from": s, "to": s, "what": "intro / drums drop in / drops out / hits ..."}],
 "sounds_like": ["artist or song (sounds like)"]}"""

CLIP_Q = """This is a one-second clip of a voice track (music removed) from a video. Is there a non-word human sound in
it: sniff, inhale, "ew", "ugh", sigh, "hmm", "mmm", gasp, moan, laugh, kiss, or a spoken word? Answer only JSON:
{"sound": "<the sound, 'word' for speech, or none>", "feeling": "<disgust | unimpressed | curious | interested |
delighted | aroused | amused | none>"}"""


def _keys():
    sys.path.insert(0, str(HERE))
    import keys
    return [(n, keys.get(n, required=False)) for n in KEYS]


def ask_audio(prompt, files):
    """The audio model on inline audio; the first key that answers (a spent key falls through)."""
    parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "audio/mpeg",
                                                   "data": base64.b64encode(Path(f).read_bytes()).decode()}} for f in files]
    body = json.dumps({"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.2}}).encode()
    last = "no key"
    for name, k in _keys():
        if not k:
            continue
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={k}", data=body,
                headers={"Content-Type": "application/json"}), timeout=600)
            text = "".join(p.get("text", "") for p in json.load(r)["candidates"][0]["content"]["parts"])
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0)) if m else None
        except urllib.error.HTTPError as e:
            last = "%s %s" % (name, e.code)
    raise RuntimeError("the audio model did not answer (%s)" % last)


def family(text):
    t = " ".join(str(x) for x in (text if isinstance(text, (list, tuple)) else [text])).lower()
    for fam, words in FAMILIES:                      # hip-hop words first: "trap-pop" is still the trap family
        if any(w in t for w in words):
            return fam
    return "other"


def _mp3(src, out, t=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src)] + (["-t", str(t)] if t else []) + ["-vn", "-ac", "1",
                                                                                         "-ar", "44100", str(out)]
    subprocess.run(cmd, check=True)
    return out


def isolate_voice(mix, out):
    """The voices alone (ElevenLabs audio isolation)."""
    sys.path.insert(0, str(HERE))
    import keys
    k = keys.get("ELEVENLABS_API_KEY")
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"a.mp3\"\r\n"
            f"Content-Type: audio/mpeg\r\n\r\n").encode() + Path(mix).read_bytes() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/audio-isolation", data=body,
                                 headers={"xi-api-key": k, "Content-Type": f"multipart/form-data; boundary={b}"})
    Path(out).write_bytes(urllib.request.urlopen(req, timeout=600).read())
    return out


def music_check(music_mp3, named=None, ask=ask_audio):
    """Two reads of the isolated music; `checked` when their genre families agree."""
    reads = [ask(MUSIC_Q, [music_mp3]) or {} for _ in range(2)]
    fams = [family([r.get("genre"), r.get("subgenre"), r.get("decided_by")]) for r in reads]
    out = {"reads": reads, "families": fams, "agreed": fams[0] == fams[1] and fams[0] != "other", "by": MODEL}
    if out["agreed"]:
        r = reads[0]
        out.update(family=fams[0], genre=r.get("genre"), subgenre=r.get("subgenre"), felt_tempo=r.get("felt_tempo"),
                   bpm=r.get("bpm"), music_vocal=r.get("music_vocal"), instruments=r.get("instruments") or [],
                   mood_words=r.get("mood_words") or [], sections=r.get("sections") or [],
                   sounds_like=r.get("sounds_like") or [])
        if named:
            out["named_family"] = family(named)
            out["name_disputed"] = out["named_family"] not in ("other", fams[0])
    return out


def voiced_spans(voice_mp3, noise="-46dB", gap=0.15):
    """Where the voice track carries sound: [(a, b)] seconds."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(voice_mp3), "-af", f"silencedetect=noise={noise}:d={gap}",
                        "-f", "null", "-"], capture_output=True, text=True)
    marks = re.findall(r"silence_(start|end): ([0-9.]+)", r.stderr)
    m = re.search(r"Duration: (\d+):(\d+):([0-9.]+)", r.stderr)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None
    spans, at = [], 0.0
    for kind, t in marks:
        t = float(t)
        if kind == "start" and t - at > 0.1:
            spans.append((round(at, 2), round(t, 2)))
        if kind == "end":
            at = t
    if dur and dur - at > 0.1 and (not marks or marks[-1][0] == "end"):
        spans.append((round(at, 2), round(dur, 2)))
    return spans


def label_seconds(voice_mp3, spans, ask=ask_audio, until=None):
    """Each voiced second labelled on its own; same sounds in a row merged."""
    rows = []
    tmp = Path(tempfile.mkdtemp(prefix="listen-"))
    seconds = sorted({int(t) for a, b in spans for t in _range(a, b) if until is None or t < until})
    for s in seconds:
        clip = tmp / ("s%03d.mp3" % s)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", "1", "-i", str(voice_mp3), str(clip)],
                       check=True)
        a = ask(CLIP_Q, [clip]) or {}
        snd = str(a.get("sound") or "none").strip().lower()
        if snd in ("none", "word", ""):
            continue
        if rows and rows[-1]["sound"] == snd and rows[-1]["until"] == s:
            rows[-1]["until"] = s + 1
        else:
            rows.append({"at": float(s), "until": s + 1, "sound": snd, "feeling": a.get("feeling") or "none"})
    return rows


def _range(a, b):
    k = int(a)
    while k < b:
        yield k
        k += 1


def run(run_dir, only=None, ask=ask_audio):
    d = Path(run_dir)
    ss_f = d / "sound-sheet.json"
    ss = json.loads(ss_f.read_text()) if ss_f.exists() else {}
    tmp = Path(tempfile.mkdtemp(prefix="listen-"))
    mix = _mp3(d / "source.mp4", tmp / "mix.mp3")
    mu = ss.get("music") or {}
    if only in (None, "music") and mu.get("present"):
        sys.path.insert(0, str(HERE))
        import music as MU
        iso = MU.split(d / "source.mp4", d / "music")
        named = " ".join(str(x) for x in ((mu.get("heard") or {}).get("genre"), (mu.get("heard") or {}).get("subgenre"),
                                          (mu.get("heard") or {}).get("sounds_like")) if x)
        mu["checked"] = music_check(_mp3(iso, tmp / "music.mp3"), named, ask)
        ss["music"] = mu
    if only in (None, "sounds"):
        voice = isolate_voice(mix, tmp / "voice.mp3")
        ss["human_sounds"] = label_seconds(voice, voiced_spans(voice), ask)
        ss["human_sounds_by"] = "ElevenLabs audio isolation, ffmpeg silencedetect, %s per second (listen.py)" % MODEL
    ss_f.write_text(json.dumps(ss, indent=1, ensure_ascii=False))
    return {"music": (ss.get("music") or {}).get("checked"), "human_sounds": ss.get("human_sounds")}


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    print(json.dumps(run(a[0], a[a.index("--only") + 1] if "--only" in a else None), indent=1, ensure_ascii=False))
