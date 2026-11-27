"""NEW ONLY — old people, old sets and old product pictures never reach a new ad.

The list is data, one per brand: `runs/ai-elements/<brand>/new-only.json`. Only a row with
`status: approved` refuses, so a built list changes nothing until the owner's yes
(`approve`). A run named in `in_flight` finishes with what it started with; every other
run is refused by name. New names pass: nothing here needs a person or set listed to be
allowed, so a character made for a piece just works.

    python3 new_only.py build <brand>                write or refresh the list (rows stay draft)
    python3 new_only.py approve <brand> [--group g]  the owner's yes: rows refuse from now on
    python3 new_only.py check <brand> <what>         say what a person id or picture path gets
    python3 new_only.py show <brand>                 the counts

Stdlib only and no package imports, so another component can load this file by path.
Public: old_person, old_set, old_picture, refuse_person, refuse_set, refuse_pictures,
run_of, keep, fresh_product, sheet_views, sheet_cutouts, copy_of_old.
"""
import argparse
import fnmatch
import glob
import json
import os
import sys
from pathlib import Path

FILE = "new-only.json"
GROUPS = ("people", "sets", "pictures")
STILL_RUNNING = ("making", "editing", "final-needs-you")


def root():
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(__file__).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of %s" % here)


def path_of(brand, ws=None):
    return Path(ws or root()) / "runs" / "ai-elements" / str(brand) / FILE


def manifest(brand, ws=None):
    try:
        return json.loads(path_of(brand, ws).read_text())
    except (OSError, ValueError):
        return {}


def _row(m, group, rid):
    r = (m.get(group) or {}).get(str(rid))
    return r if r and r.get("status") == "approved" else None


def _finishing(m, run):
    return bool(run) and Path(str(run)).name in (m.get("in_flight") or [])


def old_person(brand, person, run=None, ws=None):
    """Why this person is out, or None."""
    m = manifest(brand, ws)
    r = _row(m, "people", person)
    if not r or _finishing(m, run):
        return None
    return "%s is off the %s cast: %s" % (person, brand, r.get("why") or "removed")


def old_set(brand, set_id, run=None, ws=None):
    m = manifest(brand, ws)
    r = _row(m, "sets", set_id)
    if not r or _finishing(m, run):
        return None
    return "set %s is out for %s: %s" % (set_id, brand, r.get("why") or "removed")


def _places(text):
    """(brand, kind, id) when a path sits under the element bank, else (brand or None, None, None)."""
    parts = text.split("/")
    for i, p in enumerate(parts):
        if p == "ai-elements" and len(parts) > i + 3:
            return parts[i + 1], parts[i + 2], parts[i + 3]
        if p == "brands" and len(parts) > i + 1:
            return parts[i + 1], None, None
    return None, None, None


def run_of(path):
    """The run a working path belongs to: runs/<tool>/<brand>/<label>/…, else None."""
    parts = str(path).split("/")
    for i, p in enumerate(parts):
        if p == "runs" and len(parts) > i + 3 and parts[i + 1] != "ai-elements":
            return parts[i + 3]
    return None


def old_picture(path, brand=None, run=None, ws=None):
    """Why this picture is out, or None. A file of an out person or set, or a picture matching
    a `pictures` row (an old packshot, a store photo, a past ad)."""
    text = str(path).replace(os.sep, "/")
    held, kind, rid = _places(text)
    if kind == "casting":
        return old_person(held, rid, run, ws)
    if kind == "sets":
        return old_set(held, rid, run, ws)
    brand = brand or held
    if not brand:
        return None
    m = manifest(brand, ws)
    if _finishing(m, run):
        return None
    for rid, r in (m.get("pictures") or {}).items():
        if r.get("status") == "approved" and (fnmatch.fnmatch(text, r.get("match") or "")
                                              or fnmatch.fnmatch("/" + text, r.get("match") or "")):
            return "%s is an old product picture (%s): %s" % (text.rsplit("/", 1)[-1], rid, r.get("why") or "")
    return None


def _refuse(why):
    raise SystemExit("NEW ONLY: %s. Use the new cast and the product's kit (runs/ai-elements)." % why)


