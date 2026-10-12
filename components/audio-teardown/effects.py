"""THE EFFECTS — every added sound, timed by a tool, named by an ear.

    TIMED     every sharp sound in the voices-removed track (measure.py events):
              onsets sharper than 85% of the track's own, each tagged by Google's
              AudioSet sound list (PANNs) and marked on or off the beat
    NAMED     Gemini listens to that track with the list of moments
              (prompts/effects-name-v<N>-damon.md): what each really is, whether
              it was added in the edit or made by the room or the product, its
              job in the edit, its UCS category — and adds any it missed
    FILED     every name under a UCS category (definitions/sound.json); the
              machine's own AudioSet guess is filed by rule when the ear is silent

The tagger alone is weak on edit effects (it heard whooshes as "Animal" and
"Vehicle" across a dozen swipes, 2026-09-30); it is trusted for WHEN, the ear for WHAT.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import gemini as G

HERE = Path(__file__).resolve().parent
PY = Path(os.environ.get("AUDIO_PYTHON") or "/nonexistent/audio-python")
DEF = json.loads((HERE / "definitions" / "sound.json").read_text())
LISTS = {k: DEF["lists"][k] for k in ("effect_job", "ucs_category")}
RULES = DEF["audioset_to_ucs"]["rules"]
ROOMISH = {"Inside, small room", "Inside, large room or hall", "Silence", "Outside, urban or manmade",
           "Outside, rural or natural", "Environmental noise", "Noise"}


def ucs_of(sound):
    s = (sound or "").lower()
    for pat, cat in RULES:
        if re.search(pat, s):
            return cat
    return "OBJECTS"


def timed(track, beats):
    r = subprocess.run([str(PY), str(HERE / "measure.py"), "events", str(track), json.dumps(beats or [])],
                       capture_output=True, text=True, timeout=900)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stderr or r.stdout)[-200:], "events": []}


def check(track, cands):
    """Each moment on its own 1.2-second clip: is it an effect, and what is it."""
    import tempfile
    from concurrent.futures import ThreadPoolExecutor
    p, q = G.prompt("effects-check", HERE)

    def one(e):
        with tempfile.TemporaryDirectory() as td:
            c = Path(td) / "c.mp3"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(max(0, e["at"] - 0.4)), "-t", "1.2",
                            "-i", str(track), str(c)], check=True)
            try:
                r, _, _ = G.ask(c, q, models=[("gemini-3.5-flash", 60), ("gemini-3.1-pro-preview", 90)])
                return e | {"check": r if isinstance(r, dict) else {}}
            except Exception as x:
                return e | {"check": {"error": str(x)[:120]}}
    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(one, cands)), p.name


def read(track, beats=None):
    """The effects section of the Sound Sheet."""
    if not track or not Path(track).exists():
        return {"effects": [], "why": "no voices-removed track to listen to"}
    t = timed(track, beats)
    cands = []
    for e in t.get("events", []):
        if e.get("music_likelihood", 0) >= 0.5:
            continue
        if cands and e["at"] - cands[-1]["at"] < 0.35:       # one moment, not three onsets of it
            continue
        cands.append(e)
    cands = cands[:30]
    checked, check_prompt = check(track, cands) if cands else ([], None)
    confirmed = [c for c in checked if c["check"].get("effect")]
    out = {"machine": {"onsets": t.get("onsets"), "candidates": checked, "error": t.get("error")},
           "moments_found": len(cands), "moments_confirmed": len(confirmed), "check_prompt": check_prompt}
    listing = "\n".join(f"- {c['at']}s · {c['check'].get('name') or 'effect'} (sure: {c['check'].get('sure', '—')})"
                        for c in confirmed) or "- (none confirmed)"
    p, text = G.prompt("effects-name", HERE)
    text = text.replace("{events}", listing).replace("{lists}", json.dumps(LISTS))
    try:
        heard, model, _ = G.ask(track, text)
        heard = heard if isinstance(heard, dict) else {}
        out["heard_by"], out["prompt"] = model, p.name
    except Exception as e:
        heard, out["heard_error"] = {}, str(e)[:200]
    by_time = {round(c["at"], 1): c for c in confirmed}
    effects, used = [], set()
    for e in heard.get("effects") or []:
        at = round(float(e.get("at") or 0), 2)
        near = next((c for c in confirmed if abs(c["at"] - at) <= 0.35 and id(c) not in used), None)
        if near:
            used.add(id(near))
        elif not e.get("missed_by_list"):
            continue                                          # not a confirmed moment and not claimed as missed
        cat = e.get("ucs_category") or ""
        effects.append({"at": near["at"] if near else at, "name": (near or {}).get("check", {}).get("name") or e.get("name"),
                        "sure": (near or {}).get("check", {}).get("sure", "whole-track only"),
                        "ucs_category": cat if cat in LISTS["ucs_category"] else (f"other: {cat}" if cat else ucs_of(e.get("name"))),
                        "job": e.get("job"), "added": e.get("added")})
    for c in confirmed:                                       # confirmed but the whole-track read skipped it
        if id(c) not in used:
            name = c["check"].get("name")
            effects.append({"at": c["at"], "name": name, "sure": c["check"].get("sure"), "ucs_category": ucs_of(name),
                            "job": None, "added": None})
    effects.sort(key=lambda x: x["at"])
    out["effects"], out["room"] = effects, heard.get("room")
    out["unknown_labels"] = [f"job: {e['job']}" for e in effects if e.get("job") and e["job"] not in LISTS["effect_job"]]
    return out


def render(ef):
    md = ["### EFFECTS", ""]
    fx = ef.get("effects") or []
    if not fx:
        md.append("No added sound effects found." + (f" ({ef.get('why')})" if ef.get("why") else ""))
    else:
        md += ["| Time | Sound | Sure | UCS category | Job | Added in the edit? |", "|---|---|---|---|---|---|"]
        md += [f"| {e['at']}s | {e.get('name') or '—'} | {e.get('sure') or '—'} | {e.get('ucs_category') or '—'} | {e.get('job') or '—'} | "
               f"{'yes' if e.get('added') else 'no — room or product' if e.get('added') is False else '—'} |" for e in fx]
    md += ["", f"- **Room:** {ef.get('room') or '—'}",
           f"- **How found:** {ef.get('moments_found', '—')} sharp moments timed by the tool, "
           f"{ef.get('moments_confirmed', '—')} confirmed as effects, each on its own clip"]
    if ef.get("heard_error"):
        md.append(f"- Not heard: {ef['heard_error']} — the list above is the machine's own")
    return "\n".join(md + [""])
