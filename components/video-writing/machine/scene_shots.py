#!/usr/bin/env python3
"""Scenes are sequences: one moment is one scene, its shots in order (components/video-production/BRIEF-SPEC.md,
"Scenes and shots", 2026-11-08). One generation carries as many shots as fit (2026-11-12): consecutive scenes that
share a section, or continue in the same place, join into one scene while the whole stays within GENERATION_SECONDS;
a 3D cut-away and every card, insert or screen stay their own scenes.

    python3 components/video-writing/machine/scene_shots.py check <5-brief.md | brief.json>
    python3 components/video-writing/machine/scene_shots.py fold  <5-brief.md | brief.json> [--write]

`check` prints every run of consecutive scenes that is one moment split apart and exits 1 when there is one.
`fold` joins each run into one scene: the shots in order, every line keeping its speaker, the beats in order, the
first frame of the first scene and the last frame of the last. Without `--write` it prints the folded scene list.
With `--write` it keeps the file it replaces beside it as `<name>.before-fold.<ext>` and writes the fold in place.
"""
import copy
import json
import re
import sys
from pathlib import Path

JOINABLE = {"talking", "broll", "b-roll", "insert-less", None}      # cards, inserts and screens stay their own scenes
GENERATION_SECONDS = 30.0      # what most video models take in one generation (owner, 2026-11-12)
WORDS_PER_SECOND = 3.0         # a read at about 180 words a minute, when a scene carries no timing of its own
MIN_SCENE_SECONDS = 1.5        # BRIEF-SPEC rule 3: a shot is at least 1.5 s
FENCE = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def _first_source(sc):
    """The source shot a scene copies (K01 …), from its shots or its `source` line."""
    for sh in sc.get("shots") or []:
        if sh.get("copies"):
            return str(sh["copies"])
    m = re.match(r"\s*(K\d+)", str(sc.get("source") or ""))
    return m.group(1) if m else None


def _moment(sc):
    """What makes two scenes the same moment: a shared parent scene, else section + setting + people + source shot."""
    if sc.get("parent_scene") or (sc.get("sourceScene") or {}).get("parent_scene"):
        return ("parent", sc.get("parent_scene") or sc["sourceScene"]["parent_scene"])
    setting = sc.get("setting_id") or sc.get("setting") or (sc.get("sourceScene") or {}).get("setting_id")
    who = sc.get("who") or (sc.get("sourceScene") or {}).get("who")
    src = _first_source(sc)
    if not (setting and who and src):
        return None
    return ("same", sc.get("section"), str(setting), str(who), src)


def _place(sc):
    return str(sc.get("setting_id") or sc.get("setting") or (sc.get("sourceScene") or {}).get("setting_id") or "").strip()


def _site(sc):
    """The place a room belongs to: HOTEL SUITE and HOTEL BATHROOM are one hotel, HOME KITCHEN and HOME OFFICE one home."""
    words = _place(sc).upper().split()
    return words[0] if words else ""


def _look(sc):
    """A 3D cut-away (a skin cross-section, a molecule) is its own world, never in one generation with people."""
    words = (_place(sc) + " " + str(sc.get("look") or "")).upper()
    return "cutaway" if re.search(r"\b3D\b|CROSS-SECTION|MACRO ANIMATION", words) else "world"


def seconds(sc):
    """How long a scene runs: its own clock or shot lengths when it has them, else its read at WORDS_PER_SECOND."""
    clock = sc.get("clock") or {}
    if isinstance(clock.get("start"), (int, float)) and isinstance(clock.get("end"), (int, float)) and clock["end"] > clock["start"]:
        return float(clock["end"] - clock["start"])
    shot = sum(float(sh.get("seconds") or 0) for sh in sc.get("shots") or [] if isinstance(sh.get("seconds"), (int, float)))
    if shot:
        return max(MIN_SCENE_SECONDS, shot)
    return max(MIN_SCENE_SECONDS, len(str(sc.get("voice") or "").split()) / WORDS_PER_SECOND)


