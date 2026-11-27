#!/usr/bin/env python3
"""What the maker builds first, for a maker pack: the written brief itself, and its ELEMENTS table with the real files.

16 Nov 2026 walkthrough (the maker's view, top to bottom): the pack named "KORY cast sheet", the style frame and the
product photo without carrying any of them, so the maker could not make clip one. Now every pack carries:
  brief/<key>-brief.md     the written brief (its PRODUCT, PROPS and CAMERA sections rule every clip)
  ELEMENTS.md, elements.json  every person, look, voice, setting, product and prop to build ONCE, its scenes, its real
                           reference and status, with the files: the swipe frames it names, the product's real pictures
  refs/elements/<element>/ those files
Spends nothing.
"""
import json
import re
import shutil
import sys
from pathlib import Path


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "element"


def _product_pictures(ws, brand, bank):
    try:
        sys.path.insert(0, str(ws / "components" / "brandpath"))
        import brandpath as BP
        img = Path(BP.brand_root(brand)) / "products" / "images"
    except Exception:  # noqa: BLE001 — the workspace's own brand folder
        img = ws / "brands" / brand / "products" / "images"
    stem = re.sub(r"[^a-z0-9]+", "-", str(bank).lower()).strip("-")
    if not img.is_dir() or not stem:
        return []
    return [f for f in sorted(img.glob(stem + "*"))
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and f.stat().st_size < 8_000_000][:8]


def _from_scenes(production, order, briefs, writing):
    """Every scene's own elements, resolved in the ad's style (video-production styles/style_chain.scene_refs): each
    person's sheet, the set's 3D print, the product's picture, the ad's look. -> {name: {kind, files, scenes}}."""
    found = {}
    try:
        here = Path(__file__).resolve().parent
        sys.path.insert(0, str(here.parents[1] / "video-production" / "styles"))
        import style_chain as SC
    except Exception:  # noqa: BLE001 — no style chain here: the brief's own table stands alone
        return found
    def add(name, kind, f, sid, note=""):
        if not f or not Path(str(f)).is_file():
            return
        e = found.setdefault(name, {"kind": kind, "files": [], "scenes": [], "note": note})
        if str(f) not in e["files"]:
            e["files"].append(str(f))
        if sid not in e["scenes"]:
            e["scenes"].append(sid)
    for sid in order:
        try:
            r = SC.scene_refs(production, sid, briefs=Path(briefs), writing=Path(writing))
        except Exception:  # noqa: BLE001 — a scene the chain cannot resolve keeps the brief's own words
            continue
        for p in r.get("people") or []:
            add(p.get("name") or p.get("element"), "person", p.get("path"), sid, p.get("element") or "")
        s = r.get("set") or {}
        add(s.get("name") or s.get("id") or "set", "setting", r.get("set_print"), sid, "3D print" if s.get("print") else "")
        pr = r.get("product") or {}
        add(pr.get("id") or "product", "product", pr.get("picture"), sid, pr.get("where") or "")
        lk = r.get("look") or {}
        add("the ad's look (" + str(r.get("style") or "style") + ")", "look", lk.get("file") if isinstance(lk, dict) else lk, sid)
    return found


def _real_product_photos(ws, brand, product):
    """The product's real photos from its bank folder (runs/ai-elements/<brand>/products/<id>/sources): the packshots
    and the tube front/back, for the end card of an ad made in another style (song-ad: only the end card is real)."""
    src = Path(ws) / "runs" / "ai-elements" / brand / "products" / str(product) / "sources"
    if not src.is_dir():
        return []
    return [f for f in sorted(src.iterdir()) if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            and re.search(r"packshot|tube|front", f.name, re.I) and f.stat().st_size < 8_000_000][:4]


