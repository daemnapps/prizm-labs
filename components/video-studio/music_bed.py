"""The music bed for a brief, made the video line's way (components/video-edit/machine/music_bed.py on the team repo):
ElevenLabs Music v2.5 (the ruled door), instrumental, built to the swipe's sound notes, under the narrator only.

  python3 music_bed.py <brief>        writes briefs/<brief>/music/bed.mp3 and bed.json (the request, kept with the file)
  python3 music_bed.py <brief> <lane> [<lane> ...]
                                      one bed per lane of the brief's music plan, its sections timed to the scenes:
                                      briefs/<brief>/music/beds/<lane>.mp3 + .json, for the owner to pick by ear
  python3 music_bed.py <brief> --use <lane>
                                      the picked lane becomes the brief's bed (bed.mp3 + bed.json), which the edit lays in

The music plan (briefs/<brief>/music/plan.json, else suno-plan.json) is data: "lanes" {lane: {style, exclude}} and
"sections" [{"scene": "<scene id>", "does": "what the music does from that scene's start"}]. A section runs from its
scene's start (the edit's layout) to the next section's; the first starts the bed, the last runs to the end plus 1 s.
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


def _plan(n):
    m = os.path.join(SC.bdir(n), "music")
    for f in ("plan.json", "suno-plan.json"):
        if os.path.isfile(os.path.join(m, f)):
            return json.load(open(os.path.join(m, f)))
    sys.exit("no music plan for this brief: write " + os.path.join(m, "plan.json"))


def lane_bed(n, lane):
    """One bed in one lane, its sections cut to the scenes (the drop lands on the scene that names the product, etc.)."""
    plan = _plan(n)
    L = plan["lanes"][lane]
    lay = json.load(open(os.path.join(SC.bdir(n), "studio-build", "layout.json")))
    starts = {s["scene"]: s["start"] for s in lay["scenes"]}
    secs = plan["sections"]
    edges = [starts[x["scene"]] for x in secs] + [lay["length"] + 1.0]
    neg = [x.strip() for x in L.get("exclude", "").split(",") if x.strip()]
    chunks = [{"text": "", "duration_ms": int(round((edges[i + 1] - edges[i]) * 1000)),
               "positive_styles": [L["style"], "instrumental", x["does"]], "negative_styles": neg} for i, x in enumerate(secs)]
    req = {"model_id": "music_v2_5", "seed": int(L.get("seed", 1)),     # a lane's own seed: another take of the same lane
           "composition_plan": {"positive_global_styles": [], "negative_global_styles": [], "chunks": chunks}}
    out = os.path.join(SC.bdir(n), "music", "beds")
    os.makedirs(out, exist_ok=True)
    body, dest = os.path.join(out, lane + ".req.json"), os.path.join(out, lane + ".mp3")
    json.dump(req, open(body, "w"))
    r = subprocess.run(["curl", "-s", "-o", dest, "-w", "%{http_code}", "-X", "POST", URL, "-H", "@-",
                        "-H", "Content-Type: application/json", "--data-binary", f"@{body}"],
                       input=f"xi-api-key: {VC.key('ELEVENLABS_API_KEY')}\n", capture_output=True, text=True, timeout=900)
    os.remove(body)
    if r.stdout.strip() != "200":
        raise SystemExit(lane + ": ElevenLabs said " + r.stdout.strip() + ": " + open(dest, errors="ignore").read()[:300])
    json.dump({"request": req, "lane": lane, "starts_at": round(edges[0], 3), "duck_db": -19,
               "sections": [dict(x, at=round(edges[i] - edges[0], 3)) for i, x in enumerate(secs)],
               "from": "ElevenLabs Music, one lane of the brief's music plan, sections on the scene starts"},
              open(os.path.join(out, lane + ".json"), "w"), indent=1)
    print(lane, round(SC.probe_dur(dest), 2), "s, starts at", round(edges[0], 3))


def use(n, lane):
    import shutil
    m = os.path.join(SC.bdir(n), "music")
    shutil.copy(os.path.join(m, "beds", lane + ".mp3"), os.path.join(m, "bed.mp3"))
    j = json.load(open(os.path.join(m, "beds", lane + ".json")))
    lay = json.load(open(os.path.join(SC.bdir(n), "studio-build", "layout.json")))   # the edit as it is now (the hook may have changed length)
    at = {s["scene"]: s["start"] for s in lay["scenes"]}
    j["starts_at"] = round(at[j["sections"][0]["scene"]], 3)
    # the bed's level, section by section: ducked under the voice (duck_db), and a section's own `level_db` on top of
    # that (a stop under the doubt line: the music drops away to the frame, then slams back on the next section)
    plan = {x["scene"]: x for x in _plan(n)["sections"]}
    secs = [dict(x, at=round(at[x["scene"]] - j["starts_at"], 3)) for x in j["sections"]]
    md = SC.probe_dur(os.path.join(m, "bed.mp3"))
    pts = [{"t": 0, "v": 0}]
    for i, x in enumerate(secs):
        v = round(10 ** ((j.get("duck_db", -19) + float(plan.get(x["scene"], {}).get("level_db", 0))) / 20), 4)
        t0 = 0.25 if i == 0 else x["at"]
        if i:
            pts.append({"t": round(t0 - 0.04, 3), "v": pts[-1]["v"]})
        pts.append({"t": round(t0, 3), "v": v})
    pts += [{"t": round(md - 1.5, 3), "v": pts[-1]["v"]}, {"t": round(md, 3), "v": 0}]
    j["sections"], j["duck_points"] = secs, pts
    json.dump(j, open(os.path.join(m, "bed.json"), "w"), indent=1)
    print("bed:", lane)


if __name__ == "__main__":
    a = sys.argv[1:] or sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001")
    if len(a) == 1:
        main(a[0])
    elif a[1] == "--use":
        use(a[0], a[2])
    else:
        for ln in a[1:]:
            lane_bed(a[0], ln)
