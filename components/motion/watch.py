#!/usr/bin/env python3
"""The watcher: the preview looked at, not only measured (the chain's own eyes on a rehearsal before a take is paid for).

    python3 watch.py <motion dir>

The measured rows (match.py) compare numbers read off two tracks. They cannot see what neither track holds: a person
the tracker never followed, a limb drawn where no limb is, a figure sliding at a cut. This sends preview.mp4 (the real
footage, its skeleton and the 3D rehearsal side by side) to the house's video judge with prompts/motion-watch.md and
keeps its answer as verdict.json: per shot whether the people are placed and sized as the footage and whether the
shot's move happens, each fault with when and how much it matters, and two plain sentences. The verdict is worked out
from the per-shot answers: a shot whose move does not happen, or whose people are misplaced or the wrong size, makes it
"not yet" (`holds`), and motion_chain's own decision holds that rehearsal; limb faults are kept and do not hold. Every call is kept: motion-watch.sent.json, motion-watch.answer.json. No brand, product or person is
named here.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read as RD  # noqa: E402

PROMPT = HERE / "prompts" / "motion-watch.md"
VERDICTS = ("true to the footage", "close, small faults", "not yet")


def watch(motion_dir):
    d = Path(motion_dir)
    clip = d / "preview.mp4"
    if not clip.exists():
        raise SystemExit("no preview to watch here (%s)" % clip)
    ref = json.loads((d / "ref.json").read_text()) if (d / "ref.json").exists() else {}
    read = json.loads((d / "motion-read.json").read_text()) if (d / "motion-read.json").exists() else {}
    rows = json.loads((d / "match-rehearsal.json").read_text()) if (d / "match-rehearsal.json").exists() else {}
    cuts = [s["from"] for s in (read.get("shots") or [])[1:]] or ref.get("cuts") or []
    failed = "; ".join("%s (%s)" % (r["name"], r["short"]) for r in rows.get("rows") or [] if r["ok"] is False) or "none"
    text = PROMPT.read_text().replace("{seconds}", "%.1f" % float(read.get("seconds") or ref.get("seconds") or RD._seconds(clip))).replace(
        "{cuts}", (", with cuts at %s s" % ", ".join("%.2f" % c for c in cuts)) if cuts else ", in one shot").replace(
        "{people}", ", ".join("%s (%s)" % (p["ours"], p.get("role") or "in the shot") for p in read.get("people") or []) or "as the footage shows").replace("{failed}", failed)
    (d / "motion-watch.sent.json").write_text(json.dumps({"prompt": text, "clip": clip.name, "models": RD.models(),
                                                          "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1, ensure_ascii=False))
    answer, how = RD.ask(text, clip)
    (d / "motion-watch.answer.json").write_text(json.dumps({"answer": answer, "by": how}, indent=1, ensure_ascii=False))
    got = RD._json(answer, "the watcher")
    if isinstance(got, list):                           # some answers come back wrapped in a list
        got = got[0] if got and isinstance(got[0], dict) else {}
    if not isinstance(got, dict):
        raise SystemExit("the watcher answered with no object: " + answer[:200])
    shots = [x for x in got.get("shots") or [] if isinstance(x, dict)]
    faults = [f for f in got.get("faults") or [] if isinstance(f, dict) and f.get("what")]
    # The verdict is worked out from what the watcher answered shot by shot, not from its own one-word verdict (which
    # calls every clipped mitten "not yet"): a shot whose move does not happen, or whose people are in the wrong place
    # or the wrong size, holds the rehearsal; limb faults are kept as faults and do not.
    holds = ["shot %s: %s" % (x.get("shot"), "the move does not happen as in the footage" if x.get("move_matches") is False else
                              "the stand-ins are not where the real people are" if x.get("placed") is False else "the stand-ins read the wrong size")
             + ((" (%s)" % str(x.get("saw")).rstrip(".")) if x.get("saw") else "")
             for x in shots if x.get("move_matches") is False or x.get("placed") is False or x.get("sized") is False]
    verdict = "not yet" if holds or not shots else ("close, small faults" if faults or any(x.get("limbs_plausible") is False for x in shots) else "true to the footage")
    rec = {"verdict": verdict, "usable": verdict != "not yet", "holds": holds, "watcher_said": got.get("verdict"), "summary": got.get("summary", ""),
           "faults": faults, "shots": shots,
           "checked": "the chain's own watcher (the house's video judge, %s) on preview.mp4" % how.get("model"),
           "watched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (d / "verdict.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = watch(sys.argv[1])
    print(r["verdict"])
    for f in r["faults"]:
        print(" - %s | %s | %s" % (f.get("matters"), f.get("at"), f.get("what")))
    print(r["summary"])
