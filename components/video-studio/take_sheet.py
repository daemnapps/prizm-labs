#!/usr/bin/env python3
"""The take sheet: a production scene's continuous take written out as take.py's take.json, by the chain.

Production sets a scene the swipe holds as one take up as a `gen.take` step (seed_from_brief.py): its lines, beats,
subjects and the swipe shots it re-makes. The scene chain (take.py scene: inject -> motion -> start picture from the
set print -> input review -> take -> checks) reads the scene's take.json. Before this file nothing wrote that sheet for
a fresh production, so a scene went from its step straight to a paid print with no direction, rehearsal or start
picture (owner, 16 Nov 2026: "we need to have everything on chain work"). This writes it, from the chain's own records:

  - lines, beats, subjects, staging   the gen.take step as production seeded it
  - brand, framemap, motion           the writing run's swipe (source.mp4) and frame map: the window the copied
                                      shots span, so the motion chain reads the swipe's seconds (our beats, its timing)
  - cast, set, set_print, product     the ad's style (style_chain.scene_refs): each person's sheet in the ad's style
                                      for the look the scene names, the scene's set and its kept 3D print
  - look                              the style's words
  - controls, delivery, emotion,      the creative dials the writing already set: the levels it aimed for (the
    doctrine                          controls target its own brief prompt carried) and the scene's delivery, emotion
                                      and doctrine from the production brief; production adds no dial of its own

    python3 take_sheet.py <production, e.g. idea-12> [scene ...] [--force] [--print] [--dials]

Never overwrites a take.json that exists unless --force (the one it replaces is kept as take.before-sheet.json).
--dials lays only the writing's dials onto take.json files that exist, leaving everything else on them as it is.
Spends nothing. No brand, product or person is named here.
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

NOBODY = {"", "NOBODY", "NONE", "NO ONE", "NOONE"}
SCENE_DIALS = ("delivery", "emotion", "doctrine")     # the production brief's per-scene dials, carried as they are
# the writing's prompts that carry the video controls target, latest stage first: the brief's own prompt is the one the
# scenes were written to (video-writing writing_v2.controls_target -> creative_controls.target_md)
TARGET_PROMPTS = ("5-brief.md", "4g-spice.md", "4ab-reading-hooks.md", "3-injection.md")
TARGET = re.compile(r"Preset: [^\n(]*\((?P<id>[a-z0-9_-]+)\)[^\n]*\n\s*\n(?P<rows>(?:- [a-z_]+: -?\d[^\n]*(?:\n|$))+)")
ROW = re.compile(r"^- ([a-z_]+): (-?\d[^\n]*?)\s*$", re.M)


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {} if default is None else default


def _style_chain():
    import importlib.util
    f = ST.part("video-production") / "styles" / "style_chain.py"
    sp = importlib.util.spec_from_file_location("take_sheet_style_chain", f)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def parse_target(text):
    """The last controls-target block in a prompt (creative_controls.target_md): {preset, levels: {dial: "4 (surreal)"}},
    or None when the text carries none."""
    m = None
    for m in TARGET.finditer(text or ""):
        pass
    if not m:
        return None
    return {"preset": m["id"], "levels": {k: v for k, v in ROW.findall(m["rows"])}}


def controls_target(rdir, brand=None):
    """The dial levels the writing aimed for: read off the writing run's own prompt, exactly as it was sent; when no
    prompt of the run carried them, the creative controls' target for video (the writing's preset, the brand's saved
    levels, the floor), worked out the same way the writing does. None when neither can be read."""
    for name in TARGET_PROMPTS:
        try:
            got = parse_target((Path(rdir) / "prompts" / name).read_text())
        except OSError:
            continue
        if got:
            return dict(got, came_from="the writing's %s prompt" % name.rsplit(".", 1)[0])
    try:
        import importlib.util
        f = ST.part("creative-controls") / "creative_controls.py"
        sp = importlib.util.spec_from_file_location("take_sheet_creative_controls", f)
        cc = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(cc)
        # the preset the writing run was written to, when the run records one (`controls_preset.preset`, written by
        # the writing machine once it picks the preset by awareness); else, or when that preset cannot be worked out
        # here, the preset every run was written to before: maxed (2026-11-18)
        preset = "maxed"
        try:
            preset = ((json.loads((Path(rdir) / "run.json").read_text()).get("controls_preset") or {}).get("preset")) or "maxed"
        except (OSError, ValueError, AttributeError):
            pass
        try:
            got = parse_target(cc.target_md(preset, brand, "video"))
        except Exception:  # noqa: BLE001 -- a preset this checkout's controls do not know: the earlier default
            got = None
        if not got and preset != "maxed":
            got = parse_target(cc.target_md("maxed", brand, "video"))
    except Exception:  # noqa: BLE001 -- no controls here: the sheet carries no target rather than an invented one
        got = None
    return dict(got, came_from="creative controls target for video (no writing prompt carried one)") if got else None


def brief_scene(run, s):
    """The production brief's scene as production folds it (seed_from_brief), for the dials a step was seeded without."""
    try:
        import seed_from_brief as SB
        doc = SB.with_edits(SB.brief_json(run), {})
    except Exception:  # noqa: BLE001 -- no brief to read: the step's own fields are all there is
        return {}
    return next((x for x in doc.get("scenes") or [] if x.get("id") == s), {})


