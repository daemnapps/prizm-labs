#!/usr/bin/env python3
"""Programmed motion: a scene's own take turned into stand-in figures in 3D, before any video model is paid for
(components/video-production/BRIEF-SPEC.md rule 7; ruled 2026-11-09: our own motion is the default).

    python3 motion_program.py <take.json> --out <dir> [--model opus|sonnet|gemini-3.1-pro-preview] [--no-render]
    python3 motion_program.py scene <scene dir>          the scene's take.json, programmed into <scene dir>/motion/
    python3 motion_program.py first-frame <scene dir> [look pictures...]   the start picture, made from the rehearsal's
                                                         first frame through the house picture door

1. The timeline: each line's window from its read's length (a line with no read: its words at 2.7 a second).
2. The blocking: the take (staging, cast, every line's `do`, `moves` and `camera`) and the timeline go to Claude, on
   the plan of whoever runs it (the `claude` command line, no metered key), with prompts/motion-program.md; it answers
   with people, beats and a camera in blocking_blender.py's words. A `gemini-*` model name sends it to Gemini instead.
3. The figures: Blender renders the stand-ins and writes their exact skeletons (no reading back from pictures).
4. The preview: skeleton.mp4 (OpenPose colours, what the pose route drives a take with), overlay.mp4, sheet.jpg,
   camera.json, motion.json. Programmed motion is ready as made; nobody has to approve it.

Every call is kept: sent.json (the prompt exactly as sent), answer.json (the model's words), spec.json (what was built).
Claude needs the `claude` command line signed in; Gemini reads GEMINI_API_KEY through the key loader. No brand,
product or person is named here.
"""
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import home as ST  # noqa: E402
import motion as MO  # noqa: E402

PROMPT = HERE / "prompts" / "motion-program.md"
MODEL = "opus"            # Claude, on the signed-in plan; a gemini-* name goes to Gemini
ACTIONS = ("walk", "walk_to", "reach", "mic", "turn", "lean", "nod", "shake", "tilt", "laugh", "squat", "sit", "cross_legs", "point", "look")


def timeline(take, gap=0.35, lead=0.5):
    """Each line's window: its read's length, one after another."""
    t, rows = lead, []
    for k, ln in enumerate(take.get("script") or []):
        n = MO.seconds_of(ln["read"]) if ln.get("read") and Path(ln["read"]).exists() else 0
        n = n or max(0.8, len(str(ln.get("say", "")).split()) / 2.7)
        rows.append({"line": k + 1, "speaker": ln.get("speaker"), "from": round(t, 2), "to": round(t + n, 2)})
        t += n + gap
    return rows, round(t + 0.6, 2)


def _take_words(take):
    keep = {k: take[k] for k in ("staging", "look", "camera") if take.get(k)}
    cast = take.get("cast") or {}
    keep["cast"] = {n: ({"look": c.get("look")} if isinstance(c, dict) else {}) for n, c in cast.items()}
    keep["script"] = [{k: ln[k] for k in ("speaker", "say", "do", "who", "action", "prop", "target", "where", "moves", "camera") if ln.get(k)}
                      for ln in take.get("script") or []]
    return json.dumps(keep, indent=1, ensure_ascii=False)


GEMINI_FALLBACK = "gemini-3.1-pro-preview"
GEMINI_KEYS = ("GEMINI_API_KEY", "GEMINI_API_KEY_PERSONAL")   # the company key, then the backup key


def ask(text, model=MODEL):
    """One answer from whichever account can give it (owner, 12 Nov 2026: every tool is account agnostic). A Claude
    model goes through the team's claude door, which already tries every Claude account here in priority order; only
    when every one is out does the same prompt go to Gemini, on each key in GEMINI_KEYS in turn. The answer records
    which account gave it and what was tried before."""
    tried = []
    if not model.startswith("gemini"):
        try:
            return ask_claude(text, model)
        except SystemExit as e:
            tried.append("claude %s: %s" % (model, str(e)[:120]))
        model = GEMINI_FALLBACK
    for name in GEMINI_KEYS:
        key = ST.key(name)
        if not key:
            tried.append(name + ": not in the key file")
            continue
        try:
            out, usage = ask_gemini(text, model, key)
            return out, dict(usage or {}, account=name, model=model, tried=tried)
        except SystemExit as e:
            tried.append("%s: %s" % (name, str(e)[:120]))
    raise SystemExit("no account could answer: " + " · ".join(tried))


