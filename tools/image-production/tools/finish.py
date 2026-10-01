#!/usr/bin/env python3
"""Generated frames in, filed and delivered ads out. Nothing by hand.

    finish.py <run-dir>              judge, name, file, deliver
    finish.py <run-dir> --dry-run    judge, then say what would happen — files
                                     nothing, delivers nothing. **It still calls
                                     the judge, so it is not free.** The free
                                     dry run is `machine.py --dry-run <run-dir>`.

A run directory looks like this before it is finished:

    runs/<brand>/<batch>/
      batch.json          the spec — what was asked for, and the checks
      inbox/<slug>.png    one generated frame per ad, any aspect
      prompts/<slug>.txt  the prompt that made it, verbatim

and like this after:

      ads/<slug>/<13-field-name>-a01.png   survivors, named for Meta
      rejected/<slug>.png + why.md         killed, with the reason
      report.md                            what passed, what died, why

**Damon never runs this.** A session runs it on his behalf and hands him the
link. The point of the file is that every batch is finished the same way, by
the same checks, whoever is at the keyboard.

Why auto-reject: the alternative is his eyes on every frame, which is the
thing that eats the day. The machine kills what fails a checkable test and he
only ever looks at survivors. Every kill is logged with its reason, because a
reject is a prompt defect — you fix the prompt, not the picture.
"""

import argparse, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

# The naming standard graduated to components/naming; naming/ has
# not existed since, so this import died and took the whole finish step with
# it — judge, name, file and deliver, all of stage two's tail (2026-09-14).
sys.path.insert(0, str(P.NAMING))
import pad as PAD            # 4:5 → 9:16 with solid bands; and the band check
import names as N
import deliver as D          # names the survivors, in-process, with per-asset extra
import record as R           # files the `made` record for every asset, pass or reject
GEMINI = Path(__file__).resolve().parent / "gemini_image.py"
UUID = re.compile(r"<<<([0-9a-f-]{36})>>>")

# Delivery goes through the Drive API (the gdrive-creator engine), never the
# mount. Measured 2026-09-07: Drive for Desktop went offline mid-copy, the
# server got names with no bytes, and the mount showed the opposite. The run
# root's id lives in batch.json as `drive_root` (the brand's run folder);
# assets land at <drive_root>/<talent>/<format>/<name>.png — by man, then by
# format, the way Damon reviews.
WS = P.REPO                     # found by walking up, never counted
sys.path.insert(0, str(P.GDRIVE))
import gates as G               # the declared gates + the repo-root record
import brand_facts as BF        # the judge's product tests, from the brand

# Four things, and only four. Narrowed 2026-09-05 on Damon's call: the job is
# replicated structure, brand injected correctly, consistent imagery — not a
# forensic QA pass. Finger-counting and micro-geometry killed good ads and cost
# more time than the defects they caught. What stayed is what costs money or
# breaks the brand.
STANDING_CHECKS = [
    "The text is READABLE. FAIL only for words that are garbled, corrupted, "
    "malformed or running into themselves (RPMPM, SAALE) — the kind of thing a "
    "reader would notice instantly. Normal repetition of a word across the copy "
    "is FINE. Small imperfections in a distressed or hand-drawn style are FINE.",
    "The offer bar is complete and not cut off at any edge of the frame.",
    "No third-party or competitor brand name, logo or wordmark is legible "
    "anywhere in the frame.",
    "Nothing is grossly broken — a limb attached wrongly, a face melted, a body "
    "with the wrong number of arms. Judge this the way a viewer scrolling past "
    "would. A partly hidden hand, a foreshortened grip, an odd-looking finger "
    "or a stylised illustration all PASS.",
]

