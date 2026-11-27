"""thumbs_up.py: RETIRED AS A COVER STEP (2026-11-12). A frame with words, marks or a product cut-out laid on it is
not a cover. A cover is a picture made by image production, start to finish: `components/image-production/make.py
--purpose cover` (a version id, a frame of that version's own video, the swipe id it follows, its headline); `line.py`
step 5 runs it for every version. Asked to make covers, this file refuses and names that route (`--styles` still lists
the styles and their evidence). Rollback: steps.json `line.cover_job.on` false, or COVER_JOB_OFF=1 (team/rollbacks.md,
COVER-JOB). Everything below describes what it did, and does again with the switch off.

It was the edit line's thumbnail step: one cover per version, in the style of the platform it runs on.
thumbs.py made the plain cover (a clean frame + its words, placed by the scene); this made the styled one.
The turned-up style was a clickbait / watchbait cover. It read too polished for Meta and Instagram, which have a cover
look of their own, so the step has per-platform styles (cover_styles.json), each built from a breakdown of real covers on that platform's explore surface
(the swipes: components/asset-index/swipes, runs/asset-index/swipes/covers). "turned-up" is the original look.

  python3 thumbs_up.py <spec.json>                  every item -> <out>/<id>.jpg, plus <out>/sheet.jpg (all side by side)
  python3 thumbs_up.py <spec.json> --grid [id ...]  the same with a labelled 200 px grid, for placing marks and words
  python3 thumbs_up.py <spec.json> --only id ...    just those items
  python3 thumbs_up.py --styles                     the styles, what each draws, and the evidence behind it
  (also: python3 thumbs.py --spec <spec.json> ...)

A cover is a real frame of its own version (never an AI picture). The style decides everything around it:
  canvas            1080x1920 (instagram, tiktok, youtube-shorts, turned-up) or 1280x720 (youtube)
  grade             native (the frame as shot) or punched (contrast/saturation up, vignette)
  words             "boxes" (2-4 giant words on dark/accent boxes, tilted: turned-up), "caption" (one native line as
                    written, the platform's own type, no box), "caption-box" (the same on white rounded boxes),
                    "outline" (big white words, black outline, key word in the accent: YouTube)
  marks             which of circle / arrow / bubble / sticker / stamp the style draws; the rest are dropped and named
  absurd            0-3, the surreal dial (stand out visually without words). It works with the
                    brand's own product cut-out ("prop": a transparent PNG, e.g. the product kit's packshot-cutout.png),
                    never an AI picture: 1 one odd thing (the product stuck on the frame like a sticker, tilted, white
                    edge, top corner), 2 impossible scale (the product bigger than the room, cropped by the frame),
                    3 impossible scene (the product raining down both sides of the frame round a giant one; the
                    real frame stays readable in the middle). At 2 and 3 the product is placed off every face and
                    lips (the big one tries top, bottom, then a side; a falling one that would land on a face is left
                    out); a frame with no free place refuses the level. "words": false drops
                    the caption so the picture carries it alone.
Nothing sits on a face; key content stays inside the style's safe area. Every item is checked: the clean picture is read
for faces and lips (thumbs.scene, macOS Vision) and every word box, mark, bubble, sticker and stamp is measured against
them; one on lips, or over 5% of a face, fails the item.

spec.json (positions are in the style's canvas, 1080x1920 unless the style says otherwise; a panel's focus and a
bubble's `at` are in its source frame scaled to cover the canvas):
  {"brand": "<brand>", "out": "<folder>", "style": "instagram",          style: default for every item (turned-up if none)
   "items": [{"id": "H2", "style": "tiktok",                             an item may name its own
              "swipe": "ig-014",                                         the real cover it follows (shown on the sheet)
              "panels": [{"src": "<video or picture>", "t": 28.2, "zoom": 1.2, "focus": [540, 960]}, ...],
                         one panel fills the frame; two or more stack top to bottom, equal heights
              "caption": "my skin felt like sandpaper",                  the caption styles' line, as written (no caps)
              "caption_y": 0.55,                                         its centre, share of the height; left out, the
                                                                         step picks the clearest height in the style's bands
              "sticker": "All of my skin feels like sand paper. Can I try it for FREE?",
              "words": [["MY SKIN", ""], ["= SANDPAPER", "key"]], "words_y": 1440,
              "circle": [x, y, width, height, degrees], "arrow": [x1, y1, x2, y2],
              "bubble": {"panel": 0, "at": [x, y], "zoom": 2.5, "center": [x, y], "r": 220},
              "stamp": ["BLACK FRIDAY", "BUY 2<br>GET 1 FREE"],
              "absurd": 2, "prop": "<transparent product PNG>", "words": false}]}   absurd/prop may be set for the whole spec
"caption" is a line, or lines [["Gift for my man", ""], ["Triple discount", "key"]]: a key line sits on the dark box in
the accent (caption-box) or takes the accent colour (caption, outline). A caption style with no "caption" turns the
item's words into lines in sentence case: the words before the key word, then the key word and what follows.
Brand look (fonts, colours) comes from brands/<brand>/brand-identity/edit-style.json "thumbnail"; the native styles use
the platform's type (looks/fonts) and only take the brand's accent where the style says so. Renders through
HyperFrames (this Mac's ffmpeg has no drawtext). Brand-agnostic.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
DEFAULT = {"fonts": {"display": None, "body": None},
           "colors": {"dark": "#19110E", "accent": "#EBA53A", "light": "#FFFBF0", "mark": "#E5322D", "stamp_text": "#C8202A"}}
STYLES_FILE = HERE / "cover_styles.json"


def styles():
    return json.loads(STYLES_FILE.read_text())["styles"]


def style(name):
    S = styles()
    if name not in S:
        raise SystemExit("thumbs_up: no style %r (have: %s)" % (name, ", ".join(S)))
    return S[name]


def look(brand):
    f = REPO / "brands" / brand / "brand-identity" / "edit-style.json"
    t = (json.loads(f.read_text()).get("thumbnail") if f.exists() else None) or {}
    out = json.loads(json.dumps(DEFAULT))
    for k in ("fonts", "colors"):
        out[k].update(t.get(k) or {})
    for k, v in out["fonts"].items():          # a font path is kept relative to the shared drive ("Shared Assets/...")
        if v and not os.path.isabs(v):
            hits = sorted(Path.home().glob("Library/CloudStorage/*/Shared drives/" + v))
            out["fonts"][k] = str(hits[0]) if hits else None
    return out


def _font_css(S):
    """@font-face for the style's caption font (a looks/fonts id), and the files the page carries."""
    fid = (S.get("words") or {}).get("font")
    if not fid or fid.startswith("brand-"):
        return "", [], None
    import fonts as F
    css, files = F.faces(fid)
    return css, files, F.stack(fid)


