"""Open a brief's scene canvas in HyperFrames Studio, on the editing board's lanes.

  python3 to_studio.py <brief>          writes briefs/<brief>/studio/ (a HyperFrames project) and prints how to open it

Made scenes go in as their real files at their place in the cut; scenes still waiting are the editing board's labelled
slot frames, sized by an estimate (spoken words at 2.7 a second, 2.5 s if silent) and named as estimates. Every
lane is there in the editing board's order: A-roll, B-roll, Greenscreen, Cards, End card, Captions, Song, Voice.
Uses the team's own layout and compose code from a read-only copy (see AIW below); nothing in it is changed.
"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIW = Path(os.environ.get("SCENE_CANVAS_AIW") or HERE.parents[1])     # the workspace this component sits in
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402
MACHINE = ST.part("video-edit", AIW) / "machine"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MACHINE))
import scene_canvas as SC  # noqa: E402
import brief_layout as BL  # noqa: E402  the editing board's lanes, tracks, slot frames
import compose as C  # noqa: E402
import looks as LK  # noqa: E402

CAPTION_LOOK = "headline-plain"  # the brief names no style; the editing board's default (TikTok text, lower)


FPS = 24000 / 1001


RENDER_LAG = 0   # renders at 24000/1001 (--fps); clip and caption starts are rounded down to the ms so each lands on its own frame (measured 8 Nov)



def _voice(root):
    """The narrator's name for the timeline label: the brief's own `voice_name`, else "the narrator"."""
    try:
        return json.load(open(os.path.join(root, "brief.json"))).get("voice_name") or "the narrator"
    except (OSError, ValueError):
        return "the narrator"

def snap(t, lag=None):
    lag = RENDER_LAG if lag is None else lag
    return round(round(t * FPS) / FPS + (lag if t > 0 else 0), 4)


def est(sc):
    if sc["status"] == "made":
        return round(int(sc["run"]["duration"] * FPS + 1e-6) / FPS, 6), "made"   # whole frames, rounded down (never past the clip's end), so every scene starts on the frame grid
    n = len((sc["workflow"].get("words") or "").split())
    return (round(n / 2.7, 2) if n else 2.5), "estimate until the voice read" if n else "estimate (silent beat)"


def build(n, hook=None):
    """hook: a hook scene id (H1..) played before the ad; its version is written under versions/<hook>/."""
    st = SC.brief_state(n)
    root = SC.bdir(n)
    if hook:
        hs = SC.scene_state(n, hook, st["brief"])
        rep = hs["workflow"].get("replaces")          # a hook that is the opening itself, changed, takes that scene's place
        st["scenes"] = [hs] + [x for x in st["scenes"] if x["scene"] != rep]
    base = Path(root) / "versions" / hook if hook else Path(root)
    out = base / "studio-build"
    out.mkdir(parents=True, exist_ok=True)
    row = {c: (name, t) for c, name, t in BL.LANES}
    pic, marks, ovs, at = [], [], [], 0.0
    times = []
    for sc in st["scenes"]:
        wf, s = sc["workflow"], sc["scene"]
        d, why = est(sc)
        code = wf.get("roll") or "B"
        name, track = row[code]
        label = f"{s} · {wf['title']}"
        if sc["status"] == "made":
            src = os.path.join(root, "scenes", s, sc["run"]["files"]["video"])
            pic.append({"id": s, "roll": "a", "kind": None, "src": src, "start": math.floor(at * 1000) / 1000, "duration": round(d + 0.002, 3),   # start rounded down, 2 ms overlap: no sample ever falls between two clips
                        "source_start": 0, "scene": s, "still": False, "volume_db": 0, "why": f"{s}: made on the scene canvas, {sc['pick']}",
                        "drift": False, "track": track, "row": name, "label": label + f" · {sc['pick']}"})
            cp = os.path.join(root, "scenes", s, sc["run"]["files"]["captions"])
            lag = RENDER_LAG
            for i, line in enumerate(json.load(open(cp)).get("lines") or []):
                a, b = snap(line["start"], lag), snap(line["end"], lag)   # on the picture's own frames, so a caption never changes a frame before a cut
                ovs.append({"id": f"{s}-c{i}", "kind": "label", "text": line["text"], "label": f"{s} {line['text']}",
                            "start": math.floor((at + a) * 1000) / 1000, "duration": round(b - a, 3),
                            "track": BL.TRACK["captions"], "row": "Captions", "entrance": "cut",
                            "text_look": LK.text_look("headline", CAPTION_LOOK), "look_id": CAPTION_LOOK, "y_pct": 62})
        else:
            fake = {"id": s, "kind": {"A": "talking", "B": "broll", "C": "card", "E": "endcard"}.get(code, "broll"),
                    "happens": f"{wf['title']} · waits: {', '.join(sc['waits'])}"}
            frame = BL.slot_frame(out, fake, {"start": at, "end": at + d})
            pic.append({"id": s, "roll": "a", "kind": None, "src": str(frame), "start": round(at, 3), "duration": d,
                        "source_start": 0, "scene": s, "still": True, "volume_db": None, "why": f"{s}: slot, {why}",
                        "drift": False, "track": track, "row": name, "label": f"{label} · waits: {', '.join(sc['waits'])}"})
        lp = sc["run"]["files"].get("layers") if sc["status"] == "made" else None
        if lp:                                 # offer cards: their own layer on the Cards lane, timed to their line
            for i, L in enumerate(json.load(open(os.path.join(root, "scenes", s, lp)))["layers"]):
                ovs.append({"id": f"{s}-{L['id']}", "kind": "label", "text": L["text"], "label": f"{s} offer · {L['text'][:40]}",
                            "start": round(at + L["start"], 3), "duration": round(L["end"] - L["start"], 3),
                            "track": row["C"][1], "row": "Cards", "entrance": "cut",
                            "text_look": LK.text_look("headline", "headline-white-box"), "look_id": "headline-white-box", "y_pct": 12})
        words = (wf.get("words") or "").strip()
        if words and s != "S1" and sc["status"] == "made" and (sc["run"].get("voice")):
            marks.append({"id": f"voice-{s}", "track": BL.TRACK["voice"], "row": "Voice", "start": round(at, 3),
                          "duration": d, "label": f"{s} {_voice(root)} (clone) · in the clip · {words}"})
        elif words and s != "S1":
            marks.append({"id": f"voice-{s}", "track": BL.TRACK["voice"], "row": "Voice", "start": round(at, 3),
                          "duration": d, "label": f"{s} {words}"})
        times.append({"scene": s, "start": round(at, 3), "end": round(at + d, 3), "from": why})
        at += d
    end = round(at, 3)
    marks.append({"id": "voice-s1", "track": BL.TRACK["voice"], "row": "Voice", "start": 0, "duration": times[0]["end"] - times[0]["start"],
                  "label": "S1 original voices (in the clip)"})
    used = {(sc["workflow"].get("roll") or "B") for sc in st["scenes"]}
    for code, name, track in BL.LANES:
        if code not in used:
            marks.append({"id": f"empty-{code}", "track": track, "row": name, "start": 0, "duration": end, "label": "none in this brief"})
    music = None
    bed = Path(root) / "music" / "bed.mp3"
    bj = Path(root) / "music" / "bed.json"
    plan = json.load(open(bj)) if bj.exists() else {}
    if bed.exists():                   # the bed, at the level its plan says (under the interview, under the narrator)
        s1 = next((t["start"] for t in times if t["scene"] == "S1"), 0.0)   # the bed follows the ad, after any hook
        m0 = s1 + float(plan.get("starts_at", times[1]["start"] if len(times) > 1 else 0.0))
        md = round(min(SC.probe_dur(str(bed)), end - m0), 3)
        v = round(10 ** (-19 / 20), 4)
        pts = plan.get("duck_points") or [{"t": 0, "v": 0}, {"t": 0.25, "v": v}, {"t": round(md - 1.5, 3), "v": v}, {"t": md, "v": 0}]
        pts = [p for p in pts if p["t"] <= md] + ([{"t": md, "v": 0}] if pts[-1]["t"] > md else [])
        who = "Suno" if plan.get("source") == "suno" else "ElevenLabs Music"
        music = {"src": str(bed), "start": round(m0, 3), "duration": md, "label": f"Song · music bed ({who})", "duck": {"points": pts}}
        marks.append({"id": "song-bed", "track": BL.TRACK["song"], "row": "Song", "start": round(m0, 3), "duration": md,
                      "label": f"Music bed · {who} · {plan.get('lane','bed')} · drop {plan.get('drop_at', '-')} s · hit {plan.get('hit_at', '-')} s"})
    else:
        marks.append({"id": "song-none", "track": BL.TRACK["song"], "row": "Song", "start": 0, "duration": end,
                      "label": "none in this brief (a cleared music bed after S1 if one is available)"})
    sheet = {"meta": {"brand": "brief", "label": st["brief"]["brief"], "format": "brief-layout", "style_id": None,
                      "width": 1080, "height": 1920, "fps": 30, "made_by": "scene canvas", "brief": st["brief"]["brief"]},
             "controls": {"transition": {"value": "cut"}, "captions": {"value": "off"}},
             "voice": None, "voice_cuts": [], "music": music, "sfx": [],
             "picture": pic, "captions": {"look": None, "words": []}, "overlays": ovs, "markers": marks}
    json.dump(sheet, open(out / "cutsheet.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"brief": st["brief"]["brief"], "length": end, "scenes": times}, open(out / "layout.json", "w"), indent=1)
    project = base / "studio"
    C.compose(sheet, Path("/"), project, captions=False)
    return project, times, end


if __name__ == "__main__":
    n = (sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001"))
    project, times, end = build(n)
    for r in times:
        print(f"{r['scene']:4} {r['start']:6.2f}–{r['end']:6.2f}s  {r['from']}")
    print("length", end, "s · project:", project)