def build(out, writing_run, key, brand, ws, production=None, order=(), briefs=None, extra=None, clips=None):
    out, W = Path(out), Path(writing_run)
    src = W / "stages" / "5-brief.md"
    if not src.exists():
        src = Path("/dev/null")
    (out / "brief").mkdir(exist_ok=True)
    if src.is_file():
        shutil.copy2(src, out / "brief" / ("%s-brief.md" % key))
    frames = W / "framemap" / "shots"
    m = re.search(r"## ELEMENTS\s*\n(.*?)\n\n", src.read_text() if src.is_file() else "", re.S)
    rows = []
    for line in (m.group(1).splitlines() if m else [])[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        name, kind, bank, scenes, ref, status = cells[:6]
        d = out / "refs" / "elements" / _slug(name)
        files = []
        picks = [frames / ("K%s-%s.jpg" % (k, part)) for k in sorted(set(re.findall(r"K(\d{2,3})", ref)))
                 for part in ("first", "mid", "last")]
        if kind == "product":
            picks += _product_pictures(Path(ws), brand, bank)
        for f in picks:
            if f.exists():
                d.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d / f.name)
                files.append("refs/elements/%s/%s" % (_slug(name), f.name))
        rows.append({"element": name, "kind": kind, "bank": bank, "scenes": scenes, "reference": ref,
                     "status": status, "files": files})
    if production and briefs:                   # the scenes' own files in the ad's style (17 Nov: a 3D ad's sheets)
        have = {r["element"].upper(): r for r in rows}
        for name, e in _from_scenes(production, order, briefs, W.parent).items():
            d = out / "refs" / "elements" / _slug(name)
            files = []
            for f in e["files"]:
                d.mkdir(parents=True, exist_ok=True)
                dst = d / (Path(f).parent.name + "-" + Path(f).name if (d / Path(f).name).exists() else Path(f).name)
                shutil.copy2(f, dst)
                files.append("refs/elements/%s/%s" % (_slug(name), dst.name))
            row = have.get(str(name).upper())
            if row:
                row["files"] += [x for x in files if x not in row["files"]]
                row["status"] = (row["status"] + " · BANKED here") if "BANKED" not in row["status"] else row["status"]
            else:
                rows.append({"element": name, "kind": e["kind"], "bank": e.get("note") or "", "scenes": ", ".join(e["scenes"]),
                             "reference": "banked in the ad's style", "status": "BANKED (use these files)", "files": files})
    have = {r["element"].upper(): r for r in rows}
    for x in extra or []:                       # places a clip is set in that its scene's own set does not name (18 Nov)
        row = have.get(str(x["name"]).upper())
        if row is None:
            row = {"element": x["name"], "kind": x["kind"], "bank": "", "scenes": "", "reference": "banked in the ad's style"
                   if x.get("file") else "none banked", "status": "BANKED (use these files)" if x.get("file") else "TO MAKE",
                   "files": []}
            rows.append(row)
            have[str(x["name"]).upper()] = row
        if x.get("scene") and x["scene"] not in row["scenes"]:
            row["scenes"] = ", ".join([s for s in str(row["scenes"]).split(", ") if s] + [x["scene"]])
        if x.get("file"):
            d = out / "refs" / "elements" / _slug(x["name"])
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x["file"], d / Path(x["file"]).name)
            f = "refs/elements/%s/%s" % (_slug(x["name"]), Path(x["file"]).name)
            if f not in row["files"]:
                row["files"].append(f)
    for row in [r for r in rows if r["kind"] == "product"]:
        real = _real_product_photos(ws, brand, row["element"])
        if real:
            d = out / "refs" / "elements" / _slug(row["element"]) / "real-photo"
            d.mkdir(parents=True, exist_ok=True)
            for f in real:
                shutil.copy2(f, d / f.name)
            row["files"] += ["refs/elements/%s/real-photo/%s" % (_slug(row["element"]), f.name) for f in real]
            row["reference"] = str(row["reference"]) + " · real photos in real-photo/: the end card only"
    if clips:                                   # named by the clips that use them, with every look a clip uses (18 Nov
        for row in rows:                        # cold run, notes 8 and 10: scene numbers read as clip numbers, and two
            stem = _slug(row["element"])[:30]   # of creator's looks reached clips but not this table)
            mine = []
            for c in clips:
                hit = [r for r in c.get("refs") or [] if Path(r).name.startswith(stem + "-")]
                if hit or (row["kind"] == "look" and any("the-ad-s-look" in r for r in c.get("refs") or [])):
                    mine.append(c["id"])
                for r in hit:
                    if "look-" not in Path(r).name or not (out / r).is_file():
                        continue
                    d = out / "refs" / "elements" / _slug(row["element"])
                    d.mkdir(parents=True, exist_ok=True)
                    name = Path(r).name[len(stem) + 1:]
                    if not any(Path(f).name.endswith(name) for f in row["files"]):
                        shutil.copy2(out / r, d / name)
                        row["files"].append("refs/elements/%s/%s" % (_slug(row["element"]), name))
            if mine:
                row["scenes"] = ", ".join(dict.fromkeys(mine))
    (out / "elements.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    L = ["# Build these first · %s" % key, "",
         "Every clip uses these. An element marked BANKED is already made: use its files as they are. Build each element "
         "still TO MAKE once, from its real reference, and reuse it in every clip it is in; each person looks the same in "
         "every clip. The full brief is `brief/%s-brief.md`: its product, props and camera notes are the rules for every "
         "clip. The product is never drawn from words: use its picture here (the real photo, or its banked picture in the "
         "ad's style)." % key, "",
         "| Element | Kind | %s | Reference | Status | Files here |" % ("Clips" if clips else "Scenes"), "|---|---|---|---|---|---|"]
    for r in rows:
        shown = ", ".join("`%s`" % f for f in r["files"])          # every file, never "+N more" (a look hid there)
        L.append("| %s | %s | %s | %s | %s | %s |" % (r["element"], r["kind"], r["scenes"], r["reference"], r["status"], shown or "–"))
    (out / "ELEMENTS.md").write_text("\n".join(L) + "\n")
    return rows
