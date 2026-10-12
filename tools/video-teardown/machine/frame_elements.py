"""ELEMENTS FROM FRAMES — every person, place and prop of the swipe, cut out of
its real frames (the owner, 2026-10-08: "we can actually work with the real frames
… use those as the references").

The frame map names who is in each shot and where ("Makeup Artist (left, 20%
width)", "Host is centered at 50% width, visible from 10% to 90% height",
"Model center (30-90% width)"); the teardown record names the places and props
with their times. This collects, for each of them, every frame of
`framemap/frames/` it appears in and saves:

    framemap/elements/<kind>-<slug>/
        <slug>-<K>-<index>-<t>.jpg   a crop per frame — the recorded position,
                                     padded 8% of the frame each side; no
                                     position = the full frame (a hard link,
                                     no extra disk). PLACES are full frames,
                                     one per shot (the middle one), with the
                                     people in each shot noted.
        best.jpg                     the largest, clearest crop (the shot where
                                     it is alone / biggest, the sharpest frame
                                     of that shot's middle)
        element.json                 name, kind, shots, times, boxes, frames
                                     used, crops, best
    framemap/elements/index.json     one row per element

POSITIONS, read in this order: a range ("A% to B% width", "A-B% W", "from A%
to B% height"); a single point ("20% width") only when two or more people
share the shot, as that point ± 15%; a side word (left / right / centre) only
when two or more people share the shot. Heights given as a single point are
body-part marks ("eyes at 40% height"), never a box, so they are ignored.

Brand-agnostic: it reads only the run's own frame map and teardown record.
Never asks a model. Idempotent: a crop already on disk is not cut again.

    python3 frame_elements.py <teardown run dir> [--drive]
"""
import argparse, json, os, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAD = 8.0            # % of the frame added on every side of a recorded box
POINT_HALF = 15.0    # a single "20% width" is a box 30% wide around it
SIDES = {"left": (0.0, 55.0), "right": (45.0, 100.0),
         "center": (20.0, 80.0), "centre": (20.0, 80.0), "centered": (20.0, 80.0), "centred": (20.0, 80.0)}
KINDS = ("person", "place", "prop")

