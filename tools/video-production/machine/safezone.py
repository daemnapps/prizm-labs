#!/usr/bin/env python3
"""
safezone.py — the subject 4:5 zone, checked on every still production makes.

the owner, 2026-09-23: "safe zones for text and subjects (this should mostly be
handled at the production level)". The standing frame rule (2026-09-22):
every asset is 9:16, and faces, the product and the hands doing the beat sit
inside the CENTRED 4:5 zone of that frame — no 4:5 canvas, no padding bands.

image-production already gates this for pictures (image_production/judge.py
`SAFE_ZONE`, engine.py's generate-at-4:5-then-place, providers.py
`finish_9x16`), and it measured the lesson this module is built on: ASKING a
model to hold a zone fails (13 of 13 live rolls). So nothing here asks a model
whether the subject is in the zone. One vision call says WHERE the subject is
(a box); the zone is geometry; the verdict is the box against the zone.

Reused from image-production, never copied (components/CLAUDE.md):
  * the delivered frame — `providers.OUT_W x OUT_H` (1080x1920) — and the 4:5
    aspect from `route.aspects()`;
  * the vision door — `route.judge_entry()` (the model and its key) and
    `judge.google_caller` (one prompt + one picture, the transport seam);
  * the prompt file reader — `prompting.latest` / `prompting.body`;
  * the rule `judge.seen` is built on: a judge that did not run is not a pass.

The prompt is `prompts/stage-5-qc/stage5-subject-zone-v1-damon.md` — sent as
written. `caller(prompt, image_path, entry) -> str` is the seam; the tests
pass a stub and nothing here opens a socket by itself.

    python3 machine/safezone.py <still.png> [--dry-run]

COST (estimate, stated not measured): one call to the judge model
(gemini-3.1-pro-preview) with one ~1024x1536 picture and ~450 words of prompt
is roughly 1.5k tokens in and 150 out — about $0.005 a still at $2/M in and
$12/M out. A frame that fails gets ONE edit on the stills door (the tracked
GPT Image rate, ~$0.18) and one more check.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT_DIR = HERE.parent / "prompts" / "stage-5-qc"
PROMPT_STAGE = "stage5-subject-zone"

CHECK_USD = 0.005          # one zone check (estimate — see the docstring)
FIX_USD = 0.18             # one fix edit on the stills door (tracked gpt-image rate)

# a box may overhang the zone edge by this much (points of the frame's
# height/width) before it counts as outside — a vision box is not a ruler
TOLERANCE = 1.5

# the stills that are FRAMES of the finished ad — what a clip starts on or the
# edit lays under words. A cast sheet is not a frame.
FRAME_ROLES = ("first", "last", "plate", "packshot")
SUBJECT_ORDER = ("face", "product", "hands")


def _ip():
    """image-production's package, found by walking up (brandfiles.py's way)."""
    for d in [HERE, *HERE.parents]:
        ip = d / "tools" / "image-production"
        if (ip / "image_production").is_dir():
            if str(ip) not in sys.path:
                sys.path.insert(0, str(ip))
            import image_production.judge as judge          # type: ignore
            import image_production.route as route          # type: ignore
            import image_production.providers as providers  # type: ignore
            import image_production.prompting as prompting  # type: ignore
            return judge, route, providers, prompting
    raise SystemExit("image-production not found upward of this folder — the zone "
                     "check reuses its judge and cannot run without it")


# ------------------------------------------------------------- geometry

def delivered_aspect() -> float:
    _j, _r, providers, _p = _ip()
    return providers.OUT_W / providers.OUT_H                  # 9:16


def zone_aspect() -> float:
    _j, route, _pv, _p = _ip()
    a = route.aspects().get("4:5") or {"w": 4, "h": 5}
    return a["w"] / a["h"]


def zone_of(w: int, h: int) -> dict:
    """The delivered 9:16 frame and its centred 4:5 zone, as pct boxes of a
    still of w x h. A still that is not 9:16 (the stills door makes 2:3) is
    read as the clip door frames it — a centred crop that fills 9:16."""
    d = delivered_aspect()
    if w / h > d:
        fw, fh = h * d, float(h)
    else:
        fw, fh = float(w), w / d
    z = zone_aspect()
    zw, zh = fw, fw / z
    if zh > fh:
        zh, zw = fh, fh * z
    pct = lambda x, y, bw, bh: {"x_pct": round(100 * x / w, 2), "y_pct": round(100 * y / h, 2),
                                 "w_pct": round(100 * bw / w, 2), "h_pct": round(100 * bh / h, 2)}
    return {"frame": pct((w - fw) / 2, (h - fh) / 2, fw, fh),
            "zone": pct((w - zw) / 2, (h - zh) / 2, zw, zh)}


def to_frame(box: dict, frame: dict) -> dict:
    """A pct box on the still -> a pct box on the delivered 9:16 frame (what
    the edit places words against), clipped to the frame."""
    def ax(pos, size, f0, fs):
        a = max(0.0, (pos - f0) / fs * 100)
        b = min(100.0, (pos + size - f0) / fs * 100)
        return round(a, 2), round(max(0.0, b - a), 2)
    x, w = ax(box["x_pct"], box["w_pct"], frame["x_pct"], frame["w_pct"])
    y, h = ax(box["y_pct"], box["h_pct"], frame["y_pct"], frame["h_pct"])
    return {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h, "what": box.get("what", "")}


def outside(box: dict, zone: dict, tol: float = TOLERANCE) -> bool:
    return (box["x_pct"] < zone["x_pct"] - tol
            or box["y_pct"] < zone["y_pct"] - tol
            or box["x_pct"] + box["w_pct"] > zone["x_pct"] + zone["w_pct"] + tol
            or box["y_pct"] + box["h_pct"] > zone["y_pct"] + zone["h_pct"] + tol)


# ---------------------------------------------------------------- prompt

def prompt_path(folder: Path | None = None) -> Path:
    _j, _r, _pv, prompting = _ip()
    return prompting.latest(PROMPT_STAGE, folder or PROMPT_DIR)


def prompt_text(folder: Path | None = None) -> str:
    _j, _r, _pv, prompting = _ip()
    return prompting.body(prompt_path(folder))


def move_delta(result: dict, folder: Path | None = None) -> str:
    """The ONE change for a frame that failed, read from the prompt file's
    ```delta block (above its rule, so it is never sent to the judge)."""
    text = prompt_path(folder).read_text()
    m = re.search(r"```delta\s*\n(.*?)\n```", text, re.S)
    if not m:
        raise SystemExit(f"{prompt_path(folder).name} carries no ```delta block")
    z = result["zone"]
    what = " and ".join(result.get("outside") or ["subject"])
    return (m.group(1).strip()
            .replace("{what}", what)
            .replace("{top}", f"{round(z['y_pct'])}")
            .replace("{bottom}", f"{round(z['y_pct'] + z['h_pct'])}"))


