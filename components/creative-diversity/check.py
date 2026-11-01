#!/usr/bin/env python3
"""Score a new creative against the live library — before it's made, or before it goes in.

Brief mode (before anything is made) — give its moves:
    python3 components/creative-diversity/check.py brand-a \
        who=face-dark-marks awareness=unaware argument=grandmas-recipe \
        format=micro-drama face=female/45-54/southeast-asian setting=kitchen look=phone-ugc

Card mode (a finished ad on the approval page) — reads the ad itself:
    python3 components/creative-diversity/check.py --card "<card folder>"

Never calls Meta: it compares against the saved library (matrix.json). Card mode
tags the ad's own media with the same prompt as the library (Gemini) and writes
the result on the card as card["diversity"].
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import matrix as M  # noqa: E402


def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod

DIMS = json.loads((HERE / "dimensions.json").read_text())


def library(brand):
    base = ROOT / "runs" / "creative-diversity" / brand
    days = sorted(p.name for p in base.iterdir() if (p / "matrix.json").exists()) if base.exists() else []
    if not days:
        return None, None
    return json.loads((base / days[-1] / "matrix.json").read_text()), days[-1]


def score(brand, moves):
    """{moves} -> nearest live creative, how many moves apart, the verdict, and the gap it fills."""
    mx, day = library(brand)
    if not mx:
        return {"verdict": "unscored", "why": f"no library read for {brand} yet (pull · tag · matrix)"}
    best = None
    for i in mx["items"]:
        d, diff = M.distance(moves, i["moves"])
        if best is None or d < best[0]:
            best = (d, i, diff)
    r = DIMS["rule"]
    n = best[0] if best else 99
    verdict = "variation" if n <= r["variation_at_or_below"] else "risky" if n == r["risky"] else "new"
    lv = moves.get("awareness")
    fills = []
    if lv and mx["spread"].get(lv) and mx["spread"][lv]["have"] < mx["spread"][lv]["target"]:
        fills.append(f"{lv} is under target ({mx['spread'][lv]['have']:.0%} vs {mx['spread'][lv]['target']:.0%})")
    who = moves.get("who")
    if who and not any(i["moves"].get("who") == who for i in mx["items"]):
        fills.append(f"nothing running for {who}")
    setting = moves.get("setting")
    if setting and not any(i["moves"].get("setting") == setting for i in mx["items"]):
        fills.append(f"setting {setting} not used yet")
    return {"verdict": verdict, "moves_apart": n, "min_moves": r["min_moves"],
            "nearest": best[1]["asset"] if best else None,
            "nearest_is": {k: best[1]["moves"].get(k) for k in M.BIG} if best else None,
            "same_on": [k for k in M.BIG if best and k not in best[2]],
            "fills": fills, "library": day, "moves": moves}


def media_key(files):
    h = hashlib.sha1()
    for f in sorted(files):
        p = Path(f)
        h.update(p.name.encode())
        h.update(str(p.stat().st_size).encode())
    return h.hexdigest()[:16]


def score_card(folder):
    """Tag a card's lead media like the library, score it, write card['diversity']."""
    sys.path.insert(0, str(ROOT / "components" / "meta-upload"))
    import cards as C
    import tag as T
    folder = Path(folder)
    card = C.load(folder)
    brand = card.get("brand") or C.where(folder)["brand"]
    files = [p for p in C.media_files(folder, card) if p.is_file()]
    if not files:
        return None
    key = media_key(files)
    if (card.get("diversity") or {}).get("media_key") == key:
        return card["diversity"]
    lead = next((p for p in files if p.suffix.lower() in (".mp4", ".mov")), files[0])
    words = card.get("words") or {}
    asset = {"file": str(lead), "bodies": words.get("primary") or [], "titles": words.get("headlines") or [],
             "links": [p.get("url") if isinstance(p, dict) else str(p) for p in card.get("pages") or []]}
    if lead.suffix.lower() == ".mov":
        asset["file"] = str(lead)  # Gemini takes .mov as video/mp4 in practice
    t = T.check(brand, T.tag_one(_shared_keys().lookup("GEMINI_API_KEY"), T.fill(brand), asset))
    s = score(brand, M.moves(t))
    s.update({"media_key": key, "scored_at": datetime.now().isoformat(timespec="seconds"),
              "read_from": lead.name, "tag": t})
    card = C.load(folder)
    card["diversity"] = s
    C.save(folder, card)
    return s


def record_brief(brand, brief, moves, force=False):
    """Score a brief's 7 moves and write them on its header in
    brands/<brand>/briefs/briefs.json as `moves` + `diversity`. A variation of a
    running creative is refused (exit 1) unless force — the brief goes back."""
    f = ROOT / "brands" / brand / "briefs" / "briefs.json"
    reg = json.loads(f.read_text())
    row = next((b for b in reg["briefs"] if b.get("brief") == brief or brief in (b.get("aliases") or [])), None)
    if row is None:
        sys.exit(f"{brief} is not in {f.relative_to(ROOT)} — open the brief first")
    s = score(brand, moves)
    if s["verdict"] == "variation" and not force:
        print(json.dumps({k: v for k, v in s.items() if k != "moves"}, indent=1))
        sys.exit(f"REFUSED: {brief} is a variation of a running creative "
                 f"({s['moves_apart']} move(s) from {s['nearest']}, same {', '.join(s['same_on'])}). "
                 f"Change at least {s['min_moves'] - s['moves_apart']} more.")
    row["moves"] = {k: moves.get(k) for k in M.BIG}
    row["diversity"] = {k: s.get(k) for k in ("verdict", "moves_apart", "nearest", "same_on", "fills", "library")}
    row["diversity"]["scored_at"] = datetime.now().isoformat(timespec="seconds")
    f.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
    return s


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--brief":
        # check.py --brief <brand> <brief-id> who=… awareness=… argument=… format=… face=… setting=… look=…
        brand, brief = a[1], a[2]
        pairs = dict(x.split("=", 1) for x in a[3:] if "=" in x)
        missing = [k for k in M.BIG if not pairs.get(k)]
        if missing:
            sys.exit(f"a brief declares all 7 moves — missing: {', '.join(missing)}")
        s = record_brief(brand, brief, {k: pairs[k] for k in M.BIG}, force="--force" in a)
        print(f"{brief}: {s['verdict']} — {s['moves_apart']} moves from the nearest running creative; "
              f"fills: {'; '.join(s['fills']) or 'no open gap'}")
    elif a and a[0] == "--card":
        print(json.dumps({k: v for k, v in (score_card(a[1]) or {}).items() if k != "tag"}, indent=1))
    else:
        brand, pairs = a[0], dict(x.split("=", 1) for x in a[1:])
        print(json.dumps(score(brand, {k: pairs.get(k) for k in M.BIG}), indent=1))
