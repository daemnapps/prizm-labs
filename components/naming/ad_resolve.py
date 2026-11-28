#!/usr/bin/env python3
"""Every live ad, tied to a brief or a creator.

An ad's name is the join key between spend and the work behind it (CONVENTION.md). Most live ads carry the short
form `brand_product_brief_batch_funnel` and read straight off the name. Three kinds do not, and each is tied here:

  extra field   `…_brief-0318_batch-…_funnel_p-<tag>`  the short form with a field after the funnel (a Facebook
                                                         Page's tag, added 21-28 Nov 2026); read as usual. The Page
                                                         an ad runs from is meta-upload/page_index.py's job
  creator ad    `<Creator>_<product>_<date>_trybe=<id>`  the creator-program id; tied to its creator through the
                                                         newest creator-program read, else the name's first part
  legacy name   `IG Story Images - <page> - Copy`        made before the register; tied through the brand's small
                                                         alias file, brands/<brand>/meta/ad-aliases.json

resolve() returns {"brief", "brief_id", "product", "creator", "trybe_id", "legacy", "via", "extra"}; `via` is
"name" | "trybe" | "alias", or None when nothing ties the ad (listed by `check`, never guessed).

    ad_resolve.py check <brand> [warehouse.json]    every ad in the newest warehouse copy: tied how, and what is not
"""
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N  # noqa: E402

TRYBE = re.compile(r"trybe=([0-9a-z]+)", re.I)
BRIEF_IN = re.compile(r"brief-(\d{4})")
ALIAS_FILE = ("meta", "ad-aliases.json")


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def alias_file(brand):
    return N.BP.brand_path(N.slug(brand), *ALIAS_FILE, root=N.WS / "brands")


def aliases(brand):
    """The brand's legacy-name table: [{"match": "<name before the first ' - '>", "brief" | "creator" | "legacy"}]."""
    d = _read(alias_file(brand)) or {}
    return [a for a in (d.get("aliases") or []) if isinstance(a, dict) and a.get("match")]


def trybe_creators(brand):
    """creator-program id -> creator, from every creator-program read (runs/winners/<brand>/creators/<date>/trybe.json);
    the newer read wins."""
    out = {}
    for f in sorted(glob.glob(str(N.WS / "runs/winners" / N.slug(brand) / "creators/*/trybe.json"))):
        for r in (_read(f) or {}).get("rows") or []:
            if isinstance(r, dict) and r.get("trybe_id") and r.get("creator"):
                out[str(r["trybe_id"]).lower()] = r["creator"]
    return out


def name_creator(name):
    """The creator a creator ad's name starts with (`ThomasGuzek_FLEX…` -> `Thomas Guzek`)."""
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", re.split(r"_|\s+-\s+", name or "")[0]).strip() or None


def legacy_stem(name):
    return re.split(r"\s+-\s+", (name or "").strip())[0].strip().lower()


def resolve(brand, name, al=None, tc=None):
    out = {"brief": None, "brief_id": None, "product": None, "creator": None, "trybe_id": None, "legacy": None,
           "via": None, "extra": []}
    name = (name or "").strip()
    d = N.parse_any(name) if name else None
    if d and d.get("brief_id") and str(d["brief_id"]).startswith("brief-"):
        out.update(brief_id=d["brief_id"], brief=d["brief_id"][-4:], product=d.get("product"), via="name",
                   extra=d.get("extra") or [])
        return out
    m = TRYBE.search(name)
    if m:
        tid = m.group(1).lower()
        tc = trybe_creators(brand) if tc is None else tc
        out.update(trybe_id=tid, creator=tc.get(tid) or name_creator(name), via="trybe")
        return out
    m = BRIEF_IN.search(name)
    if m:                                      # a brief number in a name of no known shape still names its brief
        out.update(brief=m.group(1), brief_id="brief-" + m.group(1), via="name")
        return out
    stem, full = legacy_stem(name), name.lower()
    for a in (aliases(brand) if al is None else al):
        if str(a["match"]).strip().lower() in (stem, full):
            b = a.get("brief")
            if b:
                bid = N.brief_id(b) if N.is_brief_id(b) else str(b)
                out.update(brief_id=bid, brief=bid[-4:] if bid.startswith("brief-") else None, product=a.get("product"))
            out.update(creator=a.get("creator"), legacy=a.get("legacy"), via="alias")
            return out
    return out


def resolve_all(brand, ad_names):
    al, tc = aliases(brand), trybe_creators(brand)
    return {n: resolve(brand, n, al, tc) for n in ad_names}


def check(brand, wf=None):
    wf = wf or (sorted(glob.glob(str(N.WS / "runs/funnel-tracking" / N.slug(brand) / "2*/warehouse.json"))) or [None])[-1]
    if not wf:
        print(f"{brand}: no warehouse copy")
        return 1
    ads = (_read(wf) or {}).get("ads") or []
    got = resolve_all(brand, [a.get("ad_name") for a in ads])
    by = {}
    for a in ads:
        r = got[a.get("ad_name")]
        kind = ("brief" if r["brief"] else "creator" if r["creator"] else "legacy" if r["legacy"] else "not tied")
        by.setdefault(kind, []).append(a.get("ad_name"))
    print(f"{brand}: {len(ads)} ads · " + " · ".join(f"{len(v)} {k}" for k, v in sorted(by.items())))
    for n in by.get("legacy", []) + by.get("not tied", []):
        print(f"  {'legacy' if got[n]['legacy'] else 'NOT TIED'}  {n}")
    return 1 if by.get("not tied") else 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "check":
        sys.exit(check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    print(__doc__)
