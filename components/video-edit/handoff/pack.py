#!/usr/bin/env python3
"""Hand one component's finished output to the role that runs the next component of the video chain.

    python3 components/video-edit/handoff/pack.py video-writing <teardown label> [--no-drive] [--dry-run]
    python3 components/video-edit/handoff/pack.py video-production <brief number | writing run> [--brand b]
                                             [--swipe <video>] [--no-drive] [--dry-run]

video-teardown -> video-writing: the teardown's working run (runs/video-teardown/_work/<label>/, stages 0 to 2 done)
is copied whole into teardown-run/, which is what the writing's door takes. Folder:
runs/handoffs/creative-strategist/<brand>/<label>/ (no brief number exists before the writing).

video-writing -> video-production: reads the brief register, the writing run (runs/video-writing/<brand>/<run>/) and its
teardown (runs/video-teardown/<brand>/<run>/). Writes runs/handoffs/video-producer/<brand>/<brief key>/:

  START.md        what this is and the one line to say to your Claude to switch the stage on
  HANDOFF.json    the record: chain, stage, role, brand, brief, where it came from, how to activate, what comes next
  BRIEF.md        the written brief (the writing run's deliverable/5-brief.md)
  teardown/       the swipe torn down: 1-teardown.md, 2-spec.md, 1-transcript.md, FRAME-MAP.md, sound-sheet.md
  writing/        the writing audit (audit.md): what the checks said about the brief
  SWIPE.md        the swipe: where its video sits
  refs/           swipe.mp4 and swipe-poster.jpg
  returned/       empty: production hands on by filing the editor's hand-off (the edit kit)

video-production -> video-edit is the production's own edit kit (the Studio's maker pack), checked by
components/video-edit/handoff_check.py. Every folder is copied to the same path under Shared Assets/ (copies and
updates, never deletes).

Spends nothing. Refuses a brief whose writing was not accepted or whose route is not AI.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_handoff as SH  # noqa: E402
sys.path.append(str(HERE.parents[1] / "briefs"))
import video_delivery  # noqa: E402

ROLE = "video-producer"
TEARDOWN = (("stages/1-teardown.md", "1-teardown.md"), ("stages/2-spec.md", "2-spec.md"),
            ("stages/1-transcript.md", "1-transcript.md"), ("framemap/FRAME-MAP.md", "FRAME-MAP.md"),
            ("sound-sheet.md", "sound-sheet.md"), ("elements.json", "elements.json"))


def resolve(ref, brand=None, root=None):
    """(register key, register row, writing run dir) for a brief number or a writing run label."""
    root = Path(root or SH.repo())
    reg = (SH._json(root / "components" / "image-teardown" / "briefs.json") or {}).get("briefs") or {}
    want = str(ref).lstrip("#")
    for k, v in reg.items():
        if not str(v.get("type", "")).startswith("video"):
            continue
        if brand and v.get("brand") != brand:
            continue
        if SH.number(k).lstrip("0") == want.lstrip("0") or v.get("run") == want:
            run = root / "runs" / "video-writing" / v["brand"] / str(v.get("run") or "")
            return k, v, run
    raise SystemExit("No video brief %s in the register%s." % (ref, (" for " + brand) if brand else ""))


def studio_production(run_label, brand=""):
    """The Video Studio production already opened for this writing run: {production, brief_key, url}, or None."""
    data = os.environ.get("VIDEO_STUDIO_DATA")
    if not data:
        return None
    for p in sorted((Path(data) / "briefs").glob("*/brief.json")):
        b = SH._json(p) or {}
        if b.get("brief") == run_label or str(b.get("working_key") or "").endswith(run_label):
            n = p.parent.name
            return {"production": n, "brief_key": b.get("brief_key"),
                    "url": "http://localhost:8922/?brand=%s&n=%s" % (b.get("brand") or brand, n), "title": b.get("title")}
    return None


def swipe_video(run_label, given=None):
    if given:
        return Path(given)
    data = os.environ.get("VIDEO_STUDIO_DATA")
    if data:
        hits = sorted((Path(data) / "sources").glob("*/%s.mp4" % run_label))
        if hits:
            return hits[0]
    # the teardown's own copy of the swipe (2026-11-19: a swipe that came in by link was never in the Studio's sources,
    # so the production hand-off went out without its video)
    ws = Path(__file__).resolve().parents[3]
    for c in [ws / "runs" / "video-teardown" / "_work" / run_label / "source.mp4",
              *sorted((ws / "runs" / "video-teardown").glob("*/%s/source.mp4" % run_label))]:
        if c.is_file() and c.stat().st_size > 50000:
            return c
    return None


def build(ref, brand=None, swipe=None, drive=True, dry=False, root=None, by=None):
    root = Path(root or SH.repo())
    key, row, run = resolve(ref, brand, root)
    brand = row["brand"]
    rj = SH._json(run / "run.json") or {}
    if not (run / "deliverable" / "5-brief.md").is_file():
        raise SystemExit("REFUSED: %s has no written brief (deliverable/5-brief.md)." % run.relative_to(root))
    acc = (rj.get("writing_acceptance") or {}).get("accepted") is True
    route = rj.get("production_route") or ("ai" if row.get("type") == "video-ai" else row.get("type"))
    if not acc:
        raise SystemExit("REFUSED: the writing for %s was not accepted by its checks; it stays with writing." % key)
    if route != "ai":
        raise SystemExit("REFUSED: %s is a %s brief; the producer hand-off is the AI route." % (key, route))
    st = SH.stage("video-production")
    tear = root / "runs" / "video-teardown" / brand / run.name
    out = SH.folder(ROLE, brand, key, root)
    studio = studio_production(run.name, brand)
    if studio:
        studio["same_number"] = SH.number(studio.get("brief_key") or "") == SH.number(key)
    vid = swipe_video(run.name, swipe)
    title = row.get("title") or ""
    form = rj.get("format_id") or ""
    fmt = {"key": key, "folder": SH.HANDOFFS.as_posix() + "/%s/%s/%s/" % (ROLE, brand, key), "number": SH.number(key),
           "brand": brand, "format": form or "<format>", "label": run.name}
    say = st["activates"]["say"].format(**fmt)
    nxt = SH.stage(st["next"])
    rec = {
        "schema": SH.SCHEMA, "status": "draft", "chain": "video", "stage": st["id"], "role": ROLE, "format": form,
        "brand": brand, "key": key, "brief": "brief-" + SH.number(key), "title": title,
        "made": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from": {"stage": "video-writing", "by": by or rj.get("ran_by") or ""},
        "route": route, "writing_accepted": acc,
        "writing_sha256": (rj.get("writing_acceptance") or {}).get("source_sha256"),
        "activate": {"skill": st["activates"]["skill"], "run": st["activates"]["run"].format(**fmt), "say": say},
        "sources": [{"path": (run / "deliverable" / "5-brief.md").relative_to(root).as_posix(), "what": "the brief"},
                    {"path": tear.relative_to(root).as_posix(), "what": "the teardown run"},
                    {"label": "Shared Assets/components/video-teardown/swipes/%s" % run.name, "what": "the swipe library"}],
        "studio": studio,
        "next": {"stage": nxt["id"], "role": nxt["role"],
                 "folder": SH.HANDOFFS.as_posix() + "/%s/%s/%s/" % (nxt["role"], brand, key),
                 "how": "production's edit kit (the Studio's Send to maker) files it"},
        "holders": SH.holders(ROLE),
    }
    if dry:
        return out, rec
    out.mkdir(parents=True, exist_ok=True)
    (out / "returned").mkdir(exist_ok=True)
    shutil.copy2(str(run / "deliverable" / "5-brief.md"), str(out / "BRIEF.md"))
    video_delivery.pack(out)
    (out / "teardown").mkdir(exist_ok=True)
    for src, dst in TEARDOWN:
        if (tear / src).is_file():
            shutil.copy2(str(tear / src), str(out / "teardown" / dst))
    if (run / "stages" / "4f-audit.md").is_file():
        (out / "writing").mkdir(exist_ok=True)
        shutil.copy2(str(run / "stages" / "4f-audit.md"), str(out / "writing" / "audit.md"))
    (out / "refs").mkdir(exist_ok=True)
    if vid and vid.is_file():
        shutil.copy2(str(vid), str(out / "refs" / "swipe.mp4"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", str(vid), "-frames:v", "1",
                        "-q:v", "3", str(out / "refs" / "swipe-poster.jpg")])
    label = SH.label_of(out, root)
    (out / "SWIPE.md").write_text(
        "# The swipe\n\n- The video: `%s/refs/swipe.mp4`%s\n- The swipe library (every teardown version): `%s`\n"
        "- First frame: `refs/swipe-poster.jpg`\n\nThe storyboard copies the swipe's beats in order "
        "(teardown/1-teardown.md, teardown/FRAME-MAP.md); the words, shots and cast are ours (BRIEF.md).\n"
        % (label, "" if (out / "refs" / "swipe.mp4").is_file() else " (not packed: no copy of the swipe was found here)",
           rec["sources"][2]["label"]), encoding="utf-8")
    rec["files"] = sorted(SH.files(out))
    (out / "HANDOFF.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "START.md").write_text(start_md(rec, studio), encoding="utf-8")
    rec["files"] = sorted(SH.files(out))
    (out / "HANDOFF.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if drive:
        SH.mirror(out, root)
    return out, rec


def start_md(rec, studio):
    picked = ("\n**Already started in the Studio:** production %s (%s). Open it and carry on from where it stands.\n"
              % (studio["production"], studio["url"])) if studio else \
        "\n**Not in the Studio yet:** set it up there from BRIEF.md.\n"
    return (
        "# %s · brief %s · video production\n\n"
        "video-writing is done: the brief passed its checks. This is the hand-off to **video-production**, run by "
        "whoever holds the **video-producer** role (today: %s).\n%s\n"
        "## Switch it on\n\nSay this to your Claude:\n\n> %s\n\nThe component's door:\n\n    %s\n\n"
        "## What's here\n\n"
        "- `BRIEF.md`: the brief. Cast, scenes, words, on-screen text. Don't rewrite it; flag what's wrong.\n"
        "- `VIDEO-DELIVERY.md`: every requested version and its thumbnail, production steps, checks and return files.\n"
        "- `teardown/`: the swipe torn down. `1-teardown.md` beat by beat, `2-spec.md` what must carry over, "
        "`FRAME-MAP.md` frame by frame.\n"
        "- `SWIPE.md` and `refs/`: the swipe video and its first frame.\n"
        "- `writing/audit.md`: what the writing checks said.\n\n"
        "## When you're done\n\nProduction hands on to **video-edit** by filing the edit kit (the Studio's "
        "**Send to maker**) at `%s`. Nothing goes in `returned/` by hand.\n\n"
        "Spend past a cap, going live, sending and signing stay the owner's call. Everything else is yours.\n"
        % (rec["title"] or rec["key"], SH.number(rec["key"]), ", ".join(rec["holders"]) or "nobody yet", picked,
           rec["activate"]["say"], rec["activate"]["run"], rec["next"]["folder"]))


HEAVY_SKIP = ("versions", "qc-log", "manifest-reviews")      # history the writing never reads


def build_writing(label, drive=True, dry=False, root=None, by=None):
    """video-teardown -> video-writing: the teardown working run, copied whole into teardown-run/."""
    root = Path(root or SH.repo())
    src = root / "runs" / "video-teardown" / "_work" / label
    rj = SH._json(src / "run.json")
    if not rj:
        raise SystemExit("No teardown working run %s (runs/video-teardown/_work/)." % label)
    done = all((src / "stages" / x).is_file() for x in ("1-teardown.md", "2-spec.md"))
    if not done:
        raise SystemExit("REFUSED: %s has not finished stages 1 and 2; it stays with the teardown." % label)
    if (src / "stages" / "3-injection.md").is_file():
        raise SystemExit("REFUSED: %s already has writing (stage 3); hand it on from video-writing instead." % label)
    brand = rj.get("brand") or ""
    role = "creative-strategist"
    st = SH.stage("video-writing")
    out = SH.folder(role, brand, label, root)
    fmt = {"key": label, "folder": SH.HANDOFFS.as_posix() + "/%s/%s/%s/" % (role, brand, label), "number": label,
           "brand": brand, "label": label, "format": rj.get("format_id") or ""}
    rec = {
        "schema": SH.SCHEMA, "status": "draft", "chain": "video", "stage": st["id"], "role": role,
        "brand": brand, "key": label, "brief": None, "title": label,
        "made": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from": {"stage": "video-teardown", "by": by or rj.get("ran_by") or ""}, "route": rj.get("production_route"),
        "activate": {"skill": st["activates"]["skill"], "run": st["activates"]["run"].format(**fmt),
                     "say": st["activates"]["say"].format(**fmt)},
        "sources": [{"path": src.relative_to(root).as_posix(), "what": "the teardown working run"}],
        "next": {"stage": "video-production", "role": "video-producer",
                 "how": "pack.py video-production <brief number> once the brief is accepted and numbered"},
        "holders": SH.holders(role),
    }
    if dry:
        return out, rec
    out.mkdir(parents=True, exist_ok=True)
    (out / "returned").mkdir(exist_ok=True)
    shutil.copytree(str(src), str(out / "teardown-run"), symlinks=False, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*HEAVY_SKIP))
    rec["files"] = sorted(SH.files(out))
    (out / "START.md").write_text(
        "# %s · video writing\n\nvideo-teardown is done: stages 0 to 2. This is the hand-off to **video-writing**, run "
        "by whoever holds the **creative-strategist** role (today: %s).\n\n## Switch it on\n\nSay this to your "
        "Claude:\n\n> %s\n\nThe component's door:\n\n    %s\n\n## What's here\n\n- `teardown-run/`: the "
        "teardown's working run as the writing reads it (stages, run.json, frames, the swipe video).\n\n## When "
        "you're done\n\nThe accepted brief is filed at `runs/video-writing/%s/%s/deliverable/5-brief.md` and "
        "numbered; then `pack.py video-production <brief number>` hands it to video production.\n"
        % (label, ", ".join(rec["holders"]) or "nobody yet", rec["activate"]["say"], rec["activate"]["run"], brand,
           label), encoding="utf-8")
    (out / "HANDOFF.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    rec["files"] = sorted(SH.files(out))
    (out / "HANDOFF.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if drive:
        SH.mirror(out, root)
    return out, rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("video-writing", "video-production", "production"))
    ap.add_argument("ref")
    ap.add_argument("--brand")
    ap.add_argument("--swipe")
    ap.add_argument("--by")
    ap.add_argument("--resume-writing", action="store_true", help="pack unfinished writing at its current stage")
    ap.add_argument("--role", choices=("creative-strategist", "video-producer"), default="video-producer",
                    help="recipient role for an explicitly delegated writing continuation")
    ap.add_argument("--no-drive", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.resume_writing and a.stage != "video-writing":
        ap.error("--resume-writing applies only to video-writing")
    if a.resume_writing:
        from resume_writing import build as resume
        out, rec = resume(a.ref, a.role, not a.no_drive, a.dry_run, by=a.by)
    elif a.stage == "video-writing":
        out, rec = build_writing(a.ref, not a.no_drive, a.dry_run, by=a.by)
    else:
        out, rec = build(a.ref, a.brand, a.swipe, not a.no_drive, a.dry_run, by=a.by)
    if a.dry_run:
        print(json.dumps(rec, indent=1))
        return
    print("Handed to %s: %s (%d files)%s" % (rec["role"], out.relative_to(SH.repo()), len(rec["files"]),
                                             "" if a.no_drive else ", on the Drive at the same path"))


if __name__ == "__main__":
    main()
