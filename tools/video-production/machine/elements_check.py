"""The elements lock — every element a brief needs is banked and confirmed
before anything is paid for (the owner, 2026-09-23: "the system should prompt to
confirm the elements before going into actual production … and if elements
need to be generated we need to go through that step … standardize this part
of the process … every single line of execution is literally fool proof").

Three verbs:

    python3 elements_check.py sheet   <brief.md> --brand B [--out DIR]
    python3 elements_check.py confirm <run-dir>  --by NAME
    python3 elements_check.py status  <run-dir>

`sheet [--teardown DIR]` reads the brief's json block and lists every element it uses — each
PERSON (with the LOOK they wear in each scene and their VOICE if they speak),
each SETTING, the PRODUCT, every PROP — and resolves each against the brand's
bank. What a banked element must hold is not written here: it is read from
`../elements-standard.json` (the standard, `PRODUCTION-ELEMENTS.md`). Each
element comes back `banked` or `to make`, with the exact missing pieces.

`run.py start` calls `gate()`: an element still `to make` is REFUSED by name
(the make-list is written to `<run>/elements.json`); all banked but not
confirmed is REFUSED until `confirm` writes `<run>/elements-lock.json` with the
sheet's fingerprint. Change an element after confirming and the fingerprint no
longer matches — confirm again. A dry run reports and refuses nothing.

SWIPE FRAMES (the owner, 2026-10-08: "we can actually work with the real frames …
use those as the references"). Every element still `to make` carries
`swipe_frames`: the element the swipe's frame map cut out of its real frames
(video-teardown `framemap/elements/<kind>-<slug>/`, frame_elements.py) —
matched by the swipe person / place / prop the brief's "real reference" names,
else by the brief's own id, else by the times it names — with its best frame,
the frame nearest each time the brief names, and one crop per shot. So 3.2
starts from real frames; make_character.py / make_set.py take them as "real
video frame" references when a spec names none. The teardown run is
`--teardown`, else the production run's storyboard.json, else the brief's
writing-shelf slug, else the run's own name.

Brand content is read from `brands/<brand>/` only; nothing brand-specific
lives here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
import importlib.util as _ilu
_sp = _ilu.spec_from_file_location("vm_element_paths", Path(__file__).resolve().parent / "element_paths.py")
EP = _ilu.module_from_spec(_sp); _sp.loader.exec_module(EP)


def _workspace() -> Path:
    p = HERE
    while p != p.parent:
        if (p / "brands").is_dir() and (p / "components").is_dir():
            return p
        p = p.parent
    raise SystemExit("cannot find the workspace root (no brands/ + components/ above this file)")


def standard() -> dict:
    return json.loads((COMPONENT / "elements-standard.json").read_text())


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _json_block(text: str):
    import importlib.util as ilu   # by file — never HERE first on sys.path (it has a platform.py)
    sp = ilu.spec_from_file_location("vm_scenes", HERE / "scenes.py")
    scenes_mod = ilu.module_from_spec(sp); sp.loader.exec_module(scenes_mod)
    doc, _ = scenes_mod.json_block(text)
    return doc if isinstance(doc, dict) else {}


def _people_in(who: str, cast_ids: list[str]) -> list[str]:
    """Which cast ids a scene's `who` names (it is prose: "X's hands, and Y's
    forearm"). Longest id first so "THE DAUGHTER" wins over a shorter id."""
    who_u = (who or "").upper()
    return [c for c in sorted(cast_ids, key=len, reverse=True) if c.upper() in who_u]


def _files(folder: Path, patterns: list[str]) -> list[str]:
    out = []
    for pat in patterns:
        out += [str(p.relative_to(folder)) for p in sorted(folder.glob(pat)) if p.is_file()]
    return out


# A MINI RUN GETS ITS ELEMENTS FROM THE DRIVE (LD-28 (element fetch), 2026-10-19).
# Cast sheets, references and packshots are media, gitignored, so they never reach
# a worker's clone. Only in a worker spawn (DRIVE_MOUNT=off, LD-26 (mount switch)):
# the gate fetches each runs/ai-elements/ folder's missing files from its Drive twin,
# counts the product's Drive packshot and Drive-held references (nothing is fetched
# under brands/, a wall), and carries the owner's confirm from the brief's own folder.
# A person's own run never reaches any of it.
REACH = None        # gdrive-creator's reach, resolved on first use; the seam tests swap
# LD-60 (manifest reads Drive), 2026-10-21: in a worker spawn every door that asks "is it banked?" (the lock
# and the writing manifest) reads the SAME way — sheet(..., drive=True). A file not in this checkout counts
# when the Drive lists it by key: a runs/ folder's twin by reach.list_tree, a product picture by its row in
# brands/<brand>/products/DRIVE-INDEX.json (the Drive's own listing, kept in git). Listing only: nothing is
# downloaded and nothing is written; the lock still FETCHES what production will use, as before.
_DRIVE_LIST = []    # the brand, while sheet(drive=True) runs
_TWINS = {}         # (id(REACH), folder) -> [relative path] | None (not on the Drive), one listing per folder
_NO_DRIVE = []      # the SystemExit text once the Drive cannot be reached at all: said once, never re-asked
BRANDFILES = None   # this machine's brandfiles, resolved on first use; the seam tests swap
_DRIVE_BRAND = []   # the brand, only while gate() checks in a worker spawn


