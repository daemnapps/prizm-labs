#!/usr/bin/env python3
"""icons.py — the icon / emoji / sticker library's installer and lookup. Like fonts,
an icon must be a LOCAL file for a render to be the same every time. Drawn elements
(arrows, rings, bursts, price tags…) are pure SVG/CSS in compose.py and need nothing.
Nothing is downloaded unless someone runs `install`.

    python3 machine/icons.py                  # dry run: every file it would fetch, from where, to where
    python3 machine/icons.py --sizes          # the same with each file's size (asks the server, downloads nothing)
    python3 machine/icons.py install [id ...] # fetch into looks/icons/<set>/
    python3 machine/icons.py status           # drawn · fetched · missing, per row
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
UA = "Mozilla/5.0 video-edit icons.py"


def library() -> dict:
    return json.loads((TOOL / "looks/icons.json").read_text())


def rows() -> dict[str, dict]:
    return {r["id"]: r for r in library()["icons"]}


def url_of(r: dict) -> str | None:
    s = library()["sets"].get(r["set"]) or {}
    if not s.get("url"):
        return None
    return s["url"].format(name=r["source"], code=r["source"], style=r.get("style", "outline")).replace(" ", "%20")


def local(r: dict) -> Path | None:
    if r["kind"] == "drawn":
        return None
    name = f"{r['source']}-{r['style']}.svg" if r["set"] == "tabler" else (r["source"].split("/")[-1] + ".svg" if r["set"] == "fluent" else f"{r['source']}.svg")
    return TOOL / library().get("fetch_dir", "looks/icons") / r["set"] / name


def sprite_path(r: dict) -> Path:
    return TOOL / library().get("fetch_dir", "looks/icons") / "fluent-animated" / f"{r['id']}.png"


def sprite(icon_id: str) -> dict | None:
    """An animated emoji's sprite strip (built by `install` from the Fluent Emoji Animated APNG):
    {png, frames, fps} — or None when the row has no animation or it is not fetched."""
    r = rows().get(icon_id)
    if not r or not r.get("animated"):
        return None
    p = sprite_path(r)
    meta = p.with_suffix(".json")
    if not (p.is_file() and meta.is_file()):
        return None
    return {"png": p, **json.loads(meta.read_text())}


def build_sprite(r: dict, tile: int = 192) -> dict:
    """APNG → one-row strip of `tile`-px frames (alpha kept) + its frame count and rate."""
    import subprocess
    import tempfile
    s = library()["sets"][r["animated"]["set"]]
    url = s["url"].format(name=r["animated"]["source"]).replace(" ", "%20")
    tmp = Path(tempfile.mkdtemp()) / "a.png"
    tmp.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read())
    n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(tmp)],
                           capture_output=True, text=True, check=True).stdout.strip())
    rate = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(tmp)], capture_output=True, text=True).stdout.strip()
    a, b = (rate.split("/") + ["1"])[:2]
    fps = round(float(a) / float(b or 1), 3)
    out = sprite_path(r); out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-vf", f"scale={tile}:{tile}:flags=lanczos,tile={n}x1", "-frames:v", "1",
                    "-pix_fmt", "rgba", str(out)], check=True)
    meta = {"frames": n, "fps": fps, "tile": tile, "from": url}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def status(icon_id: str) -> str:
    r = rows().get(icon_id)
    if not r:
        return "unknown"
    if r["kind"] == "drawn":
        return "drawn"
    p = local(r)
    return "fetched" if p and p.is_file() else "missing"


def svg(icon_id: str) -> str | None:
    """The fetched SVG's markup, sized to fill its box, or None when not fetched."""
    r = rows()[icon_id]
    p = local(r)
    if not p or not p.is_file():
        return None
    t = p.read_text()
    t = t[t.find("<svg"):]
    import re
    t = re.sub(r'\s(width|height)="[^"]*"', "", t, count=2)
    return t.replace("<svg", '<svg width="100%" height="100%"', 1)


def plan(ids: list[str] | None = None) -> list[dict]:
    out, seen = [], set()
    for r in library()["icons"]:
        if r["kind"] == "drawn" or (ids and r["id"] not in ids):
            continue
        u, p = url_of(r), local(r)
        if u in seen:
            continue  # a sticker reuses its emoji's file
        seen.add(u)
        out.append({"icon": r["id"], "set": r["set"], "licence": r["licence"], "url": u, "dest": str(p)})
    return out


def size_of(url: str) -> int | None:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        return int(urllib.request.urlopen(req, timeout=20).headers.get("Content-Length") or 0) or None
    except Exception:
        return None


def install(ids: list[str] | None = None) -> list[dict]:
    got = plan(ids)
    for x in got:
        d = Path(x["dest"]); d.parent.mkdir(parents=True, exist_ok=True)
        d.write_bytes(urllib.request.urlopen(urllib.request.Request(x["url"], headers={"User-Agent": UA}), timeout=30).read())
    for r in library()["icons"]:  # the animated ones: APNG → sprite strip
        if r.get("animated") and (not ids or r["id"] in ids) and not sprite(r["id"]):
            m = build_sprite(r)
            got.append({"icon": r["id"], "set": r["animated"]["set"], "licence": r["licence"], "url": m["from"], "dest": str(sprite_path(r))})
    return got


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["status"]:
        for i, r in rows().items():
            print(f"{status(i):8} {i:20} {r['kind']:8} {r['set']:10} {r['licence']}")
        return 0
    if argv[:1] == ["install"]:
        print(f"fetched {len(install(argv[1:] or None))} file(s)"); return 0
    sizes = "--sizes" in argv
    ids = [a for a in argv if not a.startswith("-")] or None
    total, missing, got = 0, [], plan(ids)
    print("DRY RUN — nothing downloaded. `install` would fetch:")
    for x in got:
        n = size_of(x["url"]) if sizes else None
        total += n or 0
        if sizes and not n:
            missing.append(x["icon"])
        print(f"  {x['icon']:18} {x['set']:10} {x['licence']:10} {(str(round(n / 1024, 1)) + ' KB') if n else ('NOT FOUND' if sizes else ''):>9}  {x['url']}")
    by = {}
    for x in got:
        by[x["set"]] = by.get(x["set"], 0) + 1
    print(f"{len(got)} file(s): " + ", ".join(f"{k} {v}" for k, v in by.items()) + (f" — {total / 1024:.0f} KB in all" if sizes else ""))
    if missing:
        print("NOT FOUND at the source: " + ", ".join(missing))
    print(f"drawn by the edit (nothing to fetch): {sum(1 for r in rows().values() if r['kind'] == 'drawn')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
