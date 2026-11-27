#!/usr/bin/env python3
"""Production spec (stage 2p): how a torn-down source is MADE, abstracted into capabilities, brand-free.

The writing side reads a swipe in three steps: teardown (the record) → replication spec (elements, abstracted) →
injection (our brand in the slots). Production runs the same three on how the video is made:

    teardown    the frame map (stage 1f: every shot's people, frames, camera, moments, text, sound, hand-off) and the
                sound sheet (audio teardown), already made by the teardown
    spec        THIS: every shot's capabilities (camera, motion, performance, edit, sound, on_screen, set, casting),
                each with a generic mandate, the source instance and the slot our scene fills (prompts/stage-2p-production)
    injection   components/video-studio/production_inject.py: a written scene's beats, cast, props, place and dials
                into those slots, each capability routed to the tool that makes it

    python3 production_spec.py <teardown run dir> [--model opus] [--print]     writes <run>/production-spec.json + .md

The model is asked through the motion component's one text door (motion_program.ask: every Claude account here,
then Gemini on each key). The prompt as sent and the answer are kept beside the spec. No brand, product or person is
named here.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parents[1]
PROMPTS = HERE.parent / "prompts" / "stage-2p-production"
SLOTS = ("OUR_ACTION", "OUR_PROP", "OUR_TARGET", "OUR_CAST", "OUR_PLACE", "OUR_LINE", "OUR_GRAPHIC", "FIXED")
KINDS = ("camera", "motion", "performance", "edit", "sound", "on_screen", "set", "casting")


def prompt_file():
    """The newest prompt in the stage's folder (-vN-)."""
    files = sorted(PROMPTS.glob("stage2p-production-v*-owner.md"), key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not files:
        raise SystemExit("no production spec prompt in %s" % PROMPTS)
    return files[-1]


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def framemap_words(run):
    """The frame map, shot by shot, as the spec reads it: the map of each shot, without stills or file names."""
    fm = _load(Path(run) / "framemap" / "framemap.json") or {}
    shots = []
    for s in fm.get("shots") or []:
        m = s.get("map") or {}
        shots.append({"id": s.get("id"), "from": s.get("start"), "to": s.get("end"),
                      **{k: m[k] for k in ("who", "start_frame", "end_frame", "camera", "moments", "on_screen", "sound", "edit") if m.get(k)}})
    if not shots:
        raise SystemExit("this run has no frame map yet (%s): run the teardown's frame map (stage 1f) first" % (Path(run) / "framemap"))
    return shots


def skeleton_words(run):
    """Sections 1 and 2 of the writing side's replication spec (format, structural skeleton), when the run has one."""
    f = Path(run) / "stages" / "2-spec.md"
    if not f.exists():
        return "(none written for this source)"
    text = f.read_text()
    end = text.find("**3.")
    return text[:end if end > 0 else 3000].strip()


def sound_words(run):
    s = _load(Path(run) / "sound-sheet.json")
    if s is None:
        return "(no sound sheet)"
    keep = {k: s[k] for k in ("music", "effects", "human_sounds", "room", "voices", "breaks") if k in s}
    return json.dumps(keep or s, ensure_ascii=False)[:12000]


def build_prompt(run):
    run = Path(run)
    rec = _load(run / "run.json") or {}
    return (prompt_file().read_text()
            .replace("{framemap}", json.dumps(framemap_words(run), indent=1, ensure_ascii=False))
            .replace("{sound_sheet}", sound_words(run))
            .replace("{skeleton}", skeleton_words(run))
            .replace("{layers}", json.dumps({k: v for k, v in (rec.get("layers") or {}).items() if k != "_why"},
                                            ensure_ascii=False)))   # the reasons are the writing's, not this prompt's


def clean(got, shot_ids):
    """The answer held to its shape: known shots, known kinds and slots, ids as <shot>.<C>. What was dropped is said."""
    dropped, shots = [], []
    for s in got.get("shots") or []:
        if s.get("id") not in shot_ids:
            dropped.append({"shot": s.get("id"), "why": "not a shot of the frame map"})
            continue
        caps = []
        for c in s.get("capabilities") or []:
            slot = str(c.get("slot") or "").upper()
            if c.get("kind") not in KINDS or slot not in SLOTS or not c.get("mandate"):
                dropped.append({"shot": s["id"], "capability": c.get("id"), "why": "kind, slot or mandate missing or unknown"})
                continue
            caps.append(dict(c, slot=slot, ref="%s.%s" % (s["id"], c.get("id"))))
        shots.append(dict(s, capabilities=caps))
    return dict(got, shots=shots, dropped=dropped)


def markdown(spec):
    out = ["# Production spec", "", "**Format:** " + str(spec.get("format") or ""), "", "## Casting", ""]
    out += ["- **%s** ×%s — %s; reads as %s" % (c.get("role"), c.get("count", 1), c.get("function"), c.get("reads_as")) for c in spec.get("casting") or []]
    for s in spec.get("shots") or []:
        out += ["", "## %s · %s · %s–%s s" % (s.get("id"), s.get("phase"), s.get("from"), s.get("to")), "",
                "| # | kind | capability | mandate | slot | source |", "|---|---|---|---|---|---|"]
        out += ["| %s | %s | %s | %s | %s | %s |" % (c["id"], c["kind"], c.get("capability"), c["mandate"], c["slot"], c.get("source_instance", ""))
                for c in s["capabilities"]]
    out += ["", "## Load-bearing", ""] + ["- %s — %s" % (x.get("id"), x.get("why")) for x in spec.get("load_bearing") or []]
    out += ["", "## Swappable", ""] + ["- " + str(x) for x in spec.get("swappable") or []]
    return "\n".join(out) + "\n"


def ask(text, model=None):
    sys.path.insert(0, str(COMPONENTS / "motion"))
    import motion_program as MP
    return MP.ask(text, model or MP.MODEL)


def run_spec(run, model=None, asker=None):
    run = Path(run)
    text = build_prompt(run)
    (run / "production-spec.sent.json").write_text(json.dumps({"prompt_file": prompt_file().name, "prompt": text}, indent=1, ensure_ascii=False))
    answer, usage = (asker or ask)(text, model)
    (run / "production-spec.answer.json").write_text(str(answer))
    m = re.search(r"\{.*\}", str(answer), re.S)
    try:
        got = json.loads(m.group(0) if m else answer)
    except ValueError:
        raise SystemExit("the production spec came back with no JSON: " + str(answer)[:300])
    spec = clean(got, {s["id"] for s in framemap_words(run)})
    spec.update({"prompt": prompt_file().name, "by": usage})
    (run / "production-spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    (run / "production-spec.md").write_text(markdown(spec))
    return spec


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if "--print" in a:
        print(build_prompt(a[0]))
        sys.exit(0)
    sp = run_spec(a[0], a[a.index("--model") + 1] if "--model" in a else None)
    print("%d shots, %d capabilities, %d load-bearing, %d dropped" % (
        len(sp["shots"]), sum(len(s["capabilities"]) for s in sp["shots"]), len(sp.get("load_bearing") or []), len(sp["dropped"])))
