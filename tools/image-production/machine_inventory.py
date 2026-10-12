#!/usr/bin/env python3
"""python3 machine_inventory.py <brand> [--mount all|company|other] [--resume]

A full, deep inventory of everything a brand owns on the Drive — every folder,
every file, both mounts. Not a sample and not the picture shelves only:
the owner, 2026-09-21, "get a full index of the brand assets because you'll also
see logos and fonts and stuff like that by going deep into EACH folder in this
drive. this is years of content that we can use today."

READ ONLY. Nothing is written to, moved on, renamed on or deleted from any
Drive. The inventory is written into this repo.

Resumable: each folder is written as it finishes, so a slow mount can be
stopped and restarted without losing what it already walked.
"""
import argparse
import json
import os
import pathlib
import sys
import time
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "inventory"

KIND = {
    "image": {".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff", ".gif", ".bmp"},
    "vector": {".svg", ".ai", ".eps"},
    "video": {".mp4", ".mov", ".m4v", ".avi", ".webm", ".mkv"},
    "audio": {".mp3", ".wav", ".m4a", ".aif", ".aiff"},
    "font": {".otf", ".ttf", ".woff", ".woff2", ".eot"},
    "design": {".psd", ".psb", ".sketch", ".fig", ".xd", ".indd", ".afdesign", ".afphoto"},
    "doc": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".pages"},
    "sheet": {".csv", ".xls", ".xlsx", ".numbers", ".tsv"},
    "deck": {".ppt", ".pptx", ".key"},
    "data": {".json", ".xml", ".yml", ".yaml"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "project": {".prproj", ".aep", ".drp", ".fcpbundle", ".capture"},
}
EXT_KIND = {e: k for k, exts in KIND.items() for e in exts}
SKIP_DIR = {".git", "node_modules", "__pycache__", ".Trash", "$RECYCLE.BIN"}
# What a search for the brand's marks and type actually looks like.
MARK = ("logo", "wordmark", "lockup", "monogram", "brandmark", "icon", "favicon",
        "identity", "brand-kit", "brandkit", "style-guide", "styleguide", "guidelines")
TYPE_ = ("font", "typeface", "type", "glyph")


def mounts(which="all"):
    cloud = pathlib.Path.home() / "Library" / "CloudStorage"
    out = []
    if not cloud.is_dir():
        return out
    for m in sorted(cloud.glob("GoogleDrive-*")):
        company = os.environ.get("DRIVE_ACCOUNT_HINT", "") in m.name
        if which == "company" and not company:
            continue
        if which == "other" and company:
            continue
        out.append((m, "company" if company else "other"))
    return out


def scope(brand):
    """What the brand itself says is in and out — `brands/<brand>/archive/retired-2026-09-30/assets.json`
    (retired from the brand folder in the v6 layout; its rulings still hold).
    Ruled by a person, read at run time, never a list in code."""
    here = pathlib.Path(__file__).resolve()
    ws = next((d for d in here.parents if (d / "brands").is_dir()), None)
    f = next((c for c in (ws / "brands" / brand / "assets.json",
                          ws / "brands" / brand / "archive" / "retired-2026-09-30" / "assets.json")
              if c.is_file()), None) if ws else None
    if not f or not f.is_file():
        return {"home": None, "excluded": []}
    d = json.loads(f.read_text())
    return {"home": (d.get("home") or {}).get("path"),
            "excluded": [x["path"] for x in d.get("excluded", [])]}


