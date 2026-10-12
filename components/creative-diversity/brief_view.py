#!/usr/bin/env python3
"""The brief reader behind the Viewer Check's "new to Meta" line — before anything is produced.

the owner, 2026-10-08: "add in to the viewer … identifying diversity against the
scripts / briefs it reads. this would make the process more bullet proof."

Reads written briefs (chain stage 5 outputs, Distinct Six versions, any .md),
reads the seven moves off each (Gemini, prompts/read-brief-moves-v1-damon.md),
then says which pairs Meta would group as one creative and which copy what is
already running. Off to the side of the Viewer Check; wired in after the developer's
merge. Never calls Meta.

    python3 components/creative-diversity/brief_view.py brand-a <brief.md> <brief.md> ...
    python3 components/creative-diversity/brief_view.py brand-a --runs runs/video-teardown/<brand>/<run>

Writes runs/creative-diversity/<brand>/brief-view/<stamp>.json and prints the verdict.
"""
import json
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check as K  # noqa: E402
import matrix as M  # noqa: E402
import tag as T  # noqa: E402

PROMPT = HERE / "prompts" / "read-brief-moves-v1-damon.md"
MIN = json.loads((HERE / "dimensions.json").read_text())["rule"]["min_moves"]


def filled(brand, brief_text):
    L = T.lists(brand)
    av = json.loads((ROOT / "brands" / brand / "core-avatars" / "avatars.json").read_text())["avatars"]
    subs = " · ".join(f"`{s}`" for a in av for s in (a.get("sub_avatars") or [a["id"]]))
    text = PROMPT.read_text()
    for k, v in {"BRAND": L["BRAND"], "SUBS": subs, "ANGLES": L["ANGLES"],
                 "FORMATS": L["VIDEO_FORMATS"] + " · " + L["VIDEO_STRUCTURES"] + " · " + L["IMAGE_FORMATS"],
                 "SETTINGS": L["SETTINGS"], "STYLES": L["VIDEO_STYLES"] + " · " + L["IMAGE_STYLES"],
                 "BRIEF": brief_text[:60000]}.items():
        text = text.replace("{" + k + "}", v)
    return text



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


def gemini_text(prompt):
    k = _shared_keys().lookup("GEMINI_API_KEY")
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    r = T.call(f"{T.API}/v1beta/models/{T.MODEL}:generateContent?key={k}",
               json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])


def read_moves(brand, text):
    t = gemini_text(filled(brand, text))
    t = T.check(brand, {**t, "style": t.get("style"), "sub_avatar": t.get("sub_avatar")})
    return t


def view(brand, items):
    """items: [(label, text)] -> verdict dict."""
    read = []
    for label, text in items:
        t = read_moves(brand, text)
        mv = M.moves({"sub_avatar": t.get("sub_avatar"), "awareness": t.get("awareness"), "angle": t.get("angle"),
                      "format": t.get("format"), "setting": t.get("setting"), "style": t.get("style"),
                      "face": _face(t.get("face"))})
        run = K.score(brand, mv)
        read.append({"label": label, "moves": mv, "why": t.get("why"), "sections": t.get("sections"),
                     "running": {k: run.get(k) for k in ("verdict", "moves_apart", "nearest", "same_on")}})
    pairs = []
    for a, b in combinations(read, 2):
        d, diff = M.distance(a["moves"], b["moves"])
        same = [k for k in M.BIG if k not in diff]
        pairs.append({"a": a["label"], "b": b["label"], "moves": d, "same_on": same,
                      "verdict": "one creative to Meta" if d <= 1 else "risky" if d < MIN else "distinct"})
    out = {"brand": brand, "read_at": datetime.now().isoformat(timespec="seconds"), "min_moves": MIN,
           "briefs": read, "pairs": pairs,
           "pass": all(p["verdict"] == "distinct" for p in pairs) and all(r["running"]["verdict"] != "variation" for r in read)}
    d = ROOT / "runs" / "creative-diversity" / brand / "brief-view"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{datetime.now():%Y%m%d-%H%M%S}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def _face(f):
    """The face as matrix.moves expects it: a tag-shaped dict."""
    if not f or f in ("none", "unclear"):
        return {"people": 0} if f == "none" else {}
    parts = (str(f).split("/") + ["", "", ""])[:3]
    return {"people": 1, "gender": parts[0], "age_band": parts[1], "ethnic_appearance": parts[2]}


def main():
    a = sys.argv[1:]
    brand = a[0]
    items = []
    if "--runs" in a:
        for r in a[a.index("--runs") + 1:]:
            f = Path(r) / "stages" / "5-brief.md"
            if f.exists():
                items.append((Path(r).name, f.read_text()))
    else:
        items = [(Path(f).name, Path(f).read_text()) for f in a[1:]]
    if len(items) < 1:
        sys.exit("no briefs found")
    out = view(brand, items)
    for r in out["briefs"]:
        print(f"- {r['label']}: {r['why']}\n    moves {r['moves']}\n    vs running: {r['running']['verdict']} ({r['running']['moves_apart']} moves)")
    for p in out["pairs"]:
        print(f"  {p['a'][:34]} × {p['b'][:34]}: {p['moves']} moves → {p['verdict']}  (same on {', '.join(p['same_on'])})")
    print("PASS" if out["pass"] else "NOT DISTINCT ENOUGH")


if __name__ == "__main__":
    main()
