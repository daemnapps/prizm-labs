#!/usr/bin/env python3
"""Compose before the image model: a people scene's start picture laid out in code, so the picture model only makes it
look real (2026-11-15).

Why: a 3D set print, even staged exactly, re-composes the shot: people come back larger or smaller than the rehearsal,
turned the wrong way, or standing where someone should hide them. Every composition decision is made here, before any
picture model; the model is left only the look.

    1 plate    the set printed once from the rehearsal camera with nobody in it (a filed kept print, so GATE-4 holds)
    2 pieces   each cast member printed alone, full body, in the rehearsal first frame's pose and facing, on a flat ground,
               from the same camera; cut out here (`cutout`: the ground keyed off by its own colour)
    3 place    each cutout scaled so its neck-to-hip length is the rehearsal's and moved so its neck lands on the
               rehearsal's neck point; laid back to front by distance from the camera, so whoever is behind is covered
               as in the rehearsal (`compose`)
    4 look     one light pass (relight, contact shadows, colour match; nothing moved or resized), then start_check and the
               face check. The plain composite stands when the pass moves anyone (`finish`)

    python3 compose_start.py targets <scene dir>                       where each person must land, from the rehearsal
    python3 compose_start.py compose <scene dir> <plate> NAME=<piece> ...   the composite, written to motion/composed.png
    python3 compose_start.py words <scene dir> NAME                     a person piece's print words
    python3 compose_start.py run <scene dir> [--no-look]                the route from take.json `compose`: compose,
                                                                        light pass, start_check and face check

Brand-free: the people, the place and the files come from the scene.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# MediaPipe's body points: shoulders, hips, ankles
SH, HP, AN = (11, 12), (23, 24), (27, 28)


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _mid(pts, ids):
    got = [pts[i] for i in ids if i < len(pts) and pts[i] and (len(pts[i]) < 3 or pts[i][2] > 0.3)]
    if not got:
        return None
    return (sum(p[0] for p in got) / len(got), sum(p[1] for p in got) / len(got))


def body_points(person):
    """(neck, hips, feet) of one tracked person, in fractions of the frame: the neck is between the shoulders."""
    pts = person.get("body33") or []
    return _mid(pts, SH), _mid(pts, HP), _mid(pts, AN)


def targets(scene_dir, frame=0):
    """Where each person lands in the start picture: the rehearsal's first frame (motion/rehearsal/pose.json), per
    person their neck point, neck-to-hip length (fractions of the frame height) and distance from the camera (the
    rehearsal's own spec when it has places and a camera; else lower feet are nearer)."""
    d = Path(scene_dir) / "motion" / "rehearsal"
    pose = _load(d / "pose.json") or {}
    people = next((f["people"] for f in (pose.get("frames") or [])[frame:] if f["people"]), [])
    if not people:
        raise SystemExit("no rehearsal pose to compose against (%s)" % (d / "pose.json"))
    W, H = pose.get("width") or 480, pose.get("height") or 854
    spec = _load(d / "spec.json") or {}
    cam = ((spec.get("camera") or {}).get("shots") or [{}])[0].get("at") or (spec.get("camera") or {}).get("at")
    at = {p["name"]: p.get("at") for p in spec.get("people") or [] if p.get("at")}
    out = {}
    for p in people:
        name = p.get("name") or str(p.get("id"))
        neck, hips, feet = body_points(p)
        if not (neck and hips):
            continue
        dist = None
        if cam and at.get(name):
            dist = ((at[name][0] - cam[0]) ** 2 + (at[name][1] - cam[1]) ** 2) ** 0.5
        import measure as ME
        span = ME.frame_measures(p, W / float(H)).get("span")
        out[name] = {"neck": [round(neck[0], 4), round(neck[1], 4)], "hips": [round(hips[0], 4), round(hips[1], 4)],
                     "span": span,
                     "torso": round(((neck[0] - hips[0]) * W / H) ** 2 + (neck[1] - hips[1]) ** 2, 8) ** 0.5,
                     "depth": round(dist, 3) if dist is not None else round(1.0 - (feet or hips)[1], 4)}
    return {"width": W, "height": H, "people": out}


def cutout(picture, out=None, soft=34.0, hard=70.0):
    """The person off a flat ground: the ground's colour is read from the picture's border, every pixel near it goes
    clear (a soft edge between `soft` and `hard`), the ground's tint is taken off the edges, and only the largest piece
    is kept. Returns an RGBA picture (saved to `out` when given)."""
    import numpy as np
    from PIL import Image, ImageFilter
    im = Image.open(picture).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    ground = np.median(border, axis=0)
    dist = np.sqrt(((a - ground) ** 2).sum(axis=2))
    alpha = np.clip((dist - soft) / (hard - soft), 0, 1)
    g = int(np.argmax(ground))                        # the ground's strongest channel
    others = [c for c in range(3) if c != g]
    lead = float(ground[g] - ground[others].max())
    if lead > 40:                                     # a coloured ground: its shade and shadow go too (they keep its lead)
        dom = a[:, :, g] - a[:, :, others].max(axis=2)
        alpha = np.minimum(alpha, np.clip((lead * 0.55 - dom) / (lead * 0.3), 0, 1))
    try:                                              # only the largest piece: stray specks of ground colour go
        from scipy import ndimage
        lab, n = ndimage.label(alpha > 0.5)
        if n > 1:
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
            keep = 1 + int(np.argmax(sizes))
            alpha = alpha * ndimage.binary_dilation(lab == keep, iterations=3)
    except ImportError:
        pass
    cap = a[:, :, others].max(axis=2)                 # the ground's tint taken off the edges
    edge = (alpha < 0.98) & (alpha > 0)
    a[:, :, g] = np.where(edge, np.minimum(a[:, :, g], cap), a[:, :, g])
    rgba = Image.fromarray(np.dstack([a, alpha * 255]).astype(np.uint8), "RGBA")
    rgba.putalpha(rgba.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))
    if out:
        rgba.save(out)
    return rgba


