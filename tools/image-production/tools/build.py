#!/usr/bin/env python3
"""Stage two — brief in, finished ads out. Six machine steps and one of yours.

    build.py <run>                  every step, in order
    build.py <run> --step 7         just that one
    build.py <run> --headline 2     recomposite with headline variation 2

The steps, and what each writes:

    7  make the plates       higgsfield     iterations/plate-<name>.png
    8  judge the plates      gemini + code  out/08-plate-check.md
    9  measure the plate     code           out/09-measure.json
   10  composite the product imagemagick    iterations/<name>-product.png
   11  set the type          imagemagick    finals/ad-<name>.png
   12  prove it              imagemagick    finals/source-vs-<name>.jpg

**Nothing leaves this tool with a defect anyone has already seen.** If a check
fails, the fix happens here — the ad is not handed over with a note attached.
Damon, 2026-08-31: "if you see the problem, then don't fucking deliver it."
A known flaw plus an apology is worse than nothing, because it moves the work
of noticing onto the person who asked for it.

**The brief is the only input.** Not the stage outputs, not the run folder.
If a fact is not in the brief it does not reach the ad — the full reasoning
is in `../README.md` (it was `STAGE-TWO.md` until the split).

Step 8 judges itself. Taste happened upstream, in choosing the brand and the
angle to swipe; from here the questions are factual — is it accurate, does it
make sense, does it work, is it visual — and those are programmable. Measured
checks run off the pixels; the brief's own accept tests go to a vision model
with the plate in front of it. A failing plate is regenerated, not shipped.
"""

import argparse, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def brief_of(run):
    b = run / "out/06-brief.md"
    if not b.is_file():
        sys.exit(f"no brief at {b}. Stage two builds nothing without one.")
    return b.read_text()


# ---------------------------------------------------------------- 7 · plates

def step_plates(run, brief, only=None):
    r = sh([sys.executable, str(P.TOOLS / "generate.py"), str(run)]
           + (["--only", only] if only else []))
    print(r.stdout.rstrip() or r.stderr.rstrip()[-400:])
    made = sorted((run / "iterations").glob("plate-*.png"))
    return made


# ----------------------------------------------------------- 8 · judge them

def step_check(run, brief, retry=2):
    """Judge every plate against the brief's own tests. No human in it."""
    r = subprocess.run([sys.executable, str(P.TOOLS / "judge.py"), str(run),
                        "--retry", str(retry)], text=True)
    return run / "out/08-plate-check.md"


def _unused_manual_check(run, brief):
    """Superseded 2026-08-28: this asked Damon to mark plates PASS or FAIL.
    His ruling — the taste was choosing what to swipe; the rest is
    verification, and verification gets programmed."""
    tests = []
    m = re.search(r"\*\*The accept tests\*\*(.+?)(?:\n\s*##|\Z)", brief, re.S)
    if not m:
        m = re.search(r"\*\*How we will know it is right\.\*\*(.+?)(?:\n\s*\*\*|\Z)",
                      brief, re.S)
    if m:
        for line in m.group(1).splitlines():
            t = line.strip().lstrip("-*0123456789. ").strip()
            if len(t) > 12:
                tests.append(t)

    plates = sorted((run / "iterations").glob("plate-*.png"))
    out = run / "out/08-plate-check.md"
    body = ["# Judge the plates", "",
            "The brief's own accept tests, on the picture alone, before anything",
            "is built on it. A plate that fails gets regenerated or killed — never",
            "composited to see how it looks.", "",
            "**Mark each plate `PASS` or `FAIL` on its line.** Steps 9 to 12 will",
            "not run until a plate says PASS.", ""]
    for p in plates:
        body += [f"## {p.stem}", "", "**Verdict:** UNCHECKED", ""]
        for t in tests:
            body.append(f"- [ ] {t}")
        body += ["- [ ] No legible third-party brand anywhere in frame "
                 "(automatic reject).", ""]
    out.write_text("\n".join(body) + "\n")
    print(f"  wrote {out.relative_to(P.LAB)} — {len(plates)} plate(s), "
          f"{len(tests)} tests each")
    print("  → open the plates, mark each PASS or FAIL, then re-run")
    return out


