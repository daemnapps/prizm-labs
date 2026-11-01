#!/usr/bin/env python3
"""The product from its 3D model — the thin CLI over image_production.product3d.

    product3d.py render --brand <b> --product <p> --out <png> [--pose <id>]
                        [--azimuth 30 --elevation 10 --focal 50] [--size 1024]
                        [--light-azimuth -40 --light-elevation 40 --warmth 0.2]
    product3d.py place  --scene <png> --render <png> --out <png>
                        (--box l,t,r,b | --anchor x,y (--px-per-cm k | --height h))
    product3d.py iou    --brand <b> --product <p> --out <dir> [--angles 0,45,90,180]
    product3d.py poses  --brand <b> --product <p>

`render` writes the product posed on transparent (+ `-mask.png`, + `.json`);
`place` composites one render into a scene with its contact shadow, light and
grain matched; `iou` scores the model's silhouette against the kit's real
turntable cut-outs. the owner never runs this — a session does, and hands him the
picture.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))      # APPEND, never insert at 0
from image_production import product3d as D                # noqa: E402


def _kit(a):
    kit = D.find_kit(a.brand, a.product)
    if not D.has_model(kit):
        sys.exit(f"`{a.product}` ({a.brand}) has no kit with a 3D model ({D.DECLARATION})")
    return kit


def _nums(s):
    return [float(v) for v in s.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["render", "place", "iou", "poses"])
    ap.add_argument("--brand")
    ap.add_argument("--product")
    ap.add_argument("--pose")
    ap.add_argument("--out")
    ap.add_argument("--azimuth", type=float, default=0.0)
    ap.add_argument("--elevation", type=float, default=8.0)
    ap.add_argument("--focal", type=float, default=50.0)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--light-azimuth", type=float)
    ap.add_argument("--light-elevation", type=float)
    ap.add_argument("--warmth", type=float)
    ap.add_argument("--scene")
    ap.add_argument("--render")
    ap.add_argument("--box")
    ap.add_argument("--anchor")
    ap.add_argument("--px-per-cm", type=float)
    ap.add_argument("--height", type=float)
    ap.add_argument("--angles", default="0,45,90,135,180,225,270,315")
    a = ap.parse_args(argv)

    if a.command == "poses":
        d = D.declaration(_kit(a))
        for pid, p in d["poses"].items():
            print(f"  {pid:<12} {'(default) ' if pid == d.get('default_pose') else ''}{p.get('what', '')}")
        return 0
    if a.command == "render":
        light = {k: v for k, v in (("azimuth", a.light_azimuth), ("elevation", a.light_elevation),
                                   ("warmth", a.warmth)) if v is not None}
        rec = D.render_product(_kit(a), a.pose, {"azimuth": a.azimuth, "elevation": a.elevation,
                                                  "focal_mm": a.focal},
                               a.out, size_px=a.size, light=light, samples=a.samples)
        print(json.dumps({k: rec.get(k) for k in ("file", "source", "pose", "px_per_cm",
                                                  "contact_px", "assembly_cm", "why")}, indent=1))
        return 0
    if a.command == "place":
        kw = {}
        if a.box:
            kw["box"] = _nums(a.box)
        else:
            kw["anchor"] = _nums(a.anchor)
            if a.px_per_cm:
                kw["px_per_cm"] = a.px_per_cm
            else:
                kw["height_px"] = a.height
        print(json.dumps(D.place_product(a.scene, a.render, a.out, **kw), indent=1))
        return 0
    if a.command == "iou":
        r = D.silhouette_iou(_kit(a), [int(v) for v in _nums(a.angles)], a.out)
        Path(a.out, "iou.json").write_text(json.dumps(r, indent=1))
        for row in r["angles"]:
            print(f"  {row['angle']:>4}°  IoU {row['iou']}")
        print(f"  mean {r['mean']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
