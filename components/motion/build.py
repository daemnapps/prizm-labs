#!/usr/bin/env python3
"""Build: each stand-in made to its cast member's body, and checked (the guide must never show the wrong body).

    python3 build.py <scene dir>              measure every cast member's build and write <scene>/motion/build.json
    python3 build.py check <scene dir>        render the stand-ins at rest and measure them the same way (match-build.json)

A video model copies the stand-in's build along with its moves: a slim woman rehearsed by a barrel-shaped figure comes
out wide and waistless. So each figure's torso is shaped from its cast member:

  measured    the cast sheet (take.json `cast.NAME.sheet`): the front view found with the people reader, the person's
              outline read (MediaPipe's person mask), and the torso's width read at the chest, the waist and the hips,
              each as a share of the torso's length (shoulder joints to hip joints), with the arms kept out of it
  from words  where there is no sheet, or it cannot be read: the cast member's description (`look`: woman or man, and
              slim / petite / broad / heavy / athletic / curvy)

Hips read off a sheet are held to what a body of that sex carries against its chest (a jacket's hem, a skirt or a hand
is clothing, not hips); both numbers are kept. Widths go to blocking_blender.py as each person's `build` (half-widths in metres on a 0.48 m torso). `check` renders
every stand-in alone at rest, front-on, and measures its outline with the same rule, so the row compares like with like:
`build · NAME` passes when the stand-in's chest, waist and hips are each within 15% of the cast member's.
No brand, product or person is named here.
"""
import json
import math
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TORSO_M = 0.48                     # the stand-in's torso, shoulder joints to hip joints, in metres
# where each width is read, as a share of the way from the shoulder joints down to the hip joints: the widest row in the
# bust band, the narrowest in the waist band, the widest in the hip band (each body has its own waist line)
LEVELS = {"chest": (0.30, 0.48, max), "waist": (0.50, 0.85, min), "hips": (0.95, 1.20, max)}
BAND = 0.15                        # a stand-in passes within 15% of the cast member's width at each level
# widths as a share of torso length (a plain adult, read off people standing front-on)
BASE = {"woman": {"chest": 0.60, "waist": 0.50, "hips": 0.72}, "man": {"chest": 0.66, "waist": 0.60, "hips": 0.66}}
WORDS = [(("slim", "slender", "thin", "petite", "skinny", "willowy", "lean"), {"chest": 0.9, "waist": 0.86, "hips": 0.9}),
         (("broad", "big", "heavy", "heavyset", "stocky", "burly", "large", "plus-size", "chubby", "fat"), {"chest": 1.15, "waist": 1.28, "hips": 1.12}),
         (("athletic", "muscular", "fit", "toned"), {"chest": 1.06, "waist": 0.92, "hips": 0.98}),
         (("curvy", "hourglass", "voluptuous"), {"chest": 1.06, "waist": 0.9, "hips": 1.14})]
WOMAN = ("woman", "girl", "she", "her ", "lady", "female", "mother", "mom", "wife", "girlfriend", "dress")


def from_words(look, name=""):
    """Widths from a description: woman or man, then the build words."""
    text = (" %s %s " % (look or "", name or "")).lower()
    who = "woman" if any(w in text for w in WOMAN) else "man"
    out = dict(BASE[who])
    said = []
    for words, k in WORDS:
        hit = next((w for w in words if (" %s " % w) in text or (" %s," % w) in text), None)
        if hit:
            said.append(hit)
            out = {lv: out[lv] * k[lv] for lv in out}
    return {"widths": {k: round(v, 3) for k, v in out.items()}, "from": "words", "said": "%s%s" % (who, (", " + ", ".join(said)) if said else "")}


