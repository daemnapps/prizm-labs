"""Real human movement: a real person's performance sent with every clip that has a person in it.

2026-10-28: a clip needs more than a still to move like a person. A clip made from one still invents its
movement and comes out stiff. So every call with a person on screen is sent, beside its picture and its voice, a few
seconds of REAL footage of a person doing what the scene does (talking to the lens, pointing, nodding), bound in the
prompt as movement only. A talking clip copies the swipe's own creator (`from_swipe`, owner, 2026-10-31); the bank covers
everything else.

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
USE_LINE = ("Video {n} is a real person using a product, for the movement only: copy how the hand reaches, how the fingers spread "
            "and press, the pace of each stroke and how the skin gives under them. The product, person and place are this "
            "prompt's and its pictures', never taken from Video {n}: no face, skin, hair, clothing, packaging, colour, words or subtitles.")
SCENE_LINE = ("Video {n} is real footage for the motion only: copy how things move, the pace and how the camera follows. Take nothing "
              "else from it: no person, object, place, colour, words or subtitles.")
LINES = {"usage": USE_LINE, "broll": SCENE_LINE}
MOST = 2                  # video references on one clip: one for the performance, one for the action


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


def line(ref: dict, n: int) -> str:
    """The binding line for one reference, by what kind of footage it is."""
    return LINES.get(ref.get("use"), LINE).format(n=n)


def shared(does: str, entry: dict) -> int:
    """How many of the entry's action words the shot uses, whatever their ending."""
    stem = lambda w: re.sub(r"(ing|es|s)$", "", w)
    return len({stem(w) for w in _words(does)} & {stem(w) for w in _words(" ".join(entry.get("does") or []))})


def first_at(does: str, entry: dict) -> int:
    """Where the entry's action first comes in the shot: what the shot does first is what it is about."""
    said = [re.sub(r"(ing|es|s)$", "", w) for w in re.findall(r"[a-z]+", str(does).lower())]
    have = {re.sub(r"(ing|es|s)$", "", w) for w in _words(" ".join(entry.get("does") or []))}
    return next((i for i, w in enumerate(said) if w in have), len(said))


def choose(call: dict, does: str, entries: list | None = None) -> list:
    """What this shot needs, by what it shows: a talking clip gets a real talking person, and any clip whose action is in
    the bank (a product in use, a hand on the skin, a walk, b-roll) gets that action too. A clip with no match gets none:
    footage of something else would pull the shot off what the prompt says."""
    rows = bank() if entries is None else entries
    out = []
    if call.get("talking"):
        talkers = [e for e in rows if e.get("kind", "talking") == "talking"]
        men = [e for e in talkers if "man" in (e.get("does") or [])]
        out += pick(does, True, men if men and re.search(r"\b(he|his|him|man)\b", does.lower()) else talkers)
    rest = [e for e in rows if e.get("kind") in ("usage", "action", "broll") and (call.get("people") or e.get("kind") != "action")]
    best = sorted(rest, key=lambda e: first_at(does, e))[:1]
    out += [e for e in best if shared(does, e)]
    return out[:MOST]


def piece(entry: dict, seconds: float) -> dict:
    """Which part of the entry to send: from its own best start, the call's length kept inside 5 to 10 s."""
    want = min(max(float(seconds), BEST[0]), BEST[1])
    have = float(entry.get("seconds") or want)
    start = float(entry.get("from") or 0.0)
    return {"kind": "movement", "use": entry.get("kind", "talking"), "id": entry["id"], "src": entry["file"], "from": round(start, 2),
            "seconds": round(min(want, max(have - start, 1.0)), 2)}


CAPTION_BAND = "drawbox=x=0:y=468:w=480:h=215:color=0x1c1c1c:t=fill"     # on the 480-wide frame: a flat bar over a swipe's burned-in captions


