#!/usr/bin/env python3
"""The motion read: a real reference clip and its track in, the moment as body mechanics out (stage 1 of the chain).

    python3 read.py <motion dir> --context <take.json | context.json> [--cuts 2.67,3.83] [--about "what the clip is"]

<motion dir> holds a tracked reference (motion.py: read.mp4, pose.json, camera.json). The model watches the clip
itself, twice. First it only says who is who (prompts/motion-who.md): which of our people each tracked person plays,
who is visible in each shot, how the camera is held. Then, with the track laid out under our own people's names
(measure.py) and our shot's context (what is happening, who, why), it answers with motion-read.json: per beat who starts, who answers and how late, each body's weight, torso, head, hands and eyes,
the contact, the distance, the timing in seconds, what the camera operator does, and the one measure that proves the
beat happened (what match.py checks a finished take against).

Every call is kept beside it: motion-who.sent.json / .answer.json and motion-read.sent.json / .answer.json (the prompt
exactly as sent, the clip's name, the model; the model's words). The model is the house's video judge (generative-model-house
`behind.judge`, then `behind.judge_busy`); keys by name, the company key then the backup. No brand, product or person
is named here.
"""
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import home as ST  # noqa: E402
import measure as ME  # noqa: E402

PROMPT = HERE / "prompts" / "motion-read.md"
WHO = HERE / "prompts" / "motion-who.md"
KEYS = ("GEMINI_API_KEY", "GEMINI_API_KEY_PERSONAL")
MEASURES = ("lean", "head", "knees", "hips", "hand_l", "hand_r", "turn", "near")


def models():
    first = ST.house_model("behind.judge", "gemini-3.1-pro-preview")
    busy = ST.house_model("behind.judge_busy") or {}
    return [first] + [m for m in (busy.get("models") or []) if m != first]


def context_words(ctx):
    """Our shot in words: a take.json (staging, cast, script, why) or a plain {"what", "people", "why"} context."""
    if ctx.get("script") is not None or ctx.get("staging"):
        cast = ctx.get("cast") or {}
        keep = {"what_happens": ctx.get("staging"), "why_this_shot": ctx.get("why"), "seconds": ctx.get("seconds"),
                "people": {n: (c.get("look") if isinstance(c, dict) else "") for n, c in cast.items()},
                "beats": [{k: ln[k] for k in ("do", "moves", "faces", "say", "speaker") if ln.get(k)} for ln in ctx.get("script") or []],
                "place": ctx.get("look")}
        return json.dumps({k: v for k, v in keep.items() if v}, indent=1, ensure_ascii=False)
    return json.dumps(ctx, indent=1, ensure_ascii=False)


def _seconds(clip):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def ask(text, clip, tried=None):
    """One answer from the first model and key that gives one: the clip goes in as it is, the prompt beside it."""
    tried = tried if tried is not None else []
    video = base64.b64encode(Path(clip).read_bytes()).decode()
    # movement is read at 8 pictures a second (a model's own default of one a second misses a lean, a duck, a recoil);
    # a long clip is read slower so it stays under about 160 pictures
    secs = _seconds(clip)
    fps = max(2, min(8, int(160 / secs))) if secs else 8
    body = {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "video/mp4", "data": video}, "video_metadata": {"fps": fps}},
                                                    {"text": text}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}}
    for model in models():
        for name in KEYS:
            key = ST.key(name)
            if not key:
                tried.append("%s: not in the key file" % name)
                continue
            url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
            for attempt in range(3):
                try:
                    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                               headers={"Content-Type": "application/json", "x-goog-api-key": key})
                    res = json.load(urllib.request.urlopen(r, timeout=600))
                    parts = res["candidates"][0]["content"]["parts"]
                    out = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                    return out, {"model": model, "account": name, "usage": res.get("usageMetadata") or {}, "tried": tried}
                except urllib.error.HTTPError as e:
                    if e.code in (500, 502, 503, 504) and attempt < 2:
                        time.sleep(8 * (attempt + 1))
                        continue
                    tried.append("%s on %s: %s %s" % (model, name, e.code, e.read()[:120].decode("utf8", "replace")))
                    break
                except (urllib.error.URLError, KeyError, IndexError, OSError) as e:
                    tried.append("%s on %s: %s" % (model, name, str(e)[:120]))
                    break
    raise SystemExit("no account could read the clip: " + " · ".join(tried))