def writing_dials(bd, s, params=None):
    """The creative dials the writing already set for one scene of a production: `controls` (the target the writing
    aimed for), then the scene's `delivery`, `emotion` and `doctrine`. The gen.take step carries them when production
    seeded it with them; otherwise they are read from the writing run. Nothing is added that the writing did not set."""
    bd = Path(bd)
    brief = _load(bd / "brief.json")
    run = brief.get("brief") or brief.get("run")
    p = params
    if p is None:
        wf = _load(bd / "scenes" / s / (((brief.get("picks") or {}).get(s) or "take-1") + ".json"))
        p = next((x.get("params") or {} for x in wf.get("steps") or [] if x.get("tool") == "gen.take"), {})
    out = {k: p[k] for k in ("controls",) + SCENE_DIALS if p.get(k)}
    if run and any(k not in out for k in SCENE_DIALS):
        sc = brief_scene(run, s)
        out.update({k: sc[k] for k in SCENE_DIALS if sc.get(k) and k not in out})
    if run and "controls" not in out:
        brand = brief.get("brand") or _load(Path(ST.WRITING) / str(run) / "run.json").get("brand")
        got = controls_target(Path(ST.WRITING) / str(run), brand)
        if got:
            out["controls"] = got
    return {k: out[k] for k in ("controls",) + SCENE_DIALS if k in out}


def k_ids(copies):
    """'K05-K10', ['K53, K55-K60', 'K61'] -> ['K05', ..., 'K10', 'K53', 'K55', ...] in order, each once."""
    out = []
    for part in ([copies] if isinstance(copies, str) else copies or []):
        for piece in re.split(r"[,\s]+", str(part)):
            m = re.fullmatch(r"K(\d+)(?:-K?(\d+))?", piece.strip(), re.I)
            if not m:
                continue
            a, b = int(m[1]), int(m[2] or m[1])
            w = len(m[1])
            for i in range(a, b + 1):
                k = "K%0*d" % (w, i)
                if k not in out:
                    out.append(k)
    return out


def window(framemap, ks):
    """The seconds the copied swipe shots span in the frame map: (from, to), or None when none of them is mapped."""
    shots = {s.get("id"): s for s in (_load(framemap).get("shots") or [])}
    got = [shots[k] for k in ks if k in shots]
    if not got:
        return None
    return round(min(float(s["start"]) for s in got), 3), round(max(float(s["end"]) for s in got), 3)


def people(words, cast_names):
    """The cast a who / speaker field names ("creator's hands", "HUSBAND and creator" -> creator, HUSBAND), in order."""
    w = str(words or "").upper()
    if w.strip() in NOBODY:
        return []
    found = sorted(((w.find(n.upper()), n) for n in cast_names if n and n.upper() in w), key=lambda x: x[0])
    if found:
        return [n for _, n in found]
    return [w.strip()] if re.fullmatch(r"[A-Z][A-Z .'-]*", w.strip()) else []


WORDS_A_SECOND = 2.7      # a line with no read runs at motion_program's own pace