def passed(run, name):
    f = run / "out/08-plate-check.md"
    if not f.is_file():
        return False
    block = re.search(rf"## {re.escape(name)}\n(.+?)(?=\n## |\Z)",
                      f.read_text(), re.S)
    return bool(block) and "PASS" in block.group(1).upper()


# -------------------------------------------------------- 9 · measure it

def step_measure(run, plate):
    """Where the bands and the inset actually landed on THIS plate.

    The source's numbers describe the source. Carrying them across put a
    headline underneath a product circle on 2026-08-28 — the plate's own
    geometry is what the type gets positioned against.
    """
    w, h = sh(["magick", "identify", "-format", "%w %h", str(plate)]).stdout.split()
    w, h = int(w), int(h)

    # the empty band: the first row from the bottom half that is flat and dark
    col = sh(["magick", str(plate), "-crop", f"1x{h}+{w//5}+0", "+repage", "txt:-"]).stdout
    band = None
    for line in col.splitlines()[1:]:
        try:
            y = int(line.split(":")[0].split(",")[1])
            hx = line.split("#")[1][:6]
        except (IndexError, ValueError):
            continue
        if y < h * 0.4:
            continue
        if all(int(hx[i:i+2], 16) < 14 for i in (0, 2, 4)):
            band = y
            break

    # the inset ring: near-white pixels in the lower-right of the picture area
    ring = sh(["magick", str(plate), "-colorspace", "sRGB", "txt:-"]).stdout
    xs, ys = [], []
    for line in ring.splitlines()[1:]:
        try:
            pos, rest = line.split(":", 1)
            x, y = map(int, pos.split(","))
            hx = rest.split("#")[1][:6]
        except (IndexError, ValueError):
            continue
        if y < h * 0.4 or x < w * 0.5:
            continue
        if all(int(hx[i:i+2], 16) > 235 for i in (0, 2, 4)):
            xs.append(x); ys.append(y)

    out = dict(plate=plate.name, width=w, height=h,
               band_top_px=band, band_top_pct=round(band / h * 100, 1) if band else None,
               inset=None)
    # An inset is a bounded ring, not the page. On a white-ground format the
    # whole background reads as near-white, and taking that as a ring put the
    # real product in a phantom circle in the corner (2026-08-30). So: only
    # trust it on a dark ground, and only if the shape is compact and roughly
    # round.
    ground = sh(["magick", str(plate), "-format", "%[pixel:p{6,6}]",
                 "info:"]).stdout.strip()
    light_ground = "255,255,255" in ground or "white" in ground.lower()
    if xs and len(xs) > 200 and not light_ground:
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        round_enough = bh and 0.75 < bw / bh < 1.35
        small_enough = bw < w * 0.45
        if round_enough and small_enough:
            out["inset"] = dict(cx=(min(xs)+max(xs))//2, cy=(min(ys)+max(ys))//2,
                                r=bw//2,
                                top_pct=round(min(ys)/h*100, 1),
                                bottom_pct=round(max(ys)/h*100, 1))
    f = run / "out/09-measure.json"
    prev = json.loads(f.read_text()) if f.is_file() else {}
    prev[plate.stem] = out
    f.write_text(json.dumps(prev, indent=2) + "\n")
    print(f"  {plate.stem}: {w}x{h}"
          + (f" · empty band from {out['band_top_pct']}%" if band else " · no empty band found")
          + (f" · inset at {out['inset']['top_pct']}-{out['inset']['bottom_pct']}%"
             if out["inset"] else ""))
    return out


# ------------------------------------------------- 10 · composite the product