_N = r"(\d{1,3}(?:\.\d+)?)"
_RANGE = r"(?:from\s+)?{n}\s*%?\s*(?:-|–|to)\s*{n}\s*%\s*(?:of\s+(?:the\s+)?(?:frame\s+)?)?(?:{axis})\b"
_POINT = r"{n}\s*%\s*(?:of\s+(?:the\s+)?(?:frame\s+)?)?(?:{axis})\b"
AXES = {"w": r"width|wide|w", "h": r"height|tall|h"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-") or "x"


def base_name(who):
    """'Host (face, torso, arms)' -> 'Host'."""
    return re.sub(r"\s*\(.*$", "", str(who or "")).strip()


# ---------------------------------------------------------------- positions

def parse_position(text, crowd=False):
    """{"w": (a, b) | None, "h": (c, d) | None, "how": "range" | "point" | "word"}
    in % of the frame, or None when the text gives no usable position.
    `crowd`: two or more people share the shot — only then do a single point
    or a side word place someone."""
    t = str(text or "")
    out, how = {"w": None, "h": None}, None
    for ax, words in AXES.items():
        m = re.search(_RANGE.format(n=_N, axis=words), t, re.I)
        if m:
            a, b = sorted((float(m.group(1)), float(m.group(2))))
            if b > a:
                out[ax], how = (a, min(b, 100.0)), "range"
    if out["w"] is None and crowd:
        m = re.search(_POINT.format(n=_N, axis=AXES["w"]), t, re.I)
        if m:
            c = float(m.group(1))
            out["w"], how = (max(0.0, c - POINT_HALF), min(100.0, c + POINT_HALF)), how or "point"
        else:
            w = re.search(r"\b(left|right|centred|centered|centre|center)\b", t, re.I)
            if w:
                out["w"], how = SIDES[w.group(1).lower()], how or "word"
    if out["w"] is None and out["h"] is None:
        return None
    out["how"] = how
    return out


def crop_box(pos, width, height, pad=PAD):
    """Pixel box (x0, y0, x1, y1) for a position in %, padded `pad`% of the
    frame on every side and clamped to it. No position = the full frame."""
    if not pos:
        return (0, 0, width, height)
    wa, wb = pos.get("w") or (0.0, 100.0)
    ha, hb = pos.get("h") or (0.0, 100.0)
    wa, wb = max(0.0, wa - pad), min(100.0, wb + pad)
    ha, hb = max(0.0, ha - pad), min(100.0, hb + pad)
    x0, x1 = int(round(width * wa / 100)), int(round(width * wb / 100))
    y0, y1 = int(round(height * ha / 100)), int(round(height * hb / 100))
    return (x0, y0, max(x1, x0 + 1), max(y1, y0 + 1))


def segment(text, name, others):
    """The words about `name` in a frame description: from its first mention to
    the next other name or the end of the sentence."""
    t = str(text or "")
    m = re.search(r"\b" + re.escape(name) + r"\b", t, re.I)
    if not m:
        return ""
    rest = t[m.end():]
    stops = [len(rest)]
    s = re.search(r"\.(\s|$)", rest)
    if s:
        stops.append(s.start())
    for o in others:
        if o.lower() == name.lower():
            continue
        x = re.search(r"\b" + re.escape(o) + r"\b", rest, re.I)
        if x:
            stops.append(x.start())
    return rest[:min(stops)]


# ---------------------------------------------------------------- the record

def _secs(m, s):
    return int(m) * 60 + float(s)


def spans(text):
    """Every 'M:SS(.ms) - M:SS(.ms)' span in a line, in seconds."""
    return [(_secs(a, b), _secs(c, d)) for a, b, c, d in
            re.findall(r"(\d+):(\d{2}(?:\.\d+)?)\s*[-–]\s*(\d+):(\d{2}(?:\.\d+)?)", str(text or ""))]


def _section(tear, head):
    m = re.search(r"\*\*" + head + r"\*\*(.*?)(?=\n\*\*[A-Z ]{4,}\*\*\s*\n|\n\|\s*Timestamp|\n#{2,3} |\Z)", tear, re.S)
    return m.group(1) if m else ""


def record_places(tear):
    """[{"name", "spans"}] from the record's PLACES section."""
    out = []
    for blk in re.split(r"\n(?=\*\*[^*\n]+\*\*\s*\n)", _section(tear, "PLACES")):
        h = re.match(r"\s*\*\*([^*\n]+)\*\*", blk)
        if h:
            ts = re.search(r"Timestamps?:?\**:?\s*(.*)", blk)
            out.append({"name": base_name(h.group(1)), "spans": spans(ts.group(1)) if ts else []})
    return out


def record_props(tear):
    """[{"name", "spans", "what"}] from the record's PROPS section."""
    out = []
    for name, what in re.findall(r"^\s*\*\s+\*\*([^*:\n]+):?\*\*:?\s*(.*)$", _section(tear, "PROPS"), re.M):
        out.append({"name": base_name(name), "spans": spans(what), "what": what.strip()})
    return out


# ---------------------------------------------------------------- collect

def _overlaps(shot, sp):
    return any(a < shot["end"] and b > shot["start"] for a, b in sp)


def _text(m):
    return " ".join(str(m.get(k) or "") for k in ("start_frame", "end_frame")) + " " + \
        " ".join(f"{x.get('who', '')} {x.get('does', '')}" for x in m.get("moments") or [])


def collect(doc, tear=""):
    """{(kind, name): {"shots": {K: {"start": pos, "end": pos}}, ...}} — who and
    what is in which shot, and where, from the frame map (+ the record's places
    and props)."""
    shots = doc.get("shots") or []
    people = list(doc.get("people") or [])
    props = record_props(tear)
    places = record_places(tear)
    prop_names = {slug(p["name"]): p for p in props}
    found = {}

    for s in shots:
        m = s.get("map") or {}
        if "error" in m:
            continue
        names = []
        for w in m.get("who") or []:
            n = base_name(w)
            if n and n not in names:
                names.append(n)
        humans = [n for n in names if slug(n) not in prop_names]
        crowd = len(humans) >= 2
        everyone = names + [p["name"] for p in props]
        for n in names:
            kind = "prop" if slug(n) in prop_names else "person"
            key = (kind, prop_names[slug(n)]["name"] if kind == "prop" else n)
            pos = {e: parse_position(segment(m.get(f"{e}_frame"), n, everyone), crowd and kind == "person")
                   for e in ("start", "end")}
            found.setdefault(key, {})[s["id"]] = pos
        for p in props:
            key = ("prop", p["name"])
            if s["id"] in found.get(key, {}):
                continue
            said = re.search(r"\b" + re.escape(p["name"]) + r"\b", _text(m), re.I)
            if said or (p["spans"] and _overlaps(s, p["spans"])):
                pos = {e: parse_position(segment(m.get(f"{e}_frame"), p["name"], everyone))
                       for e in ("start", "end")}
                found.setdefault(key, {})[s["id"]] = pos
    for pl in places:
        for s in shots:
            if not pl["spans"] or _overlaps(s, pl["spans"]):
                found.setdefault(("place", pl["name"]), {})[s["id"]] = {"start": None, "end": None}
    if not places:
        # no PLACES in the record: the frame map's own backdrop, one place
        for s in shots:
            found.setdefault(("place", "Swipe Set"), {})[s["id"]] = {"start": None, "end": None}
    return found


# ---------------------------------------------------------------- build

def _sharpness(img):
    from PIL import ImageFilter, ImageStat
    g = img.convert("L")
    g.thumbnail((256, 256))
    return ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).mean[0]