def ask_gemini(text, model, key):
    body = {"contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for attempt in range(4):
        try:
            r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                       headers={"Content-Type": "application/json", "x-goog-api-key": key})
            res = json.load(urllib.request.urlopen(r, timeout=300))
            parts = res["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought")), res.get("usageMetadata") or {}
        except urllib.error.HTTPError as e:
            if e.code in (500, 502, 503, 504) and attempt < 3:      # 402 (no credit) and 429 (cap) go to the next key
                time.sleep(10 * (attempt + 1))
                continue
            raise SystemExit(f"Gemini {e.code}: {e.read()[:300].decode('utf8', 'replace')}")


def ask_claude(text, model):
    """One answer from Claude through the team's one door (run-kit claude_door): it tries every account this machine
    holds, best first (company key, long-life token, this login, each saved login under ~/.claude-accounts, then Codex,
    then the session's own hand) and moves on when one runs out. No tools, one turn, JSON back."""
    import tempfile
    sys.path.insert(0, str(ST.part("run-kit")))
    from run_kit import claude_door
    with tempfile.TemporaryDirectory() as d:
        r = claude_door.run(["--output-format", "json", "--model", model, "--max-turns", "1", "--tools", "",
                             "--strict-mcp-config", "--setting-sources", ""],      # the prompt alone: no tools, no settings
                            text + "\n\nAnswer with the JSON only, no other words.", timeout=900, cwd=d)
    try:
        res = json.loads(r.stdout)
    except ValueError:
        out = (r.stdout or "").strip()               # a text-only stand-in (Codex, the session hand) answers in plain text
        if out.startswith("{") or out.startswith("```"):
            res = {"result": out}
        else:
            raise SystemExit("Claude gave no answer on any account: " + (r.stderr or r.stdout or "")[-300:])
    if res.get("is_error"):
        raise SystemExit("Claude (%s): %s" % (getattr(r, "credential", "?"), str(res.get("result"))[:300]))
    out = str(res.get("result") or "").strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[1].rsplit("```", 1)[0]
    return out, {"model": model, "account": getattr(r, "credential", None), "usage": res.get("usage"),
                 "seconds": round((res.get("duration_ms") or 0) / 1000, 1)}


PARTS = ("cheeks", "face", "jaw", "neck", "mouth", "shoulder", "chest", "eye", "forearm", "wrist")
NUMBER = {"lean": 20.0, "tilt": 10.0, "nod": 2, "shake": 2, "squat": 1.0}     # a move said in words: its usual size
FLAGS = ("laugh", "sit", "cross_legs")