# It answers the only product question that matters: would a customer
# recognise this as the thing we sell?
#
# **The product's geometry is the BRAND's, not this file's.** Until 2026-09-20
# two tests here described one brand's device, so every other brand's ad was
# judged against it. They are now built per batch from
# `brands/<brand>/element-facts.json` — the facts and forbids of the product
# element the ad's own prompt references, else the brand's canonical product
# (tools/brand_facts.py). A brand with no facts on file gets one plain test.
def product_checks(spec, run_dir=None, slug=None):
    """The product tests for one ad of one brand. Brand is required."""
    brand = P.need_brand((spec or {}).get("brand"), "the judge's product tests")
    text = ""
    if run_dir and slug:
        pf = Path(run_dir) / "prompts" / f"{slug}.txt"
        text = pf.read_text() if pf.is_file() else ""
    tests, note = BF.product_checks(brand, text)
    if note:
        print(f"  ! {note}")
    return tests

JUDGE = """You are checking one finished advertisement before it ships. The
image is attached.

Answer EVERY test below with PASS or FAIL, then one short sentence of the
evidence you actually saw. Judge only what is visible.

A hedge is a FAIL. "Probably fine", "mostly correct", "hard to tell" all mean
FAIL — an ad nobody can confirm is not an ad that passed. You are the only
gate before this reaches a paying feed.

TESTS
{tests}

Reply as JSON and nothing else:
{{"results": [{{"test": 1, "verdict": "PASS"|"FAIL", "evidence": "..."}}, ...]}}
"""


def price_pass(img_path, spec, model=None):
    """Judge the offer bar ALONE, cropped and enlarged.

    Judged inside the whole ad, a vision model reads a price it EXPECTS: it
    passed a poster whose strikethrough turned $99.99 into a clear $90.99,
    because everything else on the page said 99.99. Cropping the bar away from
    that context removes what it was guessing from, and enlarging it removes
    the excuse."""
    o = spec.get("offer") or {}
    prices = [str(v) for v in (o.get("price"), o.get("compare_at")) if v]
    if not prices:
        return []
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    w, h = im.size
    # On a 9:16 delivery the content lives in the centre 4:5 and the rest is
    # padding, so the offer bar is nowhere near the bottom of the FRAME. Find
    # the content first, then take its lower quarter. Cropping the frame blind
    # handed the judge a black band and it dutifully reported "no prices".
    if h / w > 1.4:                       # padded 9:16
        ch = int(w * 5 / 4)
        top = (h - ch) // 2
        content = im.crop((0, top, w, top + ch))
    else:
        content = im
    cw, ch = content.size
    band = content.crop((0, int(ch * 0.74), cw, ch))
    band = band.resize((cw * 2, band.size[1] * 2), Image.LANCZOS)
    tmp = Path(tempfile.mkdtemp()) / "band.png"
    band.save(tmp)

    want = " and ".join(f"${x}" for x in prices)
    test = ("Transcribe EVERY price you can see in this cropped strip, one "
            "character at a time, reading only the shapes actually printed. Do "
            "not correct, complete or guess a price from what you expect it to "
            "be — if a digit is shaped like a 0, it is a 0. The only prices "
            f"permitted are {want}. FAIL if what you transcribe differs from "
            "those in any character. Quote your transcription.")
    return seen(tmp, [test], model)[0]


def price_check(spec):
    """Transcribe-and-compare, because a general 'is it legible' test passed an
    ad whose strikethrough turned $99.99 into $90.99. The judge is made to read
    the digits out and match them against the offer we actually declared."""
    o = spec.get("offer") or {}
    prices = [str(v) for v in (o.get("price"), o.get("compare_at")) if v]
    if not prices:
        return []
    want = " and ".join(f"${p}" for p in prices)
    return ["Read every price in the image digit by digit, exactly as it "
            f"appears. The ONLY prices that may appear are {want}. FAIL if any "
            "price reads as any other number — including where a strikethrough, "
            "underline or overlap makes a digit look like a different digit "
            "(a struck 9 reading as a 0, for example). Quote what you read."]


