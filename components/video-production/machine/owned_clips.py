#!/usr/bin/env python3
"""owned_clips — a scene given to our own footage reaches the edit as a file (the logic layer, 2026-11-18).

    python3 machine/owned_clips.py <production run> [--brand <brand>] [--dry-run]

and automatically: `run.py start` calls `place()` right after the footage step.

The footage step decides, per B-roll scene, cut from our footage or generate (footage.py; shot_route.py labels a cut
scene REAL). Until this step that decision was only a line on plan.json: nothing was generated for the scene and
nothing was cut for it either, so the edit's join (video-edit kit_from_run.py) found no media/<scene>.mp4, listed the
scene "no clip made yet", and a scene given to our footage never reached the editor.

`place()` makes the decision a file. For every scene the footage decision passed (`source_plan: cut` + `owned_file`):

  1. the source is read through gdrive-creator (`reach.readable` on the clip's "Shared Assets/…" label: the key's own
     copy on any machine; a record never holds a mount path)
  2. `owned_in` → `owned_out` is cut out of it into media/<scene id>.mp4, picture only (a B-roll scene plays under
     its slice of the voice read; the footage's own sound never rides along)
  3. its `motion` and `director` verdict rows are written through preflight.verdict(): PASS, by the footage step, with
     the file, the times and what the match was judged on. That is what the edit's `approved()` reads, and it says
     plainly that the clip is our own footage and not a judged AI take.

Two rules are asked again here, for a plan decided before the footage step asked them: a clip whose text marks
(`owned_marks`) are not clean is never laid in, and one clip section is never laid on two scenes. Such a scene is
named and left without a file; the footage step itself re-decides it on the next `start`.

Nothing here stops production: a clip that cannot be read or cut is named, the decision stands, and running this
again lays it in. Idempotent (a clip already laid from the same source and times is kept). Spends nothing.

Brand-agnostic: nothing here names a brand, a product or a person.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BY = "the footage step: our own footage, cut not generated"
CLEAN = ["clean"]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_oc_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def readable(ref: str) -> Path:
    """The owned clip as a file this process can open, through gdrive-creator: a "Shared Assets/…" label (or an older
    record's mount path) by the key's copy; a plain local path as it is. Raises when it is on neither."""
    gdc = str(HERE.parents[1] / "gdrive-creator")
    if gdc not in sys.path:
        sys.path.append(gdc)
    from gdrive_creator import reach
    p = Path(reach.readable(ref))
    if not p.is_file():
        raise FileNotFoundError(f"{ref} is not a file on the Drive or on this machine")
    return p


def cut(src: Path, t_in: float, t_out: float, dst: Path) -> None:
    """owned_in → owned_out of `src` into `dst`, picture only, re-encoded so the cut lands on the exact frame."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".part" + dst.suffix)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t_in:.3f}", "-t", f"{max(t_out - t_in, 0.04):.3f}",
                    "-i", str(src), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(dst)


def stamp_of(scene: dict) -> str:
    """What a laid clip was cut from: the source and its times. A changed decision changes it, so the clip is cut again."""
    return hashlib.sha256(json.dumps([scene.get("owned_file"), scene.get("owned_in"), scene.get("owned_out")],
                                     default=str).encode()).hexdigest()[:16]


def passed(scene: dict) -> bool:
    """Did the footage decision pass this scene (a cut with its file and times)?"""
    return scene.get("source_plan") == "cut" and bool(scene.get("owned_file"))


def clean(scene: dict) -> bool:
    """No words burned into the clip, by the footage library's text marks. A scene the library did not mark (no
    `owned_tier`: a brand with no built library, or a test's own index) is not judged here; the footage step judged
    it when it decided."""
    if not scene.get("owned_tier") and "owned_marks" not in scene:
        return True
    return list(scene.get("owned_marks") or []) == CLEAN


def verdicts_for(scene: dict) -> dict:
    row = {"verdict": "PASS", "by": BY, "owned": True,
           "file": scene.get("owned_file"), "in": scene.get("owned_in"), "out": scene.get("owned_out"),
           "clip": scene.get("owned_clip"), "evidence": scene.get("owned_evidence") or {},
           "why": scene.get("footage_why") or "cut from our footage"}
    return {"motion": dict(row, checked="the footage is real: there is no generated movement to judge"),
            "director": dict(row, checked="picked by the footage decision on its match; no take was judged")}


def place(run: Path, plan: dict, brand: str = "", dry_run: bool = False, fetch=None, cutter=None, verdict=None) -> dict:
    """Lay every scene the footage decision passed into media/. `fetch(ref) -> Path`, `cutter(src, in, out, dst)` and
    `verdict(run, id, layer, payload)` are the seams a test fakes. Writes `owned_media` (the file, repo-run relative,
    and its stamp) on each placed scene of `plan` in place; the caller saves the plan.
    -> {"placed": [ids], "kept": [ids], "skipped": {id: why}, "said": [lines]}"""
    run = Path(run)
    fetch, cutter = fetch or readable, cutter or cut
    res = {"placed": [], "kept": [], "skipped": {}, "said": []}
    rows = [s for s in (plan.get("scenes") or []) if isinstance(s, dict) and passed(s)]
    if not rows:
        return res
    taken = {}
    for s in rows:
        sid = str(s.get("id"))
        try:
            t_in, t_out = float(s.get("owned_in") or 0), float(s.get("owned_out") or 0)
        except (TypeError, ValueError):
            t_in = t_out = 0.0
        key = (s.get("owned_file"), t_in, t_out)
        why = None
        if not clean(s):
            why = "words are burned into the clip (" + ", ".join(s.get("owned_marks") or ["marked"]) + "): never laid in"
        elif key in taken:
            why = f"the same clip section is already laid on {taken[key]}: one section, one scene"
        elif t_out <= t_in:
            why = f"its times are not a span ({s.get('owned_in')}–{s.get('owned_out')})"
        if why:
            res["skipped"][sid] = why
            s["owned_unplaced"] = why
            res["said"].append(f"  our footage NOT laid for {sid}: {why}")
            continue
        taken[key] = sid
        dst = run / "media" / f"{sid}.mp4"
        stamp = stamp_of(s)
        had = s.get("owned_media") or {}
        if dst.is_file() and had.get("stamp") == stamp:
            if had.get("verdicts") is False and not dry_run:     # laid before, its rows never written: written now
                try:
                    write = verdict or _load("preflight").verdict
                    for layer, payload in verdicts_for(s).items():
                        write(run, sid, layer, payload)
                    s["owned_media"]["verdicts"] = True
                    res["placed"].append(sid)       # the plan changed: the caller saves it
                    res["said"].append(f"  our footage: verdict rows written for media/{sid}.mp4")
                    continue
                except Exception:  # noqa: BLE001 - still not writable: kept as it is, said the first time
                    pass
            res["kept"].append(sid)
            continue
        if dry_run:
            res["said"].append(f"  our footage: {sid} would be cut {t_in:g}–{t_out:g}s of {s.get('owned_file')} "
                               f"into media/{sid}.mp4 (dry run)")
            continue
        try:
            src = fetch(str(s["owned_file"]))
            if dst.is_file():                       # a clip from an earlier decision: kept beside the new one
                old = run / "media" / "versions" / f"{sid}-before-owned-{had.get('stamp') or 'earlier'}.mp4"
                old.parent.mkdir(parents=True, exist_ok=True)
                if not old.exists():
                    dst.replace(old)
            cutter(src, t_in, t_out, dst)
            if not dst.is_file() or dst.stat().st_size == 0:
                raise RuntimeError("the cut wrote no file")
        except Exception as e:  # noqa: BLE001 - named, the decision stands, nothing stops
            why = f"could not be read or cut ({type(e).__name__}: {str(e)[:200]}); run owned_clips.py on this run again"
            res["skipped"][sid] = why
            s["owned_unplaced"] = why
            res["said"].append(f"  our footage NOT laid for {sid}: {why}")
            continue
        s.pop("owned_unplaced", None)
        s["owned_media"] = {"file": f"media/{sid}.mp4", "stamp": stamp, "picture_only": True}
        try:                                        # the clip is laid either way; rows that cannot be written are said
            write = verdict or _load("preflight").verdict
            for layer, payload in verdicts_for(s).items():
                write(run, sid, layer, payload)
            s["owned_media"]["verdicts"] = True
        except Exception as e:  # noqa: BLE001
            s["owned_media"]["verdicts"] = False
            res["said"].append(f"  our footage laid for {sid}, but its verdict rows could not be written "
                               f"({type(e).__name__}: {str(e)[:160]}): the edit lists it not approved until "
                               "owned_clips.py runs on this run again")
        res["placed"].append(sid)
        res["said"].append(f"  our footage laid: media/{sid}.mp4 · {t_in:g}–{t_out:g}s of {s.get('owned_file')}")
    n = len(res["placed"]) + len(res["kept"])
    if n or res["skipped"]:
        res["said"].insert(0, f"our footage: {n} scene(s) in media/ for the edit"
                           + (f" · {len(res['skipped'])} not laid" if res["skipped"] else ""))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--brand", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    run = a.run.expanduser().resolve()
    plan = _read(run / "plan.json")
    if not isinstance(plan, dict):
        sys.exit(f"no plan.json in {run}")
    res = place(run, plan, a.brand or plan.get("brand") or "", dry_run=a.dry_run)
    if not a.dry_run and (res["placed"] or res["skipped"]):
        (run / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    print("\n".join(res["said"]) or "our footage: no scene of this run is cut from our footage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
