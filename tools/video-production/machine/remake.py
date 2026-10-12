#!/usr/bin/env python3
"""remake.py — make ONE scene's clip again, with exactly one thing fixed.

the owner, 2026-09-23: "A clip that cuts off mid line, that needs to be
reproduced and clearly identified as an error" … "that needs to trigger a
specific skill to regenerate the clip properly without any slop and just do
exactly what's needed." The skill is `.claude/skills/remake-clip/`; this is
the tool it runs.

    python3 machine/remake.py order  <run> --scene <id> --why cut-off [--element voice|frame|clip] [--change "<the one fix, for a frame>"] [--heard "..."] [--dry-run]
    python3 machine/remake.py voice  <run> --scene <id>          # the voice step, headless
    python3 machine/remake.py record <run> --scene <id> --file <new clip.mp4> [--job <id>]
    python3 machine/remake.py status <run>

SURGICAL (the owner, 2026-09-23): "we need to be conscious of the element that
needs to be regenerated. If it's just the audio then we regen the audio;
then if the person is speaking we take the same frames used in the original
generation and just change the audio track." A scene is three elements —
the VOICE slice, the FRAMES, the CLIP made from them. The order names the
broken one and remakes only it, then remakes what is built on it from the
same originals:
  voice  → the scene's voice slice again (same text, voice, settings, stitched
           on the same earlier request ids) → the clip again from the SAME
           frames with the new slice
  frame  → the frame edited with ONE change (the frame-edit skill) → the clip
           again with the SAME voice slice
  clip   → the clip again from the same frames and the same slice
`--why cut-off` finds the element itself: the voice slice is transcribed
first — if the slice stops short, the voice is the broken element; if the
slice is whole, the clip is.

`order` finds the scene's clip request exactly as it was first sent (the
run's own batches), changes the ONE field the reason names, and writes
`<run>/remakes/<scene>-r<N>.json`: the request to send, every input as a
file path, what changed and why. Nothing else moves — not the prompt, not
the frames, not the voice slice, not the model. It spends nothing.

`record` files the new take: the old clip is archived (never overwritten),
the new one checked against its line — including that the line FINISHED —
and the verdict written. A clip still cut off after the second try stops
for a person (RUN-PROTOCOL: one re-prompt, then a re-composition, never a
third try on the same composition).

The one fix per reason:
  cut-off   the clip was shorter than its line. Talking on a voice slice →
            the clip runs the slice's length plus half a second; a line in
            the prompt → 2.5 words a second plus 0.8 s. Past the door's
            ceiling it is refused: split the scene at a sentence break.
            If the length already fits, the fix is a fresh take of the SAME
            request (the model stopped early) — said so on the order.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REASONS = ("cut-off", "wrong-voice", "wrong-frame", "wrong-clip")
MAX_TRIES = 2
WORDS_PER_SECOND = 2.5


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def seconds_of(f: Path) -> float | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def clip_item(run: Path, scene: str) -> dict:
    platform = _load("platform")
    for f in sorted((run / "batches").glob("*.json")):
        for it in platform.load_batch(f):
            if str(it.get("id")) == scene and it.get("kind") in ("talking", "motion"):
                return {**it, "_batch": f.name}
    raise SystemExit(f"{scene}: no clip request for this scene in {run / 'batches'} — "
                     f"a run made by hand outside the machine has nothing to remake from; make it through the machine first")


def resolve(run: Path, value: str) -> str:
    """A media value names a frame this run made (`S1-F1`) or a path."""
    for ext in (".png", ".jpg", ".mp4", ".mp3", ".wav"):
        p = run / "media" / f"{value}{ext}"
        if p.exists():
            return str(p)
    p = Path(value) if Path(value).is_absolute() else run / value
    return str(p)


def tries_so_far(run: Path, scene: str) -> list[Path]:
    return sorted((run / "remakes").glob(f"{scene}-r*.json"), key=lambda p: int(p.stem.rsplit("-r", 1)[1]))


def ceiling_of(item: dict) -> float | None:
    try:
        mi = _load("model_inputs")
        span = mi.duration_span("talking" if item.get("kind") == "talking" else "motion", (item.get("params") or {}).get("model"))
        return float(span[1]) if len(span) > 1 else None
    except Exception:
        return None


def order(a) -> int:
    run = Path(a.run).resolve()
    item = clip_item(run, a.scene)
    tries = tries_so_far(run, a.scene)
    if len(tries) >= MAX_TRIES:
        print(f"STOP  {a.scene}: remade {len(tries)} times already — a third try on the same composition is never made. "
              f"This needs a person: split the scene at a sentence, or rewrite its composition.")
        return 2
    params = dict(item.get("params") or {})
    medias = [{**m, "file": resolve(run, str(m["value"]))} for m in item.get("medias") or [] if m.get("value")]
    lp = _load("lineparity")
    line = lp.line_text_of(run, item) if item.get("lines") else ""
    was = params.get("duration")
    change, why = {}, ""
    if a.why == "cut-off":
        audio = next((m["file"] for m in medias if m.get("role") in ("audio", "audio_references")), None)
        if audio and Path(audio).exists():
            need = math.ceil((seconds_of(Path(audio)) or 0) + 0.5)
            basis = f"its voice slice runs {seconds_of(Path(audio)):.1f}s"
        else:
            words = len(lp.normalize(lp.spoken(line)))
            need = math.ceil(words / WORDS_PER_SECOND + 0.8)
            basis = f"its line is {words} words (at {WORDS_PER_SECOND} words a second)"
        ceiling = ceiling_of(item)
        if ceiling and need > ceiling:
            print(f"STOP  {a.scene}: the line needs {need}s and this door's ceiling is {ceiling:.0f}s — "
                  f"split the scene at a sentence break; the clip is never quietly shortened.")
            return 2
        if was is None or float(was) < need:
            change = {"duration": str(need) if isinstance(was, str) else need}
            why = f"the clip was {was}s and {basis}, so it ran out before the line finished"
        else:
            why = f"the length already fits ({was}s; {basis}) — the model stopped early, so this is a fresh take of the SAME request"
    element = a.element or {"wrong-voice": "voice", "wrong-frame": "frame", "wrong-clip": "clip"}.get(a.why)
    if a.why != "cut-off":
        why = f"{a.why.replace('-', ' ')}" + (f": {a.change}" if a.change else "")
    audio_file = next((m["file"] for m in medias if m.get("role") in ("audio", "audio_references")), None)
    if element is None and a.why == "cut-off":
        if not audio_file or not line:
            element = "clip"
        elif a.dry_run:
            element = "clip (the voice slice is checked first on a real order)"
        else:
            vres = lp.check(Path(audio_file), line)
            element = "voice" if vres["verdict"] == "CUT_OFF" or not vres.get("ending_heard") else "clip"
            why = (f"the voice slice itself stops short (heard {vres['heard']!r})" if element == "voice" else why)
    element = element or "clip"
    steps = []
    if element == "voice":
        steps.append({"step": "voice", "do": "remake this scene's voice slice — same text, voice, settings, stitched on the same earlier read", "by": "remake.py voice", "state": "to do"})
        change = {}
    if element == "frame":
        if not a.change:
            print(f"STOP  {a.scene}: a frame remake needs the ONE change in words (--change)."); return 2
        steps.append({"step": "frame", "do": f"edit the frame with one change: {a.change}", "by": "the frame-edit skill", "state": "to do"})
    talking = item.get("kind") == "talking" or bool(audio_file)
    steps.append({"step": "clip", "do": ("the clip again from the SAME frames with the NEW voice slice" if element == "voice" else
                                        "the clip again from the NEW frame with the SAME voice slice" if element == "frame" else
                                        "the clip again from the same frames and the same voice slice"),
                  "by": "the remake-clip skill (Higgsfield)" if str(item.get("door", "")).startswith("higgsfield") else "the run's direct door",
                  "state": "waiting on the step before" if len(steps) else "to do"})
    kept = {"voice": "the prompt, both frames, the model, every setting",
            "frame": "the prompt, the voice slice, the model, every setting",
            "clip": "the prompt, both frames, the voice slice, the model, every setting"}[element.split(" ")[0]]
    n = len(tries) + 1
    rec = {"scene": a.scene, "try": n, "reason": a.why, "element": element, "heard": a.heard, "line": line,
           "why": why, "change": change, "unchanged": kept, "talking": talking, "steps": steps,
           "request": {**params, **change}, "medias": medias, "door": item.get("door"),
           "from_batch": item["_batch"], "ordered": now(), "state": "ordered"}
    if a.dry_run:
        print(json.dumps(rec, indent=1, ensure_ascii=False))
        return 0
    dest = run / "remakes" / f"{a.scene}-r{n}.json"
    write(dest, rec)
    print(f"ORDER {a.scene} try {n}: the broken element is the {element} — {why}")
    for st in steps:
        print(f"  {st['step']:>5}: {st['do']}  [{st['by']}]")
    print(f"  kept exactly: {kept}")
    print(f"  written: {dest}")
    return 0


def voice(a) -> int:
    """The voice step of an order, headless: the scene's slice again, then the
    clip step's request is re-timed to the new slice (a talking clip runs its
    slice's length plus half a second) — frames untouched."""
    run = Path(a.run).resolve()
    tries = tries_so_far(run, a.scene)
    if not tries:
        raise SystemExit(f"{a.scene}: no remake order on file — run `order` first")
    rec = read(tries[-1])
    st = next((x for x in rec.get("steps") or [] if x["step"] == "voice"), None)
    if not st:
        raise SystemExit(f"{a.scene}: this order does not remake the voice")
    vmod = _load("voice")
    res = vmod.remake_scene(run, a.scene)
    lp = _load("lineparity")
    check = lp.check(Path(res["file"]), rec["line"]) if rec.get("line") else None
    st.update({"state": "done" if (not check or check["verdict"] == "PASS") else f"voice still {check['verdict']}", "result": res, "check": check})
    if check and check["verdict"] != "PASS":
        write(tries[-1], rec)
        print(f"STOP  {a.scene}: the new voice slice is {check['verdict']} too (heard {check['heard']!r}) — the line itself needs a person.")
        return 1
    need = math.ceil((res.get("seconds") or 0) + 0.5)
    was = rec["request"].get("duration")
    if was is None or float(was) < need:
        rec["request"]["duration"] = str(need) if isinstance(was, str) else need
        rec["change"] = {"duration": rec["request"]["duration"]}
    clip = next(x for x in rec["steps"] if x["step"] == "clip")
    clip["state"] = "to do"
    write(tries[-1], rec)
    print(f"VOICE {a.scene}: new slice {res.get('seconds'):.1f}s, the line finishes. Next: the clip, same frames, new slice.")
    return 0


