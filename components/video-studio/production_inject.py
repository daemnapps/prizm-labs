#!/usr/bin/env python3
"""Production injection: a written scene put into the capabilities of the source shots it re-makes.

Production runs the writing side's three steps on how a video is made: teardown (frame map, sound sheet) → production
spec (components/video-teardown/machine/production_spec.py: capabilities with slots, brand-free) → THIS. Every slot is
filled with our scene (cast, action, prop, target, place, line, graphic) and the FIXED capabilities (timing, camera,
edit, the shape of each move) are kept; each capability is routed to the tool of ours that makes it, or named as a gap.
The scene's creative dials come from the writing and are carried as they are: the controls target the writing aimed
for and the scene's delivery, emotion and doctrine (take_sheet.py lays them on take.json). A sheet injected before its
take carried the dials it carries now is injected again, so the direction always carries them.

    python3 production_inject.py <scene dir> --spec <teardown run>/production-spec.json [--write] [--model opus]

Writes <scene>/production-sheet.json (+ .md: roles, every slot and what fills it, every route and gap). With --write,
the sheet's beats, staging and line-up go into take.json (the take before is kept as take.before-inject.json), and the
take is then made by the one scene command (take.py scene). No brand, product or person is named here.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

PROMPTS = HERE / "prompts"


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def prompt_file():
    files = sorted(PROMPTS.glob("production-inject-v*-owner.md"), key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return files[-1]


def tools():
    """What our tools can make, by kind, read off the tools themselves so the list never goes stale."""
    m = str(ST.part("motion"))
    if m not in sys.path:
        sys.path.insert(0, m)
    import motion_program as MP
    import take as TK
    src = (Path(MP.__file__).parent / "blocking_blender.py").read_text()
    parts = re.search(r'"reach": "NAME\.([a-z|]+)"', src)
    return {
        "camera": {"tool": "motion chain: the reference's own camera, tracked (motion_chain camera_words)", "can": "any camera the reference shows"},
        "motion": {"tool": "motion chain: the reference's real skeletons when it shows our move; otherwise a 3D rehearsal programmed from our beats on its timing (motion_chain ours)",
                   "can": list(MP.ACTIONS), "reach_parts": (parts.group(1).split("|") if parts else [])},
        "performance": {"tool": "the take (take.py): faces, lines in our cast's voices, body language in words", "faces": list(TK.FACES)},
        "edit": {"tool": "the edit stage (edit_stage.py): the source's cuts, punch-ins and hand-offs on our clock"},
        "sound": {"tool": "the sound board and music bed (sound_board.py, music_bed.py): music, effects, human sounds, room"},
        "on_screen": {"tool": "the product layer (product_layer.py): our product and graphics laid over the take"},
        "set": {"tool": "the 3D set print (image production, 3d-print): our place, printed from the rehearsal's camera"},
        "casting": {"tool": "the casting chain (components/casting): our cast's masters and sheets"},
    }


def copied_shots(sd, take, spec):
    """The source shots this scene re-makes: take.json `motion.copies`, else the shots its motion reference spans."""
    m = take.get("motion") or {}
    ids = m.get("copies") or take.get("copies")
    if ids:
        ids = [ids] if isinstance(ids, str) else list(ids)
        return [s for k in ids for s in spec["shots"] if s["id"] == k]
    ref = _load(Path(sd) / "motion" / "ref.json") or {}
    spans = [(x["from"], x["to"]) for x in ref.get("spans") or []]
    if not spans and m.get("to") is not None:
        spans = [(float(m.get("from") or 0), float(m["to"]))]
    return [s for s in spec["shots"] if any(float(s["from"]) < b - 0.1 and float(s["to"]) > a + 0.1 for a, b in spans)]


def scene_words(take):
    keep = {k: take[k] for k in ("staging", "look", "lineup") if take.get(k)}
    keep["cast"] = {n: (c.get("look") if isinstance(c, dict) else "") for n, c in (take.get("cast") or {}).items()}
    if take.get("subjects"):
        keep["subjects"] = take["subjects"]   # who, the product, the place, the props, as the storyboard defines them
    keep["script"] = [{k: ln[k] for k in ("speaker", "say", "do", "who", "action", "prop", "target", "where", "faces", "moves") if ln.get(k)}
                      for ln in take.get("script") or []]
    if take.get("beats"):
        keep["beats"] = take["beats"]
    # the spoken lines, numbered once: the numbers every row's `line` uses and the check reads
    keep["lines"] = [dict(line=k, **w) for k, w in enumerate(written_lines(take), 1)]
    return keep


DIALS = ("controls", "delivery", "emotion", "doctrine", "style")   # set by the writing; production adds none
NO_DIALS = "(none carried on this scene's take)"


def dials(take):
    """The creative dials the writing set, as the scene's take carries them: the controls target (preset and the level
    of every dial), the scene's delivery, emotion and doctrine. Never one production made up."""
    d = {k: take[k] for k in DIALS if take.get(k)}
    return d or NO_DIALS


