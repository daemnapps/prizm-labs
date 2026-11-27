#!/usr/bin/env python3
"""Take finished 3D set prints as a production run's start pictures (2026-11-20).

A print made by the 3d-print skill IS the picture (image-production RULE GATE-4: "the print is the picture"). When a
brief's prints already exist (filed in its editor hand-off's `returned/` folder, each with its `.made.json` record
saying job `3d-print`), the run takes them instead of printing again: nothing is generated and nothing is spent.

    python3 take_prints.py <run dir> --handoff <hand-off folder> [--dry-run]

Which print is which scene's start picture comes from the hand-off's own step list (RUN.md: "start picture for
S4-shot-1"): a scene's first shot becomes its start frame `<scene>-F1`, the run's own frame id. Each taken print is
copied to `<run>/media/<frame>.png` and recorded in `<run>/direct.json` (door `3d-print`, the print file and its record
named), the same record every picture door writes, so the run's next stations read it. Its other shots' prints are
copied to `<run>/media/<scene>-shot-<n>.png` and listed in `<run>/shot-pictures.json`: the clip plan
sends each as the opening picture of its shot inside the scene's call. A frame the run already has a different picture for is left as it
is and said. A file with no `3d-print` record is refused, by name. No brand, product or person is named here.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

STEP = re.compile(r"^###\s*Step\s+\d+\s*·\s*`([^`]+)`\s*·\s*start picture for\s+(S[\w.]+?)(?:-shot-(\d+))?\s*$", re.M)


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def steps_of(handoff: Path) -> list:
    """[(file name, scene, shot number)] for every start-picture step in the hand-off's RUN.md."""
    text = (Path(handoff) / "RUN.md").read_text()
    return [(m.group(1), m.group(2), int(m.group(3) or 1)) for m in STEP.finditer(text)]   # one shot: no -shot-N


def is_print(f: Path) -> bool:
    rec = _read(Path(str(f) + ".made.json"), {}) or {}
    return rec.get("job") == "3d-print"


