"""Pack an unfinished writing run for a role to continue at its actual stopped stage."""
import datetime
import hashlib
import json
import re
import shutil
import os
import zipfile
from pathlib import Path

import stage_handoff as SH


def build(label, role="video-producer", drive=True, dry=False, root=None, by=None, output_root=None):
    root = Path(root or SH.repo())
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", label):
        raise SystemExit("REFUSED: use an existing writing run label")
    if role not in ("creative-strategist", "video-producer"):
        raise SystemExit("REFUSED: writing continuation belongs to the strategist or delegated producer")
    src = root / "runs/video-teardown/_work" / label
    rj = SH._json(src / "run.json") or {}
    if not rj or not all((src / "stages" / x).is_file() for x in ("1-teardown.md", "2-spec.md")):
        raise SystemExit("REFUSED: the writing continuation needs its completed teardown and spec")
    if (rj.get("writing_acceptance") or {}).get("accepted") is True:
        raise SystemExit("REFUSED: accepted writing goes through the production handoff")
    brand = rj.get("brand")
    if not brand or not re.fullmatch(r"[a-z0-9-]+", brand):
        raise SystemExit("REFUSED: the run must name its brand")
    stages = rj.get("stages") or {}
    stopped = [{"stage": k, "status": v.get("status"), "error": v.get("error"), "output": v.get("out")}
               for k, v in stages.items() if k.startswith(("stage3", "stage4", "stage5"))
               and v.get("status") in ("held", "error", "failed")]
    prompts = sorted(p.relative_to(src).as_posix() for p in (src / "hand").glob("*.prompt.md")
                     if not p.with_name(p.name.replace(".prompt.md", ".md")).exists()
                     and any(p.name in (x.get("error") or "") for x in stopped))
    revalidate = (src / "stages/5-brief.md").is_file() and stages.get("stage5", {}).get("status") in ("held", "done")
    command = "python3 components/video-writing/machine/run.py " + label + (" --revalidate" if revalidate else "")
    output_root = Path(output_root or root)
    out = SH.folder(role, brand, label, output_root)
    say = "Open the writing continuation %s from %s. Read START.md and continue the recorded writing step; this is not an accepted production brief." % (label, out.relative_to(output_root).as_posix())
    rec = {"schema": SH.SCHEMA, "status": "draft", "state": "open", "chain": "video", "stage": "video-writing", "role": role,
           "packet_kind": "writing-continuation", "work_role": "creative-strategist", "brand": brand,
           "key": label, "brief": rj.get("brief"), "title": label + " · finish writing",
           "made": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "from": {"stage": "video-writing", "by": by or ""}, "route": rj.get("production_route"),
           "writing_accepted": False, "production_ready": False,
           "source_state": rj.get("state"), "source_record_sha256": hashlib.sha256((src / "run.json").read_bytes()).hexdigest(),
           "stopped": stopped, "hand_prompts": prompts,
           "activate": {"skill": "video-writing", "run": command, "say": say},
           "sources": [{"path": src.relative_to(root).as_posix(), "what": "the unfinished writing run"}],
           "next": {"stage": "video-production", "role": "video-producer",
                    "how": "pack.py video-production <brief number> only after current writing checks accept the brief"},
           "holders": SH.holders(role), "working_dependencies": [], "working_media": "working-media.zip"}
    winner = (rj.get("writing_lane") or {}).get("winner")
    if winner:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", winner):
            raise SystemExit("REFUSED: invalid winner label")
        wd = root / "runs/video-teardown/_work" / winner
        if not any((wd / x).is_file() for x in ("stages/1-transcript.md", "stages/1-teardown.md")):
            raise SystemExit("REFUSED: the selected winner's words are missing")
        rec["working_dependencies"].append({"packet": "dependencies/" + winner,
                                            "path": wd.relative_to(root).as_posix()})
    if dry:
        return out, rec
    out.mkdir(parents=True, exist_ok=True)
    (out / "returned").mkdir(exist_ok=True)
    shutil.copytree(src, out / "teardown-run", symlinks=False, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("versions", "manifest-reviews", "__pycache__", ".DS_Store", "framemap", "audio", "music"))
    rec["working_media_parts"] = bundle_media(src, out)[1:]
    for dep in rec["working_dependencies"]:
        for name in ("run.json", "doctrine.json", "stages/1-transcript.md", "stages/1-teardown.md"):
            original = root / dep["path"] / name
            if original.is_file():
                dst = out / dep["packet"] / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, dst)
    lines = ["# " + rec["title"], "", "This is an unfinished **video-writing** assignment in the %s inbox. "
             "It is ready to continue, not accepted for production. Completed teardown and writing outputs stay intact." % role,
             "", "## Open the working copy", "", "> " + say, "",
             "    python3 components/video-edit/handoff/pull.py open %s --role %s --brand %s" % (label, role, brand),
             "", "The pull door places teardown-run/ and its selected winner inputs at their runner paths only when absent. "
             "An existing working copy is preserved: compare its run.json with this packet before resuming. "
             "working-media.zip and its numbered parts carry the full frame map, audio and music folders; the pull door restores missing files safely.",
             "", "## Next action", ""]
    for hold in stopped:
        lines.append("- %s: %s%s" % (hold["stage"], hold["status"], " — " + hold["error"] if hold["error"] else " — inspect its output and qc-log receipt"))
    for prompt in prompts:
        answer = prompt.replace(".prompt.md", ".md")
        lines.append("- Read the complete `teardown-run/%s`, write its stage answer at `runs/video-teardown/_work/%s/%s`, "
                     "and keep the companion prompt unchanged. The runner verifies the request bytes; if they changed, use the new request it emits." % (prompt, label, answer))
    if revalidate:
        lines.append("- The existing stage-5 brief is held. Inspect its saved checks and repair the failed writing requirement through the writing workflow; revalidate the existing brief. Do not manufacture acceptance.")
    lines += ["", "Then use the supported runner:", "", "    " + command, "",
              "The current format, route, story, owner rulings and winner lane are in teardown-run/. Preserve them. "
              "Prompts, qc-log and source media are carried with the run. Model calls and production generation have not been run by this packaging step.",
              "", "## Hand on", "", rec["next"]["how"] + ". Keep any hold with its receipt; an unaccepted draft never goes to production as ready.", ""]
    (out / "START.md").write_text("\n".join(lines))
    rec["files"] = sorted(set(SH.files(out)) | {"HANDOFF.json"})
    (out / "HANDOFF.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    if drive:
        SH.mirror(out, output_root)
    return out, rec


def restore_media(packet, destination, archive):
    """Restore the packet's media without escaping its run or replacing existing work."""
    archive = Path(archive)
    if archive.is_absolute() or ".." in archive.parts:
        raise SystemExit("REFUSED: unsafe writing media archive path")
    destination = Path(destination).resolve()
    with zipfile.ZipFile(Path(packet) / archive) as bundle:
        members = bundle.infolist()
        for member in members:
            relative = Path(member.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in member.filename:
                raise SystemExit("REFUSED: unsafe writing media member")
            target = (destination / relative).resolve()
            if destination not in target.parents or (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise SystemExit("REFUSED: unsafe writing media destination")
        for member in members:
            target = destination / member.filename
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def bundle_media(source, output, limit=32 * 1024 * 1024):
    """Bounded ZIP parts use ordinary file uploads; no oversized resumable request is needed."""
    paths = []
    for name in ("framemap", "audio", "music"):
        for directory, _, files in os.walk(Path(source) / name, followlinks=True):
            paths += [Path(directory) / n for n in sorted(files)
                      if not n.startswith(".") and (Path(directory) / n).is_file()]
    names, size, bundle = [], 0, None
    try:
        for original in paths or [None]:
            amount = original.stat().st_size if original else 0
            if bundle is None or (size and size + amount > limit):
                if bundle:
                    bundle.close()
                name = "working-media.zip" if not names else "working-media-%03d.zip" % (len(names) + 1)
                names.append(name)
                bundle = zipfile.ZipFile(Path(output) / name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1)
                size = 0
            if original:
                bundle.write(original, original.relative_to(source).as_posix())
                size += amount
    finally:
        if bundle:
            bundle.close()
    return names
