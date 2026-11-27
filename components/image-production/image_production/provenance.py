"""Made by the tool: the fingerprint of every picture image production delivers (2026-11-11).

Every picture this tool delivers is fingerprinted (sha256 of its bytes) the moment it lands:

    the engine (make.py, IP.make)        run.json  pictures[].sha256, and the ledger
    plain.make (board, teardown, pair)   <stem>.recipe.json  sha256, and the ledger
    the tool's words (words.set_on_top,  the ledger, ONLY when the plate under the words is itself
      design_type.render), to_frame       a picture this tool made: the tool's words over a frame grab
                                          are still a frame grab

The ledger is one append-only line per picture at ~/.image-production/made.jsonl (IMAGE_MADE_LEDGER moves it).

The Meta approval filer (components/meta-upload/to_check.py) and the approval page's card checks read `known()`:
a thumbnail or an image/carousel picture whose bytes are in no record is refused. A frame grab, a type layer added
outside the tool, a hand composite or split, a picture from any other door, or one byte changed by hand after the
tool delivered it: none has a record. The fix is always the same: make the picture with make.py.

ROLLBACK: models.json `gate.made_by_tool` (`on`, or one lane under `lanes`), or MADE_BY_TOOL_GATE_OFF=all or a
comma list of lanes in the environment. Row in the team's team/rollbacks.md.

Stdlib only, no package imports: meta-upload loads this file by path.
"""
import hashlib
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = HERE.parent / "models.json"
SAY = ("not made by the image production tool: its bytes are in no image-production run record. Covers and "
       "pictures are made start to finish with components/image-production/make.py (from the filed 3D set, the "
       "product from its 3D kit, the words from the tool) and filed as delivered. A frame grab, words typed on "
       "afterwards, a hand composite or split, or any edit after delivery is refused. Make it with make.py, "
       "then file the file it delivered")


