"""THE USAGE BANK — how the product is really held and used, read off the brand's own footage of real
people using it (2026-10-09, the owner: "look at the B-roll that I have in the archives of real people using
the product so you can index the actual angles and the way that the product is used … the bristles need
to be up against the face and it needs to fit in the palm of his hand").

  find     the footage index (tools/asset-index, search.py) is asked for the product in use, with
           the kit's own queries (`kit.json usage.queries`) — only the brand's own creators and archive,
           never a swipe of another brand's product (`usage.collections`, default: the brand's creators)
  frames   a few frames from each hit, out of the clip's local proxy (ffmpeg; nothing is downloaded)
  read     each frame is read by the vision model against the kit: is this the real product (shape,
           colour, details), and if so — the grip, where it touches, which side faces the skin, the camera,
           wet / foam, hand count. A frame that is not the real product is dropped, with why.
  bank     kept frames land in the kit's `usage/` with `usage/index.json`; element_refs picks the closest
           one per scene as the "product in use" reference

    python3 product_usage.py <brand> <product slug> [--per 6] [--frames 3] [--dry-run]

Brand-agnostic: the queries, the collections and the product's description come from the kit.
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
SEARCH = WS / "tools" / "asset-index" / "machine"


def _footage_local(ref):
    """A footage "Shared Assets/…" label (or an old mount path) as a file to open — asset-index
    shared_paths.local(), through the key (LD-56 (footage index in git))."""
    import importlib.util as _u
    f = Path(__file__).resolve().parents[2] / "asset-index" / "machine" / "shared_paths.py"
    sp = _u.spec_from_file_location("asset_index_shared_paths", str(f)); m = _u.module_from_spec(sp); sp.loader.exec_module(m)
    return m.local(ref)

DEFAULT_QUERIES = [
    "man uses the {what} on his jaw", "man scrubs his face with the {what}", "the {what} on his cheek, foam",
    "the {what} in the shower on his face", "holds the {what} in his palm to the camera",
    "the {what} on his neck", "close-up of the {what} against the skin", "mirror, man uses the {what} on his face",
]

READ = """You are looking at one frame of real footage. The product we sell is: {what}. Its real shape and
details are in the reference picture (image 2) — {details}

