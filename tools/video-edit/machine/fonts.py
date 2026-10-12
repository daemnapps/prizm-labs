#!/usr/bin/env python3
"""fonts.py — the font library's installer and lookup. Fonts must be LOCAL files so
a render is the same on every machine (HyperFrames renders in a clean headless
Chrome). Nothing is downloaded unless someone runs `install`.

    python3 machine/fonts.py                      # dry run: what it would fetch, from where, to where
    python3 machine/fonts.py --sizes              # the same, with each file's size (asks the server, downloads nothing)
    python3 machine/fonts.py install [id ...]     # fetch every non-bundled font (or just these) into looks/fonts/<id>/
    python3 machine/fonts.py status               # bundled · fetched · missing, per font

A font row lives in looks/fonts.json. `bundled` fonts ship inside HyperFrames and
need nothing. The rest come from Google Fonts' css2 API (woff2, the subsets named
in fonts.json) and are written with a manifest.json the edit reads for @font-face.
Until a font is fetched, `stack()` returns its fallback font and the gate WARNS.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def library() -> dict:
    return json.loads((TOOL / "looks/fonts.json").read_text())


def rows() -> dict[str, dict]:
    return {r["id"]: r for r in library()["fonts"]}


def folder(font_id: str) -> Path:
    return TOOL / library().get("fetch_dir", "looks/fonts") / font_id


def manifest(font_id: str) -> dict | None:
    m = folder(font_id) / "manifest.json"
    if not m.is_file():
        return None
    d = json.loads(m.read_text())
    return d if all((folder(font_id) / f["file"]).is_file() for f in d.get("files") or []) and d.get("files") else None


def status(font_id: str) -> str:
    r = rows().get(font_id)
    if not r:
        return "unknown"
    if r.get("bundled"):
        return "bundled"
    return "fetched" if manifest(font_id) else "missing"


def resolve(font_id: str) -> tuple[dict, str | None]:
    """The row that will actually draw, and a warning when it is a stand-in."""
    R = rows()
    r = R.get(font_id)
    if r is None:
        raise KeyError(f"font `{font_id}` is not in looks/fonts.json")
    st = status(font_id)
    if st in ("bundled", "fetched"):
        return r, None
    fb = R.get(r.get("fallback") or "inter") or R["inter"]
    return fb, f"font `{font_id}` ({r['family']}) is not fetched yet — drawn in `{fb['id']}` ({fb['family']}) until `python3 machine/fonts.py install {font_id}` is run"


def stack(font_id: str) -> str:
    r, _ = resolve(font_id)
    return f"'{r['family']}',{r.get('generic', 'sans-serif')}"


def faces(font_id: str, url_prefix: str = "assets/fonts") -> tuple[str, list[Path]]:
    """@font-face CSS for a FETCHED font, and the files the page must carry. Empty for bundled or missing."""
    if status(font_id) != "fetched":
        return "", []
    m = manifest(font_id)
    css, files = [], []
    for f in m["files"]:
        p = folder(font_id) / f["file"]
        files.append(p)
        ur = f";unicode-range:{f['unicode_range']}" if f.get("unicode_range") else ""
        css.append(f"@font-face{{font-family:'{m['family']}';font-style:{f.get('style', 'normal')};font-weight:{f['weight']};"
                   f"font-display:block;src:url('{url_prefix}/{font_id}-{p.name}') format('woff2'){ur}}}")
    return "".join(css), files


# ------------------------------------------------------------------ the fetch list
def plan(ids: list[str] | None = None) -> list[dict]:
    """Every file `install` would write: {font, url, dest, weight, subset}. Reads Google's css2 (a few KB of text per font)."""
    lib = library()
    subsets = set(lib.get("subsets") or ["latin"])
    out = []
    for r in lib["fonts"]:
        if r.get("bundled") or not r.get("fetch") or (ids and r["id"] not in ids):
            continue
        req = urllib.request.Request(r["fetch"] + "&display=block", headers={"User-Agent": UA})
        css = urllib.request.urlopen(req, timeout=20).read().decode()
        seen = {}
        for block in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*{([^}]*)}", css):
            subset, body = block
            if subset not in subsets:
                continue
            url = re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1)
            weight = re.search(r"font-weight:\s*([^;]+);", body).group(1).strip()
            style = re.search(r"font-style:\s*([^;]+);", body).group(1).strip()
            ur = (re.search(r"unicode-range:\s*([^;]+);", body) or [None, None])[1]
            if url in seen:  # a variable font serves one file for every weight: widen that file's range
                ws = seen[url]
                lo, hi = min(ws["w"] + [int(weight.split()[0])]), max(ws["w"] + [int(weight.split()[-1])])
                ws["w"] += [lo, hi]
                ws["row"]["weight"] = f"{lo} {hi}" if lo != hi else str(lo)
                continue
            name = f"{subset}-{len([x for x in out if x['font'] == r['id']]) + 1}.woff2"
            row = {"font": r["id"], "family": r["family"], "url": url, "file": name, "dest": str(folder(r["id"]) / name),
                   "weight": weight, "style": style, "subset": subset, "unicode_range": ur.strip() if ur else None}
            seen[url] = {"w": [int(weight.split()[0])], "row": row}
            out.append(row)
    return out


def size_of(url: str) -> int | None:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        return int(urllib.request.urlopen(req, timeout=20).headers.get("Content-Length") or 0) or None
    except Exception:
        return None


def install(ids: list[str] | None = None) -> list[dict]:
    rows_ = plan(ids)
    by: dict[str, list[dict]] = {}
    for x in rows_:
        d = Path(x["dest"]); d.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(x["url"], headers={"User-Agent": UA})
        d.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        by.setdefault(x["font"], []).append(x)
    for fid, xs in by.items():
        (folder(fid) / "manifest.json").write_text(json.dumps({"id": fid, "family": xs[0]["family"], "licence": rows()[fid]["licence"],
                                                               "source": rows()[fid]["source"],
                                                               "files": [{k: x[k] for k in ("file", "weight", "style", "subset", "unicode_range", "url")} for x in xs]}, indent=1))
    return rows_


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["status"]:
        for fid, r in rows().items():
            print(f"{status(fid):8} {fid:18} {r['family']}  ({r['licence']})")
        return 0
    if argv[:1] == ["install"]:
        done = install(argv[1:] or None)
        print(f"fetched {len(done)} file(s) into {TOOL / library().get('fetch_dir', 'looks/fonts')}")
        return 0
    sizes = "--sizes" in argv
    ids = [a for a in argv if not a.startswith("-")] or None
    total, rows_ = 0, plan(ids)
    print("DRY RUN — nothing downloaded. `install` would fetch:")
    for x in rows_:
        n = size_of(x["url"]) if sizes else None
        total += n or 0
        print(f"  {x['font']:18} {x['subset']:9} w{x['weight']:9} {(str(round(n / 1024)) + ' KB') if n else '':>7}  {x['url']}  →  {Path(x['dest']).relative_to(TOOL)}")
    fonts = sorted({x['font'] for x in rows_})
    print(f"{len(rows_)} file(s), {len(fonts)} font(s): {', '.join(fonts)}" + (f" — {total / 1024:.0f} KB in all" if sizes else ""))
    print("bundled (nothing to fetch): " + ", ".join(fid for fid, r in rows().items() if r.get("bundled")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
