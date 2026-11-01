"""THE EFFECTS — an overlay or animation the swipe runs inside a shot, made as its own piece (2026-10-27).

2026-10-28: how a scene handles an effect that is neither its start nor its end.

The scene plan (storyboard_plan.py `effects_for`) lists every effect per shot: what ours shows, the swipe moment it
copies and the line it plays under. This makes each one, never inside the acting clip:

    1. the swipe frame in the middle of its effect moment, and that moment cut out as a clip
    2. ONE still in the swipe's effect style showing OURS, on plain black, no person (the picture door, the swipe
       frame as Image 1)
    3. ONE clip from that still with the swipe's moment as the motion reference (Video 1: motion only) and the
       brief's beats — Seedance, silent
    4. a record the edit reads: where the effect sits (the shot, the line it plays under)

    python3 effects.py make <production run> [--only G01-FX1] [--dry-run]

Writes runs/video-production/<brand>/<label>/effects/<id>/ (swipe-frame.jpg, swipe-segment.mp4, still.png,
clip.mp4, effect.json). Brand-agnostic: everything comes from the run's own files.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_fx_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(mod)
    return mod


def teardown_of(run: Path) -> Path:
    rj = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    b = rj.get("brief_from") or ""
    t = Path(b).parent.parent if b else None
    if t is not None and not t.is_absolute():
        t = WS / t
    return t if t is not None and (t / "source.mp4").is_file() else WS / "runs" / "video-teardown" / "_work" / run.name


def effects_of(run: Path) -> list[dict]:
    sb = json.loads((run / "storyboard.json").read_text())
    return [{**e, "section": g["id"]} for g in sb.get("sections") or [] for e in g.get("effects") or []]


# THE PRODUCT'S OWN LOOK (2026-10-27). An effect that shows the product, its paste or its ingredients carries the product kit's own in-use photos
# (the real paste on a real hand) and the kit's never-show lines, so its colour and texture are the real thing's.
def product_refs(run: Path, e: dict) -> tuple[list, list]:
    td = teardown_of(run)
    rj = json.loads((td / "run.json").read_text()) if (td / "run.json").is_file() else {}
    brand, product = run.parent.name, rj.get("product") or ""
    kit_p = WS / "runs" / "ai-elements" / brand / "products" / product / "kit.json"
    if not product or not kit_p.is_file():
        return [], []
    kit = json.loads(kit_p.read_text())
    beh = kit.get("behaviour") or {}
    # the product's own words — its name and the ingredients on its label — say an effect shows it; colour words never do
    label = " ".join(str(x) for x in (kit.get("label_read") or kit.get("label_words") or []))
    words = {w for w in re.findall(r"[a-z]{5,}", label.lower()) if w not in ("skincare", "the best", "best")}
    text = str(e.get("ours") or "").lower()
    if not (words & set(re.findall(r"[a-z]{5,}", text)) or re.search(r"\b(scrub|serum|cream)\b", text)):
        return [], []
    refs = [WS / r["file"] for r in beh.get("receipts") or []
            if str(r.get("for")) in ("in use", "texture", "colour") and str(r.get("file", "")).lower().endswith((".jpg", ".png", ".jpeg"))]
    src = kit_p.parent / "sources"
    refs += [f for f in sorted(src.glob("*swatch*")) + sorted(src.glob("*applying*")) if f.is_file()]
    seen, out = set(), []
    for f in refs:
        if f.is_file() and f.name not in seen:
            seen.add(f.name); out.append(f)
    return out[:2], [str(x) for x in beh.get("never_show") or [] if re.search(r"paste|cream|grain|colou?r|blue|white", str(x), re.I)]


def upscaled(clip: Path) -> str:
    """NO LOW-RESOLUTION SHOT (2026-10-28): an effect is made at the
    clip door's low resolution like every clip, so it is upscaled on this Mac the same way before the edit takes it.
    The made clip is kept beside it as clip-made.mp4."""
    cr = _load("clips_run")
    cfg = json.loads((HERE / "v2.json").read_text())["clips"]
    if cr._height(clip) >= int((cfg.get("upscale_local") or {}).get("target_height", 1920)) * 0.6:
        return "already"
    made = clip.with_name("clip-made.mp4")
    if not made.is_file():
        clip.replace(made)
    cr.upscale_local(made, clip, cfg)
    return f"from {made.name}"


def our_picture(run: Path, section: str):
    """Our own scene's approved start picture for this effect's section: the effect is drawn on its object."""
    cp = _load("clips_plan")
    sb = json.loads((run / "storyboard.json").read_text())
    g = next((x for x in sb.get("sections") or [] if x["id"] == section), None)
    pid = cp.picture_ids(g).get("start") if g else None
    f = cp.picture_file(run, pid) if pid else None
    return Path(f) if f and Path(f).is_file() else None


def still_prompt(e: dict, refs=(), never=(), ours=None) -> str:
    if ours:
        # ON OUR OWN OBJECT (2026-10-28): the swipe's graphic
        # is drawn ON the object in hand, so ours is drawn on the matching object in our own scene, never a separate panel
        n = 3 + len(refs)
        return ("Image 1 is a frame from a video ad: an object in the scene turns see-through in an animated infomercial "
                f"style ({e['swipe'].get('what') or 'the effect'}). Image 2 is our own scene. Make ONE picture that is "
                "Image 2 exactly — the same person, hands, object, room, light and framing — with ONE change: the object "
                "in Image 2 that plays the part of the object in Image 1 turns see-through in exactly Image 1's style "
                "(the same see-through layers, glow, colours and finish), showing inside it: "
                f"{e['ours']} This is the effect's first moment, before anything moves. No words, no logos."
                + (" The paste, its colour and its grains are exactly the real product's in IMAGE "
                   + " and IMAGE ".join(str(i) for i in range(3, n)) + "; never: " + "; ".join(never) + "." if refs else ""))
    return ("Image 1 is a frame from a video ad. It shows an animated see-through graphic laid over an object "
            f"({e['swipe'].get('what') or 'the effect'}). Make ONE picture in exactly that graphic's style: the same "
            "clean infomercial look, the same see-through layers, the same colours, glow and finish. It shows: "
            f"{e['ours']} This is the effect's first moment, before anything moves. The graphic fills the frame, "
            "centred, on a plain pure black background. No person, no face, no hands, no room, no words, no logos."
            + (f" The paste, its colour and its grains are exactly the real product's in IMAGE 2"
               f"{' and IMAGE 3' if len(refs) > 1 else ''}; never: " + "; ".join(never) + "." if refs else ""))


def clip_prompt(e: dict, ours=None) -> str:
    if ours:
        beats = " ".join(f"{i + 1}) {b}." for i, b in enumerate([x.strip().rstrip(".") for x in
                                                                  str(e["ours"]).split(";") if x.strip()]))
        return ("Image 1 is the first frame. Video 1 is the motion only: copy how its object turns see-through, how the "
                "effect fills, flows and settles, its timing and pace; take nothing else from it. Inside the see-through "
                "object, in order: " + beats + " Everything outside the object stays exactly as in Image 1: the same "
                "person, hands, room and light. The camera holds still. No words.")
    beats = " ".join(f"{i + 1}) {b}." for i, b in enumerate([x.strip().rstrip(".") for x in
                                                              str(e["ours"]).split(";") if x.strip()]))
    return ("Image 1 is the first frame. Video 1 is the motion only: copy how its see-through effect fills, flows and "
            "settles, its timing and pace; take nothing else from it. In order: " + beats +
            " The plain black background stays black. The camera holds still. No person, no hands, no words.")


def make(run: Path, only: list | None = None, dry_run: bool = False) -> list[dict]:
    run = Path(run).resolve()
    td = teardown_of(run)
    src = td / "source.mp4"
    out = []
    for e in effects_of(run):
        if only and e["id"] not in only:
            continue
        sw = e.get("swipe") or {}
        if sw.get("start") is None:
            print(f"{e['id']}: no swipe moment found for it — named in the scene plan, made by hand")
            continue
        d = run / "effects" / e["id"]
        d.mkdir(parents=True, exist_ok=True)
        a, z = float(sw["start"]), float(sw["end"])
        frame, seg = d / "swipe-frame.jpg", d / "swipe-segment.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a + min(1.0, (z - a) / 2):.2f}", "-i", str(src),
                        "-frames:v", "1", "-q:v", "2", str(frame)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{z:.2f}", "-i", str(src),
                        "-an", "-c:v", "libx264", "-crf", "20", "-preset", "fast", str(seg)], check=True)
        old = json.loads((d / "effect.json").read_text()) if (d / "effect.json").is_file() else {}
        if old.get("ours_override"):                     # a person's fix to this one effect, kept across re-makes
            e = {**e, "ours": old["ours_override"]}
        prefs, never = product_refs(run, e)
        ours = our_picture(run, e["section"]) if e.get("on_object", True) else None
        rec = {"id": e["id"], "name": e["name"], "section": e["section"], "scene": e.get("scene"),
               "plays_over": e.get("plays_over"), "ours": e["ours"], "swipe": sw,
               "still_prompt": still_prompt(e, prefs, never, ours), "clip_prompt": clip_prompt(e, ours),
               "on": str(ours.relative_to(run)) if ours else None,
               "product_refs": [str(p) for p in prefs], "ours_override": old.get("ours_override"),
               "seconds": round(max(4.0, z - a), 1)}
        still = d / "still.png"
        if not still.is_file():
            _load("direct_openai").generate(rec["still_prompt"], [frame] + ([ours] if ours else []) + list(prefs), still,
                                            dry_run=dry_run)
        clip = d / "clip.mp4"
        if not dry_run and not clip.is_file():
            # one more try when the maker refuses (a refused take is often the dice, not the words); a second refusal is
            # recorded on this effect and the next one is still made
            for attempt in (1, 2):
                try:
                    got = _load("seedance").motion(rec["clip_prompt"], still, clip, seconds=rec["seconds"], no_people=True,
                                                   whole=True, videos=[seg])
                    rec["made"] = {k: got.get(k) for k in ("model", "request_id")}
                    rec.pop("refused", None)
                    break
                except RuntimeError as err:
                    rec["refused"] = str(err)[:300]
                    print(f"{e['id']}: try {attempt} refused — {str(err)[:120]}")
        if not dry_run and clip.is_file():
            rec["upscaled"] = upscaled(clip)
        rec.update(still=str(still.relative_to(run)), clip=str(clip.relative_to(run)) if clip.is_file() else None)
        (d / "effect.json").write_text(json.dumps(rec, indent=1))
        print(f"{e['id']}: {'planned' if dry_run else 'made'} — {rec['clip'] or 'no clip yet'}")
        out.append(rec)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("run")
    m.add_argument("--only", action="append", default=[])
    m.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    make(Path(a.run), a.only or None, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
