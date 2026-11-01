#!/usr/bin/env python3
"""The creative controls — one set of dials for copy, video and pictures.

    python3 components/creative-controls/creative_controls.py render [--check]

`controls.json` holds the dials, emotions, techniques, guards and presets;
`glossary.json` holds the literature, the names practitioners and researchers
use. `render` writes `slices/controls.md` (bound in a prompt as
`{creative_controls}`) and `GLOSSARY.md` (for people). Neither is edited by
hand: the next render erases it. `--check` fails if either has drifted.

A chain imports this file for `dials(medium)` and `target(preset, brand)`
and never restates a dial. Stdlib only, no credential, writes nothing but
the two rendered files.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTROLS = HERE / "controls.json"
GLOSSARY = HERE / "glossary.json"
SLICE = HERE / "slices" / "controls.md"
GLOSSARY_MD = HERE / "GLOSSARY.md"
HEAD = "<!-- rendered from components/creative-controls by creative_controls.py render — do not hand-edit -->"
REPO = next((r for r in HERE.parents if (r / "components").is_dir() and (r / "runs").is_dir()), HERE.parents[1])


def load():
    return json.loads(CONTROLS.read_text())


def dials(medium=None):
    """Every dial, or only the ones a medium (copy · video · image) uses."""
    return [d for d in load()["dials"] if medium is None or medium in d["media"]]


def target(preset="maxed", brand=None, medium="image"):
    """The levels a run aims for: every dial's default for the medium, the
    preset on top, then any level a person saved on the Creative Controls page
    (synced to runs/creative-controls/<brand>/levels.json)."""
    c = load()
    pr = next((p for p in c["presets"] if p["id"] == preset), None)
    if not pr:
        raise KeyError("no creative-controls preset %r; choose from %s"
                       % (preset, ", ".join(p["id"] for p in c["presets"])))
    levels = {d["id"]: d["default"]["level"] for d in c["dials"] if medium in d["media"]}
    levels.update({k: v for k, v in pr["levels"].items() if k in levels})
    saved = REPO / "runs" / "creative-controls" / (brand or "") / "levels.json"
    if brand and saved.is_file():
        levels.update({k: v for k, v in json.loads(saved.read_text()).get(preset, {}).items() if k in levels})
    for k, v in c.get("floor", {}).get("levels", {}).items():   # never sterile, whatever was saved
        if k in levels:
            levels[k] = max(levels[k], v)
    return pr, levels


DIAL_LINE = re.compile(r"^\s*-\s*`?([a-z_]+)`?\s*:\s*swipe\s+(-?\d)\s*(?:→|->)\s*ours\s+(-?\d)", re.M)


def floor_problems(text):
    """The never-sterile check on a written stage: every floor dial must appear
    in its THE DIALS lines (`dial: swipe N → ours M`) at or above the floor.
    [] when it clears. A stage that set no dials at all fails: nothing was set."""
    floor = load().get("floor", {}).get("levels", {})
    ours = {m.group(1): int(m.group(3)) for m in DIAL_LINE.finditer(text or "")}
    if not ours:
        return ["no dials were set (no THE DIALS lines)"]
    only_when_set = set(load().get("floor", {}).get("when_set", []))  # e.g. parody marks: most swipes carry none
    out = []
    for k, v in floor.items():
        if k not in ours:
            if k not in only_when_set:
                out.append("%s not set" % k)
        elif ours[k] < v:
            out.append("%s %d, under the floor %d" % (k, ours[k], v))
    return out


def target_md(preset="maxed", brand=None, medium="image"):
    pr, levels = target(preset, brand, medium)
    names = {d["id"]: {s["level"]: s["name"] for s in d["scale"]} for d in load()["dials"]}
    return ("Preset: %s (%s) — %s\n\n" % (pr["name"], pr["id"], pr["what"])
            + "\n".join("- %s: %s (%s)" % (k, v, names[k].get(v, "")) for k, v in levels.items()) + "\n")


def _cites(rows):
    return "; ".join("%s%s%s" % (r["cite"], " " + r["url"] if r.get("url") else "",
                                 "" if r.get("checked") else " (unchecked)") for r in rows)


def render_slice(c):
    out = [HEAD, "", "# Creative controls — the dials for copy, video and pictures", "",
           "Bound as `{creative_controls}`. Source: components/creative-controls.", "",
           c["what"], "", "**One standard.** %s" % c["rule"], "", "**The default.** %s" % c["default_rule"], "",
           "## The guards — always on, whatever the dials say", ""]
    out += ["- **%s** (`%s`) — %s" % (g["name"], g["id"], g["what"]) for g in c["guards"]]
    out += ["", "| Dial | Also called | Lowest | | | | Highest | Default | Medium |",
            "|---|---|---|---|---|---|---|---|---|"]
    for d in c["dials"]:
        cells = [s["name"] for s in sorted(d["scale"], key=lambda s: s["level"])]
        out.append("| **%s** (`%s`) | %s | %s | %s | %s |" % (
            d["name"], d["id"], ", ".join(d["aka"]), " | ".join(cells), d["default"]["level"], ", ".join(d["media"])))
    out.append("")
    for d in c["dials"]:
        out += ["## %s (`%s`)" % (d["name"], d["id"]), "",
                "%s _Applies to: %s._" % (d["what"], ", ".join(d["media"])), "",
                "**Where it comes from.** %s" % d["framework"], "",
                "| Level | Name | What it looks like |", "|---|---|---|"]
        out += ["| %s | %s | %s |" % (s["level"], s["name"], s["what"]) for s in d["scale"]]
        out += ["", "- **In copy:** %s" % d["copy"], "- **In video:** %s" % d["video"],
                "- **In a picture:** %s" % d["image"],
                "- **Default:** %s — %s" % (d["default"]["level"], d["default"]["why"]),
                "- **Risk:** %s" % d["risk"]]
        if d.get("pairs_with"):
            out.append("- **Pairs with:** %s" % ", ".join("`%s`" % x for x in d["pairs_with"]))
        if d.get("humor_values"):
            out.append("- **Humor kinds (marketing-doctrine delivery dial):** %s" % ", ".join("`%s`" % x for x in d["humor_values"]))
        out += ["- **Research:** %s" % _cites(d["research"]), ""]
    if c.get("bar"):
        out += ["## The bar — what maxed looks like", "", c["bar_rule"], ""]
        out += ["- **%s** (`%s`, %s) — %s _Dials: %s._" % (b["name"], b["id"], b["awareness"], b["move"],
                ", ".join("%s %s" % kv for kv in b["dials"].items())) for b in c["bar"]]
        out.append("")
    if c.get("floor"):
        out += ["## The floor — never sterile", "", c["floor"]["what"], "",
                " · ".join("%s at least %s" % kv for kv in c["floor"]["levels"].items()), ""]
    out += ["## Emotions — the named bank", "", c["emotion_rule"], "",
            "| Emotion | Valence | Arousal | What it is | In copy | In video | In a picture |",
            "|---|---|---|---|---|---|---|"]
    out += ["| **%s** (`%s`) | %s | %s | %s | %s | %s | %s |" % (
        e["name"], e["id"], e["valence"], e["arousal"], e["what"], e["copy"], e["video"], e["image"]) for e in c["emotions"]]
    out += ["", "## Techniques — switches, used or not", "", c["technique_rule"], ""]
    fams = []
    for t in c["techniques"]:
        if t["family"] not in fams:
            fams.append(t["family"])
    for f in fams:
        out += ["### %s" % f, ""]
        for t in c["techniques"]:
            if t["family"] == f:
                aka = " — also called %s" % ", ".join(t["aka"]) if t["aka"] else ""
                out.append("- **%s** (`%s`)%s. %s _Source: %s_" % (t["name"], t["id"], aka, t["what"], t["source"]))
        out.append("")
    out += render_story(c)
    out += ["## How the dials pull on each other", ""]
    out += ["- **%s** %s _(%s)_" % (r["id"], r["rule"], r["source"]) for r in c["interactions"]]
    out += ["", "## Presets — starting points a chain may load", ""]
    out += ["- **%s** (`%s`) — %s %s" % (p["name"], p["id"], p["what"], " · ".join(
        "%s %s" % (k, v) for k, v in p["levels"].items())) for p in c["presets"]]
    return "\n".join(out).rstrip("\n") + "\n"


def arcs_for(awareness):
    """The arcs that fit an awareness level (a marketing-doctrine awareness id), in bank order."""
    return [a for a in load().get("arcs") or [] if awareness in a["best_for"]]


def section_plan(arc_id):
    """An arc's beats as the section plan a writer fills: [{beat, section}], in order. Unknown arc -> KeyError."""
    for a in load().get("arcs") or []:
        if a["id"] == arc_id:
            return [dict(b) for b in a["beats"]]
    raise KeyError("no arc %r; arcs: %s" % (arc_id, ", ".join(a["id"] for a in load().get("arcs") or [])))


