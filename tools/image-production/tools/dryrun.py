#!/usr/bin/env python3
"""The dry run — everything a batch or a brief needs, resolved. Spends nothing.

    machine.py --dry-run runs/<brand>/<batch>          a batch (batch.json)
    machine.py --dry-run <swipe> --brand <brand> ...   a swipe and its brief
    run.py runs/<brand>/<batch> --dry-run              the same, for one batch

For each concept it resolves every input and says OK or MISSING:

    the batch.json · the brand's folder · the template named · the style pack
    named · the picture format named · the prompt exactly as it would be sent ·
    the model it would route to · the product elements the prompt references
    and what the brand says is true of them · the packshot · the logo · the
    palette · the fonts · the roster · the offer bank · what the elements and
    copy gates would say · where the record and the pictures would go

**It starts no model and no generator, judges nothing, and writes no file** —
not in the run, not under the repo-root `runs/`, not on Drive. Exit 1 when
anything REQUIRED is missing or a gate would hold; exit 0 otherwise.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import gates as G
import brand_facts as BF


def model_for(ad, spec):
    """plates.py's own routing. It imports the padder (and so the imaging
    library) — a machine without it can still be told what is missing."""
    try:
        import plates as PL
        return PL.model_for(ad, spec)
    except ImportError as e:
        return "unknown", f"plates.py could not be imported: {e}"

SYSTEM_FONTS = Path("/System/Library/Fonts/Supplemental")


class Report:
    def __init__(self):
        self.missing = 0

    def ok(self, what, detail=""):
        print(f"    OK       {what:<18} {detail}")

    def note(self, what, detail=""):
        print(f"    --       {what:<18} {detail}")

    def bad(self, what, detail=""):
        self.missing += 1
        print(f"    MISSING  {what:<18} {detail}")

    def file(self, what, path, required=True, detail=""):
        path = Path(path) if path else None
        if path and path.is_file():
            self.ok(what, f"{_rel(path)} {detail}".rstrip())
            return True
        where = _rel(path) if path else "nothing on file"
        (self.bad if required else self.note)(what, f"{where} {detail}".rstrip()
                                              + ("" if required else " — not on file, not required"))
        return False


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(P.REPO))
    except ValueError:
        return str(p)


def _template(name):
    f = P.TEMPLATES / f"{name}.json"
    try:
        return f, json.loads(f.read_text())
    except (OSError, ValueError):
        return f, None


def _layout_needs(tpl):
    """What a layout template's furniture asks of the brand."""
    els = (tpl or {}).get("elements") or []
    return {"logo": any(e.get("kind") == "logo" for e in els),
            "product": bool(((tpl or {}).get("layout") or {}).get("product")),
            "tone": next((e.get("tone") or "light" for e in els if e.get("kind") == "logo"), "light")}


def _brand_rows(r, brand, needs, product, words_have_price):
    b = P.brand(brand)
    if needs.get("product"):
        try:
            cut = P.product_cutout(brand, product)
        except SystemExit as e:
            cut = None
            r.bad("packshot", str(e))
        else:
            if cut is None:
                r.bad("packshot", f"{brand} declares no local cutout"
                                  + (f" for `{product}`" if product else "")
                                  + " in products/images.json")
            else:
                r.file("packshot", cut)
    else:
        r.note("packshot", "not composited — the product goes in as an element id")
    if needs.get("logo"):
        r.file("logo", b["logo_dark"] if needs.get("tone") == "dark" else b["logo_white"])
    else:
        r.note("logo", "no zone names one — none is drawn")
    pal = sorted(b["identity"].glob("*.md")) if b["identity"].is_dir() else []
    hexes = set()
    for f in pal:
        hexes |= set(re.findall(r"#[0-9A-Fa-f]{6}", f.read_text(errors="replace")))
    if hexes:
        r.ok("palette", f"{len(hexes)} colours in {_rel(b['identity'])}/*.md")
    else:
        r.note("palette", f"no colours on file in {_rel(b['identity'])} — only neutrals will be drawn")
    r.file("fonts (brand)", b["identity"] / "fonts.md", required=False)
    r.file("offer bank", b["offer"], required=words_have_price,
           detail="" if words_have_price else "(the words name no price)")


def _fonts(r):
    import render as RD                       # importing draws nothing
    names = sorted(set(RD.FONTS.values()))
    gone = [n for n in names if not (SYSTEM_FONTS / n).is_file()]
    if gone:
        r.bad("fonts (type)", "not installed: " + ", ".join(gone))
    else:
        r.ok("fonts (type)", f"{len(names)} faces the compositor sets type in")


# ------------------------------------------------------------------ a batch

