"""Designed type: the words set by a real layout in the brand's own fonts, in place of the compositor's stamped type.

A set record carries `design`: {"layout": "big-offer", "slots": {"zone_a": "head", ...}, "area": {"top": 15, "bottom": 58,
"left": 8, "right": 92}, "ink": "#1A1A1A", "ground": "#EEE7D7", "fonts": {"display": ..., "sans": ...}}. The board's words reach the slots through the type layer,
so a change of words on the board changes the picture. `area` is in percent of the frame, inside the safe zone and clear
of the product; the page shrinks everything together until the words fit it, and a layout that cannot fit is refused.
"""
import base64
import html
import json
import re
import subprocess
import tempfile
from pathlib import Path

from . import paths as P

CHROMES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium"]
SAFE = {"top": 14.8, "bottom": 85.2, "left": 5.0, "right": 95.0}
FIT = """<script>Promise.all([document.fonts.load('20px Display'),document.fonts.load('20px Sans')]).then(()=>{const a=document.querySelector('[data-fit]'),r=document.documentElement;let s=1;
const over=()=>a.scrollHeight>a.clientHeight+1||[...a.querySelectorAll('.line')].some(l=>l.scrollWidth>a.clientWidth+1);
while(s>.2&&over()){s-=.01;r.style.setProperty('--s',s)}
document.body.dataset.fit=JSON.stringify({scale:+s.toFixed(2),ok:!over(),fonts:document.fonts.check('20px Display')&&document.fonts.check('20px Sans'),
words:a.innerText})})</script>"""


def _font(rel):
    """Font files live on the company drive, never in git; `rel` is the path below the drive's top folder."""
    for root in Path.home().glob("Library/CloudStorage/*/Shared drives/Shared Assets"):
        if (root / rel).is_file():
            return root / rel
    raise FileNotFoundError("font not on the drive: " + rel)


def _fonts(d):
    out = []
    for name, f in (("Display", d["fonts"]["display"]), ("Sans", d["fonts"]["sans"])):
        b = base64.b64encode(_font(f).read_bytes()).decode()
        out.append("@font-face{font-family:%s;src:url(data:font/woff2;base64,%s)}" % (name, b))
    return "".join(out)


def slots_of(layer):
    """The board's words by slot. `offer` splits itself: its last line is the price, the lines above it the lead."""
    got = {}
    for e in layer.get("elements") or []:
        slot = (layer["design"].get("slots") or {}).get(str(e.get("element")))
        if slot and e.get("text"):
            got.setdefault(slot, []).append(e["text"].strip())
    words = {k: "\n".join(v) for k, v in got.items()}
    if "offer" in words:
        lines = words.pop("offer").split("\n")
        words["price"], words["lead"] = lines[-1], " ".join(lines[:-1])
    return words


def page(plate, layer):
    d = layer["design"]
    body = (P.home() / "type-layouts" / (d["layout"] + ".html")).read_text()
    words = slots_of(layer)
    for k in re.findall(r"\{\{(\w+)\}\}", body):
        if k in ("ink", "ground"):
            v = d.get(k) or {"ink": "#1A1A1A", "ground": "#EEE7D7"}[k]
        else:
            lines = words.get(k, "").split("\n")
            v = "<br>".join(html.escape(x) for x in lines) if k == "head" and d["layout"] == "headline-badge" else html.escape((" · " if k == "cta" else " ").join(lines))
        body = body.replace("{{%s}}" % k, v)
    a = {**SAFE, **(d.get("area") or {})}
    if a["top"] < SAFE["top"] or a["bottom"] > SAFE["bottom"]:
        raise ValueError("the type area leaves the safe zone")
    img = base64.b64encode(Path(plate).read_bytes()).decode()
    return ("<!doctype html><meta charset=utf-8><style>%s:root{--s:1}*{box-sizing:border-box}html,body{margin:0;width:1080px;height:1920px;overflow:hidden}"
            "body{background:url(data:image/png;base64,%s) 0 0/1080px 1920px;color:%s}"
            ".area{position:absolute;top:%s%%;bottom:%s%%;left:%s%%;right:%s%%;display:flex;flex-direction:column;align-items:center;text-align:center;overflow:hidden}"
            ".line{max-width:100%%;white-space:nowrap}</style><body>%s%s"
            % (_fonts(d), img, d.get("ink", "#1A1A1A"), a["top"], 100 - a["bottom"], a["left"], 100 - a["right"], body, FIT))


def _chrome(args):
    bin_ = next((c for c in CHROMES if Path(c).exists()), None)
    if not bin_:
        raise RuntimeError("no Chrome on this machine to render the layout")
    return subprocess.run([bin_, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                           "--window-size=1080,1920", "--virtual-time-budget=4000"] + args, capture_output=True, text=True, timeout=90)


def render(plate, layer, out):
    """Set the layout over the plate at `out`. Returns the same shape as words.set_on_top."""
    work = Path(tempfile.mkdtemp(prefix="type-"))
    f = work / "page.html"
    f.write_text(page(plate, layer))
    dom = _chrome(["--dump-dom", f.as_uri()]).stdout
    m = re.search(r'data-fit="([^"]+)"', dom)
    fit = json.loads(html.unescape(m.group(1))) if m else {}
    if not fit.get("ok") or not fit.get("fonts"):
        return {"ok": False, "plate": str(plate), "elements": 0, "notes": ["the layout did not fit or lost its fonts: %s" % fit]}
    shot = work / "shot.png"
    _chrome(["--screenshot=" + str(shot), f.as_uri()])
    if not shot.is_file():
        return {"ok": False, "plate": str(plate), "elements": 0, "notes": ["Chrome made no picture"]}
    Path(out).write_bytes(shot.read_bytes())
    return {"ok": True, "plate": str(plate), "elements": len(layer.get("elements") or []), "notes": ["designed type: %s" % fit]}