def widths(mask, pts, arm_r=0.09):
    """The torso's width at each level, as a share of torso length. `mask`: rows of 0/1 (the person's outline); `pts`:
    pixel points {"lsh", "rsh", "lhip", "rhip", "lel", "rel", "lwr", "rwr"} (arms may be missing). A row's width is the
    run of outline that holds the body's middle line, cut where an arm hangs against it."""
    H, W = len(mask), len(mask[0])
    sh = ((pts["lsh"][0] + pts["rsh"][0]) / 2, (pts["lsh"][1] + pts["rsh"][1]) / 2)
    hp = ((pts["lhip"][0] + pts["rhip"][0]) / 2, (pts["lhip"][1] + pts["rhip"][1]) / 2)
    torso = math.dist(sh, hp)
    if torso < 8:
        return None

    def arm_x(side, y):
        """Where an arm crosses row y, if it does: the shoulder-elbow-wrist line, interpolated."""
        chain = [pts.get(side + "sh"), pts.get(side + "el"), pts.get(side + "wr")]
        chain = [p for p in chain if p]
        if len(chain) >= 2 and pts.get(side + "wr"):         # the hand hangs on past the wrist: a hand's length more
            e, w = chain[-2], chain[-1]
            L = math.dist(e, w) or 1.0
            chain.append((w[0] + (w[0] - e[0]) / L * 0.4 * torso, w[1] + (w[1] - e[1]) / L * 0.4 * torso))
        for a, b in zip(chain, chain[1:]):
            if min(a[1], b[1]) <= y <= max(a[1], b[1]) and abs(b[1] - a[1]) > 1e-6:
                return a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])
        return None
    def row_width(f):
        y = int(round(sh[1] + (hp[1] - sh[1]) * f))
        if not 0 <= y < H:
            return None
        cx = int(round(sh[0] + (hp[0] - sh[0]) * f))
        row = mask[y]
        if not (0 <= cx < W) or not row[cx]:
            return None
        a = b = cx
        while a > 0 and row[a - 1]:
            a -= 1
        while b < W - 1 and row[b + 1]:
            b += 1
        # an arm hanging against the body is not body: the run stops an arm's half-width short of where it crosses
        for side in ("l", "r"):
            x = arm_x(side, y)
            if x is None:
                continue
            if x < cx and a <= x:                     # the run reaches past the arm's middle: arm and body touch here
                a = max(a, int(x + arm_r * torso))
            elif x >= cx and b >= x:
                b = min(b, int(x - arm_r * torso))
        return (b - a + 1) / torso if b > a else None
    out = {}
    for lv, (f0, f1, pick) in LEVELS.items():
        got = [w for w in (row_width(f0 + (f1 - f0) * k / 12.0) for k in range(13)) if w]
        if len(got) >= 4:
            out[lv] = round(pick(sorted(got)[1:-1] if len(got) > 5 else got), 3)     # the most extreme row but one each side (a stray row is not the body)
    return out or None


# ---------------------------------------------------------------- the cast sheet (runs under the reader's Python)

def _sheet(path):
    import cv2
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision as V
    from rtmlib import Wholebody
    import motion as MO
    img = cv2.imread(str(path))
    if img is None:
        return {"error": "the sheet could not be opened"}
    H, W = img.shape[:2]
    kps, scs = Wholebody(mode="balanced", backend="onnxruntime", device="cpu", to_openpose=False)(img)
    best = None
    for kp, sc in zip(kps, scs):
        # the front view: both shoulders and hips seen, and the face itself seen (the face's own points read clearly: a
        # back view has eyes guessed on the back of the head, never a face); of those, the one whose face reads best
        if min(sc[5], sc[6], sc[11], sc[12]) < 0.5:
            continue
        face = float(sc[23:91].mean())
        if face < 0.5:
            continue
        tall = float(kp[:17, 1][sc[:17] > 0.3].max() - kp[:17, 1][sc[:17] > 0.3].min())
        if best is None or face > best[3]:
            best = (tall, kp, sc, face)
    if best is None:
        return {"error": "no front view found on the sheet"}
    _, kp, sc, _ = best
    seen = sc[:17] > 0.3
    x0, x1 = max(0, int(kp[:17, 0][seen].min() - 0.25 * best[0] * 0.5)), min(W, int(kp[:17, 0][seen].max() + 0.25 * best[0] * 0.5))
    y0, y1 = max(0, int(kp[:17, 1][seen].min() - 0.15 * best[0])), min(H, int(kp[:17, 1][seen].max() + 0.05 * best[0]))
    crop = np.ascontiguousarray(cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
    pose = V.PoseLandmarker.create_from_options(V.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MO.model("pose")), running_mode=V.RunningMode.IMAGE, num_poses=1,
        min_pose_detection_confidence=0.2, output_segmentation_masks=True))
    r = pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
    if not r.segmentation_masks:
        return {"error": "the person's outline could not be read"}
    m = (r.segmentation_masks[0].numpy_view() > 0.5).astype("uint8")
    names = {"lsh": 5, "rsh": 6, "lel": 7, "rel": 8, "lwr": 9, "rwr": 10, "lhip": 11, "rhip": 12}
    pts = {k: (float(kp[i][0] - x0), float(kp[i][1] - y0)) for k, i in names.items() if sc[i] > 0.35}
    w = widths(m.tolist(), pts)
    if not w or len(w) < 3:
        return {"error": "the torso's widths could not all be read (%s)" % (", ".join(sorted(w or {})) or "none")}
    return {"widths": w, "from": "sheet", "sheet": str(path)}