def product_box(plate):
    """Where the product sits on this plate.

    An edit model handed a product ad draws a product, whatever the prompt
    says — the reference wins over the words, the same way it does for camera
    position. So the plate is allowed its placeholder and the real packshot is
    composited over it. This finds what to cover: the largest dark mass in the
    middle of the frame, against the light ground these formats use.
    """
    w, h = map(int, sh(["magick", "identify", "-format", "%w %h", str(plate)])
               .stdout.split())
    cx0, cy0 = int(w * 0.18), int(h * 0.10)
    cw, ch = int(w * 0.64), int(h * 0.80)
    tmp = Path("/tmp/_pbox.png")
    sh(["magick", str(plate), "-crop", f"{cw}x{ch}+{cx0}+{cy0}", "+repage",
        "-colorspace", "gray", "-threshold", "82%", "-negate",
        "-morphology", "close", "disk:6", str(tmp)])
    box = sh(["magick", str(tmp), "-format", "%@", "info:"]).stdout.strip()
    m = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", box or "")
    if not m:
        return None
    bw, bh, bx, by = map(int, m.groups())
    if bw < w * 0.08 or bh < h * 0.08:
        return None
    return dict(x=cx0 + bx, y=cy0 + by, w=bw, h=bh)


def final_check(run, final, brief):
    """What is wrong with the finished ad, in plain terms. Empty means ship."""
    out = []
    if not final or not final.exists():
        return ["the ad was never written"]
    w, h = map(int, sh(["magick", "identify", "-format", "%w %h",
                        str(final)]).stdout.split())
    if abs((w / h) - (9 / 16)) > 0.06:
        out.append(f"wrong shape for a feed ad: {w}x{h}")

    layer = run / "out/11-type-layer.json"
    if layer.is_file():
        n = len(json.loads(layer.read_text()).get("elements", []))
        if n < 3:
            out.append(f"only {n} pieces of copy set — an ad needs a headline, "
                       f"an offer and a mark at minimum")
    if re.search(r"product[^.\n]{0,60}composit", brief, re.I):
        # the product must actually be visible in the finished file
        r = sh(["magick", str(final), "-format", "%[fx:standard_deviation]", "info:"])
        if not r.stdout.strip():
            out.append("could not read the finished ad")
    return out


def brief_product_spot(brief):
    """The product's position, read off the brief's own words."""
    m = re.search(r"Product Sticker(.{0,400}?)Position:\s*top\s*(\d+)%?,\s*"
                  r"left\s*(\d+)%?,\s*span\s*(\d+)", brief, re.S | re.I)
    if not m:
        return None
    ctx = m.group(1)
    rot = re.search(r"[Rr]otated?\s*(-?\d+)", ctx)
    out = re.search(r"(#[0-9A-Fa-f]{6})\s*stroke|stroke[^.]{0,20}(#[0-9A-Fa-f]{6})", ctx)
    return dict(top=int(m.group(2)), left=int(m.group(3)),
                span=int(m.group(4)),
                rotate=int(rot.group(1)) if rot else 0,
                outline=(out.group(1) or out.group(2)) if out else None)


