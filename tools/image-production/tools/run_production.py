#!/usr/bin/env python3
"""Stage two, end to end: brief in, finished ads out.

    run_production.py <run>              every step
    run_production.py --all              every run that has a brief
    run_production.py <run> --brand <brand> --product <slug>

The packshot, the logo and the colours are the BRAND's. The brand is `--brand`,
else the one teardown recorded for the run (`vars/brand_name.md`); there is no
default. `--product` names whose packshot goes on the ad — needed when the
brand has more than one on file.

    7  plates      higgsfield   the photographs, no words in them
    8  judge       gemini       the brief's own accept tests, no human in it
    9  compose     imagemagick  square on the damage, type, logo, sticker
   10  deliver     drive        mirrored, linked, and named

Nothing is delivered with a defect anyone has already seen. If a check fails
the fix happens here, not in a note attached to a broken ad.
"""
import json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import gates as G


def sh(c, **k):
    return subprocess.run(c, capture_output=True, text=True, **k)


def headlines(run_name, n=4):
    """The control and the first three variations, from the hook set."""
    f = P.TEARDOWN / "runs" / run_name / "out/04-headlines.md"
    if not f.is_file():
        return []
    out = []
    for m in re.finditer(r"\*\*(?:V\d+(?:\s*\(CONTROL\))?):\*\*\s*(.+)", f.read_text()):
        parts = [p.strip() for p in m.group(1).split("/")]
        if len(parts) >= 3:
            out.append(parts[:3])
    return out[:n]


def run_one(name, brand=None, product=None):
    print(f"\n=== {name} ===")
    brief = P.brief_for(name)
    if not brief.is_file():
        print("  no brief — teardown has not finished this run")
        return
    brand = P.brand_of_run(name, brand)
    cutout = P.product_cutout(brand, product)
    cutout = str(cutout) if cutout else ""
    # Every template, style pack and picture format the brief names is a real
    # row in the element library, or nothing is built (tools/gates.py).
    G.elements_gate_for_brief(P.RUNS / name, brief)
    run = P.RUNS / name
    (run / "iterations").mkdir(parents=True, exist_ok=True)
    (run / "finals").mkdir(exist_ok=True)
    (run / "assets").mkdir(exist_ok=True)
    src = P.source_for(name)
    if src and not (run / "assets" / src.name).exists():
        sh(["cp", str(src), str(run / "assets" / f"source{src.suffix}")])
    if not (run / "out").exists():
        (run / "out").mkdir()
    sh(["cp", str(brief), str(run / "out/06-brief.md")])

    print("[7] plates · higgsfield")
    r = sh([sys.executable, str(P.TOOLS / "generate.py"), str(run)])
    for l in r.stdout.splitlines():
        if "→" in l or "FAILED" in l or "trimmed" in l:
            print("   ", l.strip()[:110])
    plates = sorted((run / "iterations").glob("plate-*.png"))
    if not plates:
        print("  no plates came back")
        return

    print("[8] judge · gemini + measured checks")
    r = sh([sys.executable, str(P.TOOLS / "judge.py"), str(run), "--retry", "1"])
    for l in r.stdout.splitlines():
        if "→" in l or "plates pass" in l:
            print("   ", l.strip()[:110])

    ok = []
    chk = run / "out/08-plate-check.md"
    if chk.is_file():
        t = chk.read_text()
        for p in plates:
            b = re.search(rf"## {re.escape(p.stem)}\n(.+?)(?=\n## |\Z)", t, re.S)
            # The verdict line, not any PASS in the block. A failing plate
            # lists its passing tests too, so "PASS appears somewhere" let
            # four rejected plates through on 2026-08-31.
            if b and re.search(r"\*\*Verdict:\*\*\s*PASS", b.group(1), re.I):
                ok.append(p)
    # The media gate: the judge's verdicts, written down as a gate. A plate
    # it failed is held from delivery with the reason; the verdicts themselves
    # are judge.py's and are not touched here.
    G.media_gate(run, [(p.stem, ["failed its accept tests — out/08-plate-check.md says which"])
                       for p in plates if p not in ok])
    if not ok:
        print("  no plate passed — nothing built")
        G.file_quietly(G.file_swipe_record, run, brand)
        return

    print("[9] compose · draft → finish → type")
    # Every swipe is a different format, and the brief measured it. Rendering
    # from that data is the whole point of the teardown. A hardcoded layout
    # was drawn over three unrelated formats on 2026-08-31 and shipped.
    for p in ok:
        variant = p.stem.replace("plate-", "")
        out = run / "finals" / f"ad-{variant}.png"
        # Three passes, and the order is the whole point:
        #   1. the scene as a draft — ground, band, no product, no type
        #   2. a finishing pass on that draft alone, for the craft a
        #      rectangle cannot do: contact shadow, resolved edges, one grade
        #   3. the real product and the type laid on top, untouched
        # Polishing with the product in frame re-draws its label into mush,
        # and polishing with type in frame re-draws the words. Both measured
        # on 2026-08-31.
        draft = run / "iterations" / f"draft-{variant}.png"
        sh([sys.executable, str(P.TOOLS / "render.py"),
            str(P.brief_for(name)), str(p), str(draft),
            cutout, variant, "--picture", f"--brand={brand}"])
        fin = run / "iterations" / f"finished-{variant}.png"
        pol = sh([sys.executable, str(P.TOOLS / "polish.py"),
                  str(draft), str(fin)])
        base, mode = ((fin, "--over") if fin.is_file() else (p, "--all"))
        if not fin.is_file():
            print(f"    finishing pass failed for {variant} — "
                  f"built from the unfinished draft")
        r = sh([sys.executable, str(P.TOOLS / "render.py"),
                str(P.brief_for(name)), str(base), str(out),
                cutout, variant, mode, f"--brand={brand}"])
        msg = (r.stdout or r.stderr).strip()
        print("   ", msg[:400])
        # A picture with content where the product goes cannot carry the
        # product. Building the ad anyway puts a tube on top of a limb and
        # calls it finished.
        if "is not clear on the plate" in msg:
            out.unlink(missing_ok=True)
            print(f"    withheld {out.name} — its product zone is occupied")
    G.file_quietly(G.file_swipe_record, run, brand)


def _flag(argv, name):
    """Pull `--name value` / `--name=value` out of argv; the rest stays."""
    for i, x in enumerate(argv):
        if x == name and i + 1 < len(argv):
            v = argv[i + 1]; del argv[i:i + 2]; return v
        if x.startswith(name + "="):
            del argv[i]; return x.split("=", 1)[1]
    return None


def main():
    argv = list(sys.argv[1:])
    brand, product = _flag(argv, "--brand"), _flag(argv, "--product")
    args = [a for a in argv if not a.startswith("--")]
    if "--all" in sys.argv:
        args = sorted(d.name for d in (P.TEARDOWN / "runs").iterdir()
                      if d.is_dir() and (d / "out/06-brief.md").is_file())
    if not args:
        sys.exit("name a run, or --all")
    for n in args:
        try:
            run_one(n, brand, product)
        except SystemExit as e:                 # a refusal names itself
            print(f"  {n}: {e}")
        except Exception as e:
            print(f"  {n}: {type(e).__name__}: {e}")
    print("\n[10] deliver")
    sh([sys.executable, str(P.TOOLS / "drive_link.py"), "--all"])


if __name__ == "__main__":
    main()
