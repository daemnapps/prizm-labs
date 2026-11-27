#!/usr/bin/env python3
"""concept: the concept a brief names, and the opening each filed asset carries, kept on the brief's record.

    concept.py show   <brand> <brief> [--product P]    what the record holds, and what the brief itself names
    concept.py record <brand> <brief> [--product P]    read the brief and write its concept onto the record

The ad's short name stays as CONVENTION.md says: brand, product, brief, batch. A name that short can't say which
concept an ad is, or which opening an asset carries, so both are looked up on the brief's record (the brief register)
by the brief id the name already holds:

  concept        the concept the brief names (`concept` in its piece block); set once, read off the brief
  concept_from   the brief file it was read from, repo-relative
  openings       {ad name: [{"asset": "asset-01", "version": "control", "opening": "Opening 1 · Control",
                             "text": "..."}]}: which opening each filed asset is, written when the ad is filed

Nothing here is invented and no model is called: a brief that names no concept gets none, and says so.
A change to a concept is made on the brief, never on the card or in the name.
"""
import argparse, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N  # noqa: E402

WS = N.WS
OFF_ENV = "NAMING_CONCEPT"             # "off" / "0" skips the hook at brief registration
BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.S)
BRIEF_NAMES = ("7-final-brief.md", "5-brief.md", "EDITOR-BRIEF.md", "brief.md", "06-brief.md")


def off():
    return os.environ.get(OFF_ENV, "").strip().lower() in ("off", "0", "no", "false")


# ---------------------------------------------------------------- the brief

def piece_block(text):
    """The brief's own record: the first fenced json block that holds a `piece` or a `hooks` list. {} when none."""
    for raw in BLOCK.findall(text or ""):
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if isinstance(d, dict) and (isinstance(d.get("piece"), dict) or isinstance(d.get("hooks"), list)):
            return d
    return {}


def _named(v):
    """(name, why) of a concept or an idea as the brief wrote it: a line, or an object with a name and a reason."""
    if isinstance(v, str):
        return (" ".join(v.split()) or None), None
    if isinstance(v, dict):
        name = next((v[k] for k in ("name", "concept", "idea", "title", "label", "text", "choice") if v.get(k)), None)
        why = next((v[k] for k in ("why", "reason", "because") if v.get(k)), None)
        return (" ".join(str(name).split()) if name else None), (" ".join(str(why).split()) if why else None)
    return None, None


def from_brief(path):
    """What a brief names: {"concept", "concept_why", "idea", "openings": [{"id", "text", "take"}]}.
    A brief with no piece block, or one that names no concept, answers None for it."""
    try:
        d = piece_block(Path(path).read_text())
    except OSError:
        d = {}
    piece = d.get("piece") if isinstance(d.get("piece"), dict) else {}
    concept, why = _named(piece.get("concept") if "concept" in piece else d.get("concept"))
    idea, _ = _named(piece.get("idea") if "idea" in piece else d.get("idea"))
    openings = []
    for h in d.get("hooks") or []:
        if isinstance(h, dict) and (h.get("id") or h.get("text")):
            openings.append({"id": h.get("id"), "text": h.get("text"), "take": h.get("take")})
    return {"concept": concept, "concept_why": why, "idea": idea, "openings": openings}


def brief_file(entry, ws=None):
    """The brief a register entry stands for: its own `brief_file`, else the writing run's brief, else the run's."""
    ws = Path(ws or WS)
    if entry.get("brief_file") and (ws / entry["brief_file"]).is_file():
        return ws / entry["brief_file"]
    name, brand = str(entry.get("run") or ""), N.slug(entry.get("brand") or "")
    if not name:
        return None
    label = Path(name).name
    homes = [ws / "runs" / "video-writing" / brand / label / "deliverable", ws / name / "deliverable", ws / name,
             ws / "runs" / "video-teardown" / brand / label]
    for d in homes:
        for bn in BRIEF_NAMES:
            if (d / bn).is_file():
                return d / bn
    for d in homes[:2]:
        found = sorted(d.glob("*.md")) if d.is_dir() else []
        if found:
            return found[0]
    return None


# ---------------------------------------------------------------- the record

