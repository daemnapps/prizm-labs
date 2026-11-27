"""ONE STYLE OF SHOT, ONE PICTURE (2026-10-31).

owner: "we look for similar frames in the swipe and just generate what is absolutely needed."

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
SPEECH = 11.0       # seconds of words in one take: with the room a take needs, it stays inside the model's 15 s
SIMILAR = 0.42      # share of differing bits: the same locked frame measured under 0.36, a new set-up over 0.49


def _bits(file: Path) -> list:
    im = Image.open(file).convert("L").resize((SIZE + 1, SIZE))
    p = list(im.tobytes())
    return [p[y * (SIZE + 1) + x] < p[y * (SIZE + 1) + x + 1] for y in range(SIZE) for x in range(SIZE)]


def apart(a: list, b: list) -> float:
    return sum(x != y for x, y in zip(a, b)) / max(1, len(a))


def _who(g: dict, run: Path | None = None) -> tuple:
    """What a section's picture must show: its people, place, props, and every product its scenes use (owner,
    2026-11-20: a scene with the product or other props never starts on another scene's picture)."""
    own = [str(e) for e in g.get("elements") or [] if str(e).startswith(("person ·", "place ·", "prop ·", "product ·"))]
    if run is not None:
        try:
            sp = importlib.util.spec_from_file_location("vm_ss_cr", HERE / "clip_refs.py")
            cr = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(cr)
            own += ["product · " + b for b in cr.product_ids(run, {"scenes": g.get("scenes") or []}, HERE.parents[2])]
        except Exception:  # noqa: BLE001 -- products unread: the section shares nothing it cannot be sure of
            own.append("product · unknown · " + str(g.get("id")))
    return tuple(sorted(set(own)))


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
        who = _who(g, run)
        if not file or not file.is_file() or not pid or not who:
            continue
        bits = _bits(file)
        hit = next((x for x in leaders if x["who"] == who and apart(x["bits"], bits) < SIMILAR), None)
        if hit:
            g["start_picture"], g["same_picture_as"] = hit["pid"], hit["id"]
            shared[g["id"]] = hit["id"]
        else:
            leaders.append({"id": g["id"], "who": who, "bits": bits, "pid": pid})
    f.write_text(json.dumps(sb, indent=1, ensure_ascii=False))
    return shared


def long_takes(run: Path) -> list:
    """THE TALKING-HEAD PATH (2026-10-31). Neighbouring sections on one picture become long takes of up to SPEECH seconds
    of words, so the model never pads a short line with its own. The start picture alone carries the person."""
    run = Path(run)
    f = run / "storyboard.json"
    sb = json.loads(f.read_text())
    out, cur = [], None
    for g in sb.get("sections") or []:
        pid = g.get("same_picture_as") or g["id"]
        if g.get("same_picture_as"):
            g["maker"] = "lip-sync"          # a shot that shares the talking picture is talking
        talking = g.get("maker") == "lip-sync"
        if cur is not None and talking and cur["picture"] == (cur["lead"].get("same_picture_as") or pid) or (
                cur is not None and talking and g.get("same_picture_as") == cur["lead"]["id"]):
            lead = cur["lead"]
            for k in ("scenes", "moments", "beats", "lips", "effects"):
                lead[k] = (lead.get(k) or []) + [x for x in (g.get(k) or []) if x not in (lead.get(k) or [])]
            lead["elements"] = (lead.get("elements") or []) + [e for e in (g.get("elements") or []) if e not in (lead.get("elements") or [])]
            lead["seconds"] = round(float(lead.get("seconds") or 0) + float(g.get("seconds") or 0), 2)
            if isinstance(lead.get("voice"), dict) and isinstance(g.get("voice"), dict):
                lead["voice"].update(g["voice"])
            if isinstance(lead.get("voice_from"), dict) and isinstance(g.get("voice_from"), dict):
                lead["voice_from"].update(g["voice_from"])
            lead["cuts"] = []
            continue
        out.append(g)
        cur = {"lead": g, "picture": pid} if talking else None
    for g in out:
        if g.get("maker") != "lip-sync":
            continue
        secs = g.get("voice") if isinstance(g.get("voice"), dict) else {}
        takes, now, used = [], [], 0.0
        for s in g.get("scenes") or []:
            n = float(secs.get(s) or 0)
            if now and used + n > SPEECH:
                takes.append((now, used)); now, used = [], 0.0
            now.append(s); used += n
        if now:
            takes.append((now, used))
        base = {"starts_from": "the section's start picture"}
        g["clips"] = [{**base, "scenes": sc, "seconds": round(u, 2)} for sc, u in takes]
        (g.get("swipe") or {})["shots"] = ((g.get("swipe") or {}).get("shots") or [])[:1]
    sb["sections"], sb["picture_only"] = out, True
    f.write_text(json.dumps(sb, indent=1, ensure_ascii=False))
    return [g["id"] for g in out if g.get("maker") == "lip-sync"]


if __name__ == "__main__":
    print(json.dumps(group(Path(sys.argv[1])), indent=1))
    print(json.dumps(long_takes(Path(sys.argv[1]))))
