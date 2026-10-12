#!/usr/bin/env python3
"""The element library — every format, structure, framework, style, delivery
value, template and doctrine term in the system, in one shape, and the one
place a tool asks "is this a real one?".

    python3 elements.py build                     # read every source, write library/
    python3 elements.py list                      # what's in it, per element
    python3 elements.py get format video song-ad  # one row, or refused
    python3 elements.py check format:video=song-ad style:image=candid-ugc

    import elements as E
    E.get("format", "video", "song-ad")           # the row, or raises Unknown
    E.check({("format", "video"): "song-ad"})     # [] or a list of problems

the owner, 2026-09-20: *"If we have these different formats, structures,
frameworks, styles, we need to define all these unique elements… Things
aren't enforced… Everything needs to be green light."*

WHAT IT DOES NOT DO: it never edits a source list. Every list stays where the
tool that uses it reads it (sources.json says where). A list is changed at its
source; `build` refreshes the library. Rows the owner has named that no list holds
yet live in additions.json, as drafts.

THE SAME FIELDS ON EVERY ROW: id · name · what · why_it_works · status ·
signed · examples · evidence · source · extra · aliases · note.

ALIASES (2026-09-28, Master Plan v2 3.1). An id is lowercase with "-" between
words, never squashed (`sticky-note`, not `stickynote`). Old spellings live on
as `aliases` on their row, so `get()` and `check()` resolve them; they are
never a second row. the owner's rulings over a source list — a rename, an alias,
a dropped id, a status — live in decisions.json and are applied at build; the
source list itself is not touched.
"""
import glob as _glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                          # components/elements
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
LIBRARY = ROOT / "library"
FIELDS = ("id", "name", "what", "why_it_works", "status", "signed", "examples", "evidence")
APPROVED = {"approved", "proven"}
ID_RULE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")           # lowercase, "-" between words
RULING_FIELDS = ("name", "what", "why_it_works", "status", "signed", "examples", "evidence", "note")


class Unknown(KeyError):
    """A value that is not on its list. Refused, never guessed."""


# ------------------------------------------------------------------ build

def _dig(d, dotted):
    for part in dotted.split("."):
        d = d[part]
    return d


def _rows_of(block):
    """A list of rows, or a {key: row} map turned into rows carrying @key."""
    if isinstance(block, dict):
        return [dict(v, **{"@key": k}) for k, v in block.items() if isinstance(v, dict)]
    return list(block)


def _shape(raw, src, asset, source_label):
    idf = src.get("id", "id")
    rid = raw.get(idf) if not idf.startswith("@") else raw.get(idf)
    row = {"id": rid}
    for f in FIELDS[1:]:
        key = (src.get("fields") or {}).get(f, f)
        v = raw.get(key)
        if isinstance(v, (list, dict)) and f in ("what", "evidence", "examples"):
            v = json.dumps(v, ensure_ascii=False)[:600]
        row[f] = v
    status = (row.get("status") or "draft")
    row["status"] = status
    row["approved"] = status in APPROVED
    row["source"] = source_label
    row["extra"] = {k: raw[k] for k in (src.get("extra") or []) if k in raw}
    row["aliases"] = _aliases(raw.get("aliases"))
    row["note"] = raw.get("note")
    return row


def _aliases(v):
    if not v:
        return []
    return [str(a) for a in ([v] if isinstance(v, str) else v)]


def _decide(key, entry, decisions):
    """Apply the owner's rulings for one list (decisions.json): renames, aliases,
    dropped ids, status rulings. The source list is never touched."""
    d = decisions.get(key) or {}
    unresolved = []
    by_id = {r["id"]: r for r in entry["rows"]}
    for old, new in (d.get("renames") or {}).items():
        r = by_id.get(old)
        if r is None:
            if new not in by_id:
                unresolved.append(f"rename {old} -> {new}: neither id is on the list")
            continue
        r["id"] = new
        if old not in r["aliases"]:
            r["aliases"].append(old)
    by_id = {r["id"]: r for r in entry["rows"]}
    for alias, target in (d.get("aliases") or {}).items():
        r = by_id.get(target)
        if r is None:
            unresolved.append(f"alias {alias} -> {target}: no such row")
        elif alias not in r["aliases"] and alias != r["id"]:
            r["aliases"].append(alias)
    for id_, ruling in (d.get("rulings") or {}).items():
        r = by_id.get(id_)
        if r is None:
            unresolved.append(f"ruling on {id_}: no such row")
            continue
        for f in RULING_FIELDS:
            if f in ruling:
                r[f] = ruling[f]
        if "aliases" in ruling:
            r["aliases"] += [a for a in _aliases(ruling["aliases"]) if a not in r["aliases"]]
        r["approved"] = (r.get("status") or "draft") in APPROVED
    entry["dropped"] = dict(d.get("dropped") or {})
    if d:
        entry["decisions"] = "components/elements/decisions.json"
    return unresolved


