"""THE LAYERS TEMPLATE (2026-11-13): the props a swipe floats in, and its flashes, laid the one way every time.

    python3 layers.py build <production> <scene>     write the scene's layer card from brief.json "layers"
    python3 layers.py check <production> <scene>     the placement rules, read off what would be laid

brief.json "layers": {"<scene>": {"props": [{"picture": <cut-out .png>, "at": s, "until": s|null, "label": "...",
                                             "caption": "<a word under it, optional>"}],
                                  "flash": [{"at": s, "color": "#d4141b"}]}}

THE STANDARD (13 Nov review: props covered a face, sat too large and off centre, and bounced), the same for every prop
and every brand:
  - centred across the frame, standing at waist height (its foot at FOOT of the frame's height);
  - HEIGHT of the frame's height at most, smaller than a face in a wide shot;
  - never on screen during a close-up shot of the scene (shot-list rows whose `swipe_camera` says close-up): a
    prop's time is cut back so it is gone before the close-up starts and does not come back in it;
  - a clean pop: it appears and leaves in two frames, no bounce, no float;
  - the picture is an image-production cut-out (a file with a run.json beside it or one folder up), never drawn.
  - a flash: the frame punches in and blurs through a coloured flash, 0.42 s, at its second (the swipe's red whip).

The card is a HyperFrames project at scenes/<scene>/card/ (index.template.html, the same contract the Studio's card
step renders: {{DUR}}, the cut under it as assets/bg.mp4) and the scene's take carries one hyperframes.card step.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os  # noqa: E402
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves

FOOT = 0.86          # where a prop stands: its foot at 86% of the frame's height (waist height in a medium shot)
HEIGHT = 0.20        # a prop's height: 20% of the frame's height at most
W, H = 1080, 1920


def _load(p, d=None):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def closeups(rows, scene, dur):
    """The scene's close-up windows [(a, b)] in seconds of the scene, from its shot-list rows and their shares."""
    out, at = [], 0.0
    for r in [r for r in rows if r.get("scene") == scene]:
        span = float(r.get("share") or 0) * dur
        if "close" in str(r.get("swipe_camera") or "").lower():
            out.append((round(at, 3), round(at + span, 3)))
        at += span
    return out


def fit(props, cu, dur):
    """Each prop's on-screen window, cut back so it never shows in a close-up. A prop that starts inside a close-up
    waits for its end. Returns [{..., "at", "until", "trimmed"}]."""
    out = []
    for p in props:
        a, b = float(p["at"]), float(p.get("until") if p.get("until") is not None else dur)
        trimmed = []
        for ca, cb in cu:
            if ca <= a < cb:
                trimmed.append("starts after the close-up %.2f-%.2f s" % (ca, cb))
                a = cb
            if a < ca < b:
                trimmed.append("leaves before the close-up %.2f-%.2f s" % (ca, cb))
                b = ca
        if b - a > 0.05:
            out.append(dict(p, at=round(a, 3), until=round(b, 3), trimmed=trimmed))
    return out


def from_tool(picture) -> bool:
    p = Path(picture)
    return p.is_file() and any((d / "run.json").is_file() for d in (p.parent, p.parent.parent))


def check(props, cu, dur):
    """Rows for the edit stage: one per prop, ok when it is an image-production cut-out and never in a close-up."""
    rows = []
    for p in fit(props, cu, dur):
        ok = from_tool(p["picture"])
        rows.append({"name": p.get("label") or Path(p["picture"]).stem, "ok": ok,
                     "short": "%.2f-%.2f s, centred, waist height, %d%% tall" % (p["at"], p["until"], HEIGHT * 100),
                     "detail": (("Kept out of close-ups: " + "; ".join(p["trimmed"]) + ". ") if p["trimmed"] else "") +
                               ("" if ok else "Not an image-production cut-out: make it with image production "
                                              "(purpose prop) and name its -cut.png.")})
    return rows