def measured(img_path, spec, ad=None):
    """Counted off the pixels. No model, no argument. Runs first."""
    from PIL import Image
    fails = []
    im = Image.open(img_path)
    w, h = im.size
    ratio = h / w

    # An ad may declare its own ratio; that wins over the batch default.
    want = (ad or {}).get("ratio") or spec.get("ratio", "9x16")
    target = {"9x16": 16 / 9, "4x5": 5 / 4, "1x1": 1.0}.get(want)
    if target and abs(ratio - target) > 0.02:
        fails.append(f"aspect is {w}x{h} ({ratio:.3f}), spec wants {want}")

    # The safe-zone rule: at 9:16 the centre 4:5 is what the feed shows, so
    # anything that matters has to live there. We cannot read intent, but we
    # can catch the frame being the wrong shape to hold it.
    if want == "9x16" and h < w * 16 / 9 - 2:
        fails.append("frame is shorter than 9:16 — content cannot be safe")
    # The bands must be a flat ground. A stretched edge reads as a smear and
    # shipped once (2026-09-09); the gate refuses it rather than trusting the padder.
    if want == "9x16" and not PAD.solid(img_path):
        fails.append("band is not solid — smeared pad; re-pad from the centre 4:5")
    return fails


def seen(img_path, tests, model=None):
    """The brief's own tests, put to a vision model with the picture in front
    of it. Returns (fails, raw) so a kill can quote its evidence."""
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(tests))
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(JUDGE.format(tests=numbered))
        prompt_file = f.name
    out = tempfile.NamedTemporaryFile("r", suffix=".md", delete=False).name
    cmd = [sys.executable, str(GEMINI), "--prompt-file", prompt_file,
           "--image", str(img_path), "--out", out]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # The judge failing is not the ad passing. Hold it.
        return ([f"judge did not run: {r.stderr.strip()[:200]}"], "")
    raw = Path(out).read_text()
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        data = json.loads(raw[start:end])
    except Exception:
        return ([f"judge returned unreadable output"], raw)
    fails = []
    for res in data.get("results", []):
        if str(res.get("verdict", "")).upper() != "PASS":
            i = int(res.get("test", 0)) - 1
            t = tests[i] if 0 <= i < len(tests) else f"test {res.get('test')}"
            fails.append(f"{t.split('.')[0]} — {res.get('evidence','')}")
    return (fails, raw)


def asset_extra(ad, spec, run_dir, slug, verdict):
    """What the machine knows about this asset at the moment it ships."""
    pf = run_dir / "prompts" / f"{slug}.txt"
    prompt = pf.read_text().strip() if pf.is_file() else ""
    return {
        "sub": ad.get("sub"),
        "lane": spec.get("lane") or spec["avatar"],
        "template": ad.get("template", "prompted"),
        "copy": {"slots": ad.get("copy", {}), "provenance": "declared" if ad.get("copy") else "unknown"},
        "hook": ad.get("hook", "unknown"),
        "offer": {"id": (spec.get("offer") or {}).get("id", "unknown"),
                  "bar_text": (spec.get("offer") or {}).get("bar_text", "unknown")},
        "model": {"requested": spec.get("model", "unknown"), "reported": ad.get("model_reported", "unknown")},
        "references": [{"role": "element", "ref": u} for u in UUID.findall(prompt)],
        "qc": {"status": "pass", "checks_run": verdict.get("checks_run", []),
               "fails": [], "judge_model": verdict.get("judge_model", "unknown"),
               "coverage": "measured + seen + price pass"},
    }


def upload_unit(unit, spec, fields, files=None):
    """Every named asset in the unit → Drive, by man then format. Returns
    {file name: drive id} for the record. Update-in-place on a rerun."""
    from gdrive_creator import engine
    svc = engine.service()
    men = json.loads((WS / "brands" / spec["brand"] / "core-avatars/casting/roster.json").read_text())["people"]
    man = next((f"{p['name']} {p['age']}" for p in men if p["id"] == fields["talent"]), fields["talent"])
    dest = engine.folder(fields["format"], engine.folder(man, spec["drive_root"], svc), svc)
    out = {}
    for f in (files or sorted(unit.glob("*.png"))):
        fid, _ = engine.upload_file(f, f.name, dest, mime="image/png", svc=svc)
        out[f.name] = fid
    return out