def refuse_person(brand, person, run=None, ws=None):
    why = old_person(brand, person, run, ws)
    if why:
        _refuse(why)


def refuse_set(brand, set_id, run=None, ws=None):
    why = old_set(brand, set_id, run, ws)
    if why:
        _refuse(why)


def refuse_pictures(paths, brand=None, run=None, ws=None, out=None):
    """Stop at the first old picture in a list of references. `out` is the picture being made:
    its run finishes as it started, and email pictures are not this list's job."""
    if "email-production" in str(out or ""):
        return
    run = run or (run_of(out) if out else None)
    for p in paths or []:
        why = old_picture(p, brand, run, ws)
        if why:
            _refuse(why)


def keep(brand, people, key="id", ws=None):
    """A list of person rows with the out ones dropped."""
    return [p for p in people if not old_person(brand, p.get(key), ws=ws)]


def _kit(brand, slug, ws):
    home = Path(ws or root()) / "runs" / "ai-elements" / str(brand) / "products"
    hits = []
    for f in sorted(home.glob("*/kit.json")):
        try:
            k = json.loads(f.read_text())
        except ValueError:
            continue
        names = [f.parent.name] + list(k.get("aliases") or [])
        if slug in names:
            return f.parent, k
        if f.parent.name.startswith(str(slug) + "-"):
            hits.append((f.parent, k))
    return hits[0] if len(hits) == 1 else (None, None)


def fresh_product(brand, slug, ws=None):
    """(path, why) of the product shown new: the kit's chosen view, else its true-size front.
    (None, why) when the old pictures are still allowed for this brand or there is no kit."""
    m = manifest(brand, ws)
    if not any(r.get("status") == "approved" for r in (m.get("pictures") or {}).values()):
        return None, "old product pictures are not cut off for this brand"
    kit, k = _kit(brand, slug, ws)
    if kit is None:
        return None, "no kit for %s" % slug
    for p in ("model/sheet/current/front.png", "model/reference-front.png"):
        if (kit / p).is_file():
            return kit / p, "the product's current casting sheet, %s" % p
    return None, "the kit for %s holds no view yet" % slug


VIEWS = (("front", "the FRONT view"), ("three-quarter", "the THREE-QUARTER view"), ("side", "the SIDE view"),
         ("back", "the BACK view"))


def sheet_views(brand, slug, ws=None):
    """[(path, what side)] off the current casting sheet, once old product pictures are cut off for the brand."""
    if not fresh_product(brand, slug, ws)[0]:
        return []
    kit = _kit(brand, slug, ws)[0]
    return [(kit / "model/sheet/current" / ("%s.png" % v), w) for v, w in VIEWS
            if (kit / "model/sheet/current" / ("%s.png" % v)).is_file()]


def copy_of_old(path, brand, ws=None):
    """Why a loose picture file is out: it is a byte-for-byte copy of a blocked picture in a product's kit (a tool that
    pastes a product from its own folder carries no path the rows can match). None when it is not."""
    f = Path(path)
    if not f.is_file():
        return None
    size, data = f.stat().st_size, None
    for q in sorted((Path(ws or root()) / "runs" / "ai-elements" / str(brand) / "products").glob("*/model/*.png")):
        if q.stat().st_size != size or not old_picture(q, brand, ws=ws):
            continue
        data = data or f.read_bytes()
        if q.read_bytes() == data:
            return "%s is a copy of %s/model/%s, an old product picture" % (f.name, q.parents[1].name, q.name)
    return None


CUTOUTS = (("front", 0), ("three-quarter", 30), ("back", 180))


def sheet_cutouts(kit):
    """[(angle, path)] of the casting sheet's own views on a clear ground: what a tool lays into a picture."""
    d = Path(kit) / "model/sheet/current/cutouts"
    return [(a, d / ("%s.png" % v)) for v, a in CUTOUTS if (d / ("%s.png" % v)).is_file()]


def _first_made(folder):
    times = [os.path.getmtime(f) for f in glob.glob(str(folder) + "/**", recursive=True) if os.path.isfile(f)]
    return min(times) if times else None