def _joins(prev, sc, total):
    """Whether `sc` goes into the same generation as the run that ends in `prev` (`total` seconds so far)."""
    if sc.get("kind") not in JOINABLE or prev.get("kind") not in JOINABLE:
        return False
    m = _moment(prev)
    if m and _moment(sc) == m:                       # one moment split apart always joins (2026-11-08)
        return True
    if _look(sc) != _look(prev) or total + seconds(sc) > GENERATION_SECONDS:
        return False
    if (sc.get("section") == "hook") != (prev.get("section") == "hook"):
        return False                                 # hook versions swap the opening: the hook is always its own scene
    same_section = sc.get("section") and sc.get("section") == prev.get("section")
    same_place = _site(sc) and _site(sc) == _site(prev)
    return bool(same_section or same_place)


def runs(scenes):
    """[(start index, end index)] for every run of two or more consecutive scenes that belong in one generation."""
    out, i = [], 0
    while i < len(scenes):
        j, total = i + 1, seconds(scenes[i])
        while j < len(scenes) and _joins(scenes[j - 1], scenes[j], total):
            total += seconds(scenes[j])
            j += 1
        if j - i >= 2:
            out.append((i, j - 1))
        i = j
    return out


def check(scenes):
    problems = []
    for a, b in runs(scenes):
        ids = [s.get("id") for s in scenes[a:b + 1]]
        src = _first_source(scenes[a]) or "the same source shot"
        secs = sum(seconds(s) for s in scenes[a:b + 1])
        problems.append(f"{ids[0]}–{ids[-1]} fit one generation ({secs:.0f} s, same section or place, from {src}) but are split "
                        f"into {len(ids)} scenes: fold them into one scene with "
                        f"{sum(len(s.get('shots') or [{}]) for s in scenes[a:b + 1])} shots")
    return problems


def fold_run(group):
    """One scene from a run of scenes that are one moment."""
    first, last = group[0], group[-1]
    sc = copy.deepcopy(first)
    sc["id"] = first.get("parent_scene") or (first.get("sourceScene") or {}).get("parent_scene") or first.get("id")
    shots, beats, lines, speakers, starts = [], [], [], [], []
    for g in group:
        spk = g.get("speaker")
        starts.append(len(shots) + 1)                     # the shot this old scene's moment starts on
        for sh in g.get("shots") or []:
            sh = copy.deepcopy(sh)
            sh.setdefault("speaker", spk)
            for ln in sh.get("lines") or []:
                ln.setdefault("speaker", sh.get("speaker") or spk)
            shots.append(sh)
        for b in copy.deepcopy(g.get("beats") or []):
            # each beat keeps its own scene's who and place once the scenes are one: a later scene's people and setting
            # are not lost to the first scene's
            b.setdefault("who", g.get("who") or spk or "")
            b.setdefault("setting_id", g.get("setting_id") or "")
            beats.append(b)
        if g.get("voice"):
            lines.append({"speaker": spk, "say": g["voice"]})
        if spk and spk not in speakers:
            speakers.append(spk)
    for k, sh in enumerate(shots, 1):
        old = sh.get("id")
        sh["id"] = f"{sc['id']}.{k}"
        for b in beats:
            if b.get("shot") == old:
                b["shot"] = sh["id"]
        if k > 1:
            sh["scene_master"] = f"{sc['id']}.1"          # the same people in the same place as shot 1
    for k, b in enumerate(beats, 1):
        b["id"] = f"B{k}"
    sc["shots"], sc["beats"] = shots, beats
    # every old scene's staging stays, each on the shot its moment starts on (a later scene's was lost to the first's)
    for key in ("happens", "happens_swipe"):
        said = [(k, str(g.get(key)).strip()) for k, g in zip(starts, group) if str(g.get(key) or "").strip()]
        if len({s for _, s in said}) > 1:
            sc[key] = "\n".join(f"Shot {k}: {s}" for k, s in said)
    sc["voice"] = " ".join(x["say"] for x in lines)
    sc["script"] = lines                                  # the moment's lines in order, each with its speaker
    sc["speaker"] = speakers[0] if len(speakers) == 1 else "several"
    sc["speakers"] = speakers
    if last.get("last_frame") is not None:
        sc["last_frame"] = copy.deepcopy(last["last_frame"])
    sc["folded_from"] = [g.get("id") for g in group]
    sources = [sh.get("copies") for sh in shots if sh.get("copies")]
    sc["take"] = "continuous"                             # one scene is one generation (2026-11-12; BRIEF-SPEC 6-8)
    if len(set(sources)) == 1:                            # the swipe holds one take here: its motion is the reference
        sc.setdefault("motion", {"copies": sources[0]})
    elif sources:                                         # several swipe shots: their motion runs in order in one take
        sc.setdefault("motion", {"copies": list(dict.fromkeys(sources))})
    sections = list(dict.fromkeys(g.get("section") for g in group if g.get("section")))
    if len(sections) > 1:
        sc["sections"] = sections                         # `section` stays the first, so section checks still read one
    sc["seconds"] = round(sum(seconds(g) for g in group), 1)
    for k in ("source_turn_id", "speaker_map", "native_voice_routing"):
        sc.pop(k, None)
    return sc


