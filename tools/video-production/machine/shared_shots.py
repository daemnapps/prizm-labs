"""ONE STYLE OF SHOT, ONE PICTURE (2026-10-31).

the owner: "we look for similar frames in the swipe and just generate what is absolutely needed."

After the storyboard, sections that show the same people in the same looks and place, on swipe frames that look alike,
share the first section's start picture. Their words, face and hands change in the clip. A section that looks different
in the swipe keeps its own picture. `clips_plan.picture_ids` reads `start_picture`, so every reader follows one field.

    python3 shared_shots.py <production run>
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
SIMILAR = 0.42      # share of differing bits: the same locked frame measured under 0.36, a new set-up over 0.49


def _bits(file: Path) -> list:
    im = Image.open(file).convert("L").resize((SIZE + 1, SIZE))
    p = list(im.tobytes())
    return [p[y * (SIZE + 1) + x] < p[y * (SIZE + 1) + x + 1] for y in range(SIZE) for x in range(SIZE)]


def apart(a: list, b: list) -> float:
    return sum(x != y for x, y in zip(a, b)) / max(1, len(a))


def _who(g: dict) -> tuple:
    return tuple(sorted(str(e) for e in g.get("elements") or [] if str(e).startswith(("person ·", "place ·"))))


def _clips_plan():
    sp = importlib.util.spec_from_file_location("vm_ss_cp", HERE / "clips_plan.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def group(run: Path, frames: Path | None = None) -> dict:
    """{section: the section whose picture it shares}, written into storyboard.json."""
    run = Path(run)
    f = run / "storyboard.json"
    sb = json.loads(f.read_text())
    tear = frames or (Path(sb["teardown"]) / "framemap" / "shots" if sb.get("teardown") else None)
    cp = _clips_plan()
    leaders, shared = [], {}
    for g in sb.get("sections") or []:
        g.pop("start_picture", None)
        g.pop("same_picture_as", None)
        ks = (g.get("swipe") or {}).get("shots") or []
        file = tear / ks[0]["first"] if tear and ks and ks[0].get("first") else None
        pid = cp.picture_ids(g).get("start")
        if not file or not file.is_file() or not pid or not _who(g):
            continue
        bits = _bits(file)
        hit = next((x for x in leaders if x["who"] == _who(g) and apart(x["bits"], bits) < SIMILAR), None)
        if hit:
            g["start_picture"], g["same_picture_as"] = hit["pid"], hit["id"]
            shared[g["id"]] = hit["id"]
        else:
            leaders.append({"id": g["id"], "who": _who(g), "bits": bits, "pid": pid})
    f.write_text(json.dumps(sb, indent=1, ensure_ascii=False))
    return shared


if __name__ == "__main__":
    print(json.dumps(group(Path(sys.argv[1])), indent=1))
