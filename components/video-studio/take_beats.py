"""THE TAKE'S BEAT DOOR (2026-11-15): a made take shows every beat we wrote, or it is not used.

Why: takes came back with the right faces doing another moment (the reference's own action in place of the beat
we wrote), people missing from a line-up, people joining it. The face door (take_faces.py) only asks whether each face
is its sheet. This door asks whether the clip SHOWS each beat: who does it, the action, the prop, the target, where,
and the people on screen as written (who is there, nobody extra, the order of a line-up).

  fields   before anything is bought: every beat carries who and action as fields of their own (`gaps`). A beat
           written as one prose sentence (`do`) is listed as a gap to split; a beat with fields but no who or no
           action stops the take (take.py one).
  take     after the take is made: the clip and our beats go to the video reader (components/motion read.py `ask`,
           the same door the motion read and the watcher use), prompts/take-beats.md. One row per beat: seen or not,
           with what the clip shows instead; plus the cast on screen and the line-up. Any beat not seen, or a cast or
           line-up miss, is a fail: the take is kept beside as <out>.beats-miss.mp4, never placed at `out`, and the run
           stops with the reason. The record is <out>.beats.json.

SWITCH: take-beats.json beside this file (`on`, parts `fields`, `take`), or TAKE_BEATS_OFF=1 / =<part> on one machine.
Row TAKE-BEATS in team/rollbacks.md.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CONF = HERE / "take-beats.json"
PROMPT = HERE / "prompts" / "take-beats.md"
NOBODY = ("HANDS", "NOBODY", "PRODUCT", "")


def _conf():
    try:
        return json.loads(CONF.read_text())
    except (OSError, ValueError):
        return {}


def on(part):
    off = os.environ.get("TAKE_BEATS_OFF", "")
    if off in ("1", "true", "all") or off == part:
        return False
    c = _conf()
    return bool(c.get("on", True)) and bool(c.get(part, True))


def _mc():
    import settings as ST
    p = str(ST.part("motion"))
    if p not in sys.path:
        sys.path.insert(0, p)
    import motion_chain as MC
    return MC


def beats_of(take):
    """The take's beats, in order: its script lines when they say what the bodies do, else the brief's discrete beats
    seeded beside the script (seed_from_brief: `beats`)."""
    script = take.get("script") or []
    if any(ln.get("action") or ln.get("do") for ln in script):
        return [ln for ln in script if ln.get("action") or ln.get("do") or ln.get("say")]
    return [b for b in take.get("beats") or [] if isinstance(b, dict) and (b.get("action") or b.get("do"))]


def gaps(take):
    """Beats that are not discrete enough to make: {"beat", "stop", "why"}. `stop` True refuses a paid take."""
    cast = set((take.get("cast") or {}).keys())
    out = []
    for k, b in enumerate(beats_of(take), 1):
        if not b.get("action"):
            if b.get("do"):
                out.append({"beat": k, "stop": False, "why": "written as one sentence (`do`): split it into who, action, prop, "
                                                              "target and where"})
            elif not b.get("say"):
                out.append({"beat": k, "stop": True, "why": "no action"})
            continue
        who = str(b.get("who") or "")
        if not who:
            out.append({"beat": k, "stop": True, "why": "no who: name the cast member who does it"})
        elif cast and who.upper() not in NOBODY and who not in cast:
            out.append({"beat": k, "stop": True, "why": "%s does it but is not in the cast" % who})
        tgt = re.split(r"[^A-Za-z0-9_-]", str(b.get("target") or "").strip() + " ")[0]
        if tgt.isupper() and len(tgt) > 1 and cast and tgt not in cast:
            out.append({"beat": k, "stop": True, "why": "the target %s is not in the cast" % tgt})
    return out


def lineup(take):
    """The people who must be on screen, in their order when the take fixes one (`lineup`: names in order; else the
    cast). Read by the check."""
    return list(take.get("lineup") or (take.get("cast") or {}).keys())


def ask_words(take):
    """The prompt the reader gets: our beats as fields, the cast and the line-up."""
    MC = _mc()
    cast = {n: (c.get("look") if isinstance(c, dict) else "") for n, c in (take.get("cast") or {}).items()}
    rows = []
    for k, b in enumerate(beats_of(take), 1):
        f = {x: b[x] for x in ("who", "action", "prop", "target", "where") if b.get(x)}
        rows.append({"beat": k, "in_words": MC.beat_action(b), **f, **({"says": b["say"]} if b.get("say") else {})})
    return PROMPT.read_text().replace("{beats}", json.dumps(rows, indent=1, ensure_ascii=False)).replace(
        "{cast}", json.dumps(cast, indent=1, ensure_ascii=False)).replace(
        "{lineup}", json.dumps({"order": lineup(take), "fixed": bool(take.get("lineup"))}, ensure_ascii=False)).replace(
        "{staging}", str(take.get("staging") or ""))


def read(take, clip, ask=None):
    """The clip read against our beats. Returns {"pass", "beats": [...], "cast", "lineup", "model"} and writes
    <clip>.beats.json (with the prompt as sent)."""
    if ask is None:
        MC = _mc()
        sys.path.insert(0, str(Path(MC.__file__).parent))
        import read as RD
        ask = RD.ask
    text = ask_words(take)
    answer, meta = ask(text, clip)
    try:
        got = json.loads(answer)
    except ValueError:
        raise SystemExit("the beat reader answered with no JSON: " + str(answer)[:300])
    want = len(beats_of(take))
    rows = got.get("beats") or []
    seen = {int(r.get("beat") or 0): r for r in rows}
    beats = [dict(seen.get(k) or {"beat": k, "seen": False, "shows": "not read"}, beat=k) for k in range(1, want + 1)]
    cast = got.get("cast") or {"ok": None}
    line = got.get("lineup") or {"ok": None}
    misses = [b for b in beats if b.get("seen") is not True]
    ok = not misses and cast.get("ok") is not False and line.get("ok") is not False
    res = {"clip": str(clip), "pass": ok, "beats": beats, "cast": cast, "lineup": line,
           "why": "" if ok else "; ".join(
               ["beat %d not shown (%s)" % (b["beat"], b.get("shows") or "no reason given") for b in misses] +
               (["cast: " + str(cast.get("why"))] if cast.get("ok") is False else []) +
               (["line-up: " + str(line.get("why"))] if line.get("ok") is False else [])),
           "model": (meta or {}).get("model"), "account": (meta or {}).get("account"), "prompt": text}
    Path(str(clip) + ".beats.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


def hold_misses(take, out, ask=None):
    """After the take is made: read it; a take that does not show our beats moves to <out>.beats-miss.mp4 and stops
    the run (SystemExit) with the reason."""
    if not on("take") or not beats_of(take):
        return None
    res = read(take, out, ask=ask)
    if not res["pass"]:
        miss = Path(out).with_suffix(".beats-miss.mp4")
        Path(out).rename(miss)
        raise SystemExit("the take does not show what we wrote: %s; kept as %s, not used" % (res["why"], miss.name))
    return res