def fold(scenes):
    out, i = [], 0
    spans = {a: b for a, b in runs(scenes)}
    while i < len(scenes):
        if i in spans:
            out.append(fold_run(scenes[i:spans[i] + 1]))
            i = spans[i] + 1
        else:
            out.append(scenes[i])
            i += 1
    return out


FILLER = {"nothing", "none", "no words", "-", "—"}


def _lines(*vals):
    """The old scenes' lines in order, a line that runs on across them said once, filler ("nothing") dropped."""
    out = []
    for v in vals:
        s = str(v).strip() if v else ""
        if s and s.lower().rstrip(".") not in FILLER and s not in out:
            out.append(s)
    return "\n".join(out)


def join_run(group):
    """One scene from consecutive scenes that carry the same section tag, in the shape of a hand-joined brief: the
    first scene's fields, and every old scene's shots in order as the scene's own shots (S1.1, S1.2 ...), each later
    shot keeping the scene master. Nothing is dropped: each shot names the old scene it came from (`of_scene`), and
    every old scene's own fields are kept in `joined_scenes`, so the words, pictures and on-screen text of every old
    scene stay on the joined one (owner ruling, 2026-11-16). Nothing else decides the join."""
    first, last = group[0], group[-1]
    sc = copy.deepcopy(first)
    sid = first.get("id")
    shots, beats, script, kept = [], [], [], []
    for g in group:
        keep = {k: copy.deepcopy(v) for k, v in g.items() if k != "shots"}
        if "shots" in g and not g["shots"]:
            keep["_empty_shots"] = True
        kept.append(keep)
        own = copy.deepcopy(g.get("shots") or []) or [{"id": g.get("id")}]
        rename = {}
        for sh in own:
            n = len(shots) + 1
            added = []
            new_id = f"{sid}.{n}"
            rename[sh.get("id")] = new_id
            sh["was_id"], sh["id"], sh["of_scene"] = sh.get("id"), new_id, g.get("id")
            if n > 1 and "scene_master" not in sh:
                sh["scene_master"] = f"{sid}.1"           # the same people in the same place as shot 1
                added.append("scene_master")
            if g is not first and sh.get("start_picture") == "first_frame" and g.get("first_frame") is not None \
                    and "first_frame" not in sh:
                sh["first_frame"] = copy.deepcopy(g["first_frame"])   # its own old scene's first frame, not shot 1's
                added.append("first_frame")
            sh["_added"] = added
            shots.append(sh)
        for bt in copy.deepcopy(g.get("beats") or []):
            if bt.get("shot") in rename:
                bt["shot"] = rename[bt["shot"]]
            beats.append(bt)
        if g.get("voice"):
            script.append({"of_scene": g.get("id"), "speaker": g.get("speaker"), "say": g["voice"]})
    for k, bt in enumerate(beats, 1):
        bt["id"] = f"B{k}"                                # one beat list for the scene: no repeated ids
    sc["shots"], sc["beats"], sc["script"], sc["joined_scenes"] = shots, beats, script, kept
    sc["voice"] = " ".join(x["say"] for x in script)
    firsts = {}
    for sh in shots:
        firsts.setdefault(sh["of_scene"], sh["id"].rsplit(".", 1)[-1])
    sc["happens"] = "\n".join(f"Shot {firsts.get(g.get('id'), k)}: {str(g.get('happens')).strip()}"
                               for k, g in enumerate(group, 1) if g.get("happens"))
    sc["on_screen"] = _lines(*[g.get("on_screen") for g in group])
    speakers = list(dict.fromkeys(g.get("speaker") for g in group if g.get("speaker")))
    sc["speakers"], sc["speaker"] = speakers, (speakers[0] if len(speakers) == 1 else ("several" if speakers else first.get("speaker")))
    if last.get("last_frame") is not None:
        sc["last_frame"] = copy.deepcopy(last["last_frame"])
    sc["joined_from"] = [g.get("id") for g in group]
    return sc


