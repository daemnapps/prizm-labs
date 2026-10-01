#!/usr/bin/env python3
"""Make the Drive run folder equal the repo's delivered set — through the API.

    drive_reconcile.py <run-root-id> <runs/<brand>/<batch> ...> [--name "RUN-01 fed-up-king"] [--apply]

Dry by default. Prints the plan; `--apply` executes the parts the service
account is allowed to do (rename in place, make folders, server-side copy,
upload) and writes `trash.json` beside the run for the parts it is NOT
allowed to do — trashing — which a session then does with Damon's own
Drive login. Measured 2026-09-09: the SA uploads, updates and renames on the
shared drive but gets 403 on `trashed: true`.

Why this exists (2026-09-07): Drive for Desktop went offline mid-upload.
Metadata reached the server, bytes did not, and the mount showed the
opposite of the server. The mount is now for nothing but reading local
bytes; structure is built and verified here.

Layout on Drive, by man then format — the way Damon reviews:
    <run-root>/<talent>/<format>/<asset-name>.png

Never re-points the run root (his link); never deletes — only lists ids to
trash, reversibly. Idempotent: run it twice and the second run plans nothing.
"""
import argparse, json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P                # the workspace is found by walking up, never counted

WS = P.REPO
sys.path.insert(0, str(P.GDRIVE))
sys.path.insert(0, str(P.NAMING))
from gdrive_creator import engine
import names as N

F = "id,name,mimeType,size,parents,trashed"
FOLDER = "application/vnd.google-apps.folder"


def children(svc, fid):
    out, tok = [], None
    while True:
        r = svc.files().list(q=f"'{fid}' in parents and trashed = false",
                             fields=f"nextPageToken,files({F})", pageSize=1000,
                             pageToken=tok, supportsAllDrives=True,
                             includeItemsFromAllDrives=True).execute()
        out += r.get("files", []); tok = r.get("nextPageToken")
        if not tok:
            return out


def walk(svc, fid, path=""):
    """Every file under fid, with its path relative to fid."""
    for c in children(svc, fid):
        p = f"{path}/{c['name']}" if path else c["name"]
        if c["mimeType"] == FOLDER:
            yield from walk(svc, c["id"], p)
        else:
            c["path"] = p
            yield c


def expected(run_dirs):
    """Every delivered asset the repo knows about, from the manifests."""
    exp = {}
    for rd in run_dirs:
        for m in Path(rd).rglob("manifest.json"):
            for row in json.loads(m.read_text()).get("ads", []):
                f = m.parent / row["file"]
                d = N.parse(row["name"])
                if not d or not f.is_file():
                    print(f"  ! skip {row['name']} — {'unparseable' if not d else 'file missing'}")
                    continue
                exp[row["file"]] = {"local": f, "talent": d["talent"],
                                    "format": d["format"], "batch": d["batch"]}
    return exp


def man_folders(svc, root_id, brand):
    """talent slug -> the man's folder name on Drive. An existing folder wins
    (Damon has seen "Hal 66"); a missing one is named from the roster the same
    way, `<Name> <age>`, so the run reads as people, not slugs."""
    have = {c["name"]: c for c in children(svc, root_id) if c["mimeType"] == FOLDER}
    names = {}
    roster = WS / "brands" / brand / "core-avatars/casting/roster.json"
    people = json.loads(roster.read_text())["people"] if roster.is_file() else []
    for pp in people:
        names[pp["id"]] = next((n for n in have if n.lower().split()[0] == pp["id"]),
                               f"{pp['name']} {pp['age']}")
    return names