Answer about the frame (image 1) ONLY. Return ONE JSON object:
{{"is_product": true|false  — the real product from image 2 is clearly visible (not another brand's brush, not a bottle),
 "why_not": "if false, what it is instead",
 "in_use": true|false  — it is touching the face, neck or skin right now,
 "contact": "jaw" | "cheek" | "neck" | "chin" | "forehead" | "none",
 "skin_side": "bristles" | "back" | "edge" | "none"  — which side of the product is against the skin,
 "grip": one short phrase of how the hand holds it (e.g. "closed palm, fingers round the back, thumb on the band"),
 "hands": 0 | 1 | 2,
 "fills_palm": true|false,
 "camera": "selfie front" | "mirror" | "profile" | "pov" | "close-up" | "other",
 "wet": true|false, "foam": true|false,
 "setting": "shower" | "sink" | "bedroom" | "outdoors" | "other",
 "describe": "one sentence a picture prompt could copy: how the hand holds it and where it meets the skin"}}"""


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py"); m = u.module_from_spec(sp); sp.loader.exec_module(m); return m


def _search():
    sys.path.insert(0, str(SEARCH))
    import search  # noqa: E402
    return search


def hits(brand: str, kit: dict, per: int = 6) -> list:
    S = _search()
    u = kit.get("usage") or {}
    what = u.get("search_name") or kit.get("what") or "the product"
    queries = u.get("queries") or [q.format(what=what) for q in DEFAULT_QUERIES]
    keep_paths = u.get("from_paths") or ["/content-creators/", "/archive/"]     # never another brand's swipe
    seen, out = set(), []
    for q in queries:
        for h in S.search(q, None, brand=brand, mapped=False)[:per]:   # real clips with in/out only (LD-59)
            if h["clip_id"] in seen or not any(k in (h.get("shared_path") or "") for k in keep_paths):
                continue
            seen.add(h["clip_id"])
            out.append({**h, "query": q})
    return out


def frames(hit: dict, folder: Path, n: int = 3) -> list:
    src = hit.get("proxy") if hit.get("proxy") and Path(hit["proxy"]).is_file() else hit.get("shared_path")
    if src and not Path(src).exists():
        src = _footage_local(src)             # a "Shared Assets/…" label, read through the key (LD-56)
    if not src or not Path(src).exists():
        return []
    t0, t1 = float(hit.get("in") or 0), float(hit.get("out") or 0)
    if t1 <= t0:
        t1 = t0 + 2
    got = []
    for i in range(n):
        t = t0 + (t1 - t0) * (i + 0.5) / n
        f = folder / f"{hit['clip_id']}-{t:05.1f}.jpg"
        if not f.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                            "-q:v", "3", str(f)], capture_output=True)
        if f.exists():
            got.append((t, f))
    return got


def read(frame: Path, kit_dir: Path, kit: dict, caller=None) -> dict:
    rv = _load("product_kit")._review()
    ref = kit_dir / "sources" / "turntable-sheet.png"
    details = "; ".join(x for x in (kit.get("what"), (kit.get("behaviour") or {}).get("held")) if x)
    q = READ.format(what=kit.get("what") or "the product", details=details)
    parts = [{"text": q}, rv._part(str(frame))] + ([rv._part(str(ref))] if ref.is_file() else [])
    a = rv.ask(parts, caller=caller)
    return a if isinstance(a, dict) else (a[0] if a else {})


def build(brand: str, slug: str, per: int = 6, n: int = 3, dry_run: bool = False, caller=None, log=print) -> dict:
    PK = _load("product_kit")
    kit_dir = PK.home(brand, slug)
    kit = json.loads((kit_dir / "kit.json").read_text())
    hs = hits(brand, kit, per)
    log(f"usage: {len(hs)} clip(s) of {kit.get('what')} in use found in the footage index")
    if dry_run:
        for h in hs:
            log(f"  {h['score']:.2f}  {h['clip_id']}  {h['shows'][:90]}")
        return {"clips": len(hs)}
    folder = kit_dir / "usage"
    folder.mkdir(exist_ok=True)
    idx_f = folder / "index.json"
    idx = json.loads(idx_f.read_text()) if idx_f.is_file() else {"frames": {}, "dropped": {}}
    for h in hs:
        for t, f in frames(h, folder, n):
            if f.name in idx["frames"] or f.name in idx["dropped"]:
                continue
            try:
                r = read(f, kit_dir, kit, caller=caller)
            except Exception as e:                      # noqa: BLE001 — one unreadable frame never stops the bank
                log(f"  {f.name}: not read ({type(e).__name__})")
                continue
            row = {**r, "clip_id": h["clip_id"], "at": round(t, 1), "shared_path": h.get("shared_path"),
                   "shows": h.get("shows"), "file": f"usage/{f.name}"}
            if r.get("is_product") and r.get("in_use") is not None:
                idx["frames"][f.name] = row
                log(f"  KEEP {f.name}: {r.get('contact')} · {r.get('skin_side')} to skin · {r.get('grip')} · {r.get('camera')}")
            else:
                idx["dropped"][f.name] = {"why": r.get("why_not") or "not the real product", "clip_id": h["clip_id"]}
                f.unlink(missing_ok=True)                 # the bank's own temp frame, never footage
                log(f"  drop {f.name}: {r.get('why_not') or 'not the real product'}")
            idx_f.write_text(json.dumps(idx, indent=1, ensure_ascii=False))
    kept = idx["frames"].values()
    # what the real footage says, in numbers — the words every picture of it in use can carry
    use = [x for x in kept if x.get("in_use")]
    tally = lambda k: sorted({str(x.get(k)) for x in use}, key=lambda v: -sum(str(x.get(k)) == v for x in use))
    idx["summary"] = {"frames": len(list(kept)), "in_use": len(use), "skin_side": tally("skin_side"),
                      "contact": tally("contact"), "hands": tally("hands"), "camera": tally("camera"),
                      "fills_palm": sum(bool(x.get("fills_palm")) for x in use)}
    idx_f.write_text(json.dumps(idx, indent=1, ensure_ascii=False))
    log(f"usage bank: {idx['summary']}")
    return idx


WORDS = {"jaw": ("jaw", "jawline", "beard line"), "cheek": ("cheek",), "neck": ("neck",), "chin": ("chin",),
         "forehead": ("forehead",)}


def pick(kit_dir: Path, scene_text: str) -> Path | None:
    """The banked usage frame closest to what the scene does: where it touches, wet or not, the camera."""
    f = Path(kit_dir) / "usage" / "index.json"
    if not f.is_file():
        return None
    # only the RIGHT use: bristles on the skin, one hand (a creator pressing the smooth back to his jaw is
    # real footage of the wrong use)
    rows = [r for r in json.loads(f.read_text()).get("frames", {}).values()
            if r.get("in_use") and r.get("skin_side") == "bristles" and str(r.get("hands")) == "1"]
    if not rows:
        return None
    t = (scene_text or "").lower()
    def score(r):
        s = 0.0
        for k, ws in WORDS.items():
            if any(w in t for w in ws) and r.get("contact") == k:
                s += 3
        if ("shower" in t or "water" in t or "wet" in t) == bool(r.get("wet")):
            s += 1
        if "foam" in t and r.get("foam"):
            s += 1
        if "mirror" in t and r.get("camera") == "mirror":
            s += 1
        if r.get("skin_side") == "bristles":
            s += 1
        if r.get("hands") == 1:
            s += 1
        if r.get("fills_palm"):
            s += 0.5
        return s
    best = max(rows, key=score)
    p = Path(kit_dir) / best["file"]
    return p if p.is_file() else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("brand"); ap.add_argument("slug")
    ap.add_argument("--per", type=int, default=6); ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    x = ap.parse_args()
    build(x.brand, x.slug, x.per, x.frames, x.dry_run)