# A plate scene (a screen, a card, the end card) is its own picture: it never joins another scene. 2026-11-19: an end
# card tagged call-to-action was folded into the talking scene before it and dropped out of the run sheet.
PLATE_KINDS = ("screen", "card", "endcard")


def join_sections(scenes):
    """Consecutive scenes with the same section tag become one scene, their shots in order inside it. A plate scene
    (PLATE_KINDS) always stands alone."""
    out, i = [], 0
    while i < len(scenes):
        j = i + 1
        tag = scenes[i].get("section")
        plate = lambda s: str(s.get("kind") or "") in PLATE_KINDS
        while tag and not plate(scenes[i]) and j < len(scenes) and scenes[j].get("section") == tag and not plate(scenes[j]):
            j += 1
        out.append(join_run(scenes[i:j]) if j - i >= 2 else scenes[i])
        i = j
    return out


def unjoin(scenes):
    """The scenes as they were written, before the section join: each old scene back from `joined_scenes` with its
    own shots, ids and fields exactly as written. Checks that judge one written scene at a time read this view."""
    out = []
    for sc in scenes:
        if not (sc.get("joined_from") and isinstance(sc.get("joined_scenes"), list)):
            out.append(sc)
            continue
        for old in sc["joined_scenes"]:
            g = copy.deepcopy(old)
            empty = g.pop("_empty_shots", False)
            mine = [copy.deepcopy(sh) for sh in sc.get("shots") or [] if sh.get("of_scene") == old.get("id")]
            for sh in mine:
                for k in sh.pop("_added", []):
                    sh.pop(k, None)
                sh.pop("of_scene", None)
                sh["id"] = sh.pop("was_id")
            if not (len(mine) == 1 and set(mine[0]) == {"id"} and mine[0]["id"] == old.get("id")):
                g["shots"] = mine
            elif empty:
                g["shots"] = []
            out.append(g)
    return out


def unjoined_text(path):
    """The brief's text with its scene block put back as written (unjoin), or None when nothing in it was joined."""
    text, doc, block = _load(str(path))
    scenes = doc.get("scenes") or []
    flat = unjoin(scenes)
    if len(flat) == len(scenes):
        return None
    body = json.dumps(dict(doc, scenes=flat), indent=1, ensure_ascii=False)
    return body + "\n" if block is None else text[:block.start(1)] + body + text[block.end(1):]


SCENE_KEYS = ("scene", "opener_scene", "from_scene", "at_scene", "scene_id", "after_scene", "before_scene")
SHOT_KEYS = ("shot",)