def batch(run, r=None):
    """Dry-run one batch folder. Returns the number of required things missing."""
    r = r or Report()
    run = Path(run).resolve()
    print(f"\n=== {_rel(run)}")
    sf = run / "batch.json"
    if not r.file("batch.json", sf):
        return r.missing
    try:
        spec = json.loads(sf.read_text())
    except ValueError as e:
        r.bad("batch.json", f"not valid JSON — {e}")
        return r.missing
    brand = spec.get("brand")
    try:
        P.need_brand(brand, "everything a batch is built from")
        r.ok("brand", f"brands/{brand}")
    except SystemExit as e:
        r.bad("brand", str(e))
        return r.missing
    Q = G.quality()
    words = G.burned_words(spec)
    priced = any(Q.prices_in(t) for _, t in words)

    picked, el_problems = G.picked_in_batch(spec, run)
    ads = spec.get("ads") or []
    if not ads:
        r.bad("ads", "batch.json names no ads")
    for ad in ads:
        slug = ad.get("slug", "?")
        print(f"\n  · {slug}")
        t = ad.get("template", spec.get("template"))
        needs = {}
        if t in G.NO_TEMPLATE:
            r.note("template", "prompted — the model draws its own type, no layout file")
        else:
            f, tpl = _template(G.stem(t))
            if r.file("template", f):
                needs = _layout_needs(tpl)
        pack = ad.get("pack") or ad.get("style_pack") or spec.get("pack") or spec.get("style_pack")
        slots = run / "slots" / f"{slug}.json"
        if not pack and slots.is_file():
            try:
                pack = json.loads(slots.read_text()).get("pack")
            except ValueError:
                pass
        if pack:
            import prompt as PR
            (r.ok if pack in PR.packs() else r.bad)("style pack", f"`{pack}` in style-packs.json")
        else:
            r.note("style pack", "none named")
        fmt = ad.get("picture_format") or spec.get("picture_format")
        if fmt:
            bank = {x.get("key") for x in json.loads(P.FORMAT_BANK.read_text()).get("formats", [])}
            (r.ok if fmt in bank else r.bad)("picture format", f"`{fmt}` in format-bank.json")
        else:
            r.note("picture format", "none named")

        pf = run / "prompts" / f"{slug}.txt"
        text = ""
        if r.file("prompt", pf):
            text = pf.read_text().strip()
            model, why = model_for(ad, spec)
            r.ok("would be sent", f"{len(text)} chars · {ad.get('aspect', '4:5')} · {model} ({why})")
            print("             " + text[:150].replace("\n", " ") + ("…" if len(text) > 150 else ""))
        book = BF.book(brand)
        for uid in dict.fromkeys(BF.ELEMENT.findall(text)):
            row = book.get(uid) or {}
            if row.get("blocked"):
                r.bad("element", f"<<<{uid}>>> {row.get('name', '')} is BLOCKED — {str(row.get('warning', ''))[:110]}")
            elif row:
                r.ok("element", f"<<<{uid[:8]}…>>> {row.get('name', '')} · {row.get('kind', '?')} · "
                                f"{len(row.get('facts') or [])} facts")
            else:
                r.note("element", f"<<<{uid[:8]}…>>> has no entry in {brand}'s element-facts.json")
        if ad.get("shows_product", True):
            tests, note = BF.product_checks(brand, text)
            r.ok("judge · product", f"{len(tests)} test(s) — " + (note or f"from {brand}'s element-facts.json"))
        if ad.get("cast") and spec.get("drive_root"):
            r.file("roster", P.BRANDS / brand / "core-avatars/casting/roster.json")
        _brand_rows(r, brand, needs, ad.get("product_slug") or spec.get("product_slug"), priced)
        if needs:
            _fonts(r)

    print("\n  · gates (what they would say — nothing is written)")
    for p in el_problems:
        r.bad("elements gate", p)
    if not el_problems:
        r.ok("elements gate", ", ".join(f"{k}: {'/'.join(v)}" for k, v in picked.items() if v)
             or "nothing named that the library lists")
    bank = P.brand(brand)["offer"]
    cp = G.copy_problems(spec, bank.read_text(errors="replace") if bank.is_file() else "")
    for p in cp:
        r.bad("copy gate", p)
    if not cp:
        r.ok("copy gate", f"{len(words)} burned-in line(s) — no UNFILLED note, every price is in the offer bank")
    r.note("media gate", "runs after the judge — a failed picture is held from delivery")

    print("\n  · where it would go")
    r.note("record", f"{_rel(P.RECORDS / brand / run.name)}/  (text only)")
    root = spec.get("drive_root")
    r.note("pictures", f"Drive folder {root}" if root else "no `drive_root` in batch.json — named and recorded, not uploaded")
    return r.missing