def _read_seconds(bd, wf):
    """The scene's narration read length in seconds (its voice.read step's file), or None before it is read."""
    import subprocess
    st = next((x for x in wf.get("steps") or [] if x.get("tool") == "voice.read"), None)
    f = Path(bd) / str(((st or {}).get("inputs") or {}).get("file") or "")
    if not st or not f.is_file():
        return None
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def shots_params(bd, s, wf, run):
    """A scene set up as AI shots (gen.shot steps, one per brief shot) read as one take with cuts inside, in the
    gen.take step's shape: each shot's lines in order, the brief's beats, and the brief's camera per shot (angle and
    camera_move) as the directed camera, timed on the scene's read (else its words). None when the scene has no
    gen.shot step. The take is made in one call with a cut per shot (take.py camera `shots`)."""
    shots = [x for x in wf.get("steps") or [] if x.get("tool") == "gen.shot"]
    if not shots:
        return None
    sc = brief_scene(run, s) if run else {}
    by_id = {x.get("id"): x for x in sc.get("shots") or []}
    voice = next((x for x in wf.get("steps") or [] if x.get("tool") in ("voice.read", "voice.ai")), {})
    spk = (voice.get("params") or {}).get("speaker")
    script, rows = [], []
    for st in shots:
        p = st.get("params") or {}
        bs = by_id.get(st.get("note")) or {}
        lines = [ln for ln in p.get("lines") or bs.get("lines") or [] if (ln.get("say") or "").strip()]
        for ln in lines:
            script.append({k: v for k, v in (("speaker", p.get("speaker") or spk), ("say", ln["say"].strip()),
                                              ("lips", p.get("lips"))) if v})
        words = sum(len(ln["say"].split()) for ln in lines)
        cam = ", ".join(str(x).strip().rstrip(".") for x in (bs.get("angle"), bs.get("camera_move")) if x)
        rows.append({"shot": st.get("note") or st.get("id"), "step": st.get("id"), "words": max(words, 1),
                     "camera": cam or "as in the motion reference", "face": bs.get("face") or ""})
    total = _read_seconds(bd, wf) or sum(r["words"] for r in rows) / WORDS_A_SECOND
    total = max(2.0 * len(rows), total)
    cam_shots = [{"shot": r["shot"], "seconds": round(total * r["words"] / sum(x["words"] for x in rows), 2),
                  "words": r["camera"] + ("; face: " + r["face"] if r["face"] else "")} for r in rows]
    beats = [{"shot": b.get("shot"), "who": b.get("who") or sc.get("who") or spk or "", "action": b.get("action") or b.get("do") or "",
              "prop": b.get("prop") or "", "target": b.get("target") or "",
              "where": b.get("where") or b.get("setting_id") or sc.get("setting_id") or "",
              "camera": b.get("camera") if b.get("camera") not in (None, "", "held") else "", "over": b.get("over") or ""}
             for b in sc.get("beats") or []]
    if not beats:
        beats = [{"shot": r["shot"], "who": spk or "", "action": (by_id.get(r["shot"]) or {}).get("action") or sc.get("happens") or "",
                  "face": r["face"]} for r in rows]
    out = {"script": script, "beats": beats, "staging": sc.get("happens") or "", "subjects": wf.get("subjects") or {},
           "camera": {"directed": True, "shots": cam_shots, "from": "the brief's shots: angle and camera_move"},
           "seconds": int(math.ceil(total)), "motion": {"copies": [p for st in shots for p in [((st.get("params") or {}).get("copies"))] if p]},
           "shot_steps": [r["step"] for r in rows]}
    out.update({k: sc[k] for k in ("delivery", "emotion") if sc.get(k)})
    if isinstance(sc.get("doctrine"), dict):
        out["doctrine"] = sc["doctrine"]
    return out