def _link(src, dst):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def _area(box, W, H):
    return (box[2] - box[0]) * (box[3] - box[1]) / float(W * H)


def build(run_dir):
    """framemap/elements/ from framemap/framemap.json + framemap/frames/. -> the index."""
    from PIL import Image
    d = Path(run_dir)
    fm_dir = d / "framemap"
    doc = json.loads((fm_dir / "framemap.json").read_text())
    try:
        frames = json.loads((fm_dir / "frames" / "index.json").read_text())["frames"]
    except (OSError, ValueError, KeyError):
        raise SystemExit("no framemap/frames/index.json — run framemap.py --frames-only first")
    try:
        tear = (d / "stages" / "1-teardown.md").read_text()
    except OSError:
        tear = ""
    by_shot = {}
    for f in frames:
        by_shot.setdefault(f["shot"], []).append(f)
    shots = {s["id"]: s for s in doc.get("shots") or []}
    who_in = {sid: [base_name(w) for w in (s.get("map") or {}).get("who") or []] for sid, s in shots.items()}
    W = H = None
    first = next(iter(frames), None)
    if first:
        with Image.open(fm_dir / first["file"]) as im:
            W, H = im.size
    root = fm_dir / "elements"
    root.mkdir(parents=True, exist_ok=True)
    index = []
    for (kind, name), at in sorted(collect(doc, tear).items(), key=lambda kv: (KINDS.index(kv[0][0]), kv[0][1])):
        folder = root / f"{kind}-{slug(name)}"
        folder.mkdir(exist_ok=True)
        rec = {"name": name, "kind": kind, "slug": slug(name), "shots": [], "times": [],
               "boxes": {}, "frames_used": [], "crops": [], "best": None}
        if kind == "place":
            rec["people"] = {}
        for sid in sorted(at, key=lambda k: shots[k]["start"]):
            fs = by_shot.get(sid) or []
            if not fs:
                continue
            s = shots[sid]
            rec["shots"].append(sid)
            rec["times"].append([s["start"], s["end"]])
            pos = at[sid]
            rec["boxes"][sid] = {e: (list(crop_box(pos[e], W, H)) if pos[e] else None) for e in ("start", "end")}
            rec["boxes"][sid]["how"] = (pos["start"] or pos["end"] or {}).get("how") or "full frame"
            rec["frames_used"] += [f["file"] for f in fs]
            if kind == "place":
                rec["people"][sid] = [n for n in who_in.get(sid, []) if n]
                fs = [fs[len(fs) // 2]]
            half = (s["start"] + s["end"]) / 2
            for f in fs:
                p = pos["end"] if (f["t"] >= half and pos["end"]) else (pos["start"] or pos["end"])
                box = crop_box(p, W, H)
                out = folder / f"{slug(name)}-{Path(f['file']).name}"
                src = fm_dir / f["file"]
                if not out.exists():
                    if box == (0, 0, W, H):
                        _link(src, out)
                    else:
                        with Image.open(src) as im:
                            im.crop(box).save(out, quality=85)
                rec["crops"].append({"file": f"elements/{folder.name}/{out.name}", "frame": f["file"],
                                     "shot": sid, "t": f["t"], "box": list(box)})
        if not rec["crops"]:
            continue
        rec["best"] = best_of(rec, shots, who_in, fm_dir, W, H)
        bf = folder / "best.jpg"
        if rec["best"]:
            shutil.copyfile(fm_dir / rec["best"]["file"], bf)
            rec["best"]["copy"] = f"elements/{folder.name}/best.jpg"
        (folder / "element.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        index.append({"kind": kind, "name": name, "folder": f"elements/{folder.name}",
                      "shots": rec["shots"], "frames": len(rec["frames_used"]), "crops": len(rec["crops"]),
                      "best": (rec["best"] or {}).get("copy")})
    body = {"run": d.name, "frame_size": [W, H], "pad_percent": PAD, "elements": index}
    (root / "index.json").write_text(json.dumps(body, indent=1, ensure_ascii=False))
    return body


def best_of(rec, shots, who_in, fm_dir, W, H):
    """The largest, clearest crop: the shot where the element is alone (a place:
    the emptiest), then biggest, then longest; inside it the sharpest of the
    frames around its middle."""
    from PIL import Image

    def rank(sid):
        others = [n for n in who_in.get(sid, []) if n and n != rec["name"]]
        box = rec["boxes"][sid]["start"] or [0, 0, W, H]
        return (-len(others), _area(box, W, H), shots[sid]["end"] - shots[sid]["start"])
    sid = max(rec["shots"], key=rank)
    cands = [c for c in rec["crops"] if c["shot"] == sid]
    mid = len(cands) // 2
    cands = cands[max(0, mid - 4): mid + 5]
    best, score = None, -1.0
    for c in cands:
        try:
            with Image.open(fm_dir / c["file"]) as im:
                sc = _sharpness(im)
        except OSError:
            continue
        if sc > score:
            best, score = c, sc
    return dict(best, sharpness=round(score, 2)) if best else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--drive", action="store_true", help="also copy framemap/ to the run's Drive folder")
    a = ap.parse_args(argv)
    body = build(a.run_dir)
    for e in body["elements"]:
        print(f"  {e['kind']:6} {e['name']:28} shots {','.join(e['shots'])} · {e['crops']} crops · best {e['best']}")
    print(f"{len(body['elements'])} elements → {Path(a.run_dir) / 'framemap' / 'elements'}")
    if a.drive:
        sys.path.insert(0, str(HERE))
        import framemap as FM
        got = FM.mirror(a.run_dir)
        print(f"Drive: {got[1]} copied, {got[2]} already there → {got[0]}" if got else "Drive: not a machine run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