def record(a) -> int:
    run = Path(a.run).resolve()
    tries = tries_so_far(run, a.scene)
    if not tries:
        raise SystemExit(f"{a.scene}: no remake order on file — run `order` first")
    rec_path = tries[-1]
    rec = read(rec_path)
    new = Path(a.file).resolve()
    if not new.exists():
        raise SystemExit(f"{new}: not found")
    media = run / "media"
    old = media / f"{a.scene}.mp4"
    if old.exists():
        arch = media / "versions"
        arch.mkdir(parents=True, exist_ok=True)
        k = 1
        while (arch / f"{a.scene}-v{k}.mp4").exists():
            k += 1
        old.rename(arch / f"{a.scene}-v{k}.mp4")
        rec["archived"] = str(arch / f"{a.scene}-v{k}.mp4")
    media.mkdir(parents=True, exist_ok=True)
    dest = media / f"{a.scene}.mp4"
    dest.write_bytes(new.read_bytes())
    rec.update({"file": str(dest), "job": a.job, "recorded": now()})
    for st in rec.get("steps") or []:
        if st["step"] == "clip":
            st["state"] = "done"
    if rec.get("line"):
        lp = _load("lineparity")
        pre = _load("preflight")
        res = lp.check(dest, rec["line"])
        pre.verdict(run, a.scene, "parity", res)
        rec["parity"] = res
        rec["state"] = "fixed" if res["verdict"] == "PASS" else ("still cut off" if res["verdict"] == "CUT_OFF" else "flagged")
    else:
        rec["state"] = "recorded — no line to check"
    write(rec_path, rec)
    print(f"{rec['state'].upper()}  {a.scene} try {rec['try']}" + (f" — heard: {rec['parity']['heard']!r}" if rec.get("parity") else ""))
    if rec["state"] == "still cut off" and rec["try"] >= MAX_TRIES:
        print("  STOP — two tries, still cut off. This needs a person.")
    return 0 if rec["state"] in ("fixed", "recorded — no line to check") else 1