def value(action, v, names):
    """An action's value as the figures take it, from whatever was written: a number for a size, true/false for a
    state, NAME.part for a reach, a name or degrees for a turn or a point, [x, y] for a walk. None: it cannot be read."""
    if action in NUMBER:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
        m = re.search(r"-?\d+(?:\.\d+)?(?!\s*(?:cm|mm|m\b|s\b|%|\d))", str(v))   # a size, not a distance or a time
        if m:
            return float(m.group(0)) if action != "squat" or float(m.group(0)) <= 1 else 1.0
        if action in ("lean", "tilt") and re.search(r"\b(back|upright|straight|level|0)\b", str(v), re.I):
            return 0.0
        return NUMBER[action]
    if action in FLAGS:
        return v if isinstance(v, bool) else not re.search(r"\b(false|no|stands?|uncross|off)\b", str(v), re.I)
    if action == "reach":
        if v is None or v is False:
            return None
        m = re.search(r"\b(%s|ME|SELF)\.([a-z]+)" % "|".join(map(re.escape, names)) if names else r"\b(ME|SELF)\.([a-z]+)", str(v))
        if m:
            return "%s.%s" % (m.group(1), m.group(2))
        part = next((x for x in PARTS if re.search(r"\b%s" % x, str(v), re.I)), None)
        who = next((n for n in names if re.search(r"\b%s\b" % re.escape(n), str(v))), None)
        if part and (who or re.search(r"\b(own|her|his|their|self)\b", str(v), re.I)):
            return "%s.%s" % (who or "ME", part)
        return None
    if action == "point" and isinstance(v, str) and not any(re.search(r"\b%s\b" % re.escape(n), v) for n in names):
        # a direction in words: points that way from where the person stands (blocking_blender "rel")
        dx = (1 if re.search(r"\bright\b", v, re.I) else -1 if re.search(r"\bleft\b", v, re.I) else 0)
        dy = (1 if re.search(r"\b(behind|back|down the|away|far)\b", v, re.I) else -1 if re.search(r"\b(forward|toward the camera|front)\b", v, re.I) else 0)
        return ["rel", dx, dy] if dx or dy else None
    if action in ("turn", "point", "walk_to", "mic", "look"):
        if isinstance(v, (int, float, list)) or v is None:
            return v
        hit = next((n for n in names if re.search(r"\b%s\b" % re.escape(n), str(v))), None)
        if hit:
            return hit
        m = re.search(r"-?\d+(?:\.\d+)?", str(v))
        return float(m.group(0)) if m and action in ("turn", "look") else (0.0 if action in ("turn", "look") else None)
    return v


def clean(spec, seconds):
    """Only people, actions and times the figures can carry; a value said in words is read into the figures' terms
    (`value`), its words kept as `note`; what was dropped is said."""
    names = [p["name"] for p in spec.get("people") or []]
    dropped, beats = [], []
    for b in spec.get("beats") or []:
        acts = [a for a in ACTIONS if a in b]
        if b.get("who") not in names or not acts:
            dropped.append(b)
            continue
        f0 = max(0.0, min(seconds, float(b.get("from") or 0)))
        f1 = max(f0 + 0.2, min(seconds, float(b.get("to") or f0 + 1)))
        for a in acts:
            v = value(a, b[a], names)
            if v is None and a not in ("reach", "point", "mic"):
                dropped.append(b)
                continue
            if a == "reach" and v is None and b[a] not in (None, False, "", "null"):
                dropped.append(b)                    # a reach to something the figures have no point for
                continue
            beat = {"from": round(f0, 2), "to": round(f1, 2), "who": b["who"], a: v,
                    **({"hands": b["hands"]} if a == "reach" and b.get("hands") else {})}
            if isinstance(b[a], str) and b[a] != v:
                beat["note"] = b[a]
            beats.append(beat)
    cam = spec.get("camera") or {}
    cam["follow"] = [f for f in cam.get("follow") or [] if f.get("who") in names]
    return {"people": spec["people"], "beats": beats, "camera": cam, "notes": spec.get("notes") or [],
            "dropped": dropped}


PLACES = ("\n\nWhere everyone starts, and where the camera is, are already set from real footage of this moment (metres; "
          "the camera stands at [0, 0] looking toward +y, so these replace the camera rule above): {places}. Every person "
          "listed starts exactly there; give them that `at`, and put any walk inside the same frame.")