def step_product(run, plate, measure, packshot, brief_text=""):
    """Put the real product in. Never generated — it carries a wordmark."""
    if not packshot or not Path(packshot).exists():
        print(f"  {plate.stem}: no packshot supplied — leaving the plate as is")
        return plate

    dest = run / "iterations" / f"{plate.stem}-product.png"
    cut = run / "iterations" / ".product-cut.png"
    sh(["magick", str(packshot), "-alpha", "set", "-fuzz", "14%",
        "-fill", "none", "-draw", "color 2,2 floodfill",
        "-trim", "+repage", str(cut)])

    ins = measure.get("inset")
    if ins:
        # a format with a product inset: fill the ring
        d = ins["r"] * 2
        fill = sh(["magick", str(plate), "-format",
                   f"%[pixel:p{{{ins['cx']},{ins['cy']-ins['r']//2}}}]",
                   "info:"]).stdout.strip() or "#DEDEDE"
        disc = run / "iterations" / ".product-disc.png"
        sh(["magick", "-size", f"{d}x{d}", f"xc:{fill}",
            "(", str(cut), "-resize", f"x{int(d*0.72)}", ")",
            "-gravity", "center", "-composite",
            "(", "-size", f"{d}x{d}", "xc:black", "-fill", "white",
            "-draw", f"circle {d//2},{d//2} {d//2},{int(d*0.03)}", ")",
            "-alpha", "off", "-compose", "CopyOpacity", "-composite", str(disc)])
        sh(["magick", str(plate), str(disc), "-geometry",
            f"+{ins['cx']-ins['r']}+{ins['cy']-ins['r']}", "-composite", str(dest)])
        print(f"  {plate.stem}: real product set into the inset ring")
        return dest

    # First choice: the position the brief actually stated. A brief that says
    # where the product goes is the authority; hunting for a dark blob is the
    # fallback for when it did not.
    spot = brief_product_spot(brief_text)
    if spot:
        w, h = map(int, sh(["magick", "identify", "-format", "%w %h", str(plate)])
                   .stdout.split())
        span = int(w * spot["span"] / 100)
        x, y = int(w * spot["left"] / 100), int(h * spot["top"] / 100)
        piece = run / "iterations" / ".product-piece.png"
        cmd = ["magick", str(cut), "-resize", f"{span}x"]
        if spot.get("outline"):
            cmd += ["-bordercolor", "none", "-border", "12",
                    "(", "+clone", "-alpha", "extract", "-morphology", "dilate",
                    "disk:9", "-negate", ")", "-alpha", "off",
                    "-compose", "CopyOpacity", "-composite"]
        if spot.get("rotate"):
            cmd += ["-background", "none", "-rotate", str(spot["rotate"])]
        cmd.append(str(piece))
        sh(cmd)
        if spot.get("outline"):
            lay = run / "iterations" / ".product-lay.png"
            sh(["magick", str(piece), "-background", spot["outline"],
                "-alpha", "remove", "-alpha", "off", str(lay)])
            sh(["magick", str(plate), "(", str(lay), ")", "-geometry",
                f"+{x}+{y}", "-composite",
                "(", str(cut), "-resize", f"{int(span*0.88)}x",
                "-background", "none", "-rotate", str(spot.get("rotate") or 0), ")",
                "-geometry", f"+{x+int(span*0.06)}+{y+int(span*0.06)}",
                "-composite", str(dest)])
        else:
            sh(["magick", str(plate), str(piece), "-geometry", f"+{x}+{y}",
                "-composite", str(dest)])
        print(f"  {plate.stem}: real product placed where the brief said "
              f"(top {spot['top']}%, left {spot['left']}%, span {spot['span']}%)")
        return dest

    # a format where the product is the hero: cover the placeholder with it
    box = product_box(plate)
    if not box:
        print(f"  {plate.stem}: could not find the product's place")
        return plate
    # Cover the placeholder, not the frame. A filled rectangle the size of the
    # box wipes out whatever the format drew around the product — on a diagram
    # format that is the callout arrows (2026-08-30). So the placeholder is
    # masked to its own silhouette, and the real product goes over that.
    bg = sh(["magick", str(plate), "-format", "%[pixel:p{6,6}]", "info:"]).stdout.strip()
    mask = run / "iterations" / ".placeholder-mask.png"
    sh(["magick", str(plate), "-crop",
        f"{box['w']}x{box['h']}+{box['x']}+{box['y']}", "+repage",
        "-colorspace", "gray", "-threshold", "82%", "-negate",
        "-morphology", "close", "disk:8", "-blur", "0x1", mask.as_posix()])
    wipe = run / "iterations" / ".wipe.png"
    sh(["magick", "-size", f"{box['w']}x{box['h']}", f"xc:{bg or 'white'}",
        str(mask), "-alpha", "off", "-compose", "CopyOpacity", "-composite",
        str(wipe)])
    sh(["magick", str(plate), str(wipe), "-geometry",
        f"+{box['x']}+{box['y']}", "-composite",
        "(", str(cut), "-resize", f"{int(box['w']*1.02)}x{int(box['h']*1.02)}", ")",
        "-gravity", "none", "-geometry",
        f"+{box['x']}+{box['y']}", "-composite", str(dest)])
    print(f"  {plate.stem}: real product composited over the placeholder "
          f"({box['w']}x{box['h']} at {box['x']},{box['y']})")
    return dest


