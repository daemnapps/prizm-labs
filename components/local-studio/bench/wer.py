"""WER of each local Whisper transcript against the corrected Carousel lyrics (song/teardown/transcript.json),
next to ElevenLabs Scribe's own first pass ('scribe_heard') on the same song."""
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
T = json.load(open(REPO / "productions/music-video/song/teardown/transcript.json"))
norm = lambda s: re.sub(r"[^a-z' ]", " ", s.lower()).split()
def wer(r, h):
    d = list(range(len(h) + 1))
    for i, a in enumerate(r, 1):
        p = d[:]; d[0] = i
        for j, b in enumerate(h, 1):
            d[j] = min(p[j] + 1, d[j - 1] + 1, p[j - 1] + (a != b))
    return d[-1] / len(r)
ref = [w for t in T for w in norm(t["text"])]
res = {"reference_words": len(ref), "ElevenLabs Scribe v2 (cloud, first pass)": round(wer(ref, [w for t in T for w in norm(t.get("scribe_heard") or "")]), 3)}
for f in sorted((REPO / "tools/local/samples/stt-carousel-song").glob("*.json")):
    segs = json.load(open(f))["segments"]
    res[f.stem] = round(wer(ref, [w for s in segs for w in norm(s["text"])]), 3)
print(json.dumps(res, indent=1))
