#!/usr/bin/env python3
"""File a run's WORDS to the repo's one home for run records.

    python3 file_run.py                  every finished run on this machine
    python3 file_run.py <run-label>      one run

    runs/video-teardown/<brand>/<slug>/     station 1 — the Teardown Record
        run.json  transcript.json  sound-sheet.*  doctrine.json  elements.json
        post-talk.json
        stages/ + prompts/ 0-* 1-* 1k-* 1c-* 2-*
    runs/video-writing/<brand>/<slug>/      station 2 — our version
        run.json  RULINGS.md  swipe-match.json  manifest.json  deliverable/
        stages/ + prompts/ every other stage (1b, 3, 4a-4g, 5, 7, 7b, 8 …)

One run, two shelves, one slug (the owner, 2026-09-30: "naming needs to be lined
up cleanly across all the tools so we don't have confusion on where things are
and what tools did what"). The teardown shelf holds what was READ off the
swipe and nothing brand-written; the writing shelf holds everything written
for a brand. A teardown-only run (no route picked) has no writing shelf.

`runs/README.md` (the developer, 2026-09-16): a machine's record must not live beside
its code, because code moves. This machine's working copy lives in
`runs/video-teardown/_work/<slug>/` (SI-56, 2026-10-08; gitignored, named in
workdir.py), read by the board, mirrored to the Drive. This is one more copy,
of the text only.

TEXT ONLY, ALWAYS: never the source video, a poster, a frame, the Doc's HTML,
or anything over 1 MB. Media lives on the Drive (workspace rule 3).

It never deletes and never fails a run: run.py wraps it like every other
end-of-run step, so a problem here prints SKIPPED and the run is still whole.

Switch it off: `VT_NO_REPO_FILING=1` in the environment.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
sys.path.insert(0, str(MACHINE))
import chain as C                                            # noqa: E402
import workdir                                               # noqa: E402

TOOL = "video-teardown"
WRITING_TOOL = "video-writing"
OFF_ENV = "VT_NO_REPO_FILING"
MAX_BYTES = 1_000_000
TOP_FILES = ("run.json", "doctrine.json", "elements.json",
             "RULINGS.md", "transcript.json", "swipe-match.json", "manifest.json",
             "sound-sheet.json", "sound-sheet.md",  # + the owner's rulings and the checks (2026-09-25)
             "post-talk.json")  # the post's caption and comments the culture read used (2026-10-05)
WRITING_TOP = {"RULINGS.md", "swipe-match.json", "manifest.json"}
TEARDOWN_STAGE = re.compile(r"^(0|1|1k|1c|2)-")   # triage, record, culture read, doctrine read, spec


def shelf(rel):
    """Which station a filed file belongs to: TOOL or WRITING_TOOL (run.json: both)."""
    rel = Path(rel)
    if rel.parts[0] == "framemap":
        return TOOL
    if rel.parts[0] in TEXT_FOLDERS:
        return TOOL if TEARDOWN_STAGE.match(rel.name) else WRITING_TOOL
    return WRITING_TOOL if rel.name in WRITING_TOP else TOOL
TEXT_FOLDERS = ("stages", "prompts")
FRAMEMAP_FILES = ("framemap/framemap.json", "framemap/FRAME-MAP.md")   # the swipe, shot by shot (2026-10-01)
# + the index of the elements cut from the frames (2026-10-08) — its TEXT only;
# the frames, crops and clips stay in runs/video-teardown/_work/ (ignored) and on the Drive
FRAMEMAP_FILES += ("framemap/elements/index.json",)
TEXT_SUFFIX = ".md"


def _safe(s):
    return re.sub(r"[^a-z0-9-]+", "-", str(s or "").lower()).strip("-")


def home(brand, slug, repo=None, tool=TOOL):
    """<repo>/runs/<tool>/<brand>/<slug>/ — the repo FOUND by walking
    up (chain.workspace), never counted."""
    repo = Path(repo) if repo else C.workspace()
    return repo / "runs" / tool / _safe(brand) / _safe(slug)


def _wanted(run_dir):
    run_dir = Path(run_dir)
    for name in TOP_FILES:
        f = run_dir / name
        if f.is_file():
            yield f, Path(name)
    for name in FRAMEMAP_FILES:
        f = run_dir / name
        if f.is_file():
            yield f, Path(name)
    for folder in TEXT_FOLDERS:
        d = run_dir / folder
        if d.is_dir():
            for f in sorted(d.glob("*" + TEXT_SUFFIX)):
                if f.is_file():
                    yield f, Path(folder) / f.name


def file_run(run_dir, repo=None):
    """Copy one run's text to the repo-root runs/ home.
    -> (dest, copied, left_out). Raises on a run with no brand — the brand IS
    the filing key, and a guessed one would file the record under the wrong
    shelf."""
    run_dir = Path(run_dir)
    st = json.loads((run_dir / "run.json").read_text())
    brand = _safe(st.get("brand"))
    if not brand:
        raise ValueError(f"{run_dir.name}: run.json names no brand, so there "
                         "is no shelf to file it on")
    slug = st.get("slug") or run_dir.name
    dest = home(brand, slug, repo)
    wdest = home(brand, slug, repo, WRITING_TOOL)
    wanted = list(_wanted(run_dir))
    wrote_any = any(shelf(rel) == WRITING_TOOL for _, rel in wanted)
    copied, left_out = [], []
    for src, rel in wanted:
        if src.stat().st_size > MAX_BYTES:
            left_out.append(f"{rel} (over 1 MB)")
            continue
        try:
            src.read_text(encoding="utf-8")          # text, or it does not go
        except (UnicodeDecodeError, OSError):
            left_out.append(f"{rel} (not text)")
            continue
        targets = ([dest, wdest] if rel.name == "run.json" and wrote_any
                   else [wdest if shelf(rel) == WRITING_TOOL else dest])
        for base in targets:
            out = base / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            if not out.is_file() or out.read_bytes() != src.read_bytes():
                shutil.copyfile(src, out)
        copied.append(str(rel))
    # The brief production takes is refreshed on EVERY filing, by any door
    # (2026-10-01: a corrected brief was filed by hand and deliverable/ kept
    # the old one, so production would have read the brief the owner never saw).
    for name in ("7-final-brief.md", "5-brief.md"):
        src = wdest / "stages" / name
        if src.is_file():
            (wdest / "deliverable").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, wdest / "deliverable" / name)
            break
    return dest, copied, left_out


def number_brief(run_dir, dest):
    """Give a filed AI-route brief its brief number (tools/image-teardown/tools/briefs.py `open`,
    type video-ai), then write it into both filed run.json copies. A run that already has a number keeps it;
    a creator-route brief is numbered by its own lane, not here. -> the number, or None."""
    import subprocess
    st = json.loads((Path(run_dir) / "run.json").read_text())
    if st.get("production_route") != "ai" or st.get("brief"):
        return st.get("brief")
    brand, slug = _safe(st.get("brand")), st.get("slug") or Path(run_dir).name
    wdest = Path(str(dest).replace(f"/runs/{TOOL}/", f"/runs/{WRITING_TOOL}/"))
    if not (wdest / "deliverable").is_dir() and not (Path(dest) / "stages" / "5-brief.md").is_file():
        return None                         # no finished brief yet: numbers are for briefs, not runs in progress
    ws = C.workspace()
    cmd = [sys.executable, str(ws / "tools/image-teardown/tools/briefs.py"), "open", slug,
           "--brand", brand, "--type", "video-ai"]
    if st.get("product"):
        cmd += ["--product", str(st["product"])]
    subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=120)
    number = (json.loads((Path(dest) / "run.json").read_text()) if (Path(dest) / "run.json").is_file() else {}).get("brief")
    if number:
        for rj in (Path(run_dir) / "run.json", wdest / "run.json"):
            if rj.is_file():
                m = json.loads(rj.read_text())
                if m.get("brief") != number:
                    m["brief"] = number
                    rj.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
    return number


def file_after_run(run_dir, repo=None):
    """The end-of-run call. -> a one-line note, or None when switched off."""
    if os.environ.get(OFF_ENV):
        return None
    # Only a run in the machine's REAL runs folder reaches the repo's record.
    # Tests and scratch runs point the runs root at a temp folder; they must
    # never be able to write into runs/video-teardown/ (2026-09-18: a test
    # that touched live runs cost a real one, four times).
    if repo is None and \
            Path(run_dir).resolve().parent != workdir.root(C.WS).resolve():
        return None
    dest, copied, left_out = file_run(run_dir, repo)
    # THE BRIEF GOES WHERE THE STANDARD SAYS. runs/README.md has said since
    # 2026-09-17 that the thing a person traffics lives in `deliverable/`; an
    # index over every run on 2026-09-23 found 198 runs and three briefs
    # actually filed there. A consumer that wants "the brief for this run"
    # should not have to know that this machine calls it stages/7-final-brief.md.
    try:
        import shutil
        wdest = Path(str(dest).replace(f"/runs/{TOOL}/", f"/runs/{WRITING_TOOL}/"))
        for name in ("7-final-brief.md", "5-brief.md"):
            src = wdest / "stages" / name
            if src.is_file():
                (wdest / "deliverable").mkdir(exist_ok=True)
                shutil.copy2(src, wdest / "deliverable" / name)
                break
    except Exception:                       # filing is never fatal to a run
        pass
    # THE BRIEF NUMBER IS GIVEN WHEN THE BRIEF IS WRITTEN (the owner, 2026-10-09: "give the brief number the
    # moment it's created"). An AI-route brief gets its brief-NNNN from the register the moment it is filed,
    # so the same number follows it through production, the edit, delivery and the Meta ad name.
    if repo is None:                        # real filings only: a test's temp repo never touches the register
        try:
            number_brief(run_dir, dest)
        except Exception:                   # never fatal to a run
            pass
    # The brief index — one row per brief — is rebuilt with every filing.
    if repo is None:
        try:
            import brief_index as _bi
            _bi.build()
        except Exception:                   # never fatal to a run
            pass
    try:
        shown = dest.relative_to(Path(repo) if repo else C.workspace())
    except ValueError:
        shown = dest
    return (f"{len(copied)} text file(s) → {shown}"
            + (f" · left out: {', '.join(left_out)}" if left_out else ""))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = C.runs_root()
    if argv:
        dirs = [root / C.run_slug(_safe(argv[0]))]
        if not dirs[0].is_dir():
            dirs = [root / argv[0]]
    else:
        dirs = sorted(p for p in root.iterdir()
                      if p.is_dir() and (p / "run.json").is_file())
    n = 0
    for d in dirs:
        try:
            dest, copied, left_out = file_run(d)
            print(f"  {d.name}: {len(copied)} file(s) → {dest}"
                  + (f" · left out: {', '.join(left_out)}" if left_out else ""))
            n += 1
        except Exception as e:
            print(f"  {d.name}: SKIPPED — {e}")
    print(f"{n} run(s) filed under runs/{TOOL}/ and runs/{WRITING_TOOL}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