def piece_points(rgba_path, work):
    """The piece's own neck and hips, read with the motion reader (the picture as a short clip, as start_check reads a
    start picture). Returns (neck, hips) in pixels, or None."""
    import subprocess
    from PIL import Image
    import motion as MO
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    flat = work / "flat.png"
    im = Image.open(rgba_path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(flat)
    clip = work / "piece.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "0.3", "-i", str(flat), "-vf",
                    "fps=16,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(clip)], check=True)
    MO.track(clip, work, kind="picture")
    pose = _load(work / "pose.json") or {}
    people = max((f["people"] for f in pose.get("frames") or []), key=len, default=[])
    if not people:
        return None
    p = max(people, key=lambda q: (q.get("box") or [0, 0, 0])[2] if q.get("box") else 0)
    neck, hips, _ = body_points(p)
    if not (neck and hips):
        return None
    W, H = im.size
    import measure as ME
    span = ME.frame_measures(p, W / float(H)).get("span")
    return (neck[0] * W, neck[1] * H), (hips[0] * W, hips[1] * H), (span * H if span else None)


def place(plate, pieces, tg):
    """The composite: each piece scaled to its target's neck-to-hip length and moved so its neck is on the target's
    neck, laid far to near. `pieces`: {name: (rgba, (neck_px, hips_px))}. Returns (picture, placements)."""
    from PIL import Image
    base = Image.open(plate).convert("RGBA")
    W, H = base.size
    rows = []
    order = sorted(pieces, key=lambda n: -float(tg["people"][n]["depth"]))       # farthest first
    for name in order:
        rgba, pts = pieces[name]
        neck, hips = pts[0], pts[1]
        span = pts[2] if len(pts) > 2 else None
        t = tg["people"][name]
        # sized by the torso (neck to hips): a stand-in's head is not a real head's size, its torso is a body's
        want = (((t["neck"][0] - t["hips"][0]) * W) ** 2 + ((t["neck"][1] - t["hips"][1]) * H) ** 2) ** 0.5
        have = ((neck[0] - hips[0]) ** 2 + (neck[1] - hips[1]) ** 2) ** 0.5
        s = want / have if have else 1.0

        im = rgba.resize((max(1, round(rgba.width * s)), max(1, round(rgba.height * s))), Image.LANCZOS)
        x = round(t["neck"][0] * W - neck[0] * s)
        y = round(t["neck"][1] * H - neck[1] * s)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.paste(im, (x, y), im)
        base.alpha_composite(layer)
        rows.append({"name": name, "scale": round(s, 4), "at": [x, y], "neck": [round(t["neck"][0] * W), round(t["neck"][1] * H)],
                     "depth": t["depth"]})
    return base.convert("RGB"), rows


def compose(scene_dir, plate, pieces_files, frame=0):
    """motion/composed.png from the plate and each person's piece (their print on a flat ground): cut out, read,
    placed on the rehearsal's first frame. Writes motion/compose.json (every placement and why) and returns it."""
    from PIL import Image
    sd = Path(scene_dir)
    d = sd / "motion" / "compose"
    d.mkdir(parents=True, exist_ok=True)
    tg = targets(sd, frame)
    pw, ph = Image.open(plate).size
    missing = [n for n in tg["people"] if n not in pieces_files]
    pieces, notes = {}, []
    for name, f in pieces_files.items():
        if name not in tg["people"]:
            notes.append("%s: not in the rehearsal's first frame, left out" % name)
            continue
        cut = cutout(f, d / ("%s-cut.png" % name.lower()))
        if cut.size != (pw, ph):                      # every piece is printed from the plate's camera at its size
            cut = cut.resize((pw, ph), Image.LANCZOS)
            cut.save(d / ("%s-cut.png" % name.lower()))
        pts = piece_points(d / ("%s-cut.png" % name.lower()), d / ("%s-read" % name.lower()))
        if not pts:
            notes.append("%s: no body read in the piece; left out" % name)
            missing.append(name)
            continue
        pieces[name] = (cut, pts)
    pic, rows = place(plate, pieces, tg)
    out = sd / "motion" / "composed.png"
    pic.save(out)
    rec = {"picture": str(out), "plate": str(plate), "pieces": {k: str(v) for k, v in pieces_files.items()},
           "placed": rows, "missing": missing, "notes": notes, "targets": tg}
    (sd / "motion" / "compose.json").write_text(json.dumps(rec, indent=1))
    return rec


FACE_WORDS = ("Picture 1 is a person on a flat green ground; picture 2 is that same person's real face. Change ONLY the "
              "face and head of picture 1 to be exactly the person in picture 2: the same face shape and width, the "
              "same skin tone (never lighter), the same eyes, brows, nose, lips and jaw, the same hair. A mask, glasses "
              "or anything worn on the face in picture 1 stays exactly as it is, over the new face. Keep everything "
              "else of picture 1 exactly: the head's turn and tilt, the body, its figure and pose, the outfit, the "
              "hands and what they hold, the framing and the flat green ground. No text.")
FACE_TRIES = 3


def true_faces(scene_dir, pieces, gate=None, edit=None):
    """Each piece whose person the take shows (take.json `in_picture`, else the whole cast) checked against their face
    master; a piece that comes back DIFFERENT is edited once more through the house picture door (FACE_WORDS: the face
    from the master, everything else kept), up to FACE_TRIES, and the first that passes is used. Returns the pieces to
    compose from and the record per person."""
    import motion_program as MP
    sd = Path(scene_dir)
    take = _load(sd / "take.json") or {}
    cast = take.get("cast") or {}
    want = take.get("in_picture") or list(cast)
    g = gate or MP._face_gate()
    out, rec = dict(pieces), {}
    for name, piece in pieces.items():
        master = (cast.get(name) or {}).get("master") if isinstance(cast.get(name), dict) else None
        if name not in want or not master or not Path(master).is_file():
            continue
        tries = []
        r = g.stamp(str(piece), [master])
        tries.append({"picture": str(piece), "pass": bool(r.get("pass"))})
        cur = Path(piece)
        n = 0
        while not r.get("pass") and n < FACE_TRIES:
            n += 1
            fixed = sd / "motion" / "compose" / ("%s-face-%d.png" % (name.lower(), n))
            fixed.parent.mkdir(parents=True, exist_ok=True)
            (edit or _edit_face)(piece, master, fixed)
            r = g.stamp(str(fixed), [master])
            tries.append({"picture": str(fixed), "pass": bool(r.get("pass")),
                          "why": [p.get("why") for p in r.get("people") or []]})
            cur = fixed
        if r.get("pass"):
            out[name] = str(cur)
        rec[name] = {"pass": bool(r.get("pass")), "tries": tries}
    return out, rec


def _edit_face(piece, master, out):
    """One face edit through the house picture door; the piece (a kept print) is the print it starts from."""
    import motion_program as MP
    PR, rungs = MP._image_door()
    from image_production import set_gate
    set_gate.door_gate([piece], from_print=piece, door="motion compose: the face from the master", lane="video")
    with set_gate.cleared():
        return PR.generate_ladder(rungs, FACE_WORDS, [Path(piece), Path(master)], Path(out), "9:16")


SAFE_WORDS = ("This picture is the first frame for an AI video model whose content filter is strict. It refuses: nudity "
              "or see-through clothing; visible cleavage, or framing that sexualises the chest, buttocks or groin; "
              "underwear or swimwear shots; anyone who could be a minor in a suggestive pose; blood, wounds or violence; "
              "weapons; drugs. Would that filter likely refuse this picture? Answer JSON only: "
              '{"safe": true or false, "why": "what would trip it, in a few words, or empty"}')


def safe_for_video(picture, judge=None):
    """Whether a video model's content filter would take this start picture, asked through the house picture judge
    (video-production vision_judge: the claude CLI, then a local model, then Gemini). A refused take costs nothing
    when it is caught here. Cached beside the picture by its bytes: <picture>.safe.json. Returns {"safe", "why", "by"}."""
    import hashlib
    pic = Path(picture)
    side = pic.with_name(pic.name + ".safe.json")
    sha = hashlib.sha256(pic.read_bytes()).hexdigest()
    old = _load(side) or {}
    if old.get("sha256") == sha:
        return old
    if judge is None:
        import importlib.util
        import motion_program as MP
        f = MP.ST.REPO / "components" / "video-production" / "machine" / "vision_judge.py"
        sp = importlib.util.spec_from_file_location("compose_vision_judge", f)
        VJ = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(VJ)
        judge = lambda text, pics: VJ.ask(text, pics, want_json=True)         # noqa: E731
    ans = judge(SAFE_WORDS, [str(pic)])
    m = re.search(r"\{.*\}", str(ans), re.S)
    try:
        got = json.loads(m.group(0) if m else str(ans))
    except ValueError:
        got = {"safe": None, "why": "the judge gave no answer: " + str(ans)[:120]}
    rec = {"safe": got.get("safe"), "why": got.get("why") or "", "by": getattr(ans, "backend", None), "sha256": sha}
    side.write_text(json.dumps(rec, indent=1))
    return rec


def finish(scene_dir, composite, plate_print, look=True):
    """The composite made one real photograph (LOOK_WORDS: light, colour, contact shadows; nothing moved), then both
    the looked picture and the plain composite checked: start_check against the rehearsal's first frame and the face
    check against the sheets. The looked picture is the start picture when it passes both; the plain composite when
    only it does (the pass moved someone). Writes motion/first-frame.png and the record into motion/compose.json."""
    import shutil
    import motion_chain as MC
    import motion_program as MP
    sd = Path(scene_dir)
    d = sd / "motion"
    take = _load(sd / "take.json") or {}
    tried = []
    if look:
        PR, rungs = MP._image_door()
        from image_production import set_gate
        set_gate.door_gate([composite], from_print=plate_print, door="motion compose: the light pass", lane="video")
        out = d / "composed-look.png"
        with set_gate.cleared():                      # the composite, then the empty place its light comes from
            made = PR.generate_ladder(rungs, LOOK_WORDS, [Path(composite), Path(plate_print)], out, "9:16")
        tried.append(("look", out, made))
    tried.append(("composite", Path(composite), None))
    rows = []
    for kind, pic, made in tried:
        chk = MC.start_check(sd, pic)
        ok_face, frec = MP.faces_in_picture(take, pic)
        safe = safe_for_video(pic)
        rows.append({"kind": kind, "picture": str(pic), "start_check": {"passed": chk["passed"], "failed": chk["failed"],
                     "rows": [{"name": r["name"], "ok": r["ok"], "short": r.get("short")} for r in chk["rows"]]},
                     "faces": {"pass": ok_face, "people": [(Path(p.get("master", "")).name, p.get("verdict")) for p in (frec or {}).get("people") or []]},
                     "safe": {k: safe.get(k) for k in ("safe", "why", "by")}, "made": made})
    use = next((r for r in rows if not r["start_check"]["failed"] and r["faces"]["pass"] and r["safe"]["safe"] is not False), None)
    if use:
        shutil.copyfile(use["picture"], d / "first-frame.png")
        MC.start_check(sd, d / "first-frame.png")        # the record names the start picture itself
    rec = _load(d / "compose.json") or {}
    rec["finish"] = {"rows": rows, "used": use and use["kind"]}
    (d / "compose.json").write_text(json.dumps(rec, indent=1, default=str))
    return {"ok": bool(use), "used": use and use["kind"], "rows": rows}


def run(scene_dir, look=True):
    """The whole route from the take's own record: take.json `compose` = {"plate": <the plate's kept print>,
    "pieces": {NAME: <that person's kept print>}} (filed by the 3d-print skill). Composes, then finishes."""
    sd = Path(scene_dir)
    take = _load(sd / "take.json") or {}
    c = take.get("compose") or {}
    if not (c.get("plate") and c.get("pieces")):
        raise SystemExit("this take has no `compose` (plate + pieces) to compose its start picture from")
    pieces, faces = true_faces(sd, c["pieces"])        # each shown person's face is their master's before composing
    rec = compose(sd, c["plate"], pieces)
    rec["faces"] = faces
    (sd / "motion" / "compose.json").write_text(json.dumps(rec, indent=1, default=str))
    if rec["missing"]:
        raise SystemExit("start picture held: no piece for %s" % ", ".join(rec["missing"]))
    return finish(sd, rec["picture"], c["plate"], look=look)


PIECE_WORDS = ("A real photograph of ONE person alone, {who}: {look}. Full body, head to feet, the whole person in the "
               "picture with green space all round. Facing, exactly: {facing}. {hands}The background is one flat, "
               "even, plain green, nothing else in the picture: no floor, no wall, no shadow, no other person, no props "
               "but what this person holds. The large face in the reference picture is this person's REAL face: copy "
               "the face, skin tone, build and outfit exactly; never slimmer, younger, lighter or prettier. No text.")

PLATE_WORDS = ("A real photograph of the empty place, shot on a phone: {place}. Keep the 3D render's camera, framing, "
               "walls, floor, furniture and light exactly. Nobody in it: no people, no figures, no hands. No text, no logos.")

LOOK_WORDS = ("Picture 1 is a finished composite: every person is already in the right place, at the right size, facing "
              "the right way. Picture 2 is the same place empty: its light is the light of the scene. Make picture 1 one "
              "real photograph taken in that place: light every person by that room's own light (its colour, direction "
              "and warmth on skin, hair and clothes, its highlights and its shadows on the side away from it), give each "
              "one soft contact shadows where the feet meet the floor and their reflection in a shiny floor, and match "
              "colour, grain, sharpness and depth of field across people and place, so nobody reads cut out. Do not move, "
              "resize, turn, add or remove anyone or anything; keep every face, body, outfit and the frame exactly.")


def person_words(scene_dir, name):
    """A person piece's print words: their look from the take, their pose and facing from the rehearsal's first frame."""
    import motion_chain as MC
    sd = Path(scene_dir)
    take = _load(sd / "take.json") or {}
    look = ((take.get("cast") or {}).get(name) or {}).get("look") or ""
    reh = _load(sd / "motion" / "rehearsal" / "pose.json") or {}
    people = next((f["people"] for f in reh.get("frames") or [] if f["people"]), [])
    mine = [p for p in people if p.get("name") == name]
    # only the body's own facing and hands: where the person sits in the frame and how big is the composite's job
    bits = [b.strip(" .") for b in re.split(r"[;:]", MC.framing_words(mine))] if mine else []
    facing = [b for b in bits if re.search(r"(turned|facing|back to|profile|three-quarter)", b)]
    hands = [b.split(".")[0] for b in bits if re.search(r"\bhand\b", b)]
    face = "; ".join(facing) or "toward the camera"
    if re.search(r"turned to the picture's (left|right)", face):
        face += ", the face and chest turned that way, away from the camera, never squared to it"
    return PIECE_WORDS.format(who=name, look=look.rstrip("."), facing=face,
                              hands=("Hands: " + "; ".join(hands) + ". ") if hands else "")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    if a[0] == "targets":
        print(json.dumps(targets(a[1]), indent=1))
    elif a[0] == "words":
        print(person_words(a[1], a[2]))
    elif a[0] == "run":
        r = run(a[1], look="--no-look" not in a)
        print(json.dumps({"ok": r["ok"], "used": r["used"], "rows": [{k: x[k] for k in ("kind", "start_check", "faces")} for x in r["rows"]]}, indent=1, default=str))
    elif a[0] == "compose":
        files = dict(x.split("=", 1) for x in a[3:])
        print(json.dumps({k: v for k, v in compose(a[1], a[2], files).items() if k != "targets"}, indent=1))
    else:
        sys.exit(__doc__)