# ------------------------------------------------------------------ a swipe

def teardown_dry(name, stages, brandargs):
    """The teardown steps' own dry run (image-teardown/tools/run.py --dry-run).
    It calls no model and writes nothing; its exit code is how many are MISSING."""
    cmd = [sys.executable, str(P.TEARDOWN / "tools/run.py"), name,
           ",".join(str(s) for s in stages)] + brandargs + ["--dry-run"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(P.TEARDOWN))
    for line in (res.stdout or res.stderr).splitlines():
        print("    " + line)
    return res.returncode


def swipe(name, brand, product=None, first=2, last=6, build=True, brandargs=None, r=None):
    r = r or Report()
    print(f"\n=== {name}")
    if not brand:                                   # an old run with no batch.json names no brand
        r.bad("brand", "this run has no batch.json and no --brand was given — name the brand")
        return r.missing
    if first <= last:
        print(f"  · teardown steps {first}-{last} (their own dry run)")
        if teardown_dry(name, range(first, last + 1), brandargs or ["--brand", brand]):
            r.bad("teardown", "its dry run reports something missing — see above")
    if not build:
        return r.missing
    print("\n  · build")
    try:
        P.need_brand(brand, "the packshot, logo and colours")
        r.ok("brand", f"brands/{brand}")
    except SystemExit as e:
        r.bad("brand", str(e))
        return r.missing
    brief = P.brief_for(name)
    planned = first <= 6 <= last
    if brief.is_file():
        r.ok("brief", _rel(brief))
        picked, problems = G.picked_in_brief(brief)
        for p in problems:
            r.bad("elements gate", p)
        if not problems:
            r.ok("elements gate", ", ".join(f"{k}: {'/'.join(v)}" for k, v in picked.items() if v)
                 or "the brief carries its own geometry — names no template")
        needs = {"product": True, "logo": False}
        try:                                  # a brief carrying its own geometry
            import render as RD
            own, _ = RD.load(brief)
            needs = _layout_needs(own)
            needs["product"] = True           # the brief says; the packshot must be there if it does
        except BaseException:                 # noqa: BLE001 — an unreadable layout is the renderer's to report
            pass
        for t in picked.get("template", []):
            f, tpl = _template(t)
            if r.file("template", f):
                needs = _layout_needs(tpl)
        Q = G.quality()
        text = G.built_words(brief)
        _brand_rows(r, brand, needs, product, bool(Q.prices_in(text)))
    elif planned:
        r.note("brief", f"{_rel(brief)} — step 6 writes it in this run; its template and words are checked then")
        _brand_rows(r, brand, {"product": True}, product, False)
    else:
        r.bad("brief", f"{_rel(brief)} — teardown has not finished this run")
    src = P.source_for(name)
    (r.ok if src else r.note)("layout reference", _rel(src) if src else "no source picture in the swipe's assets")
    plates = sorted((P.RUNS / name / "iterations").glob("plate-*.png"))
    if plates:
        r.ok("plates", f"{len(plates)} already in {_rel(P.RUNS / name / 'iterations')}")
    else:
        r.bad("plates", "none on file, and tools/generate.py is retired — a session "
                        "generates them and files them as iterations/plate-<name>.png")
    _fonts(r)
    r.note("record", f"{_rel(P.RECORDS / brand / name)}/  (text only)")
    return r.missing


def main(targets, brand=None, product=None, first=2, last=6, build=True, brandargs=None):
    """targets: batch folders (hold a batch.json) and/or swipe names."""
    print("DRY RUN — resolving every input. No model, no generator, no judge, "
          "nothing written.")
    missing = 0
    for t in targets:
        p = Path(t).resolve() if Path(t).exists() else Path(t)
        as_batch = next((c for c in (p, P.PROD / t, P.RUNS / t) if (c / "batch.json").is_file()), None)
        if as_batch or p.name == "batch.json":
            missing += batch(as_batch or p.parent)
        elif (p / "prompts").is_dir() or (p.is_dir() and p.parent.parent == P.RUNS):
            missing += batch(p)                     # a batch folder with no spec yet
        else:
            missing += swipe(p.name, brand, product, first, last, build, brandargs)
    print(f"\n{'NOT READY' if missing else 'READY'} — {missing} required thing(s) missing"
          f"{'' if missing else '. Nothing was spent and nothing was written.'}")
    return 1 if missing else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--brand")
    ap.add_argument("--product")
    a = ap.parse_args()
    sys.exit(main(a.targets, a.brand, a.product, first=7, last=6))