def _running(brand, ws):
    try:
        rows = json.loads((Path(ws) / "runs" / "queue" / "index.json").read_text()).get("entries") or []
    except (OSError, ValueError):
        return []
    ids = {e["id"] for e in rows if e.get("brand") == brand and e.get("stage") in STILL_RUNNING and e.get("id")}
    briefs = {i.rsplit("_", 1)[-1] for i in ids if "brief-" in i}     # the run folder and the queue spell the product apart
    folders = (Path(ws) / "runs" / "video-production" / brand).glob("*brief-*")
    return sorted(ids | {d.name for d in folders if d.name.rsplit("_", 1)[-1] in briefs})


def build(brand, ws=None, cutoff="2026-10-30"):
    """Refresh the list from the removal list and the bank. A row already decided keeps its status."""
    import time
    ws = Path(ws or root())
    bank = ws / "runs" / "ai-elements" / brand
    was = manifest(brand, ws)
    limit = time.mktime(time.strptime(cutoff, "%Y-%m-%d"))
    rows = {g: dict(was.get(g) or {}) for g in GROUPS}     # a row stays when its folder has been moved out
    live = set(_running(brand, ws))
    removal = json.loads((bank / "removal-list.json").read_text())
    for p in removal.get("people") or []:
        rows["people"][p["person"]] = {"why": "marked Remove on the production page", "group": "removal"}
        live |= {str(x).split(" (")[0] for x in p.get("in_progress") or []}
    for d in sorted(p for p in bank.glob("casting/_*") if p.is_dir()):
        rows["people"][d.name] = {"why": "kept for the record, not a cast member", "group": "removal"}
    for group, rid, row in (was.get("extra_rows") or []):
        rows[group][rid] = row
    worlds = " ".join(f.read_text() for f in bank.glob("worlds/*/world.json"))
    in_world = {d.name for d in (bank / "sets").glob("*") if '"%s"' % d.name in worlds or "/%s/" % d.name in worlds}
    for d in sorted(p for p in (bank / "sets").glob("*") if p.is_dir()):
        t = _first_made(d)
        if t and t < limit and was.get("sets_ruled") and d.name not in in_world:
            rows["sets"][d.name] = {"why": "made before the rebuild", "group": "sets"}
    for rid, row in (was.get("picture_rows") or {}).items():
        rows["pictures"][rid] = dict(row, group="pictures")
    for g in GROUPS:
        for rid, row in rows[g].items():
            row["status"] = (was.get(g) or {}).get(rid, {}).get("status", "draft")
    out = dict(was, _what="What the chains refuse for this brand. Only approved rows refuse; a run in in_flight "
                          "finishes as it started. Built by components/casting/casting/new_only.py.",
               brand=brand, cutoff=cutoff, in_flight=sorted(live), **rows)
    path_of(brand, ws).write_text(json.dumps(out, indent=1, sort_keys=False) + "\n")
    return out


def approve(brand, group=None, ws=None):
    m = manifest(brand, ws)
    n = 0
    for g in GROUPS:
        for row in (m.get(g) or {}).values():
            if row.get("status") == "draft" and (group is None or row.get("group") == group):
                row["status"] = "approved"
                n += 1
    path_of(brand, ws).write_text(json.dumps(m, indent=1) + "\n")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("build", "approve", "check", "show"))
    ap.add_argument("brand")
    ap.add_argument("what", nargs="?")
    ap.add_argument("--group")
    ap.add_argument("--run")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        build(a.brand)
    if a.cmd == "approve":
        print(approve(a.brand, a.group), "rows now refuse")
    if a.cmd == "check":
        why = old_person(a.brand, a.what, a.run) or old_picture(a.what, a.brand, a.run) or old_set(a.brand, a.what, a.run)
        print(("REFUSED: " + why) if why else "ok")
        return 1 if why else 0
    if a.cmd in ("build", "show"):
        m = manifest(a.brand)
        for g in GROUPS:
            rows = (m.get(g) or {}).values()
            print(g, len(rows), "rows,", sum(1 for r in rows if r.get("status") == "approved"), "refusing")
        print("in flight", len(m.get("in_flight") or []))
    return 0


if __name__ == "__main__":
    sys.exit(main())
