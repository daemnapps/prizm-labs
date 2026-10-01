#!/usr/bin/env python3
"""Put a brief's pictures on Drive, and record where they went.

    deliver.py --brand <brand>            every brief for that brand
    deliver.py --briefs p005,p006         just these

Damon, 2026-09-14, after seeing they existed only on the laptop: *"you need
to go ahead and put the images together properly in Google Drive. Everything
needs to be organized properly, and then the register entries."*

**Why they were nowhere.** Rendered pictures are excluded from git by rule
(nothing over 10MB, no media), which is right — but nothing had ever put them
anywhere else. So six finished drafts lived in one folder on one machine,
unshareable and unbacked.

**One folder per brief, named by the thing that joins everything**:

    Shared Assets/image-teardown/<brand>/<brief id>/
        source.jpg     the competitor's ad this came from
        draft.png      the whole ad, for review
        brief.md       the brief itself, so the folder stands alone

The brief id is the same id that travels into every Meta ad name, so a folder
on Drive, a row in `briefs.json` and a line in a Meta report all say `p005`.

**Through the API, never the mount.** Drive for Desktop went offline mid-copy
on 2026-09-07 and the server got filenames with no bytes.
"""
import argparse, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import paths as _P
WS = _P.REPO                      # the workspace, found by walking up — not counted
sys.path.insert(0, str(WS / "components/gdrive-creator"))
sys.path.insert(0, str(WS / "components/video-teardown/machine"))
sys.path.insert(0, str(HERE / "tools"))
import briefs as B

ROOT = ["lab", "damon", "image-teardown"]


def service():
    import keys
    for k, v in (keys.all_keys() or {}).items():
        os.environ.setdefault(k, v)
    from gdrive_creator import engine
    return engine, engine.service()


def folder(engine, svc, name, parent):
    return engine.folder(name, parent, svc=svc)


def drive_root(engine, svc):
    d = svc.drives().list(fields="drives(id,name)").execute()["drives"]
    shared = next((x for x in d if x["name"] == "Shared Assets"), None)
    if not shared:
        sys.exit("no 'Shared Assets' shared drive reachable by this account")
    node = shared["id"]
    for part in ROOT:
        node = folder(engine, svc, part, node)
    return node


def upload(svc, path: Path, parent, name=None):
    from googleapiclient.http import MediaFileUpload
    name = name or path.name
    # Update in place if it is already there: a new id would break every link
    # already handed out.
    q = (f"'{parent}' in parents and name='{name}' and trashed=false")
    hit = svc.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                           includeItemsFromAllDrives=True).execute()["files"]
    media = MediaFileUpload(str(path), resumable=False)
    if hit:
        fid = svc.files().update(fileId=hit[0]["id"], media_body=media,
                                 supportsAllDrives=True, fields="id").execute()["id"]
    else:
        fid = svc.files().create(body={"name": name, "parents": [parent]},
                                 media_body=media, fields="id",
                                 supportsAllDrives=True).execute()["id"]
    svc.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"},
                             supportsAllDrives=True).execute()
    return fid


def newest_draft(brand, bid):
    d = HERE / "drafts" / brand
    # numeric, not lexical: "v9" sorted after "v11" and the newest judged set
    # was skipped (2026-09-18)
    for v in sorted((x for x in d.glob("v*") if x.is_dir() and re.fullmatch(r"v\d+", x.name)),
                    key=lambda x: int(x.name[1:]), reverse=True):
        for n in (f"{bid}-draft.png", f"{bid}-plate.png"):
            if (v / n).is_file():
                return v / n
        # A judged set is the last word: a brief the judge passed nothing
        # for has no draft, rather than an older unjudged one standing in
        # (2026-09-17 — the older one is the slop the judge exists to stop).
        if (v / "judge.json").is_file() and list(v.glob(f"{bid}-roll-*.png")):
            return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand"); ap.add_argument("--briefs")
    a = ap.parse_args()
    reg = B.load()
    ids = [x.strip() for x in a.briefs.split(",")] if a.briefs else \
        [b for b, r in reg["briefs"].items()
         if r.get("run") and (not a.brand or r.get("brand") == a.brand)]
    if not ids:
        sys.exit("nothing to deliver")

    engine, svc = service()
    root = drive_root(engine, svc)
    for bid in sorted(ids):
        rec = reg["briefs"].get(bid)
        if not rec or not rec.get("run"):
            print(f"  ! {bid}: no run"); continue
        run = HERE / "runs" / rec["run"]
        here = folder(engine, svc, bid, folder(engine, svc, rec["brand"], root))
        put = {}
        src = run / "assets/source.jpg"
        if src.is_file():
            put["source"] = upload(svc, src, here, "source.jpg")
        drf = newest_draft(rec["brand"], bid)
        if drf:
            put["draft"] = upload(svc, drf, here, "draft.png")
        bf = run / "out/06-brief.md"
        if bf.is_file():
            put["brief"] = upload(svc, bf, here, "brief.md")

        # The work order and its prompts. Damon, 2026-09-14: *"What the hell
        # does my designer do from here? … They're in Higgsfield mostly."*
        # The brief is the argument; this is the job. It travels with the
        # brief because the designer never opens the repo.
        ws = HERE / "worksheets" / rec["brand"] / bid
        if (ws / "work-order.md").is_file():
            put["work order"] = upload(svc, ws / "work-order.md", here,
                                       "work-order.md")
            pf = folder(engine, svc, "prompts", here)
            n = 0
            for p in sorted((ws / "prompts").glob("*.txt")):
                upload(svc, p, pf, p.name); n += 1
            if n:
                put[f"{n} prompts"] = pf
            if (ws / "refs").is_dir():
                rf = folder(engine, svc, "refs", here)
                for r in sorted((ws / "refs").iterdir()):
                    upload(svc, r, rf, r.name)
                put["refs"] = rf

        rec["drive"] = {
            "folder": f"https://drive.google.com/drive/folders/{here}",
            **{k: f"https://drive.google.com/file/d/{v}/view" for k, v in put.items()},
        }
        print(f"  {bid}  {', '.join(put)}  → {rec['drive']['folder']}")
    B.save(reg)
    print(f"\n{len(ids)} delivered · links recorded in briefs.json")


if __name__ == "__main__":
    main()
