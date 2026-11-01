#!/usr/bin/env python3
"""The delivery step — nothing leaves a run unnamed.

    deliver.py <folder> --brand <brand> --product <product> \
               --media static --source ai --talent none \
               --avatar <avatar> --format <format> \
               --concept <angle> --ratio 9x16

Renames every finished asset in the folder to the convention, writes the
manifest beside them, and prints the ad unit name to paste into Meta.

This is a **step in production**, not a tidy-up afterwards. An asset that
reaches Drive with a name like `ad-control.png` is already lost: nothing
joins it to spend, and by the time a report is being read nobody can
reconstruct which concept, format or identity it was. Naming happens once,
at the moment of delivery, by machine.

See CONVENTION.md for what each field means.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import names as N


def from_brief(brief):
    """problem / angle / concept, read from the brief that produced the ads.

    An angle typed at upload is a guess by whoever is uploading. An angle
    declared in the brief is the one the copy was written to — the only
    version worth grouping spend by."""
    import re
    p = Path(brief)
    if not p.is_file():
        return {}
    m = re.search(r"```json\s*(\{.*?\})\s*```", p.read_text(), re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    return {k: d[k] for k in ("problem", "angle", "concept") if d.get(k)}


def deliver(folder, fields, extra=None, batch=None, dry=False):
    folder = Path(folder)
    if not folder.is_dir():
        raise SystemExit(f"{folder} is not a folder")
    batch = batch or N.next_batch(fields["brand"])
    # Built from AD_FIELDS in order, so adding or removing a field in
    # names.py never leaves this call silently one argument behind.
    ad = N.ad_name(*[batch if f == "batch" else fields[f]
                     for f in N.AD_FIELDS])

    # The angle vocabulary belongs to the brand's own angle source, not to
    # whoever types the delivery command. A warning, never a block — an
    # unsigned angle is a strategy gap to close, not a reason to hold ads.
    warn = N.check_angle(fields["brand"], fields["angle"])
    if warn:
        print(f"  ! {warn}")

    # Anything already named to the convention keeps its place; everything
    # else is a fresh asset. Sorted so the numbering is stable across reruns.
    assets = sorted((p for p in folder.iterdir()
                     if p.is_file()
                     and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".mp4"}
                     and not p.name.startswith(".")),
                    key=lambda p: p.name)

    # A folder handed to the gate holds deliverables and nothing else.
    # Measured 2026-09-02: six rejected builds sat beside six good ones and
    # all twelve were given shipping names — after which nothing on disk
    # said which six the builder had refused.
    rejected = [p.name for p in assets if p.name.upper().startswith("FLAGGED")]
    if rejected:
        raise SystemExit(
            f"{len(rejected)} rejected build(s) in {folder}: "
            f"{rejected[0]} … — move them out before delivering. The gate "
            f"does not put a shipping name on work the builder refused.")
    if not assets:
        raise SystemExit(f"no assets to deliver in {folder}")

    rows, plan = [], []
    for i, f in enumerate(assets, 1):
        dst = folder / f"{N.asset_name(ad, i)}{f.suffix.lower()}"
        plan.append((f, dst))
        # The filename, not a path. The folder travels — to Drive, into an
        # upload — and a stored path stops being true the moment it does.
        rows.append({"name": dst.stem, "ad_name": ad, "file": dst.name,
                     **(extra or {}).get(f.name, {})})

    if dry:
        print(f"ad unit  {ad}")
        for a, b in plan:
            print(f"  {a.name}  →  {b.name}")
        return ad, rows

    for a, b in plan:
        N.rename_to(a, b)
    man = {"ad_name": ad, "batch": batch, **fields,
           "_upload": f"All {len(rows)} assets go into ONE ad unit named "
                      f"'{ad}'. Meta reports one row for the unit.",
           "_join": "Meta's ad_name equals `ad_name`. Read it with "
                    "names.parse_any (either form) for "
                    + ", ".join(N.AD_FIELDS) + ".",
           "ads": rows}
    (folder / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")

    gone = N.audit(folder / "manifest.json")
    if gone:
        raise SystemExit(f"manifest lists files that do not exist: {gone}")
    print(f"ad unit  {ad}")
    print(f"assets   {len(rows)}  ·  manifest written  ·  audit clean")
    return ad, rows


def main():
    a = argparse.ArgumentParser()
    a.add_argument("folder")
    for f in N.AD_FIELDS:
        if f != "batch":
            a.add_argument(f"--{f}", required=(f not in ("problem","angle","concept")), default="unsigned" if f=="angle" else None)
    a.add_argument("--batch")
    a.add_argument("--brief-file", help="read problem/angle/concept from this "
                                        "brief instead of the flags")
    a.add_argument("--extra-json", help="per-asset fields keyed by the file's "
                   "CURRENT name, merged into its manifest row — the half of "
                   "the record the name does not carry (sub, hook, copy, qc)")
    a.add_argument("--dry-run", action="store_true")
    o = a.parse_args()
    fields = {f: getattr(o, f) for f in N.AD_FIELDS if f != "batch"}
    if o.brief_file:
        declared = from_brief(o.brief_file)
        for k, v in declared.items():
            if fields.get(k) and fields[k] != v:
                print(f"  ! {k}: brief says {v!r}, flag says {fields[k]!r} "
                      f"— using the brief")
            fields[k] = v
    extra = json.loads(Path(o.extra_json).read_text()) if o.extra_json else None
    deliver(o.folder, fields, extra=extra, batch=o.batch, dry=o.dry_run)


if __name__ == "__main__":
    main()
