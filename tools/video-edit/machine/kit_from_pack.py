#!/usr/bin/env python3
"""kit_from_pack.py — the join between an EDITOR HANDOFF and the edit: takes the
pack production made for a human editor (a zip or folder with the handoff
document, scene clips, voice or song files) and writes the edit kit from it.
The pack is never written to.

    build(pack, kit_dir, run_dir) -> (kit, notes)     python3 machine/run.py pack <zip|folder> --brand <b> --label <l>

The handoff is read by the model (prompts/stage-1-read-pack): every handoff is
shaped differently, and a fixed parser breaks on the next one. The prompt as
sent and the reply are saved in the run. What it returns is checked here
against the files that are really in the pack, so a name it made up is refused.

A clip with `sound: own` keeps its own sound and is cut at its pauses (talking
A-roll). A clip under a `bed` (one song or master voice track) is muted and laid
end to end, and the bed is the clock.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
MEDIA = {".mp4", ".mov", ".m4v", ".webm", ".wav", ".mp3", ".m4a", ".aac", ".png", ".jpg", ".jpeg"}


def unpack(pack: Path, kit_dir: Path) -> Path:
    """Copy the pack into the kit folder (a zip is unpacked). Returns that folder."""
    kit_dir.mkdir(parents=True, exist_ok=True)
    if pack.is_file() and pack.suffix == ".zip":
        with zipfile.ZipFile(pack) as z:
            for n in z.namelist():
                if n.startswith("__MACOSX") or n.endswith("/"):
                    continue
                dest = kit_dir / n
                if not dest.exists() or dest.stat().st_size != z.getinfo(n).file_size:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(n) as src, dest.open("wb") as out:
                        shutil.copyfileobj(src, out)
    elif pack.is_dir():
        for f in pack.rglob("*"):
            if f.is_file():
                dest = kit_dir / f.relative_to(pack)
                if not dest.exists() or dest.stat().st_size != f.stat().st_size:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
    else:
        raise SystemExit(f"{pack} is neither a zip nor a folder")
    return kit_dir


def probe(f: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,r_frame_rate:format=duration", "-of", "json", str(f)],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return {}
    kinds = {s.get("codec_type") for s in d.get("streams") or []}
    fps = next((s["r_frame_rate"] for s in d.get("streams") or [] if s.get("codec_type") == "video"), None)
    if fps and "/" in fps:
        a, b = fps.split("/"); fps = round(int(a) / int(b), 3) if int(b) else None
    return {"seconds": round(float((d.get("format") or {}).get("duration") or 0), 2), "sound": "audio" in kinds, "picture": "video" in kinds, "fps": fps}


def handoff_of(kit_dir: Path) -> Path:
    docs = sorted(kit_dir.rglob("*.md"), key=lambda p: ("HANDOFF" not in p.name.upper() and "EDITOR" not in p.name.upper(), len(p.parts)))
    if not docs:
        raise SystemExit(f"no handoff document (.md) in {kit_dir}")
    return docs[0]


def repo_root() -> Path:
    for p in [TOOL, *TOOL.parents]:
        if (p / "runs" / "README.md").exists():
            return p
    return TOOL


def read_pack(kit_dir: Path, run_dir: Path, files: dict) -> dict:
    root = repo_root()
    sys.path.insert(0, str(root / "components" / "run-kit"))
    from run_kit import model as M, prompts as P
    learned = json.loads((TOOL / "learned.json").read_text()).get("rules") or []
    path = P.latest(TOOL / "prompts" / "stage-1-read-pack", "stage1-read-pack")
    sent = P.fill(Path(path).read_text(), {
        "handoff": handoff_of(kit_dir).read_text(),
        "files": json.dumps(files, indent=0, ensure_ascii=False),
        "learned": json.dumps(learned, ensure_ascii=False) if learned else "nothing on file yet"})
    fix = ""
    for attempt in (1, 2):
        tag = "" if attempt == 1 else "-retry"
        (run_dir / f"stage1-read-pack--sent{tag}.md").write_text(sent + fix)
        mdl, _ = M.pick("checks", len(sent))
        reply = M.call(sent + fix, mdl, label="video-edit read pack")
        (run_dir / f"stage1-read-pack--reply{tag}.md").write_text(reply)
        try:
            d = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
        except Exception as e:
            fix = f"\n\n## Your last answer could not be read as JSON ({e}). Answer again with JSON only."
            continue
        bad = [c.get("file") for c in d.get("clips") or [] if c.get("file") not in files]
        if d.get("bed") and d["bed"].get("file") not in files:
            bad.append(d["bed"]["file"])
        if not bad:
            d["_prompt"] = Path(path).name
            d["_model"] = mdl
            return d
        fix = "\n\n## Your last answer named files that are not in the pack. Use only names from the file list:\n" + "\n".join(f"- {b}" for b in bad)
    raise SystemExit(f"the handoff could not be read twice over — see {run_dir}/stage1-read-pack--reply-retry.md")


def build(pack: Path, kit_dir: Path, run_dir: Path, brand: str, label: str) -> tuple[dict, list[str]]:
    unpack(pack.resolve(), kit_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for f in sorted(kit_dir.rglob("*")):
        if f.is_file() and f.suffix.lower() in MEDIA:
            files[str(f.relative_to(kit_dir))] = probe(f)
    by_name = {**files, **{Path(k).name: v for k, v in files.items()}}
    full = {Path(k).name: k for k in files}
    read = read_pack(kit_dir, run_dir, files)
    notes = []
    clips, t = [], 0.0
    bed = read.get("bed")
    for c in read.get("clips") or []:
        name = full.get(Path(c["file"]).name, c["file"])
        info = by_name.get(name) or {}
        if not c.get("approved"):
            continue  # held: named on the page from `held`
        row = {"id": c["id"], "src": name, "scene": c.get("scene"), "approved": True, "roll": "a",
               "why": c.get("what") or f"scene {c.get('scene')}", "qc": c.get("qc")}
        if bed:  # one song or master voice under everything: clips run end to end, muted
            row.update({"talks": False, "covers": [round(t, 3), round(t + info.get("seconds", 0), 3)]})
            t += info.get("seconds", 0)
        else:
            row.update({"talks": True, "words": None, "speaks": c.get("speaks", True)})
        clips.append(row)
    overlays = []
    for i, k in enumerate(read.get("cards") or []):
        if not any(c["id"] == k.get("on") for c in clips):
            notes.append(f"card on {k.get('on')} dropped — that clip is held or not in the pack: {' / '.join(k.get('lines') or [])}")
            continue
        overlays.append({"id": f"card{i + 1}", "kind": "hook" if k.get("kind") == "hook" else "label",
                         "text": "\n".join(k.get("lines") or []), "with": k["on"], "y_pct": 16})
    kit = {"from_pack": str(pack), "brand": brand, "label": label, "format": read.get("kind"),
           "brief": str(handoff_of(kit_dir).relative_to(kit_dir)), "fps": read.get("fps"),
           "voice": ({"src": full.get(Path(bed["file"]).name, bed["file"]), "words": None, "kind": bed.get("what"), "until_picture_ends": True} if bed else None),
           "music": None, "sfx": [], "clips": clips, "overlays": overlays,
           "held": read.get("held") or [], "missing": read.get("missing") or [], "notes_for_damon": read.get("notes_for_damon") or [],
           "read_by": f"{read['_model']} · prompt {read['_prompt']}"}
    return kit, notes
