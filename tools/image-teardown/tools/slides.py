#!/usr/bin/env python3
"""The slides — a list carousel made slide by slide, each from the swipe's own slide.

    python3 tools/slides.py <run> --brand <brand> --product <slug> [--only 3,5] [--tries 3] [--dry-run]

the owner, 2026-10-25: "we have that whole looksmaxxing clipper breakdown with each of those carousels, we need to
build more carousels." The winning clipper carousels are LISTS: a portrait with the hook, then one category per
slide, each its own layout (a 2x2 grid of tips, a bad-habit-vs-fix split). The carousel road (tools/carousel.py)
makes every later slide as one change off slide one, which cannot turn a portrait into a grid. Here slide N is
made from the swipe's own slide N as the picture reference and the AI sequence brief's own "## Slide N" (what it
shows and what it says), with the brief's thread on every slide. Every slide is finished the way a still is
(tools/pictures.py): the real product laid in
where the slide shows it and the words kept on top of it, the swipe slide's own fidelity.

Needs the run torn down as a sequence (vars/route.json form sequence, out/06-brief.md the AI sequence brief).
A slide plan beside the run, vars/slides.json ({"thread", "slides": {"N": "**Shows:** ... **Says:** ..."}, "refs":
{"N": "<picture from the repo root>"}}), is read before the brief's slide sections: for when stage 6 withheld its
picture lines or cut a grid's tiles, and for a slide the swipe has none for (refs), such as our CTA end card.
Writes runs/image-edit/<brand>/clipper-carousels/<run>/: slide-NN.png in order (the folder
components/meta-upload/feed_carousel.py files as one card), each slide's own image-production record under
work/slide-NN/, and sheet.jpg (the swipe's slides over ours). Slides run at the same time. Nothing reaches Meta.
"""
import argparse, json, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402
import pictures as PIC  # noqa: E402

MAKE = PIC.MAKE


def slide_sections(brief):
    """{n: the brief's own "## Slide n" section}, and its thread (identical on every slide)."""
    t = brief.read_text()
    secs = {int(m.group(1)): m.group(2).strip()
            for m in re.finditer(r"(?ms)^## Slide (\d+)\s*\n(.*?)(?=^#{1,2} )", t)}
    th = re.search(r"(?ms)^## The thread[^\n]*\n(.*?)(?=^#{1,2} )", t)
    return secs, (th.group(1).strip() if th else "")


def shows_product(sec, name):
    """The slide puts the product in frame: named in what it shows or says (as the brief writes product names, in
    capitals), and not negated."""
    body = re.split(r"(?m)^\*\*Why they swipe", sec)[0]
    neg = r"\b(no|not|never|without)\b[^.\n]{0,40}$"
    return any(not re.search(neg, body[:m.start()], re.I) for m in re.finditer(r"\b" + re.escape(name) + r"\b", body))