def _sha(f: Path) -> str:
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def shot_ids(run: Path) -> dict:
    """{scene: [shot id, …]} in the brief's own order (a split scene's left shots, then its right): the hand-off's
    shot N is the scene's N-th shot."""
    rj = _read(Path(run) / "run.json", {}) or {}
    bf = Path(rj.get("brief_from") or Path(run) / "brief.md")
    if not bf.is_absolute():
        bf = Path(__file__).resolve().parents[3] / bf
    try:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", bf.read_text(), re.S)
        doc = json.loads(blocks[-1]) if blocks else {}
    except (OSError, ValueError):
        return {}
    out = {}
    for s in doc.get("scenes") or []:
        ids = [sh.get("id") for sh in s.get("shots") or []]
        ids += [sh.get("id") for side in ("left", "right") for sh in ((s.get("split") or {}).get(side) or {}).get("shots") or []]
        out[s.get("id")] = [x for x in ids if x]
    return out


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(f"tp_{name}", Path(__file__).resolve().parent / f"{name}.py")
    m = u.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def paste_products(run: Path, pic: Path, scene: str, paste=None) -> dict:
    """THE REAL PRODUCT, PASTED, on every taken print (owner, 2026-11-20: the picture model redraws a label whatever
    reference it gets; product_paste.py, 2026-10-09: "the picture model never gets the last word on the product").
    Each product the scene uses (its product elements and every banked product its words name) is pasted from its
    kit's real cut-outs over the drawn one; the print as taken is kept as media/versions/<name>-before-paste.png. The
    result per product is recorded beside the picture as <name>.paste.json, which the clip checklist reads."""
    run, pic = Path(run), Path(pic)
    cr = _load("clip_refs")
    ws = Path(__file__).resolve().parents[3]
    ids = cr.product_ids(run, {"scenes": [scene]}, ws)
    rec = {}
    if not ids:
        return rec
    keep = run / "media" / "versions" / f"{pic.stem}-before-paste{pic.suffix}"
    if not keep.exists():
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pic, keep)
    paste = paste or _load("product_paste").run
    for pid in ids:
        kit = ws / "runs" / "ai-elements" / str(cr.brand_of(run)) / "products" / pid
        what = (_read(kit / "kit.json", {}) or {}).get("what") or pid.replace("-", " ")
        try:
            got = paste(str(pic), kit, out=str(pic), what=what)
        except Exception as e:  # noqa: BLE001 -- a paste that cannot run is said, never a pass
            got = {"ok": False, "why": [f"{type(e).__name__}: {str(e)[:160]}"]}
        rec[pid] = {k: v for k, v in (got or {}).items() if k in ("ok", "angle", "overlap", "skipped", "why")}
    (pic.parent / f"{pic.stem}.paste.json").write_text(json.dumps(
        {"picture_sha": _sha(pic), "products": rec, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1) + "\n")
    return rec


def paste_all(run: Path, paste=None) -> dict:
    """The real product pasted into every print the run already took (start pictures and shot pictures) whose paste
    record is missing or older than the picture: {picture: {product: result}}."""
    run = Path(run)
    made = _read(run / "direct.json", {}) or {}
    pics = [(k.split("-")[0], Path(v["file"])) for k, v in made.items()
            if isinstance(v, dict) and v.get("door") == "3d-print" and v.get("file")]
    for sc, rows in (_read(run / "shot-pictures.json", {}) or {}).items():
        pics += [(sc, Path(r["file"])) for r in rows if r.get("file")]
    out = {}
    for scene, pic in pics:
        if not pic.is_file():
            continue
        rec = _read(pic.parent / f"{pic.stem}.paste.json", {}) or {}
        if rec.get("picture_sha") == _sha(pic):
            continue                                   # pasted already, and the picture has not changed since
        out[pic.name] = paste_products(run, pic, scene, paste=paste)
    return out


def take(run: Path, handoff: Path, dry: bool = False) -> dict:
    run, handoff = Path(run), Path(handoff)
    names = shot_ids(run)
    got = Path(handoff) / "returned"
    made = _read(run / "direct.json", {}) or {}
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    res = {"taken": {}, "kept": {}, "refused": {}, "extra": {}, "missing": []}
    for name, scene, shot in steps_of(handoff):
        f = got / name
        if not f.is_file():
            res["missing"].append(name)
            continue
        if not is_print(f):
            res["refused"][name] = "no 3d-print record beside it (.made.json job 3d-print)"
            continue
        if shot != 1:
            # a later shot's own print: the opening picture of that shot inside the scene's call (clips_run
            # `shot_pictures`), kept in the run's media beside the start frame
            dst = run / "media" / f"{scene}-shot-{shot}.png"
            ids = names.get(scene) or []
            sid = ids[shot - 1] if len(ids) >= shot else f"{scene}.{shot}"
            res["extra"].setdefault(scene, []).append({"shot": sid, "file": str(dst), "from": str(f)})
            if not dry:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    shutil.copy2(f, dst)
                    paste_products(run, dst, scene)
            continue
        frame = f"{scene}-F1"
        dst = run / "media" / f"{frame}.png"
        old = made.get(frame) or {}
        if old.get("file") and Path(old["file"]).is_file() and _sha(old["file"]) != _sha(f):
            res["kept"][frame] = "the run already has a different picture for it: " + str(old["file"])
            continue
        res["taken"][frame] = str(f)
        if dry:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        paste_products(run, dst, scene)
        made[frame] = {"file": str(dst), "model": "3d set print", "door": "3d-print", "taken_from": str(f),
                       "record": str(f) + ".made.json", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "note": "a finished 3D set print taken as the start picture: nothing generated, nothing spent"}
    fresh = [k for k, v in res["taken"].items() if (made.get(k) or {}).get("taken_from") == v
             and (made.get(k) or {}).get("at", "") >= stamp]
    if not dry and fresh:
        # re-read just before writing and add only what this pass took: a live run may have written in between
        now = _read(run / "direct.json", {}) or {}
        now.update({k: made[k] for k in fresh})
        (run / "direct.json").write_text(json.dumps(now, indent=1, ensure_ascii=False) + "\n")
    if not dry:
        (run / "taken-prints.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
        (run / "shot-pictures.json").write_text(json.dumps(
            {sc: [{"shot": x["shot"], "file": x["file"]} for x in rows] for sc, rows in res["extra"].items()},
            indent=1, ensure_ascii=False) + "\n")
    return res


SET_PIC = re.compile(r"-(s\d+[a-z]?)-(?:(f1)|shot-(\d+))$")


def _set_gate():
    root = Path(__file__).resolve().parents[2] / "image-production"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from image_production import set_gate
    return set_gate


def take_sets(run: Path, brand: str, dry: bool = False, sets_root=None) -> dict:
    """Every kept set print filed for this run's own pictures (the 3d-print queue's `<run>-<scene>-f1` and
    `<run>-<scene>-shot-<n>` sets, 2026-11-21) IS that picture: copied to media/<scene>-F1.png or
    media/<scene>-shot-<n>.png, recorded in direct.json (door 3d-print) and shot-pictures.json. Nothing is generated
    and nothing is spent. A picture the run already has that is NOT a set print (a still a door generated) is moved
    to media/versions/<frame>-generated-<stamp>.png and the print takes its place; a set print already there is left.
    {taken, shots, set_aside, waiting}."""
    run = Path(run)
    sg = _set_gate()
    base = Path(sets_root) if sets_root else Path(__file__).resolve().parents[3] / "runs" / "image-production" / brand / "sets"
    pre = re.sub(r"[^a-z0-9]+", "-", run.name.lower()).strip("-")
    made = _read(run / "direct.json", {}) or {}
    names = shot_ids(run)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    res = {"taken": {}, "shots": {}, "set_aside": {}, "waiting": []}
    shots = _read(run / "shot-pictures.json", {}) or {}
    for d in sorted(base.glob(pre + "-s*")) if base.is_dir() else []:
        m = SET_PIC.search(d.name[len(pre):]) if d.name.startswith(pre + "-") else None
        if not m:
            continue
        scene = m.group(1).upper()
        kp = sg.kept_print(brand, d.name)
        if kp is None:
            res["waiting"].append(d.name)
            continue
        if m.group(2):
            frame, dst = f"{scene}-F1", run / "media" / f"{scene}-F1.png"
        else:
            n = int(m.group(3))
            frame, dst = f"{scene}-shot-{n}", run / "media" / f"{scene}-shot-{n}.png"
        if dst.is_file() and _sha(dst) == _sha(kp):
            side = dst.parent / f"{dst.name}.print.json"
            if not dry and (_read(side, {}) or {}).get("print") != str(kp):
                side.write_text(json.dumps({"print": str(kp)}) + "\n")
            continue                                   # already this print
        if dst.is_file() and not sg.is_kept_print(brand, dst):
            aside = run / "media" / "versions" / f"{frame}-generated-{stamp}.png"
            res["set_aside"][frame] = str(aside)
            if not dry:
                aside.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(aside))
        if dry:
            (res["taken"] if m.group(2) else res["shots"])[frame] = str(kp)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kp, dst)
        # the picture's print record names the print it now is (2026-11-21: a reprinted picture kept naming its old
        # print, so the picture inventory judged the new picture against the old one)
        (dst.parent / f"{dst.name}.print.json").write_text(json.dumps({"print": str(kp)}) + "\n")
        # a kept image-production print made with the products' casting sheets is the real product (the clip
        # checklist's rule): the paste record says so for each product the set's request carried
        req = _read(base.parent / "set-requests" / f"{d.name}.json", {}) or {}
        pids = [str(k.get("kit") if isinstance(k, dict) else k) for k in req.get("products") or []]
        (dst.parent / f"{dst.stem}.paste.json").write_text(json.dumps(
            {"picture_sha": _sha(dst), "products": {pid: {"ok": True, "skipped": "kept image-production print made "
                                                                                 "with its casting sheet"} for pid in pids},
             "from_set": d.name, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1) + "\n")
        if m.group(2):
            res["taken"][frame] = str(kp)
            made[frame] = {"file": str(dst), "model": "3d set print", "door": "3d-print", "taken_from": str(kp),
                           "set": d.name, "record": f"runs/image-production/{brand}/sets/{d.name}/set.json", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "note": "the kept 3D set print taken as the start picture: nothing generated, nothing spent"}
        else:
            ids = names.get(scene) or []
            sid = ids[n - 1] if len(ids) >= n else f"{scene}.{n}"
            rows = [r for r in shots.get(scene) or [] if r.get("file") != str(dst)]
            shots[scene] = sorted(rows + [{"shot": sid, "file": str(dst)}], key=lambda r: str(r["file"]))
            res["shots"][frame] = str(kp)
    if not dry and (res["taken"] or res["shots"]):
        now = _read(run / "direct.json", {}) or {}
        now.update({k: made[k] for k in res["taken"]})
        (run / "direct.json").write_text(json.dumps(now, indent=1, ensure_ascii=False) + "\n")
        (run / "shot-pictures.json").write_text(json.dumps(shots, indent=1, ensure_ascii=False) + "\n")
        (run / "taken-sets.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--handoff")
    ap.add_argument("--sets", metavar="BRAND", help="take this run's kept 3D set prints from the brand's filed sets")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--paste", action="store_true", help="paste the real product into every print already taken")
    a = ap.parse_args(argv)
    if a.paste:
        for pic, rec in paste_all(Path(a.run)).items():
            print(pic, json.dumps(rec))
        return 0
    if a.sets:
        r = take_sets(Path(a.run), a.sets, a.dry_run)
        for k, v in list(r["taken"].items()) + list(r["shots"].items()):
            print(f"{'would take' if a.dry_run else 'took'} {k} ← {v}")
        for k, v in r["set_aside"].items():
            print(f"set aside {k} (a generated picture, not a set print) → {v}")
        for k in r["waiting"]:
            print(f"waiting {k}: no kept print yet")
        print(f"{len(r['taken'])} start picture(s), {len(r['shots'])} shot picture(s) from kept set prints")
        return 0
    if not a.handoff:
        ap.error("--handoff or --sets is needed to take prints")
    res = take(Path(a.run), Path(a.handoff), a.dry_run)
    for k, v in res["taken"].items():
        print(f"{'would take' if a.dry_run else 'took'} {k} ← {Path(v).name}")
    for k, v in res["kept"].items():
        print(f"kept {k}: {v}")
    for k, v in res["refused"].items():
        print(f"REFUSED {k}: {v}")
    for k in res["missing"]:
        print(f"missing {k}")
    print(f"{len(res['taken'])} start picture(s), {sum(len(v) for v in res['extra'].values())} more shot print(s) listed")
    return 2 if res["refused"] else 0


if __name__ == "__main__":
    sys.exit(main())
