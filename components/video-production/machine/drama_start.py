#!/usr/bin/env python3
"""How a micro drama starts: from a swipe (its beats are the swipe's), or our own with no swipe (its beats are a drama
story preset's). Owner, 2026-11-27: "i'm going to do my best to just inject a bunch of the swipes ... but we should
also have the ability to build our own without a swipe."

    drama_start.py preset --brand B --avatar A [--awareness LEVEL] [--style STYLE]
        the drama story preset for a no-swipe film: creative-controls story_presets.json, script format micro-drama,
        live-action (style cinematic-live) unless another style is named; rotating away from presets already written
        for this brand's avatar; its arc fitted to the awareness level. Prints {id, name, why, used}.

The no-swipe film is then made by the writing chain's own from-scratch door, unchanged:
    scratch.py <label> --brand B --product P --avatar A --preset <id>   then   run.py <label> --autonomous
Spends nothing, calls no model. Brand-agnostic; Python 3.9, standard library.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "run-kit"))
from run_kit.paths import repo  # noqa: E402

WS = repo(HERE)
LIVE = "cinematic-live"


def _presets():
    cc = str(WS / "components" / "creative-controls")
    if cc not in sys.path:
        sys.path.append(cc)
    import story_presets as SP
    return SP


def used(brand, avatar):
    """Story presets already written for this brand's avatar, read from the writing runs' run.json."""
    out = []
    root = WS / "runs" / "video-teardown" / "_work"
    for f in (root.glob("*/run.json") if root.is_dir() else []):
        try:
            st = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        who = ((st.get("declared_audience") or {}).get("avatar") or (st.get("audience") or {}).get("_avatar") or "")
        sp = (st.get("story_preset") or {}).get("id")
        if sp and st.get("brand") == brand and who == avatar:
            out.append(sp)
    return out


def preset(brand, avatar, awareness=None, style=LIVE):
    SP = _presets()
    had = used(brand, avatar)
    ranked = [(p, why) for p, why in SP.pick(script_format="micro-drama", awareness=awareness, length="short", used=had)
              if (p.get("format") or {}).get("style") == style]
    if not ranked:
        raise SystemExit("no micro-drama story preset in style %r" % style)
    p, why = ranked[0]
    return {"id": p["id"], "name": p["name"], "why": "; ".join(why) if isinstance(why, list) else str(why or ""),
            "style": style, "used": sorted(set(had))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preset"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--awareness")
    ap.add_argument("--style", default=LIVE)
    a = ap.parse_args(argv)
    print(json.dumps(preset(a.brand, a.avatar, a.awareness, a.style), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