def css(L, S):
    c = dict(L["colors"])
    W, H = S["size"]
    w = S.get("words") or {}
    face = ""
    for name, key in (("ThumbDisplay", "display"), ("ThumbBody", "body")):
        if L["fonts"].get(key):
            face += "@font-face{font-family:'%s';src:url('assets/%s.woff2') format('woff2')}" % (name, key)
    fcss, _, stack = _font_css(S)
    face += fcss
    cap_font = {"brand-body": "'ThumbBody',sans-serif", "brand-display": "'ThumbDisplay',serif"}.get(w.get("font"), stack or "sans-serif")
    accent = w.get("accent") or c["accent"]
    grade = S.get("grade") or "none"
    return face + """
html,body{margin:0;background:#000}
#stage{position:relative;width:%(W)dpx;height:%(H)dpx;overflow:hidden;background:#000;font-family:'ThumbBody',sans-serif;font-weight:600}
.pan{position:absolute;left:0;width:%(W)dpx;overflow:hidden}
.pan img{position:absolute;filter:%(grade)s}
.seam{position:absolute;left:0;right:0;height:%(seam)dpx;background:%(light)s;box-shadow:0 0 18px rgba(0,0,0,.5)}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse at 50%% 45%%,rgba(0,0,0,0) 55%%,rgba(0,0,0,.45) 100%%)}
.bubble{position:absolute;left:60px;top:300px;width:640px;background:#fff;border-radius:26px;padding:22px 30px 26px;box-shadow:0 10px 28px rgba(0,0,0,.28);color:#111;transform:scale(.88);transform-origin:0 0}
.bubble .who{font-size:30px;color:#6E6058;margin-bottom:8px}
.bubble .q{font-size:50px;line-height:1.14}
.bubble:after{content:"";position:absolute;left:46px;bottom:-26px;border:16px solid transparent;border-top:18px solid #fff}
.words{position:absolute;left:40px;right:40px;display:flex;flex-direction:column;align-items:center;gap:10px;transform:rotate(-3deg)}
.words span{display:inline-block;background:%(dark)s;color:%(light)s;font-size:104px;line-height:1;padding:14px 26px 18px;border-radius:14px;box-shadow:0 12px 30px rgba(0,0,0,.5);white-space:nowrap}
.words span.key{background:%(accent)s;color:%(dark)s;font-size:132px;transform:rotate(2deg)}
.cap{position:absolute;left:%(cap_side)dpx;right:%(cap_side)dpx;text-align:%(cap_align)s;font-family:%(cap_font)s;font-weight:%(cap_weight)s;font-size:%(cap_size)dpx;line-height:%(cap_lh)s;color:%(cap_fill)s;letter-spacing:%(cap_ls)s}
.cap.plain{text-shadow:0 2px 6px rgba(0,0,0,.55),0 0 2px rgba(0,0,0,.6)}
.cap .ln.key{color:%(accent)s}
.cap.boxed{line-height:%(box_lh)s}
.cap.boxed .ln+.ln{margin-top:%(gap).0fpx}
.cap.boxed span{background:%(box)s;color:%(box_text)s;padding:.1em .42em .14em;border-radius:.26em;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.cap.boxed .ln.key span{background:%(key_box)s;color:%(accent)s}
.cap.outline{line-height:1.02;text-transform:%(transform)s;-webkit-text-stroke:%(stroke)dpx #000;paint-order:stroke fill;text-shadow:0 4px 14px rgba(0,0,0,.45)}
.stamp{position:absolute;right:36px;top:296px;transform:rotate(9deg);background:%(light)s;border:8px solid %(dark)s;border-radius:22px;padding:14px 26px 18px;text-align:center;box-shadow:0 14px 34px rgba(0,0,0,.5)}
.stamp .a{font-family:'ThumbDisplay',serif;font-size:46px;color:%(dark)s;letter-spacing:2px}
.stamp .b{font-size:58px;color:%(stamp_text)s;line-height:1.05}
.mag{position:absolute;border-radius:50%%;border:12px solid #fff;box-shadow:0 0 0 10px %(mark)s,0 18px 40px rgba(0,0,0,.55);background-repeat:no-repeat;filter:contrast(1.2) saturate(1.3)}
svg.fx{position:absolute;inset:0;width:%(W)dpx;height:%(H)dpx;overflow:visible}
.prop{position:absolute;transform-origin:50%% 50%%}
.prop.stick{filter:drop-shadow(0 0 0 #fff) drop-shadow(7px 0 0 #fff) drop-shadow(-7px 0 0 #fff) drop-shadow(0 7px 0 #fff) drop-shadow(0 -7px 0 #fff) drop-shadow(0 18px 22px rgba(0,0,0,.45))}
.prop.giant{filter:drop-shadow(0 40px 60px rgba(0,0,0,.55))}
.prop.fall{filter:drop-shadow(0 18px 24px rgba(0,0,0,.45))}
.prop.blur{filter:blur(5px) drop-shadow(0 18px 24px rgba(0,0,0,.35));opacity:.92}
""" % dict(c, W=W, H=H, grade=grade, accent=accent, seam=S.get("seam", 12), cap_font=cap_font,
           cap_side=w.get("side", 90), cap_align=w.get("align", "center"), cap_weight=w.get("weight", 600),
           cap_size=w.get("size", 58), cap_lh=w.get("line_height", 1.22), cap_fill=w.get("fill", "#fff"),
           cap_ls=w.get("letter_spacing", "0"), box=w.get("box", "#fff"), box_text=w.get("box_text", "#111"),
           stroke=w.get("stroke", 10), transform=w.get("transform", "none"), key_box=w.get("key_box", "#111"),
           gap=_box_gap(w) * w.get("size", 58), box_lh=_box_lh(w))