def program(take, out_dir, model=MODEL, render=True, rows=None, seconds=None, frame=None):
    """`rows`/`seconds`: each line's window given from outside (a reference's own beat timing, motion_chain `ours`)
    instead of the lines' read lengths. `frame`: the reference's own staging (retarget.build: people's starting places,
    the tracked camera path, fps, cuts): our figures start where its people stood and are filmed by its camera, and
    only their moves are programmed."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if not rows:
        rows, seconds = timeline(take)
    text = PROMPT.read_text().replace("{take}", _take_words(take)).replace(
        "{timeline}", "\n".join(f"line {r['line']} ({r['speaker']}): {r['from']}-{r['to']} s" for r in rows)).replace(
        "{seconds}", str(seconds))
    places = {p["name"]: p["at"] for p in (frame or {}).get("people") or []}
    if places:
        text += PLACES.replace("{places}", json.dumps(places))
    (out / "sent.json").write_text(json.dumps({"model": model, "prompt": text}, indent=1, ensure_ascii=False))
    answer, usage = ask(text, model)
    (out / "answer.json").write_text(answer)
    try:
        got = json.loads(answer)
    except ValueError:
        raise SystemExit("the motion programmer answered with no JSON: " + answer[:300])
    spec = clean(got, seconds)
    spec.update({"seconds": seconds, "fps": 16, "size": [480, 854], "render": render,
                 "sky": take.get("sky") or [0.55, 0.72, 0.92], "floor": take.get("floor") or [0.82, 0.74, 0.58]})
    if frame:
        for person in spec["people"]:
            if person["name"] in places:
                person["at"] = places[person["name"]][:2]
        spec.update({k: frame[k] for k in ("camera", "fps", "seconds", "size", "sky", "floor", "cuts") if frame.get(k)})
    (out / "spec.json").write_text(json.dumps(spec, indent=1))
    rec = MO.blocking(out / "spec.json", out / "blocking.mp4", exact=True, motion_dir=out)
    m = rec["motion"]
    m.update({"kind": "programmed", "status": "ready", "model": model, "timeline": rows, "notes": spec["notes"],
              "dropped": len(spec["dropped"]), "beats": len(spec["beats"]), "people_names": [p["name"] for p in spec["people"]],
              "tokens": usage, "seconds_to_program": round(time.time() - t0, 1)})
    m["take_motion"].update({"approved": True, "pose": str(out / "skeleton.mp4")})
    (out / "motion.json").write_text(json.dumps(m, indent=1))
    return m


DRESS = ("Picture 1 is a 3D blocking frame: grey stand-in figures showing exactly where every person stands, which way "
         "each one faces, their pose and the camera. Make it a real photo: the same people, positions, poses, framing and "
         "camera height as picture 1, each stand-in becoming the person described below, as they look in the other "
         "pictures when given. {look}. People: {people}. Shot on a phone, natural light, real skin and fabric, no text.")

DRESS_PRINT = ("Picture 1 is the scene's filed 3D set print: the real place, light and people, each face and outfit as it "
               "must stay. Picture 2 is a 3D blocking frame: grey stand-ins showing exactly where every person stands, "
               "which way each one faces, their pose and the camera. Make a real photo of picture 1's people and place "
               "in picture 2's positions, poses, framing and camera height. {look}. People: {people}. Shot on a phone, "
               "natural light, real skin and fabric, no text.")


def _image_door():
    """The house picture ladder (components/image-production: GPT Image 2.5 through the Higgsfield command line, then
    the models the house names when it refuses)."""
    tried = []
    for root in (Path(ST.WRITING).parents[2] if len(Path(ST.WRITING).parents) > 2 else None, ST.REPO):
        part = ST.part("image-production", root) if root else None
        if not (part and (part / "image_production" / "providers.py").exists()):
            continue
        sys.path[:0] = [str(part), str(Path(part).parent / "gdrive-creator"), str(Path(part).parent / "casting")]
        try:
            from image_production import providers as PR
            from image_production import route as RT
        except ImportError as e:          # a partial copy of the workspace: try the next one
            tried.append(f"{part}: {e}")
            for k in [k for k in sys.modules if k.startswith("image_production")]:
                sys.modules.pop(k)
            continue
        t = RT.table()                                                # the house's own table, its models filled in
        return PR, RT.rungs("gpt-image-person", t["models"]["gpt-image-person"], t)
    raise SystemExit("no working image-production component here to make the first frame: " + "; ".join(tried))


# THE AD'S STYLE (owner ruling, 12 Nov 2026; video-production styles/style_chain.py): in a non-photoreal ad the start
# picture is drawn in the ad's style from the same variants every time: the location's set print first (the picture
# gate's kept print), then the blocking frame, each person's variant sheet for the scene's look, and the ad's one look
# picture. A photoreal ad keeps DRESS.
STYLED_DRESS = ("Picture 1 is the place, already drawn in the ad's style: keep its room, furniture, materials and light. "
                "Picture 2 is a 3D blocking frame: grey stand-in figures showing exactly where every person stands, which "
                "way each one faces, their pose and the camera; keep those exactly and set the place from picture 1 around "
                "them from that camera. {sheets}Each stand-in becomes that person exactly as their sheet shows: face, hair, "
                "build, outfit and every mark. The last picture shows only the style to draw in, never its faces or "
                "layout. {look}. People: {people}. Rendered entirely in this style: {formula}. Never photoreal. No text.")


def _style_chain():
    f = ST.part("video-production") / "styles" / "style_chain.py"
    if not f.is_file():
        return None
    import importlib.util
    sp = importlib.util.spec_from_file_location("motion_style_chain", f)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def styled_scene(scene_dir):
    """The ad's style and the scene's variants (style_chain.scene_refs), or None for a photoreal ad / no production."""
    SC = _style_chain()
    sd = Path(scene_dir).resolve()
    if SC is None or sd.parent.name != "scenes":
        return None
    prod, briefs = sd.parent.parent.name, sd.parent.parent.parent
    try:
        r = SC.scene_refs(prod, sd.name, briefs=briefs, writing=ST.WRITING)
    except SystemExit:
        return None
    return None if SC.is_photoreal(r["style"]) else r


def rehearsal(motion_dir):
    """The blocking the scene's take moves to: the motion chain's rehearsal (chain.json `rehearse`, else
    rehearsal/blocking.mp4), and the programmed blocking only when no rehearsal exists."""
    d = Path(motion_dir)
    try:
        st = (json.loads((d / "chain.json").read_text()).get("stages") or {}).get("rehearse") or {}
    except (OSError, ValueError):
        st = {}
    for f in ([d / st["file"]] if st.get("ok") and st.get("file") else []) + [d / "rehearsal" / "blocking.mp4",
                                                                                  d / "blocking.mp4"]:
        if f.is_file():
            return f
    raise SystemExit(f"no rehearsal or blocking in {d}: run the motion chain on this scene first")


def _motion_chain():
    import motion_chain as MC                            # late: motion_chain reads this module's neighbours
    return MC


def framing(scene_dir):
    """The rehearsal's first frame in words (motion_chain.frame_words), ahead of the look in the start picture's prompt:
    an image model ignores a grey stand-in's camera and follows words. Empty when the rehearsal has no pose to read."""
    try:
        return _motion_chain().frame_words(scene_dir)
    except SystemExit:
        return ""