def build():
    spec = json.loads((ROOT / "sources.json").read_text())
    shipped = _shipped()
    lists = {}
    for src in spec["sources"]:
        el = src["element"]
        units = []                                          # (asset, rows, label)
        missing = ("path" in src and not (REPO / src["path"]).is_file()) or \
                  ("glob" in src and not _glob.glob(str(REPO / src["glob"])))
        if missing:
            # A source list this checkout does not carry (a tool that is not
            # public): its rows are the ones last built from it, as shipped.
            label = src.get("path") or src.get("glob")
            for (e, asset), entry in sorted(shipped.items()):
                if e == el and str(entry.get("source") or "").startswith(label):
                    key = f"{el}/{asset}"
                    lists[key] = {k: entry.get(k) for k in ("element", "asset", "source", "enforced_by", "note")}
                    lists[key]["rows"] = [dict(r, aliases=_aliases(r.get("aliases"))) for r in entry["rows"]
                                          if r.get("source") != "components/elements/additions.json"]
            continue
        if "inline" in src:
            units.append((src["asset"], src["inline"], "components/elements/sources.json (inline)"))
        elif "glob" in src:
            rows = []
            for f in sorted(_glob.glob(str(REPO / src["glob"]))):
                d = json.loads(Path(f).read_text())
                d["@stem"] = Path(f).stem
                rows.append(d)
            units.append((src["asset"], rows, src["glob"]))
        else:
            data = json.loads((REPO / src["path"]).read_text())
            if "groups" in src:
                g = src["groups"]
                for grp in _dig(data, g["path"]):
                    units.append((grp[g["id"]], _rows_of(grp[g["rows"]]), f'{src["path"]} › {grp[g["id"]]}'))
            else:
                units.append((src["asset"], _rows_of(_dig(data, src["rows"])), src["path"]))
        for asset, rows, label in units:
            key = f"{el}/{asset}"
            entry = lists.setdefault(key, {"element": el, "asset": asset, "source": label,
                                           "enforced_by": src.get("enforced_by"),
                                           "note": src.get("note"), "rows": []})
            for raw in rows:
                entry["rows"].append(_shape(raw, src, asset, label))
    # rows the owner has named that no source holds yet
    for add in json.loads((ROOT / "additions.json").read_text())["rows"]:
        key = f'{add["element"]}/{add["asset"]}'
        entry = lists.setdefault(key, {"element": add["element"], "asset": add["asset"],
                                       "source": "components/elements/additions.json",
                                       "enforced_by": None, "note": None, "rows": []})
        if any(r["id"] == add["id"] for r in entry["rows"]):
            continue                                        # the source has it now
        row = {f: add.get(f) for f in FIELDS}
        row["status"] = row.get("status") or "draft"
        row["approved"] = row["status"] in APPROVED
        row["source"] = "components/elements/additions.json"
        row["extra"] = {}
        row["aliases"] = _aliases(add.get("aliases"))
        row["note"] = add.get("note")
        entry["rows"].append(row)
    # the owner's rulings over the source lists — applied here, never written back
    dfile = ROOT / "decisions.json"
    decisions = (json.loads(dfile.read_text()).get("lists") or {}) if dfile.is_file() else {}
    LIBRARY.mkdir(exist_ok=True)
    index = {"built_from": "components/elements/sources.json + additions.json + decisions.json", "lists": []}
    for key, entry in sorted(lists.items()):
        unresolved = _decide(key, entry, decisions)
        ids = [r["id"] for r in entry["rows"]]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        taken = set(ids)
        for r in entry["rows"]:                             # an alias is never also an id
            r["aliases"] = [a for a in r["aliases"] if a not in taken]
        off_rule = [i for i in ids if not ID_RULE.match(str(i or ""))]
        entry["duplicates"] = dupes
        entry["off_rule"] = off_rule
        entry["unresolved"] = unresolved
        fname = key.replace("/", ".") + ".json"
        (LIBRARY / fname).write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n")
        index["lists"].append({
            "element": entry["element"], "asset": entry["asset"], "file": f"library/{fname}",
            "source": entry["source"], "enforced_by": entry["enforced_by"], "note": entry["note"],
            "rows": len(entry["rows"]), "approved": sum(1 for r in entry["rows"] if r["approved"]),
            "aliases": sum(len(r["aliases"]) for r in entry["rows"]),
            "dropped": sorted(entry["dropped"]), "off_rule": off_rule, "unresolved": unresolved,
            "duplicates": dupes})
    (LIBRARY / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    return index


def _shipped():
    """{(element, asset): list} — the library as it stands in this folder,
    read before a build overwrites it."""
    out = {}
    for f in sorted((ROOT / "library").glob("*.json")):
        if f.stem == "index":
            continue
        d = json.loads(f.read_text())
        out[(d.get("element"), d.get("asset"))] = d
    return out


# ------------------------------------------------------------------ read

_cache = {}


def _list(element, asset):
    key = f"{element}.{asset}"
    if key not in _cache:
        f = LIBRARY / f"{key}.json"
        if not f.is_file():
            known = sorted(p.stem for p in LIBRARY.glob("*.json") if p.stem != "index")
            raise Unknown(f"no list for {element}/{asset} — the library has: {', '.join(known)}")
        _cache[key] = json.loads(f.read_text())
    return _cache[key]


def rows(element, asset):
    return _list(element, asset)["rows"]


def aliases(element, asset):
    """{alias (lower-cased): row} for one list — rows without an `aliases`
    field (older libraries) simply have none."""
    return {a.lower(): r for r in rows(element, asset) for a in (r.get("aliases") or [])}


def dropped(element, asset):
    """{id: why} — ids the owner dropped from this list; asking for one is refused
    with the reason, not with a guess."""
    return _list(element, asset).get("dropped") or {}


def _known(element, asset):
    out = []
    for r in rows(element, asset):
        al = r.get("aliases") or []
        out.append(f"{r['id']} (was {', '.join(al)})" if al else str(r["id"]))
    return ", ".join(out) or "none yet"


def get(element, asset, id_):
    """The row this id names — by id, or by one of its aliases (an old
    spelling). Refused with the real options when it names nothing."""
    for r in rows(element, asset):
        if r["id"] == id_:
            return r
    want = str(id_).lower()
    for r in rows(element, asset):                          # `Apology` is `apology`
        if str(r["id"]).lower() == want:
            return r
    hit = aliases(element, asset).get(want)
    if hit is not None:
        return hit
    why = dropped(element, asset).get(id_)
    if why:
        raise Unknown(f"`{id_}` was dropped from {element}/{asset} — {why}")
    raise Unknown(f"`{id_}` is not a {element} for {asset} — known: {_known(element, asset)}")


def canonical(element, asset, id_):
    """The id to write: `stickynote` -> `sticky-note`. Raises Unknown as get()."""
    return get(element, asset, id_)["id"]


def check(labels, approved_only=False):
    """labels: {(element, asset): id or [ids]} → a list of problems, [] when clean."""
    problems = []
    for (el, asset), vals in labels.items():
        for v in ([vals] if isinstance(vals, str) else vals):
            try:
                r = get(el, asset, v)
                if approved_only and not r["approved"]:
                    problems.append(f"{el}/{asset} `{v}` is a {r['status']}, not approved")
            except Unknown as e:
                problems.append(e.args[0])
    return problems


# ------------------------------------------------------------------ cli

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.split("\n\n")[1])
        return 0
    cmd = argv[0]
    if cmd == "build":
        idx = build()
        for l in idx["lists"]:
            flag = "" if l["rows"] else "   ← EMPTY"
            flag += f"   ← duplicate ids: {', '.join(l['duplicates'])}" if l["duplicates"] else ""
            flag += f"   ← off the id rule: {', '.join(l['off_rule'])}" if l["off_rule"] else ""
            flag += f"   ← unresolved: {'; '.join(l['unresolved'])}" if l["unresolved"] else ""
            print(f"  {l['element']:<10} {l['asset']:<16} {l['rows']:>4} rows · {l['approved']:>3} approved · "
                  f"{l['aliases']:>3} aliases{flag}")
        print(f"-> {LIBRARY}/  ({sum(l['rows'] for l in idx['lists'])} rows in {len(idx['lists'])} lists, "
              f"{sum(l['aliases'] for l in idx['lists'])} aliases)")
        return 0
    if cmd == "list":
        idx = json.loads((LIBRARY / "index.json").read_text())
        for l in idx["lists"]:
            print(f"  {l['element']}/{l['asset']}: {l['rows']} ({l['approved']} approved) — {l['source']}")
        return 0
    if cmd == "get" and len(argv) == 4:
        try:
            print(json.dumps(get(*argv[1:]), indent=1, ensure_ascii=False))
            return 0
        except Unknown as e:
            print(f"REFUSED: {e.args[0]}")
            return 2
    if cmd == "check":
        labels = {}
        for a in argv[1:]:
            k, _, v = a.partition("=")
            el, _, asset = k.partition(":")
            labels.setdefault((el, asset), []).append(v)
        probs = check(labels)
        print("clean" if not probs else "REFUSED:\n  " + "\n  ".join(probs))
        return 2 if probs else 0
    print(__doc__.split("\n\n")[1])
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