def clean(got, names, seconds):
    """The answer held to its shape: beats in order inside the clip, people from our shot, checks on real measures.
    What was dropped is said, never silently kept."""
    dropped = []
    people = [p for p in got.get("people") or [] if p.get("ours")]
    known = set(names) or {p["ours"] for p in people}
    # who each tracked tag plays: the tag map is the record; each person's `reference` is read off it, in shot order
    tags = {str(t).upper(): n for t, n in (got.get("tags") or {}).items()}
    if tags:
        for p in people:
            p["reference"] = sorted((t for t, n in tags.items() if n == p["ours"]), key=lambda t: (int(t[1:] or 0) if t[1:].isdigit() else 0, t[0]))
        for t, n in tags.items():
            if n != "extra" and n not in {p["ours"] for p in people}:
                dropped.append({"tag": t, "why": "mapped to %s, who is not in our shot" % n})
    beats = []
    for b in sorted(got.get("beats") or [], key=lambda x: float(x.get("from") or 0)):
        try:
            f0 = max(0.0, min(seconds, float(b.get("from") or 0)))
            f1 = max(f0 + 0.1, min(seconds, float(b.get("to") or f0 + 1)))
        except (TypeError, ValueError):
            dropped.append({"beat": b.get("what"), "why": "no times"})
            continue
        b["from"], b["to"] = round(f0, 2), round(f1, 2)
        c = b.get("check") or {}
        if c.get("measure") not in MEASURES or c.get("who") not in known:
            if c:
                dropped.append({"beat": b.get("what"), "why": "its check names a measure or person the track does not have", "check": c})
            b["check"] = None
        else:
            try:
                c["by"] = abs(float(c.get("by") or 0))
                c["half_done_at"] = float(c.get("half_done_at") if c.get("half_done_at") is not None else (f0 + f1) / 2)
            except (TypeError, ValueError):
                b["check"] = None
        beats.append(b)
    cam = got.get("camera") or {}
    return {"moment": got.get("moment", ""), "tags": tags, "people": people, "beats": beats, "camera": cam,
            "fake_risks": got.get("fake_risks") or [], "missing": got.get("missing") or [], "dropped": dropped}


def ground(rec, tr, tags):
    """Every beat's check held to the track: the direction and size of the move are read off that person's own track
    inside the beat, not taken on the model's word. A measure that does not really move there gives way to the one that
    does; a beat in which nothing of that person moves past its floor is a hold and carries no check."""
    for b in rec["beats"]:
        c = b.get("check")
        if not c:
            continue
        # inside the shot the beat sits in: a jump across a cut is not a move
        mid = (b["from"] + b["to"]) / 2
        S = next((S for S in tr if S["from"] <= mid < S["to"]), None)
        mine = sorted((ME.by_name(S, tags).get(c["who"]) or {}).get("rows") or [], key=lambda r: r["t"]) if S else []
        a0, b0 = max(b["from"] - 0.2, S["from"] if S else 0), min(b["to"] + 0.2, (S["to"] - 0.01) if S else b["to"])
        got = ME.change(mine, c["measure"], a0, b0)
        if not got or abs(got["delta"]) < 0.6 * ME.FLOOR[c["measure"]]:
            ev = [e for e in ME.events(mine, a0, b0) if e["measure"] in MEASURES]
            if not ev:
                rec["dropped"].append({"beat": b.get("what"), "why": "nothing of %s's moves past its floor in the track here: a hold" % c["who"], "check": c})
                b["check"] = None
                continue
            got, c["measure"] = ev[0], ev[0]["measure"]
        c.update({"moves": "up" if got["delta"] > 0 else "down", "by": round(abs(got["delta"]), 2), "half_done_at": got["at"], "from_track": True})


def _json(answer, what):
    try:
        return json.loads(answer)
    except ValueError:
        raise SystemExit("%s came back with no JSON: %s" % (what, answer[:300]))


