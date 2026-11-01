#!/usr/bin/python3
"""LD-56 (footage index in git): move the clip index out of tools/asset-index/work/ (this Mac only,
git-ignored, ids = sha1 of an absolute path) into runs/asset-index/<brand>/<collection>/<drive-file-id>/,
keyed by the Drive file id the GDRIVE_SA_KEY can fetch, so every machine — the mini included — reads it.

    migrate_index.py pass1 [--collection <brand>-<name>] [--out runs/asset-index/_migration]
    migrate_index.py pass2 --go [--collection …]        (uploads + records; after pass 1's totals are posted)

PASS 1 is READ-ONLY: for every record in work/<brand>-<collection>/<clip>/ it finds the footage file on
Shared Assets through the key (the work/_maps/<collection>.json label, then the folder listing: name, then
size, then md5Checksum) and sorts the record into
    matched     the key fetches it — its Drive id, md5Checksum and size are kept
    mac_only    the file is on this Mac but not on Shared Assets (pass 2 uploads it, copy only)
    nowhere     neither — the record has nothing to point at
    empty       a clip folder with no clip.json (an unfinished run)
and writes one report per collection (text) under --out. Nothing on the Drive or on this Mac changes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
REPO = COMP.parents[1]
WORK = COMP / "work"
sys.path.append(str(REPO / "components" / "gdrive-creator"))
SA = "Shared Assets/"


def collections(only=None):
    out = []
    for d in sorted(WORK.iterdir()) if WORK.is_dir() else []:
        if d.is_dir() and not d.name.startswith(("_", ".")) and "-" in d.name and (not only or d.name == only):
            out.append(d)
    return out


def label_of(path):
    """A mount path or label → "Shared Assets/…", else None."""
    s = str(path)
    return SA + s.split(SA, 1)[1] if SA in s else None


class Drive:
    """Folder listings through the key, cached per folder: {name: [{id, size, md5}]}."""

    def __init__(self):
        from gdrive_creator import engine as E
        self.E, self.svc, self.ids, self.lists = E, E.service(), {}, {}

    def folder(self, label):
        if label not in self.ids:
            self.ids[label] = self.E.folder_by_path(label, svc=self.svc)
        return self.ids[label]

    def listing(self, label):
        if label not in self.lists:
            fid, rows, tok = self.folder(label), {}, None
            while fid:
                r = self.svc.files().list(q="'%s' in parents and trashed=false" % fid, pageToken=tok, pageSize=1000,
                                          fields="nextPageToken, files(id,name,size,md5Checksum,mimeType)",
                                          supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                for f in r.get("files", []):
                    if f.get("mimeType") != "application/vnd.google-apps.folder":
                        rows.setdefault(f["name"], []).append(
                            {"id": f["id"], "size": int(f.get("size") or -1), "md5": f.get("md5Checksum")})
                tok = r.get("nextPageToken")
                if not tok:
                    break
            self.lists[label] = rows
        return self.lists[label]

    def by_name(self, brand, name, size=None):
        """Fallback for a record the old map never placed: the file by NAME anywhere under
        Shared Assets/brands/<brand>/ (one names-only listing per brand), size-checked."""
        key = "names:" + brand
        if key not in self.lists:
            from gdrive_creator import reach as R
            idx = {}
            for rel, fid in R.list_tree(["brands", brand], svc=self.svc, max_items=200000) or []:
                idx.setdefault(rel.rsplit("/", 1)[-1], []).append((rel, fid))
            self.lists[key] = idx
        out = []
        for rel, fid in self.lists[key].get(name) or []:
            m = self.svc.files().get(fileId=fid, fields="size,md5Checksum", supportsAllDrives=True).execute()
            out.append({"id": fid, "size": int(m.get("size") or -1), "md5": m.get("md5Checksum"),
                        "label": SA + "brands/%s/%s" % (brand, rel)})
        if len(out) > 1 and size:
            out = [h for h in out if h["size"] == size] or out
        return out[0] if len(out) == 1 or (out and size and out[0]["size"] == size) else None

    def find(self, label, size=None):
        parent, name = label.rsplit("/", 1)
        hits = self.listing(parent).get(name) or []
        if len(hits) > 1 and size:
            hits = [h for h in hits if h["size"] == size] or hits
        return hits[0] if hits else None


def local_file(rec):
    """The footage file on this Mac the record was made from, if it is still there."""
    for p in (Path(rec.get("path") or "") / (rec.get("folder") or "") / (rec.get("filename") or ""),):
        try:
            if p.is_file():
                return p
        except OSError:
            pass
    return None


def pass1(col, drive, out_dir):
    brand, name = col.name.split("-", 1)
    try:
        mp = json.loads((WORK / "_maps" / (col.name + ".json")).read_text())
    except (OSError, ValueError):
        mp = {}
    rows, t0 = [], time.time()
    for clip in sorted(p for p in col.iterdir() if p.is_dir()):
        cj = clip / "clip.json"
        if not cj.is_file():
            rows.append({"old_id": clip.name, "class": "empty"})
            continue
        rec = json.loads(cj.read_text())
        size = ((rec.get("meta") or {}).get("bytes")) if isinstance(rec.get("meta"), dict) else None
        lab = label_of((mp.get(clip.name) or {}).get("path") or "")
        hit = drive.find(lab, size) if lab else None
        how = "map" if hit else None
        if hit is None and rec.get("filename"):
            hit = drive.by_name(brand, rec["filename"], size)
            if hit:
                lab, how = hit["label"], "name"
        row = {"old_id": clip.name, "filename": rec.get("filename"), "bytes": size, "label": lab, "found_by": how}
        if hit:
            row.update({"class": "matched", "drive_id": hit["id"], "md5": hit["md5"], "drive_size": hit["size"],
                        "size_ok": (size is None or hit["size"] == size)})
        else:
            f = local_file(rec)
            if f is not None:
                row.update({"class": "mac_only", "local": str(f), "bytes": f.stat().st_size})
            else:
                row.update({"class": "nowhere"})
        rows.append(row)
    tally = {}
    for r in rows:
        tally[r["class"]] = tally.get(r["class"], 0) + 1
    mac_bytes = sum(r.get("bytes") or 0 for r in rows if r["class"] == "mac_only")
    rep = {"collection": col.name, "brand": brand, "name": name, "records": len(rows), "tally": tally,
           "size_mismatch": sum(1 for r in rows if r.get("class") == "matched" and not r.get("size_ok")),
           "mac_only_bytes": mac_bytes, "seconds": round(time.time() - t0), "rows": rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ("pass1-" + col.name + ".json")).write_text(json.dumps(rep, indent=1))
    return rep


def pass2(col, report, runs_root, go=False):
    """Write runs/asset-index/<brand>/<collection>/<drive-id>/ for every MATCHED record: clip.json (the old
    record plus drive_id, label, md5, size, old_id — the Whisper text kept as it is, decision c), breakdown.json,
    and the record's frame pictures (git-ignored, beside it on this machine only); then map.json
    {drive_id: {label, md5, size, old_id, filename}} and old-ids.json {old_id: drive_id}. Text in git, media not.
    Two old records on one Drive file: the first is kept, the rest listed. mac_only uploads come in their own
    step once a home folder for them is ruled (pass 1 lists them). Without go, counts only."""
    import shutil
    brand, name = col.name.split("-", 1)
    dest = Path(runs_root) / brand / name
    mp, old, dup, wrote = {}, {}, [], 0
    held = []
    for r in report["rows"]:
        if r["class"] != "matched":
            continue
        if not r.get("size_ok", True):
            # the Drive file's size differs from the record's: no record until a person has read it (lead, 071)
            held.append({"old_id": r["old_id"], "filename": r.get("filename"), "bytes": r.get("bytes"),
                         "drive_size": r.get("drive_size"), "drive_id": r.get("drive_id")})
            continue
        did = r["drive_id"]
        if did in mp:
            dup.append({"old_id": r["old_id"], "same_as": mp[did]["old_id"], "drive_id": did})
            old[r["old_id"]] = did
            continue
        src = col / r["old_id"]
        rec = json.loads((src / "clip.json").read_text())
        rec.update({"clip_id": did, "drive_id": did, "label": r["label"], "md5": r.get("md5"),
                    "size": r.get("drive_size"), "old_id": r["old_id"], "path": None})
        mp[did] = {"label": r["label"], "md5": r.get("md5"), "size": r.get("drive_size"), "old_id": r["old_id"],
                   "filename": r.get("filename")}
        old[r["old_id"]] = did
        if go:
            d = dest / did
            d.mkdir(parents=True, exist_ok=True)
            (d / "clip.json").write_text(json.dumps(rec, indent=1))
            if (src / "breakdown.json").is_file():
                shutil.copy2(str(src / "breakdown.json"), str(d / "breakdown.json"))
            for f in src.iterdir():
                if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".mp4"):
                    shutil.copy2(str(f), str(d / f.name))      # media: git-ignored, this machine only
            wrote += 1
    if go:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "map.json").write_text(json.dumps(mp, indent=1, sort_keys=True))
        (dest / "old-ids.json").write_text(json.dumps(old, indent=1, sort_keys=True))
    return {"collection": col.name, "records": len(mp), "written": wrote, "duplicates": len(dup), "dup_rows": dup,
            "held_size_mismatch": held, "to": str(dest)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("pass1", help="read-only report")
    p1.add_argument("--collection")
    p1.add_argument("--out", default=str(REPO / "runs" / "asset-index" / "_migration"))
    p2 = sub.add_parser("pass2", help="write the records (needs --go)")
    p2.add_argument("--collection")
    p2.add_argument("--reports", default=str(REPO / "runs" / "asset-index" / "_migration"))
    p2.add_argument("--runs", default=str(REPO / "runs" / "asset-index"))
    p2.add_argument("--go", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "pass2":
        for col in collections(a.collection):
            rep = json.loads((Path(a.reports) / ("pass1-" + col.name + ".json")).read_text())
            r = pass2(col, rep, a.runs, go=a.go)
            print("%s: %d records%s · %d duplicates · %d held (size mismatch) → %s" % (r["collection"], r["records"],
                  " written" if a.go else " (dry: nothing written)", r["duplicates"], len(r["held_size_mismatch"]), r["to"]))
        return 0
    if a.cmd == "pass1":
        drive = Drive()
        for col in collections(a.collection):
            r = pass1(col, drive, Path(a.out))
            print("%s: %d records · %s · size mismatches %d · mac-only %.1f MB · %ds"
                  % (r["collection"], r["records"], r["tally"], r["size_mismatch"], r["mac_only_bytes"] / 1e6, r["seconds"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