def kits(brand, lead):
    """{slug: (name, kit folder, its real front photo)} for every product of the brand that has a product kit, the
    run's own product first. A slide may show several (the owner, 2026-10-25: "every product is mentioned in there for
    that, that the Flex or the formulations can do")."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("element_paths", str(P.REPO / "tools/video-production/machine/element_paths.py"))
    ep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ep)
    out = {}
    slugs = [lead] + sorted(p.stem for p in (P.REPO / "brands" / brand / "products").glob("*.md") if p.stem != lead)
    for s in slugs:
        try:
            k = ep.product_kit(brand, s)
        except Exception:
            k = None
        if not k:
            continue
        front = next((k / "model" / n for n in ("reference-front-transparent.png", "packshot-cutout.png", "front.png")
                      if (k / "model" / n).is_file()), None)
        name = PIC.product_name(brand, s)
        if name not in {v[0] for v in out.values()}:          # one product per name: WIDGET, not also its case
            out[s] = (name, k, front)
    return out


def looks(kit):
    """ " (what it looks like)", the kit's own words (kit.json `what`), so the drawn stand-in has the real one's shape
    and the real photo can be laid over it."""
    f = Path(kit) / "kit.json"
    w = json.loads(f.read_text()).get("what") if f.is_file() else None
    return f" ({w})" if w else ""


def direction(n, sec, thread, names):
    parts = [
        f"Remake IMAGE 1 (slide {n} of a real slideshow post) as slide {n} of ours: keep its layout, framing, camera, "
        "light, type treatment and where every word sits exactly, and change only what this slide's plan below says.",
        PIC.FIDELITY + " " + PIC.OWN_COLOURS,
        "THE THREAD (the same on every slide of this carousel): " + thread if thread else "",
        f"THIS SLIDE'S PLAN (what it shows, and the words it says, set exactly as written, in IMAGE 1's own type "
        f"style and places; nothing else written on the picture; no long dashes):\n{sec}",
        "Every person is a generated young man, clearly a different person from anyone in IMAGE 1. "
        "Any logo, label or brand mark in IMAGE 1 becomes a plain, unbranded item: the only brand on this slide is "
        + ((" and ".join(names) + ", each drawn exactly as its own attached real photo (its shape, colour and label), at "
            "its real size, where the plan puts it. A product being used is held so most of it shows: fingertips at its "
            "edges, never a fist round it.") if names else "none."),
    ]
    return "\n\n".join(p for p in parts if p)


def make_slide(run, brand, products, n, sec, thread, swipe, root, tries, dry, drawn=False):
    """One slide: made, finished, copied to slide-NN.png. Retried with the held reason, up to `tries`."""
    work = root / "work" / f"slide-{n:02d}"
    work.mkdir(parents=True, exist_ok=True)
    shown = [s for s, (nm, _k, _f) in products.items() if shows_product(sec, nm)]
    in_frame = bool(shown)
    note = ""
    for k in range(1, tries + 1):
        cmd = [sys.executable, str(MAKE), "--brand", brand, "--purpose", "ad", "--aspect", "4:5", "--count", "1",
               "--people", "--direction", direction(n, sec, thread, [products[s][0] + looks(products[s][1]) for s in shown]) + note,
               "--ref", str(swipe), "--out", str(work), "--label", f"{run.name}-slide-{n:02d}-r{k}"]
        lead = next(iter(products))                          # the run's own product: its photo and facts ride with --product
        if lead in shown:
            # laid in (default): the real photo replaces the drawn one afterwards. drawn: the product is drawn from its
            # real photo and the judge checks it against that photo, the way the owner makes in-use shots in Higgsfield
            cmd += ["--product", lead, "--no-product-3d"] + ([] if drawn else ["--product-after"])
        for s in shown:                                      # every other product: its kit's own real photo as a reference
            if s != lead and products[s][2]:                 # (a formula's stored product photo can be its label, not the pack)
                cmd += ["--ref", str(products[s][2])]
        if dry:
            cmd.append("--dry-run")
        r = subprocess.run(cmd, capture_output=True, text=True)
        made = [Path(m) if Path(m).is_absolute() else P.REPO / m for m in re.findall(r"✓ (\S+\.png)", r.stdout + r.stderr)]
        if dry:
            return {"slide": n, "product": [products[s][0] for s in shown], "dry": r.returncode == 0}
        pic = next((m for m in made if m.is_file()), None)
        if pic:
            for s in ([] if drawn else shown):                # every product on the slide, its real photo laid in
                if pic.is_file():
                    PIC.real_product(brand, s, products[s][0], [pic], work)
            if pic.is_file():
                PIC.native_finish(pic, swipe, work / "polished")
                shutil.copy2(pic, root / f"slide-{n:02d}.png")
                return {"slide": n, "product": [products[s][0] for s in shown], "file": str(root / f"slide-{n:02d}.png"), "tries": k}
        held = [l for l in (r.stdout + r.stderr).splitlines() if re.search(r"✗|held|HELD|reject", l)]
        why = (held[-1].strip() if held else (r.stderr.strip().splitlines() or ["nothing was delivered"])[-1])[:300]
        if pic is not None and (work / "rejected" / (pic.stem + "-why.md")).is_file():
            why = (work / "rejected" / (pic.stem + "-why.md")).read_text().strip()[:300]   # the real product would not lie in
        note = f"\n\nTHE LAST TRY WAS HELD FOR THIS, FIX IT: {why}"
    return {"slide": n, "product": [products[s][0] for s in shown], "file": None, "tries": tries, "why": why}


def plain_slide(run, brand, products, n, sec, swipe, root, tries, dry, thread="", notes=None, prefs=None, people=None):
    """One slide the plain way (tools/image-production plain.make), the way the owner makes them in Higgsfield
    (2026-10-25: "there's a lot of control that I think is messing stuff up", then "literally 1000000x better"): the
    swipe's slide, each product's real pictures and line from its kit, the slide's own lines, in one call. No house
    prompt, no judge, no paste, no grain; the made 4:5 sits on black for the 9:16."""
    sys.path.append(str(P.REPO / "tools" / "image-production"))
    from image_production import plain
    work = root / "work" / f"slide-{n:02d}"
    work.mkdir(parents=True, exist_ok=True)
    shown = [s for s, (nm, _k, _f) in products.items() if shows_product(sec, nm)]
    names = [products[s][0] for s in shown]
    text = ((thread + "\n\n") if thread else "") + sec + "\n\nThe only text on the slide is the words in backticks above, spelled exactly."
    if dry:
        return {"slide": n, "product": names, "dry": True}
    why = ""
    for k in range(1, tries + 1):
        raw = work / f"plain-r{k}.png"
        try:
            plain.make(brand, text, raw, references=[swipe], products=shown, aspect="9:16",
                       product_refs={nm: [P.REPO / x for x in v] for nm, v in (prefs or {}).items()},
                       product_lines=notes or {}, people=people, kind="slide")
        except (Exception, SystemExit) as e:                 # a refusal or a dropped call: once more
            why = f"{type(e).__name__}: {str(e)[:200]}"
            continue
        plain.to_frame(raw, root / f"slide-{n:02d}.png")
        return {"slide": n, "product": names, "file": str(root / f"slide-{n:02d}.png"), "tries": k, "plain": True}
    return {"slide": n, "product": names, "file": None, "tries": tries, "why": why}

def sheet(swipes, root, n_slides):
    """The swipe's slides over ours, one column per slide."""
    from PIL import Image
    W, H = 300, 534
    s = Image.new("RGB", (n_slides * (W + 8), 2 * (H + 8)), "white")
    for n in range(1, n_slides + 1):
        for row, f in enumerate((swipes.get(n), root / f"slide-{n:02d}.png")):
            if f and Path(f).is_file():
                im = Image.open(f).convert("RGB")
                im.thumbnail((W, H))
                s.paste(im, ((n - 1) * (W + 8) + (W - im.width) // 2, row * (H + 8) + (H - im.height) // 2))
    s.save(root / "sheet.jpg", quality=85)
    return root / "sheet.jpg"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run"); ap.add_argument("--brand", required=True); ap.add_argument("--product", required=True)
    ap.add_argument("--only", help="slides to make again, e.g. 3,5 (the others are kept)")
    ap.add_argument("--tries", type=int, default=5)
    ap.add_argument("--plain", action="store_true", help="the plain way: one call with the swipe's slide, the real product photos and the slide's own lines, no house prompt, judge, paste or grain (a plan can also say \"mode\": \"plain\")")
    ap.add_argument("--drawn", action="store_true", help="products in use are drawn from their real photos and judged against them (the owner, 2026-10-25: \"I have no problem when I do this stuff natively in Higgsfield\"), never pasted over; a plan can also say \"products\": \"drawn\"")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    run = P.run_dir(a.run)
    route = json.loads((run / "vars/route.json").read_text()) if (run / "vars/route.json").is_file() else {}
    brief = run / "out/06-brief.md"
    plan_only = (run / "vars" / "slides.json").is_file()
    if route.get("form") != "sequence" or not (brief.is_file() or plan_only):
        sys.exit(f"{a.run}: not a sequence with its AI sequence brief or a slide plan written (vars/route.json, "
                 "out/06-brief.md or vars/slides.json)")
    swipes = {int(m.group(1)): p for p in sorted((run / "assets").glob("source-*"))
              if (m := re.fullmatch(r"source-(\d+)", p.stem))}
    secs, thread = slide_sections(brief) if brief.is_file() else ({}, "")   # a complete slide plan needs no brief
    notes, prefs, people = {}, {}, None
    plan = run / "vars" / "slides.json"
    if plan.is_file():
        # a slide plan beside the run (vars/slides.json: {"thread", "slides": {"N": "**Shows:** … **Says:** …"}})
        # wins over the brief's own slide sections, e.g. when stage 6 withheld its picture lines or cut tiles
        pj = json.loads(plan.read_text())
        secs.update({int(k): v for k, v in (pj.get("slides") or {}).items()})
        # a slide the swipe has no slide for (the CTA end card, the owner 2026-10-25: "we also always need an end slide
        # with a CTA") names its own picture reference: "refs": {"7": "<path from the repo root>"}
        swipes.update({int(k): P.REPO / v for k, v in (pj.get("refs") or {}).items()})
        thread = pj.get("thread") or thread
        a.drawn = a.drawn or pj.get("products") == "drawn"
        a.plain = a.plain or pj.get("mode") == "plain"
        notes, prefs = pj.get("product_notes") or {}, pj.get("product_refs") or {}
        people = pj.get("people")             # "lookalike" (the default with a swipe) or "made-up"
        print(f"{a.run}: the slide plan in vars/slides.json is used before the brief's slide sections")
    want = [int(x) for x in a.only.split(",")] if a.only else sorted(secs)
    missing = [n for n in want if n not in secs or n not in swipes]
    if missing:
        sys.exit(f"{a.run}: no brief section or swipe slide for slide(s) {missing}")
    products = kits(a.brand, a.product)
    root = P.REPO / "runs" / "image-edit" / a.brand / "clipper-carousels" / a.run
    root.mkdir(parents=True, exist_ok=True)
    print(f"{a.run} · {len(want)} slide(s) · each from the swipe's own slide · real products: "
          + ", ".join(v[0] for v in products.values()))
    with ThreadPoolExecutor(max_workers=len(want)) as ex:
        done = list(ex.map(lambda n: plain_slide(run, a.brand, products, n, secs[n], swipes[n], root, a.tries, a.dry_run, thread,
                                                 notes, prefs, people)
                           if a.plain else make_slide(run, a.brand, products, n, secs[n], thread, swipes[n],
                                                root, a.tries, a.dry_run, a.drawn), want))
    for d in sorted(done, key=lambda d: d["slide"]):
        print(f"  slide {d['slide']:>2}" + (f" ({', '.join(d['product'])})" if d["product"] else "") + ": "
              + ("dry run ok" if d.get("dry") else ("✓ " + Path(d["file"]).name if d.get("file") else "✗ " + d.get("why", ""))))
    if not a.dry_run:
        (root / "slides.json").write_text(json.dumps({"run": a.run, "brand": a.brand, "product": a.product,
                                                      "slides": sorted(done, key=lambda d: d["slide"])}, indent=1))
        print(f"  sheet: {sheet(swipes, root, max(secs))}")
    sys.exit(0 if all(d.get("file") or d.get("dry") for d in done) else 1)


if __name__ == "__main__":
    main()
