"""The music bed for a brief, made the video line's way (components/video-edit/machine/music_bed.py on the team repo):
ElevenLabs Music v2.5 (the ruled door), instrumental, built to the swipe's sound notes, under the narrator only.

  python3 music_bed.py <brief>        writes briefs/<brief>/music/bed.mp3 and bed.json (the request, kept with the file)
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import video_studio as SC  # noqa: E402
import voice_continuous as VC  # noqa: E402

URL = "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192"
BASE = ["instrumental", "sits under a voice", "continuous loop feel, no big changes"]
NEG = ["vocals", "singing", "lyrics", "choir", "spoken word", "drops", "build-ups", "EDM drop", "aggressive",
       "distorted", "orchestral", "cinematic trailer"]
# the swipe's sound notes (writing room draft, "LAYERS AND SOUND — carried from the swipe")
SWIPE = {"tempo_bpm": 123, "energy": "mid", "mood": "upbeat confident", "genre": "electronic",
         "enters": "on the cut after the interview hook", "ends": "quietly after the ask"}


def main(n):
    lay = json.load(open(os.path.join(SC.bdir(n), "studio-build", "layout.json")))
    start = next(s["start"] for s in lay["scenes"] if s["scene"] != "S1")
    seconds = lay["length"] - start + 1.0
    style = [f"{SWIPE['tempo_bpm']} BPM", f"{SWIPE['energy']} energy", SWIPE["mood"], SWIPE["genre"], "ends with a soft fade out"]
    req = {"model_id": "music_v2_5", "seed": 1, "composition_plan": {"positive_global_styles": [], "negative_global_styles": [],
           "chunks": [{"text": "", "duration_ms": int(seconds * 1000), "positive_styles": BASE + style, "negative_styles": NEG}]}}
    out = os.path.join(SC.bdir(n), "music")
    os.makedirs(out, exist_ok=True)
    body = os.path.join(out, "bed.req.json")
    json.dump(req, open(body, "w"))
    dest = os.path.join(out, "bed.mp3")
    r = subprocess.run(["curl", "-s", "-o", dest, "-w", "%{http_code}", "-X", "POST", URL, "-H", "@-",
                        "-H", "Content-Type: application/json", "--data-binary", f"@{body}"],
                       input=f"xi-api-key: {VC.key('ELEVENLABS_API_KEY')}\n", capture_output=True, text=True, timeout=900)
    os.remove(body)
    if r.stdout.strip() != "200":
        raise SystemExit("music: ElevenLabs said " + r.stdout.strip() + ": " + open(dest, errors="ignore").read()[:300])
    json.dump({"request": req, "swipe": SWIPE, "starts_at": round(start, 3), "duck_db": -19,
               "from": "video line: ElevenLabs Music, ducked about -19 dB under the voice, mix at -14 LUFS"},
              open(os.path.join(out, "bed.json"), "w"), indent=1)
    print("bed", round(SC.probe_dur(dest), 2), "s, starts at", round(start, 3))


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001")))
