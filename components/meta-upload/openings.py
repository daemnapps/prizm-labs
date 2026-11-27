#!/usr/bin/env python3
"""openings: which opening each asset of a flexible video ad carries.

A brief is one flexible ad: the control and every hook version ride in one card as asset-01, asset-02 ... The short
ad name can't say which opening an asset is, so the card lists it (card.json `openings`, one row per asset, in the
card's media order) and the filer writes the same rows onto the brief's record (components/naming/concept.py), so a
result on one asset can be read back to the opening that earned it.

Where a row's label comes from, the first that answers, asset by asset (`from` says which):
  caller        the caller's own label for it (`given`, in media order: a line, or {"version", "opening", "text"})
  edit record   the edit's own record beside the render: <run>/renders/control.mp4 is the control, and
                <run>/edit-map-<version>.json names the hook that version was cut for (`hook`)
  file name     `control` when the file says so, else the version its name gives; the opening is then not known,
                except a card with one master only, which is the control
The opening's words come from the brief's own list of openings when the label matches one of them.
Nothing is guessed: an asset whose opening can't be read carries `opening` null.
"""
import json, re
from pathlib import Path

ASSET = re.compile(r"_(asset-\d+)\.[A-Za-z0-9]+$")


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _edit_record(media):
    """(version, hook label or None, True when the edit's record was read) for one render."""
    m = Path(media)
    version = m.stem
    if m.parent.name != "renders":
        return version, None, False
    run = m.parent.parent
    if version == "control":
        return version, None, (run / "edit-map.json").is_file()
    f = run / f"edit-map-{version}.json"
    try:
        hook = json.loads(f.read_text()).get("hook")
    except (OSError, ValueError, AttributeError):
        return version, None, False
    return version, (str(hook) if hook else None), True


def _control_of(brief_openings):
    """The brief's control opening: the one whose take is the control, else the first."""
    rows = [o for o in brief_openings or [] if isinstance(o, dict)]
    return next((o for o in rows if str(o.get("take") or "").lower() == "control"),
                next((o for o in rows if "control" in _norm(o.get("id"))), rows[0] if rows else None))


def _match(label, brief_openings):
    """The brief opening a label names: the same words, else the same opening number."""
    rows = [o for o in brief_openings or [] if isinstance(o, dict) and o.get("id")]
    want = _norm(label)
    if not want:
        return None
    hit = next((o for o in rows if _norm(o["id"]) == want), None)
    if hit:
        return hit
    n = re.match(r"opening (\d+)\b", want)
    if n:
        same = [o for o in rows if re.match(r"opening %s\b" % n.group(1), _norm(o["id"]))]
        if len(same) == 1:
            return same[0]
    return None


def labels(media, names, given=None, brief_openings=None):
    """One row per asset, in the card's media order:
    {"asset": "asset-01", "file": <name on the card>, "version", "opening", "text", "from"}."""
    out = []
    for i, (src, name) in enumerate(zip(media or [], names or [])):
        m = ASSET.search(str(name))
        row = {"asset": m.group(1) if m else "asset-%02d" % (i + 1), "file": str(name), "version": None,
               "opening": None, "text": None, "from": "file name"}
        version, hook, read = _edit_record(src)
        row["version"] = version
        g = given[i] if given and i < len(given) else None
        if isinstance(g, str) and g.strip():
            g = {"opening": g.strip()}
        if isinstance(g, dict) and (g.get("opening") or g.get("version")):
            row.update({k: g[k] for k in ("version", "opening", "text") if g.get(k)})
            row["from"] = "caller"
        elif read:
            row["from"] = "edit record"
            if hook:
                row["opening"] = hook
        is_control = _norm(row["version"]) == "control" or (i == 0 and not row["opening"] and row["from"] != "caller"
                                                             and len(media) == 1)
        if not row["opening"] and is_control:
            c = _control_of(brief_openings)
            if c:
                row["opening"], row["text"] = c.get("id"), c.get("text")
        if row["opening"] and not row["text"]:
            hit = _match(row["opening"], brief_openings)
            if hit:
                row["text"] = hit.get("text")
        out.append(row)
    return out
