#!/usr/bin/env python3
"""audiocheck.py — the voice is checked BEFORE any picture is paid for.

the owner, 2026-09-23: "the script itself and audio is what drives the video,
then the clips are just representations of what's being said and heard" —
and the cut-off line "should happen at the production level". So the one
read is heard right after `voice.py` makes it, scene by scene, and the run
stops here if a slice is wrong. Before this, the words were only checked on
the finished clip, after the frames and the clip had been paid for.

    python3 machine/audiocheck.py <run> [--fix]        # --fix remakes a failing slice once (voice only)

Per scene slice (`vo/<scene>.mp3` against `lines.json[scene]`):
  words     the slice says its line (lineparity's match, same threshold)
  finished  the line's last words are heard at the end (lineparity.ending_heard)
  sound     not silent and not clipping (integrated loudness above −50 LUFS,
            true peak under 0 dBTP) — only broken audio stops a run.
  protected every protected word of the brand in the line (brands/<brand>/brand-identity/voice/
            pronunciation.json — brand, product, ingredient, mechanism) is heard,
            matched on its REAL spelling (fuzzy, providers.json
            gates.protected_words), and every figure is heard as the words it is
            said as (spoken_numbers). A miss is a stop, named. A word nobody has
            confirmed by ear yet is a WARNING listing it — never a stop.
  level     reported, not a stop: every slice's loudness, and a warning when
            the quietest and loudest scenes are more than 6 LU apart (the read
            drifting in volume from scene to scene).

A failing slice is remade ONCE, voice only (`voice.remake_scene`: same text,
voice, settings, stitched on the same earlier read), then heard again. Still
failing → the run stops, named, before any frame or clip is made. Written to
`vo/audio-check.json` and to `verdicts.json[scene]["voice"]`.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUIET_LUFS = -50.0          # below this there is no voice to speak of — a stop
DRIFT_LU = 6.0              # scenes further apart than this are named as a level problem, not a stop
PEAK_DBTP = 0.0


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def loudness(path: Path) -> tuple[float | None, float | None]:
    """(integrated LUFS, true peak dBTP) off ffmpeg's ebur128 meter."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    text = r.stderr.split("Summary:")[-1]
    i = re.search(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", text)
    pk = re.search(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", text)
    f = lambda m: (None if not m else (-99.0 if m.group(1) == "-inf" else float(m.group(1))))
    return f(i), f(pk)


def numbers_heard(line: str, heard: str) -> list[dict]:
    return _load("spoken_numbers").figures_heard(line, heard)


HUMS = {"mm", "mmm", "hmm", "mhm", "mm-hmm", "mmhmm", "uh-huh", "uh", "um", "huh", "hm"}


def hum_only(line: str) -> bool:
    w = re.sub(r"[^a-z\- ]", " ", (line or "").lower()).split()
    return bool(w) and all(x.strip("-") in HUMS or x in HUMS for x in w)


def check_slice(path: Path, line: str, transport=None, key=None, rows=None) -> dict:
    lp = _load("lineparity")
    lx = _load("lexicon")
    heard = lp.check(path, line, transport=transport, key=key)
    lufs, peak = loudness(path)
    sound_ok = lufs is not None and lufs > QUIET_LUFS and (peak is None or peak < PEAK_DBTP)
    problems = []
    # A HUM IS NOT A SPELLING (2026-10-02): "Mm-hmm." comes back as "Mhm", or in
    # another script altogether ("Угу", "हम्म") — the transcriber has no fixed
    # spelling for it. A line made only of hums passes when a short sound is heard.
    if hum_only(line) and (heard.get("heard") or "").strip():
        heard = {**heard, "verdict": "PASS"}
    if heard["verdict"] == "CUT_OFF":
        problems.append("the line does not finish")
    elif heard["verdict"] != "PASS":
        problems.append(f"says other words (match {heard['match']})")
    if not sound_ok:
        problems.append(f"broken sound ({lufs} LUFS, peak {peak} dBTP)")
    protected = lx.heard_check(line, heard["heard"], rows or [], lx.threshold_of())
    for p in protected:
        if not p["heard_ok"]:
            problems.append(f"protected word not heard: {p['term']!r} (sent as {p['say_as']!r}, best match {p['match']})")
    figures = numbers_heard(line, heard["heard"])
    for f in figures:
        if not f["heard_ok"]:
            problems.append(f"number not heard as said: {f['figure']!r} should be {f['said']!r}")
    unconfirmed = lx.unconfirmed_in(line, rows or [])
    return {"heard": heard["heard"], "match": heard["match"], "finished": heard.get("ending_heard"),
            "lufs": lufs, "peak_dbtp": peak, "protected": protected, "numbers": figures,
            "unconfirmed": unconfirmed, "pass": not problems, "problems": problems, "at": now()}


def check_run(run: Path, fix: bool = True, transport=None, key=None, voice_transport=None) -> dict:
    """Every slice of the one read, heard. Returns {"pass": bool, "scenes": {...}}
    and writes vo/audio-check.json. A run with no read (nothing speaks) passes."""
    lp = _load("lineparity")
    pre = _load("preflight")
    lines = json.loads((run / "lines.json").read_text()) if (run / "lines.json").exists() else {}
    k = key if key is not None else lp.key_of()
    out = {"at": now(), "scenes": {}, "pass": True}
    rows = _load("lexicon").for_run(run)
    if not any(lines.values()):
        out["note"] = "nothing speaks in this run"
        return out
    if not k:
        out.update({"pass": True, "note": "no ELEVENLABS_API_KEY — the voice could not be heard, so it was not checked"})
        print("audio check skipped — no ELEVENLABS_API_KEY")
        return out
    for sid, text in lines.items():
        if not text:
            continue
        path = run / "vo" / f"{sid}.mp3"
        if not path.exists():
            out["scenes"][sid] = {"pass": False, "problems": [f"no voice slice at vo/{sid}.mp3"]}
            out["pass"] = False
            continue
        res = check_slice(path, text, transport=transport, key=k, rows=rows)
        if not res["pass"] and fix:
            first = res
            vmod = _load("voice")
            vmod.remake_scene(run, sid, transport=voice_transport, key=k)
            res = check_slice(path, text, transport=transport, key=k, rows=rows)
            res["remade"] = {"once": True, "first_try": first}
        out["scenes"][sid] = res
        pre.verdict(run, sid, "voice", {"verdict": "PASS" if res["pass"] else "FAIL", **{x: res.get(x) for x in ("heard", "match", "finished", "lufs", "problems", "unconfirmed")}})
        if not res["pass"]:
            out["pass"] = False
    unconfirmed = sorted({t for r in out["scenes"].values() for t in r.get("unconfirmed") or []})
    if unconfirmed:
        out["warnings"] = [f"not yet confirmed by ear: {', '.join(unconfirmed)} — the owner hears them "
                           f"(machine/say_it.py <brand>) and marks them confirmed in the brand's "
                           f"brand-identity/voice/pronunciation.json"]
    levels = {sid: r.get("lufs") for sid, r in out["scenes"].items() if r.get("lufs") is not None}
    if levels:
        lo, hi = min(levels.values()), max(levels.values())
        out["level"] = {"quietest": [k for k, v in levels.items() if v == lo][0], "loudest": [k for k, v in levels.items() if v == hi][0],
                        "spread_lu": round(hi - lo, 1), "warning": (hi - lo) > DRIFT_LU}
    (run / "vo").mkdir(parents=True, exist_ok=True)
    (run / "vo" / "audio-check.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


def report(out: dict) -> None:
    for sid, r in out.get("scenes", {}).items():
        tag = "PASS" if r.get("pass") else "STOP"
        extra = " (remade once)" if r.get("remade") else ""
        print(f"{tag}  voice {sid}{extra} · {r.get('lufs')} LUFS" + ("" if r.get("pass") else f" — {'; '.join(r.get('problems') or [])} — heard {r.get('heard')!r}"))
    _level_line(out)


def _level_line(out: dict) -> None:
    for w in out.get("warnings") or []:
        print(f"WARN  {w}")
    lv = out.get("level")
    if lv and lv["warning"]:
        print(f"WARN  the read drifts in volume: {lv['spread_lu']} LU between {lv['loudest']} (loudest) and {lv['quietest']} (quietest)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run"); ap.add_argument("--fix", action="store_true", help="remake a failing slice once, voice only")
    a = ap.parse_args(argv)
    out = check_run(Path(a.run).resolve(), fix=a.fix)
    report(out)
    return 0 if out["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
