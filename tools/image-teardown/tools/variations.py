#!/usr/bin/env python3
"""The variation batch — every brief's written variations, made off its winner.

    variations.py --brand <brand> --product <product>
    variations.py --brand <brand> --product … --briefs p158,p159
    variations.py --brand <brand> --product … --dry-run
    variations.py --brand <brand> --product … --no-name      stop before naming

Damon, 2026-09-23: *"we need to just focus on this image editing so we can
get our batch of variations from the briefs, that's the whole point of this
stage specifically."*

**This stage ends at named pictures.** Not at ad copy, not at an import
sheet — those were taken out of it on his word the same day ("don't worry
about primary text yet, remove that from the chain"). What comes out is a
batch a person can load; what goes in is briefs that already have a judged
draft (the draft standard) and the variations stage 4 wrote for them.

One delta per picture, off the proven baseline, so a difference in the
account can only be the thing that moved.

    1  read      each brief's written headline variations (headline_sets.py)
    2  generate  one call per variation — the image-edit engine, the swipe's
                 own draft as the reference
    3  judge     the two-picture judge: change present · nothing else moved
    4  stage     baseline first, then its variations, one folder per brief
    5  name      the convention, one ad unit per brief, assets a01…aNN
    6  list      drop.csv — every asset, its ad name, the headline it carries
    7  mirror    Drive, at the mirrored runs path

**One call per variation, never one call with five.** The engine names a
result's folder after the row it ran, so five `headline` rows in one call
land on top of each other.

**A refusal is retried before it is believed.** The image provider
rate-limits a burst — six at once refused fifty-four of sixty on 2026-09-23
and every one of them succeeded alone.

A brief whose stage 4 wrote no variations is a text-free ad: it is listed as
skipped and nothing is invented for it. Its variations are pictures, which
is a generation, not an edit.
"""
import argparse, csv, json, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import briefs as B
import deliver as DV
import headline_sets as HS
import worksheet as WS_
N = B.N                            # components/naming/names — parse_any

WS = P.REPO
ROOT = P.LANE                      # the lane: worksheets, drafts, runs
VARY = WS / "tools/image-edit/vary.py"


def wanted(rec):
    """What this brief asks to be varied, and how.

    Stage 4 writes headline variations for an ad that carries a headline;
    stage 5 writes PICTURE variations — a body part, a setting, a different
    person — for one that does not. Damon, 2026-09-23: "run the variations
    for what needs a variation." Both are one delta off the winner; only the
    delta differs, so both run through the same stage."""
    hs = HS.for_brief(rec)
    if hs:
        return "headline", [{"n": v["n"], "delta": v["headline"],
                             "label": v["headline"]} for v in hs]
    _, ps = WS_.variations(B.run_dir(rec))
    return "picture", [{"n": i, "delta": (v["moved"] or v["name"]).strip(),
                        "label": v["name"]}
                       for i, v in enumerate(ps, 1) if (v["moved"] or v["name"])]


def _made(out):
    """The delivered picture, if this variation has one. The file on disk is
    the truth: a dry run overwrites variations.json with `dry` and a move
    rewrites its paths, but a delivered picture is a delivered picture."""
    return next((x for x in out.rglob("*.png")
                 if "engine" not in str(x) and "rejected" not in str(x)), None)


def _state(out, dry):
    if _made(out):
        return "pass", ""
    rec = out / "variations.json"
    if not rec.is_file():
        rec = out / "edit.json"          # the edit door keeps its own record
    if not rec.is_file():
        return None, ""
    d = json.loads(rec.read_text())
    if dry:
        return "dry", ""
    if d.get("delivered"):
        return "pass", ""
    if d.get("rejected"):
        return "held", ""
    # variations.json wraps its rows; edit.json IS the row
    rows = d.get("variations") or [d]
    return "refused", ((rows or [{}])[0].get("refused") or "")