def repoint(doc):
    """Every pointer outside the scene list (sound effects, music cues, layers, hooks, openings) that names an old
    scene now inside a joined one is pointed at the joined scene, and at its shot. Returns how many moved."""
    where, shot_of = {}, {}
    for sc in doc.get("scenes") or []:
        for sh in sc.get("shots") or [] if sc.get("joined_from") else []:
            if isinstance(sh, dict) and sh.get("of_scene") and sh["of_scene"] not in where:
                where[sh["of_scene"]] = (sc["id"], sh["id"])
            if isinstance(sh, dict) and sh.get("was_id") and sh["was_id"] != sh["id"]:
                shot_of[sh["was_id"]] = sh["id"]
    moved = [0]

    def walk(o):
        if isinstance(o, dict):
            for k in list(o):
                v = o[k]
                if k in SCENE_KEYS and isinstance(v, str) and v in where and "was_" + k not in o:
                    o["was_" + k], o["shot_in_scene"] = v, where[v][1]
                    o[k] = where[v][0]
                    moved[0] += 1
                elif k in SHOT_KEYS and isinstance(v, str) and v in shot_of and "was_" + k not in o:
                    o["was_" + k], o[k] = v, shot_of[v]
                    moved[0] += 1
                elif k == "scenes" and isinstance(v, list) and all(isinstance(x, str) for x in v):
                    new = list(dict.fromkeys(where.get(x, (x,))[0] for x in v))
                    if new != v:
                        o["was_scenes"], o[k] = v, new
                        moved[0] += 1
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    for k, v in doc.items():
        if k != "scenes":
            walk(v)
    return moved[0]


def as_written(doc):
    """The brief's machine block as it was written, before the section join and its repoint: joined scenes back to
    their old scenes, every repointed cue back to the scene it named. A join is a regrouping, not an edit, so the
    fingerprints that guard a brief (swipe match, manifest, writing acceptance) read this view."""
    doc = copy.deepcopy(doc)
    doc.pop("footage_band", None)

    def back(o):
        if isinstance(o, dict):
            for k in [k for k in list(o) if k.startswith("was_") and k[4:] in SCENE_KEYS + SHOT_KEYS + ("scenes",)]:
                o[k[4:]] = o.pop(k)
            o.pop("shot_in_scene", None)
            for v in o.values():
                back(v)
        elif isinstance(o, list):
            for x in o:
                back(x)
    for k, v in doc.items():
        if k != "scenes":
            back(v)
    for sc in doc.get("scenes") or []:
        sc.pop("footage", None)                           # a shotless scene's footage answer, derived the same way
        for sh in sc.get("shots") or []:
            if isinstance(sh, dict):
                sh.pop("subjects", None)                  # derived from the brief's definitions on every write
                sh.pop("footage", None)                   # derived from the footage library on every write
    doc["scenes"] = unjoin(doc.get("scenes") or [])
    return doc


def same_as_written(now_text, before_text):
    """True when `now_text` is `before_text` with its scenes joined by section tag and nothing else changed: the words
    outside the machine block identical, and the block identical once read as written."""
    blocks_now, blocks_before = list(FENCE.finditer(now_text)), list(FENCE.finditer(before_text))
    if not blocks_now or not blocks_before:
        return False
    a, b = blocks_now[-1], blocks_before[-1]
    if now_text[:a.start(1)] != before_text[:b.start(1)] or now_text[a.end(1):] != before_text[b.end(1):]:
        return False
    try:
        return as_written(json.loads(a.group(1))) == json.loads(b.group(1))
    except ValueError:
        return False


LOCK_REF = re.compile(r"^\s*(S[\w-]*?)(?:\s*[·:,]\s*(S[\w.-]+))?\s*[·:,]")


def _cast_in(text, cast_ids):
    text = str(text or "")
    return [c for c in cast_ids if re.search(r"(?<![A-Za-z])" + re.escape(c) + r"(?![A-Za-z])", text)]


def _repo(start):
    for d in [Path(start).resolve()] + list(Path(start).resolve().parents):
        if (d / "components" / "naming" / "names.py").is_file() and (d / "brands").is_dir():
            return d
    return None


def product_subject(brand, product, repo):
    """The brief's product as the bank holds it, through the one product door every brand uses
    (components/naming/products.py `record`): catalog id, name, bank page, kit, Drive packshots. None when unknown."""
    if not (brand and product and repo):
        return None
    import importlib.util as iu
    sp = iu.spec_from_file_location("scene_shots_products", Path(repo) / "components" / "naming" / "products.py")
    pr = iu.module_from_spec(sp)
    sys.path.insert(0, str(Path(repo) / "components" / "naming"))
    sp.loader.exec_module(pr)
    rec = pr.record(brand, product, root=repo)
    return {k: v for k, v in rec.items() if k not in ("brand", "missing")} if rec else None


