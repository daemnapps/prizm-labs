#!/usr/bin/env python3
"""The clip library — footage we already made, by section, ready to reuse.

the owner, 2026-10-08: "we need to be resourceful with the assets that we have
generated … reuse things where it makes sense."

Reads a production folder on Drive (its numbered section folders and its
00_EDITING_BRIEF.md, which maps every clip to its voiceover line) and writes one
record per clip: the doctrine section it serves, the line it was cut to, the
editor's note and its Drive file id (so frames are read from the cloud). Never
downloads a video, never calls Meta.

    python3 components/distinct-six/clips.py brand-a "<Drive folder>" --name p133-neckline

Writes runs/distinct-six/<brand>/clip-library/<name>.json (the Creative Index loads it).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SHARED = os.environ.get("SHARED_DRIVE_NAME", "Shared Drive")  # the shared drive's folder name on the mount
ROOT = Path(__file__).resolve().parents[2]

# folder → doctrine sections (elements/library/doctrine.section.json); a clip's own
# name can sharpen it (CLIP_SECTION) — read off the editing brief's block notes.
FOLDER_SECTION = {"hook": ["hook"], "variant_hooks": ["hook"], "recognition": ["identification", "problem"],
                  "recipe": ["unique-mechanism"], "mechanism": ["unique-mechanism"], "application": ["solution"],
                  "origin": ["proof"], "product_proof_close": ["product", "proof"]}
CLIP_SECTION = {"lotion_sits_on_top": ["failed-solutions"], "harsh_scrub_warning": ["objections"],
                "sun_printing_line": ["root-cause"], "product_push_in": ["product"], "rinse_trust": ["solution", "proof"],
                "phone_pinch_zoom": ["proof"], "white_blouse_freedom": ["transformation"],
                "guarantee_lipsync": ["offer"], "cta_blessing_lipsync": ["call-to-action"], "end_card": ["call-to-action"],
                "even_tone_reveal": ["hook", "transformation"]}


def fid(path):
    try:
        return subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(path)],
                              capture_output=True, text=True).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def brief_lines(text):
    """clip stem -> (vo line, note) from the editing brief's tables."""
    out = {}
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        for c in cells:
            for m in re.finditer(r"([0-9]{2}_[a-z_]+/)?([a-z]{1,3}\d{2}_[a-z_]+)", c):
                stem = m.group(2)
                vo = cells[0].strip('"') if cells and cells[0] != c else ""
                note = cells[-1] if len(cells) > 2 and cells[-1] != c else ""
                out.setdefault(stem, (vo, note))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("folder")
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    base = Path(a.folder)
    bf = next(base.parent.glob(base.name + "*/00_EDITING_BRIEF.md"), None) or next(base.glob("**/00_EDITING_BRIEF.md"), None)
    lines = {}
    if bf:
        sys.path.insert(0, str(ROOT / "components" / "gdrive-creator"))
        import daemn_keys
        from gdrive_creator import engine as G
        G.configure(key_lookup=daemn_keys.key)
        tmp = ROOT / "runs" / "distinct-six" / a.brand / "clip-library" / f"{a.name}-EDITING_BRIEF.md"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        G.get_media(fid(bf), str(tmp))
        lines = brief_lines(tmp.read_text())
    clips = []
    for f in sorted(base.rglob("*")):
        if f.suffix.lower() not in (".mp4", ".mov", ".wav", ".mp3"):
            continue
        folder = re.sub(r"^\d+_", "", f.parent.name)
        stem = f.stem
        key = re.sub(r"^[a-z]{1,3}\d{2}_", "", stem)
        sections = next((v for k, v in CLIP_SECTION.items() if k in key), None) \
            or next((v for k, v in FOLDER_SECTION.items() if k in folder), [])
        vo, note = lines.get(stem, ("", ""))
        clips.append({"clip": stem, "folder": f.parent.name, "kind": "voice" if f.suffix.lower() in (".wav", ".mp3") else "video",
                      "sections": sections, "vo_line": vo, "note": note, "drive_id": fid(f),
                      "path": str(f).split(SHARED + "/")[-1]})
    out = ROOT / "runs" / "distinct-six" / a.brand / "clip-library" / f"{a.name}.json"
    out.write_text(json.dumps({"brand": a.brand, "name": a.name, "source": str(base).split(SHARED + "/")[-1],
                               "editing_brief": bool(bf), "clips": clips}, indent=1, ensure_ascii=False))
    print(f"{len(clips)} clips → {out.relative_to(ROOT)}")
    for c in clips:
        print(f"  {c['clip']:<34} {','.join(c['sections']):<34} {c['vo_line'][:60]}")


if __name__ == "__main__":
    main()