def read(motion_dir, ctx, cuts=None, about=None):
    """Two looks at the same clip: who is who (prompts/motion-who.md), then the moment as body mechanics with the track
    laid out under our own people's names (prompts/motion-read.md). A person's correction of who is who (who.json)
    wins over the first look before the second is asked."""
    d = Path(motion_dir)
    clip = d / "read.mp4"
    if not clip.exists() or not (d / "pose.json").exists():
        raise SystemExit("no tracked reference here (%s): track it first (motion.py track)" % d)
    pose, tr, cam = ME.load(d, cuts)
    seconds = round(pose["frames"][-1]["t"] + 1.0 / (pose.get("fps") or 16), 2) if pose["frames"] else 0.0
    # the clip the model watches carries each tracked person's box and tag, so who is who is seen, not guessed
    import motion as MO
    r = subprocess.run([MO.reader_python(), str(HERE / "measure.py"), "_label", str(d)] + (["--cuts", ",".join(str(c) for c in cuts)] if cuts else []),
                       capture_output=True, text=True)
    labelled = d / "labelled.mp4"
    watch = labelled if r.returncode == 0 and labelled.exists() else clip
    ref = about or "It runs %.1f seconds%s." % (seconds, (" and has %d shots (cuts at %s s)" % (
        len(tr), ", ".join("%.2f" % s["from"] for s in tr[1:]))) if len(tr) > 1 else " in one shot")
    names = [n for n in (list((ctx.get("cast") or {}).keys()) or [p.get("name") for p in ctx.get("people") or [] if isinstance(p, dict)]) if n]
    t0 = time.time()
    # 1. who is who
    who_text = WHO.read_text().replace("{context}", context_words(ctx)).replace("{reference}", ref).replace("{tags}", ME.tag_list(tr))
    (d / "motion-who.sent.json").write_text(json.dumps({"prompt": who_text, "clip": watch.name, "models": models(),
                                                         "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1, ensure_ascii=False))
    answer, how_who = ask(who_text, watch)
    (d / "motion-who.answer.json").write_text(json.dumps({"answer": answer, "by": how_who}, indent=1, ensure_ascii=False))
    got_who = _json(answer, "who is who")
    have = {"%s%d" % (letter, S["shot"]) for S in tr for letter in S["people"]}
    tags = {str(t).upper(): n for t, n in (got_who.get("tags") or {}).items() if str(t).upper() in have and (n == "extra" or not names or n in names)}
    try:                                                 # a person's correction wins before the mechanics are read
        fixed = {str(k).upper(): v for k, v in json.loads((d / "who.json").read_text()).items() if not str(k).startswith("_")}
    except (OSError, ValueError):
        fixed = {}
    tags.update({t: n for t, n in fixed.items() if t in have})
    held = "; ".join("shot %s: %s" % (k, v) for k, v in sorted((got_who.get("held") or {}).items())) or "not said"
    # 2. the moment as body mechanics, the track under our names
    track = ME.table(tr, cam, who=tags)
    text = PROMPT.read_text().replace("{context}", context_words(ctx)).replace("{reference}", ref).replace("{track}", track).replace("{held}", held)
    (d / "motion-read.sent.json").write_text(json.dumps({"prompt": text, "clip": watch.name, "models": models(),
                                                          "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1, ensure_ascii=False))
    answer, how = ask(text, watch)
    (d / "motion-read.answer.json").write_text(json.dumps({"answer": answer, "by": how}, indent=1, ensure_ascii=False))
    got = _json(answer, "the motion read")
    got["tags"] = tags
    rec = clean(got, names, seconds)
    ground(rec, tr, tags)
    for n in names:                                      # everyone in our shot is on the list, followed or not
        if n not in {p["ours"] for p in rec["people"]}:
            rec["people"].append({"ours": n, "role": "stands by", "reference": sorted(t for t, v in tags.items() if v == n)})
    visible = {str(k): [n for n in v if not names or n in names] for k, v in (got_who.get("visible") or {}).items()}
    rec.update({"seconds": seconds, "visible": visible, "held": got_who.get("held") or {}, "why": got_who.get("why") or {},
                "shots": [{"shot": s["shot"], "from": s["from"], "to": s["to"], "people": list(s["people"])} for s in tr],
                "camera_track": [{k: c[k] for k in ("shot", "from", "to", "pan", "tilt", "push", "roll", "shake", "punch", "edit_zoom", "words")} for c in cam],
                "model": how["model"], "account": how["account"], "seconds_to_read": round(time.time() - t0, 1),
                "read_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    (d / "motion-read.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or "--context" not in a:
        sys.exit(__doc__)
    cuts = [float(x) for x in a[a.index("--cuts") + 1].split(",") if x] if "--cuts" in a else None
    rec = read(a[0], json.loads(Path(a[a.index("--context") + 1]).read_text()), cuts,
               a[a.index("--about") + 1] if "--about" in a else None)
    print(json.dumps({k: rec[k] for k in ("moment", "people", "model", "seconds_to_read")}, indent=1, ensure_ascii=False))
    print("%d beats, %d dropped" % (len(rec["beats"]), len(rec["dropped"])))
