#!/usr/bin/env python3
"""A finished drop, read the way Meta needs it.

Drops keep their words in their own `copy.csv` (one row per ad unit) and
their pictures — or finished videos — in one folder per unit. The copywriter
run `build.py --run` was written for never exists for a drop, which is why
the 260923a import sheet could not be built (Print Run, 30 Sep). This reads
the drop itself.

    from drop import read_handoff, read_drop
    units = read_handoff(<ad-uploader hand-off folder>)   # the normal door
    units = read_drop(<runs/image-teardown/<brand>/<batch>/deliverable>)

Each unit comes back as:

    {"unit": short name, "old_name": 13-field name, "brief_id",
     "media": [Path, ...]  pictures and/or videos, in asset order,
     "kind": "image" | "video" | "mixed",
     "bodies": [...], "titles": [...], "descriptions": [...],
     "ads": [{"meta_ad_name", "link_id"}, ...]   one per landing page}

Nothing here talks to Meta and nothing here rewrites a word: the copy row is
cut at the writer's own word-count marker (`*97 words.*`) — everything after
it is the writer's notes to us, never ad copy — and the headlines and
descriptions are the numbered lists the writer put under HEADLINES and
DESCRIPTIONS. That is exactly what the 42 live 260923a ads carry.
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "components/naming"))
import names as N
import shared_drive as SD

DRIVE = SD.shared_assets()          # the mount's Shared Assets, else a named path that does not exist
PICTURE = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO = {".mp4", ".mov", ".m4v"}

_END = re.compile(r"^\s*\*\d+\s+words\.?\*\s*$", re.M)
_ITEM = re.compile(r"^\s*\d+\.\s+\*\*(.+?)\*\*", re.M)


def body_of(text):
    """The ad copy only: everything before the writer's word-count line."""
    text = (text or "").replace("\r\n", "\n")
    m = _END.search(text)
    return (text[:m.start()] if m else text).strip()


def listed(text, heading):
    """The numbered bold items under a **HEADING** block, in order."""
    text = (text or "").replace("\r\n", "\n")
    m = re.search(r"\*\*" + heading + r"\*\*\s*\n(.*?)(?:\n\s*\*\*[A-Z ]+\*\*|\n---|\Z)", text, re.S)
    return [s.strip() for s in _ITEM.findall(m.group(1))] if m else []


def copy_rows(deliverable):
    """copy.csv -> {old unit name: {"bodies", "titles", "descriptions"}}."""
    f = Path(deliverable) / "copy.csv"
    if not f.is_file():
        return {}
    out = {}
    for r in csv.DictReader(f.open(encoding="utf-8-sig")):
        both = (r.get("primary_text") or "") + "\n" + (r.get("alt_text") or "")
        bodies = [b for b in (body_of(r.get("primary_text")), body_of(r.get("alt_text"))) if b]
        # headlines and descriptions: plain columns when the drop has them
        # (one per line, or split by " | "), else the writer's HEADLINES /
        # DESCRIPTIONS lists inside the copy text
        col = lambda k: [x.strip() for x in re.split(r"\n| \| ", r.get(k) or "") if x.strip()]
        out[r["ad_name"]] = {
            "bodies": list(dict.fromkeys(bodies)),
            "titles": list(dict.fromkeys(col("headlines") or listed(both, "HEADLINES"))),
            "descriptions": list(dict.fromkeys(col("descriptions") or listed(both, "DESCRIPTIONS"))),
            "lane": r.get("lane", ""),
        }
    return out


def _exists(p):
    """p.exists(); a path the mount will not stat (OSError, e.g. EDEADLK) reads as absent."""
    try:
        return p.exists()
    except OSError:
        return False


def _is_file(p):
    """p.is_file(); a path the mount will not stat (OSError, e.g. EDEADLK) reads as absent."""
    try:
        return p.is_file()
    except OSError:
        return False


def where(rel):
    """A repo-relative path, found in this checkout or on the Drive."""
    rel = Path(rel)
    if rel.is_absolute():
        return rel
    for root in (REPO, DRIVE):
        if _exists(root / rel):
            return root / rel
    return REPO / rel


def media_in(folder):
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in PICTURE | VIDEO)


def kind_of(media):
    k = {"video" if p.suffix.lower() in VIDEO else "image" for p in media}
    return k.pop() if len(k) == 1 else ("mixed" if k else "none")


DROP_HOMES = ("image-teardown", "image-edit")   # new home first; legacy drops read in place