def headline_check(ad):
    """HEADLINE MATCH — the picture must show what the words say.

    Added 2026-09-09 on Damon's call. The gate read the type and the product
    and never asked the obvious question: if the headline says the neck is
    bumped up, is a bumped-up neck actually in frame? A picture that argues
    something its own headline does not is slop, however clean it renders."""
    h = (ad.get("copy") or {}).get("headline", "").replace("\n", " ").strip()
    if not h:
        return []
    return [f'The headline on this ad reads "{h}". The picture must SHOW what that '
            f'claim is about — the problem, the person or the moment the words name, '
            f'visible in frame. FAIL if the words and the picture are arguing different '
            f'things, or if what the headline names is not visible at all. Say what you see.']


def add_asset(run_dir, slug, img, index, change, source, dry=False, model=None):
    """One new picture into an EXISTING unit — a variation or a fix.

    `deliver()` numbers a whole folder by sorted name and refuses collisions,
    so it cannot append; this judges one frame, gives it the unit's name at
    `index` (a fix replaces the file under the same name, keeping the old one
    in superseded/), writes its manifest row, its record and its Drive copy.
    Returns (True, name) or (False, fails)."""
    import datetime as dt, json
    run_dir = Path(run_dir).resolve(); img = Path(img)
    spec = json.loads((run_dir / "batch.json").read_text())
    ad = next((a for a in spec["ads"] if a["slug"] == slug), None)
    if not ad:
        return False, ["unit not in batch.json"]
    unit = run_dir / "ads" / slug
    man = json.loads((unit / "manifest.json").read_text())
    name = N.asset_name(man["ad_name"], index)
    tests = list(STANDING_CHECKS) + (product_checks(spec, run_dir, slug) if ad.get("shows_product", True) else []) + headline_check(ad) + ad.get("checks", [])
    PAD.pad(img)
    fails = measured(img, spec, ad); raw = ""
    if not fails:
        fails, raw = seen(img, tests, model)
        fails += price_pass(img, spec, model)
    if fails:
        rej = unit / "rejected"; rej.mkdir(exist_ok=True)
        shutil.copy2(img, rej / f"{name}.png")
        (rej / f"{name}-why.md").write_text(f"# {name} — rejected\n\n" + "\n".join(f"- {x}" for x in fails)
                                            + f"\n\nchange asked: {change}\n" + (f"\n<details><summary>judge, raw</summary>\n\n```\n{raw}\n```\n</details>\n" if raw else ""))
        n = len(list(rej.glob(f"{name}*.png")))
        v = {"event": "made", "name": name, "ad_name": man["ad_name"], "fields": {**{k: man.get(k) for k in N.AD_FIELDS}, "lane": spec.get("lane"), "sub": ad.get("sub")},
             "template": ad.get("template", "prompted"), "copy": {"slots": ad.get("copy", {}), "provenance": "declared"},
             "offer": spec.get("offer", {}), "prompt": {"text": change, "path": None}, "references": [{"role": "image_reference", "ref": source}],
             "location": {"drive_id": None, "drive_path": f"rejected/{name}.png", "durable_url": None},
             "qc": {"status": "reject", "checks_run": tests, "fails": fails, "judge_model": model or "gemini", "coverage": "measured + seen + price pass"}}
        R.write(R.item_id(man["batch"], slug, f"a{index:02d}r{n}"), "image-production", v, via="finish.add_asset")
        return False, fails
    dst = unit / f"{name}.png"
    if dst.exists():
        sup = unit / "superseded"; sup.mkdir(exist_ok=True)
        shutil.move(str(dst), sup / f"{name}-{dt.datetime.now():%y%m%d%H%M%S}.png")
    shutil.copy2(img, dst)
    (run_dir / "prompts").mkdir(exist_ok=True)
    pp = run_dir / "prompts" / f"{slug}-a{index:02d}.txt"; pp.write_text(change + "\n")
    row = {"name": name, "ad_name": man["ad_name"], "file": dst.name, "sub": ad.get("sub"), "lane": spec.get("lane"),
           "template": ad.get("template", "prompted"), "copy": {"slots": ad.get("copy", {}), "provenance": "declared"},
           "hook": ad.get("hook", "unknown"), "offer": spec.get("offer", {}),
           "model": {"requested": spec.get("model", "unknown"), "reported": "unknown"},
           "references": [{"role": "image_reference", "ref": source}],
           "prompt": {"text": change, "path": str(pp.relative_to(WS))},
           "variation": f"a{index:02d} — {change}",
           "qc": {"status": "pass", "checks_run": tests, "fails": [], "judge_model": model or "gemini", "coverage": "measured + seen + price pass", "judged": dt.date.today().isoformat()}}
    man["ads"] = [r for r in man["ads"] if r["name"] != name] + [row]
    man["ads"].sort(key=lambda r: r["name"])
    (unit / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    ids_path = run_dir.parent / "_drive-ids.json"
    ids = json.loads(ids_path.read_text()) if ids_path.is_file() else {}
    if spec.get("drive_root") and not dry:
        fields = {"talent": man["talent"], "format": man["format"]}
        up = upload_unit(unit, spec, fields, files=[dst])
        for fname, fid in up.items():
            ids[fname] = {"id": fid, "path": f"RUN-01 fed-up-king/{fields['talent']}/{fields['format']}/{fname}"}
        ids_path.write_text(json.dumps(ids, indent=1) + "\n")
    R.made_from_manifest(unit / "manifest.json", run_dir / "batch.json", ids, only=[name])
    return True, name


def reject_record(run_dir, spec, ad, slug, fails):
    """A reject gets a record too — beside why.md, never a shipping name."""
    v = {"event": "made", "name": f"{slug} (rejected, unnamed)", "ad_name": None,
         "fields": {"brand": spec["brand"], "talent": (ad or {}).get("cast"), "avatar": spec["avatar"],
                    "format": (ad or {}).get("format"), "concept": (ad or {}).get("concept"),
                    "angle": (ad or {}).get("angle", "unsigned"), "batch": spec["batch"],
                    "lane": spec.get("lane") or spec["avatar"], "sub": (ad or {}).get("sub")},
         "template": (ad or {}).get("template", "prompted"),
         "copy": {"slots": (ad or {}).get("copy", {}), "provenance": "declared" if (ad or {}).get("copy") else "unknown"},
         "offer": {"id": (spec.get("offer") or {}).get("id", "unknown"), "bar_text": "unknown"},
         "prompt": R.prompt_for(run_dir / "ads" / slug, slug),
         "location": {"drive_id": None, "drive_path": f"rejected/{slug}.png", "durable_url": None},
         "qc": {"status": "reject", "checks_run": "standing + product + own", "fails": fails,
                "judge_model": "unknown", "coverage": "measured + seen + price pass"}}
    n = len(list((run_dir / "rejected").glob(f"{slug}*.png"))) or 1
    R.write(R.item_id(spec["batch"], slug, f"r{n}"), "image-production", v, via="finish.py")


def finish(run_dir, dry=False, model=None):
    run_dir = Path(run_dir).resolve()
    spec = json.loads((run_dir / "batch.json").read_text())
    inbox = run_dir / "inbox"
    if not inbox.is_dir():
        raise SystemExit(f"no inbox in {run_dir}")

    ads = {a["slug"]: a for a in spec["ads"]}
    passed, killed = [], []
    verdicts = {}

    for img in sorted(inbox.glob("*.png")):
        slug = img.stem
        ad = ads.get(slug)
        if not ad:
            killed.append((slug, ["not in batch.json — nothing declared it"]))
            continue

        tests = list(STANDING_CHECKS)
        if ad.get("shows_product", True):
            tests += product_checks(spec, run_dir, slug)
        tests += headline_check(ad) + ad.get("checks", [])

        if (ad.get("ratio") or spec.get("ratio", "9x16")) == "9x16":
            PAD.pad(img)                      # 4:5 → 9:16, solid bands, in place
        fails = measured(img, spec, ad)
        raw = ""
        if not fails:                      # measured failures short-circuit
            fails, raw = seen(img, tests, model)
            # The offer bar gets a second look on its own, zoomed. A wrong
            # price is the one defect that costs money rather than face.
            fails += price_pass(img, spec, model)

        if fails:
            killed.append((slug, fails))
            verdicts[slug] = {"verdict": "reject", "fails": fails, "checks_run": tests,
                              "judge_model": model or "gemini (gemini_image.py default)"}
            if not dry:
                rej = run_dir / "rejected"
                rej.mkdir(exist_ok=True)
                shutil.copy2(img, rej / img.name)
                (rej / f"{slug}-why.md").write_text(
                    f"# {slug} — rejected\n\n"
                    + "\n".join(f"- {f}" for f in fails)
                    + ("\n\n<details><summary>judge, raw</summary>\n\n"
                       f"```\n{raw}\n```\n</details>\n" if raw else "\n"))
        else:
            passed.append(slug)
            verdicts[slug] = {"verdict": "pass", "fails": [], "checks_run": tests,
                              "judge_model": model or "gemini (gemini_image.py default)"}
            if not dry:
                dest = run_dir / "ads" / slug
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img, dest / "a01.png")

    if not dry:
        # The media gate — the judge's verdicts, declared. A picture it failed
        # is HELD from delivery with the reason (check.json); it was never
        # copied into ads/, so nothing below can ship it. Verdict logic above
        # is untouched; survivors still ship.
        (run_dir / "verdicts.json").write_text(
            json.dumps(verdicts, indent=1, ensure_ascii=False) + "\n")
        G.media_gate(run_dir, killed)
        held_slugs = {s for s, _ in killed}
        passed = [s for s in passed if s not in held_slugs]
        drive_ids = {}
        for slug in passed:
            ad = ads[slug]
            fields = {"brand": spec["brand"], "product": spec["product"],
                      "media": spec.get("media", "static"), "source": spec.get("source", "ai"),
                      "talent": ad.get("cast", "none"), "avatar": spec["avatar"],
                      "problem": ad.get("problem") or spec["problem"],
                      "angle": ad.get("angle", "unsigned"), "concept": ad["concept"],
                      "format": ad["format"], "brief": spec.get("brief", "p001"),
                      "ratio": ad.get("ratio") or spec.get("ratio", "9x16")}
            # The half of the record the name does not carry, keyed by the
            # file's name BEFORE delivery renames it.
            unit = run_dir / "ads" / slug
            extra = {f.name: asset_extra(ad, spec, run_dir, slug, verdicts.get(slug, {}))
                     for f in unit.iterdir() if f.suffix.lower() == ".png"}
            D.deliver(unit, fields, extra=extra, batch=spec["batch"])
            if spec.get("drive_root"):
                drive_ids.update(upload_unit(unit, spec, fields))
            R.made_from_manifest(unit / "manifest.json", run_dir / "batch.json", drive_ids)
        for slug, fails in killed:
            reject_record(run_dir, spec, ads.get(slug), slug, fails)

    report = [f"# {spec['brand']} · {spec['batch']} — finish report", "",
              f"**{len(passed)} passed · {len(killed)} rejected** "
              f"of {len(passed)+len(killed)} generated", ""]
    if passed:
        report += ["## Shipped", ""] + [f"- `{s}`" for s in passed] + [""]
    if killed:
        report += ["## Rejected — every one of these is a prompt to fix", ""]
        for slug, fails in killed:
            report.append(f"**{slug}**")
            report += [f"  - {f}" for f in fails]
            report.append("")
    text = "\n".join(report)
    if not dry:
        (run_dir / "report.md").write_text(text)
        # The record — text only, never a picture — to the repo-root runs/.
        G.file_quietly(G.file_record, run_dir)
    print(text)
    if not dry and passed:
        root = spec.get("drive_root")
        print("\nDelivered → " + (f"https://drive.google.com/drive/folders/{root}" if root
                                  else "nowhere on Drive — batch.json has no `drive_root`; the assets are named and recorded in the repo"))
    return passed, killed


def main():
    a = argparse.ArgumentParser()
    a.add_argument("run_dir")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--model", help="vision model for the judge")
    o = a.parse_args()
    finish(o.run_dir, dry=o.dry_run, model=o.model)


if __name__ == "__main__":
    main()
