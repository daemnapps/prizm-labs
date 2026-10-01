#!/usr/bin/env python3
"""Stage 8 — the pictures. Two halves, because the generator is reached through
the session's own Higgsfield connection, not from a script:

    python3 pictures.py scrub-base-01 --page base           # -> pictures-request[-<sub>].json
        every picture brief in the layout, as a generation request: prompt,
        aspect, model, and the brand reference photographs to attach (by
        media_id from references.json). The session submits these.

    python3 pictures.py scrub-base-01 --page base --record results.json
        results.json: [{"id": "...", "url": "https://..."}] from the generator.
        Downloads each into the brand's page-kit project under
        src/<funnel>/assets/images/<page-name>/<id>.<ext> and writes
        pictures[-<sub>].json (id -> asset path) for the build step.

Brand-agnostic: the only brand-specific thing is which photographs are on file,
and those are read from the run's references.json.
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "machine"))
import page_paths as P   # noqa: E402
WORKSPACE = P.WORKSPACE   # AI_WORKSPACE, else found by walking up — never counted
MODEL = "gpt_image_2"          # the general photoreal model; takes reference images in the `image` role
QUALITY = "medium"

NEVER = ("No text, lettering, numbers, logos, labels, badges, watermarks or graphic overlays anywhere in the image. "
         "No camera, phone, tripod or lighting equipment in frame. No invented packaging. "
         "The woman, where one appears, is in her late fifties to sixties with her real skin: fine lines and veins stay.")


def load(run, page):
    suffix = "" if page == "base" else f"-{page}"
    plan = json.loads((run / f"layout{suffix}.json").read_text())
    # a picture that exists under another id is a reuse, not a new brief
    aliases = json.loads((run / "picture-aliases.json").read_text()) if (run / "picture-aliases.json").exists() else {}
    base = json.loads((run / "pictures.json").read_text()) if (run / "pictures.json").exists() else {}
    made_here = json.loads((run / f"pictures{suffix}.json").read_text()) if (run / f"pictures{suffix}.json").exists() else {}
    for sec in plan["sections"]:
        for pic in sec.get("pictures", []):
            for key in ("reuse", "id"):
                v = pic.get(key)
                if v in aliases:
                    pic["reuse"] = aliases[v]; break
            if not pic.get("reuse") and not pic.get("use") and pic.get("id") in base and page != "base":
                pic["reuse"] = pic["id"]
    refs = json.loads((run / "references.json").read_text())["references"] if (run / "references.json").exists() else {}
    return plan, refs, suffix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label"); ap.add_argument("--page", default="base")
    ap.add_argument("--record", default=None); ap.add_argument("--dest", default=None,
                    help="the brand's page-kit project (default ~/Projects/<brand>-pages)")
    a = ap.parse_args()
    run = P.need_run(a.label)   # either home: runs/page-machine/<brand>/, then the old runs/
    state = json.loads((run / "run.json").read_text())
    plan, refs, suffix = load(run, a.page)
    page_name = plan["page_name"]

    if not a.record:
        reqs = []
        for s in plan["sections"]:
            for pic in s.get("pictures", []):
                if pic.get("reuse") or pic.get("use") or pic.get("aspect") in (None, "none"):
                    continue
                medias = []
                for att in pic.get("attach") or []:
                    if att and att != "none" and att in refs:
                        medias.append({"value": refs[att]["media_id"], "role": "image"})
                    elif att and att != "none":
                        print(f"  ! {pic['id']}: reference {att} is not uploaded — generating without it")
                prompt = pic["brief"].strip()
                if medias:
                    prompt += " Match the attached reference photograph exactly for the product's colour, label and the scrub's colour and texture."
                prompt += " " + NEVER
                reqs.append({"id": pic["id"], "field": pic["field"], "block": s["block"],
                             "params": {"model": MODEL, "prompt": prompt, "aspect_ratio": pic["aspect"],
                                        "quality": QUALITY, "medias": medias}})
        out = run / f"pictures-request{suffix}.json"
        out.write_text(json.dumps(reqs, indent=1))
        print(f"{len(reqs)} pictures to make for {page_name} -> {out.name}")
        return

    results = {r["id"]: r["url"] for r in json.loads(Path(a.record).read_text())}
    dest = Path(a.dest).expanduser() if a.dest else Path.home() / "Projects" / f"{state['brand']}-pages"
    imgdir = dest / "src" / state["funnel"] / "assets" / "images" / page_name
    imgdir.mkdir(parents=True, exist_ok=True)
    # what this page already has on file — a record is never thrown away by a re-run
    prev_path = run / f"pictures{suffix}.json"
    prev = json.loads(prev_path.read_text()) if prev_path.exists() else {}
    base_made = json.loads((run / "pictures.json").read_text()) if (run / "pictures.json").exists() and page_name != state["page_name"] else {}
    made = {}
    for s in plan["sections"]:
        for pic in s.get("pictures", []):
            pid = pic["id"]
            if pic.get("reuse"):
                # resolve to the file itself: the base page's folder, or this page's
                images_root = dest / "src" / state["funnel"] / "assets" / "images"
                hit = sorted(images_root.glob(f"{state['page_name']}*/{pic['reuse']}.*"))
                if hit:
                    rel = hit[0].relative_to(dest / "src" / state["funnel"] / "assets")
                    made[pid] = {"asset": str(rel), "reuse": pic["reuse"], "field": pic["field"], "block": s["block"]}
                else:
                    print(f"  ! reuse {pic['reuse']} for {pid}: no file on disk")
                continue
            if pic.get("use"):
                srcp = WORKSPACE / pic["use"]
                if not srcp.exists():
                    print(f"  ! {pid}: {pic['use']} is not on file"); continue
                path = imgdir / f"{pid}{srcp.suffix.lower()}"
                path.write_bytes(srcp.read_bytes())
                made[pid] = {"asset": f"images/{page_name}/{path.name}", "used": pic["use"], "field": pic["field"], "block": s["block"]}
                print("  used", pic["use"]); continue
            url = results.get(pid)
            if not url:
                # already made earlier, on file: keep the record
                kept = prev.get(pid) or {}
                if kept.get("asset") and (dest / "src" / state["funnel"] / "assets" / kept["asset"]).exists():
                    made[pid] = kept; continue
                on_disk = sorted(imgdir.glob(f"{pid}.*"))
                if on_disk:
                    made[pid] = {"asset": f"images/{page_name}/{on_disk[0].name}", "field": pic["field"], "block": s["block"]}; continue
                if base_made.get(pid, {}).get("asset"):
                    made[pid] = {"reuse": pid}; continue
                print(f"  ! no result for {pid}"); continue
            # the generator hands back a 1–2 MB PNG; the page wants a web-sized JPEG
            raw = imgdir / f"{pid}.download"
            urllib.request.urlretrieve(url, raw)
            path = imgdir / f"{pid}.jpg"
            try:
                from PIL import Image
                im = Image.open(raw).convert("RGB")
                im.thumbnail((1600, 1600))
                im.save(path, "JPEG", quality=86, optimize=True, progressive=True)
                raw.unlink()
            except Exception as e:
                print(f"  ! {pid}: could not convert ({e}); keeping the original")
                raw.rename(imgdir / f"{pid}.png"); path = imgdir / f"{pid}.png"
            for old in imgdir.glob(f"{pid}.*"):
                if old != path: old.unlink()
            made[pid] = {"asset": f"images/{page_name}/{path.name}", "url": url, "field": pic["field"], "block": s["block"]}
            print("  saved", path.relative_to(dest))
    (run / f"pictures{suffix}.json").write_text(json.dumps(made, indent=1))
    print(f"recorded {len(made)} pictures -> pictures{suffix}.json")


if __name__ == "__main__":
    main()
