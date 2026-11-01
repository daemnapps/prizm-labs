#!/usr/bin/env python3
"""LD-86 (old records repaired): a one-time repair of named picture records into LD-81 (portable picture records)'s
shape, so remake() reads their references on any Mac. Ruled for the five brand-b nov records only (the team, relayed
2026-10-22: "repair the old records" — it overrides the "no backfill" line for those five); every other old record
stays as LD-80 (stored path check) lists it.

    python3 tools/email-production/design/repair_records.py --dry-run <record.json> ...   every mapping, nothing written
    python3 tools/email-production/design/repair_records.py <record.json> ...             written in place

A reference that holds only a machine "path" maps by the FORM of that path, from the path itself, brandpath's drive
index and the run's media/drive.json — no network, no key:

  1 brandpath cache    /var/folders/…/T/brandpath-drive-cache/<brand>/<drive id>/<name>
                       -> the index row for that id: {drive_id, label "Shared Assets/" + its drive_path, bytes}
  2 Drive-app mount    …/Library/CloudStorage/GoogleDrive-…/Shared drives/Shared Assets/<rest>
                       -> {label "Shared Assets/<rest>"}; the index row's drive_id (and bytes) too only when <rest> IS
                       that row's drive_path
  3 a clone's run      …/runs/email-production/<brand>/<label>/media/<file>
                       -> picture_record._drive_row() (the run's drive.json row), else {label} where mirror() puts it,
                       picture_record._folder() + "/media/<file>"
  4 anything else      left exactly as it is and LISTED; never guessed (so is a form-1 path with no index row, or
                       whose name is not the row's)

The entry is written by picture_record._entry() itself, so the shape is LD-81's and never restated here. Pins (kind
holding "pin") are never touched: remake() skips them by design. A reference that already has "ref" is LD-81's shape
and stays. The record's "file" gains "file_ref" only from the record's own run's drive.json (form 3), else stays
without one (remake() falls back to the mirror label). A second run changes nothing.
"""
import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent.parent / "brandpath"))   # the sibling component, as look.py reaches it
import brandpath  # noqa: E402
import drive_index as DI  # noqa: E402
import picture_record as PR  # noqa: E402

CACHE = re.compile(r"^(?:/private)?/var/folders/.+/T/brandpath-drive-cache/([^/]+)/([^/]+)/([^/]+)$")
MOUNT = re.compile(r"/Library/CloudStorage/GoogleDrive-[^/]+/Shared drives/Shared Assets/(.+)$")
RUN_MEDIA = re.compile(r"/runs/email-production/([^/]+)/([^/]+)/media/([^/]+)$")


def _index_ref(r):
    """An index row as an LD-79 (Drive ref resolver) ref."""
    ref = {"drive_id": r["drive_id"], "label": "Shared Assets/" + r["drive_path"]}
    if r.get("bytes") is not None:
        ref["bytes"] = r["bytes"]
    return ref


def place(path, brand, repo, brands_dir):
    """(form, ref, note) for a stored machine path — note says why form 3 fell back to the mirror label, else None —
    or (None, None, why) when it is left as it is."""
    p = str(path)
    m = CACHE.match(p)
    if m:
        b, fid, name = m.groups()
        r = DI.row(b, fid, brands_dir)
        if not r or r.get("drive_id") != fid or not r.get("drive_path"):
            return None, None, "brandpath cache, but %s's drive index has no row for %s" % (b, fid)
        if PurePosixPath(r["drive_path"]).name != name:
            return None, None, "brandpath cache, but the index row for %s is %s, not %s" % (fid, r["drive_path"], name)
        return 1, _index_ref(r), None
    m = MOUNT.search(p)
    if m:
        rest = m.group(1)
        r = DI.row(brand, rest, brands_dir)
        if r and r.get("drive_id") and r.get("drive_path") == rest:
            return 2, _index_ref(r), None
        return 2, {"label": "Shared Assets/" + rest}, None
    m = RUN_MEDIA.search(p)
    if m:
        b, label, name = m.groups()
        run_dir = Path(repo) / "runs" / "email-production" / b / label
        got = PR._drive_row(run_dir, run_dir / "media" / name)
        if got:
            return 3, got, None
        return 3, {"label": "%s/media/%s" % (PR._folder(b, run_dir), name)}, _no_row(run_dir / "media" / name)
    return None, None, "a form this repair does not know"


def _no_row(f):
    """Why picture_record._drive_row() gave no row: no drive.json, or no picture on this Mac for its bytes."""
    if not (f.parent / "drive.json").is_file():
        return "the mirror label: the run has no media/drive.json"
    if not f.is_file():
        return "the mirror label: the picture is not on this Mac, so _drive_row() gives no drive.json row"
    return "the mirror label: the run's drive.json names no Drive id for it"