def measure_sheet(path):
    """A cast sheet's front view measured (in the reader's Python). {"widths": {...}} or {"error": ...}."""
    import motion as MO
    r = subprocess.run([MO.reader_python(), str(HERE / "build.py"), "_sheet", str(path)], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": "the sheet reader failed: " + (r.stderr or r.stdout)[-200:]}


def for_scene(scene_dir, take=None):
    """Every cast member's build for this scene, measured from their sheet where it can be, else from their words.
    Kept in <scene>/motion/build.json (a sheet is read again only when it changes)."""
    d = Path(scene_dir) / "motion"
    take = take or json.loads((Path(scene_dir) / "take.json").read_text())
    f = d / "build.json"
    try:
        old = json.loads(f.read_text())
    except (OSError, ValueError):
        old = {}
    out = {}
    for name, c in (take.get("cast") or {}).items():
        c = c if isinstance(c, dict) else {"sheet": c}
        sheet = Path(c["sheet"]) if c.get("sheet") else None
        stamp = round(sheet.stat().st_mtime, 3) if sheet and sheet.exists() else None
        was = old.get(name) or {}
        if stamp and was.get("from") == "sheet" and was.get("stamp") == stamp:
            was["measured"] = was.get("measured") or was["widths"]          # the sheet is not read again; the body rule is
            was["widths"], was["held_to_a_body"] = plausible(was["measured"], c.get("look"), name)
            out[name] = was
            continue
        got = measure_sheet(sheet) if stamp else {"error": "no cast sheet"}
        if got.get("widths"):
            w, changed = plausible(got["widths"], c.get("look"), name)
            got.update({"measured": got["widths"], "widths": w, "held_to_a_body": changed, "stamp": stamp,
                        "said": from_words(c.get("look"), name)["said"]})
            out[name] = got
        else:
            w = from_words(c.get("look"), name)
            w["why_not_sheet"] = got.get("error")
            out[name] = w
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1))
    return out


HIP_CAP = {"man": 1.12, "woman": 1.55}     # hips at most this share of the chest: a sheet's jacket hem or skirt is clothing, not hips


def plausible(w, look, name=""):
    """A measured build held to a body: the hips read off a sheet take in a jacket's hem, a skirt or a hand, so they are
    kept within what a body of that sex carries against its chest. Returns (widths, what was changed)."""
    who = "woman" if any(x in (" %s %s " % (look or "", name or "")).lower() for x in WOMAN) else "man"
    out, said = dict(w), []
    cap = HIP_CAP[who] * max(out.get("chest", 0), out.get("waist", 0))
    if out.get("hips") and cap and out["hips"] > cap:
        said.append("hips %.2f read off the sheet held to %.2f (%s: clothing, not hips)" % (out["hips"], cap, who))
        out["hips"] = round(cap, 3)
    return out, said


def to_standin(w):
    """Widths (shares of torso length) as the stand-in's half-widths in metres: blocking_blender's `build`."""
    return {k: round(w[k] * TORSO_M / 2, 4) for k in ("chest", "waist", "hips") if k in w}


# ---------------------------------------------------------------- the check: the stand-ins rendered and measured