HTML = """<!doctype html>
<html><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
html,body{margin:0;background:#000}
#stage{position:relative;width:%(W)dpx;height:%(H)dpx;overflow:hidden;background:#000}
#bg{position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover}
.prop{position:absolute;left:50%%;bottom:%(bottom)dpx;transform:translateX(-50%%);opacity:0;filter:drop-shadow(0 14px 24px rgba(0,0,0,.5))}
.prop img{height:%(ph)dpx;width:auto;display:block}
.prop .cap{font:700 56px/1 "Helvetica Neue",Arial,sans-serif;color:#fff;text-align:center;margin-top:8px;text-shadow:0 3px 10px rgba(0,0,0,.7)}
.flash{position:absolute;inset:0;opacity:0}
</style></head><body>
<div id="stage" data-composition-id="layers" data-start="0" data-width="%(W)d" data-height="%(H)d" data-fps="30" data-duration="{{DUR}}">
<video id="bg" class="clip" data-start="0" data-duration="{{DUR}}" data-track-index="1" data-timeline-label="the cut" src="assets/bg.mp4" data-media-start="0" muted playsinline></video>
<div class="clip" data-start="0" data-duration="{{DUR}}" data-track-index="2" data-timeline-label="Layers · props and flashes (layers.py)">
%(body)s
<script>
const tl=gsap.timeline({paused:true});
%(js)s
window.__timelines=window.__timelines||{};window.__timelines["layers"]=tl;
</script>
</div></div></body></html>
"""


def html(props, flashes):
    body, js = [], []
    for i, p in enumerate(props):
        cap = ('<div class="cap">%s</div>' % p["caption"]) if p.get("caption") else ""
        body.append('<div class="prop" id="p%d"><img src="assets/%s" alt="">%s</div>' % (i, Path(p["picture"]).name, cap))
        js.append('tl.set("#p%d",{opacity:1},%.3f);' % (i, p["at"]))
        js.append('tl.set("#p%d",{opacity:0},%.3f);' % (i, p["until"]))
    for i, f in enumerate(flashes):
        body.append('<div class="flash" id="f%d" style="background:%s"></div>' % (i, f.get("color", "#d4141b")))
        a = float(f["at"])
        js.append('tl.to("#bg",{filter:"blur(18px)",scale:1.18,duration:.12,ease:"power2.in"},%.3f);' % a)
        js.append('tl.to("#f%d",{opacity:.82,duration:.1},%.3f);tl.to("#f%d",{opacity:0,duration:.22},%.3f);' % (i, a + 0.04, i, a + 0.2))
        js.append('tl.to("#bg",{filter:"blur(0px)",scale:1,duration:.22,ease:"power2.out"},%.3f);' % (a + 0.2))
    return HTML % {"W": W, "H": H, "bottom": int(H * (1 - FOOT)), "ph": int(H * HEIGHT), "body": "\n".join(body), "js": "\n".join(js)}


def build(B, scene, spec, rows, dur, rows_scene=None):
    """Write scenes/<scene>/card/ from the spec ({"props", "flash"}); returns (card step, check rows). rows_scene: the
    shot-list scene whose close-ups apply (a hook version uses the first scene's rows). The card is rewritten only
    when it changes, so an unchanged layer never asks for a new render."""
    B = Path(B)
    cu = closeups(rows, rows_scene or scene, dur)
    props = fit(spec.get("props") or [], cu, dur)
    proj = B / "scenes" / scene / "card"
    (proj / "assets").mkdir(parents=True, exist_ok=True)
    for p in props:
        if Path(p["picture"]).is_file():
            shutil.copy(p["picture"], proj / "assets" / Path(p["picture"]).name)
    page = html(props, spec.get("flash") or [])
    tpl = proj / "index.template.html"
    if not tpl.exists() or tpl.read_text() != page:
        tpl.write_text(page)
    (proj / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}))
    (proj / "meta.json").write_text(json.dumps({"id": "layers-%s" % scene, "name": "layers-%s" % scene}))
    step = {"id": "card-1", "tool": "hyperframes.card", "model": None, "prompt": "layers: %d props, %d flashes (layers.py)"
            % (len(props), len(spec.get("flash") or [])), "seed": None, "inputs": {"project": "card"},
            "params": {"in": 0.0, "out": dur}, "note": "the layers template: centred, waist height, never in a close-up"}
    return step, check(spec.get("props") or [], cu, dur)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 3 or a[0] not in ("build", "check"):
        sys.exit(__doc__)
    import settings as ST
    B = ST.BRIEFS / a[1]
    spec = ((_load(B / "brief.json", {}) or {}).get("layers") or {}).get(a[2]) or {}
    rows = (_load(B / "shot-list.json", {}) or {}).get("shots") or []
    dur = next((s["end"] - s["start"] for s in (_load(B / "studio-build" / "layout.json", {}) or {}).get("scenes") or []
                if s["scene"] == a[2]), 15.0)
    if a[0] == "build":
        step, rows_ = build(B, a[2], spec, rows, dur)
    else:
        rows_ = check(spec.get("props") or [], closeups(rows, a[2], dur), dur)
    for r in rows_:
        print("%s %-24s %s %s" % ("✓" if r["ok"] else "✗", r["name"], r["short"], r["detail"]))