def register(reg_file=None):
    f = Path(reg_file) if reg_file else N.register_file()
    return f, json.loads(f.read_text())


def _save(f, reg):
    """Written whole beside the file, then swapped in, so a reader never sees half a register."""
    tmp = f.with_name(f".{f.name}.{os.getpid()}.concept.tmp")
    tmp.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, f)
    N._ALIASES = None


def find_entry(reg, brand, brief, product=None):
    """(key, entry) on the register for this brief, or (None, None)."""
    hit = N.find_brief(brand, brief, product, reg=reg)
    r = (hit or {}).get("register")
    if not r:
        return None, None
    return r["key"], reg["briefs"][r["key"]]


def _rel(p, ws=None):
    try:
        return str(Path(p).resolve().relative_to(Path(ws or WS).resolve()))
    except ValueError:
        return Path(p).name


def record(brand, brief, product=None, reg_file=None, ws=None, again=False):
    """Read the concept off the brief and write it onto its register entry. Set once: an entry that already has a
    concept keeps it unless `again`. -> {"key", "concept", "from", "wrote"}; concept None when the brief names none."""
    f, reg = register(reg_file)
    key, entry = find_entry(reg, brand, brief, product)
    if entry is None:
        return {"key": None, "concept": None, "from": None, "wrote": False, "why": f"no brief {brief} for {brand}"}
    if entry.get("concept") and not again:
        return {"key": key, "concept": entry["concept"], "from": entry.get("concept_from"), "wrote": False}
    bf = brief_file(entry, ws)
    got = from_brief(bf) if bf else {"concept": None}
    if not got.get("concept"):
        return {"key": key, "concept": None, "from": _rel(bf, ws) if bf else None, "wrote": False,
                "why": "the brief names no concept" if bf else "no brief file found for this entry"}
    entry["concept"] = got["concept"]
    entry["concept_from"] = _rel(bf, ws)
    if got.get("concept_why"):
        entry["concept_why"] = got["concept_why"]
    _save(f, reg)
    return {"key": key, "concept": got["concept"], "from": entry["concept_from"], "wrote": True}


def file_assets(brand, brief, product, ad_name, labels, reg_file=None):
    """Write which opening each filed asset carries onto the brief's register entry, under the ad's name.
    `labels` is the card's `openings` list. -> True when the record changed."""
    rows = [{k: x.get(k) for k in ("asset", "version", "opening", "text") if x.get(k) is not None}
            for x in labels or [] if isinstance(x, dict) and x.get("asset")]
    if not rows or not ad_name:
        return False
    f, reg = register(reg_file)
    _, entry = find_entry(reg, brand, brief, product)
    if entry is None:
        return False
    have = entry.get("openings") if isinstance(entry.get("openings"), dict) else {}
    if have.get(ad_name) == rows:
        return False
    entry["openings"] = {**have, ad_name: rows}
    _save(f, reg)
    return True


def auto(brand, brief, product=None, say=print):
    """The hook at brief registration. Never raises: a brief is opened either way."""
    if off():
        return None
    try:
        res = record(brand, brief, product)
        if res.get("wrote"):
            say(f"  concept: {res['concept']} (read off {res['from']})")
        return res.get("concept")
    except Exception as e:                       # noqa: BLE001
        say(f"  concept: not read ({str(e)[:200]})")
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("show", "record"))
    ap.add_argument("brand"); ap.add_argument("brief"); ap.add_argument("--product")
    ap.add_argument("--again", action="store_true", help="record: read it off the brief again")
    a = ap.parse_args(argv)
    _, reg = register()
    key, entry = find_entry(reg, a.brand, a.brief, a.product)
    if entry is None:
        print(f"no brief {a.brief} for {a.brand}", file=sys.stderr)
        return 2
    if a.verb == "record":
        res = record(a.brand, a.brief, a.product, again=a.again)
        print(json.dumps(res, indent=1, ensure_ascii=False))
        return 0
    bf = brief_file(entry)
    print(json.dumps({"key": key, "on_record": {k: entry.get(k) for k in ("concept", "concept_from", "openings")},
                      "brief_file": _rel(bf) if bf else None, "brief_names": from_brief(bf) if bf else None},
                     indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
