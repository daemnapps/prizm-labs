"""Open a brief's Video Studio in HyperFrames Studio, on the editing board's lanes.

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
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
AIW = Path(os.environ.get("VIDEO_STUDIO_AIW") or HERE.parents[3])     # the workspace this component sits in
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves
import settings as ST  # noqa: E402
MACHINE = ST.part("video-edit", AIW) / "machine"
sys.path.insert(0, str(MACHINE))
import video_studio as SC  # noqa: E402
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


def sound_layers(plan, m0, md, end, who):
    """The bed's marks and the ad's sound effects, each on its own row (owner, 12 Nov: music and every effect are laid
    and named in the edit, never mixed into the bed). plan is music/bed.json: its "cue_sheet" [{"at", "until", "what"}]
    names the Song row's stretches (the drop, the hit, the stop); its "effects" [{"at", "sound", "what", "file",
    "volume_db"}] become Sound effects rows, timed on the ad's clock from the bed's start m0. Returns (marks, sfx)."""
    marks, sfx = [], []
    cues = [c for c in plan.get("cue_sheet") or [] if c.get("at") is not None and float(c["at"]) < md]
    for k, c in enumerate(cues):
        until = min(float(c.get("until") or md), md)
        marks.append({"id": f"song-cue-{k + 1}", "track": BL.TRACK["song"], "row": "Song",
                      "start": round(m0 + float(c["at"]), 3), "duration": round(until - float(c["at"]), 3),
                      "label": f"Music · {who} · {plan.get('lane', 'bed')} · {c.get('what', '')}"})
    if not cues:
        marks.append({"id": "song-bed", "track": BL.TRACK["song"], "row": "Song", "start": round(m0, 3), "duration": md,
                      "label": f"Music bed · {who} · {plan.get('lane','bed')} · drop {plan.get('drop_at', '-')} s · hit {plan.get('hit_at', '-')} s"})
    for k, e in enumerate(plan.get("effects") or []):
        if e.get("file") and os.path.isfile(e["file"]) and e.get("at") is not None and m0 + float(e["at"]) < end:
            sfx.append({"id": f"sfx-{k + 1}", "at": round(m0 + float(e["at"]), 3), "src": e["file"],
                        "label": f"Effect · {e.get('sound', 'effect')} · {e.get('what', '')}",
                        "volume_db": float(e.get("volume_db", -8))})
    return marks, sfx


REPLY_ZONES = ("upper-third", "top-headline", "lower-third", "center")   # inside the safe zones (looks/placement.json)


def reply_zone(pic):
    """The safe zone where the comment sticker covers the faces least over the whole video (owner, 17 Nov: "did you
    make sure the subjects are also in the safe zone"): every made clip's faces tracked on the final clock (the team's
    faces.py), each candidate zone scored by how much face it would cover, the least taken. No tracker: upper-third."""
    try:
        import faces as FA
        import placement as PL
        sub = {"meta": {"width": 1080, "height": 1920}, "picture": [dict(p_, kind=None) for p_ in pic if not p_.get("still")]}
        FA.attach(sub, Path("/"), fps=2.0)
        boxes = [b for p_ in sub["picture"] for b in p_.get("face_track") or []]
        zones = {z["id"]: z for z in json.load(open(Path(PL.__file__).resolve().parent.parent / "looks" / "placement.json"))["zones"]}
    except Exception as e:  # noqa: BLE001 - no face tracker here: the sticker's own zone
        print("reply zone: faces not tracked:", type(e).__name__, str(e)[:100])
        return "upper-third"
    def covered(z):
        return sum(max(0.0, min(z["x"] + z["w"], b["x"] + b["w"]) - max(z["x"], b["x"])) *
                   max(0.0, min(z["y"] + z["h"], b["y"] + b["h"]) - max(z["y"], b["y"])) for b in boxes)
    best = min((z for z in REPLY_ZONES if z in zones), key=lambda z: covered(zones[z]))
    print("reply zone:", best, {z: round(covered(zones[z])) for z in REPLY_ZONES if z in zones})
    return best


def build(n, hook=None, variant=None):
    """hook: a hook scene id (H1..) played before the ad; its version is written under versions/<hook>/.
    variant: a brief.json "variants" id, the same ad cut from other footage: its own take of every scene (and of each
    hook), written under versions/<variant>/ or versions/<variant>-<hook>/."""
    st = SC.brief_state(n)
    root = SC.bdir(n)
    var = (st["brief"].get("variants") or {}).get(variant) if variant else None
    if var:
        b2 = dict(st["brief"], picks=dict(st["brief"]["picks"], **var["picks"]))
        st["brief"] = b2
        st["scenes"] = [SC.scene_state(n, x["scene"], b2) for x in st["scenes"]]
    if hook:
        hs = SC.scene_state(n, hook, st["brief"])
        rep = hs["workflow"].get("replaces")          # a hook that is the opening itself, changed, takes that scene's place
        rep_d = next((est(x)[0] for x in st["scenes"] if x["scene"] == rep), 0.0) if rep else 0.0
        st["scenes"] = [hs] + [x for x in st["scenes"] if x["scene"] != rep]
    vid = "-".join(x for x in (variant, hook) if x)
    base = Path(root) / "versions" / vid if vid else Path(root)
    out = base / "studio-build"
    out.mkdir(parents=True, exist_ok=True)
    row = {c: (name, t) for c, name, t in BL.LANES}
    pic, marks, ovs, at = [], [], [], 0.0
    times = []
    # the caption look, when the production names one (brief.json "captions": {"look": a looks/bank.json id or a look
    # copied from its swipe, "skip": [scenes that keep their plain lines]}): word by word, every word on its spoken time,
    # drawn by the team's compose. Without it, each scene's lines go in as plain labels (CAPTION_LOOK).
    capset = dict(st["brief"].get("captions") or {})
    if not capset.get("look"):          # the brand's standard caption style (brands/<brand>/brand-identity/edit-style.json)
        brand = (st["brief"].get("shot_fill") or {}).get("brand") or str(st["brief"].get("brief") or "").split("_")[0].split("-")[0]
        es = ST.REPO / "brands" / brand / "brand-identity" / "edit-style.json"
        if es.is_file():
            style = json.load(open(es)).get("captions") or {}
            capset = dict(style, **{k: v for k, v in capset.items() if v})
        else:
            print("NO CAPTION STYLE: brand %s has no brand-identity/edit-style.json and the brief names no captions.look" % brand)
    cap_words, cap_skip = [], set(capset.get("skip") or [])
    for sc in st["scenes"]:
        wf, s = sc["workflow"], sc["scene"]
        d, why = est(sc)
        code = wf.get("roll") or "B"
        name, track = row.get(code) or row["B"]     # a roll with no lane of its own (e.g. "S" screen) plays as B-roll
        label = f"{s} · {wf['title']}"
        if sc["status"] == "made":
            src = os.path.join(root, "scenes", s, sc["run"]["files"]["video"])
            pic.append({"id": s, "roll": "a", "kind": None, "src": src, "start": math.floor(at * 1000) / 1000, "duration": round(d + 0.002, 3),   # start rounded down, 2 ms overlap: no sample ever falls between two clips
                        "source_start": 0, "scene": s, "still": False, "volume_db": 0, "why": f"{s}: made on the Video Studio, {sc['pick']}",
                        "drift": False, "track": track, "row": name, "label": label + f" · {sc['pick']}"})
            cp = os.path.join(root, "scenes", s, sc["run"]["files"]["captions"])
            lag = RENDER_LAG
            clines = json.load(open(cp)).get("lines") or []
            if capset.get("look") and s not in cap_skip and clines and all(ln.get("words") for ln in clines):
                sung = os.path.exists(os.path.join(root, "song-cut.json"))   # a song: each lyric line is one caption
                for li, line in enumerate(clines):
                    for w in line["words"]:
                        a, b = snap(w["start"], lag), snap(w["end"], lag)
                        cap_words.append(dict({"text": w["text"], "start": math.floor((at + a) * 1000) / 1000,
                                               "end": math.floor((at + b) * 1000) / 1000},
                                              **({"line": "%s:%d" % (s, li)} if sung else {})))
                clines = []
            for i, line in enumerate(clines):
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
    sfx = []
    bed = Path(root) / "music" / "bed.mp3"
    bj = Path(root) / "music" / "bed.json"
    plan = json.load(open(bj)) if bj.exists() else {}
    sung = Path(root) / "song-cut.json"
    song = None
    if sung.exists():                  # a sung ad: the song IS the soundtrack, from the first frame at full level
        rel = (json.load(open(sung)).get("song") or "")
        # song-cut.json names the song from the writing workspace (video_studio._ws); a deployed Studio copy has no
        # runs of its own, so that workspace is read first, then this checkout (2026-11-20)
        cands = [Path(rel)] if rel and os.path.isabs(rel) else \
            [r / rel for r in (SC._ws(), Path(__file__).resolve().parents[4])] if rel else []
        song = next((c for c in cands if c.is_file()), None)
    if song:
        # a hook version: the hook carries its own slice of the song, so the song starts where the body starts, and
        # past the scene the hook replaces (2026-11-20, a sung ad's hooks played over the song's own opening line)
        m0 = times[0]["end"] if hook else 0.0
        src0 = rep_d if hook else 0.0
        md = round(min(SC.probe_dur(str(song)) - src0, end - m0), 3)
        music = {"src": str(song), "start": round(m0, 3), "duration": md, "label": "Song · the sung track (Suno)",
                 "duck": {"points": [{"t": 0, "v": 1.0}, {"t": md, "v": 1.0}]}}
        if src0:
            music["source_start"] = round(src0, 3)
        marks.append({"id": "song-sung", "track": BL.TRACK["song"], "row": "Song", "start": round(m0, 3), "duration": md,
                      "label": "Song · the sung track, every scene laid on its line"})
    elif bed.exists():                 # the bed, at the level its plan says (under the interview, under the narrator)
        s1 = next((t["start"] for t in times if t["scene"] == "S1"), 0.0)   # the bed follows the ad, after any hook
        m0 = s1 + float(plan.get("starts_at", times[1]["start"] if len(times) > 1 else 0.0))
        md = round(min(SC.probe_dur(str(bed)), end - m0), 3)
        v = round(10 ** (-19 / 20), 4)
        pts = plan.get("duck_points") or [{"t": 0, "v": 0}, {"t": 0.25, "v": v}, {"t": round(md - 1.5, 3), "v": v}, {"t": md, "v": 0}]
        pts = [p for p in pts if p["t"] <= md] + ([{"t": md, "v": 0}] if pts[-1]["t"] > md else [])
        who = "Suno" if plan.get("source") == "suno" else "ElevenLabs Music"
        music = {"src": str(bed), "start": round(m0, 3), "duration": md, "label": f"Song · music bed ({who})", "duck": {"points": pts}}
        song_marks, sfx = sound_layers(plan, m0, md, end, who)
        marks += song_marks
    else:
        marks.append({"id": "song-none", "track": BL.TRACK["song"], "row": "Song", "start": 0, "duration": end,
                      "label": "none in this brief (a cleared music bed after S1 if one is available)"})
    cap_zones = {}
    if cap_words:   # off the faces: the team's face tracker and placement give each captioned scene its free height
        import faces as FA
        import placement as PL
        sub = {"meta": {"width": 1080, "height": 1920}, "controls": {},
               "picture": [dict(p, kind=None) for p in pic if not p["still"] and p["scene"] not in cap_skip],
               "captions": {"look": capset["look"], "words": cap_words}, "overlays": [],
               # words already burned into the picture (a production's pinned banners): placement keeps captions off them
               "keep_clear": [dict(k, end=k.get("end", 1e9)) for k in capset.get("keep_clear") or []]}
        try:
            FA.attach(sub, Path("/"))
        except Exception as e:                              # no tracker: the look's own height stands
            print("faces not tracked:", type(e).__name__, str(e)[:120])
        PL.place(sub)
        cap_zones = sub["captions"].get("zones") or {}
        for sc, z in (capset.get("zones") or {}).items():   # a scene the production places by hand (brief.json captions.zones)
            cap_zones[sc] = z
    # THE COMMENT REPLY AND THE OFFER (owner, 17 Nov 2026: "the comment needs to be present throughout the entire video
    # and we need an offer text on the end of it … also safe zones need to be applied"). The reply sticker runs from
    # the first frame to the last (brief.json "reply": the control's comment, and each hook version's own); the end card
    # carries the brief's own offer lines and CTA over the product's real packshot. Every layer sits in a named zone of
    # video-edit looks/placement.json, inside the platform safe zones (defaults.json safe_zones).
    layers = {"platform_ui": [], "pictures": []}
    reply = st["brief"].get("reply") or {}
    rtext = reply.get(hook) or reply.get("control")
    if rtext:
        layers["platform_ui"].append({"id": "reply", "kind": "comment_reply", "style": "tiktok-reply-white", "text": rtext,
                                      "handle": "", "start": 0.0, "duration": end, "zone": reply_zone(pic)})
    off = st["brief"].get("offer_card") or {}
    endt = next((t_ for t_ in times if t_["scene"] == off.get("scene")), None)
    if off and endt:
        a_, d_ = endt["start"], round(endt["end"] - endt["start"], 3)
        for j, (txt, y) in enumerate(zip(off.get("lines") or [], (20, 26))):
            ovs.append({"id": "offer-%d" % j, "kind": "label", "text": txt, "label": "offer · " + txt[:40], "start": round(a_ + 0.1 + j * 0.15, 3),
                        "duration": round(d_ - 0.1 - j * 0.15, 3), "track": row["C"][1], "row": "Cards", "entrance": "pop",
                        "text_look": LK.text_look("headline", "headline-white-box"), "look_id": "headline-white-box", "y_pct": y})
        if off.get("cta"):
            ovs.append({"id": "offer-cta", "kind": "label", "text": off["cta"], "label": "CTA · " + off["cta"][:40], "start": round(a_ + 0.5, 3),
                        "duration": round(d_ - 0.5, 3), "track": row["C"][1], "row": "Cards", "entrance": "pop",
                        "text_look": LK.text_look("headline", "headline-white-box"), "look_id": "headline-white-box", "y_pct": 48})
        pk = off.get("packshot")
        pk = str(pk if not pk or os.path.isabs(pk) else ST.REPO / pk)      # stored repo-relative (builder card rule 4)
        if pk and os.path.isfile(pk):
            layers["pictures"].append({"id": "packshot", "src": pk, "start": round(a_ + 0.05, 3), "duration": d_,
                                       "x_pct": 50, "y_pct": 36, "w_pct": 34, "h_pct": 14, "pop": True})
    sheet = {"meta": {"brand": "brief", "label": st["brief"]["brief"], "format": "brief-layout",
                      "style_id": (lambda x: x.get("id") if isinstance(x, dict) else x)(st["brief"].get("style")),
                      "width": 1080, "height": 1920, "fps": 30, "made_by": "Video Studio", "brief": st["brief"]["brief"]},
             "controls": {"transition": {"value": "cut"}, "captions": {"value": "off"}},
             "voice": None, "voice_cuts": [], "music": music, "sfx": sfx,
             "picture": pic, "captions": {"look": capset.get("look") if cap_words else None, "words": cap_words, "zones": cap_zones,
                          "accent": capset.get("accent") or []},
             "overlays": ovs, "markers": marks, "layers": layers}
    for _try in (1, 2):                # the moves director's picks (edit_moves.py): one move per scene, laid here
        try:
            import edit_moves as EM
            EM.apply(Path(root), sheet)
            break
        except Exception as e:  # noqa: BLE001 — owner ruling 2026-11-20: retry then fail loudly
            if _try == 2:
                raise RuntimeError("edit moves not laid twice (%s: %s) — the build stops" % (type(e).__name__, str(e)[:160]))
    json.dump(sheet, open(out / "cutsheet.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"brief": st["brief"]["brief"], "length": end, "scenes": times}, open(out / "layout.json", "w"), indent=1)
    project = base / "studio"
    C.compose(sheet, Path("/"), project, captions=bool(cap_words))
    return project, times, end


if __name__ == "__main__":
    n = (sys.argv[1] if len(sys.argv) > 1 else sys.exit("name the brief, e.g. " + os.path.basename(__file__) + " 0001"))
    project, times, end = build(n)
    for r in times:
        print(f"{r['scene']:4} {r['start']:6.2f}–{r['end']:6.2f}s  {r['from']}")
    print("length", end, "s · project:", project)