def _deliverable_for(manifest):
    """The drop a hand-off packaged: runs/image-teardown/<brand>/<drop>/deliverable,
    else the legacy runs/image-edit/<brand>/<drop>/deliverable (filed before 2026-10-07)."""
    brand, batch = manifest["brand"], manifest.get("batch") or ""
    m = re.match(r"batch-(\d{4})-(\d{2})-(\d{2})-([a-z])$", batch)
    drop = f"{m.group(1)[2:]}{m.group(2)}{m.group(3)}{m.group(4)}" if m else batch
    for machine in DROP_HOMES:
        p = where(f"runs/{machine}/{brand}/{drop}/deliverable")
        if _exists(p):
            return p
    return where(f"runs/image-teardown/{brand}/{drop}/deliverable")


def read_handoff(folder):
    """Every ad unit in an ad-uploader hand-off, with its media, words and pages."""
    folder = Path(folder).resolve()
    man = json.loads((folder / "manifest.json").read_text())
    idx = json.loads((folder / "assets/index.json").read_text())
    deliverable = _deliverable_for(man)
    words = copy_rows(deliverable)
    # pictures sit on the Drive copy of the hand-off; git keeps none
    roots = [folder, DRIVE / "handoffs" / man["role"] / man["brand"] / man["name"]]
    drop_roots = [deliverable, DRIVE / deliverable.relative_to(REPO)] if deliverable.is_relative_to(REPO) else [deliverable]
    units = []
    for a in idx["ads"]:
        media = []
        for f in a["files"]:
            hit = next((r / f["file"] for r in roots if _is_file(r / f["file"])), None)
            if not hit and f.get("was"):          # the drop's own copy, old name
                hit = next((c for r in drop_roots for c in (r / a["old_name"] / f["was"], r / f["was"])
                            if _is_file(c)), None)
            media.append(hit or roots[-1] / f["file"])
        w = words.get(a["old_name"], {})
        units.append({
            "unit": a["ad_name"], "old_name": a["old_name"], "brief_id": a["brief_id"],
            "media": media, "missing": [str(p) for p in media if not Path(p).is_file()],
            "kind": kind_of(media),
            "bodies": w.get("bodies", []), "titles": w.get("titles", []),
            "descriptions": w.get("descriptions", []), "lane": w.get("lane", ""),
            "ads": [{"meta_ad_name": m["meta_ad_name"], "link_id": m["link_id"]} for m in a["meta_ad_names"]],
        })
    links = json.loads((folder / "references/links.json").read_text()) if (folder / "references/links.json").is_file() else {}
    return {"brand": man["brand"], "batch": man.get("batch"), "handoff": man["name"],
            "deliverable": str(deliverable), "links": links, "units": units}


def read_drop(deliverable, brand, funnels=()):
    """A drop with no hand-off: units by folder, words by copy.csv, Meta names
    by names.short_meta for each funnel given."""
    deliverable = where(deliverable)
    words = copy_rows(deliverable)
    units = []
    for old, w in words.items():
        d = N.parse_any(old) or {}
        short = N.short_unit(brand, d.get("product") or "", d.get("brief"), d.get("batch")) if d else old
        folder = deliverable / old
        media = media_in(folder) or next(
            (m for m in (media_in(where(Path("runs") / machine / brand / deliverable.parent.name / "deliverable" / old))
                         for machine in DROP_HOMES) if m), [])
        units.append({
            "unit": short, "old_name": old, "brief_id": d.get("brief_id"),
            "media": media, "missing": [] if media else [str(folder)], "kind": kind_of(media),
            "bodies": w["bodies"], "titles": w["titles"], "descriptions": w["descriptions"], "lane": w["lane"],
            "ads": [{"meta_ad_name": N.short_meta(short, f), "link_id": None} for f in funnels],
        })
    return {"brand": brand, "batch": deliverable.parent.name, "handoff": None,
            "deliverable": str(deliverable), "links": {}, "units": units}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", help="an ad-uploader hand-off folder")
    a = ap.parse_args()
    d = read_handoff(a.folder)
    for u in d["units"]:
        print(f"{u['unit']}  {len(u['media'])} {u['kind']}  bodies {len(u['bodies'])} "
              f"titles {len(u['titles'])} desc {len(u['descriptions'])}  pages {len(u['ads'])}"
              + (f"  MISSING {len(u['missing'])}" if u["missing"] else ""))