def reframe(scene_dir, picture, chk):
    """An image model often draws the person smaller than the motion's first frame even when told the framing. When
    everyone is placed right and only the size is short (under 75%), the picture is zoomed in about the rehearsal's own
    head positions, so heads stay where the motion has them and bodies reach its size. Never wider, never a person cut
    out of place: a fail on people or placement is left for a remake. Keeps the drawn picture as first-frame-drawn.png."""
    import re
    rows = chk.get("rows") or []
    bad = [r for r in rows if r.get("ok") is False]
    sizes = [int(m.group(1)) / 100 for r in bad if r["name"].endswith(" framing")
             for m in [re.match(r"(\d+)%", r.get("short") or "")] if m]
    if not bad or len(sizes) != len(bad) or max(sizes) >= 0.75 or min(sizes) < 0.35:
        return False
    try:
        reh = json.loads((Path(scene_dir) / "motion" / "rehearsal" / "pose.json").read_text())
        first = next(f["people"] for f in reh["frames"] if f["people"])
        heads = [p["body33"][0][:2] for p in first if p.get("body33")]
    except (OSError, ValueError, StopIteration, KeyError, IndexError):
        return False
    if not heads:
        return False
    from PIL import Image
    hx, hy = sum(h[0] for h in heads) / len(heads), sum(h[1] for h in heads) / len(heads)
    s = max(0.4, min(sizes) / 0.95)                       # the share of the picture kept: the person lands at ~95%
    im = Image.open(picture)
    W, H = im.size
    x0, y0 = max(0, min(W * (1 - s), hx * W * (1 - s))), max(0, min(H * (1 - s), hy * H * (1 - s)))
    im.save(Path(picture).with_name("first-frame-drawn.png"))
    im.crop((round(x0), round(y0), round(x0 + W * s), round(y0 + H * s))).resize((W, H), Image.LANCZOS).save(picture)
    return True


