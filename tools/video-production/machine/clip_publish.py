#!/usr/bin/env python3
"""clip_publish.py — hands the made clips to the editor, with their check results.

    python3 machine/clip_publish.py <run>          (also runs at the end of `clips_run.py run`)

The clips route keeps its results in clips/ledger.json and its files in clips/<call>.mp4. The
edit (tools/video-edit kit_from_run.py `approved()`) reads something else: media/<scene>.mp4
and verdicts.json[scene] with `motion` and `director` verdicts that are not FLAG, and for a talking
scene a `parity` verdict PASS. Until this step existed those were written by hand, so every cut
dropped every clip ("not approved — no motion verdict").

For each scene it takes the made calls that carry it, cuts the scene's own window out of each call
(the call's `lines` carry the window; a call that is only this scene is copied whole), joins the
pieces when a scene spans two calls, and writes media/<scene>.mp4. The verdicts come from what the
clip step already measured — clip_qc (framing · scene · camera · lips) and the face lock — and the
line check; they are written through preflight.verdict() so a FLAG keeps its history. A scene whose
check was never run gets NO verdict (the edit then holds it as "not approved") — nothing here
approves a clip the checks did not look at. Idempotent; spends nothing.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BY = "auto: clip_qc + line check"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def scenes_of(call: dict) -> list[str]:
    out = []
    for x in list(call.get("lines") or []) + list(call.get("voice_parts") or []):
        s = x.get("scene")
        if s and s not in out:
            out.append(s)
    return out


def window_of(call: dict, sid: str) -> tuple[float, float] | None:
    """The scene's window inside this call's clip, seconds from the clip's start; None = the whole clip."""
    ls = [l for l in call.get("lines") or [] if l.get("scene") == sid]
    if not ls or len(scenes_of(call)) <= 1:
        return None
    a, z = min(float(l["at"]) for l in ls), max(float(l["until"]) for l in ls)
    return max(0.0, a - 0.05), z + 0.05


def judge(row: dict, talking: bool) -> dict:
    """motion / director / parity verdict payloads from one ledger row (a missing check = no payload)."""
    out = {}
    qc = row.get("qc")
    if isinstance(qc, dict):
        cam = (qc.get("camera") or {}).get("ok", True)
        scn = (qc.get("scene") or {}).get("ok", True)
        out["motion"] = {"verdict": "PASS" if (cam and scn) else "FLAG", "by": BY,
                         "scene": qc.get("scene"), "camera": qc.get("camera")}
        fl = row.get("face_lock") or {}
        parts = {"framing": (qc.get("framing") or {}).get("ok", True), "face": fl.get("ok", True)}
        if talking:
            parts["lips"] = (qc.get("lips") or {}).get("ok", True)
        bad = [k for k, v in parts.items() if not v]
        if row.get("below_criteria"):
            bad = bad + ["below criteria"]
        out["director"] = {"verdict": "FLAG" if bad else "PASS", "by": BY, "checked": parts,
                           "problems": bad, "below_criteria": bool(row.get("below_criteria")),
                           "failed_checks": row.get("failed_checks") or []}
    lc = row.get("line_check")
    if talking and isinstance(lc, dict) and lc.get("verdict"):
        out["parity"] = {k: lc.get(k) for k in ("verdict", "heard", "match", "ending_heard")}
    return out


def _worst(rows: list[dict]) -> dict:
    """Several calls carry one scene: it passes only when every piece does."""
    bad = [r for r in rows if r.get("verdict") != "PASS"]
    return bad[0] if bad else rows[0]


def _cut(src: Path, win, dst: Path) -> None:
    if win is None:
        shutil.copyfile(src, dst)
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{win[0]:.3f}", "-t", f"{win[1] - win[0]:.3f}",
                    "-i", str(src), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac",
                    "-movflags", "+faststart", str(dst)], check=True)


def _join(parts: list[Path], dst: Path) -> None:
    with tempfile.TemporaryDirectory() as t:
        lst = Path(t) / "l.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", str(dst)], check=True)


def publish(run: Path) -> dict:
    run = Path(run)
    plan = _read(run / "clips" / "plan.json", {}) or {}
    ledger = _read(_load("clip_kit").ledger_path(run), {}) or {}
    calls = sorted(plan.get("calls") or [], key=lambda c: float(c.get("at") or 0))
    preflight = _load("preflight")
    by_scene: dict[str, list[tuple[dict, dict]]] = {}
    for c in calls:
        for sid in scenes_of(c):
            by_scene.setdefault(sid, []).append((c, ledger.get(c["id"]) or {}))
    done, held = [], {}
    media = run / "media"
    media.mkdir(exist_ok=True)
    for sid, pairs in by_scene.items():
        missing = [c["id"] for c, r in pairs
                   if r.get("status") != "done" or not (run / "clips" / f"{c['id']}.mp4").is_file()]
        if missing:
            held[sid] = "waiting on " + ", ".join(missing)
            continue
        pieces = []
        with tempfile.TemporaryDirectory() as t:
            for i, (c, r) in enumerate(pairs):
                p = Path(t) / f"p{i}.mp4"
                _cut(run / "clips" / f"{c['id']}.mp4", window_of(c, sid), p)
                pieces.append(p)
            dst = media / f"{sid}.mp4"
            if len(pieces) == 1:
                shutil.copyfile(pieces[0], dst)
            else:
                _join(pieces, dst)
        # the on-camera test: this scene is spoken to camera in at least one carrying call
        talking = any(any(v.get("scene") == sid for v in (c.get("voice_parts") or [])) for c, _ in pairs)
        per = [judge(r, talking and any(v.get("scene") == sid for v in (c.get("voice_parts") or [])))
               for c, r in pairs]
        for layer in ("motion", "director", "parity"):
            rows = [p[layer] for p in per if layer in p]
            if not rows or (layer != "parity" and len(rows) < len(per)):
                continue                                  # a check that never ran writes nothing
            preflight.verdict(run, sid, layer, _worst(rows))
        done.append(sid)
    return {"published": done, "held": held}


def main(argv=None) -> int:
    run = Path((argv or sys.argv[1:])[0]).resolve()
    res = publish(run)
    print(f"published {len(res['published'])} scene(s) to media/ + verdicts.json"
          + (f" · waiting: {res['held']}" if res["held"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
