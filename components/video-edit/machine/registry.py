#!/usr/bin/env python3
"""registry.py — the HyperFrames registry as one of our banks: every block and component
indexed by id in looks/registry.json, so a teardown, a brief or the edit can name any of
them; installed on demand into looks/registry/ (a HyperFrames project folder).

    python3 machine/registry.py index              # rebuild looks/registry.json from `hyperframes catalog --json`
    python3 machine/registry.py install <id> ...   # `hyperframes add <id>` into looks/registry/ (approved)
    python3 machine/registry.py status [<fits>]    # installed / not, per row (optionally one family)
    python3 machine/registry.py find <words>       # rows whose id or description carry the words

    installed(id) -> bool · row(id) -> dict | None · gate(id) -> reason | None

The gate (cutsheet.py) accepts a registry id only once it is installed: an unknown id is
red, a known one that is not installed is red and says the one command that installs it.
A row's `fits` is our family for it: transition · overlay · particles · mock-ui · camera ·
caption · other — read off its registry tags.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
INDEX = TOOL / "looks/registry.json"
PROJECT = TOOL / "looks/registry"
FITS = [  # first match wins
    ("caption", ("captions", "caption-style", "subtitles")),
    ("transition", ("transition", "transition-primitive", "wipe", "transitions-dev-port")),
    ("particles", ("particles", "confetti")),
    ("mock-ui", ("mock-ui", "notification", "chat", "ui-props", "social", "ad-template")),
    ("camera", ("camera", "3d-motion", "orbit", "depth")),
    ("overlay", ("overlay", "texture", "effect", "effects", "grain", "lower-third", "annotation", "background", "shader")),
]


def fits_of(tags: list[str]) -> str:
    t = set(tags or [])
    for fam, keys in FITS:
        if t & set(keys):
            return fam
    return "other"


def index() -> dict:
    out = subprocess.run(["hyperframes", "catalog", "--json"], capture_output=True, text=True, check=True).stdout
    items = json.loads(out)
    rows = [{"id": i["name"], "category": i["type"], "fits": fits_of(i.get("tags")), "title": i.get("title"),
             "what": i.get("description", ""), "tags": i.get("tags") or [],
             "size": (f"{i['dimensions']['width']}x{i['dimensions']['height']}" if i.get("dimensions") else None),
             "seconds": i.get("duration"), "install_cmd": f"python3 machine/registry.py install {i['name']}"}
            for i in sorted(items, key=lambda x: x["name"])]
    ver = subprocess.run(["hyperframes", "--version"], capture_output=True, text=True).stdout.strip()
    d = {"_readme": "Every HyperFrames registry block and component, indexed by id so a teardown, a brief or the edit can name one. "
                    "`fits` is our family for it. A sheet may name a row only once it is INSTALLED (`python3 machine/registry.py install <id>` → "
                    "looks/registry/); the gate refuses an unknown id, and a known one that is not installed. Rebuilt by `registry.py index`.",
         "source": "hyperframes catalog --json", "hyperframes": ver, "updated": dt.date.today().isoformat(), "count": len(rows),
         "by_fits": {f: sum(1 for r in rows if r["fits"] == f) for f in sorted({r["fits"] for r in rows})}, "blocks": rows}
    INDEX.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    return d


def rows() -> dict[str, dict]:
    if not INDEX.exists():
        return {}
    return {r["id"]: r for r in json.loads(INDEX.read_text())["blocks"]}


def row(rid: str) -> dict | None:
    return rows().get(rid)


def file_of(rid: str) -> Path | None:
    r = row(rid)
    if not r:
        return None
    return PROJECT / ("compositions" if r["category"] == "block" else "compositions/components") / f"{rid}.html"


def installed(rid: str) -> bool:
    f = file_of(rid)
    return bool(f and f.is_file())


def gate(rid: str) -> str | None:
    """None when the id may be used; else why not."""
    if not row(rid):
        return f"`{rid}` is not in the HyperFrames registry index (looks/registry.json) — `registry.py find <words>` to look one up"
    if not installed(rid):
        return f"registry `{rid}` is not installed — `python3 machine/registry.py install {rid}`"
    return None


def install(ids: list[str]) -> list[dict]:
    PROJECT.mkdir(parents=True, exist_ok=True)
    hf = PROJECT / "hyperframes.json"
    if not hf.exists():
        hf.write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}, indent=1))
    out = []
    for rid in ids:
        if not row(rid):
            out.append({"id": rid, "ok": False, "why": "not in the index"}); continue
        r = subprocess.run(["hyperframes", "add", rid, "--dir", str(PROJECT), "--json", "--no-clipboard"], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout[r.stdout.index("{"):])
        except Exception:
            j = {"ok": False, "error": (r.stderr or r.stdout)[-400:]}
        out.append({"id": rid, "ok": bool(j.get("ok")) and installed(rid), "written": j.get("written"), "error": j.get("error")})
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "status"
    if cmd == "index":
        d = index(); print(f"indexed {d['count']} registry items → {INDEX}  ({', '.join(f'{k} {v}' for k, v in d['by_fits'].items())})"); return 0
    if cmd == "install":
        res = install(argv[1:])
        for x in res:
            print(("INSTALLED " if x["ok"] else "FAILED    ") + x["id"] + ("" if x["ok"] else f" — {x.get('error') or x.get('why')}"))
        return 0 if all(x["ok"] for x in res) else 1
    if cmd == "find":
        q = [w.lower() for w in argv[1:]]
        for r in rows().values():
            hay = f"{r['id']} {r['what']} {' '.join(r['tags'])}".lower()
            if all(w in hay for w in q):
                print(f"{'installed ' if installed(r['id']) else '          '}{r['id']:32} {r['fits']:10} {r['what'][:90]}")
        return 0
    fam = argv[1] if len(argv) > 1 else None
    n = 0
    for r in rows().values():
        if fam and r["fits"] != fam:
            continue
        n += installed(r["id"])
        print(f"{'installed' if installed(r['id']) else '-':9} {r['id']:34} {r['category']:9} {r['fits']}")
    print(f"{n} installed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