FACE_TRIES = 3     # a start picture whose people are not their sheets is made again, this many pictures in all, then held


def _face_gate():
    import importlib.util
    p = ST.REPO / "components" / "video-production" / "machine" / "face_gate.py"
    spec = importlib.util.spec_from_file_location("motion_face_gate", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def faces_in_picture(take, picture, gate=None):
    """(pass, record): the start picture's people against their character sheets (take.json `in_picture`, the cast
    names seen in the first frame; default every cast member with a sheet), through video-production's face gate.
    (True, None) when the take names no sheets."""
    cast = take.get("cast") or {}
    names = take.get("in_picture") or list(cast)
    masters = [str(c.get("master") or c.get("sheet")) for n, c in cast.items() if n in names and isinstance(c, dict)
               and Path(str(c.get("master") or c.get("sheet") or "")).is_file()]     # the face master reads better than a body sheet
    if not masters:
        return True, None
    rec = (gate or _face_gate()).stamp(str(picture), masters)
    return bool(rec.get("pass")), rec


def photoreal_refs(take, frame0, looks=None):
    """A photoreal start picture's references and whether they lead with a print. The scene names the filed 3D set
    print it is dressed from (take.json `set_print`: printed from the rehearsal's camera with the cast's face board);
    it leads, so GATE-4 sees a kept print first and the people, place and light come from it; the stand-in frame only
    places them. Without one, every photoreal start picture led with the stand-in frame and was refused (2026-11-15)."""
    refs = [Path(frame0)] + [Path(x) for x in (looks or []) if Path(x).exists()]
    sp = take.get("set_print")
    if sp and Path(sp).exists():
        return [Path(sp)] + refs, True
    return refs, False


def first_frame(scene_dir, looks=None):
    """The scene's start picture, made from the rehearsal's first frame: our cast laid over the stand-ins, so the
    picture and the motion agree from frame one. `looks`: pictures that show the people (a start picture, cast sheets).
    In a non-photoreal ad the people, the place and the look come from the ad's style variants (styled_scene)."""
    ST.data_env()                                        # a code-only copy reads sets, styles and writing runs from the data copy
    d = Path(scene_dir) / "motion"
    take = json.loads((Path(scene_dir) / "take.json").read_text())
    blk = rehearsal(d)
    frame0 = d / "frame-1.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(blk), "-frames:v", "1", str(frame0)], check=True)
    cast = take.get("cast") or {}
    people = "; ".join(f"{n}: {c.get('look')}" for n, c in cast.items() if isinstance(c, dict) and c.get("look"))
    st = styled_scene(scene_dir)
    if st and st["missing"]:
        raise SystemExit("start picture held: " + "; ".join(st["missing"]))
    feel = take.get("doctrine") or {}            # the doctrine's moment (video-writing doctrine_tags.py): faces carry its feeling
    feel = ("The faces and bodies carry this feeling, turned up but real: %s (%s). " % (feel["show"], feel["feel"])) if feel.get("feel") and feel.get("show") else ""
    look = (framing(scene_dir) + " " + feel + (take.get("look") or "")).strip()
    record = {}
    if st:
        sheets = ("Then come the character sheets, one per person, in this order: "
                  + ", ".join(p["name"] for p in st["people"]) + ". ") if st["people"] else ""
        if st.get("product"):
            sheets += (f"Then the product picture: the product sits {st['product']['where']}, exactly as that picture "
                       "shows it, its label as on it. ")
        if st.get("moment"):
            sheets += f"At this first moment: {st['moment']}; where the blocking and these words differ on the hands, the words win. "
        if st.get("props"):
            sheets += "In the place: " + "; ".join(st["props"]) + ". "
        prompt = STYLED_DRESS.format(sheets=sheets, look=look, people=people or "as their sheets show",
                                     formula=st["formula"])
        refs = ([Path(st["set_print"])] if st["set_print"] else []) + [frame0] + [Path(p["path"]) for p in st["people"]]
        refs += [Path(st["product"]["picture"])] if st.get("product") else []
        refs += [Path(x) for x in (looks or []) if Path(x).exists()]
        if (st.get("look") or {}).get("file"):
            refs.append(Path(st["look"]["file"]))
        record = {"style": st["style"], "set": (st["set"] or {}).get("id"), "rehearsal": str(blk),
                  "product": (st.get("product") or {}).get("id"),
                  "picture_from": [{"element": p["element"], "file": p["file"]} for p in st["people"]]}
    else:
        refs, from_print = photoreal_refs(take, frame0, looks)
        prompt = (DRESS_PRINT if from_print else DRESS).format(look=look, people=people)
        if from_print:
            record = {"set_print": str(refs[0]), "rehearsal": str(blk)}
    PR, rungs = _image_door()
    out = d / "first-frame.png"
    # GATE-4 (2026-11-10): the start picture comes from a filed 3D set print; the blocking frame is a layout, not a print
    from image_production import set_gate
    set_gate.door_gate(refs, door="video-studio motion first frame", lane="video")
    faces = []
    for attempt in range(FACE_TRIES):        # 2026-11-13: the people in the start picture are their sheets, or it is made again
        with set_gate.cleared():
            rec = PR.generate_ladder(rungs, prompt, refs, out, "9:16")     # a refusal moves to the next model on the ladder
        ok, frec = faces_in_picture(take, out)
        faces.append({"try": attempt + 1, "pass": ok, "people": [(Path(p.get("master", "")).name, p.get("verdict"))
                                                                  for p in (frec or {}).get("people") or []]})
        if ok:
            break
        out.rename(out.with_name("first-frame.face-miss-%d.png" % (attempt + 1)))
    else:
        (d / "first-frame.faces.json").write_text(json.dumps(faces, indent=1))
        raise SystemExit("start picture held: its people are not their character sheets after %d pictures (%s). "
                         "See motion/first-frame.faces.json; no take is made from it." % (FACE_TRIES, faces[-1]["people"]))
    (d / "first-frame.faces.json").write_text(json.dumps(faces, indent=1))
    chk = _motion_chain().start_check(scene_dir, out)     # the picture against the rehearsal's first frame
    zoomed = reframe(scene_dir, out, chk)
    if zoomed:
        chk = _motion_chain().start_check(scene_dir, out)
    (d / "first-frame.json").write_text(json.dumps({"prompt": prompt, "references": [str(r) for r in refs], "made": rec,
                                                     "picture": "first-frame.png", "start_check": {k: chk[k] for k in ("passed", "failed")},
                                                     **record}, indent=1, default=str))
    if chk["failed"]:
        raise SystemExit("start picture held: it does not match the rehearsal's first frame ("
                         + "; ".join("%s %s" % (r["name"], r["short"])
                                     for r in chk["rows"] if r["ok"] is False)
                         + "). See motion/match-start-picture.json; remake it before any take.")
    return {"file": str(out), "prompt": prompt, "references": [str(r) for r in refs], "start_check": chk}


def program_scene(scene_dir, model=MODEL):
    take_file = Path(scene_dir) / "take.json"
    if not take_file.exists():
        raise SystemExit(f"this scene has no take written yet ({take_file})")
    return program(json.loads(take_file.read_text()), Path(scene_dir) / "motion", model)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    model = a[a.index("--model") + 1] if "--model" in a else MODEL
    if a[0] == "scene":
        print(json.dumps(program_scene(a[1], model), indent=1))
    elif a[0] == "first-frame":
        print(json.dumps(first_frame(a[1], a[2:]), indent=1))
    else:
        out = a[a.index("--out") + 1] if "--out" in a else "motion"
        print(json.dumps(program(json.loads(Path(a[0]).read_text()), out, model, "--no-render" not in a), indent=1))