def one(brand, bid, v, baseline, drop, dry, tries=3):
    """One variation, retried. The image provider rate-limits a burst — six
    at once refused fifty-four of sixty on 2026-09-23 and every one of them
    succeeded alone, so a refusal is retried before it is believed."""
    out = WS / "runs/image-edit" / brand / drop / "working" / bid / f"h{v['n']}"
    done, _ = _state(out, dry)
    if done == "pass":
        # resume, never re-spend — and a dry run stops HERE rather than
        # running vary.py, which would overwrite the real record with `dry`
        return bid, v, "pass", "already made"
    # The label nests under the run on BOTH planes — the Drive mirror is
    # built from it, so a flat label scattered twenty-four loose folders
    # across the brand's root (2026-09-23).
    if v.get("kind") == "picture":
        # no library row names "a body part" or "a setting", so the delta is
        # carried in words through the edit door — still ONE delta, still
        # judged against the baseline
        cmd = [sys.executable, str(WS / "tools/image-edit/edit.py"),
               str(baseline), "--brand", brand,
               "--label", f"{drop}/working/{bid}/h{v['n']}", "--out", str(out),
               "--change", v["delta"]]
    else:
        cmd = [sys.executable, str(VARY), str(baseline), "--brand", brand,
               "--label", f"{drop}/working/{bid}/h{v['n']}", "--out", str(out),
               "--v", f"headline:headline={v['delta']}"]
    if dry:
        cmd.append("--dry-run")
    note = ""
    for attempt in range(1, tries + 1):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WS))
        state, why = _state(out, dry)
        note = why or (r.stderr.strip().split("\n")[-1] if r.returncode else "")
        if state in ("pass", "held", "dry"):
            return bid, v, state, note
        if attempt < tries:
            time.sleep(20 * attempt)                   # let the burst drain
    return bid, v, "refused", note


# ---- steps 4-7: stage, name, list, mirror -------------------------------
def control_words(brand, bid):
    """The headline the baseline itself carries, off its own control prompt."""
    f = ROOT / "worksheets" / brand / bid / "prompts/00-control.txt"
    if not f.is_file():
        return ""
    m = re.search(r"THE WORDS, exactly:\s*(.+?)\. Spell", f.read_text(), re.S)
    if not m:
        return ""
    q = re.findall(r'"([^"]+)"', m.group(1))
    return " / ".join(q) if q else m.group(1).strip()[:90]


FINISH = WS / "tools/image-production/finish.py"


def as_9x16(src, dst):
    """Every asset is 9:16 (the 22 Sep frame rule). A brief's draft is 4:5
    content, so the baseline is FINISHED into the batch, never copied raw —
    ten of eleven baselines shipped at 4:5 beside their own 9:16 variations
    before this (2026-09-23)."""
    from PIL import Image
    w, h = Image.open(src).size
    if abs(w / h - 9 / 16) < 0.02:
        shutil.copy(src, dst)
        return "already 9:16"
    # finish in a scratch dir: it writes its mask, canvas and raw beside the
    # output, and those must not sit in the folder a person opens to load from
    import tempfile
    with tempfile.TemporaryDirectory(prefix="finish-") as tmp:
        made = Path(tmp) / dst.name
        r = subprocess.run([sys.executable, str(FINISH), str(src), "--out", str(made)],
                           capture_output=True, text=True, cwd=str(WS))
        if r.returncode or not made.is_file():
            shutil.copy(src, dst)
            return "finish failed — shipped at its own frame"
        shutil.copy(made, dst)
    return "finished to 9:16"


def stage_one(brand, bid, vs, baseline, out, folder_name=None):
    """Baseline first, then its variations — the order the asset ids follow.

    The folder is named for the AD UNIT once it has one, so the folder a
    person opens to load from carries the name they paste into Meta; a brief
    id names it only until the run is named (Damon, 2026-09-23: "I don't see
    you've used the proper naming conventions for this step")."""
    d = out / "deliverable" / (folder_name or bid)
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.png"):
        old.unlink()
    as_9x16(baseline, d / "00-baseline.png")
    for v in sorted(vs, key=lambda x: x["n"]):
        src = out / "working" / bid / f"h{v['n']}"
        f = [x for x in src.rglob("*.png")
             if "engine" not in str(x) and "rejected" not in str(x)]
        if f:
            shutil.copy(f[0], d / f"{v['n']:02d}-headline.png")
    return d


def name_one(brand, bid, rec, folder, batch, product):
    """The convention, through the delivery gate. The format comes off the
    run's own element labels (stage 2b) — never guessed here, and a run
    without them is named without a format rather than with a wrong one."""
    el = WS / "runs/image-teardown" / brand / rec["run"] / "elements.json"
    fmt = None
    if el.is_file():
        fmt = (json.loads(el.read_text()).get("labels") or {}).get("format/image")
    if fmt in (None, "none-fits"):
        return None, "no format label — run `chain.py fill --labels` first"
    dec = rec.get("declares") or {}
    cmd = [sys.executable, str(WS / "components/naming/deliver.py"), str(folder),
           "--brand", brand, "--product", product or rec.get("product"),
           "--media", "static", "--source", "ai", "--talent", "none",
           "--avatar", rec.get("avatar") or "", "--format", fmt,
           "--brief", bid, "--ratio", "9x16", "--batch", batch]
    for k in ("problem", "angle", "concept"):
        if dec.get(k):
            cmd += [f"--{k}", dec[k]]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WS))
    if r.returncode:
        return None, (r.stderr.strip().split("\n")[-1] or "deliver refused")
    line = next((l for l in r.stdout.splitlines() if l.startswith("ad unit")), "")
    return line.split(None, 2)[-1].strip() if line else None, ""


