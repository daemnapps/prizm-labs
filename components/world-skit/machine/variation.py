#!/usr/bin/env python3
"""variation.py: a new world-skit mission, as one simple request. Fill a mission file; words that did not change reuse their voice, so a variation pays only for its new lines.

    python3 variation.py plan <mission.json>        every changed line, what it costs, spends nothing
    python3 variation.py make <mission.json>        voices the new lines, checks the script, renders, checks the result
    python3 variation.py handoff <mission.json>     files it as a brief for the video editor

A mission file: {"label", "brand", "from": <finished video-edit run>, "cap_usd", "headline", "problem", "place", "lines": {id: words}, "tags": {id: delivery}}.
`from` is the sequence to reuse. The run is written to runs/video-edit/<brand>/<label>/. No brand is named here."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
USD_PER_1K = 0.30      # the voice door's rate, close to what the first skit cost
LINKS = ("3d", "product", "sfx", "ba", "voices", "hooks.py")
LOW = ROOT / "components/video-edit/lowpoly/lowpoly.py"


def load(path):
    m = json.loads(Path(path).read_text())
    src = ROOT / m["from"]
    return m, src, ROOT / "runs/video-edit" / m["brand"] / m["label"]


def changed(m, src):
    lines = json.loads((src / "lines.json").read_text())
    return {k: v for k, v in m.get("lines", {}).items() if lines.get(k) != v}


def plan(path):
    m, src, run = load(path)
    new = changed(m, src)
    chars = sum(len(v) for v in new.values())
    usd = chars / 1000 * USD_PER_1K
    who = {s["id"]: s["speaker"] for s in json.loads((src / "plan.json").read_text())["scenes"]}
    for k, v in new.items():
        print("%-5s %-4s %s" % (k, who.get(k, "?"), v))
    print("%d new lines · %d characters · about $%.2f · stop price $%.2f · render free" % (len(new), chars, usd, float(m["cap_usd"])))
    return usd <= float(m["cap_usd"]), usd


def make(path):
    ok, usd = plan(path)
    if not ok:
        raise SystemExit("over the stop price: nothing spent")
    m, src, run = load(path)
    run.mkdir(parents=True, exist_ok=True)
    for f in LINKS:
        if not (run / f).exists() and (src / f).exists():
            os.symlink(src / f, run / f)
    if not (run / "voice").exists():
        shutil.copytree(src / "voice", run / "voice")
    lines = json.loads((src / "lines.json").read_text())
    pl = json.loads((src / "plan.json").read_text())
    who = {s["id"]: s for s in pl["scenes"]}
    new = changed(m, src)
    done = json.loads((run / "lines.json").read_text()) if (run / "lines.json").exists() else {}
    lines.update(new)
    for k in new:
        who[k]["delivery_tag"] = m.get("tags", {}).get(k, who[k]["delivery_tag"])
    (run / "lines.json").write_text(json.dumps(lines, indent=1))
    (run / "plan.json").write_text(json.dumps(pl, indent=1))
    (run / "run.json").write_text(json.dumps({"brand": m["brand"]}))
    fresh = {k: v for k, v in new.items() if done.get(k) != v}   # a rerun never pays for a read it already has
    for speaker in sorted({who[k]["speaker"] for k in fresh}):
        tmp = run / ("_v_" + speaker)
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        ids = [k for k in fresh if who[k]["speaker"] == speaker]
        (tmp / "run.json").write_text(json.dumps({"brand": m["brand"]}))
        (tmp / "lines.json").write_text(json.dumps({k: new[k] for k in ids}))
        (tmp / "plan.json").write_text(json.dumps({"cast": {"name": speaker}, "scenes": [who[k] for k in ids]}))
        subprocess.run([sys.executable, str(ROOT / "components/video-production/machine/voice.py"), str(tmp), "--per-line", "--character", speaker, "--cast-root", str(run / "voices")], check=True)
        for f in (tmp / "voice").glob("*.mp3"):
            shutil.copy(f, run / "voice" / f.name)
    ad = json.loads((src / "ad.json").read_text())
    ad["headline"] = m["headline"]
    ad["bleeps"] = []
    ad.update(m.get("ad", {}))
    (run / "ad.json").write_text(json.dumps(ad))
    subprocess.run([sys.executable, str(LOW), "track", str(run)], check=True)
    check = subprocess.run([sys.executable, str(HERE / "script_check.py"), str(run), "--problem", m["problem"], "--place", m["place"]], capture_output=True, text=True)
    print(check.stdout)
    report = {"script_faults": [x for x in check.stdout.splitlines() if x.startswith("FAULT")], "voice_usd_estimate": round(usd, 3)}
    (run / "check.json").write_text(json.dumps(report, indent=1))
    if report["script_faults"] and not m.get("force"):
        raise SystemExit("script check failed: fix the mission, nothing rendered")
    sys.path.insert(0, str(ROOT / "components/video-teardown/machine"))
    import transcript as tr
    words = tr.scribe_only(run / "vo" / "track.mp3")["words"]
    (run / "vo" / "words.json").write_text(json.dumps(words))
    marks, keys = [], [k for k in ad.get("mask", {})]
    for w in words:
        if any(k in w.get("text", "").lower() for k in keys):
            marks.append({"at": round(w["start"] - .02, 3), "to": round(w["end"] + .02, 3)})
    ad["bleeps"] = marks
    (run / "ad.json").write_text(json.dumps(ad))
    subprocess.run([sys.executable, str(LOW), "render", str(run)], check=True)
    subprocess.run([sys.executable, str(HERE / "check.py"), "listen", str(run)], check=True)


def handoff(path):
    m, src, run = load(path)
    key = "%s_%s" % (m["brand"], m["label"])
    home = ROOT / "runs/handoffs/video-editor" / m["brand"] / key
    (home / "returned").mkdir(parents=True, exist_ok=True)
    (home / "refs").mkdir(exist_ok=True)
    lines = json.loads((run / "lines.json").read_text())
    ad = json.loads((run / "ad.json").read_text())
    who = {s["id"]: s["speaker"] for s in json.loads((run / "plan.json").read_text())["scenes"]}
    script = "\n".join("%s: %s" % (who[r["id"]].title(), lines[r["id"]]) for r in ad["timeline"] if r["id"] in lines)
    (home / "BRIEF.md").write_text("# %s\n\nA world-skit variation, finished draft attached on the Drive at runs/video-edit/%s/%s/final.mp4.\n\nTop text: %s\n\n## Script\n\n%s\n\n## The job\n\nCut against the finished draft: tighten the joke timing, listen to the mix, return the master to returned/.\n" % (m["label"], m["brand"], m["label"], m["headline"], script))
    (home / "run.json").write_text(json.dumps({"label": m["label"], "brand": m["brand"], "from": m["from"], "kind": "world-skit"}, indent=1))
    print(home)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("plan", "make", "handoff"):
        raise SystemExit(__doc__)
    {"plan": plan, "make": make, "handoff": handoff}[sys.argv[1]](sys.argv[2])