def build_prompt(sd, take, spec):
    shots = copied_shots(sd, take, spec)
    if not shots:
        raise SystemExit("no source shot of the production spec matches this scene (take.json motion.copies, or its motion reference)")
    caps = [dict(c, shot=s["id"], at="%s-%s s" % (s["from"], s["to"])) for s in shots for c in s["capabilities"]]
    # only the roles these shots use: a role from another part of the source is not this scene's to fill
    used = " ".join(str(c.get("who") or "") for c in caps).lower()
    casting = [r for r in spec.get("casting") or [] if str(r.get("role") or "").lower() in used] or spec.get("casting") or []
    dl = dials(take)
    text = (prompt_file().read_text()
            .replace("{capabilities}", json.dumps(caps, indent=1, ensure_ascii=False))
            .replace("{casting}", json.dumps(casting, ensure_ascii=False))
            .replace("{scene}", json.dumps(scene_words(take), indent=1, ensure_ascii=False))
            .replace("{dials}", json.dumps(dl, indent=1, ensure_ascii=False) if isinstance(dl, dict) else dl)
            .replace("{tools}", json.dumps(tools(), ensure_ascii=False)))
    return text, shots


def ask(text, model=None):
    m = str(ST.part("motion"))
    if m not in sys.path:
        sys.path.insert(0, m)
    import motion_program as MP
    return MP.ask(text, model or MP.MODEL)


def _norm(t):
    return re.sub(r"[^a-z0-9]+", " ", str(t or "").lower()).strip()


def written_lines(take):
    """Our scene's spoken lines, in order, each with its speaker: what every production row is checked against."""
    return [{"speaker": ln.get("speaker") or "", "say": ln.get("say") or ""} for ln in take.get("script") or [] if (ln.get("say") or "").strip()]


def line_check(take, rows):
    """Every line of our script in exactly one row, in order, word for word, by its own speaker; and no row saying
    words we did not write. Returns the problems, empty when everything lines up."""
    want = written_lines(take)
    said = [r for r in rows if (r.get("say") or "").strip()]
    out, at = [], 0
    for r in said:
        k = r.get("line")
        try:
            k = int(k)
        except (TypeError, ValueError):
            k = None
        if not k or k < 1 or k > len(want):
            out.append('a row says "%s", which is not a line of our script' % r.get("say"))
            continue
        w = want[k - 1]
        if _norm(r["say"]) != _norm(w["say"]):
            out.append('line %d is reworded: written "%s", row says "%s"' % (k, w["say"], r["say"]))
        if (r.get("speaker") or "") != w["speaker"]:
            out.append("line %d belongs to %s, the row gives it to %s" % (k, w["speaker"], r.get("speaker") or "nobody"))
        if k <= at:
            out.append("line %d comes out of order" % k)
        at = max(at, k)
    got = {int(r["line"]) for r in said if str(r.get("line") or "").isdigit()}
    out += ['line %d (%s: "%s") is missing' % (k, w["speaker"], w["say"]) for k, w in enumerate(want, 1) if k not in got]
    return out


def markdown(sheet):
    out = ["# Production sheet", "", "## Roles", ""] + ["- %s → **%s**" % (k, v) for k, v in (sheet.get("roles") or {}).items()]
    out += ["", "## Beats", "", "| capability | s | who | action | prop | target | where | says |", "|---|---|---|---|---|---|---|---|"]
    out += ["| %s | %s–%s | %s | %s | %s | %s | %s | %s |" % (b.get("capability"), b.get("from"), b.get("to"), b.get("who"), b.get("action"),
                                                          b.get("prop", ""), b.get("target", ""), b.get("where", ""), b.get("say", ""))
            for b in sheet.get("script") or []]
    out += ["", "## Slots", "", "| capability | slot | ours | from |", "|---|---|---|---|"]
    out += ["| %s | %s | %s | %s |" % (x.get("capability"), x.get("slot"), x.get("ours"), x.get("filled_from")) for x in sheet.get("slots") or []]
    out += ["", "## Routes", "", "| capability | kind | tool | gap |", "|---|---|---|---|"]
    out += ["| %s | %s | %s | %s |" % (x.get("capability"), x.get("kind"), x.get("tool"), x.get("gap", "")) for x in sheet.get("routes") or []]
    return "\n".join(out) + "\n"