def _drive_mode() -> bool:
    import os
    return os.environ.get("DRIVE_MOUNT") == "off"


def _reach():
    global REACH
    if REACH is None:
        gd = next((d / "gdrive-creator" for d in HERE.parents
                   if (d / "gdrive-creator" / "gdrive_creator").is_dir()), None)
        if gd is not None and str(gd) not in sys.path:
            sys.path.append(str(gd))          # appended, never ahead of this machine
        from gdrive_creator import reach as R
        REACH = R
    return REACH


def _brandfiles():
    global BRANDFILES
    if BRANDFILES is None:
        sp = _ilu.spec_from_file_location("vm_brandfiles", HERE / "brandfiles.py")
        m = _ilu.module_from_spec(sp); sp.loader.exec_module(m)
        BRANDFILES = m
    return BRANDFILES


def _inside(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def fetch_from_drive(body: dict, ws: Path) -> list[str]:
    """Every file a sheet's runs/ai-elements/ folder holds on the Drive mirror
    (`Shared Assets/<the folder's repo path>`) and not here, copied into the
    same relative place. Never over a file that is here (exclusive create),
    never outside runs/ai-elements/, never under brands/. A folder the Drive
    does not have stays as it is. Returns notes of what was fetched or could
    not be."""
    import os
    import shutil
    import tempfile
    R = _reach()
    ws = ws.resolve()
    home = ws / "runs" / EP.ELEMENTS
    wall = ws / "brands"
    notes, seen, stage = [], set(), None
    for i in body["items"]:
        if not i.get("folder"):
            continue
        folder = (ws / i["folder"]).resolve()
        if folder in seen or not _inside(folder, home) or _inside(folder, wall):
            continue
        seen.add(folder)
        parts = list(folder.relative_to(ws).parts)
        label = "Shared Assets/" + "/".join(parts)
        try:
            tree = R.list_tree(parts)
        except SystemExit as e:
            # no Drive at all here (gdrive-creator's missing package or key): said
            # once, and the lock checks what is here — it refuses, never skips
            notes.append(f"no Drive here ({e}) — nothing fetched; the elements are checked as they are here")
            _NO_DRIVE[:] = [str(e)]
            break
        except Exception as e:
            notes.append(f"the Drive could not list {label} ({type(e).__name__}: {e}) — checked as it is here")
            continue
        _TWINS[(id(R), "/".join(parts))] = None if tree is None else [rel for rel, _fid in tree]
        n, skipped = 0, []
        for relpath, _fid in tree or []:
            dest = folder / relpath
            if not _inside(dest.resolve(), folder) or _inside(dest.resolve(), wall):
                skipped.append(relpath)
                continue
            if os.path.lexists(str(dest)):
                continue                      # here already: never overwritten
            sub = list(Path(relpath).parent.parts)
            if stage is None:
                stage = Path(tempfile.mkdtemp(prefix="elements-drive-"))
            sdir = stage.joinpath(*parts, *sub)
            sdir.mkdir(parents=True, exist_ok=True)
            try:
                got = R.get(parts + sub, Path(relpath).name, sdir)
                if not got or not Path(got).is_file():
                    skipped.append(relpath)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(str(got), "rb") as src, open(str(dest), "xb") as out:
                    shutil.copyfileobj(src, out)
                n += 1
            except FileExistsError:
                continue
            except Exception as e:
                skipped.append(f"{relpath} ({type(e).__name__}: {e})")
        if n:
            notes.append(f"fetched {n} file(s) from {label} into {folder.relative_to(ws)}")
        if skipped:
            notes.append(f"not fetched from {label}: " + ", ".join(skipped))
    return notes


def _product_on_drive(folder: Path, req) -> str | None:
    """The brand, when a worker spawn checks a product folder under brands/
    against the product standard; None otherwise (and always for a person)."""
    if not _DRIVE_BRAND:
        return None
    if req != standard()["product"]["requires"]:
        return None
    if not _inside(folder.resolve(), (_workspace() / "brands").resolve()):
        return None
    return _DRIVE_BRAND[0]


def _drive_packshot(brand: str, pid: str):
    """(True, why) when the brand's Drive packshot for the product is a file
    here — the door element_refs binds after the lock — else (False, why)."""
    try:
        got, why = _brandfiles().packshot_of(brand, pid, fetch=True)
    except (Exception, SystemExit) as e:
        return False, f"{type(e).__name__}: {e}"
    if got and not str(got).startswith(("http://", "https://")) and Path(str(got)).is_file():
        return True, why
    return False, why


def _drive_ref_gap(r: dict):
    """None when a reference missing here reads on the Drive by its
    `drive_path`; else the gap, by name."""
    dp = (r.get("drive_path") or "").strip().strip("/")
    if not dp:
        return f"reference {r['file']} is named but not in the folder and has no drive_path"
    label = dp if dp.startswith("Shared Assets/") else "Shared Assets/" + dp
    try:
        _reach().readable(label)
        return None
    except (Exception, SystemExit) as e:
        return (f"reference {r['file']} is named but not in the folder and its drive_path "
                f"{label} does not read ({type(e).__name__}: {e})")


def _listed_ref_gap(folder: Path, r: dict):
    """LD-60: None when a reference missing here is LISTED on the Drive — in its folder's twin, by the
    products index (old or current path, or its drive_id), or by its drive_path's id. Nothing is read."""
    if r["file"] in (_twin(folder) or []):
        return None
    brand = _DRIVE_LIST[0]
    try:
        rel = str(folder.resolve().relative_to((_workspace() / "brands" / brand).resolve()) / r["file"])
    except ValueError:
        rel = None
    for ref in (r.get("drive_id"), r.get("drive_path"), rel and "brands/%s/%s" % (brand, rel)):
        if ref and _indexed(brand, ref):
            return None
    dp = (r.get("drive_path") or "").strip().strip("/")
    if dp and not _NO_DRIVE:
        try:
            if _reach().drive_id(dp if dp.startswith("Shared Assets/") else "Shared Assets/" + dp):
                return None
        except (Exception, SystemExit):
            pass
    return (f"reference {r['file']} is named but not in the folder, and the Drive lists no copy of it "
            f"(no twin file, no products index row, no drive_path that resolves)")


def _carry_lock(run: Path, brief_dir: Path, fp: str):
    """the owner's confirm from the brief's own folder, when it confirmed exactly
    this set (an EQUAL fingerprint): copied into `<run>/elements-lock.json`
    with `carried_from`. None — and nothing written — otherwise."""
    src = brief_dir / "elements-lock.json"
    lock = run / "elements-lock.json"
    if lock.exists() or not src.is_file():
        return None
    try:
        held = json.loads(src.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(held, dict) or held.get("fingerprint") != fp:
        return None
    try:
        where = str(brief_dir.resolve().relative_to(_workspace().resolve()))
    except ValueError:
        where = str(brief_dir.resolve())
    held = dict(held, carried_from=where)
    lock.write_text(json.dumps(held, indent=1))
    return held


def _twin(folder: Path):
    """The Drive twin of a runs/ folder (`Shared Assets/<its repo path>`), as relative paths — one listing
    per folder per process, shared with fetch_from_drive. None when it is not on the Drive or not a runs/
    folder (brands/ pictures are found through the products index, never listed here)."""
    ws = _workspace().resolve()
    try:
        parts = list(folder.resolve().relative_to(ws).parts)
    except ValueError:
        return None
    if parts[:1] != ["runs"] or _NO_DRIVE:
        return None
    key = (id(_reach()), "/".join(parts))
    if key not in _TWINS:
        try:
            tree = _reach().list_tree(parts)
        except SystemExit as e:
            _NO_DRIVE[:] = [str(e)]
            return None
        except Exception:
            tree = None
        _TWINS[key] = None if tree is None else [rel for rel, _fid in tree]
    return _TWINS[key]


def _twin_has(folder: Path, patterns) -> int:
    import fnmatch
    names = _twin(folder) or []
    return len({n for n in names for pat in patterns if fnmatch.fnmatchcase(n, pat)})


def _indexed(brand: str, ref: str):
    """The products index row (brandpath drive_index) for an old or current path, or None — no network."""
    try:
        bp = next(d / "brandpath" for d in HERE.parents if (d / "brandpath" / "drive_index.py").is_file())
        if str(bp) not in sys.path:
            sys.path.append(str(bp))
        import drive_index as DI
        return DI.row(brand, ref, str(_workspace() / "brands"))
    except Exception:
        return None


def _indexed_packshots(brand: str, pid: str) -> list:
    try:
        bp = next(d / "brandpath" for d in HERE.parents if (d / "brandpath" / "drive_index.py").is_file())
        if str(bp) not in sys.path:
            sys.path.append(str(bp))
        import drive_index as DI
        return [r for r in DI.rows(brand, str(_workspace() / "brands"))
                if r.get("folder") == pid and r.get("kind") == "packshot" and r.get("drive_id")]
    except Exception:
        return []


def _quality_hold(folder: Path) -> list[str]:
    """A folder holding quality-hold.json is not complete, whatever else it has; an unreadable record holds too."""
    f = folder / "quality-hold.json"
    if not f.is_file():
        return []
    try:
        why = json.loads(f.read_text()).get("reason") or "held"
    except (ValueError, AttributeError) as e:
        return [f"quality hold record unreadable ({e}); fix or remove {f.name}"]
    return [f"quality hold: {why}"]


def _check_folder(folder: Path, req: dict) -> list[str]:
    """What a bank folder is missing, against one kind's `requires` rows."""
    missing = _quality_hold(folder)
    listed = bool(_DRIVE_LIST)
    if not folder.is_dir() and not (listed and _twin(folder)):
        return [f"no folder {folder.name}/ in the bank"]
    brand = _product_on_drive(folder, req)
    is_product = req == standard()["product"]["requires"]
    for row in req:
        found = _files(folder, row["files"]) if folder.is_dir() else []
        need = row.get("min", 1)
        if len(found) < need:
            if brand and row["name"] == "real packshot":
                ok, why = _drive_packshot(brand, folder.name)
                if ok:
                    continue
                missing.append(f"{row['name']} ({row['why']}) — not on the Drive either: {why}")
                continue
            if listed and is_product and row["name"] == "real packshot" \
                    and _indexed_packshots(_DRIVE_LIST[0], folder.name):
                continue        # on the Drive by its id (products/DRIVE-INDEX.json)
            if listed and len(found) + _twin_has(folder, row["files"]) >= need:
                continue        # listed on the Drive twin, by key
            missing.append(f"{row['name']} ({row['why']})")
    prov = folder / "provenance.json"
    if prov.is_file():
        missing += provenance_gaps(prov, drive_refs=bool(brand))
    return missing


def provenance_gaps(prov: Path, drive_refs: bool = False) -> list[str]:
    """EVERY ELEMENT DOCUMENTED, FROM A REAL REFERENCE (the owner, 2026-09-23):
    the record names its real references, each with a file that exists, what
    kind of real thing it is and where it came from, plus rights, how it was
    made and where the full-size files live. `drive_refs` (a product checked
    in a worker spawn): a reference not in the folder counts when its
    `drive_path` reads on the Drive."""
    rules = standard()["provenance_rules"]
    try:
        rec = json.loads(prov.read_text())
    except Exception as e:
        return [f"provenance.json does not read ({e})"]
    gaps = [f"provenance.json has no `{k}`" for k in rules["required"] if not rec.get(k)]
    for r in rec.get("real_references") or []:
        if r.get("removed"):
            # the photo file was deleted on the record of where the person came from stays, and is enough
            continue
        miss = [k for k in rules["real_reference_needs"] if not r.get(k)]
        if miss:
            gaps.append(f"a real reference is missing {', '.join(miss)}")
        elif r["kind"] not in rules["real_kinds"]:
            gaps.append(f"reference {r['file']} is `{r['kind']}` — not a real source ({', '.join(rules['real_kinds'])})")
        elif not (prov.parent / r["file"]).exists():
            if _DRIVE_LIST and not drive_refs:
                gap = _listed_ref_gap(prov.parent, r)
                if gap:
                    gaps.append(gap)
            elif drive_refs:
                gap = _drive_ref_gap(r)
                if gap:
                    gaps.append(gap)
            else:
                gaps.append(f"reference {r['file']} is named but not in the folder")
    return gaps


def _vt_workdir():
    """video-teardown's working-folder module, loaded by file (SI-56)."""
    m = sys.modules.get("vt_workdir")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vt_workdir", COMPONENT.parents[1] / "tools" / "video-teardown" / "machine" / "workdir.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["vt_workdir"] = m
        spec.loader.exec_module(m)
    return m


# the teardown's working runs, runs/video-teardown/_work/ (SI-56)
TEARDOWN_RUNS = _vt_workdir().root(COMPONENT.parents[1])


def resolve_teardown(td) -> Path | None:
    """A teardown run's WORKING folder (where its frames are) from any way it is
    written: absolute, relative to this machine (storyboard.json), relative to
    the workspace, or its repo shelf `runs/video-teardown/<brand>/<slug>`."""
    if not td:
        return None
    td = Path(str(td))
    cands = [td] if td.is_absolute() else [HERE / td, COMPONENT.parents[1] / td]
    cands.append(TEARDOWN_RUNS / td.name)
    for c in cands:
        c = c.resolve()
        if (c / "framemap").is_dir():
            return c
    return None


def teardown_of(brief_path=None, out=None) -> Path | None:
    """Which swipe run a brief was written from: the production run's
    storyboard.json, the brief's writing-shelf slug, or the run's own name."""
    if out:
        try:
            got = resolve_teardown(json.loads((Path(out) / "storyboard.json").read_text()).get("teardown"))
            if got:
                return got
        except (OSError, ValueError):
            pass
    if brief_path:
        parts = Path(brief_path).resolve().parts
        if "video-writing" in parts and len(parts) > parts.index("video-writing") + 2:
            got = resolve_teardown(parts[parts.index("video-writing") + 2])
            if got:
                return got
    if out:
        name = Path(out).resolve().name
        got = resolve_teardown(name)
        if got:
            return got
        hits = [d for d in sorted(TEARDOWN_RUNS.glob(f"*-{name}")) if (d / "framemap").is_dir()] \
            if TEARDOWN_RUNS.is_dir() else []
        if len(hits) == 1:
            return hits[0]
    return None


_EKIND = {"person": "person", "setting": "place", "prop": "prop"}


def _times(text: str) -> list[float]:
    return [int(m) * 60 + float(s) for m, s in re.findall(r"\b(\d{1,2}):(\d{2}(?:\.\d+)?)\b", text or "")]


def match_swipe_element(kind: str, eid: str, ref: str, elements: list[dict]):
    """(element, how) — the swipe element a brief element is made from, or (None, "")."""
    pool = [e for e in elements if e.get("kind") == _EKIND.get(kind)]
    said = (ref or "").lower()
    for e in sorted(pool, key=lambda e: -len(e["name"])):
        if re.search(r"\b" + re.escape(e["name"].lower()) + r"\b", said):
            return e, "named in the brief's real reference"
    for e in pool:
        if slug(e["name"]) == slug(eid):
            return e, "the same name"
    if kind == "prop":
        mine = set(slug(eid).split("-"))
        for e in sorted(pool, key=lambda e: -len(e["name"])):
            if set(slug(e["name"]).split("-")) <= mine:
                return e, "its words are in the prop's name"
    ts = _times(ref)
    if ts:
        hits = [e for e in pool if any(a <= t < b for t in ts for a, b in e.get("times") or [])]
        if len(hits) == 1:
            return hits[0], "the only one on screen at the times named"
    if kind == "setting" and len(pool) == 1:
        return pool[0], "the swipe's only place"
    return None, ""


def swipe_frames(kind: str, eid: str, ref: str, td: Path, ws: Path) -> dict | None:
    """The real frames to make this element from (see the docstring)."""
    idx_p = td / "framemap" / "elements" / "index.json"
    if not idx_p.is_file():
        return None
    elements = []
    for row in json.loads(idx_p.read_text()).get("elements") or []:
        try:
            elements.append(json.loads((td / "framemap" / row["folder"] / "element.json").read_text())
                            | {"folder": row["folder"]})
        except (OSError, ValueError):
            continue
    e, how = match_swipe_element(kind, eid, ref, elements)
    if not e or not e.get("crops"):
        return None
    fm = td / "framemap"

    def rel(p):
        try:
            return str((fm / p).resolve().relative_to(ws.resolve()))
        except ValueError:
            return str((fm / p).resolve())

    def pick(c):
        return {"file": rel(c["file"]), "t": c["t"], "shot": c["shot"]}
    crops = e["crops"]
    at = []
    for t in _times(ref):
        c = min(crops, key=lambda c: abs(c["t"] - t))
        if pick(c) not in at:
            at.append(pick(c))
    per_shot = []
    for k in e.get("shots") or []:
        mine = [c for c in crops if c["shot"] == k]
        if mine:
            per_shot.append(pick(mine[len(mine) // 2]))
    best = e.get("best") or crops[len(crops) // 2]
    try:
        run_rel = str(td.resolve().relative_to(ws.resolve()))
    except ValueError:
        run_rel = str(td.resolve())
    return {"run": run_rel, "element": rel(e["folder"]), "name": e["name"], "kind": e["kind"],
            "matched_by": how, "best": pick(best), "at_times": at, "crops": per_shot,
            "crops_total": len(crops), "frames_total": len(e.get("frames_used") or [])}


def sheet(brief_text: str, brand: str, root: Path | None = None, teardown=None, drive=None) -> dict:
    """The element sheet. `drive` (LD-60 (manifest reads Drive)): count a file the Drive LISTS by key as
    banked; None = only in a worker spawn (DRIVE_MOUNT=off), as the lock always has. The lock and the
    writing manifest both call this, so on any one machine the two cannot disagree."""
    if drive is None:
        drive = _drive_mode()
    if drive and not _DRIVE_LIST:
        _DRIVE_LIST[:] = [brand]
        try:
            return sheet(brief_text, brand, root, teardown, drive=True)
        finally:
            del _DRIVE_LIST[:]
    ws = root or _workspace()
    bh = ws / "brands" / brand
    std = standard()
    doc = _json_block(brief_text)
    scenes = doc.get("scenes") or []
    cast = doc.get("cast") or []
    cast_ids = [c.get("id") or c.get("name") for c in cast if (c.get("id") or c.get("name"))]
    items = []

    # THE BRAND'S STORY PEOPLE (the owner, 2026-09-23: "it should be Yai because
    # our story is about Brand-B's grandma … if the brief ever calls for stuff
    # like that, we use those elements"): a NEW person whose role is one of
    # them is refused — cast the banked person
    story = {}
    af = EP.cast_list(brand, ws) / "authority.json"
    if af.is_file():
        story = {k: v for k, v in (json.loads(af.read_text()).get("_story_roles") or {}).items()
                 if not k.startswith("_")}

    # PEOPLE — who, the bank folder, the looks worn, the voice if they speak
    for c in cast:
        cid = c.get("id") or c.get("name")
        new = (c.get("bank_id") or "").upper() == "NEW"
        bank_id = slug(cid) if new or not c.get("bank_id") else c["bank_id"]
        folder = EP.casting_home(brand, bank_id, ws)
        in_scenes = [s.get("id") for s in scenes if cid in _people_in(s.get("who", ""), cast_ids)]
        speaks = [s.get("id") for s in scenes if (s.get("voice") or "").strip() and
                  (s.get("speaker") or (_people_in(s.get("who", ""), cast_ids)[:1] or [""])[0]) == cid]
        looks_needed = sorted({(s.get("looks") or {}).get(cid) or c.get("look") or ""
                               for s in scenes if s.get("id") in in_scenes})
        # how the brief shows them decides what they need (7 Oct): never on screen
        # and speaking → a voice only; only from behind / as a crowd → a master
        # and a look sheet; everyone else → the full person standard
        shown = ""
        for rec in ("spec.json", "provenance.json"):
            try:
                shown = shown or (json.loads((folder / rec).read_text()).get("shown") or "")
            except Exception:
                pass
        kind = ("person_voice_only" if (not in_scenes and speaks) else
                "person_background" if shown == "background" else "person")
        missing = (["NEW — make from the real reference: " + (c.get("real_reference") or "NONE NAMED (the brief must name one)")]
                   if new and not folder.is_dir() else _check_folder(folder, std[kind]["requires"]))
        if new:
            said = " ".join([cid, c.get("name") or "", c.get("identity_block") or "", c.get("role") or "", c.get("real_reference") or ""]).lower()
            for sid_, words in story.items():
                hit = next((w for w in words if re.search(r"\b" + re.escape(w.lower()) + r"\b", said)), None)
                if hit:
                    missing.insert(0, f"this is the brand's story person `{sid_}` (\"{hit}\") — cast them by bank_id, never a new face")
        looks_file = folder / "looks.json"
        banked_looks = json.loads(looks_file.read_text()).get("looks", {}) if looks_file.exists() else {}
        for lk in looks_needed:
            if not lk:
                missing.append("the brief names no look for them (every person in a scene wears a banked look)")
            elif lk.upper().startswith("NEW"):
                missing.append(f"a new look to make — {lk.split(':',1)[-1].strip()}")
            elif lk not in banked_looks:
                missing.append(f"look `{lk}` is not in looks.json")
        vfile = folder / "voice.json"
        voice = json.loads(vfile.read_text()) if vfile.exists() else {}
        asked = (c.get("voice") or {})
        if speaks and not voice.get("voice_id"):
            persona = asked.get("persona") or asked.get("new") or ""
            missing.append("a voice of their own (they speak in " + ", ".join(speaks) + ")"
                           + (f" — make from: {persona}" if persona else ""))
        items.append({"kind": "person", "id": cid, "bank_id": bank_id,
                      "folder": str(folder.relative_to(ws)), "scenes": in_scenes,
                      "speaks": speaks, "looks": looks_needed,
                      "voice_id": voice.get("voice_id"),
                      "describe": c.get("identity_block", ""),
                      "status": "to make" if missing else "banked", "missing": _dedupe(missing)})

    # SETTINGS — one set per place a scene happens in
    world = {w.get("id"): w for w in (doc.get("world") or []) if w.get("id")}
    used = {}
    for s in scenes:
        sid = s.get("setting_id") or s.get("setting")
        if sid:
            used.setdefault(sid, []).append(s.get("id"))
    for sid, in_scenes in used.items():
        w = world.get(sid, {})
        if re.match(r"(?i)^\s*real\b", str(w.get("bank_id") or "")):
            # REAL FOOTAGE WE OWN (2026-10-23): a place the brief marks `real footage` is never generated — its shots
            # are cut from the brand's own clips (the footage gate, footage.py); nothing to bank here
            items.append({"kind": "setting", "id": sid, "bank_id": "real-footage", "folder": "", "scenes": in_scenes,
                          "describe": w.get("description", ""), "status": "banked", "missing": [],
                          "real_footage": True})
            continue
        new = (w.get("bank_id") or "").upper() == "NEW"
        bank_id = slug(sid) if new or not w.get("bank_id") else w["bank_id"]
        folder = EP.elements_home(brand, "sets", bank_id, ws)
        missing = (["NEW — make from the real reference: " + (w.get("real_reference") or "NONE NAMED (the brief must name one)")]
                   if new and not folder.is_dir() else _check_folder(folder, std["setting"]["requires"]))
        if sid not in world:
            missing.append("the brief's THE WORLD section never describes it")
        items.append({"kind": "setting", "id": sid, "bank_id": bank_id,
                      "folder": str(folder.relative_to(ws)), "scenes": in_scenes,
                      "describe": w.get("description", ""),
                      "status": "to make" if missing else "banked", "missing": _dedupe(missing)})

    # PRODUCT — the real packshot, never drawn from words
    prod_scenes = [s.get("id") for s in scenes if s.get("product")]
    lock = doc.get("product_lock") or []
    if prod_scenes or lock:
        pid = (doc.get("piece") or {}).get("product") or doc.get("product_id") or ""
        folder = EP.product_home(brand, pid, ws) if pid else None
        missing = []
        if not pid:
            missing.append("the brief names no product id (piece.product) — the packshot cannot be found")
        else:
            missing = _check_folder(folder, std["product"]["requires"])
            kit = None if folder.is_dir() else EP.product_kit(brand, pid, ws)
            if kit is not None:   # the brand keeps the product as a flat file: check its truth kit
                folder, missing = kit, _check_folder(kit, std["product_kit"]["requires"])
        items.append({"kind": "product", "id": pid or "?", "bank_id": pid,
                      "folder": str(folder.relative_to(ws)) if folder else "",
                      "scenes": prod_scenes or [l.split(" ")[0] for l in lock],
                      "describe": lock[0] if lock else "",
                      "status": "to make" if missing else "banked", "missing": missing})

    # PROPS — anything a hand holds that is not the product
    props = {}
    for s in scenes:
        for p in s.get("props") or []:
            props.setdefault(p, []).append(s.get("id"))
    for p, in_scenes in props.items():
        folder = EP.elements_home(brand, "props", slug(p), ws)
        missing = _check_folder(folder, std["prop"]["requires"])
        items.append({"kind": "prop", "id": p, "bank_id": slug(p),
                      "folder": str(folder.relative_to(ws)), "scenes": in_scenes,
                      "status": "to make" if missing else "banked", "missing": missing})

    # THE BRIEF ITSELF — the fields the standard says a brief must carry
    brief_gaps = []
    for s in scenes:
        if s.get("kind") in ("talking", "broll", None) and not (s.get("setting_id") or s.get("setting")):
            if s.get("kind") != "card":
                brief_gaps.append(f"{s.get('id')}: no setting_id")
        # A SILENT SCENE SAYS SO (2026-10-09): the contract will not take an empty `voice`, so a wordless
        # scene writes "none" (or "None. Heard: …" — what is heard, no words). That is not a line; no speaker.
        _v = (s.get("voice") or "").strip()
        if _v and not re.match(r"(?i)^none\b", _v) and std["brief"].get("speaker_required"):
            if not s.get("speaker"):
                brief_gaps.append(f"{s.get('id')}: has words but names no `speaker`")
            elif s["speaker"] not in cast_ids:
                brief_gaps.append(f"{s.get('id')}: speaker `{s['speaker']}` is not in the cast")
        if s.get("to_camera") and not (s.get("motion") or {}).get("reference") and std["brief"].get("motion_reference_required"):
            brief_gaps.append(f"{s.get('id')}: no motion reference")
    # THE REAL FRAMES each element still to make is made from (2026-10-08)
    td = resolve_teardown(teardown) if teardown else None
    if td:
        refs = {("person", c.get("id") or c.get("name")): c.get("real_reference") or "" for c in cast}
        refs.update({("setting", w.get("id")): w.get("real_reference") or "" for w in doc.get("world") or []})
        for i in items:
            if i["status"] == "to make" and i["kind"] in _EKIND:
                sf = swipe_frames(i["kind"], i["id"], refs.get((i["kind"], i["id"]), ""), td, ws)
                if sf:
                    i["swipe_frames"] = sf
    body = {"brand": brand, "title": (doc.get("piece") or {}).get("title", ""),
            "items": items, "brief_gaps": brief_gaps}
    # THE SWIPE'S STYLE rides on the sheet (2026-10-09): make_character / make_set
    # made from this sheet put it at the top of every prompt instead of photoreal.
    sid = (doc.get("piece") or {}).get("style_id")
    if sid and not str(sid).startswith("⟨"):
        body["style_id"] = sid
    if td:
        try:
            body["teardown"] = str(td.resolve().relative_to(ws.resolve()))
        except ValueError:
            body["teardown"] = str(td)
    body["fingerprint"] = fingerprint(body)
    body["to_make"] = [i for i in items if i["status"] == "to make"]
    return body


def _dedupe(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def fingerprint(body: dict) -> str:
    """What was confirmed: every element's id, bank folder, looks and voice —
    and the bytes of every file in each bank folder, so a swapped picture
    or voice breaks the lock too."""
    ws = _workspace()
    h = hashlib.sha256()
    for i in sorted(body["items"], key=lambda x: (x["kind"], x["id"])):
        h.update(json.dumps({k: i.get(k) for k in ("kind", "id", "bank_id", "looks", "voice_id")},
                            sort_keys=True).encode())
        folder = ws / i.get("folder", "") if i.get("folder") else None
        if folder and folder.is_dir():
            for p in sorted(folder.rglob("*")):
                # upload caches (*.gemini-uri.json) are written by the picture
                # judges themselves; they are not the element, so a QC pass
                # never breaks the lock it is checking (2026-10-02)
                if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".gemini-uri.json"):
                    h.update(p.name.encode())
                    h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


def gate(run: Path, brief_text: str, brand: str, dry_run: bool,
         brief_dir=None) -> tuple[list[str], list[str]]:
    """(refusals, notes). Writes `<run>/elements.json` either way. In a worker
    spawn (DRIVE_MOUNT=off) only: the element folders are fetched from the
    Drive first, the product counts its Drive packshot, and a confirm in
    `brief_dir` for this exact set is carried into the run."""
    drive = _drive_mode()
    td = teardown_of(out=run)
    _TWINS.clear(); del _NO_DRIVE[:]       # one Drive listing per gate, shared by the fetch and the sheet
    fetched = fetch_from_drive(sheet(brief_text, brand, teardown=td, drive=False), _workspace()) if drive else []
    if drive:
        _DRIVE_BRAND[:] = [brand]
    try:
        body = sheet(brief_text, brand, teardown=td, drive=drive)
    finally:
        del _DRIVE_BRAND[:]
    (run / "elements.json").write_text(json.dumps(body, indent=1))
    _note_made_here(run, body)
    fails, notes = [], list(fetched)
    for i in body["to_make"]:
        fails.append(f"{i['kind']} {i['id']} is not banked — make: " + "; ".join(i["missing"]))
    for g in body["brief_gaps"]:
        fails.append(f"brief: {g}")
    if not fails:
        lock = run / "elements-lock.json"
        held = json.loads(lock.read_text()) if lock.exists() else {}
        if drive and not held and brief_dir is not None:
            held = _carry_lock(run, Path(brief_dir), body["fingerprint"]) or held
            if held:
                notes.append(f"the confirm carried from {held['carried_from']}/elements-lock.json")
        if held.get("fingerprint") != body["fingerprint"] and not dry_run \
                and os.environ.get("VP_REUSED_AUTO", "1") != "0":
            # NO PERSONAL SIGN-OFF : every element banked and every check green locks
            # itself, whether the element was banked before this run or made in it. The banking checks above are unchanged.
            # REUSED ELEMENTS APPROVE THEMSELVES (the owner, 2026-10-19: "if we're reusing elements or reusing
            # avatars … those should be automatically approved. There's no reason to reapprove these
            # things"). Every element was already in the bank when this run first looked, so the lock is
            # written by the machine and said so. An element made new in THIS run still waits for the
            # cast approval (batch_approve.py cast), and so does one another run banked but nobody has
            # confirmed yet: "reused" means confirmed in an earlier run (review, 19 Oct). Off: VP_REUSED_AUTO=0.
            held = confirm(run, "auto: every element is banked and every check is green (no personal sign-off, 2026-10-27)")
            notes.append("elements: every one banked — locked automatically")
        if held.get("fingerprint") != body["fingerprint"]:
            fails.append("the elements are banked but not confirmed" +
                         (" (they changed since the last confirm)" if held else "") +
                         f" — show the elements page, then: elements_check.py confirm {run}")
    if dry_run:
        notes += [f"(dry run) {f}" for f in fails]
        return [], notes
    return fails, notes


def _note_made_here(run: Path, body: dict) -> None:
    """Every element this run had to MAKE (not yet banked when it looked) — kept for the run's life in
    elements-new.json, so it is never mistaken for a reused one once it is banked."""
    f = run / "elements-new.json"
    seen = set(json.loads(f.read_text())) if f.exists() else set()
    now = seen | {f"{i['kind']} {i['id']}" for i in body.get("to_make") or []}
    if now != seen or not f.exists():
        f.write_text(json.dumps(sorted(now), indent=1))


def _confirmed_before(run: Path) -> set:
    """Every element folder a person (or an earlier reuse) confirmed in ANOTHER production run's lock."""
    out = set()
    root = _workspace() / "runs" / "video-production"
    for lock in root.glob("*/*/elements-lock.json"):
        if lock.parent.resolve() == Path(run).resolve():
            continue
        try:
            items = json.loads(lock.read_text()).get("items") or []
        except (OSError, ValueError):
            continue
        out |= {str(x).split(" → ", 1)[1] for x in items if " → " in str(x)}
    return out


def _made_here(run: Path) -> list:
    f = run / "elements-new.json"
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return ["(no record of what was banked when this run started)"]


def confirm(run: Path, by: str) -> dict:
    body = json.loads((run / "elements.json").read_text())
    if body.get("to_make"):
        raise SystemExit("cannot confirm — still to make: " +
                         ", ".join(f"{i['kind']} {i['id']}" for i in body["to_make"]))
    fresh = fingerprint(body)
    lock = {"fingerprint": fresh, "by": by, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "items": [f"{i['kind']} {i['id']} → {i['folder']}" for i in body["items"]]}
    (run / "elements-lock.json").write_text(json.dumps(lock, indent=1))
    return lock


def bind(brief: Path, pairs: dict) -> dict:
    """The make step's last act: every element the brief wrote as NEW that has
    now been made and banked is pointed at its bank folder, in the brief's
    own block. `pairs` maps a cast or world id to its bank id. The brief before
    binding is kept beside it (`<name>-before-bind.md`)."""
    text = brief.read_text()
    m = list(re.finditer(r"```json\s*\n(.*?)\n```", text, re.S))
    if not m:
        raise SystemExit("no json block in the brief")
    blk = m[-1]
    doc = json.loads(blk.group(1))
    done = {}
    # "CAST ID.look=look-id": every NEW look that person wears becomes the banked one
    for k, v in list(pairs.items()):
        if k.endswith(".look"):
            cid = k[:-5]; n = 0
            for s in doc.get("scenes") or []:
                lk = (s.get("looks") or {}).get(cid)
                if lk and lk.upper().startswith("NEW"):
                    s["looks"][cid] = v; n += 1
            done[k] = (f"NEW ×{n}", v); pairs.pop(k)
    for key in ("cast", "world"):
        for row in doc.get(key) or []:
            rid = row.get("id")
            if rid in pairs:
                done[rid] = (row.get("bank_id"), pairs[rid]); row["bank_id"] = pairs[rid]
    missing = [k for k in pairs if k not in done]
    if missing:
        raise SystemExit("not in the brief: " + ", ".join(missing))
    keep = brief.with_name(brief.stem + "-before-bind.md")
    if not keep.exists():
        keep.write_text(text)
    brief.write_text(text[:blk.start(1)] + json.dumps(doc, indent=1, ensure_ascii=False) + text[blk.end(1):])
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet"); s.add_argument("brief"); s.add_argument("--brand", required=True)
    s.add_argument("--out")
    s.add_argument("--teardown", help="the swipe's teardown run (default: found from the run / the brief)")
    c = sub.add_parser("confirm"); c.add_argument("run"); c.add_argument("--by", required=True)
    t = sub.add_parser("status"); t.add_argument("run")
    b = sub.add_parser("bind"); b.add_argument("brief"); b.add_argument("pairs", nargs="+", help="ID=bank_id")
    a = ap.parse_args(argv)
    if a.cmd == "sheet":
        td = a.teardown or teardown_of(a.brief, a.out)
        body = sheet(Path(a.brief).read_text(), a.brand, teardown=td)
        if a.out:
            Path(a.out).mkdir(parents=True, exist_ok=True)
            (Path(a.out) / "elements.json").write_text(json.dumps(body, indent=1))
        for i in body["items"]:
            print(f"{i['status']:8}  {i['kind']:8} {i['id']}" +
                  ("" if i["status"] == "banked" else "  — " + "; ".join(i["missing"])))
            if i.get("swipe_frames"):
                sf = i["swipe_frames"]
                print(f"          swipe frames: {sf['name']} ({sf['matched_by']}) · best {sf['best']['file']}"
                      f" · {sf['crops_total']} crops · {sf['element']}")
        for g in body["brief_gaps"]:
            print(f"brief     {g}")
        return 1 if body["to_make"] or body["brief_gaps"] else 0
    if a.cmd == "bind":
        done = bind(Path(a.brief), dict(x.split("=", 1) for x in a.pairs))
        for k, (was, now) in done.items():
            print(f"{k}: {was} → {now}")
        return 0
    if a.cmd == "confirm":
        print(json.dumps(confirm(Path(a.run), a.by), indent=1))
        return 0
    body = json.loads((Path(a.run) / "elements.json").read_text())
    lock = Path(a.run) / "elements-lock.json"
    print(f"{len(body['items'])} elements, {len(body['to_make'])} to make, "
          f"confirmed: {'yes' if lock.exists() else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
