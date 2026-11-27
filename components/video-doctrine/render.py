#!/usr/bin/env python3
"""Render every slice in slices/ from frameworks.json.

    python3 components/video-doctrine/render.py [--check]

frameworks.json is the truth. The slices are what a prompt binds. Never
hand-edit a slice: edit the JSON and run this. --check exits 1 if a slice on
disk differs from what the JSON renders.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JSON_PATH = HERE / "frameworks.json"
SLICES = HERE / "slices"
HEAD = "<!-- rendered from components/video-doctrine/frameworks.json by render.py — do not hand-edit -->"
TAIL = "These are defaults. The swipe's own read wins over a default, and the video rulings win over this slice."


def _open(title, var, rule):
    return [HEAD, "", "# %s" % title, "", "Bound as `{%s}`." % var, "", rule, ""]


def _groups(d, block, title, var):
    b = d[block]
    out = _open(title, var, b["rule"])
    for g in b["groups"]:
        out += ["## %s" % g["name"], "", "| Term | What it does |", "|---|---|"]
        out += ["| %s | %s |" % (r["name"], r["job"]) for r in g["rows"]]
        out += ["", "Source: %s" % d["sources"][g["ref"]], ""]
    return out + [TAIL, ""]


def consistency(d):
    b = d["consistency"]
    out = _open("Consistency", "consistency", b["rule"]) + ["| Paper | What it locks |", "|---|---|"]
    out += ["| %s | %s |" % (r["name"], r["job"]) for r in b["rows"]]
    return out + ["", TAIL, ""]


def shapes(d):
    b = d["shapes"]
    out = _open("Video shapes", "video_shapes", b["rule"])
    out += ["| Format | Kind | Shots | Camera | Cutting | Sound | Protect |", "|---|---|---|---|---|---|---|"]
    out += ["| %(format)s | %(kind)s | %(shots)s | %(camera)s | %(cutting)s | %(sound)s | %(protect)s |" % r for r in b["rows"]]
    return out + ["", TAIL, ""]


def shot_brief(d):
    b = d["shot_brief"]
    out = _open("The shot brief", "shot_brief", b["rule"]) + ["```"]
    out += ["%s: [%s]" % (r["slot"], r["asks"]) for r in b["lines"]]
    return out + ["```", "", "Source: %s" % d["sources"][b["ref"]], "", TAIL, ""]


def render_all(d):
    return {
        "shot-language.md": _groups(d, "shot_language", "Shot language", "shot_language"),
        "look.md": _groups(d, "look", "Light and color", "look"),
        "staging.md": _groups(d, "staging", "Blocking and continuity", "staging"),
        "cutting.md": _groups(d, "cutting", "Pacing and sound", "cutting"),
        "consistency.md": consistency(d),
        "video-shapes.md": shapes(d),
        "shot-brief.md": shot_brief(d),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    d = json.loads(JSON_PATH.read_text())
    bad = []
    SLICES.mkdir(exist_ok=True)
    for name, lines in render_all(d).items():
        text = "\n".join(lines)
        f = SLICES / name
        if a.check:
            if not f.is_file() or f.read_text() != text:
                bad.append(name)
        else:
            f.write_text(text)
    if bad:
        print("drifted: " + ", ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