def _shaped(r, ref):
    """The reference in LD-81's shape, written by picture_record._entry() itself: its _store is handed the ref found
    here for this one call, so nothing is put and the shape is never restated. Every other key ("pinterest", …)
    rides along as _entry's extra."""
    extra = {k: v for k, v in r.items() if k not in ("path", "kind")}
    real = PR._store
    PR._store = lambda run_dir, brand, path: (ref, None)
    try:
        return PR._entry(None, None, r["path"], r.get("kind"), extra or None)
    finally:
        PR._store = real


def repair(rec_path, repo, brands_dir, out):
    """Repair one record in memory; returns (new record, counts, listed). Prints every mapping to `out`."""
    rec_path = Path(rec_path)
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    run_dir = rec_path.parents[3]                    # <run>/media/records/<label>/record.json
    brand = run_dir.parent.name
    n = {"form 1": 0, "form 2": 0, "form 3": 0, "file_ref": 0, "pins": 0, "already": 0, "left": 0}
    listed = []
    refs = []
    for r in rec.get("references") or []:
        kind = r.get("kind") or ""
        if "pin" in kind.lower():
            n["pins"] += 1
            refs.append(r)
            continue
        if "ref" in r:
            n["already"] += 1
            refs.append(r)
            continue
        form, ref, why = place(r.get("path"), brand, repo, brands_dir)
        if ref is None:
            n["left"] += 1
            listed.append((kind, r.get("path"), why))
            print("   LEFT AS IT IS · %s · %s — %s" % (kind, r.get("path"), why), file=out)
            refs.append(r)
            continue
        n["form %d" % form] += 1
        print("   form %d · %s · %s\n      -> %s%s" % (form, kind, r.get("path"), json.dumps(ref, ensure_ascii=False),
                                                     "  (%s)" % why if why else ""), file=out)
        refs.append(_shaped(r, ref))
    new = {}
    for k, v in rec.items():
        new[k] = refs if k == "references" else v
        if k == "file" and "file_ref" not in rec and isinstance(v, str) and v.startswith("media/"):
            got = PR._drive_row(run_dir, run_dir / v)
            if got:
                new["file_ref"] = got
                n["file_ref"] += 1
                print("   file · %s\n      -> file_ref %s" % (v, json.dumps(got, ensure_ascii=False)), file=out)
            else:
                print("   file · %s — no file_ref; remake() uses %s" % (v, _no_row(run_dir / v)), file=out)
    return new, n, listed


def main(argv=None, out=None):
    out = out or sys.stdout
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("records", nargs="+", help="record.json files to repair")
    ap.add_argument("--dry-run", action="store_true", help="print every mapping, write nothing")
    ap.add_argument("--repo", help="the workspace root (default: brandpath's repo())")
    ap.add_argument("--brands-dir", help="the brands folder (default: <repo>/brands)")
    a = ap.parse_args(argv)
    repo = Path(a.repo) if a.repo else Path(brandpath.repo(HERE))
    brands_dir = Path(a.brands_dir) if a.brands_dir else repo / "brands"
    total = {"form 1": 0, "form 2": 0, "form 3": 0, "file_ref": 0, "pins": 0, "already": 0, "left": 0}
    changed, all_listed = 0, []
    for f in a.records:
        f = Path(f)
        try:
            shown = f.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            shown = str(f)
        print(shown, file=out)
        old = f.read_text(encoding="utf-8")
        new, n, listed = repair(f, repo, brands_dir, out)
        text = json.dumps(new, indent=1, ensure_ascii=False) + "\n"
        for k in total:
            total[k] += n[k]
        all_listed += [(shown,) + x for x in listed]
        if text != old:
            changed += 1
            if not a.dry_run:
                f.write_text(text, encoding="utf-8")
            print("   => %s" % ("would change (dry run)" if a.dry_run else "written"), file=out)
        else:
            print("   => unchanged", file=out)
    print("\nsummary: %d record%s · %d reference%s repaired (form 1: %d, form 2: %d, form 3: %d) · %d file_ref added · "
          "%d already LD-81 · %d pin%s untouched · %d left as they are · %d record%s %s"
          % (len(a.records), "" if len(a.records) == 1 else "s",
             total["form 1"] + total["form 2"] + total["form 3"],
             "" if total["form 1"] + total["form 2"] + total["form 3"] == 1 else "s",
             total["form 1"], total["form 2"], total["form 3"], total["file_ref"], total["already"],
             total["pins"], "" if total["pins"] == 1 else "s", total["left"], changed, "" if changed == 1 else "s",
             "would change — dry run, nothing written" if a.dry_run else "changed"), file=out)
    for rec, kind, path, why in all_listed:
        print("LEFT AS IT IS: %s · %s · %s — %s" % (rec, kind, path, why), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