def inject(scene_dir, spec_file, write=False, model=None, asker=None):
    sd = Path(scene_dir)
    take = _load(sd / "take.json")
    if take is None:
        raise SystemExit("this scene has no take.json (%s)" % sd)
    spec = _load(spec_file)
    if not spec:
        raise SystemExit("no production spec at %s: run components/video-teardown/machine/production_spec.py on the source first" % spec_file)
    text, shots = build_prompt(sd, take, spec)
    (sd / "production-inject.sent.json").write_text(json.dumps({"prompt_file": prompt_file().name, "spec": str(spec_file), "prompt": text}, indent=1, ensure_ascii=False))
    answer, usage = (asker or ask)(text, model)
    (sd / "production-inject.answer.json").write_text(str(answer))
    m = re.search(r"\{.*\}", str(answer), re.S)
    try:
        sheet = json.loads(m.group(0) if m else answer)
    except ValueError:
        raise SystemExit("the injection came back with no JSON: " + str(answer)[:300])
    sheet["line_check"] = line_check(take, sheet.get("script") or [])
    cast = set((take.get("cast") or {}).keys())
    sheet["gaps"] = [r for r in sheet.get("routes") or [] if str(r.get("tool", "")).upper().startswith(("GAP", "PARTLY"))]
    sheet["not_cast"] = sorted({b.get("who") for b in sheet.get("script") or [] if cast and b.get("who") not in cast})
    sheet.update({"shots": [s["id"] for s in shots], "spec": str(spec_file), "by": usage, "dials": dials(take)})
    (sd / "production-sheet.json").write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    (sd / "production-sheet.md").write_text(markdown(sheet))
    if write and sheet["line_check"]:
        # rows that do not line up with our script never reach the take's prompt: the sheet is kept for the board, the
        # take stays as written
        write = False
        sheet["not_written"] = "the take was not written: its rows do not line up with our script"
        (sd / "production-sheet.json").write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    if write:
        (sd / "take.before-inject.json").write_text(json.dumps(take, indent=1, ensure_ascii=False))
        script = []
        for b in sheet.get("script") or []:
            ln = {k: b[k] for k in ("who", "action", "prop", "target", "where", "say", "faces", "moves") if b.get(k)}
            ln["say"] = b.get("say") or ""
            ln["speaker"] = b.get("speaker") or b.get("who") or ""      # who says the line, apart from whose body leads
            script.append(ln)
        take.update({"script": script, "staging": sheet.get("staging") or take.get("staging"), "production_sheet": str(sd / "production-sheet.json")})
        if sheet.get("lineup"):
            take["lineup"] = sheet["lineup"]
        shots = ((sheet.get("direction") or {}).get("camera") or {}).get("shots") or []
        if shots:                                   # our own camera direction, said shot by shot in the take
            end = max([float(b.get("to") or 0) for b in (sheet["direction"].get("beats") or [])] + [float(take.get("seconds") or 0)])
            take["camera"] = {"directed": True, "shots": [
                {"seconds": round((float(shots[k + 1]["from"]) if k + 1 < len(shots) else end) - float(x.get("from") or 0), 2),
                 "words": x.get("words") or ""} for k, x in enumerate(shots)]}
        (sd / "take.json").write_text(json.dumps(take, indent=1, ensure_ascii=False))
    if write and sheet.get("direction"):
        m = str(ST.part("motion"))
        if m not in sys.path:
            sys.path.insert(0, m)
        import motion_chain as MC                   # our direction rendered as the rehearsal the take moves to
        MC.direct(sd, sheet["direction"], take.get("seconds"))
    return sheet


def run_of(sd, take):
    """The teardown run of the source this scene re-makes: the folder of its motion reference's source video, when that
    folder holds a frame map."""
    srcs = [(take.get("motion") or {}).get("source"), (_load(Path(sd) / "motion" / "ref.json") or {}).get("source")]
    for s in srcs:
        if s and (Path(s).parent / "framemap" / "framemap.json").exists():
            return Path(s).parent
    return None


def ensure(scene_dir, model=None):
    """Production's first step for a scene, with nobody asked: the source's production spec (made once per source),
    then our scene injected into it, unless take.json already carries its sheet. Returns the sheet's path, or None when
    the scene re-makes no torn-down source."""
    sd = Path(scene_dir)
    take = _load(sd / "take.json") or {}
    if take.get("production_sheet") and Path(take["production_sheet"]).exists():
        made = _load(take["production_sheet"]) or {}
        if made.get("dials", NO_DIALS) == dials(take):
            return Path(take["production_sheet"])
        # the take now carries dials its sheet was directed without (or other ones): directed again with them
    run = run_of(sd, take)
    if run is None:
        return None
    spec = run / "production-spec.json"
    if not spec.exists():
        sys.path.insert(0, str(HERE.parent / "video-teardown" / "machine"))
        import production_spec as PS
        PS.run_spec(run, model)
    inject(sd, spec, write=True, model=model)
    return sd / "production-sheet.json"


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or "--spec" not in a:
        sys.exit(__doc__)
    sh = inject(a[0], a[a.index("--spec") + 1], "--write" in a, a[a.index("--model") + 1] if "--model" in a else None)
    for x in sh.get("line_check") or []:
        print("LINE: " + x)
    print("%d beats, %d slots, %d routes, %d gaps%s" % (len(sh.get("script") or []), len(sh.get("slots") or []), len(sh.get("routes") or []),
                                                        len(sh["gaps"]), (", not in the cast: " + ", ".join(sh["not_cast"])) if sh["not_cast"] else ""))