def plan(svc, root_id, run_dirs, brand_root, brand):
    exp = expected(run_dirs)
    men = man_folders(svc, root_id, brand)
    for w in exp.values():
        w["man"] = men.get(w["talent"], w["talent"])
    have = list(walk(svc, root_id))
    everywhere = list(walk(svc, brand_root)) if brand_root else have
    good = {}   # name -> byte-carrying file anywhere under the brand folder
    for f in everywhere:
        if int(f.get("size") or 0) > 0 and f["name"] in exp:
            good.setdefault(f["name"], f)
    steps, trash = [], []
    placed = {}
    for f in have:
        want = exp.get(f["name"])
        target = f"{want['man']}/{want['format']}/{f['name']}" if want else None
        if not want:
            trash.append({"id": f["id"], "why": "not in the delivered set", "path": f["path"]})
        elif int(f.get("size") or 0) == 0:
            trash.append({"id": f["id"], "why": "zero bytes", "path": f["path"]})
        elif f["path"] != target:
            trash.append({"id": f["id"], "why": f"wrong place, belongs at {target}", "path": f["path"]})
        elif f["name"] in placed:
            trash.append({"id": f["id"], "why": "duplicate", "path": f["path"]})
        else:
            placed[f["name"]] = f
    for name, w in sorted(exp.items()):
        if name in placed:
            continue
        src = good.get(name)
        steps.append({"op": "copy" if src else "upload", "name": name,
                      "talent": w["man"], "format": w["format"],
                      "from": src["id"] if src else str(w["local"])})
    return exp, placed, steps, trash


def apply(svc, root_id, steps):
    cache = {}
    def sub(path_parts):
        key = tuple(path_parts)
        if key not in cache:
            parent = root_id if len(path_parts) == 1 else sub(path_parts[:-1])
            cache[key] = engine.folder(path_parts[-1], parent, svc)
        return cache[key]
    for s in steps:
        dest = sub([s["talent"], s["format"]])
        if s["op"] == "copy":
            svc.files().copy(fileId=s["from"], body={"name": s["name"], "parents": [dest]},
                             fields="id", supportsAllDrives=True).execute()
        else:
            engine.upload_file(s["from"], s["name"], dest, mime="image/png", svc=svc)
        print(f"  {s['op']:6} {s['talent']}/{s['format']}/{s['name']}")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("root_id"); a.add_argument("runs", nargs="+")
    a.add_argument("--name", help="rename the run root to this, in place")
    a.add_argument("--brand-root", help="folder to search for byte-carrying twins")
    a.add_argument("--brand", required=True, help="roster to name the men's folders from")
    a.add_argument("--apply", action="store_true")
    o = a.parse_args()
    svc = engine.service()
    meta = svc.files().get(fileId=o.root_id, fields="id,name,trashed", supportsAllDrives=True).execute()
    print(f"root  {meta['name']}  ({meta['id']})  trashed={meta['trashed']}")
    if meta["trashed"]:
        raise SystemExit("the run root is in the Trash — restore it first, never re-create it")
    exp, placed, steps, trash = plan(svc, o.root_id, o.runs, o.brand_root, o.brand)
    print(f"expected {len(exp)}  in place {len(placed)}  to place {len(steps)} "
          f"({sum(s['op']=='copy' for s in steps)} copy, {sum(s['op']=='upload' for s in steps)} upload)  to trash {len(trash)}")
    if not o.apply:
        for s in steps[:8]: print("  plan", s["op"], s["talent"], s["format"], s["name"][:60])
        for t in trash[:8]: print("  trash", t["why"], "—", t["path"][:70])
        return
    if o.name and meta["name"] != o.name:
        svc.files().update(fileId=o.root_id, body={"name": o.name}, fields="id,name", supportsAllDrives=True).execute()
        print(f"renamed → {o.name}")
    apply(svc, o.root_id, steps)
    out = Path(o.runs[0]).parent / "_drive-trash.json"
    out.write_text(json.dumps(trash, indent=1) + "\n")
    print(f"trash list ({len(trash)}) → {out}   — the SA cannot trash; a session does it with Damon's login")
    exp2, placed2, steps2, trash2 = plan(svc, o.root_id, o.runs, None, o.brand)
    print(f"after: expected {len(exp2)}  in place {len(placed2)}  still to place {len(steps2)}")


if __name__ == "__main__":
    main()