BOX_LH = 1.5      # caption-box: the box padding (.1em + .14em) plus the glyphs' own height (~1.2em) fit inside 1.5em,
BOX_GAP = 0.3     # so a wrapped line's box never covers the descenders of the line above ("Why you" read "Whv vou")


def _box_lh(w):
    return max(float(w.get("line_height", 1.22)), BOX_LH)


def _box_gap(w):
    return max(float(w.get("gap", 0.18)), BOX_GAP)


def esc(t):
    return str(t).replace("&", "&amp;").replace("<br>", "\n").replace("<", "&lt;").replace("\n", "<br>")


def _sentence(t):
    t = re.sub(r"\s+", " ", str(t)).strip().lower()
    t = re.sub(r"\$(\d)", r"$\1", t)
    return t[:1].upper() + t[1:] if t else t


def sentence(words):
    """Turned-up words -> native caption lines, as written but in sentence case. The words before the first key word
    are one line; the key word and what follows are a second line marked key:
    [["GIFT FOR MY MAN", ""], ["TRIPLE", "key"], ["DISCOUNT", ""]] -> [["Gift for my man", ""], ["Triple discount", "key"]]."""
    a, b, seen = [], [], False
    for t, cls in words:
        seen = seen or cls == "key"
        (b if seen else a).append(t)
    out = [[_sentence(" ".join(a)), ""]] if a else []
    if b:
        out.append([_sentence(" ".join(b)), "key" if a else ""])
    return out


