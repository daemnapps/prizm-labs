#!/usr/bin/env python3
"""Scenes are sequences: one moment is one scene, its shots in order (components/video-production/BRIEF-SPEC.md,
"Scenes and shots", 2026-11-08).

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


def runs(scenes):
    """[(start index, end index)] for every run of two or more consecutive scenes that are one moment."""
    out, i = [], 0
    while i < len(scenes):
        m = _moment(scenes[i]) if scenes[i].get("kind") in JOINABLE else None
        j = i + 1
        while m and j < len(scenes) and scenes[j].get("kind") in JOINABLE and _moment(scenes[j]) == m:
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
        problems.append(f"{ids[0]}–{ids[-1]} are one moment (same place, people and {src}) split into {len(ids)} scenes: "
                        f"fold them into one scene with {sum(len(s.get('shots') or [{}]) for s in scenes[a:b + 1])} shots")
    return problems


def fold_run(group):
    """One scene from a run of scenes that are one moment."""
    first, last = group[0], group[-1]
    sc = copy.deepcopy(first)
    sc["id"] = first.get("parent_scene") or (first.get("sourceScene") or {}).get("parent_scene") or first.get("id")
    shots, beats, lines, speakers = [], [], [], []
    for g in group:
        spk = g.get("speaker")
        for sh in g.get("shots") or []:
            sh = copy.deepcopy(sh)
            sh.setdefault("speaker", spk)
            for ln in sh.get("lines") or []:
                ln.setdefault("speaker", sh.get("speaker") or spk)
            shots.append(sh)
        beats += copy.deepcopy(g.get("beats") or [])
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
    sc["voice"] = " ".join(x["say"] for x in lines)
    sc["script"] = lines                                  # the moment's lines in order, each with its speaker
    sc["speaker"] = speakers[0] if len(speakers) == 1 else "several"
    sc["speakers"] = speakers
    if last.get("last_frame") is not None:
        sc["last_frame"] = copy.deepcopy(last["last_frame"])
    sc["folded_from"] = [g.get("id") for g in group]
    sources = {sh.get("copies") for sh in shots if sh.get("copies")}
    if len(sources) == 1:                                 # the swipe holds one take here: made as ONE clip (BRIEF-SPEC 6-8)
        sc["take"] = "continuous"
        sc.setdefault("motion", {"copies": next(iter(sources))})
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
