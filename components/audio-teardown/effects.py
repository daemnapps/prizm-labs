"""THE EFFECTS — every added sound, timed and grouped by a tool, named once per sound by an ear, from one list.

    TIMED     every sharp onset in the top 30% of the voices-removed track and every soft stretch the music's loop
              does not hold (a riser, a swell, a whoosh); each with how much louder it is than the same place in the
              music's own loop (`stands_out`), its fingerprint group (the same added sound = the same group) and the
              nearest bank sound by that fingerprint (`bank_match`) — all measure.py events, the same every run
    HEARD     ONE read of the whole track (prompts/effects-check-v<N>): every moment listed by group, the ear says
              which groups are added sounds (and at which moments, when only some are), names each group ONCE with a
              value of definitions/sound.json `effect_name`, gives its job and category, and adds what the tool
              missed, soft sounds included
    FILED     every name under a UCS category (definitions/sound.json) and, when the bank holds it, its bank sound

Why (2026-11-15): on one swipe the same three hits were typewriter/click/whoosh on one run and camera shutter on the
next, and one run missed a click the other found. The old pass kept the top 15% of onsets, dropped every one the
tagger heard as music (in a song: all of them), judged each moment alone on a 1.2 s clip and let the whole-track read
rename it freely. A per-moment A/B listen (the loop, then the moment) was tried the same day on the fast model and was
worse: the same snare came back "spray", "paper" and "cloth". One whole-track read on the judge model, groups named
once from a fixed list, is what held.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import gemini as G

HERE = Path(__file__).resolve().parent
PY = Path.home() / ".daemn" / "venvs" / "audio" / "bin" / "python"
DEF = json.loads((HERE / "definitions" / "sound.json").read_text())
LISTS = {k: DEF["lists"][k] for k in ("effect_job", "ucs_category")}
NAMES = DEF["lists"]["effect_name"]
BANK_OF = {k: v for k, v in DEF.get("effect_bank", {}).items() if not k.startswith("_")}
RULES = DEF["audioset_to_ucs"]["rules"]
ALIAS = {"woosh": "whoosh", "swish": "swoosh", "shutter": "camera shutter", "typing": "typewriter",
         "keyboard": "typewriter", "cash register": "ka-ching", "tick": "ticking", "scratch": "record scratch",
         "hit": "impact", "bang": "impact", "sweep": "riser", "uplifter": "riser"}


def ucs_of(sound):
    s = (sound or "").lower()
    for pat, cat in RULES:
        if re.search(pat, s):
            return cat
    return "OBJECTS"


def snap(name):
    """A heard name onto the list: exact, an alias, the list value it contains, else "other: <name>"."""
    n = re.sub(r"[^a-z\- ]+", "", str(name or "").lower()).strip()
    if not n or n in ("null", "none"):
        return None
    if n in NAMES:
        return n
    if n in ALIAS:
        return ALIAS[n]
    for v in sorted(NAMES, key=len, reverse=True):
        if v != "other" and re.search(r"\b%s\b" % re.escape(v), n):
            return v
    for k, v in ALIAS.items():
        if re.search(r"\b%s\b" % re.escape(k), n):
            return v
    return "other: " + n


def bank_files():
    """Every banked effect on this machine (Shared Assets/banks/sfx), for the fixed nearest-sound match."""
    roots = [Path(os.environ["AUDIO_TEARDOWN_SFX_BANK"])] if os.environ.get("AUDIO_TEARDOWN_SFX_BANK") else []
    roots += [r / "Shared Assets" / "banks" / "sfx" for r in
              sorted(Path.home().glob("Library/CloudStorage/GoogleDrive-*/Shared drives"))]
    for r in roots:
        if r.is_dir():
            return sorted(str(f) for f in r.glob("*.mp3"))
    return []


def timed(track, beats, bank=None):
    args = [str(PY), str(HERE / "measure.py"), "events", str(track), json.dumps(beats or [])]
    if bank:
        args.append(json.dumps(bank))
    r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stderr or r.stdout)[-200:], "events": []}


def listing(events):
    """The moments as the ear reads them: one line per group, its moments in time order."""
    by = {}
    for e in events:
        by.setdefault(e["group"], []).append(e)
    lines = []
    for g in sorted(by, key=lambda g: by[g][0]["at"]):
        ms = by[g]
        kind = "soft rise" if all(m["kind"] == "soft" for m in ms) else "sharp hit"
        lines.append(f"- group {g} ({kind}): " + ", ".join(
            f"{m['at']}s" + (f"-{m['until']}s" if m.get("until") else "") for m in ms))
    return "\n".join(lines) or "- (the tool timed nothing)"


def apply(events, heard):
    """The ear's groups onto the tool's moments: [effect rows], every member of an added group (or only the moments
    it names) carries the group's one name. A name off the list is kept as "other: <name>"."""
    out = []
    by = {g.get("group"): g for g in heard.get("groups") or [] if isinstance(g, dict)}
    for e in events:
        g = by.get(e["group"])
        if not g or not g.get("added"):
            continue
        only = [float(x) for x in g.get("only_at") or [] if isinstance(x, (int, float, str)) and
                re.match(r"^[0-9.]+$", str(x))]
        if only and not any(abs(e["at"] - x) <= 0.12 for x in only):
            continue
        out.append(row(e, g))
    for m in heard.get("missed") or []:
        try:
            at = round(float(m.get("at")), 2)
        except (TypeError, ValueError):
            continue
        if any(abs(r["at"] - at) <= 0.2 for r in out):
            continue
        until = m.get("until")
        near = min(events, key=lambda e: abs(e["at"] - at), default=None)
        if near and abs(near["at"] - at) <= 0.15 and not isinstance(until, (int, float)):
            out.append(row(near, m, found="tool + ear"))      # the ear's moment, at the second the tool measured
            continue
        out.append(row({"at": at, "until": round(float(until), 2) if isinstance(until, (int, float)) else None,
                        "kind": "soft" if isinstance(until, (int, float)) and until - at >= 0.25 else "hit"}, m,
                       found="ear only"))
    return sorted(out, key=lambda r: r["at"])


