"""BODY CHECK — limbs counted, hands sized, on every picture and every take (2026-10-28).

The clip judge scores a whole take and let a third arm and an oversized hand through. This check asks about ONLY the
bodies (prompts/v2/body-check-v1-owner.md), on the picture itself or on frames across a take, and its failure is a hard
stop: a picture is not approved and a take does not pass.

    python3 body_check.py <run> <picture or video> [...]
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT = HERE.parent / "prompts" / "v2" / "body-check-v1-owner.md"
FRAMES = 6


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_bc_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def frames_of(video: Path, out: Path, n: int = FRAMES) -> list:
    """n frames spread across the video (never its first or last instant)."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True).stdout.strip() or 0)
    got = []
    for i in range(n):
        f = out / f"f{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * (i + 0.5) / n:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=540:-2", str(f)], check=True)
        got.append(f)
    return got


def verdict(text: str) -> dict:
    V = _load("v2_checks")
    a = V.json_of(text) or {}
    if not isinstance(a.get("ok"), bool) or not isinstance(a.get("people"), list):
        raise ValueError("Body check returned no usable anatomy verdict")
    people = [p for p in a.get("people") or [] if isinstance(p, dict)]
    bad = any(int(p.get("arms") or 0) > 2 or int(p.get("hands") or 0) > 2 or p.get("oversized_hand") or p.get("fused")
              for p in people)
    ok = bool(a.get("ok", not bad)) and not bad
    probs = [str(p.get("what")) for p in a.get("problems") or [] if isinstance(p, dict) and p.get("what")]
    if not ok and not probs:
        probs = ["a body is wrong (extra arm or hand, an oversized or fused hand)"]
    return {"ok": ok, "people": people, "problems": probs}


READS = 2       # two separate reads; a body is wrong only when both say so (one read alone called a held tube an arm)


def check(run: Path, f: Path, job: str = "body-check", ask=None) -> dict:
    """The body check of one picture or one video, on the judge's model, read twice. {"ok", "people", "problems",
    "reads"}; it fails only when every read finds the same kind of fault; an unanswered check is not ok."""
    f = Path(f)
    if subprocess.run(["ffprobe", "-v", "error", str(f)], capture_output=True).returncode:
        return {}                                           # not a picture or video ffprobe can read: not checked
    V = _load("v2_checks")
    model = _load("house").judge()
    try:
        with tempfile.TemporaryDirectory() as d:
            files = frames_of(f, Path(d)) if f.suffix.lower() in (".mp4", ".mov", ".webm") else [f]
            reads = []
            for i in range(READS):
                # the second read sees the frames in reverse order, so it is a fresh read (and never a remembered one)
                text, _info = (ask or V.ask)(Path(run), f"{job}-r{i + 1}",
                                             PROMPT.read_text() + f"\n\n(Read {i + 1} of {READS}: look again from scratch.)",
                                             files if i % 2 == 0 else files[::-1], model=model)
                reads.append(verdict(text))
        kinds = [{k for p in r["people"] for k in ("arms", "hands", "oversized_hand", "fused")
                  if (k in ("arms", "hands") and int(p.get(k) or 0) > 2) or (k not in ("arms", "hands") and p.get(k))}
                 for r in reads]
        agreed = set.intersection(*kinds) if kinds else set()
        ok = not agreed and any(r["ok"] for r in reads)
        probs = [] if ok else [x for r in reads for x in r["problems"]][:4]
        return {"ok": ok, "people": reads[0]["people"], "problems": probs, "agreed": sorted(agreed), "reads": len(reads),
                "checker_sha256": hashlib.sha256(PROMPT.read_bytes()).hexdigest()}
    except Exception as e:                                  # noqa: BLE001 — an unanswered check never passes
        return {"ok": False, "people": [], "problems": [f"the body check did not answer: {e}"[:200]]}


def main(argv=None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    if len(a) < 2:
        print(__doc__)
        return 2
    bad = 0
    for f in a[1:]:
        got = check(Path(a[0]), Path(f), f"body-check-{Path(f).stem}")
        bad += not got["ok"]
        print(f"{Path(f).name}: {'OK' if got['ok'] else 'WRONG'} {json.dumps(got['people'])} {'; '.join(got['problems'])}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