def define_subjects(doc, product=None):
    """Every shot names its subjects from the brief's own definitions, so production never has to guess what "the
    brush" or "he" is: the people (their identity and this scene's look), the product line written for this shot, the
    place, and the props with their size and look. Nothing is invented: a subject the brief does not define is left
    out. Derived on every write; `as_written` leaves it out. Returns how many shots carry subjects."""
    cast = {str(c.get("id")): c for c in doc.get("cast") or [] if isinstance(c, dict) and c.get("id")}
    world = {str(w.get("id")): w for w in doc.get("world") or [] if isinstance(w, dict) and w.get("id")}
    props = {str(x.get("name")).lower(): x for x in doc.get("props") or [] if isinstance(x, dict) and x.get("name")}
    locks = []
    for ln in doc.get("product_lock") or []:
        m = LOCK_REF.match(str(ln))
        if m:
            locks.append((m.group(1), m.group(2), str(ln)))
    n = 0
    for sc in doc.get("scenes") or []:
        olds = {o.get("id"): o for o in sc.get("joined_scenes") or []}
        for sh in sc.get("shots") or []:
            if not isinstance(sh, dict):
                continue
            src = olds.get(sh.get("of_scene")) or sc
            scene_ref, shot_ref = src.get("id"), sh.get("was_id") or sh.get("id")
            names = []
            for field in (src.get("who"), " ".join((src.get("looks") or {}).keys()), src.get("speaker"), sh.get("speaker")):
                for c in _cast_in(field, list(cast)):
                    if c not in names:
                        names.append(c)
            people = [{"id": c, "is": cast[c].get("identity_block") or cast[c].get("description") or "",
                       "look": (src.get("looks") or {}).get(c, "")} for c in names]
            lines = [ln for s, shot, ln in locks if (shot and shot == shot_ref) or (not shot and s == scene_ref)]
            said = " ".join(str(x) for x in [src.get("happens"), (src.get("first_frame") or {}).get("subject"),
                                             sh.get("gestures"), sh.get("ends_on"), sh.get("face")] if x).lower()
            shows = bool(lines) or bool(product and any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", said)
                                                          for w in product.get("words") or []))
            place = world.get(str(src.get("setting_id") or ""))
            subj = {}
            if people:
                subj["people"] = people
            if shows:
                subj["product"] = dict({k: v for k, v in (product or {}).items() if k != "words"}, in_shot=lines)
            if place:
                subj["place"] = {"id": place["id"], "is": place.get("description") or "", "light": place.get("light") or ""}
            pr = [dict(name=props[str(x).lower()].get("name"), size=props[str(x).lower()].get("size") or "",
                       look=props[str(x).lower()].get("look") or "") for x in src.get("props") or [] if str(x).lower() in props]
            if pr:
                subj["props"] = pr
            if subj:
                sh["subjects"] = subj
                n += 1
            else:
                sh.pop("subjects", None)
    return n


def _portable(p):
    """A machine path to a file in the workspace, as a repo-relative path (builder card rule 4)."""
    p = str(p or "")
    m = re.search(r"/((?:components|runs|brands)/.+)$", p)
    return m.group(1) if (p.startswith("/") and m) else (p or None)


