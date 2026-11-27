#!/usr/bin/python3
"""Video writing — station 2 of the four (teardown · writing · production · edit).

    python3 components/video-writing/machine/run.py <teardown run> [--allow-new-format] [--sandbox]
        [--revalidate] [--piece <new label> [--fork-only]] [--autonomous] [--owner-script <locked script.md>] [--ask <ask.json | ask name>]

<teardown run> is a teardown working folder (runs/video-teardown/_work/<label>/) or just its
label. The teardown must have finished stages 0 → 2 on a route; this writes stages 3 → 5 (v2:
injection, reading + hooks, placement + expansion + close, audit, spice, brief) into the same
run folder, where production and the shelves read them exactly as before.

--piece <label> starts a NEW piece from a finished teardown (2026-10-23): the teardown's record is copied into
runs/video-teardown/_work/<label>/ and its frames and video are linked, never torn down again; the writing then
runs in the new folder. --owner-script locks the owner's own script into the writing: every pass carries its lines
verbatim and the brief is held if one is missing (writing_v2.py, "the owner's locked script").
--fork-only (with --piece) makes the new piece's folder and stops before any writing (2026-11-27): a continuation's
creative matrix row is pinned into that folder (creative_matrix.py cell) before its writing runs, or the writing
picks a new row (micro-drama series layer, video-production formats/recipes/drama-series-v1.md).
--autonomous runs the writing with the decision layer on for this run only (2026-11-27, owner: "i need this process to be
autonomous"): every structure, hook, audit, swipe-match and manifest hold is decided by video-teardown decide.py from
the owner's past calls, filed in runs/decisions/calls.jsonl for him to agree with or overrule, and the run continues.
It sets VT_CHAIN=v2 (the layer's switch; only the mini's door set it before) and points OUTLIER_SETTINGS at a copy of
the house settings in the run folder with teardown and writing on auto and the master pause off for this run alone.
Nothing that spends on pictures or clips is touched: production keeps its own stops.
--ask names the creative strategist's ask the piece was ordered with (2026-11-03): its offer lines, never-list and
moment go on top of every pass, and the moment is kept on run.json (writing_v2.py, "the ask this ad was ordered with").
--preset <id | auto> writes the piece in a story preset (2026-11-21, creative-controls story_presets.json): its shape
goes on top of every pass, filled with the brand's own research; --dry files the first prompt as sent and calls nothing.

The teardown can also hand off by itself: video-teardown `run.py <video> ... --writing v2`
loads writing_v2.py from this folder when it reaches stage 3.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD = HERE.parents[1] / "video-teardown" / "machine"


def resolve(arg):
    """A folder path, or a label under the teardown's working folder -> the run folder."""
    p = Path(arg)
    if p.is_dir() and (p / "run.json").is_file():
        return p.resolve()
    sys.path.insert(0, str(TD))
    import chain as C
    d = C.runs_root(create=False) / p.name
    if (d / "run.json").is_file():
        return d
    raise SystemExit("no teardown run at %s or %s — run the teardown first" % (p, d))


TEARDOWN_STAGES = ("stage0", "stage1", "stage1b", "stage1c", "stage1k", "stage2")
LINKED = ("framemap", "source.mp4", "audio", "music", "transcript.json", "sound-sheet.json", "sound-sheet.md",
          "poster.jpg", "source.gemini-uri.json", "doctrine.json", "research", "lips.json")


def fork(src, label):
    """A new piece from a finished teardown: the record copied, the heavy media linked, the writing empty."""
    import json
    import shutil
    from datetime import datetime, timezone
    src = Path(src)
    dst = src.parent / label
    if (dst / "run.json").is_file():
        return dst                                  # already started: resume it, never overwrite
    dst.mkdir(parents=True)
    from writing_result import child_state
    st = child_state(json.loads((src / "run.json").read_text()), src.name)
    keep = {k: v for k, v in (st.get("stages") or {}).items() if k in TEARDOWN_STAGES and v.get("status") == "done"}
    for rec in keep.values():
        for f in (rec.get("out"), rec.get("sent")):
            if f and (src / f).is_file():
                (dst / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / f, dst / f)
    for name in LINKED:
        if (src / name).exists():
            os.symlink((src / name).resolve(), dst / name)
    for k in ("writing", "writing_v2_calls", "writing_v2_total", "owner_script", "owner_words_check", "story", "role",
              "reference_for", "viewer_check", "missed_checks", "_order"):
        st.pop(k, None)
    st.update(label=label, slug=label, stages=keep, forked_from=str(src.name),
              opened=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    (dst / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return dst


def autonomous(run_dir):
    """This run's writing decides its own holds (decide.py); the house settings file is never changed."""
    import json
    os.environ["VT_CHAIN"] = "v2"
    os.environ["VT_AUTO"] = "1"
    house = HERE.parents[2] / "runs" / "settings" / "settings.json"
    try:
        cfg = json.loads(house.read_text())
    except (OSError, ValueError):
        cfg = {}
    auto = dict(cfg.get("automation") or {}, paused=False, teardown="auto", writing="auto")
    cfg["automation"] = auto
    mine = Path(run_dir) / "autonomy-settings.json"
    mine.write_text(json.dumps(cfg, indent=1) + "\n")
    os.environ["OUTLIER_SETTINGS"] = str(mine)
    print("autonomous: holds go to the decision layer (runs/decisions/calls.jsonl); the run continues")
    return mine


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    argv[0] = str(resolve(argv[0]))
    if "--revalidate" in argv and "--piece" in argv:
        raise SystemExit("--revalidate checks an existing piece; do not combine it with --piece")
    if "--piece" in argv:
        i = argv.index("--piece")
        label = argv[i + 1]
        del argv[i:i + 2]
        argv[0] = str(fork(argv[0], label))
        print("piece:", argv[0])
        if "--fork-only" in argv:
            print("forked only: pin its creative matrix row, then run.py %s [--story <story.md>]" % label)
            return 0
    elif "--fork-only" in argv:
        raise SystemExit("--fork-only needs --piece <new label>")
    if "--autonomous" in argv:
        argv.remove("--autonomous")
        autonomous(Path(argv[0]))
    os.environ.setdefault("DISABLE_PROMPT_CACHING", "1")
    sys.path.insert(0, str(HERE))
    import writing_v2
    sys.argv = [str(HERE / "writing_v2.py")] + argv
    return 0 if writing_v2.main() else 1      # stopped or held short of a brief -> non-zero


if __name__ == "__main__":
    sys.exit(main())