def prepare(src: Path, dest: Path, start: float, seconds: float, ffmpeg: str = "ffmpeg", runner=None,
            clear_words: bool = False) -> Path:
    """No sound, no colour, a little soft, 480 wide: the movement, never the person. A swipe's captions are wiped first."""
    wipe = CAPTION_BAND + "," if clear_words else ""
    runner = runner or (lambda cmd: subprocess.run(cmd, check=True, capture_output=True))
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    runner([ffmpeg, "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}", "-i", str(src), "-an",
            "-vf", f"scale=480:-2,{wipe}format=gray,gblur=sigma={SOFT},format=yuv420p", str(dest)])
    return Path(dest)


def make(run: Path, ref: dict, ffmpeg: str = "ffmpeg", runner=None) -> Path:
    """The prepared piece for one planned movement ref, made once (local ffmpeg, no network, no money)."""
    dest = Path(run) / ref["file"]
    root = HERE.parents[2]
    src = root / ref["src"]
    source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    signature = hashlib.sha256(json.dumps([source_hash, ref["from"], ref["seconds"], SOFT, 480] + (["bar"] if ref.get("clear_words") else [])).encode()).hexdigest()
    stamp = dest.with_suffix('.source.json')
    if dest.is_file() and stamp.is_file() and json.loads(stamp.read_text()).get('signature') == signature:
        return dest
    cached = root / 'runs/ai-elements/movement/prepared' / (signature + '.mp4')
    if not cached.is_file():
        prepare(src, cached, ref["from"], ref["seconds"], ffmpeg, runner, clear_words=bool(ref.get("clear_words")))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, dest)
    stamp.write_text(json.dumps({'signature': signature, 'reference': ref['id'], 'source_sha256': source_hash}))
    return dest


def talk_stretch(sb: dict) -> tuple:
    """(start, end) of the swipe's longest unbroken run of talking shots, read from the storyboard."""
    if sb.get("talk_window"):       # a person's measured window wins: the frame map does not time every graphic
        return tuple(sb["talk_window"])
    # a shot with a graphic or card on it would carry into the clip (2026-10-31: the swipe's razor walked into ours)
    shots = sorted({(float(k["start"]), float(k["end"])) for g in sb.get("sections") or [] if g.get("maker") == "lip-sync"
                    for k in (g.get("swipe") or {}).get("shots") or []
                    if k.get("start") is not None and k.get("end") is not None
                    and not re.search(r"graphic|cartoon|sticker", json.dumps([k.get("frame"), k.get("overlays")]), re.I)})
    runs = []
    for a, z in shots:
        if runs and a <= runs[-1][1] + 0.2:
            runs[-1][1] = max(runs[-1][1], z)
        else:
            runs.append([a, z])
    return tuple(max(runs, key=lambda r: r[1] - r[0])) if runs else (0.0, 0.0)


def from_swipe(call: dict, teardown: Path, start: float, talk: tuple) -> list:
    """A talking clip's one movement reference: the swipe's own creator talking, nearest its own moment in the swipe
    (owner, 2026-10-31: "just use the content creator we're swiping from as the talking man reference")."""
    src = Path(teardown).resolve() / "source.mp4"
    begin, end = talk
    if not src.is_file() or end <= begin:
        return []
    seconds = round(min(max(float(call.get("duration") or call.get("seconds") or 5), BEST[0]), BEST[1], end - begin), 2)
    start = round(max(min(float(start), end - seconds), begin), 2)
    return [{"kind": "movement", "use": "talking", "id": "swipe-creator", "src": str(src.relative_to(HERE.parents[2])),
             "from": start, "seconds": seconds, "clear_words": True,
             "file": f"clips/refs/{call['id']}-swipe-creator-{seconds}-move1.mp4"}]


def for_call(call: dict, does: str, entry_id=None) -> list:
    """The real-video refs for one call, chosen by what the shot shows; a person picked by hand on the board wins."""
    if entry_id == "none":
        return []
    got = ([e for e in bank() if e['id'] == entry_id] if entry_id else choose(call, does))
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