def write_list(brand, out, by, named):
    """drop.csv, and the headline written into each manifest.

    The list is EVERY folder in the deliverable, read off its own manifest —
    not only the ads that had variations. An ad whose brief wrote none still
    ships its winner, and a list built from the variations left ten of
    twenty-one ads out of it (2026-09-23)."""
    rows = []
    for mf in sorted((out / "deliverable").glob("*/manifest.json")):
        m = json.loads(mf.read_text())
        # the brief is a field of the ad name — read it there, not off the
        # variations, or an ad with none lists a blank brief (2026-09-23)
        # either form (`…-p140-9x16-260902a` or `…_brief-0140_9x16_batch-…`),
        # read by field name, never by position; the register keys on p140
        pa = N.parse_any(m.get("ad_name", ""))
        bid = B.key(pa["brief"]) if pa and re.fullmatch(r"p\d{3}|brief-\d{4}", pa["brief"]) else None
        vs = sorted(by.get(bid, []), key=lambda x: x["n"]) if bid else []
        order = {"a01": (control_words(brand, bid) if bid else "",
                         "the winner — the ad already running")}
        for k, v in enumerate(vs, start=2):
            order[f"a{k:02d}"] = (v["headline"], f"headline variation {v['n']}")
        for a in m["ads"]:
            an = (N.parse_any(a["name"]) or {}).get("asset_n")
            tag = f"a{an:02d}" if an else a["name"].rsplit("-", 1)[-1]
            if tag in order:
                a["headline"], a["what"] = order[tag]
        mf.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
        for a in m["ads"]:
            rows.append([bid or "", m["ad_name"],
                         (N.parse_any(a["name"]) or {}).get("asset_id") or a["name"].rsplit("-", 1)[-1],
                         a.get("what", ""), a.get("headline", ""), a["file"]])
    f = out / "deliverable/drop.csv"
    with f.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["brief", "ad_name", "asset", "what", "headline", "file"])
        w.writerows(rows)
    return f, rows