def status(a) -> int:
    run = Path(a.run).resolve()
    rows = sorted((run / "remakes").glob("*.json"))
    if not rows:
        print("no remakes on this run")
    for p in rows:
        r = read(p)
        print(f"{r['scene']:>8} try {r['try']}  {r['state']:<18} {r['reason']} · element: {r.get('element', 'clip')} — {r['why']}")
        for st in r.get("steps") or []:
            print(f"{'':>10}{st['step']:>6}: {st['state']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("order"); o.add_argument("run"); o.add_argument("--scene", required=True)
    o.add_argument("--why", required=True, choices=REASONS); o.add_argument("--heard", default=""); o.add_argument("--dry-run", action="store_true")
    o.add_argument("--element", choices=["voice", "frame", "clip"], help="which element is broken; cut-off finds it itself")
    o.add_argument("--change", default="", help="the ONE change, when the element is the frame")
    o.set_defaults(fn=order)
    r = sub.add_parser("record"); r.add_argument("run"); r.add_argument("--scene", required=True)
    r.add_argument("--file", required=True); r.add_argument("--job", default=None); r.set_defaults(fn=record)
    v = sub.add_parser("voice"); v.add_argument("run"); v.add_argument("--scene", required=True); v.set_defaults(fn=voice)
    s = sub.add_parser("status"); s.add_argument("run"); s.set_defaults(fn=status)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