def roots_for(mount, brand, ruled=None):
    """Every place this brand's material could sit on one mount, found by
    looking — never a path typed in, and never one the brand ruled out."""
    found, brand = [], brand.lower()
    # macOS writes filenames in NFD and a JSON file is written in NFC, so
    # "MANË" ruled out in the file did not match "MANË" on the disk. Both sides
    # are normalised or the exclusion silently does nothing.
    def norm(x):
        return unicodedata.normalize("NFC", str(x)).lower()

    out = [norm(x) for x in (ruled or {}).get("excluded", [])]

    def allowed(p):
        low = norm(p)
        return not any(x in low for x in out)
    for top in ("Shared drives", "My Drive"):
        base = mount / top
        if not base.is_dir():
            continue
        try:
            for a in sorted(base.iterdir()):
                if not a.is_dir() or a.name in SKIP_DIR:
                    continue
                if brand in a.name.lower():
                    if allowed(a):
                        found.append(a)
                    continue
                # The brand folder sits at an unknown depth — Team Drive/brands/<brand>
                # on one mount, a folder of its own on another. Three levels of
                # looking finds both without a path being typed in.
                for b in sorted(a.iterdir()):
                    if not b.is_dir() or b.name.startswith("."):
                        continue
                    if brand in b.name.lower():
                        if allowed(b):
                            found.append(b)
                        continue
                    try:
                        for c in sorted(b.iterdir()):
                            if c.is_dir() and brand in c.name.lower() and allowed(c):
                                found.append(c)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue
    return found


def walk(root, echo, seen_dirs, budget_s, skip=()):
    rows, t0 = [], time.time()
    stack = [pathlib.Path(root)]
    while stack:
        if time.time() - t0 > budget_s:
            echo(f"    … stopped at the time budget, {len(rows):,} files so far")
            return rows, False
        d = stack.pop()
        key = str(d)
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        try:
            entries = sorted(d.iterdir())
        except (OSError, PermissionError) as e:
            echo(f"    ! {d.name}: {type(e).__name__}")
            continue
        for p in entries:
            if p.name.startswith(".") or p.name in SKIP_DIR:
                continue
            try:
                if p.is_dir():
                    low = unicodedata.normalize("NFC", str(p)).lower()
                    if any(x in low for x in skip):
                        continue          # a folder the brand ruled out, pruned here
                    stack.append(p)
                    continue
                st = p.stat()
            except (OSError, PermissionError):
                continue
            ext = p.suffix.lower()
            low = f"{p.parent.name}/{p.name}".lower()
            rows.append({
                "path": str(p), "name": p.stem, "ext": ext,
                "kind": EXT_KIND.get(ext, "other"),
                "bytes": st.st_size,
                "modified": time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
                "folder": str(p.parent),
                "is_mark": any(w in low for w in MARK),
                "is_type": ext in KIND["font"] or any(w in low for w in TYPE_),
            })
        if len(rows) % 2000 < 40 and rows:
            echo(f"    … {len(rows):,} files")
    return rows, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("--mount", default="all", choices=("all", "company", "other"))
    ap.add_argument("--budget", type=int, default=3000, help="seconds per root")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    out_f = OUT / f"{a.brand}-inventory.json"
    have = json.loads(out_f.read_text()) if out_f.is_file() else {"brand": a.brand, "roots": {}}

    def echo(m):
        print(m, flush=True)

    ruled = scope(a.brand)
    if ruled["excluded"]:
        echo(f"ruled out by {a.brand}'s assets.json (archive/retired-2026-09-30): " + " · ".join(ruled["excluded"]))
    for mount, which in mounts(a.mount):
        echo(f"\n== {which}: {mount.name}")
        for root in roots_for(mount, a.brand, ruled):
            key = str(root)
            if have["roots"].get(key, {}).get("complete"):
                echo(f"  = {root.name} (already walked)")
                continue
            echo(f"  -> {root}")
            rows, complete = walk(root, echo, set(), a.budget,
                                  skip=[unicodedata.normalize("NFC", x).lower()
                                        for x in ruled["excluded"]])
            have["roots"][key] = {"mount": which, "root": key, "complete": complete,
                                  "files": rows, "count": len(rows),
                                  "walked_at": time.strftime("%Y-%m-%dT%H:%M")}
            out_f.write_text(json.dumps(have, indent=1))
            echo(f"  {'done' if complete else 'PARTIAL'}: {len(rows):,} files")

    total = sum(r["count"] for r in have["roots"].values())
    have["count"] = total
    out_f.write_text(json.dumps(have, indent=1))
    echo(f"\n{total:,} files across {len(have['roots'])} root(s) -> {out_f}")


main()
