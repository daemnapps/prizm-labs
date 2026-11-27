#!/usr/bin/env python3
"""The video-editor hand-off checklist: one pack in, every check pass/fail with its evidence out. Reads only.

    python3 components/video-edit/handoff_check.py <brief key or number> [--brand <brand>] [--json]
    python3 components/video-edit/handoff_check.py --all [--brand <brand>] [--json]

A hand-off is ready for the editor only when every line passes. The checks follow the pack the Studio builds
(TIMELINE.html, BRIEF.md, the run sheet, clips.json, ELEMENTS.md, the Premiere timeline, the HyperFrames project, the
voice or song, returned/) and the editor's own door (open_brief.py list / open): a pack the editor's list cannot see,
or cannot open, fails here before anyone waits on it.

Reads the workspace pack (runs/handoffs/video-editor/<brand>/<key>/), its Drive copy (Shared Assets, found the way the
editor's door finds it) and, when VIDEO_STUDIO_DATA is set, the Studio's hand-off records. Writes nothing.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "run-kit"))
import open_brief as OB  # noqa: E402  (the editor's own door: same Drive finder, same list rules)
from run_kit import paths as P  # noqa: E402

ROLE = Path("runs") / "handoffs" / "video-editor"
NEEDS_CLIPS = ("needs clips", "needs clip", "to make")


def _files(root):
    out = {}
    for dp, dn, fn in os.walk(str(root)):
        dn[:] = [d for d in dn if d != "__pycache__" and not d.startswith(".")]
        for f in fn:
            if f.startswith(".") or f.endswith(".tmp"):
                continue
            p = Path(dp) / f
            out[str(p.relative_to(root))] = p.stat().st_size
    return out


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _studio_records():
    data = os.environ.get("VIDEO_STUDIO_DATA")
    if not data:
        return None
    recs = {}
    for p in (Path(data) / "briefs").glob("*/maker-pack.json"):
        r = _json(p)
        if isinstance(r, dict):
            recs[p.parent.name] = r
    return recs


def _drive_root():
    try:
        return OB.shared_assets()
    except SystemExit:
        return None


def check(folder, repo, drive, recs):
    f = Path(folder)
    key, brand = f.name, f.parent.name
    have = _files(f)
    out = []

    def add(group, name, ok, evidence=""):
        out.append({"group": group, "check": name, "ok": bool(ok), "evidence": evidence})

    # the pack
    add("Pack", "Named by its brief number", re.search(r"_brief-\d{4}$", key), key)
    for doc, what in (("BRIEF.md", "Brief"), ("RUN.md", "Run sheet"), ("run.json", "Run sheet data"),
                      ("CLIPS.md", "Clip list"), ("clips.json", "Clip list data"), ("ELEMENTS.md", "Build list"),
                      ("TIMELINE.html", "Timeline page")):
        n = have.get(doc, 0)
        add("Pack", "%s (%s)" % (what, doc), n > 50, ("%d bytes" % n) if n else "missing")
    run_t = (f / "RUN.md").stat().st_mtime if (f / "RUN.md").exists() else 0
    errs = [k for k in have if k.endswith("MISSING.txt") and (f / k).stat().st_mtime > run_t]   # a note older than the run sheet is spent
    add("Pack", "No build errors left in the pack", not errs,
        " · ".join((f / k).read_text(encoding="utf-8", errors="ignore").strip()[:160] for k in errs))

    # the clips
    cj = _json(f / "clips.json")
    scenes = (cj.get("scenes") if isinstance(cj, dict) else cj) or []
    to_make = [s for s in scenes if str(s.get("status", "")).lower() in NEEDS_CLIPS or s.get("clips")]
    add("Clips", "Clip list readable", bool(scenes), "%d scenes, %d with clips to make" % (len(scenes), len(to_make)))
    ref_dirs = {p.split("/")[1] for p in have if p.startswith("refs/") and p.count("/") >= 2}
    no_refs = []
    for s in to_make:
        for cid in s.get("clips") or []:
            if cid not in ref_dirs:
                no_refs.append(cid)
    add("Clips", "Every clip to make has its reference frames", not no_refs,
        ("no refs: " + ", ".join(no_refs[:8])) if no_refs else "%d clip folders" % len(ref_dirs))
    # one list of clips (cold run 18 Nov: RUN.md made 52 assets while CLIPS.md asked for 30, under other names)
    rj = _json(f / "run.json") or {}
    clips_all = (cj.get("clips") if isinstance(cj, dict) else []) or []
    made_by_model = [c for c in clips_all if c.get("tool") != "edit"]
    steps = [st for st in (rj.get("steps") or []) if isinstance(st, dict)] if isinstance(rj, dict) else []
    sheet_assets = {Path(str(st.get("asset") or "")).name for st in steps if st.get("medium") == "video"}
    if steps and made_by_model:
        off = [c["id"] for c in made_by_model if Path(str(c.get("return") or "")).name not in sheet_assets]
        extra = len(sheet_assets) - len(made_by_model)
        add("Clips", "Run sheet and clip list name the same clips", not off and extra == 0,
            ("not in RUN.md: " + ", ".join(off[:8])) if off else
            ("RUN.md has %d clip steps, CLIPS.md %d clips" % (len(sheet_assets), len(made_by_model))) if extra else
            "%d clips" % len(made_by_model))
    # every clip carries what it needs (V59; 0333 reached the editor with the product's sheet on no clip, 2026-11-25)
    if made_by_model:
        bare = [c["id"] for c in made_by_model if not c.get("packet")]
        short = ["%s (%s)" % (c["id"], "; ".join(c["packet"]["missing"])) for c in made_by_model if (c.get("packet") or {}).get("missing")]
        gone = [r["file"] for c in made_by_model for r in (c.get("packet") or {}).get("references") or []
                if r.get("file") and not r["file"].startswith("returned/") and r["file"] not in have]
        add("Clips", "Every clip carries its people, product, place and full prompt", not bare and not short and not gone,
            ("no packet: " + ", ".join(bare[:8])) if bare else ("not ready: " + " · ".join(short[:4])) if short else
            ("file not in the folder: " + ", ".join(gone[:4])) if gone else "%d clips" % len(made_by_model))
        by_words = {}                                         # the same words are the same clip, paid for twice (0378, 2026-11-25)
        for c in made_by_model:
            w = str((c.get("packet") or {}).get("clip_prompt") or "").strip()
            if w and not c.get("song_at"):
                by_words.setdefault(w, []).append(c["id"])
        twice = [v for v in by_words.values() if len(v) > 1]
        add("Clips", "No two clips ask for the same shot", not twice, " · ".join(", ".join(v[:4]) for v in twice[:4]) or "%d clips" % len(made_by_model))
        long_ = ["%s (%.0f s)" % (c["id"], c["secs"]) for c in made_by_model if float(c.get("secs") or 0) > 15.5 and not c.get("song_at")]
        add("Clips", "No clip is longer than one call makes (15 s)", not long_, ", ".join(long_[:6]) or "%d clips" % len(made_by_model))
        bare_ = {}                                            # nothing named without a picture (2026-11-25)
        for c in made_by_model:
            for r in (c.get("packet") or {}).get("references") or []:
                if r["role"] in ("place", "prop") and not r.get("file"):
                    bare_[r["name"]] = bare_.get(r["name"], 0) + 1
        add("Clips", "Every place and prop has its picture", not bare_,
            ("%d with no picture: " % len(bare_) + ", ".join("%s (%d clips)" % x for x in sorted(bare_.items(), key=lambda x: -x[1])[:8])) if bare_ else "")
        on = [c["id"] for c in made_by_model if any(r["role"] == "product" and r.get("file") for r in (c.get("packet") or {}).get("references") or [])]
        vid = {Path(str(st.get("asset") or "")).name: st for st in steps if st.get("medium") == "video"}
        unsent = [c["id"] for c in made_by_model if c["id"] in on and Path(str(c.get("return") or "")).name in vid and
                  not any(r.get("packet") == "product" for r in vid[Path(str(c.get("return") or "")).name].get("references") or [])]
        if on and steps:
            add("Clips", "The product's sheet is sent with every clip it is in", not unsent,
                ("not sent: " + ", ".join(unsent[:8])) if unsent else "%d clips" % len(on))
    if (f / "3d" / "JUTSU.md").exists():
        boards = [c["id"] for c in made_by_model if c.get("start_picture") and not (f / "refs" / c["id"] / "print-board.png").exists()]
        add("Clips", "Every 3D start picture has its print board", not boards,
            ("no board: " + ", ".join(boards[:8])) if boards else "")
    add("Pack", "Front page (handoff.md)", have.get("handoff.md", 0) > 50, "missing" if "handoff.md" not in have else "")
    el = (f / "ELEMENTS.md").read_text(encoding="utf-8", errors="ignore") if (f / "ELEMENTS.md").exists() else ""
    rows = [l for l in el.splitlines() if l.startswith("|") and not set(l) <= set("|-: ")]
    add("Clips", "Build list filled (cast, sets, props)", len(rows) > 1, "%d rows" % max(0, len(rows) - 1))

    # what the editor works in
    sw = f / "swipe" / "swipe.mp4"                  # the video this ad remakes travels with it (2026-11-19)
    add("Edit files", "Swipe video (swipe/swipe.mp4)", sw.is_file() and sw.stat().st_size > 50000,
        "%.1f MB" % (sw.stat().st_size / 1e6) if sw.is_file() else "missing")
    xml = OB.premiere_xml(f) or next(iter(sorted((f / "premiere").glob("brief-*.xml"))), None)
    add("Edit files", "Premiere timeline", xml, xml.name if xml else "none")
    hf = OB.hyperframes_dir(f)
    add("Edit files", "HyperFrames project", hf, str(hf.relative_to(f)) if hf else "none")
    audio = [k for k in have if k.split("/")[0] in ("voice", "song", "music") and k.endswith((".mp3", ".wav", ".m4a", ".aac"))]
    add("Edit files", "Voice or song audio", audio, "%d audio files" % len(audio))
    add("Edit files", "returned/ folder ready", (f / "returned").is_dir(), "")

    # the editor's own door
    num = OB.number(key)
    seen = OB.info(f)
    add("Editor", "Shows in the editor's brief list", bool(re.search(r"brief-\d+", key)) and (seen["hyperframes"] or seen["premiere"]),
        "open_brief list %s" % brand)
    add("Editor", "Has a name in the list", OB.title_of(f), OB.title_of(f) or "blank")

    # the Drive copy
    if drive is None:
        add("Drive", "Shared drive reachable", False, "Shared Assets not mounted here")
    else:
        d = drive / ROLE / brand / key
        sibs = sorted(p.name for p in (drive / ROLE / brand).glob(key + " (*)")) if (drive / ROLE / brand).is_dir() else []
        add("Drive", "On the Drive under the same name", d.is_dir(), str(Path(ROLE) / brand / key) if d.is_dir() else "missing")
        add("Drive", "No duplicate copies", not sibs, ", ".join(sibs))
        if d.is_dir():
            dh = _files(d)
            miss = [k for k in have if k not in dh]
            stale = [k for k in have if k in dh and dh[k] != have[k]]
            extra = sorted(k for k in dh if k not in have and not k.startswith("_superseded/") and
                           (re.search(r" \(\d+\)(\.[^/]*)?$", k) or k.endswith(("MISSING.txt", "DRIVE-NOTE.txt"))))
            add("Drive", "No stray copies or old notes on the Drive", not extra, ", ".join(extra[:6]))
            add("Drive", "Drive copy matches the pack", not miss and not stale,
                " · ".join(x for x in (("missing: " + ", ".join(miss[:4])) if miss else "",
                                       ("out of date: " + ", ".join(stale[:4])) if stale else "") if x))

    # the system's records
    if recs is not None:
        owner = [n for n, r in recs.items() if Path(r.get("folder") or "").name == key]
        add("Studio", "Studio knows this hand-off", owner, ", ".join(owner) or "no Studio record points here")
    reg = _json(repo / "components" / "image-teardown" / "briefs.json") or {}
    add("Studio", "In the brief register", key in (reg.get("briefs") or {}), "components/image-teardown/briefs.json")
    prod = cj.get("production") if isinstance(cj, dict) else None
    twins = []
    if prod:
        for other in (repo / ROLE / brand).iterdir():
            if other.is_dir() and other != f and not other.name.startswith(("_", ".")):
                oc = _json(other / "clips.json")
                if isinstance(oc, dict) and oc.get("production") == prod:
                    twins.append(other.name)
    add("Studio", "Only one pack for this ad", not twins, ", ".join(twins))
    return {"key": key, "brand": brand, "number": num, "title": OB.title_of(f), "checks": out,
            "passed": sum(c["ok"] for c in out), "total": len(out)}


def packs(repo, brand=None, only=None):
    root = repo / ROLE
    for b in sorted(p for p in root.iterdir() if p.is_dir() and (not brand or p.name == brand)):
        for k in sorted(p for p in b.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
            if only and only not in (k.name, OB.number(k.name), OB.number(k.name).lstrip("0")):
                continue
            if not only and not re.search(r"brief-\d+", k.name):
                continue
            yield k


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", nargs="?", help="a brief key or number")
    ap.add_argument("--all", action="store_true", help="every numbered hand-off")
    ap.add_argument("--brand")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.brief and not a.all:
        ap.error("name a brief, or --all")
    repo = P.repo()
    drive, recs = _drive_root(), _studio_records()
    res = [check(k, repo, drive, recs) for k in packs(repo, a.brand, None if a.all else a.brief)]
    if not res:
        raise SystemExit("No hand-off found for %s" % (a.brief or a.brand or "any brand"))
    if a.json:
        print(json.dumps(res, indent=1))
        return
    for r in res:
        print("%s · %s · %d/%d" % (r["number"], r["title"] or r["key"], r["passed"], r["total"]))
        for c in r["checks"]:
            if not c["ok"]:
                print("  ✗ %s · %s%s" % (c["group"], c["check"], (" — " + c["evidence"]) if c["evidence"] else ""))
    sys.exit(0 if all(r["passed"] == r["total"] for r in res) else 1)


if __name__ == "__main__":
    main()