def sheet_for(bd, s, cast_names=None):
    """The take sheet for one scene of a production folder, from its picked take's gen.take step, or, for a scene of
    AI shots, its gen.shot steps read as one take with a cut per shot (shots_params). None when the scene has neither."""
    bd = Path(bd)
    brief = _load(bd / "brief.json")
    take_name = (brief.get("picks") or {}).get(s, "take-1")
    wf = _load(bd / "scenes" / s / (take_name + ".json"))
    st = next((x for x in wf.get("steps") or [] if x.get("tool") == "gen.take"), None)
    run = brief.get("brief") or brief.get("run")
    if st:
        p, made_from = st.get("params") or {}, "gen.take"
    else:
        p = shots_params(bd, s, wf, run)
        if p is None:
            return None
        made_from = "gen.shot x %d" % len(p["shot_steps"])
    rdir = Path(ST.WRITING) / str(run)
    rj = _load(rdir / "run.json")
    brand = brief.get("brand") or (brief.get("shot_fill") or {}).get("brand") or rj.get("brand")
    sd = bd / "scenes" / s
    if cast_names is None:
        try:
            cast_names = [c["name"] for c in _style_chain().writing_cast(run, Path(ST.WRITING)) if c.get("name")]
        except Exception:  # noqa: BLE001 -- no style chain here: names come from the step itself
            cast_names = []
    beats = [dict(b) for b in p.get("beats") or []]
    script = []
    for ln in p.get("script") or []:
        row = {k: ln[k] for k in ("speaker", "say", "lips", "mouthed_by") if ln.get(k) is not None}
        do = [b.get("action") for b in beats if b.get("action") and b.get("over") and b["over"].strip()[:30] in (ln.get("say") or "")]
        if do:
            row["do"] = "; ".join(do)
        script.append(row)
    names = []
    for x in [ln.get("speaker") for ln in script] + [b.get("who") for b in beats]:
        for n in people(x, cast_names):
            if n not in names:
                names.append(n)
    take = {"scene": s, "brand": brand, "staging": p.get("staging") or "", "script": script, "beats": beats,
            "subjects": p.get("subjects") or {}, "camera": p.get("camera") or {},
            "cast": {n: {} for n in names}, "out": str(sd / "take.mp4"),
            "written_by": "take_sheet.py from %s.json (%s)" % (take_name, made_from)}
    if p.get("shot_steps"):                  # the AI shots this one take makes (laid back by ai_shots.lay)
        take["shot_steps"] = p["shot_steps"]
    if p.get("seconds"):
        take["seconds"] = p["seconds"]
    take.update(writing_dials(bd, s, p))     # the writing's dials, carried as set; production adds none
    fm = rdir / "framemap" / "framemap.json"
    src = rdir / "source.mp4"
    copies = (p.get("motion") or {}).get("copies")
    ks = k_ids(copies)
    span = window(fm, ks) if fm.exists() and ks else None
    if fm.exists():
        take["framemap"] = str(fm)
    if span and src.exists():
        take["motion"] = {"source": str(src), "from": span[0], "to": span[1], "copies": ks}
    elif ks:
        take["motion"] = {"copies": ks}
    try:                                    # the ad's style: cast sheets, set and its kept print, product, look words
        SC = _style_chain()
        tmp = sd / "take.json"
        had = tmp.read_text() if tmp.exists() else None
        tmp.write_text(json.dumps(take, indent=1, ensure_ascii=False))   # scene_refs reads the cast names from it
        try:
            r = SC.scene_refs(bd.name, s, briefs=bd.parent, writing=Path(ST.WRITING))
        finally:
            if had is None:
                tmp.unlink()
            else:
                tmp.write_text(had)
        for person in r.get("people") or []:
            take["cast"][person["name"]] = {"sheet": person["path"], "element": person.get("element"),
                                            "look": "%s, %s style" % (person["name"].title(), r.get("style"))}
        if r.get("set"):
            take["set"] = r["set"].get("name")
        if r.get("set_print"):
            take["set_print"] = r["set_print"]
        if r.get("product"):
            take["product"] = r["product"]
        if r.get("formula"):
            take["look"] = r["formula"]
        if r.get("missing"):
            take["missing"] = r["missing"]
    except Exception as e:  # noqa: BLE001 -- said on the sheet: the chain holds a take whose picture cannot be made
        take["missing"] = ["style refs not read: %s" % str(e)[:200]]
    return take


def write(bd, s, force=False):
    """Write <scene>/take.json from the scene's gen.take step. Returns its path, or None (not a take / already there)."""
    sd = Path(bd) / "scenes" / s
    out = sd / "take.json"
    if out.exists() and not force:
        return None
    take = sheet_for(bd, s)
    if take is None:
        return None
    if out.exists():
        out.replace(sd / "take.before-sheet.json")
    out.write_text(json.dumps(take, indent=1, ensure_ascii=False))
    return out


def carry(bd, s):
    """Lay the writing's dials onto a scene's take.json that exists, changing nothing else on it. Returns the dials
    when they changed the sheet, else None (no sheet, or it already carries them)."""
    f = Path(bd) / "scenes" / s / "take.json"
    take = _load(f) if f.exists() else None
    if not take or not isinstance(take, dict):      # no sheet, or one that cannot be read: left exactly as it is
        return None
    got = writing_dials(bd, s)
    if not got or all(take.get(k) == v for k, v in got.items()):
        return None
    take.update(got)
    f.write_text(json.dumps(take, indent=1, ensure_ascii=False))
    return got


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    bd = Path(argv[0]) if Path(argv[0]).is_dir() else ST.BRIEFS / argv[0]
    scenes = [a for a in argv[1:] if not a.startswith("--")] or (_load(bd / "brief.json").get("order") or [])
    for s in scenes:
        if "--dials" in argv:
            got = carry(bd, s)
            print("%s  %s" % (s, ("dials laid on: " + ", ".join(got)) if got else "unchanged (no sheet, or it carries them)"))
            continue
        if "--print" in argv:
            print(json.dumps({s: sheet_for(bd, s)}, indent=1, ensure_ascii=False))
            continue
        f = write(bd, s, force="--force" in argv)
        print("%s  %s" % (s, f or "skipped (not one take, or take.json already there)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