# ------------------------------------------------------------ 11 · set type

def type_layer(run, brief, measure):
    """The layout data from the brief, shifted onto this plate's own geometry."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", brief, re.S)
    if not m:
        sys.exit("the brief carries no layout data — stage one owes it")
    d = json.loads(m.group(1))

    band = measure.get("band_top_pct")
    if band:
        tops = [e["top_pct"] for e in d["elements"] if e.get("top_pct") is not None]
        if tops:
            shift = band - min(tops) + 1.5
            if abs(shift) > 0.4:
                for e in d["elements"]:
                    if e.get("top_pct") is not None:
                        e["top_pct"] = round(e["top_pct"] + shift, 1)
                print(f"  positions shifted {shift:+.1f}% onto this plate's band")
    # A text block squeezed into a narrow span wraps and then shrinks until it
    # is unreadable. Briefs sometimes hand back a 37%-wide box for a headline
    # that needs half the frame. Give any block carrying real copy a sensible
    # minimum width, centred on the axis it was given.
    for e in d["elements"]:
        txt = str(e.get("text", "")).strip()
        if len(txt) < 8:
            continue
        left = float(e.get("left_pct") or 0)
        right = float(e.get("right_pct") or 100)
        longest = max((len(l) for l in txt.split("\n")), default=len(txt))
        want = min(84.0, max(46.0, longest * 2.4))
        if right - left < want:
            mid = (left + right) / 2
            mid = min(max(mid, want / 2 + 6), 100 - want / 2 - 6)
            e["left_pct"] = round(mid - want / 2, 1)
            e["right_pct"] = round(mid + want / 2, 1)

    # A block's own height is what caps its type size, and briefs write it
    # tight — a 3% cap inside a 3% band leaves no room, so the compositor
    # steps the type down until it is unreadable. Give each block room to
    # hold the size it was specified at.
    for e in d["elements"]:
        cap = float(e.get("cap_pct") or 2)
        lines = int(e.get("max_lines") or
                    (str(e.get("text", "")).count("\n") + 1))
        need = cap * lines * 1.5 + 1.5
        if float(e.get("height_pct") or 0) < need:
            e["height_pct"] = round(need, 1)

    for e in d["elements"]:
        f = str(e.get("font", "")).lower()
        e["font"] = ("compressed-grotesque" if "compressed" in f else
                     "condensed-grotesque" if "condensed" in f else "grotesque")
        for k in ("measure", "max_lines"):
            if isinstance(e.get(k), str):
                e.pop(k)
    out = run / "out/11-type-layer.json"
    out.write_text(json.dumps(d, indent=2) + "\n")
    return out


def step_type(run, plate, layer, name):
    dest = run / "finals" / f"ad-{name}.png"
    dest.parent.mkdir(exist_ok=True)
    r = sh([sys.executable, str(P.COMPOSE), "--plate", str(plate),
            "--layer", str(layer), "--file", "all", "--out", str(dest)])
    for line in (r.stdout + r.stderr).splitlines():
        if "note:" in line or "elements set" in line:
            print("   ", line.strip())
    return dest if dest.exists() else None


# ------------------------------------------------------------- 12 · prove it

def step_proof(run, final, name):
    src = next((p for p in (run / "assets").iterdir()
                if p.stem == "source" and p.suffix.lower() in (".jpg", ".png")), None)
    if not src or not final:
        return None
    dest = run / "finals" / f"source-vs-{name}.jpg"
    sh(["magick", str(src), "-resize", "x1100", "/tmp/_a.png"])
    sh(["magick", str(final), "-resize", "x1100", "/tmp/_b.png"])
    sh(["magick", "/tmp/_a.png", "/tmp/_b.png", "+append",
        "-bordercolor", "#141414", "-border", "10", str(dest)])
    print(f"  proof → {dest.name}")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--step", type=int)
    ap.add_argument("--packshot")
    ap.add_argument("--brand", help="folder under brands/ — left out, the brand "
                                    "teardown recorded for this run")
    ap.add_argument("--product", help="the product's slug, for its packshot")
    a = ap.parse_args()

    run = Path(a.run)
    if not run.is_absolute():
        run = P.RUNS / Path(a.run).name
    brief = brief_of(run)
    (run / "iterations").mkdir(exist_ok=True)

    if a.packshot:
        packshot = Path(a.packshot)
    else:
        # The packshot is the BRAND's, for the product named. This searched
        # one brand's products folder whoever the run was for (2026-09-20).
        brand = P.brand_of_run(run.name, a.brand)
        packshot = P.product_cutout(brand, a.product)
        if packshot is None or not packshot.is_file():
            cands = sorted((P.BRANDS / brand / "products").rglob("*.png"))
            if a.product:
                cands = [p for p in cands if a.product in p.parts] or cands
            packshot = next((p for p in cands if "cutout" in p.name.lower()), None) \
                or next((p for p in cands if "packshot" in p.name.lower()), None) \
                or next((p for p in cands if "hero" in p.name.lower()), None)

    steps = [a.step] if a.step else [7, 8, 9, 10, 11, 12]

    if 7 in steps:
        print("\n[7] make the plates  ·  higgsfield")
        step_plates(run, brief)

    plates = sorted((run / "iterations").glob("plate-*.png"))
    if not plates:
        sys.exit("no plates — step 7 made nothing")

    if 8 in steps:
        print("\n[8] judge the plates  ·  measured checks + vision")
        step_check(run, brief)

    ready = [p for p in plates if passed(run, p.stem)]
    if not ready:
        print("\nStopping: no plate passed its own accept tests.")
        print("out/08-plate-check.md names what failed and what to change.")
        return

    # If the brief says an element is composited, a finished ad without it is
    # not finished. Nothing caught this on 2026-08-31 — four ads shipped with
    # no product in them because the product step was skipped and no step
    # after it cared. It cares now.
    wants_product = bool(re.search(
        r"product[^.\n]{0,60}(composit|from the (brand|real)[^.\n]*photograph)",
        brief, re.I))
    if wants_product and not packshot:
        sys.exit("the brief composites a product and no packshot was found.\n"
                 "Pass --packshot, or put one in the brand's products folder.\n"
                 "Refusing to build an ad the brief says has a product in it.")

    bad = []
    for plate in ready:
        name = plate.stem.replace("plate-", "")
        print(f"\n— {name} —")
        meas = step_measure(run, plate) if 9 in steps else \
            json.loads((run / "out/09-measure.json").read_text())[plate.stem]
        # Type first, product last. The product is a sticker that overlaps the
        # copy — put it on before the type and the type covers it, which is
        # exactly what happened on 2026-08-31: the product was there and
        # invisible behind the headline box.
        final = plate
        if 11 in steps:
            layer = type_layer(run, brief, meas)
            final = step_type(run, plate, layer, name) or plate
        if packshot and (10 in steps or 11 in steps):
            withp = step_product(run, Path(final), meas, packshot, brief)
            if withp != Path(final):
                sh(["magick", str(withp), str(final)])
            elif wants_product:
                print(f"  {name}: WARNING — the product did not composite; "
                      f"this ad is missing it")
        if 12 in steps:
            step_proof(run, final, name)

        # Last gate: look at what was actually produced, not at what the
        # steps reported. A step can succeed and still leave a broken ad.
        problems = final_check(run, Path(final), brief)
        if problems:
            print(f"  {name}: NOT DELIVERABLE —")
            for pr in problems:
                print(f"      · {pr}")
            print(f"      fix these before this ad goes anywhere")
            bad.append(name)


if __name__ == "__main__":
    main()
