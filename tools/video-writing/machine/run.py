#!/usr/bin/python3
"""Video writing — station 2 of the four (teardown · writing · production · edit).

    python3 tools/video-writing/machine/run.py <teardown run> [--allow-new-format] [--sandbox]
        [--piece <new label>] [--owner-script <locked script.md>]

<teardown run> is a teardown working folder (runs/video-teardown/_work/<label>/) or just its
label. The teardown must have finished stages 0 → 2 on a route; this writes stages 3 → 5 (v2:
injection, reading + hooks, placement + expansion + close, audit, spice, brief) into the same
run folder, where production and the shelves read them exactly as before.

--piece <label> starts a NEW piece from a finished teardown (2026-10-23): the teardown's record is copied into
runs/video-teardown/_work/<label>/ and its frames and video are linked, never torn down again; the writing then
runs in the new folder. --owner-script locks the owner's own script into the writing: every pass carries its lines
verbatim and the brief is held if one is missing (writing_v2.py, "the owner's locked script").

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
          "poster.jpg", "source.gemini-uri.json", "doctrine.json", "research")


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
    st = json.loads((src / "run.json").read_text())
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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    argv[0] = str(resolve(argv[0]))
    if "--piece" in argv:
        i = argv.index("--piece")
        label = argv[i + 1]
        del argv[i:i + 2]
        argv[0] = str(fork(argv[0], label))
        print("piece:", argv[0])
    os.environ.setdefault("DISABLE_PROMPT_CACHING", "1")
    sys.path.insert(0, str(HERE))
    import writing_v2
    sys.argv = [str(HERE / "writing_v2.py")] + argv
    return 0 if writing_v2.main() else 1      # stopped or held short of a brief -> non-zero


if __name__ == "__main__":
    sys.exit(main())