def ledger_path():
    """The machine's one ledger. A workspace pointed at a throwaway folder (every test) keeps its own, so a test run
    never adds its stand-in pictures to the machine's record."""
    if os.environ.get("IMAGE_MADE_LEDGER"):
        return Path(os.environ["IMAGE_MADE_LEDGER"])
    ws = os.environ.get("AI_WORKSPACE")
    if ws:
        import tempfile
        tmp = Path(tempfile.gettempdir()).resolve()
        w = Path(ws).resolve()
        if w == tmp or tmp in w.parents:
            return w / ".image-production" / "made.jsonl"
    return Path.home() / ".image-production" / "made.jsonl"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stamp(path, route, base=None, **extra):
    """Record one delivered picture in the ledger. Returns its sha256. Never stops a delivery."""
    path = Path(path)
    digest = sha256(path)
    row = {"sha256": digest, "file": str(path), "route": route, "made": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if base:
        row["from"] = base
    row.update({k: v for k, v in extra.items() if v is not None})
    try:
        led = ledger_path()
        led.parent.mkdir(parents=True, exist_ok=True)
        with open(led, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as e:                                   # the sidecar record still carries the fingerprint
        print(f"  SKIP the made-by-tool ledger — {e}")
    return digest


def hand_off(path, brief, step, job, record=None):
    """A picture a maker made from a brief's hand-off steps and saved with briefs make.py: it is made through the
    process (its steps, its 3D print, the generation's own record), so it gets the same record as the tool's pictures:
    <file>.made.json beside it (travels with the file to the Drive) and a ledger line. Returns the sidecar."""
    path = Path(path)
    digest = stamp(path, "hand-off", brief=brief, step=step, job=job, record=record)
    side = path.parent / (path.name + ".made.json")
    side.write_text(json.dumps({"machine": "image-production", "route": "hand-off", "sha256": digest, "brief": brief,
                                "step": step, "job": job, "record": record}, indent=1) + "\n")
    return side


def set_print(path, brand=None, set_name=None, **extra):
    """A kept print of a filed 3D set (picture_sets.py put, note "kept ..."). Under RULE GATE-4 the print IS the
    picture: it was made through the process (the set at true sizes, printed with the product's casting sheet), so it
    gets the tool's record like any picture the tool delivers, and what the tool lays on it (the real product pasted,
    the words) derives from it. Before this (2026-11-24) every set-route picture was refused at the approval page."""
    return stamp(path, "set-print", brand=brand, set=set_name, **extra)


def derive_from(out, bases, route, **extra):
    """`derive` from the source picture files themselves: `out` is stamped only when every one of `bases` (a path or a
    list of paths, e.g. the four photos of a laid-out slide) was made by this tool. Returns the new sha256 or None."""
    bases = [bases] if isinstance(bases, (str, Path)) else list(bases or [])
    shas = [sha256(b) for b in bases if Path(b).is_file()]
    if not shas or len(shas) != len(bases) or not all(_in_ledger(s) for s in shas) or not Path(out).is_file():
        return None
    return stamp(out, route, base=shas[0], bases=shas if len(shas) > 1 else None, **extra)


def derive(out, base_sha, route, **extra):
    """Stamp `out` (the tool's words, a resize) only when the picture under it was made by this tool.
    Returns the new sha256, or None when the base has no record (then `out` is not tool-made)."""
    if not base_sha or not Path(out).is_file() or not _in_ledger(base_sha):
        return None
    return stamp(out, route, base=base_sha, **extra)


_CACHE = {"key": None, "set": set()}


def _ledger_set():
    led = ledger_path()
    try:
        st = led.stat()
    except OSError:
        return set()
    key = (str(led), st.st_mtime_ns, st.st_size)
    if _CACHE["key"] != key:
        got = set()
        for line in led.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                got.add(json.loads(line)["sha256"])
            except (ValueError, KeyError, TypeError):
                continue
        _CACHE.update(key=key, set=got)
    return _CACHE["set"]


def _in_ledger(digest):
    return digest in _ledger_set()


def _sidecars(path):
    """Run records that may sit beside a picture copied out of its run folder with them."""
    p = Path(path)
    for d in (p.parent, p.parent.parent):
        yield d / "run.json"
    yield p.with_suffix(".recipe.json")
    yield p.parent / (p.name + ".made.json")       # saved through a brief's hand-off (briefs make.py save)


def _in_sidecar(path, digest):
    for f in _sidecars(path):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rec.get("machine") == "image-production" and any(
                isinstance(x, dict) and x.get("sha256") == digest for x in rec.get("pictures") or []):
            return str(f)
        if f.name.endswith((".recipe.json", ".made.json")) and rec.get("sha256") == digest:
            return str(f)
    return None


def known(path, digest=None):
    """Where the record of this picture is (the ledger or a run record), or None when it was not made by the tool."""
    digest = digest or sha256(path)
    if _in_ledger(digest):
        return str(ledger_path())
    return _in_sidecar(path, digest)


def switch():
    try:
        return (json.loads(MODELS.read_text()).get("gate") or {}).get("made_by_tool") or {}
    except (OSError, ValueError):
        return {}


def on(lane):
    """Is the gate on for this approval-page lane (video = its thumbnails, image, carousel, creator)?"""
    off = {x.strip() for x in os.environ.get("MADE_BY_TOOL_GATE_OFF", "").split(",") if x.strip()}
    if off & {"all", lane}:
        return False
    cfg = switch()
    if not cfg:
        return True                                        # no switch found: the rule holds
    return bool(cfg.get("on")) and (cfg.get("lanes") or {}).get(lane, True) is not False


def since():
    """Cards filed before this moment are left as they were filed (the check is not added to them)."""
    return switch().get("since") or ""


def refusals(paths):
    """[(path, why)] for every picture in `paths` with no record."""
    bad = []
    for p in paths:
        p = Path(p)
        if not p.is_file():
            continue
        if not known(p):
            bad.append((p, f"{p.name}: {SAY}."))
    return bad


SLACK = 120                                                # seconds between a picture landing and its record being written


def backfill(root):
    """Fingerprint pictures this tool made before fingerprints existed (2026-11-11): an engine run.json's pictures and a
    plain picture's .recipe.json, each only when the picture was not touched after the tool wrote its record (a file
    changed later, by words typed on or any hand edit, stays unrecorded). Returns [(path, sha256 or why-not)]."""
    root = Path(root)
    found = []
    recs = [root] if root.is_file() else sorted(root.rglob("run.json")) + sorted(root.rglob("*.recipe.json"))
    for rec in recs:
        try:
            data = json.loads(rec.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rec.name == "run.json":
            if data.get("machine") != "image-production":
                continue
            pics = [rec.parent / Path(x.get("file") or x.get("name") or "").name for x in data.get("pictures") or []
                    if isinstance(x, dict)]
        else:
            if "prompt" not in data or "made_by" not in data:
                continue
            stem = rec.name[: -len(".recipe.json")]
            pics = [p for p in rec.parent.glob(stem + ".*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
        for p in pics:
            if not p.is_file():
                continue
            if p.stat().st_mtime > rec.stat().st_mtime + SLACK:
                found.append((p, "changed after the tool recorded it: not recorded"))
                continue
            digest = sha256(p)
            if not _in_ledger(digest):
                stamp(p, "backfill", record=str(rec))
            found.append((p, digest))
    return found


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "backfill":
        for p, s in backfill(sys.argv[2]):
            print(f"{s[:12] if len(s) == 64 else s:<14} {p}")
    elif len(sys.argv) >= 3 and sys.argv[1] == "known":
        for f in sys.argv[2:]:
            print(f"{'MADE BY THE TOOL' if known(f) else 'NOT MADE BY THE TOOL':<22} {f}")
    else:
        print("provenance.py backfill <run folder or run.json> | known <picture> ...")
