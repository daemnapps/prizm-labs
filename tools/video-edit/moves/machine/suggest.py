"""moves: the shortlist. For every scene in a project's loop, gather the scene facts, the music events in its
bar, and the 8 best candidate moves from library/moves-v1-damon.json, scored by plain rules. No external API.

    python3 machine/suggest.py [<project>]      # default productions/music-video

Reads  <project>/edit/loop.json, <project>/song/crsl/bass.json, kicks.json, <project>/3d/catalogue.json
Writes out/<name>-moves.json and .md   (<name> = the project folder's name)

Scoring (all additive, highest first):
  +3 if the move's main trigger (the first one listed) happens in the bar, +4 if that event is rare in the
     loop (break, silence, drop, reverse, space, double-time, loop seam, vocal word); +1 per further trigger hit
  +0.5 per word shared between the move's picture and the scene's description (up to +2)
  +2 if the move suits one of the scene's kinds (real / ai / 3d / mix), +1 more for the family's lean
  +2 if the move uses an object that is in the scene (+1 if it takes any object and the scene has one)
  +0.3 x wow as the tie-break
  -0.75 for each earlier scene whose shortlist already carries the move, so the loop gets a spread
  At most 3 moves per family in the top 8, so the shortlist is a spread, not eight flavours of one idea.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOVES = Path(__file__).resolve().parents[1]
TOP, PER_FAMILY = 8, 3
STRONG_KICK = 7.0      # kicks.json strength at or above this is a "strong kick"
LONG_SLIDE = 10.0      # bass slide at or above this is a long slide (bars 2, 6, 8 in the scenes doc)
SLIDE = 5.0

# which families lean toward which kind of scene
FAMILY_LEAN = {
    "transition": {"real", "mix", "3d"}, "cut": {"real"}, "object-move": {"3d", "mix"},
    "pop-in": {"ai", "mix", "3d"}, "camera": {"real", "3d"}, "time": {"real", "ai"},
    "frame-break": {"real", "ai", "mix"}, "type": {"real", "mix"}, "sound-sync": {"real", "3d", "mix"},
}
ALIASES = {"statue": "damon-full-body", "stone": "damon-full-body", "everything": "*orbit*",
           "bag": "bag-cream-strap", "record": "vinyl", "ball": "padel-ball", "racket": "padel-racket",
           "monk": "monk", "orbits": "*orbit*"}
RARE = {"break", "silence", "drop", "reverse", "space", "double-time", "loop seam", "last bar", "vocal word", "strong kick"}
STOP = set("""a an the and or of in on at to into from with his him he it its is as by for so that this then
one two same next scene shot frame picture every each like until while over out up down back off all
through whole still just very only first per cut cuts beat real sits turns""".split())


def load(p):
    return json.loads(Path(p).read_text())


def fmt_t(t, bar, beat):
    b = 1 + (t - bar["start"]) / beat
    return f"{t:.2f}s (bar {bar['n']}, beat {b:.2f})"


def scene_objects(shots, catalogue):
    """catalogue ids present in the scene: whole words in the shots' object and description text,
    plus sources that are catalogue ids themselves."""
    words = set(re.findall(r"[a-z]+", " ".join((s.get("object") or "") + " " + (s.get("what") or "") for s in shots).lower()))
    srcs = {x for s in shots for x in (s.get("src") or [])}
    found = {cid for cid in catalogue if cid in srcs}
    skip = {"desk", "damon", "full", "body", "strap", "black", "cream", "pouch", "sign"}
    for cid in catalogue:
        need = [w for w in cid.split("-") if w not in skip]
        if need and all(w in words for w in need) and (cid != "goja-sign" or "sign" in words or "neon" in words):
            found.add(cid)
    for word, cid in ALIASES.items():
        if word in words:
            if cid == "*orbit*":
                found.update(["carousel", "koi", "padel-racket", "bag-cream-strap", "goja-sign", "turntable"])
            elif cid in catalogue:
                found.add(cid)
    return sorted(found)


def bar_events(bar, kicks, notes, beat, n_bars):
    s, e = bar["start"], bar["end"]
    ks = [(t, v) for t, v in kicks if s <= t < e]
    ns = [n for n in notes if s <= n["t"] < e]
    music = (bar.get("music") or "").lower()
    tags = {"downbeat"}
    if ks: tags.add("kick")
    if any(v >= STRONG_KICK for _, v in ks): tags.add("strong kick")
    if ns: tags.add("bass note")
    if any(n["slide"] >= SLIDE for n in ns): tags.add("bass slide")
    if bar.get("word"): tags.add("vocal word")
    if "double-time" in music: tags.add("double-time")
    if "space" in music: tags.add("space")
    if "revers" in music: tags.add("reverse")
    if "break" in music or "drums out" in music: tags.update({"break", "silence"})
    if not ks and not ns: tags.add("silence")
    if "return" in music: tags.add("drop")
    if bar["n"] in (1, n_bars): tags.add("loop seam")
    if bar["n"] == n_bars: tags.add("last bar")
    held = [n for n in notes if n["t"] < s < n["t"] + n["dur"]]
    return {
        "tags": sorted(tags),
        "kicks": [{"t": round(t, 3), "at": fmt_t(t, bar, beat), "strength": v} for t, v in ks],
        "bass_notes": [{"t": n["t"], "at": fmt_t(n["t"], bar, beat), "note": n["note"], "dur": n["dur"],
                         "slide": n["slide"], "level": n["level"], "long_slide": n["slide"] >= LONG_SLIDE} for n in ns],
        "bass_held_over": [f"{n['note']} from {n['t']:.2f}s, held {n['dur']:.2f}s" for n in held],
        "snare": "not measured yet (only kicks and bass are in the song files)",
    }


TAGS = ["strong kick", "kick", "bass slide", "bass note", "downbeat", "vocal word", "double-time", "drop",
        "break", "silence", "space", "reverse", "loop seam", "last bar"]


def trigger_tags(text):
    text = text.lower()
    out = []
    for tag in TAGS:
        key = "kick (strongest)" if tag == "strong kick" else tag
        if tag == "kick" and "strong kick" in out:
            continue
        if key in text:
            out.append(tag)
    return out


def score(move, kinds, objs, tags, scene_words, seen):
    why, pts = [], 0.0
    parts = move["music_trigger"].split(",")
    main = trigger_tags(parts[0])
    rest = [t for t in trigger_tags(",".join(parts[1:])) if t not in main]
    hit_main = [t for t in main if t in tags]
    hit_rest = [t for t in rest if t in tags]
    if hit_main:
        pts += 4 if any(t in RARE for t in hit_main) else 3
    pts += len(hit_rest)
    if hit_main or hit_rest:
        why.append("music: " + ", ".join(hit_main + hit_rest))
    fit = sorted(set(move["kinds"]) & kinds)
    if fit:
        pts += 2
        why.append("suits " + "/".join(fit))
    if FAMILY_LEAN.get(move["family"], set()) & kinds:
        pts += 1
    mo = move.get("objects") or []
    if mo and mo != ["*"] and set(mo) & set(objs):
        pts += 2
        why.append("uses " + ", ".join(sorted(set(mo) & set(objs))))
    elif mo == ["*"] and objs:
        pts += 1
        why.append("takes any object (" + objs[0] + (" …" if len(objs) > 1 else "") + ")")
    shared = sorted(scene_words & (set(re.findall(r"[a-z]{3,}", (move["name"] + " " + move["what_you_see"]).lower())) - STOP))
    if shared:
        pts += min(2.0, 0.5 * len(shared))
        why.append("matches the scene: " + ", ".join(shared[:4]))
    pts += 0.3 * move["wow"]
    if seen.get(move["id"]):
        pts -= 0.75 * seen[move["id"]]
        why.append(f"already shortlisted in {seen[move['id']]} earlier scene(s)")
    return round(pts, 2), why


def shortlist(moves, kinds, objs, tags, shots, seen):
    scene_words = set(re.findall(r"[a-z]{3,}", " ".join(s.get("what") or "" for s in shots).lower())) - STOP
    scored = []
    for m in moves:
        pts, why = score(m, kinds, objs, tags, scene_words, seen)
        scored.append((pts, m, why))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    out, fam = [], {}
    for pts, m, why in scored:
        if fam.get(m["family"], 0) >= PER_FAMILY:
            continue
        fam[m["family"]] = fam.get(m["family"], 0) + 1
        out.append({"id": m["id"], "name": m["name"], "family": m["family"], "score": pts, "why": why,
                    "wow": m["wow"], "cost": m["cost"], "what_you_see": m["what_you_see"]})
        if len(out) == TOP:
            break
    for c in out:
        seen[c["id"]] = seen.get(c["id"], 0) + 1
    return out


def main():
    project = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "productions/music-video")
    loop = load(project / "edit" / "loop.json")
    bass = load(project / "song" / "crsl" / "bass.json")["notes"]
    kicks = load(project / "song" / "crsl" / "kicks.json")["kicks"]
    catalogue = load(project / "3d" / "catalogue.json")["objects"]
    index = load(MOVES / "library" / "moves-v1-damon.json")["moves"]
    bars = loop["bars"]
    beat = (bars[0]["end"] - bars[0]["start"]) / 4

    scenes, seen = [], {}
    pre = [s for s in loop["shots"] if s["end"] <= 0]
    if pre:
        kinds = {s["kind"] for s in pre}
        objs = scene_objects(pre, catalogue)
        tags = ["downbeat", "silence"]
        scenes.append({"scene": "0 · first play", "start": pre[0]["start"], "end": 0.0, "bar": None,
                       "music": "none yet: the loop starts on the downbeat as he presses play", "word": "",
                       "kinds": sorted(kinds), "objects": objs, "shots": pre,
                       "events": {"tags": tags, "kicks": [], "bass_notes": [], "bass_held_over": [],
                                  "snare": "n/a"},
                       "candidates": shortlist(index, kinds, objs, set(tags), pre, seen)})
    for bar in bars:
        shots = [s for s in loop["shots"] if bar["start"] - 0.01 <= s["start"] < bar["end"] - 0.01]
        kinds = {s["kind"] for s in shots}
        objs = scene_objects(shots, catalogue)
        ev = bar_events(bar, kicks, bass, beat, len(bars))
        scenes.append({"scene": str(bar["n"]), "start": bar["start"], "end": bar["end"], "bar": bar["n"],
                       "music": bar.get("music"), "word": bar.get("word"), "kinds": sorted(kinds), "objects": objs,
                       "shots": shots, "events": ev, "candidates": shortlist(index, kinds, objs, set(ev["tags"]), shots, seen)})

    name = project.name
    outdir = MOVES / "out"
    outdir.mkdir(exist_ok=True)
    (outdir / f"{name}-moves.json").write_text(json.dumps(
        {"project": str(project.relative_to(ROOT)), "beat_seconds": round(beat, 4), "index_size": len(index),
         "scenes": scenes}, indent=1, ensure_ascii=False))

    md = [f"# Moves shortlist: {name}", "",
          f"Made by `tools/moves/machine/suggest.py` from `{project.relative_to(ROOT)}/edit/loop.json`, the bass and "
          f"kick files, and the {len(index)}-move index. Top {TOP} per scene, at most {PER_FAMILY} per family. "
          f"A beat is {beat:.3f}s. This is the shortlist the creative-director prompt picks from, not the choice.", ""]
    for sc in scenes:
        md.append(f"## Scene {sc['scene']} · {sc['start']:.2f}–{sc['end']:.2f}s")
        md.append(f"- **Music:** {sc['music']}" + (f" · word: *{sc['word']}*" if sc['word'] else ""))
        md.append(f"- **Kinds:** {', '.join(sc['kinds'])} · **objects:** {', '.join(sc['objects']) or 'none'}")
        for s in sc["shots"]:
            md.append(f"- **Shot {s['start']:.2f}–{s['end']:.2f} ({s['kind']}):** {s['what']}")
        ev = sc["events"]
        md.append(f"- **Events:** {', '.join(ev['tags'])}")
        if ev["kicks"]:
            md.append("- **Kicks:** " + "; ".join(f"{k['at']} · {k['strength']}" for k in ev["kicks"]))
        if ev["bass_notes"]:
            md.append("- **Bass:** " + "; ".join(f"{n['note']} at {n['at']}, {n['dur']:.2f}s, slide {n['slide']}"
                                                  + (" (long slide)" if n["long_slide"] else "") for n in ev["bass_notes"]))
        if ev["bass_held_over"]:
            md.append("- **Bass held over from before:** " + "; ".join(ev["bass_held_over"]))
        md += ["", "| # | Move | Family | Score | Why |", "|---|---|---|---|---|"]
        for i, c in enumerate(sc["candidates"], 1):
            md.append(f"| {i} | `{c['id']}` {c['name']} | {c['family']} | {c['score']} | {'; '.join(c['why'])} |")
        md.append("")
    (outdir / f"{name}-moves.md").write_text("\n".join(md))
    print(f"{len(scenes)} scenes · {len(index)} moves → tools/moves/out/{name}-moves.json / .md")


if __name__ == "__main__":
    main()