# ----------------------------------------------------------------- check

def _size(path) -> tuple[int, int] | None:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:                                  # noqa: BLE001
        return None


def _subjects(raw: str) -> list[dict] | None:
    try:
        data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        rows = data.get("subjects")
        if not isinstance(rows, list):
            return None
        out = []
        for r in rows:
            box = {k: float(r[k]) for k in ("x_pct", "y_pct", "w_pct", "h_pct")}
            if (not all(0 <= v <= 100 for v in box.values()) or box["w_pct"] <= 0
                    or box["h_pct"] <= 0 or box["x_pct"] + box["w_pct"] > 100.5
                    or box["y_pct"] + box["h_pct"] > 100.5):
                return None                    # a box off the picture is not a measurement
            what = str(r.get("what") or "").lower().strip()
            out.append({**box, "what": what, "label": str(r.get("label") or "")})
        rank = {w: i for i, w in enumerate(SUBJECT_ORDER)}
        return sorted(out, key=lambda b: rank.get(b["what"], len(rank)))
    except Exception:                                  # noqa: BLE001
        return None


def default_caller(transport=None):
    """image-production's own judge caller, with the run's google transport."""
    judge, _r, _pv, _p = _ip()
    return lambda prompt, img, entry: judge.google_caller(prompt, img, entry, transport=transport)


def check(still, caller=None, entry=None, folder: Path | None = None) -> dict:
    """One still's zone verdict:
      PASS       every subject sits in the zone (or there is no subject)
      FAIL       a subject crosses out of it — `outside` names which
      UNCHECKED  the judge did not run or answered nothing readable; not a
                 pass, and not something a fix edit can help
    `subject_box` is the first subject (face, else product, else hands) on
    the delivered 9:16 frame; `subject_box_still` the same on the still."""
    _j, route, _pv, _p = _ip()
    entry = entry or route.judge_entry()
    base = {"check": "subject_zone", "file": str(still), "judge_model": entry.get("vendor_model", "unknown"),
            "prompt": prompt_path(folder).name}
    size = _size(still)
    if size is None:
        return {**base, "verdict": "UNCHECKED", "why": "the still could not be read"}
    w, h = size
    geo = zone_of(w, h)
    base.update({"size": [w, h], "zone": geo["zone"], "frame": geo["frame"]})
    caller = caller or default_caller()
    try:
        raw = caller(prompt_text(folder), str(still), entry)
    except BaseException as e:                         # noqa: BLE001 — a missing key is SystemExit
        if isinstance(e, KeyboardInterrupt):
            raise
        return {**base, "verdict": "UNCHECKED", "why": f"judge did not run: {type(e).__name__}: {str(e)[:160]}"}
    subs = _subjects(raw or "")
    if subs is None:
        return {**base, "verdict": "UNCHECKED", "why": "judge returned unreadable output", "raw": (raw or "")[:400]}
    out_of = [s["what"] or "subject" for s in subs if outside(s, geo["zone"])]
    first = subs[0] if subs else None
    return {**base, "verdict": "FAIL" if out_of else "PASS",
            "outside": sorted(set(out_of), key=out_of.index),
            "subjects": subs,
            "subject_box": to_frame(first, geo["frame"]) if first else None,
            "subject_box_still": {k: first[k] for k in ("x_pct", "y_pct", "w_pct", "h_pct", "what")} if first else None}


def is_frame(item: dict) -> bool:
    """Is this machine-hand item a frame of the ad (and so zone-checked)?"""
    if item.get("kind") not in ("still", "edit", "restyle"):
        return False
    return item.get("frame_role") in FRAME_ROLES or str(item.get("id", "")).endswith("-still")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("still")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.dry_run:
        _j, route, _pv, _p = _ip()
        print(json.dumps({"would_send": a.still, "model": route.judge_entry().get("vendor_model"),
                          "prompt": prompt_path().name, "usd_estimate": CHECK_USD}, indent=1))
        return 0
    print(json.dumps(check(a.still), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
