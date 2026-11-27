"""One continuous narration read for a brief's body, split into scene files that join back seamlessly.

  python3 voice_continuous.py 0322          3 reads on eleven_v3 in the brief's cloned voice, each heard back by scribe;
                                             the best is kept and cut at each scene's first word into voice/continuous/S*.mp3
Each scene file runs from its first word to the next scene's first word, so laid end to end they are the one read.
The voice, model and settings are the ones set for the on-screen demographic (voices.py), written into voice/reads.json
before the read.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LEAD = 0.04


def key(name):
    sys.path.insert(0, HERE)
    import settings as ST
    return ST.key(name)


def toks(s):
    return [re.sub(r"[^a-z0-9$]", "", w.lower()) for w in s.split() if re.sub(r"[^a-z0-9$]", "", w.lower())]


def tts(text, voice, seed, out, model="eleven_v3", settings=None):
    """settings: the voice's own banked voice_settings (a voice checked on one model reads on that model, as checked)."""
    req = {"text": text, "model_id": model, "seed": seed, "apply_text_normalization": "off"}
    if settings:
        req["voice_settings"] = settings
    body = json.dumps(req).encode()
    r = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_192", data=body,
                               headers={"xi-api-key": key("ELEVENLABS_API_KEY"), "Content-Type": "application/json"})
    open(out, "wb").write(urllib.request.urlopen(r, timeout=300).read())


MAX_CHARS = 4500   # one read per request; a longer script (a 3-minute story) is read in parts at scene breaks (20 Nov)


def tts_long(lines, voice, seed, out, model="eleven_v3", settings=None):
    """The whole script in one voice and seed; read in one request when it fits, else in parts split at scene lines
    and joined end to end, so a long script reads like a short one."""
    text = " ".join(lines)
    if len(text) <= MAX_CHARS:
        return tts(text, voice, seed, out, model, settings)
    parts, cur = [], []
    for ln in lines:
        if cur and len(" ".join(cur + [ln])) > MAX_CHARS:
            parts.append(" ".join(cur)); cur = []
        cur.append(ln)
    parts.append(" ".join(cur))
    files = []
    for k, t in enumerate(parts):
        pf = out[:-4] + ".part%d.mp3" % k
        tts(t, voice, seed, pf, model, settings)
        files.append(pf)
    lst = out[:-4] + ".parts.txt"
    open(lst, "w").write("".join("file '%s'\n" % os.path.abspath(x) for x in files))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)


def stt(path):
    import uuid
    b = "----" + uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="model_id"\r\n\r\nscribe_v1\r\n'.encode(),
             f'--{b}\r\nContent-Disposition: form-data; name="timestamps_granularity"\r\n\r\nword\r\n'.encode(),
             f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
             + open(path, "rb").read() + b"\r\n", f"--{b}--\r\n".encode()]
    r = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=b"".join(parts),
                               headers={"xi-api-key": key("ELEVENLABS_API_KEY"), "Content-Type": "multipart/form-data; boundary=" + b})
    d = json.load(urllib.request.urlopen(r, timeout=300))
    return [{"w": w["text"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in d["words"] if w.get("type") == "word"]


def main(n):
    sys.path.insert(0, HERE)
    import video_studio as SC
    B = SC.bdir(n)
    # the narrator is the voice set for the people on screen (voices.py; rule 2026-11-12): a copied or recast production
    # never keeps the voice it came with. A face with no voice set refuses here, before anything is read.
    import voices as VO
    for line in VO.apply(n):
        if line.startswith("narrator"):
            print(line, flush=True)
    reads = json.load(open(os.path.join(B, "voice", "reads.json")))
    brief = json.load(open(os.path.join(B, "brief.json")))
    order = [s for s in brief["order"] if s in reads["lines"]]
    sent = [reads["lines"][s]["sent"] for s in order]
    text = " ".join(sent)
    out = os.path.join(B, "voice", "continuous")
    os.makedirs(out, exist_ok=True)
    best = None
    for seed in (1, 2, 3):
        f = os.path.join(out, f"body-r{seed}.mp3")
        said = f[:-4] + ".txt"           # the words this read says: a read is reused only for the same words
        # a read is reused only for the same words IN THE SAME VOICE (20 Nov: four ads kept another voice's read
        # after the narrator changed, because only the words were compared)
        key = text + "\n#voice:" + str(reads["voice_id"]) + "#model:" + str(reads.get("model") or "eleven_v3")
        if not os.path.exists(f) or not os.path.exists(said) or open(said).read() != key:
            tts_long(sent, reads["voice_id"], seed, f, reads.get("model") or "eleven_v3", reads.get("settings"))
            open(said, "w").write(key)
        words = stt(f)
        heard = [re.sub(r"[^a-z0-9$]", "", w["w"].lower()) for w in words]
        match = difflib.SequenceMatcher(None, toks(text), heard).ratio()
        gaps = [words[i + 1]["start"] - words[i]["end"] for i in range(len(words) - 1)]
        long_gaps = sum(1 for g in gaps if g > 0.7)
        score = match - 0.02 * long_gaps
        print(f"r{seed}: match {match:.3f}, pauses over 0.7 s: {long_gaps}, {words[-1]['end']:.1f} s")
        if not best or score > best[0]:
            best = (score, seed, f, words, match)
        if match >= 0.95 and long_gaps == 0:
            break                        # a clean first read is kept: no paid second or third read (owner, 20 Nov)
    _, seed, f, words, match = best
    heard = [re.sub(r"[^a-z0-9$]", "", w["w"].lower()) for w in words]
    # where each scene's first word landed in the read
    starts, i = [], 0
    sm = difflib.SequenceMatcher(None, toks(text), heard)
    pos = {}
    for a, b2, size in sm.get_matching_blocks():
        for k in range(size):
            pos[a + k] = b2 + k
    for s, line in zip(order, sent):
        k = i
        while k not in pos:
            k += 1
        starts.append(pos[k] - (k - i) if pos[k] - (k - i) >= 0 else pos[k])
        i += len(toks(line))
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                 capture_output=True, text=True).stdout)
    meta = {"voice_id": reads["voice_id"], "model": reads.get("model") or "eleven_v3", "seed": seed, "match": round(match, 3), "file": os.path.basename(f),
            "text": text, "scenes": {}}
    for j, s in enumerate(order):
        a = max(0.0, words[starts[j]]["start"] - LEAD) if j else 0.0
        b2 = words[starts[j + 1]]["start"] - LEAD if j + 1 < len(order) else total
        ws = [dict(w, start=round(w["start"] - a, 3), end=round(w["end"] - a, 3)) for w in words[starts[j]:(starts[j + 1] if j + 1 < len(order) else None)]]
        sf = os.path.join(out, f"{s}.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-ss", f"{a:.3f}", "-to", f"{b2:.3f}", "-c:a", "libmp3lame", "-q:a", "2", sf], check=True)
        json.dump({"scene": s, "from": meta["file"], "at": [round(a, 3), round(b2, 3)], "words": ws}, open(os.path.join(out, f"{s}.words.json"), "w"), indent=1)
        meta["scenes"][s] = {"at": [round(a, 3), round(b2, 3)], "first": ws[0]["w"], "last": ws[-1]["w"]}
        print(f"{s}: {a:6.2f}–{b2:6.2f}  {ws[0]['w']} … {ws[-1]['w']}")
    json.dump(meta, open(os.path.join(out, "body.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "0322")