def check(scene_dir, builds=None):
    """Each stand-in rendered alone at rest, front-on, its outline measured with the same rule as the sheet, set against
    its cast member. Writes <scene>/motion/match-build.json (rows) and build-lineup.png."""
    import motion as MO
    d = Path(scene_dir) / "motion"
    builds = builds or json.loads((d / "build.json").read_text())
    names = list(builds)
    work = d / "build-lineup"
    work.mkdir(parents=True, exist_ok=True)
    spec = {"fps": 16, "seconds": 0.13, "size": [240 * max(1, len(names)), 480], "transparent": True, "render": True,
            "people": [{"name": n, "at": [1.0 * i, 3.0], "face": 0, "build": to_standin(builds[n]["widths"])} for i, n in enumerate(names)],
            "beats": [], "sky": [1, 1, 1], "floor": [1, 1, 1], "no_floor": True,
            "camera": {"at": [0.5 * (len(names) - 1), -3.0, 0.9], "look": [0.5 * (len(names) - 1), 3.0, 0.9], "lens": 50,
                       "ortho": max(2.2, 1.0 * len(names) + 0.2)}}
    (work / "spec.json").write_text(json.dumps(spec))
    r = subprocess.run([MO.blender(), "-b", "--factory-startup", "-P", str(HERE / "blocking_blender.py"), "--", str(work / "spec.json"), str(work)],
                       capture_output=True, text=True)
    png = work / "f-0001.png"
    if r.returncode or not png.exists():
        raise SystemExit("the stand-ins could not be rendered for the build check: " + (r.stderr or r.stdout)[-300:])
    m = subprocess.run([MO.reader_python(), str(HERE / "build.py"), "_lineup", str(work)], capture_output=True, text=True)
    try:
        got = json.loads(m.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise SystemExit("the stand-ins could not be measured: " + (m.stderr or m.stdout)[-300:])
    rows = []
    for n in names:
        cast, mine = builds[n]["widths"], got.get(n) or {}
        src = "the cast sheet" if builds[n].get("from") == "sheet" else "the cast member's description (%s)" % builds[n].get("said")
        if not mine:
            rows.append({"beat": 0, "name": "build · " + n, "ok": None, "short": "not measured", "detail": "The stand-in's outline could not be read.", "holds": False})
            continue
        off = {lv: (mine[lv] / cast[lv] - 1) for lv in cast if lv in mine and cast[lv]}
        worst = max(off, key=lambda k: abs(off[k])) if off else None
        ok = bool(off) and all(abs(v) <= BAND for v in off.values())
        rows.append({"beat": 0, "name": "build · " + n, "ok": ok,
                     "short": "as the cast" if ok else "%s %d%% %s" % (worst, round(abs(off[worst]) * 100), "wider" if off[worst] > 0 else "narrower"),
                     "detail": "The stand-in against %s, each as a share of torso length: %s. Within %d%% at every level passes." % (
                         src, "; ".join("%s %.2f (cast %.2f)" % (lv, mine.get(lv, 0), cast[lv]) for lv in cast), round(BAND * 100)),
                     "holds": builds[n].get("from") == "sheet", "reference": cast, "clip": mine})
    rec = {"clip": "build", "rows": rows, "passed": sum(1 for r in rows if r["ok"] is True), "failed": sum(1 for r in rows if r["ok"] is False),
           "held_by": ["%s: %s" % (r["name"], r["short"]) for r in rows if r["ok"] is False and r.get("holds")],
           "open": sum(1 for r in rows if r["ok"] is None), "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (d / "match-build.json").write_text(json.dumps(rec, indent=1))
    try:
        (d / "build-lineup.png").write_bytes(png.read_bytes())
    except OSError:
        pass
    return rec


def _lineup(work):
    """Runs under the reader's Python: the lineup render's alpha read as each stand-in's outline, measured at their
    exact joints (pose.json from the render)."""
    import cv2
    work = Path(work)
    img = cv2.imread(str(work / "f-0001.png"), cv2.IMREAD_UNCHANGED)
    pose = json.loads((work / "pose.json").read_text())
    H, W = img.shape[:2]
    alpha = (img[:, :, 3] > 127).astype("uint8") if img.shape[2] == 4 else None
    out = {}
    if alpha is None:
        return out
    for p in pose["frames"][0]["people"]:
        b = p["body33"]
        pts = {k: (b[i][0] * W, b[i][1] * H) for k, i in (("lsh", 11), ("rsh", 12), ("lel", 13), ("rel", 14), ("lwr", 15), ("rwr", 16), ("lhip", 23), ("rhip", 24))}
        w = widths(alpha.tolist(), pts)
        if w:
            out[p.get("name") or str(p["id"])] = w
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "_sheet":
        print(json.dumps(_sheet(a[1])))
    elif a[0] == "_lineup":
        print(json.dumps(_lineup(a[1])))
    elif a[0] == "check":
        rec = check(a[1])
        for r in rec["rows"]:
            print("%s  %-24s %s" % ({True: "✓", False: "✗", None: "–"}[r["ok"]], r["name"], r["short"]))
    else:
        print(json.dumps(for_scene(a[0]), indent=1))