def attach_footage(doc, footage):
    """The footage pass's answer (video-production footage.storyboard_pass) on every shot it decided: `footage` =
    {plan: cut | generate | presenter | made | held, clip (when cut), nearest (our closest clip, cut or not)}.
    Keyed by the scene as written, so a joined scene's shots each carry their own old scene's answer. Derived on every
    write, like `subjects`; `as_written` leaves it out. Returns how many shots carry it."""
    rows = (footage or {}).get("scenes") or {}
    n = 0
    for sc in doc.get("scenes") or []:
        if not sc.get("shots"):            # a scene with no shot lines (an end card): its answer sits on the scene
            row = rows.get(sc.get("id"))
            if row and (row.get("clip") or row.get("nearest")):
                sc["footage"] = {"plan": row.get("plan"),
                                 **{k: dict(row[k], frame=_portable(row[k].get("frame"))) for k in ("clip", "nearest") if row.get(k)}}
                n += 1
            else:
                sc.pop("footage", None)
            continue
        for sh in sc.get("shots") or []:
            if not isinstance(sh, dict):
                continue
            row = rows.get(sh.get("of_scene") or sc.get("id"))
            if not row:
                sh.pop("footage", None)
                continue
            f = {"plan": row.get("plan")}
            for k in ("clip", "nearest"):
                if row.get(k):
                    f[k] = dict(row[k], frame=_portable(row[k].get("frame")))
            if row.get("alternates"):
                f["alternates"] = row["alternates"]
            if row.get("place"):
                f["place"] = row["place"]
            sh["footage"] = f
            n += 1
    if footage:
        doc["footage_band"] = {"band": footage.get("band"), "creators": footage.get("creators") or [],
                               "cut": footage.get("cut"), "generate": footage.get("generate")}
    return n


def footage_file(path, footage):
    """Put the footage pass's answer on every shot of a brief in place (attach_footage); returns shots answered."""
    path = str(path)
    text, doc, block = _load(path)
    n = attach_footage(doc, footage)
    body = json.dumps(doc, indent=1, ensure_ascii=False)
    Path(path).write_text(body + "\n" if block is None else text[:block.start(1)] + body + text[block.end(1):])
    return n


def fold_file(path):
    """Join a brief's scenes by section tag in place, keeping the file before beside it, and point every cue that
    named an old scene at its joined scene. Returns (scenes before, scenes after); a brief already joined and
    pointed is left untouched. The writing chain calls this the moment a brief is written (2026-11-16), so the
    storyboard shows one scene per section with its shots inside."""
    path = str(path)
    text, doc, block = _load(path)
    scenes = doc.get("scenes") or []
    before = json.dumps(doc, sort_keys=True, ensure_ascii=False)
    folded = join_sections(scenes)
    doc = dict(doc, scenes=folded)
    repoint(doc)
    run = {}
    try:
        run = json.loads((Path(path).resolve().parent.parent / "run.json").read_text())
    except (OSError, ValueError):
        pass
    define_subjects(doc, product_subject(run.get("brand"), run.get("product"), _repo(path)))
    if json.dumps(doc, sort_keys=True, ensure_ascii=False) == before:
        return len(scenes), len(folded)
    p = Path(path)
    if len(folded) < len(scenes):                       # a repoint alone keeps the brief-as-written copy already there
        p.with_name(p.stem + ".before-fold" + p.suffix).write_text(text)
    body = json.dumps(dict(doc, scenes=folded), indent=1, ensure_ascii=False)
    p.write_text(body + "\n" if block is None else text[:block.start(1)] + body + text[block.end(1):])
    return len(scenes), len(folded)


def _load(path):
    text = Path(path).read_text()
    if path.endswith(".json"):
        return text, json.loads(text), None
    m = list(FENCE.finditer(text))
    if not m:
        sys.exit(f"{path}: no json block")
    return text, json.loads(m[-1].group(1)), m[-1]


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "fold"):
        sys.exit(__doc__)
    path = argv[1]
    text, doc, block = _load(path)
    scenes = doc.get("scenes") or []
    if argv[0] == "check":
        problems = check(scenes)
        for p in problems:
            print("SPLIT:", p)
        print("scenes are sequences ✓" if not problems else f"{len(problems)} moment(s) split apart")
        return 1 if problems else 0
    folded = fold(scenes)
    doc = dict(doc, scenes=folded)
    if "--write" not in argv:
        print(json.dumps([{"id": s.get("id"), "shots": len(s.get("shots") or []), "speakers": s.get("speakers") or [s.get("speaker")]}
                          for s in folded], ensure_ascii=False))
        return 0
    p = Path(path)
    p.with_name(p.stem + ".before-fold" + p.suffix).write_text(text)
    body = json.dumps(doc, indent=1, ensure_ascii=False)
    p.write_text(body + "\n" if block is None else text[:block.start(1)] + body + text[block.end(1):])
    print(f"folded {len(scenes)} scenes into {len(folded)}; the file before is kept beside it")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