def caption_lines(it):
    """The caption as [[text, kind], ...]. A plain string is one line."""
    c = it.get("caption")
    if isinstance(c, str):
        return [[c, ""]] if c else []
    if c:
        return [[t, k] for t, k in c]
    return sentence(it["words"]) if it.get("words") else []


def grab(src, t, out, W, H):
    if Path(src).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(t or 0), "-i", src, "-frames:v", "1"]
    subprocess.run(cmd + ["-q:v", "2", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", out], check=True)


def allowed(it, S):
    """The item with only what the style draws; the names of what it dropped."""
    keep = set(S.get("marks", []))
    out, dropped = dict(it), []
    for k in ("circle", "arrow", "bubble", "sticker", "stamp"):
        if out.get(k) and k not in keep:
            dropped.append(k)
            out.pop(k)
    mode = (S.get("words") or {}).get("look", "boxes")
    if mode != "boxes" and it.get("words") is not False and (out.get("words") or out.get("caption")):
        out["caption"] = caption_lines(out)
    if mode == "none" or it.get("words") is False:
        out.pop("caption", None)
        out.pop("words", None)
    return out, dropped


def _caption_html(it, S):
    """The caption block and its box (for the face check). Lines are wrapped by the browser; the box estimate
    counts the wrapped lines from the type size."""
    w = S["words"]
    mode = w.get("look")
    lines = [l for l in (it.get("caption") or []) if l[0]]
    if not lines:
        return "", None
    W, H = S["size"]
    size = w.get("size", 58)
    side = w.get("side", 90)
    per = 0.6 if mode == "outline" else 0.52
    lh = size * (1.02 if mode == "outline" else _box_lh(w) if mode == "caption-box" else w.get("line_height", 1.22))
    gap = _box_gap(w) * size if mode == "caption-box" else 0
    rows = sum(max(1, -(-int(len(t) * size * per) // int(W - 2 * side))) for t, _ in lines)
    hgt = rows * lh + gap * (len(lines) - 1)
    y = float(it.get("caption_y", w.get("y", 0.5)))
    top = max(S.get("safe", [0, H])[0], min(y * H - hgt / 2, S.get("safe", [0, H])[1] - hgt))
    cls = {"outline": "outline", "caption-box": "boxed"}.get(mode, "plain")
    blocks = []
    for t, k in lines:
        body = esc(t)
        if mode == "caption-box":
            blocks.append(f'<div class="ln{" key" if k == "key" else ""}"><span>{body}</span></div>')
        else:
            blocks.append(f'<div class="ln{" key" if k == "key" else ""}">{body}</div>')
    return f'<div class="cap {cls}" style="top:{top:.0f}px">{"".join(blocks)}</div>', (side, top, W - side, top + hgt)


def _on_face(box, it, S):
    """True when a product box lands on a face (over 5% of it) or touches lips: the face check's own test.
    The faces come from render(), which reads the clean picture first (it["_faces"], fractions of the canvas)."""
    W, H = S["size"]
    x0, y0, x1, y1 = box
    for kind in ("lips", "faces"):
        for b in (it.get("_faces") or {}).get(kind, []):
            bx0, by0, bx1, by1 = b["x"] * W, b["y"] * H, (b["x"] + b["w"]) * W, (b["y"] + b["h"]) * H
            ix = max(0, min(x1, bx1) - max(x0, bx0)); iy = max(0, min(y1, by1) - max(y0, by0))
            if (kind == "lips" and ix * iy > 0) or (kind == "faces" and ix * iy / ((bx1 - bx0) * (by1 - by0) or 1) > 0.05):
                return True
    return False


def props(it, S):
    """The surreal dial's product cut-outs: [(class, x, y, width, degrees)] in the canvas, from the level and the id
    (seeded, so a re-render is the same picture). Nothing lands on a face or lips: the big product tries its places in
    order and a falling one that would land on a face is left out; when no place is free the level is refused."""
    import random
    lvl = int(it.get("absurd") or 0)
    if not lvl or not it.get("prop"):
        return []
    W, H = S["size"]
    ratio = _prop_ratio(it)
    rnd = random.Random(it["id"])
    if lvl == 1:
        w = W * 0.32
        return [("stick", W - w - 46, H * 0.05, w, rnd.uniform(12, 20))]
    w = W * (1.15 if lvl == 2 else 0.6)
    tilt = rnd.uniform(-12, 12) if lvl == 2 else rnd.uniform(-10, 10)
    h = w * ratio
    places = ([((W - w) / 2 + rnd.uniform(-60, 60), -w * 0.62),                # hanging in from the top
               ((W - w) / 2, H - h * 0.42),                                    # rising from the bottom
               (-w * 0.55, (H - h) / 2), (W - w * 0.45, (H - h) / 2)]          # leaning in from a side
              if lvl == 2 else
              [(W * 0.2, -H * 0.04), (W * 0.2, H - h * 0.7),
               (-w * 0.35, (H - h) / 2), (W - w * 0.65, (H - h) / 2)])
    giant = next(((x, y) for x, y in places if not _on_face((x, y, x + w, y + h), it, S)), None)
    if giant is None:
        raise SystemExit("cover %s: surreal level %d has no place for the product off the faces in this frame; "
                         "use level 1, a wider frame, or set absurd to 0" % (it["id"], lvl))
    out = [("giant", giant[0], giant[1], w, tilt)]
    if lvl == 2:
        return out
    for i in range(12):                                                         # the real frame stays readable mid-frame
        pw = W * rnd.uniform(0.12, 0.28)
        x = rnd.uniform(-pw * 0.35, W * 0.22) if i % 2 else rnd.uniform(W * 0.7, W - pw * 0.6)
        y = rnd.uniform(-H * 0.04, H * 0.94)
        r = rnd.uniform(-70, 70)
        if not _on_face((x, y, x + pw, y + pw * ratio), it, S):
            out.append(("blur" if i % 4 == 3 else "fall", x, y, pw, r))
    return out


def _prop_ratio(it):
    if it.get("prop_ratio"):
        return float(it["prop_ratio"])
    try:
        from PIL import Image
        w, h = Image.open(it["prop"]).size
        return h / w
    except Exception:
        return 1.5


def item_html(it, L, S, grid):
    W, H = S["size"]
    n = len(it["panels"])
    hgt = H // n
    body = []
    for i, p in enumerate(it["panels"]):
        z = float(p.get("zoom", 1.0)); fx, fy = p.get("focus", [W / 2, H / 2])
        w, h = W * z, H * z
        left = min(0, max(W - w, W / 2 - fx * z)); top = min(0, max(hgt - h, hgt / 2 - fy * z))   # never a gap at an edge
        body.append(f'<div class="pan" style="top:{i * hgt}px;height:{hgt}px"><img src="assets/p{i}.jpg" '
                    f'style="width:{w:.0f}px;height:{h:.0f}px;left:{left:.0f}px;top:{top:.0f}px"></div>')
        if i:
            body.append(f'<div class="seam" style="top:{i * hgt - S.get("seam", 12) // 2}px"></div>')
    if S.get("vignette"):
        body.append('<div class="vig"></div>')
    for cls, x, y, w, r in props(it, S):
        body.append(f'<img class="prop {cls}" src="assets/prop.png" style="left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;transform:rotate({r:.1f}deg)">')
    mark = L["colors"]["mark"]
    fx = []
    if it.get("circle"):
        x, y, w, h, r = it["circle"]
        for col, sw in (("#fff", 26), (mark, 16)):
            fx.append(f'<ellipse cx="{x}" cy="{y}" rx="{w / 2}" ry="{h / 2}" transform="rotate({r} {x} {y})" fill="none" stroke="{col}" stroke-width="{sw}"/>')
    if it.get("arrow"):
        x1, y1, x2, y2 = it["arrow"]
        q = f"M{x1},{y1} Q{(x1 + x2) / 2 + 60},{(y1 + y2) / 2 + 60} {x2},{y2}"
        fx.append(f'<defs><marker id="ah" markerWidth="4" markerHeight="4" refX="2.2" refY="2" orient="auto"><path d="M0,0 L4,2 L0,4 z" fill="{mark}" stroke="#fff" stroke-width=".5"/></marker></defs>'
                  f'<path d="{q}" fill="none" stroke="#fff" stroke-width="40" stroke-linecap="round"/>'
                  f'<path d="{q}" fill="none" stroke="{mark}" stroke-width="26" stroke-linecap="round" marker-end="url(#ah)"/>')
    if fx:
        body.append(f'<svg class="fx" viewBox="0 0 {W} {H}">' + "".join(fx) + "</svg>")
    b = it.get("bubble")
    if b:
        p = it["panels"][b.get("panel", 0)]
        tz = float(p.get("zoom", 1.0)) * float(b.get("zoom", 2.5)); r = b.get("r", 220)
        (mx, my), (cx, cy) = b["at"], b["center"]
        body.append(f'<div class="mag" style="left:{cx - r}px;top:{cy - r}px;width:{2 * r}px;height:{2 * r}px;'
                    f'background-image:url(assets/p{b.get("panel", 0)}.jpg);background-size:{W * tz:.0f}px {H * tz:.0f}px;'
                    f'background-position:{r - mx * tz:.0f}px {r - my * tz:.0f}px"></div>')
    if it.get("sticker"):
        body.append(f'<div class="bubble"><div class="who">Reply to a customer\'s comment</div><div class="q">{esc(it["sticker"])}</div></div>')
    mode = (S.get("words") or {}).get("look", "boxes")
    if mode == "boxes" and it.get("words"):
        ws = "".join(f'<span class="{cls}">{esc(t)}</span>' for t, cls in it["words"])
        body.append(f'<div class="words" style="top:{it.get("words_y", 1440)}px">{ws}</div>')
    elif mode in ("caption", "caption-box", "outline") and it.get("caption"):
        body.append(_caption_html(it, S)[0])
    if it.get("stamp"):
        a, bb = it["stamp"]
        body.append(f'<div class="stamp"><div class="a">{esc(a)}</div><div class="b">{esc(bb)}</div></div>')
    if grid:
        body += [f'<div style="position:absolute;left:0;right:0;top:{y}px;height:2px;background:#0f0"></div>'
                 f'<div style="position:absolute;left:4px;top:{y}px;color:#0f0;font:30px sans-serif">{y}</div>' for y in range(0, H, 200)]
        body += [f'<div style="position:absolute;top:0;bottom:0;left:{x}px;width:2px;background:#0ff"></div>'
                 f'<div style="position:absolute;top:4px;left:{x}px;color:#0ff;font:30px sans-serif">{x}</div>' for x in range(0, W, 200)]
    cid = "thumb-" + "".join(ch for ch in it["id"].lower() if ch.isalnum())
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css(L, S)}</style></head><body>'
            f'<div id="stage" data-composition-id="{cid}" data-start="0" data-width="{W}" data-height="{H}" data-fps="30" data-duration="0.5">'
            f'<div class="clip" data-start="0" data-duration="0.5" data-track-index="1">{"".join(body)}</div></div></body></html>')


def boxes(it, S):
    """Every overlay's box (x0, y0, x1, y1 in px), approximate, for the face check."""
    W, H = S["size"]
    out = []
    mode = (S.get("words") or {}).get("look", "boxes")
    if mode == "boxes" and it.get("words"):
        y = it.get("words_y", 1440)
        for t, cls in it["words"]:
            fs = 132 if cls == "key" else 104
            w = min(W - 80, len(t) * fs * 0.6 + 52); h = fs + 32
            out.append(("words " + t, (W / 2 - w / 2, y, W / 2 + w / 2, y + h))); y += h + 10
    elif it.get("caption"):
        _, b = _caption_html(it, S)
        if b:
            out.append(("caption", b))
    ratio = _prop_ratio(it) if it.get("prop") else 1.5
    for cls, x, y, w, r in props(it, S):
        out.append(("product cut-out", (x, y, x + w, y + w * ratio)))
    if it.get("circle"):
        x, y, w, h, r = it["circle"]; out.append(("circle", (x - w / 2, y - h / 2, x + w / 2, y + h / 2)))
    if it.get("bubble"):
        (cx, cy), r = it["bubble"]["center"], it["bubble"].get("r", 220); out.append(("bubble", (cx - r, cy - r, cx + r, cy + r)))
    if it.get("sticker"):
        out.append(("sticker", (60, 300, 620, 300 + 70 + 50 * (1 + len(it["sticker"]) // 26))))
    if it.get("stamp"):
        out.append(("stamp", (W - 380, 290, W - 36, 540)))
    return out


def face_check(it, S, base, sc=None):
    """Read the clean picture's faces and lips; name every overlay that lands on them."""
    import thumbs as TH
    W, H = S["size"]
    sc = sc or TH.scene(base)
    bad = []
    for name, (x0, y0, x1, y1) in boxes(it, S):
        for kind in ("lips", "faces"):
            for b in sc.get(kind, []):
                bx0, by0, bx1, by1 = b["x"] * W, b["y"] * H, (b["x"] + b["w"]) * W, (b["y"] + b["h"]) * H
                ix = max(0, min(x1, bx1) - max(x0, bx0)); iy = max(0, min(y1, by1) - max(y0, by0))
                share = ix * iy / ((bx1 - bx0) * (by1 - by0) or 1)
                if (kind == "lips" and ix * iy > 0) or (kind == "faces" and share > 0.05):
                    bad.append("%s on %s (%.0f%%)" % (name, "the lips" if kind == "lips" else "a face", share * 100))
    return bad


def _render_still(d, html, name):
    (d / "index.html").write_text(html)
    r = subprocess.run(["hyperframes", "render", "--quality", "draft", "--fps", "30", "-o", str(d / f"{name}.mp4"), "."],
                       cwd=d, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("render failed: %s" % (r.stderr or r.stdout)[-300:])
    f = d / f"{name}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.2", "-i", str(d / f"{name}.mp4"), "-frames:v", "1", "-q:v", "2", str(f)], check=True)
    return f


PLACE_COST = {"lips": 12.0, "faces": 6.0, "hands": 2.0, "salient": 1.0}


def place_caption(it, S, sc):
    """No caption_y given: try every height inside the style's bands (where that platform's covers put their words)
    and keep the one whose caption box covers the least lips, face, hands and subject, nearest the band's own spot."""
    W, H = S["size"]
    ratio = _prop_ratio(it) if it.get("prop") else 1.5
    sc = dict(sc, faces=list(sc.get("faces", [])) + [{"x": x / W, "y": y / H, "w": w / W, "h": w * ratio / H}
                                                    for cls, x, y, w, r in props(it, S) if cls != "blur"])
    best = None
    for bi, (a, b) in enumerate((S.get("words") or {}).get("bands") or [[0.2, 0.8]]):
        y = a
        while y <= b + 1e-9:
            _, box = _caption_html(dict(it, caption_y=y), S)
            x0, y0, x1, y1 = box
            cost = 0.0
            for k, wt in PLACE_COST.items():
                for q in sc.get(k, []):
                    qx0, qy0, qx1, qy1 = q["x"] * W, q["y"] * H, (q["x"] + q["w"]) * W, (q["y"] + q["h"]) * H
                    ix = max(0, min(x1, qx1) - max(x0, qx0)); iy = max(0, min(y1, qy1) - max(y0, qy0))
                    cost += wt * ix * iy / ((x1 - x0) * (y1 - y0) or 1)
            cost += 0.02 * bi + 0.05 * abs(y - (a + b) / 2)
            if best is None or cost < best[0]:
                best = (cost, round(y, 3))
            y += 0.01
    return best[1]


def render(it, L, S, out, grid=False):
    import thumbs as TH
    W, H = S["size"]
    d = Path(tempfile.mkdtemp(prefix="thumb-"))
    try:
        (d / "assets" / "fonts").mkdir(parents=True)
        for key, f in L["fonts"].items():
            if f:
                shutil.copy(f, d / "assets" / f"{key}.woff2")
        _, files, _ = _font_css(S)
        fid = (S.get("words") or {}).get("font")
        for f in files:
            shutil.copy(f, d / "assets" / "fonts" / f"{fid}-{f.name}")
        for i, p in enumerate(it["panels"]):
            grab(p["src"], p.get("t"), str(d / "assets" / f"p{i}.jpg"), W, H)
        if it.get("prop") and it.get("absurd"):
            shutil.copy(it["prop"], d / "assets" / "prop.png")
        (d / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}))
        (d / "meta.json").write_text(json.dumps({"id": "thumb-" + it["id"], "name": "thumb-" + it["id"]}))
        bare = {k: v for k, v in it.items() if k in ("id", "panels")}       # the clean picture: placement and the face check
        base = _render_still(d, item_html(bare, L, S, False), "base")
        sc = TH.scene(base)
        it = dict(it, _faces={k: sc.get(k, []) for k in ("faces", "lips")})   # the product keeps off these
        if it.get("caption") and "caption_y" not in it and (S.get("words") or {}).get("look") != "boxes":
            it = dict(it, caption_y=place_caption(it, S, sc))
        f = Path(out) / ("%s%s.jpg" % (it["id"], "-grid" if grid else ""))
        shutil.copy(_render_still(d, item_html(it, L, S, grid), "t"), f)
        return f, face_check(it, S, base, sc), it.get("caption_y")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def show_styles():
    for name, S in styles().items():
        w = S.get("words") or {}
        print("%-15s %dx%d  grade %s  words %s%s  marks %s" % (name, S["size"][0], S["size"][1], "punched" if S.get("grade", "none") != "none" else "native",
              w.get("look"), (" (" + w.get("font", "") + ")") if w.get("font") else "", ", ".join(S.get("marks", [])) or "none"))
        for e in S.get("evidence", []):
            print("    -", e)


def main(a):
    if a and a[0] == "--styles":
        return show_styles()
    import thumbs as TH
    TH.refuse_as_cover_step("thumbs_up.py (thumbs.py --spec)")
    spec = json.loads(Path(a[0]).read_text())
    grid = "--grid" in a
    only = [x for x in a[1:] if not x.startswith("--")]
    L = look(spec["brand"])
    out = Path(spec["out"]); out.mkdir(parents=True, exist_ok=True)
    made, fails = [], []
    for it in spec["items"]:
        if only and it["id"] not in only:
            continue
        it = dict({k: spec[k] for k in ("absurd", "prop") if k in spec}, **it)     # spec-wide defaults
        if spec.get("words") is False:                                              # a set with no words wins over
            it["words"] = False                                                     # each item's own thumbnail words
        sname = it.get("style") or spec.get("style") or "turned-up"
        S = style(sname)
        it2, dropped = allowed(it, S)
        f, bad, cy = render(it2, L, S, out, grid)
        made.append(f)
        note = ("  caption at %.0f%% of the height" % (cy * 100)) if cy is not None and "caption_y" not in it else ""
        note += ("  (style %s leaves out: %s)" % (sname, ", ".join(dropped))) if dropped else ""
        print(it["id"], sname, f, ("OK" if not bad else "ON A FACE: " + "; ".join(bad)) + note)
        fails += [it["id"]] if bad else []
    if len(made) > 1:
        args = sum([["-i", str(f)] for f in made], [])
        sheet = out / ("sheet-grid.jpg" if grid else "sheet.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex",
                        f"{''.join(f'[{i}:v]scale=400:-2[s{i}];' for i in range(len(made)))}{''.join(f'[s{i}]' for i in range(len(made)))}hstack={len(made)}",
                        "-q:v", "3", str(sheet)], check=True)
        print("sheet", sheet)
    if fails and not grid:
        raise SystemExit("thumbs_up: %s cover a face or lips: move the words or marks (use --grid)" % ", ".join(fails))


if __name__ == "__main__":
    main(sys.argv[1:])
