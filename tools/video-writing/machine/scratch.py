#!/usr/bin/env python3
"""FROM SCRATCH — a video written from an idea, with no swipe (2026-10-28).

the owner, 2026-10-28: "we're going to actually test creating a song from scratch, doing full writing from scratch" and
"you tell me how this flow should go based on my tools". The writing chain (stages 3 → 5) reads six records a teardown
normally leaves (triage, teardown, audience, doctrine, culture, spec). From scratch there is no swipe, so this door
writes those six from the picks the Story Playbook flow makes, then the writing chain runs unchanged:

    avatar + product      the brand's own files (bound by the chain as {avatar}, {product_file})
    awareness             a marketing-doctrine awareness id: where the ad may begin
    arc                   a creative-controls arc: its beats ARE the section plan (creative_controls.section_plan)
    format + style        a format bank id and its playbook; a style bank id
    the story             our concept file (writing_v2 --story): every beat, person and line comes from it

    python3 tools/video-writing/machine/scratch.py <label> --brand <b> --product <p> --avatar <a>
        --awareness <level> --arc <arc id> --format <format id> --style <style id> --story <concept.md> [--write]

Makes runs/video-teardown/_work/<label>/ (the writing's working folder, where production and the board read it) and,
with --write, runs the writing chain on it. Spends nothing itself; --write spends the writing's model calls.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
sys.path.insert(0, str(WS / "tools" / "video-teardown" / "machine"))
sys.path.insert(0, str(WS / "components" / "creative-controls"))

RECORDS = [  # (stage key, name, file) — the six a teardown leaves, in its order
    ("stage0", "Triage", "0-triage.md"), ("stage1", "Teardown", "1-teardown.md"), ("stage1b", "Audience", "1b-audience.md"),
    ("stage1c", "Doctrine", "1c-doctrine.md"), ("stage1k", "Culture", "1k-culture.md"), ("stage2", "Spec", "2-spec.md")]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(path, key, rid):
    """One row of a bank file (a list, or a dict holding the list), by id."""
    d = json.loads(Path(path).read_text())
    rows = d if isinstance(d, list) else (d.get(key) or d.get("rows") or d.get("items") or [])
    for r in rows:
        if isinstance(r, dict) and r.get("id") == rid:
            return r
    raise SystemExit("%s: no %r — known: %s" % (path, rid, ", ".join(str(r.get("id")) for r in rows if isinstance(r, dict))))


def records(a):
    """The six records, written from the picks. Returns {file: text}."""
    import creative_controls as CC
    doc = json.loads((WS / "components/marketing-doctrine/frameworks.json").read_text())
    level = next((l for l in doc["awareness"]["levels"] if l["id"] == a.awareness), None)
    if not level:
        raise SystemExit("no awareness level %r — known: %s" % (a.awareness, ", ".join(l["id"] for l in doc["awareness"]["levels"])))
    arc = next((x for x in CC.load()["arcs"] if x["id"] == a.arc), None)
    if not arc:
        raise SystemExit("no arc %r — known: %s" % (a.arc, ", ".join(x["id"] for x in CC.load()["arcs"])))
    if a.awareness not in arc["best_for"]:
        print("note: arc %s is not listed for %s (best for %s) — written as asked" % (a.arc, a.awareness, ", ".join(arc["best_for"])))
    secs = {s["id"]: s for s in doc["sections"]}
    fmt = _row(WS / "components/elements/library/format.video.json", "rows", a.format)
    sty = _row(WS / "components/elements/library/style.video.json", "rows", a.style)
    play = WS / "tools/video-production/formats/playbooks" / ("%s.md" % a.format)
    playbook = play.read_text().strip() if play.is_file() else "(no playbook for this format)"
    plan = CC.section_plan(a.arc)
    beats = "\n".join("| %d | %s | %s | %s |" % (i + 1, b["beat"], secs[b["section"]]["name"], secs[b["section"]]["what"])
                      for i, b in enumerate(plan))
    head = ("FROM SCRATCH — there is no swipe. This record is written from the picks (avatar, product, awareness, arc, "
            "format, style) and the story file; read it as the structure to follow, never as a video that was watched.")
    return {
        "0-triage.md": "\n".join([
            "LANE: FROM SCRATCH", "SOUND FORM: %s" % ("SUNG" if a.format == "song-ad" else "SPOKEN"),
            "FORMAT: %s — %s" % (fmt["id"], fmt.get("what") or fmt.get("name")),
            "STYLE: %s — %s" % (sty["id"], sty.get("what") or sty.get("name")),
            "STRUCTURE: %s — %s" % (arc["id"], arc["what"]), "MADE: from-scratch",
            "ONE LINE: written from our own story (story.md); no swipe.", ""]),
        "1-teardown.md": "\n".join([
            "# The structure to follow (from scratch)", "", head, "",
            "## The arc: %s" % arc["name"], "", arc["what"] + " " + arc["how"], "",
            "| # | Beat | Section | What the section does |", "|---|---|---|---|", beats, "",
            "## The format: %s" % fmt.get("name", fmt["id"]), "", playbook, "",
            "## The style: %s" % sty.get("name", sty["id"]), "", sty.get("what") or "", ""]),
        "1b-audience.md": "\n".join([
            "# Audience (declared, from scratch)", "", "AVATAR: %s (the brand's avatar file, bound as {avatar})" % a.avatar,
            "AWARENESS: %s — %s" % (level["name"], level["knows"]),
            "WHERE THE AD MAY BEGIN: %s" % level["where_the_ad_may_begin"],
            "MUST: %s" % "; ".join(level.get("must") or []), "MUST NOT: %s" % "; ".join(level.get("must_not") or []), ""]),
        "1c-doctrine.md": "\n".join([
            "# Doctrine (from scratch)", "", head, "", "AWARENESS: %s" % level["name"],
            "ARC: %s (%s)" % (arc["name"], arc["id"]),
            "SECTIONS, IN ORDER: %s" % " → ".join(secs[b["section"]]["name"] for b in plan),
            "THE CLOSE: after the last beat, as the awareness level asks (offer, call-to-action, urgency where true).", ""]),
        "1k-culture.md": "\n".join([
            "# Culture (from scratch)", "", "No swipe to read. The culture comes from the avatar's culture map "
            "(bound as {culture_map}) and from the story file's own references.", ""]),
        "2-spec.md": "\n".join([
            "### 1. FORMAT", "%s, in the %s style, told as %s." % (fmt.get("name", fmt["id"]), sty.get("name", sty["id"]), arc["name"]), "",
            "### 2. THE STRUCTURAL SKELETON", "", "| Phase | Function | Duration | Fixed position? | Fixed or flexes? |",
            "|---|---|---|---|---|"] + ["| %s | %s | — | Fixed | Flexes |" % (b["beat"], secs[b["section"]]["name"]) for b in plan] + [
            "", "### 3. THE ELEMENT INVENTORY", "",
            "Every element comes from OUR STORY (story.md): its people, its signature details, its lines and its guards. "
            "The skeleton above is the order they are told in.", ""]),
    }


def build(a):
    import chain as C
    d = C.runs_root(create=True) / a.label
    if (d / "run.json").is_file():
        raise SystemExit("%s already exists — pick a new label (a run is never written over)" % d)
    (d / "stages").mkdir(parents=True)
    (d / "prompts").mkdir()                       # the chain files every prompt as sent here
    for f, text in records(a).items():
        (d / "stages" / f).write_text(text)
    now = _now()
    st = {"slug": a.label, "label": a.label, "opened": now, "brand": a.brand, "product": a.product,
          "ran_by": "owner", "venue": "local", "lane": "scratch", "lane_declared": "paid", "chain": "v2",
          "production_route": "ai", "route_chosen_by_hand": True, "style_id": a.style, "format_id": a.format,
          "layers": {"format": a.format, "style": a.style, "structure": a.arc},
          "declared_audience": {"avatar": a.avatar, "sub": None},
          "audience": {"_avatar": a.avatar, "_funnel": "prospect", "_sub_avatar": None},   # what stage 1b leaves; the
                                                                                            # brand map reads the avatar from it
          "scratch": {"awareness": a.awareness, "arc": a.arc, "at": now},
          "stages": {k: {"status": "done", "name": n, "out": "stages/" + f, "finished": now, "from": "scratch"}
                     for k, n, f in RECORDS}}
    (d / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    sys.path.insert(0, str(HERE))
    import writing_v2 as W
    W.lock_story(d, a.story)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description="A video written from an idea, with no swipe.")
    ap.add_argument("label")
    for k in ("brand", "product", "avatar", "awareness", "arc", "format", "style", "story"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--write", action="store_true", help="run the writing chain on it now")
    a = ap.parse_args(argv)
    d = build(a)
    print("run:", d)
    if not a.write:
        return 0
    return subprocess.call([sys.executable, str(HERE / "run.py"), str(d)])


if __name__ == "__main__":
    sys.exit(main())
