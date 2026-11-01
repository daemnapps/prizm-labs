"""Real human movement: a real person's performance sent with every clip that has a person in it.

2026-10-28: a clip needs more than a still to move like a person. A clip made from one still invents its
movement and comes out stiff. So every call with a person on screen is sent, beside its picture and its voice, a few
seconds of REAL footage of a person doing what the scene does (talking to the lens, pointing, nodding), bound in the
prompt as movement only. The swipe's own footage is not used for this: it may itself be AI-made.

The bank is `movement-bank.json` beside this folder's parent (definitions, curated by the component's owner): each entry
a real clip with what the person in it does. The chain picks by what the call's scenes do, and prepares the piece the
same way every time: no sound (a reference's voice overrides the prompt), no colour (its skin, clothes and room must not
carry over), a little soft, cut to the call's length (5 to 10 s works best).

    python3 movement.py list                       the bank
    python3 movement.py pick "<what the scene does>"   which entry the chain would send
"""
from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE.parent / "movement-bank.json"
BEST = (5.0, 10.0)        # seconds of reference that work best (model-inputs seedance-2.5: best_reference_video_seconds)
SOFT = 2.5                # blur sigma: keeps the head, hands and face's big moves, drops the face's identity
LINE = ("Video {n} is a real person's movement only: copy how the head, neck and shoulders move while talking (small nods, "
        "tilts, turns, breathing), how the face changes (brows, eyes, blinks, mouth), and how naturally the arm and hand "
        "rise, move and settle, with the same loose, unposed timing. Where the hand goes and what it touches is what this "
        "prompt says, never copied from Video {n}. Take nothing else from it: no person, face, skin, hair, clothing, "
        "objects, place, colour, words or subtitles.")


def bank(path: Path = BANK) -> list:
    if not Path(path).is_file():
        return []
    return [e for e in json.loads(Path(path).read_text()).get("entries") or [] if e.get("status") != "deprecated"]


def _words(t) -> set:
    return set(re.findall(r"[a-z]+", str(t or "").lower())) - {"the", "a", "an", "and", "to", "of", "her", "his", "on", "at", "in", "with"}


def pick(does: str, talking: bool = True, entries: list | None = None, n: int = 1) -> list:
    """The bank entries that best match what the call's scenes do: most shared words with the entry's `does` and
    `framing`, a talking clip only from talking entries. Ties go to the entry listed first."""
    want = _words(does)
    rows = []
    for i, e in enumerate(entries if entries is not None else bank()):
        if talking and not e.get("talks", True):
            continue
        have = _words(" ".join(e.get("does") or [])) | _words(e.get("framing"))
        rows.append((-len(want & have), i, e))
    rows.sort(key=lambda r: (r[0], r[1]))
    return [r[2] for r in rows[:n]]


def piece(entry: dict, seconds: float) -> dict:
    """Which part of the entry to send: from its own best start, the call's length kept inside 5 to 10 s."""
    want = min(max(float(seconds), BEST[0]), BEST[1])
    have = float(entry.get("seconds") or want)
    start = float(entry.get("from") or 0.0)
    return {"kind": "movement", "id": entry["id"], "src": entry["file"], "from": round(start, 2),
            "seconds": round(min(want, max(have - start, 1.0)), 2)}


def prepare(src: Path, dest: Path, start: float, seconds: float, ffmpeg: str = "ffmpeg", runner=None) -> Path:
    """No sound, no colour, a little soft, 480 wide: the movement, never the person."""
    runner = runner or (lambda cmd: subprocess.run(cmd, check=True, capture_output=True))
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    runner([ffmpeg, "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i", str(src), "-an",
            "-vf", f"scale=480:-2,format=gray,gblur=sigma={SOFT},format=yuv420p", str(dest)])
    return Path(dest)


def make(run: Path, ref: dict, ffmpeg: str = "ffmpeg", runner=None) -> Path:
    """The prepared piece for one planned movement ref, made once (local ffmpeg, no network, no money)."""
    dest = Path(run) / ref["file"]
    root = HERE.parents[2]
    src = root / ref["src"]
    source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    signature = hashlib.sha256(json.dumps([source_hash, ref["from"], ref["seconds"], SOFT, 480]).encode()).hexdigest()
    stamp = dest.with_suffix('.source.json')
    if dest.is_file() and stamp.is_file() and json.loads(stamp.read_text()).get('signature') == signature:
        return dest
    cached = root / 'runs/ai-elements/movement/prepared' / (signature + '.mp4')
    if not cached.is_file():
        prepare(src, cached, ref["from"], ref["seconds"], ffmpeg, runner)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, dest)
    stamp.write_text(json.dumps({'signature': signature, 'reference': ref['id'], 'source_sha256': source_hash}))
    return dest


def for_call(call: dict, does: str, entry_id=None) -> list:
    """The movement refs for one call: one bank entry for a call with a person on screen, none otherwise."""
    if not call.get("people"):
        return []
    if entry_id == "none":
        return []
    got = ([e for e in bank() if e['id'] == entry_id] if entry_id else pick(does, talking=bool(call.get("talking"))))
    if entry_id and not got:
        raise ValueError("The selected movement reference is not in the active bank: " + str(entry_id))
    return [{**piece(e, call.get("duration") or call.get("seconds") or 5),
             "file": f"clips/refs/{call['id']}-{e['id']}-{piece(e, call.get('duration') or call.get('seconds') or 5)['seconds']}-move{i + 1}.mp4"}
            for i, e in enumerate(got)]


if __name__ == "__main__":
    if sys.argv[1:2] == ["list"]:
        for e in bank():
            print(f"{e['id']:<28} {e.get('seconds', '?')} s  {', '.join(e.get('does') or [])}")
    elif sys.argv[1:2] == ["pick"]:
        print(json.dumps(pick(" ".join(sys.argv[2:])), indent=1))
