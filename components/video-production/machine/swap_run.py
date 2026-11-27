"""swap_run — run a production run's SWAP orders on Higgsfield, by the machine (2026-10-20).

The SWAP route of SHOT-ROUTES.md: route_facts.py wrote swap-orders.json at the start of the run
(the frame map's own shot clip per scene); this cuts each clip to its span, pads it to the
model's 4-second floor, sends the cast member's full sheet and the standard cast_swap prompt to
Genjutsu object swap over the API (higgsfield_api.py), and saves the result into the run.

    python3 swap_run.py <production run> --brand <brand> --cast WHO=<cast slug> [...] [--dry-run]
                        [--only S1,S4] [--resolution 1080p]

Every order gets its status, request id, credits note and the file on swap-orders.json; a finished
order is never re-sent. Brand-agnostic: the cast folder comes from the brand's casting root.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR_S = 4.0


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_sw_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# THE SWAP MODEL IS THE HOUSE'S (verify 2026-10-21 row 17, VIDEO-RULINGS V2): swipe_footage.swap, on the cloud API
MODEL = _load("house").swap()["api"]


def _ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, args)], check=True)


def _dur(p) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def prepare_clip(order: dict, shot_start: float, out: Path) -> tuple:
    """The scene's span of its shot clip, padded forward+reverse to the 4 s floor. Returns (file, kept seconds)."""
    src = Path(order["clip"])
    span = order.get("span")
    a = max(0.0, (span[0] - shot_start)) if span else 0.0
    length = (span[1] - span[0]) if span else _dur(src)
    fwd = out.with_name(out.stem + "-fwd.mp4")
    _ff("-ss", a, "-i", src, "-t", length, "-an", "-c:v", "libx264", "-crf", 18, fwd)
    kept = _dur(fwd)
    if kept >= FLOOR_S:
        fwd.rename(out)
        return out, kept
    rev = out.with_name(out.stem + "-rev.mp4")
    _ff("-i", fwd, "-vf", "reverse", "-an", "-c:v", "libx264", "-crf", 18, rev)
    lst = out.with_name(out.stem + ".txt")
    lst.write_text(f"file '{fwd.name}'\nfile '{rev.name}'\n")
    _ff("-f", "concat", "-safe", 0, "-i", lst, "-c", "copy", out)
    return out, kept


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run a production run's SWAP orders on Higgsfield.")
    ap.add_argument("run")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--cast", action="append", default=[], help="WHO=<cast slug>, once per person")
    ap.add_argument("--also", default="", help="a second person in the shot: <cast slug>[:<look words>], swapped too")
    ap.add_argument("--also-state", default="before", choices=["before", "after", ""])
    ap.add_argument("--only", default="")
    ap.add_argument("--resolution", default="1080p")
    ap.add_argument("--keep", default="", help="what the clip must keep (default: cast_swap's standard)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prepare-only", action="store_true",
                    help="cut and pad every clip and list its sheets, send nothing: for the session's Higgsfield door")
    a = ap.parse_args(argv)
    run = Path(a.run)
    orders_p = run / "swap-orders.json"
    orders = json.loads(orders_p.read_text())
    cast = dict(c.split("=", 1) for c in a.cast)
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    cs = _load("cast_swap")
    hf = None if (a.dry_run or a.prepare_only) else _load("higgsfield_api")
    up_cache_p = run / "hf-uploads.json"
    up_cache = json.loads(up_cache_p.read_text()) if up_cache_p.exists() else {}

    def url_of(p: Path) -> str:
        h = hashlib.sha1(p.read_bytes()).hexdigest()
        if h not in up_cache:
            up_cache[h] = hf.upload(p)
            up_cache_p.write_text(json.dumps(up_cache, indent=1))
        return up_cache[h]

    shots_start = {}
    plan = json.loads((run / "plan.json").read_text())
    fm_dir = _load("route_facts").framemap_of(run, plan)
    if fm_dir:
        for s in json.loads((fm_dir / "framemap.json").read_text()).get("shots") or []:
            shots_start[s["id"]] = float(s.get("start") or 0)

    done = 0
    for o in orders:
        if only and o["scene"] not in only:
            continue
        if o.get("status") == "completed" and o.get("file"):
            continue
        slug = cast.get(o.get("who") or "") or (next(iter(cast.values())) if len(cast) == 1 else None)
        if not slug or not o.get("clip"):
            o["status"] = "held"
            o["why"] = "no cast slug for " + str(o.get("who")) if not slug else "no shot clip in the frame map"
            print(f"  {o['scene']}: held — {o['why']}")
            continue
        refs = cs.refs(slug, a.brand)
        prompt = cs.prompt(keep=a.keep)
        if a.also:
            # TWO PEOPLE IN ONE SHOT: the first person's full sheet, then the second's master and look
            two, _, look = a.also.partition(":")
            d2 = cs.cast_dir(two, a.brand)
            lk = cs.look_for(d2, look)
            refs = refs[:5] + [d2 / "master.png"] + ([lk] if lk else [])
            n1 = len(refs) - (2 if lk else 1)
            prompt = (prompt.replace("Replace the person completely with the person in the reference sheets",
                                     f"Replace the person doing the work completely with the person in the first {n1} "
                                     "reference images")
                      + f" Also replace the person being worked on completely with the person in the last "
                        f"{len(refs) - n1} reference images, same face, skin, build and look."
                      + (" " + cs.STATE[a.also_state] if a.also_state else ""))
        clip_out = run / "media" / "swaps" / f"{o['scene']}-source.mp4"
        clip_out.parent.mkdir(parents=True, exist_ok=True)
        print(f"  {o['scene']}: {o['swipe_shot']} · {slug} · {len(refs)} sheets · {o.get('seconds')} s")
        if a.dry_run:
            continue
        start = o["shot_start"] if o.get("shot_start") is not None else shots_start.get(o["swipe_shot"], 0.0)
        clip, kept = prepare_clip(o, start, clip_out)
        if a.prepare_only:
            o.update(status="prepared", prepared_clip=str(clip), kept_seconds=round(kept, 2),
                     refs=[str(r) for r in refs][:8], prompt=prompt)
            orders_p.write_text(json.dumps(orders, indent=1))
            continue
        CL = _load("clip_limits")      # the object-swap sheet (model-inputs) before any upload or spend
        CL.raise_on_errors(CL.check("higgsfield-object-swap", kept, a.resolution, images=[Path(r) for r in refs][:8], videos=[clip]),
                           f"swap {o['scene']}")
        payload = {"video_url": url_of(clip), "image_urls": [url_of(Path(r)) for r in refs][:8],
                   "prompt": prompt, "resolution": a.resolution}
        rid = hf.submit(MODEL, payload)
        o.update(status="submitted", request_id=rid, kept_seconds=round(kept, 2))
        orders_p.write_text(json.dumps(orders, indent=1))
        body = hf.wait(rid)
        state = str(body.get("status", "")).lower()
        o["status"] = state
        urls = hf.outputs(body) if state == "completed" else []
        if urls:
            dest = run / "media" / "swaps" / f"{o['scene']}.mp4"
            hf.download(urls[0], dest)
            o["file"] = str(dest)
            done += 1
        orders_p.write_text(json.dumps(orders, indent=1))
        print(f"    → {state}" + (f" · {o.get('file')}" if o.get("file") else ""))
    orders_p.write_text(json.dumps(orders, indent=1))
    print(f"swaps: {done} made · {sum(1 for o in orders if o.get('status') == 'completed')} of {len(orders)} done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