def mirror(out, brand, drop):
    """Drive, at the mirrored runs path (the workspace rules §1)."""
    sa = P.DRIVE / "runs" / "image-edit" / brand / drop
    if not sa.parent.parent.exists():
        return None
    sa.mkdir(parents=True, exist_ok=True)
    if (sa / "deliverable").exists():
        shutil.rmtree(sa / "deliverable")
    shutil.copytree(out / "deliverable", sa / "deliverable")
    return sa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--product")
    ap.add_argument("--briefs")
    ap.add_argument("--drop", default=None)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-name", action="store_true",
                    help="stop after the judge — no staging, naming or mirror")
    ap.add_argument("--name-only", action="store_true",
                    help="steps 4-7 only: stage, name, list, mirror what is already made")
    ap.add_argument("--batch", help="the batch id (default: the next free one today)")
    a = ap.parse_args()

    # The label is the BATCH ID — the convention's own key for a day's run,
    # and the last field of every filename in it. A long descriptive label
    # said the same thing twice and matched nothing (2026-09-23).
    batch = a.batch
    if not batch:
        r = subprocess.run([sys.executable, str(WS / "components/naming/names.py"),
                            "next-batch", a.brand], capture_output=True, text=True, cwd=str(WS))
        batch = r.stdout.strip().splitlines()[-1].strip() if r.returncode == 0 else None
    drop = a.drop or batch or f"{(a.product or a.brand)}-{date.today()}"
    reg = B.load()
    want = set(B.ids(reg, a.briefs.split(","))) if a.briefs else None   # either spelling

    jobs, skipped = [], []
    for bid, rec in sorted(reg["briefs"].items()):
        if rec.get("brand") != a.brand or not rec.get("run"):
            continue
        if a.product and rec.get("product") != a.product:
            continue
        if want and bid not in want:
            continue
        baseline = DV.newest_draft(a.brand, bid)
        kind, vs = wanted(rec)
        if not baseline:
            skipped.append((bid, "no judged draft to vary")); continue
        if not vs:
            skipped.append((bid, "its brief wrote no variations")); continue
        for v in vs:
            jobs.append((bid, {**v, "kind": kind, "headline": v["label"]}, baseline))

    print(f"{len(jobs)} variations · {len({j[0] for j in jobs})} ads · "
          f"{a.workers} at a time → runs/image-edit/{a.brand}/{drop}/")
    for bid, why in skipped:
        print(f"  – {bid}  {why}")
    print()

    done = []
    if a.name_only:
        # naming a batch again must never mean rolling its pictures again
        jobs = []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = [pool.submit(one, a.brand, bid, v, bl, drop, a.dry_run)
                for bid, v, bl in jobs]
        for f in as_completed(futs):
            bid, v, state, note = f.result()
            done.append({"brief": bid, "n": v["n"], "headline": v["headline"],
                         "state": state, "note": note})
            mark = {"pass": "✓", "held": "~", "dry": "·"}.get(state, "✗")
            print(f"  {mark} {bid} h{v['n']}  {v['headline'][:52]}"
                  + (f"   {note[:60]}" if note else ""))

    rec = WS / "runs/image-edit" / a.brand / drop / "drop.json"
    rec.parent.mkdir(parents=True, exist_ok=True)
    # The record accumulates. A `--briefs p158` run wrote it with five rows
    # and dropped the other fifty-five (2026-09-23); a partial run is normal
    # (a retry, one more ad) and must never shrink the drop.
    prior = json.loads(rec.read_text())["variations"] if rec.is_file() else []
    keep = {(d["brief"], d["n"]): d for d in prior}
    for d in done:
        keep[(d["brief"], d["n"])] = d
    done = list(keep.values())
    rec.write_text(json.dumps(
        {"brand": a.brand, "product": a.product, "drop": drop,
         "at": date.today().isoformat(), "baseline": "the brief's judged draft",
         "variations": sorted(done, key=lambda x: (x["brief"], x["n"])),
         "skipped": [{"brief": b, "why": w} for b, w in skipped]},
        indent=1, ensure_ascii=False) + "\n")
    # The index reads run-label depth and never descends. A drop files its
    # edits two levels further down (<brief>/h<n>/), so without a run.json
    # HERE the whole drop is invisible while every edit under it is filed.
    n = sum(1 for d in done if d["state"] == "pass")
    if a.name_only and rec.is_file():
        done = json.loads(rec.read_text())["variations"]
        n = sum(1 for d in done if d["state"] == "pass")

    # ---- 4-7: stage, name, list, mirror ---------------------------------
    named, refused = {}, []
    if n and not (a.dry_run or a.no_name):
        # EVERY ad goes in the batch, not only the ones that had variations.
        # Damon, 2026-09-23: "not all of them need headlines but I need all
        # ads and their variations in this deliverables folder so I can
        # upload everything." A text-free ad ships its winner alone.
        made = {b: [] for b, _ in [(x[0], x) for x in
                                   [(bid, rec) for bid, rec in sorted(reg["briefs"].items())
                                    if rec.get("brand") == a.brand and rec.get("run")
                                    and (not a.product or rec.get("product") == a.product)
                                    and (not want or bid in want)
                                    and DV.newest_draft(a.brand, bid)]]}
        for d in done:
            if d["state"] == "pass":
                made.setdefault(d["brief"], []).append(d)
        print(f"\nnaming · batch {batch}")
        for bid, vs in sorted(made.items()):
            brec = reg["briefs"][bid]
            folder = stage_one(a.brand, bid, vs, DV.newest_draft(a.brand, bid), rec.parent)
            ad, why = name_one(a.brand, bid, brec, folder, batch, a.product)
            if ad:
                named[bid] = ad
                want = folder.parent / ad
                if want != folder:                  # the folder carries the ad name
                    if want.exists():
                        shutil.rmtree(want)
                    folder.rename(want)
                print(f"  ✓ {bid}  {ad}")
            else:
                refused.append((bid, why))
                print(f"  ✗ {bid}  {why}")
        # the whole drop, not just this run: the record is the source
        on_record = json.loads((rec.parent / "drop.json").read_text())["variations"] \
            if (rec.parent / "drop.json").is_file() else []
        allpass = {}
        for d in on_record + done:
            if d["state"] == "pass":
                seen = allpass.setdefault(d["brief"], {})
                seen[d["n"]] = d
        allpass = {b: sorted(v.values(), key=lambda x: x["n"]) for b, v in allpass.items()}
        csvf, rows = write_list(a.brand, rec.parent, allpass, named)
        sa = mirror(rec.parent, a.brand, drop)
        print(f"\n{len(rows)} assets · {len(named)} ad units · list: "
              f"{csvf.relative_to(WS)}" + (f" · mirrored to Drive" if sa else ""))

    (rec.parent / "run.json").write_text(json.dumps(
        {"machine": "image-edit", "brand": a.brand, "label": drop,
         "state": "filed" if n else ("held" if done else "refused"),
         "ad_units": named, "unnamed": [{"brief": b, "why": w} for b, w in refused],
         "opened": date.today().isoformat()}, indent=1) + "\n")
    print(f"\n{n} of {len(done)} delivered · "
          f"{sum(1 for d in done if d['state'] == 'held')} held · "
          f"{sum(1 for d in done if d['state'] not in ('pass', 'held', 'dry'))} refused")
    print(f"record: {rec.relative_to(WS)}")


if __name__ == "__main__":
    main()