def render_story(c):
    """The story layer (2026-10-28): arcs, story devices, persuasion triggers, the edge line."""
    if not c.get("arcs"):
        return []
    out = ["## Story arcs — the shape of the piece", "", c["arc_rule"], ""]
    for a in c["arcs"]:
        aka = " — also called %s" % ", ".join(a["aka"]) if a["aka"] else ""
        out += ["### %s (`%s`)%s" % (a["name"], a["id"], aka), "",
                "**What it is:** %s **Best for:** %s." % (a["what"], ", ".join(a["best_for"])), "",
                "**How it works:** %s" % a["how"], "",
                "**Beats → sections:** %s" % " → ".join("%s (`%s`)" % (b["beat"], b["section"]) for b in a["beats"]), "",
                "_Source: %s_" % a["source"], ""]
    out += ["## Story devices — switches inside the arc", "", c["device_rule"], ""]
    fams = []
    for d in c["story_devices"]:
        if d["family"] not in fams:
            fams.append(d["family"])
    for f in fams:
        out += ["### %s" % f, ""]
        for d in c["story_devices"]:
            if d["family"] == f:
                aka = " — also called %s" % ", ".join(d["aka"]) if d["aka"] else ""
                out.append("- **%s** (`%s`)%s. %s **How:** %s _Source: %s_" % (
                    d["name"], d["id"], aka, d["what"], d["how"], d["source"]))
        out.append("")
    out += ["## Persuasion triggers — why the story turns into a click", "", c["trigger_rule"], "",
            "| Trigger | What it is | How it is used | The line | Source |", "|---|---|---|---|---|"]
    out += ["| **%s** (`%s`) | %s | %s | %s | %s |" % (t["name"], t["id"], t["what"], t["how"], t["line"], t["source"])
            for t in c["persuasion_triggers"]]
    e = c["edge_line"]
    out += ["", "## The edge — how far, and where it stops", "", e["what"], "", "**Push:**", ""]
    out += ["- %s" % x for x in e["push"]]
    out += ["", "**Never:**", ""] + ["- %s" % x for x in e["never"]] + ["", "_Source: %s_" % e["source"], "",
                                                                         "## How the story pulls on the dials", ""]
    out += ["- **%s** %s _(%s)_" % (r["id"], r["rule"], r["source"]) for r in c["story_interactions"]]
    return out + [""]


def render_glossary(g):
    out = [HEAD, "", "# The creative glossary", "", g["what"], "", "_Source:_ %s" % g["source"], ""]
    doms = []
    for t in g["terms"]:
        if t["domain"] not in doms:
            doms.append(t["domain"])
    for dm in doms:
        out += ["## %s" % dm, "", "| Term | What it means | Medium | Checked | In the controls |", "|---|---|---|---|---|"]
        out += ["| **%s** | %s | %s | %s | %s |" % (t["term"], t["what"].replace("|", "/"), t["media"], t["checked"],
                                                  "yes" if t["in_the_controls"] else "new to us")
                for t in g["terms"] if t["domain"] == dm]
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def rendered():
    return {SLICE: render_slice(load()), GLOSSARY_MD: render_glossary(json.loads(GLOSSARY.read_text()))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["render"])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    files = rendered()
    if a.check:
        stale = [p.name for p, t in files.items() if not p.is_file() or p.read_text() != t]
        for s in stale:
            print("stale: %s" % s)
        return 1 if stale else 0
    for p, t in files.items():
        p.parent.mkdir(exist_ok=True)
        p.write_text(t)
    print("rendered %s" % ", ".join(str(p.relative_to(HERE)) for p in files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