def row(e, g, found="tool + ear"):
    name = snap(g.get("name"))
    cat = g.get("ucs_category") or ""
    r = {"at": e["at"], "until": e.get("until"), "kind": e.get("kind") or "hit", "name": name, "sure": g.get("sure"),
         "ucs_category": cat if cat in LISTS["ucs_category"] else (f"other: {cat}" if cat else ucs_of(name)),
         "job": g.get("job"), "added": g.get("in_the_edit"), "found": found}
    r.update({k: e[k] for k in ("group", "stands_out", "bank_match") if e.get(k) is not None})
    if name in BANK_OF:
        r["bank"] = BANK_OF[name]
    return r


def picture_lines(picture):
    """The picture's own edit moments, one line each, for the ear to hear the sound against."""
    rows = []
    for m in picture or []:
        try:
            rows.append(f"- {float(m['at']):.2f}s · {str(m.get('what') or 'an edit move')[:100]}")
        except (KeyError, TypeError, ValueError):
            continue
    return "\n".join(rows) or "- (not given)"


def read(track, beats=None, picture=None):
    """The effects section of the Sound Sheet. picture: the video's own edit moments [{"at", "what"}] when the caller
    has them (the video teardown's frame map); an added sound is heard against them, never taken from them."""
    if not track or not Path(track).exists():
        return {"effects": [], "why": "no voices-removed track to listen to"}
    t = timed(track, beats, bank_files())
    events = t.get("events", [])
    p, text = G.prompt("effects-check", HERE)
    text = (text.replace("{moments}", listing(events)).replace("{picture}", picture_lines(picture))
            .replace("{names}", ", ".join(NAMES))
            .replace("{lists}", json.dumps(LISTS)))
    out = {"machine": {"onsets": t.get("onsets"), "candidates": events, "error": t.get("error"),
                       "loop_beats": t.get("loop_beats"), "room": t.get("room")},
           "moments_found": len(events), "prompt": p.name, "picture_moments": len(picture or [])}
    try:
        heard, model, tried = G.ask(track, text)
        heard = G.one(heard)
        out["heard_by"] = model
        if tried:
            out["heard_after"] = [m for m, _ in tried]
    except Exception as e:  # noqa: BLE001
        heard, out["heard_error"] = {}, str(e)[:200]
    out["machine"]["heard"] = heard
    effects = apply(events, heard)
    out["effects"], out["room"] = effects, heard.get("room")
    out["moments_confirmed"] = sum(1 for e in effects if e["found"] != "ear only")
    if t.get("room"):
        out["room_measured"] = t["room"]
    out["unknown_labels"] = [f"job: {e['job']}" for e in effects if e.get("job") and e["job"] not in LISTS["effect_job"]]
    out["unknown_labels"] += [f"name: {e['name']}" for e in effects if str(e.get("name") or "").startswith("other")]
    return out


def render(ef):
    md = ["### EFFECTS", ""]
    fx = ef.get("effects") or []
    if not fx:
        md.append("No added sound effects found." + (f" ({ef.get('why')})" if ef.get("why") else ""))
    else:
        md += ["| Time | Sound | Sure | UCS category | Job | Added in the edit? |", "|---|---|---|---|---|---|"]
        md += [f"| {e['at']}s{'–' + str(e['until']) + 's' if e.get('until') else ''} | {e.get('name') or '—'} | {e.get('sure') or '—'} | {e.get('ucs_category') or '—'} | {e.get('job') or '—'} | "
               f"{'yes' if e.get('added') else 'no — room or product' if e.get('added') is False else '—'} |" for e in fx]
    rm = ef.get("room_measured") or {}
    md += ["", f"- **Room:** {ef.get('room') or '—'}" + (f" · quietest second {rm['at']}–{rm['until']}s at {rm['db']} dB"
                                                         if rm else ""),
           f"- **How found:** {ef.get('moments_found', '—')} moments timed by the tool (sharp hits and soft rises), "
           f"{ef.get('moments_confirmed', '—')} heard as added sounds; moments the tool measured as the same sound "
           f"carry one name"]
    if ef.get("heard_error"):
        md.append(f"- Not heard: {ef['heard_error']} — the list above is the machine's own")
    return "\n".join(md + [""])
